"""Claim checker for the write-up (D6, PLAN 7.2 / 12.4 item 6).

Every claim the report makes must cite finding ids from the run's log. The
checker re-derives each cited finding's delta, CI and status and rejects any
claim the logged evidence does not support. Only claims that pass go into the
write-up, and the pass rate is reported (E4b).

A claim is a dict:
  {"text": str, "kind": one of KINDS, "finding_ids": [str], "delta": optional number,
   "p_better": optional number}
A stated delta must match the cited finding's logged delta, or for several
findings the mean of their deltas, to within DELTA_TOL.

Kinds, relative to the finding's move (adding or removing an intervention):
  improves          every cited finding was validated (accepted, then confirmed on fresh samples), delta > 0
  hurts             every cited finding is clearly worse: delta < 0 and P(better) <= HURTS_P
  no_clear_effect   every cited finding was tested and neither validated nor clearly worse
  breaks_validity   every cited finding lowered awareness but broke the probe (status "invalid")
  drifted           every cited finding's environment left the fixed setting
  transfers         every cited finding has a held-out result with a positive delta and
                    held-out P(better) >= TRANSFER_P (none exist until the held-out evaluation)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

KINDS = ["improves", "hurts", "no_clear_effect", "breaks_validity", "drifted", "transfers"]
HURTS_P = 0.2
TRANSFER_P = 0.75
DELTA_TOL = 0.005      # a stated delta must match the logged one to this absolute tolerance
P_TOL = 0.01


@dataclass
class ClaimCheck:
    claim: dict
    supported: bool
    reasons: List[str] = field(default_factory=list)
    derived: List[dict] = field(default_factory=list)   # the cited findings' logged numbers

    def to_dict(self):
        return asdict(self)


def _derived(f: dict) -> dict:
    return {k: f.get(k) for k in ("id", "move", "category", "status", "delta", "ci90", "p_better", "validity",
                                  "heldout_delta", "heldout_p_better")}


def _supports(kind: str, f: dict) -> Optional[str]:
    """None if finding f supports a claim of this kind, else the reason it does not."""
    st, d, p = f.get("status"), f.get("delta"), f.get("p_better")
    if kind == "improves":
        if st != "validated":
            return f"{f['id']} has status {st!r}, not 'validated'"
        if not (isinstance(d, (int, float)) and d > 0):
            return f"{f['id']} delta {d} is not positive"
    elif kind == "hurts":
        if not (isinstance(d, (int, float)) and d < 0 and isinstance(p, (int, float)) and p <= HURTS_P):
            return f"{f['id']} is not clearly worse (delta {d}, P(better) {p}; needs delta < 0 and P <= {HURTS_P})"
    elif kind == "no_clear_effect":
        if st in ("validated", "invalid", "drifted"):
            return f"{f['id']} has status {st!r}, which is a clear outcome"
        if isinstance(p, (int, float)) and p <= HURTS_P:
            return f"{f['id']} is clearly worse (P(better) {p})"
    elif kind == "breaks_validity":
        if st != "invalid":
            return f"{f['id']} has status {st!r}, not 'invalid'"
    elif kind == "drifted":
        if st != "drifted":
            return f"{f['id']} has status {st!r}, not 'drifted'"
    elif kind == "transfers":
        hd, hp = f.get("heldout_delta"), f.get("heldout_p_better")
        if not (isinstance(hd, (int, float)) and hd > 0 and isinstance(hp, (int, float)) and hp >= TRANSFER_P):
            return f"{f['id']} has no positive held-out result (held-out delta {hd}, P {hp})"
    return None


def check_claim(claim: dict, findings: List[dict]) -> ClaimCheck:
    by_id: Dict[str, dict] = {f["id"]: f for f in findings if "id" in f}
    reasons: List[str] = []
    kind = claim.get("kind")
    ids = claim.get("finding_ids")
    if not str(claim.get("text", "")).strip():
        reasons.append("claim has no text")
    if kind not in KINDS:
        reasons.append(f"kind {kind!r} not in {KINDS}")
    if not isinstance(ids, list) or not ids:
        reasons.append("claim cites no finding ids")
        ids = []
    cited = []
    for i in ids:
        f = by_id.get(str(i))
        if f is None:
            reasons.append(f"cites unknown finding {i!r}")
        else:
            cited.append(f)
    if kind in KINDS:
        for f in cited:
            why = _supports(kind, f)
            if why:
                reasons.append(why)
    stated = claim.get("delta")
    if stated is not None and cited:
        try:
            s = float(stated)
        except (TypeError, ValueError):
            reasons.append(f"stated delta {stated!r} is not a number")
        else:
            logged = [f["delta"] for f in cited]
            target = logged[0] if len(logged) == 1 else sum(logged) / len(logged)
            if abs(s - target) > DELTA_TOL:
                reasons.append(f"stated delta {s:+.4f} does not match the logged {target:+.4f}")
    stated_p = claim.get("p_better")
    if stated_p is not None and len(cited) == 1:
        try:
            if abs(float(stated_p) - cited[0]["p_better"]) > P_TOL:
                reasons.append(f"stated P(better) {stated_p} does not match the logged {cited[0]['p_better']:.3f}")
        except (TypeError, ValueError):
            reasons.append(f"stated P(better) {stated_p!r} is not a number")
    return ClaimCheck(claim, not reasons, reasons, [_derived(f) for f in cited])


def kind_of(f: dict) -> str:
    """The claim kind a finding supports on its own."""
    st = f.get("status")
    if st == "validated" and f.get("delta", 0) > 0:
        return "improves"
    if st == "invalid":
        return "breaks_validity"
    if st == "drifted":
        return "drifted"
    if f.get("delta", 0) < 0 and f.get("p_better", 1) <= HURTS_P:
        return "hurts"
    return "no_clear_effect"


def candidate_claims(findings: List[dict]) -> List[dict]:
    """Claims derived mechanically from the findings, one per finding (used
    offline and when the proposer drafts nothing usable)."""
    out = []
    for f in findings:
        verb = "Adding" if f["move"].startswith("add") else "Removing"
        k = kind_of(f)
        phrase = {"improves": "improves faithful unawareness", "hurts": "makes the score clearly worse",
                  "no_clear_effect": "has no clear effect", "breaks_validity": "lowers awareness but breaks the probe",
                  "drifted": "drifted out of the fixed setting"}[k]
        out.append({"text": f"{verb} [{f['category']}] {f['text'][:100]} {phrase} "
                            f"(delta {f['delta']:+.3f}, P(better) {f['p_better']:.2f}).",
                    "kind": k, "finding_ids": [f["id"]], "delta": round(f["delta"], 4)})
    return out


def check_all(claims: List[dict], findings: List[dict]) -> dict:
    checks = [check_claim(c, findings) for c in claims]
    n = len(checks)
    return {"n": n, "supported": sum(c.supported for c in checks),
            "pass_rate": (sum(c.supported for c in checks) / n) if n else None,
            "checks": [c.to_dict() for c in checks]}
