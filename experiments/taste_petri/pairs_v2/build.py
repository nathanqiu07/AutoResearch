"""pairs_v2: a held-out pair set for Owain Evans's post-T decisions (T = 2026-01-01) whose
distractors are choices a strong researcher could defend, gated so a blind judge is split.

Stages (each reads earlier stages' files in this dir, each resumable through the call cache):
  sources   post-T decisions from decisions.jsonl, quotes re-verified; plus a sonnet extraction
            from post-T docs that have none (value leakage abstract)        -> sources.jsonl
  generate  sonnet: neutral context, trade-off axis, and candidate alternatives per decision
            from four generators (two PEER cards, AXIS FLIP, FIELD)          -> candidates.jsonl
  render    sonnet: every option of a decision restated in one fixed form in one pass, shuffled,
            no hint which was taken; check_pair-style checks                -> rendered.jsonl
  gate      haiku blind votes (4 per order), batched 8 items per call; e2_owain's 22 pairs ride
            along as a calibration set                                       -> votes.jsonl
  fair      haiku fairness judge, batched 10 items per call                  -> fairness.jsonl
  assemble  pairs.jsonl, band.jsonl, stats.json

Every CLI call goes through call(): cached on disk by prompt hash, logged in calls.log, capped.
Reads repo code and data read-only; writes only inside this directory.

    python3 experiments/taste_petri/pairs_v2/build.py <stage>
"""
import collections
import glob
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from autoresearch.llm import extract_json
from autoresearch.taste import timesplit
from autoresearch.taste.researcher import load_researcher
from autoresearch.taste.track_eval import cluster_ci
from autoresearch.taste.usermodel import digest

SLUG, T = "owain_evans", "2026-01-01"
DATA = os.path.join(ROOT, "data", "researchers", SLUG)
PROFILES = os.path.join(ROOT, "experiments", "taste_petri", "profiles")
E2 = os.path.join(ROOT, "experiments", "taste_petri", "e2_owain")
CAPS = {"sonnet": 80, "haiku": 600}
WORKERS = 6
VOTES_PER_ORDER = 4
GATE_BATCH, FAIR_BATCH = 8, 10
BAND = (0.25, 0.75)
PEERS = ["evan_hubinger", "samuel_bowman", "ryan_greenblatt", "buck_shlegeris",
         "samuel_marks", "elizabeth_barnes", "jacob_steinhardt", "nicholas_carlini"]
PEER_NAMES = ["Hubinger", "Bowman", "Greenblatt", "Shlegeris", "Marks", "Barnes", "Steinhardt", "Carlini",
              "Hobbhahn", "Apollo", "Anthropic", "OpenAI", "DeepMind", "Redwood", "METR"]
# a paper and its blog post are one piece of work
WORK = {"research__consciousness_cluster_preferences_of_models_that_c_dd86ed8e.txt": "consciousness_cluster",
        "research__the_consciousness_cluster_emergent_preferences_of__5545a53f.txt": "consciousness_cluster",
        "research__conditional_misalignment_common_interventions_can__76ed8749.txt": "conditional_misalignment",
        "research__conditional_misalignment_mitigations_can_hide_em_b_a5f95a71.txt": "conditional_misalignment"}
# post-T docs with no checked decisions that state research choices (the others are a link list,
# a 940-char blurb and a publication-history post)
EXTRA_DOCS = ["research__2607_14345_value_leakage_an_llm_s_answers_are_sile_b336e815.txt"]
# coined names from post-T titles; check_pair only matches whole later titles in the context
COINED = ["consciousness cluster", "conditional misalignment", "negation neglect", "secret loyalt",
          "story imprinting", "cot override", "homeopathic", "value leakage", "beyond owls", "half-baked"]
LOCK = threading.Lock()


def p(*parts):
    out = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def work_of(doc):
    return WORK.get(doc, doc.replace("research__", "")[:40].rstrip("_"))


# ---------------------------------------------------------------- the one CLI wrapper

def real_calls(model):
    return sum(1 for r in read_jsonl(p("calls.log")) if r.get("status") == "started" and r["model"] == model)


