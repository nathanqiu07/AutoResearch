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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoresearch.llm import Budget
from autoresearch.taste.backends import OpenAILLM
from autoresearch.taste.fidelity import run_fidelity, select_users
from autoresearch.taste.methods import create_method
from autoresearch.taste.prefdata import (PreferenceRecord, build_manifest, load_records,
                                       normalize_row)
from autoresearch.taste.usermodel import Choice
from dataclasses import asdict

METHODS = ["m0", "m1", "m2", "m3"]
CONFIG = {"max_history": 5, "max_hypotheses": 2, "max_principles": 2,
          "max_exemplars": 1, "max_persona_chars": 1600, "k": 5}
LIMITS = {"max_usd": 5, "max_calls": 1500, "max_seconds": 3600}
DEADLINE = "2026-11-15T17:00:00Z"
DEV_ROW = re.compile(rb'"user_split"\s*:\s*"dev"')


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


def validate_execution(plan_path, lease_path, now=None):
    plan_path, lease_path = Path(plan_path), Path(lease_path)
    plan = json.loads(plan_path.read_text())
    lease = json.loads(lease_path.read_text())
    now = time.time() if now is None else now
    if not isinstance(lease.get("job_id"), str) or not lease["job_id"].strip():
        raise ValueError("lease needs a job id")
    expected = {"role": "10", "state": "authorized", "provider": "openai",
                "model": "gpt-6-luna", "final_authorized": False,
                "user_partition": "dev", "methods": METHODS, "plan_sha256": file_sha(plan_path)}
    if any(lease.get(k) != value for k, value in expected.items()):
        raise ValueError("lease does not authorize this exact development panel")
    if (plan.get("methods") != METHODS or plan.get("method_config") != CONFIG or
            plan.get("model") != "gpt-6-luna" or plan.get("user_partition") != "dev" or
            plan.get("final") is not False or plan.get("seed") != 0 or
            plan.get("backend") != "openai" or plan.get("reasoning") != "none" or
            plan.get("tools") is not False or plan.get("output_tokens") != 2048 or
            plan.get("limits") != LIMITS or plan.get("deadline") != DEADLINE):
        raise ValueError("unexpected reference plan settings")
    claim_path = Path(lease.get("claim_path", ""))
    if (not claim_path.is_absolute() or not claim_path.parent.is_dir() or
            plan_path.parent.resolve() in claim_path.resolve().parents):
        raise ValueError("lease claim path must be absolute and outside the packet")
    for key, maximum in LIMITS.items():
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
    if set(plan["snapshots"]) != {"records.jsonl", "manifest.json"}:
        raise ValueError("snapshot set differs")
    for name, expected_hash in plan["snapshots"].items():
        if file_sha(plan_path.parent / name) != expected_hash:
            raise ValueError("snapshot hash differs: " + name)
    records = load_records(plan_path.parent / "records.jsonl")
    manifest = json.loads((plan_path.parent / "manifest.json").read_text())
    if (any(r.user_split != "dev" for r in records) or build_manifest(records, 0) != manifest or
            set(manifest["users"]) != set(plan["user_ids"]) or
            manifest["manifest_id"] != plan["derived_manifest_id"]):
        raise ValueError("snapshot is not the frozen development panel")
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


class ReferenceBackend(OpenAILLM):
    """Keep the existing backend, but cease all further calls after an uncertain one."""
    def complete(self, *args, **kwargs):
        if self.cost_summary()["reserved_usd"] > 0:
            raise RuntimeError("previous API outcome uncertain; no subsequent request allowed")
        return super().complete(*args, **kwargs)


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
    backend = ReferenceBackend(plan["model"], budget=budget, max_usd=lease["max_usd"])
    cache = plan_path.parent / "cache"
    factories = {method: (lambda user, method=method: create_method(
        method, backend, seed=0, cache_dir=cache, max_calls=lease["max_calls"], **CONFIG))
        for method in METHODS}
    mask = os.umask(0o077)
    try:
        report = run_fidelity(records, plan_path.parent / "manifest.json", factories, output,
                              "prism", users="dev", n_users=len(plan["user_ids"]), seed=0,
                              final=False, run_config={"reference_plan_sha256": file_sha(plan_path),
                              "lease_sha256": file_sha(lease_path), "method_config": CONFIG,
                              "model": plan["model"], "reasoning": "none", "tools": False,
                              "max_usd": lease["max_usd"], "max_calls": lease["max_calls"],
                              "max_seconds": lease["max_seconds"], "deadline": lease["deadline"],
                              "parent_manifest_id": plan["parent_manifest_id"]})
        write_private(plan_path.parent / "completion.json", {
            "job_id": lease["job_id"], "completed": time.time(),
            "report_sha256": file_sha(output / "report.json"),
            "budgets": report["backend_budgets"],
            "attempts": getattr(budget, "_taste_attempts", budget.calls),
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
    run = sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.add_argument("--lease", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        path = prepare(args.source, args.manifest, args.destination, args.n_users)
        print(json.dumps({"plan": str(path), "sha256": file_sha(path)}))
    else:
        path = execute(args.plan, args.lease)
        print(json.dumps({"report": str(path), "sha256": file_sha(path)}))


if __name__ == "__main__":
    main()
