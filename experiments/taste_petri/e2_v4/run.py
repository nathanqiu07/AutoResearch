"""E2 on pairs_v4 (e2_v2/PROTOCOL.md, last amendment): does a pre-T profile move sonnet toward Owain's
actual, less-default choice on blind-context pairs?

usage: python3 run.py select            # writes pairs.jsonl (the sample) and pair_ids.json
       python3 run.py run [--cap N]     # all arms on sonnet, writes results.json and results.md

Reuses e2_v2/run.py unchanged (CLI wrapper, Profiled predictor, paired_correct, cluster CIs) with its
output directory pointed here and every arm on sonnet. Adds arm ANTI (ANTI.md): a generic,
length-matched "departs from the typical or most cautious choice" placebo with no content from his work.
"""
import argparse
import collections
import importlib.util
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
TP = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location("e2v2_run", os.path.join(TP, "e2_v2", "run.py"))
V2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V2)
V2.HERE = HERE  # calls.log and cache/ live here, not in e2_v2

ARMS = ["M0s", "NAME", "P0", "P1", "P4", "MIS", "ANTI"]
P_ARMS = ["NAME", "P1", "P4"]
CONTROLS = ["M0s", "P0", "MIS", "ANTI"]
V2.SONNET_ARMS = set(ARMS)
with open(os.path.join(HERE, "ANTI.md")) as f:
    _anti = f.read().strip()
V2.FIXED["ANTI"] = lambda: _anti

SEED, N_PAIRS = 0, 96  # 96 x 7 arms x 2 orders = 1,344 calls, leaving room for JsonReply retries under 1,400


