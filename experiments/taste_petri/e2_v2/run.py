"""E2 v2 (PROTOCOL.md): does a pre-T Owain Evans profile predict his post-T choice on taste-band pairs?

usage: python3 run.py --pairs PATH --arms M0,M0s,NAME,P4 --out NAME [--cap N] [--workers N]

Predictor is e2_owain's: UserModel._predict_with with the profile in the persona slot, wrapped in
track_eval.JsonReply, both option orders, scored by track_eval.paired_correct and cluster_ci /
cluster_diff_ci over works. Every real `claude -p` call goes through CLI.complete: logged to calls.log,
cached in cache/raw by (model, arm, system, prompt), refused once calls.log holds --cap started calls.
Writes only inside this directory: calls.log, cache/, <out>.json, <out>.md.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(TP, "..", ".."))
sys.path.insert(0, ROOT)

from autoresearch.llm import LLM, Budget
from autoresearch.taste import track_eval
from autoresearch.taste.timesplit import ANON_USER
from autoresearch.taste.usermodel import Choice, UserModel

ARMS = ("M0", "M0s", "NAME", "E_pre", "P0", "P1", "P2", "P3", "P4", "P1+P3", "MIS", "MIS2")
SONNET_ARMS = {"M0s"}
LOCK = threading.Lock()
CAP = [350]  # set from --cap


def p(*parts):
    out = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def words(text):
    return len(text.split())


# ---------------------------------------------------------------- the one CLI wrapper

def real_calls():
    if not os.path.exists(p("calls.log")):
        return 0
    with open(p("calls.log")) as f:
        return sum(1 for line in f if '"status": "started"' in line)


class CLI(LLM):
    """claude -p --model MODEL, isolated as in e2_owain. The arm is part of the cache key, so no arm
    (and no gate) ever reads another's reply."""
    name = "claude-cli"

    def __init__(self, arm, model, budget):
        super().__init__(budget)
        self.arm, self.model = arm, model

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        key = hashlib.sha256(json.dumps([self.model, self.arm, system, prompt]).encode()).hexdigest()[:32]
        cpath = p("cache", "raw", key + ".json")
        if os.path.exists(cpath):
            with open(cpath) as f:
                return json.load(f)["result"]
        with LOCK:
            n = real_calls()
            if n >= CAP[0]:
                raise RuntimeError(f"call cap {CAP[0]} reached; refusing call {n + 1}")
            with open(p("calls.log"), "a") as f:  # the slot is reserved before the call
                f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n + 1, "arm": self.arm,
                                    "model": self.model, "key": key, "chars": len(prompt),
                                    "status": "started"}) + "\n")
        cmd = ["claude", "-p", "--model", self.model, "--output-format", "json", "--tools", "",
               "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--system-prompt", system]
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix="e2v2_cli_") as cwd:
            proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=600, cwd=cwd)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
        ok = proc.returncode == 0 and not data.get("is_error")
        with LOCK, open(p("calls.log"), "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "arm": self.arm, "model": self.model,
                                "key": key, "status": "ok" if ok else "error", "secs": round(time.time() - t0, 1),
                                "cost_usd": data.get("total_cost_usd"), "out": str(data.get("result"))[:120]}) + "\n")
        if not ok:
            raise RuntimeError(f"claude CLI error: {str(data.get('result'))[:300]}")
        u = data.get("usage", {})
        self.budget.charge(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                           + u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0),
                           float(data.get("total_cost_usd") or 0.0))
        with open(cpath, "w") as f:
            json.dump({"arm": self.arm, "model": self.model, "system": system, "prompt": prompt,
                       "result": data["result"]}, f, ensure_ascii=False)
        return data["result"]


BUDGET = Budget(max_calls=10 ** 6, max_cost_usd=1e9, max_seconds=12 * 3600)  # CAP is the real limit


# ---------------------------------------------------------------- profiles

