"""Offline contract tests for packet_audit; fixtures never invoke models."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "user_model_audit" / "packet_audit.py"


class PacketAuditTests(unittest.TestCase):
    def comparator(self):
        # Fail as an assertion, rather than an import error, before implementation.
        self.assertTrue(SCRIPT.is_file(), "packet_audit.py has not been implemented")
        spec = importlib.util.spec_from_file_location("packet_audit", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.compare_settings

    def test_exact_allowed_path_does_not_allow_other_model_changes(self):
        report = self.comparator()(
            {"models": {"auditor": "old", "target": "old"}, "novel": 1},
            {"models": {"auditor": "new", "target": "new"}, "novel": 2},
            allowed_paths=["models.auditor", "models"],
        )
        self.assertEqual([c["path"] for c in report["allowed_changes"]], ["models.auditor"])
        self.assertEqual([c["path"] for c in report["unexplained_changes"]],
                         ["models.target", "novel"])
        self.assertEqual(len(report["changes"]), 3)
        self.assertEqual(report["statistical_comparability"], "not_assessed")

    def test_nested_generation_routing_budget_seed_and_source_changes_survive(self):
        left = {"generation": {"target": {"temperature": 0.7}},
                "routing": {"target": {"allow_fallbacks": False}},
                "overall_cap_usd": 100, "seed_id": "v2_seed_48",
                "source_ids": ["a"], "prompt_sha256": "abc"}
        right = {"generation": {"target": {"temperature": 0.9}},
                 "routing": {"target": {"allow_fallbacks": True}},
                 "overall_cap_usd": 150, "seed_id": "v2_seed_49",
                 "source_ids": ["b"], "prompt_sha256": "def"}
        report = self.comparator()(left, right)
        self.assertEqual([c["path"] for c in report["changes"]],
                         ["generation.target.temperature", "overall_cap_usd",
                          "prompt_sha256", "routing.target.allow_fallbacks",
                          "seed_id", "source_ids"])
        self.assertEqual(len(report["unexplained_changes"]), 6)

    def test_missing_is_distinct_from_explicit_null_in_both_directions(self):
        report = self.comparator()({"removed": None}, {"added": None})
        self.assertEqual(report["changes"][0]["left"], {"present": False})
        self.assertEqual(report["changes"][0]["right"], {"present": True, "value": None})
        self.assertEqual(report["changes"][1]["left"], {"present": True, "value": None})
        self.assertEqual(report["changes"][1]["right"], {"present": False})

    def test_arrays_are_whole_values_and_boolean_is_not_number(self):
        report = self.comparator()({"seeds": [1, 2], "flag": True},
                                   {"seeds": [2, 1], "flag": 1})
        self.assertEqual([c["path"] for c in report["changes"]], ["flag", "seeds"])
        self.assertEqual(report["changes"][1]["left"]["value"], [1, 2])
        self.assertEqual(report["changes"][1]["right"]["value"], [2, 1])
        self.assertEqual(len(self.comparator()({"a": [True]}, {"a": [1]})["changes"]), 1)

    def test_key_order_alone_is_not_a_change(self):
        report = self.comparator()({"z": 1, "a": {"b": 2}}, {"a": {"b": 2}, "z": 1})
        self.assertEqual(report["changes"], [])
        self.assertEqual(report["statistical_comparability"], "not_assessed")

    def test_dotted_keys_cannot_borrow_allowance_for_nested_fields(self):
        report = self.comparator()({"a.b": 1, "a": {"b": 1}},
                                   {"a.b": 2, "a": {"b": 2}}, ["a.b"])
        self.assertEqual([c["path_segments"] for c in report["allowed_changes"]], [["a", "b"]])
        self.assertEqual([c["path_segments"] for c in report["unexplained_changes"]], [["a.b"]])

    def test_nonfinite_or_non_json_python_values_are_rejected(self):
        compare = self.comparator()
        for bad in ({"x": float("nan")}, {"x": float("inf")}, {"x": (1, 2)}, {1: "bad"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                compare(bad, {})

    def run_cli(self, directory, left, right, *extra):
        self.assertTrue(SCRIPT.is_file(), "packet_audit.py has not been implemented")
        directory = Path(directory)
        (directory / "left.json").write_text(left, encoding="utf-8")
        (directory / "right.json").write_text(right, encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), "--left", str(directory / "left.json"),
                               "--right", str(directory / "right.json"),
                               "--out", str(directory / "report.json"), *extra],
                              text=True, capture_output=True)

    def test_cli_records_hashes_paths_and_explicit_allowance(self):
        with tempfile.TemporaryDirectory() as directory:
            left, right = '{"model": "a"}\n', '{"model": "b"}\n'
            result = self.run_cli(directory, left, right, "--allow", "model")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((Path(directory) / "report.json").read_text())
            self.assertEqual(report["inputs"]["left"]["sha256"], hashlib.sha256(left.encode()).hexdigest())
            self.assertEqual(report["inputs"]["right"]["sha256"], hashlib.sha256(right.encode()).hexdigest())
            self.assertEqual(report["inputs"]["left"]["path"], str((Path(directory) / "left.json").resolve()))
            self.assertEqual(report["tool"]["sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
            self.assertEqual(len(report["allowed_changes"]), 1)
            self.assertEqual(report["unexplained_changes"], [])

    def test_cli_rejects_malformed_nonfinite_duplicate_and_nonobject_json(self):
        for bad in ('{"x":', '{"x": NaN}', '{"x": Infinity}', '{"x": 1e999}',
                    '{"x": 1, "x": 2}', '[1, 2]'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                result = self.run_cli(directory, bad, '{}')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(directory) / "report.json").exists())

    def test_cli_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            output.write_text("preserve this evidence", encoding="utf-8")
            result = self.run_cli(directory, '{}', '{}')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "preserve this evidence")


if __name__ == "__main__":
    unittest.main()
