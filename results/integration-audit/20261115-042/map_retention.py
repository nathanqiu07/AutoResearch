#!/usr/bin/env python3
"""Read only pinned metadata; never read referenced profile/result/trace bodies.

The optional --stat-references reports current sizes using lstat only. Archive
overlap is a receipt assertion, not a fresh payload hash verification.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

H = re.compile(r"[0-9a-f]{64}\Z")


def digest(b):
    return hashlib.sha256(b).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def refs(obj, pointer=""):
    """Only explicit two-key file references; scalar paths never followed."""
    if isinstance(obj, dict):
        if set(obj) == {"path", "sha256"}:
            if not isinstance(obj["path"], str) or not H.fullmatch(obj["sha256"]):
                raise ValueError("Malformed file identity at " + pointer)
            yield pointer, obj["path"], obj["sha256"]
        for key, value in obj.items():
            yield from refs(value, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from refs(value, pointer + "/" + str(i))


def classify(occurrences):
    roles = set()
    for occ in occurrences:
        p = occ["json_pointer"].split("/")
        if p[1:2] == ["jobs"]:
            roles.add("job." + p[3])
        elif p[1:2] == ["batches"]:
            roles.add("batch." + p[3])
        else:
            roles.add(occ["document"] + "." + (p[1] if len(p) > 1 and p[1] else "entrypoint"))
    return sorted(roles)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pins", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--stat-references", action="store_true")
    args = ap.parse_args()
    pins = json.loads(args.pins.read_bytes())
    data = {}; original_bytes = {}; checks = []
    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    for e in pins["inputs"]:
        path = Path(e["path"])
        b = path.read_bytes()
        check("pinned_metadata:" + e.get("relative_path", e["role"]),
              digest(b) == e["sha256"] and len(b) == e["size_bytes"])
        key = e.get("relative_path", e["role"])
        data[key] = json.loads(b); original_bytes[e["path"]] = b
    idx, sup, led = (data[k] for k in ("completion", "supervisor", "ledger_snapshot"))
    jobs = idx["jobs"]; batches = idx["batches"]
    requests = [r for j in jobs for r in j["requests"]]
    rows = led["reservation_rows"]
    check("ledger_row_shape", all(isinstance(r, list) and len(r) == 5 for r in rows))
    meta = [json.loads(r[4]) for r in rows]
    check("ledger_metadata_schema", all(set(m) == {"model", "reasoning", "request_sha256"} for m in meta))
    check("ledger_logical_sha256", digest(canonical({k: led[k] for k in ("policy_rows", "reservation_rows")})) == led["logical_snapshot_sha256"])
    check("204_unique_jobs", len(jobs) == len({j["job_id"] for j in jobs}) == 204)
    check("4_unique_batches", len(batches) == len({b["batch_id"] for b in batches}) == 4)
    check("672_unique_request_hashes", len(requests) == len({r["request_sha256"] for r in requests}) == 672)
    check("672_unique_endpoint_body_hashes", len({r["endpoint_body_sha256"] for r in requests}) == 672)
    check("672_unique_reservations", len(rows) == len({r[0] for r in rows}) == 672)
    check("ledger_to_index_request_multiset", Counter(m["request_sha256"] for m in meta) == Counter(r["request_sha256"] for r in requests))
    check("complete_statuses", all(j["status"] == "complete" for j in jobs) and all(r["status"] == "complete" for r in requests) and all(r[3] == "complete" for r in rows))
    check("ledger_no_pending_uncertain_hold", led["pending"] == led["uncertain"] == led["retained_hold_nanos"] == 0)
    check("job_usage_zero_cache_unknowns", all(j["usage"][k] == 0 for j in jobs for k in ("cache_hits", "uncertain_attempts", "unknown_input_usage_attempts", "unknown_output_usage_attempts")))
    check("job_usage_complete", all(j["usage"]["reported_usage_complete"] is True for j in jobs))
    check("fixed_model_reasoning_ledger_to_jobs", {(m["model"], m["reasoning"]) for m in meta} == {(j["backend"]["model"], j["backend"]["reasoning"]) for j in jobs} == {("gpt-6-luna", "medium")})
    nanos = sum(r[2] for r in rows)
    usage_usd = sum((Decimal(str(j["usage"]["reported_api_usd"])) for j in jobs), Decimal(0))
    check("spend_totals", nanos == led["known_spent_nanos"] == idx["counts"]["verified_known_spent_nanos"] == sup["known_verified_spend_nanos"] == 124590125 and usage_usd * 10**9 == nanos)
    check("attempt_totals", sum(j["usage"]["attempted_calls"] for j in jobs) == led["attempts"] == sup["known_verified_attempts"] == idx["counts"]["verified_attempted_calls"] == 672)
    check("terminal_supervisor", sup["status"] == "complete" and sup["child_process_terminal"] is True and sup["native_accounting_drain_verified"] is True and sup["no_retry_or_resume"] is True and sup["stop_reason"] is None)
    check("supervisor_plan_totals", sup["planned_batches"] == 4 and sup["planned_jobs"] == 204 and sup["planned_call_ceiling"] == 672)
    check("supervisor_verified_batch_names", sorted(sup["completed_verified_batches"]) == sorted(b["batch_id"] + "-verified.json" for b in batches))
    check("index_counts", idx["counts"]["planned_jobs"] == 204 and idx["counts"]["planned_requests"] == idx["counts"]["observed_terminal_attempts"] == 672 and idx["counts"]["observed_terminal_cache_hits"] == idx["counts"]["observed_terminal_unknown_attempts"] == 0)
    batch_summary = []
    for b in batches:
        js = [j for j in jobs if j["batch_id"] == b["batch_id"]]
        rs = [r for j in js for r in j["requests"]]
        nh = {r["request_sha256"] for r in rs}
        ns = sum(r[2] for r, m in zip(rows, meta) if m["request_sha256"] in nh)
        check("batch_totals:" + b["batch_id"], len(js) == b["planned_jobs"] and len(rs) == b["planned_requests"] == b["attempted_calls"] and ns == b["known_spent_nanos"] and b["known_verified"] is True)
        batch_summary.append({"batch_id": b["batch_id"], "jobs": len(js), "requests": len(rs), "known_spent_nanos": ns})
    check("each_job_plan_count", all(j["planned_request_count"] == len(j["requests"]) == j["usage"]["attempted_calls"] for j in jobs))
    check("aliases_not_independent", all(j["new_independent_observations_from_aliases"] == 0 for j in jobs))

    # Catalog existing archive members solely from their public receipts.
    prefix = "results/integration-audit/"
    cm = data[prefix + "20261115-040/copy-manifest.json"]
    cr = data[prefix + "20261115-040/copy-receipt.json"]
    cv = data[prefix + "20261115-040/standalone-verification.json"]
    check("040_manifest_receipt_link", digest(original_bytes[str(Path(pins["repo_root"]) / (prefix + "20261115-040/copy-manifest.json"))]) == cr["manifest_sha256"] == cv["manifest_sha256"])
    archives = [a for a in cm["files"] if a["kind"] == "private_archive"]
    check("040_sixteen_archive_metadata", len(archives) == cm["private_archive_count"] == cv["private_archives_verified"] == 16)
    catalog = []
    archive_summaries = []
    for a in archives:
        receipt = data[a["receipt"]]
        if "new_archives" in receipt:
            group = next(g for g in receipt["new_archives"] if g["sha256"] == a["sha256"])
            rr = [r for r in receipt["required_records"] if r.get("archive_group") == group["archive_group"] and r["storage"] == "new_archive"]
            check("032_member_catalog:" + a["sha256"], len(rr) == group["member_count"] and {r["archive_member"]: r["sha256"] for r in rr} == group["members"])
        elif "original_receipt" in receipt:
            origkey = str(Path(a["receipt"]).parent / receipt["original_receipt"])
            orig = data[origkey]
            check("025_original_receipt_link", orig["sha256"] == receipt["archive_sha256"] == a["sha256"])
            rr = [{"archive_member": k, **v} for k, v in orig["members"].items()]
        else:
            check("archive_receipt_link:" + a["sha256"], receipt["archive_sha256"] == a["sha256"])
            rr = receipt.get("files", receipt.get("members"))
        archive_summaries.append({"archive_sha256": a["sha256"], "archive_bytes": a["size_bytes"], "receipt": a["receipt"], "catalog_members": len(rr), "checkpoint_path": str(Path(cr["destination"]) / a["destination"])})
        for r in rr:
            catalog.append({"recorded_path": r.get("original_path", r.get("path")), "sha256": r["sha256"], "size_bytes": r.get("size_bytes", r.get("bytes")), "archive_member": r.get("archive_member", r.get("member")), "archive_sha256": a["sha256"], "receipt": a["receipt"]})
    # The later039 gaps are also compared; they are not in040's checkpoint.
    for key in sorted(data):
        if key.startswith(prefix + "20261115-039/"):
            receipt = data[key]
            archive_summaries.append({"archive_sha256": receipt["archive_sha256"], "archive_bytes": receipt["archive_size_bytes"], "receipt": key, "catalog_members": len(receipt["files"]), "checkpoint_path": None})
            for r in receipt["files"]:
                catalog.append({"recorded_path": r["path"], "sha256": r["sha256"], "size_bytes": r["size_bytes"], "archive_member": r["archive_member"], "archive_sha256": receipt["archive_sha256"], "receipt": key})
    by_hash = defaultdict(list)
    for c in catalog:
        by_hash[c["sha256"]].append(c)

    identities = defaultdict(list)
    for role in ("completion", "supervisor", "ledger_snapshot"):
        e = next(e for e in pins["inputs"] if e["role"] == role)
        identities[(e["path"], e["sha256"])].append({"document": role, "json_pointer": ""})
        for pointer, path, h in refs(data[role]):
            identities[(path, h)].append({"document": role, "json_pointer": pointer})
    mapped = []
    for (path, h), occ in sorted(identities.items()):
        available = by_hash.get(h, [])
        exact = [a for a in available if a["recorded_path"] == path]
        known_size = {a["size_bytes"] for a in available if a["size_bytes"] is not None}
        check("receipt_size_consistency:" + h, len(known_size) <= 1)
        observed = None
        if args.stat_references:
            pp = Path(path)
            if not pp.is_absolute() or ".." in pp.parts or pp.suffix in {".sqlite", ".db", ".eval"}:
                raise ValueError("Reference is not eligible for bounded lstat")
            try:
                ss = pp.lstat()
                observed = {"kind": "regular" if stat.S_ISREG(ss.st_mode) else "symlink" if stat.S_ISLNK(ss.st_mode) else "other", "size_bytes": ss.st_size, "mtime_ns": ss.st_mtime_ns}
            except FileNotFoundError:
                observed = {"kind": "missing"}
        category = "exact_path_and_hash_retained" if exact else "hash_only_bytes_retained" if available else "not_in_compared_receipts"
        mapped.append({"path": path, "sha256": h, "logical_occurrences": occ, "roles": classify(occ), "retention_status": category, "receipt_matches": available, "retained_size_bytes": next(iter(known_size), None), "observed_lstat": observed})
    paths = defaultdict(set)
    for r in mapped:
        paths[r["path"]].add(r["sha256"])
    conflicts = [{"path": p, "sha256s": sorted(hs)} for p, hs in paths.items() if len(hs) > 1]
    by_content = defaultdict(list)
    for r in mapped:
        by_content[r["sha256"]].append(r)
    gap_groups = []
    for h, rr in sorted(by_content.items()):
        if not by_hash.get(h):
            sizes = {r["observed_lstat"]["size_bytes"] for r in rr if r["observed_lstat"] and r["observed_lstat"]["kind"] == "regular"}
            gap_groups.append({"sha256": h, "logical_paths": [r["path"] for r in rr], "roles": sorted({q for r in rr for q in r["roles"]}), "observed_size_bytes": next(iter(sizes)) if len(sizes) == 1 else None, "size_consistent": len(sizes) <= 1})
    source = data[prefix + "20261115-035/final/source-reference.json"]
    check("declared_runtime_source_reference", idx["runtime_sha"] == source["commit"] and source["file_count"] == len(source["files"]) == 92)
    source_locations = by_hash.get(source["sha256"], [])
    check("runtime_source_tar_in_receipt_catalog", len(source_locations) > 0)
    retained = Counter(r["retention_status"] for r in mapped)
    roles = defaultdict(Counter)
    for r in mapped:
        for role in r["roles"]:
            roles[role][r["retention_status"]] += 1
    for path, b in original_bytes.items():
        check("metadata_unchanged:" + path, Path(path).read_bytes() == b)
    report = {
        "schema_version": "profile204-retention-proposal-v1", "argv": sys.argv,
        "reader_sha256": digest(Path(__file__).read_bytes()), "pins_sha256": digest(args.pins.read_bytes()),
        "scope": "First-order explicit file identities in three closed snapshots, compared with18 public archive receipt catalogs. No runtime body reads or copies; no active database.",
        "closed_accounting": {"jobs": len(jobs), "control_jobs": sum(j["control_cell"] is not None for j in jobs), "search_jobs": sum(j["search_cell"] is not None for j in jobs), "requests": len(requests), "ledger_rows": len(rows), "known_spent_nanos": nanos, "known_spent_usd": str(usage_usd), "cache_hits": 0, "pending": led["pending"], "uncertain": led["uncertain"], "retained_hold_nanos": led["retained_hold_nanos"], "model_reasoning": [["gpt-6-luna", "medium"]], "request_multiset_matches": True, "endpoint_hashes_are_distinct_identity": Counter(m["request_sha256"] for m in meta) != Counter(r["endpoint_body_sha256"] for r in requests), "batches": batch_summary},
        "retention": {"reference_occurrences_including_entrypoints": sum(len(r["logical_occurrences"]) for r in mapped), "logical_path_hash_identities": len(mapped), "distinct_paths": len(paths), "distinct_content_hashes": len(by_content), "status_counts": dict(retained), "role_status_counts": {k: dict(v) for k, v in sorted(roles.items())}, "same_path_multiple_hashes": conflicts, "new_content_hashes": len(gap_groups), "new_bytes_from_lstat_not_hash_verified": sum(g["observed_size_bytes"] or 0 for g in gap_groups), "new_content_unknown_size_count": sum(g["observed_size_bytes"] is None for g in gap_groups), "referenced_nonregular_or_missing": [{"path": r["path"], "observation": r["observed_lstat"]} for r in mapped if r["observed_lstat"] and r["observed_lstat"]["kind"] != "regular"]},
        "archive_catalogs": archive_summaries,
        "distinct_recorded_identities": {"manifest_scalar_different_from_raw_file_sha_jobs": sum(j["manifest_sha256"] != j["manifest"]["sha256"] for j in jobs), "interpretation": "All manifest file references use the path+sha256 pair. The scalar manifest_sha256 is a separate recorded identity; its derivation is unverified without reading manifest bodies. Initial equality assumption was rejected and preserved in run-01."},
        "runtime_source": {"declared_commit": source["commit"], "source_tar_sha256": source["sha256"], "source_file_count": source["file_count"], "receipt_matches": source_locations, "limit": "Recorded source reference; no executing-environment or import identity verified."},
        "limits": ["Snapshot agreement is not authenticated physical provider execution, invoicing, or new independent observations.", "No trace/result/profile/packet/release body was read or hashed; raw reference hashes are declarations until preservation verification.", "No recursive dependency closure beyond explicitly listed first-order path+SHA pairs; labels and scoring were not accessed.", "Archive overlap is based on pinned public receipt metadata; payload members were not reread in this review.", "lstat sizes are a current estimate and do not prove byte identity; per-content deduplication requires matching bytes during future preservation.", "This compares the16 archives in040 plus the039 source/publication gap archives, not every private file on the machine. Pending041 is separate and has no new profile inputs per parent's stated scope.", "Scalar SQLite source_path is deliberately excluded; no SQLite access, network, model calls, owner-code imports, or raw copies."],
        "checks": checks, "check_counts": {"passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks)}}
    args.out.mkdir(parents=True, exist_ok=False)
    for filename, obj in (("report.json", report), ("retention-map.json", {"schema_version": "profile204-first-order-retention-map-v1", "pins_sha256": report["pins_sha256"], "inputs": mapped}), ("new-content-proposal.json", {"schema_version": "profile204-new-content-proposal-v1", "files": gap_groups})):
        (args.out / filename).write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"check_counts": report["check_counts"], "accounting": report["closed_accounting"], "retention": {k: v for k, v in report["retention"].items() if k != "role_status_counts"}}, sort_keys=True))


if __name__ == "__main__":
    main()
