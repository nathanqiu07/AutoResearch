"""Immutable JSON artifacts and source-set validation for profile study v1.

Canonical hashes use compact sorted-key UTF-8 JSON with no NaN/Infinity. Source
content hashes cover the delivered string exactly; this module never fetches or
normalizes documents. Token counts are explicitly conservative UTF-8 byte bounds,
not tokenizer measurements. They may reject profiles that would fit a tokenizer.
"""
import hashlib
import json
from dataclasses import dataclass


SCHEMA_VERSION = "neutral-profile-v1"
TOKEN_COUNT_METHOD = "utf8-bytes-upper-bound-v1"
QUOTE_RESOLVER_VERSION = "unique-exact-permitted-quote-v1"
STATUSES = {"complete", "empty", "unsupported", "invalid", "unavailable", "abstained"}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_text(value):
    return sha256_bytes(value.encode("utf-8"))


def digest(value):
    return sha256_text(canonical_json(value))


class QuoteResolutionError(ValueError):
    """Stable failure code and non-text diagnostics; no partial resolved output."""
    def __init__(self, code, records):
        super().__init__(code)
        self.code = code
        self.resolution_records = json.loads(canonical_json(records))


def resolve_quote_sources(content, documents):
    """Copy JSON content and resolve exact quote-only sources to character spans.

    A source is an entry of a `sources` list or a mapping containing document_id
    or quote. Its keys must be exactly {document_id, quote}. Old offset-bearing
    sources are rejected, never repaired. Each exact quote must occur once in
    the document's permitted spans; overlaps do not count an occurrence twice.
    A quote must fit wholly inside one approved span, matching strict validators.
    For compatibility, absent permitted_spans means the entire document, whereas
    an explicit empty list permits nothing. Offsets are Python Unicode indices.
    Callers still run their normal strict artifact validation after resolution.
    """
    records = []

    def fail(code, path, source=None):
        record = {"resolver_version": QUOTE_RESOLVER_VERSION, "source_path": path,
                  "status": "invalid", "error_code": code}
        if isinstance(source, dict):
            if isinstance(source.get("document_id"), str):
                record["document_id"] = source["document_id"]
            if isinstance(source.get("quote"), str):
                record["quote_sha256"] = sha256_text(source["quote"])
        raise QuoteResolutionError(code, records + [record])

    try:
        resolved = json.loads(canonical_json(content))
    except (TypeError, ValueError):
        fail("quote_content_json", [])
    try:
        documents = json.loads(canonical_json(documents))
    except (TypeError, ValueError):
        fail("quote_source_document", [])
    if not isinstance(documents, list):
        fail("quote_source_document", [])
    approved = {}
    for index, document in enumerate(documents):
        path = ["documents", index]
        if (not isinstance(document, dict) or not isinstance(document.get("document_id"), str)
                or not document["document_id"] or document["document_id"] in approved
                or not isinstance(document.get("content"), str)):
            fail("quote_source_document", path)
        text = document["content"]
        if document.get("content_sha256") != sha256_text(text):
            fail("quote_document_hash", path, document)
        spans = document.get("permitted_spans", [{"start": 0, "end": len(text)}])
        if not isinstance(spans, list):
            fail("quote_document_spans", path, document)
        if "permitted_spans" in document:
            for span in spans:
                if (not isinstance(span, dict) or type(span.get("start")) is not int
                        or type(span.get("end")) is not int
                        or not 0 <= span["start"] < span["end"] <= len(text)):
                    fail("quote_document_spans", path, document)
        approved[document["document_id"]] = (text, spans)

    def source(entry, path):
        if not isinstance(entry, dict) or set(entry) != {"document_id", "quote"}:
            fail("quote_source_shape", path, entry)
        document_id, quote = entry["document_id"], entry["quote"]
        if not isinstance(document_id, str) or document_id not in approved:
            fail("quote_source_document", path, entry)
        if not isinstance(quote, str) or not quote:
            fail("quote_source_quote", path, entry)
        text, spans = approved[document_id]
        matches, found, start = set(), False, text.find(quote)
        while start != -1:
            found = True
            end = start + len(quote)
            if any(span["start"] <= start and end <= span["end"] for span in spans):
                matches.add((start, end))
            start = text.find(quote, start + 1)
        if not matches:
            fail("quote_unpermitted" if found else "quote_absent", path, entry)
        if len(matches) != 1:
            fail("quote_ambiguous", path, entry)
        start, end = next(iter(matches))
        records.append({"resolver_version": QUOTE_RESOLVER_VERSION, "source_path": path,
                        "document_id": document_id, "quote_sha256": sha256_text(quote),
                        "status": "resolved", "start": start, "end": end})
        return dict(entry, start=start, end=end)

    def walk(value, path):
        if isinstance(value, list):
            return [walk(entry, path + [index]) for index, entry in enumerate(value)]
        if not isinstance(value, dict):
            return value
        if "document_id" in value or "quote" in value:
            return source(value, path)
        result = {}
        for key, entry in value.items():
            if key == "sources":
                if not isinstance(entry, list):
                    fail("quote_source_shape", path + [key])
                result[key] = [source(item, path + [key, index]) for index, item in enumerate(entry)]
            else:
                result[key] = walk(entry, path + [key])
        return result

    return walk(resolved, []), records


