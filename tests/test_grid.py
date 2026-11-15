import json
import os
import tempfile
import unittest
from unittest import mock

from autoresearch.grid import grid_cells, load_prereg, option_args, run_cell, write_cell
from autoresearch.research.decisions import code_version

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TINY = {"experiment": "T", "arms": {"uniform": {"allocation": "uniform"}, "market": {"allocation": "market"},
                                    "external": {"note": "not run by this CLI"}},
        "seeds": [0, 1],
        "shared_run_settings": {"comment": "x", "iterations": 2, "samples": 4, "web": False, "shared_memory": False,
                                "faithfulness_samples": 0, "accept_p": 0.9}}


class TestOptionArgs(unittest.TestCase):
    def test_mapping(self):
        a = option_args({"iterations": 3, "web": False, "shared_memory": False, "no_claims": True,
                         "heldout_judges": ["j1", "j2"], "comment": "ignored"}, "t")
        self.assertEqual(a, ["--iterations", "3", "--no-web", "--no-shared", "--no-claims",
                             "--heldout-judges", "j1", "j2"])

    def test_rejects_typos_and_cell_paths_and_threshold_drift(self):
        for bad in ({"iteratons": 3}, {"memory_dir": "x"}, {"out": "x"}, {"accept_p": 0.8}):
            with self.assertRaises(ValueError, msg=bad):
                option_args(bad, "t")


class TestGridCells(unittest.TestCase):
    def test_tiny(self):
        cells = grid_cells(TINY, llm="offline")
        self.assertEqual([c["cell"] for c in cells], ["uniform/seed0", "uniform/seed1", "market/seed0", "market/seed1"])
        self.assertIn("--allocation", cells[-1]["argv"])
        with self.assertRaises(ValueError):
            grid_cells(TINY, arms=["external"])

    def test_settings_cross_arms(self):
        p = {**TINY, "settings": {"sim": {"tools": "simulated"}, "box": {"tools": "sandbox"}}}
        cells = grid_cells(p, arms=["uniform"], seeds=[0])
        self.assertEqual([c["cell"] for c in cells], ["uniform/sim/seed0", "uniform/box/seed0"])

    def test_committed_preregs_expand(self):
        e4 = grid_cells(load_prereg(os.path.join(ROOT, "results/prereg/E4.json")))
        e5 = grid_cells(load_prereg(os.path.join(ROOT, "results/prereg/E5.json")))
        self.assertEqual(len(e4), 6 * 8)
        self.assertEqual(len(e5), 3 * 8)


class TestRunCell(unittest.TestCase):
    def test_offline_cell_writes_outputs_and_pinned_version(self):
        cell = grid_cells(TINY, arms=["market"], seeds=[0], llm="offline")[0]
        with mock.patch.dict(os.environ, {"AUTORESEARCH_CODE_VERSION": "pinned123"}):
            self.assertEqual(code_version(), "pinned123")
            res = run_cell(cell, root=ROOT)
        self.assertTrue(res["ok"], res["error"])
        self.assertEqual(res["code_version"], "pinned123")
        reports = [k for k in res["files"] if k.startswith("out/") and k.endswith(".json")]
        self.assertEqual(len(reports), 1)
        rep = json.loads(res["files"][reports[0]])
        self.assertEqual(rep["code_version"], "pinned123")       # the subprocess saw the pinned version too
        self.assertEqual(rep["allocation"]["mode"], "market")
        with tempfile.TemporaryDirectory() as d:
            out = write_cell(res, d)
            with open(os.path.join(out, "CODE_VERSION")) as f:
                self.assertEqual(f.read().strip(), "pinned123")
            self.assertTrue(os.path.exists(os.path.join(out, reports[0])))


if __name__ == "__main__":
    unittest.main()
