"""Public sources for a researcher's work, and importing them into a studio profile.

Free, keyless sources (each fetched with a plain urllib request):
  * Semantic Scholar: author search (for disambiguation) and the author's papers with abstracts;
  * arXiv: the author's papers by name, kept only when the name is in the author list;
  * Wikipedia: a short bio for the profile card (metadata only, never taste evidence,
    since it is written about the person, not by them);
  * web pages, a LessWrong user's posts, and a blog's RSS feed.
Paid, optional: an Exa harvest through taste/scrape.scrape_exa (needs EXA_API_KEY).

Every imported document goes through store.add_doc, which dedupes by URL.
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable, Dict, List, Optional

from ..taste import scrape
from . import store

UA = {"User-Agent": "autoresearch-profile-studio/0.1"}
S2 = "https://api.semanticscholar.org/graph/v1"
S2_PAPER_FIELDS = "title,abstract,year,publicationDate,venue,citationCount,externalIds,url,authors"


def _get(url: str, timeout: int = 30, retries: int = 3, data: Optional[bytes] = None,
         headers: Optional[dict] = None) -> bytes:
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 * 2 ** attempt)
                continue
            raise RuntimeError(f"{urllib.parse.urlparse(url).netloc} answered HTTP {e.code}") from None
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(1 + attempt)
                continue
            raise RuntimeError(f"could not reach {urllib.parse.urlparse(url).netloc}: {e.reason}") from None
    raise RuntimeError("unreachable")


def _get_json(url: str, **kw):
    return json.loads(_get(url, **kw))


def strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|nav|footer|header|noscript|svg).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# ---- Semantic Scholar ----------------------------------------------------------

def s2_search(name: str, limit: int = 10) -> List[dict]:
    """Candidate authors for a name, most cited first, for the person to pick from."""
    q = urllib.parse.urlencode({"query": name, "limit": limit,
                                "fields": "name,affiliations,paperCount,citationCount,hIndex,url,homepage"})
    rows = _get_json(f"{S2}/author/search?{q}").get("data", [])
    out = [{"author_id": r["authorId"], "name": r.get("name", ""), "affiliations": r.get("affiliations") or [],
            "papers": r.get("paperCount") or 0, "citations": r.get("citationCount") or 0,
            "h_index": r.get("hIndex") or 0, "url": r.get("url", ""), "homepage": r.get("homepage") or ""}
           for r in rows]
    return sorted(out, key=lambda r: -r["citations"])


def s2_author_sample_titles(author_id: str, k: int = 3) -> List[str]:
    """A few of the author's most cited titles, so the person can tell same-named authors apart."""
    papers = s2_papers(author_id, limit=100)
    return [p["title"] for p in sorted(papers, key=lambda p: -p["citations"])[:k]]


def s2_papers(author_id: str, limit: int = 100) -> List[dict]:
    if not re.fullmatch(r"\d+", str(author_id)):
        raise store.StudioError(f"invalid Semantic Scholar author id {author_id!r}")
    q = urllib.parse.urlencode({"fields": S2_PAPER_FIELDS, "limit": min(int(limit), 1000)})
    rows = _get_json(f"{S2}/author/{author_id}/papers?{q}").get("data", [])
    out = []
    for r in rows:
        ext = r.get("externalIds") or {}
        arxiv = ext.get("ArXiv")
        out.append({"title": " ".join((r.get("title") or "").split()), "abstract": r.get("abstract") or "",
                    "date": r.get("publicationDate") or (f"{r['year']}-01-01" if r.get("year") else ""),
                    "year": r.get("year"), "venue": r.get("venue") or "", "citations": r.get("citationCount") or 0,
                    "url": f"https://arxiv.org/abs/{arxiv}" if arxiv else (r.get("url") or ""),
                    "arxiv": arxiv or "", "authors": [a.get("name", "") for a in r.get("authors") or []]})
    return out


# ---- arXiv ---------------------------------------------------------------------------

