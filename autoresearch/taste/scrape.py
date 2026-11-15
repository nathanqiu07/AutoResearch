"""Corpus collection for a selected researcher.

* arXiv: author search through the public export API (abstracts).
* Web pages: blogs/articles by URL, HTML stripped to text.
* X/Twitter: the official archive export (`tweets.js`) is imported locally;
  live scraping needs API credentials the user must supply themselves.
Everything lands in data/researchers/<slug>/corpus/ as plain text with a
`kind` prefix ('research' or 'other')."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "autoresearch-taste-scraper/0.1"}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _save(root, kind, stem, text):
    os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
    path = os.path.join(root, "corpus", f"{kind}__{slugify(stem)[:60]}.txt")
    with open(path, "w") as f:
        f.write(text)
    return path


def scrape_arxiv(author: str, root: str, max_results: int = 25):
    q = urllib.parse.urlencode({"search_query": f'au:"{author}"', "max_results": max_results})
    with urllib.request.urlopen(urllib.request.Request(
            f"http://export.arxiv.org/api/query?{q}", headers=UA), timeout=60) as r:
        tree = ET.fromstring(r.read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    paths = []
    for e in tree.findall("a:entry", ns):
        title = (e.findtext("a:title", "", ns) or "").strip()
        summary = (e.findtext("a:summary", "", ns) or "").strip()
        paths.append(_save(root, "research", title, f"{title}\n\n{summary}"))
    return paths


def scrape_url(url: str, root: str, kind: str = "research"):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        raw = r.read().decode("utf-8", "ignore")
    raw = re.sub(r"(?is)<(script|style|nav|footer).*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    return _save(root, kind, urllib.parse.urlparse(url).path or url, text)


def import_x_archive(tweets_js: str, root: str):
    raw = open(tweets_js).read()
    data = json.loads(raw[raw.index("["):])
    texts = [t.get("tweet", t).get("full_text", "") for t in data]
    research = [t for t in texts if re.search(r"paper|model|eval|experiment|research", t, re.I)]
    other = [t for t in texts if t not in research]
    out = []
    if research:
        out.append(_save(root, "research", "x_posts", "\n".join(research)))
    if other:
        out.append(_save(root, "other", "x_posts", "\n".join(other)))
    return out


# ---- Exa harvest (Track S) -------------------------------------------------
# Each item is checked as his own work and dated, then written with front matter that
# taste/timesplit.read_doc understands. See docs/track-s-extraction.md.

ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
FORUM_POST = re.compile(r"(?:lesswrong\.com|alignmentforum\.org)/posts/([A-Za-z0-9]+)", re.IGNORECASE)
TEXT_DATE = re.compile(r"\b(20\d\d-[01]\d-[0-3]\d)\b")
# (category, domains, kind). Papers use Exa's "publication" category; the other sources are
# picked by domain, since Exa's category enum has no tweet, talk or code value.
HARVEST_SOURCES = (("publication", ["arxiv.org"], "paper"),
                   (None, ["lesswrong.com", "alignmentforum.org"], "post"),
                   (None, ["apolloresearch.ai"], "blog"),
                   (None, ["x.com", "twitter.com"], "tweet"),
                   (None, ["youtube.com"], "talk"),
                   (None, ["github.com"], "code"))
ENUMERATE_SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {"title": {"type": "string"}, "url": {"type": "string"},
                                     "date": {"type": "string"}, "kind": {"type": "string"}}}}}}


def canonical_url(url: str) -> str:
    m = ARXIV_ID.search(url)
    if m:
        return f"https://arxiv.org/abs/{m.group(1)}"
    m = FORUM_POST.search(url)
    if m:
        return f"https://www.lesswrong.com/posts/{m.group(1)}"
    p = urllib.parse.urlparse(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    return f"https://{host}{p.path.rstrip('/')}"


def fetch_arxiv_meta(arxiv_ids):
    """{id: {"authors": [...], "published": "YYYY-MM-DD"}} from arXiv's API (v1 date)."""
    out = {}
    ids = sorted(set(arxiv_ids))
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"id_list": ",".join(ids[i:i + 50]), "max_results": 50})
        with urllib.request.urlopen(urllib.request.Request(
                f"http://export.arxiv.org/api/query?{q}", headers=UA), timeout=60) as r:
            tree = ET.fromstring(r.read())
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in tree.findall("a:entry", ns):
            m = ARXIV_ID.search(e.findtext("a:id", "", ns))
            if m:
                out[m.group(1)] = {"authors": [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
                                   "published": (e.findtext("a:published", "", ns) or "")[:10]}
    return out


def _name_pattern(name: str) -> str:
    first, last = (re.escape(p) for p in (name.split()[0], name.split()[-1]))
    return rf"(?:\b{first}\s+(?:\w\.?\s+)?{last}\b|\b{first[0]}\.?\s+{last}\b|\b{last},\s*{first[0]})"


def _is_him(text: str, name: str) -> bool:
    """An author string names him: "Marius Hobbhahn", "M. Hobbhahn" or "Hobbhahn, M"."""
    return re.search(_name_pattern(name), text, re.IGNORECASE) is not None


def _byline(text: str, name: str) -> bool:
    """A line near the top that starts with his name, optionally after "By" or "Authors:"."""
    return re.search(rf"(?:^|\n)\s*(?:by\s+|written\s+by\s+|authors?:\s*)?{_name_pattern(name)}",
                     text[:500], re.IGNORECASE) is not None


def author_position(authors, name):
    """'solo' | 'first' | 'last' | 'middle', or None when he isn't listed."""
    hits = [i for i, a in enumerate(authors) if a and _is_him(a, name)]
    if not hits:
        return None
    i = hits[0]
    return "solo" if len(authors) == 1 else "first" if i == 0 else "last" if i == len(authors) - 1 else "middle"


def _kind(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    for _, domains, kind in HARVEST_SOURCES:
        if any(host == d or host.endswith("." + d) for d in domains):
            return kind
    return "post"


def _windows(start: str, end: str, months: int):
    import datetime
    s, e = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)
    while s <= e:
        y, m = divmod(s.month - 1 + months, 12)
        nxt = datetime.date(s.year + y, m + 1, 1)
        yield s.isoformat(), min(e, nxt - datetime.timedelta(days=1)).isoformat()
        s = nxt


def _authorship(item, name, meta):
    """(authors, position or None, drop reason or None)."""
    url = item["url"]
    m = ARXIV_ID.search(url)
    if m and m.group(1) in meta:
        authors = meta[m.group(1)]["authors"]
    elif item.get("author"):
        authors = [a.strip() for a in re.split(r"[,;]| and ", item["author"]) if a.strip()]
    elif ((_kind(url) == "tweet" and "".join(name.lower().split()) in url.lower())
          or _byline(item.get("text") or "", name)):
        authors = [name]
    else:
        return [], None, "no_author_evidence"
    if _kind(url) == "tweet" and "".join(name.lower().split()) in url.lower():
        return [name], "solo", None
    pos = author_position(authors, name)
    return authors, pos, None if pos else "not_author"


def _date(item, meta):
    m = ARXIV_ID.search(item["url"])
    if m and meta.get(m.group(1), {}).get("published"):
        return meta[m.group(1)]["published"], "arxiv_v1"
    if item.get("publishedDate"):
        return item["publishedDate"][:10], "exa"
    m = TEXT_DATE.search((item.get("text") or "")[:2000])
    return (m.group(1), "text") if m else ("", "none")


def _write_doc(root, prefix, fm, text):
    stem = slugify(fm["title"] or fm["url"])[:50] + "_" + hashlib.sha256(fm["url"].encode()).hexdigest()[:8]
    lines = ["---"] + [f"{k}: {v}" for k, v in fm.items() if v not in (None, "")] + ["---"]
    os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
    path = os.path.join(root, "corpus", f"{prefix}__{stem}.txt")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n" + text)
    return path


def scrape_exa(name, root, client, start, end, window_months=3, arxiv_meta=fetch_arxiv_meta):
    """Find, check and save everything `name` published between start and end (YYYY-MM-DD).
    Writes corpus/*.txt and harvest_manifest.jsonl; returns counts and Exa spend."""
    surname = name.split()[-1]
    found = {}

    def add(url, title=""):
        if url:
            found.setdefault(canonical_url(url), {"url": url, "title": title})

    deep = client.deep(f"Every paper, blog post, forum post, talk and tweet written by {name}",
                       ENUMERATE_SCHEMA, start_date=start, end_date=end,
                       additional_queries=[f"{name} arXiv papers", f"{name} LessWrong posts",
                                           f"{name} Apollo Research blog", f"{name} talk podcast"])
    for it in ((deep.get("output") or {}).get("content") or {}).get("items", []):
        add(it.get("url"), it.get("title", ""))
    for lo, hi in _windows(start, end, window_months):
        for category, domains, _ in HARVEST_SOURCES:
            for r in client.search(f"{name}", num_results=25, category=category, start_date=lo, end_date=hi,
                                   include_domains=domains, include_text=[surname]):
                add(r.get("url"), r.get("title", ""))
    for r in client.contents(["https://www.apolloresearch.ai/blog", "https://www.apolloresearch.ai/research"],
                             subpages=25, subpage_target=["blog", "research"]):
        for sp in r.get("subpages") or []:
            add(sp.get("url"), sp.get("title", ""))

    urls = [v["url"] for v in found.values()]
    items = {}
    for i in range(0, len(urls), 20):
        for r in client.contents(urls[i:i + 20], text_chars=200_000):
            items.setdefault(canonical_url(r.get("url", "")), r)
    meta = arxiv_meta([m.group(1) for u in items for m in [ARXIV_ID.search(u)] if m])

    # One piece of work posted in several places (arXiv, LessWrong, his lab's blog) is one
    # document, dated by its earliest copy, so a decision can't land on both sides of T.
    by_title = {}
    for curl, item in items.items():
        title = re.sub(r"[^a-z0-9]+", " ", (item.get("title") or "").lower()).strip()
        if _kind(curl) != "tweet" and len(title) >= 12:
            by_title.setdefault(title, []).append(curl)
    crossposts = {}
    for urls in by_title.values():
        if len(urls) > 1:
            urls.sort(key=lambda u: (_date(dict(items[u], url=u), meta)[0] or "9999", _kind(u) != "paper", u))
            crossposts.update({u: urls[0] for u in urls[1:]})

    manifest, kept, tweets = [], 0, {}
    for curl, item in sorted(items.items()):
        if curl in crossposts:
            manifest.append({"url": curl, "title": item.get("title", ""), "reason": "crosspost_of",
                             "kept_as": crossposts[curl]})
            continue
        item = dict(item, url=curl)
        authors, pos, reason = _authorship(item, name, meta)
        date, date_source = _date(item, meta)
        row = {"url": curl, "title": item.get("title", ""), "date": date, "reason": reason}
        if reason is None and _kind(curl) == "tweet":
            if not date:
                row["reason"] = "undated_tweet"
            else:
                tweets.setdefault(date[:7], []).append((date, curl, item.get("text") or ""))
                row["reason"] = "kept_in_month_file"
        elif reason is None:
            fm = {"url": curl, "title": " ".join((item.get("title") or "").split()), "publishedDate": date,
                  "date_source": date_source, "authors": json.dumps(authors), "author_position": pos,
                  "kind": _kind(curl), "exa_request_id": item.get("id", "")}
            row["file"] = os.path.basename(_write_doc(root, "research", fm, item.get("text") or ""))
            row["reason"] = "kept"
            kept += 1
        manifest.append(row)
    for month, posts in sorted(tweets.items()):
        posts.sort()
        fm = {"url": posts[0][1], "title": f"X posts {month}", "publishedDate": posts[-1][0],
              "date_source": "exa", "authors": json.dumps([name]), "author_position": "solo",
              "kind": "tweet_month", "exa_request_id": ""}
        _write_doc(root, "other", fm, "\n\n".join(f"[{d}] {t}" for d, _, t in posts))
        kept += 1
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "harvest_manifest.jsonl"), "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in manifest)
    dropped = {}
    for r in manifest:
        if not r["reason"].startswith("kept") and r["reason"] != "crosspost_of":
            dropped[r["reason"]] = dropped.get(r["reason"], 0) + 1
    return {"kept": kept, "dropped": dropped, "candidates": len(found), "exa_cost": round(client.cost, 4)}
