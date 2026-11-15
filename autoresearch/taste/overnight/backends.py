"""Declared Responses API settings and a process-shared conservative USD ledger.

Rates verified by the coordinator against official model/pricing documentation
2026-11-15. All input is charged at uncached rates; this is a conservative list
price estimate, not a provider invoice. Output usage includes reasoning tokens.
Unknown outcomes retain their entire reservation, add known usage, and hold new
requests. No code path releases an uncertain reservation or retries a request.
"""
import json
import math
import os
import sqlite3
import threading
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path

from ...llm import LLM
from .contracts import canonical_json, digest


NANOS_PER_USD = 1_000_000_000
RATES = {"gpt-6-luna": ("0.10", "0.50"), "gpt-6-sol": ("2", "10"), "gpt-6-astra": ("10", "50")}
PRICING_VERSION = "openai-standard-short-context-2026-11-15"
PRICING_SOURCES = ["https://developers.openai.com/api/docs/pricing",
                   "https://developers.openai.com/api/docs/models/gpt-6-luna",
                   "https://developers.openai.com/api/docs/models/gpt-6-sol",
                   "https://developers.openai.com/api/docs/models/gpt-6-astra"]


def _money(value, rounding=ROUND_CEILING):
    if isinstance(value, bool):
        raise ValueError("dollar value must be finite nonnegative")
    try:
        amount = Decimal(str(value))
    except Exception:
        raise ValueError("dollar value must be finite nonnegative") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError("dollar value must be finite nonnegative")
    return int((amount * NANOS_PER_USD).to_integral_value(rounding=rounding))


def _time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("deadline must include timezone")
    return result.astimezone(timezone.utc)


class DollarLedger:
    """Atomic aggregate reservations across processes using one coordinator path.

    Reopening cannot change the limit, deadline, concurrency or pricing version.
    Pending reservations after a crash remain charged and count as in-flight.
    No stale lease or wall-clock expiry frees them automatically.
    """
    def __init__(self, path, *, max_usd, deadline, max_inflight=2):
        self.path = Path(path).resolve()
        self.deadline = _time(deadline)
        limit = _money(max_usd, ROUND_FLOOR)
        if limit <= 0 or not isinstance(max_inflight, int) or isinstance(max_inflight, bool) or max_inflight < 1:
            raise ValueError("positive dollar and concurrency limits required")
        self.configuration = {"limit_nanos": limit, "deadline": self.deadline.isoformat(),
                              "max_inflight": max_inflight, "pricing_version": PRICING_VERSION}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, reserved INTEGER NOT NULL, actual INTEGER NOT NULL, status TEXT NOT NULL, metadata TEXT NOT NULL)")
            existing = conn.execute("SELECT body FROM policy WHERE id=1").fetchone()
            if existing and existing[0] != canonical_json(self.configuration):
                raise ValueError("shared ledger configuration differs; cannot reset allocation")
            conn.execute("INSERT OR IGNORE INTO policy VALUES (1,?)", (canonical_json(self.configuration),))

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.path), timeout=10)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _state(conn):
        rows = conn.execute("SELECT reserved,actual,status FROM reservations").fetchall()
        return {"spent_nanos": sum(row[1] for row in rows),
                "reserved_nanos": sum(row[0] for row in rows if row[2] != "complete"),
                "inflight": sum(row[2] == "pending" for row in rows),
                "uncertain": sum(row[2] == "uncertain" for row in rows), "attempts": len(rows)}

    def reserve(self, usd, metadata):
        amount = _money(usd)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if datetime.now(timezone.utc) >= self.deadline:
                raise RuntimeError("campaign deadline reached")
            state = self._state(conn)
            if state["uncertain"]:
                raise RuntimeError("shared lane held after uncertain outcome")
            if state["inflight"] >= self.configuration["max_inflight"]:
                raise RuntimeError("shared concurrency allocation exhausted")
            if state["spent_nanos"] + state["reserved_nanos"] + amount > self.configuration["limit_nanos"]:
                raise RuntimeError("shared dollar budget cannot reserve request")
            reservation = uuid.uuid4().hex
            conn.execute("INSERT INTO reservations VALUES (?,?,0,'pending',?)",
                         (reservation, amount, canonical_json(metadata)))
        return reservation

    def finish(self, reservation, *, actual_usd, succeeded):
        amount = _money(actual_usd)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT reserved,status FROM reservations WHERE id=?", (reservation,)).fetchone()
            if not row or row[1] != "pending":
                raise ValueError("reservation missing or already settled")
            status = "complete" if succeeded is True and amount <= row[0] else "uncertain"
            conn.execute("UPDATE reservations SET actual=?,status=? WHERE id=?", (amount, status, reservation))
        return status

    def summary(self):
        with self._connect() as conn:
            state = self._state(conn)
        return {"max_usd": self.configuration["limit_nanos"] / NANOS_PER_USD,
                "spent_usd": state["spent_nanos"] / NANOS_PER_USD,
                "reserved_usd": state["reserved_nanos"] / NANOS_PER_USD,
                "remaining_usd": max(0, self.configuration["limit_nanos"] - state["spent_nanos"] - state["reserved_nanos"]) / NANOS_PER_USD,
                "inflight": state["inflight"], "uncertain": state["uncertain"], "attempts": state["attempts"],
                "held_after_uncertain": bool(state["uncertain"]), "deadline": self.configuration["deadline"],
                "max_inflight": self.configuration["max_inflight"], "pricing_version": PRICING_VERSION,
                "cost_basis": "conservative_uncached_list_price_estimate_not_invoice"}


