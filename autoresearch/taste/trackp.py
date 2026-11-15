"""Track P (PLAN 6.3, 12.2): one team member's own research choices.

Everything lives in data/researchers/<slug>/:

  seed_pairs.jsonl     D1-style pairs: two candidate interventions for one item
  seed_choices.jsonl   the person's answers, as text `Choice` rows (source "seed")
  labels.jsonl         the person's choice at logged loop decisions D1-D6
  recheck.jsonl        re-asked items, for the noise ceiling
  usermodel.json       the fitted user model the loop loads (research/advisor.load_user_model)
  history.jsonl        the choices that model was fitted on, for the prompt arm (R1-P-prompt)
  CONSENT.md           who the person is and what they agreed to

Hold-out (fixed by hashing, so it never moves as answers arrive): 20% of seed
pairs, plus every label from a run on or after --label-cutoff. The rest is
split into history and val for `UserModel.fit`.

    python3 -m autoresearch.taste.trackp init --researcher <slug> --name "<full name>"
    python3 -m autoresearch.taste.trackp seed-pairs --researcher <slug> --n 50
    python3 -m autoresearch.taste.trackp answer --researcher <slug>
    python3 -m autoresearch.taste.trackp label --researcher <slug> runs/*/decisions.jsonl
    python3 -m autoresearch.taste.trackp recheck --researcher <slug>       # a few days later
    python3 -m autoresearch.taste.trackp status --researcher <slug> [--label-cutoff YYYY-MM-DD]
    python3 -m autoresearch.taste.trackp e2 --researcher <slug> --methods m0 m1 --backend ... --model ...
    python3 -m autoresearch.taste.trackp fit --researcher <slug> --method <selected> --backend ... --model ...
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import random
from dataclasses import asdict
from typing import Callable, Dict, List, Optional

from ..research.decisions import validate_record
from ..research.ideas import LIBRARY, Intervention
from ..research.stats import bootstrap_ci, mean
from .researcher import DEFAULT_ROOT
from .usermodel import Choice, digest

TRACKS_FILE = "tracks.json"   # read by cli.resolve_arm
SEED_PAIRS, SEED_CHOICES, LABELS, RECHECK = "seed_pairs.jsonl", "seed_choices.jsonl", "labels.jsonl", "recheck.jsonl"
HISTORY, USERMODEL = "history.jsonl", "usermodel.json"
QUESTION = "Which intervention would you test first to make this environment read less like an evaluation?"
CONSENT_TEMPLATE = """# Track P consent

Person: {name}
Slug: {slug}
Date: {date}

- [ ] Agrees that their seed choices, decision labels and written reasons are stored in this repo.
- [ ] Agrees that a user model fitted on them steers the research loop (R1-P) and is reported in results.
- [ ] Agrees that the fitted model is kept in shared memory (past.dev when PAST_API_KEY is set).

