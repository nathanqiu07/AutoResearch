"""Stage 3 (PROTOCOL.md "Question and arms"): which of two real, abstracted decisions did Owain Evans make?

Predictor plumbing is e2_v2's: UserModel._predict_with with the profile in the persona slot, wrapped in
track_eval.JsonReply, both orders, track_eval.paired_correct, cluster CIs over Owain works. Profiles come from
profiles_contrastive (P1, P2, P4 fixed; P3 retrieves on each pair's two abstracted problems) and e2_v2 (P0
trimmed to P1's length, MIS = shuffled P4, MIS2 = Steinhardt's card).

    python3 run.py --sonnet NAME,P0,P1,P3,P4,MIS --haiku NAME,P4,P0,MIS   -> results.json, results_tables.md
"""
import argparse
import collections
import importlib.util
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

from common import TP, WORKERS, call, p, read_jsonl, started

from autoresearch.llm import LLM, Budget
from autoresearch.taste import track_eval
from autoresearch.taste.timesplit import ANON_USER
from autoresearch.taste.usermodel import Choice, UserModel

ARMS = ("NAME", "P0", "P1", "P2", "P3", "P4", "P1+P3", "MIS", "MIS2")
CONTROLS = ("NAME", "P0", "MIS")
P3_K = 3  # per abstracted problem, so up to 6 past decisions per pair
LINE = ["predict"]  # the calls.log budget line, set from --line


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E2 = _load("e2v2_run", os.path.join(TP, "e2_v2", "run.py"))
PC = E2.PC


def p3_text(pair):
    """Retrieval keyed on both abstracted problems, merged and ordered by score, so it does not depend on which
    option is his."""
    hits = {}
    for prob in (pair["his_problem"], pair["other_problem"]):
        for h in PC.retrieve(prob, P3_K):
            if h["decision_id"] not in hits or h["score"] > hits[h["decision_id"]]["score"]:
                hits[h["decision_id"]] = h
    return PC.render(sorted(hits.values(), key=lambda h: (-h["score"], h["decision_id"])))


def profile_text(arm, pair):
    if arm == "NAME":
        return "The researcher is Owain Evans."
    if arm in ("P0", "MIS", "MIS2"):
        return E2.FIXED[arm]()
    if arm == "P3":
        return p3_text(pair)
    if arm == "P1+P3":
        return PC.get_profile_text("P1") + "\n\n" + p3_text(pair)
    return PC.get_profile_text(arm)


class CLI(LLM):
    name = "claude-cli"

    def __init__(self, arm, model):
        super().__init__(Budget(max_calls=10 ** 6, max_cost_usd=1e9, max_seconds=24 * 3600))
        self.arm, self.model = arm, model

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        return call(self.model, LINE[0], f"attrib:{self.arm}", prompt, system)


class Profiled(UserModel):
    """The persona is the arm's profile for this pair (P3 differs per pair), looked up by the option set."""
    method_id = "attrib"

    def __init__(self, llm_, arm, pairs, **kw):
        super().__init__(llm_, **kw)
        self.persona = {frozenset((r["a_text"], r["b_text"])): profile_text(arm, r) for r in pairs}

    def predict(self, context, options):
        return self._predict_with(context, options, persona=self.persona[frozenset(options)])


def choice(r):
    return Choice(user_id=ANON_USER, context=r["context"], a_text=r["a_text"], b_text=r["b_text"],
                  chosen=r["his_side"], decision_point=r["decision_point"], example_id=r["pair_id"],
                  group_id=r["work"])


