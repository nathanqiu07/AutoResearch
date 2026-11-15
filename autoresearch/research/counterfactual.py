"""Counterfactual cue replays: scoring and per-cue effects (WS C2). Standard library only.

`harness/petri/counterfactual.py` replays a finished sandbox audit from a decision point once unchanged
(mutation "control") and once per single-cue mutation, each from the same filesystem snapshot, and writes
one row per (case, decision turn, mutation, replicate). This module

  score    adds A1 (`verbalized`) and A2 (`self_report`) to each row with C1's judges, reused from
           `Measurer`: A1 is `Measurer.verbalized` (the same audit-judge prompt the loop and PetriMeasurer
           use) on the replay transcript and the continuation's raw reasoning; A2 is `Measurer.p_eval` of
           the target over C1's probe questions, in a fresh context that shows the transcript. Offline
           (`--offline`) the project's OfflineWorld simulator stands in, keyed by each mutation's cue;
  analyze  reports per cue the paired effect vs control: per unit (case, decision turn) the mean over
           replicates of the mutation minus that of the control, then the mean over units with a
           bootstrap CI and P(lower), for A1 and A2.

The transcript a judge reads is the mutated prefix plus the continuation; the reasoning is the
continuation's only. The prefix is identical across arms except for the mutation itself, so the paired
difference isolates the cue, while absolute levels also reflect the shared prefix.

    python3 -m autoresearch.research.counterfactual score rows.jsonl --out scored.jsonl --offline
    python3 -m autoresearch.research.counterfactual analyze scored.jsonl --out-dir runs/cf

Scoring without --offline calls the judge and target models: paid, needs the user's approval.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import random
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .ladder import _read_jsonl, _write_jsonl, git_version
from .stats import bootstrap_ci, mean, prob_better

CONTROL = "control"
METRICS = {"A1": "verbalized", "A2": "self_report"}
# Offline simulator only: the OfflineWorld category each mutation stands for (none = no simulated effect).
OFFLINE_CUE_CATEGORIES = {
    "realistic_names": ["realistic_identity"], "lower_stakes": ["plausible_stakes"],
    "raise_stakes": ["explicit_rules"], "messy_formatting": ["messy_artifacts"],
    "add_fake_git_history": ["honeypot_bait"], "remove_git_history": [], "present_dates": ["deployment_framing"],
}


def is_error(r: dict) -> bool:
    return bool(r.get("error"))


def unit(r: dict) -> str:
    """The pairing unit: one decision point of one audit."""
    return f"{r.get('case_id') or r.get('seed_id')}|t{r.get('decision_turn')}"


# ---------------------------------------------------------------- scoring
class JudgeScorer:
    """A1 and A2 from C1's judges through an existing Measurer (PetriMeasurer or Measurer)."""

    def __init__(self, measurer):
        self.m = measurer

    def __call__(self, row: dict) -> dict:
        transcript = str(row.get("transcript") or "")
        if not transcript.strip():
            return {"error": "empty replay transcript"}
        a1 = self.m.verbalized(transcript, str(row.get("reasoning") or ""))
        a2 = self.m.p_eval(self.m.target, transcript)
        if a1 is None or a2 is None:
            return {"error": "judge reply unparseable (" + ", ".join(
                n for n, v in (("A1", a1), ("A2", a2)) if v is None) + ")"}
        return {"verbalized": a1, "self_report": a2}


class OfflineCueScorer:
    """OfflineWorld stand-in: deterministic per (unit, mutation, replicate) except for a per-unit draw shared by
    every arm, so the paired design is exercised. Plumbing only, never a result."""

    def __init__(self, world=None):
        from .measure import OfflineWorld
        self.world = world or OfflineWorld()

    def __call__(self, row: dict) -> dict:
        def h(s: str) -> int:
            return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16)
        cats = OFFLINE_CUE_CATEGORIES.get(row.get("mutation"), [])
        s = self.world([], cats, random.Random(h(f"{unit(row)}|{row.get('mutation')}|{row.get('replicate')}")), False)
        return {"verbalized": s.verbalized, "self_report": s.self_report}


