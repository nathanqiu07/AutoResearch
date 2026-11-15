"""Deadline report over whatever test_<ARM>.json exist: paired accuracy and mean p(his), 90% cluster CIs over works,
and each profile arm minus M0s / NAME (fit.py's report rules; pairs with a failed prediction in any arm dropped)."""
import collections
import json
import os

import common as C

F = C.synthme_fit()
ORDER = ["M0s", "NAME", "S_paper_lite", "S_inf_lite", "S_paper", "S_inf", "S_all", "ANTI0"]
arms = [a for a in ORDER if os.path.exists(os.path.join(C.HERE, f"test_{a}.json"))]
tests = {a: json.load(open(os.path.join(C.HERE, f"test_{a}.json"))) for a in arms}
work = {r["pair_id"]: r["work"] for r in F.test_pairs()}
failed = {x["pair_id"] for t in tests.values() for x in t["predictions"] if x["correct"] is None}
g = {a: collections.defaultdict(list) for a in arms}
gp = {a: collections.defaultdict(list) for a in arms}
for a, t in tests.items():
    for x in t["predictions"]:
        if x["pair_id"] not in failed:
            g[a][work[x["pair_id"]]].append(bool(x["correct"]))
            gp[a][work[x["pair_id"]]].append(sum(x["p_his"]) / 2)
n = len(work) - len(failed)
lines = [f"# SynthesizeMe for Marius Hobbhahn (swe-2-medium via devin-cli, deadline run)", "",
         f"Test pairs: {n} of {len(work)} (failed predictions dropped: {len(failed)}), works: {len({work[k] for k in work if k not in failed})}.",
         "Paired accuracy = his option chosen in both orders. 90% CIs resample works.", "",
         "| arm | words | paired acc [90% CI] | mean p(his) [90% CI] |", "|---|---|---|---|"]
for a in arms:
    acc, ph = F._acc(g[a]), F._acc(gp[a])
    lines.append(f"| {a} | {tests[a]['profile_words']} | {acc['value']:.3f} {acc['ci90']} | {ph['value']:.3f} {ph['ci90']} |")
def cell(d):
    text = f"{d['diff']:+.3f} {d['ci90']}"
    return f"**{text}**" if d["ci90"][0] > 0 or d["ci90"][1] < 0 else text


sig = []
lines += ["", "Bold = 90% CI excludes 0.", "", "| arm | Δacc vs M0s | Δp(his) vs M0s | Δacc vs NAME | Δp(his) vs NAME |", "|---|---|---|---|---|"]
for a in arms:
    if a == "M0s":
        continue
    cells = []
    for c in ("M0s", "NAME"):
        if c in arms and c != a:
            for m, d in (("paired acc", F._diff(g[a], g[c])), ("mean p(his)", F._diff(gp[a], gp[c]))):
                cells.append(cell(d))
                if d["ci90"][0] > 0 or d["ci90"][1] < 0:
                    sig.append(f"- {a} vs {c}, {m}: {d['diff']:+.3f} {d['ci90']} "
                               f"({'better' if d['diff'] > 0 else 'worse'} than {c})")
        else:
            cells += ["–", "–"]
    lines.append(f"| {a} | " + " | ".join(cells) + " |")
lines += ["", "## Significant results (90% CI excludes 0)", ""] + (sig or ["- none"]) + [
    "", f"CIs resample {len({work[k] for k in work if k not in failed})} works, so they are likely too narrow "
    "(decoys/ A/A check: few-cluster bootstrap CIs are overconfident). The lite personas skip SynthesizeMe's "
    "validation selection (deadline shortcut, lite.py); every call is swe-2-medium."]
md = "\n".join(lines) + "\n"
open(os.path.join(C.HERE, "results.md"), "w").write(md)
print(md)
