import json
import math
import os
import random
import tempfile
import unittest

from unittest import mock

from autoresearch.integrations.shared_memory import LocalSharedMemory, parse_fact
from autoresearch.llm import Budget, GpuMeter
from autoresearch.research import market as market_mod
from autoresearch.research.market import (P_FLOOR, Bid, GpuUsage, Market, Wallets, audit_ledger, gpu_s_to_usd,
                                          halving_plan, ledger_facts, log_score_payoff, usd_per_gpu_hour,
                                          usd_to_gpu_s)


def _simulate(bias: float, n: int = 4000, seed: int = 0) -> float:
    """Mean payoff per unit stake of an agent that reports true P + bias."""
    rng = random.Random(seed)
    tot = 0.0
    for _ in range(n):
        q = rng.uniform(0.1, 0.9)
        outcome = rng.random() < q
        tot += log_score_payoff(min(1.0, max(0.0, q + bias)), outcome, 1.0)
    return tot / n


class TestBidAndPayoff(unittest.TestCase):
    def test_bid_clips_and_validates(self):
        self.assertAlmostEqual(Bid("a", "c", 1.0).p_validated, 1 - P_FLOOR)
        self.assertAlmostEqual(Bid("a", "c", 0.0).p_validated, P_FLOOR)
        with self.assertRaises(ValueError):
            Bid("a", "c", 1.5)
        with self.assertRaises(ValueError):
            Bid("a", "c", 0.5, stake=-1)

    def test_payoff_sign(self):
        self.assertGreater(log_score_payoff(0.8, True, 1), 0)
        self.assertLess(log_score_payoff(0.8, False, 1), 0)
        self.assertAlmostEqual(log_score_payoff(0.5, True, 3), 0.0)
        self.assertAlmostEqual(log_score_payoff(0.8, True, 2), 2 * math.log(1.6))

    def test_honest_bidding_earns_most_in_expectation(self):
        honest = _simulate(0.0)
        for bias in (-0.3, -0.15, 0.15, 0.3):
            self.assertGreater(honest, _simulate(bias), f"bias {bias}")


