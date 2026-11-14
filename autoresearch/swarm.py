"""Parallel research swarm.

Rounds of W independent researcher workers (different seeds, optionally
different researchers' tastes) run in parallel. Within a round workers share
nothing but the memory layer; each round starts by reading everything the
previous rounds' agents wrote. If shared memory carries useful experience,
per-round scores rise and iterations-to-target fall. That is the
self-improvement signal this module measures.

`map_fn` is the executor: builtin `map` locally, `Function.map` on Modal.
"""
from __future__ import annotations

import statistics as st
from typing import Callable, Dict, Iterable, List, Optional

from .llm import Budget, get_llm
from .loop import LoopConfig, Researcher
from .memory import ResearchMemory
from .taste import load_researcher
from .tasks import get_task


def run_cell(spec: Dict, shared=None) -> Dict:
    """Run one researcher worker. `spec` is plain JSON so it ships to remote workers."""
    llm = get_llm(spec.get("llm", "offline"), spec.get("model", "claude-sonnet-5-5"),
                  Budget(max_calls=spec.get("max_calls", 2000)))
    taste = None
    if spec.get("researcher"):
        r = load_researcher(spec["researcher"])
        taste = r.cached_profile() or r.build_profile(llm, holdout=0)[0]
    flags = spec.get("flags", {})
    scout = None
    if spec.get("web", True):
        from .integrations.exa import get_scout
        scout = get_scout(llm)
    task = get_task(spec["task"])
    rep = Researcher(task, llm, ResearchMemory(None), taste,
                     LoopConfig(iterations=spec.get("iterations", 8), samples=spec.get("samples", 8),
                                seed=spec["seed"], target_score=task.target_score, **flags),
                     scout=scout, shared=shared, worker=spec.get("worker", "w")).run()
    return {"worker": spec.get("worker"), "round": spec.get("round"), "seed": spec["seed"],
            "task": rep.task, "score": rep.best_score, "validity": rep.best_metrics.get("validity"),
            "iters_to_target": rep.iterations_to_target, "shared": rep.shared_memory,
            "compute": rep.compute, "sources": rep.sources[:20], "discovered": rep.discovered_options,
            "drift_events": len(rep.drift_events), "best_config": rep.best_config}


def swarm_specs(task: str, rnd: int, workers: int, base_seed: int = 0, **kw) -> List[Dict]:
    return [{"task": task, "seed": base_seed + 100 * rnd + w, "round": rnd, "worker": f"r{rnd}w{w}", **kw}
            for w in range(workers)]


def summarize_rounds(results: Iterable[Dict], iterations: int) -> List[Dict]:
    by: Dict[int, List[Dict]] = {}
    for r in results:
        by.setdefault(r["round"], []).append(r)
    return [{"round": k, "workers": len(v), "mean_score": round(st.mean(x["score"] for x in v), 3),
             "mean_iters_to_target": round(st.mean((x["iters_to_target"] or iterations + 1) for x in v), 2),
             "shared_outcomes_used": sum(x["shared"].get("outcomes_used", 0) for x in v if x["shared"])}
            for k, v in sorted(by.items())]


def run_swarm(task: str, rounds: int, workers: int, map_fn: Callable = map, **kw) -> Dict:
    """`map_fn(specs)` must run each spec with the swarm's shared memory attached."""
    results = []
    for rnd in range(rounds):
        results += list(map_fn(swarm_specs(task, rnd, workers, **kw)))
    return {"rounds": summarize_rounds(results, kw.get("iterations", 8)), "workers": results}
