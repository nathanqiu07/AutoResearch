#!/usr/bin/env python3
"""Print the E4 commands (one research run per arm x seed, then one held-out
evaluation per run and held-out target) from the pre-registration, so paid runs
can be started by hand while WS E's runner is on hold (PLAN 12.0). It only
prints; it runs nothing.

  python3 scripts/e4_commands.py --prereg results/prereg/E4.json [--arms R0 R1-P] [--seeds 0 1] [--llm anthropic]

Model flags come from the models config the pre-registration names
(`models_config`, C2's configs/models.json): dev roles for
the runs, each held-out target with the held-out judges for the evaluations.
Refuses a DRAFT pre-registration unless --allow-draft is given (for offline dry runs).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


REPORT_GLOB = "*_" + "[0-9a-f]" * 8 + ".json"   # a run's report: <stem>_<8-hex run id>.json


def _runnable(prereg: dict, arms: Optional[List[str]]) -> Dict[str, dict]:
    runnable = {a: v for a, v in prereg["arms"].items() if "taste_mode" in v}
    arms = arms or list(runnable)
    unknown = [a for a in arms if a not in runnable]
    if unknown:
        raise SystemExit(f"arms not runnable by this CLI or unknown: {unknown} (runnable: {sorted(runnable)})")
    return {a: runnable[a] for a in arms}


def _items_args(s: dict) -> List[str]:
    out = ["--benchmark-items", s["benchmark_items"]]
    if s.get("split_file"):
        out += ["--split-file", s["split_file"]]
    return out


def commands(prereg: dict, arms: List[str] = None, seeds: List[int] = None, llm: str = "anthropic",
             extra: List[str] = None, out_root: str = "results/e4", runs_root: str = "runs/e4",
             models: Optional[dict] = None) -> List[str]:
    """One research command per arm x seed. `models` is a loaded models config;
    None leaves the CLI's default models (offline dry runs)."""
    s = prereg["shared_run_settings"]
    # thresholds have no CLI flags: the pre-registered values must be the loop's own
    from autoresearch.research.loop import ResearchConfig
    d = ResearchConfig()
    for k in ("accept_p", "confirm_p", "min_validity"):
        if k in s and s[k] != getattr(d, k):
            raise SystemExit(f"pre-registered {k}={s[k]} differs from the loop's {getattr(d, k)}; no CLI flag sets it")
    if models is not None:
        from autoresearch.research.models_config import research_args
        model_args = research_args(models, "dev")
    else:
        model_args = []
    lines = []
    for arm, a in _runnable(prereg, arms).items():
        for seed in seeds if seeds is not None else prereg["seeds"]:
            run = ["python3", "-m", "autoresearch", "--llm", llm, "research", "--arm", arm,
                   "--taste-mode", a["taste_mode"], "--seed", str(seed),
                   "--setting", s["setting"], *_items_args(s),
                   "--items-per-iter", str(s["items_per_iter"]), "--samples", str(s["samples"]),
                   "--iterations", str(s["iterations"]), "--proposals", str(s["proposals"]),
                   "--evals-per-iter", str(s["evals_per_iter"]), "--min-taste-confidence", str(s["min_taste_confidence"]),
                   "--faithfulness-samples", str(s["faithfulness_samples"]),
                   "--realism-samples", str(s["realism_samples"]), "--max-calls", str(s["max_calls"]),
                   "--mode", s["mode"], "--memory", f"{runs_root}/{arm}/seed{seed}",
                   "--decisions-dir", f"{runs_root}/decisions", "--out", f"{out_root}/{arm}/seed{seed}"]
            if "history_chars" in s:   # read only by prompt arms; passed to all so arms differ only in taste flags
                run += ["--history-chars", str(s["history_chars"])]
            if a.get("taste_track"):
                run += ["--taste-track", a["taste_track"]]
            if a.get("researcher"):
                run += ["--researcher", a["researcher"]]
            if not s.get("web"):
                run.append("--no-web")
            if not s.get("shared_memory"):
                run.append("--no-shared")
            run += model_args + list(extra or [])
            lines.append(" ".join(shlex.quote(x) for x in run))
    return lines


def heldout_commands(prereg: dict, models: dict, arms: List[str] = None, seeds: List[int] = None,
                     llm: str = "anthropic", out_root: str = "results/e4") -> List[str]:
    """Per run, one `evaluate-design --mode final` per held-out target (each target is
    reported separately, PLAN I7), written beside the run's report as heldout-<target>."""
    from autoresearch.research.models_config import research_args
    s = prereg["shared_run_settings"]
    ht = models["roles"].get("heldout_targets") or []
    targets = ht if isinstance(ht, list) else [ht]
    if not targets:
        raise SystemExit("the models config lists no held-out targets")
    lines = []
    for arm in _runnable(prereg, arms):
        for seed in seeds if seeds is not None else prereg["seeds"]:
            d = f"{out_root}/{arm}/seed{seed}"
            for t in targets:
                slug = re.sub(r"[^A-Za-z0-9.]+", "-", t).strip("-")
                ev = ["python3", "-m", "autoresearch", "--llm", llm, "evaluate-design", *_items_args(s),
                      "--samples", str(prereg.get("heldout_evaluation", {}).get("samples_per_item", 3)), "--seed", str(seed),
                      "--out", f"{d}/heldout-{slug}", *research_args(models, "final", t)]
                lines.append(f'for r in {shlex.quote(d)}/{REPORT_GLOB}; do '
                             + " ".join(shlex.quote(x) for x in ev[:6]) + ' --report "$r" '
                             + " ".join(shlex.quote(x) for x in ev[6:]) + "; done")
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prereg", default="results/prereg/E4.json")
    p.add_argument("--arms", nargs="*")
    p.add_argument("--seeds", nargs="*", type=int)
    p.add_argument("--llm", default="anthropic")
    p.add_argument("--allow-draft", action="store_true")
    p.add_argument("--models", help="models config (default: the pre-registration's models_config; "
                                    "'none' keeps the CLI's default models, for offline dry runs)")
    p.add_argument("extra", nargs=argparse.REMAINDER, help="extra research args after --, e.g. -- --target haiku")
    a = p.parse_args(argv)
    with open(a.prereg) as f:
        prereg = json.load(f)
    if str(prereg.get("status", "")).startswith("ARCHIVED"):
        raise SystemExit(f"{a.prereg} is archived (PLAN §9): {prereg['status']}")
    if str(prereg.get("status", "")).startswith("DRAFT") and not a.allow_draft:
        raise SystemExit(f"{a.prereg} is a DRAFT pre-registration; resolve 'blocked_on' and commit it as final first")
    extra = [x for x in a.extra if x != "--"]
    path = a.models or prereg.get("models_config")
    models = None
    if path and path != "none":
        from autoresearch.research.models_config import load_models_config
        models = load_models_config(path)
    for line in commands(prereg, a.arms, a.seeds, a.llm, extra, models=models):
        print(line)
    if models is None:
        print("# no models config: held-out evaluation commands need the held-out targets and judges (--models)")
        return
    print("# then, after each run: held-out evaluation, one per held-out target")
    for line in heldout_commands(prereg, models, a.arms, a.seeds, a.llm):
        print(line)

if __name__ == "__main__":
    main()
