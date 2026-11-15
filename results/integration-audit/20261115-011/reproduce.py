#!/usr/bin/env python3
"""Offline API-adapter/ledger review. Synthetic-only environment and transport."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
SYNTHETIC_ENV = {"OPENAI_API_KEY": "synthetic-not-a-real-key"}
DEADLINE = "2099-01-01T00:00:00+00:00"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def response(**changes):
    value = {"status": "completed", "model": "gpt-6-sol",
             "usage": {"input_tokens": 100, "output_tokens": 20,
                       "input_tokens_details": {"cached_tokens": 90},
                       "output_tokens_details": {"reasoning_tokens": 7}},
             "output": [{"type": "reasoning"}, {"type": "message", "role": "assistant",
                         "status": "completed", "content": [{"type": "output_text", "text": "synthetic output"}]}]}
    value.update(changes)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--reserve-worker", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    sys.path.insert(0, str(root))
    from autoresearch.taste.overnight import backends as b
    from autoresearch.taste.overnight.contracts import backend_identity
    from autoresearch.llm import Budget
    if args.reserve_worker:
        ledger = b.DollarLedger(args.reserve_worker, max_usd=1, deadline=DEADLINE, max_inflight=2)
        try:
            ledger.reserve(.1, {"synthetic_worker": True})
            print(json.dumps({"accepted": True}))
        except RuntimeError as exc:
            print(json.dumps({"accepted": False, "error": str(exc)}))
        return 0
    if args.out is None:
        parser.error("--out required")
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    (out / "ledgers").mkdir(); (out / "test-tmp").mkdir()
    pin = json.loads((root / "AUDIT_SOURCE.json").read_text())
    before = {name: sha(root / name) for name in pin["files"]}
    assert before == pin["files"]
    observations = {}

    def record(name, expected, function, predicate):
        try:
            value = function()
            item = {"returned": True, "value": value}
        except Exception as exc:
            item = {"returned": False, "exception": type(exc).__name__, "message": str(exc)}
        item["expected"] = expected
        item["assessment"] = "verified" if predicate(item) else "failed"
        observations[name] = item

    def ledger(name, **changes):
        config = dict(max_usd=1, deadline=DEADLINE, max_inflight=2); config.update(changes)
        return b.DollarLedger(out / "ledgers" / (name + ".sqlite3"), **config)

    def api_case(name, payload=None, transport_error=False, repeat=False, budget=None, allocation=.1):
        shared = ledger(name)
        calls = []
        def transport(request, timeout):
            calls.append({"body": json.loads(request.data), "url": request.full_url, "timeout": timeout,
                          "reservation_at_transport": shared.summary(),
                          "authorization_is_synthetic": request.get_header("Authorization") == "Bearer synthetic-not-a-real-key"})
            if transport_error:
                raise RuntimeError("synthetic-not-a-real-key simulated transport failure")
            return io.BytesIO(json.dumps(response() if payload is None else payload).encode())
        # The adapter has no explicit key parameter. Replace its entire os reference
        # with a synthetic-only mapping; do not inspect or patch real os.environ.
        with patch.object(b, "os", SimpleNamespace(environ=dict(SYNTHETIC_ENV))), \
             patch.object(b.urllib.request, "urlopen", side_effect=transport):
            backend = b.OpenAIResponsesBackend(model="gpt-6-sol", reasoning="medium", ledger=shared,
                                              max_usd=allocation, budget=budget, timeout=5)
            identity = backend_identity(backend)
            outcomes = []
            for _ in range(2 if repeat else 1):
                try:
                    text = backend.complete("Synthetic prompt", system="Synthetic system", max_tokens=128, temperature=.7)
                    outcomes.append({"status": "complete", "text": text})
                except Exception as exc:
                    outcomes.append({"status": "error", "exception": type(exc).__name__, "message": str(exc)})
            return {"calls": calls, "outcomes": outcomes, "identity": identity,
                    "cost": backend.cost_summary(), "usage": backend.budget.summary()}

    record("fixed_request_and_usage", "Explicit model/reasoning/store/tier, no tools or temperature; all input/output billed once",
           lambda: api_case("success"),
           lambda o: o["returned"] and o["value"]["outcomes"][0]["status"] == "complete"
           and len(o["value"]["calls"]) == 1
           and o["value"]["calls"][0]["body"] == {"model": "gpt-6-sol", "instructions": "Synthetic system",
               "input": "Synthetic prompt", "max_output_tokens": 128, "reasoning": {"effort": "medium"},
               "store": False, "service_tier": "default"}
           and o["value"]["calls"][0]["reservation_at_transport"]["inflight"] == 1
           and o["value"]["calls"][0]["reservation_at_transport"]["reserved_usd"] > 0
           and o["value"]["cost"]["spent_usd"] == .0004 and o["value"]["cost"]["reserved_usd"] == 0
           and o["value"]["usage"]["input_tokens"] == 100 and o["value"]["usage"]["output_tokens"] == 20
           and o["value"]["identity"]["enforced_settings"]["reasoning_effort"] == "medium"
           and o["value"]["identity"]["enforced_settings"]["temperature"] == "not_sent")
    record("transport_failure_holds_lane", "One attempt, full reservation retained; later call blocked; synthetic key absent from error",
           lambda: api_case("transport-failure", transport_error=True, repeat=True),
           lambda o: o["returned"] and len(o["value"]["calls"]) == 1
           and all(x["status"] == "error" and "synthetic-not-a-real-key" not in x["message"] for x in o["value"]["outcomes"])
           and o["value"]["cost"]["reserved_usd"] > 0 and o["value"]["cost"]["campaign"]["uncertain"] == 1)
    record("incomplete_usage_retained", "Incomplete response charges known usage, keeps reservation and blocks next attempt",
           lambda: api_case("incomplete", response(status="incomplete"), repeat=True),
           lambda o: o["returned"] and len(o["value"]["calls"]) == 1
           and o["value"]["cost"]["spent_usd"] == .0004 and o["value"]["cost"]["reserved_usd"] > 0)
    record("output_bound_exceeded", "Reported over-bound usage is charged and lane held",
           lambda: api_case("overbound", response(usage={"input_tokens": 100, "output_tokens": 129}), repeat=True),
           lambda o: o["returned"] and len(o["value"]["calls"]) == 1
           and o["value"]["cost"]["spent_usd"] == .00149 and o["value"]["cost"]["campaign"]["uncertain"] == 1)
    record("missing_usage_holds_full_reservation", "Missing usage remains uncertain with full reservation and no fabricated token usage",
           lambda: api_case("missing-usage", response(usage={}), repeat=True),
           lambda o: o["returned"] and len(o["value"]["calls"]) == 1 and o["value"]["cost"]["reserved_usd"] > 0
           and o["value"]["usage"]["input_tokens"] == 0 and o["value"]["usage"]["output_tokens"] == 0
           and o["value"]["cost"]["campaign"]["uncertain"] == 1)
    for name, usage, field, expected in [("partial_input_usage", {"input_tokens": 100}, "input_tokens", 100),
                                         ("partial_output_usage", {"output_tokens": 20}, "output_tokens", 20)]:
        record(name, "Retain each valid reported usage component while holding the uncertain full reservation",
               lambda name=name, usage=usage: api_case(name, response(usage=usage), repeat=True),
               lambda o, field=field, expected=expected: o["returned"] and len(o["value"]["calls"]) == 1
               and o["value"]["cost"]["campaign"]["uncertain"] == 1 and o["value"]["cost"]["reserved_usd"] > 0
               and o["value"]["usage"][field] == expected)
    record("per_job_dollar_limit", "Insufficient local allocation prevents reservation and transport",
           lambda: api_case("local-limit", allocation=.00000001),
           lambda o: o["returned"] and o["value"]["calls"] == [] and o["value"]["cost"]["campaign"]["attempts"] == 0)
    record("per_job_call_limit", "Completed first call consumes local one-call allocation",
           lambda: api_case("call-limit", repeat=True, budget=Budget(max_calls=1)),
           lambda o: o["returned"] and len(o["value"]["calls"]) == 1
           and o["value"]["outcomes"][0]["status"] == "complete" and o["value"]["outcomes"][1]["status"] == "error")

    def aggregate():
        a = ledger("aggregate", max_usd=.01); other = ledger("aggregate", max_usd=.01)
        a.reserve(.009, {"synthetic_job": "one"})
        try: other.reserve(.002, {"synthetic_job": "two"}); blocked = False
        except RuntimeError: blocked = True
        return {"blocked": blocked, "summary": other.summary()}
    record("shared_aggregate_reservations", "Separate ledger instances share one aggregate dollar ceiling", aggregate,
           lambda o: o["returned"] and o["value"]["blocked"] and o["value"]["summary"]["reserved_usd"] == .009)

    def immutable_policy():
        ledger("policy")
        cases = {}
        for field, value in [("max_usd", 2), ("deadline", "2098-01-01T00:00:00+00:00"), ("max_inflight", 3)]:
            try: ledger("policy", **{field: value}); cases[field] = False
            except ValueError: cases[field] = True
        return cases
    record("immutable_ledger_policy", "Reopening cannot reset dollars, deadline or concurrency", immutable_policy,
           lambda o: o["returned"] and all(o["value"].values()))

    def persistence():
        a = ledger("pending"); reservation = a.reserve(.2, {"synthetic": True})
        reopened = ledger("pending")
        first = reopened.summary()
        reopened.finish(reservation, actual_usd=.01, succeeded=False)
        second = ledger("pending").summary()
        try: ledger("pending").reserve(.01, {}); blocked = False
        except RuntimeError: blocked = True
        try: reopened.finish(reservation, actual_usd=0, succeeded=True); resettled = True
        except ValueError: resettled = False
        return {"pending": first, "uncertain": second, "new_reservation_blocked": blocked, "resettled": resettled}
    record("crash_pending_and_uncertain_persistence", "Pending holds persist across opens; uncertainty cannot be released or reused", persistence,
           lambda o: o["returned"] and o["value"]["pending"]["reserved_usd"] == .2
           and o["value"]["pending"]["inflight"] == 1 and o["value"]["uncertain"]["reserved_usd"] == .2
           and o["value"]["uncertain"]["spent_usd"] == .01 and o["value"]["new_reservation_blocked"] and not o["value"]["resettled"])

    def threaded():
        ledger("threads")
        def attempt(_):
            try: ledger("threads").reserve(.1, {}); return True
            except RuntimeError: return False
        with ThreadPoolExecutor(max_workers=3) as pool: accepted = list(pool.map(attempt, range(3)))
        return {"accepted": accepted, "summary": ledger("threads").summary()}
    record("thread_shared_concurrency", "Three concurrent connections admit exactly two pending calls", threaded,
           lambda o: o["returned"] and sum(o["value"]["accepted"]) == 2 and o["value"]["summary"]["inflight"] == 2)

    def processes():
        shared = ledger("processes")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--source-root", str(root), "--reserve-worker", str(shared.path)]
        # Explicit environment replaces inheritance. No real environment is read.
        children = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     env={"PYTHONDONTWRITEBYTECODE": "1"}) for _ in range(3)]
        results = []
        for child in children:
            stdout, stderr = child.communicate(timeout=20)
            results.append({"exit_code": child.returncode, "stdout": stdout, "stderr": stderr,
                            "observation": json.loads(stdout) if child.returncode == 0 else None})
        return {"argv": command, "environment": {"PYTHONDONTWRITEBYTECODE": "1"},
                "children": results, "summary": shared.summary()}
    record("process_shared_concurrency", "Three independent processes admit exactly two pending reservations", processes,
           lambda o: o["returned"] and all(x["exit_code"] == 0 for x in o["value"]["children"])
           and sum(x["observation"]["accepted"] for x in o["value"]["children"]) == 2
           and o["value"]["summary"]["inflight"] == 2)
    def expired():
        shared = ledger("expired", deadline="2000-01-01T00:00:00+00:00")
        try: shared.reserve(.1, {}); blocked = False
        except RuntimeError: blocked = True
        return {"blocked": blocked, "summary": shared.summary()}
    record("expired_campaign", "Expired ledger rejects before creating a reservation", expired,
           lambda o: o["returned"] and o["value"]["blocked"] and o["value"]["summary"]["attempts"] == 0)

    # Original tests see only an explicit synthetic child environment. The outer
    # denial guard prevents accidental networking; tests replace it with local mocks.
    test_code = """import socket, urllib.request, unittest
