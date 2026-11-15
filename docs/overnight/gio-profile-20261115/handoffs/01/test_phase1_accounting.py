import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class AccountingTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name("phase1_accounting.py")
        self.assertTrue(path.exists(), "standalone accounting tool is required")
        spec = importlib.util.spec_from_file_location("phase1_accounting", path)
        self.p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.p)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "phase1.sqlite"
        self.rows, self.jobs = [], []
        self.manifest = {"schema_version": "phase1-accounting-dispatch-v1", "ledger_path": str(self.ledger),
                         "indices": [], "embedding_summaries": [], "profile_allocation_usd": "200",
                         "prior_outside_ledger_usd": "0.017601625"}

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (canonical(data) + "\n").encode()
        path.write_bytes(raw)
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}

    def job(self, job_id, model="gpt-6-luna", inp=100, out=20):
        rates = {"gpt-6-luna": (100, 500), "gpt-6-sol": (2000, 10000), "gpt-6-astra": (10000, 50000)}
        actual = inp * rates[model][0] + out * rates[model][1]
        backend = {"model": model, "enforced_settings": {"pricing_version": self.p.OLD_PRICING,
                   "reasoning_effort": "medium", "store": False, "service_tier": "default", "tools": []}}
        trace = {"status": "started", "attempt": 1, "backend": backend,
                 "prompt": "SYNTHETIC SECRET TEXT", "settings": {"system": "", "max_tokens": 128, "temperature": 0}}
        request = {"model": model, "input": trace["prompt"], "instructions": "", "max_output_tokens": 128,
                   "reasoning": {"effort": "medium"}, "store": False, "service_tier": "default"}
        ref = self.write(self.root / job_id / "traces" / "0001-started.json", trace)
        detail = {"model": model, "known_input_tokens": inp, "known_output_tokens": out,
                  "reported_usage_complete": True, "attempted_calls": 1, "unknown_input_usage_attempts": 0,
                  "unknown_output_usage_attempts": 0, "spent_usd": actual / 1e9, "reserved_usd": 0}
        usage = {"attempted_calls": 1, "uncertain_attempts": 0, "input_tokens": inp, "output_tokens": out,
                 "reported_api_usd": actual / 1e9, "reserved_api_usd": 0, "budget_detail": detail}
        result = {"schema_version": "overnight-result-v1", "job_id": job_id, "manifest_hash": "m" + job_id,
                  "actual_backend": backend, "usage": usage, "trace_hashes": [ref["sha256"]]}
        self.jobs.append({"job_id": job_id, "manifest_sha256": "m" + job_id, "usage": usage,
                          "result": self.write(self.root / job_id / "result.json", result)})
        self.rows.append(("r-" + job_id, actual * 10, actual, "complete", canonical({
            "model": model, "reasoning": "medium", "request_sha256": digest(request)})))

    def embedding(self):
        usage = {"prompt_tokens": 100, "total_tokens": 100, "known_input_tokens": 100, "complete": True}
        receipt = {"schema_version": "bounded-embedding-receipt-v1", "status": "complete", "request_id": "emb",
                   "model": "text-embedding-3-small", "dimensions": 1536, "input_sha256": "i", "packet_sha256": "p",
                   "response_sha256": "response", "usage": usage, "known_usage_usd": 0.000002}
        ref = self.write(self.root / "embedding-receipt.json", receipt)
        summary = {"schema_version": "bounded-embedding-result-v1", "model": "text-embedding-3-small",
                   "status": "complete", "attempted_calls": 1, "known_usage_usd": 0.000002, "reserved_usd": 0,
                   "requests": [dict(receipt, receipt_path=ref["path"], receipt_sha256=ref["sha256"])]}
        self.manifest["embedding_summaries"] = [self.write(self.root / "embedding-summary.json", summary)]
        self.rows.append(("r-embedding", 5000, 2000, "complete", canonical({"producer": "bounded-embeddings-v1",
                          "request_id": "emb", "input_sha256": "i", "packet_sha256": "p"})))

    def prepare(self):
        index = {"schema_version": "pilot-completion-index-v1", "batches": [{"jobs": self.jobs}]}
        self.manifest["indices"] = [self.write(self.root / "index.json", index)]
        with sqlite3.connect(str(self.ledger)) as conn:
            conn.execute("CREATE TABLE policy (id INTEGER PRIMARY KEY, body TEXT)")
            conn.execute("CREATE TABLE reservations (id TEXT PRIMARY KEY, reserved INTEGER, actual INTEGER, status TEXT, metadata TEXT)")
            conn.execute("INSERT INTO policy VALUES (1,?)", (canonical({"pricing_version": self.p.OLD_PRICING,
                         "limit_nanos": 199982398375, "max_inflight": 2, "deadline": "2099-01-01T00:00:00+00:00"}),))
            conn.executemany("INSERT INTO reservations VALUES (?,?,?,?,?)", self.rows)

    def test_exact_per_model_adjustment_and_embedding_is_counted_once(self):
        self.job("one"); self.job("two"); self.job("three", "gpt-6-sol"); self.embedding(); self.prepare()
        before = self.ledger.read_bytes()
        report = self.p.reconcile(self.manifest)
        self.assertEqual(report["status"], "ready_for_coordinator_close")
        self.assertEqual(report["phase1_conservative_upper_usd"], "0.000497000")
        self.assertEqual(report["known_input_adjustment_usd"], "0.000055000")
        self.assertEqual(report["provisional_phase2_cap_usd"], "199.981901375")
        self.assertEqual(report["embeddings"]["old_cost_usd"], "0.000002000")
        self.assertEqual(report["per_model"]["gpt-6-luna"]["attempts"], 2)
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertNotIn("SYNTHETIC SECRET TEXT", json.dumps(report))

    def test_pending_uncertain_and_missing_index_usage_refuse_closure(self):
        self.job("one"); self.prepare()
        with sqlite3.connect(str(self.ledger)) as conn:
            conn.execute("INSERT INTO reservations VALUES ('missing',10000,0,'pending',?)",
                         (canonical({"model": "gpt-6-sol", "request_sha256": "unmatched"}),))
        report = self.p.reconcile(self.manifest)
        self.assertEqual(report["status"], "unresolved")
        self.assertEqual(report["ledger"]["pending"], 1)
        self.assertIsNone(report["provisional_phase2_cap_usd"])
        self.manifest["closure"] = {"all_jobs_done": True, "authority": "synthetic test", "ledger_snapshot_sha256": report["ledger"]["snapshot_sha256"]}
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.p.reconcile(self.manifest, finalize=True)
        with sqlite3.connect(str(self.ledger)) as conn:
            conn.execute("UPDATE reservations SET status='uncertain' WHERE id='missing'")
        self.assertEqual(self.p.reconcile(self.manifest)["ledger"]["uncertain"], 1)

    def test_final_receipt_requires_explicit_done_authority_and_same_snapshot(self):
        self.job("one"); self.prepare()
        with self.assertRaisesRegex(ValueError, "closure_authority"):
            self.p.reconcile(self.manifest, finalize=True)
        report = self.p.reconcile(self.manifest)
        self.manifest["closure"] = {"all_jobs_done": True, "authority": "coordinator synthetic signal",
                                    "ledger_snapshot_sha256": "wrong"}
        with self.assertRaisesRegex(ValueError, "snapshot"):
            self.p.reconcile(self.manifest, finalize=True)
        self.manifest["closure"]["ledger_snapshot_sha256"] = report["ledger"]["snapshot_sha256"]
        closed = self.p.reconcile(self.manifest, finalize=True)
        self.assertEqual(closed["status"], "closed")
        target = self.root / "receipt.json"
        self.p.write_receipt(target, closed)
        with self.assertRaises(FileExistsError):
            self.p.write_receipt(target, closed)

    def test_tampered_result_trace_and_duplicate_jobs_are_rejected(self):
        self.job("one"); self.prepare()
        trace = self.root / "one/traces/0001-started.json"
        original = trace.read_bytes()
        trace.write_text("{}")
        with self.assertRaisesRegex(ValueError, "trace_hash"):
            self.p.reconcile(self.manifest)
        trace.write_bytes(original)
        result_path = Path(self.jobs[0]["result"]["path"])
        original_result = result_path.read_bytes()
        result_path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "evidence_file_hash"):
            self.p.reconcile(self.manifest)
        result_path.write_bytes(original_result)
        self.jobs.append(self.jobs[0])
        self.manifest["indices"] = [self.write(self.root / "index.json", {"schema_version": "pilot-completion-index-v1", "batches": [{"jobs": self.jobs}]})]
        with self.assertRaisesRegex(ValueError, "duplicate_job"):
            self.p.reconcile(self.manifest)

    def test_request_identity_mismatch_or_cost_mismatch_is_unresolved(self):
        self.job("one"); self.prepare()
        with sqlite3.connect(str(self.ledger)) as conn:
            conn.execute("UPDATE reservations SET metadata=?", (canonical({"model": "gpt-6-luna", "request_sha256": "wrong"}),))
        self.assertEqual(self.p.reconcile(self.manifest)["status"], "unresolved")
        with sqlite3.connect(str(self.ledger)) as conn:
            conn.execute("UPDATE reservations SET metadata=?,actual=1", (self.rows[0][4],))
        report = self.p.reconcile(self.manifest)
        self.assertIn("model_cost_mismatch:gpt-6-luna", report["unresolved"])

    def test_incomplete_usage_is_explicit_even_if_known_cost_matches(self):
        self.job("one"); self.jobs[0]["usage"]["budget_detail"]["reported_usage_complete"] = False
        self.jobs[0]["usage"]["budget_detail"]["unknown_output_usage_attempts"] = 1
        ref = self.jobs[0]["result"]; result = json.loads(Path(ref["path"]).read_text())
        result["usage"] = self.jobs[0]["usage"]; self.jobs[0]["result"] = self.write(Path(ref["path"]), result)
        self.prepare()
        report = self.p.reconcile(self.manifest)
        self.assertIn("incomplete_usage:one", report["unresolved"])
        self.assertIsNone(report["phase1_conservative_upper_usd"])

    def test_final_refuses_ledger_change_during_evidence_verification(self):
        self.job("one"); self.prepare()
        report = self.p.reconcile(self.manifest)
        self.manifest["closure"] = {"all_jobs_done": True, "authority": "synthetic done signal",
                                    "ledger_snapshot_sha256": report["ledger"]["snapshot_sha256"]}
        original_load = self.p.load
        changed = False
        def changing_load(ref, evidence):
            nonlocal changed
            if not changed:
                changed = True
                with sqlite3.connect(str(self.ledger)) as conn:
                    conn.execute("UPDATE reservations SET status='pending'")
            return original_load(ref, evidence)
        with patch.object(self.p, "load", side_effect=changing_load), self.assertRaisesRegex(ValueError, "snapshot"):
            self.p.reconcile(self.manifest, finalize=True)

    def test_cached_token_details_are_not_added_to_total_input_again(self):
        self.job("one")
        ref = self.jobs[0]["result"]
        result = json.loads(Path(ref["path"]).read_text())
        result["usage"]["budget_detail"]["input_tokens_details"] = {"cached_tokens": 80, "cache_write_tokens": 20}
        self.jobs[0]["usage"] = result["usage"]
        self.jobs[0]["result"] = self.write(Path(ref["path"]), result)
        self.prepare()
        report = self.p.reconcile(self.manifest)
        self.assertEqual(report["known_input_adjustment_usd"], "0.000002500")
        with sqlite3.connect(str(self.ledger)) as conn:
            conn.execute("UPDATE policy SET body=?", (canonical({"pricing_version": "different"}),))
        with self.assertRaisesRegex(ValueError, "pricing_policy"):
            self.p.reconcile(self.manifest)


if __name__ == "__main__":
    unittest.main()
