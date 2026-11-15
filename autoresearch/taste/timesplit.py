"""Track S time split (PLAN 12.2): a researcher's dated public work becomes binary
preference pairs, split at a cutoff T so held-out pairs test prediction, not recall.
How each stage works, with real counts: docs/track-s-extraction.md.

Corpus files carry their date in front matter (written by scrape.scrape_exa):

    ---
    url: https://arxiv.org/abs/2505.23836
    publishedDate: 2025-05-28
    ---
    <text>

A file without a date is left out: it could have been written after T.

Stages, each reading only earlier stages' files, each resumable:
  harvest   Exa finds, checks and dates his work            corpus/*.txt, harvest_manifest.jsonl
  extract   Exa structured summary of each doc's decisions  extraction/exa.jsonl
  check     Claude keeps/corrects/drops each, adds missed;  extraction/decisions.jsonl, rejected.jsonl
            code verifies every quote
  distract  one alternative per decision                    extraction/distractors.jsonl
  pairs     neutral context + two options, split at T       pairs_timesplit.jsonl,
                                                            history_timesplit.jsonl, heldout_timesplit.jsonl
  review    optional human check of held-out distractors    review_timesplit.jsonl

    python3 -m autoresearch.taste.timesplit harvest --researcher <slug> --name "<Full Name>" --start YYYY-MM-DD --end YYYY-MM-DD [--lesswrong <slug>] [--feed <rss url>]
    python3 -m autoresearch.taste.timesplit extract --researcher <slug>
    python3 -m autoresearch.taste.timesplit check --researcher <slug> --max-usd 60
    python3 -m autoresearch.taste.timesplit distract --researcher <slug> --cutoff YYYY-MM-DD --max-usd 20
    python3 -m autoresearch.taste.timesplit pairs --researcher <slug> --cutoff YYYY-MM-DD --max-usd 20
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import random
import re
import unicodedata
from dataclasses import asdict
from typing import Callable, List, Optional, Tuple

from ..llm import LLM, extract_json
from .extract import profile_from_texts
from .profile import TasteProfile
from .researcher import DEFAULT_ROOT, Researcher, load_researcher
from .scrape import canonical_url
from .usermodel import Choice, digest

PAIRS, REVIEW = "pairs_timesplit.jsonl", "review_timesplit.jsonl"
HISTORY, HELDOUT = "history_timesplit.jsonl", "heldout_timesplit.jsonl"


FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

EXA_EXTRACT = os.path.join("extraction", "exa.jsonl")
DECISIONS = os.path.join("extraction", "decisions.jsonl")
REJECTED = os.path.join("extraction", "rejected.jsonl")
CHECKED = os.path.join("extraction", "checked.jsonl")
DISTRACTORS = os.path.join("extraction", "distractors.jsonl")
_DECISION = {"type": "object", "properties": {
    "point": {"type": "string", "enum": ["D1", "D2", "D3", "D4", "D5", "D6"]},
    "problem": {"type": "string"}, "did": {"type": "string"},
    "alternatives_named": {"type": "array", "items": {"type": "string"}},
    "stated_reason": {"type": "string"}, "quote": {"type": "string"}}}
DECISION_SCHEMA = {"type": "object", "properties": {
    "decisions": {"type": "array", "items": _DECISION},
    "future_work": {"type": "array", "items": {"type": "object", "properties": {
        "idea": {"type": "string"}, "quote": {"type": "string"}}}}}}
SUMMARY_QUERY = (
    "List every research decision the authors of this document made and say why. Label each with "
    "one point: D1 which experiment or hypothesis to pursue; D2 what evidence to collect (for "
    "example asking the model directly vs using probes); D3 whether to accept a result; D4 whether "
    "to continue or drop a line of work; D5 how to interpret an ambiguous result; D6 how strongly to "
    "state a claim. For each give the problem faced, what they did, any alternatives the text names, "
    "the reason the text states, and a verbatim quote of 20-300 characters from the document that "
    "shows the decision. Also list each idea named as future or follow-up work, with a verbatim quote.")


def read_doc(path: str) -> Tuple[Optional[datetime.date], str]:
    """(published date or None, body without front matter)."""
    with open(path) as f:
        raw = f.read()
    m = FRONT_MATTER.match(raw)
    if not m:
        return None, raw
    date = None
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "publishedDate" and value.strip():
            date = datetime.date.fromisoformat(value.strip()[:10])
    return date, raw[m.end():]


def front_matter(path: str) -> dict:
    with open(path) as f:
        m = FRONT_MATTER.match(f.read())
    return dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line) if m else {}


def dated_docs(researcher: Researcher) -> List[Tuple[datetime.date, str, str, str]]:
    """(date, kind, file name, text) for every dated corpus document, oldest first."""
    out = []
    for p in sorted(glob.glob(os.path.join(researcher.root, "corpus", "*.txt"))):
        date, text = read_doc(p)
        if date is not None:
            name = os.path.basename(p)
            out.append((date, "other" if name.startswith("other__") else "research", name, text))
    return sorted(out)


def docs_before(researcher: Researcher, cutoff: str) -> List[Tuple[str, str]]:
    """(kind, text) for every corpus document dated strictly before cutoff (YYYY-MM-DD)."""
    t = datetime.date.fromisoformat(cutoff)
    return [(kind, text) for date, kind, _, text in dated_docs(researcher) if date < t]


def profile_before(researcher: Researcher, cutoff: str, llm: LLM) -> TasteProfile:
    return profile_from_texts(researcher.slug, docs_before(researcher, cutoff), llm)


# ---- pairs -----------------------------------------------------------------

def _write_jsonl(path: str, rows: List[dict]) -> None:
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _read_jsonl(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


# ---- stage 2: Exa structured extraction -----------------------------------------

def exa_extract(researcher: Researcher, client, batch: int = 5) -> dict:
    """One row per corpus document in extraction/exa.jsonl with Exa's structured summary of its
    decisions. Rows are appended as they finish, and documents already there are skipped, so a
    crashed run resumes where it stopped."""
    path = os.path.join(researcher.root, EXA_EXTRACT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    done = {r["doc"] for r in _read_jsonl(path)}
    todo = []
    for p in sorted(glob.glob(os.path.join(researcher.root, "corpus", "*.txt"))):
        url = front_matter(p).get("url")
        if url and os.path.basename(p) not in done:
            todo.append((os.path.basename(p), url))
    report = {"done": 0, "skipped_existing": len(done), "errors": 0}
    summary = {"query": SUMMARY_QUERY, "schema": DECISION_SCHEMA}
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        by_url = {canonical_url(r.get("url", "")): r
                  for r in client.contents([u for _, u in chunk], text_chars=1, summary=summary)}
        with open(path, "a") as f:
            for doc, url in chunk:
                r = by_url.get(canonical_url(url), {})
                raw = r.get("summary")
                try:
                    out = json.loads(raw) if isinstance(raw, str) else raw
                    error = None if isinstance(out, dict) else "no summary returned"
                except json.JSONDecodeError:
                    out, error = None, "summary is not JSON"
                out = out if isinstance(out, dict) else {}
                report["errors"] += error is not None
                report["done"] += 1
                f.write(json.dumps({"doc": doc, "url": url, "decisions": out.get("decisions") or [],
                                    "future_work": out.get("future_work") or [], "exa_error": error,
                                    "request_id": r.get("id", "")}, ensure_ascii=False) + "\n")
    return report


# ---- stage 3: Claude check and fallback ------------------------------------------

CHECK_PROMPT_VERSION = "check-v1"
DECISIONS_MARK, EXCERPT_MARK = "\n\nDECISIONS (JSON):\n", "\n\nEXCERPT:\n"
CHECK_PROMPT = (
    "You check research decisions extracted from a document. Decision points: D1 which experiment "
    "or hypothesis to pursue; D2 what evidence to collect; D3 whether to accept a result; D4 whether "
    "to continue or drop a line of work; D5 how to interpret an ambiguous result; D6 how strongly to "
    "state a claim.\n"
    "Below are candidate decisions and an excerpt of the document. For each candidate whose quote "
    "appears in this excerpt, give a verdict: keep (correct as written), correct (real decision, but "
    "fix its fields), or drop (not a decision the authors made, or wrongly described). Say nothing "
    "about candidates whose quote is not in this excerpt. Then list decisions in this excerpt that "
    "the candidates missed. Every quote must be copied verbatim from the excerpt, 20-300 "
    "characters. Return JSON {\"verdicts\": [{\"index\": int, \"action\": \"keep\"|\"correct\"|"
    "\"drop\", \"decision\": {...only for correct...}}], \"missed\": [{\"point\", \"problem\", "
    "\"did\", \"alternatives_named\", \"stated_reason\", \"quote\"}]}.")
_FIELDS = ("point", "problem", "did", "alternatives_named", "stated_reason", "quote")
_QUOTES = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'"})


def normalize_for_quote(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    text = re.sub(r"-\s*\n\s*", "", text)
    return " ".join(text.split()).lower()


def quote_in_text(quote: str, text: str) -> bool:
    q = normalize_for_quote(quote)
    return len(q) >= 20 and q in normalize_for_quote(text)


def _check_doc(text: str, exa_decisions: List[dict], llm: LLM, chunk_chars: int, overlap: int):
    """(kept [(decision, tag)], rejected [(decision, reason)]) for one document."""
    pending = dict(enumerate(exa_decisions))
    kept, rejected, seen = [], [], set()

    def add(d, tag):
        d = {k: d.get(k) for k in _FIELDS}
        key = normalize_for_quote(str(d.get("quote") or ""))
        if key in seen:
            return
        seen.add(key)
        if quote_in_text(str(d.get("quote") or ""), text):
            kept.append((d, tag))
        else:
            rejected.append((d, "quote_not_found"))

    step = max(1, chunk_chars - overlap)
    for start in range(0, max(1, len(text) - overlap), step):
        excerpt = text[start:start + chunk_chars]
        shown = [dict(d, index=i) for i, d in pending.items()]
        out = extract_json(llm.complete(CHECK_PROMPT + DECISIONS_MARK + json.dumps(shown, ensure_ascii=False)
                                        + EXCERPT_MARK + excerpt, max_tokens=4000, temperature=0.0))
        out = out if isinstance(out, dict) else {}
        for v in out.get("verdicts") or []:
            i = v.get("index") if isinstance(v, dict) else None
            if i not in pending:
                continue
            d = pending.pop(i)
            if v.get("action") == "keep":
                add(d, "exa_verified")
            elif v.get("action") == "correct" and isinstance(v.get("decision"), dict):
                add(v["decision"], "exa_corrected")
            else:
                rejected.append((d, "claude_drop"))
        for d in out.get("missed") or []:
            if isinstance(d, dict):
                add(d, "claude_fallback")
    rejected += [(d, "unchecked") for d in pending.values()]
    return kept, rejected


def check_decisions(researcher: Researcher, llm: LLM, chunk_chars: int = 150_000, overlap: int = 2_000) -> dict:
    """Claude keeps, corrects or drops each Exa decision and adds the ones Exa missed; code then
    checks every quote against the document. Writes extraction/decisions.jsonl and rejected.jsonl;
    resumable per document."""
    root = researcher.root
    done = {r["doc"] for r in _read_jsonl(os.path.join(root, CHECKED))}
    report = {"docs": 0, "skipped_existing": len(done)}
    for row in _read_jsonl(os.path.join(root, EXA_EXTRACT)):
        if row["doc"] in done:
            continue
        date, text = read_doc(os.path.join(root, "corpus", row["doc"]))
        kept, rejected = _check_doc(text, row["decisions"] if not row.get("exa_error") else [],
                                    llm, chunk_chars, overlap)
        with open(os.path.join(root, DECISIONS), "a") as f:
            for d, tag in kept:
                f.write(json.dumps(dict(d, doc=row["doc"], url=row["url"], date=date.isoformat() if date else None,
                                        tag=tag, decision_id=digest([row["doc"], normalize_for_quote(d["quote"])])[:12]),
                                   ensure_ascii=False) + "\n")
                report[tag] = report.get(tag, 0) + 1
        with open(os.path.join(root, REJECTED), "a") as f:
            for d, reason in rejected:
                f.write(json.dumps({"doc": row["doc"], "decision": d, "reason": reason}, ensure_ascii=False) + "\n")
                report[reason] = report.get(reason, 0) + 1
        with open(os.path.join(root, CHECKED), "a") as f:
            f.write(json.dumps({"doc": row["doc"], "prompt": CHECK_PROMPT_VERSION}) + "\n")
        report["docs"] += 1
    return report


# ---- stage 4: distractors -------------------------------------------------------

SOURCES = ("named", "own_future_work", "contemporaneous", "generated")
FUTURE_PROMPT = (
    "A researcher faced the problem below and made the decision shown. Earlier, they named the "
    "candidate ideas listed as future work. Pick the candidate that is a plausible alternative answer "
    "to the same problem and that none of their later work listed below pursued. Return JSON "
    "{\"index\": <candidate index, or null if none fits>}.\n\n")
CONTEMP_PROMPT = (
    "A researcher faced the problem below. Here is work by other groups from around the same time. "
    "Pick the result that took a different approach to the same problem, and state that approach "
    "in one sentence of similar length and specificity to the decision, without naming anyone. "
    "Return JSON {\"index\": <result index, or null if none fits>, \"alternative\": <sentence>}.\n\n")
GENERATE_PROMPT = (
    "A researcher faced the problem below and made the decision shown. Write one plausible "
    "alternative decision a competent researcher could have made instead: same scope, similar length "
    "and specificity, not obviously worse. Return JSON {\"alternative\": <sentence>}.\n\n")
HALF_YEAR = datetime.timedelta(days=182)


def _describe(d: dict) -> str:
    return f"Problem: {d.get('problem', '')}\nDecision: {d.get('did', '')}\n"


def _future_candidates(researcher: Researcher, before: datetime.date) -> List[str]:
    out = []
    for row in _read_jsonl(os.path.join(researcher.root, EXA_EXTRACT)):
        date, _ = read_doc(os.path.join(researcher.root, "corpus", row["doc"]))
        if date and date < before:
            out += [w["idea"] for w in row.get("future_work") or [] if isinstance(w, dict) and w.get("idea")]
    return out


def next_distractor(decision: dict, researcher: Researcher, llm: LLM, client, cutoff: str,
                    after: Optional[str] = None) -> Optional[dict]:
    """The first distractor available from SOURCES, starting after `after`. A decision dated
    before cutoff sees only material dated before cutoff."""
    date, t = datetime.date.fromisoformat(decision["date"]), datetime.date.fromisoformat(cutoff)
    horizon = t if date < t else None
    for source in SOURCES[SOURCES.index(after) + 1 if after else 0:]:
        if source == "named":
            alts = [a for a in decision.get("alternatives_named") or [] if a and a != decision.get("did")]
            if alts:
                return {"text": alts[0], "source": source, "evidence_url": decision.get("url")}
        elif source == "own_future_work":
            ideas = _future_candidates(researcher, date)
            if not ideas:
                continue
            later = [d["did"] for d in _read_jsonl(os.path.join(researcher.root, DECISIONS))
                     if d.get("date") and (horizon is None or d["date"] < cutoff)]
            out = extract_json(llm.complete(
                FUTURE_PROMPT + _describe(decision) + "Candidates:\n" +
                "".join(f"[{i}] {c}\n" for i, c in enumerate(ideas)) +
                "Their work:\n" + "".join(f"- {w}\n" for w in later), temperature=0.0))
            i = out.get("index") if isinstance(out, dict) else None
            if isinstance(i, int) and 0 <= i < len(ideas):
                return {"text": ideas[i], "source": source, "evidence_url": None}
        elif source == "contemporaneous" and client is not None:
            end = date + HALF_YEAR
            if horizon:
                end = min(end, horizon - datetime.timedelta(days=1))
            results = [r for r in client.search(decision.get("problem") or decision["did"], num_results=8,
                                                start_date=(date - HALF_YEAR).isoformat(), end_date=end.isoformat(),
                                                exclude_text=["Hobbhahn"], exclude_domains=["apolloresearch.ai"])
                       if "hobbhahn" not in (str(r.get("author") or "") + str(r.get("highlights") or "")).lower()
                       and r.get("publishedDate") and r["publishedDate"][:10] <= end.isoformat()]
            if not results:
                continue
            out = extract_json(llm.complete(
                CONTEMP_PROMPT + _describe(decision) + "Results:\n" +
                "".join(f"[{i}] {r.get('title', '')}: {' '.join(r.get('highlights') or [])[:500]}\n"
                        for i, r in enumerate(results)), temperature=0.0))
            i = out.get("index") if isinstance(out, dict) else None
            if isinstance(i, int) and 0 <= i < len(results) and out.get("alternative"):
                return {"text": str(out["alternative"]), "source": source, "evidence_url": results[i]["url"]}
        elif source == "generated":
            out = extract_json(llm.complete(GENERATE_PROMPT + _describe(decision), temperature=0.0))
            if isinstance(out, dict) and out.get("alternative"):
                return {"text": str(out["alternative"]), "source": source, "evidence_url": None}
    return None


def find_distractors(researcher: Researcher, llm: LLM, client, cutoff: str) -> dict:
    """One distractor per checked decision in extraction/distractors.jsonl; resumable."""
    path = os.path.join(researcher.root, DISTRACTORS)
    done = {r["decision_id"] for r in _read_jsonl(path)}
    report = {s: 0 for s in SOURCES}
    report.update(none=0, skipped_existing=len(done))
    for d in _read_jsonl(os.path.join(researcher.root, DECISIONS)):
        if d["decision_id"] in done or not d.get("date"):
            continue
        out = next_distractor(d, researcher, llm, client, cutoff)
        report[out["source"] if out else "none"] += 1
        if out:
            with open(path, "a") as f:
                f.write(json.dumps(dict(out, decision_id=d["decision_id"], cutoff=cutoff), ensure_ascii=False) + "\n")
    return report


# ---- stage 5: pairs and the time split ---------------------------------------------

PAIR_PROMPT_VERSION = "pair-v1"
PAIR_PROMPT = (
    "Turn this research decision into one neutral binary choice. Write the context as the situation "
    "the researchers faced at the moment of decision: the problem and what they knew then, and for a "
    "decision about accepting, interpreting or claiming a result, the result itself. Do not reveal "
    "which option was taken, and do not name any person, lab or organisation, or any later paper. "
    "Then restate the decision taken and the alternative as two options of similar length (within "
    "20%) and the same style. Return JSON {\"context\": str, \"did\": str, \"alternative\": str}.\n\n")
BANNED = re.compile(r"hobbhahn|marius|apollo", re.IGNORECASE)
ANON_USER = "subject"


def check_pair(pair: dict, later_titles: List[str]) -> List[str]:
    """Problems with a written pair; empty when it is fine."""
    problems = []
    lengths = sorted((len(pair["a_text"]), len(pair["b_text"])))
    if not lengths[0] or lengths[1] / lengths[0] > 1.2:
        problems.append("the two options differ in length by more than 20%")
    if any(BANNED.search(pair[k]) for k in ("context", "a_text", "b_text")):
        problems.append("names the researcher or his organisation")
    ctx = pair["context"].lower()
    problems += [f"mentions later work: {t}" for t in later_titles if len(t) >= 8 and t.lower() in ctx]
    return problems


def _one_line(text) -> str:
    return " ".join(str(text or "").split())


def _corpus_meta(root: str) -> List[Tuple[Optional[datetime.date], str, dict]]:
    out = []
    for p in glob.glob(os.path.join(root, "corpus", "*.txt")):
        date, _ = read_doc(p)
        out.append((date, os.path.basename(p), front_matter(p)))
    return out


def render_pair(d: dict, alternative: str, llm: LLM, later_titles: List[str]) -> Tuple[Optional[dict], List[str]]:
    """(context/a_text/b_text with a_text the decision taken, problems). One rewrite on failure."""
    prompt = (PAIR_PROMPT + f"Problem: {_one_line(d.get('problem'))}\nDecision: {_one_line(d['did'])}\n"
              f"Alternative: {_one_line(alternative)}\nReason they gave: {_one_line(d.get('stated_reason'))}\n")
    pair, problems = None, ["no answer"]
    for attempt in range(2):
        out = extract_json(llm.complete(prompt + ("" if attempt == 0 else "Fix these problems: "
                                                  + "; ".join(problems) + "\n"), temperature=0.0))
        if not (isinstance(out, dict) and out.get("context") and out.get("did") and out.get("alternative")):
            continue
        pair = {"context": str(out["context"]), "a_text": str(out["did"]), "b_text": str(out["alternative"])}
        problems = check_pair(pair, later_titles)
        if not problems:
            return pair, []
    return None, problems


def _later_titles(docs, date: str) -> List[str]:
    return [fm.get("title", "") for d, _, fm in docs if d and d.isoformat() > date]


def _pair_row(researcher: Researcher, d: dict, alt: dict, pair: dict, cutoff: str, seed: int, meta: dict) -> dict:
    pair_id = digest([researcher.slug, d["decision_id"], alt["text"]])[:12]
    did, other = pair["a_text"], pair["b_text"]
    real_first = random.Random(f"{seed}:{pair_id}").random() < 0.5
    return {"pair_id": pair_id, "decision_id": d["decision_id"],
            "split": "history" if d["date"] < cutoff else "heldout",
            "date": d["date"], "source_doc": d["doc"], "url": d["url"],
            "decision_point": d.get("point") or "D1", "context": pair["context"],
            "a_text": did if real_first else other, "b_text": other if real_first else did,
            "chosen": "a" if real_first else "b", "reason": _one_line(d.get("stated_reason")),
            "tag": d.get("tag"), "distractor_source": alt["source"],
            "author_position": meta.get(d["doc"], {}).get("author_position"), "cutoff": cutoff,
            "seed": seed, "prompt_versions": [CHECK_PROMPT_VERSION, PAIR_PROMPT_VERSION]}


def write_pairs(researcher: Researcher, llm: LLM, cutoff: str, seed: int = 0) -> dict:
    """Write pairs_timesplit.jsonl from checked decisions and their distractors, then both Choice
    files. Never overwrites: the held-out set and its review must not shift under a rerun."""
    root = researcher.root
    if os.path.exists(os.path.join(root, PAIRS)):
        raise FileExistsError(f"{PAIRS} exists for {researcher.slug}; delete it to rebuild")
    distractors = {r["decision_id"]: r for r in _read_jsonl(os.path.join(root, DISTRACTORS))}
    stale = {r.get("cutoff") for r in distractors.values()} - {cutoff}
    if stale:
        raise ValueError(f"distractors were chosen for cutoff {sorted(map(str, stale))}, not {cutoff}; "
                         f"delete {DISTRACTORS} and rerun distract")
    docs = _corpus_meta(root)
    meta = {name: fm for _, name, fm in docs}
    # Pairs are appended to a partial file as they are written, so a crash loses at most one.
    partial = os.path.join(root, PAIRS + ".partial")
    done = {r["decision_id"] for r in _read_jsonl(partial)}
    failed = 0
    for d in _read_jsonl(os.path.join(root, DECISIONS)):
        alt = distractors.get(d["decision_id"])
        if not alt or not d.get("date") or d["decision_id"] in done:
            continue
        pair, _ = render_pair(d, alt["text"], llm, _later_titles(docs, d["date"]))
        if pair is None:
            failed += 1
            continue
        with open(partial, "a") as f:
            f.write(json.dumps(_pair_row(researcher, d, alt, pair, cutoff, seed, meta), ensure_ascii=False) + "\n")
    pairs = _read_jsonl(partial)
    _write_jsonl(os.path.join(root, PAIRS), pairs)
    if os.path.exists(partial):
        os.remove(partial)
    write_choice_files(researcher)
    return {"pairs": len(pairs), "failed_checks": failed, "cutoff": cutoff,
            "history": sum(p["split"] == "history" for p in pairs),
            "heldout": sum(p["split"] == "heldout" for p in pairs)}


def regenerate_pair(researcher: Researcher, pair: dict, llm: LLM, client) -> Optional[dict]:
    """The pair rebuilt with the next distractor source after its current one, or None."""
    d = next(r for r in _read_jsonl(os.path.join(researcher.root, DECISIONS))
             if r["decision_id"] == pair["decision_id"])
    alt = next_distractor(d, researcher, llm, client, pair["cutoff"], after=pair["distractor_source"])
    if alt is None:
        return None
    docs = _corpus_meta(researcher.root)
    rendered, _ = render_pair(d, alt["text"], llm, _later_titles(docs, d["date"]))
    if rendered is None:
        return None
    row = _pair_row(researcher, d, alt, rendered, pair["cutoff"], pair.get("seed", 0),
                    {name: fm for _, name, fm in docs})
    return dict(row, regenerated_from=pair["pair_id"])


def write_choice_files(researcher: Researcher) -> None:
    """Rewrite history and held-out Choice rows from the pairs, minus rejected pairs."""
    rejected = {r["pair_id"] for r in _read_jsonl(os.path.join(researcher.root, REVIEW)) if not r["ok"]}
    rows = {"history": [], "heldout": []}
    for p in _read_jsonl(os.path.join(researcher.root, PAIRS)):
        if p["pair_id"] in rejected:
            continue
        # Every field of a Choice can reach a user model's prompt, so none may name him: an
        # anonymous user id, a hashed source URL, and no reason that names him or his lab.
        c = Choice(user_id=ANON_USER, context=p["context"], a_text=p["a_text"], b_text=p["b_text"],
                   chosen=p["chosen"], decision_point=p["decision_point"],
                   reason="" if BANNED.search(p["reason"]) else p["reason"], timestamp=p["date"],
                   source="timesplit", example_id=p["pair_id"], group_id=digest([p["url"]])[:12])
        rows[p["split"]].append(asdict(c))
    _write_jsonl(os.path.join(researcher.root, HISTORY), rows["history"])
    _write_jsonl(os.path.join(researcher.root, HELDOUT), rows["heldout"])


def review(researcher: Researcher, ask: Callable = input, say: Callable = print, limit: int = 20) -> int:
    """Show unreviewed held-out pairs (real direction marked) and record whether the
    distractor is a plausible alternative. Resumable; returns how many were reviewed."""
    path = os.path.join(researcher.root, REVIEW)
    done = {r["pair_id"] for r in _read_jsonl(path)}
    pending = [p for p in _read_jsonl(os.path.join(researcher.root, PAIRS))
               if p["split"] == "heldout" and p["pair_id"] not in done][:limit]
    n = 0
    for p in pending:
        taken, other = (p["a_text"], p["b_text"]) if p["chosen"] == "a" else (p["b_text"], p["a_text"])
        say(f"\n{p['date']}  {p['context']}\n  taken:      {taken}\n"
            f"  distractor: {other}  ({p['distractor_source']})")
        ans = ask("plausible alternative they could have taken? y/n/quit> ").strip().lower()
        if ans not in ("y", "n"):
            break
        with open(path, "a") as f:
            f.write(json.dumps({"pair_id": p["pair_id"], "ok": ans == "y"}) + "\n")
        n += 1
    write_choice_files(researcher)
    return n


EXA_CACHE = os.path.join("runs", "track_s", "cache", "exa")


def main(argv=None):
    p = argparse.ArgumentParser(description="Track S: a researcher's dated work to time-split binary pairs")
    p.add_argument("--root", default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest="command", required=True)
    for name, helptext in (("harvest", "find, check and date his work with Exa"),
                           ("extract", "Exa structured summary of each document's decisions"),
                           ("check", "Claude keeps, corrects or drops each decision and adds missed ones"),
                           ("distract", "one distractor per decision"),
                           ("pairs", "write the pairs and the history/held-out Choice files"),
                           ("review", "check held-out pairs for obviously wrong distractors")):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("--researcher", required=True)
        if name == "harvest":
            c.add_argument("--name", required=True, help="the researcher's full name")
            c.add_argument("--start", required=True)
            c.add_argument("--end", required=True)
            c.add_argument("--lesswrong", help="his LessWrong user slug; every post he wrote or co-wrote is fetched")
            c.add_argument("--feed", help="his personal blog's RSS feed URL")
        if name in ("distract", "pairs"):
            c.add_argument("--cutoff", required=True, help="YYYY-MM-DD; work from this date on is held out")
        if name in ("check", "distract", "pairs"):
            c.add_argument("--llm", default="claude-cli")
            c.add_argument("--model", default="claude-sonnet-5-5")
            c.add_argument("--max-usd", type=float, required=True, help="spend cap for this stage")
        if name == "pairs":
            c.add_argument("--seed", type=int, default=0)
        if name == "review":
            c.add_argument("--limit", type=int, default=20)
    args = p.parse_args(argv)
    researcher = load_researcher(args.researcher, args.root)
    if args.command == "review":
        print(f"reviewed {review(researcher, limit=args.limit)} pairs")
        return
    client = None
    if args.command in ("harvest", "extract", "distract"):
        from ..integrations.exa import ExaClient
        client = ExaClient(cache_dir=EXA_CACHE)
    if args.command == "harvest":
        from .scrape import (
            list_arxiv_author,
            list_feed,
            list_lesswrong_user,
            scrape_exa,
        )
        known = list_arxiv_author(args.name)
        if args.lesswrong:
            known.update(list_lesswrong_user(args.lesswrong))
        if args.feed:
            known.update(list_feed(args.feed, args.name))
        print(json.dumps(scrape_exa(args.name, researcher.root, client, args.start, args.end, known=known)))
        return
    if args.command == "extract":
        print(json.dumps(dict(exa_extract(researcher, client), exa_cost=round(client.cost, 4))))
        return
    from ..llm import Budget, get_llm
    budget = Budget(max_cost_usd=args.max_usd, max_seconds=12 * 3600)
    llm = get_llm(args.llm, args.model, budget)
    if args.command == "check":
        report = check_decisions(researcher, llm)
    elif args.command == "distract":
        report = find_distractors(researcher, llm, client, args.cutoff)
        report["exa_cost"] = round(client.cost, 4)
    else:
        report = write_pairs(researcher, llm, args.cutoff, seed=args.seed)
    print(json.dumps(dict(report, llm_cost=round(budget.cost_usd, 4))))


if __name__ == "__main__":
    main()
