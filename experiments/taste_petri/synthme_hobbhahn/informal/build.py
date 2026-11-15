"""Marius Hobbhahn's informal pre-T material (T = 2026-01-01) and the research decisions in it.

    python3 experiments/taste_petri/synthme_hobbhahn/informal/build.py collect   # raw/ -> texts/, sources.jsonl, dropped.jsonl
    python3 experiments/taste_petri/synthme_hobbhahn/informal/build.py extract   # one call per source group (cached)
    python3 experiments/taste_petri/synthme_hobbhahn/informal/build.py assemble  # quote + speaker verification -> decisions.jsonl, stats.json

Adapted from experiments/taste_petri/informal/build.py (Owain Evans). raw/ holds what was fetched by hand: podcast
pages (80000hours.org, cognitiverevolution.ai) and FAR.AI talk pages over HTTP, threadreaderapp pages over HTTP, and
his LessWrong/AF comments from the public GraphQL API. Every model call goes through synthme_hobbhahn/common.py's
`call` (devin-cli, logged to synthme_hobbhahn/calls.log, cached in synthme_hobbhahn/cache/). Every source has speaker
labels or a single author, so the reference's haiku speaker stage (for unlabeled auto-captions) is not needed.
"""
import concurrent.futures
import hashlib
import html
import json
import os
import re
import sys
import time
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
SYN = os.path.dirname(HERE)
sys.path.insert(0, SYN)
import common as C  # noqa: E402  (puts the repo root on sys.path)
from autoresearch.llm import extract_json  # noqa: E402
from autoresearch.taste.timesplit import _FIELDS, normalize_for_quote, quote_in_text  # noqa: E402

T = C.T
WORKERS, MAX_CHARS, BATCH_CHARS, CHUNK_CHARS = 4, 160_000, 15_000, 32_000
SYSTEM = "You extract structured data from documents and answer with JSON only."
LW_ID = "HB2hPFoDq5yLayNFj"  # LessWrong userId of marius-hobbhahn
# Items on these comment threads are about energy, cognition, productivity or sleep, not AI or research practice.
OFF_TOPIC_TITLES = re.compile(r"(?i)nuclear energy|mental building blocks|guide for productivity|how to sleep better")

