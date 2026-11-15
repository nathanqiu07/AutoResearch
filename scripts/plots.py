"""Charts, tables and the results summary (PLAN 12.5 item 7; E4, E5, E1/E2, E3b).

Reads committed run outputs only (no model calls):

    python3 scripts/plots.py summary results/e5 [--out results/e5]   # tables + summary.md (no matplotlib needed)
    python3 scripts/plots.py all results/e5 [--out results/e5]       # summary + every chart the data supports
    python3 scripts/plots.py fidelity results/e1/report.json --ceiling 0.82 --out results/e1

Charts (matplotlib, scripts/requirements-plots.txt):
  anytime.png       best dev score against cumulative $, one line per arm (mean over seeds)  [main chart]
  a1_a2.png         the 2x2 table of runs by whether A1 and A2 dropped (baseline -> best)
  allocation.png    market vs uniform vs halving: $ per validated finding, and bid calibration per agent
  tools.png         real (sandbox) vs simulated tools: A1 and A2 per tool mode (agentic runs)
  fidelity.png      held-out accuracy per user-model method against the noise ceiling (E1/E2)

summary.md lists every run with its arm, seed, sample counts and CODE_VERSION, the
E5 table and the A1 x A2 table, so the README can link real numbers. Offline
simulator runs are labelled as such and must never be read as real-model numbers.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from autoresearch.research.stats import bootstrap_ci, mean  # noqa: E402


# ---------- loading ----------
def load_runs(paths: List[str]) -> List[dict]:
    """Every run report under the paths, with its held-out evaluation if present."""
    rows = []
    for p in paths:
        files = [p] if os.path.isfile(p) else sorted(os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs)
        for f in files:
            if not f.endswith(".json") or "_heldout_" in os.path.basename(f):
                continue
            try:
                with open(f) as fh:
                    rep = json.load(fh)
            except (OSError, ValueError):
                continue
            if not (isinstance(rep, dict) and "run_id" in rep and "best" in rep and "baseline" in rep):
                continue
            held = None
            for mode in ("final", "dev"):
                h = os.path.splitext(f)[0] + f"_heldout_{mode}.json"
                if os.path.exists(h):
                    with open(h) as fh:
                        held = {"mode": mode, **json.load(fh)}
                    break
            cfg = rep.get("config") or {}
            rows.append({"path": os.path.relpath(f, ROOT), "rep": rep, "heldout": held,
                         "arm": rep.get("arm") or "?", "seed": cfg.get("seed"),
                         "code_version": rep.get("code_version", "unknown"),
                         "offline": _offline(rep)})
    return rows


def _offline(rep: dict) -> bool:
    c = rep.get("compute") or {}
    return c.get("cost_usd", 0) == 0 and c.get("input_tokens", 0) == 0


def validated(rep: dict) -> int:
    return sum(f.get("status") == "validated" for f in rep.get("findings", []))


def first_validated(rep: dict) -> Optional[dict]:
    """The anytime point at which the first validated finding appeared."""
    for p in rep.get("anytime") or []:
        if p.get("validated"):
            return p
    return None


def by_arm(rows: List[dict]) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}
    for r in rows:
        out.setdefault(r["arm"], []).append(r)
    return dict(sorted(out.items()))


def _fmt(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def _ci(xs, nd=3) -> str:
    if len(xs) < 2:
        return "n/a"
    lo, hi = bootstrap_ci(xs, level=0.9, seed=0)
    return f"[{_fmt(lo, nd)}, {_fmt(hi, nd)}]"


# ---------- tables ----------
def e5_table(rows: List[dict]) -> List[str]:
    """$ per validated finding per arm (ratio of totals over seeds), time and $ to
    the first validated finding, final dev score and held-out delta."""
    L = ["| arm | runs | validated | $ total | $ per validated finding | $ to first (mean) | s to first (mean) "
         "| final dev score (90% CI) | held-out delta (90% CI) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for arm, rs in by_arm(rows).items():
        cost = [r["rep"].get("compute", {}).get("cost_usd", 0.0) or 0.0 for r in rs]
        nval = [validated(r["rep"]) for r in rs]
        firsts = [first_validated(r["rep"]) for r in rs]
        f_cost = [p["cost_usd"] for p in firsts if p and p.get("cost_usd") is not None]
        f_sec = [p["seconds"] for p in firsts if p and p.get("seconds") is not None]
        score = [r["rep"]["best"]["score"] for r in rs if r["rep"]["best"].get("score") is not None]
        held = [r["heldout"].get("pooled_delta") for r in rs if r["heldout"] and r["heldout"].get("pooled_delta") is not None]
        if not sum(nval):
            per = "no finding"
        elif sum(cost) <= 0:
            per = "n/a (no spend recorded)"
        else:
            per = _fmt(sum(cost) / sum(nval), 2)
        L.append(f"| {arm} | {len(rs)} | {sum(nval)} | {_fmt(sum(cost), 2)} | {per} "
                 f"| {_fmt(mean(f_cost), 2) if f_cost else 'n/a'} ({len(f_cost)}/{len(rs)}) "
                 f"| {_fmt(mean(f_sec), 0) if f_sec else 'n/a'} | {_fmt(mean(score))} {_ci(score)} "
                 f"| {(_fmt(mean(held)) + ' ' + _ci(held)) if held else 'n/a'} |")
    return L


def a1a2_quadrants(rows: List[dict]) -> Dict[str, Dict[str, int]]:
    """Per arm, runs by whether A1 (verbalized) and A2 (self-report) fell from baseline to best."""
    out = {}
    for arm, rs in by_arm(rows).items():
        q = {"both": 0, "A1 only": 0, "A2 only": 0, "neither": 0}
        for r in rs:
            b, f = r["rep"]["baseline"], r["rep"]["best"]
            d1 = (f.get("verbalized") or 0) < (b.get("verbalized") or 0)
            d2 = (f.get("self_report") or 0) < (b.get("self_report") or 0)
            q["both" if d1 and d2 else "A1 only" if d1 else "A2 only" if d2 else "neither"] += 1
        out[arm] = q
    return out


def a1a2_table(rows: List[dict]) -> List[str]:
    L = ["| arm | A1 and A2 dropped | only A1 | only A2 | neither | mean A1 base -> best | mean A2 base -> best |",
         "|---|---|---|---|---|---|---|"]
    quads = a1a2_quadrants(rows)
    for arm, rs in by_arm(rows).items():
        q = quads[arm]
        a1 = [(r["rep"]["baseline"].get("verbalized"), r["rep"]["best"].get("verbalized")) for r in rs]
        a2 = [(r["rep"]["baseline"].get("self_report"), r["rep"]["best"].get("self_report")) for r in rs]
        m = lambda xs, k: mean([x[k] for x in xs if x[k] is not None])  # noqa: E731
        L.append(f"| {arm} | {q['both']} | {q['A1 only']} | {q['A2 only']} | {q['neither']} "
                 f"| {_fmt(m(a1, 0))} -> {_fmt(m(a1, 1))} | {_fmt(m(a2, 0))} -> {_fmt(m(a2, 1))} |")
    return L


def runs_table(rows: List[dict]) -> List[str]:
    L = ["| arm | seed | iterations | samples | allocation | validated | calls | $ | CODE_VERSION | backend | report |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["arm"], r["seed"] if r["seed"] is not None else -1)):
        cfg, c = r["rep"].get("config") or {}, r["rep"].get("compute") or {}
        L.append(f"| {r['arm']} | {r['seed']} | {cfg.get('iterations')} | {cfg.get('samples')} "
                 f"| {cfg.get('allocation', 'uniform')} | {validated(r['rep'])} | {c.get('calls')} "
                 f"| {_fmt(c.get('cost_usd'), 2)} | `{r['code_version']}` "
                 f"| {'offline simulator' if r['offline'] else 'live models'} | {r['path']} |")
    return L


def summary_md(rows: List[dict], title: str) -> str:
    versions = sorted({r["code_version"] for r in rows})
    off = sum(r["offline"] for r in rows)
    L = [f"# {title}", "",
         f"{len(rows)} run(s), {len(by_arm(rows))} arm(s); code version(s): " + ", ".join(f"`{v}`" for v in versions) + ".",
         ""]
    if off:
        L += [f"**{off} of these runs used the offline simulator. Their numbers test the pipeline only and are not "
              "real-model results.**", ""]
    if len(versions) > 1:
        L += ["**Warning: runs from more than one code version are mixed here.**", ""]
    L += ["## Cost and findings by arm (E5)", ""] + e5_table(rows)
    L += ["", "## A1 (verbalized awareness) x A2 (direct-question P(eval)), baseline -> best design", ""] + a1a2_table(rows)
    L += ["", "## Every run", ""] + runs_table(rows) + [""]
    return "\n".join(L)


# ---------- charts ----------
def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        raise SystemExit("charts need matplotlib: pip install -r scripts/requirements-plots.txt")


def anytime_curves(rows: List[dict], x: str = "cost_usd", grid_n: int = 50) -> Dict[str, dict]:
    """Per arm: x grid and the mean (over seeds) best score at each x, a run's
    score being its best so far at that spend (step function). The x axis falls
    back from $ to calls to dev samples when nothing was spent on it (offline)."""
    curves = {}
    pts = [p for r in rows for p in (r["rep"].get("anytime") or [])]
    for key in (x, "calls", "samples"):
        if any((p.get(key) or 0) > 0 for p in pts):
            x = key
            break
    for arm, rs in by_arm(rows).items():
        series = [[(p.get(x) or 0, p["best_score"]) for p in r["rep"].get("anytime") or [] if p.get("best_score") is not None]
                  for r in rs]
        series = [s for s in series if s]
        if not series:
            continue
        top = max(s[-1][0] for s in series)
        xs = [top * k / (grid_n - 1) for k in range(grid_n)] if top > 0 else [0.0]
        ys, lo, hi = [], [], []
        for xv in xs:
            vals = []
            for s in series:
                at = [y for xx, y in s if xx <= xv]
                if at:
                    vals.append(at[-1])
            m = mean(vals) if vals else float("nan")
            ys.append(m)
            c = bootstrap_ci(vals, level=0.9, seed=0) if len(vals) >= 2 else (m, m)
            lo.append(c[0])
            hi.append(c[1])
        curves[arm] = {"x": xs, "y": ys, "lo": lo, "hi": hi, "n": len(series)}
    return {"x_key": x, "curves": curves}


def chart_anytime(rows, out_dir) -> Optional[str]:
    data = anytime_curves(rows)
    if not data["curves"]:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for arm, c in data["curves"].items():
        ax.plot(c["x"], c["y"], label=f"{arm} (n={c['n']})")
        ax.fill_between(c["x"], c["lo"], c["hi"], alpha=0.15)
    ax.set_xlabel({"cost_usd": "cumulative $", "calls": "cumulative model calls",
                   "samples": "cumulative dev samples (no $ recorded)"}.get(data["x_key"], data["x_key"]))
    ax.set_ylabel("best dev score so far")
    ax.set_title("Anytime curve: score against spend (mean, 90% CI over seeds)")
    ax.legend(frameon=False)
    return _save(fig, plt, out_dir, "anytime.png", offline=any(r["offline"] for r in rows))


def chart_a1a2(rows, out_dir) -> Optional[str]:
    quads = a1a2_quadrants(rows)
    if not quads:
        return None
    plt = _plt()
    arms = list(quads)
    fig, axes = plt.subplots(1, len(arms), figsize=(2.6 * len(arms) + 0.6, 2.9), squeeze=False)
    for ax, arm in zip(axes[0], arms):
        q = quads[arm]
        m = [[q["both"], q["A2 only"]], [q["A1 only"], q["neither"]]]
        top = max(1, max(max(r) for r in m))
        ax.imshow(m, cmap="Blues", vmin=0, vmax=top)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(m[i][j]), ha="center", va="center",
                        color="white" if m[i][j] > top / 2 else "black")
        ax.set_xticks([0, 1], ["A2 dropped", "A2 not"])
        ax.set_yticks([0, 1], ["A1 dropped", "A1 not"])
        ax.set_title(arm, fontsize=9)
    fig.suptitle("Runs by A1 and A2 change, baseline -> best", fontsize=10)
    return _save(fig, plt, out_dir, "a1_a2.png", offline=any(r["offline"] for r in rows))


def chart_allocation(rows, out_dir) -> Optional[str]:
    arms = by_arm(rows)
    if not any((r["rep"].get("allocation") or {}).get("mode") not in (None, "uniform") for r in rows):
        return None
    plt = _plt()
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4))
    def spend(r):   # $, or samples when no $ was recorded (offline)
        if use_cost:
            return (r["rep"].get("compute") or {}).get("cost_usd", 0) or 0
        al = r["rep"].get("allocation") or {}
        return (al.get("samples") or 0) + (al.get("screen_samples") or 0)
    use_cost = any(((r["rep"].get("compute") or {}).get("cost_usd") or 0) > 0 for r in rows)
    names, vals = [], []
    for arm, rs in arms.items():
        n = sum(validated(r["rep"]) for r in rs)
        names.append(arm)
        vals.append(sum(spend(r) for r in rs) / n if n else float("nan"))
    a.bar(names, vals)
    a.set_ylabel(("$" if use_cost else "samples (no $ recorded)") + " per validated finding\n(lower is better)")
    a.set_title("Allocation arms")
    agents: Dict[str, List[float]] = {}
    for r in rows:
        for e in ((r["rep"].get("market") or {}).get("ledger") or []):
            if e.get("event") == "settle":
                agents.setdefault(e["agent"], []).append((e["p_validated"] - float(e["outcome"])) ** 2)
    if agents:
        ks = sorted(agents)
        b.bar(ks, [mean(agents[k]) for k in ks])
        b.axhline(0.25, ls="--", lw=1, color="grey")
        b.set_ylabel("Brier score of bids (0.25 = always 0.5)")
        b.set_title("Market: calibration by agent")
    else:
        b.axis("off")
    return _save(fig, plt, out_dir, "allocation.png", offline=any(r["offline"] for r in rows))


def chart_tools(rows, out_dir) -> Optional[str]:
    groups: Dict[str, List[dict]] = {}
    for r in rows:
        t = r["rep"].get("tools")
        if t:
            groups.setdefault(t, []).append(r["rep"]["best"])
    if not groups:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6, 4))
    ks = sorted(groups)
    w = 0.38
    for k, key, lab in ((0, "verbalized", "A1 verbalized"), (1, "self_report", "A2 self-report P(eval)")):
        ax.bar([i + (k - 0.5) * w for i in range(len(ks))],
               [mean([s.get(key) for s in groups[t] if s.get(key) is not None]) for t in ks], w, label=lab)
    ax.set_xticks(range(len(ks)), [f"{t} (n={len(groups[t])})" for t in ks])
    ax.set_ylabel("awareness of the best design (lower is better)")
    ax.set_title("Real (sandbox) vs simulated tools")
    ax.legend(frameon=False)
    return _save(fig, plt, out_dir, "tools.png", offline=any(r["offline"] for r in rows))


def chart_fidelity(report: dict, ceiling: Optional[float], out_dir) -> str:
    plt = _plt()
    methods = report.get("methods") or {}
    ks = sorted(methods)
    acc = [methods[k]["accuracy"] for k in ks]
    err = [[a - methods[k]["ci95"][0] for k, a in zip(ks, acc)], [methods[k]["ci95"][1] - a for k, a in zip(ks, acc)]]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(ks, acc, yerr=err, capsize=3)
    ax.axhline(0.5, ls=":", lw=1, color="grey", label="chance")
    if ceiling is not None:
        ax.axhline(ceiling, ls="--", lw=1.2, color="black", label=f"noise ceiling ({ceiling:.2f})")
    ax.set_ylim(0, 1)
    ax.set_ylabel("held-out pairwise accuracy (95% CI)")
    ax.set_title("User-model fidelity against the noise ceiling")
    ax.legend(frameon=False)
    return _save(fig, plt, out_dir, "fidelity.png")


def _save(fig, plt, out_dir, name, offline=False) -> str:
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, name)
    fig.tight_layout()
    if offline:
        fig.text(0.5, -0.01, "Includes OFFLINE SIMULATOR data: pipeline check only, not real-model findings",
                 ha="center", fontsize=9, color="darkred")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["summary", "all", "fidelity"])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", help="output directory (default: the first path)")
    ap.add_argument("--title")
    ap.add_argument("--ceiling", help="fidelity: noise-ceiling accuracy, or a JSON file with 'self_agreement'")
    args = ap.parse_args(argv)
    out = args.out or (args.paths[0] if os.path.isdir(args.paths[0]) else os.path.dirname(args.paths[0]))
    if args.what == "fidelity":
        with open(args.paths[0]) as f:
            rep = json.load(f)
        ceiling = None
        if args.ceiling:
            if os.path.exists(args.ceiling):
                with open(args.ceiling) as f:
                    ceiling = float(json.load(f)["self_agreement"])
            else:
                ceiling = float(args.ceiling)
        print("wrote", chart_fidelity(rep, ceiling, out))
        return 0
    rows = load_runs(args.paths)
    if not rows:
        raise SystemExit(f"no run reports under {args.paths}")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, "summary.md")
    with open(p, "w") as f:
        f.write(summary_md(rows, args.title or f"Results: {', '.join(os.path.relpath(x, ROOT) for x in args.paths)}"))
    print("wrote", p)
    if args.what == "all":
        for fn in (chart_anytime, chart_a1a2, chart_allocation, chart_tools):
            r = fn(rows, out)
            if r:
                print("wrote", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
