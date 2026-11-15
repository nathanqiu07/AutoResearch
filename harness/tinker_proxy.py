"""Local OpenAI-compatible server in front of Tinker sampling (WS C2).

Kimi K2.6, the main target (Nathan, 2026-11-15; K2.5 is deprecated on Tinker), is served by Tinker,
not as an OpenAI endpoint. This proxy lets everything that speaks the OpenAI chat
API (autoresearch's OpenAICompatLLM, Inspect's openai-api/<name>/<model> in the
Petri harness) use Tinker models. Prompts are built and replies parsed with
tinker_cookbook's renderer for the model, so the chat template, tool-call format
and thinking blocks are Tinker's own: thinking -> `reasoning_content` (raw chain
of thought, for A1), tool calls -> OpenAI `tool_calls` (Petri targets call tools).

Spend guards (Nathan, 2026-11-15: stay inside the team's Tinker credits):
- --budget-usd: lifetime dollar cap, kept in --ledger (default ~/.autoresearch/tinker_ledger.json),
  which persists across proxy runs, so smoke + baseline + control + E3b share one budget.
- --run-budget-usd: cap for this proxy run only.
- Each request reserves its worst case (prompt + max_tokens at list price) before sampling, so
  concurrent requests cannot overshoot; the reservation is replaced by the actual cost after.
- Cost uses list prices with no cache discount, so the ledger overestimates the bill. It only sees
  this machine: the Tinker console is the real balance.
- --max-completion-tokens clamps each request's max_tokens, bounding the worst case per call.
- --max-total-tokens: the older token cap, still enforced per run.
Past any cap, requests get HTTP 429, so samples become errors instead of spending more.

    pip install tinker tinker-cookbook       # in the Petri environment
    export TINKER_API_KEY=...                # your own key, never committed
    python harness/tinker_proxy.py --list-models          # free: what Tinker serves right now
    python harness/tinker_proxy.py --port 8100 --model moonshotai/Kimi-K2.6 --budget-usd 300 --run-budget-usd 15
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# USD per 1M tokens (prefill, sample), https://thinkingmachines.ai/tinker/pricing as of 2026-10-19.
TINKER_PRICES: Dict[str, Tuple[float, float]] = {
    "moonshotai/Kimi-K2.6": (2.205, 5.49),
    # K2.5 is no longer on the pricing page (Tinker's deprecation page lists it, replacement K2.6).
    # If it still serves, it is assumed to cost the same as K2.6 (same architecture).
    "moonshotai/Kimi-K2.5": (2.205, 5.49),
}
DEFAULT_COMPLETION_TOKENS = 16384   # Petri sends no max_tokens; K2.6 can think past 4096 on an agentic turn
DEFAULT_LEDGER = "~/.autoresearch/tinker_ledger.json"


def completion_limit(req: dict, ceiling: int) -> int:
    """The request's max_tokens (default DEFAULT_COMPLETION_TOKENS), clamped to ceiling when ceiling > 0."""
    asked = int(req.get("max_tokens") or req.get("max_completion_tokens") or DEFAULT_COMPLETION_TOKENS)
    return min(asked, ceiling) if ceiling > 0 else asked


class BudgetExceeded(Exception):
    pass


