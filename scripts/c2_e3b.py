"""E3b: eval awareness in Petri audits, compared across seed conditions (WS C2).

The one scorer for agentic eval-awareness numbers. Each condition is an
AuditSeed JSONL file (stock Petri v2 seeds, Petri v1 seeds, or rewrites from
the loop or any other system, variant "ours"); a condition can also swap in a
custom auditor system prompt (--auditor-prompt NAME=FILE), to test auditor
rewrites with the seeds held fixed. Every condition is audited with
the same models and scored by PetriMeasurer, i.e. C1's judges: A2 = the target's
own P(eval), A1 = the audit judge on the transcript and raw reasoning, validity,
plus every judge's A1/A2 and Petri's own judge scores as a cross-check.
Conditions are paired by base seed (the part of seed_id before "@" or the
`base_seed_id` field), so differences are paired over seeds.

    # free plumbing check
    python3 scripts/c2_e3b.py --offline --condition stock=data/petri/seeds_v2.jsonl --split dev
    # paid (needs approval): dev target, both tool modes
    python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl --condition ours=rewrites.jsonl \
        --split dev --epochs 5 --tools simulated --out results/e3b/dev_simulated.json

Results: per condition, mean awareness / A2 / A1 / validity / score with 90%
bootstrap CIs over samples, error count, Petri cross-check means; per condition
vs the first one, the paired mean difference over seeds with a 90% CI and
P(better). Records CODE_VERSION and the full model lineup.
"""
import argparse
import datetime
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch.llm import Budget, OfflineLLM, get_llm  # noqa: E402
from autoresearch.research.measure import Models  # noqa: E402
from autoresearch.research.models_config import load_models_config  # noqa: E402
from autoresearch.research.petri_measure import PetriMeasurer, load_audit_seeds, petri_score_summary  # noqa: E402
from autoresearch.research.stats import bootstrap_ci, mean, prob_better  # noqa: E402

METRICS = ("awareness", "self_report", "verbalized", "validity", "score")


def base_id(seed_id: str) -> str:
    return seed_id.split("@", 1)[0]


def summarize(samples):
    ok = [s for s in samples if s.behavior != "error"]
    out = {"n": len(samples), "n_ok": len(ok), "errors": sorted({s.error for s in samples if s.error})[:10]}
    for m in METRICS:
        xs = [getattr(s, m) for s in ok]
        out[m] = {"mean": mean(xs) if xs else None, "ci90": list(bootstrap_ci(xs)) if len(xs) > 1 else None}
    out["misaligned_rate"] = (sum(s.behavior == "misaligned" for s in ok) / len(ok)) if ok else None
    judges = sorted({k for s in ok for k in s.judge_p_eval} | {k for s in ok for k in s.judge_verbalized})
    out["judges"] = {j: {"a2": mean([s.judge_p_eval[j] for s in ok if j in s.judge_p_eval] or [float("nan")]),
                         "a1": mean([s.judge_verbalized[j] for s in ok if j in s.judge_verbalized] or [float("nan")])}
                     for j in judges}
    out["petri_cross_check"] = petri_score_summary(samples)
    return out


