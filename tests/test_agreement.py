"""Agreement filter (personal track): a blind judge votes 5 times with each option order; a pair
leaves every split when more than 80% of its 10 votes go to the person's option. Votes are
recorded once and never re-asked."""
import json
import tempfile
import unittest

from autoresearch.llm import LLM
from autoresearch.taste import agreement
from autoresearch.taste.usermodel import Choice


class VotingLLM(LLM):
    """Of the 5 samples for (context, option shown first), the first n pick option 1."""

    def __init__(self, picks_first):
        super().__init__()
        self.picks_first, self.seen, self.calls = picks_first, {}, 0

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.calls += 1
        key = next(k for k in self.picks_first if f"Context: {k[0]}\n" in prompt and f"Option 1: {k[1]}\n" in prompt)
        i = self.seen.get(key, 0)
        self.seen[key] = i + 1
        return json.dumps({"choice": 1 if i < self.picks_first[key] else 2})


def choice(k, chosen="a"):
    return Choice(user_id="u", context=f"c{k}", a_text=f"A{k}", b_text=f"B{k}", chosen=chosen,
                  decision_point="D1", timestamp="2025-01-01", source="seed", example_id=f"p{k}")


class AgreementTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.llm = VotingLLM({
            ("c0", "A0"): 5, ("c0", "B0"): 0,   # 10/10 for his option A: dropped
            ("c1", "A1"): 0, ("c1", "B1"): 5,   # 0/10, judge sure he is wrong: kept
            ("c2", "A2"): 5, ("c2", "B2"): 1,   # 9/10: dropped
            ("c3", "A3"): 5, ("c3", "B3"): 2,   # 8/10, not more than 80%: kept
            ("c4", "A4"): 5, ("c4", "B4"): 5,   # always the first option shown: 5/10, kept
            ("c5", "A5"): 0, ("c5", "B5"): 5,   # he chose b; 10/10 for B: dropped
        })
        self.choices = [choice(k) for k in range(5)] + [choice(5, chosen="b")]

    def test_drops_pairs_where_more_than_80_percent_of_votes_go_to_the_person(self):
        agreement.judge(self.dir, self.choices, self.llm, workers=1)
        kept = agreement.keep(self.dir, self.choices)
        self.assertEqual([c.example_id for c in kept], ["p1", "p3", "p4"])

    def test_recorded_votes_are_reused_not_asked_again(self):
        agreement.judge(self.dir, self.choices, self.llm, workers=1)
        self.assertEqual(self.llm.calls, 60)
        agreement.judge(self.dir, self.choices, self.llm, workers=1)
        self.assertEqual(self.llm.calls, 60)
        kept = agreement.keep(self.dir, self.choices, threshold=0.95)
        self.assertEqual([c.example_id for c in kept], ["p1", "p2", "p3", "p4"])

    def test_refuses_to_filter_pairs_never_judged(self):
        agreement.judge(self.dir, self.choices[:4], self.llm, workers=1)
        with self.assertRaisesRegex(ValueError, "2 pair"):
            agreement.keep(self.dir, self.choices)


if __name__ == "__main__":
    unittest.main()
