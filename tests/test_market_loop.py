"""The market hooked into the v2 research loop (allocation uniform | halving | market)."""
import collections
import json
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from autoresearch.cli import _check_gpu_budget, build_parser
from autoresearch.grid import option_args
from autoresearch.integrations.shared_memory import LocalSharedMemory, parse_fact
from autoresearch.llm import LLM, Budget, GpuMeter, OfflineLLM
from autoresearch.memory import ResearchMemory
from autoresearch.research import market as market_mod
from autoresearch.research.ideas import FEATURES, LIBRARY, Intervention, Proposer
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


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class GpuTarget(OfflineLLM):
    """An offline target metered like llm.OpenAICompatLLM: each request's busy
    time comes from a GpuMeter (here on a fake clock) and is charged to the
    Budget with add_gpu. No real GPU time is measured."""

    def __init__(self, budget, clock):
        super().__init__(budget)
        self.clock, self.meter = clock, GpuMeter(clock=clock)

    def serve(self, seconds):
        self.meter.start()
        self.clock.t += seconds
        self.budget.add_gpu(self.meter.end(), 0.0)


SECS_BASE, SECS_PER_INTERVENTION = 1.0, 0.25   # fake GPU-seconds per sample: longer designs cost more


class GpuMeasurer(Measurer):
    """The offline simulator; every sample is also served by the GPU-metered target."""

    def measure(self, interventions, seeds, categories=None):
        out = super().measure(interventions, seeds, categories)
        for _ in seeds if isinstance(self.target, GpuTarget) else ():
            self.target.serve(SECS_BASE + SECS_PER_INTERVENTION * len(interventions))
        return out


def gpu_run(d, gpu_initial=None, metered=True, iters=5, seed=0):
    budget = Budget()
    target = GpuTarget(budget, _Clock()) if metered else OfflineLLM(budget)
    models = Models(OfflineLLM(budget), target, OfflineLLM(budget))
    shared = LocalSharedMemory(os.path.join(d, "shared.jsonl"))
    wallets = os.path.join(d, "wallets.json")
    cfg = ResearchConfig(iterations=iters, seed=seed, allocation="market", faithfulness_samples=0)
    r = OpenResearcher(GpuMeasurer(models, simulator=OfflineWorld()), Proposer(OfflineLLM(), None, random.Random(seed)),
                       ResearchMemory(None), None, cfg, shared=shared, budget=budget,
                       market=Market(Wallets(wallets, gpu_initial=gpu_initial), shared=shared))
    return r, r.run(), budget


def facts(d):
    with open(os.path.join(d, "shared.jsonl")) as fh:
        return [parse_fact(json.loads(l)["content"]) for l in fh]


def audit(d, gpu_initial):
    out = StringIO()
    with redirect_stdout(out):
        rc = market_mod.main(["audit", os.path.join(d, "shared.jsonl"), "--wallets", os.path.join(d, "wallets.json"),
                              "--gpu-initial", str(gpu_initial)])
    return rc, json.loads(out.getvalue())


