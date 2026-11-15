"""Owain Evans's informal pre-T material (T = 2026-01-01) and the research decisions in it.

    python3 experiments/taste_petri/informal/build.py collect   # raw/ + corpus -> texts/, sources.jsonl, dropped.jsonl
    python3 experiments/taste_petri/informal/build.py extract   # one sonnet call per source group (cached)
    python3 experiments/taste_petri/informal/build.py speaker   # haiku speaker check for unlabeled transcripts (cached)
    python3 experiments/taste_petri/informal/build.py assemble  # quote + speaker verification -> decisions.jsonl, stats.json

raw/ holds what was fetched by hand (axrp.net and theinsideview.ai over HTTP, YouTube auto-captions via Exa,
threadreaderapp over HTTP, LessWrong comments via the public GraphQL API). Every real CLI call is logged to
calls.log and cached in cache/ by prompt hash; the caps count started calls per model, so reruns cost nothing.
"""
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
from autoresearch.llm import extract_json
from autoresearch.taste.timesplit import _FIELDS, normalize_for_quote, quote_in_text

T = "2026-01-01"
CAPS = {"sonnet": 120, "haiku": 100}
WORKERS, MAX_CHARS, BATCH_CHARS, CHUNK_CHARS = 3, 160_000, 15_000, 32_000
LOCK = threading.Lock()
CORPUS = os.path.join(ROOT, "data", "researchers", "owain_evans", "corpus")
LW_ID = "spJZRySQgiKAFTtHp"  # LessWrong userId of Owain_Evans
SHORTFORM_POST, AMA_POST = "iZgdRAmFSej7tFqEg", "mwTEMHKv9tG9HxFXD"
# Work Hobbhahn co-authored, discussed in otherwise-clean sources: items about it are dropped.
HOBBHAHN_WORK = re.compile(r"(?i:hobbhahn|situational awareness dataset|me, myself,? and ai|should we publish mechanistic)|\bSAD\b")

