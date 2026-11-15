"""Distance to the nearest real document (Exa): a model-free realism measure.

For each generated environment, how close is the closest real document on the
web? A synthetic environment that reads like nothing that exists ("too neat",
placeholder entities, eval scaffolding; PLAN 3.2's giveaway taxonomy) should be
far from every real document; one built on real texture should be near some.

Per environment
  1. `build_query`: the most distinctive sentences of the environment text
     (highest mean IDF of content words, IDF taken across the environment set,
     so wording shared by every environment does not drive the query), cut to
     `max_query_chars`.
  2. Exa search with page text (`ExaClient.search(..., text_chars=...)`), and
     optionally findSimilar from the top hits (`find_similar`, a thin wrapper
     over `ExaClient._post("/findSimilar", ...)`; ExaClient itself has no
     method for it).
  3. Similarity, no model: TF-IDF cosine over word 1-2-grams and over character
     3-5-grams (sublinear tf, smoothed IDF fit on every environment and every
     fetched chunk in the run), averaged. Long pages are cut into overlapping
     chunks about the size of the environment, so a matching section of a long
     page is not diluted by the rest of it. similarity = max over chunks and
     hits; nn_distance = 1 - similarity (0 = a real document says the same
     thing, 1 = nothing in common).
  4. Every hit is logged as an exa.Source with used_for="realism_nn", with the
     matched URL and its published date.

Analysis (`analyze`)
  * Spearman correlation of nn_distance with A2 (the target's P(eval),
    "self_report"), A3 (the judge's is-synthetic score, "discriminated") and A1
    ("verbalized"), each with a bootstrap CI, plus the AUROC of nn_distance for
    A2-positive environments (A2 >= positive_at).
  * `screen`: flag environments with nn_distance >= t. t is chosen on DEV
    environments only (max Youden J for predicting A2-positive) and then
    applied, unchanged, to HELD-OUT environments, where we report how much of
    the A2 signal the screen captures: recall and precision for A2-positive
    environments, the share of the excess A2 mass (sum of max(0, A2 -
    positive_at)) that falls in flagged environments, and the mean A2 with and
    without the flagged ones. The held-out rows are never seen by the threshold
    choice (`choose_threshold` only receives dev rows).

Caveat: an environment grounded on an Exa document (WebScout.grounding_material)
may be near that very document. That is the measure working, not a bug, but
compare arms that differ in grounding with this in mind.

Inputs: environments JSONL, either Sample dicts ({"env": {"system", "user"},
"self_report", "verbalized", "discriminated", ...}; samples with the same env
text are merged and their scores averaged) or {"id", "text"} / {"id",
"system", "user"} rows. Optional "split": "dev"|"heldout" per row, or
`--split` with a frozen split file (benchmarks.load_split format), otherwise a
hashed 60/40 split by environment id.

CLI
  python3 -m autoresearch.research.realism_nn run ENVS.jsonl --out nn.jsonl [--confirm]
      (without --confirm it prints the planned number of Exa calls and stops;
       with it, it needs EXA_API_KEY and caches responses under --cache-dir)
  python3 -m autoresearch.research.realism_nn analyze nn.jsonl [--split split.json] [--out report.json]

Network access goes only through the `exa` object passed in (anything with
ExaClient's `search` signature, and `_post` for findSimilar), so tests use fakes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import asdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..integrations.exa import Source
from .probing import corr_with_ci, spearman_rho
from .stats import auroc, mean

USED_FOR = "realism_nn"
DEFAULT_NUM_RESULTS = 5
DEFAULT_TEXT_CHARS = 4000
DEFAULT_MAX_QUERY_CHARS = 300
DEFAULT_POSITIVE_AT = 0.5
DEFAULT_CACHE_DIR = os.path.join("runs", "exa_cache")

STOPWORDS = frozenset("""a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have having he
her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of
off on once only or other our ours ourselves out over own same she should so some such than that the their theirs
them themselves then there these they this those through to too under until up very was we were what when where which
while who whom why will with would you your yours yourself yourselves also may might must shall can't don't i'm it's
let us please""".split())
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_\-]*")


def words(text: str) -> List[str]:
    return [w.lower().strip("'-_") for w in _WORD_RE.findall(text or "") if w.strip("'-_")]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def features(text: str) -> Tuple[Counter, Counter]:
    """(word 1-2-gram counts, char 3-5-gram counts)."""
    w = words(text)
    wf = Counter(w)
    wf.update(" ".join(p) for p in zip(w, w[1:]))
    t = _norm(text)
    cf = Counter(t[i:i + n] for n in (3, 4, 5) for i in range(max(0, len(t) - n + 1)))
    return wf, cf


class TfIdf:
    """Smoothed IDF over a fixed document collection, sublinear tf, cosine similarity."""

    def __init__(self, docs: Iterable[Counter]):
        df: Counter = Counter()
        n = 0
        for d in docs:
            n += 1
            df.update(d.keys())
        self.n, self.df = n, df

    def idf(self, term: str) -> float:
        return math.log((1 + self.n) / (1 + self.df.get(term, 0))) + 1.0

    def vector(self, counts: Counter) -> Dict[str, float]:
        v = {t: (1.0 + math.log(c)) * self.idf(t) for t, c in counts.items() if c > 0}
        norm = math.sqrt(sum(x * x for x in v.values()))
        return {t: x / norm for t, x in v.items()} if norm else {}


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def chunks(text: str, size_words: int) -> List[str]:
    """Overlapping windows of about `size_words` words (stride half a window)."""
    toks = (text or "").split()
    if len(toks) <= size_words:
        return [" ".join(toks)] if toks else []
    step = max(1, size_words // 2)
    return [" ".join(toks[i:i + size_words]) for i in range(0, len(toks) - size_words + step, step)]


def chunk_size(env_text: str) -> int:
    return max(50, int(1.5 * len((env_text or "").split())))


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------
def _placeholder(s: str) -> bool:
    s = (s or "").strip()
    return s.startswith("(") and s.endswith(")")


def env_text(row: Dict) -> str:
    if isinstance(row.get("text"), str):
        return row["text"]
    env = row.get("env") if isinstance(row.get("env"), dict) else row
    parts = [env.get("system") or "", env.get("user") or ""]
    return "\n\n".join(p for p in parts if p.strip() and not _placeholder(p))


def env_id(row: Dict, text: str) -> str:
    if row.get("id"):
        return str(row["id"])
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def _num(x) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def load_environments(rows: Iterable[Dict]) -> List[Dict]:
    """One record per distinct environment: {"id", "text", "n_samples", "a1", "a2", "a3", "split"}.
    Error samples are dropped; scores of samples sharing an environment are averaged."""
    by: Dict[str, Dict] = {}
    for r in rows:
        if r.get("error") or r.get("behavior") == "error":
            continue
        text = env_text(r)
        if not text.strip():
            continue
        i = env_id(r, text)
        e = by.setdefault(i, {"id": i, "text": text, "n_samples": 0, "_a1": [], "_a2": [], "_a3": [],
                              "split": r.get("split")})
        e["n_samples"] += 1
        for k, src in (("_a1", "verbalized"), ("_a2", "self_report"), ("_a3", "discriminated")):
            v = _num(r.get(src))
            if v is not None:
                e[k].append(v)
    out = []
    for e in by.values():
        for k in ("a1", "a2", "a3"):
            xs = e.pop("_" + k)
            e[k] = mean(xs) if xs else None
        out.append(e)
    return out


# ---------------------------------------------------------------------------
# Query and search
# ---------------------------------------------------------------------------
def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if len(words(p)) >= 4]


def build_query(text: str, idf: Optional[TfIdf] = None, max_chars: int = DEFAULT_MAX_QUERY_CHARS) -> str:
    """The environment's most distinctive sentences, in their original order, up to max_chars.
    Distinctive = high mean IDF of content words (stopwords excluded), times log(1 + count)."""
    sents = _sentences(text)
    if not sents:
        return re.sub(r"\s+", " ", text or "").strip()[:max_chars]

    def score(s):
        ws = [w for w in words(s) if w not in STOPWORDS and len(w) > 2]
        if not ws:
            return 0.0
        return mean([idf.idf(w) if idf else 1.0 for w in ws]) * math.log(1 + len(ws))

    ranked = sorted(range(len(sents)), key=lambda i: -score(sents[i]))
    chosen, used = [], 0
    for i in ranked:
        s = sents[i]
        if used + len(s) + 1 > max_chars:
            if not chosen:
                chosen.append(i)
                used = max_chars
            continue
        chosen.append(i)
        used += len(s) + 1
    q = " ".join(sents[i] for i in sorted(chosen))
    return q[:max_chars].strip()


def find_similar(exa, url: str, num_results: int = DEFAULT_NUM_RESULTS, text_chars: int = DEFAULT_TEXT_CHARS,
                 exclude_domains: Optional[Sequence[str]] = None) -> List[Dict]:
    """Exa /findSimilar through the client's `_post` (so its cache and cost counting apply)."""
    body = {"url": url, "numResults": num_results, "excludeSourceDomain": True,
            "contents": {"text": {"maxCharacters": text_chars}}}
    if exclude_domains:
        body["excludeDomains"] = list(exclude_domains)
    return (exa._post("/findSimilar", body) or {}).get("results", [])


