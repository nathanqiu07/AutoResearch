"""Decision records at the loop's decision points (PLAN 3.1, 12.6).

The research loop exposes six decision points:

  D1  which candidate intervention(s) to test next
  D2  what evidence to collect (sample count and target)
  D3  accept, reject or defer a result
  D4  keep or abandon a direction (intervention category)
  D5  how to read a result (competing explanations)
  D6  what to claim in the write-up

Each decision is one `DecisionRecord`. One log feeds three things: fidelity
labels (the researcher labels the same records), the judgment audit (E4b), and
the "did taste change the action" analysis (I15, via `overrode_taste`).

`DecisionLog` appends records to `<root>/<run_id>/decisions.jsonl` and, when a
shared memory is attached, writes a `DECISION` fact per record.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

POINTS = ("D1", "D2", "D3", "D4", "D5", "D6")


@dataclass
class DecisionRecord:
    run_id: str
    iter: int
    point: str                                  # "D1".."D6"
    context: str
    options: List[str]
    chosen: int                                 # index into options
    user_model_choice: Optional[int]            # None when no user model was consulted (R0, prompt arms)
    user_model_confidence: Optional[float]
    evidence: Dict = field(default_factory=dict)  # p_better, delta, ci90, validity, n, ...
    overrode_taste: bool = False                # the action differs from the user model's choice
    arm: str = ""
    code_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def validate_record(rec: dict) -> List[str]:
    """Problems with one record (empty list = valid). Used by tests and by the
    rating-packet script before it trusts a decisions.jsonl."""
    errs = []
    types = {"run_id": str, "iter": int, "point": str, "context": str, "options": list, "chosen": int,
             "evidence": dict, "overrode_taste": bool, "arm": str, "code_version": str}
    for k, t in types.items():
        if k not in rec:
            errs.append(f"missing {k}")
        elif not isinstance(rec[k], t) or (t is int and isinstance(rec[k], bool)):
            errs.append(f"{k} should be {t.__name__}, got {type(rec[k]).__name__}")
    for k in ("user_model_choice", "user_model_confidence"):
        if k not in rec:
            errs.append(f"missing {k}")
    if errs:
        return errs
    if rec["point"] not in POINTS:
        errs.append(f"point {rec['point']!r} not in {POINTS}")
    opts = rec["options"]
    if not opts or not all(isinstance(o, str) for o in opts):
        errs.append("options must be a non-empty list of strings")
    elif not 0 <= rec["chosen"] < len(opts):
        errs.append(f"chosen {rec['chosen']} out of range for {len(opts)} options")
    umc, conf = rec["user_model_choice"], rec["user_model_confidence"]
    if umc is not None:
        if not isinstance(umc, int) or isinstance(umc, bool) or not 0 <= umc < len(opts or []):
            errs.append(f"user_model_choice {umc!r} out of range")
        if not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
            errs.append(f"user_model_confidence {conf!r} must be in [0, 1] when a choice is given")
        elif rec["overrode_taste"] != (umc != rec["chosen"]):
            errs.append("overrode_taste must equal (user_model_choice != chosen)")
    elif conf is not None:
        errs.append("user_model_confidence given without a user_model_choice")
    elif rec["overrode_taste"]:
        errs.append("overrode_taste is true but no user model was consulted")
    return errs


def code_version(cwd: Optional[str] = None) -> str:
    """Commit hash of the code on disk (with -dirty if modified), for every record."""
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=12"], capture_output=True,
                             text=True, timeout=10, cwd=cwd or os.path.dirname(os.path.abspath(__file__)))
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


class DecisionLog:
    """Collects the run's decision records; optionally persists them as JSONL
    and as shared-memory DECISION facts."""

    def __init__(self, run_id: str, arm: str, root: Optional[str] = None, shared=None,
                 version: Optional[str] = None):
        self.run_id, self.arm, self.shared = run_id, arm, shared
        self.version = version if version is not None else code_version()
        self.records: List[DecisionRecord] = []
        self.path = os.path.join(root, run_id, "decisions.jsonl") if root else None
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            open(self.path, "w").close()

    def add(self, iter: int, point: str, context: str, options: List[str], chosen: int,
            user_model_choice: Optional[int] = None, user_model_confidence: Optional[float] = None,
            evidence: Optional[Dict] = None) -> DecisionRecord:
        rec = DecisionRecord(
            run_id=self.run_id, iter=iter, point=point, context=context, options=[str(o) for o in options],
            chosen=chosen, user_model_choice=user_model_choice,
            user_model_confidence=None if user_model_choice is None else float(user_model_confidence or 0.0),
            evidence=dict(evidence or {}),
            overrode_taste=user_model_choice is not None and user_model_choice != chosen,
            arm=self.arm, code_version=self.version)
        errs = validate_record(rec.to_dict())
        if errs:
            raise ValueError(f"invalid {point} decision record: {errs}")
        self.records.append(rec)
        if self.path:
            with open(self.path, "a") as f:
                f.write(json.dumps(rec.to_dict(), default=str) + "\n")
        if self.shared:
            from ..integrations.shared_memory import format_fact
            self.shared.write("decider", format_fact(
                "DECISION", run=self.run_id, arm=self.arm or "none", iter=iter, point=point,
                chosen=rec.options[chosen][:80], taste=("none" if user_model_choice is None
                                                       else rec.options[user_model_choice][:80]),
                overrode=rec.overrode_taste))
        return rec

    def summary(self) -> dict:
        """Per decision point: how often the user model was consulted, and how
        often the loop's action departed from it."""
        out = {}
        for p in POINTS:
            rs = [r for r in self.records if r.point == p]
            consulted = [r for r in rs if r.user_model_choice is not None]
            out[p] = {"n": len(rs), "consulted": len(consulted),
                      "overrode_taste": sum(r.overrode_taste for r in consulted),
                      "agreement": (sum(not r.overrode_taste for r in consulted) / len(consulted))
                      if consulted else None}
        return out


def load_decisions(path: str, strict: bool = True) -> List[dict]:
    """Read a decisions.jsonl; with strict=True any invalid record raises."""
    out = []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            errs = validate_record(rec)
            if errs and strict:
                raise ValueError(f"{path}:{n}: {errs}")
            out.append(rec)
    return out
