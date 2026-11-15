"""Driver for the whole C1 real run: the calibration gate and the V3 behaviour
gap, per phase, for the team's 3-target / 2-judge lineup.

  dev phase    dev target (Qwen3-30B-A3B thinking on Modal vLLM, --dev-target
               openai-compat:<served id>) with J1 = anthropic:claude-haiku-4-5
  final phase  each held-out target (anthropic:claude-sonnet-4-5+thinking,
               openai:gpt-5+thinking) with both judges (J1 and J2 =
               openai:gpt-5.1) as held-out judges, the cross-family judge first
               (it scores A1 and V3 labels and gives the headline). Both
               held-out APIs return reasoning SUMMARIES: A1 there is a lower bound.

  python3 scripts/c1_run_gate.py --scenario pilot          # DRY RUN: plan + calls + $ for both phases
  python3 scripts/c1_run_gate.py --scenario full           # the same for the full gate
  python3 scripts/c1_run_gate.py --scenario pilot --offline                 # plumbing only, simulated models
  python3 scripts/c1_run_gate.py --scenario pilot --phase dev --dev-target openai-compat:<id> \
      --execute --approved-by-nathan                                        # real run: costs money

By default it only prints: for each phase and target, the equivalent
`python3 -m autoresearch calibrate ...` and `scripts/c1_behaviour_gap.py ...`
commands, and an upper-bound estimate of calls, tokens and dollars per kind of
call with the arithmetic and assumptions shown (calibrate.estimate_cost).
Nothing is called and no backend is constructed.

Scenarios: pilot = 20 single-factor pairs spread over the 8 factors, no
labelled set, no hand labels, V3 on 20 items; full = single-factor at 25 per
factor (200 pairs), a 200-transcript labelled subset, about 100 hand labels,
V3 on all dev items. Flags after --scenario are overridden by it.

Cue pairs (--cue-set): single (default) = one cue factor on vs all off;
--pairs N spreads N pairs over the factors, --pair-limit N keeps the first N
tasks per factor. all8 = all cues exaggerated vs all naturalistic. Every pair
must come from the --side of the frozen split, or the run stops. The pairs
and the labelled subset (balanced eval/deploy, chat/agentic-stratified, fixed
--labelled-seed) are written to --work, also on a dry run, so the printed
commands repeat the run exactly. The printed behaviour-gap command omits
--approved-by-nathan, so pasting it unedited refuses.

--execute refuses unless --approved-by-nathan is given, one --phase is chosen
(dev needs --dev-target), autoresearch/ has no uncommitted changes, and the
preregistration (--prereg) is committed, unmodified, and no longer a draft.

--offline writes its reports under runs/c1/offline/ (git-ignored), never
--out-gate/--out-gap: results/ holds real-model results only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from autoresearch.llm import Budget, OfflineLLM  # noqa: E402
from autoresearch.research import calibrate as cal  # noqa: E402
from autoresearch.research.benchmarks import load_split  # noqa: E402
from autoresearch.research.measure import (DEFAULT_PROBE_QUESTIONS, Measurer, Models,  # noqa: E402
                                           a1_is_lower_bound, headline_judge, load_probe_questions,
                                           probe_set_for)

# The team's fixed lineup (decided by Nathan). The dev target's served model id is Abhi's (C2)
# to define, so it is never hard-coded: --dev-target is required to execute the dev phase.
DEV_TARGET_PLACEHOLDER = "openai-compat:<qwen3-30b-a3b served id>"
HELDOUT_TARGETS = ["anthropic:claude-sonnet-4-5+thinking", "openai:gpt-5+thinking"]
DEV_JUDGE = "anthropic:claude-haiku-4-5"        # J1: A1 + A2 in dev
HELDOUT_JUDGE = "openai:gpt-5.1"                # J2: with J1, scores every held-out target in final
BENCH = os.path.join("data", "benchmarks")
# Two named scenarios, each printed by one command (--scenario pilot / full).
SCENARIOS = {
    "pilot": {"pairs": 20, "pair_limit": None, "labelled_n": 0, "hand_n": 0, "gap_limit": 20,
              "about": "20 single-factor cue pairs spread over the 8 factors, no Needham set, no hand labels"},
    "full": {"pairs": None, "pair_limit": 25, "labelled_n": 200, "hand_n": 100, "gap_limit": 0,
             "about": "200 cue pairs = the single-factor set at 25 per factor; a 200-transcript Needham subset; "
                      "about 100 hand labels; V3 on all dev items"},
}


def _gap_module():
    spec = importlib.util.spec_from_file_location("c1_behaviour_gap", os.path.join(ROOT, "scripts", "c1_behaviour_gap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--phase", default="both", choices=["dev", "final", "both"],
                   help="dev: dev target with J1; final: each held-out target with both judges; both (dry run / "
                        "--offline only)")
    p.add_argument("--scenario", choices=sorted(SCENARIOS),
                   help="pilot or full: sets the pair count, labelled subset, hand labels and V3 scope")
    p.add_argument("--dev-target", help=f"dev target spec, e.g. openai-compat:<served model id>; required to execute "
                                        f"the dev phase (dry runs show {DEV_TARGET_PLACEHOLDER})")
    p.add_argument("--heldout-targets", nargs="+", default=list(HELDOUT_TARGETS))
    p.add_argument("--dev-judge", default=DEV_JUDGE, help="J1")
    p.add_argument("--heldout-judge", default=HELDOUT_JUDGE, help="J2")
    p.add_argument("--llm", default="anthropic", help="backend for specs without a known prefix")
    p.add_argument("--items-original", default=os.path.join(BENCH, "evalawarebench_original.jsonl"))
    p.add_argument("--items-minimal", default=os.path.join(BENCH, "evalawarebench_minimal_cue.jsonl"))
    p.add_argument("--split", default=os.path.join(BENCH, "evalawarebench_split.json"))
    p.add_argument("--side", default="dev", choices=["dev", "heldout"])
    p.add_argument("--cue-set", default="single", choices=["single", "all8"],
                   help="single: one cue on vs all off, per factor (default); all8: all cues vs none")
    p.add_argument("--single-pairs", default=os.path.join(BENCH, "evalawarebench_single_factor_pairs.jsonl"))
    p.add_argument("--pairs", type=int, help="total cue pairs; single: spread evenly over the factors")
    p.add_argument("--pair-limit", "--limit", dest="pair_limit", type=int,
                   help="single: first N tasks per factor (default 5 = 40 pairs); all8: first N pairs (default 20); "
                        "0 = all. Ignored when --pairs is given")
    p.add_argument("--probe-questions", default=os.path.join(BENCH, "evaldetect_probes.json"))
    p.add_argument("--labelled", default=os.path.join(BENCH, "needham", "dataset.json"),
                   help="full labelled set (gated; Nathan fetches it)")
    p.add_argument("--labelled-n", type=int, default=200, help="balanced, chat/agentic-stratified subset size; 0 = none")
    p.add_argument("--labelled-seed", type=int, default=0)
    p.add_argument("--transcripts", default=os.path.join("data", "labels", "transcripts.jsonl"))
    p.add_argument("--hand-labels", default=os.path.join("data", "labels", "hand_labels.jsonl"))
    p.add_argument("--gap-items", default=os.path.join(BENCH, "evalawarebench_minimal_cue.jsonl"),
                   help="items for V3 (default minimal-cue: the base rate deployment would see)")
    p.add_argument("--gap-limit", type=int, default=20, help="first N dev items for V3; 0 = all")
    p.add_argument("--gap-seeds", type=int, default=2, help="V3 samples per item")
    p.add_argument("--no-gap", action="store_true", help="skip the V3 step")
    p.add_argument("--max-calls", type=int, default=6000, help="per step")
    p.add_argument("--max-cost-usd", type=float, default=40.0,
                   help="per step; binds where the backend reports cost (anthropic, openai, claude-cli; not openai-compat)")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--work", default=os.path.join("runs", "c1"), help="where the cue-pair and labelled subsets go")
    p.add_argument("--out-gate", default=os.path.join("results", "calibration"))
    p.add_argument("--out-gap", default=os.path.join("results", "behaviour_gap"))
    p.add_argument("--prereg", default=os.path.join("results", "prereg", "C1_gate.json"))
    p.add_argument("--offline", action="store_true", help="execute every step with offline backends")
    p.add_argument("--execute", action="store_true", help="make the real calls (needs --approved-by-nathan)")
    p.add_argument("--approved-by-nathan", action="store_true")
    return p


def apply_scenario(args) -> None:
    """A named scenario overrides the scope flags it covers."""
    if not args.scenario:
        return
    sc = SCENARIOS[args.scenario]
    args.cue_set = "single"
    args.pairs, args.pair_limit = sc["pairs"], sc["pair_limit"]
    args.labelled_n, args.gap_limit = sc["labelled_n"], sc["gap_limit"]


def judges_for(target: str, j1: str, j2: str) -> list:
    """Both judges, the one from a different family than the target first
    (measure.headline_judge): it is measurer.judge in final mode (A1, V3 labels)
    and the headline. For a target of neither judge's family (Qwen), J1 stays first."""
    head = headline_judge(target, [j1, j2])
    return [j1, j2] if head in (None, j1) else [j2, j1]


