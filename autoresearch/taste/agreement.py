"""Agreement filter, personal track only (Ethan, 2026-11-14). A pair leaves history, val and held-out
when a blind judge (no history about the person) is asked which option is the better research
decision 5 times with each option order, and more than 80% of those 10 votes (9 or 10) go to
the option the person chose. Such a pair tests generic research sense, not this person's
taste: every arm, m0 included, gets it right, so it only adds noise. Pairs the judge decides
against the person stay; they are where taste shows.

Votes, not the model's stated probability: stated confidence is poorly calibrated, while a vote
share is a count anyone can check. Pooling both orders cancels position bias, since a judge that
always picks the first option shown lands at 5 of 10.

The judge is claude-sonnet-5-5. Each vote is recorded per pair in
<person dir>/agreement.jsonl, so a new threshold needs no new calls and a judged pair is never
judged again."""
import concurrent.futures
import datetime
import json
import os
import threading
from typing import Dict, List, Optional

from .usermodel import Choice

AGREEMENT = "agreement.jsonl"
THRESHOLD = 0.8
VOTES_PER_ORDER = 5
JUDGE_MODEL = "claude-sonnet-5-5"   # Sonnet, not Opus, for cost (Ethan)
WORKERS = 16
PROMPT = ("A researcher had to make a decision. Which of these two options is the better research "
          "decision?\n\nContext: {context}\n\nOption 1: {first}\n\nOption 2: {second}\n\n"
          'Reply with only a JSON object: {{"choice": 1}} or {{"choice": 2}}.')


def rows(d: str) -> Dict[str, dict]:
    path = os.path.join(d, AGREEMENT)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r["example_id"]: r for r in map(json.loads, filter(str.strip, f))}


def _vote(llm, context: str, first: str, second: str) -> Optional[int]:
    """1 or 2, or None when the reply names neither."""
    try:
        choice = json.loads(llm.complete(PROMPT.format(context=context, first=first, second=second),
                                         max_tokens=50, temperature=1.0)).get("choice")
    except (json.JSONDecodeError, AttributeError):
        return None
    return choice if choice in (1, 2) else None


def votes(llm, c: Choice, k: int = VOTES_PER_ORDER) -> List[List[Optional[bool]]]:
    """[person's option shown first, shown second]: per sample, whether the judge picked the
    person's option (None: no valid answer)."""
    mine, other = (c.a_text, c.b_text) if c.chosen == "a" else (c.b_text, c.a_text)
    first = [_vote(llm, c.context, mine, other) for _ in range(k)]
    second = [_vote(llm, c.context, other, mine) for _ in range(k)]
    return [[None if v is None else v == 1 for v in first], [None if v is None else v == 2 for v in second]]


def share(row: dict) -> float:
    """Share of valid votes that went to the person's option."""
    valid = [v for order in row["votes"] for v in order if v is not None]
    if not valid:
        raise ValueError(f"pair {row['example_id']} has no valid vote; delete its row and judge it again")
    return sum(valid) / len(valid)


def judge(d: str, choices: List[Choice], llm, workers: int = WORKERS) -> List[dict]:
    """Collect votes for every choice that has no row yet. Each pair's row is appended to
    d/agreement.jsonl as soon as its votes are in, so a crash loses only the pairs in flight."""
    have = rows(d)
    todo = [c for c in choices if c.example_id not in have]
    lock, new = threading.Lock(), []

    def one(c):
        row = {"example_id": c.example_id, "votes": votes(llm, c), "judge": llm.label,
               "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        with lock, open(os.path.join(d, AGREEMENT), "a") as f:
            f.write(json.dumps(row) + "\n")
            new.append(row)

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, todo))
    return new


def keep(d: str, choices: List[Choice], threshold: float = THRESHOLD) -> List[Choice]:
    """The choices the filter keeps. Refuses if any choice was never judged, so no split is
    silently left unfiltered."""
    have = rows(d)
    missing = [c.example_id for c in choices if c.example_id not in have]
    if missing:
        raise ValueError(f"{len(missing)} pair(s) have no row in {os.path.join(d, AGREEMENT)}; "
                         "run the 'agree' command first")
    return [c for c in choices if share(have[c.example_id]) <= threshold]
