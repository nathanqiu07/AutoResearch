import json
import unittest

from autoresearch.taste.overnight import contracts
from autoresearch.taste.overnight.consumer import PROMPT_VERSION, implementation_hash, prepare_payload
from tests.test_overnight_retrieval import documents, config


class NoCalls:
    label = "offline-fixture"
    model = "no-calls"

    def complete(self, *args, **kwargs):
        raise AssertionError("baseline must not call an extractor")


class BaselineTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight.baselines import register_baselines
        register_baselines()
        self.docs = documents()
        self.cfg = dict(config(self.docs), method_id="raw_evidence", personalization_cap=512,
                        replicate_id=0, code_sha="b" * 40, extractor_settings={},
                        summary_method_id="p1_fixture",
                        decision={"context": "controlled experiments", "options": ["replication", "exploration"]},
                        consumer_identity={"model": "fixture-v1"})

    def build(self, method, **extra):
        return contracts.build_profile(self.docs, dict(self.cfg, method_id=method, **extra), NoCalls())

    def payload(self, profile):
        return prepare_payload(profile, "new context", ["left", "right"],
                               {"method_implementation_hash": profile.method_implementation_hash,
                                "renderer_implementation_hash": implementation_hash(),
                                "profile_prompt_version": profile.prompt_version,
                                "consumer_prompt_version": PROMPT_VERSION})["payload"]

    def test_no_profile_and_name_only_have_no_hidden_evidence(self):
        empty = self.build("no_profile", personalization_cap=0)
        self.assertEqual(empty.status, "complete")
        self.assertEqual(self.payload(empty)["personalization"], "")
        named = self.build("name_only", researcher_name="Fixture Researcher")
        self.assertEqual(json.loads(self.payload(named)["personalization"]), {"name": "Fixture Researcher"})
        self.assertNotIn("Bananas", self.payload(named)["personalization"])

    def test_raw_and_lexical_share_format_and_match_cap(self):
        raw, lexical = self.build("raw_evidence"), self.build("lexical_retrieval")
        self.assertEqual(raw.status, "complete")
        self.assertEqual(lexical.status, "complete")
        self.assertEqual(raw.content["passages"][0]["document_id"], "d1")
        self.assertEqual(lexical.content["passages"][0]["document_id"], "d2")
        for profile in [raw, lexical]:
            self.assertLessEqual(profile.token_count, 512)
            self.assertEqual(set(profile.content), {"passages"})

    def test_semantic_missing_name_and_too_small_raw_are_explicit(self):
        semantic = self.build("semantic_retrieval")
        self.assertEqual(semantic.status, "unavailable")
        self.assertEqual(self.build("name_only").status, "unavailable")
        self.assertEqual(self.build("raw_evidence", personalization_cap=0).status, "unavailable")

    def test_frozen_summary_is_reused_exactly_and_source_mismatch_rejected(self):
        from autoresearch.taste.overnight.registry import register_builder
        register_builder("p1_fixture", summary_fixture, prompt_version="fixture-v1", prompt_sha256="c" * 64)
        summary = self.build("p1_fixture")
        reused = self.build("memory_summary", frozen_profile=summary.to_dict(), expected_profile_id=summary.profile_id)
        self.assertEqual(reused.content, summary.content)
        self.assertEqual(reused.fit_usage["reused_profile_id"], summary.profile_id)
        changed = summary.to_dict()
        changed["allowed_source_manifest_hash"] = "d" * 64
        changed["profile_id"] = contracts.digest({k: v for k, v in changed.items() if k != "profile_id"})
        rejected = self.build("memory_summary", frozen_profile=changed, expected_profile_id=changed["profile_id"])
        self.assertEqual(rejected.status, "unavailable")

    def test_hybrid_keeps_profile_and_fixed_allocations(self):
        from autoresearch.taste.overnight.registry import register_builder
        register_builder("p1_fixture", summary_fixture, prompt_version="fixture-v1", prompt_sha256="c" * 64)
        profile = self.build("p1_fixture")
        hybrid = self.build("profile_retrieval", frozen_profile=profile.to_dict(),
                            expected_profile_id=profile.profile_id, profile_cap=128)
        self.assertEqual(hybrid.status, "complete")
        self.assertEqual(hybrid.content["profile"], profile.content)
        self.assertTrue(hybrid.content["passages"])
        self.assertLessEqual(hybrid.token_count, 512)
        too_small = self.build("profile_retrieval", frozen_profile=profile.to_dict(),
                               expected_profile_id=profile.profile_id, profile_cap=1)
        self.assertEqual(too_small.status, "unavailable")

    def test_no_silent_retrieval_without_decision_or_consumer_identity(self):
        for changes in [{"decision": None}, {"consumer_identity": None},
                        {"decision": dict(self.cfg["decision"], actual="a")}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.build("lexical_retrieval", **changes)

    def test_retrieved_profile_cannot_predict_a_different_decision(self):
        from autoresearch.taste.overnight.baselines import predict_baseline
        from autoresearch.taste.overnight.consumer import ProfileFailure
        profile = self.build("lexical_retrieval")
        with self.assertRaisesRegex(ProfileFailure, "decision_mismatch"):
            predict_baseline(profile, "unrelated", ["left", "right"], NoCalls(), {})

    def test_frozen_artifact_identity_and_empty_profile_fail_closed(self):
        empty = self.build("no_profile")
        for changes in [{"frozen_profile": empty.to_dict(), "expected_profile_id": empty.profile_id},
                        {"frozen_profile": {"content": "fabricated"}, "expected_profile_id": "x"}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.build("memory_summary", **changes).status, "unavailable")

    def test_memory_summary_requires_declared_plain_summary_method(self):
        profile = self.build("raw_evidence")
        result = self.build("memory_summary", frozen_profile=profile.to_dict(),
                            expected_profile_id=profile.profile_id, summary_method_id="p1_fixture")
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.error_code, "frozen_summary_method_mismatch")

    def test_unapproved_peer_profile_is_rejected(self):
        profile = self.build("raw_evidence").to_dict()
        profile["researcher_id"] = "someone_else"
        profile["profile_id"] = contracts.digest({k: v for k, v in profile.items() if k != "profile_id"})
        result = self.build("profile_retrieval", frozen_profile=profile,
                            expected_profile_id=profile["profile_id"], profile_cap=256)
        self.assertEqual(result.status, "unavailable")

    def test_malformed_frozen_profiles_report_unavailable_without_crashing(self):
        incomplete = self.build("raw_evidence").to_dict()
        del incomplete["renderer_implementation_hash"]
        incomplete["profile_id"] = contracts.digest({k: v for k, v in incomplete.items() if k != "profile_id"})
        for value in [None, [], "bad", incomplete]:
            for method in ["memory_summary", "profile_retrieval"]:
                with self.subTest(value=value, method=method):
                    result = self.build(method, frozen_profile=value,
                                        expected_profile_id=incomplete["profile_id"], profile_cap=128)
                    self.assertEqual(result.status, "unavailable")
                    self.assertEqual(result.error_code, "missing_or_invalid_frozen_profile")

    def test_semantic_control_uses_bound_vectors_and_retains_production_usage(self):
        from autoresearch.taste.overnight.retrieval import make_embedding_bundle
        from autoresearch.taste.overnight.baselines import predict_baseline
        from autoresearch.taste.overnight.consumer import ProfileFailure
        bundle = make_embedding_bundle(self.docs, self.cfg, self.cfg["decision"], model="fixture-embedding",
                                       vectors=[[1, 0], [0, 1], [1, 0]],
                                       usage={"mode": "offline_fixture", "calls": 0})
        changes = {"embedding_bundle": bundle, "embedding_model": "fixture-embedding",
                   "embedding_dimensions": 2, "embedding_bundle_sha256": bundle["bundle_sha256"]}
        profile = self.build("semantic_retrieval", **changes)
        self.assertEqual(profile.status, "complete")
        self.assertEqual(profile.content["passages"][0]["document_id"], "d2")
        self.assertEqual(profile.fit_usage["embedding_production_usage"], bundle["usage"])
        self.assertEqual(profile.fit_usage["calls"], 0)
        with self.assertRaisesRegex(ProfileFailure, "decision_mismatch"):
            predict_baseline(profile, "different", ["left", "right"], NoCalls(), {})
        changes["embedding_dimensions"] = 3
        rejected = self.build("semantic_retrieval", **changes)
        self.assertEqual(rejected.status, "unavailable")
        self.assertEqual(rejected.error_code, "invalid_embedding_bundle")

    def test_loaded_semantic_bundles_require_model_and_live_provenance(self):
        from autoresearch.taste.overnight.retrieval import make_embedding_bundle
        original = make_embedding_bundle(self.docs, self.cfg, self.cfg["decision"], model="fixture-embedding",
                                         vectors=[[1, 0], [0, 1], [1, 0]], usage={"mode": "offline_fixture"})
        for defect in ["live_without_producer", "missing_models"]:
            bundle = json.loads(json.dumps(original))
            extra = {"embedding_model": "fixture-embedding", "embedding_dimensions": 2}
            if defect == "live_without_producer":
                bundle["usage"] = {"mode": "live"}
            else:
                del bundle["model"]
                extra["embedding_model"] = None
            bundle["bundle_sha256"] = contracts.digest({k: v for k, v in bundle.items() if k != "bundle_sha256"})
            with self.subTest(defect=defect):
                result = self.build("semantic_retrieval", embedding_bundle=bundle,
                                    embedding_bundle_sha256=bundle["bundle_sha256"], **extra)
                self.assertEqual(result.status, "unavailable")
                self.assertEqual(result.error_code, "invalid_embedding_bundle")


def summary_fixture(documents, config, extractor):
    return {"content": {"prose": "Prefers controlled experiments when testing a claim."}}


if __name__ == "__main__":
    unittest.main()
