"""Algorithm and contract checks; synthetic fixtures are not fidelity evidence."""
import importlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from autoresearch.llm import LLM
from autoresearch.taste.usermodel import Choice, load_model


def module(name):
    try:
        return importlib.import_module("autoresearch.taste.methods." + name)
    except ModuleNotFoundError as exc:
        raise AssertionError("Required method module is not implemented: " + name) from exc


class ColorOracle(LLM):
    """Independent tiny preference world: users favor red; generic judges favor blue."""
    name = "synthetic-color-oracle"

    def __init__(self):
        super().__init__()
        self.payloads = []

    def complete(self, prompt, **kwargs):
        instruction, encoded = prompt.split("\nINPUT_JSON:\n", 1)
        data = json.loads(encoded)
        self.payloads.append(data)
        if "hypothesis" in instruction:
            chosen = data["choice"][data["choice"]["chosen"] + "_text"]
            value = {"hypothesis": "Prefer red." if "red" in chosen else "Prefer blue."}
        elif "principles" in instruction and "Propose" in instruction:
            chosen = data["choice"][data["choice"]["chosen"] + "_text"]
            value = {"principles": ["Prefer red." if "red" in chosen else "Prefer blue."]}
        elif "persona" in instruction and "Write" in instruction:
            value = {"persona": "\n".join(data["hypotheses"])}
        else:
            personal = " ".join(data["principles"]) + " " + data["persona"]
            for example in data["past_choices"]:
                personal += " " + example[example["chosen"] + "_text"]
            color = "red" if "red" in personal else "blue"
            values = [4.0 if color in text else 1.0 for text in data["options"]]
            value = {"probabilities": [x / sum(values) for x in values], "rationale": color}
        result = json.dumps(value)
        self.budget.charge(len(prompt) // 4, len(result) // 4)
        return result


def choice(i, chosen="a", group=None):
    return Choice("person", "color question %s" % i, "red %s" % i, "blue %s" % i,
                  chosen, example_id=str(i), group_id=group or "conversation-%s" % i)


class SelectionTests(unittest.TestCase):
    def test_forward_selection_uses_gain_and_interactions(self):
        c = module("common")
        # A is initially best; B helps only after A; C never helps.
        scores = {(): 0.0, ("A",): .5, ("B",): 0., ("C",): 0.,
                  ("A", "B"): 1., ("A", "C"): .5, ("A", "B", "C"): 1.}
        kept, trace = c.forward_select(["A", "B", "C"], lambda xs: scores[tuple(xs)], 3)
        self.assertEqual(kept, ["A", "B"])
        self.assertTrue(trace)

    def test_filter_rechecks_after_deletion_and_keeps_ties(self):
        c = module("common")
        # A harms initially. B becomes harmful after A is removed. C is neutral.
        scores = {("A", "B", "C"): .2, ("B", "C"): .6, ("A", "C"): .1,
                  ("A", "B"): .2, ("C",): .9, ("B",): .6, (): .9}
        kept, trace = c.remove_harmful(["A", "B", "C"], lambda xs: scores[tuple(xs)])
        self.assertEqual(kept, ["C"])
        self.assertEqual(sum(bool(t.get("removed")) for t in trace), 2)

    def test_clusters_remove_duplicates_but_preserve_negation(self):
        c = module("common")
        texts = ["Prefer concise answers.", "prefer concise answers", "Do not prefer concise answers.",
                 "Use detailed mathematical proofs."]
        clusters = c.cluster_principles(texts, threshold=.5)
        self.assertEqual(sorted(len(x["members"]) for x in clusters), [1, 1, 2])
        self.assertEqual(c.cosine({}, {}), 0.)


class MethodTests(unittest.TestCase):
    def test_save_load_restores_all_five_methods_without_refitting(self):
        classes = [("m2_synthesizeme", "SynthesizeMe"), ("m3_icai", "InverseConstitutional"),
                   ("m5_hybrid", "Hybrid"), ("m6_verified", "VerifiedHybrid"),
                   ("m7_confident", "ConfidentHybrid")]
        rows = [choice(i, chosen="a" if i % 3 else "b") for i in range(10, 30)]
        with tempfile.TemporaryDirectory() as directory:
            for filename, name in classes:
                model = getattr(module(filename), name)(ColorOracle(), seed=7)
                model.fit([choice(1), choice(2)], rows)
                before = model.predict("color", ["blue", "red"])
                path = Path(directory) / (model.method_id + ".json")
                model.save(path)
                restored = load_model(path, ColorOracle())
                after = restored.predict("color", ["blue", "red"])
                self.assertEqual((before.choice, before.probabilities, before.calibrated),
                                 (after.choice, after.probabilities, after.calibrated))
                self.assertEqual(restored.cost["calls"], 1)

    def test_persona_fallback_respects_text_cap(self):
        class BadSummaryOracle(ColorOracle):
            def complete(self, prompt, **kwargs):
                if prompt.startswith("Explain why"):
                    return json.dumps({"hypothesis": "Prefer red. " + "detail " * 30})
                if prompt.startswith("Write a short persona"):
                    return json.dumps({"persona": "Prefer blue."})
                return super().complete(prompt, **kwargs)

        model = module("m2_synthesizeme").SynthesizeMe(BadSummaryOracle(), max_persona_chars=20)
        model.fit([choice(1)], [choice(2)])
        self.assertLessEqual(len(model.artifacts().persona), 20)

    def test_filter_bounds_persona_components_without_losing_text(self):
        class ManyLinesOracle(ColorOracle):
            def complete(self, prompt, **kwargs):
                if prompt.startswith("Write a short persona"):
                    return json.dumps({"persona": "\n".join("Prefer red. Detail %s" % i for i in range(20))})
                return super().complete(prompt, **kwargs)

        model = module("m6_verified").VerifiedHybrid(ManyLinesOracle(), max_persona_lines=5)
        model.fit([choice(1)], [choice(2)])
        persona_parts = [text for kind, text in model.artifacts().metadata["filter_components"]
                         if kind == "persona"]
        self.assertLessEqual(len(persona_parts), 5)
        self.assertIn("Detail 19", model.artifacts().persona)

    def test_bad_search_bounds_fail_before_calling_model(self):
        cls = module("m2_synthesizeme").SynthesizeMe
        for config in [{"max_history": True}, {"max_hypotheses": -1}, {"max_exemplars": 100000}]:
            model = cls(ColorOracle(), **config)
            with self.assertRaises(ValueError):
                model.fit([choice(1)], [choice(2)])
            self.assertEqual(model.cost["calls"], 0)

    def test_m2_and_m3_learn_rule_without_prediction_label_leakage(self):
        for filename, name in [("m2_synthesizeme", "SynthesizeMe"),
                               ("m3_icai", "InverseConstitutional")]:
            llm = ColorOracle()
            model = getattr(module(filename), name)(llm, max_history=3)
            model.fit([choice(1), choice(2)], [choice(3), choice(4)])
            self.assertEqual(model.predict("new", ["blue toy", "red toy"]).choice, "b")
            self.assertEqual(model.predict("new", ["red toy", "blue toy"]).choice, "a")
            self.assertIn("adaptation", model.artifacts().metadata)
            for payload in llm.payloads:
                if "options" in payload:
                    self.assertNotIn("chosen", payload)
                    self.assertNotIn("reason", payload)

    def test_no_validation_explicitly_marks_unverified_fallback(self):
        for filename, name in [("m2_synthesizeme", "SynthesizeMe"),
                               ("m6_verified", "VerifiedHybrid")]:
            model = getattr(module(filename), name)(ColorOracle())
            model.fit([choice(1)], [])
            self.assertIn("unverified", model.artifacts().metadata["verification_status"])

    def test_hybrid_retrieves_context_and_survives_artifact_restore(self):
        cls = module("m5_hybrid").Hybrid
        model = cls(ColorOracle(), max_exemplars=1)
        history = [Choice("person", "astronomy planets", "red star", "blue star", "a", example_id="s"),
                   Choice("person", "cooking dinner", "red tomato", "blue tomato", "a", example_id="f")]
        model.fit(history, [])
        clone = cls(ColorOracle(), max_exemplars=1)
        clone._artifacts = model.artifacts()
        result = clone.predict("astronomy planets", ["blue planet", "red planet"])
        self.assertEqual(result.choice, "b")
        self.assertEqual(clone.llm.payloads[-1]["past_choices"][0]["example_id"], "s")

    def test_method_call_cap_covers_both_hybrid_children(self):
        model = module("m5_hybrid").Hybrid(ColorOracle(), max_calls=1)
        with self.assertRaisesRegex(RuntimeError, "budget"):
            model.fit([choice(1), choice(2)], [choice(3)])
        self.assertLessEqual(model.cost["calls"], 1)


class CalibrationTests(unittest.TestCase):
    def test_calibration_can_change_binary_choice_coherently(self):
        cls = module("m7_confident").ConfidentHybrid
        model = cls(ColorOracle())
        model.fit([choice(1)], [])
        model._artifacts.metadata["calibration"] = {"fitted": True, "a": -1., "b": 0.}
        result = model.predict("new", ["red", "blue"])
        self.assertEqual(result.choice, "b")
        self.assertTrue(result.calibrated)
        self.assertAlmostEqual(result.probabilities[0], .2)
        self.assertAlmostEqual(result.confidence, .8)

    def test_platt_reduces_loss_on_independent_overconfidence_fixture(self):
        c = module("common")
        # Both train and held-out sets have known 3/4 frequencies, raw p=.99/.01.
        p = [.99] * 40 + [.01] * 40
        y = ([1, 1, 1, 0] * 10) + ([0, 0, 0, 1] * 10)
        fit = c.fit_platt(p, y, min_samples=8)
        self.assertTrue(fit["fitted"])
        raw_loss = (-3 * math.log(.99) - math.log(.01)) / 4
        calibrated = c.apply_platt(.99, fit)
        heldout_loss = (-3 * math.log(calibrated) - math.log(1 - calibrated)) / 4
        self.assertLess(heldout_loss, raw_loss)
        self.assertGreater(calibrated, .5)
        self.assertLess(calibrated, .9)
        self.assertAlmostEqual(c.apply_platt(.01, fit), 1 - calibrated, places=5)

    def test_degenerate_calibration_stays_uncalibrated(self):
        c = module("common")
        for p, y in [([], []), ([.9] * 10, [1] * 10), ([.9, .1], [1, 0])]:
            self.assertFalse(c.fit_platt(p, y, min_samples=8)["fitted"])

    def test_calibration_partition_keeps_conversations_together(self):
        c = module("common")
        rows = [choice(i, group="g%s" % (i // 2)) for i in range(12)]
        tune, cal = c.partition_calibration(rows, seed=19)
        self.assertTrue(tune and cal)
        self.assertFalse({x.group_id for x in tune} & {x.group_id for x in cal})
        self.assertEqual({x.identity for x in tune + cal}, {x.identity for x in rows})

    def test_m7_calibration_labels_cannot_change_fitted_taste(self):
        c = module("common")
        cls = module("m7_confident").ConfidentHybrid
        rows = [choice(i, chosen="a" if i % 3 else "b") for i in range(10, 30)]
        _, cal = c.partition_calibration(rows, seed=7)
        cal_ids = {x.identity for x in cal}
        changed = [Choice(**{**x.__dict__, "chosen": ("b" if x.chosen == "a" else "a")})
                   if x.identity in cal_ids else x for x in rows]
        first, second = cls(ColorOracle(), seed=7), cls(ColorOracle(), seed=7)
        first.fit([choice(1), choice(2)], rows)
        second.fit([choice(1), choice(2)], changed)
        a, b = first.artifacts(), second.artifacts()
        self.assertEqual((a.principles, a.persona, a.exemplars), (b.principles, b.persona, b.exemplars))
        self.assertFalse(first.predict("three", ["red", "blue", "green"]).calibrated)
        prediction = first.predict("two", ["red", "blue"])
        self.assertAlmostEqual(sum(prediction.probabilities), 1.)
        self.assertEqual(prediction.confidence, max(prediction.probabilities))
        clone = cls(ColorOracle(), seed=7)
        clone._artifacts = first.artifacts()
        restored = clone.predict("two", ["red", "blue"])
        self.assertEqual(prediction.probabilities, restored.probabilities)


if __name__ == "__main__":
    unittest.main()