def predict_all(jobs):
    """jobs: (model, arm, pairs). One pool of WORKERS for everything."""
    models = {(m, a): Profiled(track_eval.JsonReply(CLI(a, m)), a, prs) for m, a, prs in jobs}
    flat = [(m, a, r) for m, a, prs in jobs for r in prs]
    flat.sort(key=lambda x: (x[0] != "sonnet", x[2]["pair_id"], x[1]))  # pair-major: a cap hit leaves arms even

    def one(job):
        m, a, r = job
        c, model = choice(r), models[(m, a)]
        try:
            ok = track_eval.paired_correct(model, c)
            p1 = model.predict(c.context, [c.a_text, c.b_text]).probabilities  # cached
            p2 = model.predict(c.context, [c.b_text, c.a_text]).probabilities
            his1, his2 = p1[0 if c.chosen == "a" else 1], p2[1 if c.chosen == "a" else 0]
            return {"model": m, "arm": a, "pair_id": r["pair_id"], "correct": ok, "p_his": [his1, his2]}
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
            return {"model": m, "arm": a, "pair_id": r["pair_id"], "correct": None, "error": repr(e)[:300]}

    with ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(one, flat))


def score(pairs, preds, model, arms):
    by_id = {r["pair_id"]: r for r in pairs}
    mine = [r for r in preds if r["model"] == model]
    failed = {r["pair_id"] for r in mine if r["correct"] is None}
    ok = {r["pair_id"] for r in mine} - failed  # every arm on the same pairs
    subsets = {"all": ok}
    for opp in sorted({by_id[k]["opponent"] for k in ok}):
        subsets[f"opponent={opp}"] = {k for k in ok if by_id[k]["opponent"] == opp}

    def grouped(arm, ids, value):
        out = collections.defaultdict(list)
        for r in mine:
            if r["arm"] == arm and r["pair_id"] in ids:
                out[by_id[r["pair_id"]]["work"]].append(value(r))
        return dict(out)

    correct, p_his = (lambda r: bool(r["correct"])), (lambda r: sum(r["p_his"]) / 2)
    res = {"n_failed_pairs": len(failed), "errors": [r for r in mine if r["correct"] is None], "subsets": {}}
    for name, ids in subsets.items():
        s = {"n_pairs": len(ids), "n_works": len({by_id[k]["work"] for k in ids}),
             "accuracy": {a: E2._acc(grouped(a, ids, correct)) for a in arms},
             "mean_p_his": {a: E2._acc(grouped(a, ids, p_his)) for a in arms}, "diff": {}}
        for c in CONTROLS:
            if c in arms:
                s["diff"][c] = {a: E2._diff(grouped(a, ids, correct), grouped(c, ids, correct))
                                for a in arms if a != c}
        res["subsets"][name] = s
    return res


def verdicts(res, arms, model):
    s = res["subsets"]["all"]
    acc = {a: s["accuracy"][a]["value"] for a in arms}
    out = []
    if s["n_pairs"] < 60 or s["n_works"] < 8:
        out.append(f"DESCRIPTIVE ONLY ({model}): {s['n_pairs']} pairs / {s['n_works']} works (< 60 or < 8).")
    if "NAME" in acc:
        if acc["NAME"] > 0.65:
            out.append(f"LEAKAGE ({model}): NAME = {acc['NAME']:.3f} > 0.65, so topic or identity leaked through the "
                       "abstraction. Re-abstract more aggressively before any claim.")
        else:
            out.append(f"NO LEAKAGE FLAG ({model}): NAME = {acc['NAME']:.3f} <= 0.65.")
    missing = [c for c in CONTROLS if c not in arms]
    for a in arms:
        if a in CONTROLS or a == "MIS2":
            continue
        if missing:
            out.append(f"{a} ({model}): taste attribution not evaluable (missing controls {missing}).")
            continue
        ds = {c: s["diff"][c][a] for c in CONTROLS}
        passed = all(d["ci90"][0] > 0 for d in ds.values())
        detail = "; ".join(f"vs {c} {d['diff']:+.3f} {d['ci90']}" for c, d in ds.items())
        out.append(f"{a} ({model}): {'TASTE ATTRIBUTION' if passed else 'no taste attribution'} "
                   f"(acc {acc[a]:.3f}; {detail}).")
    return out


