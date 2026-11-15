"""pairs_v4: held-out pairs for Owain Evans with a BLIND-CONTEXT pipeline.

pairs_v3 showed the realness tell lives in the context: pairs_v2's generator wrote it knowing his
choice, so it listed exactly what his option used and framed the question so only his option
answered it. Here an information firewall keeps his choice away from every step that writes the
context or the alternatives (asserted in code: neither `did` nor the quote may occur in those prompts).

Stages (each resumable through the prompt-hash call cache; pairs_v2 is imported read-only):
  context   sonnet, PROBLEM-ONLY: the decision's `problem` field + the doc text BEFORE the quote
            -> neutral context + open question, outcome omitted                 -> contexts.jsonl
  leak      string check + sonnet yes/no "does the context reveal the choice?"; drop if either fires
  propose   sonnet, BLIND: from context+question only, 3 resolutions: two peer cards (rotated over the
            8 non-Owain peers) in one call, a plain strong researcher (no card) in another -> proposals.jsonl
  his       sonnet renders his `did` (+ verified quote) into the same template, seeing context + did +
            one style example taken from a DIFFERENT decision's blind proposal  -> his.jsonl
  same      sonnet judge: rendering faithful to `did`? each proposal same/different decision? -> same.jsonl
  pairs     his vs each different proposal; form checks; blind length fix of the proposal -> pairs_raw.jsonl
  real      sonnet realness gate, 3 per order                                    -> realness.jsonl
  taste     sonnet taste gate, 3 per order                                       -> taste.jsonl
  confirm   3 more per order of both gates for pairs in both bands (band then rests on 12+12 votes)
  fair      haiku fairness, both orders                                          -> fairness.jsonl
  assemble  pairs.jsonl, band.jsonl, stats.json

    python3 experiments/taste_petri/pairs_v4/build.py <stage>
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
# WORKERS at call time; pointed here they write only inside pairs_v4.
v2.HERE = HERE
v2.CAPS = {"sonnet": 510, "haiku": 100}  # hard stop; per-purpose caps below
v2.WORKERS = 3  # other agents share the plan
call, p, pmap, read_jsonl, write_jsonl = v2.call, v2.p, v2.pmap, v2.read_jsonl, v2.write_jsonl
CAPS = {"build": 110, "gate": 400}
GATE_TAGS = ("real", "taste")

REAL_BAND, TASTE_BAND = (0.3, 0.7), v2.BAND
PER_ORDER = 3
GATE_BATCH, FAIR_BATCH = 10, 10
BATCH = 8
LEN_LO, LEN_HI, MAX_RATIO = 155, 180, 1.15
POINTS = {"D1": "which experiment or hypothesis to pursue", "D2": "what evidence to collect",
          "D3": "whether to accept a result", "D4": "whether to continue or drop a line of work",
          "D5": "how to interpret an ambiguous result", "D6": "how strongly to state a claim"}


def spent(purpose):
    rows = [r for r in read_jsonl(p("calls.log")) if r.get("status") == "started" and r["model"] == "sonnet"]
    return sum(r["tag"].startswith(GATE_TAGS) == (purpose == "gate") for r in rows)


def check_budget(purpose, planned):
    if spent(purpose) + planned > CAPS[purpose]:
        raise RuntimeError(f"{purpose}: {spent(purpose)} spent + {planned} planned > cap {CAPS[purpose]}")


def batches(xs, n=BATCH):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def sources():
    return read_jsonl(os.path.join(V2_DIR, "sources.jsonl"))


def norm(s):
    return v2.timesplit.normalize_for_quote(str(s or ""))


def firewall(prompt, decisions):
    """No prompt that writes a context or an alternative may contain his choice or its quote."""
    n = norm(prompt)
    for d in decisions:
        for k in ("did", "quote", "stated_reason"):
            if len(norm(d.get(k))) >= 20 and norm(d.get(k)) in n:
                raise AssertionError(f"firewall: {k} of {d['decision_id']} is in a blind prompt")


QUOTES = [d["quote"] for d in sources()]


def one_line(s):
    return " ".join(str(s or "").split())


def form_rules():
    return (f"exactly one sentence; imperative, present tense (\"Run ...\", \"Report ...\", \"Treat ...\"); "
            f"between {LEN_LO} and {LEN_HI} characters; no digits (write any number in words); no first person "
            f"(we, our, us, I, my, me); no names of people, labs, papers, models or datasets; no coined name for "
            f"the phenomenon; no justification clause and no hedging")


# ---------------------------------------------------------------- 1. problem-only context


def quote_span(text, quote):
    """(start, end) of the quote in text, matching across whitespace, hyphen breaks and curly quotes."""
    words = norm(quote).split()
    pat = r"[\s\-]*".join(re.escape(w) if w.isascii() else r"\S+" for w in words)  # NFKC splits e.g. "Section˜2"
    m = re.search(pat, text.translate(v2.timesplit._QUOTES).lower())
    return m.span() if m else None


def before_text(text, quote, chars=1600):
    """Doc text ending just before the quote (the decision), with every decision's verified quote cut
    out (an earlier decision of the same doc would otherwise reach the blind writer verbatim) and
    without lines that name Hobbhahn."""
    span = quote_span(text, quote)
    pos = span[0] if span else 0
    excerpt = text[max(0, pos - chars): pos]
    for q in QUOTES:
        while (s := quote_span(excerpt, q)):
            excerpt = excerpt[:s[0]] + " [...] " + excerpt[s[1]:]
    return one_line(" ".join(ln for ln in excerpt.splitlines() if "obbhahn" not in ln.lower()))


CONTEXT_PROMPT = """Each item below is a decision point in an AI-safety research project. You get the kind of decision, a short statement of the problem the team faced, and the text of their write-up that comes BEFORE the decision. You do not see what they decided, and you must not guess it.

