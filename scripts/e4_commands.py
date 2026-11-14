#!/usr/bin/env python3
"""Print the E4 commands (one research run per arm x seed, then its held-out
evaluation) from the pre-registration, so paid runs can be started by hand
while WS E's runner is on hold (PLAN 12.0). It only prints; it runs nothing.

  python3 scripts/e4_commands.py --prereg results/prereg/E4.json [--arms R0 R1-P] [--seeds 0 1] [--llm anthropic]

Refuses a DRAFT pre-registration unless --allow-draft is given (for offline dry runs).
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def commands(prereg: dict, arms: List[str] = None, seeds: List[int] = None, llm: str = "anthropic",
             extra: List[str] = None, out_root: str = "results/e4", runs_root: str = "runs/e4") -> List[str]:
    s = prereg["shared_run_settings"]
    # thresholds have no CLI flags: the pre-registered values must be the loop's own
    from autoresearch.research.loop import ResearchConfig
    d = ResearchConfig()
    for k in ("accept_p", "confirm_p", "min_validity"):
        if k in s and s[k] != getattr(d, k):
            raise SystemExit(f"pre-registered {k}={s[k]} differs from the loop's {getattr(d, k)}; no CLI flag sets it")
    runnable = {a: v for a, v in prereg["arms"].items() if "taste_mode" in v}
    arms = arms or list(runnable)
    unknown = [a for a in arms if a not in runnable]
    if unknown:
        raise SystemExit(f"arms not runnable by this CLI or unknown: {unknown} (runnable: {sorted(runnable)})")
    lines = []
    for arm in arms:
        a = runnable[arm]
        for seed in seeds if seeds is not None else prereg["seeds"]:
            run = ["python3", "-m", "autoresearch", "--llm", llm, "research", "--arm", arm,
                   "--taste-mode", a["taste_mode"], "--seed", str(seed),
                   "--setting", s["setting"], "--benchmark-items", s["benchmark_items"],
                   "--items-per-iter", str(s["items_per_iter"]), "--samples", str(s["samples"]),
                   "--iterations", str(s["iterations"]), "--proposals", str(s["proposals"]),
                   "--evals-per-iter", str(s["evals_per_iter"]), "--min-taste-confidence", str(s["min_taste_confidence"]),
                   "--faithfulness-samples", str(s["faithfulness_samples"]),
                   "--realism-samples", str(s["realism_samples"]), "--max-calls", str(s["max_calls"]),
                   "--mode", s["mode"], "--memory", f"{runs_root}/{arm}/seed{seed}",
                   "--decisions-dir", f"{runs_root}/decisions", "--out", f"{out_root}/{arm}/seed{seed}"]
            if a.get("taste_track"):
                run += ["--taste-track", a["taste_track"]]
            if a.get("researcher"):
                run += ["--researcher", a["researcher"]]
            if not s.get("web"):
                run.append("--no-web")
            if not s.get("shared_memory"):
                run.append("--no-shared")
            run += list(extra or [])
            lines.append(" ".join(shlex.quote(x) for x in run))
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prereg", default="results/prereg/E4.json")
    p.add_argument("--arms", nargs="*")
    p.add_argument("--seeds", nargs="*", type=int)
    p.add_argument("--llm", default="anthropic")
    p.add_argument("--allow-draft", action="store_true")
    p.add_argument("extra", nargs=argparse.REMAINDER, help="extra research args after --, e.g. -- --target haiku")
    a = p.parse_args(argv)
    with open(a.prereg) as f:
        prereg = json.load(f)
    if str(prereg.get("status", "")).startswith("DRAFT") and not a.allow_draft:
        raise SystemExit(f"{a.prereg} is a DRAFT pre-registration; resolve 'blocked_on' and commit it as final first")
    extra = [x for x in a.extra if x != "--"]
    for line in commands(prereg, a.arms, a.seeds, a.llm, extra):
        print(line)
    print(f"# then, per run: python3 -m autoresearch --llm {a.llm} evaluate-design --report <run report .json> "
          f"--benchmark-items {prereg['shared_run_settings']['benchmark_items']} --mode final --samples 3 "
          "--heldout-target <held-out target> --heldout-judges <J2a> <J2b>", file=sys.stdout)


if __name__ == "__main__":
    main()
