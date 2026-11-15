"""Owain Evans E2 (time-split pair prediction) with our pre-T profile formats as extra arms.

usage: python3 run.py {pairs,build,run,score,all}

The scoring is the repo's: track_eval.paired_correct (his option in both orders), cluster_ci /
cluster_diff_ci (groups resampled), track_eval.NamedNoHistory / docs_arm, and agreement.votes /
agreement.lopsided for the blind gate. Every real `claude -p --model haiku` call goes through
CLI.complete: logged to calls.log, cached in cache/raw by (system, prompt, occurrence), hard cap CAP.
Reads data/ and the codex-marius worktree; writes only inside this directory.
"""
import collections
import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from autoresearch.llm import LLM, Budget
from autoresearch.taste import agreement, timesplit, track_eval
from autoresearch.taste.researcher import load_researcher
from autoresearch.taste.usermodel import Choice, UserModel

SLUG, NAME, T = "owain_evans", "Owain Evans", "2026-01-01"
CAP = 350
PER_DOC = 2
WORKERS = 6
VOTES_PER_ORDER = 2  # agreement.py uses 5 (10 votes); 2 (4 votes) fits the call budget
DATA = os.path.join(ROOT, "data", "researchers", SLUG)
# codex-marius's in-progress pairs run (Devin Sonnet 5.5, pair-v2 prompt, same code as main for this stage)
RENDERED = os.path.join(ROOT, "..", "AutoResearch-owain", "data", "researchers", SLUG, "pairs_timesplit.jsonl.partial")
PROFILES = os.path.join(ROOT, "experiments", "taste_petri", "profiles", SLUG)
CE = os.path.join(ROOT, "experiments", "taste_petri", "compression_eval")
ARMS = ["M0", "NAME", "M1_docs", "A_pre", "E_pre"]
# a paper and its blog post are one piece of work: cluster them together
WORK = {"research__consciousness_cluster_preferences_of_models_that_c_dd86ed8e.txt": "consciousness_cluster",
        "research__the_consciousness_cluster_emergent_preferences_of__5545a53f.txt": "consciousness_cluster",
        "research__conditional_misalignment_common_interventions_can__76ed8749.txt": "conditional_misalignment",
        "research__conditional_misalignment_mitigations_can_hide_em_b_a5f95a71.txt": "conditional_misalignment"}
LOCK = threading.Lock()


def p(*parts):
    out = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


# ---------------------------------------------------------------- the one CLI wrapper

def real_calls():
    if not os.path.exists(p("calls.log")):
        return 0
    with open(p("calls.log")) as f:
        return sum(1 for line in f if '"status": "started"' in line)


class CLI(LLM):
    """claude -p --model haiku, isolated like ClaudeCLILLM (plus --no-session-persistence).
    The n-th identical (system, prompt) call in a process gets its own cache slot, so repeated
    votes are separate samples on the first run and cache hits on a rerun."""
    name, model = "claude-cli", "haiku"
    DEFAULT_SYSTEM = "You are a helpful assistant."
    seen: ClassVar[collections.Counter] = collections.Counter()

    def __init__(self, tag, budget):
        super().__init__(budget)
        self.tag = tag

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        system = system or self.DEFAULT_SYSTEM
        base = hashlib.sha256(json.dumps([self.model, system, prompt]).encode()).hexdigest()
        with LOCK:
            occ = CLI.seen[base]
            CLI.seen[base] += 1
        key = f"{base[:32]}_{occ}"
        cpath = p("cache", "raw", key + ".json")
        if os.path.exists(cpath):
            with open(cpath) as f:
                return json.load(f)["result"]
        with LOCK:
            n = real_calls()
            if n >= CAP:
                raise RuntimeError(f"call cap {CAP} reached; refusing call {n + 1}")
            with open(p("calls.log"), "a") as f:  # the slot is reserved before the call
                f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n + 1, "tag": self.tag,
                                    "key": key, "chars": len(prompt), "status": "started"}) + "\n")
        cmd = ["claude", "-p", "--model", self.model, "--output-format", "json", "--tools", "",
               "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--system-prompt", system]
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix="e2o_cli_") as cwd:
            proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=600, cwd=cwd)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
        ok = proc.returncode == 0 and not data.get("is_error")
        with LOCK, open(p("calls.log"), "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "tag": self.tag, "key": key,
                                "status": "ok" if ok else "error", "secs": round(time.time() - t0, 1),
                                "cost_usd": data.get("total_cost_usd"), "out": str(data.get("result"))[:120]}) + "\n")
        if not ok:
            raise RuntimeError(f"claude CLI error: {str(data.get('result'))[:300]}")
        u = data.get("usage", {})
        self.budget.charge(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                           + u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0),
                           float(data.get("total_cost_usd") or 0.0))
        with open(cpath, "w") as f:
            json.dump({"tag": self.tag, "system": system, "prompt": prompt, "result": data["result"]}, f,
                      ensure_ascii=False)
        return data["result"]


