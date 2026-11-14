"""TasteAdvisor: how a user model acts inside the research loop (PLAN 7.2).

The advisor wraps a user model (WS A's `UserModel` interface, PLAN 12.6) and
applies one policy at every decision point:

  * D1: a candidate's taste score is the user model's P(choose this candidate).
    The loop multiplies it by the learned taste weight (`Calibration.weight`),
    so taste that does not predict realised gains loses influence.
  * D2-D4: the statistics decide whenever they are decisive. The user model's
    choice is the default only where the evidence is inconclusive. When the
    action differs from the user model's choice the decision record says so
    (`overrode_taste`), which is the disagreement record.
  * D5-D6: the user model picks among interpretations; claims must still pass
    the claim checker (`claims.py`).
  * A prediction below `min_confidence` falls back to R0 behaviour.

The advisor never sees or changes the acceptance thresholds, so taste cannot
relax the evidence bar.

Two kinds of user model are accepted (duck-typed):
  * text models: `predict(context, options: List[str]) -> Prediction` with
    `.choice` (WS A uses "a", "b", ... in option order; an index, digit string
    or option text also work), `.confidence`, and optionally `.rationale` and
    `.probabilities` (one per option, used at D1 when present);
  * `ProfileUserModel`, an adapter over the existing feature-weight
    `TasteProfile`: it predicts D1 from intervention features and abstains on
    text-only decisions, so those fall back to R0.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..taste.profile import TasteProfile


@dataclass
class Advice:
    choice: Optional[int]       # index into the options, None if the model abstained or gave nothing usable
    confidence: float
    rationale: str = ""
    usable: bool = False        # confident enough to act on
    probabilities: Optional[List[float]] = None   # P(each option), when the model gives a distribution


@dataclass
class _Prediction:
    choice: object
    confidence: float
    rationale: str = ""


def choice_index(choice, options: Sequence[str]) -> Optional[int]:
    """Map a user model's `choice` onto an option index. Accepts an int index,
    a digit string, a letter ("a" = first), or the option text itself."""
    k = len(options)
    if isinstance(choice, bool) or choice is None:
        return None
    if isinstance(choice, int):
        return choice if 0 <= choice < k else None
    s = str(choice).strip()
    if s.isdigit():
        i = int(s)
        return i if 0 <= i < k else None
    if len(s) == 1 and s.isalpha():
        i = ord(s.lower()) - ord("a")
        return i if 0 <= i < k else None
    low = [o.strip().lower() for o in options]
    if s.lower() in low:
        return low.index(s.lower())
    return None


class ProfileUserModel:
    """Adapter: a feature-weight TasteProfile as a user model. It only has
    preferences over intervention features, so it answers D1 and abstains
    (confidence 0) on text-only decisions."""

    def __init__(self, profile: TasteProfile, temperature: float = 1.0):
        self.profile, self.temperature = profile, temperature

    def predict_features(self, context: str, features: List[Dict[str, float]]) -> List[float]:
        """P(choose each option): a softmax over profile scores (Bradley-Terry)."""
        zs = [self.profile.score(f) / self.temperature for f in features]
        m = max(zs) if zs else 0.0
        es = [math.exp(z - m) for z in zs]
        tot = sum(es) or 1.0
        return [e / tot for e in es]

    def predict(self, context: str, options: List[str]) -> _Prediction:
        return _Prediction(None, 0.0, "feature-weight profile has no preference over text-only options")

    def principles(self) -> List[str]:
        return list(self.profile.principles)


class TasteAdvisor:
    def __init__(self, user_model, min_confidence: float = 0.6, source: str = ""):
        self.um, self.min_conf, self.source = user_model, min_confidence, source
        self.errors: List[str] = []

    # ---------- consulting the user model ----------
    def consult(self, context: str, options: List[str]) -> Advice:
        try:
            pred = self.um.predict(context, list(options))
        except Exception as e:   # a failing user model must not stop the run; it is logged and ignored
            self.errors.append(f"predict failed: {str(e)[:200]}")
            return Advice(None, 0.0)
        idx = choice_index(getattr(pred, "choice", None), options)
        conf = _prob(getattr(pred, "confidence", 0.0))
        rationale = str(getattr(pred, "rationale", ""))
        if idx is None:
            return Advice(None, 0.0, rationale)
        return Advice(idx, conf, rationale, conf >= self.min_conf, _distribution(pred, len(options)))

    def decide(self, context: str, options: List[str], default: int, decisive: bool) -> Tuple[int, Advice]:
        """The loop's action at D2-D5. `default` is the R0 action. If the
        evidence is decisive, the statistics decide (the default stands).
        Otherwise a confident user-model choice is taken; a low-confidence one
        falls back to the default."""
        adv = self.consult(context, options)
        if decisive or not adv.usable or adv.choice is None:
            return default, adv
        return adv.choice, adv

    def d1_scores(self, context: str, texts: List[str], features: List[Dict[str, float]]) -> Tuple[List[float], Advice]:
        """P(the researcher would pick each candidate next). Uniform when the
        model abstains or is not confident, which leaves the ranking to memory
        and novelty (R0 behaviour)."""
        k = len(texts)
        if k == 0:
            return [], Advice(None, 0.0)
        uniform = [1.0 / k] * k
        if hasattr(self.um, "predict_features"):
            try:
                ps = [float(p) for p in self.um.predict_features(context, features)]
            except Exception as e:
                self.errors.append(f"predict_features failed: {str(e)[:200]}")
                return uniform, Advice(None, 0.0)
            if len(ps) != k:
                self.errors.append(f"predict_features returned {len(ps)} scores for {k} options")
                return uniform, Advice(None, 0.0)
            top = max(range(k), key=lambda i: ps[i])
            # confidence of a k-way softmax pick, rescaled so a uniform distribution is 0 and certainty is 1
            conf = (ps[top] - 1.0 / k) / (1.0 - 1.0 / k) if k > 1 else 1.0
            adv = Advice(top, _prob(conf), "feature-weight profile", True)
            return ps, adv
        adv = self.consult(context, texts)
        if adv.choice is None or not adv.usable:
            return uniform, adv
        if adv.probabilities:
            return list(adv.probabilities), adv
        rest = (1.0 - adv.confidence) / (k - 1) if k > 1 else 0.0
        return [adv.confidence if i == adv.choice else rest for i in range(k)], adv

    # ---------- what the proposer is told ----------
    def principles(self) -> List[str]:
        if hasattr(self.um, "principles"):
            try:
                return list(self.um.principles())
            except Exception:
                pass
        arts = None
        if hasattr(self.um, "artifacts"):
            try:
                arts = self.um.artifacts()
            except Exception as e:
                self.errors.append(f"artifacts failed: {str(e)[:200]}")
        pr = getattr(arts, "principles", None) if arts is not None else None
        if pr is None and isinstance(arts, dict):
            pr = arts.get("principles")
        return [str(p) for p in pr] if pr else []


def _distribution(pred, k: int) -> Optional[List[float]]:
    """The prediction's per-option probabilities, if it gives a valid one."""
    ps = getattr(pred, "probabilities", None)
    if not isinstance(ps, (list, tuple)) or len(ps) != k:
        return None
    try:
        ps = [float(p) for p in ps]
    except (TypeError, ValueError):
        return None
    if any(p < 0 or p != p for p in ps) or abs(sum(ps) - 1.0) > 1e-3:
        return None
    return ps


