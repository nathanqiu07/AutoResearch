#!/usr/bin/env python3
"""Two assigned neutral API-access probes; no research inputs, retries or scoring."""
import argparse
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

PROMPT = 'Return exactly this JSON object and no other text: {"probe":"ok"}'
SETTINGS = {"reasoning": "medium", "max_tokens": 8192, "timeout": 180}
MODELS = ["gpt-6-sol", "gpt-6-astra"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest(value):
    return text_sha(canonical(value))


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone_required")
    return result


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (canonical(data) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def outside(path, root):
    if Path(path).resolve() == Path(root).resolve() or Path(root).resolve() in Path(path).resolve().parents:
        raise ValueError("cannot_mutate_frozen_runtime")


def validate(dispatch):
    if dispatch.get("schema_version") != "neutral-api-probe-dispatch-v1" or dispatch.get("script_sha256") != file_sha(__file__):
        raise ValueError("dispatch_or_script_pin_mismatch")
    if dispatch.get("settings") != SETTINGS or type(dispatch.get("max_calls")) is not int or dispatch["max_calls"] != 2:
        raise ValueError("probe_settings_mismatch")
    if not dispatch.get("authorization_source") or not dispatch.get("campaign_id"):
        raise ValueError("explicit_assignment_required")
    maximum = Decimal(str(dispatch["max_usd"]))
    if not maximum.is_finite() or not Decimal("0.625") <= maximum <= Decimal("1"):
        raise ValueError("invalid_probe_allocation")
    probes = dispatch["probes"]
    if (not isinstance(probes, list) or [p.get("model") for p in probes] != MODELS
            or [Decimal(str(p["max_usd"])) for p in probes] != [Decimal("0.125"), Decimal("0.5")]):
        raise ValueError("assigned_panel_or_suballocation_mismatch")
    seconds = dispatch["max_seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 0 < seconds <= 400:
        raise ValueError("invalid_wall_time_allocation")
    if timestamp(dispatch["deadline"]) <= datetime.now(timezone.utc):
        raise ValueError("probe_deadline_reached")
    ref = dispatch["policy"]
    if file_sha(ref["path"]) != ref["sha256"]:
        raise ValueError("shared_policy_hash_mismatch")
    policy = json.loads(Path(ref["path"]).read_bytes())
    if policy.get("schema_version") != "phase2-ledger-policy-v1" or policy["ledger"]["max_inflight"] != 2:
        raise ValueError("shared_policy_schema_mismatch")
    if timestamp(dispatch["deadline"]) > timestamp(policy["deadline"]):
        raise ValueError("probe_exceeds_campaign_deadline")
    if not Path(policy["ledger"]["path"]).is_file():
        raise ValueError("existing_shared_ledger_required")
    for path in (dispatch["claims_root"], dispatch["output_root"], policy["ledger"]["path"]):
        outside(path, dispatch["runtime_root"])
    return policy


def load_runtime(dispatch):
    root = Path(dispatch["runtime_root"]).resolve()
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()
    if Path(git("rev-parse", "--show-toplevel")).resolve() != root or git("rev-parse", "HEAD") != dispatch["runtime_commit"]:
        raise ValueError("native_runtime_commit_mismatch")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("native_runtime_has_tracked_edits")
    target = root / "autoresearch/taste/overnight/backends.py"
    if file_sha(target) != dispatch["runtime_backend_sha256"]:
        raise ValueError("runtime_backend_hash_mismatch")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root)); importlib.invalidate_caches()
    backend = importlib.import_module("autoresearch.taste.overnight.backends")
    llm = importlib.import_module("autoresearch.llm")
    if Path(backend.__file__).resolve() != target or Path(llm.__file__).resolve() != root / "autoresearch/llm.py":
        raise ValueError("runtime_import_origin_mismatch")
    return backend, llm.Budget


def run_probe(dispatch, backend_module, budget_class):
    """Injected module is for offline tests; production main verifies native pins."""
    dispatch = json.loads(canonical(dispatch))
    policy = validate(dispatch)
    if policy["pricing_version"] != backend_module.PRICING_VERSION:
        raise ValueError("runtime_policy_pricing_mismatch")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("credential_environment_required")
    claim_id = digest({"campaign_id": dispatch["campaign_id"], "policy_sha256": dispatch["policy"]["sha256"],
                       "models": MODELS, "settings": SETTINGS, "prompt_sha256": text_sha(PROMPT)})
    write_new(Path(dispatch["claims_root"]) / (claim_id + ".json"),
              {"dispatch_sha256": digest(dispatch), "status": "claimed", "script_sha256": dispatch["script_sha256"]})
    output = Path(dispatch["output_root"]); output.mkdir(parents=True, exist_ok=False)
    ledger = backend_module.DollarLedger(policy["ledger"]["path"], max_usd=policy["ledger"]["max_usd"],
                                         deadline=policy["deadline"], max_inflight=2)
    result = {"schema_version": "neutral-api-probe-result-v1", "status": "complete", "dispatch_sha256": digest(dispatch),
              "script_sha256": dispatch["script_sha256"], "runtime_commit": dispatch["runtime_commit"],
              "runtime_backend_sha256": dispatch["runtime_backend_sha256"], "policy_sha256": dispatch["policy"]["sha256"],
              "evidence_status": "neutral_api_access_only_not_research_score", "calls": [{"model": m, "status": "not_started"} for m in MODELS]}
    start = time.monotonic()
    for number, assignment in enumerate(dispatch["probes"]):
        row = result["calls"][number]
        remaining = min(dispatch["max_seconds"] - (time.monotonic() - start),
                        (timestamp(dispatch["deadline"]) - datetime.now(timezone.utc)).total_seconds())
        if remaining <= 0:
            row.update(status="blocked", error_code="deadline_reached"); result["status"] = "partial"; break
        backend = backend_module.OpenAIResponsesBackend(model=assignment["model"], reasoning="medium", ledger=ledger,
            max_usd=assignment["max_usd"], timeout=180, budget=budget_class(max_calls=1, max_seconds=remaining,
                                                                         max_cost_usd=float(assignment["max_usd"])))
        actual = {"model": assignment["model"], "enforced_settings": backend.enforced_settings,
                  "max_tokens": 8192, "temperature": 0.0, "timeout_cap_seconds": 180}
        row.update(settings=actual, settings_sha256=digest(actual), prompt_sha256=text_sha(PROMPT), system_sha256=text_sha(""))
        write_new(output / ("%02d-started.json" % number), dict(row, status="started", neutral_prompt=PROMPT))
        stop = False
        try:
            response = backend.complete(PROMPT, system="", max_tokens=8192, temperature=0.0)
            normalized = response.strip()
            row.update(response_sha256=text_sha(response), normalized_response=normalized,
                       normalized_response_sha256=text_sha(normalized))
            # Require exactly the requested object; alternative JSON/spelling is a known invalid probe.
            if normalized == '{"probe":"ok"}':
                row["status"] = "complete"
            else:
                row.update(status="completed_call_invalid_probe", error_code="exact_probe_response_mismatch")
                result["status"] = "partial"
        except Exception:
            row.update(status="unavailable", error_code="backend_failed_no_retry")
            result["status"], stop = "partial", True
        row["cost"] = backend.cost_summary()
        try:
            write_new(output / ("%02d-result.json" % number), row)
        except Exception:
            row.update(status="artifact_failed", error_code="local_evidence_write_failed")
            result["status"], stop = "partial", True
        if stop:
            break
    result["campaign_ledger"] = ledger.summary()
    result["attempted_calls"] = sum(row.get("cost", {}).get("attempted_calls", 0) for row in result["calls"])
    result["known_usage_usd"] = str(sum(Decimal(str(row.get("cost", {}).get("spent_usd", 0))) for row in result["calls"]))
    result["reserved_usd"] = str(sum(Decimal(str(row.get("cost", {}).get("reserved_usd", 0))) for row in result["calls"]))
    write_new(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", type=Path, required=True)
    parser.add_argument("--expected-dispatch-sha256", required=True)
    args = parser.parse_args()
    try:
        if file_sha(args.dispatch) != args.expected_dispatch_sha256:
            raise ValueError("dispatch_file_hash_mismatch")
        dispatch = json.loads(args.dispatch.read_bytes())
        validate(dispatch)
        backend, budget_class = load_runtime(dispatch)
        result = run_probe(dispatch, backend, budget_class)
        print(canonical({"status": result["status"], "attempted_calls": result["attempted_calls"],
                         "summary_sha256": file_sha(Path(dispatch["output_root"]) / "summary.json")}))
        return 0 if result["status"] == "complete" else 2
    except Exception:
        print(canonical({"status": "failed", "error_code": "probe_preflight_or_local_failure_no_retry"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
