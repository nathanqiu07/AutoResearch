"""Standard-library TF-IDF and cosine similarity, shared by real_distractors (topical match of a
held-out project and a candidate distractor) and active_queries (the diversity term of the label
queue). Vectors are sparse dicts, L2-normalised, so a cosine is a dot product."""
from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List

Vector = Dict[str, float]

TOKEN = re.compile(r"[a-z][a-z0-9]+")
# A short list: TF-IDF already down-weights common words; these carry no topic at any frequency.
STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having
he her here hers him his how i if in into is it its itself just me more most my no nor not now of off on
once only or other our ours out over own same she should so some such than that the their theirs them
then there these they this those through to too under until up very was we were what when where which
while who whom why will with would you your yours via using use used based new paper post we our study
""".split())


def tokens(text: str) -> List[str]:
    return [t for t in TOKEN.findall(str(text).lower()) if t not in STOPWORDS]


class TfIdf:
    """IDF fitted on one collection; `vector` maps any text into that space."""

    def __init__(self, docs: Iterable[str] = ()):
        self.n, self.df = 0, {}
        self.fit(docs)

    def fit(self, docs: Iterable[str]) -> "TfIdf":
        for d in docs:
            self.n += 1
            for t in set(tokens(d)):
                self.df[t] = self.df.get(t, 0) + 1
        return self

    def idf(self, term: str) -> float:
        # Smoothed, so an unseen term is weighted like a term in no document, never infinite.
        return math.log((1 + self.n) / (1 + self.df.get(term, 0))) + 1.0

    def vector(self, text: str) -> Vector:
        tf: Dict[str, int] = {}
        for t in tokens(text):
            tf[t] = tf.get(t, 0) + 1
        v = {t: (1 + math.log(c)) * self.idf(t) for t, c in tf.items()}
        return normalise(v)


def normalise(v: Vector) -> Vector:
    norm = math.sqrt(sum(x * x for x in v.values()))
    return {k: x / norm for k, x in v.items()} if norm else {}


def cosine(u: Vector, v: Vector) -> float:
    """Dot product of two normalised vectors (0 when either is empty)."""
    if len(u) > len(v):
        u, v = v, u
    return sum(x * v.get(k, 0.0) for k, x in u.items())


def top_shared_terms(u: Vector, v: Vector, k: int = 6) -> List[str]:
    """The terms that contribute most to cos(u, v), highest first."""
    shared = sorted(((u[t] * v[t], t) for t in set(u) & set(v)), reverse=True)
    return [t for _, t in shared[:k]]
