"""Real distractors for the public track's time split (PLAN 6.3, 10 Exa item 1).

timesplit's held-out pairs set the researcher's real decision against an alternative a model
wrote or paraphrased. Here the alternative is a real project: a paper or post by someone else in
the same area, published after the cutoff T, as close in topic to his own post-T project as the
band allows. Then "he took this one" is a prediction between two things real researchers chose
to do, and a judge cannot win by spotting the invented option.

Steps, for each of his research documents dated on or after T (the held-out projects):
  1. Exa search for work on the same topic, dated from max(T, date - 6 months) to date + 6 months,
     with his identity.json exclude_domains/exclude_text.
  2. Each result is checked the way scrape.py checks his own work, but the other way round:
     authors from arXiv metadata, else Exa's author field (no author evidence: dropped); dropped if
     any author is him (scrape._is_him) or matches his banned names, if its URL is one of his own
     documents, if the result mentions him, or if its verified date (arXiv v1, else Exa) is before T.
  3. TF-IDF cosine on title + summary (textsim). A candidate qualifies when lo <= cos < hi: below
     lo it is an easy pick (a different area), at or above hi, or with a near-identical title, it is
     likely the same work. Each project gets the closest qualifying candidate; a candidate serves
     one project at most.
  4. The pair is written by timesplit.render_pair (same prompt, same check_pair form checks) and
     timesplit._pair_row, so the row has timesplit's exact fields, plus distractor_source "real"
     and the distractor's URL, title, date and authors.

The band (lo, hi) is set on dev data only (`band`): from one researcher's documents before T,
lo is the median and hi the 95th percentile of each document's nearest-neighbour similarity to
his other documents. So "hard" means at least as close as his typical nearest other project, and
"near-duplicate" means closer than nearly any two of his distinct projects (capped at NEAR_DUP).
DEFAULT_BAND is only a fallback and every row records which band it used.

Leakage (checked by `check_leakage` before anything is written): every pair is held out and dated
on or after T, every distractor is dated on or after T and none is his. Nothing here is written into
the researcher's directory, so the history file and the profile built from it are unchanged.

    python3 -m autoresearch.taste.real_distractors band --researcher DEV_DIR --cutoff YYYY-MM-DD --out band.json
    python3 -m autoresearch.taste.real_distractors --researcher DIR --cutoff YYYY-MM-DD --out pairs.jsonl \\
        --band band.json --max-usd 5
    python3 -m autoresearch.taste.real_distractors compare --researcher DIR --pairs pairs.jsonl --method m1 --max-usd 10
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import random
import re
import sys
from dataclasses import asdict
from typing import Callable, Dict, List, Optional, Tuple

from . import timesplit
from .researcher import Researcher
from .scrape import ARXIV_ID, _is_him, canonical_url
from .textsim import TfIdf, cosine, top_shared_terms
from .usermodel import Choice, digest

REAL_VERSION = "real-distractor-v1"
SOURCE = "real"
WINDOW = timesplit.HALF_YEAR
SUMMARY_CHARS = 1200
NEAR_DUP = 0.8            # cosine at or above which two texts are treated as one work, whatever the band
TITLE_DUP = 0.6           # title word Jaccard at or above which two items are one work (as scrape.py)
DEFAULT_BAND = (0.15, 0.6)  # untuned fallback; set the band with `band` on a dev researcher


# ---- the researcher's held-out projects -------------------------------------------

def _summary(text: str, n: int = SUMMARY_CHARS) -> str:
    body = re.sub(r"\A\s*#[^\n]*\n", "", text)        # a markdown title line repeats the title
    return " ".join(body.split())[:n]


def _first_sentence(text: str, n: int = 240) -> str:
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    return (m.group(1) if m else text)[:n].strip()


def _title_words(title: str) -> set:
    return set(re.sub(r"[^a-z0-9]+", " ", str(title).lower()).split())


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def own_documents(researcher: Researcher) -> List[dict]:
    """{doc, url, title, date, authors, author_position, kind, summary} for every dated research
    document in his corpus (other__ files are not projects)."""
    out = []
    for p in sorted(glob.glob(os.path.join(researcher.root, "corpus", "research__*.txt"))):
        date, text = timesplit.read_doc(p)
        if date is None:
            continue
        fm = timesplit.front_matter(p)
        try:
            authors = json.loads(fm.get("authors") or "[]")
        except json.JSONDecodeError:
            authors = []
        out.append({"doc": os.path.basename(p), "url": fm.get("url", ""), "title": fm.get("title", ""),
                    "date": date.isoformat(), "authors": authors, "author_position": fm.get("author_position"),
                    "kind": fm.get("kind", ""), "summary": _summary(text)})
    return sorted(out, key=lambda d: (d["date"], d["doc"]))


def heldout_projects(researcher: Researcher, cutoff: str) -> List[dict]:
    return [d for d in own_documents(researcher) if d["date"] >= cutoff]


def own_urls(researcher: Researcher) -> set:
    """Canonical URLs of everything the harvest attributed to him or saw as his crosspost."""
    urls = {canonical_url(d["url"]) for d in own_documents(researcher) if d["url"]}
    manifest = os.path.join(researcher.root, "harvest_manifest.jsonl")
    for r in timesplit._read_jsonl(manifest):
        if r.get("reason") in ("kept", "kept_in_month_file", "crosspost_of") and r.get("url"):
            urls.add(canonical_url(r["url"]))
    return urls


def text_of(item: dict) -> str:
    return f"{item.get('title', '')}. {item.get('summary', '')}"


# ---- candidates from Exa, checked ------------------------------------------------------

def search_candidates(project: dict, client, identity: dict, cutoff: str, num_results: int = 10,
                      today: Optional[str] = None) -> List[dict]:
    date = datetime.date.fromisoformat(project["date"])
    start = max(datetime.date.fromisoformat(cutoff), date - WINDOW)
    end = date + WINDOW
    if today:
        end = min(end, datetime.date.fromisoformat(today))
    query = f"{project['title']}. {_first_sentence(project['summary'])}"
    return client.search(query, num_results=num_results, start_date=start.isoformat(), end_date=end.isoformat(),
                         exclude_domains=identity.get("exclude_domains") or None,
                         exclude_text=identity.get("exclude_text") or None)


def _result_authors(r: dict, meta: dict) -> List[str]:
    m = ARXIV_ID.search(r.get("url", ""))
    if m and meta.get(m.group(1), {}).get("authors"):
        return list(meta[m.group(1)]["authors"])
    if r.get("author"):
        return [a.strip() for a in re.split(r"[,;]| and ", str(r["author"])) if a.strip()]
    return []


def _result_date(r: dict, meta: dict) -> Tuple[str, str]:
    m = ARXIV_ID.search(r.get("url", ""))
    if m and meta.get(m.group(1), {}).get("published"):
        return meta[m.group(1)]["published"][:10], "arxiv_v1"
    if r.get("publishedDate"):
        return str(r["publishedDate"])[:10], "exa"
    return "", "none"


def verify_candidate(r: dict, identity: dict, own: set, cutoff: str, meta: dict) -> Tuple[Optional[dict], str]:
    """(candidate, "ok") or (None, drop reason). A candidate must be someone else's, dated on or after T."""
    url = canonical_url(r.get("url", ""))
    if not url or url in own:
        return None, "own_work"
    title = " ".join(str(r.get("title") or "").split())
    if len(title) < 8:
        return None, "no_title"
    authors = _result_authors(r, meta)
    if not authors:
        return None, "no_author_evidence"
    banned = re.compile("|".join(map(re.escape, identity["banned"])), re.IGNORECASE)
    if any(_is_him(a, identity["name"]) or banned.search(a) for a in authors):
        return None, "researcher_is_author"
    # Work that discusses him or is hosted by his lab answers his work rather than being an independent choice.
    mentions = [t.lower() for t in identity.get("exclude_text") or []]
    seen = (str(r.get("author") or "") + " " + " ".join(r.get("highlights") or []) + " " + str(r.get("summary") or "")).lower()
    if any(t in seen for t in mentions):
        return None, "mentions_researcher"
    date, date_source = _result_date(r, meta)
    if not date:
        return None, "undated"
    if date < cutoff:
        return None, "before_cutoff"
    summary = str(r.get("summary") or "") or " ".join(r.get("highlights") or []) or str(r.get("text") or "")
    return {"url": url, "title": title, "date": date, "date_source": date_source, "authors": authors,
            "summary": " ".join(summary.split())[:SUMMARY_CHARS]}, "ok"


