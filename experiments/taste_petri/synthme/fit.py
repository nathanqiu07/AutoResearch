"""SynthesizeMe (the repo's M2, imported unchanged) fit on firewalled pre-T pairs, scored on e2_v4's 96 test pairs.

    python3 fit.py fit paper|informal|all     # writes S_paper.json / S_inf.json / S_all.json
    python3 fit.py test ARM [ARM ...]          # S_paper, S_inf, S_all, ANTI0 on the test pairs -> test_<ARM>.json
    python3 fit.py report                      # results.json, results.md

Wrapper changes, none in repo code:
- Validation predictions are BATCHED: BatchedSynthesizeMe._predict_with answers a validation pair from one
  call that predicts every validation pair under the same principles/persona/exemplars. Any other
  pair (the test pairs) goes to the repo's unbatched predictor, the same one e2_v4's arms used.
- forward_select trials run 4 at a time: during fit, m2's module-level forward_select is swapped for one
  that prefetches a round's trial scores in parallel and then runs the repo's forward_select on the
  memoised scores, so the selection logic and its trace are the repo's.
Every CLI call goes through pairs_v2's call(): cached in cache/, logged in calls.log, capped.
"""
import collections
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pairs as P  # points pairs_v2's call wrapper, cache and calls.log here

from autoresearch.llm import LLM, Budget
from autoresearch.taste import track_eval
from autoresearch.taste.methods import common, m2_synthesizeme as m2
from autoresearch.taste.timesplit import ANON_USER, banned_pattern
from autoresearch.taste.researcher import load_researcher
from autoresearch.taste.usermodel import Choice, Prediction, UserModel

HERE, TP = P.HERE, P.TP
WORKERS = 4
VAL_BATCH = 60
CONFIG = {"max_history": 50, "max_hypotheses": 8}
ARM_SOURCE = {"S_paper": "paper", "S_inf": "informal", "S_all": "all"}
CACHED = ["M0s", "NAME", "P0"]  # e2_v4/results.json
BANNED = banned_pattern(load_researcher(P.v2.SLUG))


class UsageLimit(Exception):
    """The account's CLI usage limit: stop the run instead of recording failed predictions."""


class CLI(LLM):
    name = "claude-cli"

    def __init__(self, model, tag):
        super().__init__(Budget(max_calls=10 ** 6, max_seconds=72 * 3600, max_cost_usd=1e9))  # calls.log caps
        self.model, self.tag = model, tag

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        for attempt in range(3):
            try:
                return P.call(self.model, self.tag, prompt, system=system)
            except RuntimeError as e:
                if "hit your" in str(e):
                    raise UsageLimit(str(e)) from e
                if "cap" in str(e) or attempt == 2:
                    raise
                print("retry after", str(e)[:120], flush=True)


def llm(tag):
    return track_eval.JsonReply(CLI("sonnet", tag))


# ---------------------------------------------------------------- data

def to_choice(r, source):
    reason = r.get("stated_reason", "")
    return Choice(user_id=ANON_USER, context=f"{r['context']}\n\nQuestion: {r['question']}", a_text=r["a_text"],
                  b_text=r["b_text"], chosen=r["his_side"], decision_point=r["point"],
                  reason="" if BANNED.search(reason) else reason, timestamp=r["date"], source="synthme:" + source,
                  example_id=r["pair_id"], group_id=r["work"])


def train_val(source):
    rows = {r["pair_id"]: r for r in P.read_jsonl(os.path.join(HERE, f"pairs_{source}.jsonl"))}
    with open(os.path.join(HERE, "split.json")) as f:
        sp = json.load(f)[source]
    return ([to_choice(rows[i], source) for i in sp["train_ids"]], [to_choice(rows[i], source) for i in sp["val_ids"]])


def history_and_val(name):
    if name != "all":
        return train_val(name)
    (ht_i, hv_i), (ht_p, hv_p) = train_val("informal"), train_val("paper")
    # informal pairs first: all of them, then paper pairs drawn the repo's way (seeded sample) to fill 50
    n_paper = max(0, CONFIG["max_history"] - len(ht_i))
    stub = UserModel(llm("unused"), seed=0, max_history=n_paper or 1)
    paper = common.selected_history(stub, ht_p) if n_paper else []
    return ht_i[:CONFIG["max_history"]] + paper, hv_i + hv_p


# ---------------------------------------------------------------- batched validation predictor

VAL_INSTRUCTION = ('Predict which option this user would choose in each item below. If no personal evidence is '
                   'provided, judge what a typical user would prefer. Judge every item on its own. Return '
                   '{"items": [{"key": the item key, "probabilities": [one probability per option, in order, '
                   'summing to 1]}]} with one entry per item.')
ORIG_FORWARD_SELECT = common.forward_select