For each item write the decision point as a researcher would have faced it, BEFORE choosing:
- "context": 2-4 sentences, neutral third person ("A research team ..."). The setting, what they were studying, and what they knew at that moment; for a decision about interpreting, accepting or stating a result, the result itself. Give the facts that any reasonable option would need. The excerpt may already announce or describe what the team chose (papers often state their choices before explaining them): leave all of that out. Do not list candidate options, do not mention methods or elements the team adopted as part of this decision, and do not say anything learned after it.
- "question": one short open question naming the decision, answerable in several different ways, e.g. "How should the team test whether the effect depends on the clean data?" It must not suggest an answer.
- "skip": true if the decision cannot be posed without stating its outcome, or is not a real choice (pure description). Otherwise false.
No names of people, labs, organisations, papers, models or datasets; no coined name for the phenomenon (describe it in plain words). Numbers are fine.

Return only JSON: {"items": [{"key": str, "skip": bool, "context": str, "question": str}]}

ITEMS:
"""


# The revision tells the writer only that the context steered; the leak judge's reason names the
# choice, so it never reaches the writer.
REVISE_NOTE = """
This is a revision. Each item also shows your previous context and question. Readers who knew what the team decided found that this version steers toward one particular resolution: it states or implies it, mentions elements that only one resolution would use, or frames the question so that one resolution is the obvious answer. You are still not told the decision. Rewrite the context and question so that several genuinely different resolutions answer the question equally directly: keep the facts any option needs, present facts that cut different ways neutrally, drop details that only matter to one particular resolution, and invent nothing.
"""


def context(round_="1"):
    """Round 1 writes every context; round 2 rewrites, once, the ones the leak check flagged."""
    docs = v2.corpus()
    src = sources()
    prev = {r["decision_id"]: r for r in read_jsonl(p("contexts.jsonl"))}
    rows = src if round_ == "1" else [d for d in src if prev[d["decision_id"]]["status"] == "leak"]
    check_budget("build", len(batches(rows)))

    def one(batch):
        body = "".join(f"\n=== key {d['decision_id']}\nKind of decision: {POINTS[d['point']]}\n"
                       f"Problem: {one_line(d['problem'])}\n"
                       f"Write-up text before the decision: {before_text(docs[d['doc']][1], d['quote'])}\n"
                       + ("" if round_ == "1" else f"Previous context: {prev[d['decision_id']]['context']}\n"
                          f"Previous question: {prev[d['decision_id']]['question']}\n")
                       for d in batch)
        prompt = CONTEXT_PROMPT + ("" if round_ == "1" else REVISE_NOTE) + body
        firewall(prompt, batch)
        return v2.objects_with(call("sonnet", "ctx" + round_, prompt), "key")

    got = {str(o.get("key")): o for objs in pmap(one, batches(rows)) for o in objs}
    for d in rows:
        g = got.get(d["decision_id"]) or {}
        prev[d["decision_id"]] = {
            "decision_id": d["decision_id"], "work": d["work"], "point": d["point"], "round": int(round_),
            "status": "no output" if not g.get("context") and not g.get("skip") else ("skip" if g.get("skip") else "ok"),
            "context": one_line(g.get("context")), "question": one_line(g.get("question")),
            "previous": prev.get(d["decision_id"]) if round_ != "1" else None}
    write_jsonl(p("contexts.jsonl"), [prev[d["decision_id"]] for d in src])
    print(collections.Counter(r["status"] for r in prev.values()))


# ---------------------------------------------------------------- 1b. leak check


def trigrams(text):
    t = v2.tokens(text)
    return {tuple(t[i:i + 3]) for i in range(len(t) - 2)}


LEAK_PROMPT = """Each item below shows a context and question that readers will see, and then what the research team actually decided. For each item, answer "yes" if a reader of the context and question alone could tell, or would be steered toward, what the team decided: the context states or implies the decision, lists exactly the elements the decision uses, or frames the question so that this decision is the obvious or only direct answer. Answer "no" if the context poses the decision openly, so that several genuinely different resolutions would answer it equally directly.

Return only JSON: {"items": [{"key": str, "reveals": "yes" | "no", "why": str (under 15 words)}]}

