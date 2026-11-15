"""Agreement filter, both tracks: a pair leaves every split when a blind judge gives the person's
option more than the threshold in both a/b orders; its probabilities are recorded once."""
import tempfile
import unittest

from autoresearch.taste import agreement
from autoresearch.taste.usermodel import Choice, Prediction


class FixedJudge:
    """P(the option shown first) comes from a table keyed by (context, first option)."""

    def __init__(self, p_first):
        self.p_first, self.calls = p_first, 0
        self.llm = type("L", (), {"label": "fake/judge"})()

    def predict(self, context, options):
        self.calls += 1
        p = self.p_first[(context, options[0])]
        return Prediction(choice="a" if p >= 0.5 else "b", confidence=max(p, 1 - p), probabilities=[p, 1 - p])


def choice(k, chosen="a"):
    return Choice(user_id="u", context=f"c{k}", a_text=f"A{k}", b_text=f"B{k}", chosen=chosen,
                  decision_point="D1", timestamp="2025-01-01", source="seed", example_id=f"p{k}")


class AgreementTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        # p0: judge gives his option (A) 0.9 both ways -> dropped.
        # p1: judge gives the other option 0.9 both ways -> kept (taste shows here).
        # p2: 0.9 shown first, 0.7 shown second -> kept (not above 0.8 in both orders).
        # p3: he chose b; judge gives B 0.85 both ways -> dropped.
        self.judge = FixedJudge({("c0", "A0"): 0.9, ("c0", "B0"): 0.1,
                                 ("c1", "A1"): 0.1, ("c1", "B1"): 0.9,
                                 ("c2", "A2"): 0.9, ("c2", "B2"): 0.3,
                                 ("c3", "A3"): 0.15, ("c3", "B3"): 0.85})
        self.choices = [choice(0), choice(1), choice(2), choice(3, chosen="b")]

    def test_drops_only_pairs_the_judge_confidently_decides_for_the_person(self):
        agreement.judge(self.dir, self.choices, self.judge)
        kept = agreement.keep(self.dir, self.choices)
        self.assertEqual([c.example_id for c in kept], ["p1", "p2"])

    def test_recorded_probabilities_are_reused_not_recomputed(self):
        agreement.judge(self.dir, self.choices, self.judge)
        calls = self.judge.calls
        agreement.judge(self.dir, self.choices, self.judge)
        self.assertEqual(self.judge.calls, calls)
        self.assertEqual([c.example_id for c in agreement.keep(self.dir, self.choices, threshold=0.95)],
                         ["p0", "p1", "p2", "p3"])

    def test_refuses_to_filter_pairs_never_judged(self):
        agreement.judge(self.dir, self.choices[:2], self.judge)
        with self.assertRaisesRegex(ValueError, "2 pair"):
            agreement.keep(self.dir, self.choices)


if __name__ == "__main__":
    unittest.main()
