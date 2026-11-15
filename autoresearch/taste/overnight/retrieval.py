"""In-memory retrieval from exact approved sources; no network or disk cache.

Windows use a fixed character grid, clipped to individual permitted spans and
whitespace-trimmed with exact offsets. Overlap is emitted once; exact duplicate
text keeps the lexicographically first source span.
BM25 uses Unicode word tokens, k1=1.5, b=0.75; ties use document ID and offset.
Packing includes JSON overhead in the shared conservative UTF-8 byte cap.
"""
import math
import re
from collections import Counter
from pathlib import Path

from .contracts import canonical_json, digest, sha256_bytes, validate_documents


VERSION = "approved-bm25-v2"


def implementation_hash():
    return sha256_bytes(Path(__file__).read_bytes())


def positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(name + " must be a positive integer")
    return value


def decision_query(decision):
    if (not isinstance(decision, dict) or set(decision) != {"context", "options"}
            or not isinstance(decision["context"], str)
            or not isinstance(decision["options"], list)
            or not 2 <= len(decision["options"]) <= 26
            or any(not isinstance(x, str) for x in decision["options"])):
        raise ValueError("decision must contain only text context and options")
    return canonical_json(decision)


def _permitted_ranges(doc):
    if "permitted_spans" not in doc:
        return [(0, len(doc["content"]))]
    spans = doc["permitted_spans"]
    if not isinstance(spans, list):
        raise ValueError("permitted_spans must be a list")
    ranges = set()
    for span in spans:
        if (not isinstance(span, dict)
                or type(span.get("start")) is not int
                or type(span.get("end")) is not int
                or not 0 <= span["start"] < span["end"] <= len(doc["content"])):
            raise ValueError("permitted_spans contains an invalid range")
        ranges.add((span["start"], span["end"]))
    return sorted(ranges, key=lambda pair: (pair[0], -pair[1]))


def _permission_hash(documents):
    return digest([{"document_id": doc["document_id"], "ranges": _permitted_ranges(doc)}
                   for doc in sorted(documents, key=lambda d: d["document_id"])])


def chunk_documents(documents, config):
    validate_documents(documents, config)
    width = positive_int(config.get("chunk_chars", 1200), "chunk_chars")
    seen, chunks = set(), []
    for doc in sorted(documents, key=lambda d: d["document_id"]):
        text = doc["content"]
        ranges = _permitted_ranges(doc)
        for offset in range(0, len(text), width):
            covered_end = offset
            for allowed_start, allowed_end in ranges:
                start = max(offset, allowed_start, covered_end)
                end = min(offset + width, allowed_end)
                if start >= end:
                    continue
                # Partition overlaps without joining distinct permission ranges.
                covered_end = end
                window = text[start:end]
                value = window.strip()
                if not value or value in seen:
                    continue
                seen.add(value)
                start += len(window) - len(window.lstrip())
                chunks.append({"document_id": doc["document_id"], "start": start,
                               "end": start + len(value), "text": value})
    return chunks


def _tokens(text):
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def rank_lexical(chunks, decision):
    decision_query(decision)  # Reject labels/extra fields before ranking.
    query = set(_tokens(decision["context"] + "\n" + "\n".join(decision["options"])))
    counts = [Counter(_tokens(part["text"])) for part in chunks]
    if not counts:
        return []
    lengths = [sum(c.values()) for c in counts]
    average = sum(lengths) / len(lengths) or 1
    frequency = Counter(term for count in counts for term in count)
    scored = []
    for part, count, size in zip(chunks, counts, lengths):
        score = 0.0
        for word in sorted(query):
            tf = count.get(word, 0)
            if tf:
                idf = math.log(1 + (len(chunks) - frequency[word] + .5) / (frequency[word] + .5))
                score += idf * tf * 2.5 / (tf + 1.5 * (.25 + .75 * size / average))
        scored.append((-score, part["document_id"], part["start"], part))
    return [entry[-1] for entry in sorted(scored, key=lambda row: row[:3])]


def pack_passages(chunks, cap, *, profile=None, passage_cap=None):
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
        raise ValueError("cap must be a nonnegative integer")
    if passage_cap is not None and (isinstance(passage_cap, bool) or not isinstance(passage_cap, int) or passage_cap < 0):
        raise ValueError("passage_cap must be a nonnegative integer")
    def content(rows):
        result = {"passages": rows}
        if profile is not None:
            result["profile"] = profile
        return result
    def fits(rows):
        return (len(canonical_json(content(rows)).encode("utf-8")) <= cap and
                (passage_cap is None or len(canonical_json({"passages": rows}).encode("utf-8")) <= passage_cap))
    selected = []
    for chunk in chunks:
        # Only source spans enter the prompt; arbitrary document metadata cannot.
        part = {k: chunk[k] for k in ("document_id", "start", "end", "text")}
        if fits(selected + [part]):
            selected.append(part)
            continue
        low, high = 0, len(part["text"])
        while low < high:
            middle = (low + high + 1) // 2
            candidate = dict(part, text=part["text"][:middle], end=part["start"] + middle)
            if fits(selected + [candidate]):
                low = middle
            else:
                high = middle - 1
        if low and part["text"][:low].strip():
            value = part["text"][:low].rstrip()
            selected.append(dict(part, text=value, end=part["start"] + len(value)))
    return content(selected)


