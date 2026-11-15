"""V3 behaviour gap on untouched benchmark items (C1, board task behavior-gap-probe).

For each item on one side of the frozen split, the target answers it as-is and
with an explicit evaluation notice; the judge labels both replies; the report
gives misbehaviour rates, their difference with an item-level bootstrap CI and
a `measurable` flag, overall and per safety/capability group
(autoresearch.research.calibrate.behaviour_gap). It is reported next to the
calibration gate, not as one of its checks.

  python3 scripts/c1_behaviour_gap.py                          # offline dry run (default)
  python3 scripts/c1_behaviour_gap.py --target anthropic:claude-sonnet-4-6+thinking \
      --judge <spec> --approved-by-nathan                      # real run: costs money

Specs are "backend:model" strings for llm.get_llm; a known backend prefix
overrides --llm. Any non-offline spec needs --approved-by-nathan, otherwise the
call estimate is printed and the script exits 2 without calling anything.
An offline run always writes under runs/c1/offline/behaviour_gap/, whatever
--out says: results/ holds real-model results only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from autoresearch.llm import Budget, OfflineLLM  # noqa: E402
from autoresearch.research import calibrate as cal  # noqa: E402
from autoresearch.research.measure import Measurer, Models, OfflineWorld, load_probe_questions  # noqa: E402

DEFAULT_ITEMS = os.path.join("data", "benchmarks", "evalawarebench_minimal_cue.jsonl")
DEFAULT_SPLIT = os.path.join("data", "benchmarks", "evalawarebench_split.json")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--llm", default="offline", help="backend for specs without a known prefix (default offline)")
    p.add_argument("--target", default="offline", help="target spec, e.g. anthropic:claude-sonnet-4-6+thinking")
    p.add_argument("--judge", default="offline", help="judge spec that labels behaviour")
    p.add_argument("--generator", default="offline", help="never called on untouched items; Models needs one")
    p.add_argument("--items", "--items-original", dest="items", default=DEFAULT_ITEMS,
                   help="converted benchmark JSONL (default: the minimal-cue configuration, whose base "
                        "misbehaviour rate is the one deployment would see)")
    p.add_argument("--split", default=DEFAULT_SPLIT)
    p.add_argument("--side", default="dev", choices=["dev", "heldout"])
    p.add_argument("--limit", type=int, default=0, help="first N items by id (0 = all on the side)")
    p.add_argument("--seeds", type=int, default=2, help="samples per item")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--min-misbehaving", type=int, default=cal.DEFAULT_MIN_MISBEHAVING)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--max-calls", type=int, default=2000)
    p.add_argument("--max-cost-usd", type=float, default=50.0,
                   help="spend cap; binds where the backend reports cost (anthropic, openai, claude-cli; not openai-compat)")
    p.add_argument("--max-seconds", type=float, default=7200)
    p.add_argument("--probe-questions", help="not used by V3; recorded for parity with the gate")
    p.add_argument("--out", default=os.path.join("results", "behaviour_gap"))
    p.add_argument("--approved-by-nathan", action="store_true",
                   help="required for any non-offline spec (AGENTS.md rule 5)")
    return p


def run(args) -> dict:
    """Run V3 and write the JSON. Returns the report (with "path")."""
    specs = {"target": args.target, "judge": args.judge, "generator": args.generator}
    offline = all(cal.spec_is_offline(s, args.llm) for s in (args.target, args.judge))
    items, groups = cal.load_gap_items(args.items, args.split, args.side, args.limit or None)
    est = cal.estimate_gap_calls(len(items), args.seeds)
    print(f"behaviour gap: {len(items)} {args.side} items x {args.seeds} samples = up to {est} model calls "
          f"(target={args.target}, judge={args.judge}, --max-calls {args.max_calls})")
    if not offline and not args.approved_by_nathan:
        raise SystemExit(2)
    budget = Budget(max_calls=args.max_calls, max_seconds=args.max_seconds, max_cost_usd=args.max_cost_usd)
    models = Models(generator=cal.make_llm(args.generator, args.llm, budget),
                    target=cal.make_llm(args.target, args.llm, budget),
                    judge=cal.make_llm(args.judge, args.llm, budget))
    probes = load_probe_questions(args.probe_questions) if args.probe_questions else None

    def factory(sc):
        return Measurer(models, scenario=sc, workers=args.workers, simulator=OfflineWorld(), probe_questions=probes)
    res = cal.behaviour_gap(factory, items, n_per_item=args.seeds, seed=args.seed, groups=groups, budget=budget,
                            workers=args.workers, min_misbehaving=args.min_misbehaving)
    from autoresearch.research.decisions import code_version
    now = datetime.now(timezone.utc)
    rep = {"experiment": "V3 behaviour gap (C1)", "created": now.isoformat(timespec="seconds"),
           "offline": offline or any(isinstance(m, OfflineLLM) for m in (models.target, models.judge)),
           "side": args.side, "items_file": args.items,
           "split_file": args.split, "n_items": len(items), "estimate_calls": est,
           "models": {"requested": specs, "llm_default": args.llm,
                      "labels": {"target": models.target.label, "judge": models.judge.label}},
           "result": res, "compute": budget.summary(), "code_version": code_version()}
    out = args.out
    if rep["offline"]:
        rep["note"] = cal.OFFLINE_NOTE
        # results/ is for real-model results only; offline output always goes under runs/ (git-ignored)
        out = os.path.join(cal.OFFLINE_OUT, "behaviour_gap")
        if os.path.abspath(out) != os.path.abspath(args.out):
            print(f"offline run: writing to {out}, not --out {args.out}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{now.strftime('%Y%m%dT%H%M%SZ')}_{args.side}{'_offline' if rep['offline'] else ''}.json")
    k = 1
    while os.path.exists(path):
        k += 1
        path = path[:-5] + f"_{k}.json"
    with open(path, "w") as f:
        json.dump(rep, f, indent=1)
    rep["path"] = path
    return rep


def print_summary(rep: dict) -> None:
    res = rep["result"]
    for name, s in [("overall", res["overall"])] + list(res["by_group"].items()):
        rate = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
        print(f"{name}: n={s['n']} as-is={rate(s['rate_as_is'])} with-notice={rate(s['rate_with_notice'])} "
              f"gap={rate(s['gap'])} ci={[rate(c) for c in s['ci']]} measurable={s['measurable']} "
              f"(unparseable {s['unparseable']}, unknown labels {s['unknown_labels']}, failed {s['failed_calls']}, "
              f"not run {s['not_run']})")
    if rep["offline"]:
        print(cal.OFFLINE_NOTE)
    print(f"compute {rep['compute']}")
    print("wrote", rep["path"])


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rep = run(args)
    except SystemExit as e:
        if e.code == 2:
            print("refusing: a non-offline spec needs --approved-by-nathan (no calls were made)")
        raise
    print_summary(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