def collect_candidates(projects: List[dict], researcher: Researcher, client, cutoff: str,
                       arxiv_meta: Callable, num_results: int = 10, today: Optional[str] = None):
    """({project doc: [verified candidates]}, {drop reason: count})."""
    identity = timesplit.load_identity(researcher)
    own = own_urls(researcher)
    raw = {p["doc"]: search_candidates(p, client, identity, cutoff, num_results, today) for p in projects}
    ids = sorted({m.group(1) for rs in raw.values() for r in rs for m in [ARXIV_ID.search(r.get("url", ""))] if m})
    meta = arxiv_meta(ids) if ids else {}
    out, dropped = {}, {}
    for doc, results in raw.items():
        seen = set()
        for r in results:
            cand, reason = verify_candidate(r, identity, own, cutoff, meta)
            if cand is None:
                dropped[reason] = dropped.get(reason, 0) + 1
            elif cand["url"] not in seen:
                seen.add(cand["url"])
                out.setdefault(doc, []).append(cand)
    return out, dropped


# ---- topical match within the band ----------------------------------------------------

def match(projects: List[dict], candidates: Dict[str, List[dict]], band: Tuple[float, float]) -> Dict[str, dict]:
    """{project doc: dict(candidate, similarity, shared_terms)}: the closest qualifying candidate,
    assigned greedily from the highest similarity down, so a candidate serves one project at most."""
    lo, hi = band
    pool = [c for cs in candidates.values() for c in cs]
    tfidf = TfIdf([text_of(p) for p in projects] + [text_of(c) for c in pool])
    vec = {p["doc"]: tfidf.vector(text_of(p)) for p in projects}
    scored = []
    for p in projects:
        for c in candidates.get(p["doc"], []):
            v = tfidf.vector(text_of(c))
            sim = cosine(vec[p["doc"]], v)
            near_dup = sim >= min(hi, NEAR_DUP) or _jaccard(_title_words(p["title"]), _title_words(c["title"])) >= TITLE_DUP
            if lo <= sim and not near_dup:
                scored.append((sim, p["doc"], c["url"], c, top_shared_terms(vec[p["doc"]], v)))
    out, used = {}, set()
    for sim, doc, url, c, terms in sorted(scored, key=lambda x: (-x[0], x[1], x[2])):
        if doc not in out and url not in used:
            out[doc] = dict(c, similarity=round(sim, 4), shared_terms=terms)
            used.add(url)
    return out