def _load_arms_module():
    spec = importlib.util.spec_from_file_location("pc_arms", os.path.join(TP, "profiles_contrastive", "arms.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PC = _load_arms_module()


def _read(*parts):
    with open(os.path.join(TP, *parts)) as f:
        return f.read().strip()


def p0_trimmed():
    """P0 cut to P1's word count (Amendment): whole lines while they fit, then the next line cut at a word."""
    budget, out = words(PC.get_profile_text("P1")), []
    for line in PC.get_profile_text("P0").splitlines():
        left = budget - sum(words(x) for x in out)
        if left <= 0:
            break
        out.append(line if words(line) <= left else " ".join(line.split()[:left]))
    return "\n".join(out).strip()


def mis_shuffled(seed=0):
    """P4 with each 'he does Y' moved to another 'generic sense says X' (a derangement, fixed seed)."""
    paras = [x for x in PC.get_profile_text("P4").split("\n\n") if x.strip()]
    heads, tails = zip(*(x.split(", he ", 1) for x in paras))
    rng, order = random.Random(seed), list(range(len(paras)))
    while any(i == j for i, j in enumerate(order)):
        rng.shuffle(order)
    return "\n\n".join(f"{heads[i]}, he {tails[j]}" for i, j in enumerate(order))


def mis2_steinhardt():
    text = _read("profiles", "jacob_steinhardt", "e_taste_vector.md")
    return "\n".join(x for x in text.splitlines() if not x.startswith(("<!--", "#"))).strip()


FIXED = {"M0": lambda: "", "M0s": lambda: "", "NAME": lambda: "The researcher is Owain Evans.",
         "E_pre": lambda: _read("e2_owain", "profiles", "E_pre.md"), "P0": p0_trimmed,
         "MIS": mis_shuffled, "MIS2": mis2_steinhardt}


def profile_text(arm, context):
    if arm in FIXED:
        return FIXED[arm]()
    return PC.get_profile_text(arm, context)


class Profiled(UserModel):
    """e2_owain's Persona arm, with the profile chosen per context (P3 retrieves on it)."""
    method_id = "e2v2"

    def __init__(self, llm_, arm, **kw):
        super().__init__(llm_, **kw)
        self.arm = arm

    def predict(self, context, options):
        return self._predict_with(context, options, persona=profile_text(self.arm, context))


def model_for(arm):
    return Profiled(track_eval.JsonReply(CLI(arm, "sonnet" if arm in SONNET_ARMS else "haiku", BUDGET)), arm)


# ---------------------------------------------------------------- run

def choice(r):
    return Choice(user_id=ANON_USER, context=f"{r['context']}\n\nQuestion: {r['question']}", a_text=r["a_text"],
                  b_text=r["b_text"], chosen=r["his_side"], decision_point=r["decision_point"],
                  example_id=r["pair_id"], group_id=r["work"])


def predict_all(pairs, arms, workers):
    models = {a: model_for(a) for a in arms}

    def one(job):
        arm, r = job
        c, model = choice(r), models[arm]
        try:
            ok = track_eval.paired_correct(model, c)
            # both predictions are now cached, so these cost no call
            p1 = model.predict(c.context, [c.a_text, c.b_text]).probabilities
            p2 = model.predict(c.context, [c.b_text, c.a_text]).probabilities
            his1, his2 = p1[0 if c.chosen == "a" else 1], p2[1 if c.chosen == "a" else 0]
            return {"arm": arm, "pair_id": c.example_id, "correct": ok, "p_his": [his1, his2]}
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as e:  # excluded from that arm's score
            return {"arm": arm, "pair_id": c.example_id, "correct": None, "error": repr(e)[:300]}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, [(a, r) for a in arms for r in pairs]))


# ---------------------------------------------------------------- score

def _acc(by_group):
    acc, lo, hi = track_eval.cluster_ci(by_group)
    return {"value": round(acc, 3), "ci90": [round(lo, 3), round(hi, 3)],
            "n_pairs": sum(len(v) for v in by_group.values()), "n_works": len(by_group)}


def _diff(a, b):
    d, lo, hi = track_eval.cluster_diff_ci(a, b)
    return {"diff": round(d, 3), "ci90": [round(lo, 3), round(hi, 3)]}


def score(pairs, preds, arms):
    by_id = {r["pair_id"]: r for r in pairs}
    failed = {r["pair_id"] for r in preds if r["correct"] is None}
    ok = [k for k in by_id if k not in failed]  # every arm is scored on the same pairs
    subsets = {"all": set(ok), "fair_strict": {k for k in ok if by_id[k].get("fair_strict")},
               "realness_ambiguous (<=0.5)": {k for k in ok if by_id[k].get("realness_share", 1) <= 0.5},
               "realness_tell (>0.5)": {k for k in ok if by_id[k].get("realness_share", 1) > 0.5}}
    for fam in sorted({r["generator_family"] for r in pairs}):
        subsets[f"generator={fam}"] = {k for k in ok if by_id[k]["generator_family"] == fam}

    def grouped(arm, ids, value):
        out = collections.defaultdict(list)
        for r in preds:
            if r["arm"] == arm and r["pair_id"] in ids:
                out[by_id[r["pair_id"]]["work"]].append(value(r))
        return dict(out)

    correct, p_his = (lambda r: bool(r["correct"])), (lambda r: sum(r["p_his"]) / 2)
    res = {"subsets": {}, "errors": [r for r in preds if r["correct"] is None]}
    for name, ids in subsets.items():
        if not ids:
            continue
        s = {"n_pairs": len(ids), "n_works": len({by_id[k]["work"] for k in ids}),
             "accuracy": {a: _acc(grouped(a, ids, correct)) for a in arms},
             "mean_p_his": {a: _acc(grouped(a, ids, p_his)) for a in arms}}
        if "M0" in arms:
            s["acc_minus_M0"] = {a: _diff(grouped(a, ids, correct), grouped("M0", ids, correct))
                                 for a in arms if a != "M0"}
            s["p_his_minus_M0"] = {a: _diff(grouped(a, ids, p_his), grouped("M0", ids, p_his))
                                   for a in arms if a != "M0"}
        res["subsets"][name] = s
    res["per_pair"] = {k: {"work": by_id[k]["work"], "generator": by_id[k]["generator"],
                           "blind_share": by_id[k].get("blind_share"), "realness_share": by_id[k].get("realness_share"),
                           **{a: next(({"correct": r["correct"], "p_his": r.get("p_his")} for r in preds
                                       if r["arm"] == a and r["pair_id"] == k), None) for a in arms}}
                       for k in by_id}
    return res


