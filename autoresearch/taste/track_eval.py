"""Public-track evaluation (E2): does a model fit on a researcher's pairs from before the cutoff T
predict his choices after T better than the baselines?

Arms, all scored on the held-out pairs:
  m0          no history
  m0_named    no history, but told whose choices these are (contamination probe: a gap over
              m0 means the model already knows his work)
  m1_pairs    raw history: his pairs from before T
  m1_docs     his documents from before T, in the prompt
  selected:X  the method chosen on history alone (select_method)

A pair counts as right only if the model picks his option in both a/b orders. Intervals
resample source documents (group_id), since pairs from one document are not independent.
The selected method succeeds if its gain over both m1 arms has a 90% interval above 0.

    python3 -m autoresearch.taste.track_eval gate   --researcher <slug> --max-usd 10
    python3 -m autoresearch.taste.track_eval select --researcher <slug> --max-usd 40
    python3 -m autoresearch.taste.track_eval e2     --researcher <slug> --name "<Full Name>" --selected m5 --max-usd 40
    python3 -m autoresearch.taste.track_eval final  --researcher <slug> --selected m5 --max-usd 10
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
from typing import Callable, Dict, List, Optional, Tuple

from ..llm import LLM
from ..research.decisions import code_version
from . import timesplit
from .methods import create_method
from .methods.m0_none import NoHistory
from .researcher import DEFAULT_ROOT, Researcher, load_researcher
from .usermodel import Choice, UserModel

GATE = "gate_timesplit.jsonl"
GATE_THRESHOLD = 0.75
WORKERS = 16  # judge and user-model calls on separate pairs run in parallel; --workers overrides
CACHE = os.path.join("runs", "track_s", "cache", "usermodel")


def load_choices(path: str) -> List[Choice]:
    return [Choice(**r) for r in timesplit._read_jsonl(path)]


def paired_correct(model, c: Choice) -> bool:
    """Right only if the model picks his option with it shown first and shown second."""
    first = model.predict(c.context, [c.a_text, c.b_text]).choice == c.chosen
    second = model.predict(c.context, [c.b_text, c.a_text]).choice == ("b" if c.chosen == "a" else "a")
    return first and second


def _each(fn, choices: List[Choice], workers: Optional[int] = None) -> list:
    """fn(choice) for every choice, in order, with up to `workers` (default WORKERS) running at once."""
    with concurrent.futures.ThreadPoolExecutor(workers or WORKERS) as pool:
        return list(pool.map(fn, choices))


def score(model, choices: List[Choice]) -> Dict[str, Dict[str, bool]]:
    """{group_id: {example_id: correct}}."""
    out: Dict[str, Dict[str, bool]] = {}
    for c, ok in zip(choices, _each(lambda c: paired_correct(model, c), choices)):
        out.setdefault(c.group_id or c.example_id, {})[c.example_id] = ok
    return out


def _bounds(stats: List[float], level: float) -> Tuple[float, float]:
    stats.sort()
    n = len(stats)
    return stats[int((1 - level) / 2 * n)], stats[min(n - 1, int((1 + level) / 2 * n))]


def cluster_ci(by_group: Dict[str, List[float]], level=0.9, n=2000, seed=0) -> Tuple[float, float, float]:
    """(mean score, low, high), resampling groups with replacement. Scores are bools or floats."""
    groups = sorted(by_group)
    if not groups:
        raise ValueError("no pairs to score")
    acc = sum(sum(v) for v in by_group.values()) / sum(len(v) for v in by_group.values())
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        picks = [by_group[rng.choice(groups)] for _ in groups]
        stats.append(sum(sum(v) for v in picks) / sum(len(v) for v in picks))
    return (acc, *_bounds(stats, level))


def cluster_diff_ci(a: Dict[str, List[bool]], b: Dict[str, List[bool]], level=0.9, n=2000,
                    seed=0) -> Tuple[float, float, float]:
    """Accuracy of a minus b on the same pairs, with a group-resampled interval."""
    groups = sorted(set(a) & set(b))
    if not groups:
        raise ValueError("no pairs to score in both arms")

    def diff(gs):
        return sum(sum(a[g]) - sum(b[g]) for g in gs) / sum(len(a[g]) for g in gs)

    rng = random.Random(seed)
    stats = [diff([rng.choice(groups) for _ in groups]) for _ in range(n)]
    return (diff(groups), *_bounds(stats, level))


class NamedNoHistory(NoHistory):
    """M0, optionally told whose choices these are."""

    def __init__(self, llm: LLM, name: Optional[str], **kw):
        super().__init__(llm, **kw)
        self.name = name

    def predict(self, context, options):
        if self.name:
            context = f"These are choices made by {self.name}.\n{context}"
        return super().predict(context, options)


class DocsInPrompt(UserModel):
    """M1-docs: his writing from before T in the prompt, newest kept when it doesn't all fit."""
    method_id = "m1_docs"

    def __init__(self, llm: LLM, docs: List[Tuple[str, str]], max_chars: int = 60_000, **kw):
        super().__init__(llm, **kw)
        # Each document gets at most a quarter of the space, so one long paper can't crowd out the rest.
        kept, used = [], 0
        for _, text in reversed(docs):
            piece = text[:min(max_chars // 4, max_chars - used)]
            if not piece:
                break
            kept.append(piece)
            used += len(piece)
        self.persona = "Their writing from before this decision, oldest first:\n\n" + "\n\n---\n\n".join(reversed(kept))

    def predict(self, context, options):
        return self._predict_with(context, options, persona=self.persona)


def docs_arm(researcher: Researcher, llm: LLM, cutoff: str, cache_dir: Optional[str] = None) -> DocsInPrompt:
    return DocsInPrompt(llm, timesplit.docs_before(researcher, cutoff), cache_dir=cache_dir)


class BlindJudge(NoHistory):
    def predict(self, context, options):
        return super().predict("Which of these is the better research decision?\n" + context, options)


def blind_judge(choices: List[Choice], llm: LLM, cache_dir: Optional[str] = None) -> Dict[str, bool]:
    """example_id -> a model with no history picks his option as better research in both orders."""
    judge = BlindJudge(llm, cache_dir=cache_dir)
    return {c.example_id: ok for c, ok in zip(choices, _each(lambda c: paired_correct(judge, c), choices))}


class StyleJudge(NoHistory):
    def predict(self, context, options):
        return super().predict("Which option was paraphrased from a published paper, and which was invented? "
                               "Pick the paraphrased one.\n" + context, options)


def style_scores(choices: List[Choice], llm: LLM, cache_dir: Optional[str] = None) -> Dict[str, float]:
    """example_id -> share of the two orders in which a blind judge calls his option the published
    one. A judge that can't tell, or always picks one position, scores 0.5."""
    judge = StyleJudge(llm, cache_dir=cache_dir)
    flip = {"a": "b", "b": "a"}
    def both_orders(c):
        return ((judge.predict(c.context, [c.a_text, c.b_text]).choice == c.chosen)
                + (judge.predict(c.context, [c.b_text, c.a_text]).choice == flip[c.chosen])) / 2
    return {c.example_id: v for c, v in zip(choices, _each(both_orders, choices))}


def style_leak(choices: List[Choice], scores: Dict[str, float]) -> dict:
    """Style-leak probe summary; flagged when the interval sits wholly above chance."""
    by_group: Dict[str, List[float]] = {}
    for c in choices:
        by_group.setdefault(c.group_id or c.example_id, []).append(scores[c.example_id])
    rate, lo, hi = cluster_ci(by_group)
    return {"rate": rate, "ci_low": lo, "ci_high": hi, "n_pairs": len(choices), "flagged": lo > 0.5}


def distractor_gate(researcher: Researcher, judge_llm: LLM, regenerate: Callable[[dict], Optional[dict]],
                    threshold: float = GATE_THRESHOLD, cache_dir: Optional[str] = None) -> dict:
    """If a blind judge spots his option on more than `threshold` of held-out pairs, rebuild each
    spotted pair once with the next distractor source and judge it again. Runs once per pair set.
    Then runs the style-leak probe on the final held-out pairs; it reports only, changing no pair."""
    root = researcher.root
    if os.path.exists(os.path.join(root, GATE)):
        raise FileExistsError(f"{GATE} exists; the gate runs once per pair set")
    heldout = load_choices(os.path.join(root, timesplit.HELDOUT))
    if not heldout:
        raise ValueError(f"no held-out pairs in {timesplit.HELDOUT}; run pairs with an earlier cutoff")
    before = blind_judge(heldout, judge_llm, cache_dir)
    flagged = [k for k, v in before.items() if v]
    pairs = timesplit._read_jsonl(os.path.join(root, timesplit.PAIRS))
    replaced = {}
    if before and len(flagged) / len(before) > threshold:
        by_id = {p["pair_id"]: p for p in pairs}
        for k in flagged:
            new = regenerate(by_id[k])
            if new:
                replaced[k] = new
        pairs = [replaced.get(p["pair_id"], p) for p in pairs]
        timesplit._write_jsonl(os.path.join(root, timesplit.PAIRS), pairs)
        timesplit.write_choice_files(researcher)
    new_ids = {v["pair_id"] for v in replaced.values()}
    after = blind_judge([c for c in load_choices(os.path.join(root, timesplit.HELDOUT)) if c.example_id in new_ids],
                        judge_llm, cache_dir)
    heldout = load_choices(os.path.join(root, timesplit.HELDOUT))
    style = style_scores(heldout, judge_llm, cache_dir)
    rows = [{"pair_id": k, "flagged_before": v, "regenerated_to": replaced[k]["pair_id"] if k in replaced else None,
             "flagged_after": after[replaced[k]["pair_id"]] if k in replaced else v,
             "style_leak": style[replaced[k]["pair_id"] if k in replaced else k]} for k, v in before.items()]
    leak = style_leak(heldout, style)
    # Written last: the file marks the gate as run, so a crash before here must leave it rerunnable.
    timesplit._write_jsonl(os.path.join(root, GATE), rows)
    return {"heldout": len(before), "flagged_before": len(flagged), "regenerated": len(replaced),
            "flagged_after": sum(r["flagged_after"] for r in rows), "threshold": threshold,
            "judge": judge_llm.label, "style_leak": leak}


def split_by_document(choices: List[Choice], share: float = 0.8) -> Tuple[List[Choice], List[Choice]]:
    """(earliest `share` of source documents, the rest); no document is on both sides."""
    first_seen: Dict[str, str] = {}
    for c in choices:
        g = c.group_id or c.example_id
        first_seen[g] = min(first_seen.get(g, c.timestamp), c.timestamp)
    order = sorted(first_seen, key=lambda g: (first_seen[g], g))
    early = set(order[:max(1, int(share * len(order)))])
    return ([c for c in choices if (c.group_id or c.example_id) in early],
            [c for c in choices if (c.group_id or c.example_id) not in early])


def _fit(method: str, llm: LLM, history: List[Choice], cache_dir: Optional[str] = None):
    """m1 sees every history pair. The other methods get up to 50 pairs (the most they accept)
    and a validation set of the latest documents, which some use to check or calibrate."""
    if method == "m1":
        model = create_method(method, llm, seed=0, cache_dir=cache_dir)
        model.fit(history, [])
        return model
    train, val = split_by_document(history)
    model = create_method(method, llm, seed=0, max_history=50, cache_dir=cache_dir)
    model.fit(train, val)
    return model


def select_method(history: List[Choice], llm: LLM, candidates=("m2", "m3", "m4", "m5", "m6", "m7"),
                  cache_dir: Optional[str] = None):
    """Fit each candidate on the earliest 80% of history's documents and score it on the rest."""
    train, val = split_by_document(history)
    if not val:
        raise ValueError("selection needs history pairs from at least two documents")
    # Candidates fit and score at the same time, sharing the WORKERS budget of parallel calls.
    share = max(1, WORKERS // len(candidates))

    def fit_and_score(m):
        model = _fit(m, llm, train, cache_dir)
        return sum(_each(lambda c: paired_correct(model, c), val, share)) / len(val)

    with concurrent.futures.ThreadPoolExecutor(len(candidates)) as pool:
        scores = dict(zip(candidates, pool.map(fit_and_score, candidates)))
    best = max(candidates, key=lambda m: scores[m])
    return best, scores


def _summary(by_group: Dict[str, Dict[str, bool]]) -> dict:
    acc, lo, hi = cluster_ci({g: list(v.values()) for g, v in by_group.items()})
    return {"accuracy": acc, "ci90": [lo, hi]}


def run_e2(researcher: Researcher, llm: LLM, name: str, selected: str,
           out_path: Optional[str] = None, cache_dir: Optional[str] = None) -> dict:
    root = researcher.root
    cutoffs = {p["cutoff"] for p in timesplit._read_jsonl(os.path.join(root, timesplit.PAIRS))}
    if len(cutoffs) != 1:
        raise ValueError(f"pairs carry cutoffs {sorted(cutoffs)}; expected exactly one")
    cutoff = cutoffs.pop()
    history = load_choices(os.path.join(root, timesplit.HISTORY))
    heldout = load_choices(os.path.join(root, timesplit.HELDOUT))
    if not heldout:
        raise ValueError(f"no held-out pairs in {timesplit.HELDOUT}; run pairs with an earlier cutoff")
    arms = {"m0": NamedNoHistory(llm, None, cache_dir=cache_dir),
            "m0_named": NamedNoHistory(llm, name, cache_dir=cache_dir),
            "m1_pairs": _fit("m1", llm, history, cache_dir), "m1_docs": docs_arm(researcher, llm, cutoff, cache_dir),
            f"selected:{selected}": _fit(selected, llm, history, cache_dir)}
    scored = {arm: score(model, heldout) for arm, model in arms.items()}
    flat = {arm: {k: v for g in s.values() for k, v in g.items()} for arm, s in scored.items()}
    lists = {arm: {g: list(v.values()) for g, v in s.items()} for arm, s in scored.items()}
    sel = f"selected:{selected}"
    diffs = {base: cluster_diff_ci(lists[sel], lists[base]) for base in ("m1_pairs", "m1_docs")}
    meta = {p["pair_id"]: p for p in timesplit._read_jsonl(os.path.join(root, timesplit.PAIRS))}
    breakdown = {}
    for field in ("tag", "author_position", "distractor_source"):
        cells: Dict[str, List[bool]] = {}
        for k, ok in flat[sel].items():
            cells.setdefault(str(meta.get(k, {}).get(field)), []).append(ok)
        breakdown[field] = {v: {"n": len(x), "accuracy": sum(x) / len(x)} for v, x in cells.items()}
    still_flagged = {r["regenerated_to"] or r["pair_id"] for r in timesplit._read_jsonl(os.path.join(root, GATE))
                     if r["flagged_after"]}
    unflagged = [ok for k, ok in flat[sel].items() if k not in still_flagged]
    report = {
        "researcher": researcher.slug, "cutoff": cutoff, "selected": selected,
        "n_pairs": len(heldout), "n_groups": len(scored["m0"]), "n_history": len(history),
        "arms": {arm: _summary(s) for arm, s in scored.items()},
        "selected_minus": {b: {"diff": d, "ci90": [lo, hi]} for b, (d, lo, hi) in diffs.items()},
        "success": all(lo > 0 for _, lo, _ in diffs.values()),
        "contamination_gap": dict(zip(("diff", "ci_low", "ci_high"), cluster_diff_ci(lists["m0_named"], lists["m0"]))),
        "selected_by": breakdown,
        "selected_without_still_flagged": {"n": len(unflagged),
                                           "accuracy": sum(unflagged) / len(unflagged) if unflagged else None},
        "model": llm.label, "code_version": code_version(), "cost_usd": round(llm.budget.cost_usd, 4),
    }
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
    return report


def final_model(researcher: Researcher, llm: LLM, selected: str, cache_dir: Optional[str] = None) -> str:
    """Fit the selected method on every pair (history and held-out) and save usermodel.json."""
    root = researcher.root
    pairs = (load_choices(os.path.join(root, timesplit.HISTORY))
             + load_choices(os.path.join(root, timesplit.HELDOUT)))
    path = os.path.join(root, "usermodel.json")
    _fit(selected, llm, pairs, cache_dir).save(path)
    return path


def main(argv=None):
    global WORKERS
    p = argparse.ArgumentParser(description="Public-track E2 (PLAN 12.2)")
    p.add_argument("--root", default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("gate", "select", "e2", "final"):
        c = sub.add_parser(name)
        c.add_argument("--researcher", required=True)
        c.add_argument("--llm", default="claude-cli")
        c.add_argument("--model", default="claude-sonnet-5-5")
        c.add_argument("--max-usd", type=float, required=True)
        c.add_argument("--workers", type=int, default=WORKERS, help="model calls run in parallel")
        if name == "gate":
            c.add_argument("--judge-model", default="claude-opus-5-5",
                           help="a different model from the one that wrote the pairs")
        if name in ("e2", "final"):
            c.add_argument("--selected", required=True)
        if name == "e2":
            c.add_argument("--name", required=True)
            c.add_argument("--out", default=None)
    args = p.parse_args(argv)
    WORKERS = args.workers
    from ..llm import Budget, get_llm
    budget = Budget(max_cost_usd=args.max_usd, max_seconds=12 * 3600)
    llm = get_llm(args.llm, args.model, budget)
    researcher = load_researcher(args.researcher, args.root)
    if args.command == "gate":
        from ..integrations.exa import ExaClient
        client = ExaClient(cache_dir=timesplit.EXA_CACHE)
        judge = get_llm(args.llm, args.judge_model, budget)
        report = distractor_gate(researcher, judge,
                                 lambda pair: timesplit.regenerate_pair(researcher, pair, llm, client), cache_dir=CACHE)
        report["exa_cost"] = round(client.cost, 4)
    elif args.command == "select":
        best, scores = select_method(load_choices(os.path.join(researcher.root, timesplit.HISTORY)), llm,
                                     cache_dir=CACHE)
        report = {"selected": best, "scores": scores}
    elif args.command == "e2":
        out = args.out or os.path.join("results", "track_s", f"E2_{researcher.slug}.json")
        report = run_e2(researcher, llm, args.name, args.selected, out_path=out, cache_dir=CACHE)
    else:
        report = {"saved": final_model(researcher, llm, args.selected, CACHE)}
    print(json.dumps(dict(report, llm_cost=round(budget.cost_usd, 4)), indent=2))


if __name__ == "__main__":
    main()