def _exists(path):
    return bool(path) and os.path.exists(path)


def _select_pairs(args, ids):
    if args.cue_set == "single":
        pairs = cal.load_cue_pairs(args.single_pairs)
        if args.pairs:
            return cal.spread_pairs(cal.select_pairs(pairs, ids=ids), args.pairs), args.pairs
        limit = args.pair_limit if args.pair_limit is not None else 5
        return cal.select_pairs(pairs, ids=ids, per_group=limit or None), limit
    limit = args.pairs or (args.pair_limit if args.pair_limit is not None else 20)
    return cal.pair_items(args.items_original, args.items_minimal, ids=ids, limit=limit or None), limit


def _labelled_inputs(args):
    """(path written or None, transcript lengths for the estimate, assumed?)."""
    if not args.labelled_n:
        return None, [], False
    if _exists(args.labelled):
        sub = cal.sample_labelled(cal.load_labelled(args.labelled), n=args.labelled_n, seed=args.labelled_seed)
        path = cal.labelled_subset_path(args.work, args.labelled_n, args.labelled_seed)
        cal.write_labelled(sub, path)
        return path, [len(r.transcript) for r in sub], False
    if not args.scenario:
        return None, [], False
    # a scenario's estimate with the gated file absent: bound each transcript by the cut load_labelled applies
    return None, [cal.DEFAULT_MAX_TRANSCRIPT_CHARS] * args.labelled_n, True


