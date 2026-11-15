"""Prompt caching, list-price accounting and the Message Batches backend (WS E)."""
import contextlib
import io
import json
import os
import random
import sys
import tempfile
import threading
import unittest
from unittest import mock

from autoresearch import llm as L
from autoresearch.batch import AnthropicBatchLLM, BatchQueue
from autoresearch.llm import Budget, anthropic_usage_cost


class TestUsageCost(unittest.TestCase):
    def test_plain_and_cached_pricing(self):
        cost, saved = anthropic_usage_cost("claude-sonnet-4-6", {"input_tokens": 1_000_000, "output_tokens": 0})
        self.assertAlmostEqual(cost, 3.0)
        self.assertAlmostEqual(saved, 0.0)
        cost, saved = anthropic_usage_cost("claude-sonnet-4-6", {"input_tokens": 0, "output_tokens": 0,
                                                                 "cache_read_input_tokens": 1_000_000})
        self.assertAlmostEqual(cost, 0.3)
        self.assertAlmostEqual(saved, 2.7)
        cost, _ = anthropic_usage_cost("claude-sonnet-4-6", {"cache_creation_input_tokens": 1_000_000})
        self.assertAlmostEqual(cost, 3.75)    # writes carry the 1.25x premium (saved is negative)
        cost, _ = anthropic_usage_cost("claude-opus-5-5", {"cache_read_input_tokens": 1_000_000})
        self.assertAlmostEqual(cost, 0.20)

    def test_batch_halves_and_unknown_is_free(self):
        cost, saved = anthropic_usage_cost("claude-haiku-4-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                                           batch=True)
        self.assertAlmostEqual(cost, 3.0)
        self.assertAlmostEqual(saved, 3.0)
        self.assertEqual(anthropic_usage_cost("no-such-model", {"input_tokens": 10}), (0.0, 0.0))

    def test_budget_records_cache_tokens(self):
        b = Budget()
        b.charge(10, 2, 0.01, cache_write=4, cache_read=3, saved=0.002)
        s = b.summary()
        self.assertEqual((s["cache_write_tokens"], s["cache_read_tokens"], s["saved_usd"]), (4, 3, 0.002))
        self.assertNotIn("saved_usd", Budget().summary())   # unchanged shape when nothing was cached


class Resp:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def read(self):
        return json.dumps(self.payload).encode()


class TestPromptCaching(unittest.TestCase):
    def test_long_system_prompt_is_cached_and_usage_charged(self):
        sent = []

        def fake(req, timeout=0):
            sent.append(json.loads(req.data))
            return Resp({"content": [{"type": "text", "text": "ok"}],
                         "usage": {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 0,
                                   "cache_read_input_tokens": 3000}})
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
                mock.patch.object(L.urllib.request, "urlopen", fake):
            m = L.AnthropicLLM("claude-sonnet-4-6", Budget())
            m.complete("q", system="rubric " * 3000)
            m.complete("q", system="short")
            off = L.AnthropicLLM("claude-sonnet-4-6", Budget(), cache=False)
            off.complete("q", system="rubric " * 3000)
        self.assertEqual(sent[0]["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(sent[1]["system"], "short")
        self.assertIsInstance(sent[2]["system"], str)
        self.assertEqual(m.budget.cache_read_tokens, 6000)
        self.assertEqual(m.budget.input_tokens, 2 * 3010)
        self.assertGreater(m.budget.saved_usd, 0)


class FakeBatchAPI:
    """Message Batches endpoints in memory: results come back shuffled, one errored."""

    def __init__(self, fail_text=None):
        self.created, self.fail_text = [], fail_text
        self.polls = 0

    def __call__(self, method, url, body):
        if method == "POST":
            self.created.append(body["requests"])
            return json.dumps({"id": f"b{len(self.created)}", "processing_status": "in_progress"}).encode()
        if url.endswith("/results"):
            reqs = self.created[-1]
            rows = []
            for r in reqs:
                text = r["params"]["messages"][0]["content"]
                if text == self.fail_text:
                    rows.append({"custom_id": r["custom_id"], "result": {"type": "errored",
                                                                         "error": {"type": "invalid_request"}}})
                else:
                    rows.append({"custom_id": r["custom_id"], "result": {"type": "succeeded", "message": {
                        "content": [{"type": "text", "text": "echo " + text}],
                        "usage": {"input_tokens": 100, "output_tokens": 10}}}})
            random.Random(0).shuffle(rows)
            return "\n".join(json.dumps(r) for r in rows).encode()
        self.polls += 1
        bid = url.rsplit("/", 1)[1]
        return json.dumps({"id": bid, "processing_status": "ended" if self.polls >= 2 else "in_progress",
                           "results_url": f"https://example.invalid/{bid}/results"}).encode()


class TestBatchQueue(unittest.TestCase):
    def _llm(self, api):
        q = BatchQueue("k", idle_seconds=0.2, poll_seconds=0.01, transport=api)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            return AnthropicBatchLLM("claude-haiku-4-5", Budget(), queue=q), q

    def test_concurrent_calls_share_one_batch_and_map_by_custom_id(self):
        api = FakeBatchAPI()
        m, q = self._llm(api)
        out = {}

        def call(k):
            out[k] = m.complete(f"p{k}", system="s")
        ts = [threading.Thread(target=call, args=(k,)) for k in range(12)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        self.assertEqual(out, {k: f"echo p{k}" for k in range(12)})
        self.assertEqual(len(api.created), 1)
        self.assertEqual(len(api.created[0]), 12)
        self.assertEqual(q.batches[0]["results"], {"succeeded": 12})
        self.assertEqual(m.budget.calls, 12)
        self.assertAlmostEqual(m.budget.cost_usd, 12 * 0.5 * (100 * 1.0 + 10 * 5.0) / 1e6)
        self.assertGreater(m.budget.saved_usd, 0)

    def test_errored_request_raises_only_in_its_thread(self):
        api = FakeBatchAPI(fail_text="bad")
        m, _ = self._llm(api)
        res = {}

        def call(p):
            try:
                res[p] = m.complete(p)
            except RuntimeError as e:
                res[p] = e
        ts = [threading.Thread(target=call, args=(p,)) for p in ("good", "bad")]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        self.assertEqual(res["good"], "echo good")
        self.assertIsInstance(res["bad"], RuntimeError)

    def test_get_llm_backend(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            self.assertIsInstance(L.get_llm("anthropic-batch", "claude-haiku-4-5"), AnthropicBatchLLM)
            self.assertIsInstance(L.get_llm("offline", "anthropic-batch:claude-haiku-4-5"), AnthropicBatchLLM)


class TestBatchFinalScript(unittest.TestCase):
    def test_finds_reports_and_runs_offline(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
        import batch_final
        from autoresearch.cli import main
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["--llm", "offline", "research", "--iterations", "2", "--no-web", "--no-shared",
                      "--faithfulness-samples", "0", "--memory", os.path.join(d, "m"),
                      "--decisions-dir", os.path.join(d, "dec"), "--out", os.path.join(d, "out")])
            reps = batch_final.find_reports([d])
            self.assertEqual(len(reps), 1)
            with self.assertRaises(SystemExit):   # paid backend without --yes
                with contextlib.redirect_stdout(io.StringIO()):
                    batch_final.main([d, "--llm", "anthropic-batch"])
            with contextlib.redirect_stdout(io.StringIO()):
                rc = batch_final.main([d, "--llm", "offline", "--mode", "dev", "--", "--samples", "1",
                                       "--max-items", "2"])
            self.assertEqual(rc, 0)
            self.assertEqual(len(batch_final.find_reports([d])), 1)   # its own outputs are not reports
            self.assertTrue(any("_heldout_dev" in f for f in os.listdir(os.path.join(d, "out"))))


if __name__ == "__main__":
    unittest.main()