def _prob(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(v) else max(0.0, min(1.0, v))


def load_user_model(researcher_root: str, profile: Optional[TasteProfile], llm=None):
    """The researcher's user model and where it came from.

    WS B writes `data/researchers/<slug>/usermodel.json` with WS A's selected
    method; it is loaded with WS A's `taste.usermodel.load_model(path, llm)`,
    where `llm` is the backend the user model predicts with. Without that file
    the cached feature-weight profile is wrapped in `ProfileUserModel`, which
    only informs D1."""
    path = os.path.join(researcher_root, "usermodel.json")
    if os.path.exists(path):
        if llm is None:
            raise ValueError(f"{path} needs an LLM backend for the user model to predict with")
        from ..taste.usermodel import load_model  # WS A's loader
        model = load_model(path, llm)
        return model, f"usermodel.json ({os.path.basename(researcher_root)}, method {model.method_id})"
    if profile is None:
        return None, "none"
    return ProfileUserModel(profile), f"profile.json feature weights ({profile.researcher}); D1 only"


def history_text(researcher_root: str, max_chars: int = 8000) -> str:
    """Raw history for the prompt-baseline arms (R1-P-prompt / R1-S-prompt):
    the researcher's recorded choices and documents, pasted verbatim (truncated)
    with no user model in between."""
    parts: List[str] = []
    cp = os.path.join(researcher_root, "choices.jsonl")
    if os.path.exists(cp):
        with open(cp) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        lines = []
        for r in rows:
            a, b = r.get("a_text") or r.get("a"), r.get("b_text") or r.get("b")
            lines.append(f"- context: {r.get('context', '')}; option a: {json.dumps(a)}; option b: {json.dumps(b)}; "
                         f"chose {r.get('chosen')}" + (f"; reason: {r['reason']}" if r.get("reason") else ""))
        parts.append("Past choices:\n" + "\n".join(lines))
    cdir = os.path.join(researcher_root, "corpus")
    if os.path.isdir(cdir):
        for name in sorted(os.listdir(cdir)):
            if name.endswith(".txt"):
                with open(os.path.join(cdir, name)) as f:
                    parts.append(f"Document {name}:\n{f.read()}")
    text = "\n\n".join(parts)
    return text[:max_chars] + ("\n[... truncated]" if len(text) > max_chars else "")