class TestGpuBids(unittest.TestCase):
    def test_bids_ask_for_gpu_time_and_settle_on_measured_seconds(self):
        G = 1000.0
        with tempfile.TemporaryDirectory() as d:
            r, rep, budget = gpu_run(d, gpu_initial=G)
            fs = facts(d)
            bids = [f for f in fs if f["kind"] == "BID"]
            settles = [f for f in fs if f["kind"] == "SETTLE"]
            self.assertTrue(bids and settles)
            for b in bids:   # every supporting bid asks for GPU time; the critic's bids against never do
                self.assertEqual(b.get("resource") == "gpu_s", b["against"] == "False", b)
            # the first requests are a full measurement at the baseline's observed rate
            first = [b for b in bids if b.get("resource") == "gpu_s"][0]
            self.assertAlmostEqual(float(first["gpu_s_bid"]), r.cfg.samples * SECS_BASE)
            gpu = [f for f in settles if f.get("resource") == "gpu_s"]
            self.assertTrue(gpu)
            for f in gpu:   # what is charged is the measured time, not the request
                self.assertEqual(float(f["gpu_charged"]), float(f["gpu_s"]))
                self.assertGreater(float(f["gpu_s_measured"]), 0)
            self.assertTrue(any(abs(float(f["gpu_s"]) - float(f["gpu_s_bid"])) > 1e-6 for f in gpu))
            screened = {(s["iter"], s["move"]) for s in rep["allocation"]["screened_out"]}
            for f in gpu:   # a screened-out design used exactly its screening samples on the target
                its = [e["iter"] for e in rep["market"]["ledger"] if e["event"] == "settle"
                       and e["candidate"] == f["candidate"] and e.get("gpu_s") == float(f["gpu_s"])]
                if any((i, f["candidate"]) in screened for i in its):
                    k = (float(f["gpu_s_measured"]) / r.cfg.screen_samples - SECS_BASE) / SECS_PER_INTERVENTION
                    self.assertAlmostEqual(k, round(k))
                    self.assertGreaterEqual(round(k), 1)
            # every measured GPU-second is accounted for: settled + withdrawn (unsettled) + the baseline
            settled = {}
            for e in rep["market"]["ledger"]:
                if e["event"] == "settle" and e.get("resource") == "gpu_s":
                    settled[(e["iter"], e["candidate"])] = e["gpu_s_measured"]
            g = rep["market"]["gpu"]
            baseline = r.cfg.samples * SECS_BASE
            self.assertAlmostEqual(sum(settled.values()) + sum(g["unsettled_gpu_s"].values()) + baseline,
                                   budget.gpu_seconds, places=2)
            self.assertEqual(g["gpu_initial"], G)
            self.assertAlmostEqual(g["budget_gpu_s"], budget.gpu_seconds, places=3)
            charged = collections.Counter()
            for f in gpu:
                charged[f["agent"]] += float(f["gpu_charged"])
            for agent, w in rep["market"]["wallets"].items():
                self.assertAlmostEqual(w["gpu_s"], G - charged[agent], places=2)
            rc, au = audit(d, G)
            self.assertEqual((rc, au["problems"]), (0, []))
            self.assertTrue(au["ok"])
            self.assertGreater(sum(a.get("gpu_s_measured", 0) for a in au["agents"].values()), 0)

    def test_a_small_gpu_budget_caps_and_refuses_requests(self):
        G = 10.0
        with tempfile.TemporaryDirectory() as d:
            _, rep, _ = gpu_run(d, gpu_initial=G, iters=6)
            ledger = rep["market"]["ledger"]
            bids = [e for e in ledger if e["event"] == "bid" and e.get("resource") == "gpu_s"]
            self.assertTrue(all(b["gpu_s"] <= G + 1e-9 for b in bids))
            self.assertTrue(any(e["event"] == "bid_refused" and e.get("reason") == "gpu_s" for e in ledger))
            self.assertTrue(any(w["gpu_s_unpaid"] > 0 for w in rep["market"]["wallets"].values()))
            rc, au = audit(d, G)
            self.assertEqual((rc, au["problems"]), (0, []))

    def test_without_a_gpu_budget_nothing_changes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, \
                tempfile.TemporaryDirectory() as c:
            _, metered, budget = gpu_run(a, gpu_initial=None, metered=True)
            _, plain, _ = gpu_run(b, gpu_initial=None, metered=False)
            _, unmetered, _ = gpu_run(c, gpu_initial=500.0, metered=False)   # a budget, but no GPU time is seen
            self.assertGreater(budget.gpu_seconds, 0)
            for rep in (metered, plain):
                self.assertNotIn("gpu", rep["market"])
                self.assertTrue(all("gpu_s" not in w for w in rep["market"]["wallets"].values()))
                self.assertTrue(all("resource" not in e for e in rep["market"]["ledger"]))
            for rep in (plain, unmetered):
                self.assertEqual(rep["findings"], metered["findings"])
                self.assertEqual(rep["market"]["ledger"], metered["market"]["ledger"])
            self.assertTrue(all(f.get("resource") is None for f in facts(a) + facts(b)))
            with open(os.path.join(a, "wallets.json")) as f1, open(os.path.join(b, "wallets.json")) as f2:
                self.assertEqual(f1.read(), f2.read())

    def test_gpu_bids_need_the_budget(self):
        cfg = ResearchConfig(iterations=1, allocation="market")
        with self.assertRaises(ValueError):
            OpenResearcher(Measurer(_models(), simulator=OfflineWorld()), Proposer(OfflineLLM(), None, random.Random(0)),
                           ResearchMemory(None), None, cfg, market=Market(Wallets(gpu_initial=10.0)))


