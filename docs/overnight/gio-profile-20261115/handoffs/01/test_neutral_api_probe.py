import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class NeutralProbeTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name("neutral_api_probe.py")
        self.assertTrue(path.exists(), "standalone probe is required")
        spec = importlib.util.spec_from_file_location("neutral_api_probe", path)
        self.p = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.p)
        from autoresearch.taste.overnight import backends
        from autoresearch.llm import Budget
        self.b, self.Budget = backends, Budget
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        ledger = self.root / "phase2.sqlite"
        self.b.DollarLedger(ledger, max_usd=10, deadline="2099-01-01T00:00:00Z", max_inflight=2)
        policy = {"schema_version": "phase2-ledger-policy-v1", "deadline": "2099-01-01T00:00:00Z",
                  "pricing_version": backends.PRICING_VERSION,
                  "ledger": {"path": str(ledger), "max_usd": 10, "max_inflight": 2}}
        raw = json.dumps(policy).encode(); policy_path = self.root / "policy.json"; policy_path.write_bytes(raw)
        self.dispatch = {"schema_version": "neutral-api-probe-dispatch-v1", "campaign_id": "synthetic",
                         "script_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "runtime_root": str(self.root / "runtime"), "runtime_commit": "pinned-runtime",
                         "runtime_backend_sha256": "pinned-backend", "policy": {"path": str(policy_path), "sha256": hashlib.sha256(raw).hexdigest()},
                         "authorization_source": "synthetic offline test", "deadline": "2099-01-01T00:00:00Z",
                         "max_seconds": 400, "max_calls": 2, "max_usd": "1",
                         "probes": [{"model": "gpt-6-sol", "max_usd": "0.125"}, {"model": "gpt-6-astra", "max_usd": "0.5"}],
                         "settings": {"reasoning": "medium", "max_tokens": 8192, "timeout": 180},
                         "claims_root": str(self.root / "claims"), "output_root": str(self.root / "output")}

    def response(self, text='{"probe":"ok"}'):
        return io.BytesIO(json.dumps({"status": "completed", "usage": {"input_tokens": 100, "output_tokens": 20},
            "output": [{"type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": text}]}]}).encode())

    def run_probe(self):
        return self.p.run_probe(self.dispatch, self.b, self.Budget)

    def test_two_sequential_actual_backend_calls_are_pinned_and_accounted(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-secret"}), \
             patch("urllib.request.urlopen", side_effect=[self.response(), self.response()]) as network:
            result = self.run_probe()
        self.assertEqual(network.call_count, 2)
        self.assertEqual(result["status"], "complete")
        self.assertEqual([row["model"] for row in result["calls"]], ["gpt-6-sol", "gpt-6-astra"])
        for call in network.call_args_list:
            body = json.loads(call.args[0].data)
            self.assertEqual(body["reasoning"], {"effort": "medium"})
            self.assertEqual(body["max_output_tokens"], 8192)
            self.assertEqual(body["prompt_cache_options"], {"mode": "implicit", "ttl": "30m"})
            self.assertNotIn("tools", body)
            self.assertEqual(body["input"], 'Return exactly this JSON object and no other text: {"probe":"ok"}')
        self.assertEqual(result["calls"][0]["normalized_response"], '{"probe":"ok"}')
        self.assertEqual(result["calls"][0]["cost"]["known_input_tokens"], 100)
        self.assertEqual(result["calls"][1]["cost"]["known_output_tokens"], 20)
        self.assertNotIn("synthetic-secret", json.dumps(result))
        self.assertEqual(result["campaign_ledger"]["reserved_usd"], 0)

    def test_uncertain_outcome_retains_reservation_and_stops_second_call(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-secret"}), \
             patch("urllib.request.urlopen", side_effect=RuntimeError("synthetic-secret provider text")) as network:
            result = self.run_probe()
        self.assertEqual(network.call_count, 1)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["calls"][1]["status"], "not_started")
        self.assertGreater(result["campaign_ledger"]["reserved_usd"], 0)
        self.assertNotIn("synthetic-secret", json.dumps(result))

    def test_known_schema_mismatch_is_preserved_without_retry(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-secret"}), \
             patch("urllib.request.urlopen", side_effect=[self.response('{"probe":"wrong"}'), self.response()]) as network:
            result = self.run_probe()
        self.assertEqual(network.call_count, 2)
        self.assertEqual(result["calls"][0]["status"], "completed_call_invalid_probe")
        self.assertEqual(result["calls"][1]["status"], "complete")
        self.assertEqual(result["campaign_ledger"]["uncertain"], 0)

    def test_duplicate_dispatch_cannot_repeat_calls_with_changed_output_path(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-secret"}), \
             patch("urllib.request.urlopen", side_effect=[self.response(), self.response()]) as network:
            self.run_probe()
            self.dispatch["output_root"] = str(self.root / "other-output")
            with self.assertRaises(FileExistsError):
                self.run_probe()
        self.assertEqual(network.call_count, 2)

    def test_changed_settings_policy_hash_and_expired_deadline_never_call(self):
        import copy
        for key, value in (("settings", {"reasoning": "low", "max_tokens": 8192, "timeout": 180}),
                           ("script_sha256", "wrong"), ("deadline", "2000-01-01T00:00:00Z"),
                           ("max_calls", 3), ("max_usd", "1.01")):
            original = copy.deepcopy(self.dispatch); self.dispatch[key] = value
            with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-secret"}), patch("urllib.request.urlopen") as network:
                with self.assertRaises(ValueError):
                    self.run_probe()
                self.assertFalse(network.called)
            self.dispatch = original
        self.dispatch["policy"]["sha256"] = "wrong"
        with self.assertRaises(ValueError):
            self.run_probe()


if __name__ == "__main__":
    unittest.main()
