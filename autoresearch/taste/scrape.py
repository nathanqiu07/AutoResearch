"""Corpus collection for a selected researcher.

* arXiv: author search through the public export API (abstracts).
* Web pages: blogs/articles by URL, HTML stripped to text.
* X/Twitter: the official archive export (`tweets.js`) is imported locally;
  live scraping needs API credentials the user must supply themselves.
Everything lands in data/researchers/<slug>/corpus/ as plain text with a
`kind` prefix ('research' or 'other')."""
from __future__ import annotations

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