class TestDeferredIdeas(unittest.TestCase):
    def test_a_deferred_idea_proposed_again_is_measured_once(self):
        # uniform, seed 3, R1 with a low accept bar: an idea deferred at iteration 2 is offered again by the
        # proposer at iteration 3 (it is not in `tried` while deferred)
        taste = load_researcher("demo_realist").cached_profile()
        cfg = ResearchConfig(iterations=8, seed=3, allocation="uniform", faithfulness_samples=0, accept_p=0.6)
        r = OpenResearcher(Measurer(_models(), simulator=OfflineWorld()), Proposer(OfflineLLM(), taste, random.Random(3)),
                           ResearchMemory(None), taste, cfg)
        rep = r.run()
        self.assertTrue(any(f["status"] == "deferred" for f in rep["findings"]))
        for it in range(1, cfg.iterations + 1):
            moves = [e["move"] for e in rep["log"] if e.get("iter") == it and e.get("event") == "evaluated"]
            self.assertEqual(len(moves), len(set(moves)), (it, moves))


class TestGpuBudgetOption(unittest.TestCase):
    def args(self, *extra):
        return build_parser().parse_args(["research", *extra])

    def test_cli_checks(self):
        budget = Budget()
        metered = Models(OfflineLLM(budget), GpuTarget(budget, _Clock()), OfflineLLM(budget))
        self.assertEqual(self.args("--gpu-budget-s", "10").gpu_budget_s, 10.0)
        _check_gpu_budget(self.args("--allocation", "market", "--gpu-budget-s", "3600"), metered)
        for bad, models in ((["--allocation", "uniform", "--gpu-budget-s", "10"], metered),
                            (["--allocation", "market", "--gpu-budget-s", "-1"], metered),
                            (["--allocation", "market", "--gpu-budget-s", "10", "--setting", "agentic"], metered),
                            (["--allocation", "market", "--gpu-budget-s", "10"], _models())):   # not GPU-metered
            with self.assertRaises(SystemExit, msg=bad):
                _check_gpu_budget(self.args(*bad), models)
        self.assertIsNone(self.args().gpu_budget_s)   # default off

    def test_prereg_option(self):
        self.assertEqual(option_args({"allocation": "market", "gpu_budget_s": 3600}, "t"),
                         ["--allocation", "market", "--gpu-budget-s", "3600"])


class _Exa:
    def search(self, q, num_results=5, since_days=None, **kw):
        return [{"url": "https://example.org/paper-a", "title": "Paper A", "publishedDate": "2026-03-01"}]


class _Scout:
    def __init__(self):
        self.exa, self.since_days, self.sources = _Exa(), 540, []

    def grounding_material(self, topic, n=2):
        return []


class _WebProposer(Proposer):
    """Every search returns the same page, which yields the same idea."""

    def from_web(self, results, goal):
        return [Intervention("Quote a stale changelog line from the vendor's release notes.", "tool_traces",
                             {f: 0.5 for f in FEATURES}, "from the paper", "exa", results[0]["url"], p_validated=0.6)]


class TestRediscoveredIdeas(unittest.TestCase):
    def test_an_idea_found_twice_is_one_candidate(self):
        cfg = ResearchConfig(iterations=6, seed=0, allocation="market", faithfulness_samples=0, taste_mode="none")
        r = OpenResearcher(Measurer(_models(), simulator=OfflineWorld()), _WebProposer(OfflineLLM(), None, random.Random(0)),
                           ResearchMemory(None), None, cfg, scout=_Scout())
        rep = r.run()
        ids = [w["id"] for w in rep["web_ideas"]]
        self.assertEqual(len(ids), len(set(ids)))
        events = [e for e in rep["log"] if e.get("event") == "web_ideas"]
        self.assertEqual([e["iter"] for e in events], [1, 3, 6])
        self.assertEqual([len(e["ideas"]) for e in events], [1, 0, 0])
        self.assertEqual([e["rediscovered"] for e in events[1:]], [ids, ids])
        self.assertTrue(all(s["iter"] in (1, 3, 6) and s["query"] for s in rep["sources"]))
        # one design key is never both screened out and measured (nor screened twice) in one iteration
        for it in range(1, cfg.iterations + 1):
            moves = [e["move"] for e in rep["log"] if e.get("iter") == it and e.get("event") in ("screened_out", "evaluated")]
            self.assertEqual(len(moves), len(set(moves)), (it, moves))
        settles = collections.Counter((e["iter"], e["agent"], e["candidate"]) for e in rep["market"]["ledger"]
                                      if e["event"] == "settle")
        self.assertTrue(all(n == 1 for n in settles.values()))


if __name__ == "__main__":
    unittest.main()