def verdicts(res, arms):
    """PROTOCOL.md decision rules, applied to the 'all' subset of the pairs file given."""
    s = res["subsets"]["all"]
    acc = {a: s["accuracy"][a]["value"] for a in arms}
    out = []
    if s["n_pairs"] < 30 or s["n_works"] < 8:
        out.append(f"DESCRIPTIVE ONLY: {s['n_pairs']} pairs / {s['n_works']} works (< 30 or < 8); no claim is made.")
    if "M0" in acc:
        m0 = acc["M0"]
        if m0 > 0.65:
            out.append(f"SELECTION ARTEFACT: M0 = {m0:.3f} > 0.65 on fresh samples, so the band does not hold up "
                       "beyond the gate's votes. Fall back to the sonnet-gated subset.")
        else:
            out.append(f"BAND HOLDS: M0 = {m0:.3f} <= 0.65.")
    controls = [c for c in ("M0", "P0", "MIS", "MIS2") if c in acc]
    for a in arms:
        if a in ("M0", "M0s", "P0", "MIS", "MIS2"):
            continue
        missing = [c for c in ("M0", "P0", "MIS") if c not in acc]
        if missing:
            out.append(f"{a}: 'predicts taste' not evaluable (missing arms: {', '.join(missing)}).")
            continue
        d = s["acc_minus_M0"][a]
        beats = all(acc[a] > acc[c] for c in controls)
        same_sign = "M0s" not in acc or (acc[a] - acc["M0s"]) * d["diff"] > 0
        if beats and d["ci90"][0] > 0 and same_sign:
            out.append(f"{a}: PREDICTS TASTE (beats {', '.join(controls)}; diff vs M0 {d['diff']:+.3f} "
                       f"CI {d['ci90']}; same sign vs M0s).")
        elif a == "P1" and acc[a] > acc["M0"] and not beats:
            out.append("P1: beats M0 but not P0/MIS: extra context helps; no taste claim.")
        else:
            out.append(f"{a}: does not predict taste (acc {acc[a]:.3f}; diff vs M0 {d['diff']:+.3f} CI {d['ci90']}; "
                       f"beats all of {', '.join(controls)}: {beats}; same sign vs M0s: {same_sign}).")
    return out


def report_md(res, arms, args, words_by_arm, calls_before, calls_after):
    lines = [f"# E2 v2: `{args.out}`", "",
             (f"Pairs: `{os.path.relpath(args.pairs, HERE)}`. Arms: {', '.join(arms)}. "
              f"Real CLI calls this run: {calls_after - calls_before} (calls.log total {calls_after}). "
              f"Errors: {len(res['errors'])}."), "",
             ("Paired accuracy = his option chosen in both orders. 90% CIs resample works. "
              "p(his) is averaged over both orders."), ""]
    for name, s in res["subsets"].items():
        lines += [f"## {name} (n = {s['n_pairs']}, works = {s['n_works']})", "",
                  "| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |",
                  "|---|---|---|---|---|---|"]
        for a in arms:
            acc, ph = s["accuracy"][a], s["mean_p_his"][a]
            d = s.get("acc_minus_M0", {}).get(a)
            dp = s.get("p_his_minus_M0", {}).get(a)
            dd = f"{d['diff']:+.3f} {d['ci90']}" if d else "–"
            ddp = f"{dp['diff']:+.3f} {dp['ci90']}" if dp else "–"
            lines.append(f"| {a} | {words_by_arm[a]} | {acc['value']:.3f} {acc['ci90']} | {dd} | "
                         f"{ph['value']:.3f} {ph['ci90']} | {ddp} |")
        lines.append("")
    lines += ["## Decision rules (PROTOCOL.md), on the whole pairs file", ""]
    lines += [f"- {v}" for v in res["verdicts"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--arms", required=True, help="comma-separated, from " + ",".join(ARMS))
    ap.add_argument("--out", required=True, help="basename for <out>.json and <out>.md in this directory")
    ap.add_argument("--cap", type=int, default=350, help="refuse calls once calls.log holds this many")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    arms = args.arms.split(",")
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        sys.exit(f"unknown arms {unknown}")
    CAP[0] = args.cap
    pairs = read_jsonl(args.pairs)
    words_by_arm = {a: words(profile_text(a, pairs[0]["context"])) for a in arms}
    before = real_calls()
    preds = predict_all(pairs, arms, args.workers)
    res = score(pairs, preds, arms)
    res["verdicts"] = verdicts(res, arms)
    res.update({"pairs_file": os.path.relpath(args.pairs, HERE), "arms": arms, "profile_words": words_by_arm,
                "calls_this_run": real_calls() - before, "calls_log_total": real_calls(), "predictions": preds})
    with open(p(args.out + ".json"), "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    md = report_md(res, arms, args, words_by_arm, before, real_calls())
    with open(p(args.out + ".md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
