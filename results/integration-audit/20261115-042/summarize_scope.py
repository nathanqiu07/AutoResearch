#!/usr/bin/env python3
"""Classify a pinned metadata-only retention map without opening its references."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def category(row):
    roles = set(row["roles"])
    if "completion.unchanged_planned_coverage" in roles:
        return "hold_coverage_context_not_needed_for_terminal_record_bytes"
    if roles & {"job.trace_files", "job.result", "job.profile"}:
        return "saved_request_response_result_profile_bytes"
    if roles & {"job.original_candidate_packet", "job.original_prepared", "job.rebind_evidence", "completion.candidate_proof", "completion.prepared_index"}:
        return "original_plan_rebind_and_candidate_provenance"
    if roles & {"job.claim", "job.manifest", "job.prepared_packet", "job.release", "job.dispatch_receipt", "job.prepared", "batch.summary", "batch.verified_record"}:
        return "execution_binding_and_batch_records"
    if roles & {"completion.script", "completion.supervisor_source"}:
        return "compiler_supervisor_source_optional_separate_code_review"
    return "closed_accounting_supervision_diagnostics_metadata"


def stats(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["sha256"]].append(row)
    sizes = []
    for h, rs in groups.items():
        ss = {r["observed_lstat"]["size_bytes"] for r in rs if r["observed_lstat"] and r["observed_lstat"]["kind"] == "regular"}
        assert len(ss) == 1, "Need consistent observed sizes for each declared content hash"
        sizes.append(next(iter(ss)))
    return {"logical_files": len(rows), "declared_content_hashes": len(groups),
            "logical_path_bytes_lstat": sum(r["observed_lstat"]["size_bytes"] for r in rows),
            "deduplicated_bytes_estimate": sum(sizes)}


def prefix(path):
    p = Path(path)
    coordinator = Path("/private/tmp/gio-profile-20261115-coordinator")
    if p.is_relative_to(coordinator):
        return str(coordinator / p.relative_to(coordinator).parts[0])
    return str(Path(*p.parts[:4]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--map-sha256", required=True)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    b = a.map.read_bytes()
    if hashlib.sha256(b).hexdigest() != a.map_sha256:
        raise ValueError("Wrong retention-map hash")
    rows = json.loads(b)["inputs"]
    by_category = defaultdict(list); by_prefix = defaultdict(list); by_role = defaultdict(list)
    for r in rows:
        by_category[category(r)].append(r)
        by_prefix[prefix(r["path"])].append(r)
        for role in r["roles"]:
            by_role[role].append(r)
    hold = by_category["hold_coverage_context_not_needed_for_terminal_record_bytes"]
    out = {
        "schema_version": "profile204-retention-scope-proposal-v1",
        "map_sha256": a.map_sha256,
        "total": stats(rows),
        "mutually_exclusive_categories": {k: stats(v) for k, v in sorted(by_category.items())},
        "path_prefixes": {k: stats(v) for k, v in sorted(by_prefix.items())},
        "roles_nonadditive": {k: stats(v) for k, v in sorted(by_role.items())},
        "hold_before_copy": [{"path": r["path"], "sha256": r["sha256"], "roles": r["roles"], "reason": "Coverage/selection or explicitly excluded-job context, not a dependency required to retain the204 closed job records; body uninspected and not authorized for expansion to private scoring/labels."} for r in hold],
        "potential_content_scope": {
            "direct_evidence_paths": "All saved request/response trace, result and profile refs are under explicitly indexed coordinator output or receipts/preparation paths.",
            "path_not_content_attestation": "This verifies recorded location/role only. It cannot establish that every opaque body is label-free. No file body outside the three supplied closed metadata snapshots and public archive receipts was opened.",
            "evaluation_only_or_label_path_detection": "No explicitly referenced basename/path contains evaluator, final-label, test-label, heldout-label, scoring, or SQLite file suffix. The richer-fit-paired-selection record is held separately as possible selection-sensitive metadata; other coverage context is also held.",
            "no_new_corpus_closure": "Do not recursively copy all source corpora from profile/release pointers. Saved requests/profile bytes and frozen job/batch bindings are the first proposed tier; nested source history would require a separate purpose, explicit release and exact named references.",
        },
        "required_decision": "Root selects which categories to retain. Recommend exact direct evidence and execution-binding records plus closed accounting/supervision and minimal rebind provenance, with raw bytes private, content-hash deduplication verified during copy. Hold the four coverage-context refs; compiler/supervisor code can be reviewed separately before deciding whether public. No retention is executed by this proposal.",
        "limits": ["Category and prefix byte totals deduplicate only within that row; role totals overlap and must not be added.", "All sizes are lstat observations, not raw-hash verification. Declared content hashes determine candidate deduplication only.", "Runtime source f6cd4fb5 is already cataloged separately and excluded from new-byte estimates.", "No claim to recover original Git history, runtime environment, provider wire calls, quality scores or private labels."]}
    forbidden = [r["path"] for r in rows if any(x in r["path"].lower() for x in ("evaluator", "final-label", "test-label", "heldout-label", "scoring")) or Path(r["path"]).suffix in (".sqlite", ".db", ".eval")]
    out["named_path_screen"] = {"rules": ["evaluator", "final-label", "test-label", "heldout-label", "scoring", ".sqlite", ".db", ".eval"], "matches": forbidden, "not_a_content_safety_test": True}
    assert not forbidden, "Unexpected sensitive-path marker; require scope decision"
    with a.out.open("x") as f:
        json.dump(out, f, sort_keys=True, indent=2); f.write("\n")
    print(json.dumps({"total": out["total"], "categories": out["mutually_exclusive_categories"], "held_paths": len(hold)}, sort_keys=True))


if __name__ == "__main__":
    main()
