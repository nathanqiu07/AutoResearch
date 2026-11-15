"""Post-T lineup test of profile compressions (pre-registered in prereg/compression.md §4).

usage: python3 run.py {select,build,neutralize,lineup,score,all}

Every real `claude -p --model haiku` call is logged to calls.log and cached in cache/ by prompt hash;
the script refuses to make call 101.
"""
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
from autoresearch.taste.methods.common import cluster_principles, selected_history  # noqa: E402
from autoresearch.taste.timesplit import front_matter, read_doc  # noqa: E402

PROFILES = os.path.join(ROOT, "experiments", "taste_petri", "profiles")
SLUGS = ["evan_hubinger", "samuel_bowman", "owain_evans", "ryan_greenblatt", "buck_shlegeris"]
NAMES = {"evan_hubinger": "Evan Hubinger", "samuel_bowman": "Samuel Bowman", "owain_evans": "Owain Evans",
         "ryan_greenblatt": "Ryan Greenblatt", "buck_shlegeris": "Buck Shlegeris"}
T = "2025-04-01"
CAP = 100
MAX_WORDS = 250
ARMS = ["NAMES", "EX", "M3", "A_pre", "A_full", "E_pre", "E_full", "DIFF"]
RUNS = {"L1": ("full", 1, ARMS), "L2": ("method_only", 2, ["NAMES", "M3", "A_pre", "E_pre", "DIFF"]),
        "L3": ("full", 3, ["A_pre"])}
LOCK = threading.Lock()