def paired(base, other, metric="awareness"):
    """Per base seed means, then the paired difference other - base over shared seeds."""
    def per_seed(samples):
        d = defaultdict(list)
        for s in samples:
            if s.behavior != "error":
                d[base_id(s.seed_id)].append(getattr(s, metric))
        return {k: mean(v) for k, v in d.items()}
    a, b = per_seed(base), per_seed(other)
    shared = sorted(set(a) & set(b))
    diffs = [b[k] - a[k] for k in shared]
    return {"metric": metric, "n_seeds": len(shared), "mean_diff": mean(diffs) if diffs else None,
            "ci90": list(bootstrap_ci(diffs)) if len(diffs) > 1 else None,
            "p_lower": prob_better([-x for x in diffs], [0.0] * len(diffs)) if diffs else None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--condition", action="append", required=True, metavar="NAME=FILE",
                    help="AuditSeed JSONL per condition; the first is the baseline")
    ap.add_argument("--auditor-prompt", action="append", default=[], metavar="NAME=FILE",
                    help="custom auditor system prompt for condition NAME (default: Petri's stock prompt)")
    ap.add_argument("--split", choices=["dev", "hidden", "all"], default="dev",
                    help="rows' 'split' field (rows without one are kept)")
    ap.add_argument("--tools", choices=["simulated", "sandbox"], default="simulated")
    ap.add_argument("--epochs", type=int, default=1, help="audits per seed and condition")
    ap.add_argument("--limit", type=int, help="only the first N seeds of each condition (smoke tests)")
    ap.add_argument("--mode", choices=["dev", "final"], default="dev")
    ap.add_argument("--heldout-target", help="final mode: which held-out target from configs/models.json")
    ap.add_argument("--max-turns", type=int)
    ap.add_argument("--target", help="override the dev target spec from configs/models.json (pilots)")
    ap.add_argument("--judge", help="override the dev judge spec")
    ap.add_argument("--petri-auditor", help="override the Petri auditor (Inspect model id)")
    ap.add_argument("--cache-dir", help="checkpoint finished audits here and reuse them on a re-run (resume)")
    ap.add_argument("--petri-batch", type=int, default=8, help="audits per harness call when --cache-dir is set")
    ap.add_argument("--petri-judge", help="override Petri's own judge (Inspect model id)")
    ap.add_argument("--max-cost", type=float, default=50.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    cfg = load_models_config()["roles"]
    budget = Budget(max_cost_usd=a.max_cost)
    mk = (lambda s: OfflineLLM(budget)) if a.offline else (lambda s: get_llm("auto", s, budget))
    ht = a.heldout_target or (cfg["heldout_targets"][0] if a.mode == "final" else None)
    models = Models(generator=mk(cfg["generator"]), target=mk(a.target or cfg["dev_target"]),
                    judge=mk(a.judge or cfg["dev_judge"]),
                    heldout_target=mk(ht) if ht else None,
                    heldout_judges=[mk(j) for j in cfg["heldout_judges"]] if a.mode == "final" else [])
    from autoresearch.research.petri_measure import HarnessRunner
    results, lineup = {}, {}
    conds = [c.split("=", 1) for c in a.condition]
    prompts = dict(x.split("=", 1) for x in a.auditor_prompt)
    unknown = set(prompts) - {n for n, _ in conds}
    if unknown:
        raise SystemExit(f"--auditor-prompt for unknown condition(s): {sorted(unknown)}")
    for name, path in conds:
        seeds = [s for s in load_audit_seeds(path) if a.split == "all" or s.get("split", a.split) == a.split]
        seeds = seeds[: a.limit] if a.limit else seeds
        if not seeds:
            raise SystemExit(f"{name}: no {a.split} seeds in {path}")
        for s in seeds:
            s["tools"] = a.tools
        prompt = Path(prompts[name]).read_text() if name in prompts else None
        pm = PetriMeasurer(models, seeds, tools=a.tools, mode=a.mode, workers=a.workers, auditor_prompt=prompt)
        if not a.offline:
            extra = (["--auditor", a.petri_auditor] if a.petri_auditor else []) + \
                    (["--judge", a.petri_judge] if a.petri_judge else [])
            pm.runner = HarnessRunner(mode=a.mode, max_turns=a.max_turns, target=pm.target.label, extra_args=extra,
                                      cache_dir=a.cache_dir, batch_size=a.petri_batch)
        sample_seeds = [i + len(seeds) * e for e in range(a.epochs) for i in range(len(seeds))]
        results[name] = pm.measure([], sample_seeds)
        lineup = {"target": pm.target.label, "judges": [j.label for j in pm.judges], "warnings": pm.warnings,
                  "petri_auditor": a.petri_auditor or "configs/models.json", "petri_judge": a.petri_judge or "configs/models.json",
                  "compute": budget.summary() if hasattr(budget, "summary") else {}}
        print(f"{name}: {len(results[name])} audits", file=sys.stderr)
    base_name = conds[0][0]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rep = {"experiment": "E3b", "auditor_prompts": {n: prompts.get(n, "stock") for n, _ in conds}, "date": datetime.date.today().isoformat(), "code_version": commit,
           "offline": a.offline, "mode": a.mode, "split": a.split, "tools": a.tools, "epochs": a.epochs,
           "models": lineup, "conditions": {n: summarize(s) for n, s in results.items()},
           "vs_" + base_name: {n: {m: paired(results[base_name], s, m) for m in ("awareness", "score", "validity")}
                               for n, s in results.items() if n != base_name},
           "samples": {n: [x.to_dict() for x in s] for n, s in results.items()}}
    if a.offline:
        rep["note"] = "OFFLINE SIMULATOR: plumbing check only, not a result"
    text = json.dumps(rep, indent=1, default=str)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text)
    for n, c in rep["conditions"].items():
        aw = c["awareness"]["mean"]
        print(f"{n:12s} n_ok={c['n_ok']}/{c['n']} awareness={aw if aw is None else round(aw, 3)} "
              f"validity={c['validity']['mean'] if c['validity']['mean'] is None else round(c['validity']['mean'], 3)} "
              f"petri={c['petri_cross_check']}")
    return 0


if __name__ == "__main__":
    random.seed(0)
    sys.exit(main())
