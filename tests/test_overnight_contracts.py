import hashlib
import json
import unittest

from autoresearch.llm import LLM


class RecordingConsumer(LLM):
    name = "offline-fixture"
    model = "fixture-v1"

    def __init__(self, response=None):
        super().__init__()
        self.response = response or {"probabilities": [0.25, 0.75], "rationale": "fixture"}
        self.prompts = []

    def complete(self, prompt, **settings):
        self.prompts.append((prompt, settings))
        self.budget.charge(10, 5)
        return json.dumps(self.response)


def fixture_builder(documents, config, extractor):
    return {"content": {"prose": "Prefer discriminating tests.",
                        "claims": [{"text": "Use matched controls", "source_ids": ["fit-1"]}],
                        "hypotheses": [{"date": "2026", "condition": "uncertain", "text": "Replicate"}]}}


def empty_builder(documents, config, extractor):
    return {"content": {}}


class ContractTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import contracts, registry
        self.c, self.r = contracts, registry
        for method, builder, empty in [("fixture", fixture_builder, False), ("no-profile", empty_builder, True)]:
            registry.register_builder(method, builder, prompt_version="fixture-v1",
                                      prompt_sha256="a" * 64, allows_empty=empty)
        content = "A synthetic fit source."
        self.docs = [{"document_id": "fit-1", "researcher_id": "synthetic", "content": content,
                      "content_sha256": hashlib.sha256(content.encode()).hexdigest()}]
        sources = [{"document_id": d["document_id"], "content_sha256": d["content_sha256"]} for d in self.docs]
        self.config = {"method_id": "fixture", "researcher_id": "synthetic", "allowed_sources": sources,
                       "allowed_source_manifest_hash": contracts.digest(sources), "personalization_cap": 2048,
                       "replicate_id": 0, "code_sha": "b" * 40, "extractor_settings": {}}

    def build(self, **changes):
        return self.c.build_profile(self.docs, dict(self.config, **changes), RecordingConsumer())

    def prediction_config(self, profile):
        from autoresearch.taste.overnight.consumer import implementation_hash, PROMPT_VERSION
        return {"method_implementation_hash": profile.method_implementation_hash,
                "renderer_implementation_hash": implementation_hash(),
                "profile_prompt_version": profile.prompt_version,
                "consumer_prompt_version": PROMPT_VERSION,
                "settings": {"temperature": 0.0, "max_tokens": 128}}

    def test_contract_exists(self):
        self.assertTrue(callable(self.c.build_profile))

    def test_source_content_and_exact_set_checked_before_builder(self):
        profile = self.build()
        self.assertEqual(profile.status, "complete")
        self.docs[0]["content"] += "TAMPERED"
        with self.assertRaisesRegex(ValueError, "content hash"):
            self.build()
        with self.assertRaisesRegex(ValueError, "source set"):
            self.c.build_profile([], self.config, RecordingConsumer())

    def test_artifact_is_deeply_immutable_and_content_addressed(self):
        profile = self.build()
        altered = profile.to_dict()
        altered["content"]["prose"] = "changed"
        self.assertEqual(profile.content["prose"], "Prefer discriminating tests.")
        with self.assertRaisesRegex(ValueError, "hash"):
            self.c.ProfileArtifact.from_dict(altered)
        self.assertEqual(self.c.ProfileArtifact.from_dict(profile.to_dict()).profile_id, profile.profile_id)

    def test_rich_fields_reach_prediction_without_labels_or_metadata(self):
        from autoresearch.taste.overnight.consumer import predict_profile
        profile, backend = self.build(), RecordingConsumer()
        pred = predict_profile(profile, "A new question", ["left", "right"], backend,
                               self.prediction_config(profile))
        payload = json.loads(backend.prompts[0][0].split("INPUT_JSON:\n", 1)[1])
        self.assertEqual(set(payload), {"context", "options", "personalization"})
        self.assertEqual(json.loads(payload["personalization"]), profile.content)
        self.assertEqual(pred.choice, "b")
        self.assertFalse(pred.calibrated)
        self.assertNotIn("allowed_sources", backend.prompts[0][0])

    def test_mismatched_implementation_or_prompt_never_calls_backend(self):
        from autoresearch.taste.overnight.consumer import predict_profile, ProfileFailure
        profile, backend = self.build(), RecordingConsumer()
        for key in ("method_implementation_hash", "renderer_implementation_hash", "profile_prompt_version", "consumer_prompt_version"):
            config = self.prediction_config(profile)
            config[key] = "different"
            with self.subTest(key=key), self.assertRaises(ProfileFailure) as raised:
                predict_profile(profile, "q", ["a", "b"], backend, config)
            self.assertEqual(raised.exception.status, "unavailable")
        self.assertEqual(backend.prompts, [])

    def test_empty_candidate_and_intentional_empty_control_are_distinct(self):
        from autoresearch.taste.overnight.consumer import predict_profile, ProfileFailure
        self.r.register_builder("empty-fixture", empty_builder, prompt_version="fixture-v1", prompt_sha256="a" * 64)
        profile, backend = self.build(method_id="empty-fixture"), RecordingConsumer()
        self.assertEqual(profile.status, "empty")
        with self.assertRaises(ProfileFailure) as raised:
            predict_profile(profile, "q", ["a", "b"], backend, self.prediction_config(profile))
        self.assertEqual(raised.exception.status, "empty")
        control = self.build(method_id="no-profile")
        predict_profile(control, "q", ["a", "b"], backend, self.prediction_config(control))
        payload = json.loads(backend.prompts[0][0].split("INPUT_JSON:\n", 1)[1])
        self.assertEqual(payload["personalization"], "")

    def test_oversized_and_bad_probabilities_have_explicit_status(self):
        from autoresearch.taste.overnight.consumer import predict_profile, ProfileFailure
        self.assertEqual(self.build(personalization_cap=1).status, "invalid")
        profile = self.build()
        for probabilities in ([0.1], [0.2, 0.2], [float("nan"), 1.0], [True, 0]):
            backend = RecordingConsumer({"probabilities": probabilities})
            with self.subTest(probabilities=probabilities), self.assertRaises(ProfileFailure) as raised:
                predict_profile(profile, "q", ["a", "b"], backend, self.prediction_config(profile))
            self.assertEqual(raised.exception.status, "invalid")


if __name__ == "__main__":
    unittest.main()
