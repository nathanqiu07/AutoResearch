#!/usr/bin/env python3
"""Prepare and execute one coordinator-leased PRISM development reference panel.

The benchmark, methods, and backend implementation remain unchanged. Raw records,
profiles and model outputs stay in an exclusive private directory outside Git.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoresearch.llm import Budget
from autoresearch.taste.backends import OpenAILLM
from autoresearch.taste.fidelity import run_fidelity, select_users
from autoresearch.taste.methods import create_method
from autoresearch.taste.methods.common import selected_history
from autoresearch.taste.methods.m4_bt import BradleyTerry
from autoresearch.taste.methods.m5_hybrid import Hybrid
from autoresearch.taste.methods.m6_verified import VerifiedHybrid
from autoresearch.taste.prefdata import (PreferenceRecord, build_manifest, load_records,
                                       normalize_row)
from autoresearch.taste.usermodel import Choice, UserModel, digest
from dataclasses import asdict

METHODS = ["m0", "m1", "m2", "m3"]
CONFIG = {"max_history": 5, "max_hypotheses": 2, "max_principles": 2,
          "max_exemplars": 1, "max_persona_chars": 1600, "k": 5}
LIMITS = {"max_usd": 5, "max_calls": 1500, "max_seconds": 3600}
DEADLINE = "2026-11-15T17:00:00Z"
DEV_ROW = re.compile(rb'"user_split"\s*:\s*"dev"')
SUCCESSOR_PROTOCOL = "newmethods-small-v1"
SUCCESSOR_METHODS = ["m4_full", "m4_matched5", "m5", "m6"]
SUCCESSOR_CALLS = {"prism:user666": 517, "prism:user380": 578}
APPROVED_PROPOSAL_SHA = "9d22bd02d5b70133144845274cc28e7980b880a7f76e971727d41423011e54f6"
FORBIDDEN_WIRE_HASH = "970b0250ee8dabc2697b1f9238e9af8fc6b97529d448c40db1cefd9cbc47df20"
M7_UNAVAILABLE = "One validation conversation group; zero calibration rows; no calibrated treatment."
HISTORY_POLICIES = {"m4_full": "all", "m4_matched5": "selected_five",
                    "m5": "selected_five", "m6": "selected_five"}
REMAINING_PROTOCOL = "remaining56-v1"
REMAINING_POLICY_SHA = "9baf4eded265ba814ca75fbe330ef07a006644fd98e4d234b203ea2fd8f16c65"
FIRST8_PROTOCOL = "original-first8-v1"
FIRST8_PROPOSAL_SHA = "d251373fe3da7e25ad44e590b2ff518d8ab72c193647d0181c0ab77f7c989d16"
FIRST8_USERS = ["prism:user949", "prism:user903", "prism:user347", "prism:user681",
                "prism:user557", "prism:user480", "prism:user634", "prism:user671"]
FIRST8_CAPS = {"prism:user949": (.08, 30), "prism:user903": (1.48, 260),
               "prism:user347": (.11, 50), "prism:user681": (.19, 88),
               "prism:user557": (.10, 46), "prism:user480": (.13, 58),
               "prism:user634": (.04, 21), "prism:user671": (.07, 35)}
RECOVERY903_PLAN_SHA = "712a64cd062ad2efa1c9e2aabd0bcbde7a1eb66c797a52cb9c7071e61c16cffd"
WITHHELD_634 = "04ef1fa1bb42ce73e50aa5f98c0554930934b54685a16401887dcd3f2633b9b8"


def file_sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def runtime_identity():
    files = [Path(__file__).resolve()] + sorted((ROOT / "autoresearch").rglob("*.py"))
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                               text=True).strip(),
            "python": list(sys.version_info[:3]),
            "files": {str(p.relative_to(ROOT)): file_sha(p) for p in files}}


def write_private(path, value):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def copy_private(source, target):
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(Path(source).read_bytes())


def verify_cache(directory, hashes):
    directory = Path(directory)
    if (not isinstance(hashes, dict) or not hashes or
            any(not re.fullmatch(r"[a-f0-9]{64}\.json", name) for name in hashes) or
            {p.name for p in directory.iterdir()} != set(hashes)):
        raise ValueError("cache import set differs")
    for name, expected in hashes.items():
        if file_sha(directory / name) != expected:
            raise ValueError("cache import hash differs")


def successor_limits(user_ids):
    if len(user_ids) != 1 or user_ids[0] not in SUCCESSOR_CALLS:
        raise ValueError("successor requires one preselected user")
    return {"max_usd": 1., "max_calls": SUCCESSOR_CALLS[user_ids[0]], "max_seconds": 1800}


def prepare_successor(proposal_path, user_id, destination):
    """Copy only the approved user's frozen inputs and successful imported cache."""
    proposal_path, destination = Path(proposal_path), Path(destination)
    if file_sha(proposal_path) != APPROVED_PROPOSAL_SHA:
        raise ValueError("proposal is not the authorized frozen proposal")
    limits = successor_limits([user_id])
    if destination.exists():
        raise FileExistsError("private snapshot already exists")
    if ROOT == destination.resolve() or ROOT in destination.resolve().parents:
        raise ValueError("private snapshot must be outside the repository")
    proposal = json.loads(proposal_path.read_text())
    panel = next(x for x in proposal["panels"] if x["user_id"] == user_id)
    prior_path = Path(panel["existing_m0_m3_plan_path"])
    if file_sha(prior_path) != panel["existing_m0_m3_plan_sha256"]:
        raise ValueError("prior plan hash differs")
    prior = json.loads(prior_path.read_text())
    source = prior_path.parent
    if (prior["user_ids"] != [user_id] or prior["methods"] != METHODS or
            prior["method_config"] != CONFIG or prior["final"] is not False):
        raise ValueError("prior plan is not the approved development baseline")
    for name, expected in prior["snapshots"].items():
        if name not in ("records.jsonl", "manifest.json") or file_sha(source / name) != expected:
            raise ValueError("prior snapshot hash differs")
    records = load_records(source / "records.jsonl")
    manifest = json.loads((source / "manifest.json").read_text())
    if (any(r.user_split != "dev" for r in records) or build_manifest(records, 0) != manifest or
            set(manifest["users"]) != {user_id}):
        raise ValueError("prior snapshot is not the approved development user")
    report_path, completion_path = source / "output" / "report.json", source / "completion.json"
    if (file_sha(report_path) != panel["existing_report_sha256"] or
            file_sha(completion_path) != panel["existing_completion_sha256"]):
        raise ValueError("prior terminal receipt differs")
    completion = json.loads(completion_path.read_text())
    if (completion["report_sha256"] != file_sha(report_path) or
            completion["failures"] != dict.fromkeys(METHODS, 0) or
            any(b["reserved_usd"] != 0 for b in completion["budgets"])):
        raise ValueError("prior baseline has failed or uncertain requests")
    imported = Path(panel["immutable_imported_cache_path"])
    cache_manifest = imported.parent / "cache-import-manifest.json"
    if file_sha(cache_manifest) != panel["cache_import_manifest_sha256"]:
        raise ValueError("cache manifest hash differs")
    hashes = json.loads(cache_manifest.read_text())
    verify_cache(imported, hashes)
    destination.mkdir(parents=True, mode=0o700)
    os.chmod(destination, 0o700)
    for name in ("records.jsonl", "manifest.json"):
        copy_private(source / name, destination / name)
    copy_private(proposal_path, destination / "approved-proposal.json")
    copy_private(prior_path, destination / "prior-plan.json")
    copy_private(cache_manifest, destination / "initial-cache-manifest.json")
    (destination / "cache").mkdir(mode=0o700)
    for name in hashes:
        copy_private(imported / name, destination / "cache" / name)
    plan = dict(prior, protocol=SUCCESSOR_PROTOCOL, methods=SUCCESSOR_METHODS,
                limits=limits, runtime=runtime_identity(), proposal_sha256=APPROVED_PROPOSAL_SHA,
                prior_plan_sha256=file_sha(prior_path), prior_report_sha256=file_sha(report_path),
                initial_cache=hashes, cache_import_manifest_sha256=file_sha(cache_manifest),
                forbidden_wire_hashes=[FORBIDDEN_WIRE_HASH],
                unavailable_methods={"m7": M7_UNAVAILABLE},
                history_policies=HISTORY_POLICIES,
                snapshots={name: file_sha(destination / name) for name in
                           ("records.jsonl", "manifest.json", "approved-proposal.json",
                            "prior-plan.json", "initial-cache-manifest.json")},
                worst_case_backend_calls=limits["max_calls"],
                interpretation="Two-user new-method feasibility phase; imported responses are reused evidence.")
    write_private(destination / "plan.json", plan)
    return destination / "plan.json"


