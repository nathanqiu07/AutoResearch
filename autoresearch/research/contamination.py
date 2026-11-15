"""Benchmark contamination: are our benchmark items on the web?

A target that has seen a benchmark item during training may recognise it as a
test from memory rather than from its cues. This module checks every
benchmark item (EvalAwareBench items via benchmarks.load_items_with_meta,
Petri seeds as {"seed_id", "text"} JSONL) against Exa and labels it
exact / near / none with the evidence URL, then compares detection rates of
contaminated and clean items.

Per item
  1. `distinctive_spans`: the longest runs of words whose 8-grams occur in no
     other item of the set (so shared template text, e.g. EvalAwareBench's
     scaffolding, never becomes a query), ranked by length x mean IDF of their
     content words, cut to `max_span_words` around the rarest part. The top
     `n_spans` become quoted, phrase-ish Exa queries.
  2. Exa search with page text for each span; hits are merged by URL.
  3. Overlap of the item with each page, on lowercased word tokens:
       ng13 = share of the item's 13-grams found in the page (None if < 13 words)
       ng8  = share of the item's 8-grams found in the page
       lcs  = longest common word substring / item length (difflib, no autojunk)
     The evidence page is the hit with the highest (ng13, lcs, ng8).
  4. Label (thresholds configurable, DEFAULT_LABEL_RULES):
       exact  ng13 >= 0.5 or lcs >= 0.5
       near   any shared 13-gram, or ng8 >= 0.1, or lcs >= 0.2
       none   otherwise (including items whose search found nothing)
     Each item also records the evidence URL, its published date, its domain,
     and whether the domain is a benchmark host (huggingface.co, github.com,
     arxiv.org, ...). Pass `end_date` (a model's training cutoff) to count only
     pages published before it.

Analysis (`analyze`)
  Detection per item comes from scored samples joined on item id (field
  `signal`: by default the first of aware / detected / self_report / p_eval /
  verbalized present; an item's samples are averaged and the item counts as
  detected when the mean >= 0.5), or from an item meta field. Then:
    * detection rate for contaminated (exact or near) vs clean items, a
      two-proportion z test and a bootstrap CI for the difference;
    * an adjusted comparison when a topic covariate is available: logistic
      regression detected ~ contaminated + topic dummies (Newton-Raphson with a
      small ridge penalty, Wald CI for the odds ratio), and the Mantel-Haenszel
      odds ratio across topic strata;
    * the per-item covariate table (`covariates`), joinable on item id:
      {"id", "benchmark", "topic", "contamination", "contaminated", "ng13", "ng8",
       "lcs", "evidence_url", "evidence_date", "evidence_domain", "benchmark_host"}.
  Topic is the item meta "topic" if present, else its EvalAwareBench "label"
  (safety | capability) when every item has one, else the first corpus.topic_tags tag.

CLI
  python3 -m autoresearch.research.contamination run ITEMS.jsonl --out contam.jsonl [--confirm]
      (without --confirm it prints the planned number of Exa calls and stops)
  python3 -m autoresearch.research.contamination analyze contam.jsonl --scores SAMPLES.jsonl
      [--signal self_report] [--covariates covariates.jsonl] [--out report.json]

Network access goes only through the `exa` object passed in, so tests use fakes.
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import random
import re
import sys
import urllib.parse
from collections import Counter
from dataclasses import asdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..integrations.exa import Source
from .corpus import topic_tags
from .realism_nn import STOPWORDS, words
from .stats import mean

USED_FOR = "contamination"
DEFAULT_N_SPANS = 3
DEFAULT_MAX_SPAN_WORDS = 20
DEFAULT_MIN_SPAN_WORDS = 8
DEFAULT_NUM_RESULTS = 5
DEFAULT_TEXT_CHARS = 20000
DEFAULT_LABEL_RULES = {"exact_ng13": 0.5, "exact_lcs": 0.5, "near_ng8": 0.1, "near_lcs": 0.2, "near_any_ng13": True}
DEFAULT_CACHE_DIR = os.path.join("runs", "exa_cache")
BENCHMARK_HOSTS = ("huggingface.co", "github.com", "githubusercontent.com", "arxiv.org", "paperswithcode.com",
                   "kaggle.com", "openreview.net")
SIGNAL_FIELDS = ("aware", "detected", "self_report", "p_eval", "verbalized")
ID_FIELDS = ("id", "item_id", "source_id", "seed_id")


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------
def load_benchmark_items(path: str, fmt: str = "auto") -> List[Dict]:
    """Items as {"id", "benchmark", "text", "meta"}. fmt: petri (AuditSeed rows), items
    (benchmarks.load_items_with_meta format), or auto (petri if the first row has seed_id
    and text)."""
    with open(path) as f:
        first = next((json.loads(l) for l in f if l.strip()), None)
    if first is None:
        raise ValueError(f"{path}: no items")
    if fmt == "auto":
        fmt = "petri" if ("seed_id" in first and "text" in first) else "items"
    out = []
    if fmt == "petri":
        with open(path) as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                r = json.loads(line)
                if not r.get("seed_id") or not r.get("text"):
                    raise ValueError(f"{path}:{n}: a Petri seed needs seed_id and text")
                out.append({"id": str(r["seed_id"]), "benchmark": f"petri_{r.get('variant', 'v2')}",
                            "text": r["text"], "meta": {k: v for k, v in r.items() if k not in ("text",)}})
    elif fmt == "items":
        from .benchmarks import load_items_with_meta
        for sc, meta in load_items_with_meta(path):
            text = "\n\n".join(p for p in ((sc.original or {}).get("system", ""), (sc.original or {}).get("user", ""))
                               if p and p.strip())
            out.append({"id": sc.source_id, "benchmark": str(meta.get("dataset") or "items"), "text": text,
                        "meta": meta})
    else:
        raise ValueError(f"unknown format {fmt!r} (auto | petri | items)")
    ids = [i["id"] for i in out]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path}: duplicate item ids")
    return out


def item_topics(items: List[Dict]) -> Dict[str, str]:
    """One topic per item: meta "topic", else meta "label" if every item has one, else the
    first corpus.topic_tags tag of the text."""
    if all(isinstance(i["meta"].get("topic"), str) for i in items):
        return {i["id"]: i["meta"]["topic"] for i in items}
    if all(isinstance(i["meta"].get("label"), str) for i in items):
        return {i["id"]: i["meta"]["label"] for i in items}
    return {i["id"]: topic_tags(i["text"])[0] for i in items}


# ---------------------------------------------------------------------------
# Spans
# ---------------------------------------------------------------------------
def ngrams(toks: Sequence[str], n: int) -> List[Tuple[str, ...]]:
    return [tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)]


def _surface_words(text: str) -> List[str]:
    """Whitespace words with the same count/order as `words` would give on their own."""
    return [w for w in re.findall(r"\S+", text or "") if words(w)]


def distinctive_spans(items: List[Dict], n_spans: int = DEFAULT_N_SPANS, min_words: int = DEFAULT_MIN_SPAN_WORDS,
                      max_words: int = DEFAULT_MAX_SPAN_WORDS) -> Dict[str, List[str]]:
    """{item id: up to n_spans query spans (original wording)}. A span is a maximal run of
    words whose `min_words`-grams appear in no other item; ranked by length x mean IDF."""
    surf = {i["id"]: _surface_words(i["text"]) for i in items}
    toks = {k: [words(w)[0] if len(words(w)) == 1 else " ".join(words(w)) for w in v] for k, v in surf.items()}
    gram_df: Counter = Counter()
    word_df: Counter = Counter()
    for t in toks.values():
        gram_df.update(set(ngrams(t, min_words)))
        word_df.update(set(t))
    n_items = max(1, len(items))

    def idf(w):
        return 0.0 if w in STOPWORDS else math.log((1 + n_items) / (1 + word_df[w])) + 1.0

    out = {}
    for iid, t in toks.items():
        unique = [gram_df[g] == 1 for g in ngrams(t, min_words)]
        runs, start = [], None
        for k, u in enumerate(unique + [False]):
            if u and start is None:
                start = k
            elif not u and start is not None:
                runs.append((start, k - 1 + min_words))     # word span [start, end)
                start = None
        cands = []
        for s, e in runs:
            if e - s > max_words:   # keep the rarest max_words window inside the run
                s = max(range(s, e - max_words + 1), key=lambda j: sum(idf(w) for w in t[j:j + max_words]))
                e = s + max_words
            content = [idf(w) for w in t[s:e] if w not in STOPWORDS]
            score = (e - s) * (mean(content) if content else 0.0)
            cands.append((score, s, e))
        cands.sort(key=lambda c: (-c[0], c[1]))
        if not cands and t:   # shorter than min_words, or fully shared: query the item's own opening words
            cands = [(0.0, 0, min(len(t), max_words))]
        out[iid] = [" ".join(surf[iid][s:e]) for _, s, e in cands[:n_spans]]
    return out


def span_query(span: str) -> str:
    clean = re.sub(r"\s+", " ", span.replace('"', "")).strip()
    return f'"{clean}"'


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------
def overlap(item_text: str, page_text: str) -> Dict:
    a, b = words(item_text), words(page_text)
    out = {"item_words": len(a)}
    for n in (13, 8):
        ga = set(ngrams(a, n))
        if not ga:
            out[f"ng{n}"], out[f"ng{n}_count"] = None, 0
            continue
        hit = len(ga & set(ngrams(b, n)))
        out[f"ng{n}"], out[f"ng{n}_count"] = hit / len(ga), hit
    if a and b:
        m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
        out["lcs_words"], out["lcs"] = m.size, m.size / len(a)
    else:
        out["lcs_words"], out["lcs"] = 0, 0.0
    return out


def label(ov: Optional[Dict], rules: Optional[Dict] = None) -> str:
    r = dict(DEFAULT_LABEL_RULES, **(rules or {}))
    if not ov:
        return "none"
    ng13, ng8, lcs = ov.get("ng13") or 0.0, ov.get("ng8") or 0.0, ov.get("lcs") or 0.0
    if ng13 >= r["exact_ng13"] or lcs >= r["exact_lcs"]:
        return "exact"
    if (r["near_any_ng13"] and ov.get("ng13_count", 0) > 0) or ng8 >= r["near_ng8"] or lcs >= r["near_lcs"]:
        return "near"
    return "none"


def _domain(url: str) -> str:
    host = urllib.parse.urlparse(url or "").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _rank(ov: Dict) -> Tuple[float, float, float]:
    return (ov.get("ng13") or 0.0, ov.get("lcs") or 0.0, ov.get("ng8") or 0.0)


def check_item(exa, item: Dict, spans: List[str], num_results: int = DEFAULT_NUM_RESULTS,
               text_chars: int = DEFAULT_TEXT_CHARS, end_date: Optional[str] = None,
               exclude_domains: Optional[Sequence[str]] = None, search_type: str = "auto",
               rules: Optional[Dict] = None) -> Dict:
    kw = {"num_results": num_results, "text_chars": text_chars, "search_type": search_type}
    if end_date:
        kw["end_date"] = end_date
    if exclude_domains:
        kw["exclude_domains"] = list(exclude_domains)
    pages: Dict[str, Dict] = {}
    errors = []
    for sp in spans:
        try:
            for r in exa.search(span_query(sp), **kw) or []:
                u = r.get("url")
                if u and (r.get("text") or "").strip():
                    if u not in pages or len(r.get("text") or "") > len(pages[u].get("text") or ""):
                        pages[u] = dict(r, span=sp)
        except Exception as ex:   # network / API failure: record and keep going
            errors.append(f"{type(ex).__name__}: {str(ex)[:200]}")
    scored = [(overlap(item["text"], p.get("text") or ""), p) for p in pages.values()]
    best = max(scored, key=lambda x: _rank(x[0])) if scored else None
    ov, page = (best if best else (None, None))
    lab = label(ov, rules)
    dom = _domain(page.get("url")) if page else None
    return {"id": item["id"], "benchmark": item["benchmark"], "spans": spans, "n_pages": len(pages),
            "contamination": lab,
            "ng13": ov.get("ng13") if ov else None, "ng8": ov.get("ng8") if ov else None,
            "lcs": ov.get("lcs") if ov else None, "ng13_count": ov.get("ng13_count") if ov else 0,
            "evidence_url": page.get("url") if page and lab != "none" else None,
            "best_url": page.get("url") if page else None,
            "evidence_date": page.get("publishedDate") if page else None,
            "evidence_domain": dom, "benchmark_host": bool(dom and any(dom == h or dom.endswith("." + h)
                                                                      for h in BENCHMARK_HOSTS)),
            "sources": [asdict(Source(p.get("url", ""), p.get("title") or "", p.get("publishedDate"), USED_FOR,
                                      f"item {item['id']}: {label(o, rules)} ng13={o.get('ng13')} lcs={o.get('lcs'):.3f}"))
                        for o, p in scored],
            "error": "; ".join(errors) if errors and not pages else None}


def planned_calls(spans: Dict[str, List[str]]) -> int:
    return sum(len(v) for v in spans.values())


def run(exa, items: List[Dict], n_spans: int = DEFAULT_N_SPANS, max_span_words: int = DEFAULT_MAX_SPAN_WORDS,
        **kw) -> List[Dict]:
    spans = distinctive_spans(items, n_spans, max_words=max_span_words)
    topics = item_topics(items)
    out = []
    for it in items:
        r = check_item(exa, it, spans[it["id"]], **kw)
        r["topic"] = topics[it["id"]]
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def _normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def two_proportion(x1: int, n1: int, x2: int, n2: int) -> Dict:
    """Pooled two-proportion z test of p1 = p2 (two-sided)."""
    if not n1 or not n2:
        return {"p1": None, "p2": None, "diff": None, "z": None, "p_value": None}
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else None
    return {"p1": p1, "p2": p2, "diff": p1 - p2, "z": z, "p_value": _normal_two_sided_p(z) if z is not None else None}


def bootstrap_diff_ci(a: Sequence[float], b: Sequence[float], level: float = 0.95, n: int = 2000,
                      seed: int = 0) -> Tuple[Optional[float], Optional[float]]:
    if not a or not b:
        return (None, None)
    rng = random.Random(seed)
    ds = sorted(mean([rng.choice(a) for _ in a]) - mean([rng.choice(b) for _ in b]) for _ in range(n))
    return ds[int((1 - level) / 2 * n)], ds[min(n - 1, int((1 + level) / 2 * n))]


def _solve(A: List[List[float]], b: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            raise ValueError("singular matrix")
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def logistic(X: List[List[float]], y: List[float], ridge: float = 0.1, iters: int = 50) -> Dict:
    """Logistic regression by Newton-Raphson with an L2 penalty (not on the intercept,
    column 0). Returns coefficients and Wald standard errors from the penalised Hessian."""
    k = len(X[0])
    beta = [0.0] * k
    H = None
    for _ in range(iters):
        p = [1 / (1 + math.exp(-max(-30.0, min(30.0, sum(b * x for b, x in zip(beta, row)))))) for row in X]
        g = [sum((yi - pi) * row[j] for row, yi, pi in zip(X, y, p)) - (ridge * beta[j] if j else 0.0)
             for j in range(k)]
        H = [[sum(pi * (1 - pi) * row[i] * row[j] for row, pi in zip(X, p)) + (ridge if i == j and i else 0.0)
              for j in range(k)] for i in range(k)]
        step = _solve(H, g)
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < 1e-8:
            break
    se = []
    for j in range(k):
        e = [1.0 if i == j else 0.0 for i in range(k)]
        se.append(math.sqrt(max(0.0, _solve(H, e)[j])))
    return {"coef": beta, "se": se}


def mantel_haenszel(strata: Dict[str, List[Tuple[bool, bool]]]) -> Optional[float]:
    """Common odds ratio of detected given contaminated across strata of (contaminated, detected)."""
    num = den = 0.0
    for rows in strata.values():
        n = len(rows)
        if n < 2:
            continue
        a = sum(1 for c, d in rows if c and d)
        b = sum(1 for c, d in rows if c and not d)
        c_ = sum(1 for c, d in rows if not c and d)
        d_ = sum(1 for c, d in rows if not c and not d)
        num += a * d_ / n
        den += b * c_ / n
    return num / den if den else None


def detection_from_scores(scores: Iterable[Dict], signal: Optional[str] = None,
                          cut: float = 0.5) -> Tuple[Dict[str, bool], str]:
    """({item id: detected}, field used). An item's samples are averaged, detected iff mean >= cut."""
    vals: Dict[str, List[float]] = {}
    used = signal
    for s in scores:
        if s.get("error") or s.get("behavior") == "error":
            continue
        iid = next((str(s[k]) for k in ID_FIELDS if s.get(k) not in (None, "")), None)
        if iid is None and isinstance(s.get("env"), dict):
            iid = next((str(s["env"][k]) for k in ID_FIELDS if s["env"].get(k)), None)
        if iid is None:
            continue
        f = used or next((k for k in SIGNAL_FIELDS if k in s), None)
        if f is None or s.get(f) is None:
            continue
        used = f
        v = s[f]
        vals.setdefault(iid, []).append(float(v) if not isinstance(v, bool) else (1.0 if v else 0.0))
    return {i: mean(v) >= cut for i, v in vals.items()}, used or ""


