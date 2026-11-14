"""Selectable researcher identities.

data/researchers/<slug>/
    corpus/research__*.txt   papers, blogs, research posts
    corpus/other__*.txt      non-research writing (reviews, hobbies, posts)
    choices.jsonl            structured pairwise decisions
    profile.json             cached fitted profile (written by `taste build`)
"""
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from typing import List, Optional

from ..llm import LLM
from .choices import fit_choice_model, load_choices, prediction_accuracy, split
from .extract import profile_from_texts
from .profile import TasteProfile

DEFAULT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "researchers")


@dataclass
class Researcher:
    slug: str
    root: str

    def docs(self):
        for p in sorted(glob.glob(os.path.join(self.root, "corpus", "*.txt"))):
            kind = "other" if os.path.basename(p).startswith("other__") else "research"
            yield kind, open(p).read()

    def choices(self) -> List[dict]:
        p = os.path.join(self.root, "choices.jsonl")
        return load_choices(p) if os.path.exists(p) else []

    def build_profile(self, llm: LLM, use_text=True, use_other=True, use_choices=True,
                      holdout: float = 0.3, seed: int = 0):
        docs = [(k, t) for k, t in self.docs() if (k == "research" and use_text) or (k == "other" and use_other)]
        prior = profile_from_texts(self.slug, docs, llm) if docs else None
        train, test = split(self.choices(), 1 - holdout, seed) if holdout else (self.choices(), [])
        if use_choices and train:
            prof = fit_choice_model(train, self.slug, prior)
        else:
            prof = prior or TasteProfile(self.slug)
        return prof, test

    def save_profile(self, prof: TasteProfile):
        with open(os.path.join(self.root, "profile.json"), "w") as f:
            f.write(prof.to_json())

    def cached_profile(self) -> Optional[TasteProfile]:
        p = os.path.join(self.root, "profile.json")
        return TasteProfile.from_dict(json.load(open(p))) if os.path.exists(p) else None

    def ablation_report(self, llm: LLM, seeds=(0, 1, 2)) -> dict:
        """Taste-prediction accuracy of each source combination on held-out choices."""
        combos = {"text_only": (1, 0, 0), "other_only": (0, 1, 0), "text+other": (1, 1, 0),
                  "choices_only": (0, 0, 1), "all": (1, 1, 1)}
        out = {}
        for name, (t, o, c) in combos.items():
            accs = []
            for s in seeds:
                prof, test = self.build_profile(llm, bool(t), bool(o), bool(c), seed=s)
                if test:
                    accs.append(prediction_accuracy(prof, test))
            out[name] = round(sum(accs) / len(accs), 3) if accs else None
        return out


def list_researchers(root: str = DEFAULT_ROOT) -> List[str]:
    return sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))) if os.path.isdir(root) else []


def load_researcher(slug: str, root: str = DEFAULT_ROOT) -> Researcher:
    path = os.path.join(root, slug)
    if not os.path.isdir(path):
        raise KeyError(f"researcher {slug!r} not found; available: {list_researchers(root)}")
    return Researcher(slug, os.path.abspath(path))
