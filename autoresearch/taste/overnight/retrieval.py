"""In-memory retrieval from exact approved sources; no network or disk cache.

Windows are nonoverlapping character slices, whitespace-trimmed with exact
offsets. Exact duplicate text keeps the lexicographically first source span.
BM25 uses Unicode word tokens, k1=1.5, b=0.75; ties use document ID and offset.
Packing includes JSON overhead in the shared conservative UTF-8 byte cap.
"""
import math
import re
from collections import Counter
from pathlib import Path

from .contracts import canonical_json, digest, sha256_bytes, validate_documents


VERSION = "approved-bm25-v1"


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


def chunk_documents(documents, config):
    validate_documents(documents, config)
    width = positive_int(config.get("chunk_chars", 1200), "chunk_chars")
    seen, chunks = set(), []
    for doc in sorted(documents, key=lambda d: d["document_id"]):
        text = doc["content"]
        for offset in range(0, len(text), width):
            window = text[offset:offset + width]
            value = window.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            start = offset + len(window) - len(window.lstrip())
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
                   "sources": sources, "query": decision_query(decision),
                   "consumer": consumer_identity, "config": config})