def path(*parts):
    p = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def write_json(rel, obj):
    with open(path(rel), "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def read_json(rel):
    with open(path(rel)) as f:
        return json.load(f)


def write_jsonl(rel, rows):
    with open(path(rel), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(rel):
    with open(path(rel)) as f:
        return [json.loads(line) for line in f if line.strip()]


def words(text):
    return len(text.split())


# ---------------------------------------------------------------- LLM calls

def real_calls():
    if not os.path.exists(path("calls.log")):
        return 0
    with open(path("calls.log")) as f:
        return sum(1 for line in f if "status=started" in line)


def llm(prompt, step, arm="-", attempt=0):
    """One haiku call through the local CLI, cached on disk by prompt hash (+attempt for retries)."""
    key = hashlib.sha256(("haiku\n%d\n%s" % (attempt, prompt)).encode()).hexdigest()
    cpath = path("cache", key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    with LOCK:
        n = real_calls()
        if n >= CAP:
            raise RuntimeError("call cap %d reached; refusing call %d" % (CAP, n + 1))
        with open(path("calls.log"), "a") as f:  # reserve the slot before the call
            f.write("%s step=%s arm=%s attempt=%d key=%s status=started\n"
                    % (time.strftime("%Y-%m-%dT%H:%M:%S"), step, arm, attempt, key[:12]))
    cmd = ["claude", "-p", "--model", "haiku", "--output-format", "json", "--tools", "", "--strict-mcp-config",
           "--no-session-persistence", "--setting-sources", "",
           "--system-prompt", "You are a careful assistant. Follow the output format exactly."]
    with tempfile.TemporaryDirectory(prefix="ce_cli_") as cwd:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600, cwd=cwd)
    with LOCK, open(path("calls.log"), "a") as f:
        f.write("%s step=%s arm=%s attempt=%d key=%s exit=%d\n"
                % (time.strftime("%Y-%m-%dT%H:%M:%S"), step, arm, attempt, key[:12], proc.returncode))
    data = json.loads(proc.stdout)
    if proc.returncode != 0 or data.get("is_error"):
        raise RuntimeError("claude CLI error: %s" % str(data.get("result"))[:300])
    result = data["result"]
    with open(cpath, "w") as f:
        json.dump({"step": step, "arm": arm, "attempt": attempt, "prompt": prompt, "result": result}, f,
                  ensure_ascii=False)
    return result


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def llm_json(prompt, step, arm="-", check=lambda obj: True):
    """Parse failure (or failed check) is retried once with a fresh call."""
    for attempt in (0, 1):
        raw = llm(prompt, step, arm, attempt)
        try:
            obj = parse_json(raw)
            if check(obj):
                return obj, raw, attempt
        except (ValueError, KeyError, TypeError):
            pass
    raise ValueError("unparseable after retry: %s %s\n%s" % (step, arm, raw[:500]))


# ---------------------------------------------------------------- masking

PERSON_EXTRA = ["Evan", "Samuel", "Sam", "Owain", "Ryan", "Buck", "Marius", "evhub", "sleepinyourhat",
                "OwainEvans_UK", "OwainEvans", "ryan_greenblatt", "Owain_Evans", "Hobbhahn"]
ORGS = ["Redwood Research", "Redwood", "Truthful AI", "Truthful.ai", "TruthfulAI", "Anthropic", "OpenAI", "AXRP",
        "80,000 Hours", "80000 Hours", "DeepMind", "Google", "GDM", "Apollo Research", "Apollo", "METR", "MIRI",
        "FAR.AI", "FAR AI", "UK AISI", "AISI", "NYU", "New York University", "Oxford", "Berkeley", "Stanford",
        "MATS", "Constellation", "LessWrong", "Alignment Forum", "Substack", "Hugging Face", "Huggingface",
        "Meta", "Microsoft", "xAI", "Thinking Machines", "Tinker", "ControlConf", "Asterisk"]
MODELS = ["ChatGPT", "Claude", "GPT", "Llama", "Qwen", "Gemini", "Sonnet", "Opus", "Haiku", "Bing", "Sydney",
          "Kimi", "DeepSeek", "Mistral", "Grok", "o1", "o3", "o4-mini", "4o"]
# Coined project / paper names that identify an author via haiku's prior. Case-sensitive, so the lowercase
# topic phrase ("emergent misalignment") stays visible as the protocol intends for full summaries.
WORKS = ["Sleeper Agents", "Alignment Faking", "alignment faking in large language models",
         "Risks from Learned Optimization", "Model Organisms of Misalignment", "Conditioning Predictive Models",
         "Ctrl-Z", "Emergent Misalignment", "Reversal Curse", "TruthfulQA", "Sycophancy to Subterfuge",
         "Agentic Misalignment", "Constitutional AI", "AuditBench", "SHADE-Arena", "BashBench", "LinuxArena",
         "SNLI", "MultiNLI", "SuperGLUE", "GLUE", "BIG-bench", "Inverse Scaling", "Measuring Progress on Scalable "
         "Oversight", "Subliminal Learning", "Thought Crime", "Persona Vectors", "Weird Generalization",
         "Inductive Backdoors", "Negation Neglect", "Story Imprinting", "Concept Poisoning", "School of Reward Hacks",
         "Activation Oracles", "Consciousness Cluster", "Situational Awareness Dataset", "Looking Inward",
         "Tell me about yourself", "Taken out of context", "Bumpers", "IDSS", "Prefix cache", "IABIED",
         "Open Character Training", "Litmus", "Petri", "Bloom", "Pilot Anthropic"]
COMMON_WORDS = {"Long", "Rule", "Price", "Power", "Constant", "Frank", "Fort", "Fish", "Cloud", "Stone", "Ward",
                "Hill", "Hills", "May", "Marks", "Ringer", "Song", "Noble", "Bloom", "Droid", "Rein", "Rules",
                "Baker", "Brown", "Stan", "Gal", "Rous", "Mann", "Will", "Wills", "Hume", "Kale", "Rush",
                "Tracy", "Troy", "Casey", "Cain", "Engel", "Constant", "Turner", "Wagner", "Abate", "Barnes",
                "Gould", "Hanson", "Israel", "Joseph", "Michael", "Simon", "Thomas", "Gabriel", "Valentine",
                "Graham", "Howard", "Lewis", "Lucas", "Hudson", "Russell", "Mitchell", "Taylor", "Walker",
                "Griffin", "Cameron", "Ross", "Clark", "Smith", "Miller", "Jones", "Dunn", "Kerr", "Roger",
                "Russell", "Einstein", "Novak", "Popp", "Seid", "Sie", "Wet", "Siro", "Stein", "Hoeve",
                "Durme", "Merwijk", "Weij", "Heide", "Taal", "Loe", "Bello", "Oli", "Dour", "Gruetter"}


def corpus_authors():
    people, surnames = set(), set()
    for s in SLUGS:
        for p in glob.glob(os.path.join(ROOT, "data", "researchers", s, "corpus", "*.txt")):
            try:
                names = json.loads(front_matter(p).get("authors", "[]"))
            except ValueError:
                continue
            for n in names:
                parts = n.replace(".", " ").split()
                if len(parts) >= 2 and len(n) >= 6:
                    people.add(" ".join(n.split()))
                if parts and len(parts[-1]) >= 4 and parts[-1][0].isupper() and parts[-1].isalpha():
                    surnames.add(parts[-1])
    return sorted(people), sorted(surnames - COMMON_WORDS)


def build_mask():
    banned = []
    for s in SLUGS:
        with open(os.path.join(ROOT, "data", "researchers", s, "identity.json")) as f:
            ident = json.load(f)
        banned += ident["banned"] + [ident["name"]] + ident.get("exclude_text", [])
    people, surnames = corpus_authors()
    mask = {"person_ci": sorted(set(banned)), "person_cs": sorted(set(PERSON_EXTRA + surnames)),
            "people_full": people, "org": ORGS, "model": MODELS, "work": WORKS}
    write_json("mask.json", mask)
    return mask


def _alt(strings):
    strings = sorted(set(strings), key=len, reverse=True)
    return "|".join(re.escape(s) for s in strings)


def mask_patterns(mask):
    b = r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])"
    return [
        ("[PERSON]", re.compile(b % _alt(mask["people_full"] + mask["person_ci"]), re.I)),
        ("[CITATION]", re.compile(r"\b[A-Z][A-Za-z'\-]+ (?:and [A-Z][A-Za-z'\-]+ )?et al\.?(?:,? ?\(?\d{4}[a-z]?\)?)?")),
        ("[WORK]", re.compile(b % _alt(mask["work"]))),
        ("[ORG]", re.compile(b % _alt(mask["org"]))),
        ("[MODEL]", re.compile(r"(?<![A-Za-z0-9])(?:%s)(?:[-‑ ]?[0-9][0-9A-Za-z.\-]*)?(?![A-Za-z0-9])"
                               % _alt(mask["model"]))),
        ("[PERSON]", re.compile(b % _alt(mask["person_cs"]))),
        ("[HANDLE]", re.compile(r"@[A-Za-z0-9_]{2,}")),
    ]


