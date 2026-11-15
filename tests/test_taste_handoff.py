"""Independent plumbing checks; fixture scores are never preference evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.llm import Budget
from autoresearch.taste.fidelity import run_fidelity
from autoresearch.taste.handoff import build_bundle, write_bundle
from autoresearch.taste.methods import create_method
from autoresearch.taste.offline import OfflineTasteLLM, fixture_records
from autoresearch.taste.prefdata import build_manifest, write_manifest
from autoresearch.taste.usermodel import load_model


class OfflineHandoffTests(unittest.TestCase):
    def prepare(self, root):
        rows = fixture_records()
        manifest = root / "manifest.json"
        write_manifest(manifest, build_manifest(rows))
        llm = OfflineTasteLLM(budget=Budget(max_calls=300))
        factories = {m: (lambda user, method=m: create_method(
            method, llm, max_history=2, max_hypotheses=2, max_exemplars=1,
            max_principles=2, principles_per_pair=1)) for m in ("m0", "m1", "m2", "m3")}
        report = run_fidelity(rows, manifest, factories, root / "run", "prism",
                              run_config={"backend": "offline", "model": "fixture-v1"})
        return rows, manifest, llm, report

    def test_fit_reload_predict_evaluate_and_actual_adviser(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, manifest, llm, report = self.prepare(root)
            self.assertTrue(all(v["failures"] == 0 for v in report["methods"].values()))
            before = llm.budget.calls
            bundle = build_bundle(root / "run", rows, manifest, llm=llm)
            self.assertEqual(llm.budget.calls, before + 1)
            self.assertEqual(bundle["mode"], "offline_fixture")
            self.assertIn("not preference-accuracy evidence", bundle["interpretation"])
            self.assertEqual(len(bundle["examples"]), 4)
            self.assertEqual(bundle["integration"]["status"], "verified")
            self.assertEqual(bundle["integration"]["method"], "m3")
            self.assertEqual(bundle["integration"]["confidence_status"], "uncalibrated")
            self.assertTrue(bundle["integration"]["principles"])
            for example in bundle["examples"]:
                self.assertEqual(len(example["history"]), 2)
                self.assertEqual(len(example["validation"]), 2)
                self.assertNotIn(example["target"]["example_id"],
                                 [x["example_id"] for x in example["history"] + example["validation"]])
            m2 = next(e for e in bundle["examples"] if e["method"] == "m2")
            self.assertIn("OFFLINE FIXTURE", m2["artifacts"]["persona"])
            restored = load_model(root / "run/export/usermodel.json", OfflineTasteLLM())
            target = bundle["examples"][-1]["target"]
            prediction = restored.predict(target["context"], [target["a_text"], target["b_text"]])
            self.assertFalse(prediction.calibrated)
            self.assertEqual(prediction.choice, target["chosen"])
            self.assertEqual(restored.artifacts().metadata["weights_status"], "unavailable")
            self.assertEqual(restored.artifacts().assumptions, {})
            write_bundle(bundle, root / "bundle.json")
            self.assertEqual(json.loads((root / "bundle.json").read_text()), bundle)
            with self.assertRaises(FileExistsError):
                write_bundle(bundle, root / "bundle.json")

    def test_packaging_without_llm_does_not_predict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, manifest, llm, _ = self.prepare(root)
            before = llm.budget.calls
            bundle = build_bundle(root / "run", rows, manifest)
            self.assertEqual(llm.budget.calls, before)
            self.assertEqual(bundle["integration"]["status"], "not_run")
            self.assertFalse((root / "run/export").exists())

    def test_export_refuses_final_targets_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, manifest, _, _ = self.prepare(root)
            path = root / "run/registration.json"
            registration = json.loads(path.read_text())
            registration["user_partition"] = "test"
            path.write_text(json.dumps(registration))
            with self.assertRaisesRegex(ValueError, "allow_final"):
                build_bundle(root / "run", rows, manifest)

    def test_export_without_llm_copies_model_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, manifest, llm, _ = self.prepare(root)
            before = llm.budget.calls
            export = root / "handoff"
            bundle = build_bundle(root / "run", rows, manifest, export_dir=export, method="m2")
            self.assertEqual(llm.budget.calls, before)
            self.assertEqual(bundle["integration"]["status"], "exported_not_verified")
            model = load_model(export / "usermodel.json", OfflineTasteLLM())
            self.assertEqual(model.method_id, "m2")
            with self.assertRaises(FileExistsError):
                build_bundle(root / "run", rows, manifest, export_dir=export)

    def test_unknown_mode_fails_before_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, manifest, _, _ = self.prepare(root)
            path = root / "run/report.json"
            report = json.loads(path.read_text())
            report.pop("mode")
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "mode"):
                build_bundle(root / "run", rows, manifest, export_dir=root / "export")
            self.assertFalse((root / "export").exists())

    def test_bundle_checks_manifest_and_target_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, manifest, _, _ = self.prepare(root)
            with self.assertRaisesRegex(ValueError, "records do not match"):
                build_bundle(root / "run", rows[:-1], manifest)
            path = root / "run/predictions.jsonl"
            lines = [json.loads(s) for s in path.read_text().splitlines()]
            lines[0]["actual"] = "a" if lines[0]["actual"] == "b" else "b"
            path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
            with self.assertRaisesRegex(ValueError, "observed label"):
                build_bundle(root / "run", rows, manifest)

    def test_unsupported_backend_shape_and_model_fail_explicitly(self):
        with self.assertRaises(ValueError):
            OfflineTasteLLM("a-real-model")
        with self.assertRaisesRegex(ValueError, "unsupported"):
            OfflineTasteLLM().complete('unknown\nINPUT_JSON:\n{}')


if __name__ == "__main__":
    unittest.main()
