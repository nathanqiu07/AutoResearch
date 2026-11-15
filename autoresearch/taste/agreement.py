"""Agreement filter, both tracks (Ethan, 2026-11-14). A pair leaves history, val and held-out
when a blind judge (no history about the person) gives the option the person chose more than
THRESHOLD in both a/b orders. Such a pair tests generic research sense, not this person's
taste: every arm, m0 included, gets it right, so it only adds noise. Pairs the judge
confidently decides against the person stay; they are where taste shows.

The judge's probabilities are recorded per pair in <person dir>/agreement.jsonl, so a new
threshold needs no new calls and a judged pair is never judged again."""
import concurrent.futures
import datetime
import json
import os
from typing import Dict, List

from .usermodel import Choice

AGREEMENT = "agreement.jsonl"
THRESHOLD = 0.8
JUDGE_MODEL = "claude-sonnet-5-5"   # Sonnet, not Opus, for cost (Ethan)
WORKERS = 16


def rows(d: str) -> Dict[str, dict]:
    path = os.path.join(d, AGREEMENT)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r["example_id"]: r for r in map(json.loads, filter(str.strip, f))}


def p_chosen(judge, c: Choice) -> List[float]:
    """The judge's probability for the person's option, shown first and shown second."""
    i = "ab".index(c.chosen)
    first = judge.predict(c.context, [c.a_text, c.b_text]).probabilities
    second = judge.predict(c.context, [c.b_text, c.a_text]).probabilities
    return [first[i], second[1 - i]]


def judge(d: str, choices: List[Choice], judge, workers: int = WORKERS) -> List[dict]:
    """Judge every choice that has no row yet and append the new rows to d/agreement.jsonl."""
    have = rows(d)
    todo = [c for c in choices if c.example_id not in have]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        probs = list(pool.map(lambda c: p_chosen(judge, c), todo))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    new = [{"example_id": c.example_id, "p_chosen": p, "judge": judge.llm.label, "timestamp": now}
           for c, p in zip(todo, probs)]
    with open(os.path.join(d, AGREEMENT), "a") as f:
        f.writelines(json.dumps(r) + "\n" for r in new)
    return new


def keep(d: str, choices: List[Choice], threshold: float = THRESHOLD) -> List[Choice]:
    """The choices the filter keeps. Refuses if any choice was never judged, so no split is
    silently left unfiltered."""
    have = rows(d)
    missing = [c.example_id for c in choices if c.example_id not in have]
    if missing:
        raise ValueError(f"{len(missing)} pair(s) have no row in {os.path.join(d, AGREEMENT)}; "
                         "run the 'agree' command first")
    return [c for c in choices if min(have[c.example_id]["p_chosen"]) <= threshold]
