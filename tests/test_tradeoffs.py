"""WS B personal track: the trade-off bank, pair builders, LLM scenarios and balance check."""
import json
import os
import re
import tempfile
import unittest
from collections import Counter

from autoresearch.research.measure import SCENARIOS
from autoresearch.taste import tradeoffs
from autoresearch.taste.usermodel import Prediction

ITEMS = [SCENARIOS[k] for k in ("metric_inflation", "fabrication", "sycophancy_code", "test_special_casing")]
BANK = tradeoffs.load_bank()
BY_AXIS = {r["axis"]: r for r in BANK}


class StubLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def complete(self, prompt, **kw):
        return self.replies.pop(0)


class StubModel:
    """probabilities for [first, second] option given the two option texts."""
    method_id = "stub"

    def __init__(self, fn):
        self.fn = fn

    def predict(self, context, options):
        p = self.fn(options)
        return Prediction("a", max(p), probabilities=p)


class BankTest(unittest.TestCase):
    def test_bank_has_thirteen_axes_covering_d1_to_d6(self):
        self.assertEqual(len({r["axis"] for r in BANK}), 13)
        self.assertEqual({r["decision_point"] for r in BANK}, {f"D{i}" for i in range(1, 7)})

    def test_bank_cites_no_hobbhahn_or_apollo_source(self):
        bad = re.compile("hobbhahn|apollo", re.I)
        self.assertFalse([s for r in BANK for s in r["sources"] if bad.search(s)])

    def test_load_bank_names_the_axis_with_a_missing_field(self):
        row = {k: BANK[0][k] for k in BANK[0] if k != "pole_2"}
        row["axis"] = "my-axis"
        path = os.path.join(tempfile.mkdtemp(), "bank.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps(row) + "\n")
        with self.assertRaises(ValueError) as cm:
            tradeoffs.load_bank(path)
        self.assertIn("my-axis", str(cm.exception))
        self.assertIn("pole_2", str(cm.exception))


class PairsTest(unittest.TestCase):
    def test_default_fifty_is_thirteen_stance_and_thirty_seven_scenarios(self):
        pairs = tradeoffs.build_seed_pairs(BANK, ITEMS, 50, seed=1)
        stance = [p for p in pairs if p["form"] == "stance"]
        scen = [p for p in pairs if p["form"] == "scenario"]
        self.assertEqual((len(stance), len(scen)), (13, 37))
        self.assertEqual(len({p["pair_id"] for p in pairs}), 50)
        counts = Counter(p["item"] for p in scen)
        self.assertEqual(set(counts), {sc.name for sc in ITEMS})
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
        self.assertEqual({p["axis"] for p in scen}, set(BY_AXIS))

    def test_not_enough_distinct_scenarios_raises(self):
        with self.assertRaises(ValueError):
            tradeoffs.scenario_pairs(BANK, ITEMS[:1], 14)

    def test_n_below_thirteen_gives_only_stance_items(self):
        pairs = tradeoffs.build_seed_pairs(BANK, ITEMS, 5, seed=1)
        self.assertEqual([p["form"] for p in pairs], ["stance"] * 5)
        self.assertEqual([p["axis"] for p in pairs], [r["axis"] for r in BANK[:5]])

    def test_poles_track_the_shuffled_option_order(self):
        pairs = tradeoffs.build_seed_pairs(BANK, ITEMS, 50, seed=3)
        for p in pairs:
            self.assertEqual({p["a_pole"], p["b_pole"]}, {1, 2})
            row = BY_AXIS[p["axis"]]
            key = "pole_" if p["form"] == "stance" else "scenario_"
            text = {p["a_pole"]: p["a_text"], p["b_pole"]: p["b_text"]}
            self.assertEqual(text[1], row[key + "1"])
            self.assertEqual(text[2], row[key + "2"])
        self.assertGreater(len({p["a_pole"] for p in pairs}), 1)

    def test_scenario_context_has_the_item_and_the_axis_question(self):
        sc = SCENARIOS["metric_inflation"]
        scen = tradeoffs.scenario_pairs(BANK, [sc], 3, seed=1)
        for p in scen:
            self.assertIn(sc.goal, p["context"])
            self.assertIn(BY_AXIS[p["axis"]]["scenario_question"], p["context"])
        for p in tradeoffs.stance_pairs(BANK):
            self.assertIsNone(p["item"])
            self.assertIn(BY_AXIS[p["axis"]]["question"], p["context"])
            for other in SCENARIOS.values():
                self.assertNotIn(other.goal, p["context"])

    def test_same_seed_same_pairs(self):
        self.assertEqual(tradeoffs.build_seed_pairs(BANK, ITEMS, 40, seed=2),
                         tradeoffs.build_seed_pairs(BANK, ITEMS, 40, seed=2))


class LLMScenarioTest(unittest.TestCase):
    GOOD = json.dumps({"option_1": "Hold the setting fixed and vary one thing.",
                       "option_2": "Vary several things in the setting at once."})

    def test_llm_scenarios_tag_poles_and_origin(self):
        warnings = []
        pairs = tradeoffs.llm_scenario_pairs(BANK, ITEMS[:1], StubLLM([self.GOOD] * 2), k=2,
                                             warn=warnings.append)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(warnings, [])
        self.assertEqual(len({p["axis"] for p in pairs}), 2)
        for p in pairs:
            self.assertEqual((p["origin"], p["form"], p["item"]), ("llm", "scenario", ITEMS[0].name))
            text = {p["a_pole"]: p["a_text"], p["b_pole"]: p["b_text"]}
            self.assertEqual(text[1], json.loads(self.GOOD)["option_1"])
            self.assertEqual(text[2], json.loads(self.GOOD)["option_2"])
            self.assertIn(ITEMS[0].goal, p["context"])

    def test_llm_reply_that_is_not_json_or_has_identical_options_is_skipped_with_a_warning(self):
        same = json.dumps({"option_1": "Same.", "option_2": "Same."})
        warnings = []
        pairs = tradeoffs.llm_scenario_pairs(BANK, ITEMS[:1], StubLLM(["no json here", same, self.GOOD]),
                                             k=3, warn=warnings.append)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(len(warnings), 2)


class BalanceTest(unittest.TestCase):
    def setUp(self):
        self.pair = tradeoffs.stance_pairs(BANK[:1], seed=1)[0]
        self.pole1 = {self.pair["a_pole"]: self.pair["a_text"], self.pair["b_pole"]: self.pair["b_text"]}[1]

    def check(self, fn, **kw):
        return tradeoffs.balance_check([self.pair], StubModel(fn), **kw)[0]

    def test_balance_flags_a_pair_both_orders_favour_one_pole(self):
        pole_one = lambda opts: [0.9, 0.1] if opts[0] == self.pole1 else [0.1, 0.9]
        row = self.check(pole_one)
        self.assertTrue(row["one_sided"])
        self.assertEqual(row["pair_id"], self.pair["pair_id"])
        self.assertEqual(row["p_pole1"], [0.9, 0.9])

    def test_position_bias_alone_is_not_flagged(self):
        self.assertFalse(self.check(lambda opts: [0.9, 0.1])["one_sided"])

    def test_threshold_is_respected(self):
        pole_one = lambda opts: [0.7, 0.3] if opts[0] == self.pole1 else [0.3, 0.7]
        self.assertFalse(self.check(pole_one)["one_sided"])
        self.assertTrue(self.check(pole_one, threshold=0.6)["one_sided"])


class ShownTest(unittest.TestCase):
    def pair(self, origin):
        return {"pair_id": "p1", "origin": origin}

    def row(self, type_, **kw):
        return {"type": type_, "pair_id": "p1", **kw}

    def test_bank_pair_is_shown_unless_flagged_and_unreviewed(self):
        bank = self.pair("bank")
        self.assertTrue(tradeoffs.shown(bank, []))
        self.assertTrue(tradeoffs.shown(bank, [self.row("check", one_sided=False)]))
        self.assertFalse(tradeoffs.shown(bank, [self.row("check", one_sided=True)]))

    def test_llm_pair_needs_a_clean_check_or_approval(self):
        llm = self.pair("llm")
        self.assertFalse(tradeoffs.shown(llm, []))
        self.assertTrue(tradeoffs.shown(llm, [self.row("check", one_sided=False)]))
        flagged = [self.row("check", one_sided=True)]
        self.assertFalse(tradeoffs.shown(llm, flagged))
        self.assertTrue(tradeoffs.shown(llm, flagged + [self.row("review", decision="approve")]))

    def test_drop_review_hides_any_pair(self):
        rows = [self.row("check", one_sided=False), self.row("review", decision="drop")]
        self.assertFalse(tradeoffs.shown(self.pair("bank"), rows))
        self.assertFalse(tradeoffs.shown(self.pair("llm"), rows))


if __name__ == "__main__":
    unittest.main()