ITEMS:
"""


def leak():
    src = {d["decision_id"]: d for d in sources()}
    rows = read_jsonl(p("contexts.jsonl"))
    ok = [r for r in rows if r["status"] == "ok" and "llm_leak" not in r]  # checked rows keep their verdict
    for r in ok:
        d = src[r["decision_id"]]
        shared = trigrams(d["did"]) & trigrams(r["context"] + " " + r["question"]) - trigrams(d["problem"])
        r["string_leak"] = sorted(" ".join(t) for t in shared)
    check_budget("build", len(batches(ok, 20)))

    def one(batch):
        body = "".join(f"\n=== key {r['decision_id']}\nContext: {r['context']}\nQuestion: {r['question']}\n"
                       f"What the team decided: {one_line(src[r['decision_id']]['did'])}\n" for r in batch)
        return v2.objects_with(call("sonnet", "leak", LEAK_PROMPT + body), "key")

    got = {str(o.get("key")): o for objs in pmap(one, batches(ok, 20)) for o in objs}
    for r in ok:
        g = got.get(r["decision_id"]) or {}
        r["llm_leak"] = {"yes": True, "no": False}.get(str(g.get("reveals")).lower())
        r["leak_why"] = g.get("why")
        r["status"] = ("leak" if r["string_leak"] or r["llm_leak"] is not False else "ok")
    by = {r["decision_id"]: r for r in ok}
    write_jsonl(p("contexts.jsonl"), [by.get(r["decision_id"], r) for r in rows])
    print("string leaks", sum(bool(r["string_leak"]) for r in ok), "llm leaks", sum(r["llm_leak"] is True for r in ok),
          "llm unparsed", sum(r["llm_leak"] is None for r in ok), "kept", sum(r["status"] == "ok" for r in ok))


# ---------------------------------------------------------------- 2. blind proposals

PROPOSE_HEAD = """You are helping build a test of research taste. Each item below is a decision point an AI-safety research team faced: the context and the open question. You are not told what the team did.

"""
PEER_TASK = """For each item write two resolutions: "peer_A", how a strong researcher with the priorities in CARD A would resolve this decision, and "peer_B", the same for CARD B. The cards were written for another task (designing evaluation scenarios); use them only to infer each researcher's general research priorities, and do not copy their phrasing. The two resolutions must be genuinely different decisions from each other.

CARD A:
{card_a}

CARD B:
{card_b}

"""
PLAIN_TASK = """For each item write "plain": how a strong, experienced AI-safety researcher would resolve this decision.

"""
PROPOSE_RULES = """Rules for every resolution:
- It answers the question directly with one concrete decision a strong researcher could defend in a lab meeting, feasible for a small team. Not a list of everything ("do X and also Y and Z"), not a strawman, not an overclaim, and not more cautious than the situation needs.
- It uses the context's own terms where it refers to the setup; any detail beyond them is a plain description, not an invented name.
- Form: {rules}.

Return only JSON: {{"items": [{{"key": str, {fields}}}]}}

ITEMS:
"""


def item_block(r):
    return f"\n=== key {r['decision_id']}\nContext: {r['context']}\nQuestion: {r['question']}\n"


def propose():
    src = {d["decision_id"]: d for d in sources()}
    ok = [r for r in read_jsonl(p("contexts.jsonl")) if r["status"] == "ok"]
    bs = batches(ok)
    check_budget("build", 2 * len(bs))
    jobs = []
    for b, batch in enumerate(bs):
        a, c = v2.PEERS[(2 * b) % 8], v2.PEERS[(2 * b + 1) % 8]
        body = "".join(item_block(r) for r in batch)
        peer = (PROPOSE_HEAD + PEER_TASK.format(card_a=v2.peer_card(a), card_b=v2.peer_card(c))
                + PROPOSE_RULES.format(rules=form_rules(), fields='"peer_A": str, "peer_B": str') + body)
        plain = PROPOSE_HEAD + PLAIN_TASK + PROPOSE_RULES.format(rules=form_rules(), fields='"plain": str') + body
        for prompt, kind in ((peer, ("peer:" + a, "peer:" + c)), (plain, ("plain",))):
            firewall(prompt, [src[r["decision_id"]] for r in batch])
            jobs.append((prompt, kind))

    def one(job):
        prompt, kind = job
        return kind, v2.objects_with(call("sonnet", "propose", prompt), "key")

    props = collections.defaultdict(list)
    for kind, objs in pmap(one, jobs):
        fields = ("peer_A", "peer_B") if len(kind) == 2 else ("plain",)
        for o in objs:
            for f, gen in zip(fields, kind):
                if isinstance(o.get(f), str) and len(o[f]) > 40:
                    props[str(o.get("key"))].append({"generator": gen, "text": one_line(o[f])})
    out = [{"decision_id": r["decision_id"], "proposals": props.get(r["decision_id"], [])} for r in ok]
    write_jsonl(p("proposals.jsonl"), out)
    print("decisions", len(out), "proposals", sum(len(r["proposals"]) for r in out),
          collections.Counter(len(r["proposals"]) for r in out))


# Amendment after the first sonnet gates (before any pragmatic/assertive output was seen): blind
# proposals from a strong-researcher stance came out more rigorous and more hedged than real
# decisions, and sonnet preferred them 0.88 of the time. Two more stances, fixed in advance and the
# same for every decision, still never see his choice.
STANCE_TASK = """For each item write two resolutions from two different stances:
- "pragmatic": how a busy, experienced researcher writing up a paper on a deadline would actually resolve this: the simplest decision that settles the question well enough with what the team already has. Not sloppy, but no extra controls, analyses or caveats beyond what a careful reviewer would require.
- "assertive": how a researcher confident in the work and keen to give the field a clear takeaway would resolve this: the decision that commits to a clear direction, test or claim the evidence can support, without hedging beyond what the evidence requires.
The two must be genuinely different decisions from each other.

