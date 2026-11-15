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
from typing import Dict, Optional


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Budget:
    max_calls: int = 10_000
    max_seconds: float = 3600.0
    # Per Budget (one run, or one swarm cell), not a lifetime total. Only backends
    # that report cost count toward it; today that is ClaudeCLILLM alone.
    max_cost_usd: float = 200.0
    calls: int = 0
    input_tokens: int = 0          # all input tokens, cached ones included
    output_tokens: int = 0
    cost_usd: float = 0.0
    cache_write_tokens: int = 0    # prompt caching: tokens written to the cache
    cache_read_tokens: int = 0     # prompt caching: tokens served from the cache
    saved_usd: float = 0.0         # list-price cost avoided by caching and the Batch API (E5 reports it)
    gpu_seconds: float = 0.0       # busy time of self-hosted targets billed per GPU-second (OpenAICompatLLM)
    started: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def charge(self, inp: int, out: int, cost: float = 0.0, cache_write: int = 0, cache_read: int = 0,
               saved: float = 0.0) -> None:
        with self._lock:  # backends may be called from worker threads
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.cost_usd += cost
            self.cache_write_tokens += cache_write
            self.cache_read_tokens += cache_read
            self.saved_usd += saved

    @property
    def elapsed(self) -> float:
        return time.time() - self.started

    def exhausted(self) -> bool:
        return (self.calls >= self.max_calls or self.elapsed >= self.max_seconds
                or self.cost_usd >= self.max_cost_usd)

    def add_gpu(self, seconds: float, usd: float = 0.0) -> None:
        """GPU time spent serving a self-hosted model: adds spend without counting a call."""
        with self._lock:
            self.gpu_seconds += seconds
            self.cost_usd += usd

    def check_spend(self) -> None:
        """Called before every paid request, so the cap holds even in loops
        that only watch the call count."""
        if self.cost_usd >= self.max_cost_usd:
            raise BudgetExceeded(f"spend cap reached: ${self.cost_usd:.2f} of ${self.max_cost_usd:.2f}")

    def summary(self) -> dict:
        out = {"calls": self.calls, "input_tokens": self.input_tokens,
               "output_tokens": self.output_tokens,
               "cost_usd": round(self.cost_usd, 4), "seconds": round(self.elapsed, 2)}
        if self.gpu_seconds:
            out["gpu_seconds"] = round(self.gpu_seconds, 2)
        if self.cache_write_tokens or self.cache_read_tokens or self.saved_usd:
            out.update(cache_write_tokens=self.cache_write_tokens, cache_read_tokens=self.cache_read_tokens,
                       saved_usd=round(self.saved_usd, 4))
        return out


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class LLM:
    name = "base"

    def __init__(self, budget: Optional[Budget] = None):
        self.budget = budget or Budget()

    def complete(self, prompt: str, system: str = "", max_tokens: int = 1024,
                 temperature: float = 0.7) -> str:
        raise NotImplementedError

    def complete_with_reasoning(self, prompt: str, system: str = "", max_tokens: int = 1024,
                                temperature: float = 0.7):
        """(raw reasoning, final text). Backends that expose raw chain of
        thought override this; the rest return empty reasoning, so the
        verbalized-awareness metric falls back to reading the reply only."""
        return "", self.complete(prompt, system=system, max_tokens=max_tokens, temperature=temperature)

    @property
    def label(self) -> str:
        return f"{self.name}:{getattr(self, 'model', '')}"


def parse_openai_chat(data: dict):
    """(reasoning, text, input_tokens, output_tokens) from an OpenAI-style
    chat completion. vLLM reasoning parsers put raw chain of thought in
    `reasoning_content` (newer servers: `reasoning`)."""
    msg = ((data.get("choices") or [{}])[0].get("message") or {})
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    usage = data.get("usage") or {}
    return reasoning, msg.get("content") or "", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