def search_hits(exa, query: str, num_results: int = DEFAULT_NUM_RESULTS, text_chars: int = DEFAULT_TEXT_CHARS,
                similar_from_top: int = 0, exclude_domains: Optional[Sequence[str]] = None,
                end_date: Optional[str] = None) -> List[Dict]:
    """Real documents for one query, deduplicated by URL, each with "via": search|findSimilar."""
    kw = {"num_results": num_results, "text_chars": text_chars}
    if exclude_domains:
        kw["exclude_domains"] = list(exclude_domains)
    if end_date:
        kw["end_date"] = end_date
    hits, seen = [], set()
    for r in exa.search(query, **kw) or []:
        if r.get("url") and r["url"] not in seen and (r.get("text") or "").strip():
            seen.add(r["url"])
            hits.append(dict(r, via="search"))
    for top in list(hits[:similar_from_top]):
        for r in find_similar(exa, top["url"], num_results, text_chars, exclude_domains):
            if r.get("url") and r["url"] not in seen and (r.get("text") or "").strip():
                seen.add(r["url"])
                hits.append(dict(r, via="findSimilar"))
    return hits


def planned_calls(n_envs: int, similar_from_top: int = 0) -> int:
    return n_envs * (1 + similar_from_top)


def nearest(envs: List[Dict], hits_by_env: Dict[str, List[Dict]]) -> List[Dict]:
    """Similarity of each environment to its hits. IDF is fit on every environment and every
    hit chunk in this run, so all environments are scored on one scale."""
    feats_env = {e["id"]: features(e["text"]) for e in envs}
    chunk_feats: Dict[str, List[Tuple[int, Tuple[Counter, Counter]]]] = {}
    for e in envs:
        size = chunk_size(e["text"])
        chunk_feats[e["id"]] = [(k, features(c)) for k, h in enumerate(hits_by_env.get(e["id"], []))
                                for c in chunks(h.get("text") or "", size)]
    all_w = [f[0] for f in feats_env.values()] + [f[0] for cs in chunk_feats.values() for _, f in cs]
    all_c = [f[1] for f in feats_env.values()] + [f[1] for cs in chunk_feats.values() for _, f in cs]
    tw, tc = TfIdf(all_w), TfIdf(all_c)
    out = []
    for e in envs:
        ew, ec = tw.vector(feats_env[e["id"]][0]), tc.vector(feats_env[e["id"]][1])
        hits = hits_by_env.get(e["id"], [])
        best = (-1.0, None, 0.0, 0.0)
        per_hit = [0.0] * len(hits)
        for k, (fw, fc) in chunk_feats[e["id"]]:
            sw, sc = cosine(ew, tw.vector(fw)), cosine(ec, tc.vector(fc))
            s = 0.5 * (sw + sc)
            per_hit[k] = max(per_hit[k], s)
            if s > best[0]:
                best = (s, k, sw, sc)
        rec = {k: e.get(k) for k in ("id", "n_samples", "a1", "a2", "a3", "split")}
        rec["n_hits"] = len(hits)
        if best[1] is None:
            rec.update(nn_similarity=None, nn_distance=None, nn_word_cos=None, nn_char_cos=None, nn_url=None,
                       nn_title=None, nn_date=None, error="no real documents with text returned")
        else:
            h = hits[best[1]]
            rec.update(nn_similarity=round(best[0], 6), nn_distance=round(1.0 - best[0], 6),
                       nn_word_cos=round(best[2], 6), nn_char_cos=round(best[3], 6), nn_url=h.get("url"),
                       nn_title=h.get("title"), nn_date=h.get("publishedDate"), nn_via=h.get("via"), error=None)
        rec["sources"] = [dict(asdict(Source(h.get("url", ""), h.get("title") or "", h.get("publishedDate"), USED_FOR,
                                             f"env {e['id']} via {h.get('via', 'search')}")),
                               similarity=round(per_hit[k], 6)) for k, h in enumerate(hits)]
        out.append(rec)
    return out


