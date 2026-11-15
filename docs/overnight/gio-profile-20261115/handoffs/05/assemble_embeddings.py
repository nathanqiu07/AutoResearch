#!/usr/bin/env python3
"""Offline, one-batch response-to-bundle assembly; no API or credential access.

Pass all five external files with their expected byte hashes. The released bundle
selects one proposal batch. Output must be a new directory. Each decision gets an
exclusive bundle file; manifest.json contains hashes and references, not input
text or vectors. Production cost stays on the producer receipt, referenced by
every derived bundle; assembly makes zero model calls. A completed, hash-pinned
receipt supplies provenance, not independent authentication of provider origin.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from autoresearch.taste.overnight import retrieval
from autoresearch.taste.overnight.contracts import canonical_json, digest, validate_documents

ARTIFACTS = ("proposal", "release", "request", "receipt", "response")
ITEM_FIELDS = {"context", "item_id", "option_order_id", "options", "researcher_id"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (canonical_json(value) + "\n").encode("utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def invalid_constant(unused):
        raise ValueError("nonfinite JSON constant")
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    require(isinstance(value, dict), "artifact must be a JSON object")
    return value


def indexed_vectors(rows, count, dimensions):
    require(isinstance(rows, list) and len(rows) == count, "vector index coverage mismatch")
    indexed = {}
    for row in rows:
        require(isinstance(row, dict), "vector row must be an object")
        index, vector = row.get("index"), row.get("embedding")
        require(isinstance(index, int) and not isinstance(index, bool)
                and 0 <= index < count and index not in indexed, "duplicate or invalid vector index")
        require(isinstance(vector, list) and len(vector) == dimensions, "vector dimension mismatch")
        require(all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
                    for v in vector) and any(v != 0 for v in vector), "invalid or zero vector")
        indexed[index] = vector
    return indexed


def assemble(*, proposal_bytes, release_bytes, request_bytes, receipt_bytes, response_bytes, expected_hashes):
    """Return (decision bundles, hash-only manifest), with no filesystem writes."""
    raw = dict(zip(ARTIFACTS, (proposal_bytes, release_bytes, request_bytes, receipt_bytes, response_bytes)))
    require(isinstance(expected_hashes, dict) and set(expected_hashes) == set(ARTIFACTS),
            "all five external byte hashes are required")
    for key, value in raw.items():
        require(isinstance(value, bytes) and sha(value) == expected_hashes[key], key + " file hash mismatch")
    try:
        values = {key: parse(value) for key, value in raw.items()}
        return _assemble(values, raw, dict(expected_hashes))
    except (KeyError, IndexError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("malformed assembly input") from exc


def _assemble(values, raw, hashes):
    proposal, release, request, receipt, response = (values[key] for key in ARTIFACTS)
    require(proposal.get("schema_version") == "embedding-production-proposal-v1", "proposal schema mismatch")
    require(proposal.get("proposal_sha256") == digest({k: v for k, v in proposal.items() if k != "proposal_sha256"}),
            "proposal semantic hash mismatch")
    require(proposal.get("retrieval_implementation_hash") == retrieval.implementation_hash(),
            "retrieval implementation differs from pinned proposal")
    require(release.get("schema_version") == "released-development-v2", "release schema mismatch")
    researcher = release["researcher_id"]
    batches = [b for b in proposal["batches"] if b["researcher_id"] == researcher]
    require(len(batches) == 1, "release must select exactly one proposal batch")
    batch = batches[0]
    require(batch["release_sha256"] == hashes["release"] and batch["release_semantic_sha256"] == digest(release),
            "released bytes or semantic hash mismatch")
    require(batch["request_sha256"] == hashes["request"], "staged request byte hash mismatch")
    require(set(request) == {"model", "dimensions", "encoding_format", "input"}, "request fields mismatch")
    settings = {key: request[key] for key in ("model", "dimensions", "encoding_format")}
    require(isinstance(settings["model"], str) and bool(settings["model"])
            and positive_integer(settings["dimensions"]) and settings["encoding_format"] == "float",
            "invalid embedding settings")
    require(settings == proposal["candidate_settings"] and digest(settings) == batch["settings_sha256"],
            "proposal settings mismatch")
    inputs = request["input"]
    require(isinstance(inputs, list) and inputs and all(isinstance(s, str) and s for s in inputs),
            "request inputs must be nonempty strings")
    require(len(set(inputs)) == len(inputs), "batch inputs must be deduplicated")
    require(positive_integer(batch["n_inputs"]) and batch["n_inputs"] == len(inputs)
            and batch["ordered_input_sha256"] == digest(inputs), "ordered input hash or count mismatch")
    sizes = [len(s.encode("utf-8")) for s in inputs]
    require(batch["input_text_utf8_bytes"] == sum(sizes) and batch["max_input_utf8_bytes"] == max(sizes),
            "input byte counts mismatch")
    require(receipt.get("schema_version") == "bounded-embedding-receipt-v1"
            and receipt.get("status") == "complete", "completed producer receipt required")
    require(all(receipt.get(k) == v for k, v in settings.items())
            and positive_integer(receipt.get("dimensions")), "receipt settings mismatch")
    require(receipt.get("packet_sha256") == hashes["request"]
            and receipt.get("input_sha256") == digest(inputs)
            and receipt.get("response_sha256") == hashes["response"], "receipt artifact hashes mismatch")
    require(isinstance(receipt.get("request_id"), str) and bool(receipt["request_id"])
            and positive_integer(receipt.get("count")) and receipt["count"] == len(inputs),
            "receipt request identity or count mismatch")
    for field, length in (("script_sha256", 64), ("runtime_commit", 40)):
        value = receipt.get(field)
        require(isinstance(value, str) and len(value) == length
                and all(c in "0123456789abcdef" for c in value), "missing producer implementation provenance")
    require(response.get("model") == settings["model"], "response model mismatch")
    usage = response.get("usage")
    require(isinstance(usage, dict), "raw response usage required")
    tokens = usage.get("prompt_tokens")
    require(isinstance(tokens, int) and not isinstance(tokens, bool) and 0 <= tokens <= len(raw["request"]) + 1024
            and isinstance(usage.get("total_tokens"), int) and not isinstance(usage["total_tokens"], bool)
            and usage["total_tokens"] == tokens, "incomplete or excessive raw response usage")
    require(receipt.get("usage") == {"prompt_tokens": tokens, "total_tokens": tokens,
                                     "known_input_tokens": tokens, "complete": True}
            and receipt["usage"]["complete"] is True, "receipt/raw response usage mismatch")
    cost = receipt.get("known_usage_usd")
    require(isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0,
            "producer cost must be known and nonnegative")
    raw_vectors = indexed_vectors(response.get("data"), len(inputs), settings["dimensions"])
    receipt_vectors = indexed_vectors(receipt.get("vectors"), len(inputs), settings["dimensions"])
    require(digest(raw_vectors) == digest(receipt_vectors), "receipt vectors differ from indexed raw response")

    sources, items = release["sources"], release["items"]
    require(isinstance(items, list) and items and len(items) == batch["n_decision_bundles"],
            "nonempty exact decision coverage required")
    require(digest(items) == release["items_sha256"] == batch["items_sha256"], "released item hashes mismatch")
    require(sources["allowed_source_manifest_hash"] == batch["allowed_source_manifest_hash"], "source manifest pin mismatch")
    config = {"researcher_id": researcher, "allowed_sources": sources["source_manifest"],
              "allowed_source_manifest_hash": sources["allowed_source_manifest_hash"], "chunk_chars": 1200}
    documents = sources["documents"]
    validate_documents(documents, config)
    mappings = {}
    for mapping in batch["decision_mappings"]:
        key = (mapping["item_id"], mapping["option_order_id"])
        require(key not in mappings, "duplicate decision mapping")
        mappings[key] = mapping
    require(len(mappings) == len(items), "decision mapping coverage mismatch")
    records = batch["input_records"]
    require(isinstance(records, list) and len(records) == len(inputs), "input record coverage mismatch")
    record_by_index = {}
    for record in records:
        index = record["index"]
        require(isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(inputs)
                and index not in record_by_index, "input record index invalid")
        require(record["input_sha256"] == sha(inputs[index].encode("utf-8"))
                and record["utf8_bytes"] == sizes[index], "input record hash or length mismatch")
        record_by_index[index] = record
    expected_roles = {index: set() for index in range(len(inputs))}
    prepared, seen = [], set()
    for item in items:
        require(isinstance(item, dict) and set(item) == ITEM_FIELDS and item["researcher_id"] == researcher,
                "label-free item fields or researcher mismatch")
        key = (item["item_id"], item["option_order_id"])
        require(all(isinstance(v, str) and v for v in key) and key not in seen, "invalid or duplicate item identity")
        seen.add(key)
        mapping = mappings[key]
        decision = {"context": item["context"], "options": item["options"]}
        logical = retrieval.embedding_inputs(documents, config, decision)
        indices = mapping["response_indices"]
        require(isinstance(indices, list) and len(indices) == len(logical)
                and all(isinstance(j, int) and not isinstance(j, bool) and 0 <= j < len(inputs) for j in indices),
                "decision response index mapping invalid")
        require(mapping["decision_sha256"] == digest(decision)
                and mapping["ordered_logical_input_hashes"] == [sha(s.encode("utf-8")) for s in logical]
                and [inputs[j] for j in indices] == logical, "query or approved chunk mapping mismatch")
        for position, index in enumerate(indices):
            role = ({"kind": "decision_query", "decision_sha256": digest(decision)} if position == 0 else
                    {"kind": "approved_chunk", "chunk_index": position - 1})
            expected_roles[index].add(canonical_json(role))
        prepared.append((key, decision, indices))
    for index, roles in expected_roles.items():
        actual = record_by_index[index]["roles"]
        require(roles and isinstance(actual, list) and len(actual) == len(roles)
                and {canonical_json(r) for r in actual} == roles, "unmapped input or role mismatch")

    reference = {"producer_job_id": receipt["request_id"], "receipt_sha256": hashes["receipt"],
                 "production_usage_sha256": digest({"usage": receipt["usage"], "known_usage_usd": cost}),
                 "accounting": "charged_once_by_producer_not_per_derived_bundle"}
    bundles, entries = [], []
    for key, decision, indices in prepared:
        bundle_usage = {"mode": "live", "producer_job_id": receipt["request_id"],
                        "response_sha256": hashes["response"], "receipt_sha256": hashes["receipt"],
                        "request_sha256": hashes["request"], "settings_sha256": digest(settings),
                        "response_indices": indices, "decision_item_sha256": digest(key),
                        "production_usage_reference": reference}
        bundle = retrieval.make_embedding_bundle(documents, config, decision, model=settings["model"],
                                                  vectors=[raw_vectors[j] for j in indices], usage=bundle_usage)
        bundles.append(bundle)
        entries.append({"file": "bundle-" + bundle["bundle_sha256"] + ".json",
                        "file_sha256": sha(encoded(bundle)), "bundle_sha256": bundle["bundle_sha256"],
                        "decision_sha256": digest(decision), "decision_item_sha256": digest(key)})
    manifest = {"schema_version": "offline-embedding-assembly-v1", "status": "complete", "model_calls": 0,
                "input_file_sha256": hashes, "proposal_semantic_sha256": proposal["proposal_sha256"],
                "batch_sha256": digest(batch), "researcher_id_sha256": digest(researcher),
                "allowed_source_manifest_hash": config["allowed_source_manifest_hash"],
                "retrieval_implementation_hash": retrieval.implementation_hash(),
                "production_usage_reference": reference, "bundles": entries}
    return bundles, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ARTIFACTS:
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = {name + "_bytes": getattr(args, name).read_bytes() for name in ARTIFACTS}
        hashes = {name: getattr(args, name + "_sha256") for name in ARTIFACTS}
        bundles, manifest = assemble(**raw, expected_hashes=hashes)
        # No output exists before every input and derived bundle has validated.
        args.output_dir.mkdir(parents=True, exist_ok=False)
        for bundle, entry in zip(bundles, manifest["bundles"]):
            with (args.output_dir / entry["file"]).open("xb") as stream:
                stream.write(encoded(bundle))
        manifest["assembler_sha256"] = sha(Path(__file__).read_bytes())
        with (args.output_dir / "manifest.json").open("xb") as stream:
            stream.write(encoded(manifest))
        print(canonical_json({"status": "complete", "bundles": len(bundles), "model_calls": 0,
                              "manifest_sha256": sha(encoded(manifest))}))
        return 0
    except (ValueError, OSError):
        print(canonical_json({"status": "failed", "error_code": "assembly_validation_or_exclusive_write_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
