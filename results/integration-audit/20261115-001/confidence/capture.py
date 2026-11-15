#!/usr/bin/env python3
"""Capture offline audit evidence into a new directory; never overwrite a run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FILES = ["autoresearch/research/advisor.py", "autoresearch/research/loop.py",
         "autoresearch/taste/usermodel.py", "autoresearch/taste/profile.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(repo):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()
    return {"requested_path": str(repo), "resolved_path": str(repo.resolve()),
            "commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "tracked_status": git("status", "--porcelain", "--untracked-files=no"),
            "sha256": {name: sha(repo / name) for name in FILES}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", action="append", required=True, metavar="LABEL=PATH")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    here = Path(__file__).resolve().parent
    report = {"started_utc": datetime.now(timezone.utc).isoformat(),
              "python_executable": sys.executable, "python_version": sys.version,
              "audit_script_sha256": {name: sha(here / name) for name in
                                      ("probe.py", "test_safe_fallback.py", "capture.py")},
              "runs": {}}
    for spec in args.repo:
        label, raw_path = spec.split("=", 1)
        repo = Path(raw_path)
        destination = args.output / label
        destination.mkdir()
        before = snapshot(repo)
        executions = {}
        commands = {
            "probe": [sys.executable, "-B", str(here / "probe.py"), "--repo", str(repo)],
            "regressions_red": [sys.executable, "-B", str(here / "test_safe_fallback.py"), str(repo)],
            "existing_tests": [sys.executable, "-B", "-m", "unittest", "tests.test_usermodel", "tests.test_research_loop_ws_d"],
        }
        for name, command in commands.items():
            proc = subprocess.run(command, cwd=repo, capture_output=True, text=True)
            (destination / (name + ".stdout.txt")).write_text(proc.stdout)
            (destination / (name + ".stderr.txt")).write_text(proc.stderr)
            executions[name] = {"argv": command, "cwd": str(repo), "exit_code": proc.returncode,
                                "stdout": str(destination / (name + ".stdout.txt")),
                                "stderr": str(destination / (name + ".stderr.txt"))}
            if name == "probe" and proc.returncode == 0:
                parsed = json.loads(proc.stdout)
                (destination / "observations.json").write_text(json.dumps(parsed, indent=2, sort_keys=True, allow_nan=False) + "\n")
        after = snapshot(repo)
        report["runs"][label] = {"before": before, "after": after,
                                 "audited_sources_unchanged": before["sha256"] == after["sha256"],
                                 "executions": executions}
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (args.output / "capture.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"capture": str(args.output / "capture.json"),
                      "outcomes": {label: {name: run["exit_code"] for name, run in data["executions"].items()}
                                   for label, data in report["runs"].items()}}, indent=2))


if __name__ == "__main__":
    main()
