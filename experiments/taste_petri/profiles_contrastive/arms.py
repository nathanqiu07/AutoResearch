"""Single entry point for the evaluator: get_profile_text(arm, context) -> the profile text to put
in the predictor's prompt. All arms are built from pre-T (< 2026-01-01) evidence only (README.md).

  P0     consensus placebo: the claims the blind gate called lopsided toward him, same format as P1
  P1     contrast card: claims that survived the gate, each with its generic default and quotes
  P2     axis card: 14 trade-off axes plus induced axes, one verified quote each
  P3     retrieval: his k most similar pre-T decisions to `context` (TF-IDF), as few-shot exemplars
  P4     decision-style vector (<=250 words) written only from P1 and P2
  P1+P3  P1 followed by P3

`context` matters only for the arms with P3; the others are fixed texts."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # so the evaluator can load this file by path from any directory
from retrieve import render, retrieve  # noqa: E402
ARMS = ("P0", "P1", "P2", "P3", "P4", "P1+P3")


def _card(name):
    with open(os.path.join(HERE, name + ".md")) as f:
        return f.read().strip()


def get_profile_text(arm, context="", k=5):
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}")
    parts = []
    for piece in arm.split("+"):
        parts.append(render(retrieve(context, k)) if piece == "P3" else _card(piece))
    return "\n\n".join(parts)