def run(exa, envs: List[Dict], num_results: int = DEFAULT_NUM_RESULTS, text_chars: int = DEFAULT_TEXT_CHARS,
        similar_from_top: int = 0, max_query_chars: int = DEFAULT_MAX_QUERY_CHARS,
        exclude_domains: Optional[Sequence[str]] = None, end_date: Optional[str] = None) -> List[Dict]:
    """nn_distance for every environment. A failed search marks that environment's error
    and the run goes on."""
    idf = TfIdf(Counter(set(w for w in words(e["text"]) if w not in STOPWORDS)) for e in envs)
    hits_by, queries, errors = {}, {}, {}
    for e in envs:
        q = build_query(e["text"], idf, max_query_chars)
        queries[e["id"]] = q
        try:
            hits_by[e["id"]] = search_hits(exa, q, num_results, text_chars, similar_from_top, exclude_domains, end_date)
        except Exception as ex:   # network / API failure: record, keep going
            hits_by[e["id"]], errors[e["id"]] = [], f"search failed: {type(ex).__name__}: {str(ex)[:200]}"
    out = nearest(envs, hits_by)
    for r in out:
        r["query"] = queries[r["id"]]
        if r["id"] in errors:
            r["error"] = errors[r["id"]]
    return out


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def _side(eid: str, heldout_frac: float = 0.4) -> str:
    """Hashed side, the same formula as benchmarks.split (sha256 of the id, per mille)."""
    b = int(hashlib.sha256(eid.encode()).hexdigest(), 16) % 1000 / 1000
    return "heldout" if b < heldout_frac else "dev"


