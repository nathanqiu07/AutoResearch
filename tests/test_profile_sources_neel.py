"""Source intake preserves provenance and never approves data for fitting."""
import hashlib
import unittest
from scripts.profile_sources import neel_nanda as intake


def metadata(**overrides):
    result = dict(observed_url="https://www.neelnanda.io/example?revision=2#section", title="Synthetic source", authors=["Neel Nanda"], author_contribution="sole author", published_at="2024-01-01", updated_at="2024-02-01", retrieved_at="2026-11-15T09:00:00+00:00", version_evidence={"status": "verified", "basis": "synthetic revision fixture", "observed_revision": "2"}, document_group="fixture-doc", project_group="fixture-project", duplicate_group=None, evidence_type="explicit_taste", fetch_status="complete", declared_length_bytes=21, source_spans=[{"start": 0, "end": 20, "text": "I prefer clear tests", "speaker": "Neel Nanda"}])
    result.update(overrides)
    return result


class NeelIntakeTests(unittest.TestCase):
    def test_preserves_bytes_revision_and_unapproved_status(self):
        raw = b"I prefer clear tests."
        row = intake.inspect_document(raw, metadata())
        self.assertEqual(row["observed_content_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(row["content_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(row["content"], "I prefer clear tests.")
        self.assertEqual(row["canonical_url"], "https://www.neelnanda.io/example?revision=2")
        self.assertEqual(row["split_eligibility"], "pending_evaluator")
        self.assertEqual(row["qa_status"], "ready_for_review")
        self.assertEqual(row["version_evidence"]["observed_revision"], "2")
        self.assertEqual(row["source_spans"][0]["text_sha256"], hashlib.sha256(b"I prefer clear tests").hexdigest())

    def test_changed_bytes_keep_distinct_versions(self):
        a = intake.inspect_document(b"I prefer clear tests.", metadata())
        b = intake.inspect_document(b"I prefer clear tests!", metadata())
        self.assertNotEqual(a["document_id"], b["document_id"])
        self.assertEqual(a["canonical_url"], b["canonical_url"])
        self.assertEqual(len(intake.summarize_batch([a, b])["duplicate_candidates"]), 1)

    def test_original_date_does_not_establish_observed_version(self):
        row = intake.inspect_document(b"I prefer clear tests.", metadata(version_evidence={"status": "uncertain", "basis": "publication date only"}))
        self.assertEqual(row["qa_status"], "quarantined")
        self.assertIn("unverified_observed_version", row["qa_reasons"])

    def test_truncation_and_failed_fetches_are_visible(self):
        for changes, reason in [({"declared_length_bytes": 200}, "length_mismatch"), ({"fetch_status": "truncated"}, "fetch_not_complete")]:
            row = intake.inspect_document(b"I prefer clear tests.", metadata(**changes))
            self.assertIn(reason, row["qa_reasons"])
            self.assertEqual(row["qa_status"], "quarantined")

    def test_span_must_match_exact_stored_offsets(self):
        spans = [{"start": 0, "end": 20, "text": "Invented quotation!!", "speaker": "Neel Nanda"}]
        row = intake.inspect_document(b"I prefer clear tests.", metadata(source_spans=spans))
        self.assertIn("span_text_mismatch", row["qa_reasons"])
        self.assertEqual(row["source_spans"], [])

    def test_missing_authorship_and_invalid_utf8_are_quarantined(self):
        row = intake.inspect_document(b"\xff", metadata(authors=[], declared_length_bytes=1, source_spans=[]))
        self.assertIn("invalid_utf8", row["qa_reasons"])
        self.assertIn("researcher_not_attributed", row["qa_reasons"])
        self.assertIsNone(row["content"])

    def test_crosspost_bytes_are_candidates_not_an_automatic_merge(self):
        a = intake.inspect_document(b"I prefer clear tests.", metadata())
        b = intake.inspect_document(b"I prefer clear tests.", metadata(observed_url="https://example.org/crosspost"))
        report = intake.summarize_batch([a, b])
        self.assertEqual(report["document_count"], 2)
        self.assertEqual(report["duplicate_candidates"][0]["basis"], "exact_content")
        self.assertNotEqual(a["document_id"], b["document_id"])

    def test_labels_and_split_assignments_are_rejected(self):
        for extra in [{"chosen": "a"}, {"split": "fit"}, {"answer": "secret"}]:
            with self.assertRaises(ValueError):
                intake.inspect_document(b"I prefer clear tests.", metadata(**extra))

    def test_malformed_metadata_is_rejected(self):
        for extra in [{"observed_url": "file:///etc/passwd"}, {"retrieved_at": "yesterday"}, {"authors": "Neel Nanda"}]:
            with self.assertRaises(ValueError):
                intake.inspect_document(b"I prefer clear tests.", metadata(**extra))


class PrivateStagingTests(unittest.TestCase):
    def test_raw_html_and_delivered_text_have_separate_hashes(self):
        row = intake.inspect_document(b"<p>I prefer clear tests.</p>", metadata(declared_length_bytes=28), content="I prefer clear tests.")
        self.assertEqual(row["content_sha256"], hashlib.sha256(b"I prefer clear tests.").hexdigest())
        self.assertEqual(row["observed_content_sha256"], hashlib.sha256(b"<p>I prefer clear tests.</p>").hexdigest())
        self.assertEqual(row["source_spans"][0]["offset_unit"], "unicode_codepoints")

    def test_private_staging_is_content_addressed_and_refuses_overwrite(self):
        import json
        import os
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o700)
            docs = [(b"I prefer clear tests.", metadata(), None)]
            result = intake.stage_batch(docs, root)
            batch = Path(result["path"])
            self.assertEqual(batch.name, result["manifest_sha256"])
            self.assertEqual(batch.stat().st_mode & 0o777, 0o700)
            manifest = json.loads((batch / "manifest.json").read_text())
            raw_path = batch / manifest["documents"][0]["document_id"] / "source.bin"
            self.assertEqual(raw_path.read_bytes(), b"I prefer clear tests.")
            self.assertEqual(raw_path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                intake.stage_batch(docs, root)

    def test_staging_rejects_repository_and_permissive_roots(self):
        import os
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o755)
            with self.assertRaises(ValueError):
                intake.stage_batch([], root)
            os.chmod(root, 0o700)
            (Path(root) / ".git").write_text("gitdir: example")
            with self.assertRaises(ValueError):
                intake.stage_batch([], root)
