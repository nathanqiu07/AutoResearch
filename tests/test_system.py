import os
import tempfile
import unittest

from autoresearch.benchmark import decision_alignment, run_benchmark
from autoresearch.drift import DriftMonitor
from autoresearch.llm import Budget, OfflineLLM, extract_json
from autoresearch.loop import LoopConfig, Researcher
from autoresearch.memory import ResearchMemory
from autoresearch.taste import TasteProfile, load_researcher, prediction_accuracy
from autoresearch.taste.choices import fit_choice_model
from autoresearch.taste.extract import profile_from_texts
from autoresearch.tasks import TASKS, get_task


class TaskTests(unittest.TestCase):
    def test_deterministic_and_bounded(self):
        for name in TASKS:
            t = get_task(name)
            a = t.evaluate(t.baseline_config(), OfflineLLM(), 4, 0)
            b = t.evaluate(t.baseline_config(), OfflineLLM(), 4, 0)
            self.assertEqual(a.score, b.score)
            self.assertTrue(0 <= a.score <= 1)

    def test_removing_probe_violates_invariant(self):
        t = get_task("eval_awareness")
        r = t.evaluate({**t.baseline_config(), "stakes": "removed"}, OfflineLLM(), 8, 0)
        self.assertFalse(r.valid)
        self.assertIn("probe_validity", r.violations)


class TasteTests(unittest.TestCase):
    def test_choice_fit_recovers_preferences(self):
        prof, test = load_researcher("demo_realist").build_profile(OfflineLLM())
        self.assertGreater(prediction_accuracy(prof, test), 0.75)

    def test_text_extraction_signs(self):
        p = profile_from_texts("x", [("research", "Realistic, real-world deployment data. Avoid risky moonshot bets.")],
                               OfflineLLM())
        self.assertGreater(p.weights["realism"], 0)
        self.assertLess(p.weights["risk"], 0)

    def test_choice_model_beats_chance_from_scratch(self):
        ch = [{"a": {"novelty": 1}, "b": {"novelty": 0}, "chosen": "a"}] * 10
        self.assertEqual(prediction_accuracy(fit_choice_model(ch, "x"), ch), 1.0)


class MemoryDriftTests(unittest.TestCase):
    def test_memory_persists_and_refutes(self):
        d = tempfile.mkdtemp()
        m = ResearchMemory(d)
        k = m.key("eval_awareness", "stakes", "removed")
        for _ in range(3):
            m.update(k, False, "removing stakes helps")
        m.flush()
        m2 = ResearchMemory(d)
        self.assertLess(m2.credence(k), 0.3)
        mon = DriftMonitor("goal", [], m2, OfflineLLM())
        idea = {"change": "stakes=removed", "assumptions": [k], "hypothesis": "goal"}
        self.assertFalse(mon.gate_proposal(1, idea))
        self.assertEqual(mon.events[0].kind, "refuted_assumption")

    def test_loop_never_accepts_invalid_with_drift_control(self):
        taste = TasteProfile("risky", {"risk": 2.0, "validity_care": -2.0})
        rep = Researcher(get_task("eval_awareness"), OfflineLLM(), ResearchMemory(None), taste,
                         LoopConfig(iterations=10)).run()
        self.assertEqual(rep.invalid_accepted, 0)
        self.assertGreaterEqual(rep.best_metrics["validity"], 0.7)

    def test_budget_stops_loop(self):
        llm = OfflineLLM(Budget(max_calls=20))
        rep = Researcher(get_task("eval_awareness"), llm, ResearchMemory(None), None,
                         LoopConfig(iterations=50)).run()
        self.assertLess(len(rep.history), 10)


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_runs(self):
        judge = TasteProfile("j", {"realism": 1.0})
        res = run_benchmark(["eval_awareness"], [0], judge, judge, iterations=3, samples=2,
                            conditions=["full", "naive"])
        self.assertIn("full", res["summary"])
        self.assertIsNone(decision_alignment([], judge))

    def test_extract_json(self):
        self.assertEqual(extract_json('blah {"a": 1} tail'), {"a": 1})
        self.assertEqual(extract_json('x [{"a": 1}, {"b": 2}] y'), [{"a": 1}, {"b": 2}])


if __name__ == "__main__":
    unittest.main()