class Budget:
    """Dollar spend guard whose spend persists in a JSON ledger shared by every proxy run."""

    def __init__(self, ledger_path: str, total_usd: float, run_usd: float, prices: Dict[str, Tuple[float, float]]):
        self.path = Path(ledger_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.total_usd, self.run_usd, self.prices = float(total_usd), float(run_usd), prices
        self.lock = threading.Lock()
        self.pending = 0.0      # worst-case cost of requests in flight in this process
        self.run_spent = 0.0

    @staticmethod
    def cost(price: Tuple[float, float], prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens * price[0] + completion_tokens * price[1]) / 1e6

    @staticmethod
    def price_for(prices: Dict[str, Tuple[float, float]], model: str) -> Tuple[float, float]:
        if model not in prices:
            raise ValueError(f"no Tinker price for {model!r}: add it to TINKER_PRICES or pass --price {model}=PREFILL,SAMPLE")
        return prices[model]

    @contextlib.contextmanager
    def _file_lock(self):
        # Serialises ledger updates between proxy processes on this machine.
        import fcntl
        with open(str(self.path) + ".lock", "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except FileNotFoundError:
            return {"spent_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "requests": 0, "by_model": {}}

    def spent_total(self) -> float:
        return float(self._read().get("spent_usd", 0.0))

    def reserve(self, model: str, prompt_tokens: int, max_completion: int) -> Optional[str]:
        """None if the worst case fits both budgets (and is now held), else the refusal reason."""
        worst = self.cost(self.price_for(self.prices, model), prompt_tokens, max_completion)
        with self.lock:
            with self._file_lock():
                spent = self.spent_total()
            if spent + self.pending + worst > self.total_usd + 1e-9:
                return (f"lifetime Tinker budget: ${spent:.2f} spent + ${self.pending:.2f} in flight + "
                        f"${worst:.2f} worst case > ${self.total_usd:.2f} (ledger {self.path})")
            if self.run_usd > 0 and self.run_spent + self.pending + worst > self.run_usd + 1e-9:
                return (f"per-run Tinker budget: ${self.run_spent:.2f} spent + ${self.pending:.2f} in flight + "
                        f"${worst:.2f} worst case > ${self.run_usd:.2f}")
            self.pending += worst
            return None

    def release(self, model: str, prompt_tokens: int, max_completion: int):
        worst = self.cost(self.price_for(self.prices, model), prompt_tokens, max_completion)
        with self.lock:
            self.pending = max(0.0, self.pending - worst)

    def settle(self, model: str, prompt_tokens: int, max_completion: int, completion_tokens: int):
        price = self.price_for(self.prices, model)
        actual = self.cost(price, prompt_tokens, completion_tokens)
        with self.lock:
            self.pending = max(0.0, self.pending - self.cost(price, prompt_tokens, max_completion))
            self.run_spent += actual
            with self._file_lock():
                data = self._read()
                data["spent_usd"] = round(float(data.get("spent_usd", 0.0)) + actual, 6)
                for k, v in (("prompt_tokens", prompt_tokens), ("completion_tokens", completion_tokens), ("requests", 1)):
                    data[k] = int(data.get(k, 0)) + v
                m = data.setdefault("by_model", {}).setdefault(
                    model, {"spent_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "requests": 0})
                m["spent_usd"] = round(m["spent_usd"] + actual, 6)
                m["prompt_tokens"] += prompt_tokens
                m["completion_tokens"] += completion_tokens
                m["requests"] += 1
                data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                data["note"] = "estimate at Tinker list price, no cache discount; this machine only; the Tinker console is the bill"
                tmp = str(self.path) + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(data, f, indent=1)
                os.replace(tmp, self.path)


class Pool:
    """Several Tinker accounts, each with its own lifetime Budget, drained in the listed order,
    plus one per-run cap across all of them. A request goes to the first account whose budget
    fits its worst case; when none fits, it is refused."""

    def __init__(self, accounts: List[Tuple[str, Budget]], run_usd: float = 0.0):
        labels = [label for label, _ in accounts]
        if not accounts or len(set(labels)) != len(labels):
            raise ValueError(f"pool needs at least one account and unique labels, got {labels}")
        self.accounts = dict(accounts)
        self.order = labels
        self.run_usd = float(run_usd)
        self.lock = threading.Lock()
        self.pending = 0.0
        self.run_spent = 0.0

    def _worst(self, label: str, model: str, prompt_tokens: int, max_completion: int) -> float:
        return Budget.cost(Budget.price_for(self.accounts[label].prices, model), prompt_tokens, max_completion)

    def acquire(self, model: str, prompt_tokens: int, max_completion: int) -> Tuple[Optional[str], Optional[str]]:
        """(account label, None) with the worst case held on that account, or (None, refusal reason)."""
        worst = self._worst(self.order[0], model, prompt_tokens, max_completion)
        with self.lock:
            if self.run_usd > 0 and self.run_spent + self.pending + worst > self.run_usd + 1e-9:
                return None, (f"per-run Tinker budget: ${self.run_spent:.2f} spent + ${self.pending:.2f} in flight + "
                              f"${worst:.2f} worst case > ${self.run_usd:.2f}")
            reasons = []
            for label in self.order:
                reason = self.accounts[label].reserve(model, prompt_tokens, max_completion)
                if reason is None:
                    self.pending += worst
                    return label, None
                reasons.append(f"[{label}] {reason}")
            return None, "every Tinker account is at its budget: " + "; ".join(reasons)

    def release(self, label: str, model: str, prompt_tokens: int, max_completion: int):
        self.accounts[label].release(model, prompt_tokens, max_completion)
        with self.lock:
            self.pending = max(0.0, self.pending - self._worst(label, model, prompt_tokens, max_completion))

    def settle(self, label: str, model: str, prompt_tokens: int, max_completion: int, completion_tokens: int):
        account = self.accounts[label]
        account.settle(model, prompt_tokens, max_completion, completion_tokens)
        with self.lock:
            self.pending = max(0.0, self.pending - self._worst(label, model, prompt_tokens, max_completion))
            self.run_spent += Budget.cost(Budget.price_for(account.prices, model), prompt_tokens, completion_tokens)

    def summary(self) -> List[dict]:
        return [{"account": label, "spent_usd": round(self.accounts[label].spent_total(), 4),
                 "budget_usd": self.accounts[label].total_usd} for label in self.order]


def load_pool(path: str, run_usd: float, prices: Dict[str, Tuple[float, float]],
              ledger_dir: str = "~/.autoresearch") -> Tuple[Pool, Dict[str, str]]:
    """Pool from the "tinker" list of a pool file (see docs in scripts/c2_pilot.sh):
    [{"label": "nathan", "key_env": "TINKER_API_KEY", "budget_usd": 100}, ...]. The file names
    environment variables, never keys. Returns the pool and {label: key_env}."""
    entries = json.loads(Path(path).expanduser().read_text()).get("tinker") or []
    accounts, key_envs = [], {}
    for e in entries:
        label = str(e["label"])
        if not label.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"pool label {label!r} must be letters, digits, - or _")
        key_env = e.get("key_env", "TINKER_API_KEY")
        if not os.environ.get(key_env):
            raise ValueError(f"Tinker account {label!r}: environment variable {key_env} is not set")
        ledger = str(Path(ledger_dir).expanduser() / f"tinker_ledger_{label}.json")
        accounts.append((label, Budget(ledger, total_usd=float(e["budget_usd"]), run_usd=0, prices=prices)))
        key_envs[label] = key_env
    return Pool(accounts, run_usd=run_usd), key_envs


def to_cookbook(messages: List[dict], tools: Optional[List[dict]], renderer) -> List[dict]:
    """OpenAI chat messages (+ tools) -> tinker_cookbook Messages."""
    from tinker_cookbook.renderers.base import ToolCall
    out, system = [], ""
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        content = content or ""
        if m["role"] == "system" and not out:
            system = content
            continue
        msg = {"role": m["role"], "content": content}
        if m.get("tool_calls"):
            msg["tool_calls"] = [ToolCall(id=tc.get("id"), function=ToolCall.FunctionBody(
                name=tc["function"]["name"],
                arguments=tc["function"].get("arguments") if isinstance(tc["function"].get("arguments"), str)
                else json.dumps(tc["function"].get("arguments", {}))))
                for tc in m["tool_calls"]]
        if m["role"] == "tool":
            if m.get("tool_call_id"):
                msg["tool_call_id"] = m["tool_call_id"]
            if m.get("name"):
                msg["name"] = m["name"]
        out.append(msg)
    if tools:
        specs = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                  "parameters": t["function"].get("parameters", {"type": "object", "properties": {}})}
                 for t in tools if t.get("type", "function") == "function"]
        return list(renderer.create_conversation_prefix_with_tools(specs, system_prompt=system)) + out
    return ([{"role": "system", "content": system}] if system else []) + out


def from_cookbook(msg: dict) -> Tuple[str, str, List[dict]]:
    """(reasoning, content, OpenAI tool_calls) from a parsed cookbook Message."""
    content = msg.get("content", "")
    reasoning, text = [], []
    if isinstance(content, str):
        text.append(content)
    else:
        for p in content:
            if p.get("type") == "thinking":
                reasoning.append(p.get("thinking", ""))
            elif p.get("type") == "text":
                text.append(p.get("text", ""))
    calls = [{"id": tc.id or "call_" + uuid.uuid4().hex[:12], "type": "function",
              "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
             for tc in msg.get("tool_calls") or []]
    return "\n".join(r for r in reasoning if r).strip(), "".join(text).strip(), calls


class Usage:
    def __init__(self, cap: int, path: Optional[str]):
        self.cap, self.path, self.lock = cap, path, threading.Lock()
        self.by_model: Dict[str, Dict[str, int]] = {}

    @property
    def total(self) -> int:
        return sum(v["prompt"] + v["completion"] for v in self.by_model.values())

    def over(self) -> bool:
        return self.cap > 0 and self.total >= self.cap

    def add(self, model: str, prompt: int, completion: int):
        with self.lock:
            v = self.by_model.setdefault(model, {"prompt": 0, "completion": 0, "requests": 0})
            v["prompt"] += prompt
            v["completion"] += completion
            v["requests"] += 1
            if self.path:
                with open(self.path, "w") as f:
                    json.dump({"total_tokens": self.total, "cap": self.cap, "by_model": self.by_model}, f, indent=1)


def make_service(tinker, key_env: Optional[str]):
    """A Tinker ServiceClient for the key in key_env (None: the SDK's default, TINKER_API_KEY)."""
    if not key_env:
        return tinker.ServiceClient()
    key = os.environ[key_env]
    try:
        return tinker.ServiceClient(api_key=key)
    except TypeError:
        # SDKs without an api_key argument read TINKER_API_KEY at construction time.
        with _ENV_LOCK:
            old = os.environ.get("TINKER_API_KEY")
            os.environ["TINKER_API_KEY"] = key
            try:
                return tinker.ServiceClient()
            finally:
                if old is None:
                    os.environ.pop("TINKER_API_KEY", None)
                else:
                    os.environ["TINKER_API_KEY"] = old


_ENV_LOCK = threading.Lock()


class Backend:
    def __init__(self, service=None, key_envs: Optional[Dict[str, str]] = None):
        import tinker
        self.tinker = tinker
        self.service = service or tinker.ServiceClient()
        self.models: Dict[str, Tuple[Any, Any]] = {}
        self.lock = threading.Lock()
        self.key_envs = key_envs or {}                     # pool account label -> env var holding its key
        self.services: Dict[str, Any] = {}
        self.clients: Dict[Tuple[str, str], Any] = {}
        self.renderers: Dict[str, Any] = {}

    def get(self, model: str):
        with self.lock:
            if model not in self.models:
                self.models[model] = (self.service.create_sampling_client(base_model=model).result(),
                                      self._renderer(model))
            return self.models[model]

    def _renderer(self, model: str):
        if model not in getattr(self, "renderers", {}):
            from tinker_cookbook.model_info import get_recommended_renderer_name
            from tinker_cookbook.renderers import get_renderer
            from tinker_cookbook.tokenizer_utils import get_tokenizer
            self.renderers[model] = get_renderer(get_recommended_renderer_name(model), get_tokenizer(model), model_name=model)
        return self.renderers[model]

    def renderer_for(self, model: str):
        if model in self.models:
            return self.models[model][1]
        with self.lock:
            return self._renderer(model)

    def client_for(self, model: str, label: Optional[str]):
        """Sampling client on the given pool account (None: the default account)."""
        if label is None:
            return self.get(model)[0]
        with self.lock:
            if (label, model) not in self.clients:
                if label not in self.services:
                    self.services[label] = make_service(self.tinker, self.key_envs.get(label))
                self.clients[(label, model)] = self.services[label].create_sampling_client(base_model=model).result()
            return self.clients[(label, model)]

    def complete(self, req: dict, pool: Optional[Pool] = None, ceiling: int = 0) -> Tuple[dict, int, int]:
        model = req["model"]
        renderer = self.renderer_for(model)
        prompt = renderer.build_generation_prompt(to_cookbook(req["messages"], req.get("tools"), renderer))
        max_tokens = completion_limit(req, ceiling)
        params = self.tinker.types.SamplingParams(
            max_tokens=max_tokens,
            temperature=float(req["temperature"]) if req.get("temperature") is not None else 0.7,
            top_p=float(req.get("top_p") or 1.0), stop=renderer.get_stop_sequences())
        n_prompt = prompt.length if hasattr(prompt, "length") else len(prompt.to_ints())
        label = None
        if pool is not None:
            label, reason = pool.acquire(model, n_prompt, max_tokens)
            if reason:
                raise BudgetExceeded(reason)
        try:
            client = self.client_for(model, label)
            seq = client.sample(prompt=prompt, num_samples=1, sampling_params=params).result().sequences[0]
        except BaseException:
            if pool is not None:
                pool.release(label, model, n_prompt, max_tokens)
            raise
        tokens = list(seq.tokens)
        if pool is not None:   # billed once sampled, so record before parsing can fail
            pool.settle(label, model, n_prompt, max_tokens, len(tokens))
        msg, term = renderer.parse_response(tokens)
        reasoning, content, calls = from_cookbook(msg)
        truncated = "length" in str(getattr(seq, "stop_reason", "")).lower() or not getattr(term, "is_clean", True)
        if truncated and not calls and not reasoning:
            # Cut off before </think>: the renderer returns the unfinished thought as content. It is
            # reasoning, and there is no answer; finish "length" lets the client report that.
            reasoning, content = content, ""
        finish = "tool_calls" if calls else ("length" if truncated else "stop")
        out = {"role": "assistant", "content": content or None}
        if reasoning:
            out["reasoning_content"] = reasoning
        if calls:
            out["tool_calls"] = calls
        body = {"id": "chatcmpl-" + uuid.uuid4().hex[:16], "object": "chat.completion", "created": int(time.time()),
                "model": model, "choices": [{"index": 0, "message": out, "finish_reason": finish}],
                "usage": {"prompt_tokens": n_prompt, "completion_tokens": len(tokens),
                          "total_tokens": n_prompt + len(tokens)}}
        return body, n_prompt, len(tokens)


def make_handler(backend, usage: Usage, models: List[str], budget: Optional[Pool] = None, ceiling: int = 0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                return self._send(200, {"object": "list", "data": [{"id": m, "object": "model"} for m in models]})
            self._send(404, {"error": {"message": "not found"}})

        def do_POST(self):
            if not self.path.rstrip("/").endswith("/chat/completions"):
                return self._send(404, {"error": {"message": "only /v1/chat/completions"}})
            if usage.over():
                return self._send(429, {"error": {"message": f"token cap reached ({usage.total}/{usage.cap})",
                                                  "type": "insufficient_quota"}})
            try:
                req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                if models and req.get("model") not in models:
                    return self._send(400, {"error": {"message": f"model {req.get('model')!r} not served: {models}"}})
                body, p, c = backend.complete(req, budget, ceiling)
                usage.add(req["model"], p, c)
                self._send(200, body)
            except BudgetExceeded as e:
                print(f"tinker proxy refused a request: {e}", file=sys.stderr, flush=True)
                self._send(429, {"error": {"message": str(e), "type": "insufficient_quota"}})
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": {"message": f"{type(e).__name__}: {str(e)[:500]}"}})
    return Handler


def parse_prices(specs: List[str]) -> Dict[str, Tuple[float, float]]:
    prices = dict(TINKER_PRICES)
    for spec in specs:
        model, _, nums = spec.partition("=")
        prefill, sample = (float(x) for x in nums.split(","))
        prices[model] = (prefill, sample)
    return prices


def list_models(key_envs: Dict[str, Optional[str]]) -> int:
    """Print the base models each account can sample. Free: no tokens are sampled."""
    import tinker
    for label, key_env in key_envs.items():
        try:
            # RestClient, not ServiceClient.get_server_capabilities (deprecated in tinker 0.39)
            caps = tinker.RestClient(api_key=os.environ[key_env or "TINKER_API_KEY"]).get_server_capabilities()
            caps = caps.result() if hasattr(caps, "result") else caps
            names = sorted(getattr(m, "model_name", str(m)) for m in caps.supported_models)
            print(f"[{label}] {len(names)} models: " + ", ".join(names))
        except Exception as e:  # noqa: BLE001 - report every account, then fail
            print(f"[{label}] could not list models: {type(e).__name__}: {e}")
            return 1
    return 0


def build_pool(a, prices) -> Tuple[Pool, Dict[str, str]]:
    if a.pool:
        return load_pool(a.pool, a.run_budget_usd, prices, a.ledger_dir)
    if a.budget_usd is None:
        raise SystemExit("refusing to start without a spend limit: pass --pool FILE or --budget-usd USD")
    ledger = str(Path(a.ledger_dir).expanduser() / "tinker_ledger_default.json")
    return Pool([("default", Budget(ledger, a.budget_usd, 0, prices))], run_usd=a.run_budget_usd), {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--model", action="append", default=[], help="allowed Tinker base models (default: any)")
    ap.add_argument("--max-total-tokens", type=int, default=8_000_000, help="hard cap on tokens per run; 0 = none")
    ap.add_argument("--usage-file", default="tinker_usage.json")
    ap.add_argument("--pool", help="pool file: several Tinker accounts, each with its own lifetime budget")
    ap.add_argument("--budget-usd", type=float, help="single account (TINKER_API_KEY): lifetime budget in USD")
    ap.add_argument("--run-budget-usd", type=float, default=0.0, help="cap for this proxy run, all accounts; 0 = none")
    ap.add_argument("--ledger-dir", default="~/.autoresearch", help="where the per-account spend ledgers live")
    ap.add_argument("--max-completion-tokens", type=int, default=16_384, help="clamp on each request's max_tokens; 0 = none")
    ap.add_argument("--price", action="append", default=[], help="MODEL=PREFILL,SAMPLE in USD per 1M tokens")
    ap.add_argument("--list-models", action="store_true", help="print what each account can sample, then exit (free)")
    a = ap.parse_args(argv)
    prices = parse_prices(a.price)
    if a.list_models:
        key_envs = load_pool(a.pool, 0, prices, a.ledger_dir)[1] if a.pool else {"default": None}
        raise SystemExit(list_models(key_envs))
    for m in a.model:
        Budget.price_for(prices, m)            # fail before serving if a model has no price
    pool, key_envs = build_pool(a, prices)
    usage = Usage(a.max_total_tokens, a.usage_file)
    handler = make_handler(Backend(key_envs=key_envs), usage, a.model, pool, a.max_completion_tokens)
    server = ThreadingHTTPServer(("127.0.0.1", a.port), handler)
    print(f"tinker proxy on http://127.0.0.1:{a.port}/v1; run cap ${a.run_budget_usd:.2f}; accounts: "
          + json.dumps(pool.summary()), file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    finally:
        print(json.dumps({"total_tokens": usage.total, "by_model": usage.by_model, "run_spent_usd": round(pool.run_spent, 4),
                          "accounts": pool.summary()}), file=sys.stderr)


if __name__ == "__main__":
    main()
