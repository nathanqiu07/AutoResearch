"""The demo reads immutable evidence, ignoring working-tree changes and new files."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("track_e_demo", Path(__file__).resolve().parents[1] / "scripts/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoTests(unittest.TestCase):
    def test_replay_is_committed_and_preserves_negative_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                                      cwd=root, check=True, capture_output=True)
            git("init", "-q")
            results = root / "results"
            results.mkdir()
            report = {"run_id": "r", "arm": "market", "code_version": "abc", "config": {"seed": 7, "samples": 4},
                      "baseline": {"score": .5}, "best": {"score": .4}, "findings": [{"status": "rejected"}],
                      "compute": {"calls": 0, "input_tokens": 0}}
            path = results / "run.json"
            path.write_text(json.dumps(report))
            git("add", ".")
            git("commit", "-qm", "evidence")
            path.write_text(json.dumps({**report, "best": {"score": 1.0}}))
            (results / "new.json").write_text(json.dumps(report))
            data = demo.replay(root=root)
            self.assertEqual(len(data["runs"]), 1)
            self.assertEqual(data["runs"][0]["best"]["score"], .4)
            self.assertEqual(data["runs"][0]["validated"], 0)
            self.assertEqual(data["runs"][0]["backend"], "offline simulator")
            self.assertFalse(data["complete"])
            self.assertEqual(len(data["moments"]), 4)
            self.assertIn("MISSING evidence", demo.render(data))
            for unsafe in ("/tmp", "results/../scripts", "scripts"):
                with self.assertRaises(ValueError):
                    demo.replay(paths=[unsafe], root=root)


if __name__ == "__main__":
    unittest.main()
