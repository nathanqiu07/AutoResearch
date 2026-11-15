import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

from tests import test_overnight_contracts as fixture


class RunnerTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import runner
        from autoresearch.taste.overnight.contracts import backend_identity, digest
        self.runner, self.digest, self.identity = runner, digest, backend_identity
        case = fixture.ContractTests()
        case.setUp()
        self.profile = case.build()
        self.config = case.prediction_config(self.profile)
        self.consumer = fixture.RecordingConsumer()
        self.items = [{"item_id": "dev-1", "researcher_id": "synthetic", "context": "question",
                       "options": ["left", "right"], "option_order_id": "ab"}]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def manifest(self, **updates):
        body = {"schema_version": "overnight-job-v1", "campaign_id": "fixture-campaign",
                "stage": "offline", "kind": "predict", "contract_sha256": "c" * 64,
                "config_hash": self.digest(self.config), "source_manifest_hash": self.profile.allowed_source_manifest_hash,
                "items_hash": self.digest(self.items), "profile_hash": self.profile.profile_id,
                "method_id": self.profile.method_id, "extractor": self.profile.extractor,
                "consumer": self.identity(self.consumer), "personalization_cap": self.profile.personalization_cap,
                "option_order_schedule": [{"item_id": "dev-1", "option_order_id": "ab"}],
                "replicate_id": 0, "code_sha": "d" * 40,
                "allocation": {"max_calls": 1, "max_seconds": 30, "max_usd": 0,
                               "cost_mode": "offline", "authorization_source": "offline-fixture"},
                "retry_policy": {"max_attempts": 1, "retry_uncertain": False},
                "parent_job_ids": [], "expected_outputs": ["result.json", "traces"]}
        body.update(updates)
        body["job_id"] = self.runner.job_id(body)
        return body

    def run_job(self, manifest=None, **kwargs):
        manifest = manifest or self.manifest()
        lease = {"job_id": manifest["job_id"], "lease_id": "one-lease", "owner": "fixture",
                 "expires_at": "2099-01-01T00:00:00+00:00"}
        return self.runner.run_job(manifest, lease, output_root=self.root / "outputs",
                                   lease_root=self.root / "leases", cache_root=self.root / "cache",
                                   profile=self.profile, items=self.items, config=self.config,
                                   consumer=self.consumer, **kwargs)

    def test_prediction_and_durable_duplicate_lease(self):
        result = self.run_job()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["counts"], {"attempted": 1, "complete": 1, "error": 0})
        self.assertEqual(result["predictions"][0]["prediction"]["choice"], "b")
        self.assertEqual(result["predictions"][0]["status"], "complete")
        self.assertEqual(result["predictions"][0]["item_sha256"], self.digest(self.items[0]))
        self.assertEqual(result["predictions"][0]["items_sha256"], self.digest(self.items))
        self.assertEqual(result["predictions"][0]["job_id"], self.manifest()["job_id"])
        self.assertFalse(result["predictions"][0]["prediction"]["calibrated"])
        with self.assertRaises(FileExistsError):
            self.run_job()
        self.assertEqual(len(self.consumer.prompts), 1)

    def test_missing_allocation_or_changed_input_rejected_before_call(self):
        for updates in ({"allocation": None}, {"items_hash": "f" * 64}, {"profile_hash": "f" * 64}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.run_job(self.manifest(**updates))
        self.assertEqual(self.consumer.prompts, [])

    def test_label_field_never_enters_payload(self):
        self.items[0]["chosen"] = "b"
        with self.assertRaisesRegex(ValueError, "fields"):
            self.run_job()
        self.assertEqual(self.consumer.prompts, [])

    def test_failed_attempt_is_preserved_and_never_retried(self):
        class Failure(fixture.RecordingConsumer):
            def complete(self, prompt, **kwargs):
                self.prompts.append(prompt)
                raise RuntimeError("private provider error text")
        self.consumer = Failure()
        result = self.run_job()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["usage"]["attempted_calls"], 1)
        self.assertEqual(result["usage"]["uncertain_attempts"], 1)
        self.assertEqual(result["predictions"][0]["status"], "unavailable")
        self.assertNotIn("private provider error text", json.dumps(result))
        with self.assertRaises(FileExistsError):
            self.run_job()
        self.assertEqual(len(self.consumer.prompts), 1)

    def test_cache_key_separates_prompt_profile_model_settings_order_and_stage(self):
        manifest = self.manifest()
        original = self.runner.cache_key(manifest, "prompt", {"max_tokens": 128})
        for key, value in [("profile_hash", "e" * 64), ("consumer", {"label": "different"}),
                           ("config_hash", "f" * 64), ("stage", "dev"),
                           ("option_order_schedule", [{"item_id": "dev-1", "option_order_id": "ba"}])]:
            changed = dict(manifest, **{key: value})
            self.assertNotEqual(original, self.runner.cache_key(changed, "prompt", {"max_tokens": 128}))
        self.assertNotEqual(original, self.runner.cache_key(manifest, "prompt changed", {"max_tokens": 128}))
        self.assertNotEqual(original, self.runner.cache_key(manifest, "prompt", {"max_tokens": 64}))

    def test_confirmation_cannot_write_shared_or_symlinked_outputs(self):
        private = self.root / "private"
        private.mkdir()
        manifest = self.manifest(stage="confirmation", confirmation_store_id="store",
                                 confirmation_manifest_sha256="a" * 64, deadline="2099-01-01T00:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "private"):
            self.run_job(manifest, private_root=private, confirmation_receipt={})
        (private / "escape").symlink_to(self.root / "outputs", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "private"):
            self.runner.require_private_path(private / "escape" / "new", private)
        self.assertFalse((self.root / "outputs").exists())

    def test_unsupported_backend_is_visible_without_call(self):
        self.consumer.name = "paid-unverified"
        result = self.run_job()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["usage"]["attempted_calls"], 0)
        self.assertEqual(self.consumer.prompts, [])

    def test_call_limit_keeps_missing_prediction_visible(self):
        self.items.append(dict(self.items[0], item_id="dev-2", context="another question"))
        manifest = self.manifest(option_order_schedule=[{"item_id": i["item_id"], "option_order_id": i["option_order_id"]}
                                                       for i in self.items])
        result = self.run_job(manifest)
        self.assertEqual(result["counts"], {"attempted": 2, "complete": 1, "error": 1})
        self.assertEqual(result["predictions"][1]["error_code"], "allocation_exhausted")
        self.assertEqual(len(self.consumer.prompts), 1)

    def test_runtime_model_mismatch_rejected_without_claiming_job(self):
        manifest = self.manifest(consumer={"label": "wrong-model"})
        with self.assertRaisesRegex(ValueError, "backend identity"):
            self.run_job(manifest)
        self.assertFalse((self.root / "leases").exists())

    def test_uncertain_failure_halts_following_items(self):
        class Failure(fixture.RecordingConsumer):
            def complete(self, prompt, **kwargs):
                self.prompts.append(prompt)
                raise RuntimeError("uncertain transport")
        self.consumer = Failure()
        self.items.append(dict(self.items[0], item_id="dev-2"))
        manifest = self.manifest(option_order_schedule=[{"item_id": i["item_id"], "option_order_id": i["option_order_id"]} for i in self.items],
                                 allocation={"max_calls": 2, "max_seconds": 30, "max_usd": 0,
                                             "cost_mode": "offline", "authorization_source": "fixture"})
        result = self.run_job(manifest)
        self.assertEqual(result["usage"]["attempted_calls"], 1)
        self.assertEqual(result["predictions"][1]["error_code"], "lane_held_after_uncertain_attempt")

    def test_lease_expiry_is_rechecked_between_calls(self):
        now = [datetime(2080, 1, 1, tzinfo=timezone.utc)]
        class Crossing(fixture.RecordingConsumer):
            def complete(self, prompt, **kwargs):
                result = super().complete(prompt, **kwargs)
                now[0] = datetime(2100, 1, 1, tzinfo=timezone.utc)
                return result
        self.consumer = Crossing()
        self.items.append(dict(self.items[0], item_id="dev-2"))
        manifest = self.manifest(option_order_schedule=[{"item_id": i["item_id"], "option_order_id": i["option_order_id"]} for i in self.items],
                                 allocation={"max_calls": 2, "max_seconds": 30, "max_usd": 0,
                                             "cost_mode": "offline", "authorization_source": "fixture"})
        with patch.object(self.runner, "utc_now", side_effect=lambda: now[0], create=True):
            result = self.run_job(manifest)
        self.assertEqual(result["usage"]["attempted_calls"], 1)
        self.assertEqual(result["predictions"][1]["error_code"], "deadline_or_lease_expired")


if __name__ == "__main__":
    unittest.main()