def arxiv_papers(name: str, max_results: int = 50) -> List[dict]:
    """The person's arXiv papers: searched by full name, kept only when the name matches an
    author (scrape.author_position), so a shared surname alone never counts."""
    q = urllib.parse.urlencode({"search_query": f'au:"{name}"', "max_results": int(max_results),
                                "sortBy": "submittedDate", "sortOrder": "descending"})
    tree = ET.fromstring(_get(f"https://export.arxiv.org/api/query?{q}", timeout=60))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in tree.findall("a:entry", ns):
        authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        m = scrape.ARXIV_ID.search(e.findtext("a:id", "", ns))
        if not m or not scrape.author_position(authors, name):
            continue
        out.append({"title": " ".join(e.findtext("a:title", "", ns).split()),
                    "abstract": " ".join(e.findtext("a:summary", "", ns).split()),
                    "date": e.findtext("a:published", "", ns)[:10], "url": f"https://arxiv.org/abs/{m.group(1)}",
                    "arxiv": m.group(1), "authors": authors, "venue": "arXiv",
                    "position": scrape.author_position(authors, name)})
    return out


# ---- Wikipedia -----------------------------------------------------------------------

def wikipedia_summary(name: str) -> Optional[dict]:
    title = urllib.parse.quote(name.strip().replace(" ", "_"))
    try:
        d = _get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}", retries=1)
    except RuntimeError:
        return None
    if d.get("type") != "standard" or not d.get("extract"):
        return None
    return {"title": d.get("title", name), "extract": d["extract"], "description": d.get("description", ""),
            "url": (d.get("content_urls") or {}).get("desktop", {}).get("page", "")}


# ---- web pages, LessWrong, RSS ------------------------------------------------------

def fetch_page(url: str) -> Dict[str, str]:
    p = urllib.parse.urlparse(url.strip())
    if p.scheme not in ("http", "https") or not p.netloc:
        raise store.StudioError(f"not an http(s) URL: {url!r}")
    raw = _get(url.strip(), timeout=60, retries=1).decode("utf-8", "ignore")
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    title = html.unescape(" ".join(m.group(1).split())) if m else p.netloc + p.path
    text = strip_html(raw) if re.search(r"(?i)<(html|body|p|div)\b", raw) else raw.strip()
    return {"title": title, "text": text, "url": url.strip()}


def lesswrong_posts(username: str, limit: int = 30) -> List[dict]:
    """A LessWrong user's posts with their text, newest first, via the public GraphQL API."""
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", username or ""):
        raise store.StudioError(f"invalid LessWrong username {username!r}")

    def gql(query):
        body = json.dumps({"query": query}).encode()
        return json.loads(_get("https://www.lesswrong.com/graphql", data=body,
                               headers={"content-type": "application/json"}, timeout=60))["data"]
    user = gql(f'{{ user(input:{{selector:{{slug:"{username}"}}}}){{ result {{ _id displayName }} }} }}')
    res = (user.get("user") or {}).get("result")
    if not res:
        raise store.StudioError(f"no LessWrong user {username!r}")
    posts = gql(f'{{ posts(input:{{terms:{{view:"userPosts", userId:"{res["_id"]}", limit:{int(limit)}}}}}){{ '
                'results { pageUrl title postedAt htmlBody } } }')["posts"]["results"]
    return [{"title": p["title"], "url": p["pageUrl"], "date": (p.get("postedAt") or "")[:10],
             "text": strip_html(p.get("htmlBody") or "")} for p in posts if p.get("htmlBody")]


def feed_items(url: str, name: str, limit: int = 20) -> List[dict]:
    """Posts from a blog's RSS feed, each fetched in full."""
    listed = scrape.list_feed(url, name)
    out = []
    for link, meta in sorted(listed.items(), key=lambda kv: kv[1]["published"], reverse=True)[:limit]:
        page = fetch_page(link)
        out.append({"title": meta["title"] or page["title"], "url": link, "date": meta["published"],
                    "text": page["text"]})
    return out


def exa_available() -> bool:
    return bool(os.environ.get("EXA_API_KEY"))


# ---- import into a profile ---------------------------------------------------------

def _paper_text(p: dict) -> str:
    lines = [f"Authors: {', '.join(p.get('authors') or [])}" if p.get("authors") else "",
             f"Venue: {p['venue']}" if p.get("venue") else "",
             f"Citations: {p['citations']}" if p.get("citations") else ""]
    body = p.get("abstract") or ""
    return "\n".join(l for l in lines if l) + ("\n\n" + body if body else "")


