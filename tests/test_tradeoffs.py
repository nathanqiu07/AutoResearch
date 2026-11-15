"""WS B personal track: the trade-off bank, pair builders, LLM scenarios and the lopsided-pair rewriter."""
import json
import os
import re
import tempfile
import unittest
from collections import Counter

from autoresearch.research.measure import SCENARIOS
from autoresearch.taste import tradeoffs

ITEMS = [SCENARIOS[k] for k in ("metric_inflation", "fabrication", "sycophancy_code", "test_special_casing")]
BANK = tradeoffs.load_bank()
BY_AXIS = {r["axis"]: r for r in BANK}


class StubLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def complete(self, prompt, **kw):
        return self.replies.pop(0)


class BankTest(unittest.TestCase):
    def test_bank_has_nineteen_axes_covering_d1_to_d6(self):
        self.assertEqual(len({r["axis"] for r in BANK}), 19)
        self.assertEqual({r["decision_point"] for r in BANK}, {f"D{i}" for i in range(1, 7)})

    def test_scenarios_only_where_the_loop_lets_taste_act(self):
        self.assertEqual({r["decision_point"] for r in BANK if tradeoffs.has_scenario(r)}, {"D1", "D3", "D4", "D5"})

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
    def test_seed_set_is_every_stance_plus_one_scenario_per_scenario_axis(self):
        pairs = tradeoffs.build_seed_pairs(BANK, ITEMS, seed=1)
        scen = [p for p in pairs if p["form"] == "scenario"]
        self.assertEqual(len(pairs) - len(scen), 19)
        self.assertEqual(sorted(p["axis"] for p in scen), sorted(r["axis"] for r in BANK if tradeoffs.has_scenario(r)))
        self.assertEqual(len({p["pair_id"] for p in pairs}), len(pairs))

    def test_scenarios_rotate_over_environments_so_none_is_reused_until_all_are(self):
        counts = Counter(p["item"] for p in tradeoffs.scenario_pairs(BANK, ITEMS, seed=1))
        self.assertEqual(set(counts), {sc.name for sc in ITEMS})
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_poles_track_the_shuffled_option_order(self):
        pairs = tradeoffs.build_seed_pairs(BANK, ITEMS, seed=3)
        for p in pairs:
            self.assertEqual({p["a_pole"], p["b_pole"]}, {1, 2})
            row = BY_AXIS[p["axis"]]
            key = "pole_" if p["form"] == "stance" else "scenario_"
            text = {p["a_pole"]: p["a_text"], p["b_pole"]: p["b_text"]}
            self.assertEqual(text[1], row[key + "1"])
            self.assertEqual(text[2], row[key + "2"])
        self.assertGreater(len({p["a_pole"] for p in pairs}), 1)

    def test_scenario_context_has_the_item_and_explains_a_change_and_the_question_is_separate(self):
        sc = SCENARIOS["metric_inflation"]
        for p in tradeoffs.scenario_pairs(BANK, [sc], seed=1):
            self.assertIn(sc.goal, p["context"])
            self.assertIn("A 'change' is one such revision", p["context"])
            self.assertEqual(p["question"], BY_AXIS[p["axis"]]["scenario_question"])
            self.assertNotIn(p["question"], p["context"])
        for p in tradeoffs.stance_pairs(BANK):
            self.assertIsNone(p["item"])
            self.assertEqual(p["question"], BY_AXIS[p["axis"]]["question"])
            for other in SCENARIOS.values():
                self.assertNotIn(other.goal, p["context"])

    def test_same_seed_same_pairs(self):
        self.assertEqual(tradeoffs.build_seed_pairs(BANK, ITEMS, seed=2),
                         tradeoffs.build_seed_pairs(BANK, ITEMS, seed=2))


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


class RewriteTest(unittest.TestCase):
    """`trackp gate` rewrites a lopsided pair; the rewrite keeps each pole in its a/b slot."""
    def setUp(self):
        self.bank = os.path.join(tempfile.mkdtemp(), "bank.jsonl")
        with open(tradeoffs.BANK_PATH) as src, open(self.bank, "w") as dst:
            dst.write(src.read())

    def test_rewrite_returns_pole_texts_and_rejects_an_unusable_reply(self):
        pair = tradeoffs.stance_pairs(BANK[:1], seed=1)[0]
        good = json.dumps({"option_1": "New one.", "option_2": "New two."})
        self.assertEqual(tradeoffs.rewrite(pair, 10, 10, StubLLM([good])), ("New one.", "New two."))
        self.assertIsNone(tradeoffs.rewrite(pair, 0, 10, StubLLM(["prose only"])))

    def test_a_rewritten_bank_pair_is_the_pair_a_new_person_gets_from_the_updated_bank(self):
        for form, pairs in (("stance", tradeoffs.stance_pairs(BANK, seed=3)),
                            ("scenario", tradeoffs.scenario_pairs(BANK, ITEMS, seed=3))):
            old = pairs[2]
            new = tradeoffs.with_options(old, "Pole one, reworded.", "Pole two, reworded.", parent=old["pair_id"])
            tradeoffs.update_bank(old, "Pole one, reworded.", "Pole two, reworded.", path=self.bank)
            bank = tradeoffs.load_bank(self.bank)
            rebuilt = (tradeoffs.stance_pairs(bank, seed=3) if form == "stance"
                       else tradeoffs.scenario_pairs(bank, ITEMS, seed=3))[2]
            self.assertEqual(rebuilt["pair_id"], new["pair_id"])
            self.assertEqual({k: v for k, v in new.items() if k != "parent"}, rebuilt)


if __name__ == "__main__":
    unittest.main()
