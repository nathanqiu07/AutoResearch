#!/usr/bin/env python3
"""Synthetic real-runner/API unknown-outcome audit. No network or real env reads.

Run: python3 reproduce.py --source-root SNAPSHOT --out NEW_OUTPUT_DIRECTORY
The parent starts a fresh interpreter with an explicit synthetic environment.
Source files are read only, and Python bytecode writes are disabled.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import urllib.request
from unittest.mock import patch

OLD_BACKEND_SHA = "b3b163e07365937fee4d7f1bde76fe8cc84181cbe8c07462f2cb927295f319b7"
DEADLINE = "2099-01-01T00:00:00+00:00"
KEY = "synthetic-key-not-a-real-credential"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def denied(*args, **kwargs):
    raise RuntimeError("NETWORK_DISABLED_BY_INDEPENDENT_AUDIT")


def worker(source, out):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    # Installed before imports or backend construction; fake transport overrides
    # urlopen only inside each case. Socket calls always remain disabled.
    socket.socket.connect = denied
    socket.create_connection = denied
    urllib.request.urlopen = denied
    from autoresearch.llm import Budget
    from autoresearch.taste.overnight import backends as b, runner
    from autoresearch.taste.overnight.contracts import backend_identity, digest
    from tests.test_overnight_contracts import ContractTests

    metadata = json.loads((source / "AUDIT_SOURCE.json").read_text())
    hashes_before = {name: sha(source / name) for name in metadata["files"]}
    if hashes_before != metadata["files"]:
        raise RuntimeError("source manifest mismatch before audit")
    backend_sha = sha(Path(b.__file__))
    checks, observations = [], []

    def check(name, ok, evidence, category="execution_boundary"):
        checks.append({"name": name, "status": "verified" if ok else "failed",
                       "category": category, "evidence": evidence})

    # Existing public synthetic fixture builder; no researcher data or labels.
    fixture = ContractTests()
    fixture.setUp()
    profile = fixture.build()
    config = fixture.prediction_config(profile)
    cases = [
        ("completed_control", {"input_tokens": 100, "output_tokens": 20}, "completed", False),
        ("missing_usage", None, "completed", False),
        ("input_only", {"input_tokens": 100}, "completed", False),
        ("output_only", {"output_tokens": 20}, "completed", False),
        ("input_valid_output_bool", {"input_tokens": 100, "output_tokens": True}, "completed", False),
        ("incomplete_known_usage", {"input_tokens": 100, "output_tokens": 20}, "incomplete", False),
        ("transport_exception", None, None, True),
    ]
    for name, usage, status, transport_error in cases:
        folder = out / "cases" / name
        folder.mkdir(parents=True)
        requests = []
        response = {"status": status, "output": [{"type": "message", "role": "assistant", "status": "completed",
                     "content": [{"type": "output_text", "text": '{"probabilities":[0.25,0.75]}'}]}]}
        if usage is not None:
            response["usage"] = usage
        save(folder / "synthetic-response.json", {"raises_synthetic_exception": transport_error, "response": response})

        def fake_transport(request, timeout):
            body = json.loads(request.data)
            requests.append({"body": body, "url": request.full_url, "timeout": timeout,
                             "synthetic_authorization": request.get_header("Authorization") == "Bearer " + KEY,
                             "reservation_at_send": ledger.summary()})
            if transport_error:
                raise RuntimeError("SYNTHETIC_TRANSPORT_ERROR_CANARY")
            return io.BytesIO(json.dumps(response).encode())

        ledger = b.DollarLedger(folder / "ledger.sqlite3", max_usd=.2, deadline=DEADLINE, max_inflight=2)
        def backend():
            return b.OpenAIResponsesBackend(model="gpt-6-sol", reasoning="medium", ledger=ledger,
                    max_usd=.1, budget=Budget(max_calls=4, max_seconds=60, max_cost_usd=.1), timeout=1)

        def run(consumer, tag):
            items = [{"item_id": tag + "-" + str(i), "researcher_id": "synthetic", "context": "synthetic question " + str(i),
                      "options": ["left", "right"], "option_order_id": "ab"} for i in (1, 2)]
            manifest = {"schema_version": "overnight-job-v1", "campaign_id": "synthetic-runner-api-audit",
                        "stage": "dev", "kind": "predict", "contract_sha256": "c" * 64,
                        "config_hash": digest(config), "source_manifest_hash": profile.allowed_source_manifest_hash,
                        "items_hash": digest(items), "profile_hash": profile.profile_id,
                        "method_id": profile.method_id, "extractor": profile.extractor,
                        "consumer": backend_identity(consumer), "personalization_cap": profile.personalization_cap,
                        "option_order_schedule": [{"item_id": i["item_id"], "option_order_id": i["option_order_id"]} for i in items],
                        "replicate_id": 0, "code_sha": metadata["implementation_commit"], "deadline": DEADLINE,
                        "allocation": {"max_calls": 4, "max_seconds": 60, "max_usd": .1,
                                       "cost_mode": "priced_api", "authorization_source": "synthetic transport audit only"},
                        "retry_policy": {"max_attempts": 1, "retry_uncertain": False},
                        "parent_job_ids": [], "expected_outputs": ["result.json", "traces"]}
            manifest["job_id"] = runner.job_id(manifest)
            lease = {"job_id": manifest["job_id"], "lease_id": "synthetic-lease", "owner": "independent-audit", "expires_at": DEADLINE}
            kwargs = dict(output_root=folder / "outputs", lease_root=folder / "leases", cache_root=folder / "cache",
                          profile=profile, items=items, config=config, consumer=consumer)
            result = runner.run_job(manifest, lease, **kwargs)
            duplicate = None
            try:
                runner.run_job(manifest, lease, **kwargs)
            except Exception as exc:
                duplicate = type(exc).__name__
            return result, duplicate

        # Replaces backend module's os reference, never reads actual os.environ.
        with patch.object(b, "os", SimpleNamespace(environ={"OPENAI_API_KEY": KEY})), \
             patch.object(b.urllib.request, "urlopen", side_effect=fake_transport):
            consumer = backend()
            result, duplicate = run(consumer, "initial")
            initial_cost = consumer.cost_summary()
            initial_ledger = ledger.summary()
            physical_initial = len(requests)
            fresh_result = None
            if name != "completed_control":
                fresh = backend()
                fresh_result, fresh_duplicate = run(fresh, "fresh-job")
            physical_final = len(requests)

        success = name == "completed_control"
        traces = [json.loads(p.read_text()) for p in sorted((folder / "outputs" / result["job_id"] / "traces").glob("*.json"))]
        db = sqlite3.connect(folder / "ledger.sqlite3")
        rows = [dict(zip(("reserved_nanos", "actual_nanos", "status", "metadata"), r))
                for r in db.execute("SELECT reserved, actual, status, metadata FROM reservations")]
        db.close()
        inp_known = isinstance((usage or {}).get("input_tokens"), int) and not isinstance((usage or {}).get("input_tokens"), bool)
        out_known = isinstance((usage or {}).get("output_tokens"), int) and not isinstance((usage or {}).get("output_tokens"), bool)
        expected_input = usage["input_tokens"] if inp_known else None
        expected_output = usage["output_tokens"] if out_known else None
        multiplier = 2 if success else 1
        expected_known_cost = multiplier * ((expected_input or 0) * 2 + (expected_output or 0) * 10) / 1_000_000
        identity = result["actual_backend"]
        check(name + ":identity_and_request", identity == backend_identity(consumer) and
              all(p["actual_consumer"] == identity for p in result["predictions"]) and
              all(r["body"]["model"] == "gpt-6-sol" and r["body"]["reasoning"] == {"effort": "medium"} and
                  r["body"]["max_output_tokens"] == 128 and r["body"]["store"] is False and
                  r["body"]["service_tier"] == "default" and "temperature" not in r["body"] and
                  "tools" not in r["body"] and r["synthetic_authorization"] for r in requests),
              {"actual_backend": identity, "physical_requests": len(requests)})
        check(name + ":durable_no_retry", duplicate == "FileExistsError" and physical_initial == multiplier and physical_final == multiplier,
              {"duplicate_claim_error": duplicate, "physical_initial": physical_initial, "physical_final": physical_final})
        check(name + ":counts", result["counts"] == {"attempted": 2, "complete": 2 if success else 0, "error": 0 if success else 2} and
              result["usage"]["attempted_calls"] == multiplier and result["usage"]["uncertain_attempts"] == (0 if success else 1) and
              initial_cost["attempted_calls"] == multiplier and initial_ledger["attempts"] == multiplier,
              {"counts": result["counts"], "gate_attempts": result["usage"]["attempted_calls"], "backend_attempts": initial_cost["attempted_calls"], "ledger_attempts": initial_ledger["attempts"]})
        check(name + ":usage_components", result["usage"]["input_tokens"] == (expected_input * multiplier if inp_known else None) and
              result["usage"]["output_tokens"] == (expected_output * multiplier if out_known else None) and
              abs(result["usage"]["reported_api_usd"] - expected_known_cost) < 1e-12,
              {"expected_input": expected_input, "expected_output": expected_output, "multiplier": multiplier,
               "expected_known_cost": expected_known_cost, "actual_usage": result["usage"]}, "usage_reporting")
        if success:
            check(name + ":settled_control", result["status"] == "complete" and initial_ledger["reserved_usd"] == 0 and
                  initial_ledger["uncertain"] == 0 and all(r["status"] == "complete" for r in rows), initial_ledger)
        else:
            codes = [p["error_code"] for p in result["predictions"]]
            check(name + ":uncertain_halt", result["status"] == "partial" and codes == ["backend_failed_usage_uncertain", "lane_held_after_uncertain_attempt"] and
                  all(p["status"] == "unavailable" and p["prediction"] is None for p in result["predictions"]) and
                  any(t.get("usage_status") == "uncertain" for t in traces) and len(traces) == 2 and
                  not list((folder / "cache").glob("*.json")) and "SYNTHETIC_TRANSPORT_ERROR_CANARY" not in json.dumps(result),
                  {"result_status": result["status"], "codes": codes, "trace_statuses": [t["status"] for t in traces]})
            held = rows[0]["reserved_nanos"] / 1e9
            check(name + ":full_reservation_retained", len(rows) == 1 and rows[0]["status"] == "uncertain" and held > 0 and
                  initial_ledger["reserved_usd"] == held and initial_cost["reserved_usd"] == held and
                  initial_ledger["uncertain"] == 1 and initial_ledger["inflight"] == 0 and initial_ledger["held_after_uncertain"] and
                  requests[0]["reservation_at_send"]["reserved_usd"] == held and requests[0]["reservation_at_send"]["inflight"] == 1,
                  {"ledger": initial_ledger, "rows": rows, "reservation_at_send": requests[0]["reservation_at_send"]})
            check(name + ":fresh_backend_shared_hold", physical_final == physical_initial and fresh_result["status"] == "partial" and
                  fresh_result["usage"]["budget_detail"]["attempted_calls"] == 0 and
                  fresh_result["usage"]["budget_detail"]["campaign"]["attempts"] == 1 and
                  fresh_result["usage"]["budget_detail"]["campaign"]["held_after_uncertain"],
                  {"fresh_status": fresh_result["status"], "fresh_usage": fresh_result["usage"], "physical_requests": physical_final})
            check(name + ":unknown_components_explicit", initial_cost.get("unknown_input_usage_attempts") == int(not inp_known) and
                  initial_cost.get("unknown_output_usage_attempts") == int(not out_known) and
                  initial_cost.get("known_input_tokens") == (expected_input or 0) and
                  initial_cost.get("known_output_tokens") == (expected_output or 0), initial_cost, "usage_reporting")
        observation = {"name": name, "response": response, "transport_error": transport_error, "requests": requests,
                       "result": result, "fresh_result": fresh_result, "ledger_rows": rows, "initial_cost": initial_cost,
                       "initial_ledger": initial_ledger, "traces": traces}
        save(folder / "observation.json", observation)
        observations.append(observation)

    hashes_after = {name: sha(source / name) for name in metadata["files"]}
    check("source_hashes_unchanged", hashes_before == hashes_after == metadata["files"], {"count": len(hashes_after)}, "provenance")
    report = {"source": metadata, "backend_sha256": backend_sha, "matches_audit011_backend": backend_sha == OLD_BACKEND_SHA,
              "reproducer_sha256": sha(Path(__file__).resolve()), "python": sys.version, "argv": sys.argv,
              "checks": checks, "counts": {status: sum(c["status"] == status for c in checks) for status in ("verified", "failed")},
              "execution_boundary_failures": [c["name"] for c in checks if c["status"] == "failed" and c["category"] == "execution_boundary"],
              "reporting_failures": [c["name"] for c in checks if c["status"] == "failed" and c["category"] == "usage_reporting"],
              "scope": "Real runner.run_job, dev/priced_api, real adapter and SQLite ledger; synthetic fixture/transport/key; frozen source; no live API or real env reads.",
              "limits": ["No model availability, provider identity or actual price verification.", "No full campaign/CLI/confirmation test.",
                         "counts.attempted is decision rows; usage.attempted_calls is gate invocations; budget_detail.attempted_calls is reserved requests.",
                         "A fresh job blocked by shared ledger is conservatively marked uncertain by runner, though it sends zero HTTP requests.",
                         "Frozen runtime and one canonical coordinator ledger/lease path assumed.",
                         "Prior concurrency proof reused only for byte-identical old backend, not claimed freshly tested for changed backend."]}
    save(out / "report.json", report)
    save(out / "observations.json", observations)
    print(json.dumps({k: report[k] for k in ("backend_sha256", "matches_audit011_backend", "counts", "execution_boundary_failures", "reporting_failures")}, indent=2))
    return 1 if any(c["status"] == "failed" for c in checks) else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    source, out = args.source_root.resolve(), args.out.resolve()
    if args.worker:
        return worker(source, out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "tmp").mkdir()
    command = [sys.executable, "-I", str(Path(__file__).resolve()), "--worker", "--source-root", str(source), "--out", str(out)]
    environment = {"OPENAI_API_KEY": KEY, "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(out / "tmp")}
    result = subprocess.run(command, cwd=source, env=environment, capture_output=True, text=True)
    (out / "stdout.txt").write_text(result.stdout)
    (out / "stderr.txt").write_text(result.stderr)
    save(out / "invocation.json", {"argv": command, "cwd": str(source), "exit_code": result.returncode,
                                   "environment": environment, "parent_argv": sys.argv, "script_sha256": sha(Path(__file__).resolve())})
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