def tables(res, arms, model, words_by_arm):
    lines = []
    for name, s in res["subsets"].items():
        if name == "all":
            lines += [f"### {model}: all pairs (n = {s['n_pairs']}, Owain works = {s['n_works']})", "",
                      ("| arm | words | paired acc [90% CI] | mean p(his) [90% CI] | Δ vs NAME [90% CI] | "
                       "Δ vs P0 [90% CI] | Δ vs MIS [90% CI] |"), "|---|---|---|---|---|---|---|"]
            for a in arms:
                acc, ph = s["accuracy"][a], s["mean_p_his"][a]
                cells = []
                for c in CONTROLS:
                    d = s["diff"].get(c, {}).get(a)
                    cells.append(f"{d['diff']:+.3f} {d['ci90']}" if d else "–")
                lines.append(f"| {a} | {words_by_arm[a]} | {acc['value']:.3f} {acc['ci90']} | "
                             f"{ph['value']:.3f} {ph['ci90']} | " + " | ".join(cells) + " |")
            lines.append("")
    opp = [k for k in res["subsets"] if k.startswith("opponent=")]
    lines += [f"### {model}: paired accuracy by opponent researcher", "",
              "| arm | " + " | ".join(f"{k.split('=')[1]} (n={res['subsets'][k]['n_pairs']})" for k in opp) + " |",
              "|---|" + "---|" * len(opp)]
    for a in arms:
        lines.append(f"| {a} | " + " | ".join(f"{res['subsets'][k]['accuracy'][a]['value']:.3f}" for k in opp)
                     + " |")
    lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonnet", default="NAME,P0,P1,P3,P4,MIS")
    ap.add_argument("--haiku", default="NAME,P4,P0,MIS", help="'' for none")
    ap.add_argument("--pairs", default="pairs.jsonl")
    ap.add_argument("--subset", default="in_sonnet", help="pairs column that selects the sonnet pairs")
    ap.add_argument("--line", default="predict", help="calls.log budget line (common.CAPS)")
    ap.add_argument("--out", default="", help="prefix for results.json and results_tables.md")
    args = ap.parse_args()
    LINE[0] = args.line
    arms = {m: v.split(",") for m, v in (("sonnet", args.sonnet), ("haiku", args.haiku)) if v}
    bad = [a for v in arms.values() for a in v if a not in ARMS]
    if bad:
        raise SystemExit(f"unknown arms {bad}")
    pairs = read_jsonl(p(args.pairs))
    sets = {"sonnet": [r for r in pairs if r[args.subset]], "haiku": [r for r in pairs if r.get("in_haiku")]}
    before = {m: started(m, LINE[0]) for m in arms}
    preds = predict_all([(m, a, sets[m]) for m in arms for a in arms[m]])
    out = {"arms": arms, "n_pairs": {m: len(v) for m, v in sets.items()},
           "calls_this_run": {m: started(m, LINE[0]) - before[m] for m in arms},
           "calls_total": {m: started(m, LINE[0]) for m in arms}, "models": {}, "verdicts": []}
    md = []
    for m, m_arms in arms.items():
        words_by_arm = {a: E2.words(profile_text(a, sets[m][0])) for a in m_arms}
        res = score(sets[m], preds, m, m_arms)
        res["profile_words"] = words_by_arm
        out["models"][m] = res
        out["verdicts"] += verdicts(res, m_arms, m)
        md += tables(res, m_arms, m, words_by_arm)
    by_pair = collections.defaultdict(dict)
    for r in preds:
        by_pair[r["pair_id"]][f"{r['model']}:{r['arm']}"] = {k: r.get(k) for k in ("correct", "p_his", "error")}
    out["per_pair"] = [{**{k: r[k] for k in ("pair_id", "work", "decision_point", "opponent", "opponent_work", "sim",
                                             "his_text", "other_text")}, args.subset: r[args.subset],
                        "predictions": by_pair.get(r["pair_id"], {})} for r in pairs]
    with open(p(args.out + "results.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    md += ["### Verdicts (PROTOCOL.md decision rules)", ""] + [f"- {v}" for v in out["verdicts"]]
    md += ["", f"Calls this run: {out['calls_this_run']}; predictor totals in calls.log: {out['calls_total']}."]
    with open(p(args.out + "results_tables.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