class GpuMeter:
    """Busy time of one served model, shared by every client of the same endpoint.
    A busy period opens when the first in-flight request starts; each completion
    charges the time since the last charge, so overlapping requests on the one
    GPU are counted once and long busy stretches are charged as they go (the
    spend cap can act mid-run). A LOWER BOUND on the bill: idle time before
    scale-to-zero and cold starts are not seen."""

    _meters: Dict[str, "GpuMeter"] = {}
    _registry_lock = threading.Lock()

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._lock = threading.Lock()
        self.active = 0
        self.mark = 0.0

    @classmethod
    def for_endpoint(cls, base_url: str) -> "GpuMeter":
        with cls._registry_lock:
            return cls._meters.setdefault(base_url, cls())

    def start(self) -> None:
        with self._lock:
            if self.active == 0:
                self.mark = self.clock()
            self.active += 1

    def end(self) -> float:
        """Seconds to charge for the busy time up to now."""
        with self._lock:
            now = self.clock()
            secs = max(0.0, now - self.mark)
            self.mark = now
            self.active = max(0, self.active - 1)
            return secs


class OpenAICompatLLM(LLM):
    """Any OpenAI-compatible chat endpoint, e.g. an open-weight reasoning model
    served by vLLM on Modal. Exposes raw reasoning, which the co-primary
    chain-of-thought awareness metric (PLAN A1) needs. Base URL from
    OPENAI_COMPAT_BASE_URL (e.g. https://<app>.modal.run/v1); optional key
    from OPENAI_COMPAT_API_KEY.

    A thinking model also reasons on plain `complete` calls (probe questions,
    max_tokens=300), where there is no headroom, so it can spend the whole cap
    thinking; that raises (see `_call`) rather than returning an empty answer.
    OPENAI_COMPAT_PLAIN_THINKING chooses what plain calls do instead:
      "off"       ask the server not to think (chat_template_kwargs.enable_thinking
                  = false, which Qwen3's chat template honours under vLLM);
      "headroom"  keep thinking and add THINKING_HEADROOM to max_tokens;
      unset       send the call as is.

    GPU cost: a self-hosted endpoint is billed per GPU-second, not per token.
    With `usd_per_hour` (or OPENAI_COMPAT_USD_PER_HOUR, e.g. 3.95 for one Modal
    H100 at list price) the endpoint's busy time is charged to the Budget, so
    the spend cap and E5's $ figures include the target (GpuMeter: a lower
    bound). Without a rate the busy seconds are still recorded, at $0."""
    name = "openai-compat"
    PLAIN_THINKING_MODES = ("", "off", "headroom")
    THINKING_HEADROOM = 8000   # reasoning tokens count against max_tokens (complete_with_reasoning only)

    def __init__(self, model: str, budget: Optional[Budget] = None, base_url: Optional[str] = None,
                 usd_per_hour: Optional[float] = None):
        super().__init__(budget)
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_COMPAT_BASE_URL") or "").rstrip("/")
        if not self.base_url:
            raise RuntimeError("OPENAI_COMPAT_BASE_URL is not set")
        rate = usd_per_hour if usd_per_hour is not None else os.environ.get("OPENAI_COMPAT_USD_PER_HOUR")
        try:
            self.usd_per_hour = float(rate) if rate not in (None, "") else 0.0
        except ValueError:
            raise RuntimeError(f"OPENAI_COMPAT_USD_PER_HOUR must be a number, got {rate!r}")
        if self.usd_per_hour < 0:
            raise RuntimeError("OPENAI_COMPAT_USD_PER_HOUR must be >= 0")
        self.meter = GpuMeter.for_endpoint(self.base_url)
        self.key = os.environ.get("OPENAI_COMPAT_API_KEY", "")
        self.plain_thinking = os.environ.get("OPENAI_COMPAT_PLAIN_THINKING", "")
        if self.plain_thinking not in self.PLAIN_THINKING_MODES:
            raise RuntimeError(f"OPENAI_COMPAT_PLAIN_THINKING must be one of 'off', 'headroom' or unset, "
                               f"got {self.plain_thinking!r}")

    def _call(self, prompt, system, max_tokens, temperature, extra=None):
        self.budget.check_spend()
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        body.update(extra or {})
        headers = {"content-type": "application/json"}
        if self.key:
            headers["authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(body).encode(), headers=headers)
        for attempt in range(4):
            self.meter.start()
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    data = json.loads(r.read())
                break
            except Exception:
                if attempt == 3:
                    raise
            finally:   # busy time of this attempt only; the backoff sleep below is not GPU time
                secs = self.meter.end()
                self.budget.add_gpu(secs, secs * self.usd_per_hour / 3600.0)
            time.sleep(2 ** attempt)
        reasoning, text, inp, out = parse_openai_chat(data)
        self.budget.charge(inp or _approx_tokens(system + prompt), out or _approx_tokens(reasoning + text))
        finish = (data.get("choices") or [{}])[0].get("finish_reason")
        if finish == "length" and not text.strip():   # the cap was spent on reasoning: no reply to score
            raise RuntimeError(f"{self.model} stopped at max_tokens={max_tokens} with an empty reply "
                               f"(finish_reason='length'; reasoning chars={len(reasoning)})")
        return reasoning, text

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        if self.plain_thinking == "off":
            extra = {"chat_template_kwargs": {"enable_thinking": False}}
            return self._call(prompt, system, max_tokens, temperature, extra)[1]
        if self.plain_thinking == "headroom":
            max_tokens += self.THINKING_HEADROOM
        return self._call(prompt, system, max_tokens, temperature)[1]

    def complete_with_reasoning(self, prompt, system="", max_tokens=1024, temperature=0.7):
        return self._call(prompt, system, max_tokens + self.THINKING_HEADROOM, temperature)


# USD per million tokens (input, output), list prices, so API backends count toward
# Budget.max_cost_usd. Estimates for the cap, not billing reconciliation.
PRICES_PER_MTOK = {
    "claude-sonnet-4-6": (3.0, 15.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0), "claude-opus-4-6": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0), "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-4-5": (3.0, 15.0),
    # OpenAI: list prices taken from third-party aggregators on 2026-11-14, not verified
    # against OpenAI's pricing page.
    "gpt-5": (1.25, 10.0), "gpt-5.1": (1.25, 10.0),
    "gpt-6-luna": (0.10, 0.50),   # same caveat; aggregators also list batch 0.05/0.25 and cached input 0.01
}


