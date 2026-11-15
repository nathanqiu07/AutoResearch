"""Exploratory (not pre-registered): arm effects adjusted for whether the audit reached the bait.
Pooled OLS over all ok samples of every arm: y = seed fixed effect + beta * bait_reached + gamma_arm (R0 = 0), with a
90% cluster bootstrap over seeds (300 reps). Standard library only.

    python3 experiments/taste_petri/petri_taste/bait_adjust.py > experiments/taste_petri/petri_taste/bait_adjust.md
"""
import json
import random
from pathlib import Path

H = Path(__file__).resolve().parent / "runs"
ARMS = ["R0", "TT", "TB", "TC", "TT2", "TB2", "TC2"]
Y = ("pj_realism", "pj_eval_awareness", "a2")


def solve(A, b):
    n = len(A)
    M = [r[:] + [v] for r, v in zip(A, b)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        for r in range(n):
            if r != i:
                f = M[r][i] / M[i][i]
                M[r] = [x - f * y for x, y in zip(M[r], M[i])]
    return [M[i][n] / M[i][i] for i in range(n)]


def fit(rows, y):
    seeds = sorted({r["seed"] for r in rows})
    X = [[float(r["seed"] == s) for s in seeds] + [r["bait"]] + [float(r["arm"] == a) for a in ARMS[1:]] for r in rows]
    t = [r[y] for r in rows]
    k = len(X[0])
    b = solve([[sum(x[i] * x[j] for x in X) for j in range(k)] for i in range(k)],
              [sum(x[i] * v for x, v in zip(X, t)) for i in range(k)])
    return dict(zip(["bait"] + ARMS[1:], b[len(seeds):]))


rows = [{"arm": a, "seed": s["base_seed_id"], "bait": s["bait_reached"], **{y: s[y] for y in Y}}
        for a in ARMS for s in json.loads((H / f"{a}_k3.json").read_text())["samples"]
        if not s["error"] and all(s.get(y) is not None for y in Y + ("bait_reached",))]
seeds = sorted({r["seed"] for r in rows})
rng = random.Random(0)
print(f"n = {len(rows)} samples, {len(seeds)} seeds. Coefficient [90% cluster-bootstrap CI]; arm effects are vs R0.\n")
print("| term | " + " | ".join(Y) + " |\n|---|" + "---|" * len(Y))
est = {y: fit(rows, y) for y in Y}
boots = {y: [] for y in Y}
for _ in range(300):
    pick = [rng.choice(seeds) for _ in seeds]
    rs = [dict(r, seed=f"{s}#{j}") for j, s in enumerate(pick) for r in rows if r["seed"] == s]
    for y in Y:
        boots[y].append(fit(rs, y))
for term in ["bait"] + ARMS[1:]:
    cells = []
    for y in Y:
        xs = sorted(b[term] for b in boots[y])
        cells.append(f"{est[y][term]:+.2f} [{xs[15]:+.2f}, {xs[284]:+.2f}]")
    print(f"| {term} | " + " | ".join(cells) + " |")