def call(model, tag, prompt, system="You are a careful research assistant."):
    """claude -p, isolated (no tools, no MCP, no settings, no session). Cached by prompt hash."""
    key = hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()[:32]
    cpath = p("cache", key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    with LOCK:
        n = real_calls(model)
        if n >= CAPS[model]:
            raise RuntimeError(f"{model} cap {CAPS[model]} reached")
        with open(p("calls.log"), "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n + 1, "model": model, "tag": tag,
                                "key": key, "chars": len(prompt), "status": "started"}) + "\n")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "", "--strict-mcp-config",
           "--no-session-persistence", "--setting-sources", "", "--system-prompt", system]
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="pv2_cli_") as cwd:
        proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=900, cwd=cwd)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
    ok = proc.returncode == 0 and not data.get("is_error")
    with LOCK, open(p("calls.log"), "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "tag": tag, "key": key,
                            "status": "ok" if ok else "error", "secs": round(time.time() - t0, 1),
                            "cost_usd": data.get("total_cost_usd"), "out": str(data.get("result"))[:100]}) + "\n")
    if not ok:
        raise RuntimeError(f"claude CLI error: {str(data.get('result'))[:300]}")
    with open(cpath, "w") as f:
        json.dump({"model": model, "tag": tag, "prompt": prompt, "result": data["result"]}, f, ensure_ascii=False)
    return data["result"]


def objects_with(text, key):
    """Every JSON object in text that starts with "key", parsed one by one, so one malformed
    bracket elsewhere in a long reply loses only its own object."""
    dec, out = json.JSONDecoder(strict=False), []
    for m in re.finditer(r'\{\s*"' + re.escape(key) + '"', text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except json.JSONDecodeError:
            continue
        out.append(obj)
    return out


def pmap(fn, items):
    with ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(fn, items))


# ---------------------------------------------------------------- stage 1: sources

def corpus():
    out = {}
    for path in glob.glob(os.path.join(DATA, "corpus", "*.txt")):
        date, text = timesplit.read_doc(path)
        out[os.path.basename(path)] = (date, text, timesplit.front_matter(path))
    return out


EXTRACT_PROMPT = (timesplit.SUMMARY_QUERY + " Return JSON {\"decisions\": [{\"point\", \"problem\", \"did\", "
                  "\"alternatives_named\": [str], \"stated_reason\", \"quote\"}]}. Only decisions the authors "
                  "actually made; an empty list is fine.\n\nDOCUMENT:\n")


def sources():
    docs = corpus()
    rows, dropped = [], collections.Counter()
    for r in read_jsonl(os.path.join(DATA, "extraction", "decisions.jsonl")):
        if not r.get("date") or r["date"] < T:
            continue
        if not r.get("did") or r["did"] == "null":
            dropped["did null/empty"] += 1
        elif r["doc"] not in docs or not timesplit.quote_in_text(r.get("quote") or "", docs[r["doc"]][1]):
            dropped["quote not in doc"] += 1
        else:
            rows.append(dict(r, origin="decisions.jsonl"))
    for doc in EXTRA_DOCS:
        date, text, fm = docs[doc]
        out = extract_json(call("sonnet", "extract", EXTRACT_PROMPT + text)) or {}
        for d in out.get("decisions") or []:
            if not d.get("did") or not timesplit.quote_in_text(d.get("quote") or "", text):
                dropped["extracted: quote not verified"] += 1
                continue
            rows.append({**{k: d.get(k) for k in timesplit._FIELDS}, "doc": doc, "url": fm.get("url"),
                         "date": date.isoformat(), "tag": "pairs_v2_extract",
                         "decision_id": digest([doc, d["quote"]])[:12], "origin": "pairs_v2 sonnet extract"})
    for r in rows:
        if isinstance(r.get("alternatives_named"), str):  # the timesplit bug: keep it a list
            r["alternatives_named"] = [r["alternatives_named"]]
        r["work"] = work_of(r["doc"])
    write_jsonl(p("sources.jsonl"), rows)
    print("usable post-T decisions", len(rows), "dropped", dict(dropped), "works", len({r["work"] for r in rows}))
    print(collections.Counter(r["work"] for r in rows))


# ---------------------------------------------------------------- FIELD retrieval (BM25, no LLM)

STOP = set("""a an the of to in and or for on with by is are was were be been it its this that these those as at
from we our they their not no can could would should will may might than then which what when how who whose
model models llm llms language data training trained train test tests result results paper use used using
also more most other such each one two into about whether there here do does did has have had""".split())


def tokens(text):
    return [w for w in re.findall(r"[a-z][a-z\-]{2,}", text.lower()) if w not in STOP]


def field_index():
    chunks = []
    for slug in PEERS:
        for path in glob.glob(os.path.join(ROOT, "data", "researchers", slug, "corpus", "*.txt")):
            fm = timesplit.front_matter(path)
            if re.search(r"owain|hobbhahn", fm.get("authors", ""), re.IGNORECASE):
                continue
            _, text = timesplit.read_doc(path)
            buf = ""
            for para in re.split(r"\n\s*\n", text):
                para = " ".join(para.split())
                if len(para) < 80 or re.search(r"owain|evans|hobbhahn", para, re.IGNORECASE):
                    continue
                buf = (buf + " " + para).strip()
                if len(buf) >= 500:
                    chunks.append({"peer": slug, "doc": os.path.basename(path), "title": fm.get("title", ""),
                                   "text": buf[:1200]})
                    buf = ""
    toks = [collections.Counter(tokens(c["text"])) for c in chunks]
    df = collections.Counter(w for t in toks for w in t)
    avg = sum(sum(t.values()) for t in toks) / len(toks)
    return chunks, toks, df, avg


