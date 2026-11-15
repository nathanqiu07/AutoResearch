"""Item gate (personal track): a blind judge votes 5 times with each option order; a pair is
lopsided when more than 80% of its 10 votes go to either option. Votes are recorded once per
item and never re-asked."""
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
            ("4", "A4"): 5, ("4", "B4"): 5,   # always the first option shown: 5/10, passes
        })
        self.pairs = [pair(k) for k in range(5)]

    def test_a_pair_is_lopsided_when_more_than_80_percent_of_votes_go_to_either_option(self):
        agreement.judge(self.root, self.pairs, self.llm, workers=1)
        self.assertEqual([agreement.passes(self.root, p) for p in self.pairs], [False, False, False, True, True])

    def test_an_unjudged_pair_has_no_verdict(self):
        self.assertIsNone(agreement.passes(self.root, self.pairs[0]))

    def test_votes_are_recorded_once_per_item_whatever_the_a_b_order(self):
        agreement.judge(self.root, self.pairs, self.llm, workers=1)
        self.assertEqual(self.llm.calls, 50)
        swapped = {**self.pairs[0], "pair_id": "other", "a_text": "B0", "b_text": "A0", "a_pole": 2, "b_pole": 1}
        agreement.judge(self.root, self.pairs + [swapped], self.llm, workers=1)
        self.assertEqual(self.llm.calls, 50)
        self.assertFalse(agreement.passes(self.root, swapped))

    def test_six_vote_gate_marks_five_of_six_lopsided_and_records_model(self):
        agreement.judge(self.root, [self.pairs[2], self.pairs[3]], self.llm, workers=1, votes_per_order=3)
        self.assertEqual([agreement.passes(self.root, p) for p in self.pairs[2:4]], [False, True])
        self.assertEqual([len(order) for order in agreement.rows(self.root)[agreement.key(self.pairs[2])]["votes"]],
                         [3, 3])
        self.assertEqual(agreement.rows(self.root)[agreement.key(self.pairs[2])]["judge"], self.llm.label)


if __name__ == "__main__":
    unittest.main()
