"""Reference-lane boundaries: final isolation, immutable inputs, and spending admission."""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from autoresearch.taste.prefdata import build_manifest, normalize_row


def module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "overnight_labeled_reference.py"
    spec = importlib.util.spec_from_file_location("labeled_reference", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.records = []
        for user, outer in (("dev-one", "train"), ("final-one", "test")):
            for split in ("train", "val", "test"):
                row = {"user_id": user, "conversation_id": user + split,
                       "context": [{"role": "user", "content": "A question " + split}],
                       "chosen": {"content": "Preferred " + split},
                       "rejected": {"content": "Other " + split}, "split": split}
                self.records.append(normalize_row(row, "prism", outer, 0))
        self.source = self.root / "source.jsonl"
        self.source.write_text("".join(json.dumps(asdict(r)) + "\n" for r in self.records))
        self.canonical = self.root / "canonical.json"
        self.canonical.write_text(json.dumps(build_manifest(self.records, 0)))

    def prepared(self):
        mod = module()
        out = self.root / "private"
        return mod, out, mod.prepare(self.source, self.canonical, out, n_users=1)

    def lease(self, mod, plan_path):
        plan = json.loads(plan_path.read_text())
        (self.root / "claims").mkdir(exist_ok=True)
        lease = {"job_id": "synthetic-reference-01", "role": "10", "state": "authorized",
                 "provider": "openai", "model": "gpt-6-luna", "plan_sha256": mod.file_sha(plan_path),
                 "max_usd": 5, "max_calls": 1500, "max_seconds": 3600,
                 "deadline": plan["deadline"], "final_authorized": False,
                 "user_partition": "dev", "methods": ["m0", "m1", "m2", "m3"],
                 "claim_path": str(self.root / "claims" / "synthetic-reference-01.json")}
        path = self.root / "lease.json"
        path.write_text(json.dumps(lease))
        return path, lease

    def test_preparation_never_deserializes_final_records(self):
        # Invalid JSON for final rows makes accidental final deserialization observable.
        with self.source.open("w") as f:
            for row in self.records:
                f.write(json.dumps(asdict(row)) + "\n" if row.user_split == "dev"
                        else '{"user_split": "test", "choice": INVALID FINAL ROW}\n')
        mod, out, plan_path = self.prepared()
        plan = json.loads(plan_path.read_text())
        self.assertEqual(plan["user_ids"], ["prism:dev-one"])
        self.assertEqual(plan["n_records"], 3)
        self.assertEqual(plan["n_predictions"], 4)
        staged = [json.loads(s) for s in (out / "records.jsonl").read_text().splitlines()]
        self.assertEqual({r["user_split"] for r in staged}, {"dev"})
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)
        self.assertEqual((out / "records.jsonl").stat().st_mode & 0o777, 0o600)

    def test_changed_selected_label_fails_replay(self):
        rows = [asdict(r) for r in self.records]
        rows[0]["choice"]["chosen"] = "b" if rows[0]["choice"]["chosen"] == "a" else "a"
        self.source.write_text("".join(json.dumps(r) + "\n" for r in rows))
        with self.assertRaisesRegex(ValueError, "normalization"):
            self.prepared()

    def test_changed_canonical_partition_fails_before_output(self):
        data = json.loads(self.canonical.read_text())
        data["users"]["prism:dev-one"]["history"] = []
        self.canonical.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.prepared()
        self.assertFalse((self.root / "private").exists())

    def test_private_snapshot_cannot_be_overwritten(self):
        mod, out, _ = self.prepared()
        with self.assertRaises(FileExistsError):
            mod.prepare(self.source, self.canonical, out, n_users=1)

    def test_snapshot_drift_is_rejected_before_backend(self):
        mod, out, plan_path = self.prepared()
        lease_path, _ = self.lease(mod, plan_path)
        (out / "records.jsonl").write_text("changed")
        with self.assertRaisesRegex(ValueError, "snapshot"):
            mod.validate_execution(plan_path, lease_path, now=1)

    def test_code_drift_is_rejected(self):
        mod, _, plan_path = self.prepared()
        lease_path, _ = self.lease(mod, plan_path)
        with patch.object(mod, "runtime_identity", return_value={"changed": True}):
            with self.assertRaisesRegex(ValueError, "runtime"):
                mod.validate_execution(plan_path, lease_path, now=1)

    def test_plan_settings_must_match_the_actual_intervention(self):
        mod, _, plan_path = self.prepared()
        original = json.loads(plan_path.read_text())
        for key, bad in (("backend", "different"), ("reasoning", "medium"),
                         ("tools", True), ("output_tokens", 8192)):
            with self.subTest(key=key):
                plan_path.write_text(json.dumps(dict(original, **{key: bad})))
                lease_path, _ = self.lease(mod, plan_path)
                with self.assertRaisesRegex(ValueError, "settings"):
                    mod.validate_execution(plan_path, lease_path, now=1)

    def test_claim_path_must_be_absolute_and_outside_packet(self):
        mod, out, plan_path = self.prepared()
        lease_path, lease = self.lease(mod, plan_path)
        for bad in ("relative.json", str(out / "claim.json")):
            lease_path.write_text(json.dumps(dict(lease, claim_path=bad)))
            with self.assertRaisesRegex(ValueError, "claim"):
                mod.validate_execution(plan_path, lease_path, now=1)

    def test_mismatched_or_excessive_or_final_lease_is_rejected(self):
        mod, _, plan_path = self.prepared()
        lease_path, lease = self.lease(mod, plan_path)
        for key, bad in (("plan_sha256", "bad"), ("max_usd", 6), ("max_calls", 1501),
                         ("max_seconds", 3601), ("provider", "openrouter"),
                         ("model", "different"), ("final_authorized", True),
                         ("user_partition", "test"), ("methods", ["m0"])):
            with self.subTest(key=key):
                lease_path.write_text(json.dumps(dict(lease, **{key: bad})))
                with self.assertRaises(ValueError):
                    mod.validate_execution(plan_path, lease_path, now=1)

    def test_deadline_and_duplicate_launch_are_rejected(self):
        mod, out, plan_path = self.prepared()
        lease_path, lease = self.lease(mod, plan_path)
        lease["deadline"] = "1970-01-01T00:00:01Z"
        lease_path.write_text(json.dumps(lease))
        with self.assertRaisesRegex(ValueError, "deadline"):
            mod.validate_execution(plan_path, lease_path, now=2)
        mod.claim_launch(out, {"job_id": "first"})
        with self.assertRaises(FileExistsError):
            mod.claim_launch(out, {"job_id": "first"})

    def test_uncertain_network_outcome_blocks_later_requests(self):
        mod = module()
        from autoresearch.llm import Budget
        backend = mod.ReferenceBackend("gpt-6-luna", budget=Budget(max_calls=5, max_seconds=30), max_usd=5)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-only"}), \
                patch("urllib.request.urlopen", side_effect=OSError("network")) as network:
            with self.assertRaises(RuntimeError):
                backend.complete("first")
            with self.assertRaisesRegex(RuntimeError, "uncertain"):
                backend.complete("second")
            self.assertEqual(network.call_count, 1)
            self.assertGreater(backend.cost_summary()["reserved_usd"], 0)

    def test_copying_run_packet_does_not_reset_shared_lease_claim(self):
        mod, out, plan_path = self.prepared()
        lease_path, lease = self.lease(mod, plan_path)
        second = self.root / "copied-packet"
        shutil.copytree(out, second)
        mod.claim_lease(plan_path, lease_path, lease)
        with self.assertRaises(FileExistsError):
            mod.claim_lease(second / "plan.json", lease_path, lease)
        self.assertFalse((second / "LAUNCH_USED.json").exists())


if __name__ == "__main__":
    unittest.main()