# Prompt caching and the Message Batches API (PLAN 8, cheaper measurement): a 5-minute
# cache write costs 1.25x the input price, a cache read 0.1x (0.05x on the models
# listed), and a batch request half of everything.
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = {"claude-opus-5-5": 0.05, "claude-sonnet-5-5": 0.05}
CACHE_READ_DEFAULT = 0.1
BATCH_MULT = 0.5


def anthropic_usage_cost(model: str, usage: dict, batch: bool = False, prices=None):
    """($ cost, $ saved against no caching and no batch discount) of one Messages
    API `usage` object at list price. Its input_tokens are the uncached ones.
    A model with no known price costs 0.0, as in `list_price_usd`."""
    pin, pout = (x / 1e6 for x in (prices or PRICES_PER_MTOK).get(model, (0.0, 0.0)))
    fresh, out = usage.get("input_tokens", 0) or 0, usage.get("output_tokens", 0) or 0
    write = usage.get("cache_creation_input_tokens", 0) or 0
    read = usage.get("cache_read_input_tokens", 0) or 0
    mult = BATCH_MULT if batch else 1.0
    cost = mult * (fresh * pin + write * pin * CACHE_WRITE_MULT
                   + read * pin * CACHE_READ_MULT.get(model, CACHE_READ_DEFAULT) + out * pout)
    return cost, (fresh + write + read) * pin + out * pout - cost


