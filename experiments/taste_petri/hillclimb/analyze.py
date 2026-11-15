"""Per-seed failure analysis of an arm against R0 (dev): mean per-seed metrics side by side, the objective J and the
guards, plus the Petri-judge's realism tells for the arm's samples.

    python3 experiments/taste_petri/hillclimb/analyze.py H1 [--base R0] [--split dev] [--tells]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hc  # noqa: E402

SHOW = ("score", "a2", "a1", "validity", "bait_reached", "opportunity", "scorable", "faithful", "pj_realism",
        "pj_eval_awareness")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--base", default="R0")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--tells", action="store_true")
    a = ap.parse_args()
    base, arm = hc.load_scores(a.base, a.split), hc.load_scores(a.arm, a.split)
    pb = {m: hc.per_seed(base, m) for m in SHOW}
    pa = {m: hc.per_seed(arm, m) for m in SHOW}
    seeds = sorted(set(pb["score"]) | set(pa["score"]))
    print(f"| seed | n {a.base}/{a.arm} | " + " | ".join(SHOW) + " |")
    print("|---|---|" + "---|" * len(SHOW))
    for s in seeds:
        nb = sum(r["base_seed_id"] == s for r in base)
        na = sum(r["base_seed_id"] == s for r in arm)
        cells = []
        for m in SHOW:
            x, y = pb[m].get(s), pa[m].get(s)
            f = (lambda v: "-" if v is None else f"{v:.1f}") if m.startswith("pj_") else \
                (lambda v: "-" if v is None else f"{v:.2f}")
            cells.append(f"{f(x)}→{f(y)}")
        print(f"| {s} | {nb}/{na} | " + " | ".join(cells) + " |")
    c = hc.compare_rows(base, arm)
    j = c["score"]
    print(f"\nJ = Δscore {j['diff']:+.3f} [{j['ci90'][0]:+.3f}, {j['ci90'][1]:+.3f}] over {j['n']} seeds; "
          f"faithful {c['faithful']['other']:.2f}; ΔPJ eval_aw {c['pj_eval_awareness']['diff']:+.2f}; "
          f"Δvalidity {c['validity']['diff']:+.3f}; ΔA2 {c['a2']['diff']:+.3f}; ΔPJ realism {c['pj_realism']['diff']:+.2f}")
    if a.tells:
        for r in sorted(arm, key=lambda r: (r["base_seed_id"], r["k"])):
            print(f"- {r['base_seed_id']} k{r['k']} val={r.get('validity', 0):.2f} a2={r.get('a2', 0):.2f}: "
                  f"{r.get('pj_tells', '')[:220]}")


if __name__ == "__main__":
    main()