def _quantile(xs: List[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))]


def fit_band(researcher: Researcher, cutoff: str, lo_q: float = 0.5, hi_q: float = 0.95) -> dict:
    """The similarity band from his documents before T only (dev data: nothing held out is read).
    Each document's nearest-neighbour cosine to his other documents (pairs with near-identical
    titles excluded, since those are one work); lo = the lo_q quantile, hi = the hi_q quantile
    capped at NEAR_DUP."""
    docs = [d for d in own_documents(researcher) if d["date"] < cutoff]
    if len(docs) < 3:
        raise ValueError(f"band needs at least 3 dated documents before {cutoff}; {researcher.slug} has {len(docs)}")
    tfidf = TfIdf(text_of(d) for d in docs)
    vecs = [tfidf.vector(text_of(d)) for d in docs]
    words = [_title_words(d["title"]) for d in docs]
    nn = []
    for i in range(len(docs)):
        sims = [cosine(vecs[i], vecs[j]) for j in range(len(docs))
                if j != i and _jaccard(words[i], words[j]) < TITLE_DUP]
        if sims:
            nn.append(max(sims))
    lo, hi = _quantile(nn, lo_q), min(NEAR_DUP, _quantile(nn, hi_q))
    if hi <= lo:
        hi = NEAR_DUP
    return {"lo": round(lo, 4), "hi": round(hi, 4), "source": researcher.slug, "cutoff": cutoff,
            "n_docs": len(docs), "lo_quantile": lo_q, "hi_quantile": hi_q, "method": "nearest-neighbour-quantiles",
            "version": REAL_VERSION}


def load_band(path: Optional[str], lo: Optional[float] = None, hi: Optional[float] = None) -> dict:
    if path:
        with open(path) as f:
            band = json.load(f)
    else:
        band = {"lo": DEFAULT_BAND[0], "hi": DEFAULT_BAND[1], "source": "default-untuned"}
    if lo is not None or hi is not None:
        band = dict(band, lo=band["lo"] if lo is None else lo, hi=band["hi"] if hi is None else hi,
                    source=band.get("source", "") + "+manual")
    if not 0 <= band["lo"] < band["hi"] <= 1:
        raise ValueError(f"band must satisfy 0 <= lo < hi <= 1, got {band['lo']}, {band['hi']}")
    return band


