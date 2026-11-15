"""pairs_v3: pairs_v2 re-rendered so a blind reader cannot tell the real decision from the
alternative, then gated on SONNET votes (controller, 2026-11-15: haiku's v2 band was a haiku
selection artefact; sonnet with no profile scored 0.83 on it).

Stages (each resumable through the call cache; pairs_v2 is imported read-only):
  render N        sonnet, blind to which option is his: both options restated at one level of
                  concreteness, length within 15%. Round 1 takes every pairs_v2 pair with blind
                  share in [0.15, 0.85]. Round N > 1 re-renders pairs whose latest render is out
                  of the realness band, with the readers' verdict as feedback.  -> renders.jsonl
                  Rounds 1-2 were driven by haiku realness votes, round 3 on by sonnet.
  real MODEL      realness gate ("one of these is what the team actually did") on every latest
                  render that has no MODEL votes yet, 3 per order               -> realness.jsonl
  confirm         6 more sonnet realness votes on every pair now in the realness band
  taste MODEL     taste gate (pairs_v2 prompt) on every latest render, 4 per order -> taste.jsonl
  fair            haiku fairness judge on every latest render, both orders      -> fairness.jsonl
  assemble        pairs.jsonl, band.jsonl, stats.json
Band = sonnet taste share in [0.25, 0.75] and sonnet realness in [0.3, 0.7] and fair.
"""
import collections
import importlib.util
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_DIR = os.path.join(HERE, "..", "pairs_v2")
sys.dont_write_bytecode = True  # importing pairs_v2 must not write into its dir
_spec = importlib.util.spec_from_file_location("pairs_v2_build", os.path.join(V2_DIR, "build.py"))
v2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v2)

# pairs_v2's call wrapper, cache, log and pmap resolve paths through v2.HERE and read CAPS and
# WORKERS at call time; pointed here they write only inside pairs_v3.
v2.HERE = HERE
v2.CAPS = {"sonnet": 390, "haiku": 450}  # hard stop; the per-purpose caps below are checked per stage
v2.WORKERS = 4
call, p, pmap, read_jsonl, write_jsonl = v2.call, v2.p, v2.pmap, v2.read_jsonl, v2.write_jsonl

SELECT = (0.15, 0.85)
REAL_BAND = (0.3, 0.7)
TASTE_BAND = v2.BAND
REAL_PER_ORDER, TASTE_PER_ORDER = 3, 4
MAX_RATIO = 1.15
GATE_MODEL = "sonnet"
CAPS = {"render": 40, "sonnet_gate": 350}


def spent(purpose):
    rows = [r for r in read_jsonl(p("calls.log")) if r.get("status") == "started" and r["model"] == "sonnet"]
    return sum(r["tag"].startswith("render") == (purpose == "render") for r in rows)


def check_budget(purpose, planned):
    if spent(purpose) + planned > CAPS[purpose]:
        raise RuntimeError(f"{purpose}: {spent(purpose)} spent + {planned} planned > cap {CAPS[purpose]}")

