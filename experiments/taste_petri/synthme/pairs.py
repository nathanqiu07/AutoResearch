"""Firewalled PRE-T training pairs for SynthesizeMe (PROTOCOL.md), built with pairs_v4's pipeline.

pairs_v4/build.py is imported read-only for its firewall, prompts and checks; the stage functions here
take a source set ("paper": profiles_contrastive/decisions_pre_t.jsonl, "informal": informal/decisions.jsonl).
The one change from pairs_v4 (PROTOCOL.md): the blind alternatives are rebalanced by direction, one
MORE-cautious and one LESS-cautious stance per decision, both texts fixed below before any generation.
No taste or realness band gating; a 40-pair sonnet realness sample is recorded for diagnostics only.

    python3 pairs.py <source> context|leak|context2|leak2|propose|his|same|pairs|real|split|all
"""
import collections
import importlib.util
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TP = os.path.dirname(HERE)
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("pairs_v4_build", os.path.join(TP, "pairs_v4", "build.py"))
v4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v4)
v2 = v4.v2
# pairs_v2's call wrapper resolves cache/ and calls.log through v2.HERE at call time: point it here.
v2.HERE = HERE
# PROTOCOL.md "Amendment: budget": at most 700 sonnet and 600 haiku for the rest of the run, on top of the
# 1,065 sonnet calls calls.log had started by then (589 answered, 476 refused at the account's usage limit).
SPENT_BEFORE_AMENDMENT = {"sonnet": 1065, "haiku": 0}
v2.CAPS = {"sonnet": SPENT_BEFORE_AMENDMENT["sonnet"] + 700, "haiku": 600}
v2.WORKERS = 2  # the plan is shared (e2_climb runs up to 3 concurrent)
call, read_jsonl, write_jsonl, one_line = v2.call, v2.read_jsonl, v2.write_jsonl, v4.one_line
batches, item_block, firewall, form_rules = v4.batches, v4.item_block, v4.firewall, v4.form_rules

BUILD_CAP = {"paper": 260, "informal": 160}  # sonnet calls per source for steps 1-4 + length fix + realness
SPLIT_SEED, VAL_FRACTION, TARGET = 0, 0.25, 150

# A paper and its blog post, talk or thread are one work (split unit).
WORK_KEYS = [("thought_crime", ["thought_crime", "backdoor_awareness_and_misaligned_personas"]),  # before EM: its name contains it
             ("emergent_misalignment", ["emergent_misalignment_", "deluding_ais", "thread_by_owainevans_uk_researchers_finetuned"]),
             ("forecasting_world_events", ["forecasting_future_world_events", "paper_forecasting_world_events"]),
             ("truthfulqa", ["truthfulqa_measuring", "how_truthful_is_gpt_3", "new_improved_multiple_choice_truthfulqa",
                             "how_do_new_models_from_openai"]),
             ("situational_awareness_ooc", ["taken_out_of_context", "paper_on_measuring_situational_awareness"]),
             ("introspection", ["looking_inward", "llms_can_learn_about_themselves_by_introspection"]),
             ("weird_generalization", ["weird_generalization"]),
             ("truthful_ai", ["truthful_ai_developing", "truthful_and_honest_ai"]),
             ("reward_hacks", ["school_of_reward_hacks", "harmless_reward_hacks"]),
             ("reasoning_faithfulness", ["are_deepseek_r1", "inference_time_compute_more_faithful"])]


def work_of(doc):
    for work, keys in WORK_KEYS:
        if any(k in doc for k in keys):
            return work
    return re.sub(r"_[0-9a-f]{8}\.txt$", "", doc.replace("research__", ""))[:40].rstrip("_")


def bp(source, name):
    return os.path.join(HERE, "build_" + source, name)