def analyze(results: List[Dict], detected: Dict[str, bool], level: float = 0.95, ridge: float = 0.1) -> Dict:
    rows = [r for r in results if r["id"] in detected and not r.get("error")]
    cont = [r for r in rows if r["contamination"] in ("exact", "near")]
    clean = [r for r in rows if r["contamination"] == "none"]
    a = [1.0 if detected[r["id"]] else 0.0 for r in cont]
    b = [1.0 if detected[r["id"]] else 0.0 for r in clean]
    test = two_proportion(int(sum(a)), len(a), int(sum(b)), len(b))
    out = {"n_items": len(results), "n_with_detection": len(rows),
           "labels": dict(Counter(r["contamination"] for r in results)),
           "n_benchmark_host_evidence": sum(1 for r in results if r["contamination"] != "none" and r.get("benchmark_host")),
           "contaminated": {"n": len(a), "detection_rate": mean(a) if a else None},
           "clean": {"n": len(b), "detection_rate": mean(b) if b else None},
           "two_proportion": test, "diff_bootstrap_ci": list(bootstrap_diff_ci(a, b, level)), "ci_level": level}
    topics = sorted({str(r.get("topic")) for r in rows if r.get("topic") is not None})
    if len(topics) >= 2 and len(rows) == sum(1 for r in rows if r.get("topic") is not None) and a and b:
        ref = Counter(str(r["topic"]) for r in rows).most_common(1)[0][0]
        others = [t for t in topics if t != ref]
        X = [[1.0, 1.0 if r["contamination"] != "none" else 0.0] + [1.0 if str(r["topic"]) == t else 0.0 for t in others]
             for r in rows]
        y = [1.0 if detected[r["id"]] else 0.0 for r in rows]
        zq = _z_for(level)
        try:
            fit = logistic(X, y, ridge)
            c, se = fit["coef"][1], fit["se"][1]
            out["adjusted"] = {"model": f"logit(detected) ~ contaminated + topic (reference {ref!r}), ridge {ridge}",
                               "odds_ratio": math.exp(c), "or_ci": [math.exp(c - zq * se), math.exp(c + zq * se)],
                               "coef": c, "se": se, "topics": topics}
        except ValueError as e:
            out["adjusted"] = {"error": str(e)}
        strata: Dict[str, List[Tuple[bool, bool]]] = {}
        for r in rows:
            strata.setdefault(str(r["topic"]), []).append((r["contamination"] != "none", detected[r["id"]]))
        out["mantel_haenszel_or"] = mantel_haenszel(strata)
        out["by_topic"] = {t: {"n": len(v), "n_contaminated": sum(c for c, _ in v),
                               "detection_contaminated": mean([float(d) for c, d in v if c]) if any(c for c, _ in v) else None,
                               "detection_clean": mean([float(d) for c, d in v if not c]) if any(not c for c, _ in v) else None}
                           for t, v in sorted(strata.items())}
    else:
        out["adjusted"] = None
        out["adjusted_reason"] = "needs at least two topics and items in both groups"
    return out


