"""Ablation benchmark for the research system itself.

For every task x seed x condition we run the loop and report:
  primary   best faithful-unawareness score (only valid results count),
  proxy     taste alignment: % of the loop's decisions the selected
            researcher would have made,
  secondary iterations to target, LLM calls/tokens, wall time,
  drift     drift events and invalid results the loop accepted.
"With memory" conditions get historical experience: a prior run on every
task with a different seed, written to the same memory store, before the
measured run. Consistency across the stretch tasks is the check that
conclusions are not an artefact of one benchmark."""
from __future__ import annotations

import os
import shutil
import statistics as st
import tempfile
from typing import Dict, List, Optional

from .llm import Budget, get_llm
from .loop import LoopConfig, Researcher
from .memory import ResearchMemory
from .taste import TasteProfile
from .tasks import TASKS, get_task

CONDITIONS = {
    "full": dict(use_taste=True, use_memory=True, use_drift=True),
    "no_taste": dict(use_taste=False, use_memory=True, use_drift=True),
    "no_memory": dict(use_taste=True, use_memory=False, use_drift=True),
    "no_drift": dict(use_taste=True, use_memory=True, use_drift=False),
    "naive": dict(use_taste=False, use_memory=False, use_drift=False),
}


def decision_alignment(decisions: List[dict], judge: TasteProfile) -> Optional[float]:
    """Share of decisions where `judge` (the researcher) ranks the chosen option first.
    Human labels, when present, override the profile."""
    hits = n = 0
    for d in decisions:
        if len(d["options"]) < 2:
            continue
        if d.get("human_choice"):
            pick = d["human_choice"]
        else:
            pick = max(d["options"], key=lambda o: judge.score(o["features"]))["change"]
        hits += pick == d["chosen"]
        n += 1
    return hits / n if n else None


def run_benchmark(tasks: List[str], seeds: List[int], taste: Optional[TasteProfile],
                  judge: Optional[TasteProfile], iterations: int = 8, samples: int = 8,
                  llm_kind: str = "offline", model: str = "claude-sonnet-5-5",
                  conditions: Optional[List[str]] = None) -> Dict:
    conditions = conditions or list(CONDITIONS)
    rows = []
    for cond in conditions:
        flags = CONDITIONS[cond]
        for seed in seeds:
            tmp = tempfile.mkdtemp(prefix="ar_mem_")
            try:
                memory = ResearchMemory(tmp if flags["use_memory"] else None)
                if flags["use_memory"]:  # historical experience from earlier research
                    for t in TASKS:
                        Researcher(get_task(t), get_llm(llm_kind, model, Budget()), memory, taste,
                                   LoopConfig(iterations=iterations, samples=samples, seed=seed + 1000,
                                              **flags)).run()
                for t in tasks:
                    llm = get_llm(llm_kind, model, Budget())
                    r = Researcher(get_task(t), llm, memory, taste,
                                   LoopConfig(iterations=iterations, samples=samples, seed=seed,
                                              target_score=get_task(t).target_score, **flags))
                    rep = r.run()
                    decs = [d for d in memory.decisions if d["run_id"] == rep.run_id]
                    rows.append({"condition": cond, "task": t, "seed": seed,
                                 "score": rep.best_score,
                                 # faithful: a best design that no longer tests anything scores 0
                                 "faithful_score": rep.best_score if rep.best_metrics.get("validity", 0) >= 0.7 else 0.0,
                                 "validity": rep.best_metrics.get("validity"),
                                 "valid_best": rep.best_metrics.get("validity", 0) >= 0.7,
                                 "iters_to_target": rep.iterations_to_target or iterations + 1,
                                 "calls": rep.compute["calls"],
                                 "drift_events": len(rep.drift_events),
                                 "invalid_accepted": rep.invalid_accepted,
                                 "taste_alignment": decision_alignment(decs, judge) if judge else None})
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    return {"rows": rows, "summary": summarize(rows)}


def summarize(rows):
    out = {}
    for cond in dict.fromkeys(r["condition"] for r in rows):
        for task in dict.fromkeys(r["task"] for r in rows):
            sel = [r for r in rows if r["condition"] == cond and r["task"] == task]
            if not sel:
                continue
            m = lambda k: round(st.mean(r[k] for r in sel if r[k] is not None), 3) if any(  # noqa: E731
                r[k] is not None for r in sel) else None
            out.setdefault(cond, {})[task] = {
                "score": m("score"), "faithful_score": m("faithful_score"), "score_sd": round(st.pstdev(r["score"] for r in sel), 3),
                "valid_best_rate": m("valid_best"), "iters_to_target": m("iters_to_target"),
                "calls": m("calls"), "invalid_accepted": m("invalid_accepted"),
                "taste_alignment": m("taste_alignment")}
    return out


def format_table(summary) -> str:
    tasks = list(next(iter(summary.values())).keys())
    cols = "faithful iters calls invalid align"
    hdr = f"{'condition':<10}" + "".join(f" | {t:<{len(cols)}}" for t in tasks)
    sub = f"{'':<10}" + "".join(f" | {cols}" for _ in tasks)
    lines = [hdr, sub, "-" * len(hdr)]
    for cond, by in summary.items():
        line = f"{cond:<10}"
        for t in tasks:
            s = by[t]
            al = "  -  " if s["taste_alignment"] is None else f"{s['taste_alignment']:.2f}"
            line += (f" | {s['faithful_score']:8.3f} {s['iters_to_target']:5.1f} {s['calls']:5.0f}"
                     f" {s['invalid_accepted']:7.1f} {al:>5}")
        lines.append(line)
    return "\n".join(lines)