BUDGET = Budget(max_calls=10 ** 6, max_cost_usd=1e9, max_seconds=12 * 3600)  # CAP above is the real limit


def llm(tag):
    return track_eval.JsonReply(CLI(tag, BUDGET))


# ---------------------------------------------------------------- pairs

# Read before any arm ran: the haiku renderer invented the context (a sleep study) for a decision
# whose recorded problem was only "How strongly to state a claim".
MANUAL_EXCLUDE = {"91f7dc5a9000": "renderer invented an unrelated context"}


def bad_distractor(decision, alt):
    """Unusable data: distract iterates a str alternatives_named character by character, so those
    'named' distractors are one letter long ('N', 'V', ...); some checked decisions have did "null"."""
    return (len(alt["text"].strip()) < 15 or str(decision.get("did") or "null").strip() == "null"
            or (alt["source"] == "named" and isinstance(decision.get("alternatives_named"), str)))


def make_pairs():
    researcher = load_researcher(SLUG)
    decisions = {d["decision_id"]: d for d in read_jsonl(os.path.join(DATA, "extraction", "decisions.jsonl"))}
    distractors = {r["decision_id"]: r for r in read_jsonl(os.path.join(DATA, "extraction", "distractors.jsonl"))}
    assert {r["cutoff"] for r in distractors.values()} == {T}
    rendered = [r for r in read_jsonl(RENDERED) if r["split"] == "heldout"]
    write_jsonl(p("source", "rendered_heldout_snapshot.jsonl"), rendered)
    banned = timesplit.banned_pattern(researcher)
    docs = timesplit._corpus_meta(researcher.root)
    meta = {name: fm for _, name, fm in docs}
    post = collections.defaultdict(list)
    for d in decisions.values():
        if d.get("date") and d["date"] >= T and d["decision_id"] in distractors:
            post[d["doc"]].append(d)
    excluded, out = [], []
    for doc in sorted(post):
        rng = random.Random("0:" + doc)
        have = [r for r in rendered if r["source_doc"] == doc]
        good = [r for r in have if not bad_distractor(decisions[r["decision_id"]], distractors[r["decision_id"]])]
        excluded += [{"pair_id": r["pair_id"], "doc": doc, "why": "bad distractor"} for r in have if r not in good]
        if good:
            for r in rng.sample(good, min(PER_DOC, len(good))):
                problems = timesplit.check_pair(r, timesplit._later_titles(docs, r["date"]), banned)
                assert not problems, (r["pair_id"], problems)
                out.append(dict(r, renderer="devin:claude-sonnet-5-5-medium (codex-marius run)"))
            continue
        cands = [d for d in post[doc] if not bad_distractor(d, distractors[d["decision_id"]])]
        excluded += [{"decision_id": d["decision_id"], "doc": doc, "why": "bad distractor"}
                     for d in post[doc] if d not in cands]
        rng.shuffle(cands)
        got = 0
        for d in cands:
            if got == PER_DOC:
                break
            alt = distractors[d["decision_id"]]
            pair, problems = timesplit.render_pair(d, alt["text"], CLI("render", BUDGET),
                                                   timesplit._later_titles(docs, d["date"]), banned, seed=0)
            if pair is None:
                excluded.append({"decision_id": d["decision_id"], "doc": doc, "why": "render failed", "problems": problems})
                continue
            row = timesplit._pair_row(researcher, d, alt, pair, T, 0, meta)
            if row["pair_id"] in MANUAL_EXCLUDE:
                excluded.append({"pair_id": row["pair_id"], "doc": doc, "why": MANUAL_EXCLUDE[row["pair_id"]]})
                continue
            out.append(dict(row, renderer="claude-cli:haiku (here)"))
            got += 1
    for r in out:
        r["work"] = WORK.get(r["source_doc"], r["source_doc"])
    write_jsonl(p("pairs.jsonl"), out)
    write_json(p("pairs_excluded.json"), excluded)
    print("pairs", len(out), "docs", len({r["source_doc"] for r in out}), "works", len({r["work"] for r in out}),
          "excluded", len(excluded), "calls so far", real_calls())


