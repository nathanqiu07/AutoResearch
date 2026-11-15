#!/usr/bin/env python3
"""Frozen development-only native M0/M1 consumer diagnostic; no extraction search.

This entrypoint reuses UserModel, the reviewed Responses backend, DollarLedger,
and the existing request gate. The coordinator owns leases and the shared ledger.
Private packets contain history and labels; public reports contain aggregates only.
"""
import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoresearch.llm import Budget, LLM
from autoresearch.research.stats import bootstrap_ci
from autoresearch.taste.usermodel import UserModel
from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend, RATES
from autoresearch.taste.overnight.contracts import digest
from autoresearch.taste.overnight.runner import _CallGate, timestamp

MODELS = ["gpt-6-luna", "gpt-6-sol"]
ARMS = ["none", "own", "wrong"]
DEADLINE = "2026-11-15T19:45:00Z"
DEV_ROW = re.compile(rb'"user_split"\s*:\s*"dev"')


def file_sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def private_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def runtime_identity():
    files = [Path(__file__).resolve()] + sorted((ROOT / "autoresearch").rglob("*.py"))
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "files": {str(p.relative_to(ROOT)): file_sha(p) for p in files}}


def select_panel(manifest, excluded, users=8, targets=4):
    """Use IDs/counts only; select paired donors with equal full-history size."""
    if type(users) is not int or users < 2 or users % 2 or type(targets) is not int or targets < 1:
        raise ValueError("positive target count and even user count required")
    bins = defaultdict(list)
    for user, item in manifest["users"].items():
        if (item["partition"] == "dev" and user not in excluded and item["history"]
                and len(item["test"]) >= targets):
            bins[len(item["history"])].append(user)
    pairs = []
    for count, members in bins.items():
        ordered = sorted(members, key=lambda u: digest(["morning05-user-v1", u]))
        pairs.extend((ordered[i], ordered[i + 1]) for i in range(0, len(ordered) - 1, 2))
    pairs.sort(key=lambda pair: digest(["morning05-pair-v1", pair]))
    if len(pairs) * 2 < users:
        raise ValueError("not enough unused count-matched development users")
    pairs = pairs[:users // 2]
    selected = [u for pair in pairs for u in pair]
    return {"users": selected,
            "donors": {u: pair[1 - i] for pair in pairs for i, u in enumerate(pair)},
            "targets": {u: sorted(manifest["users"][u]["test"],
                                   key=lambda i: digest(["morning05-target-v1", i]))[:targets]
                        for u in selected},
            "selection_uses": "canonical development membership, prior-use exclusion, IDs and counts only",
            "target_label_access_before_selection": False}


class _Capture(LLM):
    name = "offline-native-request-capture"
    model = "fixture"

    def __init__(self, response='{"probabilities":[0.5,0.5]}'):
        super().__init__(Budget(max_calls=1, max_seconds=60))
        self.response = response
        self.request = None

    def complete(self, prompt, system="", max_tokens=2048, temperature=0.0):
        self.request = {"prompt": prompt, "system": system, "max_tokens": max_tokens,
                        "temperature": temperature}
        return self.response


def native_request(item, history):
    backend = _Capture()
    model = UserModel(backend)
    model._predict_with(item["context"], item["options"], exemplars=history)
    return backend.request


def parse_response(request, response):
    """Run the existing native probability validation, without a network call."""
    payload = json.loads(request["prompt"].split("INPUT_JSON:\n", 1)[1])
    backend = _Capture(response)
    result = UserModel(backend)._predict_with(payload["context"], payload["options"],
                                            payload["principles"], payload["persona"], payload["past_choices"])
    if backend.request != request:
        raise ValueError("native request reconstruction differs")
    return asdict(result)


def wire_body(model, request):
    return {"model": model, "instructions": request["system"], "input": request["prompt"],
            "max_output_tokens": request["max_tokens"], "reasoning": {"effort": "none"},
            "store": False, "service_tier": "default",
            "prompt_cache_options": {"mode": "implicit", "ttl": "30m"}}


def request_bound(model, request):
    encoded = json.dumps(wire_body(model, request), ensure_ascii=False, allow_nan=False).encode("utf-8")
    input_bound = len(encoded) + 1024
    if input_bound + request["max_tokens"] >= 272000:
        raise ValueError("full history exceeds reviewed short-context bound; do not truncate")
    inp, out = map(Decimal, RATES[model])
    return (Decimal(input_bound) * inp + Decimal(request["max_tokens"]) * out) / Decimal(1_000_000)


def prepare(source, manifest_path, used_manifests, destination, source_sha256, users=8, targets=4):
    destination = Path(destination).resolve()
    if destination.exists() or ROOT in destination.parents or destination == ROOT:
        raise ValueError("new private packet outside repository required")
    manifest = json.loads(Path(manifest_path).read_text())
    excluded = set()
    used = []
    for path in used_manifests:
        prior = json.loads(Path(path).read_text())
        excluded.update(prior["users"])
        used.append({"path": str(Path(path).resolve()), "sha256": file_sha(path)})
    selection = select_panel(manifest, excluded, users, targets)
    selection.update(parent_manifest_id=manifest["manifest_id"],
                     parent_manifest_sha256=file_sha(manifest_path), excluded_user_count=len(excluded),
                     used_manifests=used)
    destination.mkdir(mode=0o700)
    # This durable selection is created BEFORE opening the choice source.
    private_json(destination / "selection.json", selection)
    if file_sha(source) != source_sha256:
        raise ValueError("source file differs from previously verified canonical source")
    selected = set(selection["users"])
    patterns = [re.compile(rb'"user_id"\s*:\s*' + re.escape(json.dumps(u).encode())) for u in selected]
    by_user = {u: {} for u in selected}
    with Path(source).open("rb") as stream:
        for line in stream:
            # Final-user rows are never parsed. Only preselected development users enter the packet.
            if not DEV_ROW.search(line) or not any(p.search(line) for p in patterns):
                continue
            record = json.loads(line)
            user = record["choice"]["user_id"]
            if user not in selected or record["user_split"] != "dev":
                raise ValueError("record outside frozen development selection")
            row = record["choice"]
            if row["example_id"] in by_user[user]:
                raise ValueError("duplicate choice")
            by_user[user][row["example_id"]] = row
    histories, items, labels = {}, [], {}
    for user in selection["users"]:
        declared = manifest["users"][user]
        expected = set(declared["history"] + declared["val"] + declared["test"])
        if set(by_user[user]) != expected:
            raise ValueError("selected source IDs differ from canonical manifest")
        histories[user] = [by_user[user][i] for i in declared["history"]]
        if {x["group_id"] for x in histories[user]} & {by_user[user][i]["group_id"] for i in declared["test"]}:
            raise ValueError("history-target conversation overlap")
        for identity in selection["targets"][user]:
            row = by_user[user][identity]
            labels[identity] = row["chosen"]
            items.append({"item_id": identity, "user_id": user, "context": row["context"],
                          "options": [row["a_text"], row["b_text"]]})
    requests = []
    conditions = [(m, a) for m in MODELS for a in ARMS]
    for index, item in enumerate(items):
        user, donor = item["user_id"], selection["donors"][item["user_id"]]
        if len(histories[user]) != len(histories[donor]):
            raise ValueError("wrong-history count does not match own full history")
        shift = index % len(conditions)
        for model, arm in conditions[shift:] + conditions[:shift]:
            history = [] if arm == "none" else histories[user if arm == "own" else donor]
            request = native_request(item, history)
            requests.append({**item, "cell_id": digest([model, arm, user, item["item_id"]]),
                             "model": model, "arm": arm, "history_count": len(history),
                             "history_user_id": None if arm == "none" else user if arm == "own" else donor,
                             "native_request": request, "wire_sha256": digest(wire_body(model, request)),
                             "request_bound_usd": str(request_bound(model, request))})
    private_json(destination / "inputs.json", {"histories": histories, "items": items})
    private_json(destination / "labels.json", labels)
    private_json(destination / "requests.json", requests)
    bound = sum((Decimal(r["request_bound_usd"]) for r in requests), Decimal(0))
    plan = {"schema_version": "gio-morning-consumer-probe-v1", "lane": "05", "models": MODELS,
            "arms": ARMS, "reasoning": "none", "output_tokens": 2048, "tools": [],
            "user_partition": "dev", "final": False, "planned_calls": len(requests),
            "users": len(selected), "targets_per_user": targets, "source_sha256": source_sha256,
            "max_usd": float(bound.quantize(Decimal('.01'), rounding=ROUND_CEILING)),
            "conservative_pre_cache_bound_usd": str(bound), "max_seconds": 3600, "deadline": DEADLINE,
            "retry_policy": "one attempt per cell; uncertain usage holds entire lane; no retries",
            "primary_metric": "equal-user accuracy, all planned failures/unavailable counted wrong",
            "length_baseline": "longer Python string; tie chooses a; scored once per unique target after execution",
            "history_policy": "all canonical history, no truncation; donor pairs match full count",
            "order": "six-condition cyclic rotation across fixed user-target sequence",
            "runtime": runtime_identity(),
            "snapshots": {name: file_sha(destination / name) for name in
                          ["selection.json", "inputs.json", "labels.json", "requests.json"]},
            "limits": ["Eight fresh development users are a diagnostic, not final-test evidence.",
                       "Donors match count, not topic, token length or labels; dependence within donor pairs.",
                       "No extraction or calibrated-confidence comparison; raw confidence is uncalibrated."]}
    private_json(destination / "plan.json", plan)
    return plan


def validate_lease(plan_path, lease):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    required = {"state": "authorized", "lane": "05", "plan_sha256": file_sha(plan_path),
                "user_partition": "dev", "final": False, "models": MODELS, "arms": ARMS,
                "max_calls": plan["planned_calls"]}
    if any(lease.get(k) != v or type(lease.get(k)) is not type(v) for k, v in required.items()):
        raise ValueError("coordinator lease does not bind exact development plan")
    if not isinstance(lease.get("job_id"), str) or not lease["job_id"]:
        raise ValueError("coordinator job identity required")
    for key in ["max_usd", "max_seconds"]:
        value = lease.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError("finite positive limits required")
    if lease["max_usd"] > plan["max_usd"] or lease["max_seconds"] > 3600:
        raise ValueError("lease exceeds frozen scope")
    deadline = timestamp(lease["deadline"])
    if deadline > timestamp(plan["deadline"]) or deadline <= datetime.now(timezone.utc):
        raise ValueError("expired or extended deadline")
    claim = Path(lease.get("claim_path", ""))
    if (not claim.is_absolute() or not claim.parent.is_dir() or claim.exists()
            or plan_path.parent == claim.parent or plan_path.parent in claim.parents
            or any((plan_path.parent / p).exists() for p in ["LAUNCH_USED.json", "outcomes.jsonl", "report.json"])):
        raise ValueError("fresh coordinator claim outside packet required")
    # Documentation/status commits may follow preparation; all runtime bytes must match.
    if runtime_identity()["files"] != plan["runtime"]["files"]:
        raise ValueError("runtime changed since preparation")
    for name, expected in plan.get("snapshots", {}).items():
        if Path(name).name != name or file_sha(plan_path.parent / name) != expected:
            raise ValueError("private frozen input changed")
    return plan


def summarize(requests, outcomes, labels):
    known = {r["cell_id"] for r in requests}
    if len(known) != len(requests) or len({r["cell_id"] for r in outcomes}) != len(outcomes):
        raise ValueError("duplicate planned or observed cells")
    if any(r["cell_id"] not in known for r in outcomes):
        raise ValueError("unexpected observed cell")
    observed = {r["cell_id"]: r for r in outcomes}
    groups, targets = defaultdict(lambda: defaultdict(list)), {}
    for row in requests:
        actual = labels[row["item_id"]]
        outcome = observed.get(row["cell_id"], {})
        prediction = outcome.get("prediction")
        groups[row["model"] + ":" + row["arm"]][row["user_id"]].append(
            (int(prediction is not None and prediction["choice"] == actual), int(prediction is not None)))
        targets[row["item_id"]] = row
    conditions, per_user = {}, {}
    for key, users in groups.items():
        per_user[key] = {u: sum(x[0] for x in vals) / len(vals) for u, vals in users.items()}
        all_rows = [x for vals in users.values() for x in vals]
        valid = sum(x[1] for x in all_rows)
        conditions[key] = {"users": len(users), "planned": len(all_rows), "valid": valid,
                           "missing_or_failed": len(all_rows) - valid, "correct": sum(x[0] for x in all_rows),
                           "user_macro_accuracy": sum(per_user[key].values()) / len(users)}
    longer, ties = defaultdict(list), 0
    for identity, row in targets.items():
        a, b = row["options"]
        ties += len(a) == len(b)
        guess = "a" if len(a) >= len(b) else "b"
        longer[row["user_id"]].append(int(guess == labels[identity]))
    differences = {}
    for model in MODELS:
        own = per_user.get(model + ":own", {})
        for arm in ["none", "wrong"]:
            other = per_user.get(model + ":" + arm, {})
            users = sorted(set(own) & set(other))
            if users:
                values = [own[u] - other[u] for u in users]
                differences[model + ":own-minus-" + arm] = {
                    "mean": sum(values) / len(values),
                    "descriptive_conditional_user_bootstrap_ci95": list(bootstrap_ci(values, level=.95)),
                    "users": len(users)}
    return {"conditions": conditions, "paired_differences": differences,
            "length_baseline": {"targets": len(targets), "users": len(longer), "ties": ties,
                                "rule": "longer Python string; ties choose a",
                                "user_macro_accuracy": sum(sum(v) / len(v) for v in longer.values()) / len(longer)},
            "interpretation": "Small development diagnostic; donor dependence, no final-test or method-superiority claim."}


def execute(plan_path, lease_path):
    plan_path, lease_path = Path(plan_path).resolve(), Path(lease_path).resolve()
    lease = json.loads(lease_path.read_text())
    plan = validate_lease(plan_path, lease)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OpenAI credential environment required")
    ledger_path = Path(lease["ledger_path"])
    if not ledger_path.is_absolute() or not ledger_path.is_file():
        raise ValueError("existing coordinator-created shared ledger required")
    ledger = DollarLedger(ledger_path, **lease["ledger_policy"])
    if ledger.summary()["held_after_uncertain"]:
        raise ValueError("coordinator ledger is held after uncertain usage")
    packet = plan_path.parent
    requests = json.loads((packet / "requests.json").read_text())
    if len(requests) != plan["planned_calls"]:
        raise ValueError("planned request count differs")
    claim = {"job_id": lease["job_id"], "plan_sha256": file_sha(plan_path),
             "lease_sha256": file_sha(lease_path), "started_utc": datetime.now(timezone.utc).isoformat()}
    private_json(lease["claim_path"], claim)
    private_json(packet / "LAUNCH_USED.json", claim)
    budget = Budget(max_calls=lease["max_calls"], max_seconds=lease["max_seconds"])
    gates, backends = {}, {}
    for model in MODELS:
        backend = OpenAIResponsesBackend(model=model, reasoning="none", ledger=ledger,
                                         max_usd=lease["max_usd"], budget=budget,
                                         timeout=min(60, lease["max_seconds"] / 2))
        backends[model] = backend
        manifest = {"stage": "dev", "allocation": {**lease, "cost_mode": "priced_api"},
                    "deadline": lease["deadline"], "job_id": lease["job_id"], "model": model}
        gates[model] = _CallGate(backend, manifest, {"expires_at": lease["deadline"]},
                                {"max_tokens": 2048, "temperature": 0.0}, packet / "traces" / model, None)
    outcomes = []
    descriptor = os.open(str(packet / "outcomes.jsonl"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        for row in requests:
            request = row["native_request"]
            outcome = {"cell_id": row["cell_id"], "user_id": row["user_id"], "item_id": row["item_id"],
                       "model": row["model"], "arm": row["arm"], "prediction": None, "error": None}
            try:
                response = gates[row["model"]].complete(request["prompt"], system=request["system"],
                                                         max_tokens=request["max_tokens"],
                                                         temperature=request["temperature"])
                outcome["prediction"] = parse_response(request, response)
            except Exception as exc:
                # Never print raw provider exceptions, payloads, or credentials.
                outcome["error"] = "invalid_output" if isinstance(exc, ValueError) else "unavailable_or_backend_failure"
                outcome["exception_type"] = type(exc).__name__
            outcomes.append(outcome)
            stream.write(json.dumps(outcome, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    # Only now do target answers enter scoring. They never entered request preparation.
    labels = json.loads((packet / "labels.json").read_text())
    report = summarize(requests, outcomes, labels)
    report.update(plan_sha256=file_sha(plan_path), runtime=plan["runtime"], completed_utc=datetime.now(timezone.utc).isoformat(),
                  outcomes_sha256=file_sha(packet / "outcomes.jsonl"),
                  accounting={"per_model": {m: b.cost_summary() for m, b in backends.items()},
                              "shared_ledger": ledger.summary(),
                              "known_estimated_usd_once": sum(b.cost_summary()["spent_usd"] for b in backends.values()),
                              "warning": "Per-model campaign fields repeat the shared ledger; do not sum them."})
    private_json(packet / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for arg in ["source", "manifest", "destination", "source-sha256"]:
        prep.add_argument("--" + arg, required=True)
    prep.add_argument("--used-manifest", action="append", required=True)
    prep.add_argument("--users", type=int, default=8)
    prep.add_argument("--targets", type=int, default=4)
    run = sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.add_argument("--lease", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.source, args.manifest, args.used_manifest, args.destination,
                         args.source_sha256, args.users, args.targets)
        print(json.dumps({k: result[k] for k in ["planned_calls", "users", "targets_per_user", "max_usd",
                                               "conservative_pre_cache_bound_usd", "deadline"]}))
    else:
        result = execute(args.plan, args.lease)
        print(json.dumps({"conditions": result["conditions"], "length_baseline": result["length_baseline"],
                          "known_estimated_usd_once": result["accounting"]["known_estimated_usd_once"]}))


if __name__ == "__main__":
    main()
