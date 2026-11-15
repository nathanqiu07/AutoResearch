"""Offline source intake for Neel; no fetching, labels, or split decisions.

The shared intake helpers live here because these two researcher-specific files
are the reserved scope. Chris's adapter uses the same checks. Metadata is supplied
by the source owner and is evidence to review, not a proof of authorship/version.
Offsets refer to Unicode codepoints in the exact decoded content; no normalization
occurs. Raw fetched bytes must be retained separately by the evaluator.
"""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SCHEMA_VERSION = "profile-source-intake-v1"
RESEARCHER_ID = "neel_nanda"
RESEARCHER_NAME = "Neel Nanda"
_FIELDS = {
    "observed_url", "title", "authors", "author_contribution", "published_at",
    "updated_at", "retrieved_at", "version_evidence", "document_group",
    "project_group", "duplicate_group", "revision_group", "crosspost_group",
    "evidence_type", "fetch_status", "declared_length_bytes", "source_spans",
}


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _inspect_document(raw, metadata, researcher_id, researcher_name, content=None):
    if not isinstance(raw, bytes) or not isinstance(metadata, dict):
        raise ValueError("raw bytes and a metadata object are required")
    if set(metadata) - _FIELDS:
        raise ValueError("unknown metadata fields; labels and splits are forbidden")
    # Detach all supplied containers and reject non-JSON or nonfinite values.
    meta = json.loads(_json(metadata))
    url = meta.get("observed_url", "")
    if not isinstance(url, str):
        raise ValueError("observed_url must be a public HTTP(S) URL")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("observed_url must be a public HTTP(S) URL")
    # Keep revision/query identity; only fragments are display-local.
    canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
    authors = meta.get("authors")
    if not isinstance(authors, list) or any(not isinstance(a, str) or not a.strip() for a in authors):
        raise ValueError("authors must be a list of nonempty names")
    retrieved = meta.get("retrieved_at")
    try:
        stamp = datetime.datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError("timezone absent")
        for key in ("published_at", "updated_at"):
            if meta.get(key) is not None:
                datetime.date.fromisoformat(meta[key])
    except (ValueError, TypeError, AttributeError):
        raise ValueError("dates must be ISO dates and retrieval must include timezone") from None
    length = meta.get("declared_length_bytes")
    if length is not None and (type(length) is not int or length < 0):
        raise ValueError("declared_length_bytes must be a nonnegative integer or null")
    version = meta.get("version_evidence")
    if not isinstance(version, dict):
        raise ValueError("version_evidence must be an object, including an explicit unknown status")
    spans = meta.get("source_spans", [])
    if not isinstance(spans, list):
        raise ValueError("source_spans must be a list")
    reasons = []
    if meta.get("fetch_status") != "complete":
        reasons.append("fetch_not_complete")
    if length is not None and length != len(raw):
        reasons.append("length_mismatch")
    if not raw:
        reasons.append("empty_content")
    if content is not None and not isinstance(content, str):
        raise ValueError("delivered content must be a string or null")
    if content is None:
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            reasons.append("invalid_utf8")
    if content == "":
        reasons.append("empty_delivered_content")
    if version.get("status") != "verified" or not version.get("basis") or not version.get("observed_revision"):
        reasons.append("unverified_observed_version")
    if researcher_name not in authors:
        reasons.append("researcher_not_attributed")
    valid_spans = []
    for span in spans:
        if not isinstance(span, dict) or set(span) - {"start", "end", "text", "speaker"}:
            raise ValueError("spans require start/end/text/speaker only")
        start, end, quote, speaker = (span.get(k) for k in ("start", "end", "text", "speaker"))
        if type(start) is not int or type(end) is not int or not isinstance(quote, str) or not isinstance(speaker, str):
            raise ValueError("malformed source span")
        if content is None or not (0 <= start < end <= len(content)) or not quote or content[start:end] != quote:
            reasons.append("span_text_mismatch")
            continue
        valid_spans.append({"start": start, "end": end, "offset_unit": "unicode_codepoints",
                            "text_sha256": _digest(quote.encode("utf-8")), "speaker": speaker})
    attributed = any(s["speaker"] == researcher_name for s in valid_spans)
    if not attributed:
        reasons.append("no_attributed_researcher_span")
    if len(authors) > 1 and not attributed:
        reasons.append("ambiguous_contribution")
    for key in ("document_group", "project_group", "duplicate_group", "revision_group", "crosspost_group"):
        if meta.get(key) is not None and (not isinstance(meta[key], str) or not meta[key]):
            raise ValueError("group hints must be nonempty strings or null")
    if not meta.get("document_group") or not meta.get("evidence_type"):
        reasons.append("missing_group_or_evidence_type")
    raw_hash = _digest(raw)
    row = {key: value for key, value in meta.items() if key != "source_spans"}
    row.update(schema_version=SCHEMA_VERSION,
               document_id="doc-" + _digest(_json([researcher_id, canonical, raw_hash])),
               researcher_id=researcher_id, canonical_url=canonical,
               observed_content_sha256=raw_hash,
               content=content, content_sha256=_digest(content.encode("utf-8")) if content is not None else None,
               content_length_bytes=len(raw), source_spans=valid_spans,
               split_eligibility="pending_evaluator",
               qa_status="quarantined" if reasons else "ready_for_review",
               qa_reasons=sorted(set(reasons)))
    return row


