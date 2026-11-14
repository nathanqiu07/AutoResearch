"""LLM backends.

`AnthropicLLM` calls the Messages API over HTTPS using only the standard
library (key read from ANTHROPIC_API_KEY). `OfflineLLM` is a deterministic
stand-in so every component can run and be tested without network access.
All calls are metered by a shared `Budget` so compute is a first-class metric.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Budget:
    max_calls: int = 10_000
    max_seconds: float = 3600.0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    started: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def charge(self, inp: int, out: int, cost: float = 0.0) -> None:
        with self._lock:  # backends may be called from worker threads
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.cost_usd += cost

    @property
    def elapsed(self) -> float:
        return time.time() - self.started

    def exhausted(self) -> bool:
        return self.calls >= self.max_calls or self.elapsed >= self.max_seconds

    def summary(self) -> dict:
        return {"calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cost_usd": round(self.cost_usd, 4), "seconds": round(self.elapsed, 2)}


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class LLM:
    name = "base"

    def __init__(self, budget: Optional[Budget] = None):
        self.budget = budget or Budget()

    def complete(self, prompt: str, system: str = "", max_tokens: int = 1024,
                 temperature: float = 0.7) -> str:
        raise NotImplementedError


class AnthropicLLM(LLM):
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, model: str = "claude-sonnet-5-5", budget: Optional[Budget] = None):
        super().__init__(budget)
        self.model = model
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        body = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        req = urllib.request.Request(
            self.URL, data=json.dumps(body).encode(),
            headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.loads(r.read())
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        usage = data.get("usage", {})
        self.budget.charge(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return "".join(b.get("text", "") for b in data.get("content", []))


class ClaudeCLILLM(LLM):
    """Uses the locally signed-in `claude` CLI (`claude -p`), so real models can
    be used with the account's existing login and no API key in this process.

    Each call is isolated so it behaves like a plain model call: all tools are
    disabled, MCP servers and settings files (including CLAUDE.md memory) are
    skipped, the CLI's own system prompt is replaced, and it runs from an empty
    temporary directory."""
    name = "claude-cli"
    DEFAULT_SYSTEM = "You are a helpful assistant."

    def __init__(self, model: str = "claude-sonnet-5-5", budget: Optional[Budget] = None,
                 binary: str = "claude", timeout: float = 300.0):
        super().__init__(budget)
        self.model, self.binary, self.timeout = model, binary, timeout

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        import tempfile
        cmd = [self.binary, "-p", "--model", self.model, "--output-format", "json",
               "--tools", "", "--strict-mcp-config", "--setting-sources", "",
               "--system-prompt", system or self.DEFAULT_SYSTEM]
        with tempfile.TemporaryDirectory(prefix="ar_cli_") as cwd:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                                  timeout=self.timeout, cwd=cwd)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"claude CLI failed: {(proc.stderr or proc.stdout).strip()[:300]}")
        if proc.returncode != 0 or data.get("is_error"):
            raise RuntimeError(f"claude CLI error: {str(data.get('result'))[:300]}")
        u = data.get("usage", {})
        inp = (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
               + u.get("cache_read_input_tokens", 0)) or _approx_tokens(prompt)
        self.budget.charge(inp, u.get("output_tokens", 0), float(data.get("total_cost_usd", 0.0)))
        return data.get("result", "")


class OfflineLLM(LLM):
    """Deterministic pseudo-LLM. Returns a hash-seeded choice among any
    options listed in the prompt as lines starting with '- ', otherwise
    echoes a compact summary. Components that need real behaviour offline
    implement their own heuristic path and use this only for plumbing."""
    name = "offline"

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        h = int(hashlib.sha256((system + prompt).encode()).hexdigest(), 16)
        opts = [l[2:].strip() for l in prompt.splitlines() if l.startswith("- ")]
        out = opts[h % len(opts)] if opts else prompt.strip().splitlines()[-1][:200] if prompt.strip() else ""
        self.budget.charge(_approx_tokens(system + prompt), _approx_tokens(out))
        return out


def get_llm(kind: str = "auto", model: str = "claude-sonnet-5-5",
            budget: Optional[Budget] = None) -> LLM:
    if kind == "offline" or (kind == "auto" and not os.environ.get("ANTHROPIC_API_KEY")):
        return OfflineLLM(budget)
    if kind == "claude-cli":
        return ClaudeCLILLM(model=model, budget=budget)
    return AnthropicLLM(model=model, budget=budget)


def extract_json(text: str):
    """Pull the first JSON object/array out of a model response, trying the
    bracket that opens first (so a list of objects is returned as a list)."""
    starts = sorted((text.find(o), o, c) for o, c in (("{", "}"), ("[", "]")) if text.find(o) != -1)
    for s, _, close_c in starts:
        e = text.rfind(close_c)
        if e > s:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                continue
    return None