RENDER_PROMPT = """Each item below is a research decision with two options in random order. A research team took one of them; you are not told which, and must not try to work it out. Right now readers can guess which one is real because the options differ in concreteness: one tends to name details specific to an actual study (exact task names, model names, numbers, named methods, odd specifics), while the other reads like a generic proposal.

Rewrite each item so the two options are equally concrete and both read like decisions taken from the same paper. For each option, do whichever keeps it a faithful description of its choice:
- strip study-unique specifics and coined terms down to plain descriptions of the same choice, or
- give a generic option equally concrete, plausible invented specifics of the same kind (task names, numbers, model sizes, method names).
Keep each option's meaning. Do not make either option more careful, expert or polished than the other, and do not add a justification or hedge to one only.

Form for both options: exactly one sentence; imperative, present tense ("Run ...", "Report ..."); no first person (we, our, us, I, my, me); no names of people, labs or papers. Both between 150 and 190 characters and within 15% of each other's length. Either both options contain digits or neither does.

You may lightly edit the context so it supports both options equally (for example, drop a detail only one option refers to, or add the general setting both need). Keep its facts, and add nothing that hints at which option was taken.

Return only JSON: {{"items": [{{"key": str, "context": str, "question": str, "option_1": str, "option_2": str}}]}}

ITEMS:
"""
# Round 1 equalised the options alone and moved realness only from 0.87 to 0.81. Reading the
# round-1 pairs at 1.0 showed the remaining tell is mostly the context, which pairs_v2's generator
# wrote knowing the team's choice: it lists exactly the elements one option uses, or frames the
# question so that only one option answers it directly.
REVISE_NOTE = """
This is a revision. Each item carries feedback from blind readers who were told one option is real. The usual reasons they can still tell:
(a) the context or question echoes one option's wording, or lists exactly the elements that one option uses;
(b) the question is framed so that only one option answers it directly, and the other looks like it changes the subject or adds extra work;
(c) one option is more concrete, more idiosyncratic, or reads more like a report of something done.
Fix all three. Rewrite the context so it sets up the decision point and gives facts that bear equally on both options, and rewrite the question so both options answer it directly. Keep every option a faithful description of the same choice as before.
"""


def selected():
    return [x for x in read_jsonl(os.path.join(V2_DIR, "pairs.jsonl"))
            if SELECT[0] <= x["blind_share"] <= SELECT[1] and not x["check_problems"]]


def his_first(pair_id):
    """Fixed option order per pair for every render round, so feedback labels stay meaningful."""
    return random.Random("v3order:" + pair_id).random() < 0.5


def latest(rows):
    """pair_id -> its newest clean render."""
    out = {}
    for r in rows:
        if not r["problems"] and (r["pair_id"] not in out or r["round"] > out[r["pair_id"]]["round"]):
            out[r["pair_id"]] = r
    return out


def votes_by(path, model, round_=None):
    """pair_id -> picked_his votes from `model` (rows before the sonnet switch carry no model: haiku)."""
    out = collections.defaultdict(list)
    for v in read_jsonl(p(path)):
        if (v["picked_his"] is not None and v.get("model", "haiku") == model
                and (round_ is None or v.get("round") == round_)):
            out[v["id"]].append(v["picked_his"])
    return out


def share(vs):
    return sum(vs) / len(vs) if vs else None


def problems(context, his, alt, checks):
    probs = v2.pair_problems(context, his, alt, *checks)
    lengths = sorted(map(len, (his, alt)))
    if lengths[0] and lengths[1] / lengths[0] > MAX_RATIO and not any("20%" in x for x in probs):
        probs.append("the two options differ in length by more than 15%")
    return probs


