"""Run a pre-registered experiment (PLAN 12.5 item 6; AGENTS.md rules 4-6).

    python3 scripts/run_experiment.py E5 --llm anthropic --yes            # local, from a code snapshot
    python3 scripts/run_experiment.py E4 --modal --llm anthropic --yes    # one Modal container per cell
    python3 scripts/run_experiment.py E5 --check                          # only run the pre-launch checks

Reads results/prereg/<EXP>.json and refuses to run unless
  * the file is committed and unmodified,
  * its status is "final" and its blocked_on list is empty (a DRAFT may run only
    offline, with --allow-draft, for a dry run of the pipeline),
  * no commit has touched the code under test (autoresearch/, modal_app.py,
    scripts/) since the pre-registration was last committed: the plan is fixed
    before the code that runs it, and any later change means re-committing the
    pre-registration,
  * --yes is given for any paid backend (the user's approval, rule 5).

The experiment then runs from a git worktree snapshot of the current commit
(runs/snapshots/<hash>), so editing the checkout cannot mix code versions into
the run (rule 4). The runner also takes the "live run" lock on autoresearch
when it can, posts the start and the end with agentctl, and writes
<out>/CODE_VERSION and <out>/RUN_MANIFEST.json.

Pre-registration kinds:
  "runner": "grid" (default)  arms x seeds (x settings) of `research` (autoresearch/grid.py)
  "runner": "commands"        "commands": a list of argv lists, run in order in the
                              snapshot; "{out}" is replaced by the output directory
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_PATHS = ["autoresearch", "modal_app.py", "scripts"]


def git(args: List[str], cwd: Optional[str] = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True, check=True).stdout.strip()


def prereg_path(exp: str, root: Optional[str] = None) -> str:
    return os.path.join(root or ROOT, "results", "prereg", f"{exp}.json")


def check(exp: str, llm: str, allow_draft: bool = False, root: Optional[str] = None) -> dict:
    """The pre-launch checks. Returns the pre-registration with commit info, or
    raises SystemExit naming every reason it may not run."""
    root = root or ROOT
    path = prereg_path(exp, root)
    rel = os.path.relpath(path, root)
    if not os.path.exists(path):
        raise SystemExit(f"no pre-registration at {rel}")
    with open(path) as f:
        prereg = json.load(f)
    problems = []
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True).returncode == 0
    if not tracked:
        problems.append(f"{rel} is not committed")
    elif git(["status", "--porcelain", "--", rel], root):
        problems.append(f"{rel} has uncommitted changes")
    draft = not str(prereg.get("status", "")).lower().startswith("final") or bool(prereg.get("blocked_on"))
    if draft:
        if not allow_draft:
            problems.append(f"{rel} is not final (status {str(prereg.get('status'))[:60]!r}, "
                            f"{len(prereg.get('blocked_on') or [])} blocked_on item(s))")
        elif llm != "offline":
            problems.append("a DRAFT pre-registration may only run offline (--llm offline)")
    info = {"prereg": prereg, "path": rel, "draft": draft}
    if tracked:
        pre_commit = git(["log", "-1", "--format=%H", "--", rel], root)
        later = git(["log", "--format=%h %s", f"{pre_commit}..HEAD", "--", *CODE_PATHS], root) if pre_commit else ""
        if later:
            problems.append("code under test changed after the pre-registration was committed; re-commit it:\n    "
                            + "\n    ".join(later.splitlines()[:10]))
        info.update(prereg_commit=pre_commit)
    if git(["status", "--porcelain", "--", *CODE_PATHS], root):
        print("note: uncommitted changes in the code under test are NOT part of the run (it runs the committed snapshot)")
    if problems:
        raise SystemExit("refusing to run " + exp + ":\n  - " + "\n  - ".join(problems))
    info["code_version"] = git(["describe", "--always", "--abbrev=12"], root)
    return info


def snapshot(commit: str, root: Optional[str] = None) -> str:
    """A detached worktree of `commit` under runs/snapshots/ (reused if present)."""
    root = root or ROOT
    d = os.path.join(root, "runs", "snapshots", commit[:12])
    if not os.path.exists(os.path.join(d, "autoresearch")):
        os.makedirs(os.path.dirname(d), exist_ok=True)
        git(["worktree", "add", "--detach", d, commit], root)
    return d


class Coordination:
    """agentctl lock / post / unlock for a live run; off with --no-coordination."""

    def __init__(self, enabled: bool, root: Optional[str] = None):
        self.enabled, self.root, self.locked = enabled, root or ROOT, False

    def _ctl(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, os.path.join(self.root, "scripts", "agentctl.py"), *args],
                              cwd=self.root, capture_output=True, text=True)

    def start(self, exp: str, msg: str):
        if not self.enabled:
            return
        r = self._ctl("lock", "autoresearch", "--reason", f"live run: {exp}")
        self.locked = r.returncode == 0
        if not self.locked:
            print("warning: could not take the 'live run' lock on autoresearch "
                  f"({(r.stderr or r.stdout).strip()[:200]}); the run uses a pinned snapshot, so it proceeds")
        self._ctl("post", f"Starting {exp} (live run)", msg, "--to", "all")

    def end(self, exp: str, msg: str):
        if not self.enabled:
            return
        self._ctl("post", f"Finished {exp}", msg, "--to", "all")
        if self.locked:
            self._ctl("unlock", "autoresearch")


def build_commands(info: dict, llm: str, out: str, use_modal: bool, arms, seeds, extra: List[str]) -> List[List[str]]:
    p = info["prereg"]
    kind = p.get("runner", "grid")
    if kind == "commands":
        return [[x.replace("{out}", out) for x in c] for c in p["commands"]]
    if kind != "grid":
        raise SystemExit(f"unknown runner {kind!r} in {info['path']}")
    if use_modal:
        cmd = ["modal", "run", "modal_app.py", "--mode", "research-grid", "--prereg", info["path"],
               "--llm", llm, "--out", out, "--yes"]
        if arms:
            cmd += ["--arms", " ".join(arms)]
        if seeds:
            cmd += ["--seeds", " ".join(map(str, seeds))]
        return [cmd]
    cmd = [sys.executable, "-m", "autoresearch.grid", "--prereg", info["path"], "--llm", llm, "--out", out, "--yes"]
    if arms:
        cmd += ["--arms", *arms]
    if seeds:
        cmd += ["--seeds", *map(str, seeds)]
    return [cmd + extra]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiment", help="E4 | E5 | E3a | E3b ... (results/prereg/<EXP>.json)")
    ap.add_argument("--llm", default="anthropic")
    ap.add_argument("--out", help="results directory (default: results/<exp>, or the pre-registration's 'out')")
    ap.add_argument("--modal", action="store_true", help="run grid cells on Modal (modal_app.py --mode research-grid)")
    ap.add_argument("--arms", nargs="*")
    ap.add_argument("--seeds", nargs="*", type=int)
    ap.add_argument("--workers", type=int, default=4, help="local: cells run at once")
    ap.add_argument("--check", action="store_true", help="only run the pre-launch checks")
    ap.add_argument("--allow-draft", action="store_true", help="offline only: run a DRAFT pre-registration")
    ap.add_argument("--yes", action="store_true", help="the user approved this paid run")
    ap.add_argument("--no-coordination", action="store_true", help="skip agentctl lock/post (tests, offline)")
    args = ap.parse_args(argv)
    info = check(args.experiment, args.llm, args.allow_draft)
    print(f"{info['path']}: OK (pre-registered at {info.get('prereg_commit', '?')[:12]}, code {info['code_version']})")
    if args.check:
        return 0
    if args.llm != "offline" and not args.yes:
        raise SystemExit("a paid run needs --yes once the user has approved it (AGENTS.md rule 5)")
    out = os.path.abspath(args.out or os.path.join(ROOT, info["prereg"].get("out") or f"results/{args.experiment.lower()}"))
    snap = snapshot(git(["rev-parse", "HEAD"]))
    extra = [] if args.modal else ["--workers", str(args.workers)]
    cmds = build_commands(info, args.llm, out, args.modal, args.arms, args.seeds, extra)
    os.makedirs(out, exist_ok=True)
    manifest = {"experiment": args.experiment, "prereg": info["path"], "prereg_commit": info.get("prereg_commit"),
                "code_version": info["code_version"], "draft": info["draft"], "llm": args.llm, "modal": args.modal,
                "snapshot": os.path.relpath(snap, ROOT), "commands": cmds, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with open(os.path.join(out, "CODE_VERSION"), "w") as f:
        f.write(info["code_version"] + "\n")
    coord = Coordination(not args.no_coordination)
    coord.start(args.experiment, f"code {info['code_version']}, backend {args.llm}, "
                                 f"{'Modal' if args.modal else 'local'}, out {os.path.relpath(out, ROOT)}")
    rc = 0
    env = {**os.environ, "AUTORESEARCH_CODE_VERSION": info["code_version"], "PYTHONPATH": snap}
    try:
        for c in cmds:
            print("$", " ".join(c))
            rc = subprocess.run(c, cwd=snap, env=env).returncode
            if rc:
                break
    finally:
        manifest.update(finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"), returncode=rc)
        with open(os.path.join(out, "RUN_MANIFEST.json"), "w") as f:
            json.dump(manifest, f, indent=1)
        coord.end(args.experiment, f"returncode {rc}; results in {os.path.relpath(out, ROOT)} "
                                   f"(CODE_VERSION {info['code_version']})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
