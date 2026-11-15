#!/usr/bin/env python3
"""Read-only reconciliation of phase1 old-price usage; never reset a ledger."""
import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

OLD_PRICING = "openai-standard-short-context-2026-11-15"
# Exact nanodollars per token; no floating point in reconciliation arithmetic.
RATES = {"gpt-6-luna": (100, 500), "gpt-6-sol": (2000, 10000), "gpt-6-astra": (10000, 50000)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def nanos(value):
    number = Decimal(str(value)) * 1_000_000_000
    if isinstance(value, bool) or not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError("invalid_exact_dollars")
    return int(number)


def dollars(value):
    return format(Decimal(value) / 1_000_000_000, ".9f")


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid_usage_count")
    return value


def load(ref, evidence):
    path = Path(ref["path"]).resolve()
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != ref["sha256"]:
        raise ValueError("evidence_file_hash_mismatch")
    evidence.append({"path": str(path), "sha256": sha})
    return json.loads(raw)


def snapshot(path):
    # mode=ro refuses a missing DB and cannot change balances/schema/policy.
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        policies = conn.execute("SELECT id,body FROM policy ORDER BY id").fetchall()
        rows = conn.execute("SELECT id,reserved,actual,status,metadata FROM reservations ORDER BY id").fetchall()
        conn.commit()
    finally:
        conn.close()
    if len(policies) != 1 or policies[0][0] != 1:
        raise ValueError("invalid_ledger_policy")
    policy = json.loads(policies[0][1])
    if policy.get("pricing_version") != OLD_PRICING:
        raise ValueError("not_phase1_pricing_policy")
    for row in rows:
        count(row[1]); count(row[2])
        if row[3] not in {"pending", "uncertain", "complete"}:
            raise ValueError("unknown_ledger_status")
    return policy, rows, digest({"policy_rows": policies, "reservation_rows": rows})


def reconcile(manifest, *, finalize=False):
    manifest = json.loads(canonical(manifest))
    if manifest.get("schema_version") != "phase1-accounting-dispatch-v1":
        raise ValueError("unsupported_dispatch_schema")
    if nanos(manifest["profile_allocation_usd"]) != 200_000_000_000 or nanos(manifest["prior_outside_ledger_usd"]) != 17_601_625:
        raise ValueError("unexpected_campaign_allocation")
    policy, rows, ledger_hash = snapshot(manifest["ledger_path"])
    evidence, unresolved, seen_jobs, requests = [], [], set(), Counter()
    totals = {model: {"input_tokens": 0, "output_tokens": 0, "attempts": 0} for model in RATES}
    for index_ref in manifest["indices"]:
        index = load(index_ref, evidence)
        if index.get("schema_version") != "pilot-completion-index-v1":
            raise ValueError("unsupported_completion_index")
        for batch in index["batches"]:
            for job in batch["jobs"]:
                job_id = job["job_id"]
                if job_id in seen_jobs:
                    raise ValueError("duplicate_job_evidence")
                seen_jobs.add(job_id)
                result = load(job["result"], evidence)
                if (result.get("schema_version") != "overnight-result-v1" or result.get("job_id") != job_id
                        or result.get("manifest_hash") != job["manifest_sha256"] or result.get("usage") != job["usage"]):
                    raise ValueError("result_index_binding_mismatch")
                usage, backend = result["usage"], result["actual_backend"]
                detail, model = usage["budget_detail"], backend["model"]
                if model not in RATES or detail.get("model") != model:
                    raise ValueError("unsupported_usage_model")
                settings = backend["enforced_settings"]
                if (settings.get("pricing_version") != OLD_PRICING or settings.get("store") is not False
                        or settings.get("service_tier") != "default" or settings.get("prompt_cache_options") is not None):
                    raise ValueError("unsupported_phase1_backend_settings")
                attempts = count(usage["attempted_calls"])
                inp, out = count(detail["known_input_tokens"]), count(detail["known_output_tokens"])
                if (detail.get("reported_usage_complete") is not True or detail.get("unknown_input_usage_attempts") != 0
                        or detail.get("unknown_output_usage_attempts") != 0 or usage.get("uncertain_attempts") != 0
                        or usage.get("input_tokens") != inp or usage.get("output_tokens") != out):
                    unresolved.append("incomplete_usage:" + job_id)
                if detail.get("attempted_calls") != attempts:
                    unresolved.append("attempt_count_mismatch:" + job_id)
                expected_cost = inp * RATES[model][0] + out * RATES[model][1]
                if nanos(detail["spent_usd"]) != expected_cost or nanos(usage["reported_api_usd"]) != expected_cost:
                    unresolved.append("reported_cost_mismatch:" + job_id)
                if nanos(detail["reserved_usd"]) or nanos(usage["reserved_api_usd"]):
                    unresolved.append("usage_has_hold:" + job_id)
                totals[model]["input_tokens"] += inp
                totals[model]["output_tokens"] += out
                totals[model]["attempts"] += attempts
                for attempt in range(1, attempts + 1):
                    path = Path(job["result"]["path"]).parent / "traces" / ("%04d-started.json" % attempt)
                    raw = path.read_bytes()
                    sha = hashlib.sha256(raw).hexdigest()
                    if sha not in result["trace_hashes"]:
                        raise ValueError("trace_hash_mismatch")
                    evidence.append({"path": str(path.resolve()), "sha256": sha})
                    trace = json.loads(raw)
                    if trace.get("status") != "started" or trace.get("attempt") != attempt or trace.get("backend") != backend:
                        raise ValueError("trace_backend_binding_mismatch")
                    args = trace["settings"]
                    if set(args) - {"system", "temperature", "max_tokens"} or not isinstance(trace["prompt"], str):
                        raise ValueError("unsupported_trace_settings")
                    # Reconstruct the pinned phase1 wire body, without outputting its text.
                    body = {"model": model, "instructions": args.get("system", ""), "input": trace["prompt"],
                            "max_output_tokens": args["max_tokens"], "reasoning": {"effort": settings["reasoning_effort"]},
                            "store": False, "service_tier": "default"}
                    requests[(model, settings["reasoning_effort"], digest(body))] += 1

    embedding_expected, embedding_tokens, embedding_cost = {}, 0, 0
    for ref in manifest["embedding_summaries"]:
        summary = load(ref, evidence)
        if summary.get("schema_version") != "bounded-embedding-result-v1" or summary.get("model") != "text-embedding-3-small":
            raise ValueError("unsupported_embedding_summary")
        if summary.get("status") != "complete" or nanos(summary["reserved_usd"]):
            unresolved.append("embedding_summary_incomplete")
        subtotal = 0
        for entry in summary["requests"]:
            key = (entry["request_id"], entry["input_sha256"], entry["packet_sha256"])
            if key in embedding_expected:
                raise ValueError("duplicate_embedding_evidence")
            receipt = load({"path": entry["receipt_path"], "sha256": entry["receipt_sha256"]}, evidence)
            if (receipt.get("schema_version") != "bounded-embedding-receipt-v1" or receipt.get("model") != "text-embedding-3-small"
                    or receipt.get("dimensions") != 1536 or receipt.get("status") != "complete"
                    or any(receipt.get(k) != entry.get(k) for k in ("request_id", "input_sha256", "packet_sha256", "response_sha256", "usage"))):
                raise ValueError("embedding_receipt_binding_mismatch")
            usage = receipt["usage"]
            tokens = count(usage["known_input_tokens"])
            if usage.get("complete") is not True or usage.get("prompt_tokens") != tokens or usage.get("total_tokens") != tokens:
                unresolved.append("embedding_usage_incomplete:" + entry["request_id"])
            cost = tokens * 20
            if nanos(receipt["known_usage_usd"]) != cost or nanos(entry["known_usage_usd"]) != cost:
                unresolved.append("embedding_cost_mismatch:" + entry["request_id"])
            embedding_expected[key] = cost
            embedding_tokens += tokens
            subtotal += cost
        if summary.get("attempted_calls") != len(summary["requests"]) or nanos(summary["known_usage_usd"]) != subtotal:
            unresolved.append("embedding_summary_count_or_cost_mismatch")
        embedding_cost += subtotal

    ledger_requests, ledger_models, embedding_seen = Counter(), {m: {"attempts": 0, "actual": 0} for m in RATES}, set()
    for reservation_id, reserved, actual, status, metadata_raw in rows:
        meta = json.loads(metadata_raw)
        model = meta.get("model")
        if model in RATES:
            ledger_requests[(model, meta.get("reasoning"), meta.get("request_sha256"))] += 1
            ledger_models[model]["attempts"] += 1
            ledger_models[model]["actual"] += actual
        elif meta.get("producer") == "bounded-embeddings-v1":
            key = (meta.get("request_id"), meta.get("input_sha256"), meta.get("packet_sha256"))
            if key in embedding_seen or key not in embedding_expected or actual != embedding_expected[key]:
                unresolved.append("embedding_ledger_mismatch:" + reservation_id)
            embedding_seen.add(key)
        else:
            unresolved.append("unknown_ledger_reservation:" + reservation_id)
    if ledger_requests != requests:
        unresolved.append("request_identity_or_multiplicity_mismatch")
    if embedding_seen != set(embedding_expected):
        unresolved.append("embedding_ledger_coverage_mismatch")
    delta, expected_total = 0, embedding_cost
    for model, total in totals.items():
        old_cost = total["input_tokens"] * RATES[model][0] + total["output_tokens"] * RATES[model][1]
        adjustment = total["input_tokens"] * RATES[model][0] // 4
        if old_cost != ledger_models[model]["actual"]:
            unresolved.append("model_cost_mismatch:" + model)
        if total["attempts"] != ledger_models[model]["attempts"]:
            unresolved.append("model_attempt_mismatch:" + model)
        total.update(old_cost_usd=dollars(old_cost), input_adjustment_usd=dollars(adjustment),
                     conservative_upper_usd=dollars(old_cost + adjustment))
        delta += adjustment
        expected_total += old_cost
    pending = sum(row[3] == "pending" for row in rows)
    uncertain = sum(row[3] == "uncertain" for row in rows)
    spent = sum(row[2] for row in rows)
    holds = sum(row[1] for row in rows if row[3] != "complete")
    if pending or uncertain or holds:
        unresolved.append("ledger_has_pending_or_uncertain_holds")
    if spent != expected_total:
        unresolved.append("aggregate_cost_mismatch")
    cap = 200_000_000_000 - 17_601_625 - spent - delta
    if cap < 0:
        unresolved.append("campaign_allocation_exhausted")
    if finalize:
        closure = manifest.get("closure", {})
        if closure.get("all_jobs_done") is not True or not isinstance(closure.get("authority"), str) or not closure["authority"].strip():
            raise ValueError("closure_authority_required")
        if closure.get("ledger_snapshot_sha256") != ledger_hash:
            raise ValueError("closure_snapshot_mismatch")
        if unresolved:
            raise ValueError("closure_unresolved_usage_or_holds")
        if snapshot(manifest["ledger_path"])[2] != ledger_hash:
            raise ValueError("closure_snapshot_changed_during_verification")
    return {"schema_version": "phase1-accounting-receipt-v1", "status": "closed" if finalize else
            ("unresolved" if unresolved else "ready_for_coordinator_close"), "dispatch_sha256": digest(manifest),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "ledger": {"path": str(Path(manifest["ledger_path"]).resolve()), "snapshot_sha256": ledger_hash,
                       "policy_sha256": digest(policy), "pricing_version": policy["pricing_version"], "attempts": len(rows),
                       "pending": pending, "uncertain": uncertain, "reserved_usd": dollars(holds), "recorded_spent_usd": dollars(spent)},
            "per_model": totals, "embeddings": {"attempts": len(embedding_expected), "input_tokens": embedding_tokens,
                       "old_cost_usd": dollars(embedding_cost), "input_adjustment_usd": "0.000000000"},
            "known_input_adjustment_usd": dollars(delta), "phase1_conservative_upper_usd": None if unresolved else dollars(spent + delta),
            "prior_outside_ledger_usd": "0.017601625", "profile_allocation_usd": "200.000000000",
            "provisional_phase2_cap_usd": None if unresolved else dollars(cap),
            "phase2_cap_usd": dollars(cap) if finalize else None, "closure": manifest.get("closure") if finalize else None,
            "unresolved": sorted(set(unresolved)), "evidence": evidence,
            "cost_basis": "phase1_recorded_cost_plus_25_percent_base_input_upper_adjustment_embeddings_unchanged_not_invoice"}


def write_receipt(path, report):
    raw = (canonical(report) + "\n").encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", required=True, type=Path)
    parser.add_argument("--expected-dispatch-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    try:
        dispatch = load({"path": str(args.dispatch), "sha256": args.expected_dispatch_sha256}, [])
        report = reconcile(dispatch, finalize=args.final)
        sha = write_receipt(args.output, report)
        print(canonical({"status": report["status"], "receipt_sha256": sha, "unresolved_count": len(report["unresolved"])}))
        return 2 if report["unresolved"] else 0
    except Exception as exc:
        # Only our fixed error code is exposed; paths/source contents are never printed.
        code = str(exc) if isinstance(exc, ValueError) and str(exc).replace("_", "").isalnum() else "accounting_failed"
        print(canonical({"status": "failed", "error_code": code}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
