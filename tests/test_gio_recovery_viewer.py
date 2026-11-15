"""Offline viewer checks; fixtures never stand in for model-run evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1] / "scripts/gio_petri/morning_recovery/viewer.py"


class RecoveryViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert MODULE.is_file(), "full-chain viewer has not been implemented"
        spec = importlib.util.spec_from_file_location("gio_recovery_viewer", MODULE)
        cls.viewer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.viewer)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.text = 'Exact profile: prefer explicit controls. <script>alert("x")</script>\n'
        (self.root / "profile.txt").write_text(self.text)
        self.ref = {"path": "profile.txt", "sha256": hashlib.sha256(self.text.encode()).hexdigest()}
        self.index = {"schema_version": "gio-recovery-viewer-v1", "artifact_kind": "offline_fixture",
                      "run_id": "synthetic-check", "scenario": "Synthetic scenario", "snapshot_status": "partial",
                      "conditions": [{"id": "rich", "status": "error", "error": "Synthetic timeout",
                                      "stages": {"profile": [self.ref]},
                                      "reviews": {"validity": {"status": "rejected", "summary": "No valid review"}},
                                      "costs": {"known_usd": 0.01, "uncertain_usd": None, "reserved_usd": 0.2}}]}

    def collect(self):
        path = self.root / "input.json"
        path.write_text(json.dumps(self.index))
        return self.viewer.collect_index(path, self.root)

    def test_missing_conditions_and_stages_remain_visible(self):
        data = self.collect()
        self.assertEqual([a["id"] for a in data["conditions"]], ["generic", "raw", "rich", "compact"])
        self.assertEqual(data["conditions"][0]["status"], "not_supplied")
        self.assertEqual(data["conditions"][2]["stages"]["environment"], [])
        page = self.viewer.render_html(data)
        for text in ("Generic", "Raw", "Rich", "Compact", "Synthetic timeout", "Not supplied", "Unmeasured"):
            self.assertIn(text, page)

    def test_exact_text_loaded_once_and_escaped_in_html(self):
        data = self.collect()
        record = data["conditions"][2]["stages"]["profile"][0]
        self.assertEqual(record["text"], self.text)
        self.assertEqual(record["pin_status"], "verified")
        page = self.viewer.render_html(data)
        self.assertNotIn('<script>alert("x")</script>', page)
        self.assertIn("&lt;script&gt;", page)

    def test_hash_mismatch_hides_untrusted_changed_content(self):
        self.ref["sha256"] = "0" * 64
        data = self.collect()
        record = data["conditions"][2]["stages"]["profile"][0]
        self.assertEqual(record["status"], "error")
        self.assertIsNone(record["text"])
        self.assertIn("hash_mismatch", record["error"])

    def test_no_implicit_reads_of_embedded_pointers(self):
        (self.root / "private.txt").write_text("DO NOT LOAD THIS BODY")
        (self.root / "profile.txt").write_text('{"path":"private.txt"}')
        self.ref.pop("sha256")
        data = self.collect()
        self.assertNotIn("DO NOT LOAD THIS BODY", json.dumps(data))
        self.assertEqual(data["conditions"][2]["stages"]["profile"][0]["pin_status"], "unpinned")

    def test_parent_traversal_and_symlink_are_errors(self):
        (self.root / "alias.txt").symlink_to(self.root / "profile.txt")
        self.index["conditions"][0]["stages"]["profile"] = [{"path": "../secret.txt"}, {"path": "alias.txt"}]
        records = self.collect()["conditions"][2]["stages"]["profile"]
        self.assertTrue(all(r["status"] == "error" and r["text"] is None for r in records))

    def test_missing_file_is_a_record_not_a_disappeared_condition(self):
        self.ref["path"] = "absent.json"
        data = self.collect()
        self.assertEqual(data["conditions"][2]["status"], "error")
        self.assertEqual(data["conditions"][2]["stages"]["profile"][0]["error"], "file_missing")

    def test_fixture_and_partial_labels_are_unavoidable(self):
        page = self.viewer.render_html(self.collect())
        self.assertIn("OFFLINE FIXTURE", page)
        self.assertIn("Not a live model result", page)
        self.assertIn("Partial snapshot", page)

    def test_review_axes_and_unknown_cost_are_separate(self):
        data = self.collect()
        arm = data["conditions"][2]
        self.assertIsNone(arm["costs"]["uncertain_usd"])
        self.assertEqual(arm["reviews"]["validity"]["status"], "rejected")
        self.assertEqual(arm["reviews"]["taste"]["status"], "unmeasured")
        page = self.viewer.render_html(data)
        for axis in ("Environment validity", "Taste adherence", "Target behavior", "Uncertain bound", "Reservations"):
            self.assertIn(axis, page)

    def test_nonfinite_cost_and_duplicate_conditions_rejected(self):
        self.index["conditions"][0]["costs"]["known_usd"] = -1
        with self.assertRaises(ValueError): self.collect()
        self.index["conditions"][0]["costs"]["known_usd"] = 0
        self.index["conditions"].append(dict(self.index["conditions"][0]))
        with self.assertRaises(ValueError): self.collect()

    def test_credential_pattern_redacted_but_original_hash_retained(self):
        secret = "sk-proj-" + "a" * 30
        (self.root / "profile.txt").write_text(secret)
        self.ref.pop("sha256")
        data = self.collect()
        record = data["conditions"][2]["stages"]["profile"][0]
        self.assertNotIn(secret, json.dumps(data))
        self.assertEqual(record["redactions"], 1)
        self.assertEqual(record["sha256"], hashlib.sha256(secret.encode()).hexdigest())

    def test_output_is_self_contained_and_refuses_overwrite(self):
        data = self.collect()
        out = self.root / "render"
        receipt = self.viewer.write_report(data, out)
        self.assertTrue((out / "index.html").is_file())
        self.assertTrue((out / "snapshot.json").is_file())
        self.assertEqual(receipt["artifact_kind"], "offline_fixture")
        page = (out / "index.html").read_text()
        self.assertNotIn('<script src=', page)
        self.assertNotIn('https://', page)
        with self.assertRaises(FileExistsError): self.viewer.write_report(data, out)

    def test_recorded_run_requires_explicit_kind(self):
        self.index["artifact_kind"] = "pretend_live"
        with self.assertRaises(ValueError): self.collect()