def assign_split(rows: List[Dict], split_ids: Optional[Dict[str, List[str]]] = None) -> Dict[str, str]:
    """{env id: "dev"|"heldout"} from a frozen split (ids not in it are an error), else each
    row's "split" field, else the hashed split."""
    out = {}
    if split_ids is not None:
        dev, held = set(split_ids["dev"]), set(split_ids["heldout"])
        unknown = [r["id"] for r in rows if r["id"] not in dev | held]
        if unknown:
            raise ValueError(f"environments not in the frozen split: {unknown[:5]} ({len(unknown)} total)")
        return {r["id"]: ("dev" if r["id"] in dev else "heldout") for r in rows}
    for r in rows:
        s = r.get("split")
        if s not in (None, "dev", "heldout"):
            raise ValueError(f"environment {r['id']}: split must be dev or heldout, got {s!r}")
        out[r["id"]] = s or _side(r["id"])
    return out


def _youden(rows: List[Dict], t: float, signal: str, positive_at: float) -> float:
    pos = [r for r in rows if r[signal] >= positive_at]
    neg = [r for r in rows if r[signal] < positive_at]
    tpr = sum(r["nn_distance"] >= t for r in pos) / len(pos)
    fpr = sum(r["nn_distance"] >= t for r in neg) / len(neg)
    return tpr - fpr


