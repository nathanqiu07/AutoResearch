"""Optional WS A development backends; shared research LLM code is untouched."""
import json
import subprocess
import tempfile

from ..llm import LLM


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