def read_ref(ref):
    path = Path(ref["path"])
    if file_sha(path) != ref["sha256"]:
        raise ValueError("source reference hash differs")
    return json.loads(path.read_text())


def first8_limits(user, recovery=False):
    if user not in FIRST8_CAPS:
        raise ValueError("user is outside the frozen original eight")
    usd, calls = FIRST8_CAPS[user]
    if user == "prism:user903" and not recovery:
        usd, calls = .08, 39
    return {"max_usd": usd, "max_calls": calls, "max_seconds": 1800}


def first8_unavailable(user, recovery=False):
    result = {"m7": M7_UNAVAILABLE}
    reason = {"prism:user949": "historical uncertain component request withheld",
              "prism:user634": "historical invalid-JSON component request withheld"}.get(user)
    if user == "prism:user903" and not recovery:
        reason = "known recovery and entirely cached component fits unavailable"
    if reason:
        result.update(m5=reason, m6=reason)
    return result


def cache_hashes(directory):
    values = {p.name: file_sha(p) for p in Path(directory).iterdir() if p.is_file()}
    verify_cache(directory, values)
    return values


def replay_cached_components(records, manifest, cache):
    user, = manifest["users"]
    by_id = {r.choice.identity: r.choice for r in records}
    history, val = ([by_id[i] for i in manifest["users"][user][s]] for s in ("history", "val"))
    backend = ReferenceBackend("gpt-6-luna", budget=Budget(max_calls=2000, max_seconds=60), max_usd=2)
    model = CacheOnlyHybrid(backend, seed=0, cache_dir=cache, max_calls=2000, **CONFIG)
    model.fit(history, val)
    if backend.budget.calls or backend.request_audit or getattr(backend.budget, "_taste_attempts", 0):
        raise ValueError("component replay was not entirely cached")
    return {"cache_hits": model.cost["cache_hits"], "api_calls": 0,
            "artifacts_sha256": digest(asdict(model.artifacts()))}


def first8_source(proposal):
    if proposal["user_ids"] != FIRST8_USERS or proposal["methods"] != SUCCESSOR_METHODS:
        raise ValueError("original-eight proposal scope differs")
    refs = proposal["evidence"]
    source_plan = read_ref(refs["original_plan"])
    source = Path(refs["original_plan"]["path"]).parent
    report = read_ref(refs["original_report"])
    completion = read_ref(refs["original_completion"])
    if (source_plan["user_ids"] != FIRST8_USERS or source_plan["methods"] != METHODS or
            source_plan["method_config"] != CONFIG or source_plan["final"] is not False or
            source_plan["user_partition"] != "dev" or
            set(report["user_ids"]) != set(FIRST8_USERS) or
            completion["report_sha256"] != refs["original_report"]["sha256"]):
        raise ValueError("original baseline identity differs")
    for name, expected in source_plan["snapshots"].items():
        if file_sha(source / name) != expected:
            raise ValueError("original snapshot differs")
    records = load_records(source / "records.jsonl")
    manifest = json.loads((source / "manifest.json").read_text())
    if any(r.user_split != "dev" for r in records) or build_manifest(records, 0) != manifest:
        raise ValueError("original source is not the frozen development snapshot")
    hashes = cache_hashes(source / "cache")
    if (len(hashes) != proposal["cache_lineage"]["original_source_entries"] or
            digest(hashes) != proposal["cache_lineage"]["original_source_map_sha256"]):
        raise ValueError("original cache differs from the approved proposal")
    return source, source_plan, records, hashes


def recovery903_contract(evidence, values, records):
    if evidence["plan"]["sha256"] != RECOVERY903_PLAN_SHA:
        raise ValueError("recovery plan is not the already leased original903 completion")
    prior, terminal, diagnostic = (values[k] for k in ("plan", "terminal", "diagnostics_verified"))
    completion = values["completion"]
    if (prior["user_ids"] != ["prism:user903"] or prior["methods"] != METHODS or
            prior["method_config"] != CONFIG or prior["user_partition"] != "dev" or
            prior["final"] is not False or terminal["job_id"] != "gio-reference-unattempted-user903-tranche-01" or
            completion["job_id"] != terminal["job_id"] or terminal["outcome"] != "terminal_known_usage" or
            terminal["returncode"] != 0 or terminal["reported_hold_usd"] != 0 or
            any(b["reserved_usd"] != 0 for b in completion["budgets"]) or
            diagnostic["observed_terminal_valid"] is not True or diagnostic["actual_wrapper_returncode"] != 0):
        raise ValueError("recovery terminal is not known, unheld and diagnostically complete")
    if sorted(values["records"], key=lambda r: r.choice.identity) != sorted(records, key=lambda r: r.choice.identity):
        raise ValueError("recovery records differ from original903 source subset")
    if completion["report_sha256"] != terminal["report_sha256"]:
        raise ValueError("recovery report binding differs")