def _z_for(level: float) -> float:
    """Two-sided normal quantile by bisection on erfc (stdlib has no inverse)."""
    lo, hi, target = 0.0, 10.0, 1 - level
    for _ in range(100):
        mid = (lo + hi) / 2
        if _normal_two_sided_p(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


COVARIATE_FIELDS = ("id", "benchmark", "topic", "contamination", "contaminated", "ng13", "ng8", "lcs",
                    "evidence_url", "evidence_date", "evidence_domain", "benchmark_host")


def covariates(results: List[Dict]) -> List[Dict]:
    """One row per item, joinable on item id."""
    return [{k: (r["contamination"] != "none" if k == "contaminated" else r.get(k)) for k in COVARIATE_FIELDS}
            for r in results]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _read_jsonl(path: str) -> List[Dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def _write_jsonl(rows: List[Dict], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.research.contamination",
                                 description="Are benchmark items on the web? (Exa)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("items", nargs="+", help="benchmark item JSONL files (EvalAwareBench items or Petri seeds)")
    r.add_argument("--format", default="auto", choices=("auto", "items", "petri"))
    r.add_argument("--out", required=True)
    r.add_argument("--n-spans", type=int, default=DEFAULT_N_SPANS)
    r.add_argument("--max-span-words", type=int, default=DEFAULT_MAX_SPAN_WORDS)
    r.add_argument("--num-results", type=int, default=DEFAULT_NUM_RESULTS)
    r.add_argument("--text-chars", type=int, default=DEFAULT_TEXT_CHARS)
    r.add_argument("--end-date", help="only pages published before YYYY-MM-DD (e.g. a training cutoff)")
    r.add_argument("--exclude-domains", nargs="*", default=[])
    r.add_argument("--search-type", default="auto")
    r.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    r.add_argument("--covariates", help="also write the per-item covariate table here")
    r.add_argument("--confirm", action="store_true", help="really call Exa (paid); otherwise only plan")
    z = sub.add_parser("analyze")
    z.add_argument("results", help="output of `run`")
    z.add_argument("--scores", nargs="*", default=[], help="scored samples with an item id field")
    z.add_argument("--signal", help=f"score field (default: first of {', '.join(SIGNAL_FIELDS)})")
    z.add_argument("--cut", type=float, default=0.5)
    z.add_argument("--items", help="item JSONL, to read detection from a meta field instead (--meta-field)")
    z.add_argument("--meta-field")
    z.add_argument("--ci-level", type=float, default=0.95)
    z.add_argument("--covariates")
    z.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        items = [it for p in a.items for it in load_benchmark_items(p, a.format)]
        spans = distinctive_spans(items, a.n_spans, max_words=a.max_span_words)
        print(f"{len(items)} items -> {planned_calls(spans)} Exa searches (cache: {a.cache_dir})", file=sys.stderr)
        if not a.confirm:
            print("dry run: pass --confirm to call Exa", file=sys.stderr)
            return 0
        from ..integrations.exa import ExaClient
        exa = ExaClient(cache_dir=a.cache_dir)
        out = run(exa, items, a.n_spans, a.max_span_words, num_results=a.num_results, text_chars=a.text_chars,
                  end_date=a.end_date, exclude_domains=a.exclude_domains, search_type=a.search_type)
        _write_jsonl(out, a.out)
        if a.covariates:
            _write_jsonl(covariates(out), a.covariates)
        print(f"wrote {len(out)} rows to {a.out}; Exa calls {exa.calls}, cost ${exa.cost:.4f}", file=sys.stderr)
        return 0
    results = _read_jsonl(a.results)
    if a.meta_field:
        if not a.items:
            ap.error("--meta-field needs --items")
        items = load_benchmark_items(a.items)
        detected = {i["id"]: bool(i["meta"].get(a.meta_field)) for i in items if a.meta_field in i["meta"]}
        used = f"meta.{a.meta_field}"
    else:
        if not a.scores:
            ap.error("analyze needs --scores (or --items with --meta-field)")
        detected, used = detection_from_scores((s for p in a.scores for s in _read_jsonl(p)), a.signal, a.cut)
    rep = analyze(results, detected, a.ci_level)
    rep["detection_signal"] = used
    if a.covariates:
        _write_jsonl(covariates(results), a.covariates)
    text = json.dumps(rep, indent=1, default=str)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
