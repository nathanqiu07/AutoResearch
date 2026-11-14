import json
import math
import os
import random
import tempfile
import unittest

from autoresearch.integrations.shared_memory import LocalSharedMemory, parse_fact
from autoresearch.research.market import (P_FLOOR, Bid, Market, Wallets, halving_plan, log_score_payoff)


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


if __name__ == "__main__":
    unittest.main()