def import_papers(root: str, slug: str, papers: List[dict], source: str, log: Callable = print,
                  require_abstract: bool = True) -> Dict[str, int]:
    """Write papers as research documents. A paper with no abstract has only a title, which
    says little about taste, so it is skipped unless require_abstract is False."""
    added = dup = skipped = 0
    for p in papers:
        if not p.get("title") or (require_abstract and not p.get("abstract")):
            skipped += 1
            continue
        extra = {"authors": json.dumps(p.get("authors") or [], ensure_ascii=False)}
        if p.get("position"):
            extra["author_position"] = p["position"]
        _, created = store.add_doc(root, slug, "research", p["title"], _paper_text(p), source=source,
                                   url=p.get("url", ""), date=p.get("date", ""), extra=extra)
        added, dup = added + created, dup + (not created)
    log(f"{source}: {added} added, {dup} already present, {skipped} skipped (no abstract)")
    return {"added": added, "duplicates": dup, "skipped": skipped}


def gather(root: str, slug: str, opts: dict, log: Callable = print) -> dict:
    """Run every source the person ticked. One failing source is reported and the rest
    still run, so a rate limit on one API does not lose the others."""
    meta = store.require_editable(root, slug)
    name = (opts.get("name") or meta["name"]).strip()
    report: Dict[str, object] = {}

    def step(key, fn):
        try:
            report[key] = fn()
        except Exception as e:  # reported to the person, not swallowed
            log(f"{key}: failed: {e}")
            report[key] = {"error": str(e)}

    seen_arxiv = set()

    if opts.get("s2_author_id"):
        def s2():
            papers = s2_papers(opts["s2_author_id"], opts.get("s2_max", 100))
            log(f"semantic scholar: {len(papers)} papers listed")
            seen_arxiv.update(p["arxiv"] for p in papers if p["arxiv"])
            return import_papers(root, slug, papers, "semantic_scholar", log)
        step("semantic_scholar", s2)
    if opts.get("arxiv"):
        def ax():
            papers = [p for p in arxiv_papers(name, opts.get("arxiv_max", 50)) if p["arxiv"] not in seen_arxiv]
            log(f"arxiv: {len(papers)} papers matched {name!r} (after removing ones already imported)")
            return import_papers(root, slug, papers, "arxiv", log)
        step("arxiv", ax)
    if opts.get("wikipedia"):
        def wiki():
            w = wikipedia_summary(opts.get("wikipedia_title") or name)
            if not w:
                log("wikipedia: no article found")
                return {"found": False}
            store.update_meta(root, slug, bio=w["extract"], bio_source=w["url"])
            log(f"wikipedia: bio taken from {w['url']} (shown on the card, not used as taste evidence)")
            return {"found": True, "url": w["url"]}
        step("wikipedia", wiki)
    if opts.get("lesswrong_user"):
        def lw():
            posts = lesswrong_posts(opts["lesswrong_user"], opts.get("lesswrong_max", 30))
            added = sum(store.add_doc(root, slug, "research", p["title"], p["text"], "lesswrong",
                                      url=p["url"], date=p["date"])[1] for p in posts if p["text"])
            log(f"lesswrong: {added} posts added of {len(posts)}")
            return {"added": added, "listed": len(posts)}
        step("lesswrong", lw)
    if opts.get("rss"):
        def rss():
            items = feed_items(opts["rss"], name, opts.get("rss_max", 20))
            added = sum(store.add_doc(root, slug, "research", p["title"], p["text"], "rss",
                                      url=p["url"], date=p["date"])[1] for p in items if p["text"])
            log(f"rss: {added} posts added of {len(items)}")
            return {"added": added, "listed": len(items)}
        step("rss", rss)
    for url in [u.strip() for u in opts.get("urls") or [] if u.strip()]:
        def page(url=url):
            pg = fetch_page(url)
            _, created = store.add_doc(root, slug, opts.get("url_kind", "research"), pg["title"], pg["text"],
                                       "url", url=url)
            log(f"web: {'added' if created else 'already present'}: {pg['title']}")
            return {"added": int(created)}
        step(f"url:{url}", page)
    if opts.get("exa"):
        def exa():
            if not exa_available():
                raise store.StudioError("harvest unavailable on this server: no Exa key configured")
            from ..integrations.exa import ExaClient
            start = opts.get("exa_start") or "2015-01-01"
            end = opts.get("exa_end") or datetime.date.today().isoformat()
            client = ExaClient(cache_dir=os.path.join("runs", "exa_cache"))
            log(f"exa: harvesting {name!r} {start}..{end}")
            rep = scrape.scrape_exa(name, os.path.join(root, slug), client, start, end)
            log(f"exa: done, cost ${client.cost:.2f}")
            return {k: v for k, v in rep.items() if isinstance(v, (int, float, str))}
        step("exa", exa)
    return report