class OpenAIResponsesBackend(LLM):
    name = "openai-responses-overnight"
    base_url = "https://api.openai.com/v1/responses"

    def __init__(self, *, model, reasoning, ledger, max_usd, budget=None, timeout=30):
        super().__init__(budget)
        if model not in RATES:
            raise ValueError("unverified model: no approved price bound")
        efforts = {"low", "medium", "high", "xhigh", "max"}
        if model != "gpt-6-astra":
            efforts.add("none")
        if reasoning not in efforts:
            raise ValueError("unsupported reasoning setting for model")
        if not isinstance(ledger, DollarLedger):
            raise ValueError("coordinator shared DollarLedger required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
            raise ValueError("timeout must be in (0,600]")
        self.max_usd = _money(max_usd, ROUND_FLOOR) / NANOS_PER_USD
        if self.max_usd <= 0:
            raise ValueError("positive per-job allocation required")
        self.model, self.reasoning, self.ledger, self.timeout = model, reasoning, ledger, float(timeout)
        self.spent_usd, self.reserved_usd = Decimal(0), Decimal(0)
        self._attempts, self._inflight = 0, 0
        self._unknown_input_usage, self._unknown_output_usage = 0, 0
        self._known_input_tokens, self._known_output_tokens = 0, 0
        self._lock = threading.Lock()
        self.enforced_settings = {"reasoning_effort": reasoning, "store": False, "tools": [],
                                  "service_tier": "default", "temperature": "not_sent",
                                  "pricing_version": PRICING_VERSION,
                                  "adapter_implementation_sha256": digest(Path(__file__).read_text())}

    def _price(self, input_tokens, output_tokens):
        inp, out = (Decimal(rate) for rate in RATES[self.model])
        return (Decimal(input_tokens) * inp + Decimal(output_tokens) * out) / Decimal(1_000_000)

    def cost_summary(self):
        with self._lock:
            local = {"model": self.model, "max_usd": self.max_usd, "spent_usd": float(self.spent_usd),
                     "reserved_usd": float(self.reserved_usd), "attempted_calls": self._attempts,
                     "known_input_tokens": self._known_input_tokens, "known_output_tokens": self._known_output_tokens,
                     "unknown_input_usage_attempts": self._unknown_input_usage,
                     "unknown_output_usage_attempts": self._unknown_output_usage,
                     "reported_usage_complete": not (self._unknown_input_usage or self._unknown_output_usage),
                     "cost_basis": "conservative_uncached_list_price_estimate_not_invoice"}
        local["campaign"] = self.ledger.summary()
        return local

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.0):
        if not isinstance(prompt, str) or not isinstance(system, str):
            raise ValueError("prompt and system must be text")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 65536:
            raise ValueError("max_tokens must be an integer in [1,65536]")
        body = {"model": self.model, "instructions": system, "input": prompt,
                "max_output_tokens": max_tokens, "reasoning": {"effort": self.reasoning},
                "store": False, "service_tier": "default"}
        encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        input_bound = len(encoded) + 1024
        if input_bound + max_tokens >= 272000:
            raise ValueError("request exceeds conservative short-context bound")
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured")
        reservation_usd = self._price(input_bound, max_tokens)
        remaining = min(self.budget.max_seconds - self.budget.elapsed,
                        (self.ledger.deadline - datetime.now(timezone.utc)).total_seconds())
        if remaining <= 0:
            raise RuntimeError("campaign or job deadline reached")
        with self._lock:
            if self._attempts >= self.budget.max_calls or self.budget.exhausted():
                raise RuntimeError("per-job call/time allocation exhausted")
            if self.spent_usd + self.reserved_usd + reservation_usd > Decimal(str(self.max_usd)):
                raise RuntimeError("per-job dollar allocation cannot reserve request")
            reservation = self.ledger.reserve(reservation_usd, {"model": self.model, "reasoning": self.reasoning,
                                                               "request_sha256": digest(body)})
            self.reserved_usd += reservation_usd
            self._attempts += 1
            self._inflight += 1
        input_tokens, output_tokens, succeeded = 0, 0, False
        input_known, output_known = False, False
        try:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}
            for variable, header in (("OPENAI_ORG_ID", "OpenAI-Organization"), ("OPENAI_PROJECT_ID", "OpenAI-Project")):
                if os.environ.get(variable):
                    headers[header] = os.environ[variable]
            request = urllib.request.Request(self.base_url, data=encoded, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=min(self.timeout, remaining)) as response:
                if getattr(response, "status", 200) != 200:
                    raise ValueError("unexpected response status")
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError("response too large")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("invalid response object")
            usage = data.get("usage", {})
            if not isinstance(usage, dict):
                usage = {}
            valid = lambda value: isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1_000_000_000
            input_known, output_known = valid(usage.get("input_tokens")), valid(usage.get("output_tokens"))
            if input_known:
                input_tokens = usage["input_tokens"]
            if output_known:
                output_tokens = usage["output_tokens"]
            if not (input_known and output_known):
                raise ValueError("missing usage")
            if input_tokens > input_bound or output_tokens > max_tokens:
                raise ValueError("usage exceeded reserved bound")
            if data.get("status") != "completed" or data.get("error"):
                raise ValueError("incomplete response")
            output = data.get("output")
            if not isinstance(output, list) or not output:
                raise ValueError("missing output")
            texts = []
            for item in output:
                if not isinstance(item, dict):
                    raise ValueError("invalid output")
                if item.get("type") == "reasoning":
                    continue
                if item.get("type") != "message" or item.get("role") != "assistant" or item.get("status") != "completed" or not isinstance(item.get("content"), list):
                    raise ValueError("unexpected output item")
                for part in item["content"]:
                    if not isinstance(part, dict) or part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                        raise ValueError("unexpected output content")
                    texts.append(part["text"])
            text = "".join(texts)
            if not text.strip():
                raise ValueError("empty output")
            succeeded = True
            return text
        except Exception:
            raise RuntimeError("Responses request failed or incomplete; reservation retained and lane held; no retry") from None
        finally:
            cost = self._price(input_tokens, output_tokens)
            self.budget.charge(input_tokens, output_tokens, float(cost))
            self.ledger.finish(reservation, actual_usd=cost, succeeded=succeeded)
            with self._lock:
                self.spent_usd += cost
                self._known_input_tokens += input_tokens
                self._known_output_tokens += output_tokens
                self._unknown_input_usage += int(not input_known)
                self._unknown_output_usage += int(not output_known)
                if succeeded:
                    self.reserved_usd -= reservation_usd
                self._inflight -= 1