"""


def propose2():
    src = {d["decision_id"]: d for d in sources()}
    faithful = {r["decision_id"] for r in read_jsonl(p("same.jsonl")) if r["faithful"] == "yes"}
    ctx = {r["decision_id"]: r for r in read_jsonl(p("contexts.jsonl"))}
    rows = read_jsonl(p("proposals.jsonl"))
    todo = [ctx[r["decision_id"]] for r in rows if r["decision_id"] in faithful
            and not any(x["generator"] in ("pragmatic", "assertive") for x in r["proposals"])]
    bs = batches(todo)
    check_budget("build", len(bs))

    def one(batch):
        prompt = (PROPOSE_HEAD + STANCE_TASK + PROPOSE_RULES.format(
            rules=form_rules(), fields='"pragmatic": str, "assertive": str') + "".join(item_block(r) for r in batch))
        firewall(prompt, [src[r["decision_id"]] for r in batch])
        return v2.objects_with(call("sonnet", "propose2", prompt), "key")

    got = {str(o.get("key")): o for objs in pmap(one, bs) for o in objs}
    for r in rows:
        g = got.get(r["decision_id"]) or {}
        r["proposals"] += [{"generator": f, "text": one_line(g[f])} for f in ("pragmatic", "assertive")
                           if isinstance(g.get(f), str) and len(g[f]) > 40]
    write_jsonl(p("proposals.jsonl"), rows)
    print("decisions", len(todo), "new proposals", sum(f in g for g in got.values() for f in ("pragmatic", "assertive")))


# ---------------------------------------------------------------- 3. his option

HIS_PROMPT = """Each item below is a decision point from an AI-safety research project (context and question), followed by what the team actually decided and a verbatim quote from their write-up. Restate the team's decision as one option in a multiple-choice item. The other options were written separately in a fixed form; the style example shows that form (it belongs to a DIFFERENT decision, so take only its form and level of detail from it, never its content).

Rules:
- Faithful: the same decision the team took, its core choice, nothing added. If the decision has several parts, keep the part that answers the question.
- Same level of abstraction as the context: refer to the setup in the context's own terms, and turn study-specific details the context does not mention (model names, dataset names, exact numbers, coined terms, odd specifics) into plain descriptions.
- Do not make it sound more careful, expert, idiosyncratic or polished than the style example, and add no reason for it.
- Form: {rules}.

Return only JSON: {{"items": [{{"key": str, "option": str}}]}}

ITEMS:
"""


def his():
    src = {d["decision_id"]: d for d in sources()}
    ctx = {r["decision_id"]: r for r in read_jsonl(p("contexts.jsonl"))}
    props = [r for r in read_jsonl(p("proposals.jsonl")) if r["proposals"]]
    bs = batches(props)
    check_budget("build", len(bs))

    def style_example(batch, k):
        other = batch[(k + 1) % len(batch)] if len(batch) > 1 else props[(props.index(batch[0]) + 1) % len(props)]
        plain = [x for x in other["proposals"] if x["generator"] == "plain"] or other["proposals"]
        return other["decision_id"], plain[0]["text"]

    def one(batch):
        body, used = "", {}
        for k, r in enumerate(batch):
            d, c = src[r["decision_id"]], ctx[r["decision_id"]]
            sid, ex = style_example(batch, k)
            used[r["decision_id"]] = sid
            body += (item_block(c) + f"What the team decided: {one_line(d['did'])}\n"
                     f"Quote: {one_line(d['quote'])}\nStyle example (different decision): {ex}\n")
        objs = v2.objects_with(call("sonnet", "his", HIS_PROMPT.format(rules=form_rules()) + body), "key")
        return [dict(o, style_from=used.get(str(o.get("key")))) for o in objs]

    got = {str(o.get("key")): o for objs in pmap(one, bs) for o in objs}
    out = [{"decision_id": r["decision_id"], "his_text": one_line(got[r["decision_id"]].get("option")),
            "style_from": got[r["decision_id"]]["style_from"]}
           for r in props if got.get(r["decision_id"], {}).get("option")]
    write_jsonl(p("his.jsonl"), out)
    print("his options", len(out), "of", len(props))


# Amendment after both gates on all pairs: where sonnet gives his option any taste votes it almost
# always also names it the real one, and his rendering keeps paper-like specifics. Rule fixed before
# re-rendering: every pair with taste share >= 1/6 and realness >= 5/6 gets his option re-rendered
# plainer (the renderer still sees only context, did, quote and its previous restatement, never the
# alternatives) and is re-gated as a new pair; the old pair is superseded.
HIS2_NOTE = """
This is a revision. Each item also shows your previous restatement. Blind readers could still tell it came from the actual write-up: it carries paper-like specifics (exact numbers, idiosyncratic details, named procedures). Restate the same decision more plainly, at the level of detail of the style example: keep the core choice, drop exact numbers and study-specific particulars that the context does not need.
"""
FAITH_PROMPT = """Each item below gives what a research team actually decided and a one-sentence restatement. Answer "yes" if the restatement describes the same decision (abstracting away study-specific details is fine), "no" if it changes, drops the core of, or adds to the decision.

Return only JSON: {"items": [{"key": str, "faithful": "yes" | "no"}]}