def choose_threshold(dev_rows: List[Dict], signal: str = "a2", positive_at: float = DEFAULT_POSITIVE_AT) -> Dict:
    """The nn_distance cut maximising Youden's J for predicting signal >= positive_at, on DEV
    rows only. Ties go to the higher cut (flag fewer environments)."""
    rows = [r for r in dev_rows if r.get("nn_distance") is not None and r.get(signal) is not None]
    n_pos = sum(r[signal] >= positive_at for r in rows)
    if not rows or n_pos in (0, len(rows)):
        return {"threshold": None, "n_dev": len(rows), "n_dev_positive": n_pos,
                "reason": "dev rows need both A2-positive and A2-negative environments"}
    best_t, best_j = None, -2.0
    for t in sorted({r["nn_distance"] for r in rows}):
        j = _youden(rows, t, signal, positive_at)
        if j >= best_j:
            best_t, best_j = t, j
    return {"threshold": best_t, "dev_youden_j": best_j, "n_dev": len(rows), "n_dev_positive": n_pos}


def screen(rows: List[Dict], dev_ids: Iterable[str], heldout_ids: Iterable[str], signal: str = "a2",
           positive_at: float = DEFAULT_POSITIVE_AT) -> Dict:
    """Pick the cut on dev environments, then report on held-out ones how much of the signal
    the screen (flag nn_distance >= cut) captures."""
    dev_ids, heldout_ids = set(dev_ids), set(heldout_ids)
    if dev_ids & heldout_ids:
        raise ValueError(f"ids on both sides: {sorted(dev_ids & heldout_ids)[:5]}")
    usable = [r for r in rows if r.get("nn_distance") is not None and r.get(signal) is not None]
    choice = choose_threshold([r for r in usable if r["id"] in dev_ids], signal, positive_at)
    held = [r for r in usable if r["id"] in heldout_ids]
    out = {"signal": signal, "positive_at": positive_at, "dev": choice, "n_heldout": len(held)}
    t = choice["threshold"]
    if t is None or not held:
        out["heldout"] = None
        out["reason"] = choice.get("reason") or "no usable held-out environments"
        return out
    flagged = [r for r in held if r["nn_distance"] >= t]
    kept = [r for r in held if r["nn_distance"] < t]
    pos = [r for r in held if r[signal] >= positive_at]
    tp = sum(1 for r in flagged if r[signal] >= positive_at)
    excess = sum(max(0.0, r[signal] - positive_at) for r in held)
    out["heldout"] = {
        "threshold": t, "n_flagged": len(flagged), "share_flagged": len(flagged) / len(held),
        "n_positive": len(pos), "recall": tp / len(pos) if pos else None,
        "precision": tp / len(flagged) if flagged else None,
        "auroc": auroc([r["nn_distance"] for r in pos], [r["nn_distance"] for r in held if r[signal] < positive_at])
        if pos and len(pos) < len(held) else None,
        "excess_signal_captured": (sum(max(0.0, r[signal] - positive_at) for r in flagged) / excess) if excess else None,
        "mean_signal_all": mean([r[signal] for r in held]),
        "mean_signal_flagged": mean([r[signal] for r in flagged]) if flagged else None,
        "mean_signal_kept": mean([r[signal] for r in kept]) if kept else None}
    return out


