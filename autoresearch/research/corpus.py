"""Real user messages, the reference the discriminator compares against.

Put JSONL files with a "text" field (one real first user message per line)
in data/real_corpus/. `fetch_hf_rows` pulls a small sample from a public
Hugging Face dataset through the datasets-server rows API, only when you
run the `corpus` command yourself.

Topic matching: `topic_tags` labels text with a small fixed taxonomy (a keyword
heuristic, see TOPIC_RULES), `load_corpus_records` returns messages with their
tags, and `matched_pool` picks the real messages that share a topic with one
benchmark item so a judge cannot separate real from synthetic by topic alone."""
from __future__ import annotations

import glob
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "real_corpus")


def load_corpus(root: str = ROOT, min_chars: int = 40, max_chars: int = 3000,
                keywords: str = "", min_matched: int = 15) -> List[str]:
    """Real messages; with `keywords`, only topic-matched ones (falls back to
    all messages if fewer than `min_matched` match; callers report which)."""
    import re
    out = []
    for p in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        with open(p) as f:
            for line in f:
                if line.strip():
                    t = json.loads(line).get("text", "")
                    if min_chars <= len(t) <= max_chars:
                        out.append(t)
    if keywords:
        m = [t for t in out if re.search(keywords, t, re.I)]
        if len(m) >= min_matched:
            return m
    return out


def fetch_hf_rows(dataset: str, config: str, split: str, n: int, extract, root: str = ROOT,
                  name: str = "corpus") -> str:
    """extract(row) -> str|None picks the first user message from a row."""
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{name}.jsonl")
    got, offset = 0, 0
    with open(path, "w") as fh:
        while got < n and offset < n * 10:
            q = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split,
                                        "offset": offset, "length": 100})
            with urllib.request.urlopen(f"https://datasets-server.huggingface.co/rows?{q}", timeout=60) as r:
                rows = json.loads(r.read()).get("rows", [])
            if not rows:
                break
            for row in rows:
                t = extract(row.get("row", {}))
                if t and got < n:
                    fh.write(json.dumps({"text": t}) + "\n")
                    got += 1
            offset += 100
    return path


def wildchat_first_user(row) -> str:
    conv = row.get("conversation") or []
    if row.get("language") not in (None, "English"):
        return ""
    for turn in conv:
        if turn.get("role") == "user":
            return turn.get("content", "")
    return ""


# ---------------------------------------------------------------------------
# Topic tags and per-item matching
# ---------------------------------------------------------------------------

OTHER_TOPIC = "other"

# One row per topic: (tag, regex). Matched case-insensitively anywhere in the text.
# Multi-label: a text gets every tag whose regex hits, or "other" if none hit.
TOPIC_RULES: List[Tuple[str, str]] = [
    ("coding", r"```|\bdef \w+\(|\bfunction\b|\bpython\b|\bjava(script)?\b|\bc\+\+|\btypescript\b|"
               r"\bsql\b|\bhtml\b|\bcss\b|\bapi\b|\bbug\b|\bcompile[rd]?\b|\bstack ?trace\b|\bgithub\b|"
               r"\bregex\b|\bcode\b|\bscript\b|\bunity\b|\bexception\b"),
    ("data_analysis", r"\b(data ?set|csv|excel|spreadsheet|pandas|dataframe|statistic\w*|regression|"
                      r"correlation|dashboard|metrics?|kpi|chart|pivot|forecast\w*)\b"),
    ("writing_editing", r"\b(essay|rewrite|rephrase|paraphrase|proofread|grammar|edit this|summari[sz]e|"
                        r"cover letter|blog post|article|paragraph|translate|translation)\b"),
    ("business_ops", r"\b(marketing|sales|revenue|customers?|startup|business plan|invoice|"
                     r"stakeholders?|quarterly|roadmap|project manage\w*|meeting|hiring|"
                     r"supply chain|inventory|budget|seo|brand(ing)?)\b"),
    ("customer_support", r"\b(refund|support ticket|ticket|complaint|order status|customer service|"
                         r"help ?desk|my order|cancel(l?ation)? my|subscription|account locked)\b"),
    ("research_science", r"\b(physics|chemistry|biology|quantum|molecul\w*|genome|hypothesis|"
                         r"experiment|scientific|research paper|climate|astronom\w*|neural network|"
                         r"machine learning|theorem|calculus|equation)\b"),
    ("education", r"\b(homework|exam|students?|teacher|lesson plan|syllabus|quiz|curriculum|"
                  r"university|school|textbook|explain to a|study guide|thesis)\b"),
    ("legal_finance", r"\b(contract|lawsuit|attorney|lawyer|legal|tax(es)?|invest\w*|stocks?|crypto\w*|"
                      r"mortgage|loan|insurance|regulation|compliance|gdpr|patent)\b"),
    ("health", r"\b(symptoms?|doctor|medical|medication|diagnos\w*|therapy|anxiety|depress\w*|"
               r"diet|nutrition|workout|injury|pain|disease|health)\b"),
    ("personal_advice", r"\b(relationship|boyfriend|girlfriend|my (wife|husband|mom|dad|friend)|"
                        r"should i (quit|move|tell|break)|advice|feel(ing)? (lost|stuck|sad)|dating|career change)\b"),
    ("creative", r"\b(poem|poetry|story|novel|lyrics|song|character|fiction|screenplay|"
                 r"roleplay|role-play|fantasy|worldbuilding|midjourney|prompt for|imagine)\b"),
    ("travel_lifestyle", r"\b(recipe|cook\w*|travel|itinerary|hotel|restaurant|vacation|gift|"
                         r"garden\w*|recommend (a )?(movie|book|game))\b"),
]
TOPIC_TAGS: List[str] = [t for t, _ in TOPIC_RULES] + [OTHER_TOPIC]
_COMPILED_RULES = [(t, re.compile(rx, re.I)) for t, rx in TOPIC_RULES]


