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
   "behaviors": ["honest", "dishonest"], "misbehavior": "dishonest",   # optional
   "meta": {...}}                                           # optional, see load_items_with_meta

`Scenario` (measure.py) has no metadata field, so per-item metadata such as
EvalAwareBench's cue-factor flags travels beside it: `load_items_with_meta`
returns (Scenario, meta) pairs. `load_items` ignores `meta`.

The dev/held-out split can be frozen to a file of ids (`freeze_split`,
`load_split`, `apply_split`) so it never changes when the hash, the item
set or the file order does. `scripts/convert_evalawarebench.py` writes
`data/benchmarks/evalawarebench_split.json` this way, grouped by task pair.

Fetching data is a separate, deliberate step (PLAN 4.3: ask before fetching).
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, Iterable, List, Optional, Tuple

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


def _read_rows(path: str) -> List[dict]:
    rows = []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{n}: not valid JSON ({e})") from e
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{n}: expected a JSON object, got {type(row).__name__}")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no benchmark items")
    return rows


def load_items(path: str, base: Scenario = DEFAULT_SCENARIO) -> List[Scenario]:
    return [item_to_scenario(row, base) for row in _read_rows(path)]


def load_items_with_meta(path: str, base: Scenario = DEFAULT_SCENARIO) -> List[Tuple[Scenario, Dict]]:
    """Like load_items, but keeps each row's `meta` dict ({} if absent) beside its Scenario.
    Ids must be unique within the file, so meta can be looked up by Scenario.source_id."""
    out, seen = [], set()
    for row in _read_rows(path):
        meta = row.get("meta") or {}
        if not isinstance(meta, dict):
            raise ValueError(f"{path}: item {row.get('id', '?')!r} has a non-object meta ({type(meta).__name__})")
        sc = item_to_scenario(row, base)
        if sc.source_id in seen:
            raise ValueError(f"{path}: duplicate item id {sc.source_id!r}")
        seen.add(sc.source_id)
        out.append((sc, dict(meta)))
    return out


def split(items: List[Scenario], heldout_frac: float = 0.4) -> Tuple[List[Scenario], List[Scenario]]:
    """Deterministic dev / held-out split by hashed item id (PLAN 7.3: 60/40).
    Hashing keeps an item on the same side however the file is ordered or grown."""
    dev, held = [], []
    for s in items:
        (held if _bucket(s.source_id) < heldout_frac else dev).append(s)
    return dev, held


def _bucket(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % 1000 / 1000


SPLIT_VERSION = 1


def freeze_split(ids: Iterable[str], heldout_frac: float = 0.4, groups: Optional[Dict[str, str]] = None,
                 **info) -> Dict:
    """Compute a dev / held-out split of item ids, to be written once and then read
    with load_split. `groups` maps id -> group key; every id in a group lands on the
    same side (e.g. an EvalAwareBench safety/capability pair, which share scaffolding,
    so splitting them would leak). Without groups each id is its own group, which
    matches split(). Extra keyword args are stored as provenance (strings only)."""
    ids = list(ids)
    if len(set(ids)) != len(ids):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"freeze_split: duplicate ids {dup[:5]}")
    if not 0.0 < heldout_frac < 1.0:
        raise ValueError(f"freeze_split: heldout_frac must be in (0, 1), got {heldout_frac}")
    groups = groups or {}
    missing = [i for i in ids if groups and i not in groups]
    if missing:
        raise ValueError(f"freeze_split: no group for ids {missing[:5]}")
    dev, held = [], []
    for i in sorted(ids):
        (held if _bucket(groups.get(i, i)) < heldout_frac else dev).append(i)
    out = {"version": SPLIT_VERSION, "heldout_frac": heldout_frac,
           "group_by": "group" if groups else "id", "dev": dev, "heldout": held}
    for k, v in info.items():
        if not isinstance(v, str):
            raise ValueError(f"freeze_split: provenance field {k!r} must be a string")
        out[k] = v
    return out


def write_split(split_data: Dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(split_data, f, indent=1, sort_keys=True)
        f.write("\n")


def load_split(path: str) -> Dict[str, List[str]]:
    """Read a frozen split file. Returns {"dev": [ids], "heldout": [ids]}; fails loudly
    on an unknown version, a missing side, or an id on both sides."""
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("version") != SPLIT_VERSION:
        raise ValueError(f"{path}: not a version-{SPLIT_VERSION} split file")
    for side in ("dev", "heldout"):
        if not isinstance(data.get(side), list) or not all(isinstance(i, str) for i in data[side]):
            raise ValueError(f"{path}: {side!r} must be a list of id strings")
    both = set(data["dev"]) & set(data["heldout"])
    if both:
        raise ValueError(f"{path}: ids on both sides of the split: {sorted(both)[:5]}")
    return {"dev": list(data["dev"]), "heldout": list(data["heldout"])}


def apply_split(items: List[Scenario], split_ids: Dict[str, List[str]],
                allow_missing: bool = False) -> Tuple[List[Scenario], List[Scenario]]:
    """Partition items by a frozen split. An item whose id the split doesn't list is an
    error: it would otherwise silently fall on one side. `allow_missing` permits split
    ids absent from items (a subset file), never the reverse."""
    dev_ids, held_ids = set(split_ids["dev"]), set(split_ids["heldout"])
    unknown = [s.source_id for s in items if s.source_id not in dev_ids | held_ids]
    if unknown:
        raise ValueError(f"items not in the frozen split: {unknown[:5]} ({len(unknown)} total)")
    if not allow_missing:
        have = {s.source_id for s in items}
        absent = sorted((dev_ids | held_ids) - have)
        if absent:
            raise ValueError(f"split ids missing from items: {absent[:5]} ({len(absent)} total); "
                             "pass allow_missing=True for a subset")
    return ([s for s in items if s.source_id in dev_ids], [s for s in items if s.source_id in held_ids])
