"""Held-out evaluation of a run's final design (E4 primary metric, PLAN 7.3 / 9).

A research run optimises on dev items with the dev target and judge. Its
result for E4 is the score of its final intervention set on *held-out* items,
measured in final mode (held-out target and judges), paired by item against
the untouched items. Optionally each intervention of the design is also
measured alone, which gives the held-out evidence that "transfers" claims need
(`claims.py`).

This module only reads a finished report; it never feeds back into a run.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .claims import check_all
from .multi import ItemPool, paired_compare, per_item_table, pooled_ci

SEED_BASE = 10_000_000   # held-out samples use seeds no run uses (runs use seed * 100000 + k)


def _scores(pairs):
    ok = [(i, s) for i, s in pairs if s.behavior != "error"]
    return [s.score for _, s in ok], [i for i, _ in ok], len(pairs) - len(ok)


def evaluate_design(report: dict, pool: ItemPool, samples_per_item: int = 3, seed: int = 0,
                    per_intervention: bool = False, items: Optional[List[str]] = None) -> dict:
    design = report.get("best_design") or []
    texts, cats = [d["text"] for d in design], [d["category"] for d in design]
    items = list(items or pool.ids)
    counter = [SEED_BASE + seed * 100000]

    def seeds():
        n = samples_per_item * len(items)
        s = list(range(counter[0], counter[0] + n))
        counter[0] += n
        return s

    def measure(t, c):
        return _scores(pool.measure(t, seeds(), c, items))

    bs, bi, berr = measure([], None)
    out = {"run_id": report.get("run_id"), "arm": report.get("arm"), "scenario": report.get("scenario"),
           "design": design, "mode": pool.mode, "items": items, "samples_per_item": samples_per_item,
           "baseline_errors": berr}
    if not design:
        out.update({"pooled_delta": 0.0, "p_better": None, "note": "run validated no intervention; design = baseline"})
    else:
        ds, di, derr = measure(texts, cats)
        p, d, per = paired_compare(ds, di, bs, bi, seed=seed)
        out.update({"pooled_delta": d, "p_better": p, "ci90_paired": pooled_ci(per) if len(per) > 1 else None,
                    "design_errors": derr, "per_item": per_item_table(bs, bi, ds, di)})
    findings = [dict(f) for f in report.get("findings", [])]
    if per_intervention and design:
        singles: Dict[str, dict] = {}
        for t, c in zip(texts, cats):
            ss, si, serr = measure([t], [c])
            p, d, per = paired_compare(ss, si, bs, bi, seed=seed + 1)
            singles[t] = {"category": c, "heldout_delta": d, "heldout_p_better": p, "errors": serr}
        out["per_intervention"] = singles
        for f in findings:
            if f.get("move", "").startswith("add") and f.get("status") == "validated" and f.get("text") in singles:
                f["heldout_delta"] = singles[f["text"]]["heldout_delta"]
                f["heldout_p_better"] = singles[f["text"]]["heldout_p_better"]
        transfer = [{"text": f"[{f['category']}] {f['text'][:100]} transfers to held-out items "
                             f"(held-out delta {f['heldout_delta']:+.3f})",
                     "kind": "transfers", "finding_ids": [f["id"]]}
                    for f in findings if "heldout_delta" in f and "id" in f]
        out["transfer_claims"] = check_all(transfer, findings)
    out["findings"] = findings
    out["warnings"] = pool.warnings
    return out


def format_heldout(res: dict) -> str:
    fmt = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
    L = [f"# Held-out evaluation: {res.get('scenario')} run {res.get('run_id')} ({res.get('arm')})", "",
         f"Mode {res['mode']}; {len(res['items'])} items x {res['samples_per_item']} samples, paired by item.", "",
         f"Pooled delta (design minus untouched items): {fmt(res.get('pooled_delta'))}; "
         f"P(design better) {fmt(res.get('p_better'))}; paired 90% CI {res.get('ci90_paired')}.", ""]
    if res.get("per_item"):
        L += ["| item | baseline | design | delta |", "|---|---|---|---|"]
        L += [f"| {i} | {fmt(r['baseline'])} | {fmt(r['best'])} | {fmt(r['delta'])} |" for i, r in res["per_item"].items()]
    if res.get("per_intervention"):
        L += ["", "| intervention alone | held-out delta | P(better) |", "|---|---|---|"]
        L += [f"| [{v['category']}] {t[:90]} | {fmt(v['heldout_delta'])} | {fmt(v['heldout_p_better'])} |"
              for t, v in res["per_intervention"].items()]
        tc = res.get("transfer_claims") or {}
        if tc.get("n"):
            L += ["", f"Transfer claims supported: {tc['supported']} of {tc['n']}."]
    if res.get("warnings"):
        L += ["", "Warnings:"] + [f"- {w}" for w in res["warnings"]]
    return "\n".join(L) + "\n"
