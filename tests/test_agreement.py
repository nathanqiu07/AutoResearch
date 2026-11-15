"""Personal-track reviews and archived blind-model vote measurements."""
import json
import tempfile
import unittest

from autoresearch.llm import LLM
from autoresearch.taste import agreement


class VotingLLM(LLM):
    """Of the 5 samples for (context, option shown first), the first n pick option 1."""

    def __init__(self, picks_first):
        super().__init__()
        self.picks_first, self.seen, self.calls = picks_first, {}, 0

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.calls += 1
        key = next(k for k in self.picks_first if f"Context: c{k[0]}\n" in prompt and f"Option 1: {k[1]}\n" in prompt)
        i = self.seen.get(key, 0)
        self.seen[key] = i + 1
        return json.dumps({"choice": 1 if i < self.picks_first[key] else 2})


def pair(k, a_pole=1):
    return {"pair_id": f"p{k}", "context": f"c{k}", "question": "Which?", "a_text": f"A{k}", "b_text": f"B{k}",
            "a_pole": a_pole, "b_pole": 3 - a_pole}


class GateTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.llm = VotingLLM({
            ("0", "A0"): 5, ("0", "B0"): 0,   # 10/10 for A: lopsided
            ("1", "A1"): 0, ("1", "B1"): 5,   # 10/10 for B: lopsided too
            ("2", "A2"): 5, ("2", "B2"): 1,   # 9/10: lopsided
            ("3", "A3"): 5, ("3", "B3"): 2,   # 8/10, not more than 80%: passes
            ("4", "A4"): 5, ("4", "B4"): 5,   # always the first option shown: position bias
            ("5", "A5"): 2, ("5", "B5"): 2,   # 3/6 on the shorter gate, no position bias
        })
        self.pairs = [pair(k) for k in range(5)]

    def test_a_pair_is_lopsided_when_more_than_80_percent_of_votes_go_to_either_option(self):
        agreement.judge(self.root, self.pairs, self.llm, workers=1)
        self.assertEqual([agreement.lopsided(agreement.rows(self.root)[agreement.key(p)]) for p in self.pairs],
                         [True, True, True, False, False])
        self.assertTrue(agreement.position_biased(agreement.rows(self.root)[agreement.key(self.pairs[4])]))

    def test_an_unjudged_pair_has_no_verdict(self):
        self.assertIsNone(agreement.passes(self.root, self.pairs[0]))

    def test_review_accepts_a_defensible_tradeoff_despite_unanimous_model_votes(self):
        pair = self.pairs[0]
        agreement.judge(self.root, [pair], self.llm, workers=1)
        agreement.record_reviews(self.root, [pair], [{
            "pair_id": pair["pair_id"], "decision": "pass", "reviewer": "reviewer",
            "reason": "Both actions serve different uses under the same budget.",
            "benefit_1": "Clear diagnosis", "cost_1": "Narrow coverage",
            "benefit_2": "Broad coverage", "cost_2": "Weaker diagnosis",
        }])
        self.assertTrue(agreement.passes(self.root, pair))

    def test_review_requires_a_case_for_both_options(self):
        with self.assertRaisesRegex(ValueError, "cost_2"):
            agreement.record_reviews(self.root, [self.pairs[0]], [{
                "pair_id": self.pairs[0]["pair_id"], "decision": "pass", "reviewer": "reviewer",
                "reason": "Both actions have a use.", "benefit_1": "A", "cost_1": "B", "benefit_2": "C",
            }])

    def test_votes_are_recorded_once_per_item_whatever_the_a_b_order(self):
        agreement.judge(self.root, self.pairs, self.llm, workers=1)
        self.assertEqual(self.llm.calls, 50)
        swapped = {**self.pairs[0], "pair_id": "other", "a_text": "B0", "b_text": "A0", "a_pole": 2, "b_pole": 1}
        agreement.judge(self.root, self.pairs + [swapped], self.llm, workers=1)
        self.assertEqual(self.llm.calls, 50)
        self.assertIsNone(agreement.passes(self.root, swapped))

    def test_six_vote_gate_marks_five_of_six_lopsided_and_records_model(self):
        agreement.judge(self.root, [self.pairs[2], pair(5)], self.llm, workers=1, votes_per_order=3)
        self.assertEqual([agreement.lopsided(agreement.rows(self.root)[agreement.key(p)])
                          for p in [self.pairs[2], pair(5)]], [True, False])
        self.assertEqual([len(order) for order in agreement.rows(self.root)[agreement.key(self.pairs[2])]["votes"]],
                         [3, 3])
        self.assertEqual(agreement.rows(self.root)[agreement.key(self.pairs[2])]["judge"], self.llm.label)

    def test_a_new_model_can_rejudge_position_bias_without_losing_old_votes(self):
        biased = self.pairs[4]
        agreement.judge(self.root, [biased], self.llm, workers=1)
        replacement = VotingLLM({("4", "A4"): 2, ("4", "B4"): 2})
        replacement.name = "new-model"
        agreement.judge(self.root, [biased], replacement, workers=1, rejudge_position_bias=True)
        with open(f"{self.root}/{agreement.AGREEMENT}") as f:
            self.assertEqual(sum(1 for _ in f), 2)
        self.assertEqual(agreement.rows(self.root)[agreement.key(biased)]["judge"], replacement.label)
        self.assertIsNone(agreement.passes(self.root, biased))


if __name__ == "__main__":
    unittest.main()