def _hand_inputs(args, env_chars_mean: float):
    if _exists(args.transcripts) and _exists(args.hand_labels):
        ts = {t.id: t for t in cal.load_transcripts(args.transcripts)}
        labels = cal.load_hand_labels(args.hand_labels)
        return True, [len(ts[i].render()) + min(len(ts[i].reasoning), cal.AUDIT_REASONING_CHARS)
                      for i, a in labels.items() if a is not None and i in ts], False
    n = SCENARIOS[args.scenario]["hand_n"] if args.scenario else 0
    # absent: Sample.to_dict keeps 1500 chars of reply and of reasoning, around a gate-sized environment
    return False, [int(env_chars_mean) + cal.TRANSCRIPT_OVERHEAD_CHARS + 1500 + 1500] * n, bool(n)


def build_plan(args) -> dict:
    """Everything the run would do, with no backend constructed."""
    apply_scenario(args)
    needed = [(args.split, "--split", "--fetch"), (args.gap_items, "--gap-items", "--fetch")]
    if args.cue_set == "single":
        needed.append((args.single_pairs, "--single-pairs", "--single-factor"))
    else:
        needed += [(args.items_original, "--items-original", "--fetch"), (args.items_minimal, "--items-minimal", "--fetch")]
    for path, what, flag in needed:
        if not _exists(path):
            raise SystemExit(f"{what} {path} not found; generate it with "
                             f"python3 scripts/convert_evalawarebench.py {flag} (see data/benchmarks/README.md)")
    ids = load_split(args.split)[args.side]
    pairs, limit = _select_pairs(args, ids)
    pairs_path = os.path.join(args.work, f"cue_pairs_{args.cue_set}_{args.side}_{len(pairs)}.jsonl")
    envs = cal.distinct_env_list(pairs)
    probes = load_probe_questions(args.probe_questions) if _exists(args.probe_questions) else None
    labelled_path, labelled_chars, labelled_assumed = _labelled_inputs(args)
    env_mean = (sum(len(e.get("system", "")) + len(e["user"]) for e in envs) / len(envs)) if envs else 0
    have_kappa, hand_chars, hand_assumed = _hand_inputs(args, env_mean)
    gap_items = [] if args.no_gap else cal.load_gap_items(args.gap_items, args.split, args.side, args.gap_limit or None)[0]
    gap_envs = [dict(sc.original) for sc in gap_items]
    dev_target = args.dev_target or DEV_TARGET_PLACEHOLDER
    phases = ["dev", "final"] if args.phase == "both" else [args.phase]
    steps = []
    for phase in phases:
        cells = ([(dev_target, [args.dev_judge])] if phase == "dev" else
                 [(t, judges_for(t, args.dev_judge, args.heldout_judge)) for t in args.heldout_targets])
        for t, judges in cells:
            answerers = [t] + judges   # Measurer.judges: J1 in dev, both held-out judges in final
            lines = cal.estimate_cost(t, answerers, judges[0], envs, probes, labelled_chars, hand_chars,
                                      gap_envs, args.gap_seeds, judges[0])
            q = [len(probe_set_for(probes or {"default": DEFAULT_PROBE_QUESTIONS}, x)) for x in answerers]
            steps.append({"phase": phase, "target": t, "judges": judges, "answerers": answerers, "lines": lines,
                          "sample_calls": cal.sample_calls(q[0], q[1:]), "probe_counts": dict(zip(answerers, q)),
                          "gate_cmd": _gate_cmd(args, phase, t, judges, pairs_path, probes, labelled_path, have_kappa),
                          "gap_args": _gap_args(args, t, judges[0]) if gap_items else None})
    return {"pairs": pairs, "pairs_path": pairs_path, "pair_limit": limit, "envs": envs, "probes": probes,
            "labelled": labelled_path, "n_labelled": len(labelled_chars), "labelled_assumed": labelled_assumed,
            "have_kappa": have_kappa, "n_hand": len(hand_chars), "hand_assumed": hand_assumed,
            "n_gap_items": len(gap_items), "dev_target": dev_target, "steps": steps}


