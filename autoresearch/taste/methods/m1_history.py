import random
from dataclasses import asdict

from ..usermodel import UserModel


class RawHistory(UserModel):
    method_id = "m1"

    def __init__(self, llm, k="all", **kwargs):
        if k != "all" and k not in (5, 10, 20):
            raise ValueError("k must be 5, 10, 20 or 'all'")
        super().__init__(llm, k=k, **kwargs)

    def fit(self, history, val):
        super().fit(history, val)
        ordered = sorted(history, key=lambda c: c.identity)
        k = self.config["k"]
        selected = ordered if k == "all" else random.Random(self.seed).sample(ordered, min(k, len(ordered)))
        self._artifacts.exemplars = [asdict(c) for c in selected]
