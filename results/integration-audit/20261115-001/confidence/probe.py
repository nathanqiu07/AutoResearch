#!/usr/bin/env python3
"""Offline behavior probe. Does not construct or call an external backend."""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace as NS

sys.dont_write_bytecode = True


def strict_value(value):
    """Preserve nonfinite observations without emitting invalid JSON numbers."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_float": "NaN" if math.isnan(value) else ("+Infinity" if value > 0 else "-Infinity")}
    if isinstance(value, dict):
        return {key: strict_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [strict_value(item) for item in value]
    return value


def attempt(call):
    try:
        return {"status": "returned", "value": strict_value(call())}
    except Exception as exc:
        return {"status": "raised", "error_type": type(exc).__name__, "message": str(exc)[:200]}


class Constant:
    def __init__(self, **values):
        self.values = values
        self.calls = 0

    def predict(self, context, options):
        self.calls += 1
        return NS(**self.values)


class Features:
    def __init__(self, probabilities):
        self.probabilities = probabilities

    def predict_features(self, context, features):
        return self.probabilities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.repo).resolve()))
    from autoresearch.research.advisor import TasteAdvisor, ProfileUserModel
    from autoresearch.taste.profile import TasteProfile
    from autoresearch.taste.usermodel import UserModel, TasteArtifacts

    def exercise(model):
        advisor = TasteAdvisor(model)
        return {
            "consult": attempt(lambda: asdict(advisor.consult("c", ["A", "B"]))),
            "decide_nondecisive": attempt(lambda: advisor.decide("c", ["A", "B"], 1, False)[0]),
            "decide_decisive": attempt(lambda: advisor.decide("c", ["A", "B"], 1, True)[0]),
            "d1": attempt(lambda: advisor.d1_scores("c", ["A", "B"], [{}, {}])[0]),
            "logged_errors": advisor.errors,
        }

    result = {}
    confidences = [
        ("negative", -1), ("above_one", 2), ("nan", float("nan")),
        ("pos_inf", float("inf")), ("neg_inf", -float("inf")),
        ("numeric_string", "0.9"), ("bool", True), ("overflow_int", 10**1000),
    ]
    for name, value in confidences:
        result["confidence:" + name] = exercise(Constant(choice="a", confidence=value))
    choices = [("unknown", "zzz"), ("bool", True), ("outside", 5),
               ("superscript_digit", "²"), ("multichar_lower", "İ")]
    for name, value in choices:
        result["choice:" + name] = exercise(Constant(choice=value, confidence=.9))
    distributions = [
        ("normal", [.9, .1]), ("nan", [float("nan"), .1]),
        ("pos_inf", [float("inf"), 0]), ("negative", [-.2, 1.2]),
        ("bad_sum", [.2, .3]), ("bool", [True, False]),
        ("strings", ["0.9", "0.1"]), ("wrong_length", [.9]),
        ("opposite_argmax", [.1, .9]), ("overflow_int", [10**1000, 0]),
    ]
    for name, value in distributions:
        result["probability:" + name] = exercise(Constant(choice="a", confidence=.9, probabilities=value))
    for calibrated in (False, True):
        result["calibrated:" + str(calibrated)] = exercise(Constant(
            choice="a", confidence=.9, probabilities=[.9, .1], calibrated=calibrated))
    for name, value in [("low_conf", [.55, .45]), ("negative", [-.2, 1.2]),
                        ("nan", [float("nan"), .1]), ("pos_inf", [float("inf"), 0]),
                        ("bad_sum", [.2, .3]), ("uniform", [.5, .5])]:
        advisor = TasteAdvisor(Features(value))
        def feature_case():
            scores, advice = advisor.d1_scores("c", ["A", "B"], [{}, {}])
            return {"scores": scores, "advice": asdict(advice), "logged_errors": advisor.errors}
        result["features:" + name] = attempt(feature_case)
    for name, weights in [("empty", {}), ("weak", {"x": .2}),
                          ("nan", {"x": float("nan")}), ("pos_inf", {"x": float("inf")})]:
        advisor = TasteAdvisor(ProfileUserModel(TasteProfile("fixture", weights)))
        def profile_case():
            scores, advice = advisor.d1_scores("c", ["A", "B"], [{"x": 1}, {"x": 0}])
            return {"scores": scores, "advice": asdict(advice), "logged_errors": advisor.errors}
        result["real_profile:" + name] = attempt(profile_case)

    # Exercise actual base parser using fixed local responses; no LLM is initialized.
    for name, probabilities in distributions:
        model = object.__new__(UserModel)
        model._artifacts = TasteArtifacts()
        model._json = lambda *args, p=probabilities: {"probabilities": p}
        result["base_parser:" + name] = attempt(lambda: asdict(model.predict("c", ["A", "B"])))
        result["base_parser_via_adviser:" + name] = exercise(model)

    model = object.__new__(UserModel)
    model._artifacts = TasteArtifacts()
    payloads = []
    def response(instruction, payload):
        payloads.append({"instruction": instruction, "payload": payload})
        return {"probabilities": [.9, .1]}
    model._json = response
    advisor = TasteAdvisor(model)
    result["empty_text_profile"] = {
        "advice": asdict(advisor.consult("c", ["A", "B"])),
        "principles": advisor.principles(), "request": payloads[-1],
    }

    # Use the real D1 implementation without constructing a full run or backend.
    from autoresearch.research.loop import OpenResearcher
    researcher = object.__new__(OpenResearcher)
    researcher.sc = NS(name="offline-fixture")
    researcher.advisor = TasteAdvisor(ProfileUserModel(TasteProfile("bad", {"realism": float("nan")})))
    ideas = [NS(features={"realism": 1}, category="fixture", text="A"),
             NS(features={"realism": 0}, category="fixture", text="B")]
    designs = [("add:a", None, ideas[0]), ("add:b", None, ideas[1])]
    def loop_case():
        researcher._d1(0, designs, NS(interventions=[]))
        return {"scores": researcher._tscore,
                "all_finite": all(math.isfinite(value) for value in researcher._tscore.values())}
    result["actual_loop_d1_nan"] = attempt(loop_case)
    print(json.dumps(strict_value(result), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
