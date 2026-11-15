"""Paired comparisons of the real-material arms vs stock and vs R0 (arms/runs, read-only), as markdown.

    python3 experiments/taste_petri/real_material/summarize.py k1
    python3 experiments/taste_petri/real_material/summarize.py k2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TP = HERE.parent
sys.path.insert(0, str(TP / "proxy"))
import proxy_eval
from proxy_eval import mean

ARMS = ["RM1", "RM2", "RM3", "TRM"]
SHOWN = ("pj_eval_awareness", "pj_realism", "a2", "a1", "validity", "faithful", "bait_reached")
proxy_eval.METRICS = SHOWN


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def cell(c, m):
    x = c["metrics"].get(m)
    if not x:
        return "n/a"
    d = 1 if m.startswith("pj_") else 2
    lo, hi = x["ci90"] or (float("nan"), float("nan"))
    return f"{x['mean_diff']:+.{d}f} [{lo:+.{d}f}, {hi:+.{d}f}] P↓{x['p_lower']:.2f}"


def level(run, m, keep=None):
    xs = [r[m] for r in run["samples"] if not r["error"] and r.get(m) is not None
          and (keep is None or r["base_seed_id"] in keep)]
    return f"{mean(xs):.2f}" if xs else "n/a"


def subset(run, keep):
    return {**run, "samples": [r for r in run["samples"] if r["base_seed_id"] in keep]}


def table(tag):
    stock = load(TP / "arms" / "runs" / "stock_dev_k2.pj.json")
    r0 = load(TP / "arms" / "runs" / f"R0_{tag}.pj.json") or load(TP / "arms" / "runs" / "R0_k1.pj.json")
    out = [f"R0 reference: {r0['condition']} k={r0['samples_per_seed']}; stock: stock_dev_k2", ""]
    lv = ["| run | n_ok | " + " | ".join(SHOWN) + " |", "|---|---|" + "---|" * len(SHOWN)]
    for name, run in [("stock", stock), ("R0", r0)]:
        lv.append(f"| {name} | {run['summary']['n_ok']}/{run['summary']['n']} | "
                  + " | ".join(level(run, m) for m in SHOWN) + " |")
    dif = {"stock": [], "R0": [], "R0 fitted": []}
    hdr = "| arm | n seeds | " + " | ".join(f"Δ{m}" for m in SHOWN) + " |"
    for arm in ARMS:
        run = load(HERE / "runs" / f"{arm}_{tag}.json")
        if not run:
            continue
        seeds = [json.loads(l) for l in (HERE / "seeds" / f"{arm}.jsonl").read_text().splitlines()]
        fitted = {s["base_seed_id"] for s in seeds if s["changed_vs_R0"]}
        lv.append(f"| {arm} | {run['summary']['n_ok']}/{run['summary']['n']} | "
                  + " | ".join(level(run, m) for m in SHOWN) + " |")
        for key, base, other in [("stock", stock, run), ("R0", r0, run),
                                 ("R0 fitted", subset(r0, fitted), subset(run, fitted))]:
            c = proxy_eval.compare(base, other)
            (HERE / "runs" / f"cmp_{arm}_{tag}_vs_{key.replace(' ', '_')}.json").write_text(json.dumps(c, indent=1))
            n = max((x["n_seeds"] for x in c["metrics"].values()), default=0)
            dif[key].append(f"| {arm} | {n} | " + " | ".join(cell(c, m) for m in SHOWN) + " |")
    sep = "|---|---|" + "---|" * len(SHOWN)
    for key, rows in dif.items():
        out += ["", f"### Δ vs {key} (paired per base seed; 90% bootstrap CI; P↓ = P(arm lower))", hdr, sep, *rows]
    return "\n".join(["### Levels", *lv, *out])


if __name__ == "__main__":
    print(table(sys.argv[1] if len(sys.argv) > 1 else "k1"))