def render(round_):
    round_ = int(round_)
    v2pairs = {x["pair_id"]: x for x in selected()}
    rows = read_jsonl(p("renders.jsonl"))
    if round_ == 1:
        todo = [(x, None) for x in v2pairs.values()]
    else:
        model = "haiku" if round_ == 2 else GATE_MODEL
        prev = {pid: r for pid, r in latest(rows).items() if r["round"] < round_}
        todo = []
        for pid, r in prev.items():
            real = votes_by("realness.jsonl", model, r["round"])
            s = share(real[pid])
            if s is not None and not REAL_BAND[0] <= s <= REAL_BAND[1]:
                hf = his_first(pid)
                looks_real = 1 if (s > 0.5) == hf else 2
                n = len(real[pid])
                todo.append((v2pairs[pid], {"r": r, "verdict": (
                    f"Readers asked which option the team actually did picked Option {looks_real} in "
                    f"{round(max(s, 1 - s) * n)} of {n} votes. Rebalance concreteness so neither reads as the real one.")}))
    check_budget("render", -(-len(todo) // 8) + 1)  # +1: the fix pass rarely needs more than one batch
    checks = (titles(), *v2.banned())

    def item_text(x, fb):
        base = fb["r"] if fb else {"context": x["context"], "question": x["question"],
                                   "his_text": x["a_text"] if x["his_side"] == "a" else x["b_text"],
                                   "alt_text": x["b_text"] if x["his_side"] == "a" else x["a_text"]}
        one, two = (base["his_text"], base["alt_text"]) if his_first(x["pair_id"]) else (base["alt_text"], base["his_text"])
        out = (f"\n=== key {x['pair_id']}\nContext: {base['context']}\nQuestion: {base['question']}\n"
               f"Option 1: {one}\nOption 2: {two}\n")
        return out + (f"Feedback on this version: {fb['verdict']}\n" if fb else "")

    def run(jobs, fixes, tag):
        def one(batch):
            body = "".join(item_text(x, fb) + (f"Problems to fix: {fixes[x['pair_id']]}\n" if x["pair_id"] in fixes else "")
                           for x, fb in batch)
            try:
                prompt = RENDER_PROMPT.format() + (REVISE_NOTE if round_ > 1 else "") + body
                return v2.objects_with(call("sonnet", tag, prompt), "key")
            except RuntimeError as e:
                print(tag, "failed", e)
                return []
        got = {}
        for objs in pmap(one, [jobs[i:i + 8] for i in range(0, len(jobs), 8)]):
            got.update({str(o.get("key")): o for o in objs})
        out = {}
        for x, _ in jobs:
            g = got.get(x["pair_id"])
            if not (g and g.get("option_1") and g.get("option_2") and g.get("context")):
                out[x["pair_id"]] = None
                continue
            one, two = str(g["option_1"]), str(g["option_2"])
            his, alt = (one, two) if his_first(x["pair_id"]) else (two, one)
            out[x["pair_id"]] = {"pair_id": x["pair_id"], "round": round_, "context": str(g["context"]),
                                 "question": str(g.get("question") or x["question"]), "his_text": his,
                                 "alt_text": alt, "problems": problems(str(g["context"]), his, alt, checks)}
        return out

    first = run(todo, {}, f"render{round_}")
    fixes = {k: ("; ".join(v["problems"]) if v else "no valid answer last time") for k, v in first.items()
             if not v or v["problems"]}
    if fixes:
        check_budget("render", -(-len(fixes) // 8))
        second = run([(x, fb) for x, fb in todo if x["pair_id"] in fixes], fixes, f"render{round_}_fix")
        first.update({k: v for k, v in second.items() if v})
    new = [v for v in first.values() if v]
    write_jsonl(p("renders.jsonl"), [r for r in rows if r["round"] != round_] + new)
    print(f"round {round_}: todo {len(todo)}, rendered {len(new)}, clean {sum(not r['problems'] for r in new)}",
          collections.Counter(x for r in new for x in r["problems"]).most_common(5))


def titles():
    out = [fm.get("title", "") for d, _, fm in v2.corpus().values() if d and d.isoformat() >= v2.T]
    return out + [re.sub(r"^\[[\d.]+\]\s*", "", t) for t in out]


def items(rows):
    decision = {x["pair_id"]: x["decision_id"] for x in selected()}
    return [{"id": r["pair_id"], "round": r["round"], "group": decision[r["pair_id"]], "context": r["context"],
             "question": r["question"], "his": r["his_text"], "alt": r["alt_text"]} for r in rows]


def vote(model, its, prompt, per_order, size, seed, tag):
    """One vote row per (item, order, rep): picked_his for 1/2 prompts, the raw answer for fairness."""
    slots = [(it, hf, rep) for it in its for hf in (True, False) for rep in range(per_order)]
    batches = v2.pack(slots, size, seed)
    print(tag, model, "items", len(its), "calls", len(batches))
    if model == "sonnet":
        check_budget("sonnet_gate", len(batches))

    def one(batch):
        body = "".join(v2.render_item(k + 1, it, *((it["his"], it["alt"]) if hf else (it["alt"], it["his"])))
                       for k, (it, hf, _) in enumerate(batch))
        try:
            out = v2.extract_json(call(model, tag, prompt.format(n=len(batch), items=body))) or {}
        except RuntimeError as e:
            print(tag, "failed", e)
            out = {}
        res = []
        for k, (it, hf, rep) in enumerate(batch):
            a = out.get(str(k + 1)) if isinstance(out, dict) else None
            row = {"id": it["id"], "round": it["round"], "model": model, "his_first": hf, "rep": rep, "answer": a}
            if tag == "fair":
                row["fairness"] = None if a not in (0, 1, 2) else (
                    "ok" if a == 0 else ("his_weaker" if (a == 1) == hf else "alt_weaker"))
            else:
                row["picked_his"] = None if a not in (1, 2) else (a == 1) == hf
            res.append(row)
        return res

    return [v for res in pmap(one, batches) for v in res]


def real(model):
    """Realness votes for every latest render that has none from `model` yet."""
    done = {(v["id"], v["round"]) for v in read_jsonl(p("realness.jsonl")) if v.get("model", "haiku") == model}
    rows = [r for r in final_rows() if (r["pair_id"], r["round"]) not in done]
    seed = f"real:{model}:" + ",".join(sorted(str(r["round"]) for r in rows))
    new = vote(model, items(rows), v2.REAL_PROMPT, REAL_PER_ORDER, v2.GATE_BATCH, seed, "real")
    write_jsonl(p("realness.jsonl"), read_jsonl(p("realness.jsonl")) + new)
    shares = [share(votes_by("realness.jsonl", model, r["round"])[r["pair_id"]]) for r in final_rows()]
    shares = [x for x in shares if x is not None]
    print(f"{model}: latest renders with votes {len(shares)}, mean realness {sum(shares) / len(shares):.2f}, "
          f"in band {sum(REAL_BAND[0] <= x <= REAL_BAND[1] for x in shares)}")


def confirm():
    """6 fresh sonnet realness votes for every latest render now in the realness band. Re-rendering
    out-of-band pairs gives each one several draws at the band, so a pair can land there by vote
    noise; the band then rests on 12 votes."""
    rows = [r for r in final_rows()
            if (s := share(votes_by("realness.jsonl", GATE_MODEL, r["round"])[r["pair_id"]])) is not None
            and REAL_BAND[0] <= s <= REAL_BAND[1]]
    new = vote(GATE_MODEL, items(rows), v2.REAL_PROMPT, REAL_PER_ORDER, v2.GATE_BATCH, "real:confirm", "real")
    write_jsonl(p("realness.jsonl"), read_jsonl(p("realness.jsonl")) + [dict(v, confirm=True) for v in new])


def final_rows():
    return list(latest(read_jsonl(p("renders.jsonl"))).values())


def taste(model):
    old = [v for v in read_jsonl(p("taste.jsonl")) if v["model"] != model]
    new = vote(model, items(final_rows()), v2.GATE_PROMPT, TASTE_PER_ORDER, v2.GATE_BATCH, "taste:" + model, "taste")
    write_jsonl(p("taste.jsonl"), old + new)


def fair():
    write_jsonl(p("fairness.jsonl"), vote("haiku", items(final_rows()), v2.FAIR_PROMPT, 1, v2.FAIR_BATCH, "fair", "fair"))


def assemble():
    v2pairs = {x["pair_id"]: x for x in selected()}
    final = latest(read_jsonl(p("renders.jsonl")))
    taste_s, taste_h = votes_by("taste.jsonl", "sonnet"), votes_by("taste.jsonl", "haiku")
    fair_votes = collections.defaultdict(list)
    for v in read_jsonl(p("fairness.jsonl")):
        fair_votes[v["id"]].append(v["fairness"])
    pairs = []
    for pid, x in v2pairs.items():
        r = final[pid]
        hf = his_first(pid)  # a/b order of the deliverable = the rendered order
        real_s = votes_by("realness.jsonl", "sonnet", r["round"])[pid]
        rs, ts, fv = share(real_s), share(taste_s[pid]), fair_votes[pid]
        row = {k: x[k] for k in ("pair_id", "decision_id", "doc", "work", "date", "decision_point", "axis",
                                 "generator", "generator_family", "field_source", "url", "cutoff")}
        row.update(context=r["context"], question=r["question"],
                   a_text=r["his_text"] if hf else r["alt_text"], b_text=r["alt_text"] if hf else r["his_text"],
                   his_side="a" if hf else "b", render_round=r["round"],
                   realness_share=rs, n_realness_votes=len(real_s),
                   realness_haiku_round1=share(votes_by("realness.jsonl", "haiku", 1)[pid]),
                   blind_share=ts, n_votes=len(taste_s[pid]), blind_share_haiku=share(taste_h[pid]),
                   blind_share_v2_haiku=x["blind_share"], fairness_votes=fv,
                   real_band=REAL_BAND[0] <= rs <= REAL_BAND[1], taste_band=TASTE_BAND[0] <= ts <= TASTE_BAND[1],
                   fair=len(fv) == 2 and all(f == "ok" for f in fv))
        row["band"] = row["real_band"] and row["taste_band"] and row["fair"]
        pairs.append(row)
    write_jsonl(p("pairs.jsonl"), pairs)
    band = [x for x in pairs if x["band"]]
    write_jsonl(p("band.jsonl"), band)
    real_ok = [x for x in pairs if x["real_band"]]
    real_taste = [x for x in real_ok if x["taste_band"]]

    def counts(key):
        out = collections.defaultdict(collections.Counter)
        for x in pairs:
            c = out[x[key]]
            c["selected"] += 1
            c["real_band"] += x["real_band"]
            c["sonnet_taste_band"] += x["taste_band"]
            c["real_and_taste"] += x["real_band"] and x["taste_band"]
            c["band"] += x["band"]
        return {k: dict(v) for k, v in out.items()}

    def mean(xs):
        xs = [v for v in xs if v is not None]
        return round(sum(xs) / len(xs), 3) if xs else None

    stats = {
        "funnel": {"selected (v2 haiku blind share in [0.15,0.85])": len(pairs),
                   "rendered clean": len(final),
                   "sonnet realness band [0.3,0.7] (latest render, 12 votes if confirmed)": len(real_ok),
                   "and sonnet taste band [0.25,0.75]": len(real_taste),
                   "and fair (haiku, both orders ok) = band": len(band)},
        "sonnet_taste_band_alone": sum(x["taste_band"] for x in pairs),
        "haiku_taste_band_alone": sum(TASTE_BAND[0] <= x["blind_share_haiku"] <= TASTE_BAND[1] for x in pairs),
        "fair_alone": sum(x["fair"] for x in pairs),
        "real_band_by_render_round": collections.Counter(x["render_round"] for x in real_ok),
        "mean_realness": {"haiku round 1": mean(x["realness_haiku_round1"] for x in pairs),
                          "sonnet latest": mean(x["realness_share"] for x in pairs)},
        "mean_blind_share": {"sonnet": mean(x["blind_share"] for x in pairs),
                             "haiku": mean(x["blind_share_haiku"] for x in pairs),
                             "v2 haiku (pre re-render)": mean(x["blind_share_v2_haiku"] for x in pairs)},
        "sonnet_taste_hist_8votes": collections.Counter(round(x["blind_share"] * 8) for x in pairs),
        "sonnet_realness_by_work": {w: {"date": min(x["date"] for x in pairs if x["work"] == w),
                                        "mean": mean(x["realness_share"] for x in pairs if x["work"] == w)}
                                    for w in sorted({x["work"] for x in pairs})},
        "by_family": counts("generator_family"),
        "by_work": counts("work"),
        "band_works": len({x["work"] for x in band}), "band_decisions": len({x["decision_id"] for x in band}),
        "band_his_side": collections.Counter(x["his_side"] for x in band),
        "calls": {"sonnet render": spent("render"), "sonnet gate": spent("sonnet_gate"),
                  "haiku": v2.real_calls("haiku")},
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in read_jsonl(p("calls.log"))), 2),
    }
    with open(p("stats.json"), "w") as f:
        json.dump(stats, f, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(stats, indent=1, default=str))


if __name__ == "__main__":
    stage, *args = sys.argv[1:]
    {"render": render, "real": real, "confirm": confirm, "taste": taste, "fair": fair, "assemble": assemble}[stage](*args)