class TestHalvingPlan(unittest.TestCase):
    def test_fits_budget(self):
        for n_av, budget, full, screen in [(6, 12, 6, 2), (10, 24, 6, 2), (3, 6, 6, 2), (8, 40, 8, 2)]:
            n, keep = halving_plan(n_av, budget, full, screen)
            self.assertLessEqual(n, n_av)
            self.assertEqual(keep, max(1, n // 2))
            cost = n * screen + keep * (full - screen)
            self.assertTrue(cost <= budget or n == 1, (n_av, budget, n, cost))

    def test_default_budget_screens_more_than_uniform(self):
        n, keep = halving_plan(6, budget=12, full=6, screen=2)   # uniform measures 2 with this budget
        self.assertEqual((n, keep), (3, 1))

    def test_cheap_screening_target(self):
        n, keep = halving_plan(10, budget=12, full=6, screen=2, merged=False, screen_cost=0.25)
        # survivors get 6 fresh dev samples each: 3 * 2 * 0.25 + 1 * 6 = 7.5 fits, 4 candidates (2 kept) = 14 does not
        self.assertEqual((n, keep), (3, 1))

    def test_none_available(self):
        self.assertEqual(halving_plan(0, 12, 6), (0, 0))


class TestMarket(unittest.TestCase):
    def test_priority_and_critic(self):
        m = Market()
        m.bid("proposer", "x", 0.8)
        m.bid("proposer", "y", 0.6)
        m.bid("critic", "x", 0.1, against=True)
        self.assertLess(m.consensus("x"), 0.8)
        m.bid("critic", "z", 0.9, against=True)
        self.assertEqual(m.priority("z"), 0.0)           # a critic alone never funds a candidate
        self.assertEqual(m.order(["x", "y", "z"]), ["y", "x"])

    def test_one_open_bid_per_agent_and_candidate(self):
        m = Market()
        a = m.bid("p", "x", 0.7)
        b = m.bid("p", "x", 0.2)
        self.assertIs(a, b)
        self.assertEqual(len(m.bids_on("x")), 1)

    def test_settle_updates_wallets_and_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "wallets.json")
            m = Market(Wallets(path))
            m.bid("good", "x", 0.9)
            m.bid("bad", "x", 0.1)
            ch = m.settle({"x": True}, it=1)
            self.assertGreater(ch["good"], 0)
            self.assertLess(ch["bad"], 0)
            self.assertEqual(m.open, {})
            saved = json.load(open(path))
            self.assertGreater(saved["good"]["balance"], saved["bad"]["balance"])
            self.assertEqual(Wallets(path).balance("good"), saved["good"]["balance"])   # persists across runs
            rep = m.report()
            self.assertEqual(rep["n_settled"], 2)
            self.assertIsNotNone(rep["brier"])

    def test_withdraw_keeps_deferred(self):
        m = Market()
        m.bid("p", "x", 0.5)
        m.bid("p", "y", 0.5)
        self.assertEqual(m.withdraw(keep=["y"]), 1)
        self.assertEqual([c for _, c in m.open], ["y"])

    def test_allocate_screens_in_priority_order(self):
        m = Market()
        bids = [Bid("p", c, p, stake=1.0) for c, p in (("a", 0.2), ("b", 0.9), ("c", 0.6), ("d", 0.4))]
        alloc = m.allocate(bids, budget_samples=12, full=6, screen=2)
        self.assertEqual(list(alloc), ["b", "c", "d"])
        self.assertEqual(set(alloc.values()), {2})

    def test_overclaimer_loses_budget(self):
        """An agent that over-claims is funded first at the start, then its
        stake (its influence on funding) falls below the honest agent's."""
        rng = random.Random(3)
        m = Market(stake_frac=0.2)
        for k in range(300):
            q = rng.uniform(0.1, 0.7)
            m.bid("honest", f"c{k}", q)
            m.bid("overclaimer", f"c{k}", min(1.0, q + 0.35))
            m.settle({f"c{k}": rng.random() < q})
        self.assertGreater(m.wallets.balance("honest"), m.wallets.balance("overclaimer"))
        self.assertGreater(m.stake_for("honest"), m.stake_for("overclaimer"))

    def test_broke_agent_cannot_bid(self):
        m = Market(Wallets(initial=0.1))
        self.assertIsNone(m.bid("p", "x", 0.5))
        self.assertEqual(m.ledger[-1]["event"], "bid_refused")

    def test_facts_written_and_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            sh = LocalSharedMemory(os.path.join(d, "s.jsonl"))
            m = Market(shared=sh, run_id="r1")
            m.bid("scout", "add:abc", 0.7, exp_delta=0.05)
            m.settle({"add:abc": False})
            facts = [parse_fact(r["content"]) for r in sh.recall("x", "BID SETTLE", 10)]
            kinds = sorted(f["kind"] for f in facts if f)
            self.assertEqual(kinds, ["BID", "SETTLE"])
            self.assertEqual(sh.facts("x", "SETTLE", "SETTLE")[0]["outcome"], "False")

    def test_decision_and_label_facts_parse(self):
        from autoresearch.integrations.shared_memory import format_fact
        f = parse_fact("[author=decider] " + format_fact("DECISION", run="r", point="D3", chosen="accept it"))
        self.assertEqual((f["kind"], f["point"], f["chosen"]), ("DECISION", "D3", "accept it"))
        self.assertEqual(parse_fact(format_fact("DISAGREE", run="r", point="D1"))["kind"], "DISAGREE")


def _load(path):
    with open(path) as fh:
        return json.load(fh)


class TestGpuMarket(unittest.TestCase):
    def test_dollar_only_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            sh = LocalSharedMemory(os.path.join(d, "s.jsonl"))
            path = os.path.join(d, "wallets.json")
            m = Market(Wallets(path), shared=sh, run_id="r")
            m.bid("p", "x", 0.7)
            m.settle({"x": True})
            self.assertEqual(set(m.ledger[0]), {"event", "iter", "agent", "candidate_id", "p_validated",
                                                "exp_delta", "stake", "against"})
            self.assertNotIn("resource", m.ledger[1])
            self.assertEqual(set(_load(path)["p"]), {"balance", "settled", "payoff", "log_score"})
            self.assertNotIn("gpu", m.report())
            self.assertTrue(all("resource" not in r["content"] for r in sh.recall("x", "BID SETTLE", 10)))

    def test_dollar_only_ignores_a_bad_rate_env(self):
        with mock.patch.dict(os.environ, {market_mod.RATE_ENV: "not-a-number"}):
            m = Market()
            m.bid("p", "x", 0.6)
            m.settle({"x": False})
            with self.assertRaises(ValueError):
                Market(Wallets(gpu_initial=10)).usd_per_hour

    def test_gpu_bid_needs_budget_and_support(self):
        with self.assertRaises(ValueError):
            Market().bid("p", "x", 0.5, gpu_s=10)
        m = Market(Wallets(gpu_initial=100))
        with self.assertRaises(ValueError):
            m.bid("critic", "x", 0.2, against=True, gpu_s=10)
        with self.assertRaises(ValueError):
            Bid("a", "c", 0.5, resource="gpu_s")          # a GPU bid must ask for some time
        with self.assertRaises(ValueError):
            Bid("a", "c", 0.5, gpu_s=3.0)                 # gpu_s without resource=gpu_s

    def test_request_is_limited_by_balance_and_open_requests(self):
        m = Market(Wallets(gpu_initial=100))
        self.assertIsNotNone(m.bid("p", "x", 0.6, gpu_s=70))
        self.assertIsNone(m.bid("p", "y", 0.6, gpu_s=40))   # 70 already asked for
        self.assertEqual(m.ledger[-1]["event"], "bid_refused")
        self.assertEqual(m.ledger[-1]["reason"], "gpu_s")
        self.assertIsNotNone(m.bid("p", "z", 0.6, gpu_s=30))
        m.withdraw()                                         # released without charge: nothing ran
        self.assertEqual(m.wallets.gpu_balance("p"), 100)
        self.assertIsNotNone(m.bid("p", "y", 0.6, gpu_s=100))

    def test_settlement_charges_measured_time_split_by_request(self):
        with tempfile.TemporaryDirectory() as d:
            sh = LocalSharedMemory(os.path.join(d, "s.jsonl"))
            m = Market(Wallets(os.path.join(d, "w.json"), gpu_initial=500), shared=sh, run_id="r", usd_per_hour=3.6)
            m.bid("a", "x", 0.8, gpu_s=300)
            m.bid("b", "x", 0.4, gpu_s=100)
            m.bid("critic", "x", 0.3, against=True)
            before = {k: m.wallets.balance(k) for k in ("a", "b", "critic")}
            ch = m.settle({"x": True}, gpu_seconds={"x": 40.0})
            self.assertAlmostEqual(m.wallets.gpu_balance("a"), 500 - 30.0)   # 3/4 of the measured 40 s, not the 300 bid
            self.assertAlmostEqual(m.wallets.gpu_balance("b"), 500 - 10.0)
            self.assertEqual(m.wallets.gpu_balance("critic"), 500)           # the critic asked for nothing
            for k in before:                                                  # credits follow the log score as before
                self.assertAlmostEqual(ch[k], m.wallets.balance(k) - before[k])
            settles = [f for f in (parse_fact(r["content"]) for r in sh.recall("x", "SETTLE", 50))
                       if f and f["kind"] == "SETTLE"]
            gpu = {f["agent"]: f for f in settles if f.get("resource") == "gpu_s"}
            self.assertEqual(set(gpu), {"a", "b"})
            self.assertEqual((float(gpu["a"]["gpu_s"]), float(gpu["a"]["gpu_s_measured"])), (30.0, 40.0))
            self.assertAlmostEqual(float(gpu["a"]["usd_equiv"]), 0.03)       # 30 s at $3.6/h
            bids = [f for f in (parse_fact(r["content"]) for r in sh.recall("x", "BID", 50)) if f and f["kind"] == "BID"]
            self.assertEqual({f["agent"]: f.get("resource") for f in bids}, {"a": "gpu_s", "b": "gpu_s", "critic": None})
            rep = m.report()["gpu"]
            self.assertEqual((rep["gpu_s_measured"], rep["n_settled"]), (40.0, 2))
            self.assertAlmostEqual(rep["usd_equiv"], 0.04)
            self.assertEqual(_load(os.path.join(d, "w.json"))["a"]["gpu_s_spent"], 30.0)

    def test_settling_gpu_bids_needs_a_measurement(self):
        m = Market(Wallets(gpu_initial=50))
        m.bid("a", "x", 0.8, gpu_s=10)
        bal = m.wallets.balance("a")
        with self.assertRaises(ValueError):
            m.settle({"x": True})
        self.assertIn(("a", "x"), m.open)                   # nothing was paid
        self.assertEqual(m.wallets.balance("a"), bal)

    def test_overrun_is_recorded_unpaid(self):
        m = Market(Wallets(gpu_initial=20))
        m.bid("a", "x", 0.5, gpu_s=20)
        m.settle({"x": False}, gpu_seconds={"x": 35.0})
        w = m.wallets.summary()["a"]
        self.assertEqual((w["gpu_s"], w["gpu_s_spent"], w["gpu_s_unpaid"]), (0.0, 20.0, 15.0))
        self.assertIsNone(m.bid("a", "y", 0.5, gpu_s=1))     # no GPU time left

    def test_gpu_usage_reads_the_meter_through_the_budget(self):
        t = [0.0]
        meter, budget = GpuMeter(clock=lambda: t[0]), Budget()
        usage = GpuUsage(budget)

        def call(secs):   # what OpenAICompatLLM does around one request
            meter.start()
            t[0] += secs
            budget.add_gpu(meter.end())
        with usage.measure("x"):
            call(12.5)
            call(2.5)
        call(100.0)                                          # outside any measurement: not attributed
        with usage.measure("y"):
            call(4.0)
            with self.assertRaises(RuntimeError):
                with usage.measure("z"):
                    pass
        self.assertEqual(usage.seconds, {"x": 15.0, "y": 4.0})
        self.assertEqual(usage.pop(["x"]), {"x": 15.0})
        with self.assertRaises(TypeError):
            GpuUsage(object())

    def test_conversion(self):
        self.assertAlmostEqual(gpu_s_to_usd(3600, 3.95), 3.95)
        self.assertAlmostEqual(usd_to_gpu_s(3.95, 3.95), 3600)
        with self.assertRaises(ValueError):
            usd_to_gpu_s(1.0, 0.0)
        with mock.patch.dict(os.environ, {market_mod.RATE_ENV: "7.2"}):
            self.assertEqual(usd_per_gpu_hour(), 7.2)
            self.assertEqual(usd_per_gpu_hour(1.0), 1.0)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(usd_per_gpu_hour())
            m = Market(Wallets(gpu_initial=100))
            m.bid("a", "x", 0.6, gpu_s=50)
            self.assertIsNone(m.cost_usd("x", 0.2))           # GPU time asked for but no rate: no single-currency cost
            self.assertEqual(m.cost_usd("nothing", 0.2), 0.2)
        m = Market(Wallets(gpu_initial=100), usd_per_hour=3.6)
        m.bid("a", "x", 0.6, gpu_s=50)
        self.assertAlmostEqual(m.cost_usd("x", 0.2), 0.25)


def _ledger_run(path, wallets, run="r1", n=40, seed=0, gpu=False):
    rng = random.Random(seed)
    sh = LocalSharedMemory(path)
    m = Market(wallets, shared=sh, run_id=run, stake_frac=0.2)
    for k in range(n):
        c = f"c{k}"
        q = rng.uniform(0.1, 0.9)
        m.bid("honest", c, q, gpu_s=rng.uniform(5, 20) if gpu else None)
        m.bid("over", c, min(1.0, q + 0.3))
        m.bid("critic", c, 1 - q, against=True)
        if k % 7 == 3:
            m.withdraw()
            continue
        m.settle({c: rng.random() < q}, gpu_seconds={c: rng.uniform(0, 25)} if gpu else None)
    return m


class TestLedgerAudit(unittest.TestCase):
    def test_replay_matches_wallets(self):
        for gpu in (False, True):
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "s.jsonl")
                m = _ledger_run(path, Wallets(os.path.join(d, "w.json"), gpu_initial=200 if gpu else None), gpu=gpu)
                facts, ordered = ledger_facts(path)
                self.assertTrue(ordered)
                rep = audit_ledger(facts, gpu_initial=200 if gpu else None, wallets=m.wallets.summary())
                self.assertTrue(rep["ok"], rep["problems"][:3])
                for a, w in m.wallets.summary().items():
                    self.assertAlmostEqual(rep["agents"][a]["balance"], w["balance"], places=3)
                    self.assertEqual(rep["agents"][a]["n_settled"], w["settled"])
                    self.assertAlmostEqual(rep["agents"][a]["mean_log_score"], w["mean_log_score"], places=2)
                if gpu:
                    self.assertAlmostEqual(rep["agents"]["honest"]["gpu_balance"], m.wallets.summary()["honest"]["gpu_s"],
                                           places=3)
                self.assertGreater(rep["agents"]["honest"]["balance"], rep["agents"]["over"]["balance"])
                # the same check through the SharedMemory object (a local store is read in file order)
                self.assertEqual(ledger_facts(LocalSharedMemory(path))[1], True)

    def _tamper(self, path, kind, key, value, nth=0):
        with open(path) as fh:
            rows = [json.loads(l) for l in fh]
        hits = [r for r in rows if r["content"].startswith(kind) and f" {key}=" in r["content"]]
        f = parse_fact(hits[nth]["content"])
        hits[nth]["content"] = hits[nth]["content"].replace(f" {key}={f[key]}", f" {key}={value}", 1)
        with open(path, "w") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in rows)

    def test_detects_tampering(self):
        cases = [("SETTLE", "payoff", "5.0", "payoff_is_log_score"), ("SETTLE", "balance", "999.0", "balance_chain"),
                 ("SETTLE", "gpu_charged", "0.0", "gpu_charge_is_measured"),
                 ("SETTLE", "gpu_s", "0.01", "gpu_shares_add_up"), ("BID", "gpu_s_bid", "5000", "gpu_request_within_balance")]
        for kind, key, value, check in cases:
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "s.jsonl")
                _ledger_run(path, Wallets(gpu_initial=200), gpu=True)
                self._tamper(path, kind, key, value, nth=2)
                rep = audit_ledger(ledger_facts(path)[0], gpu_initial=200)
                self.assertFalse(rep["ok"], key)
                self.assertIn(check, {p["check"] for p in rep["problems"]}, (key, rep["problems"][:3]))

    def test_a_withdrawn_bid_then_a_new_bid_on_the_same_candidate(self):
        """The v2 loop withdraws unfunded bids and bids again next iteration with a
        stake from the new balance; withdrawals write no fact, so the settled bid
        is the latest BID, not the first."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.jsonl")
            m = Market(Wallets(os.path.join(d, "w.json"), gpu_initial=100), shared=LocalSharedMemory(path), run_id="r")
            m.bid("a", "x", 0.7, gpu_s=10)
            m.bid("a", "y", 0.9, gpu_s=10)
            m.settle({"y": True}, gpu_seconds={"y": 4.0})   # the balance, so the next stake, changes
            m.withdraw()                                     # x was not funded
            m.bid("a", "x", 0.6, gpu_s=20)
            m.settle({"x": False}, gpu_seconds={"x": 7.0})
            rep = audit_ledger(ledger_facts(path)[0], gpu_initial=100, wallets=m.wallets.summary())
            self.assertTrue(rep["ok"], rep["problems"])
            self.assertEqual(rep["agents"]["a"]["n_bids"], 3)

    def test_settle_without_bid_and_wallet_mismatch(self):
        from autoresearch.integrations.shared_memory import format_fact
        f = parse_fact(format_fact("SETTLE", agent="a", candidate="x", outcome=True, p=0.7, payoff=0.3, balance=100.3,
                                   run="r"))
        rep = audit_ledger([f], wallets={"a": {"balance": 100.3, "settled": 2}})
        self.assertEqual({p["check"] for p in rep["problems"]}, {"bid_before_settle", "wallet_matches_ledger"})

    def test_wallets_carried_over_between_runs(self):
        with tempfile.TemporaryDirectory() as d:
            path, wpath = os.path.join(d, "s.jsonl"), os.path.join(d, "w.json")
            _ledger_run(path, Wallets(wpath), run="r1", n=10)
            os.remove(path)
            m = _ledger_run(path, Wallets(wpath), run="r2", n=10, seed=1)   # starts from r1's balances
            facts, _ = ledger_facts(path)
            self.assertFalse(audit_ledger(facts)["ok"])                       # from 100 the chain breaks
            rep = audit_ledger(facts, initial=None)
            self.assertTrue(rep["ok"], rep["problems"][:3])
            self.assertAlmostEqual(rep["agents"]["over"]["balance"], m.wallets.balance("over"), places=3)

    def test_unordered_facts_get_per_fact_checks(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.jsonl")
            _ledger_run(path, Wallets(), n=12)
            facts, _ = ledger_facts(path)
            rep = audit_ledger(list(reversed(facts)), ordered=False)
            self.assertFalse(rep["ordered"])
            self.assertEqual({p["check"] for p in rep["problems"]}, {"bid_before_settle"})   # reversed: SETTLE before BID

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path, wpath = os.path.join(d, "s.jsonl"), os.path.join(d, "w.json")
            _ledger_run(path, Wallets(wpath), n=8)
            with mock.patch("sys.stdout"):
                self.assertEqual(market_mod.main(["audit", path, "--wallets", wpath]), 0)
                self._tamper(path, "SETTLE", "balance", "1.0")
                self.assertEqual(market_mod.main(["audit", path]), 1)


if __name__ == "__main__":
    unittest.main()
