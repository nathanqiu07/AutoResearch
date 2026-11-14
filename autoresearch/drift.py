"""Drift control.

Long autonomous runs drift when the loop (a) starts optimising a proxy that
no longer tracks the goal, (b) acts on assumptions that are false, or (c)
wanders to ideas unrelated to the anchor goal. The monitor guards each:

  * proposal gate  - rejects ideas relying on assumptions that memory has
                     refuted with enough evidence, and ideas whose rationale is
                     off-goal (lexical relevance offline; LLM judge online);
  * result gate    - an improvement that violates a task invariant is logged
                     as proxy gaming and never becomes the new best;
  * re-anchoring   - every `reanchor_every` iterations the goal, invariants,
                     and validated/refuted assumptions are re-stated to the
                     proposer, and stagnation triggers a strategy reset.
Every event is logged so drift rate is a measurable secondary metric."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .llm import LLM, OfflineLLM, extract_json
from .memory import ResearchMemory

_STOP = set("the a an of to and in is it that this for with be on while so as are".split())


def _toks(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in _STOP and len(w) > 2}


@dataclass
class DriftEvent:
    iteration: int
    kind: str
    detail: str


@dataclass
class DriftMonitor:
    goal: str
    invariants: List[str]
    memory: ResearchMemory
    llm: LLM
    refute_threshold: float = 0.3
    min_evidence: float = 2.0
    min_relevance: float = 0.05
    reanchor_every: int = 5
    stagnation_patience: int = 4
    enabled: bool = True
    events: List[DriftEvent] = field(default_factory=list)

    def relevance(self, text: str) -> float:
        if not isinstance(self.llm, OfflineLLM):
            out = extract_json(self.llm.complete(
                f"Goal: {self.goal}\nProposed idea: {text}\nReturn JSON {{\"relevance\": 0-1}} "
                "for how directly this idea advances the goal (not a proxy of it).",
                temperature=0.0, max_tokens=50)) or {}
            return float(out.get("relevance", 0.5))
        g, t = _toks(self.goal), _toks(text)
        return len(g & t) / max(1, len(t))

    def gate_proposal(self, it: int, idea: dict) -> bool:
        if not self.enabled:
            return True
        for key in idea.get("assumptions", []):
            if (self.memory.evidence(key) >= self.min_evidence
                    and self.memory.credence(key) < self.refute_threshold):
                self.events.append(DriftEvent(it, "refuted_assumption",
                                              f"{idea['change']} relies on refuted '{key}'"))
                return False
        rel = self.relevance(idea.get("hypothesis", ""))
        if rel < self.min_relevance:
            self.events.append(DriftEvent(it, "off_goal", f"{idea['change']} relevance={rel:.2f}"))
            return False
        return True

    def gate_result(self, it: int, idea: dict, result, best_score: float) -> bool:
        """Return True if the result may be accepted as progress."""
        if result.valid:
            return True
        if result.score > best_score:
            self.events.append(DriftEvent(it, "proxy_gaming",
                                          f"{idea['change']} improved score but violated {result.violations}"))
        return not self.enabled  # without the monitor, invalid gains slip through

    def reanchor_text(self) -> str:
        good = sorted(((k, v) for k, v in self.memory.assumptions.items()
                       if self.memory.evidence(k) >= self.min_evidence), key=lambda kv: -self.memory.credence(kv[0]))
        val = [k for k, _ in good if self.memory.credence(k) > 0.7][:8]
        ref = [k for k, _ in good if self.memory.credence(k) < self.refute_threshold][:8]
        return (f"GOAL (re-anchored): {self.goal}\nINVARIANTS: {self.invariants}\n"
                f"VALIDATED: {val}\nREFUTED (do not rely on): {ref}")