def topic_tags(text: str) -> List[str]:
    """Multi-label topic tags for `text`, in TOPIC_RULES order; ["other"] when
    nothing matches. A keyword heuristic, not a classifier: it will mislabel
    some messages and miss paraphrases. Treat tags as a coarse topic filter, and
    override them with a "topics" field in the JSONL (e.g. LLM-tagged) if needed."""
    tags = [t for t, rx in _COMPILED_RULES if rx.search(text or "")]
    return tags or [OTHER_TOPIC]


def _read_jsonl_lines(path: str):
    with open(path) as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield n, json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{n}: invalid JSON ({e})") from e


def load_corpus_records(root: str = ROOT, min_chars: int = 40, max_chars: int = 3000) -> List[Dict]:
    """Real messages as {"text", "topics", "source"}. `source` is the file stem and
    `topics` comes from the heuristic tagger, unless the JSONL line already has a
    "source" or "topics" field, which wins (so tagged files can override the heuristic)."""
    out = []
    for p in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        for n, row in _read_jsonl_lines(p):
            t = row.get("text", "")
            if not (min_chars <= len(t) <= max_chars):
                continue
            topics = row.get("topics")
            if topics is None:
                topics = topic_tags(t)
            elif not (isinstance(topics, list) and topics and all(isinstance(x, str) for x in topics)):
                raise ValueError(f"{p}:{n}: 'topics' must be a non-empty list of strings, got {topics!r}")
            out.append({"text": t, "topics": list(topics), "source": row.get("source") or stem})
    return out


def matched_pool(records: Sequence[Dict], text_or_topics: Union[str, Iterable[str]],
                 min_matched: int = 15, user_text: Optional[str] = None,
                 length_band: Optional[float] = None) -> Tuple[List[str], Dict]:
    """Real messages sharing at least one topic with one benchmark item.

    `text_or_topics` is the item's system+user text (tagged with `topic_tags`) or a
    list of tags. If fewer than `min_matched` messages match, returns the WHOLE pool
    with info["fallback"] = True; callers must report that as NOT topic-matched.

    `length_band` (off by default), with `user_text`: additionally keep only messages
    whose length is within a factor of `length_band` of the item's user turn (e.g. 4.0
    keeps L/4..4L), applied only if at least `min_matched` messages survive;
    info["length_matched"] says whether it was applied.
    Info: {"topics", "n_matched", "fallback", "n_total", "length_matched"}."""
    topics = topic_tags(text_or_topics) if isinstance(text_or_topics, str) else list(text_or_topics)
    if length_band is not None and (length_band < 1 or user_text is None):
        raise ValueError(f"length_band needs user_text and a factor >= 1, got length_band={length_band!r}, "
                         f"user_text={'None' if user_text is None else 'given'}")
    wanted = set(topics)
    matched = [r for r in records if wanted & set(r.get("topics", []))]
    info = {"topics": topics, "n_total": len(records), "length_matched": False}
    if len(matched) < min_matched:
        info.update(n_matched=len(matched), fallback=True)
        return [r["text"] for r in records], info
    if length_band is not None and user_text:
        lo, hi = len(user_text) / length_band, len(user_text) * length_band
        banded = [r for r in matched if lo <= len(r["text"]) <= hi]
        if len(banded) >= min_matched:
            matched = banded
            info["length_matched"] = True
    info.update(n_matched=len(matched), fallback=False)
    return [r["text"] for r in matched], info


