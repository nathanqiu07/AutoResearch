#!/usr/bin/env python3
"""Bounded independent audit035 cross-check; standard library, metadata output.

Reads only exact inventory-named references. Does not import the owner reader or
runtime, load SQLite, invoke services, reconstruct prompts, or examine labels.
Optional --inputs changes read_path mappings only, with the same logical pins.
"""
import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import itertools
import json
from pathlib import Path
import tarfile

RUNTIME = "f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca"
READER_SHA = "a1673fc9e2a6be897ca13562a02250677bc819ed1bfa9f8f09b1344405bb36b0"
REPORT_SHA = "d1f9512120fefb9e014c09761ce682ed64406b10a0f8bf2c3a807e9122d37cd9"
INVENTORY_SHA = "401d8952d2a0ed81c98d06c2b7aa9ff9e7ca379ed52ce30170e000c6942ac70e"
OLD = "df4cbde2513374d37d42fc382fb38b5af057d5d0c6645dc36b3fb8d5f22e884a"
TARGET6 = "64894d812872c2af9c83852550a07d59700fa577a61c146d6276b8d02b68b89b"
P7 = "818518adfb6b0d9f277e1a33a577752f85386aae1acee48b75e8ff647f8e8970"
ORIGINS = {OLD: "original_stopped_dispatch", TARGET6: "target6_continuation", P7: "p7_continuation"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode())