def list_price_usd(model: str, input_tokens: int, output_tokens: int, prices=None) -> float:
    """Cost at list price, or 0.0 for a model with no known price (the caller decides
    whether an unknown price is acceptable; OpenAIResponsesLLM refuses to start without one)."""
    inp, out = (prices or PRICES_PER_MTOK).get(model, (0.0, 0.0))
    return (input_tokens * inp + output_tokens * out) / 1_000_000


MANUAL_THINKING_MARKERS = ("-4-5", "-4-1", "-4-0", "sonnet-4-2", "opus-4-2", "-3-")


def anthropic_needs_manual_thinking(model: str) -> bool:
    """True for Claude models that take manual extended thinking
    ({"type": "enabled", "budget_tokens": N}) instead of adaptive thinking.

    Source: Anthropic's extended-thinking docs, as we read them: adaptive thinking with
    `display` exists only on Claude 4.6 and later; Sonnet 4.5, Haiku 4.5 and older need a
    token budget (N >= 1024, N < max_tokens). The rule is a substring match on the model id
    (MANUAL_THINKING_MARKERS above), so correct that tuple if a model is misclassified."""
    return any(marker in model for marker in MANUAL_THINKING_MARKERS)


class AnthropicLLM(LLM):
    """Messages API over stdlib HTTP. A model id ending in "+thinking" (e.g.
    "claude-sonnet-4-6+thinking") turns on adaptive thinking for
    `complete_with_reasoning`, which is what the target's reply goes through.
    The API returns a SUMMARY of the model's thinking, never the raw chain of
    thought, so awareness read from it (A1) is a lower bound: the summary can
    drop a remark the raw reasoning made. Plain `complete` stays thinking-off
    (cheaper; used for probe questions and judging)."""
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"
    THINKING_SUFFIX = "+thinking"
    THINKING_HEADROOM = 8000   # thinking tokens count against max_tokens
    # Prompt caching: a system prompt of at least this many (approximate) tokens goes
    # out as a cached block. Shorter prefixes cannot be cached (the minimum is 512-4096
    # tokens by model), so they stay a plain string and pay no write premium.
    CACHE_MIN_TOKENS = 512

    def __init__(self, model: str = "claude-sonnet-5-5", budget: Optional[Budget] = None, cache: bool = True):
        super().__init__(budget)
        self.cache = cache
        self.thinking = model.endswith(self.THINKING_SUFFIX)
        self.model = model[:-len(self.THINKING_SUFFIX)] if self.thinking else model
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}{self.THINKING_SUFFIX if self.thinking else ''}"

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(
            self.URL, data=json.dumps(body).encode(),
            headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=300 if "thinking" in body else 120) as r:
                    data = json.loads(r.read())
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        self.charge_usage(data.get("usage", {}))
        return data

    def charge_usage(self, usage: dict, batch: bool = False) -> None:
        """Charge one response's usage to the Budget, cache and batch pricing included."""
        cost, saved = anthropic_usage_cost(self.model, usage, batch=batch)
        write = usage.get("cache_creation_input_tokens", 0) or 0
        read = usage.get("cache_read_input_tokens", 0) or 0
        self.budget.charge((usage.get("input_tokens", 0) or 0) + write + read, usage.get("output_tokens", 0) or 0,
                           cost, cache_write=write, cache_read=read, saved=saved)

    def system_field(self, system: str):
        """The request's `system`: a cached text block when it is long enough to cache."""
        if self.cache and _approx_tokens(system) >= self.CACHE_MIN_TOKENS:
            return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        return system

    def request_body(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.7) -> dict:
        """The Messages API body `complete` sends (the batch runner sends the same)."""
        body = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = self.system_field(system)
        return body

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.budget.check_spend()
        body = self.request_body(prompt, system, max_tokens, temperature)
        return "".join(b.get("text", "") for b in self._post(body).get("content", []))

    def complete_with_reasoning(self, prompt, system="", max_tokens=1024, temperature=0.7):
        if not self.thinking:
            return "", self.complete(prompt, system=system, max_tokens=max_tokens, temperature=temperature)
        self.budget.check_spend()
        # no temperature: sampling parameters are restricted while thinking is on
        if anthropic_needs_manual_thinking(self.model):   # budget_tokens < max_tokens always holds: headroom is added
            thinking = {"type": "enabled", "budget_tokens": self.THINKING_HEADROOM}
        else:
            thinking = {"type": "adaptive", "display": "summarized"}
        body = {"model": self.model, "max_tokens": max_tokens + self.THINKING_HEADROOM,
                "thinking": thinking,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = self.system_field(system)
        data = self._post(body)
        reasoning, text = parse_anthropic_thinking(data)
        if data.get("stop_reason") == "max_tokens" and not text.strip():   # thinking used the whole cap
            raise RuntimeError(f"{self.model} stopped at max_tokens={body['max_tokens']} with an empty reply "
                               f"(stop_reason='max_tokens'; thinking chars={len(reasoning)})")
        return reasoning, text


def parse_anthropic_thinking(data: dict):
    """(summarized thinking, final text) from a Messages API response."""
    blocks = data.get("content", [])
    reasoning = "\n".join(b.get("thinking", "") for b in blocks if b.get("type") == "thinking" and b.get("thinking"))
    return reasoning, "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def parse_openai_responses(data: dict):
    """(reasoning summary, final text, input_tokens, output_tokens) from an OpenAI
    Responses API result. Raises on anything that is not a completed text answer,
    so a refusal or a truncated reply becomes an error sample, not an empty reply."""
    if data.get("status") != "completed" or data.get("error"):
        raise RuntimeError(f"OpenAI response not completed: status={data.get('status')!r} "
                           f"error={str(data.get('error'))[:200]} incomplete={data.get('incomplete_details')}")
    reasoning, texts = [], []
    for item in data.get("output") or []:
        if item.get("type") == "reasoning":
            reasoning += [part.get("text", "") for part in item.get("summary") or [] if part.get("text")]
        elif item.get("type") == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    texts.append(part.get("text", ""))
                elif part.get("type") == "refusal":
                    raise RuntimeError(f"OpenAI model refused: {str(part.get('refusal'))[:200]}")
    usage = data.get("usage") or {}
    return "\n".join(reasoning), "".join(texts), usage.get("input_tokens", 0), usage.get("output_tokens", 0)


def parse_openai_price_env(value: str):
    """(bare price or None, {model: price}) from OPENAI_PRICE_PER_MTOK. Either
    "<input>,<output>" (the instance's own model) or
    "<model>=<input>,<output>;<model2>=<input>,<output>" (USD per million tokens)."""
    def bad():
        return RuntimeError("OPENAI_PRICE_PER_MTOK must be '<input>,<output>' or "
                            f"'<model>=<input>,<output>;<model2>=<input>,<output>' in USD per million tokens, got {value!r}")

    def price(text: str):
        try:
            inp, out = (float(x) for x in text.split(","))
        except ValueError:
            raise bad() from None
        if not (0 <= inp < float("inf") and 0 <= out < float("inf")):   # rejects negative, nan, inf
            raise bad()
        return inp, out

    if "=" not in value and ";" not in value:
        return price(value), {}
    per_model = {}
    for entry in value.split(";"):
        model, sep, text = entry.partition("=")
        if not sep or not model.strip():
            raise bad()
        per_model[model.strip()] = price(text)
    return None, per_model


class OpenAIResponsesLLM(LLM):
    """OpenAI models through the Responses API over stdlib HTTP, for use as a
    target (the model inside the environment) or a held-out judge.

    A model id ending in "+thinking" asks for reasoning with a summary on
    `complete_with_reasoning` (the target's reply). Like the Anthropic backend,
    what comes back is a SUMMARY of the reasoning, not the raw chain of thought,
    so awareness read from it (A1) is a lower bound. Plain `complete` sends no
    reasoning options.

    Spend safety: the key comes from OPENAI_API_KEY. The backend refuses to
    start unless it knows the model's price, from PRICES_PER_MTOK or from
    OPENAI_PRICE_PER_MTOK="<input>,<output>" (USD per million tokens), so every
    call counts toward Budget.max_cost_usd. No temperature is sent: reasoning
    models reject sampling parameters."""
    name = "openai"
    URL = "https://api.openai.com/v1/responses"
    THINKING_SUFFIX = "+thinking"
    THINKING_HEADROOM = 8000   # reasoning tokens count against max_output_tokens

    def __init__(self, model: str, budget: Optional[Budget] = None, reasoning_effort: str = "medium"):
        super().__init__(budget)
        self.thinking = model.endswith(self.THINKING_SUFFIX)
        self.model = model[:-len(self.THINKING_SUFFIX)] if self.thinking else model
        self.reasoning_effort = reasoning_effort
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.prices = dict(PRICES_PER_MTOK)
        env_price = os.environ.get("OPENAI_PRICE_PER_MTOK", "")
        if env_price:
            bare, per_model = parse_openai_price_env(env_price)
            self.prices.update(per_model)
            if bare:
                self.prices[self.model] = bare
        if self.model not in self.prices:
            raise RuntimeError(f"no price known for OpenAI model {self.model!r}: set OPENAI_PRICE_PER_MTOK="
                               "'<input>,<output>' so the spend cap can count its calls")

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}{self.THINKING_SUFFIX if self.thinking else ''}"

    def _post(self, body: dict):
        self.budget.check_spend()
        req = urllib.request.Request(
            self.URL, data=json.dumps(body).encode(),
            headers={"authorization": f"Bearer {self.key}", "content-type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    data = json.loads(r.read())
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        usage = data.get("usage") or {}
        inp, out = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        self.budget.charge(inp, out, list_price_usd(self.model, inp, out, self.prices))   # charged even if parsing fails
        return parse_openai_responses(data)[:2]

    def _body(self, prompt, system, max_tokens):
        body = {"model": self.model, "input": prompt, "max_output_tokens": max_tokens, "store": False}
        if system:
            body["instructions"] = system
        return body

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        return self._post(self._body(prompt, system, max_tokens))[1]

    def complete_with_reasoning(self, prompt, system="", max_tokens=1024, temperature=0.7):
        body = self._body(prompt, system, max_tokens + (self.THINKING_HEADROOM if self.thinking else 0))
        if self.thinking:
            body["reasoning"] = {"effort": self.reasoning_effort, "summary": "auto"}
        return self._post(body)


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
        self.budget.check_spend()
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


BACKENDS = ("offline", "anthropic", "openai", "openai-compat", "claude-cli", "anthropic-batch")


def split_spec(model: str):
    """("backend", "model") for a "backend:model" spec such as
    "anthropic:claude-sonnet-4-6+thinking" or "openai:<model>+thinking";
    (None, model) for a bare model name."""
    head, sep, rest = model.partition(":")
    return (head, rest) if sep and head in BACKENDS and rest else (None, model)


def get_llm(kind: str = "auto", model: str = "claude-sonnet-5-5",
            budget: Optional[Budget] = None) -> LLM:
    """`model` may be a "backend:model" spec, which overrides `kind` for this one
    role, so one run can mix vendors (e.g. an OpenAI target with a Claude judge)."""
    backend, model = split_spec(model)
    kind = backend or kind
    if kind == "openai":
        return OpenAIResponsesLLM(model=model, budget=budget)
    if kind == "offline" or (kind == "auto" and not os.environ.get("ANTHROPIC_API_KEY")):
        return OfflineLLM(budget)
    if kind == "claude-cli":
        return ClaudeCLILLM(model=model, budget=budget)
    if kind == "openai-compat":
        return OpenAICompatLLM(model=model, budget=budget)
    if kind == "anthropic-batch":   # Message Batches API: half price, asynchronous (autoresearch/batch.py)
        from .batch import AnthropicBatchLLM
        return AnthropicBatchLLM(model=model, budget=budget)
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
