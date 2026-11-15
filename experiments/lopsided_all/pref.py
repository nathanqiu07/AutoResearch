"""Does fitting on balanced pairs predict Marius's preferences better? (Ethan, 2026-11-15)

Each method is fit twice on the earliest 80% of pre-T documents: once on all their pairs, once on
only the pairs the weaker gate keeps (not `lopsided_his`). Both fits, and m0, are scored on
(a) the latest 20% of pre-T documents (dev) and (b) the 83 post-T held-out pairs, each also
restricted to the pairs the weaker and the strict gate keep. A pair counts as right only when
the model picks his option in both a/b orders (track_eval.paired_correct).

Ethan chose to score the held-out pairs here as well, so they are no longer unseen for E2_S.

shortcut: m1 sees a fixed 20-pair sample and m3 proposes from 20 pairs, to keep the run inside
the Claude CLI limit; the full-size fits need ~10x the calls.

Usage: python3 -m experiments.lopsided_all.pref --max-usd 3 [--methods m2,m5]"""
import argparse
import concurrent.futures
import json
import os

from autoresearch.llm import Budget, get_llm
from autoresearch.taste import timesplit, track_eval
from autoresearch.taste.methods import create_method

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..", "data", "researchers", "marius_hobbhahn")
CACHE = os.path.join("runs", "lopsided_all", "cache")
MODEL = "claude-haiku-5-5"
METHODS = {"m1": {"k": 20}, "m3": {"max_history": 20}, "m4": {"max_history": 50},
           "m2": {"max_history": 10}, "m5": {"max_history": 10}, "m6": {"max_history": 10},
           "m7": {"max_history": 10}}


class JsonReply:
    """Haiku sometimes wraps its JSON in a code fence or a sentence, which UserModel._json rejects;
    pass on the reply's last JSON object instead (track_eval does the same for its own arms)."""

    def __init__(self, inner):
        self.inner, self.budget, self.label, self.name = inner, inner.budget, inner.label, inner.name
        self.model = inner.model

    def complete(self, *args, **kwargs):
        text = self.inner.complete(*args, **kwargs)
        obj = track_eval._last_object(text)
        return text if obj is None else json.dumps(obj)


def fit(method: str, llm, history):
    model = create_method(method, llm, seed=0, cache_dir=CACHE, **METHODS[method])
    train, val = track_eval.split_by_document(history)
    model.fit(*((history, []) if method == "m1" else (train, val)))
    return model


def summarize(scored: dict, keep, methods) -> dict:
    """Accuracy and 90% CI of each arm on the pairs `keep` admits, groups resampled."""
    lists = {arm: {g: [ok for k, ok in v.items() if keep(k)] for g, v in s.items()} for arm, s in scored.items()}
    lists = {arm: {g: v for g, v in groups.items() if v} for arm, groups in lists.items()}
    out = {"n": sum(len(v) for v in lists["m0"].values())}
    for arm, groups in lists.items():
        acc, lo, hi = track_eval.cluster_ci(groups)
        out[arm] = {"accuracy": round(acc, 3), "ci90": [round(lo, 3), round(hi, 3)]}
    for m in methods:
        for base in ("m0", f"{m}_all"):
            other = f"{m}_gated"
            d, lo, hi = track_eval.cluster_diff_ci(lists[other], lists[base])
            out[f"{other}-{base}"] = {"diff": round(d, 3), "ci90": [round(lo, 3), round(hi, 3)]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-usd", type=float, required=True)
    ap.add_argument("--methods", default="m1,m3,m4", help="comma-separated keys of METHODS")
    args = ap.parse_args(argv)
    methods = args.methods.split(",")

    with open(os.path.join(ROOT, "agreement.jsonl")) as f:
        gate = {r["pair_id"]: r for r in map(json.loads, f)}
    history = track_eval.load_choices(os.path.join(ROOT, timesplit.HISTORY))
    heldout = track_eval.load_choices(os.path.join(ROOT, timesplit.HELDOUT))
    train, dev = track_eval.split_by_document(history)
    gated = [c for c in train if not gate[c.example_id]["lopsided_his"]]

    budget = Budget(max_calls=20_000, max_seconds=4 * 3600, max_cost_usd=args.max_usd)
    llm = JsonReply(get_llm("claude-cli", MODEL, budget))
    jobs = {f"{m}_{name}": (m, rows) for m in methods for name, rows in (("all", train), ("gated", gated))}
    with concurrent.futures.ThreadPoolExecutor(len(jobs)) as pool:
        futures = {arm: pool.submit(fit, m, llm, rows) for arm, (m, rows) in jobs.items()}
        models = {"m0": track_eval.NamedNoHistory(llm, None, cache_dir=CACHE),
                  **{arm: f.result() for arm, f in futures.items()}}

    report = {"model": llm.label, "n_train_all": len(train), "n_train_gated": len(gated), "methods": {m: METHODS[m] for m in methods}}
    for name, rows in (("dev", dev), ("heldout", heldout)):
        scored = {arm: track_eval.score(model, rows) for arm, model in models.items()}
        report[name] = {"all": summarize(scored, lambda k: True, methods),
                        "weak_gate": summarize(scored, lambda k: not gate[k]["lopsided_his"], methods),
                        "strict_gate": summarize(scored, lambda k: not gate[k]["lopsided"], methods)}
    report["cost_usd"] = round(budget.cost_usd, 4)
    report["calls"] = budget.calls
    with open(os.path.join(HERE, "pref_results.json" if methods == ["m1", "m3", "m4"]
                           else f"pref_results_{'_'.join(methods)}.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: report[k] for k in ("cost_usd", "calls")}))


if __name__ == "__main__":
    main()
