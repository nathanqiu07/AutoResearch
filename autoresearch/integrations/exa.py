"""Exa client plus the WebScout agent that runs inside the research loop.

The scout does three things model knowledge alone cannot:
  1. fact-check: before the loop commits to an experiment, it searches recent
     sources for evidence on the assumption the experiment rests on, and the
     verdict (with URLs) feeds the assumption ledger and the drift critic;
  2. discover methods: on re-anchor iterations it searches for newly published
     techniques against eval-awareness and turns them into new design options
     the loop can test;
  3. ground environments: it fetches real public workflow documents so the
     generator builds environments from real artifacts, not invented ones.
Every source used is recorded with what it was used for, so output is checkable.
Key: EXA_API_KEY (never stored or logged)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..llm import LLM, OfflineLLM, extract_json
from .http import post_json

BASE = "https://api.exa.ai"


def _filters(start_date, end_date, include_domains, exclude_domains, include_text, exclude_text) -> dict:
    out = {}
    if start_date:
        out["startPublishedDate"] = f"{start_date}T00:00:00Z"
    if end_date:
        out["endPublishedDate"] = f"{end_date}T00:00:00Z"
    for key, value in (("includeDomains", include_domains), ("excludeDomains", exclude_domains),
                       ("includeText", include_text), ("excludeText", exclude_text)):
        if value:
            out[key] = list(value)
    return out


class ExaClient:
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        self.key = api_key or os.environ.get("EXA_API_KEY")
        if not self.key:
            raise RuntimeError("EXA_API_KEY is not set")
        self.cache_dir = cache_dir
        self.cost = 0.0
        self.calls = 0

    def _post(self, path, body):
        ck = None
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            ck = os.path.join(self.cache_dir, hashlib.sha256(
                (path + json.dumps(body, sort_keys=True)).encode()).hexdigest()[:24] + ".json")
            if os.path.exists(ck):
                return json.load(open(ck))
        # Deep search and long-page fetches can take minutes; the default 60s would pay twice.
        out = post_json(BASE + path, body, {"x-api-key": self.key}, timeout=300)
        self.calls += 1
        self.cost += float((out.get("costDollars") or {}).get("total", 0.0))
        if ck:
            json.dump(out, open(ck, "w"))
        return out

    def search(self, query, num_results=5, since_days=None, highlights_query=None,
               category=None, text_chars=0, *, start_date=None, end_date=None,
               include_domains=None, exclude_domains=None, include_text=None, exclude_text=None,
               search_type="auto", summary=None, max_age_hours=None):
        """Dates are YYYY-MM-DD. includeText/excludeText are deprecated upstream and match
        approximately, so callers must not rely on them alone."""
        body = {"query": query, "type": search_type, "numResults": num_results,
                "contents": {"highlights": {"query": highlights_query or query,
                                            "maxCharacters": 800}}}
        if text_chars:
            body["contents"]["text"] = {"maxCharacters": text_chars}
        if summary:
            body["contents"]["summary"] = summary
        if max_age_hours is not None:
            body["contents"]["maxAgeHours"] = max_age_hours
        if since_days:
            start = dt.datetime.utcnow() - dt.timedelta(days=since_days)
            body["startPublishedDate"] = start.strftime("%Y-%m-%dT00:00:00Z")
        if category:
            body["category"] = category
        body.update(_filters(start_date, end_date, include_domains, exclude_domains, include_text, exclude_text))
        return self._post("/search", body).get("results", [])

    def deep(self, query, output_schema, *, additional_queries=None, system_prompt=None, num_results=25,
             start_date=None, end_date=None, include_domains=None):
        """Deep search; the structured answer is at response["output"]["content"]."""
        body = {"query": query, "type": "deep", "numResults": num_results, "outputSchema": output_schema}
        if additional_queries:
            body["additionalQueries"] = additional_queries
        if system_prompt:
            body["systemPrompt"] = system_prompt
        body.update(_filters(start_date, end_date, include_domains, None, None, None))
        return self._post("/search", body)

    def contents(self, urls, text_chars=4000, *, summary=None, max_age_hours=None, subpages=0,
                 subpage_target=None):
        body = {"urls": urls, "text": {"maxCharacters": text_chars}}
        if summary:
            body["summary"] = summary
        if max_age_hours is not None:
            body["maxAgeHours"] = max_age_hours
        if subpages:
            body["subpages"] = subpages
        if subpage_target:
            body["subpageTarget"] = subpage_target
        return self._post("/contents", body).get("results", [])

    def answer(self, query):
        out = self._post("/answer", {"query": query, "model": "exa"})
        return out.get("answer", ""), out.get("citations", [])


@dataclass
class Source:
    url: str
    title: str
    published: Optional[str]
    used_for: str
    detail: str = ""


@dataclass
class WebScout:
    exa: ExaClient
    llm: LLM
    since_days: int = 540
    sources: List[Source] = field(default_factory=list)

    def _log(self, results, used_for, detail=""):
        for r in results:
            self.sources.append(Source(r.get("url", ""), r.get("title") or "", r.get("publishedDate"),
                                       used_for, detail))

    # 1. fact-check an assumption ------------------------------------------
    def check_assumption(self, task_goal: str, change: str, hypothesis: str) -> Dict:
        q = f"language model evaluation awareness: does {change.replace('_', ' ').replace('=', ' ')} make tests look less like tests"
        res = self.exa.search(q, num_results=5, since_days=self.since_days,
                              highlights_query=f"evidence about {change} and models detecting evaluations")
        self._log(res, "fact_check", change)
        if not res:
            return {"stance": "none", "confidence": 0.0, "urls": []}
        evidence = "\n".join(f"[{i}] {r.get('title')} ({r.get('url')}): {' '.join(r.get('highlights') or [])[:600]}"
                             for i, r in enumerate(res))
        if isinstance(self.llm, OfflineLLM):
            return {"stance": "unjudged", "confidence": 0.0, "urls": [r["url"] for r in res]}
        out = extract_json(self.llm.complete(
            f"Goal: {task_goal}\nAssumption under test: {hypothesis}\nWeb evidence:\n{evidence}\n"
            "Does the evidence support or refute the assumption? Return JSON {\"stance\": "
            "\"support\"|\"refute\"|\"none\", \"confidence\": 0-1, \"cited\": [indices], \"why\": str}. "
            "Use 'none' if the sources do not address it.", temperature=0.0)) or {}
        cited = [res[i]["url"] for i in out.get("cited", []) if isinstance(i, int) and i < len(res)]
        return {"stance": out.get("stance", "none"), "confidence": float(out.get("confidence", 0)),
                "why": out.get("why", ""), "urls": cited or [r["url"] for r in res[:2]]}

    # 2. discover new methods ----------------------------------------------
    def discover_options(self, task_goal: str, search_space: Dict[str, List[str]]) -> List[Dict]:
        res = self.exa.search("new techniques to reduce evaluation awareness in LLM benchmarks "
                              "realistic agentic environments", num_results=6, since_days=self.since_days,
                              )
        self._log(res, "method_discovery")
        if not res or isinstance(self.llm, OfflineLLM):
            return []
        evidence = "\n".join(f"[{i}] {r.get('title')} ({r.get('url')}): {' '.join(r.get('highlights') or [])[:600]}"
                             for i, r in enumerate(res))
        out = extract_json(self.llm.complete(
            f"Goal: {task_goal}\nCurrent design knobs: {json.dumps(search_space)}\nRecent sources:\n{evidence}\n"
            "Propose up to 3 NEW design options taken from these sources that are not already knobs/options. "
            "Return JSON list of {\"knob\": snake_case, \"option\": snake_case, \"description\": str, "
            "\"source_index\": int, \"features\": {realism|grounding|simplicity|novelty|cost|risk|validity_care: 0-1}}.",
            temperature=0.3)) or []
        found = []
        for o in out if isinstance(out, list) else []:
            if not (isinstance(o, dict) and o.get("knob") and o.get("option")):
                continue
            i = o.get("source_index")
            o["source_url"] = res[i]["url"] if isinstance(i, int) and i < len(res) else res[0]["url"]
            found.append(o)
        return found

    # 3. ground environments in real artifacts ------------------------------
    def grounding_material(self, topic: str, n: int = 2) -> List[str]:
        res = self.exa.search(f"{topic} real internal team workflow writeup", num_results=n, text_chars=1500)
        self._log(res, "environment_grounding", topic)
        return [f"{r.get('title')}: {(r.get('text') or '')[:1200]}" for r in res]


def get_scout(llm: LLM, cache_dir: Optional[str] = None) -> Optional[WebScout]:
    if not os.environ.get("EXA_API_KEY"):
        return None
    return WebScout(ExaClient(cache_dir=cache_dir), llm)