# The Inside View's transcript opens with highlights + the SAD section (SAD is co-authored by Hobbhahn); only the
# part from the Out-of-Context Reasoning heading (Connecting the Dots, Twitter questions) is sent for extraction.
EXTRACT_FROM = {"pod_insideview": "\nOut-of-Context Reasoning\n"}
PODCASTS = [
    # id, raw file, url, date, title, host, speaker labels (owain_label, host_label regex) or None
    ("pod_axrp42", "axrp42.txt", "https://axrp.net/episode/2025/06/06/episode-42-owain-evans-llm-psychology.html",
     "2025-06-06", "AXRP 42 - Owain Evans on LLM Psychology", "Daniel Filan",
     (r"^Owain Evans \(\d", r"^Daniel Filan \(\d")),
    ("pod_insideview", "insideview.txt", "https://theinsideview.ai/owain", "2024-08-23",
     "The Inside View - Owain Evans on Situational Awareness", "Michael Trazzi", (r"^Owain:", r"^Michaël:")),
    ("pod_tds", "tds_yt.txt", "https://www.youtube.com/watch?v=dea1XQojRmw", "2021-01-13",
     "Towards Data Science podcast - Owain Evans: Predicting the future of AI (auto-captions)", "Jeremie Harris", None),
    ("pod_quri", "quri_yt.txt", "https://www.youtube.com/watch?v=o6CjRA2KpX0", "2023-04-30",
     "QURI - Discussion with Owain Evans on Language Models (auto-captions)", "Ozzie Gooen", None),
]
CORPUS_DOCS = [
    # id, corpus file substring, register, in the paper training set (profiles_contrastive/decisions_pre_t.jsonl)?
    ("ama_post", "ama_on_truthful_ai", "ama", False),
    ("ideas_2021", "ai_safety_research_project_ideas", "ideas", True),
    ("advice_slides", "tips_on_empirical_research_slides", "advice", True),
    ("thread_em", "thread_by_owainevans_uk_researchers_finetuned", "thread", True),
]
THREADS = [  # threadreaderapp ids; date from the tweet-id snowflake
    ("thread_instructgpt", "1496499142306246665", "InstructGPT alignment-failure probing thread"),
    ("thread_reversal", "1705285631520407821", "Reversal Curse paper thread"),
    ("thread_introspection", "1847293315139715104", "Looking Inward (introspection) paper thread"),
    ("thread_weirdgen", "1999172920506269783", "Weird generalization and inductive backdoors paper thread"),
]
DROPPED_BY_HAND = [  # found while searching, not collected
    {"url": "https://80000hours.org/podcast/episodes/owain-evans-emergent-misalignment/", "date": "2026-08-20",
     "reason": "post-T (80,000 Hours #252, recorded 2026-06/07); also the podme URL in the manifest"},
    {"url": "https://podme.com/no/episode/12825779", "date": "2026-08-20", "reason": "post-T (same 80k episode)"},
    {"url": "https://www.lesswrong.com/posts/vAniKbagqhyzpha6r", "date": "2026-11-08", "reason": "post-T (Three half-baked research ideas)"},
    {"url": "https://linkedin.com/posts/owain-evans-78b210133_some-background-reading-for-openai-and-anthropic-activity-7492005646091935744-SW98",
     "date": "2026-08-08", "reason": "post-T (Some background reading for OpenAI and Anthropic incidents)"},
    {"url": "https://arxiv.org/abs/2411.16353", "date": "2024-11-25",
     "reason": "Lessons from studying two-hop latent reasoning is an arXiv paper (already in the paper set) and mentions Hobbhahn"},
    {"url": "https://owainevans.github.io/hinton.html", "date": "2025-11-10",
     "reason": "Hinton Lectures 2025: general-audience lectures, YouTube subtitles rate-limited (429), no published transcript; lecture 3 presents Apollo/OpenAI work co-authored by Hobbhahn"},
    {"url": "https://www.youtube.com/watch?v=Sl0AQITwMuQ", "date": "2024-10-16",
     "reason": "Cognitive Revolution crossover is a re-broadcast of The Inside View episode (duplicate)"},
    {"url": "manifest youtube.com/live, youtube.com/shorts, m.youtube.com, youtube.com/clip URLs", "date": "",
     "reason": "not Owain Evans (unrelated videos in the harvest manifest)"},
    {"url": "threadreaderapp threads 2034299680914608426, 2044488099707949545, 2055318932857459009, 2078149961506795887",
     "date": "2026", "reason": "post-T threads"},
]

COMMON = """Return 3-15 items. Each item is one of:
- "decision": a research decision he (or his team) made, where another choice was possible;
- "rejected": an option, method or line of work he rejected or argued against;
- "disagreement": a place where he disagrees with a default view or practice in the field;
- "advice": advice he gives about how to do research (what to work on, how to test, how to interpret results).
Prefer research methodology (evaluation design, experimental controls, what evidence to trust, which questions \
to pursue, how strongly to state claims) over biography, logistics or summaries of results. Only include items the \
text itself supports; return {{"decisions": []}} if there are none. For each item give:
- item_type: decision / rejected / disagreement / advice
- point: one of D1-D6 (D1 which experiment or hypothesis to pursue; D2 what evidence to collect; D3 whether to accept \
a result; D4 whether to continue or drop a line of work; D5 how to interpret an ambiguous result; D6 how strongly to \
state a claim)
- problem: the research problem or question faced, stated neutrally (1 sentence)
- did: what he chose, did or recommends (1 sentence)
- alternatives_named: a JSON list of strings, the alternatives the text itself names or rejects ([] if none)
- stated_reason: the reason the text gives ("" if none)
- quote: a VERBATIM passage of HIS OWN words, 15-60 words, copied character for character, that shows the item. \
Do not paraphrase, fix spelling or punctuation, merge passages, or use ellipses.{extra}

Return only JSON: {{"decisions": [{{"item_type": ..., "point": ..., "problem": ..., "did": ..., \
"alternatives_named": [...], "stated_reason": ..., "quote": ...{extra_keys}}}]}}
"""
REGISTER_INTRO = {
    "podcast": ("You read the transcript of a podcast/interview in which the AI-safety researcher Owain Evans is the "
                "guest and {host} is the host. Extract items from what OWAIN says, never from the host's questions "
                "or summaries. {caption_note}"),
    "comment": ("You read comments that the AI-safety researcher Owain Evans posted on LessWrong / the Alignment Forum. "
                "Each comment starts with a header [C<n>] giving its date and the post it is on; text under "
                "'PARENT (not his words)' is the comment he replied to, for context only. Lines starting with '>' "
                "inside his comment quote other people; never quote those."),
    "shortform": ("You read short-form posts (shortform comments) by the AI-safety researcher Owain Evans on LessWrong. "
                  "Each starts with a header [C<n>]. Lines starting with '>' quote other people; never quote those."),
    "ama": ("You read an Ask-Me-Anything on LessWrong about the Truthful AI paper: the AMA post (by Owain Evans) "
            "and his answers. Each part starts with a header [C<n>]; text under 'PARENT (not his words)' is the "
            "question he answered, for context only. Never quote the questions."),
    "ideas": "You read a list of AI-safety research project ideas written by Owain Evans.",
    "advice": "You read slides/notes by Owain Evans giving tips on doing empirical AI research.",
    "thread": ("You read a Twitter/X thread by Owain Evans (unrolled). Extract research choices and the reasoning "
               "he gives, as well as any views on how to do research."),
}
CAPTION_NOTE = ("The transcript is automatic YouTube captions with no speaker labels, no punctuation and some "
                "mis-heard words: work out from context who is speaking, copy quotes exactly as written (including "
                "errors), and give a speaker field for each item.")