# ---- pairs ----------------------------------------------------------------------

def _gist(item: dict) -> str:
    return f"{item['title']}: {_first_sentence(item.get('summary', ''))}".strip(": ")


def project_decision(p: dict) -> dict:
    """A held-out project as a decision row in timesplit's shape (D1: which project to pursue)."""
    return {"decision_id": digest(["project", p["doc"]])[:12], "date": p["date"], "doc": p["doc"], "url": p["url"],
            "point": "D1", "did": _gist(p), "stated_reason": "", "tag": "real_project"}


def render_real_pair(researcher: Researcher, p: dict, cand: dict, llm, cutoff: str, band: dict, seed: int,
                     docs, banned) -> Tuple[Optional[dict], List[str]]:
    d = project_decision(p)
    d["problem"] = ("Choosing which research project to take on next. Both candidates are about "
                    + ", ".join(cand.get("shared_terms") or ["the same area"]) + ".")
    # Neither title may appear in the context, nor any of his later titles (timesplit's check).
    later = timesplit._later_titles(docs, d["date"]) + [p["title"], cand["title"]]
    pair, problems = timesplit.render_pair(d, _gist(cand), llm, later, banned, seed)
    if pair is None:
        return None, problems
    meta = {name: fm for _, name, fm in docs}
    row = timesplit._pair_row(researcher, d, {"text": _gist(cand), "source": SOURCE}, pair, cutoff, seed, meta)
    row.update(prompt_versions=row["prompt_versions"] + [REAL_VERSION], distractor_url=cand["url"],
               distractor_title=cand["title"], distractor_date=cand["date"], distractor_date_source=cand["date_source"],
               distractor_authors=cand["authors"], similarity=cand["similarity"],
               band={"lo": band["lo"], "hi": band["hi"], "source": band.get("source", "")})
    return row, []


def check_leakage(pairs: List[dict], researcher: Researcher, cutoff: str) -> List[str]:
    """Problems that would let post-T material into history, or make the distractor his; empty when clean."""
    identity = timesplit.load_identity(researcher)
    banned = re.compile("|".join(map(re.escape, identity["banned"])), re.IGNORECASE)
    own = own_urls(researcher)
    problems = []
    for r in pairs:
        pid = r.get("pair_id")
        if r.get("split") != "heldout" or str(r.get("date", "")) < cutoff:
            problems.append(f"{pid}: not a held-out pair dated on or after {cutoff}")
        if r.get("cutoff") != cutoff:
            problems.append(f"{pid}: cutoff {r.get('cutoff')} differs from {cutoff}")
        if str(r.get("distractor_date", "")) < cutoff:
            problems.append(f"{pid}: distractor dated before {cutoff}")
        if any(_is_him(a, identity["name"]) or banned.search(a) for a in r.get("distractor_authors") or []):
            problems.append(f"{pid}: the distractor's author is the researcher")
        if not r.get("distractor_authors"):
            problems.append(f"{pid}: distractor has no verified authors")
        if canonical_url(r.get("distractor_url", "")) in own:
            problems.append(f"{pid}: the distractor is one of his own documents")
    return problems


def build_real_pairs(researcher: Researcher, cutoff: str, client, llm, band: dict, seed: int = 0,
                     arxiv_meta: Optional[Callable] = None, num_results: int = 10,
                     today: Optional[str] = None) -> Tuple[List[dict], List[dict], dict]:
    """(pairs, match rows for audit, report). Raises if any pair fails check_leakage."""
    if arxiv_meta is None:
        from .scrape import fetch_arxiv_meta as arxiv_meta
    projects = heldout_projects(researcher, cutoff)
    candidates, dropped = collect_candidates(projects, researcher, client, cutoff, arxiv_meta, num_results, today)
    matched = match(projects, candidates, (band["lo"], band["hi"]))
    docs = timesplit._corpus_meta(researcher.root)
    banned = timesplit.banned_pattern(researcher)
    pairs, audit, failed = [], [], 0
    for p in projects:
        cand = matched.get(p["doc"])
        row = {"doc": p["doc"], "title": p["title"], "date": p["date"], "n_candidates": len(candidates.get(p["doc"], [])),
               "distractor": cand, "status": "no_candidate_in_band" if cand is None else "matched"}
        if cand is not None:
            pair, problems = render_real_pair(researcher, p, cand, llm, cutoff, band, seed, docs, banned)
            if pair is None:
                failed += 1
                row.update(status="render_failed", problems=problems)
            else:
                pairs.append(pair)
                row["pair_id"] = pair["pair_id"]
        audit.append(row)
    problems = check_leakage(pairs, researcher, cutoff)
    if problems:
        raise ValueError("leakage check failed: " + "; ".join(problems))
    report = {"researcher": researcher.slug, "cutoff": cutoff, "heldout_projects": len(projects),
              "candidates_verified": sum(map(len, candidates.values())), "dropped": dropped,
              "matched": len(matched), "no_candidate_in_band": len(projects) - len(matched),
              "render_failed": failed, "pairs": len(pairs), "band": band}
    return pairs, audit, report