def _gate_cmd(args, phase, target, judges, pairs_path, probes, labelled_path, have_kappa) -> list:
    cmd = ["python3", "-m", "autoresearch", "--llm", args.llm, "calibrate", "--mode", phase, "--target", target,
           "--judge", judges[0], "--generator", judges[0]]
    if phase == "final":
        cmd += ["--heldout-target", target, "--heldout-judges"] + list(judges)
    cmd += ["--cue-pairs", pairs_path]
    if probes:
        cmd += ["--probe-questions", args.probe_questions]
    if labelled_path:
        cmd += ["--labelled", labelled_path]
    if have_kappa:
        cmd += ["--transcripts", args.transcripts, "--hand-labels", args.hand_labels]
    return cmd + ["--max-calls", str(args.max_calls), "--max-cost", str(args.max_cost_usd), "--out", args.out_gate]


def _gap_args(args, target, judge) -> list:
    # The printed command leaves out --approved-by-nathan on purpose: pasted
    # as-is it prints its estimate and refuses, so approval stays a typed act.
    return ["--llm", args.llm, "--target", target, "--judge", judge, "--generator", judge,
            "--items", args.gap_items, "--split", args.split, "--side", args.side,
            "--limit", str(args.gap_limit), "--seeds", str(args.gap_seeds), "--max-calls", str(args.max_calls),
            "--max-cost-usd", str(args.max_cost_usd), "--workers", str(args.workers), "--out", args.out_gap]


