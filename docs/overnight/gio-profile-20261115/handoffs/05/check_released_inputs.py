"""Check control construction on exact released dev bundles, without predictions.

The evaluator handoff and every released file must match their recorded hashes.
Only the named shared-dev releases are opened. Output contains hashes and spans,
not source text, decision text, labels, scores, or synthetic predictions.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--handoff-sha256", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[5]))
    parser.add_argument("--consumer-model", required=True)
    parser.add_argument("--cap", type=int, default=2048)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.cap < 0 or not args.consumer_model.strip():
        parser.error("cap must be nonnegative and consumer model nonempty")
    if file_hash(args.handoff) != args.handoff_sha256:
        raise ValueError("evaluator handoff file hash mismatch")
    handoff = json.loads(Path(args.handoff).read_text())
    if handoff.get("role_id") != "04" or handoff.get("event") != "DATA_READY":
        raise ValueError("not an evaluator DATA_READY handoff")
    root = Path(args.repo_root).resolve()
    sys.path.insert(0, str(root))
    from autoresearch.taste.overnight.baselines import METHODS, register_baselines
    from autoresearch.taste.overnight.contracts import build_profile, digest, render_content, validate_documents
    from autoresearch.taste.overnight.retrieval import chunk_documents

    class NoCalls:
        label, model = "no-model-calls", "construction-only"

        def complete(self, *unused, **settings):
            raise AssertionError("input readiness must not call a model")

    code_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", "autoresearch/taste/overnight"],
                                    cwd=root, text=True)
    if dirty:
        raise ValueError("runtime code must be committed before readiness checking")
    register_baselines()
    shared = {(r["location"], r["sha256"]) for r in handoff["outputs"] if r.get("visibility") == "shared-dev"}
    releases = handoff["development"]["released"]
    if not releases:
        raise ValueError("no declared development releases")
    rows, bundles = [], []
    names = {"neel_nanda": "Neel Nanda", "chris_olah": "Chris Olah"}
    expected_unavailable = {
        "semantic_retrieval": "embedding_backend_not_configured",
        "memory_summary": "missing_or_invalid_frozen_profile",
        "profile_retrieval": "missing_or_invalid_frozen_profile",
    }
    for release in releases:
        if (release["location"], release["sha256"]) not in shared:
            raise ValueError("release is not an exact shared-dev output")
        if file_hash(release["location"]) != release["sha256"]:
            raise ValueError("released bundle file hash mismatch")
        bundle = json.loads(Path(release["location"]).read_text())
        if bundle.get("schema_version") != "released-development-v2":
            raise ValueError("only declared development-v2 bundles are supported")
        if digest(bundle) != release["semantic_sha256"]:
            raise ValueError("released bundle semantic hash mismatch")
        researcher, items, sources = bundle["researcher_id"], bundle["items"], bundle["sources"]
        if not isinstance(items, list) or not items:
            raise ValueError("released item list must be nonempty; readiness is unmeasured")
        if (researcher != release["researcher_id"] or researcher not in names
                or digest(items) != bundle["items_sha256"]
                or digest(items) != release["items_sha256"]
                or len(items) != release["n_ordered_items"]
                or sources["allowed_source_manifest_hash"] != release["allowed_source_manifest_hash"]):
            raise ValueError("released identity, item, or source hash mismatch")
        documents = sources["documents"]
        base = {"researcher_id": researcher, "researcher_name": names[researcher],
                "allowed_sources": sources["source_manifest"],
                "allowed_source_manifest_hash": sources["allowed_source_manifest_hash"],
                "personalization_cap": args.cap, "replicate_id": 0, "code_sha": code_sha,
                "extractor_settings": {}, "consumer_identity": {"model": args.consumer_model},
                "chunk_chars": 1200, "top_k": 5}
        validate_documents(documents, base)
        source_by_id = {d["document_id"]: d["content"] for d in documents}
        chunks = chunk_documents(documents, base)
        chunk_ends = {(c["document_id"], c["start"]): c["end"] for c in chunks}
        selected_hashes = {method: [] for method in METHODS}
        same_raw_lexical = 0
        for item in items:
            if set(item) != {"context", "item_id", "option_order_id", "options", "researcher_id"}:
                raise ValueError("unexpected fields in label-free item")
            if item["researcher_id"] != researcher:
                raise ValueError("item researcher mismatch")
            decision = {"context": item["context"], "options": item["options"]}
            contents = {}
            for method in METHODS:
                config = dict(base, method_id=method, decision=decision)
                profile = build_profile(documents, config, NoCalls())
                content = profile.content
                rendered_bytes = len(render_content(content).encode("utf-8"))
                passages = content.get("passages", []) if isinstance(content, dict) else []
                spans = []
                for passage in passages:
                    text = source_by_id[passage["document_id"]]
                    start, end = passage["start"], passage["end"]
                    if (not isinstance(start, int) or not isinstance(end, int)
                            or not 0 <= start < end <= len(text) or passage["text"] != text[start:end]):
                        raise ValueError("selected passage does not match exact approved span")
                    spans.append({"document_id": passage["document_id"], "start": start, "end": end,
                                  "text_sha256": hashlib.sha256(passage["text"].encode()).hexdigest(),
                                  "truncated": end != chunk_ends[(passage["document_id"], start)]})
                if rendered_bytes > args.cap or profile.fit_usage["calls"] != 0:
                    raise ValueError("control exceeded cap or called model")
                if method == "no_profile" and (content is not None or not profile.intentional_empty):
                    raise ValueError("no-profile must be intentionally empty")
                if method == "name_only" and content != {"name": names[researcher]}:
                    raise ValueError("name-only contains unexpected personalization")
                expected_error = expected_unavailable.get(method)
                expected = ((profile.status == "unavailable" and profile.error_code == expected_error)
                            if expected_error else profile.status == "complete")
                contents[method] = profile.content_sha256
                selected_hashes[method].append(digest(spans))
                rows.append({"researcher_id": researcher, "item_id": item["item_id"],
                             "option_order_id": item["option_order_id"], "method_id": method,
                             "decision_sha256": digest(decision), "config_id": profile.config_id,
                             "profile_id": profile.profile_id, "content_sha256": profile.content_sha256,
                             "method_implementation_hash": profile.method_implementation_hash,
                             "renderer_implementation_hash": profile.renderer_implementation_hash,
                             "prompt_sha256": profile.prompt_sha256,
                             "allowed_source_manifest_hash": profile.allowed_source_manifest_hash,
                             "status": profile.status, "error_code": profile.error_code,
                             "expected_state": expected, "rendered_utf8_bytes": rendered_bytes,
                             "personalization_cap": args.cap, "passage_count": len(spans),
                             "selected_source_count": len({p["document_id"] for p in spans}),
                             "truncated_passage_count": sum(p["truncated"] for p in spans),
                             "spans": spans, "fit_usage": profile.fit_usage})
            same_raw_lexical += contents["raw_evidence"] == contents["lexical_retrieval"]
        bundles.append({"researcher_id": researcher, "bundle_sha256": release["sha256"],
                        "bundle_semantic_sha256": release["semantic_sha256"],
                        "items_sha256": release["items_sha256"], "n_ordered_items": len(items),
                        "n_semantic_targets": release["n_semantic_targets"],
                        "n_dev_source_groups": release["n_dev_source_groups"],
                        "n_fit_documents": len(documents), "available_chunks": len(chunks),
                        "raw_equals_lexical_count": same_raw_lexical,
                        "distinct_selected_span_sets": {m: len(set(v)) for m, v in selected_hashes.items()}})
    report = {"schema_version": "control-input-readiness-v1", "mode": "offline_construction_only",
              "code_sha": code_sha, "handoff_sha256": args.handoff_sha256,
              "checker_sha256": file_hash(__file__), "consumer_identity": {"model": args.consumer_model},
              "personalization_cap": args.cap, "model_calls": 0,
              "scientific_accuracy": "not_measured", "payload_prediction_audit": "not_performed",
              "expected_prerequisite_gaps": expected_unavailable,
              "all_expected_states": all(row["expected_state"] for row in rows),
              "bundles": bundles, "rows": rows}
    with Path(args.output).open("x") as output:
        json.dump(report, output, ensure_ascii=False, allow_nan=False, indent=2)
        output.write("\n")
    print(json.dumps({"rows": len(rows), "all_expected_states": report["all_expected_states"],
                      "output_sha256": file_hash(args.output), "bundles": bundles}))


if __name__ == "__main__":
    main()