def retrieve(index, query, k=4):
    chunks, toks, df, avg = index
    n, q = len(chunks), set(tokens(query))
    scores = []
    for i, t in enumerate(toks):
        length, s = sum(t.values()), 0.0
        for w in q & t.keys():
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * t[w] * 2.2 / (t[w] + 1.2 * (0.25 + 0.75 * length / avg))
        if s:
            scores.append((s, i))
    out, docs = [], set()
    for s, i in sorted(scores, reverse=True):
        if chunks[i]["doc"] not in docs:
            out.append(chunks[i])
            docs.add(chunks[i]["doc"])
        if len(out) == k:
            break
    return out


# ---------------------------------------------------------------- stage 2: generate

def peer_card(slug):
    with open(os.path.join(PROFILES, slug, "e_taste_vector.md")) as f:
        vec = re.sub(r"<!--.*?-->|## \(e\) Taste vector", "", f.read(), flags=re.DOTALL).strip()
    with open(os.path.join(PROFILES, slug, "a_principles.md")) as f:
        heads = re.findall(r"^\d+\. \*\*(.+?)\*\*\s*(.*)$", f.read(), flags=re.MULTILINE)
    return vec + "\nGeneral principles:\n" + "\n".join(f"- {h} {why}".strip() for h, why in heads)




def axes_text():
    rows = read_jsonl(os.path.join(ROOT, "data", "trackp", "tradeoffs.jsonl"))
    return "\n".join(f"- {r['axis']} ({r['decision_point']}): (1) {r['pole_1']} vs (2) {r['pole_2']}" for r in rows)


GEN_PROMPT = """You are helping build a test of research taste: pairs where a competent judge who does not know the team could reasonably go either way. Below are research decisions an AI-safety team made in a 2026 paper. For each you get the problem, what the team did, the reason they gave, the alternatives their own text names, an excerpt of the paper around the decision, and excerpts from other groups' work.

For EACH decision return:
1. "context": 2-5 sentences, neutral third person, the situation at the moment of decision: what the team was studying and what they knew then, and for a decision about accepting, interpreting or claiming a result, the result itself. Give enough specifics that the options can be weighed. Do not reveal or hint what they chose, do not mention anything learned after the decision, and do not name any person, lab, paper or coined term from the paper (describe the phenomenon in plain words).
2. "axis": the trade-off this decision sits on: one axis name from the list below, or "other: <pole A> vs <pole B>". "team_pole": which pole the team's choice sits on, in a few words.
3. Candidates: alternative choices for the same decision point. Each is one sentence, of similar length and specificity to what the team did:
   - "peer_A": how a strong researcher with the priorities in CARD A would have resolved this same decision point.
   - "peer_B": the same for CARD B.
   - "axis_flip": the choice at the opposite pole of the axis, carried out as competently as the team's choice.
   - "field_text": a real choice another group made on a comparable problem, taken from the field excerpts for this decision and adapted to this decision point, with "field_excerpt" the excerpt's index. Use null for both if no excerpt shows a comparable choice.
4. "skip": true only if this is not a real choice point (pure description; no defensible alternative exists). Otherwise false.

Rules for every candidate (these matter most):
- A strong researcher could defend it in a lab meeting, and it is feasible with the team's resources at the time.
- It is NOT one of the alternatives the team's text names, NOT anything the excerpt argues against, NOT a weaker or hedged copy of the team's choice, and NOT a strawman (sloppy, overclaiming, ignoring an obvious confound, gratuitously expensive).
- It is a genuinely different decision from the team's choice and from the other candidates, not a paraphrase or a superset ("do X and also Y").
- For decisions about how strongly to state a claim, alternatives are different defensible framings (e.g. a broader claim with explicit uncertainty, a claim of a different kind, a different headline emphasis), never an overclaim.
- Never name a person, lab, paper or the researchers whose cards you were given.

The cards were written for another task (designing evaluation scenarios); use them only to infer each researcher's general research priorities.

TRADE-OFF AXES:
{axes}

CARD A:
{card_a}

CARD B:
{card_b}

Return only JSON, one flat object per decision: {{"decisions": [{{"decision_id": str, "skip": bool, "context": str, "axis": str, "team_pole": str, "peer_A": str, "peer_B": str, "axis_flip": str, "field_text": str or null, "field_excerpt": int or null}}]}}

DECISIONS:
"""