# ---- Choice rows and the real-vs-LLM comparison --------------------------------------

def to_choices(pairs: List[dict], researcher: Researcher) -> List[Choice]:
    """Held-out Choice rows exactly as timesplit.write_choice_files makes them (anonymous user,
    hashed source URL as group, no reason that names him)."""
    banned = timesplit.banned_pattern(researcher)
    return [Choice(user_id=timesplit.ANON_USER, context=p["context"], a_text=p["a_text"], b_text=p["b_text"],
                   chosen=p["chosen"], decision_point=p["decision_point"],
                   reason="" if banned.search(p["reason"]) else p["reason"], timestamp=p["date"],
                   source="timesplit", example_id=p["pair_id"], group_id=digest([p["url"]])[:12])
            for p in pairs]


def write_choices(path: str, choices: List[Choice]) -> None:
    timesplit._write_jsonl(path, [asdict(c) for c in choices])


def _group_means(by_group: Dict[str, Dict[str, bool]]) -> Dict[str, float]:
    return {g: sum(v.values()) / len(v) for g, v in by_group.items() if v}


def compare_accuracy(model, llm_heldout: List[Choice], real_heldout: List[Choice], seed: int = 0,
                     n_boot: int = 2000) -> dict:
    """The same fitted user model scored (both a/b orders, track_eval.paired_correct) on the
    LLM-distractor and the real-distractor held-out pairs. `matched` compares the two on the source
    documents present in both, as a per-document accuracy difference with a document-resampled 90%
    interval; the two sets differ in granularity (a decision vs a whole project), so `matched` is the
    fairer contrast."""
    from .track_eval import cluster_ci, score
    out = {}
    scored = {}
    for name, choices in (("llm", llm_heldout), ("real", real_heldout)):
        if not choices:
            out[name] = {"n_pairs": 0, "accuracy": None, "ci90": None}
            continue
        scored[name] = score(model, choices)
        acc, lo, hi = cluster_ci({g: list(v.values()) for g, v in scored[name].items()})
        out[name] = {"n_pairs": len(choices), "n_docs": len(scored[name]), "accuracy": acc, "ci90": [lo, hi]}
    if len(scored) == 2:
        a, b = _group_means(scored["real"]), _group_means(scored["llm"])
        common = sorted(set(a) & set(b))
        if common:
            diffs = [a[g] - b[g] for g in common]
            rng = random.Random(seed)
            boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n_boot))
            out["matched"] = {"n_docs": len(common), "real": sum(a[g] for g in common) / len(common),
                              "llm": sum(b[g] for g in common) / len(common),
                              "real_minus_llm": sum(diffs) / len(diffs),
                              "ci90": [boots[int(0.05 * n_boot)], boots[min(n_boot - 1, int(0.95 * n_boot))]]}
        else:
            out["matched"] = {"n_docs": 0}
    return out


def compare(researcher: Researcher, real_pairs: List[dict], llm, method: str, cache_dir: Optional[str] = None) -> dict:
    """Fit `method` on his history pairs (before T, unchanged by this module) and compare_accuracy."""
    from .track_eval import _fit, load_choices
    history = load_choices(os.path.join(researcher.root, timesplit.HISTORY))
    llm_heldout = load_choices(os.path.join(researcher.root, timesplit.HELDOUT))
    cutoffs = {p["cutoff"] for p in real_pairs} | {p["cutoff"] for p in timesplit._read_jsonl(
        os.path.join(researcher.root, timesplit.PAIRS))}
    if len(cutoffs) > 1:
        raise ValueError(f"real and LLM pairs carry different cutoffs {sorted(cutoffs)}")
    model = _fit(method, llm, history, cache_dir)
    report = compare_accuracy(model, llm_heldout, to_choices(real_pairs, researcher))
    return dict(report, researcher=researcher.slug, method=method, n_history=len(history),
                cutoff=cutoffs.pop() if cutoffs else None)


