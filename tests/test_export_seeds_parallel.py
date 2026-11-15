"""export_design rewrites the split's seeds concurrently, keeping seed order and per-seed failures."""
import threading
import time
import unittest

from autoresearch.research.export_seeds import export_design
from autoresearch.research.petri_measure import PetriMeasurer
from tests.test_petri_measure import SEEDS, Scripted, models

FOUR = [dict(s, seed_id=f"{s['seed_id']}_{i}") for i in range(2) for s in SEEDS]
REPORT = {"run_id": "r", "arm": "R1", "best_design": [{"text": "keep shell output terse"}]}


class SlowGen(Scripted):
    def __init__(self, fail_on=None):
        super().__init__("claude-gen")
        self.active, self.max_active, self.fail_on = 0, 0, fail_on
        self.lock = threading.Lock()

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        if "rewrite a Petri audit seed" in prompt:
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.05)
            with self.lock:
                self.active -= 1
            if self.fail_on and self.fail_on in prompt:
                raise RuntimeError("boom")
        return super().complete(prompt, system, max_tokens, temperature)


class ExportParallelTest(unittest.TestCase):
    def measurer(self, gen):
        m, _, _, _ = models()
        m.generator = gen
        return PetriMeasurer(m, FOUR, runner=lambda s: [])

    def test_rewrites_overlap_and_rows_keep_seed_order(self):
        gen = SlowGen()
        rows, failures = export_design(REPORT, self.measurer(gen), FOUR, "taste_real")
        self.assertGreaterEqual(gen.max_active, 2)
        self.assertEqual(failures, [])
        self.assertEqual([r["seed_id"] for r in rows], [f"{s['seed_id']}@taste_real" for s in FOUR])
        self.assertTrue(all(r["text"] == "Rewritten seed text." and r["faithful"] == 0.7 for r in rows))

    def test_a_failed_rewrite_is_reported_and_the_others_still_export(self):
        gen = SlowGen(fail_on="deletes audit logs")   # the two dev_seed_17 copies
        rows, failures = export_design(REPORT, self.measurer(gen), FOUR, "taste_real")
        self.assertEqual([r["base_seed_id"] for r in rows], ["dev_seed_48_0", "dev_seed_48_1"])
        self.assertEqual(sorted(f["seed_id"] for f in failures), ["dev_seed_17_0", "dev_seed_17_1"])
        self.assertTrue(all("seed rewrite failed" in f["error"] for f in failures))


if __name__ == "__main__":
    unittest.main()