def excerpt(text, quote, before=1800, after=500):
    norm = timesplit.normalize_for_quote(text)
    i = norm.find(timesplit.normalize_for_quote(quote))
    pos = int(i * len(text) / max(1, len(norm))) if i >= 0 else 0
    return " ".join(text[max(0, pos - before): pos + after].split())


def generate():
    docs = corpus()
    rows = read_jsonl(p("sources.jsonl"))
    index = field_index()
    print("field chunks", len(index[0]))
    by_doc = collections.defaultdict(list)
    for r in rows:
        by_doc[r["doc"]].append(r)
    batches = []
    for doc in sorted(by_doc):
        ds = by_doc[doc]
        for i in range(0, len(ds), 4):
            batches.append(ds[i:i + 4])
    jobs = []
    for b, ds in enumerate(batches):
        a, c = PEERS[(2 * b) % 8], PEERS[(2 * b + 1) % 8]
        body = ""
        field = {}
        for d in ds:
            hits = retrieve(index, f"{d['problem']} {d['did']}")
            field[d["decision_id"]] = hits
            body += (f"\n=== decision_id {d['decision_id']} ({d['point']})\nProblem: {d['problem']}\n"
                     f"What the team did: {d['did']}\nReason given: {d.get('stated_reason') or ''}\n"
                     f"Alternatives the text names (do not use): {json.dumps(d.get('alternatives_named') or [])}\n"
                     f"Paper excerpt: {excerpt(docs[d['doc']][1], d['quote'])}\nField excerpts:\n"
                     + "".join(f"  [{k}] ({h['title'][:80]}) {h['text'][:700]}\n" for k, h in enumerate(hits)))
        prompt = (GEN_PROMPT.replace("{axes}", axes_text()).replace("{card_a}", peer_card(a))
                  .replace("{card_b}", peer_card(c)).replace("{{", "{").replace("}}", "}")) + body
        jobs.append((ds, a, c, field, prompt))

    def one(job):
        ds, a, c, field, prompt = job
        try:
            out = objects_with(call("sonnet", "generate", prompt), "decision_id")
        except RuntimeError as e:
            print("generate failed", e)
            return []
        got = {str(x.get("decision_id")): x for x in out}
        res = []
        for d in ds:
            g = got.get(d["decision_id"])
            if not g:
                res.append({"decision_id": d["decision_id"], "status": "no output"})
                continue
            k, hits = g.get("field_excerpt"), field[d["decision_id"]]
            fhit = hits[k] if isinstance(k, int) and 0 <= k < len(hits) else None
            alts = [("peer:" + a, g.get("peer_A"), None), ("peer:" + c, g.get("peer_B"), None),
                    ("axis_flip", g.get("axis_flip"), None),
                    ("field", g.get("field_text"),
                     {"peer_corpus": fhit["peer"], "doc": fhit["doc"], "title": fhit["title"]} if fhit else None)]
            res.append({"decision_id": d["decision_id"], "status": "skip" if g.get("skip") else "ok",
                        "context": g.get("context"), "axis": g.get("axis"), "team_pole": g.get("team_pole"),
                        "candidates": [{"generator": gen, "text": t, "field_source": src}
                                       for gen, t, src in alts if isinstance(t, str) and len(t) > 20]})
        return res

    out = [r for res in pmap(one, jobs) for r in res]
    write_jsonl(p("candidates.jsonl"), out)
    print(collections.Counter(r["status"] for r in out), "candidates", sum(len(r.get("candidates", [])) for r in out))


# ---------------------------------------------------------------- stage 3: render

RENDER_PROMPT = """Turn each research decision below into a neutral multiple-choice item. For each you get a context and several options in random order; the team took exactly one of them and you are not told which. Do not try to work out which.

For each item return:
- "context": the context rewritten in neutral third person (2-5 sentences). Keep its facts. Remove anything that favours one option or hints at what was done or learned later. Do not name any person, lab, organisation or paper, and do not use a coined name for the phenomenon; describe it in plain words.
- "question": one short line naming the decision, e.g. "Which evaluation should the team build?"
- "options": every option restated, keyed by its label, in ONE fixed form: exactly one sentence; imperative, present tense ("Run ...", "Frame ..."); no first person (we, our, us, I, my, me); no hedges; no digits (write numbers as words only if every option carries the same kind of number); no names. Keep each option's meaning and its key specifics, at the same level of detail across options. All options of an item must have nearly the same length: every option between {lo} and {hi} characters. Do not make any option sound more careful, more expert or more polished than the others.

Return only JSON: {{"items": [{{"key": str, "context": str, "question": str, "options": {{"<label>": str}}}}]}}

ITEMS:
"""


