#!/usr/bin/env python3
"""Fixed-history association control over frozen PRISM development inputs.

Historical predictions are aliases. Paid execution requires a distinct coordinator
lease and fresh response cache; no fit, baseline record, or core method is changed.
"""
import argparse
import copy
from dataclasses import asdict
from decimal import Decimal, ROUND_CEILING
import json
import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import overnight_labeled_reference as ref
from autoresearch.taste.methods.m1_history import RawHistory
from autoresearch.taste.usermodel import TasteArtifacts

PROTOCOL = "paired-history-v1"
PROPOSAL_SHA = "84010c55b57f5746893a19ebfb54471d9dcb160f34853eee9e57b0d000780a71"
GUARD_SHA = "6c272e0091356f6ee99e2bc814c1b333977f025e7ce2e2eb77ea894ea79ccd39"
METHODS = {"own": "m1_own", "wrong": "m1_wrong"}


def runtime_identity():
    value = ref.runtime_identity()
    value["files"][str(Path(__file__).relative_to(ROOT))] = ref.file_sha(__file__)
    return value


def limits(row):
    cost = sum(Decimal(row["arms"][a]["reservation_sum_bound_usd"]) for a in ("own", "wrong"))
    cap = (cost * Decimal("1.15")).quantize(Decimal(".001"), rounding=ROUND_CEILING)
    return {"max_calls": sum(row["arms"][a]["eligible_calls"] for a in ("own", "wrong")),
            "max_usd": float(cap), "max_seconds": 1800}


def target_key(context, options):
    return ref.digest([context, list(options)])


class ControlBackend(ref.ReferenceBackend):
    def __init__(self, *args, allowed_requests, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_requests = set(allowed_requests)

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.0):
        identity = ref.wire_identity(self.model, prompt, system, max_tokens)
        if identity not in self.allowed_requests:
            self.guard_denials.append({"request_sha256": identity, "reason": "outside_frozen_request_set"})
            raise RuntimeError("request is outside frozen request set; no transport")
        return super().complete(prompt, system, max_tokens, temperature)


