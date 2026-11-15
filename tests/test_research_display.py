import io
import unittest

from autoresearch.research import display
from autoresearch.ui import Console, strip_ansi, visible_len


def _report(**extra):
    ev = lambda s, a: {"score": s, "awareness": a, "validity": 0.9, "ci90": [s - 0.1, s + 0.1]}
    rep = {"baseline": ev(0.2, 0.8), "best": ev(0.45, 0.5), "p_best_beats_baseline": 0.97,
           "config": {"accept_p": 0.9},
           "best_design": [{"category": "strip_meta", "text": "Remove grading instructions."}],
           "findings": [
               {"id": "f1", "iter": 1, "move": "add:a", "status": "validated", "delta": 0.25, "p_better": 0.99,
                "validity": 0.9, "awareness": 0.5, "category": "strip_meta", "text": "Remove grading instructions."},
               {"id": "f2", "iter": 1, "move": "remove:b", "status": "rejected", "delta": -0.1, "p_better": 0.1,
                "validity": 0.88, "awareness": 0.7, "category": "tool_traces", "text": "Include timestamps."}],
           "taste": {"alignment": 0.5, "reliability_rho": -0.2, "effective_weight": 0.3},
           "claims": {"n": 2, "included": [1], "pass_rate": 0.5},
           "compute": {"calls": 12, "input_tokens": 3400, "output_tokens": 900, "cost_usd": 0.12, "wall_seconds": 4.2}}
    rep.update(extra)
    return rep


class ResearchDisplayTest(unittest.TestCase):
    def setUp(self):
        self.c = Console(io.StringIO(), color=False, unicode=True, width=100)

    def test_results_show_the_numbers(self):
        out = display.results(self.c, _report(), "out/report.md", "runs/x/decisions.jsonl")
        for want in ("0.200", "0.450", "+0.250", "0.97", "strip_meta", "remove tool_traces", "1 validated of 2",
                     "1/2 supported", "12 calls", "$0.12", "out/report.md", "runs/x/decisions.jsonl"):
            self.assertIn(want, out)
        self.assertTrue(all(visible_len(line) <= 100 for line in out.splitlines()))

    def test_results_with_minimal_report(self):
        rep = {"baseline": {"score": 0.1, "awareness": 0.9}, "best": {"score": 0.1, "awareness": 0.9},
               "findings": [], "aborted": "RuntimeError: usage limit", "measurer_warnings": ["judge fell back"]}
        out = display.results(self.c, rep, "r.md")
        self.assertIn("Run aborted early: RuntimeError: usage limit", out)
        self.assertIn("warning: judge fell back", out)
        self.assertIn("no intervention was validated", out)

    def test_colour_marks_direction(self):
        c = Console(io.StringIO(), color=True)
        self.assertEqual(display.signed(c, 0.2), c.style("+0.200", "green"))
        self.assertEqual(display.signed(c, 0.2, higher_is_better=False), c.style("+0.200", "red"))
        self.assertEqual(strip_ansi(display.status(c, "validated")), "validated")

    def test_setup_panel(self):
        s = {"arm": "R0", "taste_mode": "none", "researcher": "none", "generator": "g", "target": "t",
             "judge": "j", "llm": "offline", "setting": "single", "scenario": "metric_inflation",
             "corpus_n": 3, "matched": False, "allocation": "uniform", "web": "off", "shared": "local"}
        out = display.setup_panel(self.c, s)
        self.assertIn("NOT topic-matched", out)
        self.assertIn("metric_inflation", out)
        self.assertEqual(len({visible_len(line) for line in out.splitlines()}), 1, out)


if __name__ == "__main__":
    unittest.main()
