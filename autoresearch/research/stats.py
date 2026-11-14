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


def auroc(positives: Sequence[float], negatives: Sequence[float]) -> float:
    """P(score of a random positive > score of a random negative), ties count
    half (Mann-Whitney U / n1 n2). For P(eval) with positives = our synthetic
    environments and negatives = real deployment traffic, 0.5 means the two
    are indistinguishable, which is the target (PLAN issue I1)."""
    if not positives or not negatives:
        return float("nan")
    wins = 0.0
    for p in positives:
        for n in negatives:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(positives) * len(negatives))


def cohen_kappa(a: Sequence, b: Sequence) -> float:
    """Chance-corrected agreement between two raters' labels (e.g. the A1
    judge vs hand labels). PLAN P1 gate suggests kappa >= 0.6."""
    if len(a) != len(b) or not a:
        raise ValueError(f"kappa needs two equal-length, non-empty label lists (got {len(a)} and {len(b)})")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    labels = set(a) | set(b)
    expected = sum((list(a).count(k) / n) * (list(b).count(k) / n) for k in labels)
    return 1.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)


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
