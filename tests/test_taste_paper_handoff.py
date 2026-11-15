"""M2/M3 handoff and evidence tests with deterministic synthetic responses."""
import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.research.advisor import TasteAdvisor
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import load_model
from tests.test_taste_methods import ColorOracle, choice


class PaperMethodHandoffTests(unittest.TestCase):
    def test_m2_exports_principles_without_changing_validated_predictor(self):
        model = create_method("m2", ColorOracle())
        model.fit([choice(1), choice(2)], [choice(3)])
        artifact = model.artifacts()
        self.assertTrue(artifact.persona)
        self.assertTrue(TasteAdvisor(model).principles())
        self.assertEqual(artifact.principles, artifact.metadata["retained_hypotheses"])
        result = model.predict("new decision", ["blue", "red"])
        self.assertEqual(result.choice, "b")
        # The selected persona/examples were validated together. Exporting rules
        # for the proposer must not silently inject a new predictor component.
        self.assertEqual(model.llm.payloads[-1]["principles"], [])
        self.assertEqual(model.llm.payloads[-1]["persona"], artifact.persona)
        self.assertFalse(result.calibrated)

    def test_m2_m3_save_load_preserves_prompts_and_evidence(self):
        for method in ("m2", "m3"):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as directory:
                model = create_method(method, ColorOracle())
                history = [choice(1), choice(2)]
                model.fit(history, [choice(3)])
                artifacts = model.artifacts()
                self.assertTrue(artifacts.metadata["extraction_prompts"])
                for evidence in artifacts.metadata["principle_evidence"]:
                    self.assertTrue(set(evidence["history_ids"]) <= {c.identity for c in history})
                    self.assertTrue(evidence["history_ids"])
                path = Path(directory) / "usermodel.json"
                model.save(path)
                restored = load_model(path, ColorOracle())
                self.assertEqual(restored.artifacts(), artifacts)
                self.assertEqual(TasteAdvisor(restored).principles(), artifacts.principles)
                self.assertEqual(restored.predict("new", ["blue", "red"]).choice, "b")

    def test_m3_never_sends_validation_to_model(self):
        left, right = create_method("m3", ColorOracle()), create_method("m3", ColorOracle())
        left.fit([choice(1), choice(2)], [choice(999, "a")])
        right.fit([choice(1), choice(2)], [choice(999, "b")])
        self.assertEqual(left.llm.payloads, right.llm.payloads)
        self.assertNotIn("999", json.dumps(left.llm.payloads))
        self.assertEqual(left.artifacts().principles, right.artifacts().principles)

    def test_m2_generation_sees_history_not_validation_labels(self):
        model = create_method("m2", ColorOracle())
        model.fit([choice(1), choice(2)], [choice(999)])
        proposals = [p for p in model.llm.payloads if "choice" in p or "hypotheses" in p]
        self.assertNotIn("999", json.dumps(proposals))
        for payload in model.llm.payloads:
            if "options" in payload:
                self.assertNotIn("chosen", payload)


if __name__ == "__main__":
    unittest.main()