def choices():
    """Choice rows as timesplit.write_choice_files makes them, but grouped by work, not URL."""
    banned = timesplit.banned_pattern(load_researcher(SLUG))
    return [Choice(user_id=timesplit.ANON_USER, context=r["context"], a_text=r["a_text"], b_text=r["b_text"],
                   chosen=r["chosen"], decision_point=r["decision_point"],
                   reason="" if banned.search(r["reason"]) else r["reason"], timestamp=r["date"],
                   source="timesplit", example_id=r["pair_id"], group_id=r["work"])
            for r in read_jsonl(p("pairs.jsonl"))]


# ---------------------------------------------------------------- profiles (pre-T only)

def compression_eval():
    spec = importlib.util.spec_from_file_location("ce_run", os.path.join(CE, "run.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build():
    ce = compression_eval()
    with open(os.path.join(CE, "mask.json")) as f:
        pats = ce.mask_patterns(json.load(f))
    # A_pre: principle headlines whose every cited quote predates T (stricter than compression_eval's "any")
    with open(os.path.join(PROFILES, "a_principles.md")) as f:
        text = f.read()
    kept, dropped = [], []
    for b in re.split(r"\n(?=\d+\. \*\*)", text):
        m = re.match(r"(\d+)\. \*\*(.+?)\*\*", b)
        if m:
            dates = re.findall(r"\((\d{4}-\d{2}-\d{2});", b)
            (kept if dates and all(d < T for d in dates) else dropped).append(m.group(2).strip())
    a_pre = ce.truncate("\n".join("- " + ce.apply_mask(h, pats) for h in kept))
    # E_pre: compression_eval's taste-vector prompt over evidence claims dated before T
    pre = [r for r in read_jsonl(os.path.join(PROFILES, "evidence.jsonl")) if r.get("date") and r["date"] < T]
    claims = "\n".join(f"- ({ce.norm_d(r['dpoint']) or 'D?'}) {ce.apply_mask(r['claim'], pats)}" for r in pre)
    with open(os.path.join(CE, "prompts", "e_pre.txt")) as f:
        prompt = f.read().replace("{EVIDENCE}", claims)
    e_raw = CLI("build:E_pre", BUDGET).complete(prompt, system="You are a careful assistant. Follow the output format exactly.")
    e_pre = ce.truncate(ce.apply_mask(e_raw.strip(), pats))
    for arm, body in (("A_pre", a_pre), ("E_pre", e_pre)):
        with open(p("profiles", arm + ".md"), "w") as f:
            f.write(body + "\n")
    write_json(p("profiles", "build_report.json"), {
        "T": T, "evidence_pre_T": len(pre), "a_blocks_kept": len(kept), "a_blocks_dropped_post_T": dropped,
        "words": {"A_pre": ce.words(a_pre), "E_pre": ce.words(e_pre)},
        "mask_hits_after": {"A_pre": ce.leak_hits(a_pre, pats), "E_pre": ce.leak_hits(e_pre, pats)}})
    print(f"built A_pre ({ce.words(a_pre)} words, {len(kept)}/{len(kept) + len(dropped)} blocks) "
          f"E_pre ({ce.words(e_pre)} words); calls so far {real_calls()}")


class Principles(UserModel):
    method_id = "principles"

    def __init__(self, llm_, principles, **kw):
        super().__init__(llm_, **kw)
        self.principles = principles

    def predict(self, context, options):
        return self._predict_with(context, options, principles=self.principles)


class Persona(UserModel):
    method_id = "persona"

    def __init__(self, llm_, persona, **kw):
        super().__init__(llm_, **kw)
        self.persona = persona

    def predict(self, context, options):
        return self._predict_with(context, options, persona=self.persona)


def arms():
    cache = os.path.join(HERE, "cache", "usermodel")
    with open(p("profiles", "A_pre.md")) as f:
        a_pre = [line[2:] for line in f.read().splitlines() if line.startswith("- ")]
    with open(p("profiles", "E_pre.md")) as f:
        e_pre = f.read().strip()
    return {"M0": track_eval.NamedNoHistory(llm("M0"), None, cache_dir=cache),
            "NAME": track_eval.NamedNoHistory(llm("NAME"), NAME, cache_dir=cache),
            "M1_docs": track_eval.docs_arm(load_researcher(SLUG), llm("M1_docs"), T, cache_dir=cache),
            "A_pre": Principles(llm("A_pre"), a_pre, cache_dir=cache),
            "E_pre": Persona(llm("E_pre"), e_pre, cache_dir=cache)}


# ---------------------------------------------------------------- run

def run():
    cs = choices()
    models = arms()

    def one(job):
        arm, c = job
        model = models[arm]
        try:
            ok = track_eval.paired_correct(model, c)
            # both predictions are now in the user-model cache, so these cost no call
            p1 = model.predict(c.context, [c.a_text, c.b_text]).probabilities
            p2 = model.predict(c.context, [c.b_text, c.a_text]).probabilities
            his1 = p1[0 if c.chosen == "a" else 1]
            his2 = p2[1 if c.chosen == "a" else 0]
            return {"arm": arm, "pair_id": c.example_id, "correct": ok, "p_his": [his1, his2]}
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as e:  # recorded and excluded from that arm's score
            return {"arm": arm, "pair_id": c.example_id, "correct": None, "error": repr(e)[:300]}

    def vote(c):
        his, other = (c.a_text, c.b_text) if c.chosen == "a" else (c.b_text, c.a_text)
        return {"pair_id": c.example_id, "key": c.example_id,
                "votes": agreement.votes(llm("gate"), c.context, his, other, k=VOTES_PER_ORDER)}

    with ThreadPoolExecutor(WORKERS) as ex:
        gate = list(ex.map(vote, cs))
        write_jsonl(p("gate_votes.jsonl"), gate)
        print("gate done; calls so far", real_calls())
        rows = list(ex.map(one, [(arm, c) for arm in ARMS for c in cs]))
    write_jsonl(p("predictions.jsonl"), rows)
    print("arms done; calls so far", real_calls(), "errors", sum(r["correct"] is None for r in rows))


# ---------------------------------------------------------------- score

def _acc(by_group):
    acc, lo, hi = track_eval.cluster_ci(by_group)
    return {"accuracy": round(acc, 3), "ci90": [round(lo, 3), round(hi, 3)],
            "n_pairs": sum(len(v) for v in by_group.values()), "n_groups": len(by_group)}


def _diff(a, b):
    d, lo, hi = track_eval.cluster_diff_ci(a, b)
    return {"diff": round(d, 3), "ci90": [round(lo, 3), round(hi, 3)]}


def score():
    pairs = {r["pair_id"]: r for r in read_jsonl(p("pairs.jsonl"))}
    preds = read_jsonl(p("predictions.jsonl"))
    gate = {r["pair_id"]: r for r in read_jsonl(p("gate_votes.jsonl"))}
    share = {k: agreement.share(r) for k, r in gate.items()}  # pole 1 = his option
    lop = {k: agreement.lopsided(r) for k, r in gate.items()}
    failed = {r["pair_id"] for r in preds if r["correct"] is None}
    ok_ids = [k for k in pairs if k not in failed]

    def grouped(arm, ids, value=lambda r: bool(r["correct"])):
        out = collections.defaultdict(list)
        for r in preds:
            if r["arm"] == arm and r["pair_id"] in ids:
                out[pairs[r["pair_id"]]["work"]].append(value(r))
        return dict(out)

    def p_his(r):  # the arm's probability on his option, averaged over both orders
        return sum(r["p_his"]) / 2

    blind = {k: (1.0 if share[k] > 0.5 else 0.5 if share[k] == 0.5 else 0.0) for k in pairs}
    # not_toward_his: every pair the blind judge does not confidently get right (not lopsided, or
    # lopsided against his option): the pairs where generic research sense is not enough
    subsets = {"all": set(ok_ids), "not_lopsided": {k for k in ok_ids if not lop[k]},
               "lopsided": {k for k in ok_ids if lop[k]},
               "not_toward_his": {k for k in ok_ids if not (lop[k] and share[k] > 0.5)}}
    res = {"T": T, "n_pairs": len(pairs), "excluded_for_errors": sorted(failed), "votes_per_order": VOTES_PER_ORDER,
           "gate": {"lopsided": sum(lop.values()), "lopsided_toward_his": sum(lop[k] and share[k] > 0.5 for k in pairs),
                    "lopsided_against_his": sum(lop[k] and share[k] < 0.5 for k in pairs),
                    "not_lopsided": sum(not v for v in lop.values()),
                    "mean_share_for_his": round(sum(share.values()) / len(share), 3)},
           "subsets": {}, "real_calls": real_calls()}
    for name, ids in subsets.items():
        if not ids:
            continue
        g = {a: grouped(a, ids) for a in ARMS}
        bj = collections.defaultdict(list)
        for k in ids:
            bj[pairs[k]["work"]].append(blind[k])
        res["subsets"][name] = {
            "arms": {a: _acc(g[a]) for a in ARMS},
            "blind_judge_majority": _acc(dict(bj)),
            "minus_M0": {a: _diff(g[a], g["M0"]) for a in ARMS if a != "M0"},
            "minus_M1_docs": {a: _diff(g[a], g["M1_docs"]) for a in ARMS if a != "M1_docs"},
            "mean_p_his": {a: _acc(grouped(a, ids, p_his)) for a in ARMS},
            "mean_p_his_minus_M0": {a: _diff(grouped(a, ids, p_his), grouped("M0", ids, p_his))
                                    for a in ARMS if a != "M0"}}
    # per-pair table and breakdowns
    per = {k: {"work": pairs[k]["work"], "distractor_source": pairs[k]["distractor_source"],
               "renderer": pairs[k]["renderer"], "share_for_his": share[k], "lopsided": lop[k],
               **{a: next((r["correct"] for r in preds if r["arm"] == a and r["pair_id"] == k), None) for a in ARMS}}
           for k in pairs}
    res["by_distractor_source"] = {
        s: {"n": sum(v["distractor_source"] == s for v in per.values()),
            "lopsided": sum(v["lopsided"] for v in per.values() if v["distractor_source"] == s),
            **{a: sum(bool(v[a]) for v in per.values() if v["distractor_source"] == s) for a in ARMS}}
        for s in sorted({v["distractor_source"] for v in per.values()})}
    res["per_pair"] = per
    write_json(p("results.json"), res)
    print(json.dumps({k: res[k] for k in ("gate", "real_calls")}, indent=1))
    for name, s in res["subsets"].items():
        print("\n==", name)
        for a, v in s["arms"].items():
            print(f"{a:8} {v['accuracy']:.3f} {v['ci90']} n={v['n_pairs']} g={v['n_groups']} "
                  f"| -M0 {s['minus_M0'].get(a)} | -M1 {s['minus_M1_docs'].get(a)}")
        print("blind   ", s["blind_judge_majority"])


if __name__ == "__main__":
    step = sys.argv[1]
    for name, fn in (("pairs", make_pairs), ("build", build), ("run", run), ("score", score)):
        if step in (name, "all"):
            fn()
