"""Track S time split (PLAN 12.2): the profile is built only from documents
dated strictly before the cutoff T, so held-out pairs drawn from work after T
test prediction rather than recall.

Corpus files carry their date in front matter:

    ---
    publishedDate: 2024-05-01T00:00:00.000Z
    ---
    <text>

A file without a date is left out: it could have been written after T.

Pairs: each dated research document becomes one choice between the direction it
actually took and a distractor. The distractor is preferably a "future work"
idea named in an earlier document and never pursued, else a model-written
alternative on the same topic. Documents before T give history pairs (what a
method fits on); documents from T on give held-out pairs. A history pair is
built from documents before T only. A person then checks ~20 held-out pairs and
rejects any whose distractor is obviously wrong.

  data/researchers/<slug>/
    pairs_timesplit.jsonl     every pair with its provenance
    review_timesplit.jsonl    the person's verdicts
    history_timesplit.jsonl   Choice rows from before T
    heldout_timesplit.jsonl   Choice rows from T on, minus rejected pairs

    python3 -m autoresearch.taste.timesplit build --researcher <slug> --cutoff YYYY-MM-DD --dry-run
    python3 -m autoresearch.taste.timesplit build --researcher <slug> --cutoff YYYY-MM-DD --llm anthropic
    python3 -m autoresearch.taste.timesplit review --researcher <slug>
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import unicodedata
from dataclasses import asdict
from typing import Callable, List, Optional, Tuple

from ..llm import LLM, extract_json
from .extract import profile_from_texts
from .profile import TasteProfile
from .researcher import DEFAULT_ROOT, Researcher, load_researcher
from .usermodel import Choice, digest

PAIRS, REVIEW = "pairs_timesplit.jsonl", "review_timesplit.jsonl"
HISTORY, HELDOUT = "history_timesplit.jsonl", "heldout_timesplit.jsonl"
EXTRACT_PROMPT = ("Read this research document. Return JSON {\"topic\": <a few neutral words naming the "
                  "area>, \"direction\": <one sentence: the research direction this work took>, "
                  "\"future_work\": [<one sentence per direction it names as future or follow-up "
                  "work>]}.\n\n")

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

EXA_EXTRACT = os.path.join("extraction", "exa.jsonl")
DECISIONS = os.path.join("extraction", "decisions.jsonl")
REJECTED = os.path.join("extraction", "rejected.jsonl")
CHECKED = os.path.join("extraction", "checked.jsonl")
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

def _pick_prompt(topic: str, direction: str, candidates: List[str], taken: List[str]) -> str:
    return ("We are building a test of whether a model can predict a researcher's next direction. "
            "Give one distractor: a direction they plausibly could have taken on this topic but did "
            "not. Prefer one of the candidate ideas they named earlier, unless it matches anything "
            "in the list of directions they did take; otherwise write a new one of similar scope "
            "and specificity, so that it isn't obviously wrong. Return JSON {\"distractor\": <one "
            "sentence>}.\n\n"
            f"Topic: {topic}\nDirection actually taken: {direction}\n"
            "Candidate ideas named earlier:\n" + "".join(f"- {c}\n" for c in candidates) +
            "Directions they did take:\n" + "".join(f"- {t}\n" for t in taken))


def _write_jsonl(path: str, rows: List[dict]) -> None:
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _read_jsonl(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def build_pairs(researcher: Researcher, cutoff: str, llm: LLM) -> dict:
    """Write the pairs and both Choice files. Never overwrites: the held-out set and
    its review must not shift under a rerun."""
    if os.path.exists(os.path.join(researcher.root, PAIRS)):
        raise FileExistsError(f"{PAIRS} exists for {researcher.slug}; delete it to rebuild")
    t = datetime.date.fromisoformat(cutoff)
    research = [(date, name, text) for date, kind, name, text in dated_docs(researcher) if kind == "research"]
    docs = []
    for date, name, text in research:
        out = extract_json(llm.complete(EXTRACT_PROMPT + text[:12000], temperature=0.0))
        if isinstance(out, dict) and out.get("direction"):
            docs.append({"date": date, "name": name, "topic": str(out.get("topic", "")),
                         "direction": str(out["direction"]),
                         "future_work": [str(x) for x in out.get("future_work") or []]})
    pairs, skipped = [], len(research) - len(docs)
    for d in docs:
        held_out = d["date"] >= t
        visible = [e for e in docs if held_out or e["date"] < t]   # a history pair sees nothing from T on
        candidates = [idea for e in visible if e["date"] < d["date"] for idea in e["future_work"]]
        out = extract_json(llm.complete(_pick_prompt(d["topic"], d["direction"], candidates,
                                                     [e["direction"] for e in visible]), temperature=0.0))
        distractor = str(out.get("distractor", "")).strip() if isinstance(out, dict) else ""
        if not distractor or distractor == d["direction"]:
            skipped += 1
            continue
        pair_id = digest([researcher.slug, d["name"], d["direction"], distractor])[:12]
        real_first = int(pair_id, 16) % 2 == 0
        pairs.append({"pair_id": pair_id, "split": "heldout" if held_out else "history",
                      "date": d["date"].isoformat(), "source_doc": d["name"], "topic": d["topic"],
                      "direction": d["direction"], "distractor": distractor,
                      "distractor_origin": "future_work" if distractor in candidates else "generated",
                      "a_text": d["direction"] if real_first else distractor,
                      "b_text": distractor if real_first else d["direction"],
                      "chosen": "a" if real_first else "b"})
    _write_jsonl(os.path.join(researcher.root, PAIRS), pairs)
    write_choice_files(researcher)
    return {"pairs": len(pairs), "skipped": skipped, "cutoff": cutoff,
            "history": sum(p["split"] == "history" for p in pairs),
            "heldout": sum(p["split"] == "heldout" for p in pairs)}


# ---- stage 2: Exa structured extraction -----------------------------------------

def exa_extract(researcher: Researcher, client, batch: int = 10) -> dict:
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
        by_url = {r.get("url"): r for r in client.contents([u for _, u in chunk], text_chars=1, summary=summary)}
        with open(path, "a") as f:
            for doc, url in chunk:
                r = by_url.get(url, {})
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


def _context(slug: str, pair: dict) -> str:
    return (f"Topic: {pair['topic']}\n"
            f"Which research direction did {slug} pursue around {pair['date'][:7]}?")


def write_choice_files(researcher: Researcher) -> None:
    """Rewrite history and held-out Choice rows from the pairs, minus rejected pairs."""
    rejected = {r["pair_id"] for r in _read_jsonl(os.path.join(researcher.root, REVIEW)) if not r["ok"]}
    rows = {"history": [], "heldout": []}
    for p in _read_jsonl(os.path.join(researcher.root, PAIRS)):
        if p["pair_id"] in rejected:
            continue
        c = Choice(user_id=researcher.slug, context=_context(researcher.slug, p), a_text=p["a_text"],
                   b_text=p["b_text"], chosen=p["chosen"], decision_point="D1", timestamp=p["date"],
                   source="timesplit", example_id=p["pair_id"])
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
        say(f"\n{p['date']}  {p['topic']}\n  taken:      {p['direction']}\n"
            f"  distractor: {p['distractor']}  ({p['distractor_origin']})")
        ans = ask("plausible alternative they could have taken? y/n/quit> ").strip().lower()
        if ans not in ("y", "n"):
            break
        with open(path, "a") as f:
            f.write(json.dumps({"pair_id": p["pair_id"], "ok": ans == "y"}) + "\n")
        n += 1
    write_choice_files(researcher)
    return n


def main(argv=None):
    p = argparse.ArgumentParser(description="Track S time split: history and held-out pairs (PLAN 12.2)")
    p.add_argument("--root", default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build history and held-out pairs from the dated corpus")
    b.add_argument("--researcher", required=True)
    b.add_argument("--cutoff", required=True, help="YYYY-MM-DD; documents from this date on are held out")
    b.add_argument("--llm", default="offline")
    b.add_argument("--model", default="claude-sonnet-5-5")
    b.add_argument("--max-calls", type=int, default=400)
    b.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("review", help="check held-out pairs for obviously wrong distractors")
    r.add_argument("--researcher", required=True)
    r.add_argument("--limit", type=int, default=20)
    args = p.parse_args(argv)
    researcher = load_researcher(args.researcher, args.root)
    if args.command == "review":
        print(f"reviewed {review(researcher, limit=args.limit)} pairs")
        return
    docs = dated_docs(researcher)
    research = [d for d in docs if d[1] == "research"]
    t = datetime.date.fromisoformat(args.cutoff)
    if args.dry_run:
        print(json.dumps({"dated_research_docs": len(research),
                          "before_cutoff": sum(d[0] < t for d in research),
                          "from_cutoff": sum(d[0] >= t for d in research),
                          "max_model_calls": 2 * len(research), "note": "no model calls made"}))
        return
    from ..llm import Budget, get_llm
    llm = get_llm(args.llm, args.model, Budget(max_calls=args.max_calls))
    print(json.dumps(build_pairs(researcher, args.cutoff, llm)))


if __name__ == "__main__":
    main()
