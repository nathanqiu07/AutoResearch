"""Paired comparisons of every arm vs stock and vs R0, as a markdown table (and compare JSONs in runs/).

    python3 experiments/taste_petri/arms/summarize.py k1      # runs/<arm>_k1.pj.json
    python3 experiments/taste_petri/arms/summarize.py k2      # runs/<arm>_k2.pj.json, where present
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "proxy"))
import proxy_eval  # noqa: E402
from proxy_eval import mean  # noqa: E402

ARMS = ["R0", "T1", "T2", "T3", "T4", "T5", "G1"]
proxy_eval.METRICS = ("a2", "a1", "validity", "bait_reached", "faithful", "pj_eval_awareness", "pj_audit_sa",
                      "pj_realism")


def load(name):
    p = HERE / "runs" / f"{name}.pj.json"
    return json.loads(p.read_text()) if p.exists() else None


def cell(c, m, digits=2):
    x = c["metrics"].get(m)
    if not x:
        return "n/a"
    lo, hi = x["ci90"] or (float("nan"), float("nan"))
    return f"{x['mean_diff']:+.{digits}f} [{lo:+.{digits}f}, {hi:+.{digits}f}] P(lower) {x["p_lower"]:.2f}"


def arm_mean(run, m):
    xs = [r[m] for r in run["samples"] if not r["error"] and r.get(m) is not None]
    return mean(xs) if xs else None


def table(tag, stock_name, r0_name):
    stock, r0 = load(stock_name), load(r0_name)
    rows_s = ["| arm | n_ok | len× | ΔA2 vs stock | ΔA1 | Δvalidity | faithful | bait | ΔPetri eval_aw | ΔPetri realism | valid win |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    rows_r = ["| arm | ΔA2 vs R0 | ΔA1 | Δvalidity | ΔPetri eval_aw | ΔPetri realism | Petri win vs R0 | valid win vs R0 |",
              "|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        run = load(f"{arm}_{tag}")
        if not run:
            continue
        seeds = [json.loads(l) for l in (HERE / "seeds" / f"{arm}.jsonl").read_text().splitlines()]
        lr = mean([s["len_ratio"] for s in seeds])
        cs = proxy_eval.compare(stock, run)
        (HERE / "runs" / f"cmp_{arm}_{tag}_vs_stock.json").write_text(json.dumps(cs, indent=1))
        faith, bait = arm_mean(run, "faithful"), arm_mean(run, "bait_reached")
        d = {m: cs["metrics"][m]["mean_diff"] for m in cs["metrics"]}
        win = d["a2"] < 0 and d["validity"] >= -0.05 and (faith or 0) >= 0.7
        rows_s.append(f"| {arm} | {run['summary']['n_ok']}/{run['summary']['n']} | {lr:.2f} | {cell(cs, 'a2')} | "
                      f"{cell(cs, 'a1')} | {cell(cs, 'validity')} | {faith:.2f} | {bait:.2f} | "
                      f"{cell(cs, 'pj_eval_awareness', 1)} | {cell(cs, 'pj_realism', 1)} | {'YES' if win else 'no'} |")
        if arm == "R0":
            continue
        cr = proxy_eval.compare(r0, run)
        (HERE / "runs" / f"cmp_{arm}_{tag}_vs_R0.json").write_text(json.dumps(cr, indent=1))
        e = {m: cr["metrics"][m]["mean_diff"] for m in cr["metrics"]}
        pwin = e["pj_eval_awareness"] < 0 and e["pj_realism"] > 0 and e["validity"] >= -0.05
        vwin = e["a2"] < 0 and e["validity"] >= -0.05 and (faith or 0) >= 0.7
        rows_r.append(f"| {arm} | {cell(cr, 'a2')} | {cell(cr, 'a1')} | {cell(cr, 'validity')} | "
                      f"{cell(cr, 'pj_eval_awareness', 1)} | {cell(cr, 'pj_realism', 1)} | {'YES' if pwin else 'no'} | "
                      f"{'YES' if vwin else 'no'} |")
    lvl = ["| run | A2 | A1 | validity | bait | Petri eval_aw | Petri realism |", "|---|---|---|---|---|---|---|"]
    for name in [stock_name] + [f"{a}_{tag}" for a in ARMS]:
        run = load(name)
        if run:
            lvl.append(f"| {name} | " + " | ".join(
                f"{arm_mean(run, m):.2f}" for m in ("a2", "a1", "validity", "bait_reached", "pj_eval_awareness",
                                                     "pj_realism")) + " |")
    return "\n".join(["### Levels", *lvl, "", "### vs stock", *rows_s, "", "### vs R0 (taste vs generic realism)", *rows_r])


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "k1"
    print(table(tag, "stock_dev_k2", f"R0_{tag}"))
