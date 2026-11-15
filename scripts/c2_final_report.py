"""E3b final report on the screened seeds: every arm, strong subset first (results/prereg/E3b.json
strong_subset), then all 12; A1 (spontaneous / chain of thought), A2 (self-report) and Petri
eval_awareness separately; paired per seed vs stock and vs control (bootstrap 90% CI).

    python3 scripts/c2_final_report.py results/e3b/final_screened_*.json [--out results/e3b/final_report.md]
Several result files are merged (samples pooled per arm and seed, e.g. the 12-seed runs + the strong5 x2 repeat).
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def boot(diffs, n=4000, seed=0):
    if len(diffs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    ms = sorted(mean([rng.choice(diffs) for _ in diffs]) for _ in range(n))
    return ms[int(0.05 * n)], ms[int(0.95 * n)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    strong = set(json.loads(Path("results/prereg/E3b.json").read_text())["strong_subset"]["seeds"])
    # arm -> seed -> list of (A1, A2, petri, validity)
    data = defaultdict(lambda: defaultdict(list))
    errs = defaultdict(int)
    for f in a.files:
        rep = json.loads(Path(f).read_text())
        for arm, samples in rep["samples"].items():
            for s in samples:
                if s["behavior"] == "error":
                    errs[arm] += 1
                    continue
                p = (s.get("petri_scores") or {}).get("eval_awareness")
                data[arm][s["seed_id"].split("@")[0]].append(
                    (s["verbalized"], s["self_report"], p if isinstance(p, (int, float)) else float("nan"), s["validity"]))
    order = ["stock", "control"] + sorted(k for k in data if k not in ("stock", "control"))
    lines = []

    def table(label, seeds_filter):
        lines.append(f"\n### {label}\n")
        lines.append("| arm | n | A1 spontaneous | A2 self-report | Petri (1-10) | validity | A1 vs stock [90% CI] | A1 vs control [90% CI] | Petri vs stock |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        base = {}
        for ref in ("stock", "control"):
            base[ref] = {sd: mean([x[0] for x in v]) for sd, v in data.get(ref, {}).items() if seeds_filter(sd)}
        bpetri = {sd: mean([x[2] for x in v]) for sd, v in data.get("stock", {}).items() if seeds_filter(sd)}
        for arm in order:
            per = {sd: v for sd, v in data[arm].items() if seeds_filter(sd)}
            allx = [x for v in per.values() for x in v]
            if not allx:
                continue
            row = [arm, str(len(allx))] + [f"{mean([x[i] for x in allx]):.2f}" for i in (0, 1, 2, 3)]
            for ref in ("stock", "control"):
                if arm == ref:
                    row.append("-")
                    continue
                d = [mean([x[0] for x in per[sd]]) - base[ref][sd] for sd in per if sd in base[ref]]
                lo, hi = boot(d)
                row.append(f"{mean(d):+.2f} [{lo:+.2f}, {hi:+.2f}] (n={len(d)})" if d else "n/a")
            dp = [mean([x[2] for x in per[sd]]) - bpetri[sd] for sd in per if sd in bpetri]
            row.append("-" if arm == "stock" else (f"{mean(dp):+.2f}" if dp else "n/a"))
            lines.append("| " + " | ".join(row) + " |")

    lines.append("# E3b final: screened seeds, Kimi K2.6 (taste arms other than taste_real are one-shot picks)")
    table(f"Strong-awareness subset ({len(strong)} seeds, fixed before results)", lambda sd: sd in strong)
    table("All screened seeds", lambda sd: True)
    lines.append(f"\nerrored audits (excluded): {dict(errs)}")
    lines.append("\nPer seed A1 (mean over runs), strong subset:\n")
    seeds = sorted(strong, key=lambda s: int(s.split("_")[-1]))
    lines.append("| arm | " + " | ".join(s.replace("v2_seed_", "") for s in seeds) + " |")
    lines.append("|---|" + "---|" * len(seeds))
    for arm in order:
        cells = [f"{mean([x[0] for x in data[arm][sd]]):.2f}" if data[arm].get(sd) else "-" for sd in seeds]
        lines.append(f"| {arm} | " + " | ".join(cells) + " |")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n")


if __name__ == "__main__":
    main()