def _usd(known: float, unknown: bool) -> str:
    return f"${known:,.2f}" + (" + GPU time (unknown)" if unknown else "")


def _sum(lines, gate_only=False):
    ls = [x for x in lines if not (gate_only and x.step.startswith("V3"))]
    return (sum(x.calls for x in ls), sum(x.usd or 0.0 for x in ls), any(x.usd is None for x in ls))


def print_plan(plan: dict, args) -> None:
    scen = f"scenario {args.scenario}: {SCENARIOS[args.scenario]['about']}" if args.scenario else "custom scope"
    print(f"C1 run plan ({scen})")
    print(f"  cue pairs: {len(plan['pairs'])} {args.side} pairs ({args.cue_set}), {len(plan['envs'])} distinct "
          f"environments answered (cue, no cue, placebo; cached)")
    lab = (f"{plan['n_labelled']} transcripts" + (" ASSUMED at the 20,000-char cut (gated file not on disk)"
                                                  if plan["labelled_assumed"] else f" -> {plan['labelled']}"))
    print(f"  labelled set (a): {lab if plan['n_labelled'] else 'none'}")
    hand = f"{plan['n_hand']}" + (" ASSUMED (no hand labels on disk yet)" if plan["hand_assumed"] else "")
    print(f"  hand labels (d): {hand if plan['n_hand'] else 'none'}; V3: "
          f"{plan['n_gap_items']} items x {args.gap_seeds} samples" if plan["n_gap_items"] else "  V3: skipped")
    if plan["dev_target"] == DEV_TARGET_PLACEHOLDER and args.phase != "final":
        print(f"  dev target: {DEV_TARGET_PLACEHOLDER} (placeholder; pass --dev-target to execute)")
    missing = [n for n, ok in (("labelled set (check a)", plan["labelled"]), ("hand labels (check d)", plan["have_kappa"]),
                               ("probe questions", plan["probes"])) if not ok]
    if missing:
        print("  missing inputs (those checks would be SKIPPED, and a skipped check fails the gate): " + "; ".join(missing))
    print("\nAssumptions behind every number below (upper bounds unless marked):")
    for a in cal.cost_assumptions():
        print("  - " + a)
    rows = []
    for s in plan["steps"]:
        print(f"\n== {s['phase']} phase | target {s['target']} | A2 answerers: {', '.join(s['answerers'])} | "
              f"A1 + V3 judge: {s['judges'][0]}")
        if a1_is_lower_bound(s["target"]):
            print("   (this API returns reasoning SUMMARIES: A1 on this target is a LOWER BOUND)")
        for x in s["lines"]:
            print(f"   {x.step:<42} {x.model}\n      {x.how}")
        qs = ", ".join(f"{k} {v}" for k, v in s["probe_counts"].items())
        print(f"   probe questions per answerer: {qs}. Loop, per Measurer.sample() (generated item, real corpus, "
              f"no faithfulness rewrite): up to {s['sample_calls']} calls")
        g, a = _sum(s["lines"], gate_only=True), _sum(s["lines"])
        print(f"   gate: {g[0]:,} calls, {_usd(g[1], g[2])} | gate + V3: {a[0]:,} calls, {_usd(a[1], a[2])}")
        if a[0] > args.max_calls:
            print(f"   WARNING: up to {a[0]:,} calls exceeds --max-calls {args.max_calls} per step; raise it or the step "
                  f"stops early and unanswered items fail their check")
        if a[1] > args.max_cost_usd:
            print(f"   WARNING: bound exceeds --max-cost-usd {args.max_cost_usd:g} per step; raise it or the step "
                  f"stops early and unanswered items fail their check")
        print("   " + " ".join(_q(x) for x in s["gate_cmd"]))
        if s["gap_args"]:
            print("   " + " ".join(_q(x) for x in ["python3", "scripts/c1_behaviour_gap.py"] + s["gap_args"]))
        rows.append((s["phase"], s["target"], g, a))
    print("\nSUMMARY (upper bounds under the assumptions above)")
    print(f"  {'phase':<6} {'target':<40} {'gate calls':>10} {'gate $':>12} {'+V3 calls':>10} {'+V3 $':>12}")
    for phase, t, g, a in rows:
        print(f"  {phase:<6} {t:<40} {g[0]:>10,} {('$%.2f' % g[1]) + ('+GPU' if g[2] else ''):>12} "
              f"{a[0]:>10,} {('$%.2f' % a[1]) + ('+GPU' if a[2] else ''):>12}")
    tg = [sum(r[2][i] for r in rows) for i in (0, 1)] + [any(r[2][2] for r in rows)]
    ta = [sum(r[3][i] for r in rows) for i in (0, 1)] + [any(r[3][2] for r in rows)]
    print(f"  {'total':<47} {tg[0]:>10,} {('$%.2f' % tg[1]) + ('+GPU' if tg[2] else ''):>12} "
          f"{ta[0]:>10,} {('$%.2f' % ta[1]) + ('+GPU' if ta[2] else ''):>12}")
    if tg[2] or ta[2]:
        print("  +GPU: the openai-compat dev target (Qwen on Modal) bills GPU time, not tokens; its share is not in $.")


