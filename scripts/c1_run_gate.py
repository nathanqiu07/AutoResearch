"""Driver for the whole C1 real run: the calibration gate and the V3 behaviour
gap, for each target in a list (default: Claude Sonnet 4.6 with thinking, and
an OpenAI model named with --openai-target).

  python3 scripts/c1_run_gate.py --judge <spec> --openai-target <model>     # DRY RUN (default): prints only
  python3 scripts/c1_run_gate.py --offline                                  # runs everything offline (plumbing)
  python3 scripts/c1_run_gate.py --judge <spec> --openai-target <model> \
      --execute --approved-by-nathan                                        # real run: costs money

By default it only prints: for each target, the equivalent
`python3 -m autoresearch calibrate ...` and `scripts/c1_behaviour_gap.py ...`
commands with an upper-bound call estimate (and a cost bound if you pass
--usd-per-call). Nothing is called and no backend is constructed.

The cue pairs are the original vs minimal-cue items on the dev side of the
frozen split, first --pair-limit by id (about 20 for the subset run, 0 = all
dev pairs). They are written to --work (also on a dry run) so the printed
calibrate command repeats the run exactly. The printed behaviour-gap command
omits --approved-by-nathan, so pasting it unedited refuses. The probe questions, the labelled set and the hand
labels are used only if their files exist.

Execution is in-process (calibrate.run_gate and c1_behaviour_gap.run, the same
functions the printed commands reach), which lets the driver restrict pairs to
the dev split and apply --max-cost-usd; the calibrate CLI has no spend flag.

--execute refuses unless --approved-by-nathan is given, autoresearch/ has no
uncommitted changes, and the preregistration (--prereg) is committed,
unmodified, and no longer marked draft.
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
from autoresearch.research.measure import Measurer, Models, load_probe_questions  # noqa: E402

SONNET_TARGET = "anthropic:claude-sonnet-4-6+thinking"
BENCH = os.path.join("data", "benchmarks")


def _gap_module():
    spec = importlib.util.spec_from_file_location("c1_behaviour_gap", os.path.join(ROOT, "scripts", "c1_behaviour_gap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--targets", nargs="+", help=f"target specs (default: {SONNET_TARGET} and openai:<--openai-target>)")
    p.add_argument("--openai-target", help="OpenAI model id, e.g. '<model>+thinking'; required unless --offline")
    p.add_argument("--judge", help="judge spec (A1, A2 answers are the target's own); required unless --offline")
    p.add_argument("--generator", help="never called by the gate; defaults to the judge")
    p.add_argument("--llm", default="anthropic", help="backend for specs without a known prefix")
    p.add_argument("--mode", default="dev", choices=["dev", "final"])
    p.add_argument("--items-original", default=os.path.join(BENCH, "evalawarebench_original.jsonl"))
    p.add_argument("--items-minimal", default=os.path.join(BENCH, "evalawarebench_minimal_cue.jsonl"))
    p.add_argument("--split", default=os.path.join(BENCH, "evalawarebench_split.json"))
    p.add_argument("--side", default="dev", choices=["dev", "heldout"])
    p.add_argument("--pair-limit", type=int, default=20, help="first N dev cue pairs by id; 0 = all")
    p.add_argument("--probe-questions", default=os.path.join(BENCH, "evaldetect_probes.json"))
    p.add_argument("--labelled", default=os.path.join(BENCH, "needham", "dataset.json"))
    p.add_argument("--transcripts", default=os.path.join("data", "labels", "transcripts.jsonl"))
    p.add_argument("--hand-labels", default=os.path.join("data", "labels", "hand_labels.jsonl"))
    p.add_argument("--gap-items", default=os.path.join(BENCH, "evalawarebench_minimal_cue.jsonl"),
                   help="items for V3 (default minimal-cue: the base rate deployment would see)")
    p.add_argument("--gap-limit", type=int, default=20, help="first N dev items for V3; 0 = all")
    p.add_argument("--gap-seeds", type=int, default=2, help="V3 samples per item")
    p.add_argument("--max-calls", type=int, default=4000, help="per step")
    p.add_argument("--max-cost-usd", type=float, default=40.0, help="per step; binds where the backend reports cost (anthropic, openai, claude-cli; not openai-compat)")
    p.add_argument("--usd-per-call", type=float, help="rough average price, to print a cost bound")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--work", default=os.path.join("runs", "c1"), help="where the cue-pair subset file goes")
    p.add_argument("--out-gate", default=os.path.join("results", "calibration"))
    p.add_argument("--out-gap", default=os.path.join("results", "behaviour_gap"))
    p.add_argument("--prereg", default=os.path.join("results", "prereg", "C1_gate.json"))
    p.add_argument("--offline", action="store_true", help="execute every step with offline backends")
    p.add_argument("--execute", action="store_true", help="make the real calls (needs --approved-by-nathan)")
    p.add_argument("--approved-by-nathan", action="store_true")
    return p


def resolve_targets(args) -> list:
    if args.targets:
        return list(args.targets)
    if args.offline:
        return [SONNET_TARGET, "openai:" + (args.openai_target or "<model>")]
    if not args.openai_target:
        raise SystemExit("--openai-target is required (Nathan has not named the OpenAI model; it is never hard-coded)")
    o = args.openai_target
    return [SONNET_TARGET, o if cal.spec_backend(o, "") else "openai:" + o]


def _exists(path):
    return bool(path) and os.path.exists(path)


def build_plan(args) -> dict:
    """Everything the run would do, with no backend constructed."""
    targets = resolve_targets(args)
    if not args.offline and not args.judge:
        raise SystemExit("--judge is required (pick one from another family than the targets)")
    judge = args.judge or "offline"
    generator = args.generator or judge
    for path, what in ((args.items_original, "--items-original"), (args.items_minimal, "--items-minimal"),
                       (args.split, "--split"), (args.gap_items, "--gap-items")):
        if not _exists(path):
            raise SystemExit(f"{what} {path} not found; generate it with "
                             "python3 scripts/convert_evalawarebench.py --fetch (see data/benchmarks/README.md)")
    ids = load_split(args.split)[args.side]
    pairs = cal.pair_items(args.items_original, args.items_minimal, ids=[i for i in ids], limit=args.pair_limit or None)
    pairs_path = os.path.join(args.work, f"cue_pairs_{args.side}_{len(pairs)}.jsonl")
    probes = load_probe_questions(args.probe_questions) if _exists(args.probe_questions) else None
    labelled = args.labelled if _exists(args.labelled) else None
    n_labelled = len(cal.load_labelled(labelled)) if labelled else 0
    have_kappa = _exists(args.transcripts) and _exists(args.hand_labels)
    n_hand = sum(v is not None for v in cal.load_hand_labels(args.hand_labels).values()) if have_kappa else 0
    gap_items, _ = cal.load_gap_items(args.gap_items, args.split, args.side, args.gap_limit or None)
    steps = []
    for t in targets:
        gate_cmd = ["python3", "-m", "autoresearch", "--llm", args.llm, "calibrate", "--target", t, "--judge", judge,
                    "--generator", generator, "--mode", args.mode, "--cue-pairs", pairs_path]
        if probes:
            gate_cmd += ["--probe-questions", args.probe_questions]
        if labelled:
            gate_cmd += ["--labelled", labelled]
        if have_kappa:
            gate_cmd += ["--transcripts", args.transcripts, "--hand-labels", args.hand_labels]
        gate_cmd += ["--max-calls", str(args.max_calls), "--out", args.out_gate]
        # The printed command leaves out --approved-by-nathan on purpose: pasted
        # as-is it prints its estimate and refuses, so approval stays a typed act.
        gap_args = ["--llm", args.llm, "--target", t, "--judge", judge, "--generator", generator,
                    "--items", args.gap_items, "--split", args.split, "--side", args.side,
                    "--limit", str(args.gap_limit), "--seeds", str(args.gap_seeds), "--max-calls", str(args.max_calls),
                    "--max-cost-usd", str(args.max_cost_usd), "--workers", str(args.workers), "--out", args.out_gap]
        gap_cmd = ["python3", "scripts/c1_behaviour_gap.py"] + gap_args
        gate_calls = cal.estimate_gate_calls(cal.probe_count(probes, t), n_labelled, len(pairs), n_hand)
        gap_calls = cal.estimate_gap_calls(len(gap_items), args.gap_seeds)
        steps.append({"target": t, "gate": {"cmd": gate_cmd, "calls": gate_calls},
                      "gap": {"cmd": gap_cmd, "args": gap_args, "calls": gap_calls}})
    return {"targets": targets, "judge": judge, "generator": generator, "pairs": pairs, "pairs_path": pairs_path,
            "probes": probes, "labelled": labelled, "n_labelled": n_labelled, "have_kappa": have_kappa,
            "n_hand": n_hand, "n_gap_items": len(gap_items), "steps": steps}


def print_plan(plan: dict, args) -> None:
    missing = [name for name, ok in (("labelled set (check a)", plan["labelled"]),
                                     ("hand labels (check d)", plan["have_kappa"]),
                                     ("probe questions (default placeholders used)", plan["probes"])) if not ok]
    print(f"C1 run plan: {len(plan['targets'])} targets, judge={plan['judge']}, mode={args.mode}, "
          f"{len(plan['pairs'])} {args.side} cue pairs, {plan['n_labelled']} labelled, {plan['n_hand']} hand labels, "
          f"V3 on {plan['n_gap_items']} items x {args.gap_seeds}")
    if missing:
        print("missing inputs (those checks will be SKIPPED and the gate will fail): " + "; ".join(missing))
    total = 0
    for s in plan["steps"]:
        for name in ("gate", "gap"):
            st = s[name]
            total += st["calls"]
            cost = f"<= ${st['calls'] * args.usd_per_call:.2f}" if args.usd_per_call else "cost unknown (--usd-per-call)"
            print(f"\n[{s['target']}] {name}: up to {st['calls']} calls, {cost}")
            print("  " + " ".join(_q(x) for x in st["cmd"]))
    cost = f", <= ${total * args.usd_per_call:.2f}" if args.usd_per_call else ""
    print(f"\ntotal: up to {total} calls{cost}. The gate step runs in-process with --max-cost-usd {args.max_cost_usd}; "
          f"the printed calibrate command is otherwise identical.")


def _q(x: str) -> str:
    return x if x and all(c.isalnum() or c in "-_./:+=#" for c in x) else json.dumps(x)


def _git(*a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)


def preflight(args) -> list:
    """Reasons --execute must refuse; empty means go."""
    problems = []
    if not args.approved_by_nathan:
        problems.append("--execute needs --approved-by-nathan (AGENTS.md rule 5: costly runs need the user's OK)")
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


def execute(plan: dict, args) -> list:
    """Run every step in-process. With --offline every backend is OfflineLLM,
    whatever the specs say. Returns [(target, step, path, passed/measurable)]."""
    gap = _gap_module()
    transcripts = cal.load_transcripts(args.transcripts) if plan["have_kappa"] else None
    hand = cal.load_hand_labels(args.hand_labels) if plan["have_kappa"] else None
    labelled = cal.load_labelled(plan["labelled"]) if plan["labelled"] else None
    done = []
    for s in plan["steps"]:
        t = s["target"]
        budget = Budget(max_calls=args.max_calls, max_cost_usd=args.max_cost_usd, max_seconds=7200)
        mk = (lambda spec: OfflineLLM(budget)) if args.offline else (lambda spec: cal.make_llm(spec, args.llm, budget))
        models = Models(generator=mk(plan["generator"]), target=mk(t), judge=mk(plan["judge"]))
        ms = Measurer(models, workers=args.workers, simulator=cal.OfflineCalibrationWorld(), mode=args.mode,
                      probe_questions=plan["probes"])
        inputs = {"target_spec": t, "judge_spec": plan["judge"], "generator_spec": plan["generator"],
                  "cue_pairs": plan["pairs_path"], "items_original": args.items_original,
                  "items_minimal": args.items_minimal, "split": args.split, "side": args.side,
                  "pair_limit": args.pair_limit, "labelled": plan["labelled"],
                  "probe_questions": args.probe_questions if plan["probes"] else None,
                  "transcripts": args.transcripts if plan["have_kappa"] else None,
                  "hand_labels": args.hand_labels if plan["have_kappa"] else None, "driver": "scripts/c1_run_gate.py"}
        rep, path = cal.run_gate(ms, budget, labelled=labelled, cue_pairs=plan["pairs"], transcripts=transcripts,
                                 hand_labels=hand, out_dir=args.out_gate, inputs=inputs)
        print(f"\n[{t}] gate ({'offline dry run' if rep['offline'] else 'REAL'}):")
        for line in cal.verdict_lines(rep):
            print("  " + line)
        print(f"  -> {path}")
        done.append((t, "gate", path, rep["passed"]))
        offline_models = ["--llm", "offline", "--target", "offline", "--judge", "offline", "--generator", "offline"]
        g_args = gap.build_parser().parse_args(
            s["gap"]["args"] + (offline_models if args.offline else ["--approved-by-nathan"]))
        g = gap.run(g_args)
        g["models"]["requested"]["target_in_plan"] = t
        with open(g["path"], "w") as f:
            json.dump({k: v for k, v in g.items() if k != "path"}, f, indent=1)
        print(f"[{t}] behaviour gap: measurable={g['result']['overall']['measurable']} "
              f"gap={g['result']['overall']['gap']} -> {g['path']}")
        done.append((t, "gap", g["path"], g["result"]["overall"]["measurable"]))
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
    print("\nDRY RUN: nothing was called. Re-run with --execute --approved-by-nathan once the prereg is final, "
          "or --offline to exercise the plumbing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
