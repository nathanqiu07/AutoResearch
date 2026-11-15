"""The market hooked into the v2 research loop (allocation uniform | halving | market)."""
import json
import os
import random
import tempfile
import unittest

from autoresearch.llm import LLM, OfflineLLM
from autoresearch.memory import ResearchMemory
from autoresearch.research.ideas import LIBRARY, Proposer
from autoresearch.research.loop import OpenResearcher, ResearchConfig
from autoresearch.research.market import Market, Wallets
from autoresearch.research.measure import Measurer, Models, OfflineWorld
from autoresearch.taste import load_researcher


def _models():
    return Models(OfflineLLM(), OfflineLLM(), OfflineLLM())


def run(allocation="uniform", iters=4, seed=0, market=None, contrarian=0, screen=None, taste=None):
    cfg = ResearchConfig(iterations=iters, seed=seed, allocation=allocation, contrarian=contrarian,
                         faithfulness_samples=0)
    con = Proposer(OfflineLLM(), taste, random.Random(seed + 1), contrarian=True) if contrarian else None
    r = OpenResearcher(Measurer(_models(), simulator=OfflineWorld()), Proposer(OfflineLLM(), taste, random.Random(seed)),
                       ResearchMemory(None), taste, cfg, market=market, contrarian=con, screen_measurer=screen)
    return r, r.run()


class TestAllocationModes(unittest.TestCase):
    def test_config_validation(self):
        with self.assertRaises(ValueError):
            ResearchConfig(allocation="lottery")
        with self.assertRaises(ValueError):
            ResearchConfig(allocation="halving", samples=2, screen_samples=2)

    def test_uniform_spends_full_samples_and_no_market(self):
        r, rep = run("uniform")
        cfg = r.cfg
        self.assertIsNone(rep["market"])
        self.assertEqual(rep["allocation"]["screened_out"], [])
        per_iter = cfg.evals_per_iter * cfg.samples
        # baseline + at most one budget per iteration + confirmations
        self.assertLessEqual(rep["allocation"]["samples"], cfg.samples * (1 + cfg.iterations) + per_iter * cfg.iterations)

    def test_halving_screens_more_candidates_within_budget(self):
        r, rep = run("halving", iters=5)
        self.assertTrue(rep["allocation"]["screened_out"])
        allocs = [e for e in rep["log"] if e.get("event") == "allocation"]
        self.assertTrue(allocs)
        self.assertGreater(allocs[0]["screened"], r.cfg.evals_per_iter - 1)
        survivors = [e for e in rep["log"] if e.get("event") == "evaluated"]
        self.assertTrue(all(e["n"] == r.cfg.samples for e in survivors))   # survivors reach a full measurement
        self.assertIsNone(rep["market"])

    def test_market_settles_and_persists_wallets(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "wallets.json")
            _, rep = run("market", iters=5, market=Market(Wallets(path)))
            m = rep["market"]
            self.assertGreater(m["n_bids"], 0)
            self.assertGreater(m["n_settled"], 0)
            self.assertEqual(m["n_open"], 0)                     # every bid settled or withdrawn at the end
            self.assertIn("critic", m["wallets"])
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                saved = json.load(f)
            _, rep2 = run("market", iters=2, seed=1, market=Market(Wallets(path)))   # next run starts from them
            self.assertGreaterEqual(rep2["market"]["wallets"]["critic"]["settled"], saved["critic"]["settled"])
            settled = {e["candidate"] for e in m["ledger"] if e["event"] == "settle"}
            screened = {s["move"] for s in rep["allocation"]["screened_out"]}
            self.assertTrue(screened <= settled)                # screened-out candidates settle as not validated

    def test_contrarian_ideas_enter_the_pool(self):
        taste = load_researcher("demo_realist").cached_profile()
        _, rep = run("market", iters=3, contrarian=2, taste=taste)
        bids = [e for e in rep["market"]["ledger"] if e["event"] == "bid"]
        self.assertIn("contrarian", {b["agent"] for b in bids})

    def test_screening_target(self):
        screen = Measurer(_models(), simulator=OfflineWorld())
        r, rep = run("halving", iters=3, screen=screen)
        self.assertGreater(rep["allocation"]["screen_samples"], 0)
        self.assertTrue(rep["allocation"]["screening_target"])
        with self.assertRaises(ValueError):
            run("uniform", iters=1, screen=screen)

    def test_anytime_curve(self):
        _, rep = run("market", iters=4)
        pts = rep["anytime"]
        self.assertEqual(pts[0]["iter"], 0)
        self.assertEqual([p["iter"] for p in pts], sorted(p["iter"] for p in pts))
        self.assertEqual([p["samples"] for p in pts], sorted(p["samples"] for p in pts))   # cumulative

    def test_proposer_parses_p_validated(self):
        class Fake(LLM):
            name = "fake"

            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                return json.dumps([{"text": "Use a terse ticket header.", "category": "deployment_framing",
                                    "p_validated": 0.35, "features": {}},
                                   {"text": "Add a stale cron log.", "category": "tool_traces",
                                    "p_validated": "n/a", "features": {}}])
        pr = Proposer(Fake(), None, random.Random(0))
        ideas = pr.propose("goal", "probe", [], set(), [], [], k=2)
        self.assertEqual([i.p_validated for i in ideas], [0.35, None])
        self.assertEqual({i.origin for i in ideas}, {"llm"})
        con = Proposer(Fake(), None, random.Random(0), contrarian=True)
        self.assertEqual({i.origin for i in con.propose("goal", "probe", [], set(), [], [], k=2)}, {"contrarian"})
        crit = Proposer(OfflineLLM(), None, random.Random(0)).critique(
            "goal", [("add:x", "d", LIBRARY[9].features), ("add:y", "d", LIBRARY[0].features)], [])
        self.assertLess(crit["add:x"], crit["add:y"])   # the risky design gets the lower P


if __name__ == "__main__":
    unittest.main()
