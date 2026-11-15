"""Regression checks for audit persistence and cross-worktree test protection."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autoresearch.taste import fidelity
from autoresearch.taste.methods import create_method
from autoresearch.taste.prefdata import build_manifest, write_manifest
from tests.test_fidelity import records
from tests.test_usermodel import RecordingLLM


class TastePipelineAuditTests(unittest.TestCase):
    def test_final_marker_resolves_to_same_common_git_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repository"
            worktree = Path(d) / "separate-worktree"
            common = root / ".git"
            with patch.object(fidelity, "__file__", str(root / "autoresearch/taste/fidelity.py")), \
                    patch.object(fidelity.subprocess, "check_output", return_value=".git\n"):
                primary = fidelity._final_marker()
            with patch.object(fidelity, "__file__", str(worktree / "autoresearch/taste/fidelity.py")), \
                    patch.object(fidelity.subprocess, "check_output", return_value=str(common) + "\n"):
                linked = fidelity._final_marker()
            self.assertEqual(primary, linked)
            self.assertEqual(primary.parent, common.resolve())

    def test_linked_worktree_honors_legacy_primary_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repository"
            worktree = Path(d) / "linked"
            worktree.mkdir()
            common = root / ".git"
            common.mkdir(parents=True)
            legacy = root / "results/fidelity/TEST_USED"
            legacy.parent.mkdir(parents=True)
            legacy.write_text('{"already_used": true}')
            manifest = worktree / "manifest.json"
            write_manifest(manifest, build_manifest(records()))
            factory = {"m0": lambda user: create_method("m0", RecordingLLM())}
            with patch.object(fidelity, "__file__", str(worktree / "autoresearch/taste/fidelity.py")), \
                    patch.object(fidelity.subprocess, "check_output", return_value=str(common) + "\n"):
                with self.assertRaises(FileExistsError):
                    fidelity.run_fidelity(records(), manifest, factory, worktree / "new-final", "arena",
                                          users="test", final=True,
                                          final_marker=common / "fidelity_TEST_USED")
            self.assertFalse((worktree / "new-final").exists())

    def test_nonfinite_response_keeps_raw_failure_trace(self):
        for token in ("NaN", "1e999"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as d:
                trace = Path(d) / "requests.jsonl"

                class RawResponse(RecordingLLM):
                    def complete(self, prompt, **kwargs):
                        self.budget.charge(10, 5)
                        return '{"probabilities": [%s, 0.2]}' % token

                model = create_method("m0", RawResponse(), trace_path=trace)
                with self.assertRaises(ValueError):
                    model.predict("question", ["left", "right"])
                rows = [json.loads(line) for line in trace.read_text().splitlines()]
                self.assertEqual(len(rows), 1)
                self.assertIn(token, rows[0]["raw_response"])
                self.assertIn("error", rows[0])
                self.assertEqual(model.cost["calls"], 1)

    def test_cache_hits_remain_auditable_without_extra_model_calls(self):
        with tempfile.TemporaryDirectory() as d:
            trace = Path(d) / "requests.jsonl"
            llm = RecordingLLM()
            model = create_method("m0", llm, cache_dir=Path(d) / "cache", trace_path=trace)
            model.predict("question", ["left", "right"])
            model.predict("question", ["left", "right"])
            rows = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual(len(llm.prompts), 1)
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[1]["cache_hit"])
            self.assertEqual(rows[0]["parsed_response"], rows[1]["parsed_response"])
            self.assertEqual(rows[0]["prompt"], rows[1]["prompt"])

    def test_budget_rejection_is_logged_without_provider_call(self):
        with tempfile.TemporaryDirectory() as d:
            trace = Path(d) / "requests.jsonl"
            llm = RecordingLLM()
            model = create_method("m0", llm, max_calls=0, trace_path=trace)
            with self.assertRaisesRegex(RuntimeError, "budget"):
                model.predict("question", ["left", "right"])
            row = json.loads(trace.read_text())
            self.assertIn("budget", row["error"])
            self.assertEqual(llm.prompts, [])
            self.assertEqual(model.cost["calls"], 0)

    def test_manifest_provenance_is_copied_and_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = build_manifest(records(), provenance={"revision": "fixed", "files": []})
            write_manifest(root / "manifest.json", manifest)
            factory = {"m0": lambda user: create_method("m0", RecordingLLM())}
            report = fidelity.run_fidelity(records(), root / "manifest.json", factory,
                                           root / "out", "arena")
            self.assertNotEqual(report["mode"], "live")
            self.assertEqual(report["provenance"], manifest["provenance"])
            self.assertEqual(json.loads((root / "out/split-manifest.json").read_text()), manifest)
            drifted = copy.deepcopy(manifest)
            drifted["provenance"]["revision"] = "changed-after-registration"
            (root / "manifest.json").write_text(json.dumps(drifted))
            with self.assertRaisesRegex(ValueError, "manifest"):
                fidelity.run_fidelity(records(), root / "manifest.json", factory,
                                      root / "bad", "arena")
            self.assertFalse((root / "bad").exists())


if __name__ == "__main__":
    unittest.main()
