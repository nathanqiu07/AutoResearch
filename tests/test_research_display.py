import io
import json
import os
import random
import tempfile
import unittest

from autoresearch.llm import OfflineLLM
from autoresearch.memory import ResearchMemory
from autoresearch.research import display
from autoresearch.research.ideas import Proposer
from autoresearch.research.loop import OpenResearcher, ResearchConfig
from autoresearch.research.measure import Measurer, Models, OfflineWorld
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



def _run(progress=None, iters=3):
    cfg = ResearchConfig(iterations=iters, seed=0, faithfulness_samples=0)
    ms = Measurer(Models(OfflineLLM(), OfflineLLM(), OfflineLLM()), simulator=OfflineWorld())
    r = OpenResearcher(ms, Proposer(OfflineLLM(), None, random.Random(0)), ResearchMemory(None), None, cfg,
                       progress=progress)
    return r.run()


class ProgressTest(unittest.TestCase):
    def test_progress_sees_every_iteration_and_does_not_change_the_run(self):
        events = []
        rep = _run(events.append)
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "baseline")
        self.assertEqual([e["iter"] for e in events if e["event"] == "iteration"], [1, 2, 3])
        self.assertEqual([e["iter"] for e in events if e["event"] == "progress"], [0, 1, 2, 3])
        self.assertNotIn("iteration", [e["event"] for e in rep["log"]])   # display-only events stay out of the log
        plain = _run()
        self.assertEqual(rep["findings"], plain["findings"])
        self.assertEqual(len(rep["log"]), len(plain["log"]))

    def test_printer_renders_a_run(self):
        buf = io.StringIO()
        c = Console(buf, color=False, unicode=True, width=100)
        _run(display.Progress(c, accept_p=0.9, confirm_p=0.75), iters=2)
        out = buf.getvalue()
        for want in ("baseline", "iteration 1/2", "iteration 2/2", "measure", "outcome", "best"):
            self.assertIn(want, out)
        self.assertTrue(all(visible_len(line) <= 100 for line in out.splitlines()), out)


    def test_printer_shows_a1_a2_and_streams_events(self):
        buf = io.StringIO()
        c = Console(buf, color=False, unicode=True, width=100)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            rep = _run(display.Progress(c, accept_p=0.9, confirm_p=0.75, events_path=path), iters=2)
            events = [json.loads(line) for line in open(path)]
        out = buf.getvalue()
        self.assertIn("A1 ", out)
        self.assertIn("A2 ", out)
        self.assertEqual(events[0]["event"], "baseline")
        self.assertIn("verbalized", events[0])
        self.assertIn("self_report", events[0])
        self.assertEqual(sum(e["event"] == "evaluated" for e in events),
                         sum(e["event"] == "evaluated" for e in rep["log"]))
        self.assertTrue(all(visible_len(line) <= 100 for line in out.splitlines()), out)


if __name__ == "__main__":
    unittest.main()