def parallel_forward_select(candidates, score, max_items):
    memo = {}

    def key(items):
        return json.dumps(items, sort_keys=True, default=str)

    def memo_score(items):
        k = key(items)
        if k not in memo:
            jobs = [items[:-1] + [c] for c in candidates if c not in items[:-1]] if items else [items]
            with ThreadPoolExecutor(WORKERS) as ex:
                for its, s in zip(jobs, ex.map(score, jobs)):
                    memo[key(its)] = s
            if k not in memo:
                memo[k] = score(items)
        return memo[k]

    return ORIG_FORWARD_SELECT(candidates, memo_score, max_items)


class BatchedSynthesizeMe(m2.SynthesizeMe):
    _val = {}

    def fit(self, history, val):
        self._val = {(c.context, (c.a_text, c.b_text)): c for c in val}
        self._memo, self._locks, self._lock = {}, {}, threading.Lock()
        self.batch = {"calls": 0, "items": 0, "misses": 0}
        m2.forward_select = parallel_forward_select
        try:
            super().fit(history, val)
        finally:
            m2.forward_select = ORIG_FORWARD_SELECT
            self._val = {}

    def _predict_with(self, context, options, principles=(), persona="", exemplars=()):
        k = (context, tuple(options))
        if k not in self._val:
            return super()._predict_with(context, options, principles, persona, exemplars)
        cond = json.dumps([list(principles), persona, list(exemplars)], sort_keys=True, default=str)
        with self._lock:
            lock = self._locks.setdefault(cond, threading.Lock())
        with lock:
            if cond not in self._memo:
                self._memo[cond] = self._batched(principles, persona, exemplars)
        return self._memo[cond][k]

    def _batched(self, principles, persona, exemplars):
        rows, out = list(self._val.values()), {}
        for start in range(0, len(rows), VAL_BATCH):
            chunk = rows[start:start + VAL_BATCH]
            items = [{"key": f"v{i + 1}", "context": c.context, "options": [c.a_text, c.b_text]}
                     for i, c in enumerate(chunk)]
            res = self._json(VAL_INSTRUCTION, {"principles": list(principles), "persona": persona,
                                               "past_choices": list(exemplars), "items": items})
            self.batch["calls"] += 1
            got = {str(o.get("key")): o.get("probabilities") for o in res.get("items", []) if isinstance(o, dict)}
            for it, c in zip(items, chunk):
                p = got.get(it["key"])
                k = (c.context, (c.a_text, c.b_text))
                if (isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                                                 and x >= 0 for x in p) and sum(p) > 0):
                    p = [x / sum(p) for x in p]
                    i = max(range(2), key=p.__getitem__)
                    out[k] = Prediction(chr(ord("a") + i), p[i], "", p)
                    self.batch["items"] += 1
                else:  # an item the batch reply dropped: the repo's single-pair predictor
                    self.batch["misses"] += 1
                    out[k] = m2.SynthesizeMe._predict_with(self, c.context, [c.a_text, c.b_text],
                                                           principles, persona, exemplars)
        return out


def s_path(arm):
    return os.path.join(HERE, arm + ".json")