def recovery903_diagnostics(evidence, values, events_path):
    claim, terminal, diagnostic = (values[k] for k in ("envelope_claim", "envelope_terminal", "diagnostics_verified"))
    envelope = claim["envelope"]
    identity = hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if (envelope["inputs"]["plan"] != evidence["plan"] or envelope["kind"] != "reference" or
            envelope["runtime_commit"] != values["plan"]["runtime"]["commit"] or
            claim["canonical_envelope_sha256"] != identity or
            terminal["canonical_envelope_sha256"] != identity or diagnostic["canonical_envelope_sha256"] != identity or
            diagnostic["terminal_sha256"] != evidence["envelope_terminal"]["sha256"] or
            terminal["scientific_runtime_commit"] != envelope["runtime_commit"] or
            terminal["status"] != "complete" or terminal["entry_exit_code"] != 0 or terminal["wrapper_exit_code"] != 0 or
            terminal["events_sha256"] != evidence["events"]["sha256"] or diagnostic["events_sha256"] != terminal["events_sha256"] or
            file_sha(events_path) != terminal["events_sha256"]):
        raise ValueError("recovery diagnostic envelope is not bound to the exact terminal run")
    diagnostics = terminal["diagnostics"]
    if (diagnostics["diagnostic_write_failed"] is not False or diagnostics["dropped_event_count"] != 0 or
            diagnostics["diagnostic_close_failed"] is not False or diagnostics.get("diagnostic_hash_failed", False) is not False):
        raise ValueError("recovery diagnostic failure")
    rows = [json.loads(line) for line in Path(events_path).read_text().splitlines()]
    if (len(rows) != terminal["event_count"] or diagnostic["event_count"] != len(rows) or
            [r["sequence"] for r in rows] != list(range(len(rows))) or
            any(r["stage"] == "denied_before_transport" for r in rows)):
        raise ValueError("recovery diagnostic events are incomplete or denied")
    wires = {r["endpoint_body_sha256"] for r in rows}
    if any(not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key) for key in wires):
        raise ValueError("recovery event lacks exact request identity")
    return sorted(wires)


def recovery903_source(path, records):
    evidence = json.loads(Path(path).read_text())
    values = {k: read_ref(evidence[k]) for k in ("plan", "terminal", "diagnostics_verified")}
    source = Path(evidence["plan"]["path"]).parent
    values["completion"] = json.loads((source / "completion.json").read_text())
    values["records"] = load_records(source / "records.jsonl")
    recovery903_contract(evidence, values, records)
    values.update({k: read_ref(evidence[k]) for k in ("envelope_claim", "envelope_terminal", "cache_manifest")})
    consumed = recovery903_diagnostics(evidence, values, evidence["events"]["path"])
    for name, expected in values["plan"]["snapshots"].items():
        if file_sha(source / name) != expected:
            raise ValueError("recovery inputs changed")
    if (file_sha(source / "completion.json") != values["terminal"]["completion_sha256"] or
            file_sha(source / "output" / "report.json") != values["terminal"]["report_sha256"]):
        raise ValueError("recovery terminal content changed")
    verify_cache(source / "cache", values["cache_manifest"])
    return source, evidence, values["cache_manifest"], consumed


def merge_cache_maps(original, recovery):
    if any(name in original and original[name] != expected for name, expected in recovery.items()):
        raise ValueError("recovery cache conflicts with original known cache")
    return dict(original, **recovery)