def p(*parts):
    return os.path.join(HERE, *parts)


def jl_write(path, rows):
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def jl_read(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def strip_front_matter(text):
    return text.split("\n---\n", 1)[1] if text.startswith("---\n") else text


def corpus_doc(key):
    hits = [f for f in os.listdir(CORPUS) if key in f]
    assert len(hits) == 1, (key, hits)
    with open(os.path.join(CORPUS, hits[0])) as f:
        raw = f.read()
    fm = dict(re.findall(r"^(\w+): (.*)$", raw.split("\n---\n", 1)[0], re.MULTILINE))
    return hits[0], fm, strip_front_matter(raw)


def snowflake_date(tweet_id):
    return time.strftime("%Y-%m-%d", time.gmtime(((int(tweet_id) >> 22) + 1288834974657) / 1000))


def own_text(md):
    """His words only: drop blockquoted lines (quotes of other people)."""
    return "\n".join(line for line in (md or "").splitlines() if not line.lstrip().startswith(">"))


def speaker_split(text, owain_re, host_re):
    """Owain's turns only, for a transcript with speaker labels; unlabeled lines continue the last speaker."""
    out, cur = [], None
    for line in text.splitlines():
        if re.match(owain_re, line):
            cur = "owain"
        elif re.match(host_re, line):
            cur = "host"
        if cur == "owain":
            out.append(line)
    return "\n".join(out)


def chunks(text):
    """Pieces of at most about CHUNK_CHARS, cut at line breaks."""
    out, cur = [], ""
    for line in text.splitlines(keepends=True):
        if cur and len(cur) + len(line) > CHUNK_CHARS:
            out.append(cur)
            cur = ""
        cur += line
    return out + [cur] if cur else out


def collect():
    os.makedirs(p("texts", "comments"), exist_ok=True)
    sources, groups, dropped = [], [], list(DROPPED_BY_HAND)

    for sid, fn, url, date, title, host, labels in PODCASTS:
        with open(p("raw", fn)) as f:
            text = f.read()
        assert date < T
        if "hobbhahn" in text.lower():
            dropped.append({"url": url, "date": date, "reason": "mentions Hobbhahn"})
            continue
        with open(p("texts", sid + ".txt"), "w") as f:
            f.write(text)
        src = {"source_id": sid, "register": "podcast", "url": url, "date": date, "title": title, "host": host,
               "text_path": f"texts/{sid}.txt", "speaker_labels": bool(labels), "in_paper_set": False, "chars": len(text)}
        if labels:
            with open(p("texts", sid + ".owain.txt"), "w") as f:
                f.write(speaker_split(text, *labels))
            src["owain_text_path"] = f"texts/{sid}.owain.txt"
        sources.append(src)
        if sid in EXTRACT_FROM:
            cut = text.rfind(EXTRACT_FROM[sid])
            dropped.append({"url": url, "date": date, "reason": f"first {cut} chars not extracted: highlights and the SAD "
                            "section (SAD paper co-authored by Hobbhahn)"})
            text = text[cut:]
        for i, chunk in enumerate(chunks(text), 1):
            path = f"texts/{sid}.part{i}.txt"
            with open(p(path), "w") as f:
                f.write(chunk)
            groups.append({"group": f"{sid}_part{i}", "register": "podcast", "sources": [sid], "host": host,
                           "labels": bool(labels), "text_file": path})

    for sid, key, register, in_paper in CORPUS_DOCS:
        fn, fm, text = corpus_doc(key)
        date = fm["publishedDate"][:10]
        assert date < T and "hobbhahn" not in text.lower(), (fn, date)
        with open(p("texts", sid + ".txt"), "w") as f:
            f.write(text)
        sources.append({"source_id": sid, "register": register, "url": fm["url"], "date": date, "title": fm.get("title", ""),
                        "text_path": f"texts/{sid}.txt", "corpus_doc": fn, "in_paper_set": in_paper, "chars": len(text)})
        if sid != "ama_post":  # the AMA post goes in one group with his answers
            groups.append({"group": sid, "register": register, "sources": [sid]})

    for sid, tid, title in THREADS:
        with open(p("raw", f"tr_{tid}.txt")) as f:
            text = f.read()
        start = text.index("Owain Evans\n")  # the thread body sits between the author line and the footer
        text = text[start:text.index("Stay in touch and get notified")].strip()
        date = snowflake_date(tid)
        assert date < T and "hobbhahn" not in text.lower()
        with open(p("texts", sid + ".txt"), "w") as f:
            f.write(text)
        sources.append({"source_id": sid, "register": "thread", "url": f"https://threadreaderapp.com/thread/{tid}.html",
                        "date": date, "title": title, "text_path": f"texts/{sid}.txt", "in_paper_set": False,
                        "chars": len(text)})
        groups.append({"group": sid, "register": "thread", "sources": [sid]})

    with open(p("raw", "lw_comments.json")) as f:
        comments = json.load(f)["data"]["comments"]["results"]
    by_register = {"comment": [], "shortform": [], "ama": ["ama_post"]}
    for c in sorted(comments, key=lambda c: c["postedAt"]):
        post = c.get("post") or {}
        date = c["postedAt"][:10]
        if date >= T:
            continue
        names = [(post.get("user") or {}).get("username") or ""] + [a.get("username") or "" for a in post.get("coauthors") or []]
        parent = c.get("parentComment") or {}
        names.append((parent.get("user") or {}).get("username") or "")
        blob = " ".join(names + [c["contents"]["markdown"] or "", post.get("title") or "", (parent.get("contents") or {}).get("markdown") or ""])
        if "hobbhahn" in blob.lower():
            dropped.append({"url": c["pageUrl"], "date": date,
                            "reason": f"Hobbhahn author/co-author/parent/mention (post: {post.get('title')})"})
            continue
        if len(own_text(c["contents"]["markdown"]).split()) < 15:
            dropped.append({"url": c["pageUrl"], "date": date, "reason": "comment under 15 words of his own text"})
            continue
        register = ("shortform" if post.get("_id") == SHORTFORM_POST else "ama" if post.get("_id") == AMA_POST else "comment")
        sid = "lw_" + c["_id"]
        header = f"Comment by Owain_Evans, {date}, on \"{post.get('title') or '(no post title)'}\"\n{c['pageUrl']}\n"
        parent_md = (parent.get("contents") or {}).get("markdown")
        body = c["contents"]["markdown"]
        with open(p("texts", "comments", sid + ".md"), "w") as f:
            f.write(header + (f"\nPARENT (not his words):\n{parent_md[:1500]}\n" if parent_md else "") + "\nHIS COMMENT:\n" + body)
        sources.append({"source_id": sid, "register": register, "url": c["pageUrl"], "date": date,
                        "title": f"comment on: {post.get('title') or '(no post title)'}", "text_path": f"texts/comments/{sid}.md",
                        "in_paper_set": False, "chars": len(body)})
        by_register[register].append(sid)

    src_by_id = {s["source_id"]: s for s in sources}
    for register, ids in by_register.items():
        batch, size = [], 0
        for sid in ids:
            n = src_by_id[sid]["chars"]
            if batch and size + n > BATCH_CHARS:
                groups.append({"group": f"{register}_{len([g for g in groups if g['register'] == register]) + 1}",
                               "register": register, "sources": batch})
                batch, size = [], 0
            batch.append(sid)
            size += n
        if batch:
            groups.append({"group": f"{register}_{len([g for g in groups if g['register'] == register]) + 1}",
                           "register": register, "sources": batch})

    jl_write(p("sources.jsonl"), sources)
    jl_write(p("dropped.jsonl"), dropped)
    with open(p("groups.json"), "w") as f:
        json.dump(groups, f, indent=1)
    print(len(sources), "sources,", len(groups), "groups,", len(dropped), "dropped")
    for g in groups:
        print(" ", g["group"], len(g["sources"]))


def started_calls(model):
    if not os.path.exists(p("calls.log")):
        return 0
    with open(p("calls.log")) as f:
        return sum(json.loads(line).get("status") == "started" and json.loads(line).get("model") == model for line in f)


def cache_path(model, prompt):
    return p("cache", hashlib.sha256(json.dumps([model, prompt]).encode()).hexdigest()[:32] + ".json")


def call(model, prompt, tag):
    cpath = cache_path(model, prompt)
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    with LOCK:
        n = started_calls(model)
        if n >= CAPS[model]:
            raise RuntimeError(f"{model} call cap {CAPS[model]} reached")
        with open(p("calls.log"), "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "n": n + 1, "tag": tag,
                                "key": os.path.basename(cpath)[:-5], "chars": len(prompt), "status": "started"}) + "\n")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "", "--strict-mcp-config",
           "--no-session-persistence", "--setting-sources", "", "--system-prompt",
           "You extract structured data from documents and answer with JSON only."]
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="inf_cli_") as cwd:
        proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=900, cwd=cwd)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
    ok = proc.returncode == 0 and not data.get("is_error")
    with LOCK, open(p("calls.log"), "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "tag": tag,
                            "key": os.path.basename(cpath)[:-5], "status": "ok" if ok else "error",
                            "secs": round(time.time() - t0, 1), "cost_usd": data.get("total_cost_usd"),
                            "out": str(data.get("result"))[:120]}) + "\n")
    if not ok:
        raise RuntimeError(f"claude CLI error on {tag}: {str(data.get('result'))[:300]}")
    with open(cpath, "w") as f:
        json.dump({"tag": tag, "model": model, "prompt_chars": len(prompt), "result": data["result"]}, f, ensure_ascii=False)
    return data["result"]