def _q(x: str) -> str:
    return x if x and all(c.isalnum() or c in "-_./:+=#" for c in x) else json.dumps(x)


def _git(*a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)


def preflight(args) -> list:
    """Reasons --execute must refuse; empty means go."""
    problems = []
    if not args.approved_by_nathan:
        problems.append("--execute needs --approved-by-nathan (AGENTS.md rule 5: costly runs need the user's OK)")
    if args.phase == "both":
        problems.append("--execute runs one phase at a time: pass --phase dev or --phase final")
    if args.phase in ("dev", "both") and not args.dev_target:
        problems.append("--dev-target is required for the dev phase (the Qwen served model id, from C2)")
    dirty = _git("status", "--porcelain", "--", "autoresearch").stdout.strip()
    if dirty:
        problems.append(f"autoresearch/ has uncommitted changes, so the code version would be ambiguous:\n{dirty}")
    rel = os.path.relpath(os.path.abspath(args.prereg), ROOT)
    if not os.path.exists(args.prereg):
        problems.append(f"preregistration {args.prereg} does not exist")
    elif _git("ls-files", "--error-unmatch", rel).returncode != 0:
        problems.append(f"preregistration {args.prereg} is not committed")
    elif _git("diff", "--quiet", "HEAD", "--", rel).returncode != 0:
        problems.append(f"preregistration {args.prereg} has uncommitted edits")
    else:
        with open(args.prereg) as f:
            status = str(json.load(f).get("status", ""))
        if status.upper().startswith("DRAFT"):
            problems.append(f"preregistration {args.prereg} is still a draft (status: {status[:60]!r})")
    return problems


def build_models(step: dict, mk):
    """dev: the dev target with J1 as judge (A2 is the target's own answer).
    final: the held-out target with both judges as held-out judges, the
    cross-family one first (it becomes measurer.judge: A1 and V3 labels)."""
    t, judges = step["target"], step["judges"]
    if step["phase"] == "dev":
        return Models(generator=mk(judges[0]), target=mk(t), judge=mk(judges[0]))
    return Models(generator=mk(judges[0]), target=mk(t), judge=mk(judges[0]),
                  heldout_target=mk(t), heldout_judges=[mk(j) for j in judges])


