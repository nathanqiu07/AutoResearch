"""Continue only never-started issued reference jobs; never retry or settle funds.

The coordinator injects credentials into the environment. This script does not
read credential files. --check performs read-only preflight and no launches.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

INDEX_SHA = "8333a1e33103923f9913bebfe262c7a8df238900abfb97aa4f8a16c87c4e76e1"
RUNTIME_COMMIT = "63a2c21d1096700f816f4edf71048bcfd4891927"
LATEST_START = datetime(2026, 11, 15, 16, 44, tzinfo=timezone.utc)
DEADLINE = "2026-11-15T17:00:00Z"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_ref(ref):
    data = Path(ref["path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != ref["sha256"]:
        raise ValueError("pinned_file_changed")
    return json.loads(data)


def prior_state(dispatch, rows):
    """Reconcile a drained v1; claimed jobs without terminal proof block v2."""
    terminal = read_ref(dispatch["prior_terminal"])
    claim = read_ref(dispatch["prior_claim"])
    prior = Path(dispatch["prior_terminal"]["path"]).parent
    if (Path(dispatch["prior_claim"]["path"]).parent != prior or
            claim["issued_index_sha256"] != dispatch["index"]["sha256"] or
            terminal["status"] not in ("stopped", "complete") or
            terminal["all_tranches_still_reserved"] is not True or
            terminal["no_retry"] is not True):
        raise ValueError("prior_supervisor_not_drained")
    completed = terminal["completed"]
    records = {r["job_id"]: r for r in completed}
    started = {json.loads(p.read_text())["job_id"] for p in
               (prior / "execution").glob("*-started.json")}
    if (len(records) != len(completed) or started != set(records) or
            len(records) != terminal["attempted_packets"] or
            len(rows) - len(records) != terminal["unattempted_packets"]):
        raise ValueError("prior_started_terminal_mismatch")
    by_id = {r["job_id"]: r for r in rows}
    if not set(records) <= set(by_id):
        raise ValueError("prior_job_not_issued")
    unknown = 0
    for job, record in records.items():
        if json.loads((prior / "execution" / (job + "-terminal.json")).read_text()) != record:
            raise ValueError("prior_terminal_record_changed")
        outcome = record["outcome"]
        if outcome not in ("terminal_known_usage", "terminal_with_unknown_hold",
                            "missing_or_invalid_terminal_evidence"):
            raise ValueError("unknown_prior_outcome")
        unknown += outcome != "terminal_known_usage"
        # Verify previously frozen completion/report identities without reading scores.
        packet = Path(by_id[job]["plan_path"]).parent
        for key, path in (("completion_sha256", packet / "completion.json"),
                          ("report_sha256", packet / "output" / "report.json")):
            if key in record and sha(path) != record[key]:
                raise ValueError("prior_completion_changed")
    if type(terminal["new_uncertain_packets"]) is not int or unknown != terminal["new_uncertain_packets"]:
        raise ValueError("prior_unknown_count_mismatch")
    for row in rows:
        packet = Path(row["plan_path"]).parent
        for marker in (Path(row["claim_path"]), packet / "LAUNCH_USED.json"):
            if marker.exists():
                if row["job_id"] not in records:
                    raise ValueError("unreconciled_claim")
                value = json.loads(marker.read_text())
                if any(value.get(k) != expected for k, expected in (
                        ("job_id", row["job_id"]), ("plan_sha256", row["plan_sha256"]),
                        ("lease_sha256", row["sha256"]))):
                    raise ValueError("prior_claim_binding_mismatch")
        if row["job_id"] not in records and any((packet / p).exists() for p in
                                               ("output", "completion.json")):
            raise ValueError("unreconciled_output")
    return [r for r in rows if r["job_id"] not in records], unknown, sorted(records)


def preflight(dispatch):
    if dispatch["schema_version"] != "reference-supervisor-v2-dispatch" or dispatch["script_sha256"] != sha(__file__):
        raise ValueError("script_or_dispatch_identity_mismatch")
    if dispatch["index"]["sha256"] != INDEX_SHA:
        raise ValueError("issued_index_identity_mismatch")
    index = read_ref(dispatch["index"])
    rows = index["leases"]
    if len(rows) != 57 or any(len({r[k] for r in rows}) != 57 for k in
                            ("job_id", "claim_path", "user_id", "plan_path", "path")):
        raise ValueError("duplicate_or_wrong_issued_jobs")
    if (Decimal(index["aggregate_reserved_usd"]) != Decimal("44.90") or
            Decimal(index["retained_old_usd"]) != Decimal("5") or
            index["reference_max_concurrent_jobs"] != 2):
        raise ValueError("reservation_policy_mismatch")
    runtime = Path(index["runtime_root"])
    if index["runtime_commit"] != RUNTIME_COMMIT or subprocess.check_output(
            ["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip() != RUNTIME_COMMIT:
        raise ValueError("runtime_commit_mismatch")
    if subprocess.check_output(["git", "-C", str(runtime), "status", "--porcelain",
                                "--untracked-files=no"], text=True).strip():
        raise ValueError("runtime_dirty")
    identity = None
    for row in rows:
        lease = read_ref({"path": row["path"], "sha256": row["sha256"]})
        plan = read_ref({"path": row["plan_path"], "sha256": row["plan_sha256"]})
        expected = {"job_id": row["job_id"], "claim_path": row["claim_path"],
                    "plan_sha256": row["plan_sha256"], "state": "authorized", "role": "10",
                    "provider": "openai", "model": "gpt-6-luna", "methods": ["m0", "m1", "m2", "m3"],
                    "max_seconds": 900, "max_calls": row["max_calls"], "max_usd": .7,
                    "deadline": DEADLINE, "user_partition": "dev", "final_authorized": False}
        if any(lease.get(k) != v for k, v in expected.items()) or not 107 <= row["max_calls"] <= 325:
            raise ValueError("lease_policy_mismatch")
        if plan["worst_case_backend_calls"] != row["max_calls"] or plan["user_ids"] != [row["user_id"]]:
            raise ValueError("plan_binding_mismatch")
        if identity is None:
            identity = plan["runtime"]
        elif plan["runtime"] != identity:
            raise ValueError("mixed_runtime_identity")
    if identity["commit"] != RUNTIME_COMMIT or identity["python"] != list(sys.version_info[:3]):
        raise ValueError("runtime_python_mismatch")
    for name, expected_hash in identity["files"].items():
        if sha(runtime / name) != expected_hash:
            raise ValueError("runtime_file_changed")
    eligible, unknown, excluded = prior_state(dispatch, rows)
    if dispatch["eligible_job_ids"] != [r["job_id"] for r in eligible]:
        raise ValueError("eligible_jobs_changed")
    root = Path(dispatch["output_root"])
    if not root.is_absolute() or root.exists() or not root.parent.is_dir():
        raise ValueError("fresh_output_root_required")
    return index, eligible, unknown, excluded


class Supervisor:
    def __init__(self, rows, run, launch, *, prior_unknown=0, now=None):
        self.rows, self.run, self.launch = rows, Path(run), launch
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.active, self.completed = {}, []
        self.next_index, self.unknown, self.stop = 0, prior_unknown, None

    def gates(self):
        if self.unknown >= 2:
            self.stop = "two_new_uncertain_packets_inspection_required"
        elif self.stop is None:
            if (self.run.parent / "STOP_ADMISSIONS").exists():
                self.stop = "coordinator_stop_admissions"
            elif self.now() >= LATEST_START:
                self.stop = "latest_packet_start_reached"

    def poll(self):
        for pid, (process, log, row) in list(self.active.items()):
            rc = process.poll()
            if rc is None:
                continue
            log.close()
            del self.active[pid]
            packet = Path(row["plan_path"]).parent
            record = {"job_id": row["job_id"], "returncode": rc,
                      "entire_tranche_remains_reserved_usd": .7,
                      "finished_at": self.now().isoformat()}
            try:
                cp, report = packet / "completion.json", packet / "output" / "report.json"
                completion = json.loads(cp.read_text())
                if completion["job_id"] != row["job_id"] or completion["report_sha256"] != sha(report):
                    raise ValueError("completion_binding")
                budgets = completion["budgets"]
                if len(budgets) != 1:
                    raise ValueError("budget_count")
                spent, held = (Decimal(str(budgets[0][k])) for k in ("spent_usd", "reserved_usd"))
                attempts = completion["attempts"]
                if (not spent.is_finite() or not held.is_finite() or
                        not 0 <= spent <= Decimal(".7") or not 0 <= held <= Decimal(".7") or
                        type(attempts) is not int or not 0 <= attempts <= row["max_calls"]):
                    raise ValueError("budget_values")
                record.update(completion_sha256=sha(cp), report_sha256=sha(report),
                              known_spent_usd=float(spent), reported_hold_usd=float(held),
                              wrapper_attempts=attempts, failures=completion["failures"],
                              outcome="terminal_with_unknown_hold" if held else "terminal_known_usage")
                self.unknown += bool(held)
                if rc:
                    self.stop = "nonzero_exit_inspection_required"
            except Exception:
                self.unknown += 1
                record["outcome"] = "missing_or_invalid_terminal_evidence"
                self.stop = "terminal_evidence_failure"
            write(self.run / (row["job_id"] + "-terminal.json"), record)
            self.completed.append(record)
        self.gates()

    def step(self):
        # Observe all exits before filling a slot, and again before each admission.
        self.poll()
        while self.stop is None and len(self.active) < 2 and self.next_index < len(self.rows):
            self.poll()
            if self.stop is not None:
                break
            row = self.rows[self.next_index]
            packet = Path(row["plan_path"]).parent
            if any(p.exists() for p in (Path(row["claim_path"]), packet / "LAUNCH_USED.json",
                                        packet / "output", packet / "completion.json")):
                self.stop = "claim_or_launch_marker_appeared"
                break
            if sha(row["path"]) != row["sha256"] or sha(row["plan_path"]) != row["plan_sha256"]:
                self.stop = "packet_identity_changed"
                break
            # A consumed admission remains excluded even if Popen or journaling fails.
            write(self.run / (row["job_id"] + "-admitted.json"), {
                "job_id": row["job_id"], "lease_sha256": row["sha256"],
                "plan_sha256": row["plan_sha256"], "admitted_at": self.now().isoformat()})
            self.next_index += 1
            log = (self.run / (row["job_id"] + ".log")).open("x")
            try:
                process = self.launch(row, log)
            except Exception:
                log.close()
                self.unknown += 1
                self.stop = "launch_failure_inspection_required"
                break
            self.active[process.pid] = (process, log, row)
            write(self.run / (row["job_id"] + "-started.json"), {
                "job_id": row["job_id"], "lease_sha256": row["sha256"],
                "plan_sha256": row["plan_sha256"], "started_at": self.now().isoformat(), "pid": process.pid})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", required=True)
    parser.add_argument("--dispatch-sha256", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dispatch = read_ref({"path": args.dispatch, "sha256": args.dispatch_sha256})
    index, rows, prior_unknown, excluded = preflight(dispatch)
    if args.check:
        print(json.dumps({"status": "preflight_passed_no_launch", "eligible_packets": len(rows),
                          "excluded_job_ids": excluded, "prior_unknown": prior_unknown,
                          "aggregate_reserved_usd": "44.90"}))
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("credential_environment_required")
    if datetime.now(timezone.utc) >= LATEST_START:
        raise ValueError("latest_packet_start_reached")
    root = Path(dispatch["output_root"])
    root.mkdir(exist_ok=False, mode=0o700)
    write(root / "SUPERVISOR_CLAIM.json", {
        "dispatch_sha256": args.dispatch_sha256, "issued_index_sha256": INDEX_SHA,
        "script_sha256": sha(__file__), "started_at": datetime.now(timezone.utc).isoformat(),
        "prior_terminal": dispatch["prior_terminal"], "excluded_job_ids": excluded,
        "prior_unknown": prior_unknown, "max_concurrent": 2, "no_retry": True,
        "all_57_tranches_remain_reserved": True, "aggregate_reserved_usd": "44.90"})
    run = root / "execution"
    run.mkdir()
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    def launch(row, log):
        return subprocess.Popen([sys.executable, "scripts/overnight_labeled_reference.py", "run",
                                 "--plan", row["plan_path"], "--lease", row["path"]],
                                cwd=index["runtime_root"], env=environment, stdout=log, stderr=log)
    supervisor = Supervisor(rows, run, launch, prior_unknown=prior_unknown)
    while supervisor.active or supervisor.next_index < len(rows):
        supervisor.step()
        if supervisor.stop and not supervisor.active:
            break
        if supervisor.active:
            time.sleep(5)
    write(root / "supervisor-terminal.json", {
        "status": "stopped" if supervisor.stop else "complete", "reason": supervisor.stop,
        "dispatch_sha256": args.dispatch_sha256, "prior_terminal": dispatch["prior_terminal"],
        "excluded_job_ids": excluded, "attempted_packets": supervisor.next_index,
        "unattempted_packets": len(rows) - supervisor.next_index,
        "prior_unknown": prior_unknown, "new_uncertain_packets": supervisor.unknown - prior_unknown,
        "total_uncertain_packets": supervisor.unknown, "completed": supervisor.completed,
        "all_tranches_still_reserved": True, "aggregate_reserved_usd": "44.90", "no_retry": True})
    print(json.dumps({"status": "stopped" if supervisor.stop else "complete",
                      "reason": supervisor.stop, "attempted_packets": supervisor.next_index,
                      "total_uncertain_packets": supervisor.unknown}))


if __name__ == "__main__":
    main()
