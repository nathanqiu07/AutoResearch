"""Offline Chris Olah source intake using the common reserved intake checks."""
from scripts.profile_sources.neel_nanda import _inspect_document, _stage_batch, summarize_batch

RESEARCHER_ID = "chris_olah"
RESEARCHER_NAME = "Chris Olah"


def inspect_document(raw, metadata, content=None):
    """Preserve speaker attribution and leave all source eligibility to evaluator."""
    return _inspect_document(raw, metadata, RESEARCHER_ID, RESEARCHER_NAME, content)


def stage_batch(documents, private_root):
    """Stage (raw bytes, metadata, delivered text or None) tuples privately."""
    return _stage_batch(documents, private_root, RESEARCHER_ID, RESEARCHER_NAME)