def inspect_document(raw, metadata, content=None):
    """Return private intake evidence; ready_for_review is not approval to fit."""
    return _inspect_document(raw, metadata, RESEARCHER_ID, RESEARCHER_NAME, content)


def summarize_batch(records):
    """Private counts and candidate duplicate links, never automatic split groups.

    Do not publish this result: document IDs reveal membership and require the
    evaluator's release decision even though raw URLs/text are not included.
    """
    records = list(records)
    ids = [r["document_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate document identity in batch")
    candidates = []
    for field, basis in (("observed_content_sha256", "exact_content"), ("canonical_url", "same_canonical_url")):
        groups = collections.defaultdict(list)
        for row in records:
            groups[(row["researcher_id"], row[field])].append(row["document_id"])
        for members in groups.values():
            if len(members) > 1:
                candidates.append({"document_ids": sorted(members), "basis": basis})
    return {"document_count": len(records),
            "qa_counts": dict(sorted(collections.Counter(r["qa_status"] for r in records).items())),
            "reason_counts": dict(sorted(collections.Counter(reason for r in records for reason in r["qa_reasons"]).items())),
            "duplicate_candidates": sorted(candidates, key=lambda c: (c["basis"], c["document_ids"]))}


def _stage_batch(documents, private_root, researcher_id, researcher_name):
    """Store immutable raw bytes and inspected text outside Git, privately.

    The caller must use the evaluator-assigned root; this enforces private modes
    and repository exclusion, not an OS security boundary between same-user agents.
    It never fetches, publishes, approves, or picks a split.
    """
    root = Path(private_root)
    if not root.is_dir() or root.is_symlink() or root.stat().st_mode & 0o077:
        raise ValueError("existing private directory (mode 0700) required")
    root = root.resolve()
    if any((p / ".git").exists() for p in (root,) + tuple(root.parents)):
        raise ValueError("evaluator store must be outside every Git checkout")
    documents = list(documents)
    records = [_inspect_document(raw, meta, researcher_id, researcher_name, content)
               for raw, meta, content in documents]
    summary = summarize_batch(records)
    payload = {"schema_version": SCHEMA_VERSION, "researcher_id": researcher_id,
               "documents": sorted(records, key=lambda r: r["document_id"]),
               "summary": summary}
    manifest = _json(payload)
    manifest_hash = _digest(manifest)
    batch = root / manifest_hash
    batch.mkdir(mode=0o700)  # Exclusive reservation before any file write.

    def write_private(path, data):
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)

    for (raw, _, _), row in zip(documents, records):
        folder = batch / row["document_id"]
        folder.mkdir(mode=0o700)
        write_private(folder / "source.bin", raw)
        if row["content"] is not None:
            write_private(folder / "content.txt", row["content"].encode("utf-8"))
        write_private(folder / "metadata.json", _json(row))
    # Manifest is last; partial interrupted batches remain visibly incomplete.
    write_private(batch / "manifest.json", manifest)
    return {"path": str(batch), "manifest_sha256": manifest_hash,
            "document_count": len(records), "qa_counts": summary["qa_counts"]}


def stage_batch(documents, private_root):
    """Stage (raw bytes, metadata, delivered text or None) tuples privately."""
    return _stage_batch(documents, private_root, RESEARCHER_ID, RESEARCHER_NAME)
