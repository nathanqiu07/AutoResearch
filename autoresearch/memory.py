"""Persistent research memory: the system's historical research experience.

Stores, across runs and tasks:
  * experiments  - every config tried, its score and delta,
  * assumptions  - claims the system relied on, each with a Beta credence
                   updated by outcomes (this is what lets later runs know
                   which assumptions turned out to be *correct*),
  * insights     - distilled lessons written at the end of a run,
  * decisions    - choices the system made, so a human can later label what
                   they would have chosen (feeding taste-prediction accuracy
                   and new structured choice data).
Assumptions are tracked at two levels: concrete ("context_length=long_padded
helps on eval_awareness") and feature-level ("realism-increasing changes help"),
the latter transferring across tasks."""
from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional


class ResearchMemory:
    def __init__(self, root: Optional[str]):
        self.root = root
        self.experiments: List[dict] = []
        self.assumptions: Dict[str, dict] = {}
        self.insights: List[dict] = []
        self.decisions: List[dict] = []
        if root:
            os.makedirs(root, exist_ok=True)
            self.experiments = self._load_jsonl("experiments.jsonl")
            self.insights = self._load_jsonl("insights.jsonl")
            self.decisions = self._load_jsonl("decisions.jsonl")
            p = os.path.join(root, "assumptions.json")
            if os.path.exists(p):
                self.assumptions = json.load(open(p))

    # ---------- persistence ----------
    def _load_jsonl(self, name):
        p = os.path.join(self.root, name)
        return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []

    def _append(self, name, rec):
        if self.root:
            with open(os.path.join(self.root, name), "a") as f:
                f.write(json.dumps(rec) + "\n")

    def flush(self):
        if self.root:
            with open(os.path.join(self.root, "assumptions.json"), "w") as f:
                json.dump(self.assumptions, f, indent=1)

    # ---------- assumptions ----------
    @staticmethod
    def key(task: str, knob: str, option: str) -> str:
        return f"{task}:{knob}={option}"

    @staticmethod
    def feature_key(feature: str) -> str:
        return f"feature:{feature}"

    def _get(self, key, statement=""):
        return self.assumptions.setdefault(key, {"statement": statement, "alpha": 1.0, "beta": 1.0})

    def credence(self, key: str) -> float:
        a = self.assumptions.get(key)
        return a["alpha"] / (a["alpha"] + a["beta"]) if a else 0.5

    def evidence(self, key: str) -> float:
        a = self.assumptions.get(key)
        return a["alpha"] + a["beta"] - 2 if a else 0.0

    def update(self, key: str, supported: bool, statement: str = "", weight: float = 1.0):
        a = self._get(key, statement)
        if statement and not a["statement"]:
            a["statement"] = statement
        a["alpha" if supported else "beta"] += weight

    def expected_gain(self, task, knob, option, features: Dict[str, float]) -> float:
        """Memory's prior on whether a change helps, in [-0.5, 0.5]."""
        k = self.key(task, knob, option)
        if self.evidence(k) > 0:
            return self.credence(k) - 0.5
        num = den = 0.0
        for f, v in features.items():
            fk = self.feature_key(f)
            if self.evidence(fk) > 0 and v:
                num += (self.credence(fk) - 0.5) * v
                den += abs(v)
        return num / den if den else 0.0

    # ---------- records ----------
    def record_experiment(self, rec: dict):
        rec = {"t": time.time(), **rec}
        self.experiments.append(rec)
        self._append("experiments.jsonl", rec)

    def record_decision(self, rec: dict):
        self.decisions.append(rec)
        self._append("decisions.jsonl", rec)

    def record_insight(self, run_id: str, task: str, text: str):
        rec = {"run_id": run_id, "task": task, "text": text}
        self.insights.append(rec)
        self._append("insights.jsonl", rec)

    def relevant_insights(self, task: str, k: int = 8) -> List[str]:
        same = [i["text"] for i in self.insights if i["task"] == task]
        other = [i["text"] for i in self.insights if i["task"] != task]
        return (same[-k:] + other[-k:])[:k]

    def tried(self, task: str, config: dict) -> bool:
        return any(e["task"] == task and e["config"] == config for e in self.experiments)
