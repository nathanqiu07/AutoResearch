"""harness/tinker_proxy.py spend guard: a dollar ledger that persists across proxy runs (WS C2).

Pure Python, no tinker import, so it runs in the main suite.
"""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
import tinker_proxy as tp  # noqa: E402

KIMI = "moonshotai/Kimi-K2.6"
PRICES = {KIMI: (2.0, 5.0)}   # USD per 1M tokens: prefill, sample (round numbers for the arithmetic)


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ledger = str(Path(self.dir.name) / "sub" / "ledger.json")

    def tearDown(self):
        self.dir.cleanup()

    def budget(self, total=10.0, run=5.0):
        return tp.Budget(self.ledger, total_usd=total, run_usd=run, prices=PRICES)

    def test_cost_is_list_price_without_cache_discount(self):
        self.assertAlmostEqual(tp.Budget.cost(PRICES[KIMI], 1_000_000, 1_000_000), 7.0)

    def test_settled_spend_persists_across_proxy_runs(self):
        b = self.budget()
        self.assertIsNone(b.reserve(KIMI, 100_000, 100_000))       # worst case $0.70
        b.settle(KIMI, 100_000, 100_000, 50_000)                   # actual $0.20 + $0.25
        again = self.budget()
        self.assertAlmostEqual(again.spent_total(), 0.45)
        self.assertAlmostEqual(again.run_spent, 0.0)              # a new run starts its own run budget
        data = json.loads(Path(self.ledger).read_text())
        self.assertEqual(data["by_model"][KIMI]["completion_tokens"], 50_000)
        self.assertEqual(data["by_model"][KIMI]["requests"], 1)

    def test_refuses_when_worst_case_would_cross_lifetime_budget(self):
        b = self.budget(total=1.0, run=5.0)
        for _ in range(4):                                         # 4 x $0.20 prefill = $0.80 spent
            self.assertIsNone(b.reserve(KIMI, 100_000, 0))
            b.settle(KIMI, 100_000, 0, 0)
        reason = b.reserve(KIMI, 0, 100_000)                       # worst case $0.50 > $0.20 left
        self.assertIn("lifetime", reason)
        self.assertIsNone(b.reserve(KIMI, 0, 20_000))               # $0.10 still fits

    def test_refuses_when_worst_case_would_cross_run_budget(self):
        b = self.budget(total=100.0, run=0.5)
        self.assertIn("run", b.reserve(KIMI, 0, 200_000))           # worst case $1.00 > $0.50 run cap

    def test_in_flight_reservations_count_so_concurrency_cannot_overshoot(self):
        b = self.budget(total=1.0, run=1.0)
        ok = [b.reserve(KIMI, 0, 50_000) for _ in range(5)]          # $0.25 each, nothing settled yet
        self.assertEqual(sum(r is None for r in ok), 4)
        self.assertIsNotNone(ok[4])

    def test_release_frees_a_failed_request(self):
        b = self.budget(total=1.0, run=1.0)
        self.assertIsNone(b.reserve(KIMI, 0, 200_000))              # $1.00, the whole budget
        self.assertIsNotNone(b.reserve(KIMI, 0, 1))
        b.release(KIMI, 0, 200_000)
        self.assertIsNone(b.reserve(KIMI, 0, 1))
        self.assertAlmostEqual(self.budget().spent_total(), 0.0)    # nothing was billed

    def test_spend_written_by_another_proxy_counts(self):
        a, b = self.budget(total=1.0), self.budget(total=1.0)
        a.reserve(KIMI, 0, 160_000); a.settle(KIMI, 0, 160_000, 160_000)   # $0.80 through proxy a
        self.assertIsNotNone(b.reserve(KIMI, 0, 50_000))                 # proxy b sees it: $0.25 > $0.20 left

    def test_unpriced_model_is_refused(self):
        with self.assertRaises(ValueError):
            tp.Budget.price_for(PRICES, "someone/Unpriced-1T")

    def test_concurrent_settles_lose_nothing(self):
        b = self.budget(total=100.0, run=100.0)
        def one():
            b.reserve(KIMI, 1_000, 1_000); b.settle(KIMI, 1_000, 1_000, 1_000)
        threads = [threading.Thread(target=one) for _ in range(40)]
        [t.start() for t in threads]; [t.join() for t in threads]
        self.assertAlmostEqual(self.budget().spent_total(), 40 * 0.007)


class PoolTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def account(self, label, total):
        return label, tp.Budget(str(self.root / f"tinker_ledger_{label}.json"), total, 0, PRICES)

    def test_drains_accounts_in_order_then_refuses(self):
        pool = tp.Pool([self.account("nathan", 0.5), self.account("abhi", 0.5)])
        used = []
        for _ in range(4):                                         # $0.25 worst case each
            label, reason = pool.acquire(KIMI, 0, 50_000)
            self.assertIsNone(reason)
            pool.settle(label, KIMI, 0, 50_000, 50_000)
            used.append(label)
        self.assertEqual(used, ["nathan", "nathan", "abhi", "abhi"])
        label, reason = pool.acquire(KIMI, 0, 50_000)
        self.assertIsNone(label)
        self.assertIn("every Tinker account", reason)
        self.assertIn("[nathan]", reason)
        self.assertIn("[abhi]", reason)

    def test_spend_lands_in_the_account_that_served_it(self):
        pool = tp.Pool([self.account("nathan", 0.3), self.account("abhi", 5.0)])
        label, _ = pool.acquire(KIMI, 0, 50_000); pool.settle(label, KIMI, 0, 50_000, 50_000)   # nathan $0.25
        label, _ = pool.acquire(KIMI, 0, 50_000); pool.settle(label, KIMI, 0, 50_000, 20_000)   # abhi $0.10
        spent = {s["account"]: s["spent_usd"] for s in pool.summary()}
        self.assertAlmostEqual(spent["nathan"], 0.25)
        self.assertAlmostEqual(spent["abhi"], 0.10)

    def test_run_cap_spans_all_accounts(self):
        pool = tp.Pool([self.account("nathan", 0.3), self.account("abhi", 5.0)], run_usd=0.4)
        label, _ = pool.acquire(KIMI, 0, 50_000); pool.settle(label, KIMI, 0, 50_000, 50_000)   # $0.25 run total
        label, reason = pool.acquire(KIMI, 0, 50_000)                                          # +$0.25 > $0.40
        self.assertIsNone(label)
        self.assertIn("per-run", reason)

    def test_release_returns_the_reservation(self):
        pool = tp.Pool([self.account("nathan", 0.25)])
        label, _ = pool.acquire(KIMI, 0, 50_000)
        self.assertIsNotNone(pool.acquire(KIMI, 0, 1)[1])
        pool.release(label, KIMI, 0, 50_000)
        self.assertIsNone(pool.acquire(KIMI, 0, 1)[1])

    def test_duplicate_labels_rejected(self):
        with self.assertRaises(ValueError):
            tp.Pool([self.account("a", 1), self.account("a", 1)])

    def test_load_pool_reads_env_names_not_keys_and_fails_on_a_missing_key(self):
        f = self.root / "pool.json"
        f.write_text(json.dumps({"tinker": [{"label": "nathan", "key_env": "T_KEY_NATHAN", "budget_usd": 100},
                                            {"label": "abhi", "key_env": "T_KEY_ABHI", "budget_usd": 80}]}))
        import os
        os.environ["T_KEY_NATHAN"] = "x"
        os.environ.pop("T_KEY_ABHI", None)
        try:
            with self.assertRaises(ValueError) as cm:
                tp.load_pool(str(f), 15, PRICES, str(self.root))
            self.assertIn("T_KEY_ABHI", str(cm.exception))
            os.environ["T_KEY_ABHI"] = "y"
            pool, key_envs = tp.load_pool(str(f), 15, PRICES, str(self.root))
            self.assertEqual(key_envs, {"nathan": "T_KEY_NATHAN", "abhi": "T_KEY_ABHI"})
            self.assertEqual([s["budget_usd"] for s in pool.summary()], [100.0, 80.0])
            self.assertEqual(pool.run_usd, 15)
        finally:
            os.environ.pop("T_KEY_NATHAN", None); os.environ.pop("T_KEY_ABHI", None)


class ClampTest(unittest.TestCase):
    def test_max_tokens_is_clamped_and_defaults_stay(self):
        self.assertEqual(tp.completion_limit({"max_tokens": 100_000}, ceiling=16_384), 16_384)
        self.assertEqual(tp.completion_limit({"max_completion_tokens": 900}, ceiling=16_384), 900)
        self.assertEqual(tp.completion_limit({}, ceiling=8_000), 8_000)
        self.assertEqual(tp.completion_limit({}, ceiling=0), tp.DEFAULT_COMPLETION_TOKENS)


class PricesTest(unittest.TestCase):
    def test_kimi_k26_is_priced_from_the_tinker_page(self):
        self.assertEqual(tp.TINKER_PRICES["moonshotai/Kimi-K2.6"], (2.205, 5.49))


if __name__ == "__main__":
    unittest.main()
