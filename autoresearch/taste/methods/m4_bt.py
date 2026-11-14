"""Bradley--Terry weights over a fixed, label-blind text feature map."""
import math

from ..choices import fit_choice_model_cv
from ..profile import FEATURES
from ..usermodel import Prediction, UserModel


class BradleyTerry(UserModel):
    method_id = "m4"
    prompt_version = "m4-features-v1"

    def _features(self, context, option):
        # A single option has no A/B position or companion option to leak its label.
        instruction = (
            "Describe the supplied option in its context using a fixed feature map. "
            "Do not predict a person's preference. Score each feature from 0 to 1: "
            "realism = practical plausibility; grounding = support from concrete evidence; "
            "simplicity = ease of understanding or execution; novelty = originality; "
            "cost = time, effort, or resources required; risk = potential for harm or failure; "
            "validity_care = care about correctness, limits, and checking claims. "
            "An empty option is a blank response; assess it as such. "
            "Return {\"features\": {" + ", ".join('"%s": 0.0' % f for f in FEATURES) + "}}."
        )
        result = self._json(instruction, {"context": context, "option": option})
        features = result.get("features")
        if (not isinstance(features, dict) or set(features) != set(FEATURES) or
                any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                    not math.isfinite(v) or not 0 <= v <= 1 for v in features.values())):
            raise ValueError("features must contain every fixed feature with a finite value in [0, 1]")
        return features

    def fit(self, history, val):
        super().fit(history, val)
        self._artifacts.metadata.update({
            "feature_schema": "m4-features-v1",
            "feature_range": [0, 1],
            "training_examples": len(self.history),
            "regularization": {"l2": 0.5, "selection": "fixed_default_without_prior"},
        })
        if not self.history:
            self._artifacts.metadata["fallback"] = "no_history"
            return
        rows = [{"a": self._features(c.context, c.a_text),
                 "b": self._features(c.context, c.b_text), "chosen": c.chosen}
                for c in self.history]
        # The existing fitter uses fixed L2=0.5 without a prior, rather than doing CV.
        profile = fit_choice_model_cv(rows, self.history[0].user_id)
        self._artifacts.weights = dict(profile.weights)
        self._artifacts.metadata["weights_status"] = "learned"

    def predict(self, context, options):
        if not isinstance(context, str) or len(options) < 2:
            raise ValueError("prediction requires text context and at least two options")
        if any(not isinstance(option, str) for option in options):
            raise ValueError("options must be text (empty responses are allowed)")
        if self._artifacts.metadata.get("weights_status") != "learned":
            return self._predict_with(context, options)
        weights = self._artifacts.weights
        if (set(weights) != set(FEATURES) or
                any(isinstance(w, bool) or not isinstance(w, (int, float)) or
                    not math.isfinite(w) for w in weights.values())):
            raise ValueError("learned weights must contain every fixed feature with finite values")
        vectors = [self._features(context, option) for option in options]
        scores = [sum(weights[f] * vector[f] for f in FEATURES) for vector in vectors]
        if not all(math.isfinite(score) for score in scores):
            raise ValueError("non-finite Bradley-Terry score")
        maximum = max(scores)
        unnormalized = [math.exp(score - maximum) for score in scores]
        total = sum(unnormalized)
        probabilities = [p / total for p in unnormalized]
        index = max(range(len(scores)), key=scores.__getitem__)
        return Prediction(chr(ord("a") + index), probabilities[index],
                          "Highest learned feature score; probability is uncalibrated.",
                          probabilities, calibrated=False)