def score_rows(rows: List[dict], scorer: Callable[[dict], dict], workers: int = 4, offline: bool = False) -> List[dict]:
    """Rows with A1/A2 added; replay errors are kept as they are, scoring failures become row errors."""
    def one(r: dict) -> dict:
        r = dict(r, offline=offline)
        if is_error(r):
            return r
        try:
            r.update(scorer(r))
        except Exception as e:  # noqa: BLE001  one failed judge call flags its row only
            r["error"] = f"scoring failed: {str(e)[:200]}"
        return r
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(one, rows))


# ---------------------------------------------------------------- effects
def per_unit(rows: List[dict], key: str) -> Dict[str, Dict[str, float]]:
    """mutation -> unit -> mean of `key` over that unit's non-error replicates."""
    acc: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        v = r.get(key)
        if not is_error(r) and isinstance(v, (int, float)):
            acc[r.get("mutation")][unit(r)].append(float(v))
    return {m: {u: mean(v) for u, v in d.items()} for m, d in acc.items()}


def cue_effects(rows: List[dict], ci: float = 0.9, n_boot: int = 2000) -> dict:
    """Per mutation and metric: mutation minus control, paired by unit (mean over replicates first)."""
    info = {}
    for r in rows:
        info.setdefault(r.get("mutation"), {"cue": r.get("cue"), "direction": r.get("direction")})
    by_metric = {name: per_unit(rows, key) for name, key in METRICS.items()}
    out = {}
    for m in sorted(x for x in info if x != CONTROL):
        mine = [r for r in rows if r.get("mutation") == m]
        e = dict(info[m], n_rows=len(mine), n_errors=sum(is_error(r) for r in mine))
        for name in METRICS:
            ctrl, mut = by_metric[name].get(CONTROL, {}), by_metric[name].get(m, {})
            shared = sorted(set(ctrl) & set(mut))
            d = [mut[u] - ctrl[u] for u in shared]
            e[name] = {"n_units": len(shared), "control_mean": mean([ctrl[u] for u in shared]) if d else None,
                       "mutation_mean": mean([mut[u] for u in shared]) if d else None,
                       "effect": mean(d) if d else None,
                       "ci": list(bootstrap_ci(d, level=ci, n=n_boot)) if len(d) > 1 else None,
                       "p_lower": prob_better([-x for x in d], [0.0] * len(d)) if d else None}
        out[m] = e
    return out


def analyze(rows: List[dict], meta: Optional[dict] = None, ci: float = 0.9, n_boot: int = 2000) -> dict:
    meta = meta or {}
    offline = any(r.get("offline") or r.get("mock") for r in rows) or bool(meta.get("offline"))
    ctrl = [r for r in rows if r.get("mutation") == CONTROL]
    rep = {"experiment": "counterfactual_cues", "date": datetime.date.today().isoformat(),
           "code_version": meta.get("code_version") or "unknown", "analysis_code_version": git_version(),
           "offline": offline, "ci_level": ci, "n_rows": len(rows),
           "n_units": len({unit(r) for r in rows}), "seeds": sorted({str(r.get("base_seed_id") or r.get("seed_id"))
                                                                     for r in rows}),
           "replicates": max([int(r.get("replicate") or 0) for r in rows] or [-1]) + 1,
           "control": {"n_rows": len(ctrl), "n_errors": sum(is_error(r) for r in ctrl),
                       **{n: mean([r[k] for r in ctrl if not is_error(r) and isinstance(r.get(k), (int, float))]
                                  or [float("nan")]) for n, k in METRICS.items()}},
           "effects": cue_effects(rows, ci, n_boot), "cost_usd": meta.get("cost_usd")}
    if not ctrl:
        rep["warning"] = "no control rows: effects cannot be computed"
    if offline:
        rep["note"] = "OFFLINE SIMULATOR / MOCK REPLAYS: pipeline check only, not a result"
    return rep


