"""Standalone producer checks: fake HTTP, real temporary shared ledger."""
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autoresearch.taste.overnight.backends import DollarLedger

HERE = Path(__file__).resolve().parent


def load_producer():
    path = HERE / "embedding_producer.py"
    spec = importlib.util.spec_from_file_location("bounded_embedding_producer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EmbeddingProducerTests(unittest.TestCase):
    def setUp(self):
        self.p = load_producer()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.requests = []
        for index in range(2):
            body = {"model": "text-embedding-3-small", "dimensions": 1536,
                    "encoding_format": "float", "input": ["synthetic source " + str(index)]}
            packet = self.root / ("packet-%d.json" % index)
            packet.write_text(self.p.canonical(body) + "\n")
            self.requests.append({"request_id": "request-%d" % index, "packet_path": str(packet),
                                  "packet_sha256": self.p.file_sha(packet),
                                  "input_sha256": self.p.digest(body["input"]),
                                  "response_path": str(self.root / ("response-%d.json" % index)),
                                  "receipt_path": str(self.root / ("receipt-%d.json" % index))})
        self.dispatch = {"schema_version": "bounded-embedding-dispatch-v1", "campaign_id": "synthetic",
                         "model": "text-embedding-3-small", "dimensions": 1536, "encoding_format": "float",
                         "rate_usd_per_million_input": "0.02", "rate_source": "https://developers.openai.com/api/docs/models/text-embedding-3-small",
                         "rate_verified_at": "2026-11-15", "authorization_source": "synthetic offline test",
                         "max_calls": 2, "max_usd": "0.01", "max_seconds": 120, "timeout_seconds": 30,
                         "deadline": "2099-01-01T00:00:00+00:00", "requests": self.requests,
                         "claims_root": str(self.root / "claims"), "summary_path": str(self.root / "summary.json"),
                         "runtime_commit": "a" * 40, "script_sha256": self.p.file_sha(HERE / "embedding_producer.py")}
        self.ledger = DollarLedger(self.root / "ledger.sqlite3", max_usd=1,
                                   deadline=self.dispatch["deadline"], max_inflight=2)
        self.calls = []

    def transport(self, request, timeout):
        self.calls.append((request, timeout))
        count = len(json.loads(request.data)["input"])
        return io.BytesIO(json.dumps({"model": "text-embedding-3-small", "object": "list",
                                     "data": [{"object": "embedding", "index": i, "embedding": [0.125] * 1536} for i in range(count)],
                                     "usage": {"prompt_tokens": 8, "total_tokens": 8}}).encode())

    def run_producer(self, transport=None):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}):
            return self.p.produce(self.dispatch, self.ledger, transport or self.transport)

    def test_exact_packets_two_calls_and_indexed_vector_receipts(self):
        result = self.run_producer()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["attempted_calls"], 2)
        self.assertEqual(len(self.calls), 2)
        for index, (request, _) in enumerate(self.calls):
            self.assertEqual(hashlib.sha256(request.data).hexdigest(), self.requests[index]["packet_sha256"])
            self.assertEqual(request.full_url, "https://api.openai.com/v1/embeddings")
            receipt = json.loads(Path(self.requests[index]["receipt_path"]).read_text())
            self.assertEqual(receipt["input_sha256"], self.requests[index]["input_sha256"])
            self.assertEqual(receipt["dimensions"], 1536)
            self.assertEqual(receipt["vectors"][0], {"index": 0, "embedding": [0.125] * 1536})
            self.assertEqual(receipt["response_sha256"], self.p.file_sha(self.requests[index]["response_path"]))
        self.assertEqual(self.ledger.summary()["attempts"], 2)
        self.assertEqual(self.ledger.summary()["reserved_usd"], 0)
        self.assertNotIn("synthetic-key", Path(self.dispatch["summary_path"]).read_text())

    def test_unknown_outcome_holds_money_and_stops_second_packet(self):
        def failure(request, timeout):
            self.calls.append((request, timeout))
            raise RuntimeError("synthetic-key private server text")
        result = self.run_producer(failure)
        self.assertEqual(result["attempted_calls"], 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result["requests"][0]["status"], "uncertain")
        self.assertEqual(result["requests"][1]["status"], "not_started")
        self.assertGreater(self.ledger.summary()["reserved_usd"], 0)
        self.assertEqual(self.ledger.summary()["uncertain"], 1)
        self.assertNotIn("synthetic-key", json.dumps(result))
        self.assertNotIn("private server text", json.dumps(result))
        with self.assertRaises((ValueError, FileExistsError)):
            self.run_producer(failure)
        self.assertEqual(len(self.calls), 1)

    def test_changed_packet_or_input_hash_is_rejected_before_reservation(self):
        self.requests[0]["input_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "input hash"):
            self.run_producer()
        self.assertEqual(self.ledger.summary()["attempts"], 0)
        self.assertEqual(self.calls, [])

    def test_invalid_vectors_preserve_known_usage_and_full_hold(self):
        def malformed(request, timeout):
            self.calls.append((request, timeout))
            return io.BytesIO(json.dumps({"model": "text-embedding-3-small", "data": [{"index": 0, "embedding": [0.1]}],
                                         "usage": {"prompt_tokens": 8, "total_tokens": 8}}).encode())
        result = self.run_producer(malformed)
        self.assertEqual(result["requests"][0]["status"], "uncertain")
        self.assertEqual(result["requests"][0]["usage"]["prompt_tokens"], 8)
        self.assertGreater(self.ledger.summary()["spent_usd"], 0)
        self.assertGreater(self.ledger.summary()["reserved_usd"], 0)
        self.assertEqual(len(self.calls), 1)

    def test_budget_and_deadline_fail_before_http(self):
        self.dispatch["max_usd"] = "0.000000001"
        with self.assertRaisesRegex(ValueError, "allocation"):
            self.run_producer()
        self.assertEqual(self.ledger.summary()["attempts"], 0)
        self.dispatch["max_usd"] = "0.01"
        self.dispatch["deadline"] = "2000-01-01T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "deadline"):
            self.run_producer()
        self.assertEqual(self.calls, [])

    def test_model_dimensions_and_script_pins_rejected_before_http(self):
        for key, value in (("model", "different"), ("dimensions", 3072), ("script_sha256", "f" * 64)):
            original = self.dispatch[key]
            self.dispatch[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_producer()
            self.dispatch[key] = original
        self.assertEqual(self.calls, [])

    def test_same_request_cannot_rerun_with_new_output_paths(self):
        self.run_producer()
        for index, request in enumerate(self.requests):
            request["response_path"] = str(self.root / ("new-response-%d.json" % index))
            request["receipt_path"] = str(self.root / ("new-receipt-%d.json" % index))
        self.dispatch["summary_path"] = str(self.root / "new-summary.json")
        with self.assertRaisesRegex(FileExistsError, "already claimed"):
            self.run_producer()
        self.assertEqual(len(self.calls), 2)

    def test_output_paths_cannot_mutate_pinned_runtime(self):
        self.dispatch["runtime_root"] = str(self.root)
        with self.assertRaisesRegex(ValueError, "frozen runtime"):
            self.run_producer()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.ledger.summary()["attempts"], 0)

    def test_native_runtime_commit_and_ledger_hash_are_checked(self):
        runtime = Path(__file__).resolve().parents[5]
        commit = subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip()
        dispatch = dict(self.dispatch, runtime_root=str(runtime), runtime_commit="f" * 40,
                        runtime_backend_sha256=self.p.file_sha(runtime / "autoresearch/taste/overnight/backends.py"),
                        ledger={"path": str(self.root / "native-ledger.sqlite3"), "max_usd": 1,
                                "deadline": self.dispatch["deadline"], "max_inflight": 2})
        with self.assertRaisesRegex(ValueError, "commit"):
            self.p.load_runtime(dispatch)
        self.assertFalse(Path(dispatch["ledger"]["path"]).exists())
        dispatch["runtime_commit"] = commit
        dispatch["runtime_backend_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "implementation hash"):
            self.p.load_runtime(dispatch)
        self.assertFalse(Path(dispatch["ledger"]["path"]).exists())

    def test_shared_budget_admission_failure_makes_no_http_call(self):
        self.ledger.reserve(1, {"fixture": "already allocated"})
        result = self.run_producer()
        self.assertEqual(result["attempted_calls"], 0)
        self.assertEqual(result["requests"][0]["status"], "blocked")
        self.assertEqual(self.calls, [])

    def test_local_artifact_failure_keeps_paid_request_accounted(self):
        original = self.p.write_new
        def fail_response(path, raw):
            if str(path) == self.requests[0]["response_path"]:
                raise OSError("synthetic local write failure")
            return original(path, raw)
        with patch.object(self.p, "write_new", side_effect=fail_response):
            result = self.run_producer()
        self.assertEqual(result["attempted_calls"], 1)
        self.assertEqual(result["requests"][0]["status"], "artifact_failed")
        self.assertEqual(result["requests"][1]["status"], "not_started")
        self.assertGreater(result["known_usage_usd"], 0)
        self.assertEqual(result["reserved_usd"], 0)
        self.assertTrue(Path(self.dispatch["summary_path"]).exists())


if __name__ == "__main__":
    unittest.main()