def backend_identity(backend):
    if hasattr(backend, "_overnight_identity"):
        return json.loads(canonical_json(backend._overnight_identity))
    identity = {"label": backend.label, "class": type(backend).__name__,
                "model": getattr(backend, "model", ""), "endpoint": getattr(backend, "base_url", "")}
    if hasattr(backend, "enforced_settings"):
        identity["enforced_settings"] = json.loads(canonical_json(backend.enforced_settings))
    return identity


def source_manifest(documents):
    return sorted(({"document_id": d["document_id"], "content_sha256": d["content_sha256"]}
                   for d in documents), key=lambda d: d["document_id"])


def validate_documents(documents, config):
    if not isinstance(documents, list) or any(not isinstance(d, dict) for d in documents):
        raise ValueError("documents must be a list of approved records")
    seen = set()
    for doc in documents:
        for key in ("document_id", "researcher_id", "content", "content_sha256"):
            if not isinstance(doc.get(key), str):
                raise ValueError("document missing text field: " + key)
        if not doc["document_id"] or doc["document_id"] in seen:
            raise ValueError("duplicate or empty document ID")
        seen.add(doc["document_id"])
        if sha256_text(doc["content"]) != doc["content_sha256"]:
            raise ValueError("document content hash mismatch")
        if doc["researcher_id"] != config["researcher_id"] and config.get("approved_peer_sources") is not True:
            raise ValueError("researcher mismatch without approved peer bundle")
    actual = source_manifest(documents)
    if actual != config.get("allowed_sources"):
        raise ValueError("exact allowed source set mismatch")
    if digest(actual) != config.get("allowed_source_manifest_hash"):
        raise ValueError("allowed source manifest hash mismatch")
    return actual


def render_content(content):
    return "" if content in (None, {}, [], "") else canonical_json(content)


