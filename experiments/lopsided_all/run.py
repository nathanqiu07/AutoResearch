"""Lopsidedness test on every researcher pair, pre-T (history) and post-T (held-out).

Same judge and rule as the personal-track item gate (autoresearch/taste/agreement.py): a blind
claude-haiku-5-5 judge, three votes per a/b order, and a pair is lopsided when more than 80% of
valid votes go to either option. Pole 1 is the option the researcher actually took.

shortcut: sampling stops once the six-vote verdict can no longer change (votes alternate
orders), so a recorded row can hold fewer than six votes; the verdict is the one six would give.

Usage: python3 -m experiments.lopsided_all.run --researcher marius_hobbhahn --max-calls 2800 --max-usd 2
Resumable: pairs already in <researcher>/agreement.jsonl are skipped."""
import argparse
import concurrent.futures
import datetime
import itertools
import json
import os
import threading

from autoresearch.llm import Budget, get_llm
from autoresearch.taste import agreement
from autoresearch.taste.trackp import CallCappedLLM

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "researchers")
ATTEMPTS = 2 * 3
_LOCK = threading.Lock()


def verdict(a: int, b: int) -> bool:
    """Lopsided under agreement.lopsided, for a pole-1 and b pole-2 valid votes."""
    return a + b > 0 and max(a, b) / (a + b) > agreement.THRESHOLD


def labels(a: int, b: int) -> dict:
    """`lopsided`: the strict two-sided rule. `lopsided_his`: the weaker one-sided rule (Ethan,
    2026-11-15), flagging only pairs where the judge confidently picks the researcher's option;
    a pair the judge confidently gets wrong still needs his taste to answer."""
    return {"lopsided": verdict(a, b), "lopsided_his": verdict(a, b) and a > b}


def settled(a: int, b: int, left: int) -> bool:
    """True when every way the remaining attempts could go (pole 1, pole 2, invalid) gives the
    same verdict."""
    outcomes = {verdict(a + rest.count(1), b + rest.count(2))
                for rest in itertools.product((1, 2, None), repeat=left)}
    return len(outcomes) == 1


def judge_pair(llm, pair: dict) -> dict:
    taken = pair[pair["chosen"] + "_text"]
    other = pair[("b" if pair["chosen"] == "a" else "a") + "_text"]
    orders, a, b = [[], []], 0, 0
    for i in range(ATTEMPTS):
        if settled(a, b, ATTEMPTS - i):
            break
        first, second = (taken, other) if i % 2 == 0 else (other, taken)
        v = agreement._vote(llm, pair["context"], first, second)
        picked_taken = None if v is None else v == (1 if i % 2 == 0 else 2)
        orders[i % 2].append(picked_taken)
        a += picked_taken is True
        b += picked_taken is False
    return {"pair_id": pair["pair_id"], "split": pair["split"], "pole_1": taken, "pole_2": other,
            "votes": orders, **labels(a, b), "judge": llm.label,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher", required=True)
    ap.add_argument("--max-calls", type=int, required=True)
    ap.add_argument("--max-usd", type=float, required=True)
    ap.add_argument("--limit", type=int, help="judge only the first N unjudged pairs")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)

    d = os.path.join(ROOT, args.researcher)
    out = os.path.join(d, "agreement.jsonl")
    with open(os.path.join(d, "pairs_timesplit.jsonl")) as f:
        pairs = [json.loads(line) for line in f if line.strip()]
    done = set()
    if os.path.exists(out):
        with open(out) as f:
            done = {json.loads(line)["pair_id"] for line in f if line.strip()}
    todo = [p for p in pairs if p["pair_id"] not in done][:args.limit]

    budget = Budget(max_calls=args.max_calls, max_seconds=4 * 3600, max_cost_usd=args.max_usd)
    llm = CallCappedLLM(get_llm("claude-cli", agreement.JUDGE_MODEL, budget), args.max_calls)

    def one(p):
        row = judge_pair(llm, p)
        with _LOCK, open(out, "a") as f:
            f.write(json.dumps(row) + "\n")

    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(one, p) for p in todo]):
            fut.result()
    print(json.dumps({"judged": len(todo), "calls": llm.attempts, "cost_usd": round(budget.cost_usd, 4)}))


if __name__ == "__main__":
    main()