def deny(*args, **kwargs):
    raise RuntimeError('NETWORK_DISABLED_BY_INDEPENDENT_AUDIT')
urllib.request.urlopen = deny
socket.socket.connect = deny
socket.create_connection = deny
suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_overnight_backends')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
"""
    test_env = {"OPENAI_API_KEY": "synthetic-key-only", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(out / "test-tmp")}
    tests = subprocess.run([sys.executable, "-B", "-c", test_code], cwd=root, env=test_env, capture_output=True, text=True)
    (out / "existing-tests.stdout.txt").write_text(tests.stdout)
    (out / "existing-tests.stderr.txt").write_text(tests.stderr)
    after = {name: sha(root / name) for name in pin["files"]}
    report = {"source_commit": pin["source_commit"], "api_implementation_commit": pin["api_implementation_commit"],
              "source_pin_sha256": sha(root / "AUDIT_SOURCE.json"), "source_hashes": before,
              "source_manifest_matches": before == pin["files"], "source_unchanged": before == after,
              "probe_sha256": sha(Path(__file__)), "argv": sys.argv, "python": sys.version,
              "real_environment_access": False, "real_network_calls": 0, "paid_calls": 0,
              "credential_handling": "Adapter os replaced by synthetic-only mapping before constructor/calls; test children receive explicit synthetic-only environment.",
              "tests": {"argv": [sys.executable, "-B", "-c", test_code], "cwd": str(root), "exit_code": tests.returncode,
                        "environment": test_env, "stdout": "existing-tests.stdout.txt", "stderr": "existing-tests.stderr.txt"},
              "observations": observations,
              "unverified": ["Current provider pricing/model availability and physical provider/model authenticity.",
                             "Conservative byte-plus-overhead reservation is a bound assumption, not tokenizer/provider billing proof.",
                             "One coordinator ledger path and trusted callers are required; choosing another path can bypass shared accounting.",
                             "No live request, invoice reconciliation, external retry/redirect behavior or full runner campaign was executed."]}
    report["counts"] = {status: sum(x["assessment"] == status for x in observations.values()) for status in ("verified", "failed")}
    (out / "observations.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"out": str(out), "counts": report["counts"], "existing_tests_exit": tests.returncode,
                      "source_unchanged": before == after}, indent=2))
    return 0 if before == after and tests.returncode == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