ITEMS:
"""


def his2_targets():
    return [x for x in read_jsonl(p("pairs.jsonl")) if x.get("his_round", 1) == 1
            and x["blind_share"] >= 1 / 6 - 1e-9 and x["realness_share"] >= 5 / 6 - 1e-9]


def his2():
    src = {d["decision_id"]: d for d in sources()}
    ctx = {r["decision_id"]: r for r in read_jsonl(p("contexts.jsonl"))}
    h1 = {r["decision_id"]: r for r in read_jsonl(p("his.jsonl"))}
    props = {r["decision_id"]: r for r in read_jsonl(p("proposals.jsonl"))}
    targets = his2_targets()
    dids = sorted({x["decision_id"] for x in targets})
    bs = batches(dids)
    check_budget("build", len(bs) + len(batches(dids, 30)))

    def one(batch):
        body = ""
        for did in batch:
            d, prev = src[did], h1[did]
            ex = next(x["text"] for x in props[prev["style_from"]]["proposals"] if x["generator"] == "plain")
            body += (item_block(ctx[did]) + f"What the team decided: {one_line(d['did'])}\nQuote: {one_line(d['quote'])}\n"
                     f"Previous restatement: {prev['his_text']}\nStyle example (different decision): {ex}\n")
        return v2.objects_with(call("sonnet", "his2", HIS_PROMPT.format(rules=form_rules()) + HIS2_NOTE + body), "key")

    got = {str(o.get("key")): one_line(o.get("option")) for objs in pmap(one, bs) for o in objs if o.get("option")}

    def faith(batch):
        body = "".join(f"\n=== key {did}\nWhat the team decided: {one_line(src[did]['did'])}\nRestatement: {got[did]}\n"
                       for did in batch)
        return v2.objects_with(call("sonnet", "faith2", FAITH_PROMPT + body), "key")

    verdict = {str(o.get("key")): str(o.get("faithful")).lower()
               for objs in pmap(faith, batches([d for d in dids if d in got], 30)) for o in objs}
    out = [{"decision_id": did, "his_text": got[did], "previous": h1[did]["his_text"], "faithful": verdict.get(did),
            "pairs": [x["pair_id"] for x in targets if x["decision_id"] == did]} for did in dids if did in got]
    write_jsonl(p("his2.jsonl"), out)
    print("decisions", len(dids), "rendered", len(out), "faithful", sum(r["faithful"] == "yes" for r in out),
          "pairs", sum(len(r["pairs"]) for r in out if r["faithful"] == "yes"))


# ---------------------------------------------------------------- 4. same/different judge

SAME_PROMPT = """Each item below gives what a research team actually decided, a one-sentence restatement of it, and several candidate options written by others for the same decision point.

For each item answer:
- "faithful": "yes" if the restatement describes the same decision as what the team decided (abstracting away study-specific details is fine), "no" if it changes, drops the core of, or adds to the decision.
- "same": for each candidate label, "same" if the candidate is essentially the team's decision (a reader who knew what the team did would say the team took this option, or it contains the team's decision as a part), else "different".

Return only JSON: {"items": [{"key": str, "faithful": "yes" | "no", "same": {"<label>": "same" | "different"}}]}

ITEMS:
"""


def same():
    src = {d["decision_id"]: d for d in sources()}
    hs = {r["decision_id"]: r for r in read_jsonl(p("his.jsonl"))}
    old = {r["decision_id"]: r for r in read_jsonl(p("same.jsonl"))}
    props = [dict(r, proposals=[x for x in r["proposals"] if x["generator"] not in old.get(r["decision_id"], {}).get("same", {})])
             for r in read_jsonl(p("proposals.jsonl")) if r["decision_id"] in hs]
    props = [r for r in props if r["proposals"] and old.get(r["decision_id"], {}).get("faithful", "yes") == "yes"]
    bs = batches(props, 12)
    check_budget("build", len(bs))

    def one(batch):
        body = "".join(f"\n=== key {r['decision_id']}\nWhat the team decided: {one_line(src[r['decision_id']]['did'])}\n"
                       f"Restatement: {hs[r['decision_id']]['his_text']}\n"
                       + "".join(f"C{i + 1}: {x['text']}\n" for i, x in enumerate(r["proposals"])) for r in batch)
        return v2.objects_with(call("sonnet", "same", SAME_PROMPT + body), "key")

    got = {str(o.get("key")): o for objs in pmap(one, bs) for o in objs}
    for r in props:
        g = got.get(r["decision_id"]) or {}
        verdicts = g.get("same") or {}
        row = old.setdefault(r["decision_id"], {"decision_id": r["decision_id"], "same": {},
                                                "faithful": str(g.get("faithful")).lower()})
        row["same"].update({x["generator"]: str(verdicts.get(f"C{i + 1}")).lower() for i, x in enumerate(r["proposals"])})
    out = list(old.values())
    write_jsonl(p("same.jsonl"), out)
    print("faithful", collections.Counter(r["faithful"] for r in out),
          "proposals", collections.Counter(v for r in out for v in r["same"].values()))


# ---------------------------------------------------------------- pairs + blind length fix


def titles():
    out = [fm.get("title", "") for d, _, fm in v2.corpus().values() if d and d.isoformat() >= v2.T]
    return out + [re.sub(r"^\[[\d.]+\]\s*", "", t) for t in out]


def problems(context, his_text, alt, checks):
    probs = v2.pair_problems(context, his_text, alt, *checks)
    lengths = sorted(map(len, (his_text, alt)))
    if lengths[0] and lengths[1] / lengths[0] > MAX_RATIO and not any("20%" in x for x in probs):
        probs.append("the two options differ in length by more than 15%")
    return probs


# The topic names of two works are coined terms the checks ban; renaming them the same way in every
# text of a pair needs no knowledge of his choice.
PLAIN_TERMS = [(re.compile(r"\bsecret loyalt", re.IGNORECASE), "hidden loyalt"),
               (re.compile(r"\bconditional misalignment", re.IGNORECASE), "context-dependent misalignment")]


def plain_terms(text):
    for pat, repl in PLAIN_TERMS:
        text = pat.sub(lambda m, repl=repl: repl.capitalize() if m.group(0)[0].isupper() else repl, text)
    return text


FIX_PROMPT = """Rewrite each sentence below to the target length range, keeping its meaning, its form (one imperative sentence, no digits, no first person, no names) and its level of detail as far as the length allows. Add no justification or hedge.

