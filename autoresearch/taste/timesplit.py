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
