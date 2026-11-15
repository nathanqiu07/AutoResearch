"""scripts/plots.py on offline grid outputs (charts only where matplotlib is installed)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import plots  # noqa: E402
from autoresearch.grid import grid_cells, run_local  # noqa: E402

try:
    import matplotlib  # noqa: F401
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False

PREREG = {"arms": {"uniform": {"allocation": "uniform"}, "market": {"allocation": "market"}}, "seeds": [0, 1],
          "shared_run_settings": {"iterations": 3, "samples": 4, "web": False, "shared_memory": False,
                                  "faithfulness_samples": 0, "no_claims": True}}


class TestPlots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ar_plots_")
        run_local(grid_cells(PREREG, llm="offline"), cls.tmp, workers=4)
        cls.rows = plots.load_runs([cls.tmp])

    def test_load_and_tables(self):
        self.assertEqual(len(self.rows), 4)
        self.assertEqual(set(plots.by_arm(self.rows)), {"uniform", "market"})
        self.assertTrue(all(r["offline"] for r in self.rows))
        md = plots.summary_md(self.rows, "t")
        self.assertIn("offline simulator", md)
        self.assertIn("| market | 2 |", md)
        per_finding = {row.split("|")[1].strip(): row.split("|")[5].strip() for row in plots.e5_table(self.rows)[2:]}
        self.assertTrue(all(v in ("n/a (no spend recorded)", "no finding") for v in per_finding.values()), per_finding)
        q = plots.a1a2_quadrants(self.rows)
        self.assertEqual(sum(q["market"].values()), 2)

    def test_anytime_falls_back_to_samples_offline(self):
        d = plots.anytime_curves(self.rows)
        self.assertEqual(d["x_key"], "samples")
        self.assertEqual(set(d["curves"]), {"uniform", "market"})
        for c in d["curves"].values():
            self.assertEqual(len(c["x"]), len(c["y"]))

    def test_summary_command(self):
        out = os.path.join(self.tmp, "charts")
        with contextlib.redirect_stdout(io.StringIO()):
            plots.main(["summary", self.tmp, "--out", out])
        self.assertTrue(os.path.exists(os.path.join(out, "summary.md")))

    @unittest.skipUnless(HAVE_MPL, "matplotlib not installed (scripts/requirements-plots.txt)")
    def test_charts(self):
        out = os.path.join(self.tmp, "charts_all")
        with contextlib.redirect_stdout(io.StringIO()):
            plots.main(["all", self.tmp, "--out", out])
        for f in ("anytime.png", "a1_a2.png", "allocation.png"):
            self.assertTrue(os.path.exists(os.path.join(out, f)), f)
        fid = os.path.join(self.tmp, "fid.json")
        with open(fid, "w") as f:
            json.dump({"methods": {"m1": {"accuracy": 0.6, "ci95": [0.55, 0.65]},
                                   "m3": {"accuracy": 0.66, "ci95": [0.6, 0.7]}}}, f)
        with contextlib.redirect_stdout(io.StringIO()):
            plots.main(["fidelity", fid, "--ceiling", "0.8", "--out", out])
        self.assertTrue(os.path.exists(os.path.join(out, "fidelity.png")))


if __name__ == "__main__":
    unittest.main()