def apply_mask(text, pats):
    for token, pat in pats:
        text = pat.sub(token, text)
    return text


def leak_hits(text, pats, extra=()):
    hits = []
    for token, pat in pats:
        hits += [m.group(0) for m in pat.finditer(text)]
    low = text.lower()
    hits += [e for e in extra if e in low]
    return hits


def title_ngrams(title, n=4):
    toks = re.findall(r"[a-z0-9]+", title.lower())
    stop = {"the", "a", "an", "of", "in", "on", "for", "and", "to", "with", "is", "are", "by", "from", "can"}
    grams = set()
    for i in range(len(toks) - n + 1):
        g = toks[i:i + n]
        if sum(t not in stop for t in g) >= 3:
            grams.add(" ".join(g))
    return grams


def norm_text(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


# ---------------------------------------------------------------- step 0: select

def select():
    corpora = {}
    url_count, title_count = {}, {}
    for s in SLUGS:
        docs = []
        for p in sorted(glob.glob(os.path.join(ROOT, "data", "researchers", s, "corpus", "*.txt"))):
            fm = front_matter(p)
            docs.append((p, fm))
        corpora[s] = docs
        for u in {fm.get("url", "") for _, fm in docs}:
            url_count[u] = url_count.get(u, 0) + 1
        for t in {fm.get("title", "").lower()[:60] for _, fm in docs}:
            title_count[t] = title_count.get(t, 0) + 1
    rows, notes = [], {}
    for s in SLUGS:
        elig = []
        for p, fm in corpora[s]:
            date, body = read_doc(p)
            if date is None or str(date) < T:
                continue
            title = fm.get("title", "")
            if url_count[fm.get("url", "")] != 1 or title_count[title.lower()[:60]] != 1:
                continue
            if fm.get("author_position") == "middle" or "hobbhahn" in fm.get("authors", "").lower():
                continue
            if re.search(r"AXRP|podcast|episode|#\d+|80,000 Hours|interview", title, re.I) or len(body) < 3000:
                continue
            elig.append({"doc_id": os.path.basename(p)[:-4], "slug": s, "date": str(date),
                         "author_position": fm.get("author_position"), "title": title,
                         "path": os.path.relpath(p, ROOT)})
        elig.sort(key=lambda r: (r["date"], r["doc_id"]))
        n = len(elig)
        k = min(5, n)
        idx = sorted({round(i * (n - 1) / 4) for i in range(5)}) if n >= 5 else list(range(n))
        rows += [elig[i] for i in idx]
        notes[s] = {"eligible": n, "taken": len(idx)}
        assert len(idx) == k
    write_jsonl("heldout/docs.jsonl", rows)
    write_json("heldout/select_notes.json", notes)
    print(json.dumps(notes))


# ---------------------------------------------------------------- step 1: build

def norm_d(d):
    m = re.match(r"D\d", d or "")
    return m.group(0) if m else ""


def evidence(slug):
    rows = [json.loads(line) for line in open(os.path.join(PROFILES, slug, "evidence.jsonl"))]
    return [r for r in rows if r.get("date") and r["date"] < T]


def truncate(text, limit=MAX_WORDS):
    """Cut at a line boundary; a single over-long line is cut at a sentence boundary."""
    out, n = [], 0
    for line in text.strip().splitlines():
        if n + words(line) > limit:
            if not out or not "".join(out).strip():
                sents = re.split(r"(?<=[.!?])\s+", line)
                part = []
                for s in sents:
                    if n + words(s) > limit:
                        break
                    part.append(s)
                    n += words(s)
                out.append(" ".join(part))
            break
        out.append(line)
        n += words(line)
    return "\n".join(out).strip()


class Row:
    def __init__(self, identity, context, a, b, chosen):
        self.identity, self.context, self.a, self.b, self.chosen = identity, context, a, b, chosen


class _M3Config:
    config = {}
    seed = 0


def build_m3(slug, pre_all, pats, prompts):
    rng = random.Random(0)
    target = [r for r in pre_all[slug] if r["kind"] in ("principle", "heuristic", "distrust")]
    rows = []
    for r in target:
        d = norm_d(r["dpoint"])
        peers = [p for s in SLUGS if s != slug for p in pre_all[s]
                 if p["kind"] in ("principle", "heuristic", "distrust") and norm_d(p["dpoint"]) == d]
        if not peers:
            continue
        peer = rng.choice(peers)
        mine, other = apply_mask(r["claim"], pats), apply_mask(peer["claim"], pats)
        if rng.random() < .5:
            rows.append(Row("%s:%s" % (slug, r["id"]), "At decision point %s, which position does this researcher "
                            "hold?" % d, mine, other, "a"))
        else:
            rows.append(Row("%s:%s" % (slug, r["id"]), "At decision point %s, which position does this researcher "
                            "hold?" % d, other, mine, "b"))
    chosen_rows = selected_history(_M3Config(), rows)
    choices = {"C%d" % (i + 1): {"context": r.context, "a": r.a, "b": r.b, "chosen": r.chosen}
               for i, r in enumerate(chosen_rows)}
    obj, raw1, _ = llm_json(prompts["m3_propose"].replace("{CHOICES}", json.dumps(choices, indent=1)),
                            "build", "M3:%s:propose" % slug,
                            check=lambda o: all(isinstance(o.get(c), list) and 1 <= len(o[c]) <= 2 for c in choices))
    proposals, provenance = [], []
    for c in choices:
        for p in obj[c]:
            proposals.append(p.strip())
            provenance.append({"history_id": c, "principle": p.strip()})
    clusters = cluster_principles(proposals, .75)
    reps = {"R%d" % (i + 1): c["representative"] for i, c in enumerate(clusters)}
    pairs = {c: {"context": v["context"], "a": v["a"], "b": v["b"]} for c, v in choices.items()}
    prompt2 = prompts["m3_reconstruct"].replace("{PRINCIPLES}", json.dumps(reps, indent=1)) \
        .replace("{CHOICES}", json.dumps(pairs, indent=1))
    mat, raw2, _ = llm_json(prompt2, "build", "M3:%s:reconstruct" % slug,
                            check=lambda o: all(o.get(r, {}).get(c) in ("a", "b") for r in reps for c in choices))
    scored = []
    for i, (rid, principle) in enumerate(reps.items()):
        acc = sum(mat[rid][c] == choices[c]["chosen"] for c in choices) / len(choices)
        scored.append({"principle": principle, "accuracy": acc, "support": len(clusters[i]["members"]),
                       "representative_index": clusters[i]["representative_index"]})
    scored.sort(key=lambda item: (-item["accuracy"], -item["support"], item["representative_index"]))
    kept = [s["principle"] for s in scored[:5]]
    write_json("profiles/%s/m3_trace.json" % slug, {
        "pseudo_choices_total": len(rows), "selected": [{"id": c, "identity": r.identity, **choices[c]}
                                                         for c, r in zip(choices, chosen_rows)],
        "proposals": provenance, "clusters": clusters, "reconstruction_matrix": mat, "scored": scored,
        "kept": kept, "raw_propose": raw1, "raw_reconstruct": raw2})
    return "\n".join("- " + apply_mask(p, pats) for p in kept)


def a_blocks(slug):
    text = open(os.path.join(PROFILES, slug, "a_principles.md")).read()
    blocks = re.split(r"\n(?=\d+\. \*\*)", text)
    out = []
    for b in blocks:
        m = re.match(r"(\d+)\. \*\*(.+?)\*\*", b)
        if m:
            out.append({"n": int(m.group(1)), "headline": m.group(2).strip(),
                        "dates": re.findall(r"\((\d{4}-\d{2}-\d{2});", b)})
    return out


def build():
    mask = build_mask()
    pats = mask_patterns(mask)
    prompts = {n[:-4]: open(path("prompts", n)).read() for n in os.listdir(os.path.join(HERE, "prompts"))
               if n.endswith(".txt")}
    pre_all = {s: evidence(s) for s in SLUGS}
    profiles = {s: {} for s in SLUGS}
    jobs = []
    for s in SLUGS:
        pre = pre_all[s]
        profiles[s]["NAMES"] = "Researcher: %s" % NAMES[s]
        # EX
        kinds = [r for r in pre if r["kind"] in ("principle", "heuristic", "distrust", "realism_move")]
        kinds.sort(key=lambda r: r["date"], reverse=True)
        kinds.sort(key=lambda r: (-int(r.get("relevance") or 0), r.get("author_position") == "middle"))
        lines, n = [], 0
        for r in kinds:
            line = '- (%s) "%s"' % (norm_d(r["dpoint"]) or "D?", apply_mask(r["quote"], pats))
            if n + words(line) > MAX_WORDS:
                break
            lines.append(line)
            n += words(line)
        profiles[s]["EX"] = "\n".join(lines)
        # A_pre / A_full
        blocks = a_blocks(s)
        for arm, keep in (("A_full", blocks), ("A_pre", [b for b in blocks if any(d < T for d in b["dates"])])):
            profiles[s][arm] = truncate("\n".join("- " + apply_mask(b["headline"], pats) for b in keep))
        # E_full
        e = open(os.path.join(PROFILES, s, "e_taste_vector.md")).read()
        e = re.sub(r"<!--.*?-->", "", e, flags=re.S)
        e = re.sub(r"^## .*$", "", e, flags=re.M)
        profiles[s]["E_full"] = truncate(apply_mask(e.strip(), pats))
        claims = "\n".join("- (%s) %s" % (norm_d(r["dpoint"]) or "D?", apply_mask(r["claim"], pats)) for r in pre)
        jobs.append((s, "E_pre", prompts["e_pre"].replace("{EVIDENCE}", claims)))
        rng = random.Random(0)
        peer_pool = [r for p in SLUGS if p != s for r in pre_all[p]]
        peers = rng.sample(peer_pool, 60)
        peer_text = "\n".join("- " + apply_mask(r["claim"], pats) for r in peers)
        jobs.append((s, "DIFF", prompts["diff"].replace("{TARGET}", claims).replace("{PEERS}", peer_text)))
        jobs.append((s, "M3", None))

    def run(job):
        s, arm, prompt = job
        if arm == "M3":
            return s, arm, build_m3(s, pre_all, pats, prompts)
        return s, arm, llm(prompt, "build", "%s:%s" % (arm, s)).strip()

    with ThreadPoolExecutor(4) as ex:
        for s, arm, text in ex.map(run, jobs):
            profiles[s][arm] = text
    report = {}
    for s in SLUGS:
        for arm in ARMS:
            raw = profiles[s][arm]
            text = raw if arm == "NAMES" else truncate(apply_mask(raw, pats))
            hits = [] if arm == "NAMES" else leak_hits(raw, pats)
            post = [] if arm == "NAMES" else leak_hits(text, pats)
            with open(path("profiles", s, arm + ".md"), "w") as f:
                f.write(text + "\n")
            report.setdefault(s, {})[arm] = {"words": words(text), "raw_words": words(raw),
                                             "mask_hits_before_remask": hits, "mask_hits_after": post}
        report[s]["pre_T_evidence"] = len(pre_all[s])
        report[s]["a_blocks_total"] = len(a_blocks(s))
        report[s]["a_blocks_pre"] = sum(any(d < T for d in b["dates"]) for b in a_blocks(s))
    write_json("profiles/build_report.json", report)
    print(json.dumps({s: {a: report[s][a]["words"] for a in ARMS} for s in SLUGS}, indent=1))


def load_profiles():
    return {s: {a: open(path("profiles", s, a + ".md")).read().strip() for a in ARMS} for s in SLUGS}


# ---------------------------------------------------------------- step 2: neutralize

def neutralize():
    mask = read_json("mask.json")
    pats = mask_patterns(mask)
    any_mask = re.compile("|".join(p.pattern for _, p in pats if _ != "[CITATION]"), re.I)
    prompt_t = open(path("prompts", "neutralize.txt")).read()
    docs = read_jsonl("heldout/docs.jsonl")
    inputs, stats = {}, {}
    for d in docs:
        _, body = read_doc(os.path.join(ROOT, d["path"]))
        kept = "\n".join(line for line in body.splitlines() if not any_mask.search(line))
        stats[d["doc_id"]] = {"body_chars": len(body), "kept_chars": len(kept)}
        inputs[d["doc_id"]] = kept[:6000]
    write_json("heldout/neutralize_input_stats.json", stats)

    def run(slug):
        mine = [d for d in docs if d["slug"] == slug]
        block = "\n\n".join("=== DOC %s ===\n%s" % (d["doc_id"], inputs[d["doc_id"]]) for d in mine)
        # haiku sometimes "repairs" truncated words inside a doc id, so match ids on their hash suffix
        def by_hash(o):
            return {k.rsplit("_", 1)[-1]: v for k, v in o.items()}

        def ok(o):
            o = by_hash(o)
            return all(isinstance(o.get(d["doc_id"].rsplit("_", 1)[-1]), dict) and
                       o[d["doc_id"].rsplit("_", 1)[-1]].get("full") and
                       o[d["doc_id"].rsplit("_", 1)[-1]].get("method_only") for d in mine)
        obj, raw, attempt = llm_json(prompt_t.replace("{DOCS}", block), "neutralize", slug, check=ok)
        obj = by_hash(obj)
        return slug, {d["doc_id"]: obj[d["doc_id"].rsplit("_", 1)[-1]] for d in mine}

    with ThreadPoolExecutor(4) as ex:
        results = dict(ex.map(run, SLUGS))
    # leak check: mask regex (names, co-authors, orgs, models, coined work names) + held-out title 4-grams
    out = []
    for d in docs:
        res = results[d["slug"]][d["doc_id"]]
        grams = title_ngrams(re.sub(r"\s*[|\-—–].*$", "", d["title"]) if len(d["title"]) > 30 else d["title"])
        row = {"doc_id": d["doc_id"], "slug": d["slug"]}
        for field in ("full", "method_only"):
            raw = res[field].strip()
            hits = leak_hits(raw, pats) + [g for g in grams if g in norm_text(raw)]
            row[field + "_raw"] = raw
            row[field] = apply_mask(raw, pats)
            row[field + "_words"] = words(raw)
            row.setdefault("leak_hits", {})[field] = hits
        out.append(row)
    write_jsonl("heldout/summaries.jsonl", out)
    print(json.dumps({r["doc_id"][:40]: r["leak_hits"] for r in out}, indent=1))


# ---------------------------------------------------------------- step 3: lineup

def batches(seed, n_docs=25):
    rng = random.Random(seed)
    order = list(range(n_docs))
    rng.shuffle(order)
    out = []
    for b in range(5):
        perm = rng.sample(SLUGS, 5)
        out.append((order[b * 5:(b + 1) * 5], perm))
    return out


def lineup():
    profiles = load_profiles()
    sums = read_jsonl("heldout/summaries.jsonl")
    assert len(sums) == 25
    prompt_t = open(path("prompts", "lineup.txt")).read()
    jobs = []
    for run, (field, seed, arms) in RUNS.items():
        for arm in arms:
            for b, (idx, perm) in enumerate(batches(seed)):
                jobs.append((run, field, arm, b, idx, perm))

    def go(job):
        run, field, arm, b, idx, perm = job
        prof = "\n\n".join("P%d:\n%s" % (i + 1, profiles[s][arm]) for i, s in enumerate(perm))
        summ = "\n\n".join("S%d: %s" % (i + 1, sums[j][field]) for i, j in enumerate(idx))
        prompt = prompt_t.replace("{PROFILES}", prof).replace("{SUMMARIES}", summ)
        labels = ["P%d" % (i + 1) for i in range(5)]

        def ok(o):
            return all(all(isinstance(o["S%d" % (i + 1)].get(p), (int, float)) for p in labels) for i in range(5))
        obj, raw, attempt = llm_json(prompt, "lineup", "%s:%s:b%d" % (run, arm, b), check=ok)
        rows = []
        for i, j in enumerate(idx):
            probs = {perm[k]: max(0., float(obj["S%d" % (i + 1)]["P%d" % (k + 1)])) for k in range(5)}
            z = sum(probs.values()) or 1.
            rows.append({"doc_id": sums[j]["doc_id"], "true": sums[j]["slug"],
                         "p": {s: probs[s] / z for s in SLUGS}, "row_sum_raw": z})
        write_json("lineup/%s_%s_b%d.json" % (run, arm, b),
                   {"run": run, "arm": arm, "batch": b, "field": field, "doc_index": idx,
                    "label_order": perm, "attempts": attempt + 1, "raw": raw, "parsed": rows})
        return rows

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(go, jobs))


