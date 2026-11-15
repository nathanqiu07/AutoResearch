"""Quoted speakers and coauthors are not silently treated as Chris."""
import unittest
from scripts.profile_sources import chris_olah as intake
from tests.test_profile_sources_neel import metadata


class ChrisIntakeTests(unittest.TestCase):
    def fixture(self, **changes):
        result = metadata(observed_url="https://colah.github.io/example/", authors=["Chris Olah"], source_spans=[{"start": 0, "end": 20, "text": "I prefer clear tests", "speaker": "Chris Olah"}])
        result.update(changes)
        return result

    def test_single_author_source_remains_pending(self):
        row = intake.inspect_document(b"I prefer clear tests.", self.fixture())
        self.assertEqual(row["researcher_id"], "chris_olah")
        self.assertEqual(row["qa_status"], "ready_for_review")
        self.assertEqual(row["split_eligibility"], "pending_evaluator")

    def test_unspecific_coauthor_contribution_is_quarantined(self):
        row = intake.inspect_document(b"I prefer clear tests.", self.fixture(authors=["Chris Olah", "Adam Jermyn"], author_contribution="coauthor", source_spans=[]))
        self.assertIn("ambiguous_contribution", row["qa_reasons"])
        self.assertEqual(row["qa_status"], "quarantined")

    def test_other_quoted_speaker_is_not_attributed_to_chris(self):
        row = intake.inspect_document(b"I prefer clear tests.", self.fixture(source_spans=[{"start": 0, "end": 20, "text": "I prefer clear tests", "speaker": "Another researcher"}]))
        self.assertEqual(row["source_spans"][0]["speaker"], "Another researcher")
        self.assertIn("no_attributed_researcher_span", row["qa_reasons"])

    def test_group_hints_survive_for_evaluator(self):
        row = intake.inspect_document(b"I prefer clear tests.", self.fixture(document_group="essay-revisions", project_group="prior-work", duplicate_group="repeated-passage"))
        self.assertEqual(row["project_group"], "prior-work")
        self.assertEqual(row["duplicate_group"], "repeated-passage")