def load(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def nanos(value):
    exact = Decimal(str(value)) * 1000000000
    require(exact == exact.to_integral_value(), "sub-nanodollar value needs explicit handling")
    return int(exact)


class Inputs:
    def __init__(self, original, mapped):
        self.pins = {r["path"]: r for r in original["files"]}
        self.mapped = {r["path"]: r for r in mapped["files"]}
        require(len(self.pins) == len(original["files"]) == len(self.mapped), "inventory duplicates")
        require({p: (r["sha256"], r["bytes"]) for p, r in self.pins.items()} ==
                {p: (r["sha256"], r["bytes"]) for p, r in self.mapped.items()}, "remapped inventory changed logical pins")
        require(digest({p: r["sha256"] for p, r in self.pins.items()}) == original["input_set_sha256"], "inventory set hash")
        self.used = {}

    def get(self, ref):
        r = self.pins[ref["path"]]
        require(r["sha256"] == ref["sha256"], "reference hash differs from inventory")
        require(Path(r["path"]).suffix == ".json", "only named JSON input allowed")
        actual = Path(self.mapped[r["path"]].get("read_path", r["path"]))
        raw = actual.read_bytes()
        require(sha(raw) == r["sha256"] and len(raw) == r["bytes"], "input byte mismatch")
        self.used[r["path"]] = (actual, raw)
        return load(raw)

    def finish(self):
        for actual, raw in self.used.values():
            require(actual.read_bytes() == raw, "input changed during bounded review")


def grid_check(rows, index, selection):
    dimensions = ("method", "cap", "evidence_policy", "researcher_id", "replicate_id")
    require(selection["methods"] == ["P%d" % i for i in range(1, 9)], "eight explicit methods")
    require(selection["profile_caps"] == [512, 2048, 8192], "three explicit caps")
    require(set(selection["evidence_policies"]) == {"explicit-only", "marked-inference"}, "two policies")
    require(set(selection["researchers"]) == {"chris_olah", "neel_nanda"}, "two researcher identifiers")
    require(selection["replicate_ids"] == [0], "one replicate")
    expected = set(itertools.product(selection["methods"], selection["profile_caps"], selection["evidence_policies"], selection["researchers"], [0]))
    tuples = [tuple(r[k] for k in dimensions) for r in rows]
    require(len(rows) == len(expected) == len(set(tuples)) == 96 and set(tuples) == expected, "exact unique 96-cell product")
    require(len({r["job_id"] for r in rows}) == len({r["cell_id"] for r in rows}) == 96, "unique job and cell IDs")
    released = {r["job_id"]: r for r in index["cells"]}
    require(set(released) == {r["job_id"] for r in rows} and len(index["cells"]) == 96, "released cell identity")
    for row in rows:
        cell = released[row["job_id"]]
        require(all(cell[k] == row[k] for k in dimensions + ("cell_id",)), "released cell dimensions")
        require(cell["dispatch_status"] == row["status"] and cell["result"]["sha256"] == row["result_sha256"], "released terminal status and result hash")
    require(Counter(r["origin"] for r in rows) == {ORIGINS[OLD]: 78, ORIGINS[TARGET6]: 6, ORIGINS[P7]: 12}, "78/6/12 origin partition")
    require(Counter(r["status"] for r in rows) == {"complete": 48, "invalid": 39, "empty": 7, "unavailable": 2}, "all four outcomes retained")
    require(all((r["method"] == "P7") == (r["origin"] == ORIGINS[P7]) for r in rows), "P7 origin separation")
    require(all(r["usage"]["attempted_calls"] == 1 for r in rows), "one recorded attempt per cell")
    unknown = [r for r in rows if r["usage"]["uncertain_attempts"]]
    require(len(unknown) == 2 and all(r["status"] == "unavailable" and r["origin"] == ORIGINS[OLD]
            and r["method"] == "P8" and r["cap"] == 2048 and r["evidence_policy"] == "explicit-only"
            and r["usage"]["input_tokens"] is None and r["usage"]["output_tokens"] is None for r in unknown), "two unknown P8 outcomes remain unknown")


def hold_check(rows, snapshot, authorization, policy):
    reservations = snapshot["reservation_rows"]
    require(len(reservations) == len({r[0] for r in reservations}) == 82, "82 unique stopped reservations")
    require(Counter(r[3] for r in reservations) == {"complete": 80, "uncertain": 2}, "stopped status partition")
    holds = [r for r in reservations if r[3] == "uncertain"]
    require(sorted(r[1] for r in holds) == [9314375, 9764250] and all(r[2] == 0 for r in holds), "unchanged uncertain hold amounts")
    retained = sum(r[1] for r in holds)
    require(retained == 19078625 == sum(r["usage"]["retained_hold_nanos"] for r in rows), "outcome-to-snapshot aggregate hold reconciliation")
    exact = [{"id": r[0], "reserved_nanos": r[1], "actual_known_nanos": r[2], "metadata": load(r[4])} for r in holds]
    require(exact == authorization["uncertain_reservations"], "exact reservation preservation in continuation authorization")
    require(authorization["predecessor_status"] == "stopped_with_uncertain_holds_not_closed" and policy["prior_phase_closure"]["status"] == "stopped_with_holds_not_closed", "old holds remain explicitly open")
    known = sum(r[2] for r in reservations)
    prior_limit = load(snapshot["policy_rows"][0][1])["limit_nanos"]
    require(prior_limit - known - retained == authorization["continuation_limit_nanos"] == nanos(policy["ledger"]["max_usd"]), "continuation allowance deducts known and held cost")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    require(not a.out.exists(), "output already exists")
    manifest_raw = (a.package / a.manifest).read_bytes()
    require(sha(manifest_raw) == a.manifest_sha256, "safe manifest pin")
    safe = load(manifest_raw)["files"]
    if isinstance(safe, list):
        safe = {r["path"]: r["sha256"] for r in safe}
    for name, pin in safe.items():
        require(sha((a.package / name).read_bytes()) == pin, "safe file hash")
    require(sha((a.package / "audit_coverage.py").read_bytes()) == READER_SHA, "frozen reader identity")
    report_raw = (a.package / "final/report.json").read_bytes()
    inventory_raw = (a.package / "final/input-inventory.json").read_bytes()
    require(sha(report_raw) == REPORT_SHA and sha(inventory_raw) == INVENTORY_SHA, "frozen evidence pins")
    report, inventory = load(report_raw), load(inventory_raw)
    inputs = Inputs(inventory, load(a.inputs.read_bytes()) if a.inputs else inventory)
    entry = inventory["entry_points"]
    index, retention, registry, rebind = (inputs.get(entry[k]) for k in ("index", "retention32", "registry", "target6_rebind"))
    selection = inputs.get(index["broad_selection"])
    source = next(r for r in retention["sources"] if r["commit"] == RUNTIME)
    require(sha((a.package / "source-f6cd4fb5.tar").read_bytes()) == source["sha256"], "frozen runtime archive hash")
    with tarfile.open(a.package / "source-f6cd4fb5.tar", "r:") as archive:
        members = {m.name: m for m in archive.getmembers() if m.isfile()}
        require(set(members) == set(source["files"]), "exact runtime source archive file set")
        for name, pin in source["files"].items():
            require(sha(archive.extractfile(members[name]).read()) == pin, "frozen runtime source hash")
    require(report["runtime_sha"] == index["runtime_sha"] == RUNTIME, "runtime identity")
    rows = report["cells"]
    grid_check(rows, index, selection)
    old = {r["job_id"]: r for r in retention["coverage"] if r["batch_id"] == OLD}
    original_ids = {r["job_id"] for r in rows if r["origin"] == ORIGINS[OLD]}
    target_ids = {r["job_id"] for r in rows if r["origin"] == ORIGINS[TARGET6]}
    p7_ids = {r["job_id"] for r in rows if r["origin"] == ORIGINS[P7]}
    require(set(old) == original_ids | target_ids and not set(old) & p7_ids, "84 original plus12 peer-method provenance")
    require({j for j, r in old.items() if r["original_dispatch_status"] == "not_dispatched"} == target_ids, "six continuations exactly original undispatched jobs")
    for row in rows:
        if row["job_id"] in original_ids:
            prior = old[row["job_id"]]
            require(prior["original_dispatch_status"] == row["status"] and prior["result_sha256"] == row["result_sha256"], "all78 original outcome hashes unchanged")
    index_by_id = {r["job_id"]: r for r in index["cells"]}
    uncertain = [r for r in rows if r["usage"]["uncertain_attempts"]]
    for row in uncertain:
        cell = index_by_id[row["job_id"]]
        result, dispatch = inputs.get(cell["result"]), inputs.get(cell["dispatch_receipt"])
        require(result["status"] == dispatch["status"] == "unavailable" and result["job_id"] == dispatch["job_id"] == row["job_id"], "unknown terminal result and dispatch identity")
        require(result["usage"] == dispatch["usage"] and result["usage"]["uncertain_attempts"] == 1, "unknown usage retained in both records")
        require(result["usage"]["input_tokens"] is None and result["usage"]["output_tokens"] is None, "unknown token counts not zero-filled")
        require(nanos(result["usage"]["reserved_api_usd"]) == row["usage"]["retained_hold_nanos"], "unknown saved hold amount")
    for jid in target_ids:
        refs = [r for r in old[jid]["required_records"] if "/execution/" in r["path"] and r["path"].endswith("/receipt.json")]
        require(len(refs) == 1, "one original non-dispatch receipt")
        receipt = inputs.get(refs[0])
        require(receipt["status"] == "not_dispatched" and receipt["result_path"] is None, "original six had no dispatched result")
    summaries = {}
    for batch in registry["batches"]:
        bid = batch["batch_id"]
        if bid not in ORIGINS:
            continue
        prepared, summary = inputs.get(batch["prepared"]), inputs.get(batch["execution_summary"])
        require(prepared["batch_id"] == summary["batch_id"] == bid, "batch identity")
        summaries[bid] = summary
        members = [r for r in rows if r["origin"] == ORIGINS[bid]]
        require(summary["counts"]["dispatched"] == len(members) and summary["counts"]["complete"] == sum(r["status"] == "complete" for r in members), "batch terminal counts")
        if bid != OLD:
            evidence, ids = inputs.get(prepared["rebind_evidence"]), inputs.get(prepared["explicit_job_ids"])
            ids = ids if isinstance(ids, list) else ids["job_ids"]
            expected_ids = target_ids if bid == TARGET6 else p7_ids
            require(evidence["job_ids"] == prepared["explicit_job_ids"], "exact continuation job-ID file reference")
            require(set(ids) == {m["job_id"] for m in evidence["mappings"]} == expected_ids, "exact continuation admission sets")
            require(len(ids) == len(expected_ids) and not set(ids) & original_ids, "no duplicate/rebound old dispatched jobs")
    snapshot, policy = inputs.get(rebind["stopped_ledger_receipt"]), inputs.get(rebind["new_ledger_policy"])
    authorization = inputs.get(policy["continuation_authorization"])
    hold_check(rows, snapshot, authorization, policy)
    side = {k: inputs.get(registry[k]) for k in ("phase2_access_probes", "phase2_embedding_production", "phase2_readiness_probe")}
    for name, summary in side.items():
        entries = summary.get("calls", summary.get("requests"))
        require(summary["attempted_calls"] == len(entries), "side-job attempt count")
        amount = sum(nanos(r["cost"]["spent_usd"] if "cost" in r else r["known_usage_usd"]) for r in entries)
        require(amount == nanos(summary["known_usage_usd"]), "side-job detail-to-summary cost")
        if name == "phase2_embedding_production":
            for request in entries:
                receipt = inputs.get({"path": request["receipt_path"], "sha256": request["receipt_sha256"]})
                require(all(receipt[k] == request[k] for k in ("request_id", "input_sha256", "packet_sha256", "response_sha256", "known_usage_usd", "usage", "status")), "embedding saved receipt metadata")
                matches = [r for r in snapshot["reservation_rows"] if all(load(r[4]).get(k) == request[k] for k in ("request_id", "input_sha256", "packet_sha256"))]
                require(len(matches) == 1 and matches[0][2] == nanos(request["known_usage_usd"]), "embedding request identity to stopped reservation")
    old_build = sum(r["usage"]["known_estimate_nanos"] for r in rows if r["origin"] == ORIGINS[OLD])
    old_known = sum(r[2] for r in snapshot["reservation_rows"])
    require(old_known - old_build == sum(nanos(side[k]["known_usage_usd"]) for k in ("phase2_access_probes", "phase2_embedding_production")) == 933440, "old cost residual exactly four side calls")
    require(len(snapshot["reservation_rows"]) - len(original_ids) == 4, "old attempt residual four")
    for bid, origins in ((OLD, {ORIGINS[OLD]}), (TARGET6, {ORIGINS[TARGET6]}), (P7, {ORIGINS[TARGET6], ORIGINS[P7]})):
        build = [r for r in rows if r["origin"] in origins]
        extras = [side["phase2_access_probes"], side["phase2_embedding_production"]] if bid == OLD else [side["phase2_readiness_probe"]]
        ledger = summaries[bid]["ledger"]
        require(ledger["attempts"] == len(build) + sum(s["attempted_calls"] for s in extras), "saved ledger scope includes side calls")
        require(nanos(ledger["spent_usd"]) == sum(r["usage"]["known_estimate_nanos"] for r in build) + sum(nanos(s["known_usage_usd"]) for s in extras), "saved ledger known-cost reconciliation")
        require(nanos(ledger["max_usd"]) - nanos(ledger["spent_usd"]) - nanos(ledger["reserved_usd"]) == nanos(ledger["remaining_usd"]), "saved capacity arithmetic")
    total_attempts = summaries[OLD]["ledger"]["attempts"] + summaries[P7]["ledger"]["attempts"]
    total_known = nanos(summaries[OLD]["ledger"]["spent_usd"]) + nanos(summaries[P7]["ledger"]["spent_usd"])
    require(total_attempts == 101 == 96 + sum(s["attempted_calls"] for s in side.values()), "deduplicated two-ledger scope has101 attempts")
    require(total_known == 103992940 == sum(r["usage"]["known_estimate_nanos"] for r in rows) + sum(nanos(s["known_usage_usd"]) for s in side.values()), "unique known cost excludes target6 cumulative double count")
    negatives = []
    for name, change in (
        ("duplicate_grid_cell", lambda r: r.__setitem__(1, deepcopy(r[0]))),
        ("mislabel_original_origin", lambda r: r[0].__setitem__("origin", "target6_continuation")),
        ("erase_unknown_token_status", lambda r: next(x for x in r if x["usage"]["uncertain_attempts"])["usage"].__setitem__("input_tokens", 0)),
    ):
        mutated = deepcopy(rows)
        change(mutated)
        try:
            grid_check(mutated, index, selection)
        except ValueError:
            negatives.append({"case": name, "rejected": True})
        else:
            raise ValueError("negative control was accepted")
    mutated = deepcopy(snapshot)
    mutated["reservation_rows"] = [r for r in mutated["reservation_rows"] if r[3] != "uncertain"]
    try:
        hold_check(rows, mutated, authorization, policy)
    except ValueError:
        negatives.append({"case": "remove_retained_uncertain_holds", "rejected": True})
    else:
        raise ValueError("removed holds accepted")
    inputs.finish()
    for name, pin in safe.items():
        require(sha((a.package / name).read_bytes()) == pin, "safe file changed after review")
    output = {"schema_version": "independent-phase2-coverage35-crosscheck-v1", "owner_reader_sha256": READER_SHA,
              "owner_report_sha256": REPORT_SHA, "owner_inventory_sha256": INVENTORY_SHA,
              "safe_manifest_sha256": a.manifest_sha256, "safe_files_verified": len(safe),
              "frozen_source_files_verified": len(source["files"]), "runtime_sha": RUNTIME,
              "full_owner_reader_rerun": False, "audit_model_calls": 0,
              "distinct_cells": 96, "origin_counts": dict(Counter(r["origin"] for r in rows)),
              "outcomes": dict(Counter(r["status"] for r in rows)), "unchanged_original_outcome_hashes": 78,
              "original_non_dispatch_receipts_verified": 6, "unknown_terminal_result_dispatch_pairs_verified": 2,
              "retained_uncertain_hold_nanos": 19078625,
              "old_side_residual_attempts": 4, "old_side_residual_known_nanos": 933440,
              "bounded_unique_attempts_including_side_jobs": total_attempts,
              "bounded_unique_known_nanos_including_side_jobs": total_known,
              "continuation_final_ledger_includes_target6_and_readiness": True,
              "unknown_provider_request_digest_reconstructed": False,
              "neutral_probe_provider_request_digest_reconstructed": False,
              "embedding_saved_receipt_to_snapshot_identity_matches": 2,
              "negative_controls": negatives,
              "named_inputs_read": [{"path": path, "sha256": inputs.pins[path]["sha256"], "bytes": inputs.pins[path]["bytes"], "roles": inputs.pins[path]["roles"]} for path in sorted(inputs.used)],
              "limits": ["Numerical reconciliation does not reconstruct uncertain build or neutral probe canonical request digests.",
                         "The two embedding request ID/input/packet hashes join saved receipts to snapshot metadata; actual provider request bytes and source content are not reconstructed.",
                         "The101-attempt and cost totals cover these two frozen ledger scopes only, not the active campaign or full budget.",
                         "No model call, labels, scoring, live ledger, source/profile quality assessment, or independent provider authentication."]}
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / "crosscheck.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verified": True, "cells": 96, "approved_inputs_read": len(inputs.used), "negative_controls_rejected": len(negatives), "audit_model_calls": 0}))


if __name__ == "__main__":
    main()
