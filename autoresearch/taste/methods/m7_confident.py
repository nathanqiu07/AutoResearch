"""M6 with a separate conversation-level calibration partition and binary Platt fit."""
from ..usermodel import Prediction, UserModel
from .common import apply_platt, bounded_float, bounded_int, fit_platt, partition_calibration
from .m5_hybrid import Hybrid
from .m6_verified import VerifiedHybrid


class ConfidentHybrid(VerifiedHybrid):
    method_id = "m7"

    def fit(self, history, val):
        # Validate the full boundary before withholding the calibration partition.
        UserModel.fit(self, history, val)
        fraction = bounded_float(self.config, "calibration_fraction", .5, minimum=.01, maximum=.99)
        minimum = bounded_int(self.config, "calibration_min_samples", 8, minimum=2, maximum=1000)
        regularization = bounded_float(self.config, "calibration_regularization", .01, minimum=1e-6, maximum=10.)
        tuning, calibration = partition_calibration(val, self.seed, fraction)
        super().fit(history, tuning)
        # All inner fit/search steps have finished before these labels are used.
        probabilities = [Hybrid.predict(self, row.context, [row.a_text, row.b_text]).probabilities[0]
                         for row in calibration]
        state = fit_platt(probabilities, [int(row.chosen == "a") for row in calibration],
                          min_samples=minimum, regularization=regularization)
        self._artifacts.metadata.update(
            adaptation=self._artifacts.metadata["adaptation"] +
                       " Binary regularized Platt scaling on a separate conversation partition.",
            calibration=state, tuning_ids=[c.identity for c in tuning],
            calibration_ids=[c.identity for c in calibration], validation_ids=[c.identity for c in val],
            confidence_status="binary_calibrated" if state["fitted"] else "uncalibrated_" + state["reason"],
            multi_option_confidence_status="uncalibrated_transfer")

    def predict(self, context, options):
        raw = Hybrid.predict(self, context, options)
        state = self._artifacts.metadata.get("calibration", {})
        if len(options) != 2 or not state.get("fitted"):
            return raw
        p = apply_platt(raw.probabilities[0], state)
        probabilities = [p, 1. - p]
        index = 0 if p >= .5 else 1
        return Prediction("a" if index == 0 else "b", probabilities[index],
                          "Binary calibrated prediction. Raw judgment: " + raw.rationale,
                          probabilities, calibrated=True)
