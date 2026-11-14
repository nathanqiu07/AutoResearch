"""Taste extraction from unstructured text (papers, blogs, posts, and
non-research writing such as reviews or hobby forums).

With a real LLM, the model reads chunks and returns principles plus feature
weights. Offline, a transparent lexicon maps stance-bearing phrases to
features (e.g. "ablation", "simple baseline" -> simplicity; "in the wild",
"real users" -> realism). Non-research text is down-weighted because it is
weaker evidence about research decisions, but is often what reveals
dispositions like risk tolerance or cost-consciousness."""
from __future__ import annotations

import re
from typing import Iterable, List, Tuple

from ..llm import LLM, OfflineLLM, extract_json
from .profile import FEATURES, TasteProfile

LEXICON = {
    "realism": ["realistic", "real-world", "in the wild", "real users", "deployment", "naturalistic", "authentic"],
    "grounding": ["grounded", "empirical", "data", "measure", "logs", "evidence", "concrete"],
    "simplicity": ["simple", "minimal", "baseline", "ablation", "occam", "clean", "parsimon"],
    "novelty": ["novel", "creative", "unexplored", "surprising", "new direction", "weird"],
    "cost": ["cheap", "efficient", "budget", "compute", "fast", "frugal"],
    "risk": ["bold", "moonshot", "high-risk", "gamble", "ambitious", "risky bet"],
    "validity_care": ["validity", "confound", "faithful", "sanity check", "control", "careful", "rigor"],
}
NEGATORS = re.compile(r"\b(not|never|avoid|against|overrated|hate|dislike|skeptical of|instead of)\b")
# cost is a penalty feature: a preference for cheap work means a negative weight on cost.
INVERTED = {"cost"}


def _lexicon_weights(text: str):
    counts = {f: 0.0 for f in FEATURES}
    for sent in re.split(r"[.!?\n]+", text.lower()):
        neg = bool(NEGATORS.search(sent))
        for f, words in LEXICON.items():
            hits = sum(sent.count(w) for w in words)
            if hits:
                sign = -1.0 if neg else 1.0
                if f in INVERTED:
                    sign = -sign
                counts[f] += sign * hits
    norm = max(1.0, max(abs(v) for v in counts.values()))
    return {f: v / norm for f, v in counts.items()}


def _llm_extract(text: str, llm: LLM) -> Tuple[dict, List[str]]:
    out = extract_json(llm.complete(
        "Read the following writing by one person. Infer how they make research "
        "decisions. Return JSON {\"principles\": [<=6 short imperative rules], "
        f"\"weights\": {{one of {FEATURES} -> float in [-1,1]}}}}. 'cost' weight is "
        "negative if they prefer cheap/efficient work.\n\n" + text[:12000], temperature=0.0))
    if not out:
        return _lexicon_weights(text), []
    w = {f: float(out.get("weights", {}).get(f, 0.0)) for f in FEATURES}
    return w, list(out.get("principles", []))[:6]


def profile_from_texts(name: str, docs: Iterable[Tuple[str, str]], llm: LLM) -> TasteProfile:
    """docs: iterable of (kind, text) where kind is 'research' or 'other'."""
    acc = {f: 0.0 for f in FEATURES}
    total, principles, sources = 0.0, [], {}
    for kind, text in docs:
        weight = 1.0 if kind == "research" else 0.4
        if isinstance(llm, OfflineLLM):
            w, pr = _lexicon_weights(text), []
        else:
            w, pr = _llm_extract(text, llm)
        for f in FEATURES:
            acc[f] += weight * w[f]
        total += weight
        principles += [p for p in pr if p not in principles]
        sources[f"text:{kind}"] = sources.get(f"text:{kind}", 0) + weight
    weights = {f: (acc[f] / total if total else 0.0) for f in FEATURES}
    if not principles:
        top = sorted(weights.items(), key=lambda kv: -abs(kv[1]))[:4]
        principles = [("prefer " if v > 0 else "avoid ") + k.replace("_", " ") for k, v in top if v]
    return TasteProfile(name, weights, principles, sources)