def read_source(s):
    with open(p(s["text_path"])) as f:
        return f.read()


def group_prompt(g, src_by_id):
    register = g["register"]
    multi = register in ("comment", "shortform", "ama")
    intro = REGISTER_INTRO[register].format(host=g.get("host", ""), caption_note="" if g.get("labels", True) else CAPTION_NOTE)
    extra, extra_keys = "", ""
    if multi:
        extra += "\n- source: the [C<n>] tag of the comment or post the quote comes from"
        extra_keys += ', "source": ...'
    if register == "podcast" and not g.get("labels", True):
        extra += "\n- speaker: \"owain\" if Owain says the quoted words, \"host\" otherwise (only return owain items)"
        extra_keys += ', "speaker": ...'
    head = intro + "\n\n" + COMMON.format(extra=extra, extra_keys=extra_keys)
    if multi:
        parts = []
        for i, sid in enumerate(g["sources"], 1):
            parts.append(f"[C{i}] " + read_source(src_by_id[sid]))
        body = "\n\n=====\n\n".join(parts)
    else:
        s = src_by_id[g["sources"][0]]
        if "text_file" in g:
            with open(p(g["text_file"])) as f:
                text = f.read()
            part = re.search(r"part(\d+)", g["group"]).group(1)
            body = f"SOURCE ({s['title']}, {s['date']}; excerpt {part}):\n" + text
        else:
            body = f"SOURCE ({s['title']}, {s['date']}):\n" + read_source(s)
    return head + "\n" + body[:MAX_CHARS]


