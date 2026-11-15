"""Message Batches API backend (PLAN 8 and 12.5 item 3: the final held-out sweeps).

Batches cost half of normal Messages API calls but return asynchronously, so a
synchronous pipeline (generator -> target -> judges, each step waiting on the
last) cannot simply hand its calls over. `BatchQueue` bridges the two: every
`AnthropicBatchLLM.complete` call from any worker thread is queued and blocks;
once no new call has arrived for `idle_seconds` (or `max_batch` are waiting),
the queue submits them as one batch, polls until it ends, and releases each
waiting thread with its own result. Run a sweep with many workers (e.g.
`--workers 64`): each pipeline stage then becomes one batch of calls.

Standard library only. The key comes from ANTHROPIC_API_KEY, as for AnthropicLLM.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
import uuid
from typing import Callable, Dict, List, Optional

from .llm import AnthropicLLM, Budget

BATCH_URL = "https://api.anthropic.com/v1/messages/batches"


class _Pending:
    __slots__ = ("body", "llm", "event", "result", "error")

    def __init__(self, body: dict, llm: "AnthropicBatchLLM"):
        self.body, self.llm = body, llm
        self.event = threading.Event()
        self.result: Optional[dict] = None
        self.error: Optional[str] = None


class BatchQueue:
    """Collects requests from many threads and submits them as Message Batches."""

    def __init__(self, key: str, idle_seconds: float = 3.0, max_batch: int = 10_000,
                 poll_seconds: float = 20.0, timeout_seconds: float = 24 * 3600,
                 transport: Optional[Callable[[str, str, Optional[dict]], bytes]] = None):
        self.key = key
        self.idle, self.max_batch = idle_seconds, max_batch
        self.poll, self.timeout = poll_seconds, timeout_seconds
        self.transport = transport or self._http
        self._lock = threading.Lock()
        self._pending: Dict[str, _Pending] = {}
        self._last = 0.0
        self._worker: Optional[threading.Thread] = None
        self.batches: List[dict] = []   # one record per submitted batch, for the run's report

    # ---------- HTTP ----------
    def _http(self, method: str, url: str, body: Optional[dict]) -> bytes:
        req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return r.read()
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("unreachable")

    # ---------- queue ----------
    def submit(self, body: dict, llm: "AnthropicBatchLLM") -> dict:
        """Queue one Messages API body and block until its batch result is in."""
        p = _Pending(body, llm)
        with self._lock:
            self._pending[f"r{uuid.uuid4().hex[:20]}"] = p
            self._last = time.time()
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, name="batch-queue", daemon=True)
                self._worker.start()
        p.event.wait()
        if p.error is not None:
            raise RuntimeError(f"batch request failed: {p.error}")
        return p.result

    def _run(self):
        while True:
            with self._lock:
                if not self._pending:
                    self._worker = None
                    return
                ready = len(self._pending) >= self.max_batch or time.time() - self._last >= self.idle
                if ready:
                    take = dict(list(self._pending.items())[: self.max_batch])
                    for k in take:
                        del self._pending[k]
            if not ready:
                time.sleep(min(0.2, self.idle))
                continue
            try:
                self._flush(take)
            except Exception as e:   # every waiting thread gets the error rather than hanging
                for p in take.values():
                    if not p.event.is_set():
                        p.error = f"{type(e).__name__}: {str(e)[:300]}"
                        p.event.set()

    def _flush(self, take: Dict[str, _Pending]):
        for p in take.values():
            p.llm.budget.check_spend()
        reqs = [{"custom_id": cid, "params": p.body} for cid, p in take.items()]
        t0 = time.time()
        batch = json.loads(self.transport("POST", BATCH_URL, {"requests": reqs}))
        bid = batch["id"]
        while batch.get("processing_status") != "ended":
            if time.time() - t0 > self.timeout:
                raise TimeoutError(f"batch {bid} did not end within {self.timeout:.0f}s")
            time.sleep(self.poll)
            batch = json.loads(self.transport("GET", f"{BATCH_URL}/{bid}", None))
        rows = [json.loads(l) for l in self.transport("GET", batch["results_url"], None).decode().splitlines()
                if l.strip()]
        by_id = {r["custom_id"]: r.get("result") or {} for r in rows}   # results come in any order
        counts: Dict[str, int] = {}
        for cid, p in take.items():
            res = by_id.get(cid, {"type": "missing"})
            counts[res.get("type", "missing")] = counts.get(res.get("type", "missing"), 0) + 1
            if res.get("type") == "succeeded":
                p.result = res["message"]
                p.llm.charge_usage(p.result.get("usage", {}), batch=True)
            else:
                p.error = f"{res.get('type')}: {json.dumps(res.get('error'))[:300]}"
            p.event.set()
        self.batches.append({"id": bid, "n": len(take), "results": counts,
                             "seconds": round(time.time() - t0, 1)})


_QUEUES: Dict[str, BatchQueue] = {}
_QLOCK = threading.Lock()


def shared_queue(key: str) -> BatchQueue:
    """One queue per API key per process, so every role's calls share batches."""
    with _QLOCK:
        if key not in _QUEUES:
            _QUEUES[key] = BatchQueue(key)
        return _QUEUES[key]


class AnthropicBatchLLM(AnthropicLLM):
    """AnthropicLLM whose calls go through the Message Batches API (half price,
    asynchronous). Same request bodies, prompt caching and Budget accounting."""
    name = "anthropic-batch"

    def __init__(self, model: str = "claude-sonnet-5-5", budget: Optional[Budget] = None, cache: bool = True,
                 queue: Optional[BatchQueue] = None):
        super().__init__(model, budget, cache)
        self.queue = queue or shared_queue(self.key)

    def _post(self, body: dict) -> dict:
        return self.queue.submit(body, self)