def sources(source):
    path = {"paper": os.path.join(TP, "profiles_contrastive", "decisions_pre_t.jsonl"),
            "informal": os.path.join(TP, "informal", "decisions.jsonl")}[source]
    rows = read_jsonl(path)
    if source == "informal":
        rows = [r for r in rows if not informal_drop(r)]
    for r in rows:
        assert r["date"] < v2.T, f"post-T decision {r['decision_id']} in {source}"
        if source == "paper":
            r["work"] = work_of(r["doc"])
        else:  # informal/: one source (podcast, thread, comment, ...) is one work; its text is texts/<source_id>*
            r["doc"], r["work"] = r["source_id"], r["work_id"].rsplit(":", 1)[-1]
    return rows


# Non-AI comments (controller, 2026-11-15): Covid/epidemiology and other off-topic posts, by title. His
# shortform and the untitled comments are all Covid or history; the visual-art post (neural nets as a model
# of art) and the existential-risk forecasting thread are kept as AI-related.
OFF_TOPIC = re.compile(r"covid|delta strain|herd immunity|household|superspreader|excess mortality|chronic fatigue"
                       r"|children and x-risk|thiel on progress|shortform|\(no post title\)", re.IGNORECASE)


def informal_drop(r):
    if r.get("in_paper_set"):
        return "in_paper_set"  # a source the paper set already uses belongs to the paper arm
    if OFF_TOPIC.search(r.get("title", "")):
        return "off_topic"
    return None


def log_informal_drops():
    rows = read_jsonl(os.path.join(TP, "informal", "decisions.jsonl"))
    dropped = [{"decision_id": r["decision_id"], "reason": informal_drop(r), "title": r["title"], "problem": r["problem"]}
               for r in rows if informal_drop(r)]
    os.makedirs(os.path.join(HERE, "build_informal"), exist_ok=True)
    write_jsonl(bp("informal", "dropped.jsonl"), dropped)
    print("informal items", len(rows), "dropped", collections.Counter(d["reason"] for d in dropped), "kept", len(rows) - len(dropped))


def docs(source):
    """doc name -> text: the researcher corpus for papers; informal/sources.jsonl's text file (the whole
    transcript, host turns included) for informal sources."""
    if source == "paper":
        return {k: v[1] for k, v in v2.corpus().items()}
    out = {}
    for s in read_jsonl(os.path.join(TP, "informal", "sources.jsonl")):
        with open(os.path.join(TP, "informal", s["text_path"])) as f:
            out[s["source_id"]] = f.read()
    return out


def spent(source):
    return sum(1 for r in read_jsonl(os.path.join(HERE, "calls.log"))
               if r.get("status") == "started" and r["model"] == "sonnet" and r["tag"].startswith(source + ":"))


def check_budget(source, planned):
    if spent(source) + planned > BUILD_CAP[source]:
        raise RuntimeError(f"{source}: {spent(source)} spent + {planned} planned > cap {BUILD_CAP[source]}")


def all_quotes():
    """Every text the firewall guards, for before_text to cut out of excerpts. Pre-T write-ups often state
    the reason (or the choice) in the text before the quote, which pairs_v4's post-T docs did not."""
    rows = sources("paper") + (sources("informal") if os.path.exists(os.path.join(TP, "informal", "decisions.jsonl")) else [])
    return v4.QUOTES + [d[k] for d in rows for k in ("quote", "did", "stated_reason") if len(v4.norm(d.get(k))) >= 20]


# ---------------------------------------------------------------- 1. problem-only context + leak check

# Informal items come from podcasts, threads, comments and advice. Fixed before any informal generation.
INFORMAL_NOTE = """These items come from talks, interviews, threads, comments and advice, not only from papers. Some are advice the speaker gives or a view he argues for, not a decision his own team made. Write each of those as a decision point a research team faces ("A research team ..."), so that the advice or view is one possible resolution of it; the rules above apply unchanged. The text before the decision may be a transcript or a comment thread: use it only for the situation.

"""


