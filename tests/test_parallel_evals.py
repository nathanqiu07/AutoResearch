"""Parallel candidate measurement (ResearchConfig.parallel_evals) and concurrent seed rewrites in PetriMeasurer:
same sample ids and same results as the sequential path, only wall time changes."""
import random
import threading
import time
import unittest

from autoresearch.llm import OfflineLLM
from autoresearch.memory import ResearchMemory
from autoresearch.research.ideas import Proposer
from autoresearch.research.loop import OpenResearcher, ResearchConfig
from autoresearch.research.measure import Measurer, Models, OfflineWorld
from autoresearch.research.petri_measure import PetriMeasurer
from tests.test_petri_measure import RESULT, SEEDS, Scripted, models, runner_from


class RecordingMeasurer(Measurer):
    """Offline measurer that records which sample ids each call got and how many calls overlapped."""

    def __init__(self, delay=0.0):
        super().__init__(Models(OfflineLLM(), OfflineLLM(), OfflineLLM()), simulator=OfflineWorld())
        self.delay, self.calls, self.active, self.max_active = delay, [], 0, 0
        self.lock = threading.Lock()

    def measure(self, interventions, seeds, categories=None):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.calls.append((tuple(interventions), tuple(seeds)))
        try:
            time.sleep(self.delay)
            return super().measure(interventions, seeds, categories)
        finally:
            with self.lock:
                self.active -= 1


def run_loop(parallel, delay=0.0):
    m = RecordingMeasurer(delay)
    cfg = ResearchConfig(iterations=3, samples=3, evals_per_iter=3, seed=4, parallel_evals=parallel,
                         use_web=False, explain=False, claims=False)
    rep = OpenResearcher(m, Proposer(OfflineLLM(), None, random.Random(cfg.seed)), ResearchMemory(None),
                         None, cfg).run()
    return m, rep


class ParallelEvalsTest(unittest.TestCase):
    def test_parallel_and_sequential_measure_the_same_designs_on_the_same_sample_ids(self):
        seq, seq_rep = run_loop(False)
        par, par_rep = run_loop(True)
        self.assertEqual(sorted(seq.calls), sorted(par.calls))
        self.assertEqual(seq_rep["compute"], par_rep["compute"])
        self.assertEqual(seq_rep["best_design"], par_rep["best_design"])

    def test_candidates_of_one_iteration_are_measured_concurrently(self):
        par, _ = run_loop(True, delay=0.05)
        self.assertGreaterEqual(par.max_active, 2)
        seq, _ = run_loop(False, delay=0.0)
        self.assertEqual(seq.max_active, 1)


class ConcurrentRewriteTest(unittest.TestCase):
    def test_seed_rewrites_overlap_and_keep_sample_order(self):
        state = {"active": 0, "max": 0}
        lock = threading.Lock()

        class Slow(Scripted):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                if "rewrite a Petri audit seed" in prompt:
                    with lock:
                        state["active"] += 1
                        state["max"] = max(state["max"], state["active"])
                    time.sleep(0.05)
                    with lock:
                        state["active"] -= 1
                return super().complete(prompt, system, max_tokens, temperature)
        m, _, _, _ = models()
        m.generator = Slow("claude-gen")
        run = runner_from({"dev_seed_48": RESULT, "dev_seed_17": RESULT})
        out = PetriMeasurer(m, SEEDS, runner=run, workers=4).measure(["x"], [0, 1, 2, 3])
        self.assertGreaterEqual(state["max"], 2)
        self.assertEqual([a["seed_id"] for a in run.calls[0]],
                         ["dev_seed_48@s0", "dev_seed_17@s1", "dev_seed_48@s2", "dev_seed_17@s3"])
        self.assertEqual(len(out), 4)


if __name__ == "__main__":
    unittest.main()