def extract():
    groups = json.load(open(p("groups.json")))
    src_by_id = {s["source_id"]: s for s in jl_read(p("sources.jsonl"))}
    os.makedirs(p("cache"), exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        futs = {pool.submit(call, "sonnet", group_prompt(g, src_by_id), g["group"]): g["group"] for g in groups}
        for fu in concurrent.futures.as_completed(futs):
            try:
                fu.result()
                print("ok", futs[fu])
            except (RuntimeError, subprocess.TimeoutExpired) as e:  # a rerun retries uncached groups
                print("FAIL", futs[fu], e)
    print("started sonnet calls:", started_calls("sonnet"))


def clean(d):
    out = {k: d.get(k) for k in _FIELDS}
    alts = out["alternatives_named"]
    out["alternatives_named"] = ([] if alts in (None, "", "null", "none", "None")
                                 else [alts] if isinstance(alts, str) else [str(a) for a in alts if a])
    out["stated_reason"] = "" if out["stated_reason"] in (None, "null") else str(out["stated_reason"])
    out["item_type"] = str(d.get("item_type") or "")
    return out


def raw_items(g, src_by_id):
    """(item, source_id) pairs from the cached sonnet output of one group, or None if not extracted."""
    cpath = cache_path("sonnet", group_prompt(g, src_by_id))
    if not os.path.exists(cpath):
        return None
    with open(cpath) as f:
        out = extract_json(json.load(f)["result"]) or {}
    items = []
    for raw in out.get("decisions") or []:
        if not isinstance(raw, dict):
            continue
        sid = g["sources"][0]
        tag = str(raw.get("source") or "")
        m = re.fullmatch(r"\[?C(\d+)\]?", tag.strip())
        if len(g["sources"]) > 1 or m:
            sid = g["sources"][int(m.group(1)) - 1] if m and 0 < int(m.group(1)) <= len(g["sources"]) else None
        items.append((raw, sid))
    return items


def speaker_prompt(s, items):
    norm = normalize_for_quote(read_source(s))
    lines = []
    for i, (raw, _) in enumerate(items, 1):
        q = normalize_for_quote(str(raw.get("quote") or ""))
        at = norm.find(q)
        ctx = norm[max(0, at - 1500):at] + " <<<" + q + ">>> " + norm[at + len(q):at + len(q) + 400]
        lines.append(f"ITEM {i}\nCONTEXT: ...{ctx}...")
    return (f"These are excerpts from automatic captions (no speaker labels) of a podcast where {s['host']} interviews "
            "the AI researcher Owain Evans. For each item, decide who speaks the words between <<< and >>>: "
            "\"owain\" (the guest), \"host\", or \"unclear\" (e.g. the span covers both speakers). Hosts ask questions, "
            "introduce the guest and summarise; Owain answers.\n"
            'Return only JSON: {"labels": [{"item": 1, "speaker": "owain"}, ...]}\n\n' + "\n\n".join(lines))


def speaker_targets():
    """(source, items whose quote is found) for each unlabeled transcript."""
    groups = json.load(open(p("groups.json")))
    src_by_id = {s["source_id"]: s for s in jl_read(p("sources.jsonl"))}
    out = []
    for g in groups:
        s = src_by_id[g["sources"][0]]
        if g["register"] == "podcast" and not s["speaker_labels"]:
            items = [(r, sid) for r, sid in (raw_items(g, src_by_id) or []) if quote_in_text(str(r.get("quote") or ""), read_source(s))]
            out.append((s, items))
    return out


def speaker():
    for s, items in speaker_targets():
        if items:
            call("haiku", speaker_prompt(s, items), "speaker/" + s["source_id"])
            print("ok", s["source_id"], len(items))
    print("started haiku calls:", started_calls("haiku"))


def assemble():
    groups = json.load(open(p("groups.json")))
    sources = jl_read(p("sources.jsonl"))
    src_by_id = {s["source_id"]: s for s in sources}
    haiku_labels = {}
    for s, items in speaker_targets():
        cpath = cache_path("haiku", speaker_prompt(s, items)) if items else None
        if cpath and os.path.exists(cpath):
            with open(cpath) as f:
                labels = (extract_json(json.load(f)["result"]) or {}).get("labels") or []
            lab = {int(x["item"]): str(x.get("speaker")) for x in labels if isinstance(x, dict) and str(x.get("item", "")).isdigit()}
            for i, (raw, _) in enumerate(items, 1):
                haiku_labels[(s["source_id"], normalize_for_quote(str(raw.get("quote") or "")))] = lab.get(i, "unclear")
    rows, stats, seen = [], {}, set()
    for g in groups:
        items = raw_items(g, src_by_id)
        st = stats.setdefault(g["register"], {"groups": 0, "groups_extracted": 0, "raw": 0, "kept": 0, "drop_source": 0,
                                              "drop_did": 0, "drop_quote": 0, "drop_quote_len": 0, "drop_speaker": 0,
                                              "drop_hobbhahn_work": 0, "drop_dup": 0})
        st["groups"] += 1
        if items is None:
            continue
        st["groups_extracted"] += 1
        for raw, sid in items:
            st["raw"] += 1
            dec = clean(raw)
            quote = str(dec["quote"] or "")
            s = src_by_id.get(sid)
            if s is None:
                st["drop_source"] += 1
                continue
            text = read_source(s)
            if s["text_path"].startswith("texts/comments/"):
                text = own_text(text.split("\nHIS COMMENT:\n", 1)[1])  # his words only, no parent, no blockquotes
            key = normalize_for_quote(quote)
            if not str(dec["did"] or "").strip() or str(dec["did"]).strip().lower() == "null":
                st["drop_did"] += 1
            elif HOBBHAHN_WORK.search(json.dumps(dec, ensure_ascii=False)):
                st["drop_hobbhahn_work"] += 1
            elif not quote_in_text(quote, text):
                st["drop_quote"] += 1
            elif not 15 <= len(quote.split()) <= 60:
                st["drop_quote_len"] += 1
            elif (sid, key) in seen:
                st["drop_dup"] += 1
            else:
                if s["register"] != "podcast":
                    verified, how = True, "sole author"
                elif s["speaker_labels"]:
                    with open(p(s["owain_text_path"])) as f:
                        verified, how = quote_in_text(quote, f.read()), "speaker labels"
                else:
                    verified, how = haiku_labels.get((sid, key)) == "owain" and str(raw.get("speaker", "owain")).lower() == "owain", "haiku + sonnet label"
                if not verified:
                    st["drop_speaker"] += 1
                    continue
                seen.add((sid, key))
                rows.append(dict(dec, register=s["register"], source_id=sid, source_url=s["url"], date=s["date"],
                                 title=s["title"], speaker_verified=True, speaker_check=how, in_paper_set=s["in_paper_set"],
                                 researcher="owain_evans", split="pre", cutoff=T,
                                 work_id=f"owain_evans:informal:{sid}",
                                 decision_id=hashlib.sha256((sid + key).encode()).hexdigest()[:12]))
                st["kept"] += 1
    for register, st in stats.items():
        mine = [r for r in rows if r["register"] == register]
        st["sources_total"] = sum(s["register"] == register for s in sources)
        st["sources_with_kept"] = len({r["source_id"] for r in mine})
        st["by_item_type"] = {t: sum(r["item_type"] == t for r in mine) for t in ("decision", "rejected", "disagreement", "advice")}
    jl_write(p("decisions.jsonl"), rows)
    with open(p("stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    print(json.dumps(stats, indent=1))
    print("kept", len(rows), "from", len({r["source_id"] for r in rows}), "sources")


if __name__ == "__main__":
    {"collect": collect, "extract": extract, "speaker": speaker, "assemble": assemble}[sys.argv[1]]()
