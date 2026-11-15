"""Bounded independent audit034 cross-check; no project imports or model calls.

Reads public metadata plus four explicitly inventoried sparse canonical profiles.
Only hashes, counts and status metadata are emitted. No choices or text exports.
"""
import argparse
from collections import Counter, defaultdict
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(value):
    return hashlib.sha256(value).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":")).encode())


def read_pin(path, expected):
    raw = path.read_bytes()
    assert sha(raw) == expected, "Pinned metadata changed"
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--phase1-report", required=True, type=Path)
    parser.add_argument("--source030-manifest", required=True, type=Path)
    parser.add_argument("--execution033-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--preservation", type=Path)
    args = parser.parse_args()
    assert bool(args.archive_root) == bool(args.preservation)
    stage = args.evidence_root
    manifest = read_pin(stage / "SAFE_PACKAGE_MANIFEST.json", "d165a5b8431e91ca022a03c5b7ad63bbadac52834132f8c42665e9766d568826")
    for name, expected in manifest["files"].items():
        relative = PurePosixPath(name)
        path = stage / name
        assert not relative.is_absolute() and ".." not in relative.parts
        assert path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == expected
    report = read_pin(stage / "run-03/report.json", "0816591add6aaea9bfe58df5df8f164831375de7112e8eed8a81cfcd47a54941")
    inventory = read_pin(stage / "run-03/input-inventory.json", "39eb0975a0d97205c978fb0763111e02e57c458386bb3e235888a5a9a0eeec3e")
    phase1 = read_pin(args.phase1_report, "cea8ff174417f23a615b3f8f8e2ab98e288ff896954d28e95786f926fc6b12db")
    source030 = read_pin(args.source030_manifest, "8a188b9a737712138a94d36c5f5e92fb1c6181ca137a2566cb169fef8703d6c6")
    prior = read_pin(args.execution033_report, "2434ad33f2f47a080615abdba43786ac64f13f63f13873c9acacdd6435745feb")
    source = json.loads((stage / "SOURCE_SNAPSHOT.json").read_text())
    assert source["source_commit"] == source030["source_commit"]
    assert all(source030["files"][name] == value for name, value in source["files"].items())
    assert sha((stage / "read_control_execution.py").read_bytes()) == report["reader_sha256"] == "9b4f2a8088c16d46dcdda304b50399c32dde245f0e8c91349b7600c5e5965d02"
    assert sha((stage / "reader033_helpers.py").read_bytes()) == prior["reader_sha256"]
    assert len(report["checks"]) == 4572 and all(row["verified"] for row in report["checks"])
    conditions = {("no_profile", 2048), ("name_only", 2048),
                  ("profile_retrieval", 2048), ("profile_retrieval", 8192)}
    conditions |= {(method, cap) for method in ("raw_evidence", "lexical_retrieval", "semantic_retrieval") for cap in (512, 2048, 8192)}
    by_item = defaultdict(list)
    canonical = {}
    for row in report["rows"]:
        by_item[row["item_sha256"]].append(row)
        key = row["job_id"], row["item_id_sha256"]
        assert key not in canonical
        canonical[key] = row
    assert len(canonical) == 364 and len(by_item) == 28
    assert set(by_item) == {row["ordered_item_sha256"] for row in phase1["rows"]}
    for group in by_item.values():
        assert len(group) == 13 and {(r["method"], r["cap"]) for r in group} == conditions
    jobs = {row["job_id"]: row for row in report["jobs"]}
    assert len(jobs) == len(report["jobs"]) == 234
    assert Counter(row["job_id"] for row in report["rows"]) == Counter({k: v["attempted_calls"] for k, v in jobs.items()})
    assert sum(j["attempted_calls"] for j in jobs.values()) == 364
    total = sum((Decimal(j["reported_api_usd"]) for j in jobs.values()), Decimal(0))
    assert total == Decimal("0.057470")
    for batch in report["batches"]:
        selected = [j for j in jobs.values() if j["batch"] == batch["name"]]
        assert len(selected) == batch["jobs"]
        assert sum(j["attempted_calls"] for j in selected) == batch["rows"] == batch["attempts"]
        assert sum((Decimal(j["reported_api_usd"]) for j in selected), Decimal(0)) == Decimal(batch["reported_api_usd"])
    prior_backend = {row["backend_identity_sha256"] for row in prior["canonical_jobs"]}
    prior_settings = {row["settings_sha256"] for row in prior["canonical_jobs"]}
    prior_system = {row["verified_hashes"]["system"] for row in prior["aliases"]}
    assert {row["verified_hashes"]["backend_identity"] for row in report["rows"]} == prior_backend
    assert {row["verified_hashes"]["settings"] for row in report["rows"]} == prior_settings
    assert {row["verified_hashes"]["system"] for row in report["rows"]} == prior_system
    p1_parents = {row["parent_job_id"] for row in prior["canonical_jobs"]}
    hybrid_jobs = [j for j in jobs.values() if j["method"] == "profile_retrieval"]
    assert len(hybrid_jobs) == 56 and all(len(j["parent_job_ids"]) == 2 and len(set(j["parent_job_ids"]) & p1_parents) == 1 for j in hybrid_jobs)
    seen = set()
    alias_cells = defaultdict(set)
    alias_jobs = set()
    for alias in report["sparse_aliases"]:
        key = alias["canonical_job_id"], alias["item_id_sha256"]
        cap = alias["comparison_cap"]
        triple = key + (cap,)
        assert triple not in seen and cap in (512, 8192)
        seen.add(triple)
        alias_cells[key].add(cap)
        alias_jobs.add(key[0])
        original = canonical[key]
        assert original["method"] in ("no_profile", "name_only") and original["cap"] == 2048
        assert alias["canonical_profile_id"] == original["profile_id"] and alias["verified_hashes"] == original["verified_hashes"]
        assert alias["additional_calls"] == alias["additional_observations"] == 0
    assert len(seen) == 112 and len(alias_cells) == 56 and len(alias_jobs) == 4
    assert all(value == {512, 8192} for value in alias_cells.values())
    subset = sum((Decimal(jobs[j]["reported_api_usd"]) for j in alias_jobs), Decimal(0))
    assert subset == Decimal("0.00463625") and alias_jobs <= set(jobs)
    owner = json.loads((stage / "018-completed-control-predictions.json").read_text())
    owner_jobs = {j["job_id"]: j for j in owner["jobs"]}
    private = [row for row in inventory["files"] if row["kind"] == "external"]
    assert len(private) == 2609
    preservation = json.loads(args.preservation.read_text())["files"] if args.archive_root else None
    accessed, variants = [], []
    for job in sorted(alias_jobs):
        parent = jobs[job]["parent_job_ids"]
        assert len(parent) == 1
        wanted = owner_jobs[job]["build_parent_profile_sha256"]
        matches = [r for r in private if r["sha256"] == wanted and r["path"].endswith("/" + parent[0] + "/profile.json")]
        assert len(matches) == 1
        entry = matches[0]
        path = Path(entry["path"])
        if preservation is not None:
            matches = [r for r in preservation if r["kind"] == "external" and r["path"] == entry["path"] and r["sha256"] == wanted]
            assert len(matches) == 1
            member = PurePosixPath(matches[0]["archive_member"])
            assert not member.is_absolute() and ".." not in member.parts
            path = (args.archive_root / str(member)).resolve()
            assert path.is_relative_to(args.archive_root.resolve())
        raw = path.read_bytes()
        assert sha(raw) == wanted and len(raw) == entry["size_bytes"]
        profile = json.loads(raw)
        assert profile["profile_id"] == jobs[job]["profile_id"] == digest({k: v for k, v in profile.items() if k != "profile_id"})
        assert profile["config_id"] == digest(profile["config"]) and profile["content_sha256"] == digest(profile["content"])
        assert profile["personalization_cap"] == profile["config"]["personalization_cap"] == 2048
        accessed.append(entry)
        for cap in (512, 8192):
            variant = copy.deepcopy(profile)
            variant.pop("profile_id")
            variant["personalization_cap"] = variant["config"]["personalization_cap"] = cap
            variant["config_id"] = digest(variant["config"])
            variant_id = digest(variant)
            expected = {a["variant_profile_id"] for a in report["sparse_aliases"] if a["canonical_job_id"] == job and a["comparison_cap"] == cap}
            assert expected == {variant_id}
            rendered = "" if variant["content"] in (None, {}, [], "") else json.dumps(variant["content"], sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            assert variant["content"] == profile["content"] and len(rendered.encode()) == profile["token_count"] <= cap
            variants.append({"canonical_job_id": job, "cap": cap, "variant_profile_id": variant_id,
                             "rendered_profile_sha256": sha(rendered.encode()), "rendered_bytes": len(rendered.encode())})
    richer = json.loads((stage / "018-richer-control-alias-proposal.json").read_text())
    assert richer["registered_aliases"] is False and richer["accounting_changed"] is False
    assert richer["candidate_references"] == len(richer["records"]) == 168
    assert richer["status"] == "candidate_prepared_only_coordinator_adoption_pending"
    assert all(r["status"] == "candidate_equal_request_not_registered" for r in richer["records"])
    private_hashes = {r["sha256"] for r in private}
    assert not any(pin in private_hashes for pin in manifest["files"].values())
    result = {"schema_version": "independent-control-execution34-crosscheck-v1", "status": "passed",
        "script_sha256": sha(Path(__file__).read_bytes()), "reviewed_reader_sha256": report["reader_sha256"],
        "safe_manifest_files_verified": len(manifest["files"]), "source_files_matched_to_independent030": len(source["files"]),
        "recorded_original_reader_checks": 4572, "canonical_jobs": len(jobs), "canonical_rows": len(canonical),
        "distinct_ordered_items_matching_independent_phase1": len(by_item), "distinct_method_cap_conditions_per_item": len(conditions),
        "paired_content_groups_in_independent_phase1": len(phase1["content_groups"]),
        "canonical_cost_once": str(total), "sparse_references": len(seen), "sparse_canonical_rows": len(alias_cells),
        "sparse_canonical_jobs": len(alias_jobs), "sparse_cost_already_in_total": str(subset),
        "hybrid_lineages_matching_independent033_P1_parent_jobs": len(hybrid_jobs),
        "backend_settings_system_hashes_match_independent033": True, "independent_cap_variants": variants,
        "private_inputs_read": accessed, "richer_unregistered_proposals_excluded": len(richer["records"]),
        "model_calls": 0, "raw_text_exported": False,
        "limits": ["This is a bounded independent check, not a repeat of all4572 reader assertions or all private inputs.",
                   "Cap variants are reconstructed identities/references, not newly executed jobs.",
                   "Exact paired content is not independent human judgments; costs are recorded estimates, not invoices.",
                   "No actual wire capture, provider authentication, private labels, ledger or scores are checked."]}
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "crosscheck.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "jobs": len(jobs), "rows": len(canonical), "references": len(seen), "variant_ids": len(variants)}))


if __name__ == "__main__":
    main()
