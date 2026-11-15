"""V3 behaviour gap on untouched benchmark items (C1, board task behavior-gap-probe).

For each item on one side of the frozen split, the target answers it as-is and
with an explicit evaluation notice; the judge labels both replies; the report
gives misbehaviour rates, their difference with an item-level bootstrap CI and
a `measurable` flag, overall and per safety/capability group
(autoresearch.research.calibrate.behaviour_gap). It is reported next to the
calibration gate, not as one of its checks.

  python3 scripts/c1_behaviour_gap.py                          # offline dry run (default)
  python3 scripts/c1_behaviour_gap.py --scenarios all --seeds 10 --target anthropic:claude-sonnet-4-6 \
      --judge <spec> --generator <spec> --approved-by-nathan   # hand-written V3 probes, generated environments
  python3 scripts/c1_behaviour_gap.py --print-smoke-plan <QWEN_SERVED_ID>   # the two smoke commands, no calls
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
import dataclasses
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from autoresearch.llm import Budget, OfflineLLM  # noqa: E402
from autoresearch.research import calibrate as cal  # noqa: E402
from autoresearch.research import probes_v3  # noqa: E402
from autoresearch.research.measure import Measurer, Models, OfflineWorld, load_probe_questions  # noqa: E402

DEFAULT_ITEMS = os.path.join("data", "benchmarks", "evalawarebench_minimal_cue.jsonl")
DEFAULT_SPLIT = os.path.join("data", "benchmarks", "evalawarebench_split.json")
CALLS_PER_ENV = 5   # 1 generator + 2 target + 2 judge


def smoke_plan(qwen_id: str = "<QWEN_SERVED_ID>", envs: int = 10) -> str:
    """The two ready-to-run smoke commands (Qwen on Modal, then GPT-5), each preceded by its call bound."""
    bound = CALLS_PER_ENV * len(probes_v3.V3_PROBES) * envs

    def cmd(target):
        return (f"python3 scripts/c1_behaviour_gap.py --scenarios all --seeds {envs} --target {target} "
                f"--judge anthropic:claude-haiku-4-5 --generator openai:gpt-6-luna "
                f"--max-calls {bound} --max-cost-usd 15 --approved-by-nathan")
    return "\n".join([
        "# Qwen needs OPENAI_COMPAT_BASE_URL=https://<app>.modal.run/v1 set; the openai-compat backend "
        "reports no cost, so only --max-calls binds.",
        "# Also set OPENAI_COMPAT_PLAIN_THINKING=off (or =headroom) for any plain Qwen call; V3 target replies use "
        "complete_with_reasoning, which adds headroom anyway. To be confirmed in C2's Modal smoke.",
        f"# up to {bound} model calls",
        cmd(f"openai-compat:{qwen_id}"),
        f"# up to {bound} model calls",
        cmd("openai:gpt-5+thinking"),
    ])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--llm", default="offline", help="backend for specs without a known prefix (default offline)")
    p.add_argument("--target", default="offline", help="target spec, e.g. anthropic:claude-sonnet-4-6+thinking")
    p.add_argument("--judge", default="offline", help="judge spec that labels behaviour")
    p.add_argument("--generator", default="offline",
                   help="never called on untouched items; writes the environments with --scenarios")
    p.add_argument("--scenarios", nargs="+", metavar="NAME",
                   help="run V3 on hand-written probes (autoresearch.research.probes_v3; 'all' = every probe) "
                        "instead of benchmark items; --items/--split/--side/--limit are then ignored")
    p.add_argument("--print-smoke-plan", nargs="?", const="<QWEN_SERVED_ID>", metavar="QWEN_SERVED_ID",
                   help="print the two ready-to-run smoke commands and exit; builds nothing")
    p.add_argument("--items", "--items-original", dest="items", default=DEFAULT_ITEMS,
                   help="converted benchmark JSONL (default: the minimal-cue configuration, whose base "
                        "misbehaviour rate is the one deployment would see)")
    p.add_argument("--split", default=DEFAULT_SPLIT)
    p.add_argument("--side", default="dev", choices=["dev", "heldout"])
    p.add_argument("--limit", type=int, default=0, help="first N items by id (0 = all on the side)")
    p.add_argument("--seeds", type=int, default=2, help="samples per item; with --scenarios, generated environments per probe")
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
    scenarios_mode = bool(args.scenarios)
    judge_target_offline = all(cal.spec_is_offline(s, args.llm) for s in (args.target, args.judge))
    if scenarios_mode:
        try:
            probes = probes_v3.resolve(args.scenarios)
        except ValueError as e:
            raise SystemExit(str(e))
        ignored = [f"--{n}" for n in ("items", "split", "side", "limit")
                   if getattr(args, n) != build_parser().get_default(n)]
        items = [dataclasses.replace(sc, source_id=sc.name) for sc in probes]
        groups = {sc.name: sc.name for sc in probes}
        est = CALLS_PER_ENV * len(items) * args.seeds
        offline = judge_target_offline and cal.spec_is_offline(args.generator, args.llm)
        print(f"behaviour gap (scenarios): {len(items)} probes x {args.seeds} environments = up to {est} model calls "
              f"(1 generator + 2 target + 2 judge each) (target={args.target}, judge={args.judge}, "
              f"generator={args.generator}, --max-calls {args.max_calls})")
        if ignored:
            print(f"--scenarios mode: ignoring {', '.join(ignored)}")
    else:
        offline = judge_target_offline
        items, groups = cal.load_gap_items(args.items, args.split, args.side, args.limit or None)
        est = cal.estimate_gap_calls(len(items), args.seeds)
        print(f"behaviour gap: {len(items)} {args.side} items x {args.seeds} samples = up to {est} model calls "
              f"(target={args.target}, judge={args.judge}, --max-calls {args.max_calls})")
    if not offline and not args.approved_by_nathan:
        raise SystemExit(2)
    if scenarios_mode and not judge_target_offline and cal.spec_is_offline(args.generator, args.llm):
        # exit text, not code 2: main() maps 2 to the approval refusal
        raise SystemExit("--scenarios with a real target needs a real --generator "
                         "(OfflineLLM cannot write environments)")
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
           "mode": "scenarios" if scenarios_mode else "items",
           # any simulated model in the loop marks the report offline, so it never lands in results/
           "offline": offline or any(isinstance(m, OfflineLLM) for m in
                                     ((models.generator,) if scenarios_mode else ()) + (models.target, models.judge)),
           "side": args.side, "items_file": None if scenarios_mode else args.items,
           "split_file": None if scenarios_mode else args.split, "n_items": len(items), "estimate_calls": est,
           "models": {"requested": specs, "llm_default": args.llm,
                      "labels": {"target": models.target.label, "judge": models.judge.label}},
           **({"probes": [sc.name for sc in items]} if scenarios_mode else {}),
           "result": res, "compute": budget.summary(), "code_version": code_version()}
    out = args.out
    if rep["offline"]:
        rep["note"] = cal.OFFLINE_NOTE
        # results/ is for real-model results only; offline output always goes under runs/ (git-ignored)
        out = os.path.join(cal.OFFLINE_OUT, "behaviour_gap")
        if os.path.abspath(out) != os.path.abspath(args.out):
            print(f"offline run: writing to {out}, not --out {args.out}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{now.strftime('%Y%m%dT%H%M%SZ')}_{'scenarios' if scenarios_mode else args.side}{'_offline' if rep['offline'] else ''}.json")
    k = 1
    while os.path.exists(path):
        k += 1
        path = path[:-5] + f"_{k}.json"
    with open(path, "w") as f:
        json.dump(rep, f, indent=1)
    rep["path"] = path
    return rep


def _rate(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def _arm(a: dict) -> str:
    return (f"n={a['n']} as-is={_rate(a['rate_as_is'])} with-notice={_rate(a['rate_with_notice'])} "
            f"gap={_rate(a['gap'])} ci={[_rate(c) for c in a['ci']]}")


def _print_group(name: str, s: dict) -> None:
    head = f"{name}: measurable={s['measurable']} (decisive pairs)"
    if s.get("pooled_screen"):
        head = f"{name} (POOLED SCREEN, not a result; decide per probe above): measurable={s['measurable']}"
    print(head + (f"; {s['reason']}" if s.get("reason") else ""))
    print(f"  decisive {_arm(s['decisive_pairs'])}")
    print(f"  all pairs {_arm(s['all_pairs'])}")
    print(f"  labels as-is {s['labels_as_is']} | with notice {s['labels_with_notice']}; "
          f"excluded from decisive {s['excluded_from_decisive']}")
    print(f"  (unparseable {s['unparseable']}, unknown labels {s['unknown_labels']}, failed {s['failed_calls']}, "
          f"not run {s['not_run']})")


def print_summary(rep: dict) -> None:
    """Per group, decisive pairs first (what `measurable` is based on), all pairs beside them, and every label's
    count per arm; the pooled "overall" comes last and is labelled as a screen. Reads only the named blocks, not
    the top-level rate/gap/ci mirror."""
    res = rep["result"]
    for name, s in res["by_group"].items():
        _print_group(name, s)
    _print_group("overall", res["overall"])
    if rep["offline"]:
        print(cal.OFFLINE_NOTE)
    print(f"compute {rep['compute']}")
    print("wrote", rep["path"])


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.print_smoke_plan is not None:
        print(smoke_plan(args.print_smoke_plan))
        return 0
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
