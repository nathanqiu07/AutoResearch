#!/usr/bin/env python3
"""Proposed safe-fallback regressions. Expected RED against the audited code.

These assertions cover malformed values and the currently documented D1 threshold.
They do not require calibration, abstention for empty text profiles, or a new policy
for invalid optional distributions when a usable choice/confidence remains.
"""
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.dont_write_bytecode = True
repo = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(repo))
from autoresearch.research.advisor import TasteAdvisor, ProfileUserModel
from autoresearch.taste.profile import TasteProfile


class Fixed:
    def __init__(self, **values):
        self.values = values

    def predict(self, context, options):
        return SimpleNamespace(**self.values)


class FixedFeatures:
    def __init__(self, values):
        self.values = values

    def predict_features(self, context, features):
        return self.values


class SafeFallbackRegressions(unittest.TestCase):
    def test_malformed_choices_abstain_and_log(self):
        for choice in ("²", "İ"):
            with self.subTest(choice=choice):
                advisor = TasteAdvisor(Fixed(choice=choice, confidence=.9))
                advice = advisor.consult("c", ["A", "B"])
                self.assertIsNone(advice.choice)
                self.assertFalse(advice.usable)
                self.assertTrue(advisor.errors)

    def test_overflow_confidence_abstains_and_logs(self):
        advisor = TasteAdvisor(Fixed(choice="a", confidence=10**1000))
        advice = advisor.consult("c", ["A", "B"])
        self.assertFalse(advice.usable)
        self.assertTrue(advisor.errors)

    def test_overflow_probability_does_not_crash_decisive_choice(self):
        advisor = TasteAdvisor(Fixed(choice="a", confidence=.9, probabilities=[10**1000, 0]))
        self.assertEqual(advisor.decide("c", ["A", "B"], 1, True)[0], 1)
        self.assertTrue(advisor.errors)

    def test_malformed_choice_cannot_break_decisive_fallback(self):
        advisor = TasteAdvisor(Fixed(choice="²", confidence=.9))
        self.assertEqual(advisor.decide("c", ["A", "B"], 1, True)[0], 1)
        self.assertTrue(advisor.errors)

    def test_invalid_feature_distributions_fall_back_and_log(self):
        for values in ([float("nan"), .1], [float("inf"), 0], [-.2, 1.2], [.2, .3]):
            with self.subTest(values=values):
                advisor = TasteAdvisor(FixedFeatures(values))
                scores, advice = advisor.d1_scores("c", ["A", "B"], [{}, {}])
                self.assertEqual(scores, [.5, .5])
                self.assertTrue(all(math.isfinite(value) for value in scores))
                self.assertFalse(advice.usable)
                self.assertTrue(advisor.errors)

    def test_real_nonfinite_profile_falls_back(self):
        for weight in (float("nan"), float("inf")):
            with self.subTest(weight=weight):
                advisor = TasteAdvisor(ProfileUserModel(TasteProfile("bad", {"x": weight})))
                scores, advice = advisor.d1_scores("c", ["A", "B"], [{"x": 1}, {"x": 0}])
                self.assertEqual(scores, [.5, .5])
                self.assertFalse(advice.usable)
                self.assertTrue(advisor.errors)

    def test_feature_advice_respects_documented_threshold(self):
        advisor = TasteAdvisor(ProfileUserModel(TasteProfile("weak", {"x": .2})), min_confidence=.6)
        scores, advice = advisor.d1_scores("c", ["A", "B"], [{"x": 1}, {"x": 0}])
        self.assertLess(advice.confidence, .6)
        self.assertFalse(advice.usable)
        self.assertEqual(scores, [.5, .5])

    def test_valid_decisive_fallback_control(self):
        advisor = TasteAdvisor(Fixed(choice="a", confidence=.9, probabilities=[.9, .1]))
        self.assertEqual(advisor.decide("c", ["A", "B"], 1, True)[0], 1)
        self.assertEqual(advisor.decide("c", ["A", "B"], 1, False)[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
