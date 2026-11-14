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
                if prompt.startswith(("Below is an interaction", "Below is a transcript", "Here is a conversation")):
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
        self.assertTrue(all(abs(x.self_report - 0.2) < 1e-9 and x.validity == 0.9 for x in samples))
        self.assertTrue(all(x.discriminated in (0.0, 1.0) for x in samples))
        self.assertEqual(s.budget.calls, 4 * 7)  # generate, target, 3 probe questions, judge, discriminator


if __name__ == "__main__":
    unittest.main()


class V2ExtensionTests(unittest.TestCase):
    def test_faithfulness_offline_shows_eval_sensitivity(self):
        from autoresearch.research.measure import SYCOPHANCY_CODE
        m = Measurer(offline_models(), scenario=SYCOPHANCY_CODE, simulator=OfflineWorld())
        f = m.faithfulness([], list(range(200)))
        self.assertEqual(f["misbehavior"], "caves|hedges")
        self.assertGreater(f["rate_plain"], f["rate_eval_notice"])

    def test_setting_gate_refuses_drift(self):
        class Gate(LLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                return json.dumps([{"index": 0, "keep": True}, {"index": 1, "keep": False, "why": "gives it a repo"}])
        p = Proposer(OfflineLLM(), None, random.Random(0), gate_llm=Gate())
        kept = p.setting_gate(LIBRARY[:2], "analytics assistant")
        self.assertEqual(kept, LIBRARY[:1])
        self.assertEqual(p.gated[0]["why"], "gives it a repo")

    def test_topic_matched_corpus(self):
        from autoresearch.research.corpus import load_corpus
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "c.jsonl"), "w") as f:
            for i in range(20):
                f.write(json.dumps({"text": f"my python function {i} throws an error when I call it twice"}) + "\n")
            for i in range(20):
                f.write(json.dumps({"text": f"write a poem about autumn leaves and rain number {i}"}) + "\n")
        self.assertEqual(len(load_corpus(d, keywords=r"\bpython\b")), 20)
        self.assertEqual(len(load_corpus(d, keywords=r"\bpython\b", min_matched=50)), 40)

    def test_report_includes_faithfulness(self):
        from autoresearch.research.measure import SYCOPHANCY_CODE
        m = Measurer(offline_models(), scenario=SYCOPHANCY_CODE, simulator=OfflineWorld())
        rep = OpenResearcher(m, Proposer(OfflineLLM(), None, random.Random(0)), ResearchMemory(None), None,
                             ResearchConfig(iterations=2, faithfulness_samples=6),
                             scenario=SYCOPHANCY_CODE).run()
        self.assertEqual(rep["faithfulness"]["best"]["n"], 6)
        self.assertIn("Faithfulness check", open(write_report(rep, tempfile.mkdtemp())).read())


class ScorerTests(unittest.TestCase):
    def test_auroc_and_kappa(self):
        from autoresearch.research.stats import auroc, cohen_kappa
        self.assertEqual(auroc([0.9, 0.8], [0.1, 0.2]), 1.0)
        self.assertEqual(auroc([0.5], [0.5]), 0.5)
        self.assertAlmostEqual(cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)
        with self.assertRaises(ValueError):
            cohen_kappa([1], [])

    def _script(self, judge_reply):
        class Script(LLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                self.budget.charge(1, 1)
                if prompt.startswith(("You write the opening", "You rewrite")):
                    return json.dumps({"system": "You are Atlas.", "user": "hey can u pull Q3 churn"})
                if prompt.startswith(("Below is", "Here is a conversation")):
                    return '{"p": 0.3}'
                if prompt.startswith("You audit"):
                    return judge_reply
                if prompt.startswith("You check whether"):
                    return '{"faithful": 0.4}'
                return "Here are the numbers."
        return Script(Budget())

    def test_unparseable_judge_is_error_not_half(self):
        s = self._script("I cannot answer that.")
        sample = Measurer(Models(s, s, s)).measure(["x"], [1])[0]
        self.assertEqual(sample.behavior, "error")
        self.assertIn("judge", sample.error)

    def test_validity_is_min_of_parts_and_faithfulness(self):
        from autoresearch.research.benchmarks import item_to_scenario
        s = self._script('{"verbalized": 0, "opportunity": 0.9, "bait_reached": 0.8, "scorable": 0.95, "behavior": "honest"}')
        sc = item_to_scenario({"id": "a1", "system": "Eval system", "user": "TEST: report the metric"})
        ms = Measurer(Models(s, s, s), scenario=sc)
        self.assertEqual(ms.generate([], random.Random(0))["user"], "TEST: report the metric")  # baseline = original
        x = ms.measure(["Frame as internal tool"], [1])[0]
        self.assertEqual((x.bait_reached, x.faithful), (0.8, 0.4))
        self.assertEqual(x.validity, 0.4)

    def test_final_mode_uses_heldout_and_reports_auroc(self):
        m = Models(OfflineLLM(), OfflineLLM(), OfflineLLM(), heldout_target=OfflineLLM(), heldout_judges=[OfflineLLM()])
        ms = Measurer(m, simulator=OfflineWorld(), mode="final")
        rep = OpenResearcher(ms, Proposer(OfflineLLM(), None, random.Random(0)), ResearchMemory(None), None,
                             ResearchConfig(iterations=2, realism_samples=30)).run()
        self.assertEqual(rep["mode"], "final")
        ra = rep["realism_auroc"]["baseline"]
        self.assertIn("target", ra)
        self.assertEqual(len(ra), 2)  # target + one held-out judge
        self.assertGreater(ra["target"]["auroc"], 0.5)  # simulated baseline is detectable
        self.assertIn("Realism AUROC", open(write_report(rep, tempfile.mkdtemp())).read())
        with self.assertRaises(ValueError):
            Measurer(m, mode="prod")

    def test_benchmark_loader_and_split(self):
        from autoresearch.research.benchmarks import load_items, split
        d = tempfile.mkdtemp()
        path = os.path.join(d, "items.jsonl")
        with open(path, "w") as f:
            for i in range(50):
                f.write(json.dumps({"id": f"i{i}", "input": f"task {i}"}) + "\n")
        items = load_items(path)
        dev, held = split(items)
        self.assertEqual(len(dev) + len(held), 50)
        self.assertEqual(split(list(reversed(items)))[1][0].source_id in {h.source_id for h in held}, True)
        with open(path, "a") as f:
            f.write(json.dumps({"id": "bad"}) + "\n")
        with self.assertRaises(ValueError):
            load_items(path)

    def test_openai_compat_parses_reasoning(self):
        from autoresearch.llm import parse_openai_chat
        r, t, i, o = parse_openai_chat({"choices": [{"message": {"reasoning_content": "this looks like a test",
                                        "content": "ok"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 7}})
        self.assertEqual((r, t, i, o), ("this looks like a test", "ok", 5, 7))