def scenario_pool(scenario, records: Optional[Sequence[Dict]] = None, root: str = ROOT,
                  min_matched: int = 15) -> Tuple[List[str], Dict]:
    """The real pool for one scenario, plus the info dict callers print.
    A benchmark item (scenario.original set) gets messages on the item's own
    topics via `matched_pool`; a hand-written scenario keeps its
    `corpus_keywords` regex. info["fallback"] is True whenever the returned
    pool is NOT topic-matched, so reports can say so."""
    records = list(records) if records is not None else load_corpus_records(root)
    original = getattr(scenario, "original", None)
    if original:
        text = f"{original.get('system', '')}\n{original.get('user', '')}"
        return matched_pool(records, text, min_matched=min_matched)
    keywords = getattr(scenario, "corpus_keywords", "")
    hits = [r["text"] for r in records if keywords and re.search(keywords, r["text"], re.I)]
    info = {"topics": [], "n_total": len(records), "length_matched": False}
    if len(hits) >= min_matched:
        info.update(n_matched=len(hits), fallback=False)
        return hits, info
    info.update(n_matched=len(hits), fallback=True)
    return [r["text"] for r in records], info


def _hf_rows_page(dataset: str, config: str, split: str, offset: int, length: int) -> List[Dict]:
    q = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split,
                                "offset": offset, "length": length})
    with urllib.request.urlopen(f"https://datasets-server.huggingface.co/rows?{q}", timeout=60) as r:
        return json.loads(r.read()).get("rows", [])


def fetch_hf_rows_by_topic(dataset: str, config: str, split: str, topics: Sequence[str], per_topic: int,
                           extract: Callable[[Dict], str], root: str = ROOT, name: str = "corpus_by_topic",
                           max_rows: int = 5000, min_chars: int = 40, max_chars: int = 3000,
                           fetch_page: Callable[[str, str, str, int, int], List[Dict]] = _hf_rows_page
                           ) -> Tuple[str, Dict[str, int]]:
    """Keep pulling rows until every topic in `topics` has `per_topic` messages or
    `max_rows` rows have been read. Writes {"text", "topics", "source"} lines to
    <root>/<name>.jsonl and returns (path, counts per requested topic) so the caller
    can see shortfalls. A message is kept if it carries a topic that is still short;
    it counts toward every requested topic it carries. Network access goes only
    through `fetch_page(dataset, config, split, offset, length)`, injectable for tests."""
    unknown = [t for t in topics if t not in TOPIC_TAGS]
    if unknown or not topics or per_topic < 1:
        raise ValueError(f"topics must be a non-empty subset of {TOPIC_TAGS} and per_topic >= 1; "
                         f"got topics={list(topics)!r}, per_topic={per_topic!r}")
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{name}.jsonl")
    counts = {t: 0 for t in topics}
    offset, page = 0, 100
    with open(path, "w") as fh:
        while offset < max_rows and any(c < per_topic for c in counts.values()):
            rows = fetch_page(dataset, config, split, offset, min(page, max_rows - offset))
            if not rows:
                break
            for row in rows:
                t = extract(row.get("row", {}))
                if not t or not (min_chars <= len(t) <= max_chars):
                    continue
                tags = topic_tags(t)
                short = [x for x in tags if x in counts and counts[x] < per_topic]
                if not short:
                    continue
                fh.write(json.dumps({"text": t, "topics": tags, "source": name}) + "\n")
                for x in tags:
                    if x in counts:
                        counts[x] += 1
            offset += len(rows)
    return path, counts
