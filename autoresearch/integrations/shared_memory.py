"""Shared multi-agent memory.

The loop runs as several agents (proposer, experimenter, critic, scout,
distiller), possibly across many parallel workers (Modal). They share facts
through a memory layer: past.dev when PAST_API_KEY is set, otherwise a local
JSONL store with the same interface. Each agent writes under its own identity
and reads what other agents wrote.

Division of labour with the other memory:
  * ResearchMemory (local JSON) holds exact numbers: Beta credences and the
    experiment log, which need precise arithmetic.
  * Shared memory holds cross-agent, cross-worker facts in text: experiment
    outcomes, web evidence with URLs, discovered methods, distilled insights.
Facts use a parseable line format "KIND key=value ..." so readers can use
them programmatically, not only as prompt context."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Dict, List, Optional

from .http import post_json

# OUTCOME/EVIDENCE/METHOD/INSIGHT/ASSUMPTION: loop agents; DECISION: research/decisions.py;
# BID/SETTLE: research/market.py; LABEL/DISAGREE: human labels and taste overrides (living user model).
FACT_KINDS = ("OUTCOME", "EVIDENCE", "METHOD", "INSIGHT", "ASSUMPTION", "DECISION", "BID", "SETTLE",
              "LABEL", "DISAGREE")
FACT_RE = re.compile(r"(\w+)=(\"[^\"]*\"|\S+)")


def format_fact(kind: str, **kv) -> str:
    parts = [kind]
    for k, v in kv.items():
        v = str(v)
        parts.append(f'{k}="{v}"' if " " in v else f"{k}={v}")
    return " ".join(parts)


def parse_fact(text: str) -> Optional[Dict[str, str]]:
    m = re.search(r"\b(" + "|".join(FACT_KINDS) + r")\b(.*)", text)
    if not m:
        return None
    d = {"kind": m.group(1)}
    for k, v in FACT_RE.findall(m.group(2)):
        d[k] = v.strip('"')
    return d


class SharedMemory:
    backend = "base"

    def write(self, agent: str, content: str, label: str = "", metadata: Optional[dict] = None): ...

    def recall(self, agent: str, query: str, limit: int = 50) -> List[dict]: ...

    def facts(self, agent: str, query: str, kind: str, limit: int = 50, exclude_author: Optional[str] = None):
        out = []
        for r in self.recall(agent, query, limit):
            if exclude_author and r.get("author") == exclude_author:
                continue
            f = parse_fact(r["content"])
            if f and f["kind"] == kind:
                out.append({**f, "_author": r.get("author")})
        return out


class LocalSharedMemory(SharedMemory):
    backend = "local"

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.log: List[dict] = []

    def write(self, agent, content, label="", metadata=None):
        rec = {"author": agent, "content": content, "label": label, "metadata": metadata or {},
               "t": time.time()}
        with open(self.path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        self.log.append({"op": "write", "agent": agent, "content": content})

    def recall(self, agent, query, limit=50):
        if not os.path.exists(self.path):
            return []
        q = set(re.findall(r"[a-z_=]+", query.lower()))
        rows = [json.loads(l) for l in open(self.path) if l.strip()]
        scored = sorted(rows, key=lambda r: -len(q & set(re.findall(r"[a-z_=]+", r["content"].lower()))))
        self.log.append({"op": "recall", "agent": agent, "query": query})
        return scored[:limit]


class PastDevMemory(SharedMemory):
    """past.dev Memory API: POST /api/v1/ingest (write), POST /api/v1/recall (read).
    The authoring agent goes in `identity`; recall reads across all project
    data, which is how agents see each other's facts."""
    backend = "past.dev"
    BASE = "https://api.past.dev/api/v1"

    def __init__(self, api_key: Optional[str] = None, run_tag: str = ""):
        self.key = api_key or os.environ.get("PAST_API_KEY")
        if not self.key:
            raise RuntimeError("PAST_API_KEY is not set")
        self.run_tag = run_tag
        self.log: List[dict] = []

    def _h(self):
        return {"Authorization": f"Bearer {self.key}"}

    def write(self, agent, content, label="", metadata=None):
        body = {"id": f"{agent}-{uuid.uuid4().hex[:12]}", "content": f"[author={agent}] {content}",
                "label": label or agent, "identity": agent,
                "metadata": {"author": agent, "run_tag": self.run_tag, **(metadata or {})}}
        out = post_json(f"{self.BASE}/ingest", body, self._h())
        self.log.append({"op": "write", "agent": agent, "content": content, "ingestionId": out.get("ingestionId")})

    def recall(self, agent, query, limit=50):
        out = post_json(f"{self.BASE}/recall", {"query": query, "identity": agent, "limit": limit},
                        self._h())
        rows = []
        for r in out.get("results", []):
            texts = [r.get("content", "")] + [e for s in r.get("sources", []) for e in s.get("excerpts", [])]
            for t in texts:
                m = re.search(r"\[author=([\w-]+)\]", t)
                rows.append({"author": m.group(1) if m else None, "content": t})
        self.log.append({"op": "recall", "agent": agent, "query": query, "n": len(rows)})
        return rows


def get_shared_memory(local_path: str, run_tag: str = "") -> SharedMemory:
    if os.environ.get("PAST_API_KEY"):
        return PastDevMemory(run_tag=run_tag)
    return LocalSharedMemory(local_path)