# ---- CLI --------------------------------------------------------------------------

def _researcher(path: str) -> Researcher:
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise SystemExit(f"{path} is not a researcher directory")
    return Researcher(os.path.basename(path.rstrip(os.sep)), path)


def _dump(path: str, obj) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "band":
        p = argparse.ArgumentParser(prog="real_distractors band",
                                    description="set the similarity band on a dev researcher's pre-T documents")
        p.add_argument("--researcher", required=True, help="a dev researcher's directory")
        p.add_argument("--cutoff", required=True)
        p.add_argument("--out", required=True)
        a = p.parse_args(argv[1:])
        band = fit_band(_researcher(a.researcher), a.cutoff)
        _dump(a.out, band)
        print(json.dumps(band))
        return
    if argv and argv[0] == "compare":
        p = argparse.ArgumentParser(prog="real_distractors compare",
                                    description="user-model accuracy on real vs LLM-made distractors")
        p.add_argument("--researcher", required=True)
        p.add_argument("--pairs", required=True, help="real-distractor pairs from this module")
        p.add_argument("--method", default="m1")
        p.add_argument("--llm", default="claude-cli")
        p.add_argument("--model", default="claude-sonnet-5-5")
        p.add_argument("--max-usd", type=float, required=True)
        p.add_argument("--out", help="default: <pairs>.compare.json")
        a = p.parse_args(argv[1:])
        from ..llm import Budget, get_llm
        from .track_eval import CACHE, JsonReply
        budget = Budget(max_cost_usd=a.max_usd, max_seconds=12 * 3600)
        report = compare(_researcher(a.researcher), timesplit._read_jsonl(a.pairs),
                         JsonReply(get_llm(a.llm, a.model, budget)), a.method, cache_dir=CACHE)
        report["llm_cost"] = round(budget.cost_usd, 4)
        _dump(a.out or a.pairs + ".compare.json", report)
        print(json.dumps(report, indent=2))
        return
    p = argparse.ArgumentParser(description="time-split pairs with real distractors from Exa (see module doc)")
    p.add_argument("--researcher", required=True, help="the researcher's directory (corpus/, identity.json)")
    p.add_argument("--cutoff", required=True, help="YYYY-MM-DD; his work from this date on is held out")
    p.add_argument("--out", required=True, help="pairs JSONL, in timesplit's pair format")
    p.add_argument("--band", help="band JSON from `band` on a dev researcher (default: untuned DEFAULT_BAND)")
    p.add_argument("--lo", type=float)
    p.add_argument("--hi", type=float)
    p.add_argument("--num-results", type=int, default=10, help="Exa results per held-out project")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--llm", default="claude-cli", help="the pair rewriter (timesplit.render_pair)")
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--max-usd", type=float, required=True)
    a = p.parse_args(argv)
    researcher = _researcher(a.researcher)
    band = load_band(a.band, a.lo, a.hi)
    if os.path.exists(a.out):
        raise SystemExit(f"{a.out} exists; held-out pairs must not shift under a rerun, so delete it to rebuild")
    from ..integrations.exa import ExaClient
    from ..llm import Budget, get_llm
    client = ExaClient(cache_dir=timesplit.EXA_CACHE)
    budget = Budget(max_cost_usd=a.max_usd, max_seconds=6 * 3600)
    pairs, audit, report = build_real_pairs(researcher, a.cutoff, client, get_llm(a.llm, a.model, budget), band,
                                            seed=a.seed, num_results=a.num_results,
                                            today=datetime.date.today().isoformat())
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    timesplit._write_jsonl(a.out, pairs)
    timesplit._write_jsonl(a.out + ".matches.jsonl", audit)
    write_choices(a.out + ".heldout_choices.jsonl", to_choices(pairs, researcher))
    print(json.dumps(dict(report, exa_cost=round(client.cost, 4), llm_cost=round(budget.cost_usd, 4))))


if __name__ == "__main__":
    main()