def context(source, round_="1"):
    v4.QUOTES = all_quotes()  # before_text cuts every guarded text out of the excerpt
    text = docs(source)
    src = sources(source)
    path = bp(source, "contexts.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    prev = {r["decision_id"]: r for r in read_jsonl(path)}
    excerpt = {d["decision_id"]: v4.before_text(text.get(d["doc"], ""), d["quote"]) for d in src}
    blocked = set()
    for d in src:  # a guarded text before_text could not cut (quote_span misses some punctuation): drop the decision
        try:
            firewall(excerpt[d["decision_id"]] + " " + d["problem"], src)
        except AssertionError:
            blocked.add(d["decision_id"])
    rows = [d for d in src if d["decision_id"] not in blocked] if round_ == "1" else [
        d for d in src if prev[d["decision_id"]]["status"] == "leak"]
    for did in blocked:
        prev[did] = {"decision_id": did, "status": "firewall_excluded", "round": 1}
    check_budget(source, len(batches(rows)))

    def one(batch):
        body = "".join(f"\n=== key {d['decision_id']}\nKind of decision: {v4.POINTS[d['point']]}\n"
                       f"Problem: {one_line(d['problem'])}\n"
                       f"Write-up text before the decision: {excerpt[d['decision_id']]}\n"
                       + ("" if round_ == "1" else f"Previous context: {prev[d['decision_id']]['context']}\n"
                          f"Previous question: {prev[d['decision_id']]['question']}\n")
                       for d in batch)
        prompt = (v4.CONTEXT_PROMPT.replace("ITEMS:\n", (INFORMAL_NOTE if source == "informal" else "") + "ITEMS:\n")
                  + ("" if round_ == "1" else v4.REVISE_NOTE) + body)
        firewall(prompt, batch)
        return v2.objects_with(call("sonnet", f"{source}:ctx{round_}", prompt), "key")

    got = {str(o.get("key")): o for objs in v2.pmap(one, batches(rows)) for o in objs}
    for d in rows:
        g = got.get(d["decision_id"]) or {}
        prev[d["decision_id"]] = {
            "decision_id": d["decision_id"], "work": d["work"], "point": d["point"], "round": int(round_),
            "status": "no output" if not g.get("context") and not g.get("skip") else ("skip" if g.get("skip") else "ok"),
            "context": one_line(g.get("context")), "question": one_line(g.get("question")),
            "previous": prev.get(d["decision_id"]) if round_ != "1" else None}
    write_jsonl(path, [prev[d["decision_id"]] for d in src if d["decision_id"] in prev])
    print(collections.Counter(r["status"] for r in prev.values()))


def leak(source):
    src = {d["decision_id"]: d for d in sources(source)}
    path = bp(source, "contexts.jsonl")
    rows = read_jsonl(path)
    ok = [r for r in rows if r["status"] == "ok" and "llm_leak" not in r]
    for r in ok:
        d = src[r["decision_id"]]
        shared = v4.trigrams(d["did"]) & v4.trigrams(r["context"] + " " + r["question"]) - v4.trigrams(d["problem"])
        r["string_leak"] = sorted(" ".join(t) for t in shared)
    check_budget(source, len(batches(ok, 20)))

    def one(batch):
        body = "".join(f"\n=== key {r['decision_id']}\nContext: {r['context']}\nQuestion: {r['question']}\n"
                       f"What the team decided: {one_line(src[r['decision_id']]['did'])}\n" for r in batch)
        return v2.objects_with(call("sonnet", f"{source}:leak", v4.LEAK_PROMPT + body), "key")

    got = {str(o.get("key")): o for objs in v2.pmap(one, batches(ok, 20)) for o in objs}
    for r in ok:
        g = got.get(r["decision_id"]) or {}
        r["llm_leak"] = {"yes": True, "no": False}.get(str(g.get("reveals")).lower())
        r["leak_why"] = g.get("why")
        r["status"] = "leak" if r["string_leak"] or r["llm_leak"] is not False else "ok"
    by = {r["decision_id"]: r for r in ok}
    write_jsonl(path, [by.get(r["decision_id"], r) for r in rows])
    print("string leaks", sum(bool(r["string_leak"]) for r in ok), "llm leaks", sum(r["llm_leak"] is True for r in ok),
          "kept", sum(r["status"] == "ok" for r in ok))


# ---------------------------------------------------------------- 2. blind proposals, rebalanced by direction

# Fixed before any generation (PROTOCOL.md): one more-cautious and one less-cautious stance per decision,
# the same two texts for every decision. Neither stance ever sees his choice (firewall-asserted).
STANCE_TASK = """For each item write two resolutions from two stances. The stances are fixed in advance and are the same for every item:
- "more_cautious": how a researcher who is MORE cautious than a typical strong researcher would resolve this decision: the option that adds the extra control, check or comparison, narrows the scope or the claim, or gathers more evidence before committing.
- "less_cautious": how a researcher who is LESS cautious than a typical strong researcher would resolve this decision: the option that commits to a clear direction, test or claim with what the team already has, takes the simpler or more ambitious route, and skips extra controls, checks or caveats.
The two must be genuinely different decisions from each other.

"""
STANCE_RULES = """Rules for every resolution:
- It answers the question directly with one concrete decision a strong researcher could defend in a lab meeting, feasible for a small team. Not a list of everything ("do X and also Y and Z"), not a strawman, not an overclaim.
- It uses the context's own terms where it refers to the setup; any detail beyond them is a plain description, not an invented name.
- Form: {rules}.

Return only JSON: {{"items": [{{"key": str, {fields}}}]}}

ITEMS:
"""
STANCES = ("more_cautious", "less_cautious")


def propose(source):
    src = {d["decision_id"]: d for d in sources(source)}
    ok = [r for r in read_jsonl(bp(source, "contexts.jsonl")) if r["status"] == "ok"]
    bs = batches(ok)
    check_budget(source, len(bs))

    def one(batch):
        prompt = (v4.PROPOSE_HEAD + STANCE_TASK + STANCE_RULES.format(
            rules=form_rules(), fields='"more_cautious": str, "less_cautious": str') + "".join(item_block(r) for r in batch))
        firewall(prompt, [src[r["decision_id"]] for r in batch])
        return v2.objects_with(call("sonnet", f"{source}:propose", prompt), "key")

    got = {str(o.get("key")): o for objs in v2.pmap(one, bs) for o in objs}
    out = [{"decision_id": r["decision_id"],
            "proposals": [{"generator": f, "text": one_line(got[r["decision_id"]][f])} for f in STANCES
                          if isinstance(got.get(r["decision_id"], {}).get(f), str) and len(got[r["decision_id"]][f]) > 40]}
           for r in ok]
    write_jsonl(bp(source, "proposals.jsonl"), out)
    print("decisions", len(out), "proposals", sum(len(r["proposals"]) for r in out),
          collections.Counter(len(r["proposals"]) for r in out))


# ---------------------------------------------------------------- 3. his option + 4. same/different

def his(source):
    src = {d["decision_id"]: d for d in sources(source)}
    ctx = {r["decision_id"]: r for r in read_jsonl(bp(source, "contexts.jsonl"))}
    props = [r for r in read_jsonl(bp(source, "proposals.jsonl")) if len(r["proposals"]) == 2]
    bs = batches(props)
    check_budget(source, len(bs))

    def one(batch):
        body, used = "", {}
        for k, r in enumerate(batch):
            d = src[r["decision_id"]]
            other = batch[(k + 1) % len(batch)] if len(batch) > 1 else props[(props.index(r) + 1) % len(props)]
            # the style example alternates between the two stances so neither direction sets his form
            ex = other["proposals"][k % 2]
            used[r["decision_id"]] = [other["decision_id"], ex["generator"]]
            body += (item_block(ctx[r["decision_id"]]) + f"What the team decided: {one_line(d['did'])}\n"
                     f"Quote: {one_line(d['quote'])}\nStyle example (different decision): {ex['text']}\n")
        objs = v2.objects_with(call("sonnet", f"{source}:his", v4.HIS_PROMPT.format(rules=form_rules()) + body), "key")
        return [dict(o, style_from=used.get(str(o.get("key")))) for o in objs]

    got = {str(o.get("key")): o for objs in v2.pmap(one, bs) for o in objs}
    out = [{"decision_id": r["decision_id"], "his_text": one_line(got[r["decision_id"]].get("option")),
            "style_from": got[r["decision_id"]]["style_from"]}
           for r in props if got.get(r["decision_id"], {}).get("option")]
    write_jsonl(bp(source, "his.jsonl"), out)
    print("his options", len(out), "of", len(props))


def same(source):
    src = {d["decision_id"]: d for d in sources(source)}
    hs = {r["decision_id"]: r for r in read_jsonl(bp(source, "his.jsonl"))}
    props = [r for r in read_jsonl(bp(source, "proposals.jsonl")) if r["decision_id"] in hs]
    bs = batches(props, 12)
    check_budget(source, len(bs))

    def one(batch):
        body = "".join(f"\n=== key {r['decision_id']}\nWhat the team decided: {one_line(src[r['decision_id']]['did'])}\n"
                       f"Restatement: {hs[r['decision_id']]['his_text']}\n"
                       + "".join(f"C{i + 1}: {x['text']}\n" for i, x in enumerate(r["proposals"])) for r in batch)
        return v2.objects_with(call("sonnet", f"{source}:same", v4.SAME_PROMPT + body), "key")

    got = {str(o.get("key")): o for objs in v2.pmap(one, bs) for o in objs}
    out = []
    for r in props:
        g = got.get(r["decision_id"]) or {}
        verdicts = g.get("same") or {}
        out.append({"decision_id": r["decision_id"], "faithful": str(g.get("faithful")).lower(),
                    "same": {x["generator"]: str(verdicts.get(f"C{i + 1}")).lower() for i, x in enumerate(r["proposals"])}})
    write_jsonl(bp(source, "same.jsonl"), out)
    print("faithful", collections.Counter(r["faithful"] for r in out),
          "proposals", collections.Counter(v for r in out for v in r["same"].values()))


# ---------------------------------------------------------------- pairs, length fix, realness sample

def his_side(pair_id):
    return "a" if random.Random("synthme:" + pair_id).random() < 0.5 else "b"


def pairs(source):
    """his vs each stance judged different. A decision keeps its pairs only when BOTH stances are
    different from his and pass the form checks, so every decision contributes one more-cautious and
    one less-cautious pair (direction balance holds in the final set, not only in generation)."""
    src = {d["decision_id"]: d for d in sources(source)}
    ctx = {r["decision_id"]: r for r in read_jsonl(bp(source, "contexts.jsonl"))}
    hs = {r["decision_id"]: r for r in read_jsonl(bp(source, "his.jsonl"))}
    sm = {r["decision_id"]: r for r in read_jsonl(bp(source, "same.jsonl"))}
    names, extra = v2.banned()
    # pairs_v2's name pattern has no closing word boundary, so "METR" matches every "metric"
    checks = (v4.titles(), names, re.compile(extra.pattern.replace("|METR|", "|METR\\b|"), extra.flags))
    rows = []
    for r in read_jsonl(bp(source, "proposals.jsonl")):
        did = r["decision_id"]
        if did not in hs or sm.get(did, {}).get("faithful") != "yes":
            continue
        for x in r["proposals"]:
            if sm[did]["same"].get(x["generator"]) != "different":
                continue
            rows.append({"pair_id": v2.digest([v2.SLUG, "synthme", source, did, x["generator"]])[:12],
                         "decision_id": did, "work": src[did]["work"], "doc": src[did]["doc"], "date": src[did]["date"],
                         "point": src[did]["point"], "generator": x["generator"],
                         "context": v4.plain_terms(ctx[did]["context"]), "question": v4.plain_terms(ctx[did]["question"]),
                         "his_text": v4.plain_terms(hs[did]["his_text"]), "alt_text": v4.plain_terms(x["text"]),
                         "alt_text_original": x["text"], "stated_reason": src[did].get("stated_reason", "")})
    for r in rows:
        r["problems"] = v4.problems(r["context"], r["his_text"], r["alt_text"], checks)
    # The fixer sees only the proposal and a target length, never his option.
    fix = [r for r in rows if r["problems"] in (["the two options differ in length by more than 15%"],
                                                ["the two options differ in length by more than 20%"])]
    if fix:
        check_budget(source, len(batches(fix, 25)))

        def one(batch):
            body = "".join(f"\n=== key {r['pair_id']}\nTarget: {round(len(r['his_text']) * 0.95)}-"
                           f"{round(len(r['his_text']) * 1.05)} characters\nSentence: {r['alt_text']}\n" for r in batch)
            return v2.objects_with(call("sonnet", f"{source}:lenfix", v4.FIX_PROMPT + body), "key")

        got = {str(o.get("key")): o for objs in v2.pmap(one, batches(fix, 25)) for o in objs}
        for r in fix:
            t = one_line((got.get(r["pair_id"]) or {}).get("text"))
            if t:
                r["alt_text"], r["length_fixed"] = t, True
                r["problems"] = v4.problems(r["context"], r["his_text"], t, checks)
    clean = collections.defaultdict(list)
    for r in rows:
        if not r["problems"]:
            clean[r["decision_id"]].append(r)
    balanced = [r for did in clean if len(clean[did]) == 2 for r in clean[did]]
    for r in balanced:
        side = his_side(r["pair_id"])
        r.update(his_side=side, a_text=r["his_text"] if side == "a" else r["alt_text"],
                 b_text=r["alt_text"] if side == "a" else r["his_text"])
    write_jsonl(bp(source, "pairs_raw.jsonl"), rows)
    write_jsonl(os.path.join(HERE, f"pairs_{source}.jsonl"), balanced)
    print("pairs", len(rows), "clean", sum(not r["problems"] for r in rows),
          "length-fixed", sum(bool(r.get("length_fixed")) for r in rows),
          "balanced pairs", len(balanced), "decisions", len(balanced) // 2, "works", len({r["work"] for r in balanced}),
          collections.Counter(x for r in rows for x in r["problems"]).most_common(6))


def real(source, n=40):
    """Diagnostic only: sonnet realness on a fixed 40-pair sample, one vote per order."""
    rows = read_jsonl(os.path.join(HERE, f"pairs_{source}.jsonl"))
    sample = random.Random("synthme:real").sample(rows, min(n, len(rows)))
    its = v4.items(sample)
    slots = [(it, hf, 0) for it in its for hf in (True, False)]
    check_budget(source, len(v2.pack(slots, v4.GATE_BATCH, "real")))
    votes = v4.vote("sonnet", its, v2.REAL_PROMPT, range(1), v4.GATE_BATCH, "real", f"{source}:real")
    write_jsonl(bp(source, "realness.jsonl"), votes)
    got = [v["picked_his"] for v in votes if v["picked_his"] is not None]
    print("realness share (his picked as real)", round(sum(got) / len(got), 3), "votes", len(got))


def split(source):
    """Whole works to validation (seeded shuffle) until it holds >= 25% of the pairs."""
    rows = read_jsonl(os.path.join(HERE, f"pairs_{source}.jsonl"))
    by_work = collections.Counter(r["work"] for r in rows)
    works = sorted(by_work)
    random.Random(SPLIT_SEED).shuffle(works)
    val, n = [], 0
    for w in works:
        if n >= VAL_FRACTION * len(rows):
            break
        val.append(w)
        n += by_work[w]
    path = os.path.join(HERE, "split.json")
    out = json.load(open(path)) if os.path.exists(path) else {}
    out[source] = {"seed": SPLIT_SEED, "val_works": sorted(val), "train_works": sorted(set(works) - set(val)),
                   "n_train": len(rows) - n, "n_val": n,
                   "train_ids": [r["pair_id"] for r in rows if r["work"] not in val],
                   "val_ids": [r["pair_id"] for r in rows if r["work"] in val]}
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(source, "train", len(rows) - n, "val", n, "val works", sorted(val))


STAGES = {"drops": lambda s: log_informal_drops(), "context": context, "leak": leak, "context2": lambda s: context(s, "2"), "leak2": leak,
          "propose": propose, "his": his, "same": same, "pairs": pairs, "real": real, "split": split}

if __name__ == "__main__":
    source, *stages = sys.argv[1:]
    for st in (["context", "leak", "context2", "leak2", "propose", "his", "same", "pairs", "real", "split"]
               if stages == ["all"] else stages):
        print("==", source, st, flush=True)
        STAGES[st](source)