Return only JSON: {"items": [{"key": str, "text": str}]}

ITEMS:
"""


def pairs():
    ctx = {r["decision_id"]: r for r in read_jsonl(p("contexts.jsonl"))}
    hs = {r["decision_id"]: r for r in read_jsonl(p("his.jsonl"))}
    sm = {r["decision_id"]: r for r in read_jsonl(p("same.jsonl"))}
    src = {d["decision_id"]: d for d in sources()}
    checks = (titles(), *v2.banned())
    built = {r["pair_id"]: r for r in read_jsonl(p("pairs_raw.jsonl"))}
    rows = []
    for r in read_jsonl(p("proposals.jsonl")):
        did = r["decision_id"]
        if did not in hs or sm.get(did, {}).get("faithful") != "yes":
            continue
        for x in r["proposals"]:
            if sm[did]["same"].get(x["generator"]) != "different":
                continue
            pid = v2.digest([v2.SLUG, "pairs_v4", did, x["generator"]])[:12]
            if pid in built:
                continue
            rows.append({"pair_id": pid, "decision_id": did, "work": src[did]["work"], "generator": x["generator"],
                         "context": ctx[did]["context"], "question": ctx[did]["question"],
                         "his_text": hs[did]["his_text"], "alt_text": x["text"], "alt_text_original": x["text"]})
    for h in read_jsonl(p("his2.jsonl")):
        for old_id in h["pairs"] if h["faithful"] == "yes" else []:
            pid = v2.digest([v2.SLUG, "pairs_v4", old_id, "his2"])[:12]
            if pid not in built:
                old = built[old_id]
                old["superseded_by"] = pid
                rows.append(dict({k: v for k, v in old.items() if k not in ("problems", "length_fixed", "superseded_by")},
                                 pair_id=pid, his_text=h["his_text"], his_round=2, supersedes=old_id))
    for r in rows:
        for k in ("context", "question", "his_text", "alt_text"):
            r[k] = plain_terms(r[k])
        r["problems"] = problems(r["context"], r["his_text"], r["alt_text"], checks)
    # The fixer sees only the proposal and a target length, never his option.
    fix = [r for r in rows if r["problems"] == ["the two options differ in length by more than 15%"]
           or r["problems"] == ["the two options differ in length by more than 20%"]]
    if fix:
        check_budget("build", len(batches(fix, 25)))

        def one(batch):
            body = "".join(f"\n=== key {r['pair_id']}\nTarget: {round(len(r['his_text']) * 0.95)}-"
                           f"{round(len(r['his_text']) * 1.05)} characters\nSentence: {r['alt_text']}\n" for r in batch)
            return v2.objects_with(call("sonnet", "lenfix", FIX_PROMPT + body), "key")

        got = {str(o.get("key")): o for objs in pmap(one, batches(fix, 25)) for o in objs}
        for r in fix:
            t = one_line((got.get(r["pair_id"]) or {}).get("text"))
            if t:
                r["alt_text"], r["length_fixed"] = t, True
                r["problems"] = problems(r["context"], r["his_text"], t, checks)
    rows = list(built.values()) + rows
    write_jsonl(p("pairs_raw.jsonl"), rows)
    print("pairs", len(rows), "clean", sum(not r["problems"] for r in rows), "length-fixed",
          sum(bool(r.get("length_fixed")) for r in rows),
          collections.Counter(x for r in rows for x in r["problems"]).most_common(6))


# ---------------------------------------------------------------- 5. gates


def his_first(pair_id):
    return random.Random("v4order:" + pair_id).random() < 0.5


def clean_pairs():
    return [r for r in read_jsonl(p("pairs_raw.jsonl")) if not r["problems"] and not r.get("superseded_by")]


def items(rows):
    return [{"id": r["pair_id"], "group": r["decision_id"], "context": r["context"], "question": r["question"],
             "his": r["his_text"], "alt": r["alt_text"]} for r in rows]


def vote(model, its, prompt, reps, size, seed, tag):
    slots = [(it, hf, rep) for it in its for hf in (True, False) for rep in reps]
    bs = v2.pack(slots, size, seed)
    print(tag, model, "items", len(its), "calls", len(bs))
    if model == "sonnet":
        check_budget("gate", len(bs))

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
            row = {"id": it["id"], "model": model, "his_first": hf, "rep": rep, "answer": a}
            if tag == "fair":
                row["fairness"] = None if a not in (0, 1, 2) else (
                    "ok" if a == 0 else ("his_weaker" if (a == 1) == hf else "alt_weaker"))
            else:
                row["picked_his"] = None if a not in (1, 2) else (a == 1) == hf
            res.append(row)
        return res

    return [v for res in pmap(one, bs) for v in res]


def votes(path):
    out = collections.defaultdict(list)
    for v in read_jsonl(p(path)):
        if v.get("picked_his") is not None:
            out[v["id"]].append(v["picked_his"])
    return out


def share(vs):
    return sum(vs) / len(vs) if vs else None


def gate(path, prompt, tag, rows, reps, seed):
    new = vote("sonnet", items(rows), prompt, reps, GATE_BATCH, seed, tag)
    write_jsonl(p(path), read_jsonl(p(path)) + new)


def real():
    done = set(votes("realness.jsonl"))
    gate("realness.jsonl", v2.REAL_PROMPT, "real", [r for r in clean_pairs() if r["pair_id"] not in done],
         range(PER_ORDER), "real")


def taste():
    done = set(votes("taste.jsonl"))
    gate("taste.jsonl", v2.GATE_PROMPT, "taste", [r for r in clean_pairs() if r["pair_id"] not in done],
         range(PER_ORDER), "taste")


def in_bands(r, rv, tv):
    rs, ts = share(rv[r["pair_id"]]), share(tv[r["pair_id"]])
    return rs is not None and ts is not None and REAL_BAND[0] <= rs <= REAL_BAND[1] and TASTE_BAND[0] <= ts <= TASTE_BAND[1]


def confirm():
    """Pairs in both bands on 6+6 votes get 6 fresh votes on each gate, so membership rests on 12+12."""
    rv, tv = votes("realness.jsonl"), votes("taste.jsonl")
    rows = [r for r in clean_pairs() if in_bands(r, rv, tv) and len(rv[r["pair_id"]]) <= 2 * PER_ORDER]
    reps = range(PER_ORDER, 2 * PER_ORDER)
    gate("realness.jsonl", v2.REAL_PROMPT, "real", rows, reps, "real:confirm")
    gate("taste.jsonl", v2.GATE_PROMPT, "taste", rows, reps, "taste:confirm")


def fair():
    """Haiku fairness in both orders for every pair in both bands."""
    rv, tv = votes("realness.jsonl"), votes("taste.jsonl")
    rows = [r for r in clean_pairs() if in_bands(r, rv, tv)]
    write_jsonl(p("fairness.jsonl"), vote("haiku", items(rows), v2.FAIR_PROMPT, range(1), FAIR_BATCH, "fair", "fair"))


# ---------------------------------------------------------------- 6. assemble


def assemble():
    src = {d["decision_id"]: d for d in sources()}
    ctx = read_jsonl(p("contexts.jsonl"))
    props = read_jsonl(p("proposals.jsonl"))
    hs = {r["decision_id"] for r in read_jsonl(p("his.jsonl"))}
    sm = {r["decision_id"]: r for r in read_jsonl(p("same.jsonl"))}
    raw = read_jsonl(p("pairs_raw.jsonl"))
    rv, tv = votes("realness.jsonl"), votes("taste.jsonl")
    fv = collections.defaultdict(list)
    for v in read_jsonl(p("fairness.jsonl")):
        fv[v["id"]].append(v["fairness"])
    pairs = []
    for r in raw:
        if r["problems"] or r.get("superseded_by"):
            continue
        pid, hf, d = r["pair_id"], his_first(r["pair_id"]), src[r["decision_id"]]
        rs, ts = share(rv[pid]), share(tv[pid])
        row = {"pair_id": pid, "decision_id": r["decision_id"], "doc": d["doc"], "work": d["work"], "date": d["date"],
               "decision_point": d["point"], "generator": r["generator"],
               "generator_family": r["generator"].split(":")[0], "context": r["context"], "question": r["question"],
               "a_text": r["his_text"] if hf else r["alt_text"], "b_text": r["alt_text"] if hf else r["his_text"],
               "his_side": "a" if hf else "b", "length_fixed": bool(r.get("length_fixed")),
               "his_round": r.get("his_round", 1), "supersedes": r.get("supersedes"),
               "realness_share": rs, "n_realness_votes": len(rv[pid]), "blind_share": ts, "n_votes": len(tv[pid]),
               "fairness_votes": fv.get(pid, []), "url": d.get("url"), "cutoff": v2.T}
        row["real_band"] = rs is not None and REAL_BAND[0] <= rs <= REAL_BAND[1]
        row["taste_band"] = ts is not None and TASTE_BAND[0] <= ts <= TASTE_BAND[1]
        row["fair"] = len(row["fairness_votes"]) == 2 and all(f == "ok" for f in row["fairness_votes"])
        row["band"] = row["real_band"] and row["taste_band"] and row["fair"]
        pairs.append(row)
    write_jsonl(p("pairs.jsonl"), pairs)
    band = [x for x in pairs if x["band"]]
    write_jsonl(p("band.jsonl"), band)

    # funnel per work: decisions through steps 1-4, then pairs through the gates
    works = sorted({d["work"] for d in src.values()})
    stage_dec = collections.OrderedDict([
        ("decisions", {d: src[d]["work"] for d in src}),
        ("context written (not skipped)", {r["decision_id"]: r["work"] for r in ctx if r["status"] in ("ok", "leak")}),
        ("no leak, round 1", {r["decision_id"]: r["work"] for r in ctx if r["status"] == "ok" and r.get("round", 1) == 1}),
        ("no leak, after blind revision", {r["decision_id"]: r["work"] for r in ctx if r["status"] == "ok"}),
        ("proposals made", {r["decision_id"]: src[r["decision_id"]]["work"] for r in props if r["proposals"]}),
        ("his option rendered", {d: src[d]["work"] for d in hs}),
        ("his option faithful", {d: src[d]["work"] for d, r in sm.items() if r["faithful"] == "yes"})])
    pair_stages = collections.OrderedDict([
        ("proposals", [(r["decision_id"], src[r["decision_id"]]["work"]) for r in props for _ in r["proposals"]]),
        ("different from his (faithful decisions)", [(r["decision_id"], r["work"]) for r in raw if "supersedes" not in r]),
        ("form checks clean", [(x["decision_id"], x["work"]) for x in pairs]),
        ("realness band", [(x["decision_id"], x["work"]) for x in pairs if x["real_band"]]),
        ("taste band", [(x["decision_id"], x["work"]) for x in pairs if x["taste_band"]]),
        ("realness and taste", [(x["decision_id"], x["work"]) for x in pairs if x["real_band"] and x["taste_band"]]),
        ("band (and fair)", [(x["decision_id"], x["work"]) for x in band])])

    def mean(xs):
        xs = [v for v in xs if v is not None]
        return round(sum(xs) / len(xs), 3) if xs else None

    all_real = [v for x in pairs for v in rv[x["pair_id"]]]
    stats = {
        "decision_funnel": {k: {"decisions": len(v), "works": len(set(v.values())),
                                "by_work": dict(collections.Counter(v.values()))} for k, v in stage_dec.items()},
        "pair_funnel": {k: {"pairs": len(v), "works": len({w for _, w in v}), "decisions": len({d for d, _ in v}),
                            "by_work": dict(collections.Counter(w for _, w in v))} for k, v in pair_stages.items()},
        "works": works,
        "leak": {"string": sum(bool(r.get("string_leak")) for r in ctx),
                 "sonnet": sum(r.get("llm_leak") is True for r in ctx),
                 "sonnet_unparsed": sum(r.get("llm_leak") is None and r["status"] == "leak" for r in ctx)},
        "same_verdicts": dict(collections.Counter(v for r in sm.values() for v in r["same"].values())),
        "mean_realness_pairwise": mean(x["realness_share"] for x in pairs),
        "realness_vote_share": round(sum(all_real) / len(all_real), 3) if all_real else None,
        "mean_realness_by_family": {f: mean(x["realness_share"] for x in pairs if x["generator_family"] == f)
                                    for f in sorted({x["generator_family"] for x in pairs})},
        "mean_taste_share": mean(x["blind_share"] for x in pairs),
        "mean_taste_by_family": {f: mean(x["blind_share"] for x in pairs if x["generator_family"] == f)
                                 for f in sorted({x["generator_family"] for x in pairs})},
        "realness_hist_6votes": dict(sorted(collections.Counter(
            round(share(rv[x["pair_id"]][:2 * PER_ORDER]) * 6) for x in pairs if rv[x["pair_id"]]).items())),
        "taste_hist_6votes": dict(sorted(collections.Counter(
            round(share(tv[x["pair_id"]][:2 * PER_ORDER]) * 6) for x in pairs if tv[x["pair_id"]]).items())),
        "lopsided_taste (>0.8 either way)": sum(x["blind_share"] is not None and max(x["blind_share"], 1 - x["blind_share"]) > 0.8
                                                for x in pairs),
        "real_taste_but_unfair": dict(collections.Counter(
            "/".join(map(str, sorted(x["fairness_votes"], key=str))) for x in pairs if x["real_band"] and x["taste_band"] and not x["fair"])),
        "his_rerender": {
            "pairs": len(re2 := [x for x in pairs if x["his_round"] == 2]),
            "before (round 1, 6 votes each)": {"realness": mean(share(rv[x["supersedes"]]) for x in re2),
                                            "taste": mean(share(tv[x["supersedes"]]) for x in re2)},
            "after": {"realness": mean(x["realness_share"] for x in re2), "taste": mean(x["blind_share"] for x in re2)},
            "after: realness band": sum(x["real_band"] for x in re2), "after: taste band": sum(x["taste_band"] for x in re2),
            "after: both": sum(x["real_band"] and x["taste_band"] for x in re2)},
        "band_by_family": dict(collections.Counter(x["generator_family"] for x in band)),
        "band_by_generator": dict(collections.Counter(x["generator"] for x in band)),
        "band_pairs": len(band), "band_works": len({x["work"] for x in band}),
        "band_decisions": len({x["decision_id"] for x in band}),
        "band_his_side": dict(collections.Counter(x["his_side"] for x in band)),
        "band_length_fixed": sum(x["length_fixed"] for x in band),
        "calls": {"sonnet build (steps 1-4)": spent("build"), "sonnet gate": spent("gate"),
                  "haiku": v2.real_calls("haiku")},
        "calls_by_tag": dict(collections.Counter(r["tag"] for r in read_jsonl(p("calls.log")) if r.get("status") == "started")),
        "errors": sum(r.get("status") == "error" for r in read_jsonl(p("calls.log"))),
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in read_jsonl(p("calls.log"))), 2),
    }
    with open(p("stats.json"), "w") as f:
        json.dump(stats, f, indent=1, ensure_ascii=False, default=str)
    print(json.dumps({k: v for k, v in stats.items() if k not in ("decision_funnel", "pair_funnel")}, indent=1, default=str))
    for k in ("decision_funnel", "pair_funnel"):
        for s, v in stats[k].items():
            print(k, "|", s, "|", {kk: vv for kk, vv in v.items() if kk != "by_work"})


if __name__ == "__main__":
    stage, *args = sys.argv[1:]
    {"context": context, "leak": leak, "propose": propose, "his": his, "same": same, "propose2": propose2, "his2": his2, "pairs": pairs,
     "real": real, "taste": taste, "confirm": confirm, "fair": fair, "assemble": assemble}[stage](*args)
