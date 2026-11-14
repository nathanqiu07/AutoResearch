"""Optional WS A development backends; shared research LLM code is untouched."""
import json
import math
import os
import subprocess
import tempfile
import threading
import urllib.request

from ..llm import LLM


class OpenAILLM(LLM):
    """Direct, tool-free Responses API with conservative pre-request cost bounds.

    Prices are list-price estimates, not billing reconciliation. Input estimates
    include the 1.25x cache-write premium even when it is not charged. Failed
    reservations remain held; any reported usage is charged in addition to that
    hold. This intentionally overestimates rather than silently reusing money.
    """
    name = "openai-responses"
    base_url = "https://api.openai.com/v1/responses"
    # USD per million tokens; conservative short-context input rate includes
    # the stated 30-minute cache-write premium. Unknown prices fail closed.
    RATES = {"gpt-6-luna": (.10 * 1.25, .50)}
    SHORT_CONTEXT_LIMIT = 272000

    def __init__(self, model="gpt-6-luna", budget=None, max_usd=.10, timeout=60):
        super().__init__(budget)
        if model not in self.RATES:
            raise ValueError("unsupported model: no approved conservative price bound")
        for name, value in (("max_usd", max_usd), ("timeout", timeout)):
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                    not math.isfinite(value) or value <= 0):
                raise ValueError(name + " must be a finite positive number")
        self.model, self.max_usd, self.timeout = model, float(max_usd), float(timeout)
        self.spent_usd, self.reserved_usd, self._inflight = 0., 0., 0
        self._cost_lock = threading.Lock()

    def cost_summary(self):
        with self._cost_lock:
            return {"model": self.model, "max_usd": self.max_usd,
                    "spent_usd": self.spent_usd, "reserved_usd": self.reserved_usd,
                    "remaining_usd": max(0., self.max_usd - self.spent_usd - self.reserved_usd),
                    "cost_basis": "conservative_list_price_estimate_including_cache_write_premium",
                    "failed_reservations": "retained_in_addition_to_any_reported_usage"}

    def _price(self, input_tokens, output_tokens):
        inp, out = self.RATES[self.model]
        return (input_tokens * inp + output_tokens * out) / 1_000_000

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.0):
        # temperature is deliberately ignored: reasoning=none and fixed default
        # tier define this backend; unsupported sampling parameters are not sent.
        if not isinstance(prompt, str) or not isinstance(system, str):
            raise ValueError("prompt and system must be text")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 65536:
            raise ValueError("max_tokens must be an integer in [1, 65536]")
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured")
        body = {"model": self.model, "instructions": system, "input": prompt,
                "max_output_tokens": max_tokens, "reasoning": {"effort": "none"},
                "store": False, "service_tier": "default"}
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        # A byte bound plus overhead is deliberately much larger than ordinary
        # text tokenization. Including output keeps the entire request short.
        input_bound = len(encoded) + 1000
        if input_bound + max_tokens >= self.SHORT_CONTEXT_LIMIT:
            raise ValueError("request exceeds conservative short-context token bound")
        reservation = self._price(input_bound, max_tokens)
        with self._cost_lock:
            if self.budget.exhausted() or self.budget.calls + self._inflight >= self.budget.max_calls:
                raise RuntimeError("OpenAI call/time budget exhausted")
            if self.spent_usd + self.reserved_usd + reservation > self.max_usd:
                raise RuntimeError("OpenAI dollar budget cannot reserve this request")
            self.reserved_usd += reservation
            self._inflight += 1
        input_tokens, output_tokens, succeeded = 0, 0, False
        try:
            headers = {"Content-Type": "application/json",
                       "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}
            for variable, header in (("OPENAI_ORG_ID", "OpenAI-Organization"),
                                     ("OPENAI_PROJECT_ID", "OpenAI-Project")):
                if os.environ.get(variable):
                    headers[header] = os.environ[variable]
            request = urllib.request.Request(self.base_url, data=encoded, headers=headers, method="POST")
            remaining_seconds = self.budget.max_seconds - self.budget.elapsed
            if remaining_seconds <= 0:
                raise RuntimeError("time budget exhausted")
            # Exactly one request. Retrying an unknown outcome could spend twice.
            with urllib.request.urlopen(request, timeout=min(self.timeout, remaining_seconds)) as response:
                if getattr(response, "status", 200) != 200:
                    raise RuntimeError("unexpected HTTP status")
                payload = response.read(8_000_001)
            if len(payload) > 8_000_000:
                raise RuntimeError("response too large")
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("invalid response")
            usage = data.get("usage", {})
            if (not isinstance(usage, dict) or any(isinstance(usage.get(key), bool) or
                    not isinstance(usage.get(key), int) or usage[key] < 0
                    for key in ("input_tokens", "output_tokens"))):
                raise ValueError("invalid usage")
            input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
            if input_tokens > input_bound or output_tokens > max_tokens:
                raise ValueError("usage exceeded reserved bounds")
            if data.get("status") != "completed" or data.get("error"):
                raise ValueError("response not completed")
            output = data.get("output")
            if not isinstance(output, list) or not output:
                raise ValueError("missing output")
            texts = []
            for item in output:
                if not isinstance(item, dict):
                    raise ValueError("invalid output item")
                # Reasoning metadata carries no user-facing answer; tool calls,
                # refusals and partially completed assistant messages are errors.
                if item.get("type") == "reasoning":
                    continue
                if (item.get("type") != "message" or item.get("role") != "assistant" or
                        item.get("status") != "completed" or not isinstance(item.get("content"), list)):
                    raise ValueError("unexpected output item")
                for part in item["content"]:
                    if (not isinstance(part, dict) or part.get("type") != "output_text" or
                            not isinstance(part.get("text"), str)):
                        raise ValueError("unexpected message content")
                    texts.append(part["text"])
            text = "".join(texts)
            if not text.strip():
                raise ValueError("empty completed output")
            succeeded = True
            return text
        except Exception:
            # Never surface request bodies, keys, server messages, or chained
            # network exceptions, any of which may contain credentials or data.
            raise RuntimeError("OpenAI request failed or returned an invalid/incomplete response; "
                               "reservation retained, no retry performed") from None
        finally:
            cost = self._price(input_tokens, output_tokens)
            self.budget.charge(input_tokens, output_tokens, cost)
            with self._cost_lock:
                self._inflight -= 1
                self.spent_usd += cost
                if succeeded:
                    self.reserved_usd = max(0., self.reserved_usd - reservation)


class CodexLLM(LLM):
    """ChatGPT-authenticated CLI development harness, not a raw-model API claim.

    CLI token/temperature limits differ from APIs. Keep this backend in its own
    comparison and pin a model before a final run. No tools may appear in a result.
    """
    name = "codex-cli"

    def __init__(self, model="default", budget=None, binary="codex", timeout=180):
        super().__init__(budget)
        self.model, self.binary, self.timeout = model, binary, timeout

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.0):
        cmd = [self.binary, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
               "--sandbox", "read-only", "--json", "--color", "never",
               "-c", "project_doc_max_bytes=0", "-c", 'web_search="disabled"',
               "-c", 'model_reasoning_effort="low"',
               "-c", "suppress_unstable_features_warning=true",
               "-c", "features.skip_host_skill_discovery=true"]
        for feature in ("shell_tool", "apps", "plugins", "memories", "multi_agent", "multi_agent_v2",
                        "browser_use", "browser_use_external", "computer_use", "image_generation",
                        "view_image", "skill_search", "workspace_dependencies", "goals", "sleep_tool"):
            cmd += ["-c", "features.%s=false" % feature]
        if self.model != "default":
            cmd += ["--model", self.model]
        cmd += ["-"]
        with tempfile.TemporaryDirectory(prefix="ar_taste_codex_") as cwd:
            proc = subprocess.run(cmd, input=system + "\n\n" + prompt,
                                  capture_output=True, text=True, timeout=self.timeout, cwd=cwd)
        if proc.returncode:
            raise RuntimeError("Codex CLI failed (exit %s); check login/model availability" % proc.returncode)
        messages, usage, unexpected, completed = [], {}, [], False
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("Codex CLI returned invalid event JSON") from exc
            if event.get("type") in ("error", "turn.failed"):
                raise RuntimeError("Codex CLI turn failed")
            if event.get("type") == "turn.completed":
                usage = event.get("usage", {})
                completed = True
            item = event.get("item", {})
            if event.get("type") == "item.completed":
                if item.get("type") == "agent_message":
                    messages.append(item.get("text", ""))
                elif item.get("type") != "reasoning":
                    unexpected.append(item.get("type"))
        self.budget.charge(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        if unexpected:
            raise RuntimeError("Codex returned non-message items %r; result excluded" % unexpected)
        if not completed or not messages:
            raise RuntimeError("Codex returned no completed prediction")
        return messages[-1]
