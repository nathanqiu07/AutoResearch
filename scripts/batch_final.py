"""Run the final held-out sweep over finished research runs through the Message
Batches API (PLAN 8 and 12.5 item 3).

Every run report found under the given paths is scored with `autoresearch
evaluate-design` (final mode, held-out items, held-out targets and judges as you
pass them). All reports run at once in one process, so their calls share
batches: with `--llm anthropic-batch` each pipeline stage (generate, target,
judge) of the whole sweep goes out as one Message Batch at half price.

Scope: single-scenario held-out sweeps (E3a, and E4's primary metric). Petri
audits (E3b) are multi-turn and interactive, so they run through
harness/petri, not through here.

This makes paid calls unless --llm offline. It refuses to start without --yes;
`--dry-run` lists what it would run. Costly runs need the user's approval
(AGENTS.md rule 5).

    python3 scripts/batch_final.py results/e4 --dry-run
    python3 scripts/batch_final.py results/e4 --llm anthropic-batch --yes -- \
        --benchmark-items data/benchmarks/evalawarebench.jsonl --heldout-target claude-haiku-5-5 \
        --heldout-judges claude-opus-5-5 --samples 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from typing import List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def find_reports(paths: List[str]) -> List[str]:
    """Run reports (JSON with run_id and best_design) under the given files or dirs,
    skipping held-out outputs this script writes."""
    out = []
    for p in paths:
        files = [p] if os.path.isfile(p) else [os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs]
        for f in sorted(files):
            if not f.endswith(".json") or "_heldout_" in os.path.basename(f):
                continue
            try:
                with open(f) as fh:
                    rep = json.load(fh)
            except (OSError, ValueError):
                continue
            if isinstance(rep, dict) and "run_id" in rep and "best_design" in rep:
                out.append(f)
    return out


def plan(reports: List[str], llm: str, mode: str, extra: List[str]) -> List[List[str]]:
    return [["--llm", llm, "evaluate-design", "--report", r, "--mode", mode, *extra] for r in reports]


def run_all(argvs: List[List[str]]) -> List[dict]:
    """Run every evaluate-design invocation concurrently; returns per-run status."""
    from autoresearch.cli import main
    status = [{"argv": a, "ok": None, "error": None} for a in argvs]

    def one(k):
        try:
            main(argvs[k])
            status[k]["ok"] = True
        except BaseException as e:   # SystemExit from the CLI is a failure of that run only
            status[k]["ok"], status[k]["error"] = False, f"{type(e).__name__}: {str(e)[:300]}"
    threads = [threading.Thread(target=one, args=(k,), name=f"heldout-{k}") for k in range(len(argvs))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return status


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="report JSON files or results directories")
    ap.add_argument("--llm", default="anthropic-batch", help="backend for every role (offline for a dry run)")
    ap.add_argument("--mode", default="final", choices=["final", "dev"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm that the user approved the paid sweep")
    args, extra = ap.parse_known_args(argv)
    extra = [x for x in extra if x != "--"]
    reports = find_reports(args.paths)
    if not reports:
        raise SystemExit(f"no run reports under {args.paths}")
    argvs = plan(reports, args.llm, args.mode, extra)
    print(f"{len(reports)} report(s), backend {args.llm}, {args.mode} mode")
    for a in argvs:
        print("  autoresearch " + " ".join(a))
    if args.dry_run:
        return 0
    if args.llm != "offline" and not args.yes:
        raise SystemExit("this sweep makes paid calls: rerun with --yes once the user has approved it")
    status = run_all(argvs)
    try:
        from autoresearch.batch import _QUEUES
        batches = [b for q in _QUEUES.values() for b in q.batches]
    except ImportError:
        batches = []
    if batches:
        print(f"{len(batches)} batch(es): " + ", ".join(f"{b['id']} n={b['n']} {b['results']}" for b in batches))
    failed = [s for s in status if not s["ok"]]
    for s in failed:
        print("FAILED:", s["argv"][4], s["error"])
    print(f"{len(status) - len(failed)}/{len(status)} held-out evaluations finished")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