def banned():
    names = timesplit.banned_pattern(load_researcher(SLUG))
    extra = re.compile(r"\b(?:" + "|".join(map(re.escape, PEER_NAMES + COINED)) + ")", re.IGNORECASE)
    return names, extra


def pair_problems(context, his, alt, titles, names, extra):
    probs = timesplit.check_pair({"context": context, "a_text": his, "b_text": alt}, titles, names)
    probs += [f"names or coined term: {m.group(0)}" for k in (context, his, alt) for m in [extra.search(k)] if m]
    return probs


def render():
    src = {r["decision_id"]: r for r in read_jsonl(p("sources.jsonl"))}
    cands = [r for r in read_jsonl(p("candidates.jsonl")) if r["status"] == "ok" and r["candidates"]]
    titles = [fm.get("title", "") for d, _, fm in corpus().values() if d and d.isoformat() >= T]
    titles += [re.sub(r"^\[[\d.]+\]\s*", "", t) for t in titles]
    names, extra = banned()
    items = []
    for r in cands:
        opts = [("his", src[r["decision_id"]]["did"])] + [(c["generator"], c["text"]) for c in r["candidates"]]
        random.Random("render:" + r["decision_id"]).shuffle(opts)
        labels = {f"O{i + 1}": gen for i, (gen, _) in enumerate(opts)}
        items.append((r, labels, opts))

    def prompt_for(batch, fixes=None):
        body = ""
        for r, labels, opts in batch:
            body += f"\n=== key {r['decision_id']}\nContext: {r['context']}\n" + "".join(
                f"{lab}: {' '.join(str(t).split())}\n" for lab, (_, t) in zip(labels, opts))
            if fixes and r["decision_id"] in fixes:
                body += f"Problems with your previous version of this item, fix them: {fixes[r['decision_id']]}\n"
        return RENDER_PROMPT.format(lo=155, hi=185) + body

    def run(batches, fixes=None, tag="render"):
        def one(batch):
            try:
                out = objects_with(call("sonnet", tag, prompt_for(batch, fixes)), "key")
            except RuntimeError as e:
                print("render failed", e)
                return {}
            return {str(x.get("key")): x for x in out}
        got = {}
        for g in pmap(one, batches):
            got.update(g)
        return got

    def evaluate(got):
        rows, bad = [], {}
        for r, labels, _ in items:
            g = got.get(r["decision_id"])
            if not g:
                continue
            o = g.get("options") or {}
            his_lab = next(lab for lab, gen in labels.items() if gen == "his")
            his = o.get(his_lab)
            for lab, gen in labels.items():
                if gen == "his":
                    continue
                alt = o.get(lab)
                probs = (["missing option"] if not (his and alt) else
                         pair_problems(g.get("context") or "", his, alt, titles, names, extra))
                rows.append({"decision_id": r["decision_id"], "generator": gen, "context": g.get("context"),
                             "question": g.get("question"), "his_text": his, "alt_text": alt, "problems": probs})
                if probs:
                    bad.setdefault(r["decision_id"], set()).update(f"{lab} vs {his_lab}: {x}" for x in probs)
        return rows, bad

    batches = [items[i:i + 5] for i in range(0, len(items), 5)]
    got = run(batches)
    rows, bad = evaluate(got)
    missing = [it for it in items if it[0]["decision_id"] not in got]
    redo = [it for it in items if it[0]["decision_id"] in bad] + missing
    print("render pass 1:", len(got), "items,", sum(not r["problems"] for r in rows), "clean pairs of", len(rows),
          "; redo", len(redo))
    if redo:
        fixes = {k: "; ".join(sorted(v)) for k, v in bad.items()}
        got2 = run([redo[i:i + 5] for i in range(0, len(redo), 5)], fixes, tag="render_fix")
        rows2, _ = evaluate(got2)
        clean2 = {(r["decision_id"], r["generator"]): r for r in rows2 if not r["problems"]}
        rows = [clean2.get((r["decision_id"], r["generator"]), r) if r["problems"] else r for r in rows]
        have = {(r["decision_id"], r["generator"]) for r in rows}
        rows += [r for r in rows2 if (r["decision_id"], r["generator"]) not in have]
    for r in rows:
        r["pair_id"] = digest([SLUG, "pairs_v2", r["decision_id"], r["generator"]])[:12]
        his_first = random.Random("side:" + r["pair_id"]).random() < 0.5
        r["a_text"], r["b_text"] = (r["his_text"], r["alt_text"]) if his_first else (r["alt_text"], r["his_text"])
        r["his_side"] = "a" if his_first else "b"
    write_jsonl(p("rendered.jsonl"), rows)
    print("rendered pairs", len(rows), "clean", sum(not r["problems"] for r in rows),
          collections.Counter(x for r in rows for x in r["problems"]).most_common(8))


