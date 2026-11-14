import json
import tempfile
import unittest
import contextlib
import io
from pathlib import Path

from autoresearch.taste.prefdata import PreferenceRecord, build_manifest, write_manifest
from autoresearch.taste.usermodel import Choice
from autoresearch.taste.methods import create_method
from tests.test_usermodel import RecordingLLM


def records():
    out = []
    for user, partition, labels in (("one", "dev", ["a"]), ("two", "dev", ["b", "b", "b"]),
                                    ("sealed", "test", ["a"])):
        for i, (split, chosen) in enumerate([("history", "a")] + [("test", y) for y in labels]):
            uid = "arena:" + user
            out.append(PreferenceRecord(Choice(uid, user + str(i), "left", "right", chosen,
                                               example_id=user + str(i), group_id=user + str(i)),
                                        "arena", partition, split, "train" if partition == "dev" else "test"))
    return out


class FidelityTests(unittest.TestCase):
    def test_shared_backend_budget_snapshot_is_saved_once(self):
        from autoresearch.taste.fidelity import run_fidelity
        llm = RecordingLLM()
        llm.cost_summary = lambda: {"reserved_usd": .25, "spent_usd": .1,
                                    "cost_basis": "conservative_estimate"}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            factories = {m: (lambda user, method=m: create_method(method, llm)) for m in ("m0", "m1")}
            report = run_fidelity(records(), p / "split.json", factories, p / "out", "arena")
            self.assertEqual(report["backend_budgets"], [{"backend": llm.label, **llm.cost_summary()}])
            self.assertEqual(json.loads((p / "out" / "report.json").read_text())["backend_budgets"],
                             report["backend_budgets"])

    def test_user_macro_not_pair_micro_and_dev_does_not_touch_test_users(self):
        from autoresearch.taste.fidelity import run_fidelity
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            llm = RecordingLLM({"probabilities": [0.8, 0.2]})
            factories = {"m0": lambda user: create_method("m0", llm)}
            report = run_fidelity(records(), p / "split.json", factories, p / "out", "arena")
            self.assertEqual(report["methods"]["m0"]["accuracy"], 0.5)
            self.assertEqual(report["methods"]["m0"]["n_users"], 2)
            self.assertNotIn("sealed", "\n".join(llm.prompts))
            self.assertEqual(len((p / "out" / "predictions.jsonl").read_text().splitlines()), 4)

    def test_final_requires_explicit_flag_and_marker_survives_output_change(self):
        from autoresearch.taste.fidelity import run_fidelity
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            marker = p / "TEST_USED"
            factory = {"m0": lambda user: create_method("m0", RecordingLLM())}
            with self.assertRaises(ValueError):
                run_fidelity(records(), p / "split.json", factory, p / "out", "arena",
                             users="test", final_marker=marker)
            self.assertFalse(marker.exists())
            run_fidelity(records(), p / "split.json", factory, p / "out", "arena",
                         users="test", final=True, final_marker=marker)
            with self.assertRaises(FileExistsError):
                run_fidelity(records(), p / "split.json", factory, p / "different", "arena",
                             users="test", final=True, final_marker=marker)

    def test_failures_count_as_wrong_and_are_retained(self):
        from autoresearch.taste.fidelity import run_fidelity
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            factory = {"m0": lambda user: create_method("m0", RecordingLLM({"probabilities": [1]}))}
            report = run_fidelity(records(), p / "split.json", factory, p / "out", "arena")
            self.assertEqual(report["methods"]["m0"]["accuracy"], 0)
            self.assertEqual(report["methods"]["m0"]["failures"], 4)
            self.assertIsNone(report["methods"]["m0"]["brier_valid_only"])

    def test_manifest_drift_fails_before_calls(self):
        from autoresearch.taste.fidelity import run_fidelity
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            with self.assertRaises(ValueError):
                run_fidelity(records()[:-1], p / "split.json", {}, p / "out", "arena")

    def test_paired_differences_use_the_same_users(self):
        from autoresearch.taste.fidelity import run_fidelity
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            factory = {m: (lambda user, method=m: create_method(method, RecordingLLM())) for m in ("m0", "m1")}
            report = run_fidelity(records(), p / "split.json", factory, p / "out", "arena")
            self.assertEqual(report["differences_vs_m1"]["m0"]["mean"], 0)
            self.assertEqual(report["differences_vs_m1"]["m0"]["ci95"], [0, 0])

    def test_cli_dry_run_inspects_without_model_calls(self):
        from autoresearch.taste.__main__ import main
        from autoresearch.taste.prefdata import save_records
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            save_records(p / "records.jsonl", records())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(["fidelity", "--records", str(p / "records.jsonl"),
                      "--manifest", str(p / "split.json"), "--dataset", "arena", "--dry-run"])
            result = json.loads(output.getvalue())
            self.assertEqual(result["n_users"], 2)
            self.assertEqual(result["n_predictions"], 8)

    def test_schema_search_is_bounded_and_dev_only(self):
        from scripts.schema_search import run_search
        from tests.test_taste_methods import ColorOracle
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(records()))
            configs = [{"id": "small", "method": "m5", "config": {"max_history": 1}}]
            summary = run_search(records(), p / "split.json", configs, ColorOracle(), p / "search", "arena")
            self.assertEqual(summary["selected_config_id"], "small")
            registration = json.loads((p / "search" / "small" / "registration.json").read_text())
            self.assertEqual(registration["user_partition"], "dev")
            self.assertNotIn("arena:sealed", registration["user_ids"])
            with self.assertRaises(ValueError):
                run_search(records(), p / "split.json", configs * 9, ColorOracle(), p / "bad", "arena")

    def test_incomplete_search_cannot_select_an_early_budget_survivor(self):
        from scripts.schema_search import run_search
        from tests.test_taste_methods import ColorOracle
        rows = [r for r in records() if r.choice.user_id == "arena:one" and r.choice_split == "test"]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            write_manifest(p / "split.json", build_manifest(rows))
            configs = [{"id": name, "method": "m5", "config": {}} for name in ("first", "second")]
            llm = ColorOracle()
            llm.budget.max_calls = 1
            summary = run_search(rows, p / "split.json", configs, llm,
                                 p / "search", "arena", max_calls=1)
            self.assertEqual(summary["trials"][0]["failures"], 0)
            self.assertEqual(summary["trials"][1]["failures"], 1)
            self.assertIsNone(summary["selected_config_id"])
            self.assertEqual(summary["status"], "incomplete")
            self.assertEqual(json.loads((p / "search" / "search.json").read_text()), summary)
