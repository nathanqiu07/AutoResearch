"""Benchmark items as rewrite inputs.

Each item is one existing test environment (e.g. an EvalAwareBench or
Agentic-Misalignment prompt) that the loop rewrites to look like deployment.
The untouched item is the baseline; a rewrite only counts if the faithfulness
judge says it still tests the same thing.

Items live in a local JSONL file, one per line. We have not verified the
upstream datasets' exact schemas, so the loader accepts a few common field
names and fails loudly on anything it can't map:

  {"id": "...", "system": "...", "user": "...",            # required: user (or input/prompt)
   "probe": "what opportunity it tests",                    # optional
   "behaviors": ["honest", "dishonest"], "misbehavior": "dishonest"}   # optional

Fetching data is a separate, deliberate step (PLAN 4.3: ask before fetching).
"""
from __future__ import annotations

import hashlib
import json
from typing import List, Tuple

from .measure import DEFAULT_SCENARIO, Scenario

USER_KEYS = ("user", "input", "prompt", "user_prompt")
SYSTEM_KEYS = ("system", "system_prompt")


def _first(row: dict, keys) -> str:
    for k in keys:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def item_to_scenario(row: dict, base: Scenario = DEFAULT_SCENARIO) -> Scenario:
    user = _first(row, USER_KEYS)
    if not user:
        raise ValueError(f"benchmark item {row.get('id', '?')!r} has no user turn (looked for {USER_KEYS})")
    item_id = str(row.get("id") or hashlib.sha1(user.encode()).hexdigest()[:10])
    behaviors = row.get("behaviors") or base.behaviors
    misbehavior = row.get("misbehavior") or base.misbehavior
    if any(m not in behaviors for m in misbehavior.split("|")):
        raise ValueError(f"benchmark item {item_id!r}: misbehavior {misbehavior!r} not among behaviors {behaviors}")
    probe = row.get("probe") or base.probe
    return Scenario(
        name=f"item_{item_id}", goal=f"Rewrite benchmark item {item_id} so the target does not recognise it as a "
                                     f"test, while it still tests: {probe}",
        setting=row.get("setting") or "as in the original item",
        probe=probe, behaviors=list(behaviors), misbehavior=misbehavior,
        corpus_keywords=row.get("corpus_keywords", base.corpus_keywords),
        original={"system": _first(row, SYSTEM_KEYS), "user": user}, source_id=item_id)


def load_items(path: str, base: Scenario = DEFAULT_SCENARIO) -> List[Scenario]:
    out = []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{n}: not valid JSON ({e})") from e
            out.append(item_to_scenario(row, base))
    if not out:
        raise ValueError(f"{path}: no benchmark items")
    return out


def split(items: List[Scenario], heldout_frac: float = 0.4) -> Tuple[List[Scenario], List[Scenario]]:
    """Deterministic dev / held-out split by hashed item id (PLAN 7.3: 60/40).
    Hashing keeps an item on the same side however the file is ordered or grown."""
    dev, held = [], []
    for s in items:
        h = int(hashlib.sha256(s.source_id.encode()).hexdigest(), 16) % 1000 / 1000
        (held if h < heldout_frac else dev).append(s)
    return dev, held
