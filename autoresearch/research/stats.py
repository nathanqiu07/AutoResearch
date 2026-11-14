"""Small-sample statistics with no dependencies: bootstrap CIs and the
bootstrap probability that one configuration beats another."""
from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def bootstrap_ci(xs: Sequence[float], level: float = 0.9, n: int = 2000, seed: int = 0) -> Tuple[float, float]:
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    ms = sorted(mean([rng.choice(xs) for _ in xs]) for _ in range(n))
    lo = ms[int((1 - level) / 2 * n)]
    hi = ms[min(n - 1, int((1 + level) / 2 * n))]
    return lo, hi


def prob_better(a: Sequence[float], b: Sequence[float], n: int = 4000, seed: int = 0) -> float:
    """P(mean(a) > mean(b)) under independent bootstrap resampling."""
    if not a or not b:
        return 0.5
    rng = random.Random(seed)
    wins = 0
    for _ in range(n):
        ma = mean([rng.choice(a) for _ in a])
        mb = mean([rng.choice(b) for _ in b])
        wins += ma > mb
    return wins / n


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) < 3:
        return 0.0

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0
