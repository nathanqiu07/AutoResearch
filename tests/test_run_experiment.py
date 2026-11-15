"""scripts/run_experiment.py: pre-launch checks and an offline run from a snapshot,
in a throwaway git repository (never this one)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import run_experiment as RE  # noqa: E402

PREREG = {"experiment": "E9", "status": "final", "blocked_on": [],
          "arms": {"uniform": {"allocation": "uniform"}, "market": {"allocation": "market"}}, "seeds": [0],
          "shared_run_settings": {"iterations": 1, "samples": 4, "web": False, "shared_memory": False,
                                  "faithfulness_samples": 0, "no_claims": True}}


def read(path):
    with open(path) as f:
        return f.read()


def sh(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=cwd, check=True,
                   capture_output=True)


class Repo:
    def __init__(self):
        self.d = tempfile.mkdtemp(prefix="ar_re_")
        shutil.copytree(os.path.join(ROOT, "autoresearch"), os.path.join(self.d, "autoresearch"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "data"), os.path.join(self.d, "data"))
        os.makedirs(os.path.join(self.d, "results", "prereg"))
        with open(os.path.join(self.d, ".gitignore"), "w") as f:
            f.write("runs/\n__pycache__/\n")
        sh(self.d, "init", "-q")
        sh(self.d, "add", ".")
        sh(self.d, "commit", "-qm", "code")

    def write_prereg(self, data, commit=True):
        with open(os.path.join(self.d, "results", "prereg", "E9.json"), "w") as f:
            json.dump(data, f)
        if commit:
            sh(self.d, "add", "results")
            sh(self.d, "commit", "-qm", "prereg")

    def touch_code(self):
        with open(os.path.join(self.d, "autoresearch", "new.py"), "w") as f:
            f.write("X = 1\n")
        sh(self.d, "add", "autoresearch")
        sh(self.d, "commit", "-qm", "code change")

    def close(self):
        shutil.rmtree(self.d, ignore_errors=True)


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def refused(self, *a, **k):
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
            RE.check("E9", *a, root=self.r.d, **k)
        return str(cm.exception)

    def test_uncommitted_refused(self):
        self.r.write_prereg(PREREG, commit=False)
        self.assertIn("not committed", self.refused("anthropic"))

    def test_draft_only_offline(self):
        self.r.write_prereg({**PREREG, "status": "DRAFT", "blocked_on": ["x"]})
        self.assertIn("not final", self.refused("anthropic"))
        self.assertIn("only run offline", self.refused("anthropic", allow_draft=True))
        info = RE.check("E9", "offline", allow_draft=True, root=self.r.d)
        self.assertTrue(info["draft"])

    def test_code_after_prereg_refused_until_recommitted(self):
        self.r.write_prereg(PREREG)
        RE.check("E9", "anthropic", root=self.r.d)
        self.r.touch_code()
        self.assertIn("changed after the pre-registration", self.refused("anthropic"))
        self.r.write_prereg({**PREREG, "note": "re-committed after the code change"})
        self.assertFalse(RE.check("E9", "anthropic", root=self.r.d)["draft"])

    def test_modified_prereg_refused(self):
        self.r.write_prereg(PREREG)
        self.r.write_prereg({**PREREG, "seeds": [0, 1]}, commit=False)
        self.assertIn("uncommitted changes", self.refused("anthropic"))

    def test_commands_runner(self):
        info = {"prereg": {"runner": "commands", "commands": [["echo", "{out}/x"]]}, "path": "p"}
        self.assertEqual(RE.build_commands(info, "offline", "/o", False, None, None, []), [["echo", "/o/x"]])
        info = {"prereg": PREREG, "path": "results/prereg/E9.json"}
        modal = RE.build_commands(info, "anthropic", "/o", True, ["market"], [0], [])[0]
        self.assertEqual(modal[:5], ["modal", "run", "modal_app.py", "--mode", "research-grid"])


class TestOfflineRun(unittest.TestCase):
    def test_runs_from_snapshot_and_writes_manifest(self):
        r = Repo()
        try:
            r.write_prereg(PREREG)
            out = os.path.join(r.d, "results", "e9")
            with mock.patch.object(RE, "ROOT", r.d), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):     # paid backend needs --yes
                    RE.main(["E9", "--llm", "anthropic", "--no-coordination"])
                rc = RE.main(["E9", "--llm", "offline", "--no-coordination", "--workers", "2"])
            self.assertEqual(rc, 0)
            man = json.loads(read(os.path.join(out, "RUN_MANIFEST.json")))
            self.assertEqual(man["returncode"], 0)
            self.assertTrue(man["snapshot"].startswith(os.path.join("runs", "snapshots")))
            ver = read(os.path.join(out, "CODE_VERSION")).strip()
            for arm in ("uniform", "market"):
                cell = os.path.join(out, arm, "seed0")
                self.assertEqual(read(os.path.join(cell, "CODE_VERSION")).strip(), ver)
                reps = [f for f in os.listdir(os.path.join(cell, "out")) if f.endswith(".json")]
                self.assertEqual(len(reps), 1)
        finally:
            r.close()


if __name__ == "__main__":
    unittest.main()