@dataclass(frozen=True)
class ProfileArtifact:
    """Canonical JSON internally prevents mutation through nested lists/dicts."""
    _json: str

    @classmethod
    def from_dict(cls, body):
        body = json.loads(canonical_json(body))
        if body.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported profile schema; legacy compatibility is unverified")
        if body.get("status") not in STATUSES:
            raise ValueError("invalid profile status")
        if body.get("content_sha256") != digest(body.get("content")):
            raise ValueError("profile content hash mismatch")
        expected = dict(body)
        profile_id = expected.pop("profile_id", None)
        if profile_id != digest(expected):
            raise ValueError("profile hash mismatch")
        rendered_count = len(render_content(body.get("content")).encode("utf-8"))
        cap = body.get("personalization_cap")
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
            raise ValueError("invalid profile cap")
        if body.get("token_count_method") != TOKEN_COUNT_METHOD or body.get("token_count") != rendered_count:
            raise ValueError("profile rendered count mismatch")
        if body["status"] == "complete" and rendered_count > cap:
            raise ValueError("complete profile exceeds personalization cap")
        if body.get("config_id") != digest(body.get("config")):
            raise ValueError("profile config hash mismatch")
        config = body.get("config", {})
        for key in ("method_id", "researcher_id", "replicate_id", "personalization_cap", "code_sha",
                    "extractor_settings", "allowed_source_manifest_hash"):
            if body.get(key) != config.get(key):
                raise ValueError("profile/config provenance mismatch: " + key)
        allowed = config.get("allowed_sources")
        if not isinstance(allowed, list) or digest(allowed) != body.get("allowed_source_manifest_hash"):
            raise ValueError("profile source manifest mismatch")
        return cls(canonical_json(body))

    def to_dict(self):
        return json.loads(self._json)

    def __getattr__(self, key):
        body = self.to_dict()
        if key not in body:
            raise AttributeError(key)
        return body[key]


def build_profile(documents, config, extractor):
    """Run one registered builder; calls must be gated by the assigned runner.

    Required config: method_id, researcher_id, allowed_sources (sorted exact
    ID/hash list), allowed_source_manifest_hash, personalization_cap, replicate_id,
    code_sha, extractor_settings. Additional method-specific config is preserved.
    """
    from .registry import get_builder
    from .consumer import implementation_hash
    config = json.loads(canonical_json(config))
    for field in ("method_id", "researcher_id", "replicate_id", "code_sha", "extractor_settings"):
        if field not in config:
            raise ValueError("missing build config: " + field)
    cap = config.get("personalization_cap")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
        raise ValueError("personalization cap must be a nonnegative integer")
    validate_documents(documents, config)
    builder = get_builder(config["method_id"])
    result = builder.function(json.loads(canonical_json(documents)), json.loads(canonical_json(config)), extractor)
    if not isinstance(result, dict) or "content" not in result:
        result = {"content": None, "status": "invalid", "error_code": "malformed_builder_output"}
    try:
        content = json.loads(canonical_json(result["content"]))
    except (ValueError, TypeError):
        content, result = None, {"status": "invalid", "error_code": "non_json_content"}
    rendered = render_content(content)
    count = len(rendered.encode("utf-8"))
    status = result.get("status", "complete")
    error = result.get("error_code")
    if status not in STATUSES:
        status, error = "invalid", "unknown_builder_status"
    if status == "complete" and not rendered and not builder.allows_empty:
        status, error = "empty", "empty_extraction"
    if count > cap:
        status, error = "invalid", "personalization_cap_exceeded"
    if result.get("weights_status", "unavailable") != "unavailable" or result.get("calibrated", False):
        status, error = "invalid", "learned_weights_or_calibration_not_neutral"
    body = {"schema_version": SCHEMA_VERSION, "researcher_id": config["researcher_id"],
            "method_id": builder.method_id, "config_id": digest(config), "config": config,
            "allowed_source_manifest_hash": config["allowed_source_manifest_hash"],
            "extractor": backend_identity(extractor), "extractor_settings": config["extractor_settings"],
            "replicate_id": config["replicate_id"], "content": content, "content_sha256": digest(content),
            "status": status, "error_code": error, "intentional_empty": builder.allows_empty and not rendered,
            "token_count": count, "token_count_method": TOKEN_COUNT_METHOD, "personalization_cap": cap,
            "confidence_status": "uncalibrated", "weights_status": "unavailable",
            "fit_usage": result.get("fit_usage", {"cost_status": "unavailable"}),
            "prompt_version": builder.prompt_version, "prompt_sha256": builder.prompt_sha256,
            "method_implementation_hash": builder.implementation_hash,
            "renderer_implementation_hash": implementation_hash(), "compatibility_status": "pinned",
            "code_sha": config["code_sha"]}
    body["profile_id"] = digest(body)
    return ProfileArtifact.from_dict(body)
