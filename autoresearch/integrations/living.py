"""The living user model (PLAN 10, past.dev item 2; PLAN 12.5 item 5).

Two fact kinds in shared memory (past.dev when PAST_API_KEY is set, else the
local JSONL store) let the user model be rebuilt between runs from what the
researcher and the loop wrote, on any worker:

  LABEL     the researcher's own choice between two options at a decision point
            (written by `label_pending` or any labelling tool through `write_label`).
  DISAGREE  the loop's action differed from the user model's pick
            (research/decisions.DecisionLog writes one per override). These are
            the decisions most worth a label, so `pending` lists the ones not
            labelled yet.

`choices_from_memory` turns LABEL facts into WS A `Choice` records
(taste/usermodel.py) for `UserModel.fit`; `export` writes them as JSONL.

    python3 -m autoresearch.integrations.living pending --memory runs/research_memory
    python3 -m autoresearch.integrations.living label --user my_slug --memory runs/research_memory
    python3 -m autoresearch.integrations.living export --user my_slug --memory runs/research_memory --out choices.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from typing import Callable, Dict, List, Optional

from .shared_memory import format_fact, get_shared_memory

MAX_TEXT = 300
RECALL_LIMIT = 1000


def _clean(text: str, n: int = MAX_TEXT) -> str:
    """Fact values cannot hold double quotes or newlines (shared_memory.FACT_RE)."""
    return " ".join(str(text).replace('"', "'").split())[:n]


def _key(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode()).hexdigest()[:12]


def write_label(shared, user_id: str, context: str, a_text: str, b_text: str, chosen: str, point: str = "",
                reason: str = "", run: str = "", source: str = "label", key: str = "") -> str:
    """One LABEL fact; returns its key (the DISAGREE key it answers, if given)."""
    if chosen not in ("a", "b"):
        raise ValueError(f"chosen must be 'a' or 'b', got {chosen!r}")
    key = key or _key(user_id, context, a_text, b_text)
    shared.write("labeller", format_fact(
        "LABEL", key=key, user=_clean(user_id, 80), point=point or "none", run=run or "none", chosen=chosen,
        source=source, t=int(time.time()), context=_clean(context), a=_clean(a_text), b=_clean(b_text),
        reason=_clean(reason) or "none"))
    return key


def write_disagree(shared, run: str, arm: str, it: int, point: str, context: str, options: List[str],
                   chosen: int, user_model_choice: int, confidence: Optional[float]) -> str:
    """One DISAGREE fact for a decision where the loop overrode the user model."""
    key = _key(run, str(it), point, context)
    shared.write("decider", format_fact(
        "DISAGREE", key=key, run=run, arm=arm or "none", iter=it, point=point,
        confidence=round(confidence, 3) if confidence is not None else "none", context=_clean(context),
        action=_clean(options[chosen]), taste=_clean(options[user_model_choice])))
    return key


def _facts(shared, kind: str, query: str) -> List[dict]:
    seen, out = set(), []
    for f in shared.facts("living", query, kind, limit=RECALL_LIMIT):
        sig = (f.get("key"), f.get("user"), f.get("chosen"), f.get("t"))
        if sig not in seen:
            seen.add(sig)
            out.append(f)
    return out


def labels(shared, user_id: Optional[str] = None) -> List[dict]:
    """LABEL facts (latest per key wins: a person may change their mind)."""
    latest: Dict[str, dict] = {}
    for f in _facts(shared, "LABEL", f"LABEL user={user_id}" if user_id else "LABEL"):
        if user_id and f.get("user") != _clean(user_id, 80):
            continue
        k = f"{f.get('user')}:{f.get('key')}"
        if k not in latest or int(f.get("t", 0)) >= int(latest[k].get("t", 0)):
            latest[k] = f
    return sorted(latest.values(), key=lambda f: int(f.get("t", 0)))


def choices_from_memory(shared, user_id: str) -> list:
    """WS A Choice records from this user's LABEL facts, oldest first."""
    from ..taste.usermodel import Choice
    return [Choice(user_id=user_id, context=f.get("context", ""), a_text=f.get("a", ""), b_text=f.get("b", ""),
                   chosen=f["chosen"], decision_point="" if f.get("point") == "none" else f.get("point", ""),
                   reason="" if f.get("reason") == "none" else f.get("reason", ""),
                   timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(f.get("t", 0)))),
                   source=f.get("source", "label"), example_id=f.get("key", ""))
            for f in labels(shared, user_id)]


def pending(shared, user_id: Optional[str] = None) -> List[dict]:
    """DISAGREE facts that this user (or anyone, without user_id) has not labelled."""
    done = {f.get("key") for f in labels(shared, user_id)}
    out, seen = [], set()
    for f in _facts(shared, "DISAGREE", "DISAGREE"):
        if f.get("key") in done or f.get("key") in seen:
            continue
        seen.add(f.get("key"))
        out.append(f)
    return out


def label_pending(shared, user_id: str, ask: Callable[[str], str] = input, limit: int = 20, out=sys.stdout) -> int:
    """Ask the researcher about each pending disagreement; writes LABEL facts.
    Option a is the user model's pick, b the loop's action; their order is shown
    shuffled by key so the labeller cannot tell which is which."""
    n = 0
    for f in pending(shared, user_id)[:limit]:
        swap = int(f["key"], 16) % 2 == 1
        a, b = (f["action"], f["taste"]) if swap else (f["taste"], f["action"])
        print(f"\n[{f.get('point')} run {f.get('run')} iter {f.get('iter')}] {f.get('context')}", file=out)
        print(f"  a) {a}\n  b) {b}", file=out)
        ans = ask("a/b/skip> ").strip().lower()
        if ans in ("a", "b"):
            write_label(shared, user_id, f.get("context", ""), a, b, ans, point=f.get("point", ""),
                        run=f.get("run", ""), source="disagreement", key=f["key"])
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["pending", "label", "export"])
    ap.add_argument("--memory", default="runs/research_memory", help="local store dir when PAST_API_KEY is unset")
    ap.add_argument("--user")
    ap.add_argument("--out")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args(argv)
    shared = get_shared_memory(os.path.join(args.memory, "shared.jsonl"))
    print(f"shared memory: {shared.backend}")
    if args.what == "pending":
        for f in pending(shared, args.user):
            print(f"{f['key']} {f.get('point')} run={f.get('run')} taste={f.get('taste')!r} action={f.get('action')!r}")
        return 0
    if not args.user:
        raise SystemExit("--user is required")
    if args.what == "label":
        print(f"labelled {label_pending(shared, args.user, limit=args.limit)}")
        return 0
    cs = choices_from_memory(shared, args.user)
    if not args.out:
        raise SystemExit("export needs --out")
    with open(args.out, "w") as f:
        for c in cs:
            f.write(json.dumps(vars(c)) + "\n")
    print(f"wrote {len(cs)} choices to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
