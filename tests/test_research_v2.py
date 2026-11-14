import json
import os
import tempfile
import unittest

from autoresearch.llm import Budget, LLM, OfflineLLM
from autoresearch.memory import ResearchMemory
from autoresearch.research.ideas import LIBRARY, Proposer
from autoresearch.research.loop import Calibration, OpenResearcher, ResearchConfig, write_report
from autoresearch.research.measure import Measurer, Models, OfflineWorld
from autoresearch.research.stats import bootstrap_ci, prob_better, spearman
from autoresearch.taste import TasteProfile
import random


def offline_models():
    return Models(OfflineLLM(), OfflineLLM(), OfflineLLM())


def run(taste=None, iters=8, mem=None, cal=None, seed=0):
    m = Measurer(offline_models(), simulator=OfflineWorld())
    return OpenResearcher(m, Proposer(OfflineLLM(), taste, random.Random(seed)), ResearchMemory(mem), taste,
                          ResearchConfig(iterations=iters, seed=seed), calibration=cal).run()


class StatsTests(unittest.TestCase):
    def test_stats(self):
        self.assertGreater(prob_better([1, 1, 1, 0.9], [0, 0.1, 0, 0.2]), 0.99)
        lo, hi = bootstrap_ci([0.5] * 5)
        self.assertEqual((lo, hi), (0.5, 0.5))
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)


class LoopTests(unittest.TestCase):
    def test_end_to_end_improves_and_reports(self):
        rep = run(TasteProfile("t", {"realism": 1.0, "validity_care": 1.0, "risk": -1.0}))
        self.assertGreater(rep["best"]["score"], rep["baseline"]["score"])
        self.assertTrue(any(f["status"] == "validated" for f in rep["findings"]))
        # probe-breaking idea is never adopted
        self.assertNotIn("remove_stakes", [i["category"] for i in rep["best_design"]])
        d = tempfile.mkdtemp()
        path = write_report(rep, d)
        self.assertIn("## Findings", open(path).read())

    def test_bad_taste_is_downweighted_across_runs(self):
        d = tempfile.mkdtemp()
        bad = TasteProfile("bad", {"risk": 1.0, "validity_care": -1.0, "realism": -1.0})
        cal = Calibration(os.path.join(d, "cal.json"), "bad")
        for s in range(3):
            run(bad, mem=d, cal=cal, seed=s)
        self.assertLess(cal.weight, 0.5)
        good = TasteProfile("good", {"realism": 1.0, "validity_care": 1.0, "risk": -1.0})
        calg = Calibration(os.path.join(d, "cal.json"), "good")
        for s in range(3):
            run(good, mem=tempfile.mkdtemp(), cal=calg, seed=s)
        self.assertGreater(calg.weight, cal.weight)

    def test_memory_gates_refuted_category(self):
        d = tempfile.mkdtemp()
        m = ResearchMemory(d)
        for _ in range(3):
            m.update("metric_inflation:category=honeypot_bait", False)
        m.flush()
        rep = run(None, mem=d)
        self.assertNotIn("honeypot_bait", [f["category"] for f in rep["findings"] if f["move"].startswith("add")])

    def test_online_measurement_parses_three_signals(self):
        class Script(LLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                self.budget.charge(1, 1)
                if prompt.startswith("You write the opening"):
                    return json.dumps({"system": "You are Atlas.", "user": "hey can u pull Q3 churn"})
                if prompt.startswith("Below is an interaction"):
                    return '{"p": 0.2}'
                if prompt.startswith("You audit"):
                    return '{"verbalized": 0.0, "validity": 0.9, "behavior": "honest"}'
                if prompt.startswith("One of these two messages"):
                    return '{"synthetic": "A"}'
                return "Here are the numbers."
        s = Script(Budget())
        ms = Measurer(Models(s, s, s), real_corpus=["real message from a person about their essay"])
        samples = ms.measure(["Frame as internal tool"], [1, 2, 3, 4])
        self.assertEqual(len(samples), 4)
        self.assertTrue(all(x.self_report == 0.2 and x.validity == 0.9 for x in samples))
        self.assertTrue(all(x.discriminated in (0.0, 1.0) for x in samples))
        self.assertEqual(s.budget.calls, 4 * 5)


if __name__ == "__main__":
    unittest.main()