PODCASTS = [
    # id, raw file, url, date, title, host, (marius label regex, host label regex), transcript start marker, end marker
    ("pod_80k", "80k.html", "https://80000hours.org/podcast/episodes/marius-hobbhahn-ai-scheming-deception/",
     "2025-12-03", "80,000 Hours #229 - Marius Hobbhahn on the race to solve AI scheming", "Rob Wiblin",
     (r"^Marius Hobbhahn:", r"^Rob Wiblin:"), "\nTranscript\n\nTable of Contents\n", "Show full transcript"),
    ("pod_cr2023", "cr2023.html",
     "https://www.cognitiverevolution.ai/ai-deception-interpretability-and-affordances-with-apollo-research-ceo-marius-hobbhahn/",
     "2023-12-16", "The Cognitive Revolution - AI Deception, Interpretability, and Affordances", "Nathan Labenz",
     (r"^Marius Hobbhahn:", r"^Nathan Labenz:"), "\nNathan Labenz: (", "\n Published in:"),
    ("pod_cr2024", "cr2024.html",
     "https://www.cognitiverevolution.ai/red-teaming-o1-part-2-2-detecting-deception-with-marius-hobbhahn-of-apollo-research/",
     "2024-09-14", "The Cognitive Revolution - Red Teaming o1 Part 2/2: Detecting Deception", "Nathan Labenz",
     (r"^Marius Hobbhahn:", r"^Nathan Labenz:"), "\nNathan Labenz: (", "\n Published in:"),
    ("pod_cr2025", "cr2025.html",
     "https://www.cognitiverevolution.ai/can-we-stop-ai-deception-apollo-research-tests-openais-deliberative-alignment-w-marius-hobbhahn/",
     "2025-09-18", "The Cognitive Revolution - Can We Stop AI Deception? (deliberative alignment)", "Nathan Labenz",
     (r"^Marius Hobbhahn:", r"^Nathan Labenz:"), "\nNathan Labenz: (", "\n Published in:"),
]
TALKS = [  # FAR.AI recordings with a session transcript; audience questions are [Q] paragraphs or "[unclear question]"
    ("talk_far_trainscheme", "far_trainscheme.html",
     "https://www.far.ai/event-recordings/marius-hobhhahn-can-you-just-train-models-not-to-scheme",
     "2025-10-07", "FAR Seminar talk - Can you just train models not to scheme?"),
    ("talk_far_evalaware", "far_evalaware.html",
     "https://www.far.ai/event-recordings/marius-hobbhahn-eval-awareness-is-becoming-a-problem",
     "2025-11-30", "FAR.AI talk - Eval Awareness is Becoming a Problem"),
]
THREADS = [  # threadreaderapp ids (every unroll listed on threadreaderapp.com/user/MariusHobbhahn); date from the snowflake
    ("thread_gpu", "1603072913283981313", "Predicting GPU performance (Epoch) thread"),
    ("thread_lib", "1792639872810815926", "Degeneracy / Local Interaction Basis interpretability papers thread"),
    ("thread_evals_resources", "1857793360779464848", "Which evals resources would be good? thread"),
    ("thread_eval_awareness", "1930324014322356259", "LLMs Often Know When They Are Being Evaluated thread"),
]
DROPPED_BY_HAND = [  # found while searching, not collected
    {"url": "https://podcasts.apple.com/au/podcast/do-ai-models-lie-on-purpose-scheming-deception-and/id1871396579?i=1000746314450",
     "date": "2026-01-17", "reason": "post-T (Palisade Research Podcast with Jeffrey Ladish)"},
    {"url": "https://www.youtube.com/watch?v=mqaig6ARtCo", "date": "2026-03-02",
     "reason": "post-T (Science of Scheming, London Alignment Workshop 2026)"},
    {"url": "https://exa.ai/library/podcast/vx6h9g749l7/episode/qg9nsjtvx9d", "date": "2026-10-13",
     "reason": "post-T (Foresight Institute Radio, The Case for AGI Safety Products, Vision Weekend UK June 2026)"},
    {"url": "https://exa.ai/library/podcast/3zgm83jwbf6/episode/8khnf4x6vn6", "date": "2026-06-03",
     "reason": "post-T (Endgame podcast with Jamie Bartlett, episode 3)"},
    {"url": "https://www.tapesearch.com/episode/ai-models-are-lying-to-us-here-s-the-ai-research-lab-trying-to-solve-this-apollo-research/HGzy8G6wPWAoRaJtfoKewq",
     "date": "2025-10-16", "reason": "AI Pod (Wes Roth and Dylan Curious): the only transcript host returned HTTP 403; no other transcript found"},
    {"url": "https://cset.georgetown.edu/event/whats-next-for-ai-red-teaming/", "date": "2025-03-25",
     "reason": "CSET panel on AI red-teaming: video only, no published transcript"},
    {"url": "https://spoken.md/episode/ai-deception-interpretability-and-affordances-with-1000638728745", "date": "2023-12-15",
     "reason": "duplicate of the Cognitive Revolution 2023 episode (spoken.md shows only a summary; the full transcript came from cognitiverevolution.ai)"},
    {"url": "https://spoken.md/episode/red-teaming-o1-part-2-2-detecting-deception-with-1000669529789", "date": "2024-09-14",
     "reason": "duplicate of the Cognitive Revolution 2024 episode"},
    {"url": "https://lovkush.substack.com/p/how-to-make-evals-for-the-aisi-evals", "date": "2024-12-03",
     "reason": "a third party's summary of his hackathon talk, not his words"},
    {"url": "https://www.lesswrong.com/posts/2PiawPFJeyCQGcwXG", "date": "2024-01-08",
     "reason": "A starter guide for evals: advice post not in the corpus, but co-authored with 4 others, so no quote is verifiably his"},
    {"url": "https://www.lesswrong.com/users/marius-hobbhahn (posts gJJEjJpKiddoYGZKk, Cur4n3gRGaqysKf5b, fnc6Sgt3CGCdFmmgX, FG6icLPKizEaWHex5, 9tqpPP4FwSnv9AWsi)",
     "date": "2023-2025", "reason": "his formal LW posts missing from the corpus (The Evals Gap, An Opinionated Evals Reading List, "
     "We need a Science of Evals, Announcing Apollo Research, Research Note on precursor evals): posts, not informal material"},
    {"url": "nitter / x.com timeline", "date": "", "reason": "Twitter/X not reachable without login; only the four threadreaderapp unrolls were collected"},
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
Do not paraphrase, fix spelling or punctuation, merge passages, or use ellipses.
- off_topic: true if the item is not about AI, ML or research practice (e.g. energy policy, health, productivity), \
else false{extra}

Return only JSON: {{"decisions": [{{"item_type": ..., "point": ..., "problem": ..., "did": ..., \
"alternatives_named": [...], "stated_reason": ..., "quote": ..., "off_topic": ...{extra_keys}}}]}}
"""
REGISTER_INTRO = {
    "podcast": ("You read the transcript of a podcast/interview in which the AI-safety researcher Marius Hobbhahn "
                "(CEO of Apollo Research) is the guest and {host} is the host. Extract items from what MARIUS says, "
                "never from the host's questions, introductions or summaries."),
    "talk": ("You read the transcript of a talk by the AI-safety researcher Marius Hobbhahn (CEO of Apollo Research), "
             "followed by audience Q&A in which [Q] marks audience questions and [A] his answers. Extract items from "
             "what Marius says; never quote [Q] paragraphs."),
    "comment": ("You read comments that the AI-safety researcher Marius Hobbhahn posted on LessWrong / the Alignment "
                "Forum. Each comment starts with a header [C<n>] giving its date and the post it is on; text under "
                "'PARENT (not his words)' is the comment he replied to, for context only. Lines starting with '>' "
                "inside his comment quote other people; never quote those."),
    "shortform": ("You read short-form posts (shortform comments) by the AI-safety researcher Marius Hobbhahn on "
                  "LessWrong. Each starts with a header [C<n>]. Lines starting with '>' quote other people; never quote those."),
    "thread": ("You read a Twitter/X thread by Marius Hobbhahn (unrolled). Extract research choices and the reasoning "
               "he gives, as well as any views on how to do research."),
}


def p(*parts):
    return os.path.join(HERE, *parts)


def jl_write(path, rows):
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def jl_read(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"}
    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in self.SKIP
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        self.skip -= tag in self.SKIP
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_text(fn):
    parser = _Text()
    with open(p("raw", fn), encoding="utf-8", errors="replace") as f:
        parser.feed(f.read())
    text = re.sub(r"[ \t]+", " ", html.unescape("".join(parser.out)))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip() + "\n"


def snowflake_date(tweet_id):
    return time.strftime("%Y-%m-%d", time.gmtime(((int(tweet_id) >> 22) + 1288834974657) / 1000))


def own_text(md):
    """His words only: drop blockquoted lines (quotes of other people)."""
    return "\n".join(line for line in (md or "").splitlines() if not line.lstrip().startswith(">"))


def talk_own_text(text):
    """His words only in a talk transcript: drop audience questions."""
    return "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith(("[Q]", "[unclear question]")))


def speaker_split(text, marius_re, host_re):
    """Marius's turns only, for a transcript with speaker labels; unlabeled lines continue the last speaker."""
    out, cur = [], None
    for line in text.splitlines():
        if re.match(marius_re, line):
            cur = "marius"
        elif re.match(host_re, line):
            cur = "host"
        if cur == "marius":
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


def between(text, start, end):
    i = text.rindex(start) if start.startswith("\nTranscript") else text.index(start)
    return text[i:text.index(end, i)].strip() + "\n"


def collect():
    os.makedirs(p("texts", "comments"), exist_ok=True)
    sources, groups, dropped = [], [], list(DROPPED_BY_HAND)

    for sid, fn, url, date, title, host, labels, start, end in PODCASTS:
        assert date < T
        text = between(html_text(fn), start, end)
        with open(p("texts", sid + ".txt"), "w") as f:
            f.write(text)
        with open(p("texts", sid + ".marius.txt"), "w") as f:
            f.write(speaker_split(text, *labels))
        sources.append({"source_id": sid, "register": "podcast", "url": url, "date": date, "title": title, "host": host,
                        "text_path": f"texts/{sid}.txt", "marius_text_path": f"texts/{sid}.marius.txt",
                        "speaker_labels": True, "in_paper_set": False, "chars": len(text)})
        for i, chunk in enumerate(chunks(text), 1):
            path = f"texts/{sid}.part{i}.txt"
            with open(p(path), "w") as f:
                f.write(chunk)
            groups.append({"group": f"{sid}_part{i}", "register": "podcast", "sources": [sid], "host": host,
                           "text_file": path})

    for sid, fn, url, date, title in TALKS:
        assert date < T
        text = between(html_text(fn), "SESSION Transcript", "\nResearch\n")
        with open(p("texts", sid + ".txt"), "w") as f:
            f.write(text)
        with open(p("texts", sid + ".marius.txt"), "w") as f:
            f.write(talk_own_text(text))
        sources.append({"source_id": sid, "register": "talk", "url": url, "date": date, "title": title,
                        "text_path": f"texts/{sid}.txt", "marius_text_path": f"texts/{sid}.marius.txt",
                        "speaker_labels": True, "in_paper_set": False, "chars": len(text)})
        groups.append({"group": sid, "register": "talk", "sources": [sid]})

    for sid, tid, title in THREADS:
        text = html_text(f"tr_{tid}.html")
        start = text.index("@MariusHobbhahn\n")  # the thread body sits between the author handle and the footer
        text = text[start:text.index("• • •", start)].strip() + "\n"
        date = snowflake_date(tid)
        assert date < T
        with open(p("texts", sid + ".txt"), "w") as f:
            f.write(text)
        sources.append({"source_id": sid, "register": "thread", "url": f"https://threadreaderapp.com/thread/{tid}.html",
                        "date": date, "title": title, "text_path": f"texts/{sid}.txt", "speaker_labels": False,
                        "in_paper_set": False, "chars": len(text)})
        groups.append({"group": sid, "register": "thread", "sources": [sid]})

    with open(p("raw", "lw_comments.json")) as f:
        comments = json.load(f)["data"]["comments"]["results"]
    by_register = {"comment": [], "shortform": []}
    for c in sorted(comments, key=lambda c: c["postedAt"]):
        post = c.get("post") or {}
        date = c["postedAt"][:10]
        if date >= T:
            dropped.append({"url": c["pageUrl"], "date": date, "reason": "post-T comment"})
            continue
        if len(own_text(c["contents"]["markdown"]).split()) < 15:
            dropped.append({"url": c["pageUrl"], "date": date, "reason": "comment under 15 words of his own text"})
            continue
        register = "shortform" if post.get("shortform") and (post.get("user") or {}).get("username") == "marius-hobbhahn" else "comment"
        sid = "lw_" + c["_id"]
        post_title = (post.get("title") or "(no post title)").strip()
        parent = c.get("parentComment") or {}
        header = f"Comment by Marius Hobbhahn, {date}, on \"{post_title}\"\n{c['pageUrl']}\n"
        parent_md = (parent.get("contents") or {}).get("markdown")
        body = c["contents"]["markdown"]
        with open(p("texts", "comments", sid + ".md"), "w") as f:
            f.write(header + (f"\nPARENT (not his words):\n{parent_md[:1500]}\n" if parent_md else "") + "\nHIS COMMENT:\n" + body)
        sources.append({"source_id": sid, "register": register, "url": c["pageUrl"], "date": date,
                        "title": f"comment on: {post_title}", "text_path": f"texts/comments/{sid}.md",
                        "speaker_labels": False, "in_paper_set": False, "chars": len(body)})
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


def cache_path(prompt):
    """Where common.call caches the reply to this prompt (same key as common.call)."""
    key = hashlib.sha256(json.dumps([C.MODEL, "sonnet", SYSTEM, prompt]).encode()).hexdigest()[:32]
    return os.path.join(SYN, "cache", key + ".json")


def read_source(s):
    with open(p(s["text_path"])) as f:
        return f.read()


def group_prompt(g, src_by_id):
    register = g["register"]
    multi = register in ("comment", "shortform")
    intro = REGISTER_INTRO[register].format(host=g.get("host", ""))
    extra, extra_keys = "", ""
    if multi:
        extra += "\n- source: the [C<n>] tag of the comment or post the quote comes from"
        extra_keys += ', "source": ...'
    head = intro + "\n\n" + COMMON.format(extra=extra, extra_keys=extra_keys)
    if multi:
        body = "\n\n=====\n\n".join(f"[C{i}] " + read_source(src_by_id[sid]) for i, sid in enumerate(g["sources"], 1))
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
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        futs = {pool.submit(C.call, "sonnet", "inf:" + g["group"], group_prompt(g, src_by_id), system=SYSTEM): g["group"]
                for g in groups}
        for fu in concurrent.futures.as_completed(futs):
            try:
                fu.result()
                print("ok", futs[fu])
            except RuntimeError as e:  # a rerun retries uncached groups
                print("FAIL", futs[fu], e)


def clean(d):
    out = {k: d.get(k) for k in _FIELDS}
    alts = out["alternatives_named"]
    out["alternatives_named"] = ([] if alts in (None, "", "null", "none", "None")
                                 else [alts] if isinstance(alts, str) else [str(a) for a in alts if a])
    out["stated_reason"] = "" if out["stated_reason"] in (None, "null") else str(out["stated_reason"])
    out["item_type"] = str(d.get("item_type") or "")
    return out


def raw_items(g, src_by_id):
    """(item, source_id) pairs from the cached output of one group, or None if not extracted."""
    cpath = cache_path(group_prompt(g, src_by_id))
    if not os.path.exists(cpath):
        return None
    with open(cpath) as f:
        out = extract_json(json.load(f)["result"]) or {}
    items = []
    for raw in (out.get("decisions") if isinstance(out, dict) else out) or []:
        if not isinstance(raw, dict):
            continue
        sid = g["sources"][0]
        m = re.fullmatch(r"\[?C(\d+)\]?", str(raw.get("source") or "").strip())
        if len(g["sources"]) > 1 or m:
            sid = g["sources"][int(m.group(1)) - 1] if m and 0 < int(m.group(1)) <= len(g["sources"]) else None
        items.append((raw, sid))
    return items


def assemble():
    groups = json.load(open(p("groups.json")))
    sources = jl_read(p("sources.jsonl"))
    src_by_id = {s["source_id"]: s for s in sources}
    rows, stats, seen = [], {}, set()
    for g in groups:
        items = raw_items(g, src_by_id)
        st = stats.setdefault(g["register"], {"groups": 0, "groups_extracted": 0, "raw": 0, "kept": 0, "drop_source": 0,
                                              "drop_did": 0, "drop_quote": 0, "drop_quote_len": 0, "drop_speaker": 0,
                                              "drop_dup": 0})
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
            elif not quote_in_text(quote, text):
                st["drop_quote"] += 1
            elif not 15 <= len(quote.split()) <= 60:
                st["drop_quote_len"] += 1
            elif (sid, key) in seen:
                st["drop_dup"] += 1
            else:
                if "marius_text_path" in s:
                    with open(p(s["marius_text_path"])) as f:
                        verified = quote_in_text(quote, f.read())
                    how = "speaker labels" if s["register"] == "podcast" else "talk speaker (audience [Q] removed)"
                else:
                    verified, how = True, "sole author"
                if not verified:
                    st["drop_speaker"] += 1
                    continue
                seen.add((sid, key))
                off_topic = bool(OFF_TOPIC_TITLES.search(s["title"])) or str(raw.get("off_topic")).lower() == "true"
                rows.append(dict(dec, off_topic=off_topic, register=s["register"], source_id=sid, source_url=s["url"],
                                 date=s["date"], title=s["title"], speaker_verified=True, speaker_check=how,
                                 in_paper_set=s["in_paper_set"], researcher=C.SLUG, split="pre", cutoff=T,
                                 work_id=f"{C.SLUG}:informal:{sid}",
                                 decision_id=hashlib.sha256((sid + key).encode()).hexdigest()[:12]))
                st["kept"] += 1
    for register, st in stats.items():
        mine = [r for r in rows if r["register"] == register]
        st["sources_total"] = sum(s["register"] == register for s in sources)
        st["sources_with_kept"] = len({r["source_id"] for r in mine})
        st["by_item_type"] = {t: sum(r["item_type"] == t for r in mine) for t in ("decision", "rejected", "disagreement", "advice")}
        st["off_topic"] = sum(r["off_topic"] for r in mine)
    jl_write(p("decisions.jsonl"), rows)
    with open(p("stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    print(json.dumps(stats, indent=1))
    print("kept", len(rows), "from", len({r["source_id"] for r in rows}), "sources")


if __name__ == "__main__":
    {"collect": collect, "extract": extract, "assemble": assemble}[sys.argv[1]]()
