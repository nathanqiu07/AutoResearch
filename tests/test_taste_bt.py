import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.llm import LLM
from autoresearch.taste.profile import FEATURES
from autoresearch.taste.usermodel import Choice, load_model


class FeatureLLM(LLM):
    """Script the external feature service; exercise the actual learner and cache."""
    name = "test-feature-mapping"

    def __init__(self, invalid=None):
        super().__init__()
        self.payloads = []
        self.invalid = invalid

    def complete(self, prompt, **kwargs):
        payload = json.loads(prompt.split("\nINPUT_JSON:\n", 1)[1])
        self.payloads.append(payload)
        self.budget.charge(10, 5)
        if "options" in payload:
            return json.dumps({"probabilities": [0.25, 0.75], "rationale": "generic"})
        features = dict.fromkeys(FEATURES, 0.0)
        features["simplicity"] = 1.0 if "simple" in payload["option"] else 0.0
        if self.invalid is not None:
            features["simplicity"] = self.invalid
        return json.dumps({"features": features})


class BradleyTerryTests(unittest.TestCase):
    def model(self, llm=None, **kwargs):
        from autoresearch.taste.methods.m4_bt import BradleyTerry
        return BradleyTerry(llm or FeatureLLM(), **kwargs)

    def history(self, chosen="a"):
        return [Choice("PRIVATE-USER", "training context %d" % i,
                       "simple history %d" % i, "complex history %d" % i,
                       chosen, reason="PRIVATE-REASON", example_id="PRIVATE-ID-%d" % i)
                for i in range(4)]

    def test_history_labels_change_heldout_preference(self):
        simple, complex_ = self.model(), self.model()
        simple.fit(self.history(), [])
        complex_.fit(self.history("b"), [])
        a = simple.predict("unseen", ["complex unseen", "simple unseen"])
        b = complex_.predict("unseen", ["complex unseen", "simple unseen"])
        self.assertEqual((a.choice, b.choice), ("b", "a"))
        self.assertGreater(a.confidence, 0.5)
        self.assertFalse(a.calibrated)
        self.assertGreater(simple.artifacts().weights["simplicity"], 0)
        self.assertLess(complex_.artifacts().weights["simplicity"], 0)
        self.assertEqual(simple.artifacts().metadata["weights_status"], "learned")

    def test_order_reversal_and_multiple_options_use_same_features(self):
        with tempfile.TemporaryDirectory() as d:
            model = self.model(cache_dir=d)
            model.fit(self.history(), [])
            forward = model.predict("new", ["simple new", "complex new"])
            calls = model.cost["calls"]
            reverse = model.predict("new", ["complex new", "simple new"])
            self.assertEqual(model.cost["calls"], calls)
            self.assertEqual((forward.choice, reverse.choice), ("a", "b"))
            self.assertEqual(forward.probabilities, list(reversed(reverse.probabilities)))
            multiple = model.predict("new", ["complex new", "simple new", "complex third"])
            self.assertEqual(multiple.choice, "b")
            self.assertEqual(len(multiple.probabilities), 3)
            self.assertAlmostEqual(sum(multiple.probabilities), 1.0)

    def test_featurizer_never_receives_labels_user_metadata_or_validation(self):
        llm = FeatureLLM()
        model = self.model(llm)
        model.fit(self.history(), [Choice("PRIVATE-USER", "VALIDATION-SECRET",
                                         "VAL-A", "VAL-B", "b")])
        for payload in llm.payloads:
            self.assertEqual(set(payload), {"context", "option"})
            text = json.dumps(payload)
            for secret in ("PRIVATE-USER", "PRIVATE-REASON", "PRIVATE-ID", "VALIDATION-SECRET",
                           "VAL-A", "VAL-B"):
                self.assertNotIn(secret, text)

    def test_invalid_features_fail_before_prediction(self):
        for value in (float("nan"), float("inf"), True, "0.5", 1.1, -0.1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.model(FeatureLLM(invalid=value)).fit(self.history(), [])

    def test_saved_weights_predict_without_refitting(self):
        model = self.model()
        model.fit(self.history(), [])
        expected = model.predict("new", ["complex new", "simple new"])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m4.json"
            model.save(path)
            loaded = load_model(path, FeatureLLM())
            self.assertEqual(loaded.history, [])
            self.assertEqual(loaded.predict("new", ["complex new", "simple new"]), expected)
            self.assertEqual(loaded.artifacts().weights, model.artifacts().weights)

    def test_empty_history_falls_back_to_generic_prediction(self):
        model = self.model()
        model.fit([], [])
        result = model.predict("new", ["simple new", "complex new"])
        self.assertEqual((result.choice, result.confidence), ("b", 0.75))
        self.assertFalse(result.calibrated)
        self.assertEqual(model.artifacts().metadata["weights_status"], "unavailable")
        self.assertEqual(model.artifacts().metadata["fallback"], "no_history")

    def test_blank_option_is_featurized_and_nontext_is_rejected(self):
        model = self.model()
        model.fit(self.history(), [])
        self.assertEqual(model.predict("new", ["", "simple new"]).choice, "b")
        for options in (["only"], ["simple", None]):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    model.predict("new", options)
