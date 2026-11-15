#!/usr/bin/env python3
"""Derive phase1 units from hash-pinned audit024 approved records, without labels.

Only structural metadata/hashes are emitted. Prediction choices, source/profile
text and raw decision strings are not exported. No project code is imported.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

INVENTORY_SHA = "4d90e111d4f02772246f5e9c5806fbcde45d11dd24c2c9a071f054edaac5e8ea"
REPORT_SHA = "188b1ca700bf34f2c48a1cc50330c4d0662fd59f896f8d52cd3e99a973fc1bfa"
METHODS = {"no_profile", "name_only", "raw_evidence", "lexical_retrieval"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--audit024-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--data-root", type=Path, help="Optional extracted private archive root")
    args = parser.parse_args()
    inv_bytes, report_bytes = args.inventory.read_bytes(), args.audit024_report.read_bytes()
    assert sha(inv_bytes) == INVENTORY_SHA
    assert sha(report_bytes) == REPORT_SHA
    inventory, prior = json.loads(inv_bytes), json.loads(report_bytes)
    approved = {row["path"]: row for row in inventory["files"]}
    original_root = Path(inventory["coordinator_root"])
    prior_jobs = {row["job_id"]: row for row in prior["jobs"]}
    read_files, checks, rows = {}, [], []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})

    def read(path, expected=None):
        entry = approved[path]
        selected = Path(path)
        if args.data_root is not None:
            root = args.data_root.resolve()
            selected = (root / Path(path).relative_to(original_root)).resolve()
            assert selected.is_relative_to(root), "mapped path escaped data root"
        raw = selected.read_bytes()
        assert sha(raw) == entry["sha256"] and len(raw) == entry["size_bytes"]
        if expected is not None:
            assert sha(raw) == expected
        read_files[path] = entry
        return json.loads(raw)

    index = read(inventory["index_path"], inventory["index_sha256"])
    release_metadata, item_records, content_groups = {}, {}, defaultdict(dict)
    profile_rows = defaultdict(list)
    for batch in index["batches"]:
        for job in batch["jobs"]:
            if job["kind"] != "predict":
                continue
            assert job["method"] in METHODS
            packet = read(job["packet"]["path"], job["packet"]["sha256"])
            release = read(packet["release"]["path"], packet["release"]["sha256"])
            result = read(job["result"]["path"], job["result"]["sha256"])
            old = prior_jobs[job["job_id"]]
            researcher = job["researcher_id"]
            check(job["job_id"] + ": researcher binding", release["researcher_id"] == researcher == old["researcher_id"])
            check(job["job_id"] + ": method and job binding", old["method"] == job["method"] and result["job_id"] == job["job_id"])
            check(job["job_id"] + ": completed rows match audit024", result["counts"] == old["counts"] and result["status"] == "complete")
            release_metadata[researcher] = {
                "release_sha256": packet["release"]["sha256"],
                "recorded_n_ordered_items": release["n_ordered_items"],
                "recorded_n_semantic_targets": release["n_semantic_targets"],
                "recorded_n_dev_source_groups": release["n_dev_source_groups"],
            }
            items = {item["item_id"]: item for item in release["items"]}
            check(job["job_id"] + ": unique release item IDs", len(items) == len(release["items"]))
            selected = [items[key] for key in packet["item_ids"]]
            check(job["job_id"] + ": result follows selected item IDs", [row["item_id"] for row in result["predictions"]] == packet["item_ids"])
            schedule = [{"item_id": item["item_id"], "option_order_id": item["option_order_id"]} for item in selected]
            check(job["job_id"] + ": selected order schedule", schedule == packet["manifest"]["option_order_schedule"])
            for item, row in zip(selected, result["predictions"]):
                assert set(item) == {"context", "item_id", "option_order_id", "options", "researcher_id"}
                assert isinstance(item["context"], str) and all(isinstance(v, str) for v in item["options"])
                check(job["job_id"] + ": item hash " + row["item_sha256"], row["item_sha256"] == digest(item))
                check(job["job_id"] + ": complete prediction " + row["item_sha256"], row["status"] == "complete")
                content_hash = digest({"context": item["context"], "options": sorted(item["options"])})
                identity = (researcher, item["item_id"])
                if identity in item_records:
                    check(job["job_id"] + ": repeated ID has unchanged ordered content", item_records[identity] == item)
                item_records[identity] = item
                content_groups[(researcher, content_hash)][item["option_order_id"]] = item
                record = {
                    "researcher_id": researcher, "method": job["method"], "batch_id": batch["batch_id"],
                    "job_id": job["job_id"], "item_id_sha256": sha(item["item_id"].encode()),
                    "ordered_item_sha256": digest(item), "option_order_id": item["option_order_id"],
                    "exact_order_invariant_content_sha256": content_hash,
                    "profile_id": old["profile_id"], "profile_content_sha256": old["profile_content_sha256"],
                    "status": row["status"],
                }
                rows.append(record)
                profile_rows[(researcher, job["method"], old["profile_id"])].append(record)
    coverage = defaultdict(list)
    for row in rows:
        coverage[(row["researcher_id"], row["ordered_item_sha256"])].append(row)
    for key, group in coverage.items():
        check("matched four-control coverage: " + key[1], len(group) == 4 and {r["method"] for r in group} == METHODS)
    check("112 complete control rows", len(rows) == 112)
    check("28 ordered decisions", len(coverage) == 28)
    check("no duplicate method/researcher/ordered-item cells", len({(r["method"], r["researcher_id"], r["ordered_item_sha256"]) for r in rows}) == len(rows))
    groups = []
    for (researcher, content_hash), variants in sorted(content_groups.items()):
        check("paired orders: " + content_hash, set(variants) == {"paired-order-0", "paired-order-1"})
        first, second = variants["paired-order-0"], variants["paired-order-1"]
        check("reversed option content: " + content_hash, first["options"] == list(reversed(second["options"])) and first["options"] != second["options"])
        check("distinct IDs for ordered variants: " + content_hash, first["item_id"] != second["item_id"])
        members = [r for r in rows if r["researcher_id"] == researcher and r["exact_order_invariant_content_sha256"] == content_hash]
        check("eight rows per exact content group: " + content_hash, len(members) == 8)
        groups.append({"researcher_id": researcher, "exact_order_invariant_content_sha256": content_hash,
                       "context_sha256": sha(first["context"].encode()), "option_content_sha256_multiset": sorted(sha(v.encode()) for v in first["options"]),
                       "ordered_variants": [{"option_order_id": v["option_order_id"], "item_id_sha256": sha(v["item_id"].encode()), "ordered_item_sha256": digest(v)} for v in [first, second]],
                       "prediction_rows": len(members), "batch_ids": sorted({r["batch_id"] for r in members})})
    profiles = [{"researcher_id": rid, "method": method, "profile_id": pid,
                 "profile_content_sha256": group[0]["profile_content_sha256"], "prediction_rows": len(group),
                 "ordered_item_count": len({r["ordered_item_sha256"] for r in group})}
                for (rid, method, pid), group in sorted(profile_rows.items())]
    researchers = {}
    for researcher in sorted(release_metadata):
        own_rows = [r for r in rows if r["researcher_id"] == researcher]
        own_groups = [g for g in groups if g["researcher_id"] == researcher]
        own_profiles = [p for p in profiles if p["researcher_id"] == researcher]
        researchers[researcher] = {**release_metadata[researcher], "prediction_rows": len(own_rows),
            "distinct_released_item_ids": len({r["item_id_sha256"] for r in own_rows}),
            "ordered_decisions": len({r["ordered_item_sha256"] for r in own_rows}),
            "exact_order_invariant_content_groups": len(own_groups),
            "distinct_context_hashes": len({g["context_sha256"] for g in own_groups}),
            "profiles_by_method": {m: {"profile_ids": len([p for p in own_profiles if p["method"] == m]),
                "distinct_profile_content_hashes": len({p["profile_content_sha256"] for p in own_profiles if p["method"] == m}),
                "rows_per_profile_histogram": dict(Counter(p["prediction_rows"] for p in own_profiles if p["method"] == m))} for m in sorted(METHODS)}}
    report = {"schema_version": "phase1-observation-units-v1", "reader_sha256": sha(Path(__file__).read_bytes()),
        "input_allowlist_sha256": INVENTORY_SHA, "audit024_report_sha256": REPORT_SHA,
        "identity_definition": "SHA-256 of compact sorted-key Unicode JSON containing exact context and lexically sorted option strings; option multiplicity preserved; no case/Unicode/whitespace normalization; item ID, researcher and order label excluded from content hash. Groups are scoped by researcher.",
        "summary": {"control_rows": len(rows), "controls": len(METHODS), "researchers": len(researchers),
            "ordered_decisions": len(coverage), "distinct_released_item_ids": len(item_records),
            "exact_content_groups_scoped_by_researcher": len(groups),
            "exact_content_groups_without_researcher": len({g["exact_order_invariant_content_sha256"] for g in groups}),
            "static_profile_ids": len([p for p in profiles if p["method"] != "lexical_retrieval"]),
            "decision_bound_lexical_profile_ids": len([p for p in profiles if p["method"] == "lexical_retrieval"]),
            "lexical_profile_content_hashes": len({p["profile_content_sha256"] for p in profiles if p["method"] == "lexical_retrieval"}),
            "batch_row_counts": dict(Counter(r["batch_id"] for r in rows))},
        "researchers": researchers, "content_groups": groups, "profile_reuse": profiles, "rows": rows,
        "checks": checks, "check_counts": {"passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks)},
        "limits": ["Exact text grouping is an order-invariant content identity, not a semantic-equivalence or independent-human-judgment proof.",
            "Released item IDs identify ordered variants here. No upstream human-judgment or item-to-DEV-source-group identifier is supplied in the five label-free item fields.",
            "DEV source-group counts are release metadata, not independently reconstructed clustering labels.",
            "Profile identities/content hashes come from the hash-pinned audited 024 report; equal profile content is not equality of full consumer input or an independent intervention.",
            "No outcomes, labels, scoring, confidence intervals, generalization or effective statistical sample size are inferred."]}
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (args.out / "input-inventory.json").write_text(json.dumps({"schema_version": "phase1-units-inputs-v1",
        "read_approved_runtime_files": list(read_files.values()), "metadata_dependencies": [
            {"path": str(args.inventory), "sha256": INVENTORY_SHA}, {"path": str(args.audit024_report), "sha256": REPORT_SHA}]}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"summary": report["summary"], "checks": report["check_counts"], "read_approved_runtime_files": len(read_files)}, sort_keys=True))
    return int(bool(report["check_counts"]["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
