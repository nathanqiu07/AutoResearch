"""Item gate for the personal-track questionnaire (Ethan, 2026-11-14). Before a trade-off pair is
shown to anyone, a blind judge (no history about any person) is asked which option is the better
research decision in both option orders. The pair is lopsided, and never shown, when
more than 80% of valid votes go to either option: whoever answers it, it tests
generic research sense, not taste. `trackp gate` rewrites a lopsided pair's options, keeping
their poles, and judges the rewrite. Nobody re-checks a pair by hand.

Votes, not the model's stated probability: stated confidence is poorly calibrated, and a vote
share is a count anyone can check. A separate position check rejects judges that mostly pick
the same display position regardless of the option placed there.

The judge model and vote count are recorded per item in <root>/agreement.jsonl, keyed by
the question and the two pole texts (not the a/b order), so an item is judged once for every
person who gets it, and a new threshold needs no new calls."""
import concurrent.futures
import datetime
import json
import os
import threading
from typing import Dict, List, Optional

from . import tradeoffs
from .usermodel import digest

AGREEMENT = "agreement.jsonl"
THRESHOLD = 0.8
VOTES_PER_ORDER = 5
JUDGE_MODEL = "claude-haiku-5-5"
WORKERS = 4
PROMPT = ("A researcher had to make a decision. Which of these two options is the better research "
          "decision?\n\nContext: {context}\n\nOption 1: {first}\n\nOption 2: {second}\n\n"
          'Reply with only a JSON object: {{"choice": 1}} or {{"choice": 2}}.')
_LOCK = threading.Lock()


def poles(pair: dict) -> List[str]:
    """[pole 1 text, pole 2 text]."""
    return [pair["a_text"], pair["b_text"]] if pair["a_pole"] == 1 else [pair["b_text"], pair["a_text"]]


def key(pair: dict) -> str:
    return digest([tradeoffs.full_context(pair), *poles(pair)])[:16]


def rows(root: str) -> Dict[str, dict]:
    path = os.path.join(root, AGREEMENT)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r["key"]: r for r in map(json.loads, filter(str.strip, f))}


def _vote(llm, context: str, first: str, second: str) -> Optional[int]:
    """1 or 2, or None when the reply names neither."""
    try:
        choice = json.loads(llm.complete(PROMPT.format(context=context, first=first, second=second),
                                         max_tokens=50, temperature=1.0)).get("choice")
    except (json.JSONDecodeError, AttributeError):
        return None
    return choice if choice in (1, 2) else None


def votes(llm, context: str, pole_1: str, pole_2: str, k: int = VOTES_PER_ORDER) -> List[List[Optional[bool]]]:
    """[pole 1 shown first, shown second]: per sample, whether the judge picked pole 1
    (None: no valid answer)."""
    first = [_vote(llm, context, pole_1, pole_2) for _ in range(k)]
    second = [_vote(llm, context, pole_2, pole_1) for _ in range(k)]
    return [[None if v is None else v == 1 for v in first], [None if v is None else v == 2 for v in second]]


def share(row: dict) -> float:
    """Share of valid votes that went to pole 1."""
    valid = [v for order in row["votes"] for v in order if v is not None]
    if not valid:
        raise ValueError(f"item {row['key']} has no valid vote; delete its row and judge it again")
    return sum(valid) / len(valid)


def lopsided(row: dict, threshold: float = THRESHOLD) -> bool:
    s = share(row)
    return max(s, 1 - s) > threshold


def position_biased(row: dict, threshold: float = THRESHOLD) -> bool:
    """The model picks a display position regardless of which pole it contains."""
    first = [v for v in row["votes"][0] if v is not None]
    second = [v for v in row["votes"][1] if v is not None]
    valid = len(first) + len(second)
    if not first or not second:
        return True
    first_share = (sum(first) + len(second) - sum(second)) / valid
    return max(first_share, 1 - first_share) > threshold


def judge(root: str, pairs: List[dict], llm, workers: int = WORKERS,
          votes_per_order: int = VOTES_PER_ORDER, rejudge_position_bias: bool = False) -> Dict[str, dict]:
    """Votes for every pair, collecting them for items that have no row yet. Each item's row is
    appended to root/agreement.jsonl as soon as its votes are in, so a crash loses only the items
    in flight. A different model may rejudge position-biased rows when requested; the old row
    remains in the audit log. Returns key -> latest row for the given pairs."""
    have = rows(root)
    todo = list({key(p): p for p in pairs if key(p) not in have or
                 (rejudge_position_bias and have[key(p)]["judge"] != llm.label and
                  position_biased(have[key(p)]))}.items())

    def one(item):
        k, p = item
        context, (p1, p2) = tradeoffs.full_context(p), poles(p)
        row = {"key": k, "context": context, "pole_1": p1, "pole_2": p2,
               "votes": votes(llm, context, p1, p2, votes_per_order),
               "judge": llm.label,
               "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        with _LOCK, open(os.path.join(root, AGREEMENT), "a") as f:
            f.write(json.dumps(row) + "\n")
        have[k] = row

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, todo))
    return {key(p): have[key(p)] for p in pairs}


def passes(root: str, pair: dict, threshold: float = THRESHOLD) -> Optional[bool]:
    """True when the pair may be shown, False when lopsided or position-biased."""
    row = rows(root).get(key(pair))
    return None if row is None else not (lopsided(row, threshold) or position_biased(row, threshold))
