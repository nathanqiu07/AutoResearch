"""Interventions that work across items (PLAN 12.4 item 4).

In single-item mode the loop rewrites one environment, so a finding can be
about that one prompt. In multi-item mode an intervention is a transformation
applied to a batch of N dev items, re-sampled every iteration, and it is
compared with the current best design *on the same items* (paired by item).
That makes a finding about eval awareness rather than about one prompt.

`ItemPool` holds the dev (or held-out) items and one measurer per item, built
lazily by a factory, so the loop can measure any design on any batch.
"""
from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .measure import Sample, Scenario
from .stats import bootstrap_ci, mean, prob_better


def item_id(sc: Scenario) -> str:
    return sc.source_id or sc.name


class ItemPool:
    def __init__(self, items: List[Scenario], make_measurer: Callable[[Scenario], object], workers: int = 4):
        if not items:
            raise ValueError("ItemPool needs at least one item")
        ids = [item_id(s) for s in items]
        if len(set(ids)) != len(ids):
            raise ValueError("ItemPool items must have unique ids")
        self.items = {item_id(s): s for s in items}
        self.ids = ids
        self._make = make_measurer
        self._measurers: Dict[str, object] = {}
        self.workers = workers

    def measurer(self, iid: str):
        if iid not in self._measurers:
            self._measurers[iid] = self._make(self.items[iid])
        return self._measurers[iid]

    def set_grounding(self, docs: List[str]) -> None:
        for iid in self.ids:
            self.measurer(iid).grounding = docs

    def sample_batch(self, rng: random.Random, n: int) -> List[str]:
        """n distinct items (all of them if the pool is smaller)."""
        return rng.sample(self.ids, min(n, len(self.ids)))

    def measure(self, interventions: List[str], seeds: Sequence[int], categories: Optional[List[str]],
                batch: List[str]) -> List[Tuple[str, Sample]]:
        """Measure one design on a batch: seed j goes to item batch[j % len(batch)].
        Items are measured in parallel; each measurer parallelises its own seeds."""
        per: Dict[str, List[int]] = {iid: [] for iid in batch}
        for j, sd in enumerate(seeds):
            per[batch[j % len(batch)]].append(sd)
        jobs = [(iid, sds) for iid, sds in per.items() if sds]

        def one(job):
            iid, sds = job
            return [(iid, s) for s in self.measurer(iid).measure(interventions, list(sds), categories)]
        with ThreadPoolExecutor(max_workers=max(1, min(self.workers, len(jobs)))) as ex:
            parts = list(ex.map(one, jobs))
        return [x for part in parts for x in part]

    @property
    def warnings(self) -> List[str]:
        out: List[str] = []
        for m in self._measurers.values():
            out += [w for w in getattr(m, "warnings", []) if w not in out]
        return out

    @property
    def mode(self) -> str:
        return getattr(self.measurer(self.ids[0]), "mode", "dev")


def item_means(scores: Sequence[float], items: Sequence[str]) -> Dict[str, float]:
    by: Dict[str, List[float]] = {}
    for s, i in zip(scores, items):
        by.setdefault(i, []).append(s)
    return {i: mean(v) for i, v in by.items()}


def paired_compare(a_scores: Sequence[float], a_items: Sequence[str], b_scores: Sequence[float],
                   b_items: Sequence[str], seed: int = 0, n: int = 4000) -> Tuple[float, float, Dict[str, float]]:
    """P(design a beats design b) and the pooled delta, paired by item.

    The per-item delta is mean(a on item) - mean(b on item); the pooled delta is
    their mean, and P(better) is the bootstrap probability (over items) that
    the pooled delta is positive. With fewer than two shared items there is
    nothing to pair, so it falls back to the unpaired bootstrap over samples."""
    ma, mb = item_means(a_scores, a_items), item_means(b_scores, b_items)
    common = [i for i in ma if i in mb]
    if len(common) < 2:
        return prob_better(list(a_scores), list(b_scores), seed=seed), mean(a_scores) - mean(b_scores), \
            {i: ma[i] - mb[i] for i in common}
    deltas = {i: ma[i] - mb[i] for i in common}
    ds = list(deltas.values())
    rng = random.Random(seed)
    wins = 0
    for _ in range(n):
        wins += mean([rng.choice(ds) for _ in ds]) > 0
    return wins / n, mean(ds), deltas


def per_item_table(base_scores, base_items, best_scores, best_items) -> Dict[str, dict]:
    """Per item: baseline and best mean score, their delta and sample counts."""
    mb, mf = item_means(base_scores, base_items), item_means(best_scores, best_items)
    out = {}
    for i in sorted(set(mb) | set(mf)):
        out[i] = {"baseline": mb.get(i), "best": mf.get(i),
                  "delta": (mf[i] - mb[i]) if i in mb and i in mf else None,
                  "n_baseline": sum(x == i for x in base_items), "n_best": sum(x == i for x in best_items)}
    return out


def pooled_ci(deltas: Dict[str, float]) -> List[float]:
    lo, hi = bootstrap_ci(list(deltas.values()))
    return [lo, hi]