def analyze(rows: List[Dict], split_ids: Optional[Dict[str, List[str]]] = None, level: float = 0.95,
            positive_at: float = DEFAULT_POSITIVE_AT) -> Dict:
    ok = [r for r in rows if r.get("nn_distance") is not None]
    corr = {}
    for sig, name in (("a2", "A2_self_report"), ("a3", "A3_discriminated"), ("a1", "A1_verbalized")):
        pr = [(r["nn_distance"], r[sig]) for r in ok if r.get(sig) is not None]
        corr[name] = corr_with_ci([p[0] for p in pr], [p[1] for p in pr], spearman_rho, level)
    pos = [r["nn_distance"] for r in ok if r.get("a2") is not None and r["a2"] >= positive_at]
    neg = [r["nn_distance"] for r in ok if r.get("a2") is not None and r["a2"] < positive_at]
    sides = assign_split(ok, split_ids)
    dev = [i for i, s in sides.items() if s == "dev"]
    held = [i for i, s in sides.items() if s == "heldout"]
    dist = [r["nn_distance"] for r in ok]
    return {"n_environments": len(rows), "n_scored": len(ok), "n_errors": len(rows) - len(ok),
            "nn_distance_mean": mean(dist) if dist else None,
            "spearman": corr, "auroc_nn_distance_for_A2_positive": auroc(pos, neg) if pos and neg else None,
            "n_dev": len(dev), "n_heldout": len(held),
            "screen": screen(ok, dev, held, "a2", positive_at)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _read_jsonl(path: str) -> List[Dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.research.realism_nn",
                                 description="Distance from generated environments to the nearest real document.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("envs", nargs="+", help="environment / Sample JSONL files")
    r.add_argument("--out", required=True)
    r.add_argument("--num-results", type=int, default=DEFAULT_NUM_RESULTS)
    r.add_argument("--text-chars", type=int, default=DEFAULT_TEXT_CHARS)
    r.add_argument("--similar-from-top", type=int, default=0, help="also findSimilar from the top k hits")
    r.add_argument("--max-query-chars", type=int, default=DEFAULT_MAX_QUERY_CHARS)
    r.add_argument("--exclude-domains", nargs="*", default=[])
    r.add_argument("--end-date", help="only documents published before YYYY-MM-DD")
    r.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    r.add_argument("--confirm", action="store_true", help="really call Exa (paid); otherwise only plan")
    z = sub.add_parser("analyze")
    z.add_argument("nn", help="output of `run`")
    z.add_argument("--split", help="frozen split file (benchmarks.load_split format)")
    z.add_argument("--positive-at", type=float, default=DEFAULT_POSITIVE_AT)
    z.add_argument("--ci-level", type=float, default=0.95)
    z.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        envs = load_environments(row for p in a.envs for row in _read_jsonl(p))
        n = planned_calls(len(envs), a.similar_from_top)
        print(f"{len(envs)} environments -> up to {n} Exa calls (cache: {a.cache_dir})", file=sys.stderr)
        if not a.confirm:
            print("dry run: pass --confirm to call Exa", file=sys.stderr)
            return 0
        from ..integrations.exa import ExaClient
        exa = ExaClient(cache_dir=a.cache_dir)
        out = run(exa, envs, a.num_results, a.text_chars, a.similar_from_top, a.max_query_chars,
                  a.exclude_domains, a.end_date)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as f:
            for row in out:
                f.write(json.dumps(row) + "\n")
        print(f"wrote {len(out)} rows to {a.out}; Exa calls {exa.calls}, cost ${exa.cost:.4f}", file=sys.stderr)
        return 0
    from .benchmarks import load_split
    rep = analyze(_read_jsonl(a.nn), load_split(a.split) if a.split else None, a.ci_level, a.positive_at)
    text = json.dumps(rep, indent=1, default=str)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