def select():
    """Spread N_PAIRS as evenly as possible over the 10 works (a work with fewer pairs gives all it has),
    then sample within each work with a fixed seed."""
    pairs = V2.read_jsonl(os.path.join(TP, "pairs_v4", "pairs.jsonl"))
    by_work = collections.defaultdict(list)
    for r in pairs:
        by_work[r["work"]].append(r)
    quota, left = {}, N_PAIRS
    for i, w in enumerate(sorted(by_work, key=lambda w: len(by_work[w]))):
        quota[w] = min(len(by_work[w]), left // (len(by_work) - i))
        left -= quota[w]
    rng = random.Random(SEED)
    chosen = [r for w in sorted(by_work) for r in rng.sample(sorted(by_work[w], key=lambda r: r["pair_id"]), quota[w])]
    with open(os.path.join(HERE, "pairs.jsonl"), "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in chosen)
    with open(os.path.join(HERE, "pair_ids.json"), "w") as f:
        json.dump({"seed": SEED, "n": len(chosen), "quota": quota, "pair_ids": [r["pair_id"] for r in chosen]}, f, indent=1)
    print(json.dumps(quota, indent=1), len(chosen))


def verdicts(s):
    out = []
    if s["n_pairs"] < 30 or s["n_works"] < 8:
        out.append(f"DESCRIPTIVE ONLY: {s['n_pairs']} pairs / {s['n_works']} works (< 30 or < 8).")
    acc = {a: s["accuracy"][a]["value"] for a in ARMS}
    for a in P_ARMS:
        d = s["acc_diff"][a]
        passed = [c for c in CONTROLS if acc[a] > acc[c] and d[c]["ci90"][0] > 0]
        detail = "; ".join(f"vs {c} {d[c]['diff']:+.3f} {d[c]['ci90']}" for c in CONTROLS)
        if len(passed) == len(CONTROLS):
            out.append(f"{a}: PREDICTS TASTE (acc {acc[a]:.3f}; {detail}).")
        else:
            out.append(f"{a}: does not predict taste (acc {acc[a]:.3f}; {detail}; "
                       f"clears {', '.join(passed) or 'none'} of {', '.join(CONTROLS)}).")
    return out


def run(cap, workers):
    V2.CAP[0] = cap
    pairs = V2.read_jsonl(os.path.join(HERE, "pairs.jsonl"))
    words_by_arm = {a: V2.words(V2.profile_text(a, pairs[0]["context"])) for a in ARMS}
    before = V2.real_calls()
    preds = V2.predict_all(pairs, ARMS, workers)
    res = V2.score(pairs, preds, ARMS)
    by_id = {r["pair_id"]: r for r in pairs}
    failed = {r["pair_id"] for r in preds if r["correct"] is None}  # V2.score drops these from every arm
    g = {a: collections.defaultdict(list) for a in ARMS}
    gp = {a: collections.defaultdict(list) for a in ARMS}
    for r in preds:
        if r["pair_id"] not in failed:
            g[r["arm"]][by_id[r["pair_id"]]["work"]].append(bool(r["correct"]))
            gp[r["arm"]][by_id[r["pair_id"]]["work"]].append(sum(r["p_his"]) / 2)
    s = res["subsets"]["all"]
    s["acc_diff"] = {a: {c: V2._diff(g[a], g[c]) for c in CONTROLS} for a in P_ARMS}
    s["p_his_diff"] = {a: {c: V2._diff(gp[a], gp[c]) for c in CONTROLS} for a in P_ARMS}
    res["verdicts"] = verdicts(res["subsets"]["all"])
    res.update({"pairs_file": "pairs.jsonl", "arms": ARMS, "profile_words": words_by_arm,
                "calls_this_run": V2.real_calls() - before, "calls_log_total": V2.real_calls(), "predictions": preds})
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    md = report_md(res, words_by_arm)
    with open(os.path.join(HERE, "results.md"), "w") as f:
        f.write(md)
    print(md)


def report_md(res, words_by_arm):
    lines = ["# E2 on pairs_v4 (sonnet)", "",
             (f"Pairs: `pairs.jsonl` ({len(res['per_pair'])} of pairs_v4's 246, seed {SEED}, ids in `pair_ids.json`). "
             f"Arms: {', '.join(ARMS)}, all sonnet. Real CLI calls this run: {res['calls_this_run']} "
             f"(calls.log total {res['calls_log_total']}). Errors: {len(res['errors'])}."), "",
             ("Paired accuracy = his option chosen in both orders. 90% CIs resample works. "
              "p(his) is averaged over both orders."), ""]
    for name, s in res["subsets"].items():
        lines += [f"## {name} (n = {s['n_pairs']}, works = {s['n_works']})", "",
                  "| arm | words | paired acc [90% CI] | mean p(his) [90% CI] |", "|---|---|---|---|"]
        for a in ARMS:
            acc, ph = s["accuracy"][a], s["mean_p_his"][a]
            lines.append(f"| {a} | {words_by_arm[a]} | {acc['value']:.3f} {acc['ci90']} | {ph['value']:.3f} {ph['ci90']} |")
        lines.append("")
        if "acc_diff" in s:
            lines += ["### Cluster-diff 90% CIs (row arm minus column control)", "",
                      "| arm | " + " | ".join(f"Δacc vs {c}" for c in CONTROLS) + " |",
                      "|---|" + "---|" * len(CONTROLS)]
            for a in P_ARMS:
                lines.append(f"| {a} | " + " | ".join(
                    f"{s['acc_diff'][a][c]['diff']:+.3f} {s['acc_diff'][a][c]['ci90']}" for c in CONTROLS) + " |")
            lines += ["", "| arm | " + " | ".join(f"Δp(his) vs {c}" for c in CONTROLS) + " |",
                      "|---|" + "---|" * len(CONTROLS)]
            for a in P_ARMS:
                lines.append(f"| {a} | " + " | ".join(
                    f"{s['p_his_diff'][a][c]['diff']:+.3f} {s['p_his_diff'][a][c]['ci90']}" for c in CONTROLS) + " |")
            lines.append("")
    lines += ["## Decision rule (PROTOCOL.md, pairs_v4 amendment), all pairs", ""]
    lines += [f"- {v}" for v in res["verdicts"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["select", "run"])
    ap.add_argument("--cap", type=int, default=1400)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.stage == "select":
        select()
    else:
        run(args.cap, args.workers)


if __name__ == "__main__":
    main()
