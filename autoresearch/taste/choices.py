"""Taste from structured choice data.

Each record is a pairwise decision the researcher actually made:
  {"a": {feature: value}, "b": {...}, "chosen": "a"|"b", "context": "..."}
We fit a Bradley-Terry / logistic model on feature differences with an L2
prior centred on a text-derived profile, so sparse choice data refines text
taste instead of overwriting it. `prediction_accuracy` is the taste-alignment
proxy metric: % of held-out decisions where the model picks what the person
picked."""
from __future__ import annotations

import json
import math
import random
from typing import Dict, List, Optional

from .profile import FEATURES, TasteProfile


def load_choices(path: str) -> List[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def _diff(c):
    return {k: c["a"].get(k, 0.0) - c["b"].get(k, 0.0) for k in FEATURES}


def fit_choice_model(choices: List[dict], name: str, prior: Optional[TasteProfile] = None,
                     l2: float = 0.5, lr: float = 0.2, epochs: int = 300) -> TasteProfile:
    center = prior.weights if prior else {f: 0.0 for f in FEATURES}
    w = dict(center)
    for _ in range(epochs):
        grad = {f: l2 * (w[f] - center.get(f, 0.0)) for f in FEATURES}
        for c in choices:
            d = _diff(c)
            y = 1.0 if c["chosen"] == "a" else 0.0
            z = sum(w[f] * d[f] for f in FEATURES)
            p = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
            for f in FEATURES:
                grad[f] += (p - y) * d[f] / max(1, len(choices))
        for f in FEATURES:
            w[f] -= lr * grad[f]
    principles = list(prior.principles) if prior else []
    sources = dict(prior.sources) if prior else {}
    sources["choices"] = float(len(choices))
    return TasteProfile(name, w, principles, sources)


def prediction_accuracy(profile: TasteProfile, choices: List[dict]) -> float:
    if not choices:
        return float("nan")
    hits = sum((profile.score(c["a"]) >= profile.score(c["b"])) == (c["chosen"] == "a")
               for c in choices)
    return hits / len(choices)


def split(choices: List[dict], frac: float = 0.7, seed: int = 0):
    c = list(choices)
    random.Random(seed).shuffle(c)
    k = int(len(c) * frac)
    return c[:k], c[k:]


def fit_choice_model_cv(choices: List[dict], name: str, prior: Optional[TasteProfile] = None,
                        l2_grid=(0.01, 0.1, 0.5, 2.0), folds: int = 4) -> TasteProfile:
    """Choose prior strength by k-fold CV, so text taste is trusted only as
    far as it predicts this person's actual decisions."""
    if prior is None or len(choices) < 2 * folds:
        return fit_choice_model(choices, name, prior)
    best_l2, best_acc = l2_grid[0], -1.0
    for l2 in l2_grid:
        accs = []
        for k in range(folds):
            test = choices[k::folds]
            train = [c for i, c in enumerate(choices) if i % folds != k]
            accs.append(prediction_accuracy(fit_choice_model(train, name, prior, l2=l2), test))
        acc = sum(accs) / folds
        if acc > best_acc:
            best_l2, best_acc = l2, acc
    prof = fit_choice_model(choices, name, prior, l2=best_l2)
    prof.sources["prior_l2"] = best_l2
    return prof
