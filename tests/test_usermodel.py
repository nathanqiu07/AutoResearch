import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.llm import LLM


class RecordingLLM(LLM):
    name = "test-recording"

    def __init__(self, answer=None):
        super().__init__()
        self.prompts = []
        self.answer = answer or {"probabilities": [0.2, 0.8], "rationale": "test"}

    def complete(self, prompt, **kwargs):
        self.prompts.append(prompt)
        self.budget.charge(10, 5)
        return json.dumps(self.answer)


class UserModelTests(unittest.TestCase):
    def api(self):
        from autoresearch.taste.usermodel import Choice
        from autoresearch.taste.methods import create_method
        return Choice, create_method

    def test_no_history_never_passes_personal_data(self):
        Choice, create = self.api()
        llm = RecordingLLM()
        model = create("m0", llm)
        model.fit([Choice("person-secret", "HISTORY-SECRET", "x", "y", "a")], [])
        pred = model.predict("new question", ["left", "right"])
        self.assertEqual(pred.choice, "b")
        self.assertEqual(pred.confidence, 0.8)
        self.assertFalse(pred.calibrated)
        self.assertNotIn("HISTORY-SECRET", llm.prompts[0])
        self.assertNotIn("person-secret", llm.prompts[0])
        self.assertEqual(model.artifacts().exemplars, [])

    def test_history_is_seeded_and_validation_not_in_prompt(self):
        Choice, create = self.api()
        history = [Choice("u", "past%d" % i, "x", "y", "a", example_id=str(i)) for i in range(8)]
        models = [create("m1", RecordingLLM(), seed=9, k=5) for _ in range(2)]
        for model in models:
            model.fit(history, [Choice("u", "VAL-SECRET", "v", "w", "b")])
            model.predict("query", ["a1", "b1"])
        self.assertEqual(models[0].artifacts().exemplars, models[1].artifacts().exemplars)
        self.assertEqual(len(models[0].artifacts().exemplars), 5)
        self.assertNotIn("VAL-SECRET", models[0].llm.prompts[-1])

    def test_fit_rejects_mixed_users_and_overlap(self):
        Choice, create = self.api()
        model = create("m1", RecordingLLM())
        c = Choice("u", "q", "a", "b", "a", example_id="same")
        with self.assertRaises(ValueError):
            model.fit([c], [c])
        with self.assertRaises(ValueError):
            model.fit([c, Choice("v", "q", "a", "b", "b")], [])

    def test_fit_rejects_reversed_duplicate_with_distinct_ids(self):
        Choice, create = self.api()
        a = Choice("u", "q", "left", "right", "a", example_id="1")
        b = Choice("u", "q", "right", "left", "b", example_id="2")
        with self.assertRaises(ValueError):
            create("m1", RecordingLLM()).fit([a], [b])

    def test_blank_response_is_preserved(self):
        Choice, create = self.api()
        model = create("m1", RecordingLLM())
        model.fit([Choice("u", "q", "", "answer", "b")], [])
        model.predict("q2", ["", "answer"])
        self.assertEqual(model.artifacts().exemplars[0]["a_text"], "")

    def test_bad_probabilities_fail_instead_of_fake_prediction(self):
        _, create = self.api()
        for probabilities in ([0.9], [float("nan"), 0.1], [-0.2, 1.2], [0.1, 0.2]):
            with self.subTest(probabilities=probabilities):
                model = create("m0", RecordingLLM({"probabilities": probabilities}))
                with self.assertRaises(ValueError):
                    model.predict("q", ["a", "b"])

    def test_multiple_options_and_cached_calls(self):
        _, create = self.api()
        with tempfile.TemporaryDirectory() as d:
            llm = RecordingLLM({"probabilities": [0.1, 0.2, 0.7]})
            model = create("m0", llm, cache_dir=d)
            self.assertEqual(model.predict("q", ["a", "b", "c"]).choice, "c")
            model.predict("q", ["a", "b", "c"])
            self.assertEqual(len(llm.prompts), 1)
            self.assertEqual(model.cost["cache_hits"], 1)

    def test_cache_separates_backend_endpoints(self):
        _, create = self.api()
        with tempfile.TemporaryDirectory() as d:
            a, b = RecordingLLM(), RecordingLLM()
            a.base_url, b.base_url = "http://one/v1", "http://two/v1"
            create("m0", a, cache_dir=d).predict("q", ["a", "b"])
            create("m0", b, cache_dir=d).predict("q", ["a", "b"])
            self.assertEqual(len(b.prompts), 1)

    def test_export_reload_preserves_baseline_and_profile_adapter(self):
        Choice, create = self.api()
        from autoresearch.taste.usermodel import load_model
        model = create("m1", RecordingLLM(), k="all")
        model.fit([Choice("u", "q", "a", "b", "b")], [])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "usermodel.json"
            model.save(path)
            loaded = load_model(path, RecordingLLM())
            self.assertEqual(loaded.artifacts().exemplars, model.artifacts().exemplars)
            self.assertEqual(loaded.predict("q2", ["x", "y"]).choice, "b")
            self.assertEqual(loaded.artifacts().to_profile("u").researcher, "u")

    def test_call_cap_stops_before_extra_backend_request(self):
        _, create = self.api()
        llm = RecordingLLM()
        model = create("m0", llm, max_calls=1)
        model.predict("q1", ["a", "b"])
        with self.assertRaises(RuntimeError):
            model.predict("q2", ["a", "b"])
        self.assertEqual(len(llm.prompts), 1)

    def test_failed_attempts_share_the_run_cap_across_models(self):
        _, create = self.api()
        class FailingLLM(RecordingLLM):
            def complete(self, prompt, **kwargs):
                self.prompts.append(prompt)
                raise RuntimeError("backend unavailable")
        llm = FailingLLM()
        llm.budget.max_calls = 1
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                create("m0", llm).predict("q", ["a", "b"])
        self.assertEqual(len(llm.prompts), 1)

    def test_reload_rejects_different_backend_identity(self):
        _, create = self.api()
        from autoresearch.taste.usermodel import load_model
        a, b = RecordingLLM(), RecordingLLM()
        a.model, b.model = "development", "evaluation"
        model = create("m0", a)
        model.fit([], [])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "model.json"
            model.save(p)
            with self.assertRaisesRegex(ValueError, "backend"):
                load_model(p, b)