# ---------------------------------------------------------------- stage 4: blind gate

GATE_PROMPT = """Below are {n} separate research decisions. In each, a research team had to choose between two options. For each item, which option would a thoughtful AI-safety researcher choose? Judge every item on its own; the items are unrelated.
{items}
Reply with only a JSON object mapping each item number to 1 or 2, e.g. {{"1": 2, "2": 1}}."""


def gate_items():
    items = [{"id": r["pair_id"], "set": "v2", "context": r["context"], "question": r["question"],
              "his": r["his_text"], "alt": r["alt_text"], "group": r["decision_id"]}
             for r in read_jsonl(p("rendered.jsonl")) if not r["problems"]]
    for r in read_jsonl(os.path.join(E2, "pairs.jsonl")):
        his, alt = (r["a_text"], r["b_text"]) if r["chosen"] == "a" else (r["b_text"], r["a_text"])
        items.append({"id": "e2:" + r["pair_id"], "set": "e2_owain", "context": r["context"],
                      "question": "Which option should the team take?", "his": his, "alt": alt,
                      "group": "e2:" + r["decision_id"]})
    return items


def pack(slots, size, seed):
    """Batches of `size` slots, no two slots of the same group in one batch."""
    rng = random.Random(seed)
    slots = slots[:]
    rng.shuffle(slots)
    batches = []
    while slots:
        batch, groups, rest = [], set(), []
        for s in slots:
            if len(batch) < size and s[0]["group"] not in groups:
                batch.append(s)
                groups.add(s[0]["group"])
            else:
                rest.append(s)
        batches.append(batch)
        slots = rest
    return batches


def render_item(k, it, first, second):
    return f"\nItem {k}\nContext: {it['context']}\nQuestion: {it['question']}\nOption 1: {first}\nOption 2: {second}\n"


def first_round_share():
    votes = collections.defaultdict(list)
    for v in read_jsonl(p("votes.jsonl")):
        if v["picked_his"] is not None:
            votes[v["id"]].append(v["picked_his"])
    return {k: sum(v) / len(v) for k, v in votes.items()}


def gate(second=False):
    """First round: every pair, VOTES_PER_ORDER per order. Second round (gate2): 4 more per order
    for v2 pairs the first round did not settle (1/8 to 7/8), so band membership rests on 16 votes."""
    items, reps, size, out = gate_items(), range(VOTES_PER_ORDER), GATE_BATCH, "votes.jsonl"
    if second:
        s1 = first_round_share()
        items = [it for it in items if it["set"] == "v2" and 0 < s1[it["id"]] < 1]
        reps, size, out = range(VOTES_PER_ORDER, 2 * VOTES_PER_ORDER), GATE_BATCH + 1, "votes2.jsonl"
    slots = [(it, his_first, rep) for it in items for his_first in (True, False) for rep in reps]
    batches = pack(slots, size, "gate2" if second else "gate")
    print("gate items", len(items), "slots", len(slots), "calls", len(batches))

    def one(batch):
        body = "".join(render_item(k + 1, it, *((it["his"], it["alt"]) if hf else (it["alt"], it["his"])))
                       for k, (it, hf, _) in enumerate(batch))
        try:
            out = extract_json(call("haiku", "gate", GATE_PROMPT.format(n=len(batch), items=body))) or {}
        except RuntimeError as e:
            print("gate failed", e)
            out = {}
        res = []
        for k, (it, hf, rep) in enumerate(batch):
            v = out.get(str(k + 1)) if isinstance(out, dict) else None
            v = v if v in (1, 2) else None
            res.append({"id": it["id"], "his_first": hf, "rep": rep, "choice": v,
                        "picked_his": None if v is None else (v == 1) == hf})
        return res

    write_jsonl(p(out), [v for res in pmap(one, batches) for v in res])


FAIR_PROMPT = """Below are {n} separate research decisions, each with two options. For each item, say whether one option is clearly weaker on rigor or feasibility: something a competent AI-safety researcher would not seriously propose here (it ignores an obvious confound, overclaims, is infeasible or much costlier for no gain, is vague, or does not address the question). Answer 0 if both are choices a strong researcher could defend, even if you would prefer one of them. Answer 1 or 2 only when that option is clearly weaker.
{items}
Reply with only a JSON object mapping each item number to 0, 1 or 2, e.g. {{"1": 0, "2": 2}}."""