def fit(name):
    arm = {"paper": "S_paper", "informal": "S_inf", "all": "S_all"}[name]
    history, val = history_and_val(name)
    model = BatchedSynthesizeMe(llm("fit:" + arm), seed=0, cache_dir=os.path.join(HERE, "cache", "um_" + arm),
                                max_calls=2400, **CONFIG)
    before = P.v2.real_calls("sonnet")
    model.fit(history, val)
    model.save(s_path(arm))
    with open(s_path(arm)) as f:
        body = json.load(f)
    body["synthme"] = {"arm": arm, "n_history_given": len(history), "n_val": len(val),
                       "history_works": sorted({c.group_id for c in history}), "val_works": sorted({c.group_id for c in val}),
                       "batched_validation": model.batch, "val_batch_size": VAL_BATCH,
                       "real_sonnet_calls_this_fit": P.v2.real_calls("sonnet") - before}
    with open(s_path(arm), "w") as f:
        json.dump(body, f, indent=1, ensure_ascii=False)
    a = body["artifacts"]
    print(json.dumps({"persona": a["persona"], "persona_validation": a["metadata"].get("persona_validation"),
                      "retained": a["metadata"].get("retained_hypotheses"), "n_exemplars": len(a["exemplars"]),
                      **body["synthme"]}, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- test arms

def words(text):
    return len(text.split())


def anti0_text():
    """ANTI0.md (written before any fit) cut to S_paper's persona word count: whole lines while they
    fit, then the next line cut at a word (e2_v2's P0 trimming rule)."""
    with open(os.path.join(HERE, "ANTI0.md")) as f:
        text = f.read().strip()
    with open(s_path("S_paper")) as f:
        budget = words(json.load(f)["artifacts"]["persona"])
    if not budget:
        return text
    out = []
    for line in text.splitlines():
        left = budget - sum(words(x) for x in out)
        if left <= 0:
            break
        out.append(line if words(line) <= left else " ".join(line.split()[:left]))
    return "\n".join(out).strip()


class Fixed(UserModel):
    method_id = "synthme_fixed"

    def __init__(self, llm_, persona, **kw):
        super().__init__(llm_, **kw)
        self.persona = persona

    def predict(self, context, options):
        return self._predict_with(context, options, persona=self.persona)


def test_model(arm):
    cache = os.path.join(HERE, "cache", "test_" + arm)
    if arm == "ANTI0":
        return Fixed(llm("test:ANTI0"), anti0_text(), cache_dir=cache, max_calls=400)
    with open(s_path(arm)) as f:
        body = json.load(f)
    model = BatchedSynthesizeMe(llm("test:" + arm), seed=0, cache_dir=cache, max_calls=400, **CONFIG)
    from autoresearch.taste.usermodel import TasteArtifacts
    model._artifacts = TasteArtifacts(**body["artifacts"])
    return model


def test_pairs():
    return P.read_jsonl(os.path.join(TP, "e2_v4", "pairs.jsonl"))


def test_choice(r):  # e2_v2.choice
    return Choice(user_id=ANON_USER, context=f"{r['context']}\n\nQuestion: {r['question']}", a_text=r["a_text"],
                  b_text=r["b_text"], chosen=r["his_side"], decision_point=r["decision_point"],
                  example_id=r["pair_id"], group_id=r["work"])


def test(arm):
    model = test_model(arm)

    def one(r):
        c = test_choice(r)
        try:
            ok = track_eval.paired_correct(model, c)
            p1 = model.predict(c.context, [c.a_text, c.b_text]).probabilities
            p2 = model.predict(c.context, [c.b_text, c.a_text]).probabilities
            return {"arm": arm, "pair_id": c.example_id, "correct": ok,
                    "p_his": [p1[0 if c.chosen == "a" else 1], p2[1 if c.chosen == "a" else 0]]}
        except (ValueError, RuntimeError) as e:
            return {"arm": arm, "pair_id": c.example_id, "correct": None, "error": repr(e)[:300]}

    before = P.v2.real_calls("sonnet")
    with ThreadPoolExecutor(WORKERS) as ex:
        preds = list(ex.map(one, test_pairs()))
    out = {"arm": arm, "profile_words": words(getattr(model, "persona", "") or model._artifacts.persona),
           "n_exemplars": len(model._artifacts.exemplars), "real_sonnet_calls": P.v2.real_calls("sonnet") - before,
           "predictions": preds}
    if arm == "ANTI0":
        out["profile_text"] = model.persona
    with open(os.path.join(HERE, f"test_{arm}.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    ok = [r for r in preds if r["correct"] is not None]
    print(arm, "errors", len(preds) - len(ok), "paired acc", round(sum(r["correct"] for r in ok) / len(ok), 3),
          "calls", out["real_sonnet_calls"])


# ---------------------------------------------------------------- report

def _acc(by_group):
    v, lo, hi = track_eval.cluster_ci(by_group)
    return {"value": round(v, 3), "ci90": [round(lo, 3), round(hi, 3)]}


def _diff(a, b):
    d, lo, hi = track_eval.cluster_diff_ci(a, b)
    return {"diff": round(d, 3), "ci90": [round(lo, 3), round(hi, 3)]}


CAUTION = re.compile(r"caut|hedg|bold|pragmat|conservative|ambitio|rigor|risk|simpl|decisive|commit", re.IGNORECASE)


def report():
    pairs = test_pairs()
    work = {r["pair_id"]: r["work"] for r in pairs}
    with open(os.path.join(TP, "e2_v4", "results.json")) as f:
        cached = [x for x in json.load(f)["predictions"] if x["arm"] in CACHED]
    s_arms = [a for a in ARM_SOURCE if os.path.exists(os.path.join(HERE, f"test_{a}.json"))]
    new = {}
    for a in s_arms + ["ANTI0"]:
        path = os.path.join(HERE, f"test_{a}.json")
        if os.path.exists(path):
            with open(path) as f:
                new[a] = json.load(f)
    preds = cached + [x for t in new.values() for x in t["predictions"]]
    arms = CACHED + list(new)
    failed = {x["pair_id"] for x in preds if x["correct"] is None}
    g = {a: collections.defaultdict(list) for a in arms}
    gp = {a: collections.defaultdict(list) for a in arms}
    for x in preds:
        if x["pair_id"] not in failed:
            g[x["arm"]][work[x["pair_id"]]].append(bool(x["correct"]))
            gp[x["arm"]][work[x["pair_id"]]].append(sum(x["p_his"]) / 2)
    res = {"n_pairs": len(pairs) - len(failed), "n_works": len({work[k] for k in work if k not in failed}),
           "excluded_failed_pairs": sorted(failed),
           "accuracy": {a: _acc(g[a]) for a in arms}, "mean_p_his": {a: _acc(gp[a]) for a in arms},
           "vs": {a: {c: {"acc": _diff(g[a], g[c]), "p_his": _diff(gp[a], gp[c])}
                      for c in arms if c != a and c not in ARM_SOURCE or (a == "S_inf" and c == "S_paper")
                      or (a == "S_all" and c == "S_paper")} for a in s_arms}}
    verdicts = []
    for a in s_arms:
        for c, label in (("M0s", "PRIMARY"), ("NAME", "SECONDARY")):
            d = res["vs"][a][c]
            hit = [m for m in ("acc", "p_his") if d[m]["ci90"][0] > 0]
            verdicts.append(f"{label} {a} vs {c}: " + (f"BEATS on {', '.join(hit)}" if hit else "does not beat") +
                            f" (Δacc {d['acc']['diff']:+.3f} {d['acc']['ci90']}; Δp(his) {d['p_his']['diff']:+.3f} {d['p_his']['ci90']}).")
        for c in ("P0", "ANTI0"):
            if c in res["vs"][a]:
                d = res["vs"][a][c]
                verdicts.append(f"descriptive {a} vs {c}: Δacc {d['acc']['diff']:+.3f} {d['acc']['ci90']}; "
                                f"Δp(his) {d['p_his']['diff']:+.3f} {d['p_his']['ci90']}.")
    if "S_inf" in s_arms:
        d = res["vs"]["S_inf"]["S_paper"]
        n_inf = len(train_val("informal")[0])
        verdicts.append(("DESCRIPTIVE ONLY (< 30 informal training pairs). " if n_inf < 30 else "")
                        + "S_inf − S_paper: " + ("CLAIM" if d["acc"]["ci90"][0] > 0 or d["acc"]["ci90"][1] < 0 else "no claim")
                        + f" (Δacc {d['acc']['diff']:+.3f} {d['acc']['ci90']}; Δp(his) {d['p_his']['diff']:+.3f} {d['p_his']['ci90']}).")
    fits = {}
    for a in s_arms:
        with open(s_path(a)) as f:
            body = json.load(f)
        art, meta = body["artifacts"], body["artifacts"]["metadata"]
        fits[a] = {"persona": art["persona"], "persona_words": words(art["persona"]),
                   "persona_validation": meta.get("persona_validation"), "retained_hypotheses": meta.get("retained_hypotheses"),
                   "n_hypotheses_proposed": len(meta.get("hypothesis_proposals", [])),
                   "hypothesis_rounds": [round(max(t["after"] for t in meta["hypothesis_trace"] if t["round"] == r), 3)
                                         for r in sorted({t["round"] for t in meta["hypothesis_trace"]})],
                   "baseline_val": meta.get("hypothesis_trace", [{}])[0].get("before"),
                   "n_exemplars": len(art["exemplars"]), "exemplar_trace_best": [
                       round(max(t["after"] for t in meta["exemplar_trace"] if t["round"] == r), 3)
                       for r in sorted({t["round"] for t in meta["exemplar_trace"]})],
                   "caution_terms_in_persona": sorted({m.group(0).lower() for m in CAUTION.finditer(art["persona"])}),
                   **body["synthme"]}
    log = P.read_jsonl(os.path.join(HERE, "calls.log"))
    started = [r for r in log if r.get("status") == "started"]
    calls = {"sonnet": sum(r["model"] == "sonnet" for r in started), "haiku": sum(r["model"] == "haiku" for r in started),
             "by_tag": dict(collections.Counter(r["tag"].rsplit(":", 1)[0] if r["tag"].startswith(("fit:", "test:")) else r["tag"]
                                                for r in started)),
             "errors": sum(r.get("status") == "error" for r in log),
             "cost_usd": round(sum(r.get("cost_usd") or 0 for r in log), 2)}
    out = {"test": res, "verdicts": verdicts, "fits": fits, "calls": calls,
           "anti0_words": new.get("ANTI0", {}).get("profile_words"), "anti0_text": new.get("ANTI0", {}).get("profile_text")}
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("verdicts", "calls")}, indent=1, ensure_ascii=False))
    print(json.dumps({a: {k: res[k][a] for k in ("accuracy", "mean_p_his")} for a in arms}, indent=1))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "fit":
        fit(args[0])
    elif cmd == "test":
        for a in args:
            test(a)
    else:
        report()