def retrieval_cache_key(documents, config, decision, consumer_identity):
    sources = validate_documents(documents, config)
    if not isinstance(consumer_identity, dict) or not consumer_identity.get("model"):
        raise ValueError("explicit consumer identity with model is required")
    return digest({"version": VERSION, "implementation_hash": implementation_hash(),
                   "sources": sources, "permission_hash": _permission_hash(documents),
                   "query": decision_query(decision),
                   "consumer": consumer_identity, "config": config})


def embedding_inputs(documents, config, decision):
    """Exact ordered inputs for a separately leased embedding call: query first."""
    chunks = chunk_documents(documents, config)
    return [decision_query(decision)] + [chunk["text"] for chunk in chunks]


def _embedding_request(documents, config, decision):
    chunks = chunk_documents(documents, config)
    inputs = [decision_query(decision)] + [chunk["text"] for chunk in chunks]
    return {"source_manifest_hash": config["allowed_source_manifest_hash"],
            "permission_hash": _permission_hash(documents),
            "researcher_id": config["researcher_id"], "chunk_chars": config.get("chunk_chars", 1200),
            "implementation_hash": implementation_hash(), "query_sha256": digest(decision),
            "chunk_hashes": [digest(chunk) for chunk in chunks],
            "input_hashes": [sha256_bytes(text.encode("utf-8")) for text in inputs],
            "input_policy": "canonical-decision-json-then-exact-chunk-text-v1",
            "similarity": "cosine-v1"}


def _unit_vectors(vectors, count):
    if not isinstance(vectors, list) or len(vectors) != count or not vectors:
        raise ValueError("embedding vector count mismatch")
    dimension = len(vectors[0]) if isinstance(vectors[0], list) else 0
    if not dimension:
        raise ValueError("embedding dimension must be positive")
    unit = []
    for vector in vectors:
        if (not isinstance(vector, list) or len(vector) != dimension
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in vector)):
            raise ValueError("embedding vector is malformed")
        try:
            numeric = [float(value) for value in vector]
        except OverflowError:
            raise ValueError("embedding coordinate exceeds numeric range") from None
        if any(not math.isfinite(value) for value in numeric):
            raise ValueError("embedding vector is nonfinite")
        scale = max(abs(value) for value in numeric)
        if scale == 0:
            raise ValueError("embedding vector has zero or invalid norm")
        # Normalize direction at an ordinary scale. A raw subnormal norm can
        # round enough to change cosine ranking; a large raw norm can overflow.
        scaled = [value / scale for value in numeric]
        norm = math.hypot(*scaled)
        unit.append([value / norm for value in scaled])
    return dimension, unit


def _embedding_usage(usage):
    if not isinstance(usage, dict) or usage.get("mode") not in {"live", "offline_fixture"}:
        raise ValueError("embedding usage mode must be explicit")
    if usage["mode"] == "live":
        if (not isinstance(usage.get("producer_job_id"), str) or not usage["producer_job_id"]
                or not isinstance(usage.get("response_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", usage["response_sha256"]) is None):
            raise ValueError("live embedding producer job and response hash required")


def make_embedding_bundle(documents, config, decision, *, model, vectors, usage):
    """Record supplied vectors, without calling a model or authenticating origin.

    Live production must retain its coordinator job ID and raw response hash in
    usage. These hashes prove consistency, not that a claimed provider ran.
    """
    request = _embedding_request(documents, config, decision)
    dimensions, _ = _unit_vectors(vectors, len(request["input_hashes"]))
    if not isinstance(model, str) or not model:
        raise ValueError("embedding model is required")
    _embedding_usage(usage)
    body = {"schema_version": "approved-embedding-bundle-v1", "request": request,
            "model": model, "dimensions": dimensions, "vectors": vectors, "usage": usage}
    body["bundle_sha256"] = digest(body)
    # Detached JSON value; changes to the producer's arrays cannot alter it.
    import json
    return json.loads(canonical_json(body))


def rank_semantic(documents, config, decision, bundle):
    chunks = chunk_documents(documents, config)
    request = _embedding_request(documents, config, decision)
    if not isinstance(bundle, dict) or bundle.get("schema_version") != "approved-embedding-bundle-v1":
        raise ValueError("embedding bundle schema mismatch")
    if (not isinstance(bundle.get("model"), str) or not bundle["model"]
            or not isinstance(config.get("embedding_model"), str) or not config["embedding_model"]):
        raise ValueError("embedding model must be explicitly declared")
    body = {key: value for key, value in bundle.items() if key != "bundle_sha256"}
    if (bundle.get("bundle_sha256") != digest(body)
            or bundle.get("bundle_sha256") != config.get("embedding_bundle_sha256")
            or bundle.get("request") != request
            or bundle.get("model") != config.get("embedding_model")):
        raise ValueError("embedding bundle source/query/model/hash mismatch")
    dimensions, vectors = _unit_vectors(bundle.get("vectors"), len(chunks) + 1)
    declared = config.get("embedding_dimensions")
    if (isinstance(declared, bool) or not isinstance(declared, int) or dimensions != declared
            or isinstance(bundle.get("dimensions"), bool) or dimensions != bundle.get("dimensions")):
        raise ValueError("embedding dimension mismatch")
    usage = bundle.get("usage")
    _embedding_usage(usage)
    query = vectors[0]
    scores = [(-sum(a * b for a, b in zip(query, vector)), chunk["document_id"], chunk["start"], chunk)
              for chunk, vector in zip(chunks, vectors[1:])]
    return [entry[-1] for entry in sorted(scores, key=lambda row: row[:3])]