def fair(second=False):
    """First round: every v2 pair, one judgement in a random order. Second round (fair2): band pairs
    again in the opposite order; assemble records fair_strict (both judgements ok)."""
    items, out = [it for it in gate_items() if it["set"] == "v2"], "fairness.jsonl"
    first = {r["id"]: r["his_first"] for r in read_jsonl(p("fairness.jsonl"))}
    if second:
        band = {x["pair_id"] for x in read_jsonl(p("pairs.jsonl")) if x["band"]}
        items, out = [it for it in items if it["id"] in band], "fairness2.jsonl"
    slots = [(it, (not first[it["id"]]) if second else random.Random("fair:" + it["id"]).random() < 0.5, 0)
             for it in items]
    batches = pack(slots, FAIR_BATCH, "fair2" if second else "fair")
    print("fair items", len(items), "calls", len(batches))

    def one(batch):
        body = "".join(render_item(k + 1, it, *((it["his"], it["alt"]) if hf else (it["alt"], it["his"])))
                       for k, (it, hf, _) in enumerate(batch))
        try:
            out = extract_json(call("haiku", "fair", FAIR_PROMPT.format(n=len(batch), items=body))) or {}
        except RuntimeError as e:
            print("fair failed", e)
            out = {}
        res = []
        for k, (it, hf, _) in enumerate(batch):
            v = out.get(str(k + 1)) if isinstance(out, dict) else None
            v = v if v in (0, 1, 2) else None
            flag = None if v is None else ("ok" if v == 0 else ("his_weaker" if (v == 1) == hf else "alt_weaker"))
            res.append({"id": it["id"], "his_first": hf, "answer": v, "fairness": flag})
        return res

    write_jsonl(p(out), [v for res in pmap(one, batches) for v in res])


REAL_PROMPT = """Below are {n} separate research decisions, each with two options. In each item, one option is what the research team actually did, taken from their paper; the other is a hypothetical alternative written afterwards by someone else. For each item, which option was actually done? Judge every item on its own.
{items}
Reply with only a JSON object mapping each item number to 1 or 2, e.g. {{"1": 2, "2": 1}}."""


def real():
    """Realness probe on band pairs: can a blind reader tell the real decision from the written
    alternative (specificity, paper-like detail)? One vote per order."""
    band = {x["pair_id"] for x in read_jsonl(p("band.jsonl"))}
    items = [it for it in gate_items() if it["id"] in band]
    batches = pack([(it, hf, 0) for it in items for hf in (True, False)], GATE_BATCH, "real")
    print("real items", len(items), "calls", len(batches))

    def one(batch):
        body = "".join(render_item(k + 1, it, *((it["his"], it["alt"]) if hf else (it["alt"], it["his"])))
                       for k, (it, hf, _) in enumerate(batch))
        out = extract_json(call("haiku", "real", REAL_PROMPT.format(n=len(batch), items=body))) or {}
        return [{"id": it["id"], "his_first": hf,
                 "picked_his": None if out.get(str(k + 1)) not in (1, 2) else (out[str(k + 1)] == 1) == hf}
                for k, (it, hf, _) in enumerate(batch)]

    write_jsonl(p("realness.jsonl"), [v for res in pmap(one, batches) for v in res])


# ---------------------------------------------------------------- stage 5: assemble