class FrozenHistory(RawHistory):
    """Hydrate the exact source artifact after checking recipient fit scope."""
    def __init__(self, *args, source, history_ids, validation_ids, targets, withheld_ids=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source
        self.history_ids, self.validation_ids = list(history_ids), list(validation_ids)
        self.target_ids = {}
        for target in targets:
            key = target_key(target["context"], target["options"])
            if key in self.target_ids:
                raise ValueError("duplicate target input identity")
            self.target_ids[key] = target["example_id"]
        self.withheld_ids = set(withheld_ids)

    def fit(self, history, val):
        if ([c.identity for c in history] != self.history_ids or
                [c.identity for c in val] != self.validation_ids):
            raise ValueError("recipient fit scope differs")
        # The source metadata retains its actual donor user identity. No relabeling.
        self._artifacts = TasteArtifacts(**copy.deepcopy(self.source["artifacts"]))

    def predict(self, context, options):
        identity = self.target_ids.get(target_key(context, options))
        if identity is None:
            raise ValueError("prediction target is outside the frozen scope")
        if identity in self.withheld_ids:
            raise RuntimeError("predeclared prior-unknown target withheld; no request")
        return super().predict(context, options)


def load_proposal(path, user):
    if ref.file_sha(path) != PROPOSAL_SHA:
        raise ValueError("proposal is not the frozen control proposal")
    proposal = json.loads(Path(path).read_text())
    rows = proposal["assignment"]
    parent = ref.read_ref(proposal["parent64"])
    if [r["target_user_id"] for r in rows] != parent["user_ids"]:
        raise ValueError("canonical cohort order differs")
    groups = {}
    for position, row in enumerate(rows, 1):
        groups.setdefault(row["selected_history_size"], []).append(row["target_user_id"])
        if (row["canonical_position_1based"] != position or row["prospective_pair_order_if_authorized"] !=
                (["own", "wrong"] if position % 2 else ["wrong", "own"])):
            raise ValueError("fixed arm order differs")
    for row in rows:
        group = groups[row["selected_history_size"]]
        if len(group) < 2 or row["donor_user_id"] != group[(group.index(row["target_user_id"]) + 1) % len(group)]:
            raise ValueError("same-size donor derangement differs")
    matches = [r for r in rows if r["target_user_id"] == user]
    if len(matches) != 1:
        raise ValueError("user is outside frozen cohort")
    row, = matches
    donor = next(r for r in rows if r["target_user_id"] == row["donor_user_id"])
    if row["donor_artifact"] != donor["own_artifact"]:
        raise ValueError("donor artifact lineage differs")
    return proposal, row, donor


def source_input(plan_ref, artifact_ref, user):
    prior = ref.read_ref(plan_ref)
    folder = Path(plan_ref["path"]).parent
    if (prior["user_partition"] != "dev" or prior["final"] is not False or prior["seed"] != 0 or
            prior["model"] != "gpt-6-luna" or prior["method_config"] != ref.CONFIG or user not in prior["user_ids"]):
        raise ValueError("source is not the frozen development baseline")
    for name in ("records.jsonl", "manifest.json"):
        if ref.file_sha(folder / name) != prior["snapshots"][name]:
            raise ValueError("source input changed")
    if any(not ref.DEV_ROW.search(line) for line in (folder / "records.jsonl").read_bytes().splitlines() if line.strip()):
        raise ValueError("source contains a non-development row")
    records = ref.load_records(folder / "records.jsonl")
    manifest = json.loads((folder / "manifest.json").read_text())
    if ref.build_manifest(records, 0) != manifest:
        raise ValueError("source manifest differs")
    body = ref.read_ref(artifact_ref)
    if body["version"] != 1 or body["method"] != "m1" or body["seed"] != 0 or body["config"] != ref.CONFIG:
        raise ValueError("source M1 artifact settings differ")
    backend = ref.ReferenceBackend("gpt-6-luna", budget=ref.Budget(max_calls=1, max_seconds=60), max_usd=1)
    model = RawHistory(backend, seed=0, **ref.CONFIG)
    by_id = {r.choice.identity: r.choice for r in records}
    split = manifest["users"][user]
    model.fit([by_id[i] for i in split["history"]], [by_id[i] for i in split["val"]])
    if asdict(model.artifacts()) != body["artifacts"] or body["backend"] != model.backend_identity or backend.budget.calls:
        raise ValueError("source artifact is not exact native history-only fit")
    return prior, records, manifest, body


def request_contract(proposal, row, guard, target_ids):
    selected = {}
    denied = guard["identity_denylists"]
    for arm in ("own", "wrong"):
        matches = [r for r in proposal["request_identity_metadata"] if r["user_id"] == row["target_user_id"] and r["arm"] == arm]
        if len(matches) != 1:
            raise ValueError("request identity panel differs")
        panel, = matches
        if (panel["targets"] != target_ids or len(panel["requests"]) != len(target_ids) or
                panel["donor_user_id"] != (row["target_user_id"] if arm == "own" else row["donor_user_id"])):
            raise ValueError("request target or source scope differs")
        for item in panel["requests"]:
            blocked = (item["endpoint_body_sha256"] in denied["endpoint_body_sorted_json_sha256"] or
                       item["body_compact_sha256"] in denied["body_compact_json_sha256"])
            if bool(item["blocked"]) != blocked:
                raise ValueError("current guard changes predeclared withholding")
        if sum(not r["blocked"] for r in panel["requests"]) != row["arms"][arm]["eligible_calls"]:
            raise ValueError("eligible request denominator differs")
        selected[arm] = panel
    return selected


def inspect_requests(source, targets):
    """Offline native constructor capture; accepts only label-free targets."""
    if any(set(t) != {"example_id", "context", "options"} for t in targets):
        raise ValueError("request inspection accepts only label-free target projections")
    backend = ControlBackend("gpt-6-luna", budget=ref.Budget(max_calls=len(targets) + 1, max_seconds=60),
                             max_usd=1, allowed_requests=())
    model = RawHistory(backend, seed=0, **ref.CONFIG)
    model._artifacts = TasteArtifacts(**copy.deepcopy(source["artifacts"]))
    captures = []
    def capture(prompt, system="", max_tokens=1024, temperature=0.0):
        instruction, payload_json = prompt.split("\nINPUT_JSON:\n", 1)
        payload = json.loads(payload_json)
        captures.append({"payload": payload, "payload_sha256": ref.digest(payload),
                         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                         "system_sha256": hashlib.sha256(system.encode()).hexdigest(),
                         "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
                         "body_compact_sha256": ref.body_identity(backend.model, prompt, system, max_tokens),
                         "endpoint_body_sha256": ref.wire_identity(backend.model, prompt, system, max_tokens),
                         "native_cache_key": ref.digest([model.backend_identity, model.prompt_version, system, prompt, temperature, max_tokens]),
                         "source_native_cache_key": ref.digest([source["backend"], model.prompt_version, system, prompt, temperature, max_tokens]),
                         "prompt_version": model.prompt_version, "backend_label": backend.label,
                         "endpoint": backend.base_url})
        return json.dumps({"probabilities": [0.5, 0.5]})
    backend.complete = capture
    for target in targets:
        model.predict(target["context"], target["options"])
    if backend.budget.calls or len(captures) != len(targets):
        raise ValueError("offline request construction differs")
    return captures


def verify_native_requests(panels, own, donor, targets):
    for arm, source in (("own", own), ("wrong", donor)):
        actual = inspect_requests(source, targets)
        expected = panels[arm]["requests"]
        if len(actual) != len(expected) or any(
                a[key] != b[key] for a, b in zip(actual, expected)
                for key in ("body_compact_sha256", "endpoint_body_sha256")):
            raise ValueError("native outgoing requests differ from frozen proposal")


def prepare(proposal_path, guard_path, user, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("private packet already exists")
    if ROOT == destination.resolve() or ROOT in destination.resolve().parents:
        raise ValueError("private packet must be outside the repository")
    proposal, row, donor = load_proposal(proposal_path, user)
    if ref.file_sha(guard_path) != GUARD_SHA:
        raise ValueError("reviewed current guard differs")
    guard = json.loads(Path(guard_path).read_text())
    own = source_input(row["target_plan"], row["own_artifact"], user)
    other = source_input(donor["target_plan"], row["donor_artifact"], row["donor_user_id"])
    records = [r for r in own[1] if r.choice.user_id == user]
    manifest = ref.build_manifest(records, 0)
    if manifest["users"][user] != own[2]["users"][user]:
        raise ValueError("derived recipient split differs")
    target_ids = manifest["users"][user]["test"]
    panels = request_contract(proposal, row, guard, target_ids)
    if any(len(value[3]["artifacts"]["exemplars"]) != row["selected_history_size"] for value in (own, other)):
        raise ValueError("history size differs")
    verify_native_requests(panels, own[3], other[3], target_projection(records, manifest, user))
    destination.mkdir(parents=True, mode=0o700)
    os.chmod(destination, 0o700)
    ref.copy_private(proposal_path, destination / "approved-proposal.json")
    ref.copy_private(guard_path, destination / "typed-denylist.json")
    for kind, entry, artifact in (("own", row, row["own_artifact"]), ("donor", donor, row["donor_artifact"])):
        source = Path(entry["target_plan"]["path"]).parent
        for name in ("plan.json", "records.jsonl", "manifest.json"):
            ref.copy_private(source / name, destination / (kind + "-source-" + name))
        ref.copy_private(artifact["path"], destination / (kind + "-artifact.json"))
    fd = os.open(str(destination / "records.jsonl"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        for record in records:
            stream.write(json.dumps(asdict(record), ensure_ascii=False, allow_nan=False) + "\n")
    ref.write_private(destination / "manifest.json", manifest)
    (destination / "cache").mkdir(mode=0o700)
    plan = {"protocol": PROTOCOL, "proposal_sha256": PROPOSAL_SHA, "runtime": runtime_identity(),
            "model": "gpt-6-luna", "backend": "openai", "reasoning": "none", "tools": False,
            "output_tokens": 2048, "timeout_seconds": 60, "seed": 0, "final": False, "user_partition": "dev",
            "user_ids": [user], "donor_user_id": row["donor_user_id"], "method_config": ref.CONFIG,
            "methods": [METHODS[a] for a in row["prospective_pair_order_if_authorized"]],
            "limits": limits(row), "deadline": ref.DEADLINE, "n_predictions": 2 * len(target_ids),
            "derived_manifest_id": manifest["manifest_id"], "parent64": proposal["parent64"],
            "request_panels": panels, "identity_denylists": guard["identity_denylists"],
            "fresh_response_cache": True, "source_fit_policy": "exact_saved_M1_history_no_refit",
            "snapshots": {p.name: ref.file_sha(p) for p in destination.iterdir() if p.is_file()}}
    ref.write_private(destination / "plan.json", plan)
    return destination / "plan.json"


def validate_execution(plan_path, lease_path, now=None):
    plan_path, lease_path = Path(plan_path), Path(lease_path)
    folder = plan_path.parent
    plan, lease = json.loads(plan_path.read_text()), json.loads(lease_path.read_text())
    now = time.time() if now is None else now
    user, = plan["user_ids"]
    proposal, row, donor = load_proposal(folder / "approved-proposal.json", user)
    expected = {"protocol": PROTOCOL, "proposal_sha256": PROPOSAL_SHA, "runtime": runtime_identity(),
                "model": "gpt-6-luna", "backend": "openai", "reasoning": "none", "tools": False,
                "output_tokens": 2048, "timeout_seconds": 60, "seed": 0, "final": False, "user_partition": "dev",
                "donor_user_id": row["donor_user_id"], "method_config": ref.CONFIG,
                "methods": [METHODS[a] for a in row["prospective_pair_order_if_authorized"]],
                "limits": limits(row), "deadline": ref.DEADLINE, "parent64": proposal["parent64"],
                "fresh_response_cache": True, "source_fit_policy": "exact_saved_M1_history_no_refit"}
    if any(plan.get(k) != value or type(plan.get(k)) is not type(value) for k, value in expected.items()):
        raise ValueError("control plan contract differs")
    snapshot_names = {"approved-proposal.json", "typed-denylist.json", "records.jsonl", "manifest.json"}
    snapshot_names |= {kind + "-source-" + name for kind in ("own", "donor") for name in ("plan.json", "records.jsonl", "manifest.json")}
    snapshot_names |= {"own-artifact.json", "donor-artifact.json"}
    if set(plan["snapshots"]) != snapshot_names or any(ref.file_sha(folder / name) != value for name, value in plan["snapshots"].items()):
        raise ValueError("packet snapshots differ")
    if plan["snapshots"]["typed-denylist.json"] != GUARD_SHA:
        raise ValueError("current guard differs")
    # Check copied sources against the proposal without reading mutable external bodies.
    source_results = []
    for kind, entry, artifact in (("own", row, row["own_artifact"]), ("donor", donor, row["donor_artifact"])):
        if (plan["snapshots"][kind + "-source-plan.json"] != entry["target_plan"]["sha256"] or
                plan["snapshots"][kind + "-artifact.json"] != artifact["sha256"]):
            raise ValueError("source artifact lineage differs")
        prior = json.loads((folder / (kind + "-source-plan.json")).read_text())
        for name in ("records.jsonl", "manifest.json"):
            if plan["snapshots"][kind + "-source-" + name] != prior["snapshots"][name]:
                raise ValueError("source record lineage differs")
        records = ref.load_records(folder / (kind + "-source-records.jsonl"))
        manifest = json.loads((folder / (kind + "-source-manifest.json")).read_text())
        if any(r.user_split != "dev" for r in records) or ref.build_manifest(records, 0) != manifest:
            raise ValueError("source development split differs")
        source_results.append((records, manifest))
    records = ref.load_records(folder / "records.jsonl")
    manifest = json.loads((folder / "manifest.json").read_text())
    if (any(r.user_split != "dev" for r in records) or ref.build_manifest(records, 0) != manifest or
            set(manifest["users"]) != {user} or manifest["manifest_id"] != plan["derived_manifest_id"] or
            manifest["users"][user] != source_results[0][1]["users"][user] or
            records != [r for r in source_results[0][0] if r.choice.user_id == user]):
        raise ValueError("recipient scope or records differ")
    targets = manifest["users"][user]["test"]
    guard = json.loads((folder / "typed-denylist.json").read_text())
    if (plan["request_panels"] != request_contract(proposal, row, guard, targets) or
            plan["identity_denylists"] != guard["identity_denylists"] or plan["n_predictions"] != 2 * len(targets)):
        raise ValueError("request scope or full denominator differs")
    verify_native_requests(plan["request_panels"],
                           json.loads((folder / "own-artifact.json").read_text()),
                           json.loads((folder / "donor-artifact.json").read_text()),
                           target_projection(records, manifest, user))
    if not (folder / "cache").is_dir() or list((folder / "cache").iterdir()):
        raise ValueError("fresh response cache required")
    required = {"role": "10", "state": "authorized", "provider": "openai", "model": "gpt-6-luna",
                "final_authorized": False, "user_partition": "dev", "protocol": PROTOCOL,
                "methods": plan["methods"], "plan_sha256": ref.file_sha(plan_path),
                "known_valid_input_replication_authorized": True}
    if any(lease.get(k) != v or type(lease.get(k)) is not type(v) for k, v in required.items()):
        raise ValueError("lease does not authorize exact prospective replication")
    if not isinstance(lease.get("job_id"), str) or not lease["job_id"].strip():
        raise ValueError("lease job id required")
    for k, maximum in plan["limits"].items():
        value = lease.get(k)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError("invalid lease limit")
    if type(lease["max_calls"]) is not int:
        raise ValueError("integral call limit required")
    deadline = ref.timestamp(lease["deadline"])
    if deadline > ref.timestamp(ref.DEADLINE) or now >= deadline:
        raise ValueError("lease deadline expired or extended")
    claim = Path(lease.get("claim_path", ""))
    if (not claim.is_absolute() or not claim.parent.is_dir() or folder.resolve() in claim.resolve().parents or
            claim.exists() or any((folder / p).exists() for p in ("LAUNCH_USED.json", "output", "completion.json"))):
        raise ValueError("fresh external claim and packet required")
    return plan, lease, records, deadline


def target_projection(records, manifest, user):
    by_id = {r.choice.identity: r.choice for r in records}
    return [{"example_id": ident, "context": by_id[ident].context,
             "options": [by_id[ident].a_text, by_id[ident].b_text]}
            for ident in manifest["users"][user]["test"]]


def execute(plan_path, lease_path):
    plan_path, lease_path = Path(plan_path), Path(lease_path)
    plan, lease, records, deadline = validate_execution(plan_path, lease_path)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OpenAI credential environment required")
    folder = plan_path.parent
    ref.claim_lease(plan_path, lease_path, lease)
    budget = ref.Budget(max_calls=lease["max_calls"], max_seconds=min(lease["max_seconds"], deadline - time.time()))
    allowed = {r["endpoint_body_sha256"] for panel in plan["request_panels"].values() for r in panel["requests"] if not r["blocked"]}
    backend = ControlBackend("gpt-6-luna", budget=budget, max_usd=lease["max_usd"], timeout=60,
                             allowed_requests=allowed, enforce_unique_requests=True,
                             forbidden_wire_hashes=plan["identity_denylists"]["endpoint_body_sorted_json_sha256"],
                             forbidden_body_hashes=plan["identity_denylists"]["body_compact_json_sha256"])
    user, = plan["user_ids"]
    manifest = json.loads((folder / "manifest.json").read_text())
    split = manifest["users"][user]
    projection = target_projection(records, manifest, user)
    def factory(method):
        arm = next(a for a, m in METHODS.items() if m == method)
        source = json.loads((folder / (("own" if arm == "own" else "donor") + "-artifact.json")).read_text())
        panel = plan["request_panels"][arm]
        withheld = [i for i, r in zip(panel["targets"], panel["requests"]) if r["blocked"]]
        return FrozenHistory(backend, source=source, history_ids=split["history"], validation_ids=split["val"],
                             targets=projection, withheld_ids=withheld, seed=0, cache_dir=folder / "cache",
                             max_calls=lease["max_calls"], **ref.CONFIG)
    mask = os.umask(0o077)
    try:
        report = ref.run_fidelity(records, folder / "manifest.json",
                                  {m: lambda u, method=m: factory(method) for m in plan["methods"]},
                                  folder / "output", "prism", users="dev", seed=0,
                                  run_config={"protocol": PROTOCOL, "plan_sha256": ref.file_sha(plan_path),
                                              "donor_user_id": plan["donor_user_id"], "fresh_response_cache": True,
                                              "source_fit_policy": plan["source_fit_policy"]})
        ref.write_private(folder / "completion.json", {
            "job_id": lease["job_id"], "completed": time.time(), "attempts": getattr(budget, "_taste_attempts", 0),
            "backend_calls": budget.calls, "budgets": [backend.cost_summary()],
            "report_sha256": ref.file_sha(folder / "output/report.json"),
            "predictions_sha256": ref.file_sha(folder / "output/predictions.jsonl"),
            "request_audit": backend.request_audit, "historical_guard_denials": backend.guard_denials,
            "failures": {m: report["methods"][m]["failures"] for m in plan["methods"]},
            "prospective_replication": True, "imported_response_cache_entries": 0,
            "new_response_cache_entries": len(list((folder / "cache").glob("*.json")))})
    finally:
        os.umask(mask)
    return folder / "output/report.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for flag in ("proposal", "guard", "user", "destination"):
        prep.add_argument("--" + flag, required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.add_argument("--lease", required=True)
    args = parser.parse_args()
    path = prepare(args.proposal, args.guard, args.user, args.destination) if args.command == "prepare" else execute(args.plan, args.lease)
    print(json.dumps({"path": str(path), "sha256": ref.file_sha(path)}))


if __name__ == "__main__":
    main()
