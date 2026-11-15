import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch


class BackendTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import backends
        self.b = backends
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "budget.sqlite3"

    def ledger(self, **kwargs):
        return self.b.DollarLedger(self.path, max_usd=kwargs.pop("max_usd", 1),
                                   deadline="2099-01-01T00:00:00+00:00", max_inflight=2, **kwargs)

    def backend(self, **kwargs):
        return self.b.OpenAIResponsesBackend(ledger=self.ledger(), max_usd=0.1,
                                             timeout=5, **kwargs)

    def response(self, **changes):
        body = {"status": "completed", "output": [{"type": "reasoning"},
                {"type": "message", "role": "assistant", "status": "completed",
                 "content": [{"type": "output_text", "text": '{"ok":true}'}]}],
                "usage": {"input_tokens": 100, "output_tokens": 20}}
        body.update(changes)
        return io.BytesIO(json.dumps(body).encode())

    def test_shared_ledger_blocks_aggregate_spend_and_reconfiguration(self):
        first = self.ledger(max_usd=0.01)
        second = self.ledger(max_usd=0.01)
        first.reserve(0.009, {"job_id": "one"})
        with self.assertRaisesRegex(RuntimeError, "budget"):
            second.reserve(0.002, {"job_id": "two"})
        with self.assertRaisesRegex(ValueError, "configuration"):
            self.ledger(max_usd=1)
        self.assertAlmostEqual(second.summary()["reserved_usd"], 0.009)

    def test_shared_concurrency_two_is_atomic_across_connections(self):
        self.ledger()
        def attempt(_):
            try:
                return self.ledger().reserve(0.001, {"fixture": True})
            except RuntimeError:
                return None
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(attempt, range(3)))
        self.assertEqual(sum(r is not None for r in results), 2)
        self.assertEqual(self.ledger().summary()["inflight"], 2)

    def test_uncertain_reservation_is_retained_and_holds_new_calls(self):
        ledger = self.ledger()
        reservation = ledger.reserve(0.1, {})
        ledger.finish(reservation, actual_usd=0.01, succeeded=False)
        summary = ledger.summary()
        self.assertAlmostEqual(summary["spent_usd"], 0.01)
        self.assertAlmostEqual(summary["reserved_usd"], 0.1)
        self.assertTrue(summary["held_after_uncertain"])
        with self.assertRaisesRegex(RuntimeError, "uncertain"):
            ledger.reserve(0.001, {})
        with self.assertRaisesRegex(ValueError, "settled"):
            ledger.finish(reservation, actual_usd=0, succeeded=True)

    def test_explicit_model_reasoning_and_storage_fields_reach_transport(self):
        backend = self.backend(model="gpt-6-sol", reasoning="medium")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
             patch("urllib.request.urlopen", return_value=self.response()) as network:
            self.assertEqual(backend.complete("q", system="s", max_tokens=128), '{"ok":true}')
        body = json.loads(network.call_args.args[0].data)
        self.assertEqual(body["model"], "gpt-6-sol")
        self.assertEqual(body["reasoning"], {"effort": "medium"})
        self.assertFalse(body["store"])
        self.assertNotIn("tools", body)
        self.assertNotIn("temperature", body)
        self.assertEqual(body["prompt_cache_options"], {"mode": "implicit", "ttl": "30m"})
        self.assertEqual(backend.enforced_settings["prompt_cache_options"], body["prompt_cache_options"])
        self.assertEqual(backend.enforced_settings["reasoning_effort"], "medium")
        self.assertAlmostEqual(backend.cost_summary()["spent_usd"], 0.00045)
        self.assertEqual(backend.cost_summary()["reserved_usd"], 0)

    def test_30m_cache_write_upper_bound_reserves_and_charges_every_input_token(self):
        from decimal import Decimal
        for model, input_rate, expected in (("gpt-6-luna", "0.125", 0.0000225),
                                           ("gpt-6-sol", "2.5", 0.00045),
                                           ("gpt-6-astra", "12.5", 0.00225)):
            with self.subTest(model=model):
                backend = self.backend(model=model, reasoning="medium")
                with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
                     patch("urllib.request.urlopen", return_value=self.response()) as network, \
                     patch.object(backend.ledger, "reserve", wraps=backend.ledger.reserve) as reserve:
                    backend.complete("synthetic", max_tokens=128)
                input_bound = len(network.call_args.args[0].data) + 1024
                # Derive the documented upper bound independently of backend._price.
                expected_input = Decimal(input_bound) * Decimal(input_rate) / 1_000_000
                output_rate = {"gpt-6-luna": Decimal("0.5"), "gpt-6-sol": Decimal("10"),
                               "gpt-6-astra": Decimal("50")}[model]
                self.assertEqual(reserve.call_args.args[0], expected_input + 128 * output_rate / 1_000_000)
                self.assertAlmostEqual(backend.cost_summary()["spent_usd"], expected)

    def test_new_cache_write_pricing_cannot_reopen_old_ledger_policy(self):
        with patch.object(self.b, "PRICING_VERSION", "openai-standard-short-context-2026-11-15"):
            prior = self.ledger()
            prior.reserve(0.001, {"legacy": True})
        with self.assertRaisesRegex(ValueError, "configuration"):
            self.ledger()
        self.assertEqual(prior.summary()["attempts"], 1)
        self.assertEqual(prior.summary()["reserved_usd"], 0.001)

    def test_invalid_model_or_reasoning_rejected_before_transport(self):
        for model, reasoning in [("unverified", "medium"), ("gpt-6-astra", "none"), ("gpt-6-sol", "ultra")]:
            with self.subTest(model=model, reasoning=reasoning), self.assertRaises(ValueError):
                self.backend(model=model, reasoning=reasoning)

    def test_large_context_and_missing_key_do_not_reserve_or_call(self):
        backend = self.backend(model="gpt-6-luna", reasoning="medium")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
             patch("urllib.request.urlopen") as network:
            with self.assertRaisesRegex(ValueError, "context"):
                backend.complete("x" * 272000, max_tokens=128)
        self.assertFalse(network.called)
        self.assertEqual(backend.ledger.summary()["attempts"], 0)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "configured"):
                backend.complete("q", max_tokens=128)
        self.assertEqual(backend.ledger.summary()["attempts"], 0)

    def test_transport_failure_retains_hold_and_never_retries(self):
        backend = self.backend(model="gpt-6-luna", reasoning="medium")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
             patch("urllib.request.urlopen", side_effect=RuntimeError("synthetic-key server body")) as network:
            with self.assertRaises(RuntimeError) as error:
                backend.complete("q", max_tokens=128)
            with self.assertRaises(RuntimeError):
                backend.complete("q", max_tokens=128)
        self.assertEqual(network.call_count, 1)
        self.assertNotIn("synthetic-key", str(error.exception))
        self.assertGreater(backend.cost_summary()["reserved_usd"], 0)
        self.assertEqual(backend.ledger.summary()["uncertain"], 1)

    def test_incomplete_response_preserves_reported_usage_and_reservation(self):
        backend = self.backend(model="gpt-6-sol", reasoning="medium")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
             patch("urllib.request.urlopen", return_value=self.response(status="incomplete")):
            with self.assertRaises(RuntimeError):
                backend.complete("q", max_tokens=128)
        self.assertAlmostEqual(backend.cost_summary()["spent_usd"], 0.00045)
        self.assertGreater(backend.cost_summary()["reserved_usd"], 0)

    def test_partial_usage_preserves_known_component_and_marks_unknown(self):
        for usage, expected, missing in (({"input_tokens": 100}, 0.00025, "output"),
                                         ({"output_tokens": 20}, 0.0002, "input")):
            with self.subTest(usage=usage):
                ledger = self.b.DollarLedger(Path(self.temp.name) / (missing + ".sqlite3"), max_usd=1,
                                             deadline="2099-01-01T00:00:00+00:00", max_inflight=2)
                backend = self.b.OpenAIResponsesBackend(model="gpt-6-sol", reasoning="medium", ledger=ledger, max_usd=0.1)
                with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
                     patch("urllib.request.urlopen", return_value=self.response(usage=usage)):
                    with self.assertRaises(RuntimeError):
                        backend.complete("q", max_tokens=128)
                summary = backend.cost_summary()
                self.assertAlmostEqual(summary["spent_usd"], expected)
                self.assertEqual(summary["unknown_" + missing + "_usage_attempts"], 1)
                self.assertFalse(summary["reported_usage_complete"])
                self.assertGreater(summary["reserved_usd"], 0)

    def test_absolute_deadline_and_per_job_budget_block_before_request(self):
        expired = self.b.DollarLedger(Path(self.temp.name) / "expired.sqlite3", max_usd=1,
                                      deadline="2000-01-01T00:00:00+00:00", max_inflight=2)
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            expired.reserve(0.001, {})
        backend = self.b.OpenAIResponsesBackend(model="gpt-6-luna", reasoning="medium", ledger=self.ledger(), max_usd=1e-8)
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), patch("urllib.request.urlopen") as network:
            with self.assertRaisesRegex(RuntimeError, "allocation"):
                backend.complete("q", max_tokens=128)
        self.assertFalse(network.called)
        self.assertEqual(backend.ledger.summary()["attempts"], 0)

    def test_runner_records_enforced_reasoning_and_exact_reserved_cost(self):
        from tests import test_overnight_runner as rf
        runner_case = rf.RunnerTests()
        runner_case.setUp()
        self.addCleanup(runner_case.doCleanups)
        runner_case.consumer = self.backend(model="gpt-6-sol", reasoning="medium")
        manifest = runner_case.manifest(stage="dev", deadline="2099-01-01T00:00:00+00:00",
                                       allocation={"max_calls": 1, "max_seconds": 30, "max_usd": 0.1,
                                                   "cost_mode": "priced_api", "authorization_source": "synthetic transport test"})
        output = [{"type": "message", "role": "assistant", "status": "completed",
                   "content": [{"type": "output_text", "text": '{"probabilities":[0.25,0.75]}'}]}]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), \
             patch("urllib.request.urlopen", return_value=self.response(output=output)):
            result = runner_case.run_job(manifest)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["actual_backend"]["enforced_settings"]["reasoning_effort"], "medium")
        self.assertAlmostEqual(result["usage"]["reported_api_usd"], 0.00045)
        self.assertEqual(result["usage"]["reserved_api_usd"], 0)
        self.assertEqual(result["usage"]["budget_detail"]["campaign"]["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