def prepare_first8(proposal_path, user_id, destination, recovery_terminal=None):
    proposal_path, destination = Path(proposal_path), Path(destination)
    if file_sha(proposal_path) != FIRST8_PROPOSAL_SHA:
        raise ValueError("proposal is not the approved original-eight followup")
    if destination.exists():
        raise FileExistsError("private snapshot already exists")
    if ROOT == destination.resolve() or ROOT in destination.resolve().parents:
        raise ValueError("private snapshot must be outside the repository")
    proposal = json.loads(proposal_path.read_text())
    source, prior, all_records, hashes = first8_source(proposal)
    recovered = recovery_terminal is not None
    if recovered and user_id != "prism:user903":
        raise ValueError("only original903 permits recovery admission")
    limits = first8_limits(user_id, recovered)
    records = [r for r in all_records if r.choice.user_id == user_id]
    manifest = build_manifest(records, 0)
    if set(manifest["users"]) != {user_id}:
        raise ValueError("selected user is absent from original development inputs")
    original_hashes = dict(hashes)
    recovery_source = evidence = recovery_hashes = None
    recovery_consumed = []
    if recovered:
        recovery_source, evidence, recovery_hashes, recovery_consumed = recovery903_source(recovery_terminal, records)
        hashes = merge_cache_maps(hashes, recovery_hashes)
    unavailable = first8_unavailable(user_id, recovered)
    # Replay from immutable copies; never write into an existing run's cache.
    replay = None
    if "m5" not in unavailable:
        with tempfile.TemporaryDirectory(prefix="reference-fit-replay-") as tmp:
            for name in hashes:
                origin = recovery_source if recovery_hashes and name in recovery_hashes else source
                copy_private(origin / "cache" / name, Path(tmp) / name)
            replay = replay_cached_components(records, manifest, Path(tmp))
            verify_cache(tmp, hashes)
    denied_ref = proposal["unknown_and_failure_exclusions"]["typed_denylist"]
    denied = read_ref(denied_ref)
    if denied["schema_version"] != "provider-unknown-wire-denylist-v2":
        raise ValueError("typed historical request identities required")
    destination.mkdir(parents=True, mode=0o700)
    os.chmod(destination, 0o700)
    for name in ("records.jsonl", "manifest.json", "plan.json"):
        copy_private(source / name, destination / ("source-" + name))
    for name in ("report", "completion"):
        copy_private(proposal["evidence"]["original_" + name]["path"], destination / ("source-" + name + ".json"))
    copy_private(proposal_path, destination / "approved-proposal.json")
    copy_private(denied_ref["path"], destination / "typed-denylist.json")
    write_private(destination / "initial-cache-manifest.json", hashes)
    if recovered:
        copy_private(recovery_terminal, destination / "recovery-evidence.json")
        for name in ("plan", "terminal", "diagnostics_verified", "envelope_claim", "envelope_terminal", "cache_manifest"):
            copy_private(evidence[name]["path"], destination / ("recovery-" + name + ".json"))
        copy_private(evidence["events"]["path"], destination / "recovery-events.jsonl")
        for name in ("completion.json", "records.jsonl", "manifest.json"):
            copy_private(recovery_source / name, destination / ("recovery-" + name))
        copy_private(recovery_source / "output" / "report.json", destination / "recovery-report.json")
    write_private(destination / "cache-lineage.json", {"original": original_hashes, "recovery": recovery_hashes})
    fd = os.open(str(destination / "records.jsonl"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        for record in records:
            stream.write(json.dumps(asdict(record), ensure_ascii=False, allow_nan=False) + "\n")
    write_private(destination / "manifest.json", manifest)
    (destination / "cache").mkdir(mode=0o700)
    for name in hashes:
        origin = recovery_source if recovery_hashes and name in recovery_hashes else source
        copy_private(origin / "cache" / name, destination / "cache" / name)
    verify_cache(destination / "cache", hashes)
    counts = [{"user_id": user_id, **{s: len(manifest["users"][user_id][s]) for s in ("history", "val", "test")}}]
    plan = dict(prior, protocol=FIRST8_PROTOCOL, methods=SUCCESSOR_METHODS, user_ids=[user_id],
                counts=counts, n_records=len(records), n_predictions=4 * counts[0]["test"],
                derived_manifest_id=manifest["manifest_id"], limits=limits, runtime=runtime_identity(),
                proposal_sha256=FIRST8_PROPOSAL_SHA, initial_cache=hashes, recovery903_enabled=recovered,
                history_policies=HISTORY_POLICIES, unavailable_methods=unavailable,
                component_fit_policy="cache_only", cached_component_replay=replay,
                identity_denylists=denied["identity_denylists"],
                forbidden_wire_hashes=sorted(set(denied["identity_denylists"]["endpoint_body_sorted_json_sha256"]) | {WITHHELD_634} | set(recovery_consumed)),
                worst_case_backend_calls=limits["max_calls"],
                snapshots={p.name: file_sha(p) for p in destination.iterdir() if p.is_file()},
                interpretation="Fixed original-eight method followup; unavailable cells remain planned; imported fits are reused evidence.")
    write_private(destination / "plan.json", plan)
    return destination / "plan.json"


def remaining_row(policy, cohort, user):
    if (policy["methods"] != SUCCESSOR_METHODS or policy["method_config"] != CONFIG or
            [(r["user_id"], r["canonical_position_1based"]) for r in policy["rows"]] !=
            [(r["user_id"], r["canonical_position_1based"]) for r in cohort["rows"]]):
        raise ValueError("remaining cohort or method contract differs")
    rows = [r for r in policy["rows"] if r["user_id"] == user]
    if len(rows) != 1:
        raise ValueError("user is outside the frozen remaining cohort")
    row, = rows
    if row["state"] == "completed_alias":
        raise ValueError("completed cells are aliases; new dispatch is forbidden")
    if row["state"] != "frozen_new_work":
        raise ValueError("unexpected remaining cohort state")
    return row


def load_remaining_policy(path, user):
    if file_sha(path) != REMAINING_POLICY_SHA:
        raise ValueError("remaining policy is not the frozen policy")
    policy = json.loads(Path(path).read_text())
    return policy, remaining_row(policy, read_ref(policy["cohort"]), user)


def prepare_remaining(policy_path, user_id, destination):
    policy_path, destination = Path(policy_path), Path(destination)
    policy, row = load_remaining_policy(policy_path, user_id)
    if destination.exists():
        raise FileExistsError("private snapshot already exists")
    if ROOT == destination.resolve() or ROOT in destination.resolve().parents:
        raise ValueError("private snapshot must be outside the repository")
    prior = read_ref(row["baseline_plan"])
    source = Path(row["baseline_plan"]["path"]).parent
    report, completion, terminal = (read_ref(row["baseline_" + name]) for name in ("report", "completion", "terminal"))
    if (prior["user_ids"] != [user_id] or prior["methods"] != METHODS or prior["method_config"] != CONFIG or
            prior["user_partition"] != "dev" or prior["final"] is not False or prior["seed"] != 0 or
            completion["report_sha256"] != row["baseline_report"]["sha256"] or
            terminal["completion_sha256"] != row["baseline_completion"]["sha256"] or
            terminal["report_sha256"] != row["baseline_report"]["sha256"]):
        raise ValueError("remaining baseline lineage differs")
    for name, expected in prior["snapshots"].items():
        if name not in ("records.jsonl", "manifest.json") or file_sha(source / name) != expected:
            raise ValueError("remaining baseline input differs")
    for name, expected in prior["runtime"]["files"].items():
        if name.startswith("autoresearch/") and file_sha(ROOT / name) != expected:
            raise ValueError("scientific method implementation differs from baseline")
    records = load_records(source / "records.jsonl")
    manifest = json.loads((source / "manifest.json").read_text())
    if (any(r.user_split != "dev" for r in records) or build_manifest(records, 0) != manifest or
            set(manifest["users"]) != {user_id} or 4 * len(manifest["users"][user_id]["test"]) != row["planned_cells"]):
        raise ValueError("remaining source is not the exact development user")
    verify_cache(source / "cache", row["baseline_cache"])
    replay = None
    if "m5" not in row["unavailable_methods"]:
        with tempfile.TemporaryDirectory(prefix="remaining-fit-replay-") as tmp:
            for name in row["baseline_cache"]:
                copy_private(source / "cache" / name, Path(tmp) / name)
            replay = replay_cached_components(records, manifest, tmp)
            verify_cache(tmp, row["baseline_cache"])
    if replay != row["cached_component_replay"]:
        raise ValueError("remaining cache-only fit proof differs")
    denied = read_ref(policy["typed_denylist"])
    destination.mkdir(parents=True, mode=0o700)
    os.chmod(destination, 0o700)
    for name in ("records.jsonl", "manifest.json"):
        copy_private(source / name, destination / name)
    for name in ("plan", "report", "completion", "terminal"):
        copy_private(row["baseline_" + name]["path"], destination / ("prior-" + name + ".json"))
    copy_private(policy_path, destination / "approved-policy.json")
    copy_private(policy["cohort"]["path"], destination / "approved-cohort.json")
    copy_private(policy["typed_denylist"]["path"], destination / "typed-denylist.json")
    write_private(destination / "initial-cache-manifest.json", row["baseline_cache"])
    (destination / "cache").mkdir(mode=0o700)
    for name in row["baseline_cache"]:
        copy_private(source / "cache" / name, destination / "cache" / name)
    verify_cache(destination / "cache", row["baseline_cache"])
    plan = dict(prior, protocol=REMAINING_PROTOCOL, methods=SUCCESSOR_METHODS,
                limits=row["limits"], runtime=runtime_identity(), policy_sha256=REMAINING_POLICY_SHA,
                initial_cache=row["baseline_cache"], unavailable_methods=row["unavailable_methods"],
                history_policies=HISTORY_POLICIES, component_fit_policy="cache_only", cached_component_replay=replay,
                identity_denylists=denied["identity_denylists"],
                forbidden_wire_hashes=sorted(set(denied["identity_denylists"]["endpoint_body_sorted_json_sha256"]) |
                                             set(policy["additional_consumed_or_withheld_endpoint_hashes"])),
                worst_case_backend_calls=row["limits"]["max_calls"], source_hold_usd=row["source_hold_usd"],
                snapshots={p.name: file_sha(p) for p in destination.iterdir() if p.is_file()},
                interpretation="Fixed remaining cohort; completed cells are separate aliases; unavailable cells remain planned.")
    write_private(destination / "plan.json", plan)
    return destination / "plan.json"


def validate_remaining(plan_path, plan, records, manifest):
    folder = plan_path.parent
    if plan["snapshots"]["approved-policy.json"] != REMAINING_POLICY_SHA:
        raise ValueError("remaining frozen policy differs")
    policy = json.loads((folder / "approved-policy.json").read_text())
    cohort = json.loads((folder / "approved-cohort.json").read_text())
    user, = plan["user_ids"]
    row = remaining_row(policy, cohort, user)
    if (plan["snapshots"]["approved-cohort.json"] != policy["cohort"]["sha256"] or
            plan.get("policy_sha256") != REMAINING_POLICY_SHA or plan.get("history_policies") != HISTORY_POLICIES or
            plan.get("unavailable_methods") != row["unavailable_methods"] or plan.get("component_fit_policy") != "cache_only" or
            plan.get("cached_component_replay") != row["cached_component_replay"]):
        raise ValueError("remaining safety contract or unavailable methods differ")
    for name in ("plan", "report", "completion", "terminal"):
        if plan["snapshots"]["prior-" + name + ".json"] != row["baseline_" + name]["sha256"]:
            raise ValueError("remaining prior source lineage differs")
    prior = json.loads((folder / "prior-plan.json").read_text())
    if any(plan["snapshots"][name] != prior["snapshots"][name] for name in ("records.jsonl", "manifest.json")):
        raise ValueError("remaining inputs differ from frozen baseline")
    for key in ("source_sha256", "parent_manifest_sha256", "parent_manifest_id", "counts", "n_records", "n_predictions"):
        if plan[key] != prior[key]:
            raise ValueError("remaining canonical lineage or denominator differs")
    if plan["n_predictions"] != row["planned_cells"] or plan["n_predictions"] != 4 * len(manifest["users"][user]["test"]):
        raise ValueError("remaining planned denominator differs")
    hashes = json.loads((folder / "initial-cache-manifest.json").read_text())
    if hashes != row["baseline_cache"] or hashes != plan["initial_cache"]:
        raise ValueError("remaining imported cache differs from frozen policy")
    verify_cache(folder / "cache", hashes)
    denied = json.loads((folder / "typed-denylist.json").read_text())
    if (plan["snapshots"]["typed-denylist.json"] != policy["typed_denylist"]["sha256"] or
            plan["identity_denylists"] != denied["identity_denylists"] or
            plan["forbidden_wire_hashes"] != sorted(set(denied["identity_denylists"]["endpoint_body_sorted_json_sha256"]) |
                                                   set(policy["additional_consumed_or_withheld_endpoint_hashes"]))):
        raise ValueError("remaining historical request exclusions differ")
    completion = json.loads((folder / "prior-completion.json").read_text())
    if plan["source_hold_usd"] != row["source_hold_usd"] or sum(b["reserved_usd"] for b in completion["budgets"]) != row["source_hold_usd"]:
        raise ValueError("remaining source holds changed")
    replay = None if "m5" in row["unavailable_methods"] else replay_cached_components(records, manifest, folder / "cache")
    if replay != row["cached_component_replay"]:
        raise ValueError("remaining cache-only fit replay differs")


def replay_normalization(record, seed):
    c = record.choice
    row = {"user_id": c.user_id.split(":", 1)[1],
           "conversation_id": c.group_id.split(":", 2)[2],
           "context": json.loads(c.context),
           "chosen": {"content": c.a_text if c.chosen == "a" else c.b_text},
           "rejected": {"content": c.b_text if c.chosen == "a" else c.a_text},
           "split": {"history": "train", "val": "val", "test": "test"}[record.choice_split]}
    if normalize_row(row, "prism", record.upstream_split, seed) != record:
        raise ValueError("selected record normalization does not replay exactly")


def prepare(source, canonical_manifest, destination, n_users=8):
    source, canonical_manifest, destination = map(Path, (source, canonical_manifest, destination))
    if destination.exists():
        raise FileExistsError("private snapshot already exists")
    if ROOT == destination.resolve() or ROOT in destination.resolve().parents:
        raise ValueError("private snapshot must be outside the repository")
    manifest_bytes = canonical_manifest.read_bytes()
    canonical = json.loads(manifest_bytes)
    if canonical["seed"] != 0:
        raise ValueError("reference panel requires canonical seed zero")
    selected = select_users(canonical, "prism", "dev", n_users, seed=0)
    if len(selected) != n_users:
        raise ValueError("not enough development users")
    selected_set, records, source_hash = set(selected), [], hashlib.sha256()
    with source.open("rb") as stream:
        for line in stream:
            source_hash.update(line)
            # Released normalized JSONL has this top-level field. Skip all final
            # rows before JSON parsing; no final label enters this process's objects.
            if not DEV_ROW.search(line):
                continue
            row = json.loads(line)
            if row.get("user_split") != "dev":
                raise ValueError("development prefilter mismatch")
            if row["choice"]["user_id"] not in selected_set:
                continue
            row["choice"] = Choice(**row["choice"])
            record = PreferenceRecord(**row)
            replay_normalization(record, canonical["seed"])
            records.append(record)
    derived = build_manifest(records, canonical["seed"])
    if set(derived["users"]) != selected_set or any(
            derived["users"][u] != canonical["users"][u] for u in selected):
        raise ValueError("selected source records differ from canonical splits")
    records.sort(key=lambda r: (selected.index(r.choice.user_id), r.choice.identity))
    destination.mkdir(parents=True, mode=0o700)
    os.chmod(destination, 0o700)
    records_path = destination / "records.jsonl"
    fd = os.open(str(records_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        for record in records:
            stream.write(json.dumps(asdict(record), ensure_ascii=False, allow_nan=False) + "\n")
    write_private(destination / "manifest.json", derived)
    counts = [{"user_id": u, **{s: len(canonical["users"][u][s]) for s in ("history", "val", "test")}}
              for u in selected]
    # Conservative upper bound for the fixed bounded adaptations: five hypotheses,
    # two forward-selection rounds, optional persona+validation, one exemplar round;
    # ICAI proposes at most ten clusters and scores each on five history choices.
    calls = sum(4 * row["test"] + min(5, row["history"]) + 1 +
                (2 + min(5, row["history"]) + max(0, min(5, row["history"]) - 1) +
                 3 + min(5, row["history"])) * row["val"] +
                min(5, row["history"]) + 2 * min(5, row["history"]) ** 2
                for row in counts)
    plan = {"schema_version": 1, "campaign_id": "gio-profile-20261115", "role": "10",
            "dataset": "prism", "user_partition": "dev", "final": False, "seed": 0,
            "user_ids": selected, "counts": counts, "n_records": len(records),
            "n_predictions": 4 * sum(row["test"] for row in counts),
            "worst_case_backend_calls": calls, "methods": METHODS, "method_config": CONFIG,
            "backend": "openai", "model": "gpt-6-luna", "reasoning": "none",
            "tools": False, "output_tokens": 2048, "limits": LIMITS, "deadline": DEADLINE,
            "source_sha256": source_hash.hexdigest(),
            "parent_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "parent_manifest_id": canonical["manifest_id"],
            "derived_manifest_id": derived["manifest_id"],
            "snapshots": {p.name: file_sha(p) for p in (records_path, destination / "manifest.json")},
            "runtime": runtime_identity(),
            "interpretation": "Exploratory recorded-preference reference, not research taste or paper reproduction.",
            "failure_policy": "Preserve all failures; stop network requests after uncertain API outcome; no retry.",
            "metrics": ["user-macro accuracy", "paired user differences versus m1",
                        "valid-only Brier with failure counts", "aggregate fit-and-predict usage", "empty artifacts"]}
    write_private(destination / "plan.json", plan)
    return destination / "plan.json"


def timestamp(value):
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("deadline requires timezone")
    return parsed.timestamp()


def validate_first8(plan_path, plan, records, manifest):
    """Bind a successor packet to approved source bytes, not merely its lease."""
    folder = plan_path.parent
    if plan["snapshots"]["approved-proposal.json"] != FIRST8_PROPOSAL_SHA:
        raise ValueError("approved original-eight proposal differs")
    proposal = json.loads((folder / "approved-proposal.json").read_text())
    user, = plan["user_ids"]
    recovery = plan.get("recovery903_enabled")
    if type(recovery) is not bool or recovery and user != "prism:user903":
        raise ValueError("invalid recovery admission")
    if (plan.get("proposal_sha256") != FIRST8_PROPOSAL_SHA or
            proposal["user_ids"] != FIRST8_USERS or proposal["methods"] != SUCCESSOR_METHODS or
            plan.get("unavailable_methods") != first8_unavailable(user, recovery) or
            plan.get("history_policies") != HISTORY_POLICIES or
            plan.get("component_fit_policy") != "cache_only"):
        raise ValueError("original-eight safety contract or unavailable methods differ")
    for name in ("plan", "report", "completion"):
        if plan["snapshots"]["source-" + name + ".json"] != proposal["evidence"]["original_" + name]["sha256"]:
            raise ValueError("original source lineage differs")
    prior = json.loads((folder / "source-plan.json").read_text())
    if any(plan["snapshots"]["source-" + name] != prior["snapshots"][name]
           for name in ("records.jsonl", "manifest.json")):
        raise ValueError("original source inputs differ")
    source_records = load_records(folder / "source-records.jsonl")
    if records != [r for r in source_records if r.choice.user_id == user]:
        raise ValueError("selected records differ from exact original source subset")
    for key in ("source_sha256", "parent_manifest_sha256", "parent_manifest_id"):
        if plan[key] != prior[key]:
            raise ValueError("canonical source lineage differs")
    counts = [{"user_id": user, **{s: len(manifest["users"][user][s]) for s in ("history", "val", "test")}}]
    if (plan["counts"] != counts or plan["n_records"] != len(records) or
            plan["n_predictions"] != 4 * counts[0]["test"]):
        raise ValueError("planned cell denominator differs")
    denied = json.loads((folder / "typed-denylist.json").read_text())
    if (plan["snapshots"]["typed-denylist.json"] != proposal["unknown_and_failure_exclusions"]["typed_denylist"]["sha256"] or
            denied["schema_version"] != "provider-unknown-wire-denylist-v2" or
            plan["identity_denylists"] != denied["identity_denylists"]):
        raise ValueError("historical request exclusion contract differs")
    lineage = json.loads((folder / "cache-lineage.json").read_text())
    hashes = json.loads((folder / "initial-cache-manifest.json").read_text())
    recovery_consumed = []
    original = lineage["original"]
    if (len(original) != proposal["cache_lineage"]["original_source_entries"] or
            digest(original) != proposal["cache_lineage"]["original_source_map_sha256"]):
        raise ValueError("original cache lineage differs from approved proposal")
    if recovery:
        evidence = json.loads((folder / "recovery-evidence.json").read_text())
        values = {}
        for name in ("plan", "terminal", "diagnostics_verified", "envelope_claim", "envelope_terminal", "cache_manifest"):
            path = folder / ("recovery-" + name + ".json")
            if file_sha(path) != evidence[name]["sha256"]:
                raise ValueError("recovery evidence copy differs")
            values[name] = json.loads(path.read_text())
        values["completion"] = json.loads((folder / "recovery-completion.json").read_text())
        values["records"] = load_records(folder / "recovery-records.jsonl")
        recovery903_contract(evidence, values, records)
        recovery_consumed = recovery903_diagnostics(evidence, values, folder / "recovery-events.jsonl")
        if lineage["recovery"] != values["cache_manifest"]:
            raise ValueError("recovery cache differs from frozen terminal cache snapshot")
        if (file_sha(folder / "recovery-completion.json") != values["terminal"]["completion_sha256"] or
                file_sha(folder / "recovery-report.json") != values["terminal"]["report_sha256"] or
                any(file_sha(folder / ("recovery-" + name)) != expected
                    for name, expected in values["plan"]["snapshots"].items())):
            raise ValueError("recovery copied source or terminal differs")
        expected_cache = merge_cache_maps(original, lineage["recovery"])
    else:
        if lineage["recovery"] is not None:
            raise ValueError("unapproved recovery cache")
        expected_cache = original
    if plan["forbidden_wire_hashes"] != sorted(set(denied["identity_denylists"]["endpoint_body_sorted_json_sha256"]) | {WITHHELD_634} | set(recovery_consumed)):
        raise ValueError("historical or recovery consumed-request exclusions differ")
    if plan["initial_cache"] != hashes or hashes != expected_cache:
        raise ValueError("imported cache differs from approved cache lineage")
    verify_cache(folder / "cache", hashes)
    replay = None if "m5" in plan["unavailable_methods"] else replay_cached_components(records, manifest, folder / "cache")
    if replay != plan["cached_component_replay"]:
        raise ValueError("cache-only component replay differs")


def validate_execution(plan_path, lease_path, now=None):
    plan_path, lease_path = Path(plan_path), Path(lease_path)
    plan = json.loads(plan_path.read_text())
    lease = json.loads(lease_path.read_text())
    protocol = plan.get("protocol", "m0-m3")
    if protocol not in ("m0-m3", SUCCESSOR_PROTOCOL, FIRST8_PROTOCOL, REMAINING_PROTOCOL):
        raise ValueError("unknown reference protocol")
    successor = protocol == SUCCESSOR_PROTOCOL
    first8 = protocol == FIRST8_PROTOCOL
    remaining = protocol == REMAINING_PROTOCOL
    methods = SUCCESSOR_METHODS if successor or first8 or remaining else METHODS
    if remaining:
        if len(plan["user_ids"]) != 1:
            raise ValueError("remaining packet requires one frozen user")
        _, row = load_remaining_policy(plan_path.parent / "approved-policy.json", plan["user_ids"][0])
        limits = row["limits"]
    elif first8:
        if len(plan["user_ids"]) != 1:
            raise ValueError("original-eight packet requires exactly one user")
        limits = first8_limits(plan["user_ids"][0], plan.get("recovery903_enabled", False))
    else:
        limits = successor_limits(plan["user_ids"]) if successor else LIMITS
    now = time.time() if now is None else now
    if not isinstance(lease.get("job_id"), str) or not lease["job_id"].strip():
        raise ValueError("lease needs a job id")
    expected = {"role": "10", "state": "authorized", "provider": "openai",
                "model": "gpt-6-luna", "final_authorized": False,
                "user_partition": "dev", "methods": methods, "plan_sha256": file_sha(plan_path)}
    if successor or first8 or remaining:
        expected["protocol"] = protocol
    if any(lease.get(k) != value for k, value in expected.items()):
        raise ValueError("lease does not authorize this exact development panel")
    if (plan.get("methods") != methods or plan.get("method_config") != CONFIG or
            plan.get("model") != "gpt-6-luna" or plan.get("user_partition") != "dev" or
            plan.get("final") is not False or plan.get("seed") != 0 or
            plan.get("backend") != "openai" or plan.get("reasoning") != "none" or
            plan.get("tools") is not False or plan.get("output_tokens") != 2048 or
            plan.get("limits") != limits or plan.get("deadline") != DEADLINE):
        raise ValueError("unexpected reference plan settings")
    if successor:
        if (plan.get("proposal_sha256") != APPROVED_PROPOSAL_SHA or
                plan.get("forbidden_wire_hashes") != [FORBIDDEN_WIRE_HASH] or
                plan.get("unavailable_methods") != {"m7": M7_UNAVAILABLE} or
                plan.get("history_policies") != HISTORY_POLICIES):
            raise ValueError("successor safety contract differs")
        verify_cache(plan_path.parent / "cache", plan["initial_cache"])
    claim_path = Path(lease.get("claim_path", ""))
    if (not claim_path.is_absolute() or not claim_path.parent.is_dir() or
            plan_path.parent.resolve() in claim_path.resolve().parents):
        raise ValueError("lease claim path must be absolute and outside the packet")
    for key, maximum in limits.items():
        value = lease.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError("lease limit is invalid: " + key)
    if not isinstance(lease["max_calls"], int):
        raise ValueError("call limit must be integral")
    deadline = timestamp(lease["deadline"])
    if deadline > timestamp(DEADLINE) or now >= deadline:
        raise ValueError("lease deadline is invalid or expired")
    if plan["runtime"] != runtime_identity():
        raise ValueError("runtime differs from the frozen plan")
    expected_snapshots = {"records.jsonl", "manifest.json"}
    if successor:
        expected_snapshots.update({"approved-proposal.json", "prior-plan.json", "initial-cache-manifest.json"})
    if first8:
        expected_snapshots.update({"approved-proposal.json", "source-plan.json", "source-report.json",
                                   "source-completion.json", "source-records.jsonl", "source-manifest.json",
                                   "initial-cache-manifest.json", "cache-lineage.json", "typed-denylist.json"})
    if first8 and plan.get("recovery903_enabled"):
        expected_snapshots.update({"recovery-evidence.json", "recovery-plan.json", "recovery-terminal.json",
            "recovery-diagnostics_verified.json", "recovery-completion.json", "recovery-report.json",
            "recovery-records.jsonl", "recovery-manifest.json", "recovery-envelope_claim.json",
            "recovery-envelope_terminal.json", "recovery-events.jsonl", "recovery-cache_manifest.json"})
    if remaining:
        expected_snapshots.update({"approved-policy.json", "approved-cohort.json", "prior-plan.json", "prior-report.json",
            "prior-completion.json", "prior-terminal.json", "typed-denylist.json", "initial-cache-manifest.json"})
    if set(plan["snapshots"]) != expected_snapshots:
        raise ValueError("snapshot set differs")
    for name, expected_hash in plan["snapshots"].items():
        if file_sha(plan_path.parent / name) != expected_hash:
            raise ValueError("snapshot hash differs: " + name)
    if successor:
        if plan["snapshots"]["approved-proposal.json"] != APPROVED_PROPOSAL_SHA:
            raise ValueError("approved proposal snapshot differs")
        proposal = json.loads((plan_path.parent / "approved-proposal.json").read_text())
        panel = next(x for x in proposal["panels"] if x["user_id"] == plan["user_ids"][0])
        if (plan["snapshots"]["initial-cache-manifest.json"] != panel["cache_import_manifest_sha256"] or
                plan["cache_import_manifest_sha256"] != panel["cache_import_manifest_sha256"] or
                json.loads((plan_path.parent / "initial-cache-manifest.json").read_text()) != plan["initial_cache"]):
            raise ValueError("cache import is not the approved cache")
        if (plan["snapshots"]["prior-plan.json"] != panel["existing_m0_m3_plan_sha256"] or
                plan["prior_plan_sha256"] != panel["existing_m0_m3_plan_sha256"] or
                plan["prior_report_sha256"] != panel["existing_report_sha256"]):
            raise ValueError("prior lineage differs from approved proposal")
        prior = json.loads((plan_path.parent / "prior-plan.json").read_text())
        if any(plan["snapshots"][name] != prior["snapshots"][name] for name in ("records.jsonl", "manifest.json")):
            raise ValueError("inputs differ from approved prior phase")
    records = load_records(plan_path.parent / "records.jsonl")
    manifest = json.loads((plan_path.parent / "manifest.json").read_text())
    if (any(r.user_split != "dev" for r in records) or build_manifest(records, 0) != manifest or
            set(manifest["users"]) != set(plan["user_ids"]) or
            manifest["manifest_id"] != plan["derived_manifest_id"]):
        raise ValueError("snapshot is not the frozen development panel")
    if first8:
        validate_first8(plan_path, plan, records, manifest)
    if remaining:
        validate_remaining(plan_path, plan, records, manifest)
    return plan, lease, records, deadline


def claim_launch(directory, claim):
    write_private(Path(directory) / "LAUNCH_USED.json", claim)


def claim_lease(plan_path, lease_path, lease):
    claim = {"job_id": lease["job_id"], "plan_sha256": file_sha(plan_path),
             "lease_sha256": file_sha(lease_path), "started": time.time()}
    # This coordinator-designated path remains shared if the packet is copied.
    # A failed launch leaves its claim consumed; retries require a fresh lease.
    write_private(Path(lease["claim_path"]), claim)
    claim_launch(Path(plan_path).parent, claim)


def wire_identity(model, prompt, system, max_tokens):
    body = {"model": model, "instructions": system, "input": prompt,
            "max_output_tokens": max_tokens, "reasoning": {"effort": "none"},
            "store": False, "service_tier": "default"}
    return hashlib.sha256(json.dumps({"endpoint": OpenAILLM.base_url, "body": body},
                                     ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def body_identity(model, prompt, system, max_tokens):
    body = {"model": model, "instructions": system, "input": prompt,
            "max_output_tokens": max_tokens, "reasoning": {"effort": "none"},
            "store": False, "service_tier": "default"}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class MatchedHistoryM4(BradleyTerry):
    method_id = "m4_matched5"

    def fit(self, history, val):
        super().fit(selected_history(self, history), val)


class CacheOnlyHybrid(Hybrid):
    """Keep the existing component fits, but prohibit their cache misses."""
    def fit(self, history, val):
        previous = self.llm.cache_only_components
        self.llm.cache_only_components = True
        try:
            super().fit(history, val)
        finally:
            self.llm.cache_only_components = previous


class CacheOnlyVerifiedHybrid(VerifiedHybrid, CacheOnlyHybrid):
    # VerifiedHybrid.fit calls super().fit, which resolves through the guarded
    # Hybrid fit above. The guard ends before the unchanged validation filter.
    pass


class UnavailableMethod(UserModel):
    def __init__(self, llm, reason, **kwargs):
        super().__init__(llm, **kwargs)
        self.reason = reason

    def fit(self, history, val):
        raise RuntimeError("predeclared unavailable: " + self.reason)


def first8_model(method, backend, unavailable, **kwargs):
    if method in unavailable:
        return UnavailableMethod(backend, unavailable[method], **kwargs)
    classes = {"m4_full": BradleyTerry, "m4_matched5": MatchedHistoryM4,
               "m5": CacheOnlyHybrid, "m6": CacheOnlyVerifiedHybrid}
    return classes[method](backend, **kwargs)


class ReferenceBackend(OpenAILLM):
    """Keep the existing backend, but cease all further calls after an uncertain one."""
    def __init__(self, *args, forbidden_wire_hashes=(), forbidden_body_hashes=(),
                 enforce_unique_requests=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.forbidden_wire_hashes = set(forbidden_wire_hashes)
        self.forbidden_body_hashes = set(forbidden_body_hashes)
        self.cache_only_components = False
        self.enforce_unique_requests = enforce_unique_requests
        self.consumed_wire_hashes, self.request_audit, self.guard_denials = set(), [], []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.0):
        if self.guard_denials:
            raise RuntimeError("previous historical request denial; no further network admission")
        if self.cache_only_components:
            raise RuntimeError("component fit cache miss; no network dispatch")
        if self.cost_summary()["reserved_usd"] > 0:
            raise RuntimeError("previous API outcome uncertain; no subsequent request allowed")
        key = wire_identity(self.model, prompt, system, max_tokens)
        body_key = body_identity(self.model, prompt, system, max_tokens)
        if key in self.forbidden_wire_hashes or body_key in self.forbidden_body_hashes:
            self.guard_denials.append({"request_sha256": key, "body_compact_json_sha256": body_key})
            raise RuntimeError("request identity forbidden; no network dispatch")
        if self.enforce_unique_requests and key in self.consumed_wire_hashes:
            raise RuntimeError("request identity already consumed; no network dispatch")
        self.consumed_wire_hashes.add(key)
        item = {"request_sha256": key, "body_compact_json_sha256": body_key, "state": "admitted"}
        self.request_audit.append(item)
        try:
            result = super().complete(prompt, system, max_tokens, temperature)
        except Exception:
            item["state"] = "uncertain" if self.cost_summary()["reserved_usd"] > 0 else "rejected"
            raise
        item["state"] = "completed"
        return result


def execute(plan_path, lease_path):
    plan_path, lease_path = Path(plan_path), Path(lease_path)
    plan, lease, records, deadline = validate_execution(plan_path, lease_path)
    output = plan_path.parent / "output"
    if output.exists():
        raise FileExistsError("reference output already exists")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unavailable; no launch claimed")
    claim_lease(plan_path, lease_path, lease)
    budget = Budget(max_calls=lease["max_calls"],
                    max_seconds=min(lease["max_seconds"], deadline - time.time()))
    successor = plan.get("protocol") == SUCCESSOR_PROTOCOL
    first8 = plan.get("protocol") == FIRST8_PROTOCOL
    remaining = plan.get("protocol") == REMAINING_PROTOCOL
    backend = ReferenceBackend(plan["model"], budget=budget, max_usd=lease["max_usd"],
                               forbidden_wire_hashes=plan.get("forbidden_wire_hashes", ()),
                               forbidden_body_hashes=plan.get("identity_denylists", {}).get("body_compact_json_sha256", ()),
                               enforce_unique_requests=successor or first8 or remaining)
    cache = plan_path.parent / "cache"
    def factory(method):
        kwargs = dict(seed=0, cache_dir=cache, max_calls=lease["max_calls"], **CONFIG)
        if first8 or remaining:
            return first8_model(method, backend, plan["unavailable_methods"], **kwargs)
        if method == "m4_matched5":
            return MatchedHistoryM4(backend, **kwargs)
        return create_method("m4" if method == "m4_full" else method, backend, **kwargs)
    factories = {method: (lambda user, method=method: factory(method)) for method in plan["methods"]}
    mask = os.umask(0o077)
    try:
        report = run_fidelity(records, plan_path.parent / "manifest.json", factories, output,
                              "prism", users="dev", n_users=len(plan["user_ids"]), seed=0,
                              final=False, run_config={"reference_plan_sha256": file_sha(plan_path),
                              "lease_sha256": file_sha(lease_path), "method_config": CONFIG,
                              "model": plan["model"], "reasoning": "none", "tools": False,
                              "max_usd": lease["max_usd"], "max_calls": lease["max_calls"],
                              "max_seconds": lease["max_seconds"], "deadline": lease["deadline"],
                              "parent_manifest_id": plan["parent_manifest_id"],
                              "protocol": plan.get("protocol", "m0-m3"),
                              "history_policies": plan.get("history_policies", {}),
                              "unavailable_methods": plan.get("unavailable_methods", {}),
                              "imported_cache_entries": len(plan.get("initial_cache", {})),
                              "component_fit_policy": plan.get("component_fit_policy"),
                              "recovery903_enabled": plan.get("recovery903_enabled", False)})
        final_cache = cache_hashes(cache) if first8 or remaining else None
        if first8 or remaining:
            if any(final_cache.get(name) != expected for name, expected in plan["initial_cache"].items()):
                raise ValueError("imported cache changed during execution")
            # Bind imported responses and successful new cache values separately.
            write_private(plan_path.parent / "final-cache-manifest.json", final_cache)
        write_private(plan_path.parent / "completion.json", {
            "job_id": lease["job_id"], "completed": time.time(),
            "report_sha256": file_sha(output / "report.json"),
            "predictions_sha256": file_sha(output / "predictions.jsonl"),
            "budgets": report["backend_budgets"],
            "attempts": getattr(budget, "_taste_attempts", budget.calls),
            "backend_calls": budget.calls,
            "request_audit": backend.request_audit,
            "historical_guard_denials": backend.guard_denials,
            "cache_provenance": ({"initial_entries": len(plan["initial_cache"]),
                "initial_map_sha256": digest(plan["initial_cache"]),
                "final_manifest_sha256": file_sha(plan_path.parent / "final-cache-manifest.json"),
                "new_entries": len(set(final_cache) - set(plan["initial_cache"])),
                "component_replay": plan["cached_component_replay"]} if first8 or remaining else None),
            "failures": {method: result["failures"] for method, result in report["methods"].items()}})
    finally:
        os.umask(mask)
    return output / "report.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", required=True)
    prep.add_argument("--manifest", required=True)
    prep.add_argument("--destination", required=True)
    prep.add_argument("--n-users", type=int, default=8)
    successor = sub.add_parser("prepare-successor")
    successor.add_argument("--proposal", required=True)
    successor.add_argument("--user", required=True, choices=sorted(SUCCESSOR_CALLS))
    successor.add_argument("--destination", required=True)
    first8 = sub.add_parser("prepare-first8")
    first8.add_argument("--proposal", required=True)
    first8.add_argument("--user", required=True, choices=FIRST8_USERS)
    first8.add_argument("--destination", required=True)
    first8.add_argument("--recovery-evidence")
    remaining = sub.add_parser("prepare-remaining")
    remaining.add_argument("--policy", required=True)
    remaining.add_argument("--user", required=True)
    remaining.add_argument("--destination", required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.add_argument("--lease", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        path = prepare(args.source, args.manifest, args.destination, args.n_users)
        print(json.dumps({"plan": str(path), "sha256": file_sha(path)}))
    elif args.command == "prepare-successor":
        path = prepare_successor(args.proposal, args.user, args.destination)
        print(json.dumps({"plan": str(path), "sha256": file_sha(path)}))
    elif args.command == "prepare-first8":
        path = prepare_first8(args.proposal, args.user, args.destination, args.recovery_evidence)
        print(json.dumps({"plan": str(path), "sha256": file_sha(path)}))
    elif args.command == "prepare-remaining":
        path = prepare_remaining(args.policy, args.user, args.destination)
        print(json.dumps({"plan": str(path), "sha256": file_sha(path)}))
    else:
        path = execute(args.plan, args.lease)
        print(json.dumps({"report": str(path), "sha256": file_sha(path)}))


if __name__ == "__main__":
    main()