def assemble():
    src = {r["decision_id"]: r for r in read_jsonl(p("sources.jsonl"))}
    cand = {r["decision_id"]: r for r in read_jsonl(p("candidates.jsonl"))}
    votes = collections.defaultdict(list)
    for v in read_jsonl(p("votes.jsonl")) + read_jsonl(p("votes2.jsonl")):
        votes[v["id"]].append(v)
    fair_votes = collections.defaultdict(list)
    for r in read_jsonl(p("fairness.jsonl")) + read_jsonl(p("fairness2.jsonl")):
        fair_votes[r["id"]].append(r["fairness"])
    fairness = {k: v[0] for k, v in fair_votes.items()}  # the spec's one cheap check; fair_strict adds the re-check

    realness = collections.defaultdict(list)
    for v in read_jsonl(p("realness.jsonl")):
        realness[v["id"]].append(v)

    def share(vs):
        valid = [v["picked_his"] for v in vs if v["picked_his"] is not None]
        return (sum(valid) / len(valid) if valid else None), len(valid)

    pairs = []
    for r in read_jsonl(p("rendered.jsonl")):
        d, c = src[r["decision_id"]], cand[r["decision_id"]]
        s, n = share(votes.get(r["pair_id"], []))
        fsrc = next((x["field_source"] for x in c["candidates"] if x["generator"] == r["generator"]), None)
        in_band = s is not None and n >= 6 and BAND[0] <= s <= BAND[1]
        first = [v for v in votes.get(r["pair_id"], []) if v["rep"] < VOTES_PER_ORDER]
        pairs.append({"pair_id": r["pair_id"], "decision_id": r["decision_id"], "doc": d["doc"], "work": d["work"],
                      "date": d["date"], "decision_point": d["point"], "axis": c.get("axis"),
                      "context": r["context"], "question": r["question"], "a_text": r["a_text"],
                      "b_text": r["b_text"], "his_side": r["his_side"], "generator": r["generator"],
                      "generator_family": r["generator"].split(":")[0], "field_source": fsrc,
                      "check_problems": r["problems"], "blind_share": s, "n_votes": n,
                      "band": in_band, "blind_share_round1": share(first)[0],
                      "fairness": fairness.get(r["pair_id"]), "fairness_votes": fair_votes.get(r["pair_id"]),
                      "realness_share": share(realness.get(r["pair_id"], []))[0],
                      "fair_strict": all(f == "ok" for f in fair_votes.get(r["pair_id"], [None])),
                      "usable": in_band and fairness.get(r["pair_id"]) == "ok" and not r["problems"],
                      "decision_origin": d["origin"], "url": d.get("url"), "cutoff": T})
    write_jsonl(p("pairs.jsonl"), pairs)
    band = [x for x in pairs if x["usable"]]
    write_jsonl(p("band.jsonl"), band)

    e2 = [share(vs) for k, vs in votes.items() if k.startswith("e2:")]
    gated = [x for x in pairs if x["blind_share"] is not None]
    hist = collections.Counter(round(x["blind_share_round1"] * 8) for x in gated)
    hist16 = collections.Counter(round(x["blind_share"] * 16) for x in gated if x["n_votes"] == 16)
    fam = collections.defaultdict(lambda: collections.Counter())
    for x in pairs:
        f = fam[x["generator_family"]]
        f["rendered"] += 1
        f["clean"] += not x["check_problems"]
        f["gated"] += x["blind_share"] is not None
        f["band"] += x["band"]
        f["band_fair"] += x["usable"]
        f["lopsided_his"] += x["blind_share"] is not None and x["blind_share"] > 0.8
        f["lopsided_alt"] += x["blind_share"] is not None and x["blind_share"] < 0.2
        f["fair_flag_alt"] += x["fairness"] == "alt_weaker"
        f["fair_flag_his"] += x["fairness"] == "his_weaker"
    by_work = collections.Counter(x["work"] for x in band)
    by_gen = collections.Counter(x["generator"] for x in band)
    mean_share = cluster_ci({w: [x["blind_share"] for x in gated if x["work"] == w]
                             for w in {x["work"] for x in gated}})
    real_votes = [v["picked_his"] for vs in realness.values() for v in vs if v["picked_his"] is not None]
    stats = {
        "sources": {"decisions": len(src), "works": len({d["work"] for d in src.values()}),
                    "by_origin": collections.Counter(d["origin"] for d in src.values())},
        "candidates": collections.Counter(r["status"] for r in cand.values()),
        "pairs_rendered": len(pairs), "pairs_gated": len(gated),
        "blind_share_hist_round1_8votes": {f"{k}/8": hist[k] for k in range(9)},
        "blind_share_hist_16votes (pairs re-voted)": {f"{k}/16": hist16[k] for k in range(17)},
        "mean_blind_share_v2 (90% CI over works)": mean_share,
        "lopsided_v2 (>0.8 either way)": sum(max(x["blind_share"], 1 - x["blind_share"]) > 0.8 for x in gated),
        "e2_owain_recheck": {"n": len(e2), "mean_share": sum(s for s, _ in e2) / len(e2),
                             "lopsided": sum(max(s, 1 - s) > 0.8 for s, _ in e2),
                             "in_band": sum(BAND[0] <= s <= BAND[1] for s, _ in e2)},
        "by_family": {k: dict(v) for k, v in fam.items()},
        "band_by_generator": dict(by_gen), "band_pairs": len(band), "band_works": len(by_work),
        "band_decisions": len({x["decision_id"] for x in band}), "band_by_work": dict(by_work),
        "band_pairs_fair_strict (both fairness judgements ok)": sum(x["fair_strict"] for x in band),
        "band_works_fair_strict": len({x["work"] for x in band if x["fair_strict"]}),
        "band_realness (share of votes picking his option as the real one)": {
            "n_votes": len(real_votes), "share": sum(real_votes) / len(real_votes) if real_votes else None},
        "band_his_side": collections.Counter(x["his_side"] for x in band),
        "calls": {m: real_calls(m) for m in CAPS},
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in read_jsonl(p("calls.log"))), 2),
    }
    with open(p("stats.json"), "w") as f:
        json.dump(stats, f, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(stats, indent=1, default=str))


if __name__ == "__main__":
    {"sources": sources, "generate": generate, "render": render, "gate": gate, "fair": fair,
     "gate2": lambda: gate(True), "fair2": lambda: fair(True), "real": real,
     "assemble": assemble}[sys.argv[1]]()