# ---------------------------------------------------------------- step 4: score

def binom_tail(k, n, p=.2):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def sign_test(wins, losses):
    n = wins + losses
    if n == 0:
        return 1.
    k = max(wins, losses)
    return min(1., 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def top1(p, true):
    m = max(p.values())
    tops = [s for s in SLUGS if p[s] == m]
    return (1. / len(tops)) if true in tops else 0., tops


def score():
    sums = read_jsonl("heldout/summaries.jsonl")
    res = {"runs": {}, "comparisons": {}}
    per_doc = {}
    for run, (field, seed, arms) in RUNS.items():
        for arm in arms:
            rows = []
            for b in range(5):
                rows += read_json("lineup/%s_%s_b%d.json" % (run, arm, b))["parsed"]
            rows.sort(key=lambda r: r["doc_id"])
            assert len(rows) == 25
            hits, picks, pt, ll = [], {s: 0. for s in SLUGS}, [], []
            conf = {t: {s: 0. for s in SLUGS} for t in SLUGS}
            hard = {"greenblatt_shlegeris": [], "hubinger_bowman": []}
            for r in rows:
                h, tops = top1(r["p"], r["true"])
                hits.append(h)
                for s in tops:
                    picks[s] += 1. / len(tops)
                    conf[r["true"]][s] += 1. / len(tops)
                pt.append(r["p"][r["true"]])
                ll.append(-math.log(max(r["p"][r["true"]], 1e-3)))
                for key, pair in (("greenblatt_shlegeris", ("ryan_greenblatt", "buck_shlegeris")),
                                  ("hubinger_bowman", ("evan_hubinger", "samuel_bowman"))):
                    if r["true"] in pair:
                        z = r["p"][pair[0]] + r["p"][pair[1]]
                        hard[key].append(r["p"][r["true"]] / z if z else .5)
            rng = random.Random(0)
            boots = sorted(sum(rng.choice(hits) for _ in hits) / len(hits) for _ in range(10000))
            k = round(sum(hits))
            res["runs"].setdefault(run, {})[arm] = {
                "top1": sum(hits) / 25, "top1_correct": sum(hits),
                "top1_ci95": [boots[249], boots[9749]], "p_vs_chance_binom": binom_tail(k, 25),
                "mean_p_true": sum(pt) / 25, "log_loss": sum(ll) / 25,
                "hard_pair": {key: {"n": len(v), "mean_ratio": sum(v) / len(v) if v else None,
                                    "acc": sum(x > .5 for x in v) / len(v) if v else None,
                                    "ties": sum(x == .5 for x in v)} for key, v in hard.items()},
                "collapse": max(picks.values()) / 25, "picks": picks, "confusion": conf}
            per_doc[(run, arm)] = {r["doc_id"]: (h, top1(r["p"], r["true"])[1]) for r, h in zip(rows, hits)}
    # noise floor: top-1 pick flips between L1 and L3 for A_pre
    a, b = per_doc[("L1", "A_pre")], per_doc[("L3", "A_pre")]
    flips = sum(a[d][1] != b[d][1] for d in a)
    res["noise_floor"] = {"pick_flip_rate": flips / 25, "flips": flips,
                          "top1_L1": res["runs"]["L1"]["A_pre"]["top1"], "top1_L3": res["runs"]["L3"]["A_pre"]["top1"]}

    def compare(run_x, x, run_y, y):
        dx, dy = per_doc[(run_x, x)], per_doc[(run_y, y)]
        wins = sum(dx[d][0] == 1 and dy[d][0] == 0 for d in dx)
        losses = sum(dx[d][0] == 0 and dy[d][0] == 1 for d in dx)
        gap = res["runs"][run_x][x]["top1"] - res["runs"][run_y][y]["top1"]
        return {"gap_top1": gap, "x_only_right": wins, "y_only_right": losses, "sign_p": sign_test(wins, losses),
                "gap_mean_p_true": res["runs"][run_x][x]["mean_p_true"] - res["runs"][run_y][y]["mean_p_true"],
                "within_noise_floor": abs(gap) <= res["noise_floor"]["pick_flip_rate"]}
    c = res["comparisons"]
    for run in ("L1", "L2"):
        c["M3_vs_A_pre_" + run] = compare(run, "M3", run, "A_pre")
        c["A_pre_vs_E_pre_" + run] = compare(run, "A_pre", run, "E_pre")
        for arm in RUNS[run][2]:
            if arm != "NAMES":
                c["%s_vs_NAMES_%s" % (arm, run)] = compare(run, arm, run, "NAMES")
    c["leak_A_full_minus_A_pre_L1"] = compare("L1", "A_full", "L1", "A_pre")
    c["leak_E_full_minus_E_pre_L1"] = compare("L1", "E_full", "L1", "E_pre")
    ranking = {arm: (res["runs"]["L1"][arm]["top1"] + res["runs"]["L2"][arm]["top1"]) / 2
               for arm in ("EX", "M3", "E_pre", "DIFF", "A_pre") if arm in res["runs"]["L2"]}
    res["ranking_mean_L1_L2_top1"] = dict(sorted(ranking.items(), key=lambda kv: -kv[1]))
    res["ranking_note"] = "EX has no L2 run in the protocol, so it is ranked on L1 only below."
    res["value_over_names"] = {arm: (c.get("%s_vs_NAMES_L1" % arm, {}).get("gap_top1", 0) > 0 and
                                     c.get("%s_vs_NAMES_L2" % arm, {}).get("gap_top1", -1) > 0)
                               for arm in ("M3", "A_pre", "E_pre", "DIFF")}
    res["calls"] = real_calls_by_step()
    res["build_report"] = read_json("profiles/build_report.json")
    res["summary_leaks"] = {s["doc_id"]: s["leak_hits"] for s in sums}
    write_json("results.json", res)
    print(json.dumps({r: {a: (v["top1"], round(v["mean_p_true"], 3)) for a, v in arms.items()}
                      for r, arms in res["runs"].items()}, indent=1))
    print(json.dumps(res["noise_floor"]), json.dumps(res["calls"]))


def real_calls_by_step():
    out = {"total": 0}
    if os.path.exists(path("calls.log")):
        for line in open(path("calls.log")):
            if "exit=" in line:
                step = re.search(r"step=(\S+)", line).group(1)
                out[step] = out.get(step, 0) + 1
                out["total"] += 1
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"select": select, "build": build, "neutralize": neutralize, "lineup": lineup, "score": score}
    for name in (list(steps) if cmd == "all" else [cmd]):
        steps[name]()
