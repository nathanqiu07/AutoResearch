"""Personal-track item reviews and the archived blind-model vote gate.

An item may be shown only after a reviewer records why both options are defensible under the
same constraint. Model vote parity is not an eligibility test: a strong preference may reflect
a real preference, and a balanced vote share may come from display-position bias. The old
votes remain in agreement.jsonl for audit and for experiments that use the voting functions.
"""
import concurrent.futures
import datetime
import json
import os
import threading
from typing import Dict, List, Optional

from . import tradeoffs
from .usermodel import digest

AGREEMENT = "agreement.jsonl"
REVIEWS = "item_reviews.jsonl"
THRESHOLD = 0.8
VOTES_PER_ORDER = 5
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


def review_rows(root: str) -> Dict[str, dict]:
    path = os.path.join(root, REVIEWS)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r["key"]: r for r in map(json.loads, filter(str.strip, f))}


def record_reviews(root: str, pairs: List[dict], decisions: List[dict]) -> int:
    """Append validated reviews; an existing question cannot silently change its decision."""
    by_id = {p["pair_id"]: p for p in pairs}
    seen = set(review_rows(root))
    prepared = []
    for item in decisions:
        pair = by_id.get(item.get("pair_id"))
        if pair is None:
            raise ValueError(f"unknown pair_id: {item.get('pair_id')}")
        decision = item.get("decision")
        if decision not in ("pass", "reject", "superseded"):
            raise ValueError("decision must be pass, reject or superseded")
        fields = ["reviewer", "reason"]
        if decision == "pass":
            fields += ["benefit_1", "cost_1", "benefit_2", "cost_2"]
        for field in fields:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"review for {pair['pair_id']} needs {field}")
        k = key(pair)
        if k in seen:
            raise ValueError(f"item {k} already has a review")
        seen.add(k)
        prepared.append({**item, "key": k,
                         "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    if prepared:
        with _LOCK, open(os.path.join(root, REVIEWS), "a") as f:
            f.writelines(json.dumps(row) + "\n" for row in prepared)
    return len(prepared)


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


def passes(root: str, pair: dict) -> Optional[bool]:
    """True when reviewed as a useful trade-off, False when rejected or superseded."""
    row = review_rows(root).get(key(pair))
    return None if row is None else row["decision"] == "pass"