def markdown(rep: dict) -> str:
    def f(x, nd=3):
        return "n/a" if x is None or x != x else f"{x:.{nd}f}"

    def c(x):
        return "n/a" if not x else f"[{x[0]:.3f}, {x[1]:.3f}]"
    L = ["# Counterfactual cue replays: per-cue effect on eval awareness", ""]
    if rep["offline"]:
        L += ["**OFFLINE SIMULATOR / MOCK DATA. These numbers test the pipeline only and are not real-model results.**", ""]
    L += [f"CODE_VERSION `{rep['code_version']}` (analysis `{rep['analysis_code_version']}`), {rep['date']}. "
          f"{rep['n_rows']} replays, {rep['n_units']} decision points over {len(rep['seeds'])} seeds, "
          f"{rep['replicates']} replicate(s). Control: A1 {f(rep['control']['A1'])}, A2 {f(rep['control']['A2'])}.", "",
          f"Effect = mutation minus control, paired by decision point; {int(round(rep['ci_level'] * 100))}% bootstrap CI. "
          "Negative = the edit lowered awareness.", "",
          "| mutation | cue | direction | metric | units | effect | CI | P(lower) | errors |",
          "|---|---|---|---|---|---|---|---|---|"]
    for m, e in rep["effects"].items():
        for name in METRICS:
            x = e[name]
            L.append(f"| {m} | {e.get('cue')} | {e.get('direction')} | {name} | {x['n_units']} | {f(x['effect'])} | "
                     f"{c(x['ci'])} | {f(x['p_lower'], 2)} | {e['n_errors']}/{e['n_rows']} |")
    return "\n".join(L) + "\n"


def write_report(rep: dict, out_dir: str) -> Dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths = {"json": str(Path(out_dir) / "counterfactual_report.json"),
             "md": str(Path(out_dir) / "counterfactual_report.md")}
    Path(paths["json"]).write_text(json.dumps(rep, indent=1, default=str))
    Path(paths["md"]).write_text(markdown(rep))
    return paths


# ---------------------------------------------------------------- CLI
def judge_measurer(target: Optional[str], judge: Optional[str], max_cost: float, probe_questions=None):
    """A Measurer with the configured (or given) target and judge, set up like PetriMeasurer's judges."""
    from ..llm import Budget, get_llm
    from .measure import Measurer, Models
    from .models_config import load_models_config
    from .petri_measure import PETRI_SCENARIO
    cfg = load_models_config()["roles"]
    budget = Budget(max_cost_usd=max_cost)
    mk = lambda s: get_llm("auto", s, budget)  # noqa: E731
    models = Models(generator=mk(cfg["generator"]), target=mk(target or cfg["dev_target"]),
                    judge=mk(judge or cfg["dev_judge"]))
    return Measurer(models, scenario=PETRI_SCENARIO, probe_questions=probe_questions), budget


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.research.counterfactual",
                                 description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="add A1/A2 to replay rows")
    s.add_argument("rows")
    s.add_argument("--out", required=True)
    s.add_argument("--offline", action="store_true", help="OfflineWorld stand-in (free)")
    s.add_argument("--target"), s.add_argument("--judge")
    s.add_argument("--max-cost", type=float, default=20.0)
    s.add_argument("--workers", type=int, default=4)
    a_ = sub.add_parser("analyze", help="per-cue paired effects vs control")
    a_.add_argument("rows")
    a_.add_argument("--out-dir", required=True)
    a_.add_argument("--ci", type=float, default=0.9)
    a_.add_argument("--code-version", help="CODE_VERSION of the replay run (default: CODE_VERSION next to rows)")
    a = ap.parse_args(argv)
    rows = _read_jsonl(a.rows)
    if a.cmd == "score":
        if a.offline:
            scored = score_rows(rows, OfflineCueScorer(), a.workers, offline=True)
        else:
            m, budget = judge_measurer(a.target, a.judge, a.max_cost)
            scored = score_rows(rows, JudgeScorer(m), a.workers)
            print(f"scoring compute: {budget.summary()}", file=sys.stderr)
        _write_jsonl(a.out, scored)
        print(f"{len(scored)} rows -> {a.out} ({sum(is_error(r) for r in scored)} errored)", file=sys.stderr)
        return 0
    cv = Path(a.rows).parent / "CODE_VERSION"
    meta = {"code_version": a.code_version or (cv.read_text().strip() if cv.exists() else None)}
    paths = write_report(analyze(rows, meta, ci=a.ci), a.out_dir)
    print("\n".join(f"wrote {p}" for p in paths.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
