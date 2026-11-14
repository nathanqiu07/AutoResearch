"""A taste profile = natural-language principles + weights over idea features.

Features are a small shared vocabulary so that taste learned from free text,
from non-research life data, and from structured choices can be combined and
compared on equal footing, and so predictions are inspectable."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List

FEATURES = ["realism", "grounding", "simplicity", "novelty", "cost", "risk", "validity_care"]


@dataclass
class TasteProfile:
    researcher: str
    weights: Dict[str, float] = field(default_factory=lambda: {f: 0.0 for f in FEATURES})
    principles: List[str] = field(default_factory=list)
    sources: Dict[str, float] = field(default_factory=dict)  # source -> evidence weight

    def score(self, features: Dict[str, float]) -> float:
        return sum(self.weights.get(k, 0.0) * v for k, v in features.items())

    def prefers(self, a: Dict[str, float], b: Dict[str, float]) -> bool:
        return self.score(a) >= self.score(b)

    @staticmethod
    def blend(profiles: List["TasteProfile"], mix: List[float], name: str) -> "TasteProfile":
        tot = sum(mix) or 1.0
        w = {f: sum(p.weights.get(f, 0) * m for p, m in zip(profiles, mix)) / tot for f in FEATURES}
        pr, src = [], {}
        for p, m in zip(profiles, mix):
            pr += [x for x in p.principles if x not in pr]
            for k, v in p.sources.items():
                src[k] = src.get(k, 0) + v * m / tot
        return TasteProfile(name, w, pr, src)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d) -> "TasteProfile":
        return cls(d["researcher"], d.get("weights", {}), d.get("principles", []), d.get("sources", {}))
