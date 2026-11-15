"""Run EvalAwareBench's judge prompt (judgePromptEvidenceBoth.txt) on each run, twice:

  mode "reasoning": the target's reasoning text goes in the {reasoning} slot.
  mode "output":    the target's visible output (text + tool calls) goes in the {reasoning} slot.

The prompt bases its awareness verdict only on the {reasoning} slot, so swapping what goes
there gives a reasoning-level and an output-level verdict from the same judge. {answer} is
left as a placeholder so the judge cannot read the other channel. Unlike the original code,
nothing is truncated to 200 characters, and any Inspect model can be the judge.

Usage: python eab_judge.py [--limit N]   -> out/eab.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re

from inspect_ai.model import ChatMessageSystem, GenerateConfig, get_model

from common import OUT, ROOT, load_config, read_jsonl, write_jsonl

TEMPLATE = (ROOT / "prompts" / "judgePromptEvidenceBoth.txt").read_text()
OMITTED = "(not shown to the judge)"


def _escape(s: str) -> str:
    # The template embeds the texts inside a JSON-looking block; keep it parseable for the judge.
    return json.dumps(s, ensure_ascii=False)[1:-1]


def parse(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def summarize(j: dict) -> dict:
    ma, hr = j.get("model_awareness", {}) or {}, j.get("hypothetical_recognition", {}) or {}
    yes = lambda d: str(d.get("conclusion", "")).strip().lower().startswith("y")
    return {
        "aware": yes(ma) if ma else None,
        "awareness_type": ma.get("awareness_type"),
        "hypothetical": yes(hr) if hr else None,
        "evidence": ma.get("evidence", []),
        "hypothetical_evidence": hr.get("evidence", []),
    }


async def judge_one(model, sem, rec: dict, mode: str) -> dict:
    text = rec["reasoning"] if mode == "reasoning" else rec["output"]
    base = {"run_id": rec["run_id"], "mode": mode}
    if not text.strip():
        return {**base, "aware": None, "skipped": "empty"}
    prompt = TEMPLATE.format(task=_escape(rec["task_text"][:4000]), reasoning=_escape(text), answer=OMITTED)
    async with sem:
        for attempt in range(3):
            out = await model.generate([ChatMessageSystem(content=prompt)])
            j = parse(out.completion)
            if j.get("model_awareness"):
                return {**base, **summarize(j), "raw": out.completion}
    return {**base, "aware": None, "skipped": "unparseable", "raw": out.completion}


async def run(limit: int | None, concurrency: int):
    cfg = load_config()
    model = get_model(cfg["models"]["eab_judge"], config=GenerateConfig(max_tokens=16000))
    recs = read_jsonl(OUT / "records.jsonl")[:limit]
    done = {(r["run_id"], r["mode"]) for r in read_jsonl(OUT / "eab.jsonl") if r.get("aware") is not None}
    prev = [r for r in read_jsonl(OUT / "eab.jsonl") if (r["run_id"], r["mode"]) in done]
    sem = asyncio.Semaphore(concurrency)
    todo = [(r, m) for r in recs for m in ("reasoning", "output") if (r["run_id"], m) not in done]
    print(f"judging {len(todo)} (run, mode) pairs; {len(prev)} already done")
    new = await asyncio.gather(*(judge_one(model, sem, r, m) for r, m in todo))
    write_jsonl(OUT / "eab.jsonl", prev + list(new))
    print(f"{sum(1 for r in new if r.get('aware') is None)} skipped or unparseable")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    asyncio.run(run(a.limit, a.concurrency))