def execute(plan: dict, args) -> list:
    """Run every step in-process. With --offline every backend is OfflineLLM,
    whatever the specs say. Returns [(phase, target, step, path, passed/measurable)]."""
    gap = _gap_module() if any(s["gap_args"] for s in plan["steps"]) else None
    transcripts = cal.load_transcripts(args.transcripts) if plan["have_kappa"] else None
    hand = cal.load_hand_labels(args.hand_labels) if plan["have_kappa"] else None
    labelled = cal.load_labelled(plan["labelled"], max_chars=None) if plan["labelled"] else None
    gate_out = os.path.join(cal.OFFLINE_OUT, "calibration") if args.offline else args.out_gate
    if args.offline:
        print(f"\noffline run: reports go to {cal.OFFLINE_OUT} (git-ignored), not --out-gate/--out-gap")
    done = []
    for s in plan["steps"]:
        t, phase = s["target"], s["phase"]
        budget = Budget(max_calls=args.max_calls, max_cost_usd=args.max_cost_usd, max_seconds=7200)
        mk = (lambda spec: OfflineLLM(budget)) if args.offline else (lambda spec: cal.make_llm(spec, args.llm, budget))
        ms = Measurer(build_models(s, mk), workers=args.workers, simulator=cal.OfflineCalibrationWorld(), mode=phase,
                      probe_questions=plan["probes"])
        inputs = {"phase": phase, "target_spec": t, "judge_specs": s["judges"], "a2_answerers": s["answerers"],
                  "cue_pairs": plan["pairs_path"], "split": args.split, "side": args.side, "cue_set": args.cue_set,
                  "single_pairs": args.single_pairs if args.cue_set == "single" else None,
                  "scenario": args.scenario, "pair_limit": plan["pair_limit"], "labelled": plan["labelled"],
                  "labelled_seed": args.labelled_seed if plan["labelled"] else None,
                  "probe_questions": args.probe_questions if plan["probes"] else None,
                  "transcripts": args.transcripts if plan["have_kappa"] else None,
                  "hand_labels": args.hand_labels if plan["have_kappa"] else None,
                  "a1_lower_bound": a1_is_lower_bound(t), "driver": "scripts/c1_run_gate.py"}
        rep, path = cal.run_gate(ms, budget, labelled=labelled, cue_pairs=plan["pairs"], transcripts=transcripts,
                                 hand_labels=hand, out_dir=gate_out, inputs=inputs)
        print(f"\n[{phase} | {t}] gate ({'offline dry run' if rep['offline'] else 'REAL'}):")
        for line in cal.verdict_lines(rep):
            print("  " + line)
        print(f"  -> {path}")
        done.append((phase, t, "gate", path, rep["passed"]))
        if not s["gap_args"]:
            continue
        offline_models = ["--llm", "offline", "--target", "offline", "--judge", "offline", "--generator", "offline"]
        g_args = gap.build_parser().parse_args(s["gap_args"] + (offline_models if args.offline else ["--approved-by-nathan"]))
        g = gap.run(g_args)
        g["models"]["requested"]["target_in_plan"] = t
        with open(g["path"], "w") as f:
            json.dump({k: v for k, v in g.items() if k != "path"}, f, indent=1)
        print(f"[{phase} | {t}] behaviour gap: measurable={g['result']['overall']['measurable']} "
              f"gap={g['result']['overall']['gap']} -> {g['path']}")
        done.append((phase, t, "gap", g["path"], g["result"]["overall"]["measurable"]))
    if args.offline:
        print("\n" + cal.OFFLINE_NOTE)
    return done


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.offline and args.execute:
        raise SystemExit("--offline and --execute are exclusive: --offline already executes, with offline backends")
    plan = build_plan(args)
    # Written even on a dry run (a local file, no calls) so the printed calibrate commands run as shown.
    cal.write_cue_pairs(plan["pairs"], plan["pairs_path"])
    print_plan(plan, args)
    if args.execute:
        problems = preflight(args)
        if problems:
            print("\nREFUSING to execute (no calls were made):")
            for p in problems:
                print(" - " + p)
            return 2
        execute(plan, args)
        return 0
    if args.offline:
        execute(plan, args)
        return 0
    print("\nDRY RUN: nothing was called. Re-run with --phase dev|final --execute --approved-by-nathan once the prereg "
          "is final, or --offline to exercise the plumbing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