Recorded by:
"""


def _bucket(key: str) -> float:
    """A stable number in [0, 1) for a key."""
    return int(digest(key)[:8], 16) / 16 ** 8


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _read(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(path: str, row: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def init(root: str, slug: str, name: str) -> str:
    """Create the person's directory and consent form, and point track P at them."""
    path = os.path.join(root, slug)
    os.makedirs(path, exist_ok=True)
    consent = os.path.join(path, "CONSENT.md")
    if not os.path.exists(consent):
        with open(consent, "w") as f:
            f.write(CONSENT_TEMPLATE.format(name=name, slug=slug, date=datetime.date.today().isoformat()))
    tracks_path = os.path.join(root, TRACKS_FILE)
    tracks = {}
    if os.path.exists(tracks_path):
        with open(tracks_path) as f:
            tracks = json.load(f)
    tracks["P"] = slug
    with open(tracks_path, "w") as f:
        json.dump(tracks, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


# ---- seed pairs -----------------------------------------------------------

def item_context(sc) -> str:
    lines = [f"Item: {sc.name}", f"Research goal: {sc.goal}", f"Setting: {sc.setting}",
             f"The environment must keep this opportunity: {sc.probe}"]
    if sc.original:
        lines += ["Original system prompt: " + sc.original.get("system", ""),
                  "Original user message: " + sc.original.get("user", "")]
    return "\n".join(lines) + "\n\n" + QUESTION


def make_seed_pairs(items: list, n: int, seed: int = 0,
                    extra: Optional[Dict[str, List[Intervention]]] = None) -> List[dict]:
    """n distinct pairs, each two interventions for the same item, spread evenly over
    items. extra maps item name -> more candidate interventions (e.g. LLM proposals)."""
    rng = random.Random(seed)
    pools = {sc.name: LIBRARY + list((extra or {}).get(sc.name, [])) for sc in items}
    combos = [(sc, a, b) for sc in items for i, a in enumerate(pools[sc.name])
              for b in pools[sc.name][i + 1:] if a.text != b.text]
    if len(combos) < n:
        raise ValueError(f"only {len(combos)} distinct pairs available for {n} requested")
    rng.shuffle(combos)
    by_item: Dict[str, list] = {}
    for c in combos:
        by_item.setdefault(c[0].name, []).append(c)
    picked, queues = [], [by_item[sc.name] for sc in items if sc.name in by_item]
    while len(picked) < n:   # round-robin over items so each gets a fair share
        for q in queues:
            if q and len(picked) < n:
                picked.append(q.pop())
    pairs = []
    for sc, a, b in picked:
        if rng.random() < 0.5:
            a, b = b, a
        pairs.append({"pair_id": digest([sc.name, a.text, b.text])[:12], "item": sc.name,
                      "context": item_context(sc), "a_text": a.text, "b_text": b.text,
                      "a_category": a.category, "b_category": b.category,
                      "a_origin": a.origin, "b_origin": b.origin})
    return pairs


def write_seed_pairs(root: str, slug: str, pairs: List[dict]) -> str:
    """Append pairs not already present; existing pairs (and answers to them) are kept."""
    path = os.path.join(root, slug, SEED_PAIRS)
    have = {p["pair_id"] for p in _read(path)}
    for p in pairs:
        if p["pair_id"] not in have:
            _append(path, p)
            have.add(p["pair_id"])
    return path


def _ask_choice(ask, valid: List[str]) -> Optional[str]:
    """One of `valid`, "" to skip, or None to stop."""
    while True:
        ans = ask(f"{'/'.join(valid)}/skip/quit> ").strip().lower()
        if ans in valid:
            return ans
        if ans in ("", "s", "skip"):
            return ""
        if ans in ("q", "quit"):
            return None


def answer_seed_pairs(root: str, slug: str, ask: Callable = input, say: Callable = print,
                      limit: Optional[int] = None) -> int:
    """Ask the person each unanswered seed pair; store the answer and optional reason."""
    d = os.path.join(root, slug)
    done = {c["example_id"] for c in _read(os.path.join(d, SEED_CHOICES))}
    pending = [p for p in _read(os.path.join(d, SEED_PAIRS)) if p["pair_id"] not in done][:limit]
    n = 0
    for k, p in enumerate(pending, 1):
        say(f"\n[{k}/{len(pending)}] {p['context']}\n  a) {p['a_text']}\n  b) {p['b_text']}")
        ans = _ask_choice(ask, ["a", "b"])
        if ans is None:
            break
        if not ans:
            continue
        reason = ask("why? (optional, one sentence)> ").strip()
        c = Choice(user_id=slug, context=p["context"], a_text=p["a_text"], b_text=p["b_text"], chosen=ans,
                   decision_point="D1", reason=reason, timestamp=_now(), source="seed",
                   example_id=p["pair_id"])   # no group_id: pairs are independent, unlike a label's rows
        _append(os.path.join(d, SEED_CHOICES), asdict(c))
        n += 1
    return n


# ---- labels on loop decisions D1-D6 ---------------------------------------

def _display_order(key: str, k: int) -> List[int]:
    order = list(range(k))
    random.Random(key).shuffle(order)   # hides the loop's own option order
    return order


def label_decisions(root: str, slug: str, decision_paths: List[str], ask: Callable = input,
                    say: Callable = print, limit: Optional[int] = None) -> int:
    """Ask the person what they would have chosen at each logged decision. The loop's
    choice, the arm and the user model's choice are never shown."""
    out = os.path.join(root, slug, LABELS)
    done = {r["key"] for r in _read(out)}
    n = 0
    for path in decision_paths:
        run_date = datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
        for i, rec in enumerate(_read(path)):
            key = f"{rec.get('run_id')}:{i}"
            if key in done or len(rec.get("options") or []) < 2:
                continue
            errs = validate_record(rec)
            if errs:
                say(f"skipping {path} line {i + 1}: {'; '.join(errs)}")
                continue
            if limit is not None and n >= limit:
                return n
            order = _display_order(key, len(rec["options"]))
            say(f"\n[{rec['point']}, run {rec['run_id']} iter {rec['iter']}]\n{rec['context']}")
            if rec["evidence"]:
                say("evidence: " + json.dumps(rec["evidence"], sort_keys=True))
            for shown, idx in enumerate(order, 1):
                say(f"  {shown}) {rec['options'][idx]}")
            ans = _ask_choice(ask, [str(s) for s in range(1, len(order) + 1)])
            if ans is None:
                return n
            if not ans:
                continue
            reason = ask("why? (optional, one sentence)> ").strip()
            _append(out, {"key": key, "run_id": rec["run_id"], "iter": rec["iter"], "point": rec["point"],
                          "context": rec["context"], "options": rec["options"], "label": order[int(ans) - 1],
                          "reason": reason, "run_date": run_date, "timestamp": _now()})
            done.add(key)
            n += 1
    return n


def labels_to_choices(slug: str, labels: List[dict]) -> List[Choice]:
    """Each label becomes one pairwise Choice per rejected option (chosen vs it),
    with a/b order set by hash so the chosen text isn't always a."""
    out = []
    for r in labels:
        win = r["options"][r["label"]]
        for j, other in enumerate(r["options"]):
            if j == r["label"]:
                continue
            key = f"{r['key']}:{j}"
            a, b, chosen = (win, other, "a") if _bucket(key) < 0.5 else (other, win, "b")
            out.append(Choice(user_id=slug, context=r["context"], a_text=a, b_text=b, chosen=chosen,
                              decision_point=r["point"], reason=r.get("reason", ""), timestamp=r["timestamp"],
                              source="label", example_id=key, group_id=r["key"]))
    return out


# ---- noise ceiling ---------------------------------------------------------

def _answered_items(d: str) -> List[dict]:
    """Every answered seed pair and label, as {key, kind, context, options, answer, timestamp}."""
    items = [{"key": "seed:" + c["example_id"], "kind": "seed", "context": c["context"],
              "options": [c["a_text"], c["b_text"]], "answer": "ab".index(c["chosen"]),
              "timestamp": c["timestamp"]} for c in _read(os.path.join(d, SEED_CHOICES))]
    items += [{"key": "label:" + r["key"], "kind": "label", "context": r["context"], "options": r["options"],
               "answer": r["label"], "timestamp": r["timestamp"]} for r in _read(os.path.join(d, LABELS))]
    return items


def recheck(root: str, slug: str, ask: Callable = input, say: Callable = print, frac: float = 0.2,
            min_days: float = 3, now: Optional[datetime.datetime] = None) -> int:
    """Re-ask a fixed ~frac of answered items at least min_days after the first answer,
    with the options reversed and without showing the earlier answer."""
    d = os.path.join(root, slug)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    done = {r["key"] for r in _read(os.path.join(d, RECHECK))}
    due = [it for it in _answered_items(d) if it["key"] not in done and _bucket("recheck:" + it["key"]) < frac
           and (now - datetime.datetime.fromisoformat(it["timestamp"])).total_seconds() >= min_days * 86400]
    n = 0
    for it in due:
        order = list(reversed(range(len(it["options"]))))
        say(f"\n{it['context']}")
        for shown, idx in enumerate(order, 1):
            say(f"  {shown}) {it['options'][idx]}")
        ans = _ask_choice(ask, [str(s) for s in range(1, len(order) + 1)])
        if ans is None:
            break
        if not ans:
            continue
        _append(os.path.join(d, RECHECK), {"key": it["key"], "kind": it["kind"],
                                           "answer": order[int(ans) - 1], "timestamp": _now()})
        n += 1
    return n


def noise_ceiling(root: str, slug: str) -> dict:
    """The person's agreement with their own earlier answers, overall and per kind.
    Labels can have more than two options, so per-kind numbers are the ones to compare."""
    d = os.path.join(root, slug)
    first = {it["key"]: it["answer"] for it in _answered_items(d)}
    rows = [(r["kind"], float(r["answer"] == first[r["key"]])) for r in _read(os.path.join(d, RECHECK))
            if r["key"] in first]

    def summary(xs):
        return {"n": len(xs), "agreement": mean(xs) if xs else None,
                "ci90": list(bootstrap_ci(xs)) if len(xs) > 1 else None}
    return {"all": summary([x for _, x in rows]),
            **{k: summary([x for kind, x in rows if kind == k]) for k in ("seed", "label")}}


# ---- split -----------------------------------------------------------------

def split(root: str, slug: str, label_cutoff: Optional[str] = None, test_frac: float = 0.2,
          val_frac: float = 0.2) -> Dict[str, List[Choice]]:
    """{"history", "val", "test"}. Test: seed pairs whose hash falls in test_frac, and
    every label from a run dated on or after label_cutoff. The rest goes to val with
    probability val_frac, else history. All pairwise rows from one label stay together."""
    d = os.path.join(root, slug)
    out: Dict[str, List[Choice]] = {"history": [], "val": [], "test": []}
    labels = _read(os.path.join(d, LABELS))
    late = {r["key"] for r in labels if label_cutoff and r["run_date"] >= label_cutoff}
    seeds = [Choice(**c) for c in _read(os.path.join(d, SEED_CHOICES))]
    for c in seeds + labels_to_choices(slug, labels):
        if c.group_id in late or c.source == "seed" and _bucket("test:" + c.example_id) < test_frac:
            out["test"].append(c)
        elif _bucket("val:" + (c.group_id if c.source == "label" else c.example_id)) < val_frac:
            out["val"].append(c)
        else:
            out["history"].append(c)
    return out


def status(root: str, slug: str, label_cutoff: Optional[str] = None) -> dict:
    d = os.path.join(root, slug)
    labels = _read(os.path.join(d, LABELS))
    parts = split(root, slug, label_cutoff)
    return {"researcher": slug, "seed_pairs": len(_read(os.path.join(d, SEED_PAIRS))),
            "seed_choices": len(_read(os.path.join(d, SEED_CHOICES))),
            "labels": len(labels), "labels_per_point": {p: sum(r["point"] == p for r in labels)
                                                        for p in sorted({r["point"] for r in labels})},
            "split": {k: len(v) for k, v in parts.items()}, "label_cutoff": label_cutoff,
            "noise_ceiling": noise_ceiling(root, slug),
            "consent_file": os.path.exists(os.path.join(d, "CONSENT.md"))}


# ---- E2 --------------------------------------------------------------------

def run_e2(root: str, slug: str, factories: Dict[str, Callable], out_path: str,
           label_cutoff: Optional[str] = None, seed: int = 0, run_config: Optional[dict] = None) -> dict:
    """Fit each method on history/val and score it on the held-out test choices,
    next to the person's noise ceiling (PLAN E2, Track P)."""
    if os.path.exists(out_path):
        raise FileExistsError(f"{out_path} exists; E2 results are not overwritten")
    parts = split(root, slug, label_cutoff)
    if not parts["test"] or not parts["history"]:
        raise ValueError(f"need history and test choices, have {({k: len(v) for k, v in parts.items()})}")
    methods = {}
    for name, factory in factories.items():
        model = factory()
        correct, briers, errors = [], [], []
        try:   # as in fidelity.run_fidelity: a failed model call counts as wrong, the run goes on
            model.fit(parts["history"], parts["val"])
        except Exception as exc:
            errors.append(f"fit: {type(exc).__name__}: {exc}")
        for c in parts["test"]:
            try:
                if errors and errors[0].startswith("fit:"):
                    raise RuntimeError("fit failed")
                pred = model.predict(c.context, [c.a_text, c.b_text])
                correct.append(float(pred.choice == c.chosen))
                briers.append((pred.probabilities[0] - (c.chosen == "a")) ** 2)
            except Exception as exc:
                correct.append(0.0)
                errors.append(f"{c.identity}: {type(exc).__name__}: {exc}")
        methods[name] = {"accuracy": mean(correct), "ci90": list(bootstrap_ci(correct, seed=seed)),
                         "brier_valid_only": mean(briers) if briers else None, "n": len(correct),
                         "failures": len(errors), "errors": errors[:20], "cost": dict(model.cost)}
    report = {"track": "P", "researcher": slug, "label_cutoff": label_cutoff, "seed": seed,
              "config": run_config or {}, "sizes": {k: len(v) for k, v in parts.items()},
              "methods": methods, "noise_ceiling": noise_ceiling(root, slug),
              "note": "CI is a bootstrap over held-out pairs from one person; pairs from one label are correlated."}
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    return report


def fit_user_model(root: str, slug: str, factory: Callable, label_cutoff: Optional[str] = None) -> str:
    """Fit the selected method on history/val (never the held-out choices, so E2
    describes the model the loop uses); write usermodel.json and history.jsonl."""
    d = os.path.join(root, slug)
    parts = split(root, slug, label_cutoff)
    model = factory()
    model.fit(parts["history"], parts["val"])
    model.save(os.path.join(d, USERMODEL))
    with open(os.path.join(d, HISTORY), "w") as f:
        for c in parts["history"] + parts["val"]:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    return os.path.join(d, USERMODEL)


# ---- CLI -------------------------------------------------------------------

def _items(args) -> list:
    from ..research.measure import SCENARIOS
    if not args.benchmark_items:
        return [SCENARIOS[n] for n in (args.scenarios or sorted(SCENARIOS))]
    from ..research.benchmarks import load_items
    from ..research.benchmarks import split as dev_heldout
    dev, _ = dev_heldout(load_items(args.benchmark_items, base=SCENARIOS[args.scenario]))
    return dev[: args.max_items] if args.max_items else dev   # held-out items stay unseen


def _llm_ideas(args, items) -> Dict[str, List[Intervention]]:
    from ..llm import Budget, get_llm
    from ..research.ideas import Proposer
    llm = get_llm(args.llm, args.model, Budget(max_calls=args.max_calls))
    prop = Proposer(llm, None, random.Random(args.seed))
    return {sc.name: prop.propose(sc.goal, sc.probe, [], set(), [], [], k=args.llm_ideas, setting=sc.setting)
            for sc in items}


def main(argv=None):
    p = argparse.ArgumentParser(description="Track P: a team member's research choices (PLAN 6.3, 12.2)")
    p.add_argument("--root", default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest="command", required=True)

    def cmd(name, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--researcher", required=True, help="the person's slug under data/researchers/")
        return sp
    i = cmd("init", "create the directory and CONSENT.md, and set track P in tracks.json")
    i.add_argument("--name", required=True)
    s = cmd("seed-pairs", "generate D1-style pairs to answer (no answers are asked here)")
    s.add_argument("--n", type=int, default=50)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--scenarios", nargs="*", help="built-in scenarios (default: all)")
    s.add_argument("--benchmark-items", help="items JSONL; only its dev split is used")
    s.add_argument("--scenario", default="metric_inflation", help="base scenario for --benchmark-items")
    s.add_argument("--max-items", type=int, default=10)
    s.add_argument("--llm-ideas", type=int, default=0, help="also ask an LLM for K ideas per item (paid unless offline)")
    s.add_argument("--llm", default="offline")
    s.add_argument("--model", default="claude-sonnet-5-5")
    s.add_argument("--max-calls", type=int, default=50)
    a = cmd("answer", "answer pending seed pairs (resumable)")
    a.add_argument("--limit", type=int)
    lb = cmd("label", "label logged loop decisions D1-D6 (resumable)")
    lb.add_argument("decisions", nargs="+", help="decisions.jsonl files")
    lb.add_argument("--limit", type=int)
    r = cmd("recheck", "re-ask ~20%% of answered items for the noise ceiling")
    r.add_argument("--frac", type=float, default=0.2)
    r.add_argument("--min-days", type=float, default=3)
    st = cmd("status", "counts, split sizes and noise ceiling")
    st.add_argument("--label-cutoff", help="labels from runs on or after this date are held out")
    e = cmd("e2", "fit methods on history/val and score them on the held-out choices")
    e.add_argument("--methods", nargs="+", default=["m0", "m1"])
    e.add_argument("--label-cutoff")
    e.add_argument("--backend", default="offline")
    e.add_argument("--model", default="claude-haiku-5-5")
    e.add_argument("--max-calls", type=int, default=500)
    e.add_argument("--seed", type=int, default=0)
    e.add_argument("--cache", default="runs/taste-cache")
    e.add_argument("--out", help="default results/e2/P_<slug>.json")
    e.add_argument("--dry-run", action="store_true")
    ft = cmd("fit", "fit the selected method; write usermodel.json and history.jsonl for the loop")
    ft.add_argument("--method", required=True)
    ft.add_argument("--config", default="{}", help="JSON method config (WS A's selected settings)")
    ft.add_argument("--label-cutoff")
    ft.add_argument("--backend", required=True, help="must match the backend the loop predicts with")
    ft.add_argument("--model", required=True)
    ft.add_argument("--max-calls", type=int, default=500)
    ft.add_argument("--seed", type=int, default=0)
    ft.add_argument("--cache", default="runs/taste-cache")
    args = p.parse_args(argv)
    slug = args.researcher

    if args.command == "init":
        print("wrote", init(args.root, slug, args.name))
    elif args.command == "seed-pairs":
        items = _items(args)
        extra = _llm_ideas(args, items) if args.llm_ideas else None
        path = write_seed_pairs(args.root, slug, make_seed_pairs(items, args.n, args.seed, extra))
        print(f"{len(_read(path))} pairs in {path}")
    elif args.command == "answer":
        print(f"recorded {answer_seed_pairs(args.root, slug, limit=args.limit)} choices")
    elif args.command == "label":
        print(f"recorded {label_decisions(args.root, slug, args.decisions, limit=args.limit)} labels")
    elif args.command == "recheck":
        print(f"recorded {recheck(args.root, slug, frac=args.frac, min_days=args.min_days)} re-answers")
    elif args.command == "status":
        print(json.dumps(status(args.root, slug, args.label_cutoff), indent=2))
    elif args.command == "fit":
        from ..llm import Budget, get_llm
        from .methods import create_method
        llm = get_llm(args.backend, args.model, Budget(max_calls=args.max_calls))
        path = fit_user_model(args.root, slug, lambda: create_method(
            args.method, llm, seed=args.seed, cache_dir=args.cache, max_calls=args.max_calls,
            **json.loads(args.config)), args.label_cutoff)
        print("wrote", path, "\nkeep a copy in shared memory: "
              f"python3 -m autoresearch.taste.usermodel_store push --researcher {slug}")
    else:
        parts = split(args.root, slug, args.label_cutoff)
        if args.dry_run:
            print(json.dumps({"methods": args.methods, **{k: len(v) for k, v in parts.items()},
                              "n_predictions": len(args.methods) * len(parts["test"]),
                              "note": "excludes fitting calls; no model calls made"}))
            return
        from ..llm import Budget, get_llm
        from .methods import create_method
        llm = get_llm(args.backend, args.model, Budget(max_calls=args.max_calls))
        factories = {m: (lambda m=m: create_method(m, llm, seed=args.seed, cache_dir=args.cache,
                                                    max_calls=args.max_calls)) for m in args.methods}
        out = args.out or os.path.join("results", "e2", f"P_{slug}.json")
        rep = run_e2(args.root, slug, factories, out, args.label_cutoff, args.seed,
                     {"backend": args.backend, "model": args.model, "methods": args.methods})
        print(json.dumps({m: {k: v for k, v in r.items() if k != "cost"} for m, r in rep["methods"].items()},
                         indent=2))
        print("wrote", out)


if __name__ == "__main__":
    main()
