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


def mutating_builder(documents, config, extractor):
    config.update(researcher_id="wrong", allowed_sources=[], allowed_source_manifest_hash="f" * 64)
    return {"content": "synthetic output"}


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

    def test_rehashed_serialized_profile_cannot_bypass_cap_or_count(self):
        profile = self.build()
        for change in ("cap", "count"):
            body = profile.to_dict()
            if change == "cap":
                body["personalization_cap"] = 1
                body["config"]["personalization_cap"] = 1
                body["config_id"] = self.c.digest(body["config"])
            else:
                body["token_count"] = 1
            body.pop("profile_id")
            body["profile_id"] = self.c.digest(body)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "cap|count"):
                self.c.ProfileArtifact.from_dict(body)

    def test_explicit_consumer_failure_status_never_becomes_prediction(self):
        from autoresearch.taste.overnight.consumer import predict_profile, ProfileFailure
        profile = self.build()
        for status in ("invalid", "unavailable", "unsupported", "empty", "abstained", "unknown"):
            backend = RecordingConsumer({"status": status, "probabilities": [0.25, 0.75]})
            with self.subTest(status=status), self.assertRaises(ProfileFailure) as raised:
                predict_profile(profile, "q", ["a", "b"], backend, self.prediction_config(profile))
            self.assertEqual(raised.exception.status, status if status != "unknown" else "invalid")

    def test_huge_probability_is_typed_invalid_instead_of_overflow(self):
        from autoresearch.taste.overnight.consumer import predict_profile, ProfileFailure
        profile = self.build()
        backend = RecordingConsumer({"probabilities": [10 ** 400, 0]})
        with self.assertRaises(ProfileFailure) as raised:
            predict_profile(profile, "q", ["a", "b"], backend, self.prediction_config(profile))
        self.assertEqual(raised.exception.status, "invalid")

    def test_builder_cannot_rewrite_authoritative_provenance(self):
        self.r.register_builder("mutating-fixture", mutating_builder, prompt_version="v1", prompt_sha256="a" * 64)
        profile = self.build(method_id="mutating-fixture")
        self.assertEqual(profile.researcher_id, "synthetic")
        self.assertEqual(profile.allowed_source_manifest_hash, self.config["allowed_source_manifest_hash"])
        self.assertEqual(profile.config["allowed_sources"], self.config["allowed_sources"])

    def test_rehashed_profile_rejects_conflicting_source_provenance(self):
        body = self.build().to_dict()
        body["allowed_source_manifest_hash"] = "f" * 64
        body.pop("profile_id")
        body["profile_id"] = self.c.digest(body)
        with self.assertRaisesRegex(ValueError, "config|source"):
            self.c.ProfileArtifact.from_dict(body)

    def test_peer_source_permission_requires_literal_true(self):
        self.docs[0]["researcher_id"] = "peer"
        for invalid_flag in ("false", 1, [], None):
            with self.subTest(flag=invalid_flag), self.assertRaisesRegex(ValueError, "peer"):
                self.build(approved_peer_sources=invalid_flag)


if __name__ == "__main__":
    unittest.main()
