"""Source-to-decision trail: from an Exa page to what the loop did because of it.

    python3 -m autoresearch.integrations.trail RUN_DIR [--memory shared.jsonl ...]
        [--decisions decisions.jsonl ...] [--html out.html] [--md out.md] [--json]

For every critic veto, and every credence update from a web fact-check, in the
runs found under RUN_DIR, this rebuilds the chain

    Exa source (URL, publish date, used_for)
      -> EVIDENCE fact (stance, confidence, URLs)                  [shared memory]
      -> veto / credence change (which experiment, which assumption)
      -> what ran instead, its OUTCOME fact and decision record
         (and what the vetoed change did wherever else it was tested)

It reads only what the run recorded: run reports (`<task>_<run>.json`), the
shared-memory JSONL (past.dev's local fallback), decision logs and
`assumptions.json`. Steps are joined on recorded keys (run id, change, URL,
iteration, delta). A step that cannot be joined from recorded data is marked
MISSING with the field that would have linked it; nothing is inferred beyond
what the loop's own code fixes (for example the credence weight
0.5 x confidence in `loop.Researcher._critic_allows`, labelled as a rule).

Two loops write different artifacts:
  v1 (`autoresearch/loop.py`): the scout fact-checks each candidate and writes
     EVIDENCE; the critic vetoes confidently refuted changes (`web_refuted`
     drift events); memory gates changes whose credence fell
     (`refuted_assumption`).
  v2 (`autoresearch/research/loop.py`): no fact-check step. Exa feeds method
     discovery: an `exa`-origin idea keeps its `source_url`, and is traced to
     its market bids (the critic bids against), findings, OUTCOME facts and
     decision records. Its only veto, `gated_refuted_category`, is memory-based.

Standard library only; no network. The HTML page is static and self-contained.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .shared_memory import parse_fact

AUTHOR_RE = re.compile(r"\[author=([\w-]+)\]")
VETO_RE = re.compile(r"^(?P<change>\S+) refuted by (?P<urls>.*)$")
GATE_RE = re.compile(r"^(?P<change>\S+) relies on refuted '(?P<key>[^']+)'$")
FACT_CHECK_WEIGHT = 0.5   # loop.Researcher._critic_allows: memory.update(..., weight=0.5 * confidence)

# Fields whose absence blocks a link, keyed so each is reported once with where it would go.
MISSING = {
    "source.iter": ("exa.Source / loop.RunReport.sources",
                    "Source has no iteration: a source is joined to EVIDENCE on (change, URL) only, "
                    "so repeated checks of one change cannot be told apart"),
    "source.fact_ref": ("exa.Source + loop._critic_allows",
                        "Source has no id of the EVIDENCE fact it fed (nor the fact a list of source ids)"),
    "evidence.iter": ("loop._critic_allows EVIDENCE fact",
                      "EVIDENCE has no iter: recovered from write order in a local JSONL only; "
                      "unavailable for past.dev recall"),
    "veto.evidence_refs": ("loop._critic_allows DriftEvent('web_refuted')",
                           "the veto records only the first refuting fact's URLs, not which EVIDENCE facts "
                           "(refuting and supporting) it weighed, nor their counts"),
    "veto.refute_confidence": ("loop.RunReport (no config)",
                               "the v1 report does not record LoopConfig.refute_confidence, so which refutations "
                               "counted toward the veto cannot be checked"),
    "credence.before_after": ("memory.ResearchMemory.update",
                              "credence before/after each update is not logged; assumptions.json holds only the "
                              "final alpha/beta after the whole run"),
    "outcome.iter": ("loop.Researcher.run OUTCOME fact",
                     "OUTCOME has no iter: joined to the history entry on (run, change, delta)"),
    "decision.vetoed": ("memory.record_decision (v1)",
                        "the v1 decision record does not mark which ranked options were vetoed"),
    "v1.decisions_file": ("<memory>/decisions.jsonl",
                          "no v1 decision log was found for this run (pass --decisions <memory>/decisions.jsonl)"),
    "shared.memory_file": ("--memory",
                           "no shared-memory JSONL with this run's facts was found (pass --memory shared.jsonl)"),
    "web_ideas.iter": ("research.loop._discover 'web_ideas' event",
                       "the web_ideas event and web_ideas list have no iteration or search query, so an idea "
                       "is joined to its source by URL only"),
    "source.query": ("research.loop._discover / exa.WebScout._log",
                     "sources do not record the query that returned them"),
    "v2.fact_check": ("research/loop.py",
                      "the v2 loop has no fact-check step: no EVIDENCE facts, so no web-based veto or "
                      "credence update exists to trace"),
    "v2.outcome_move": ("research.loop OUTCOME fact",
                        "v2 OUTCOME facts carry change=<category>, not the move/idea id: joined to the finding "
                        "on (run, category, delta, status)"),
}


# ---------- loading ----------
@dataclass
class Artifacts:
    reports: List[Tuple[str, dict]] = field(default_factory=list)          # (path, report)
    facts: List[dict] = field(default_factory=list)                        # parsed, with _ref/_author/_pos
    decisions: List[Tuple[str, dict]] = field(default_factory=list)        # (path, record)
    assumptions: Dict[str, dict] = field(default_factory=dict)
    memory_files: List[str] = field(default_factory=list)
    decision_files: List[str] = field(default_factory=list)

    def add(self, name: str, records: Sequence) -> None:
        """Classify the records of one file by their shape (a report, shared
        memory rows, decision records or an assumptions ledger)."""
        is_memory = is_decisions = False
        for n, rec in enumerate(records, 1):
            if not isinstance(rec, dict):
                continue
            if "run_id" in rec and ("history" in rec or ("findings" in rec and "baseline" in rec)):
                self.reports.append((name, rec))
            elif isinstance(rec.get("content"), str):
                f = parse_fact(rec["content"])
                if f:
                    m = AUTHOR_RE.search(rec["content"])
                    self.facts.append({**f, "_ref": f"{name}:{n}", "_pos": (name, n),
                                       "_author": rec.get("author") or (m.group(1) if m else None)})
                    is_memory = True
            elif "run_id" in rec and "options" in rec and "chosen" in rec:
                self.decisions.append((name, rec))
                is_decisions = True
            elif rec and all(isinstance(v, dict) and "alpha" in v and "beta" in v for v in rec.values()):
                self.assumptions.update(rec)
        if is_memory:
            self.memory_files.append(name)
        if is_decisions:
            self.decision_files.append(name)


def _read(path: str) -> List:
    with open(path) as fh:
        if path.endswith(".jsonl"):
            out = []
            for line in fh:
                if line.strip():
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        out.append(None)   # keep line numbers aligned with the file
            return out
        try:
            return [json.load(fh)]
        except ValueError:
            return []


def load(run_dir: str, memory: Sequence[str] = (), decisions: Sequence[str] = ()) -> Artifacts:
    """Every report, shared-memory file, decision log and assumptions.json
    under run_dir (a directory or one report file), plus the extra files."""
    paths: List[str] = []
    if os.path.isdir(run_dir):
        for root, dirs, files in os.walk(run_dir):
            dirs.sort()
            paths += [os.path.join(root, f) for f in sorted(files) if f.endswith((".json", ".jsonl"))]
    else:
        paths.append(run_dir)
    base = os.path.realpath(run_dir if os.path.isdir(run_dir) else os.path.dirname(run_dir) or ".")
    seen, art = set(), Artifacts()
    for p in list(paths) + list(memory) + list(decisions):
        real = os.path.realpath(p)
        if real in seen:
            continue
        seen.add(real)
        # refs are shown relative to the run directory when the file is inside it
        name = os.path.relpath(real, base) if real.startswith(base + os.sep) else p
        art.add(name, _read(p))
    return art


# ---------- helpers ----------
def _urls(v: Optional[str]) -> List[str]:
    return [u for u in (v or "").split(",") if u]


def _num(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _missing(key: str) -> dict:
    where, why = MISSING[key]
    return {"field": key, "where": where, "why": why}


def _evidence_view(f: dict, run_id: str, iters: Dict[str, int]) -> dict:
    return {"ref": f["_ref"], "author": f.get("_author"), "run": f.get("run"), "this_run": f.get("run") == run_id,
            "change": f.get("change"), "stance": f.get("stance"), "confidence": _num(f.get("confidence")),
            "urls": _urls(f.get("urls")), "iter": iters.get(f["_ref"]),
            "iter_from": "write order (local JSONL)" if f["_ref"] in iters else None}


def _evidence_iters(facts: List[dict], run_id: str) -> Dict[str, int]:
    """Iteration of each of this run's EVIDENCE facts, from write order: in v1
    every iteration writes its EVIDENCE facts before its single OUTCOME fact.
    Only within one local file, where line order is write order."""
    out: Dict[str, int] = {}
    by_file: Dict[str, List[dict]] = {}
    for f in facts:
        if f.get("run") == run_id and f["kind"] in ("EVIDENCE", "OUTCOME"):
            by_file.setdefault(f["_pos"][0], []).append(f)
    for rows in by_file.values():
        it = 1
        for f in sorted(rows, key=lambda x: x["_pos"][1]):
            if f["kind"] == "EVIDENCE":
                out[f["_ref"]] = it
            else:
                it += 1
    return out


def _outcome_view(f: dict) -> dict:
    keep = ("task", "change", "delta", "valid", "status", "p_eval", "validity", "run", "worker")
    return {"ref": f["_ref"], **{k: f[k] for k in keep if k in f}}


# ---------- v1 ----------
def _v1_trails(path: str, rep: dict, art: Artifacts) -> dict:
    run_id, task = rep["run_id"], rep.get("task")
    facts = [f for f in art.facts if f.get("task") in (None, task)]
    evidence = [f for f in facts if f["kind"] == "EVIDENCE"]
    outcomes = [f for f in facts if f["kind"] == "OUTCOME"]
    iters = _evidence_iters(facts, run_id)
    history = {h["iter"]: h for h in rep.get("history", [])}
    sources = rep.get("sources") or []
    dec = {r["iter"]: r for _, r in art.decisions if r.get("run_id") == run_id and isinstance(r.get("chosen"), str)}
    drift = rep.get("drift_events") or []
    run_missing = set()
    if not any(f.get("run") == run_id for f in facts):
        run_missing.add("shared.memory_file")
    if not dec:
        run_missing.add("v1.decisions_file")
    run_missing.add("veto.refute_confidence")

    def source_rows(change: str, urls: Iterable[str]) -> List[dict]:
        rows, want = [], list(dict.fromkeys(urls))
        for u in want:
            hits = [s for s in sources if s.get("url") == u and s.get("used_for") == "fact_check"
                    and s.get("detail") == change]
            if hits:
                s = hits[0]
                rows.append({"url": u, "title": s.get("title"), "published": s.get("published"),
                             "used_for": s.get("used_for"), "detail": s.get("detail"), "linked": True,
                             "times_returned": len(hits)})
            else:
                other = [s for s in sources if s.get("url") == u]
                rows.append({"url": u, "linked": False, "title": other[0].get("title") if other else None,
                             "published": other[0].get("published") if other else None,
                             "used_for": other[0].get("used_for") if other else None,
                             "missing": "no fact_check Source for this URL and change in this run's report "
                                        "(the evidence may come from another run, or sources were not saved)"})
        return rows

    def outcome_of(it: int, change: str) -> Tuple[Optional[dict], List[dict]]:
        h = history.get(it)
        mine = [f for f in outcomes if f.get("run") == run_id and f.get("change") == change]
        if h is None:
            return None, [_outcome_view(f) for f in mine]
        d = h.get("delta")
        match = [f for f in mine if d is not None and _num(f.get("delta")) is not None
                 and abs(_num(f.get("delta")) - round(d, 4)) < 1e-6]
        return ({"iter": it, "change": h.get("change"), "score": h.get("score"), "delta": d,
                 "accepted": h.get("accepted"), "valid": h.get("valid"), "metrics": h.get("metrics")},
                [_outcome_view(f) for f in (match or mine)])

    def considered_at(change: str) -> List[int]:
        return sorted(i for i, r in dec.items() if any(o.get("change") == change for o in r.get("options", [])))

    def credence(change: str) -> dict:
        key = f"{task}:{change}"
        ups = []
        for f in evidence:
            if f.get("run") == run_id and f.get("change") == change and f.get("stance") in ("support", "refute"):
                c = _num(f.get("confidence")) or 0.0
                ups.append({"evidence": f["_ref"], "direction": "+" if f["stance"] == "support" else "-",
                            "weight": round(FACT_CHECK_WEIGHT * c, 4), "iter": iters.get(f["_ref"]),
                            "rule": "weight = 0.5 x confidence (loop.Researcher._critic_allows)"})
        a = art.assumptions.get(key)
        final = None
        if a:
            final = {"alpha": a["alpha"], "beta": a["beta"], "credence": round(a["alpha"] / (a["alpha"] + a["beta"]), 4),
                     "note": "after the whole run, all updates (experiments too), not this one alone"}
        return {"assumption": key, "updates": ups, "final": final}

    trails, cred_updates = [], []
    for ev in drift:
        kind, it, detail = ev.get("kind"), ev.get("iteration"), ev.get("detail", "")
        if kind == "web_refuted":
            m = VETO_RE.match(detail)
        elif kind == "refuted_assumption":
            m = GATE_RE.match(detail)
        else:
            continue
        miss = set()
        change = m.group("change") if m else None
        t = {"loop": "v1", "run_id": run_id, "report": path, "kind": kind, "iter": it, "detail": detail,
             "change": change}
        if not m:
            t["missing"] = [{"field": "veto.detail", "where": "DriftEvent.detail",
                             "why": f"could not parse the change from {detail!r}"}]
            trails.append(t)
            continue
        ev_rows = [f for f in evidence if f.get("change") == change and f.get("_author") != "critic"]
        if kind == "web_refuted":
            cited = _urls(m.group("urls"))
            t["veto"] = {"by": "critic (drift monitor)", "cited_urls": cited,
                         "rule": "vetoed when refuting EVIDENCE (confidence >= refute_confidence) outnumbers "
                                 "supporting EVIDENCE for this change, across runs"}
            views = [_evidence_view(f, run_id, iters) for f in ev_rows]
            for v in views:
                v["cited_by_veto"] = v["stance"] == "refute" and v["urls"] == cited
            t["evidence"] = views
            t["evidence_counts"] = {s: sum(v["stance"] == s for v in views) for s in ("refute", "support", "none")}
            if not any(v["cited_by_veto"] for v in views):
                t["evidence_link"] = "MISSING: no recorded EVIDENCE fact matches the URLs the veto cites"
            urls = cited + [u for v in views for u in v["urls"] if u not in cited]
            t["sources"] = source_rows(change, urls)
            miss |= {"veto.evidence_refs", "source.iter", "source.fact_ref"}
            if any(v["this_run"] and v["iter"] is None for v in views):
                miss.add("evidence.iter")
        else:
            key = m.group("key")
            t["veto"] = {"by": "drift monitor (memory gate)", "assumption": key,
                         "rule": "gated when the assumption has enough evidence and its credence is below the "
                                 "refute threshold"}
            fact_checked = [f for f in evidence if f"{task}:{f.get('change')}" == key
                            and f.get("stance") in ("support", "refute")]
            t["evidence"] = [_evidence_view(f, run_id, iters) for f in fact_checked]
            t["sources"] = source_rows(change, [u for f in fact_checked for u in _urls(f.get("urls"))])
            if not fact_checked:
                t["evidence_link"] = ("no fact-check moved this assumption in the recorded memory: its credence "
                                      "comes from experiment outcomes")
            miss.add("credence.before_after")
        t["credence"] = credence(change)
        if t["credence"]["updates"]:
            miss.add("credence.before_after")
        t["considered_at_iters"] = considered_at(change)
        d = dec.get(it)
        ran = (d or {}).get("chosen") or (history.get(it) or {}).get("change")
        t["decision"] = ({"iter": it, "options": [o.get("change") for o in d.get("options", [])],
                          "chosen": d.get("chosen"), "ref": "v1 decisions.jsonl"} if d else None)
        if d:
            miss.add("decision.vetoed")
        hist, outs = outcome_of(it, ran) if ran else (None, [])
        t["ran_instead"] = hist
        t["veto_overridden"] = bool(ran and ran == change)   # everything gated: the loop fell back to ranked[0]
        t["ran_instead_outcomes"] = outs
        if outs:
            miss.add("outcome.iter")
        t["same_iter_events"] = [e for e in drift if e.get("iteration") == it and e is not ev]
        t["vetoed_change_elsewhere"] = {
            "this_run": [{"iter": h["iter"], "delta": h.get("delta"), "accepted": h.get("accepted"),
                          "valid": h.get("valid")} for h in rep.get("history", []) if h.get("change") == change],
            "other_runs": [_outcome_view(f) for f in outcomes if f.get("change") == change and f.get("run") != run_id]}
        t["missing"] = [_missing(k) for k in sorted(miss | run_missing) if k in MISSING]
        trails.append(t)

    vetoed = {(t["iter"], t.get("change")) for t in trails if t["kind"] == "web_refuted"}
    for f in evidence:
        if f.get("run") != run_id or f.get("stance") not in ("support", "refute"):
            continue
        change = f.get("change")
        it = iters.get(f["_ref"])
        c = _num(f.get("confidence")) or 0.0
        hist, outs = outcome_of(it, (history.get(it) or {}).get("change")) if it is not None else (None, [])
        miss = {"credence.before_after", "source.iter", "source.fact_ref"} | ({"evidence.iter"} if it is None else set())
        cred_updates.append({
            "loop": "v1", "run_id": run_id, "evidence": _evidence_view(f, run_id, iters),
            "sources": source_rows(change, _urls(f.get("urls"))),
            "assumption": f"{task}:{change}", "direction": "+" if f["stance"] == "support" else "-",
            "weight": round(FACT_CHECK_WEIGHT * c, 4), "rule": "weight = 0.5 x confidence (loop.Researcher._critic_allows)",
            "final": credence(change)["final"], "iter": it,
            "vetoed": (it, change) in vetoed if it is not None else None,
            "experiment_at_iter": hist, "experiment_outcomes": outs,
            "considered_at_iters": considered_at(change),
            "missing": [_missing(k) for k in sorted(miss | run_missing)]})
    return {"run_id": run_id, "loop": "v1", "report": path, "task": task,
            "code_version": rep.get("code_version"), "offline": _offline(rep),
            "n_sources": len(sources), "n_evidence_this_run": sum(f.get("run") == run_id for f in evidence),
            "vetoes": trails, "credence_updates": cred_updates, "source_trails": [],
            "missing": [_missing(k) for k in sorted(run_missing)]}


# ---------- v2 ----------
def _design_text(move: str, idea: dict) -> str:
    verb = "add" if move.startswith("add") else "remove"
    return f"{verb} [{idea.get('category')}] {idea.get('text')}"


def _v2_trails(path: str, rep: dict, art: Artifacts) -> dict:
    run_id = rep["run_id"]
    sources = rep.get("sources") or []
    findings = rep.get("findings") or []
    log = rep.get("log") or []
    ledger = ((rep.get("market") or {}).get("ledger")) or []
    outcomes = [f for f in art.facts if f["kind"] == "OUTCOME" and f.get("run") == run_id]
    bid_facts = [f for f in art.facts if f["kind"] in ("BID", "SETTLE") and f.get("run") == run_id]
    decisions = [r for r in rep.get("decisions") or [] if isinstance(r, dict)]
    known = {(r.get("iter"), r.get("point"), r.get("context"), r.get("chosen")) for r in decisions}
    decisions += [r for _, r in art.decisions if r.get("run_id") == run_id and "point" in r
                  and (r.get("iter"), r.get("point"), r.get("context"), r.get("chosen")) not in known]
    run_missing = {"v2.fact_check"}
    if not any(f.get("run") == run_id for f in art.facts):
        run_missing.add("shared.memory_file")

    def decisions_about(text: str) -> List[dict]:
        out = []
        for r in decisions:
            opts = r.get("options") or []
            in_opts = text in opts
            if in_opts or text in (r.get("context") or ""):
                out.append({"iter": r.get("iter"), "point": r.get("point"), "context": r.get("context"),
                            "chosen": opts[r["chosen"]] if isinstance(r.get("chosen"), int) and r["chosen"] < len(opts)
                            else r.get("chosen"),
                            "picked_this": (isinstance(r.get("chosen"), int) and r["chosen"] < len(opts)
                                            and opts[r["chosen"]] == text),
                            "user_model_choice": r.get("user_model_choice"), "overrode_taste": r.get("overrode_taste")})
        return out

    def finding_outcomes(fd: dict) -> List[dict]:
        return [_outcome_view(f) for f in outcomes if f.get("change") == fd.get("category")
                and f.get("status") == fd.get("status") and _num(f.get("delta")) is not None
                and abs(_num(f.get("delta")) - round(fd.get("delta", 0.0), 4)) < 1e-6]

    def idea_trail(idea: dict, kind: str, it: Optional[int] = None) -> dict:
        move = f"add:{idea.get('id')}"
        text = _design_text(move, idea)
        miss = set()
        url = idea.get("source_url")
        src = [s for s in sources if url and s.get("url") == url]
        t = {"loop": "v2", "run_id": run_id, "report": path, "kind": kind, "iter": it, "move": move,
             "idea": {k: idea.get(k) for k in ("id", "text", "category", "origin", "source_url", "p_validated")}}
        if url:
            t["sources"] = ([{"url": url, "title": src[0].get("title"), "published": src[0].get("published"),
                              "used_for": src[0].get("used_for"), "linked": True, "times_returned": len(src)}]
                            if src else [{"url": url, "linked": False,
                                          "missing": "the idea's source_url is not among this run's recorded sources"}])
            miss |= {"web_ideas.iter", "source.query"}
        else:
            t["sources"] = []
            t["source_link"] = f"none: origin '{idea.get('origin')}' (not from Exa)"
        t["bids"] = [{k: e.get(k) for k in ("iter", "agent", "p_validated", "stake", "against", "resource", "gpu_s")
                      if k in e} for e in ledger if e.get("event") == "bid" and e.get("candidate_id") == move]
        t["bid_facts"] = [{"ref": f["_ref"], **{k: f[k] for k in f if not k.startswith("_")}}
                          for f in bid_facts if f.get("candidate") == move]
        t["critic"] = [b for b in t["bids"] if b.get("against")]
        t["screened_out"] = [s for s in (rep.get("allocation") or {}).get("screened_out", []) if s.get("move") == move]
        fds = [f for f in findings if f.get("move") == move]
        t["findings"] = [{k: f.get(k) for k in ("id", "iter", "status", "delta", "p_better", "validity", "n")}
                         for f in fds]
        t["outcomes"] = [o for f in fds for o in finding_outcomes(f)]
        if fds and outcomes:
            miss.add("v2.outcome_move")
        t["decisions"] = decisions_about(text)
        t["in_best_design"] = any(b.get("id") == idea.get("id") for b in rep.get("best_design") or [])
        t["missing"] = [_missing(k) for k in sorted(miss | run_missing)]
        return t

    trails = []
    for e in log:
        if e.get("event") == "gated_refuted_category":
            idea = next((w for w in (rep.get("web_ideas") or []) if w.get("text") == e.get("idea")), None)
            t = idea_trail(idea or {"text": e.get("idea"), "category": e.get("category"), "origin": None},
                           "gated_refuted_category", e.get("iter"))
            t["veto"] = {"by": "memory gate (category credence)", "category": e.get("category"),
                         "rule": "an add-move is gated when its category has >= 2 evidence and credence < 0.3"}
            t["measured_instead"] = [{k: f.get(k) for k in ("id", "move", "text", "status", "delta")}
                                     for f in findings if f.get("iter") == e.get("iter")]
            trails.append(t)
    exa: Dict[str, dict] = {}
    for w in rep.get("web_ideas") or []:   # the same idea can be discovered by several searches
        if w.get("origin") == "exa":
            exa.setdefault(w.get("id") or w.get("text"), {**w, "times_discovered": 0})["times_discovered"] += 1
    source_trails = []
    for w in exa.values():
        t = idea_trail(w, "exa_idea")
        t["idea"]["times_discovered"] = w["times_discovered"]
        source_trails.append(t)
    return {"run_id": run_id, "loop": "v2", "report": path, "task": rep.get("scenario"),
            "code_version": rep.get("code_version"), "offline": _offline(rep), "n_sources": len(sources),
            "n_evidence_this_run": 0, "vetoes": trails, "credence_updates": [], "source_trails": source_trails,
            "n_critic_bids_against": sum(e.get("event") == "bid" and bool(e.get("against")) for e in ledger),
            "missing": [_missing(k) for k in sorted(run_missing)]}


def _backend(r: dict) -> str:
    # The reports do not name the backend; zero calls and tokens is the only safe offline signal
    # (the offline simulator also counts approximate tokens, so a non-zero count does not mean live).
    return "offline simulator" if r.get("offline") else "backend not recorded in the report"


def _offline(rep: dict) -> Optional[bool]:
    c = rep.get("compute") or {}
    if "calls" not in c:
        return None
    return c.get("calls") == 0 and not c.get("input_tokens")


# ---------- build and render ----------
def build(art: Artifacts, source: str = "") -> dict:
    runs = []
    for path, rep in art.reports:
        runs.append(_v1_trails(path, rep, art) if "history" in rep else _v2_trails(path, rep, art))
    fields: Dict[str, dict] = {}
    for r in runs:
        for item in r["missing"] + [m for t in r["vetoes"] + r["credence_updates"] + r["source_trails"]
                                    for m in t.get("missing", [])]:
            fields.setdefault(item["field"], item)
    return {"source": source, "memory_files": art.memory_files, "decision_files": art.decision_files,
            "runs": runs,
            "n_vetoes": sum(len(r["vetoes"]) for r in runs),
            "n_credence_updates": sum(len(r["credence_updates"]) for r in runs),
            "n_source_trails": sum(len(r["source_trails"]) for r in runs),
            "n_linked_sources": sum(bool(s.get("linked")) for r in runs
                                    for t in r["vetoes"] + r["credence_updates"] + r["source_trails"]
                                    for s in t.get("sources", [])),
            "missing_fields": [fields[k] for k in sorted(fields)],
            "caveat": "Reconstructed from recorded artifacts only. MISSING marks a link the run did not record; "
                      "offline-simulator runs are pipeline checks, not findings."}


def trail(run_dir: str, memory: Sequence[str] = (), decisions: Sequence[str] = ()) -> dict:
    return build(load(run_dir, memory, decisions), source=run_dir)


def _src_line(s: dict) -> str:
    if s.get("linked"):
        return (f"- Exa source [{s.get('used_for')}] {s.get('title') or '(untitled)'} <{s['url']}>, "
                f"published {s.get('published') or 'MISSING (no publish date recorded)'}")
    return f"- Exa source <{s['url']}>: MISSING ({s.get('missing')})"


def _ev_line(v: dict) -> str:
    where = f"iter {v['iter']} ({v['iter_from']})" if v.get("iter") is not None else "iter MISSING"
    tag = " [cited by the veto]" if v.get("cited_by_veto") else ""
    return (f"- EVIDENCE `{v['ref']}` by {v.get('author')}, run {v.get('run')}"
            f"{' (this run)' if v.get('this_run') else ''}, {where}: stance **{v.get('stance')}**, "
            f"confidence {v.get('confidence')}, URLs {', '.join(v.get('urls') or []) or '(none)'}{tag}")


def render_markdown(data: dict) -> str:
    L = [f"# Source-to-decision trail: {data['source']}", "", data["caveat"], "",
         f"Runs: {len(data['runs'])}. Vetoes: {data['n_vetoes']}. Fact-check credence updates: "
         f"{data['n_credence_updates']}. Exa idea trails: {data['n_source_trails']}. "
         f"Linked Exa sources: {data['n_linked_sources']}.",
         f"Shared memory: {', '.join(data['memory_files']) or 'MISSING (none found)'}. "
         f"Decision logs: {', '.join(data['decision_files']) or 'none found'}."]
    for r in data["runs"]:
        L += ["", f"## Run {r['run_id']} ({r['loop']}, {r.get('task')})", "",
              f"Report `{r['report']}`; code version `{r.get('code_version') or 'not recorded'}`; "
              f"{_backend(r)}; "
              f"{r['n_sources']} Exa sources recorded."]
        if not (r["vetoes"] or r["credence_updates"] or r["source_trails"]):
            L += ["", "No critic veto, fact-check credence update or Exa-sourced idea is recorded for this run."]
        for k, t in enumerate(r["vetoes"], 1):
            L += ["", f"### Veto {k}: `{t.get('change') or t.get('move')}` at iteration {t.get('iter')} ({t['kind']})", ""]
            if t.get("detail"):
                L.append(f"Recorded: \"{t['detail']}\"")
            v = t.get("veto") or {}
            L += ["", f"**1. Sources.**"] + ([_src_line(s) for s in t.get("sources", [])] or
                                              [f"- {t.get('source_link') or 'none recorded'}"])
            L += ["", "**2. Evidence.**"] + ([_ev_line(e) for e in t.get("evidence", [])] or
                                              [f"- {t.get('evidence_link') or 'none recorded'}"])
            if t.get("evidence_link") and t.get("evidence"):
                L.append(f"- {t['evidence_link']}")
            if t.get("evidence_counts"):
                c = t["evidence_counts"]
                L.append(f"- Counts over every run: {c['refute']} refute, {c['support']} support, {c['none']} none.")
            L += ["", f"**3. Veto.** By {v.get('by')}. Rule: {v.get('rule')}."]
            cr = t.get("credence") or {}
            if cr:
                L.append(f"- Assumption `{cr['assumption']}`: " + ("; ".join(
                    f"{u['direction']}{u['weight']} from `{u['evidence']}` (iter {u['iter'] if u['iter'] is not None else 'MISSING'})"
                    for u in cr["updates"]) or "no fact-check update in this run")
                    + (f"; final credence {cr['final']['credence']} ({cr['final']['note']})" if cr.get("final") else ""))
            L += ["", "**4. What ran instead.**"]
            ri = t.get("ran_instead")
            if t.get("veto_overridden"):
                L.append("- The vetoed change ran anyway: every top candidate was gated and the loop fell back to the top-ranked one.")
            if ri:
                L.append(f"- Iteration {ri['iter']}: `{ri['change']}`, delta {ri['delta']:+.4f}, accepted {ri['accepted']}, "
                         f"valid {ri['valid']}." if ri.get("delta") is not None else f"- Iteration {ri['iter']}: `{ri['change']}`.")
            elif t.get("measured_instead") is not None:
                L += [f"- {m['id']} `{m['move']}` {m['status']} (delta {m['delta']:+.4f})" for m in t["measured_instead"]] \
                    or ["- nothing was measured in this iteration"]
            else:
                L.append("- MISSING: no history entry for this iteration")
            d = t.get("decision")
            if d:
                L.append(f"- Decision record: chose `{d['chosen']}` from {d['options']}.")
            L += [f"- OUTCOME `{o['ref']}`: change {o.get('change')}, delta {o.get('delta')}, valid {o.get('valid')}"
                  for o in t.get("ran_instead_outcomes", [])]
            ve = t.get("vetoed_change_elsewhere") or {}
            if ve:
                L += ["", "**5. The vetoed change elsewhere.**",
                      f"- This run: {ve['this_run'] or 'never tested'}.",
                      f"- Other runs' OUTCOME facts: {[(o.get('run'), o.get('delta'), o.get('valid')) for o in ve['other_runs']] or 'none recorded'}."]
            L += _missing_lines(t)
        for k, u in enumerate(r["credence_updates"], 1):
            e = u["evidence"]
            L += ["", f"### Credence update {k}: `{u['assumption']}` {u['direction']}{u['weight']}", ""]
            L += [_src_line(s) for s in u["sources"]] + [_ev_line(e)]
            L.append(f"- Rule: {u['rule']}; vetoed this iteration: {u['vetoed']}; "
                     f"final credence: {u['final']['credence'] if u.get('final') else 'not found (no assumptions.json)'}.")
            x = u.get("experiment_at_iter")
            L.append(f"- Experiment at iter {u['iter']}: `{x['change']}`, delta {x['delta']:+.4f}, accepted {x['accepted']}."
                     if x and x.get("delta") is not None else "- Experiment at this iteration: MISSING (iteration unknown)")
            L += _missing_lines(u)
        for k, t in enumerate(r["source_trails"], 1):
            i = t["idea"]
            L += ["", f"### Exa idea {k}: [{i['category']}] {i['text']}", ""]
            L += [_src_line(s) for s in t["sources"]]
            L.append(f"- Discovered {i.get('times_discovered', 1)} time(s); proposer's P(validated): "
                     f"{i.get('p_validated')}; bids: " + (", ".join(_bid_text(b) for b in t["bids"]) or "none (no market)"))
            L += [f"- Screened out at iter {s['iter']} (screen score {s['screen_score']})" for s in t["screened_out"]]
            L += [f"- Finding {f['id']} iter {f['iter']}: {f['status']}, delta {f['delta']:+.4f}, P(better) {f['p_better']:.2f}"
                  for f in t["findings"]] or ["- Never measured in full."]
            L += [f"- OUTCOME `{o['ref']}`: status {o.get('status')}, delta {o.get('delta')}" for o in t["outcomes"]]
            L += [f"- Decision {d['point']} iter {d['iter']}: {_pick_text(d)}" for d in t["decisions"]]
            L.append(f"- In the final best design: {t['in_best_design']}.")
            L += _missing_lines(t)
    L += ["", "## Fields the loop does not record", ""]
    L += [f"- `{m['field']}` ({m['where']}): {m['why']}" for m in data["missing_fields"]] or ["- none"]
    return "\n".join(L) + "\n"


def _bid_text(b: dict) -> str:
    p = b.get("p_validated")
    p = f"{p:.3f}" if isinstance(p, (int, float)) else p
    return f"{b.get('agent')} p={p}{' against' if b.get('against') else ''} (iter {b.get('iter')})"


def _pick_text(d: dict) -> str:
    if d.get("picked_this"):
        return "chose this idea"
    role = "an option, not chosen" if d.get("point") == "D1" else "about this idea"
    return f"{role}; chose \"{str(d.get('chosen'))[:100]}\""


def _missing_lines(t: dict) -> List[str]:
    ms = t.get("missing") or []
    return ["", "Missing links: " + "; ".join(f"`{m['field']}`" for m in ms) + "."] if ms else []


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#66645e;--card:#fff;--line:#e3e0d8;--ok:#1d6b46;--miss:#a33a1f;
--chip:#f1eee6;--accent:#2b4c7e}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--muted:#a19e95;--card:#1f1f1c;
--line:#34332e;--ok:#6fcf9b;--miss:#f08a6c;--chip:#2a2925;--accent:#8fb0e6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}h1{font-size:24px;margin:0 0 4px}
h2{font-size:18px;margin:32px 0 8px}.muted{color:var(--muted)}.stats{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px}
.stat b{display:block;font-size:20px}details{background:var(--card);border:1px solid var(--line);border-radius:10px;
margin:10px 0;padding:10px 14px}summary{cursor:pointer;font-weight:600}
ol.chain{list-style:none;padding:0;margin:10px 0 0}ol.chain>li{border-left:3px solid var(--line);padding:4px 0 8px 14px;
margin-left:4px}ol.chain>li.ok{border-color:var(--ok)}ol.chain>li.miss{border-color:var(--miss)}
.step{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.tag{display:inline-block;font-size:12px;border-radius:4px;padding:0 6px;background:var(--chip);margin-left:6px}
.tag.miss{color:var(--miss)}.tag.ok{color:var(--ok)}code{background:var(--chip);border-radius:4px;padding:0 4px;
overflow-wrap:anywhere}a{color:var(--accent);overflow-wrap:anywhere}ul{margin:4px 0;padding-left:20px}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--line);text-align:left;
padding:6px;vertical-align:top}
"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _link(url: str) -> str:
    safe = url if re.match(r"^https?://", url or "") else ""
    return f'<a href="{_e(safe)}" rel="noopener noreferrer">{_e(url)}</a>' if safe else _e(url)


def _li(title: str, ok: bool, body: List[str]) -> str:
    tag = '<span class="tag ok">linked</span>' if ok else '<span class="tag miss">MISSING</span>'
    return (f'<li class="{"ok" if ok else "miss"}"><div class="step">{_e(title)}{tag}</div>'
            + ("<ul>" + "".join(f"<li>{b}</li>" for b in body) + "</ul>" if body else "") + "</li>")


def _src_html(s: dict) -> str:
    if s.get("linked"):
        return (f"[{_e(s.get('used_for'))}] {_e(s.get('title') or '(untitled)')}: {_link(s['url'])}, published "
                f"{_e(s.get('published') or 'MISSING')}")
    return f"{_link(s['url'])}: <span class=\"tag miss\">MISSING</span> {_e(s.get('missing'))}"


def _ev_html(v: dict) -> str:
    it = f"iter {v['iter']} ({v['iter_from']})" if v.get("iter") is not None else "iter MISSING"
    cited = ' <span class="tag">cited by the veto</span>' if v.get("cited_by_veto") else ""
    mine = " (this run)" if v.get("this_run") else ""
    return (f"<code>{_e(v['ref'])}</code> run {_e(v.get('run'))}{mine}, {_e(it)}: "
            f"<b>{_e(v.get('stance'))}</b> conf {_e(v.get('confidence'))}{cited}<br>"
            + ", ".join(_link(u) for u in v.get("urls") or []))


def _missing_html(t: dict) -> str:
    ms = t.get("missing") or []
    return ("<p class=\"muted\">Not recorded: " + ", ".join(f"<code>{_e(m['field'])}</code>" for m in ms) + "</p>"
            if ms else "")


def _veto_html(t: dict) -> str:
    srcs = t.get("sources") or []
    ev = t.get("evidence") or []
    v = t.get("veto") or {}
    steps = [_li("1. Exa source", any(s.get("linked") for s in srcs),
                 [_src_html(s) for s in srcs] or [_e(t.get("source_link") or "none recorded")]),
             _li("2. Evidence fact", bool(ev) and not (t.get("evidence_link") or "").startswith("MISSING"),
                 [_ev_html(e) for e in ev] + ([_e(t["evidence_link"])] if t.get("evidence_link") else []))]
    cr = t.get("credence") or {}
    body = [f"{_e(v.get('by'))}: {_e(v.get('rule'))}"]
    if cr:
        body.append(f"assumption <code>{_e(cr['assumption'])}</code>: " + (", ".join(
            f"{_e(u['direction'])}{_e(u['weight'])} (iter {_e(u['iter'] if u['iter'] is not None else 'MISSING')})"
            for u in cr["updates"]) or "no fact-check update this run")
            + (f"; final credence {_e(cr['final']['credence'])}" if cr.get("final") else ""))
    steps.append(_li("3. Veto / credence change", True, body))
    ri, d = t.get("ran_instead"), t.get("decision")
    body = []
    if t.get("veto_overridden"):
        body.append("The vetoed change ran anyway (every top candidate gated; fallback to the top-ranked one).")
    if ri:
        body.append(f"iter {_e(ri['iter'])}: <code>{_e(ri['change'])}</code>"
                    + (f", delta {ri['delta']:+.4f}, accepted {_e(ri['accepted'])}, valid {_e(ri['valid'])}"
                       if ri.get("delta") is not None else ""))
    for m in t.get("measured_instead") or []:
        body.append(f"{_e(m['id'])} <code>{_e(m['move'])}</code> {_e(m['status'])} (delta {m['delta']:+.4f})")
    if d:
        body.append(f"decision record: chose <code>{_e(d['chosen'])}</code> of "
                    + ", ".join(f"<code>{_e(o)}</code>" for o in d["options"]))
    body += [f"OUTCOME <code>{_e(o['ref'])}</code>: delta {_e(o.get('delta'))}, valid {_e(o.get('valid'))}"
             for o in t.get("ran_instead_outcomes") or []]
    steps.append(_li("4. Downstream: what ran instead", bool(ri or t.get("measured_instead")), body))
    ve = t.get("vetoed_change_elsewhere")
    if ve:
        steps.append(_li("5. The vetoed change elsewhere", bool(ve["this_run"] or ve["other_runs"]),
                         [f"this run: {_e(ve['this_run'] or 'never tested')}"]
                         + [f"run {_e(o.get('run'))}: delta {_e(o.get('delta'))}, valid {_e(o.get('valid'))}"
                            for o in ve["other_runs"]]))
    title = t.get("change") or t.get("move")
    return (f"<details open><summary>Iteration {_e(t.get('iter'))}: <code>{_e(title)}</code> "
            f"<span class=\"tag\">{_e(t['kind'])}</span></summary><ol class=\"chain\">{''.join(steps)}</ol>"
            f"{_missing_html(t)}</details>")


def _update_html(u: dict) -> str:
    x = u.get("experiment_at_iter")
    steps = [_li("1. Exa source", any(s.get("linked") for s in u["sources"]), [_src_html(s) for s in u["sources"]]),
             _li("2. Evidence fact", True, [_ev_html(u["evidence"])]),
             _li("3. Credence change", True, [f"<code>{_e(u['assumption'])}</code> {_e(u['direction'])}{_e(u['weight'])}; "
                                             f"{_e(u['rule'])}" + (f"; final credence {_e(u['final']['credence'])}"
                                                                    if u.get("final") else "")]),
             _li("4. Experiment at that iteration", bool(x),
                 [f"<code>{_e(x['change'])}</code> delta {x['delta']:+.4f}, accepted {_e(x['accepted'])}"]
                 if x and x.get("delta") is not None else ["iteration not recorded"])]
    return (f"<details><summary><code>{_e(u['assumption'])}</code> {_e(u['direction'])}{_e(u['weight'])}"
            f"</summary><ol class=\"chain\">{''.join(steps)}</ol>{_missing_html(u)}</details>")


def _idea_html(t: dict) -> str:
    i = t["idea"]
    steps = [_li("1. Exa source", any(s.get("linked") for s in t["sources"]), [_src_html(s) for s in t["sources"]]),
             _li("2. Idea and bids", True, [f"P(validated) stated: {_e(i.get('p_validated'))}"]
                 + [_e(_bid_text(b)) for b in t["bids"]]),
             _li("3. Measured", bool(t["findings"] or t["screened_out"]),
                 [f"screened out at iter {_e(s['iter'])}" for s in t["screened_out"]]
                 + [f"{_e(f['id'])} iter {_e(f['iter'])}: {_e(f['status'])}, delta {f['delta']:+.4f}" for f in t["findings"]]
                 + [f"OUTCOME <code>{_e(o['ref'])}</code> {_e(o.get('status'))}" for o in t["outcomes"]]),
             _li("4. Decisions", bool(t["decisions"]),
                 [f"{_e(d['point'])} iter {_e(d['iter'])}: {_e(_pick_text(d))}" for d in t["decisions"]]
                 + [f"in final best design: {_e(t['in_best_design'])}"])]
    return (f"<details><summary>[{_e(i['category'])}] {_e(i['text'])}</summary><ol class=\"chain\">{''.join(steps)}</ol>"
            f"{_missing_html(t)}</details>")


def render_html(data: dict) -> str:
    stats = [("runs", len(data["runs"])), ("vetoes", data["n_vetoes"]),
             ("credence updates", data["n_credence_updates"]), ("Exa ideas", data["n_source_trails"]),
             ("linked sources", data["n_linked_sources"])]
    parts = [f"<h1>Source-to-decision trail</h1><p class=\"muted\">{_e(data['source'])}. {_e(data['caveat'])}</p>",
             '<div class="stats">' + "".join(f'<div class="stat"><b>{_e(v)}</b>{_e(k)}</div>' for k, v in stats) + "</div>"]
    for r in data["runs"]:
        parts.append(f"<h2>Run {_e(r['run_id'])} <span class=\"tag\">{_e(r['loop'])}</span> "
                     f"<span class=\"tag\">{_e(_backend(r))}</span></h2>"
                     f"<p class=\"muted\">{_e(r['report'])}; code {_e(r.get('code_version') or 'not recorded')}; "
                     f"{_e(r['n_sources'])} Exa sources.</p>")
        if not (r["vetoes"] or r["credence_updates"] or r["source_trails"]):
            parts.append("<p>No critic veto, fact-check credence update or Exa-sourced idea is recorded for this run.</p>")
        parts += [_veto_html(t) for t in r["vetoes"]]
        parts += [_update_html(u) for u in r["credence_updates"]]
        parts += [_idea_html(t) for t in r["source_trails"]]
    rows = "".join(f"<tr><td><code>{_e(m['field'])}</code></td><td>{_e(m['where'])}</td><td>{_e(m['why'])}</td></tr>"
                   for m in data["missing_fields"])
    parts.append("<h2>Fields the loop does not record</h2>"
                 + (f"<table><tr><th>field</th><th>where</th><th>effect</th></tr>{rows}</table>" if rows else "<p>none</p>"))
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>Source-to-decision trail</title><style>{CSS}</style></head><body><main>{''.join(parts)}</main>"
            "</body></html>\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.integrations.trail",
                                 description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", help="a run directory (searched recursively) or one run report JSON")
    ap.add_argument("--memory", nargs="+", default=[], help="shared-memory JSONL file(s) with the run's facts")
    ap.add_argument("--decisions", nargs="+", default=[], help="decision log(s), e.g. <memory>/decisions.jsonl (v1)")
    ap.add_argument("--html", help="write a self-contained static HTML page here")
    ap.add_argument("--md", help="write the markdown trail here")
    ap.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    args = ap.parse_args(argv)
    if not os.path.exists(args.run_dir):
        ap.error(f"{args.run_dir} does not exist")
    data = trail(args.run_dir, args.memory, args.decisions)
    md = render_markdown(data)
    for path, text in ((args.html, render_html(data) if args.html else None), (args.md, md if args.md else None)):
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(text)
    sys.stdout.write(json.dumps(data, indent=1, default=str) + "\n" if args.json else md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
