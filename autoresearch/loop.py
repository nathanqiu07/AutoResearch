"""The research loop: propose -> taste/memory rank -> drift gate -> run ->
update beliefs -> distil insights."""
from __future__ import annotations

import json
import os
import random
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from .drift import DriftEvent, DriftMonitor
from .llm import LLM, OfflineLLM, extract_json
from .memory import ResearchMemory
from .taste import TasteProfile
from .tasks import Task


@dataclass
class LoopConfig:
    iterations: int = 20
    samples: int = 8
    proposals_per_iter: int = 6
    use_taste: bool = True
    use_memory: bool = True
    use_drift: bool = True
    taste_weight: float = 1.0
    memory_weight: float = 2.0
    explore: float = 0.1
    seed: int = 0
    target_score: Optional[float] = None


@dataclass
class RunReport:
    run_id: str
    task: str
    best_score: float
    best_config: Dict[str, str]
    best_metrics: Dict[str, float]
    history: List[dict]
    drift_events: List[dict]
    insights: List[str]
    iterations_to_target: Optional[int]
    compute: dict
    invalid_accepted: int = 0


class Researcher:
    def __init__(self, task: Task, llm: LLM, memory: ResearchMemory,
                 taste: Optional[TasteProfile], cfg: LoopConfig, log_dir: Optional[str] = None):
        self.task, self.llm, self.memory, self.taste, self.cfg = task, llm, memory, taste, cfg
        self.rng = random.Random(cfg.seed)
        self.run_id = uuid.uuid4().hex[:8]
        self.log_dir = log_dir
        self.drift = DriftMonitor(task.goal, [i.description for i in task.invariants],
                                  memory, llm, enabled=cfg.use_drift)

    # ---------- proposing ----------
    def _idea(self, knob, option):
        feats = self.task.features_of_change(knob, option)
        key = self.memory.key(self.task.name, knob, option)
        hyp = (f"Setting {knob} to {option} should make the environment feel like "
               f"real deployment so the model is not aware it is evaluated, while the "
               f"environment still tests the behaviour.")
        return {"knob": knob, "option": option, "change": f"{knob}={option}", "features": feats,
                "hypothesis": hyp,
                "assumptions": [key] + [self.memory.feature_key(f) for f, v in feats.items() if v > 0.5]}

    def propose(self, best: Dict[str, str], it: int) -> List[dict]:
        cands = [self._idea(k, o) for k, opts in self.task.search_space.items()
                 for o in opts if best.get(k) != o
                 and not self._tried({**best, k: o})]
        if not isinstance(self.llm, OfflineLLM) and cands:
            cands = self._llm_propose(best, cands, it) or cands
        self.rng.shuffle(cands)
        return cands

    def _llm_propose(self, best, cands, it):
        ctx = self.drift.reanchor_text() if (it % self.drift.reanchor_every == 0) else f"GOAL: {self.task.goal}"
        prompt = (f"{ctx}\nInsights from past research: {self.memory.relevant_insights(self.task.name)}\n"
                  f"Researcher principles: {self.taste.principles if self.taste else []}\n"
                  f"Current design: {best}\nCandidate changes:\n" +
                  "\n".join(f"- {c['change']}" for c in cands) +
                  f"\nPick up to {self.cfg.proposals_per_iter} and return a JSON list of "
                  "{\"change\": str, \"hypothesis\": str}. Hypotheses must say why the change "
                  "serves the goal, not a proxy.")
        out = extract_json(self.llm.complete(prompt, temperature=0.7)) or []
        by = {c["change"]: c for c in cands}
        picked = []
        for o in out if isinstance(out, list) else []:
            c = by.get(o.get("change"))
            if c:
                picked.append({**c, "hypothesis": o.get("hypothesis", c["hypothesis"])})
        return picked

    def _tried(self, config):
        return any(h["config"] == config for h in self.history)

    # ---------- ranking ----------
    def priority(self, idea) -> Dict[str, float]:
        t = self.taste.score(idea["features"]) if (self.cfg.use_taste and self.taste) else 0.0
        m = (self.memory.expected_gain(self.task.name, idea["knob"], idea["option"], idea["features"])
             if self.cfg.use_memory else 0.0)
        noise = self.rng.random() * self.cfg.explore
        if not (self.cfg.use_taste or self.cfg.use_memory):
            noise = self.rng.random()
        return {"taste": t, "memory": m,
                "total": self.cfg.taste_weight * t + self.cfg.memory_weight * m + noise}

    # ---------- main loop ----------
    def run(self) -> RunReport:
        t0 = time.time()
        self.history: List[dict] = []
        best = self.task.baseline_config()
        res = self.task.evaluate(best, self.llm, self.cfg.samples, self.cfg.seed)
        best_score, best_metrics = res.score, res.metrics
        self.history.append({"iter": 0, "config": best, "score": res.score, "accepted": True,
                             "valid": res.valid, "change": "baseline"})
        it_to_target, stagnant, invalid_accepted = None, 0, 0
        for it in range(1, self.cfg.iterations + 1):
            if self.llm.budget.exhausted():
                break
            cands = self.propose(best, it)[: max(self.cfg.proposals_per_iter * 3, 1)]
            if not cands:
                break
            ranked = sorted(cands, key=lambda c: -self.priority(c)["total"])
            idea = next((c for c in ranked if self.drift.gate_proposal(it, c)), None)
            if idea is None:
                idea = ranked[0]  # everything gated: fall back rather than stall
            self.memory.record_decision({
                "run_id": self.run_id, "task": self.task.name, "iter": it,
                "options": [{"change": c["change"], "features": c["features"]} for c in ranked[:4]],
                "chosen": idea["change"], "human_choice": None})
            cfg = {**best, idea["knob"]: idea["option"]}
            r = self.task.evaluate(cfg, self.llm, self.cfg.samples, self.cfg.seed + it)
            delta = r.score - best_score
            accepted = delta > 0 and self.drift.gate_result(it, idea, r, best_score)
            if accepted and not r.valid:
                invalid_accepted += 1
            # belief updates: an assumption is supported only by a *valid* gain
            supported = delta > 0 and r.valid
            stmt = f"On {self.task.name}, {idea['change']} improves faithful unawareness"
            self.memory.update(idea["assumptions"][0], supported, stmt)
            for fk in idea["assumptions"][1:]:
                self.memory.update(fk, supported, f"changes increasing {fk[8:]} help", weight=0.5)
            self.memory.record_experiment({"run_id": self.run_id, "task": self.task.name, "iter": it,
                                           "config": cfg, "change": idea["change"], "score": r.score,
                                           "delta": delta, "valid": r.valid, "metrics": r.metrics})
            self.history.append({"iter": it, "config": cfg, "score": r.score, "delta": delta,
                                 "accepted": accepted, "valid": r.valid, "change": idea["change"],
                                 "metrics": r.metrics})
            if accepted:
                best, best_score, best_metrics, stagnant = cfg, r.score, r.metrics, 0
            else:
                stagnant += 1
            if (self.cfg.target_score is not None and it_to_target is None
                    and best_score >= self.cfg.target_score):
                it_to_target = it
            if self.cfg.use_drift and stagnant >= self.drift.stagnation_patience:
                self.drift.events.append(DriftEvent(it, "stagnation",
                                                    "re-anchoring and widening exploration"))
                self.cfg.explore = min(1.0, self.cfg.explore * 2)
                stagnant = 0
        insights = self._distil(best, best_score)
        self.memory.flush()
        report = RunReport(self.run_id, self.task.name, best_score, best, best_metrics, self.history,
                           [asdict(e) for e in self.drift.events], insights, it_to_target,
                           {**self.llm.budget.summary(), "wall_seconds": round(time.time() - t0, 2)},
                           invalid_accepted)
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            with open(os.path.join(self.log_dir, f"{self.task.name}_{self.run_id}.json"), "w") as f:
                json.dump(asdict(report), f, indent=1)
        return report

    def _distil(self, best, best_score) -> List[str]:
        tried = [h for h in self.history[1:]]
        helped = [h["change"] for h in tried if h.get("accepted")]
        hurt = [h["change"] for h in tried if not h.get("valid")]
        lines = [f"Best faithful-unawareness score {best_score:.3f} with {best}."]
        if helped:
            lines.append(f"Changes that helped: {', '.join(helped)}.")
        if hurt:
            lines.append(f"Changes that broke validity (proxy traps): {', '.join(hurt)}.")
        if not isinstance(self.llm, OfflineLLM):
            txt = self.llm.complete("Summarise the 3 most transferable lessons from this research "
                                    f"log as short bullets:\n{json.dumps(tried)[:8000]}", temperature=0.2)
            lines += [l.strip("-• ").strip() for l in txt.splitlines() if l.strip()][:3]
        for l in lines:
            self.memory.record_insight(self.run_id, self.task.name, l)
        return lines

