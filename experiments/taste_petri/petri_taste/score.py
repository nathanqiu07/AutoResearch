"""Score petri_taste arms with ../real_material/rm_proxy.py's no-material path (identical to R0's scoring), and
compare them as PREREG.md says.

    python3 experiments/taste_petri/petri_taste/score.py run R0 TT TB TC --samples 3
    python3 experiments/taste_petri/petri_taste/score.py compare k3
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TP = HERE.parent
sys.path.insert(0, str(TP / "real_material"))
import rm_proxy as RP
import summarize as SU

RP.HERE = HERE
RP.CALLS_LOG = HERE / "calls.log"
RP.READ_CACHES = [TP / "proxy" / "cache", TP / "arms" / "cache"]
RP.BUDGET = 700
PAIRS = [("TT", "R0"), ("TB", "R0"), ("TC", "R0"), ("TB", "TT"), ("TC", "TT"), ("TB", "TC")]


def compare(tag):
    runs = {a: SU.load(HERE / "runs" / f"{a}_{tag}.json") for a in ("R0", "TT", "TB", "TC")}
    lv = ["| arm | n_ok | " + " | ".join(SU.SHOWN) + " |", "|---|---|" + "---|" * len(SU.SHOWN)]
    for a, r in runs.items():
        if r:
            lv.append(f"| {a} | {r['summary']['n_ok']}/{r['summary']['n']} | "
                      + " | ".join(SU.level(r, m) for m in SU.SHOWN) + " |")
    out = ["### Levels", *lv, "", "### Paired Δ (A − B per base seed; 90% bootstrap CI; P↓ = P(A lower))",
           "| A vs B | n seeds | " + " | ".join(f"Δ{m}" for m in SU.SHOWN) + " |", "|---|---|" + "---|" * len(SU.SHOWN)]
    for a, b in PAIRS:
        if runs[a] and runs[b]:
            c = SU.proxy_eval.compare(runs[b], runs[a])
            (HERE / "runs" / f"cmp_{a}_vs_{b}_{tag}.json").write_text(json.dumps(c, indent=1))
            n = max((x["n_seeds"] for x in c["metrics"].values()), default=0)
            out.append(f"| {a} vs {b} | {n} | " + " | ".join(SU.cell(c, m) for m in SU.SHOWN) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "run":
        k = int(rest[rest.index("--samples") + 1])
        for arm in [a for a in rest if not a.startswith("--") and not a.isdigit()]:
            RP.run(arm, k)
    else:
        print(compare(rest[0] if rest else "k3"))
