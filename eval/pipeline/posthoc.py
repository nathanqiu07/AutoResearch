"""Post-hoc 'was this an evaluation?' question, asked on a copy of each finished run.

For each run, the target's final-branch conversation is copied, one fixed yes/no phrasing
is appended as a user turn, and the target answers several times per phrasing. P(eval) is
the share of yes answers across all phrasings and samples. The live run is never touched.

The same thing can be run on real deployment transcripts (a JSONL file, one
{"id": ..., "messages": [...]} per line in OpenAI/Inspect chat format) to get the
negatives for the AUROC: python posthoc.py --real real_transcripts.jsonl

If the endpoint rejects the native tool-call history, the transcript is flattened into
plain text for that run and the record is marked flattened=true.

Usage: python posthoc.py [--limit N] [--real FILE]   -> out/posthoc.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re

from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageUser, GenerateConfig, get_model
from pydantic import TypeAdapter

from common import OUT, load_config, read_jsonl, split_text, target_model, write_jsonl

_msgs = TypeAdapter(list[ChatMessage])


def clean_history(msgs: list) -> list:
    # Drop a trailing assistant turn whose tool calls never got results.
    while msgs and isinstance(msgs[-1], ChatMessageAssistant) and msgs[-1].tool_calls:
        msgs = msgs[:-1]
    return msgs


def flatten(msgs: list) -> list:
    lines = []
    for m in msgs:
        if m.role == "system":
            continue
        body = m.text
        if isinstance(m, ChatMessageAssistant) and m.tool_calls:
            body += "".join(f"\n[tool call] {t.function}({json.dumps(t.arguments)})" for t in m.tool_calls)
        lines.append(f"{m.role.upper()}: {body}")
    system = [m for m in msgs if m.role == "system"]
    return system + [ChatMessageUser(content="Here is our previous interaction:\n\n" + "\n\n".join(lines))]


def parse_yes_no(text: str) -> int | None:
    _, visible = split_text(text)
    t = (visible or text).strip().lower()
    m = re.search(r"\b(yes|no)\b", t)
    return None if not m else int(m.group(1) == "yes")


async def ask(model, sem, run_id: str, msgs: list, phrasings: list[str], n: int, temp: float | None) -> dict:
    msgs = clean_history(msgs)
    gen_cfg = GenerateConfig(temperature=temp) if temp is not None else GenerateConfig()
    answers, flattened = [], False
    for pi, q in enumerate(phrasings):
        for _ in range(n):
            async with sem:
                try:
                    hist = flatten(msgs) if flattened else msgs
                    out = await model.generate(hist + [ChatMessageUser(content=q)], config=gen_cfg)
                except Exception:
                    if flattened:
                        raise
                    flattened = True
                    out = await model.generate(flatten(msgs) + [ChatMessageUser(content=q)], config=gen_cfg)
            answers.append({"phrasing": pi, "yes": parse_yes_no(out.completion), "raw": out.completion[-500:]})
    valid = [a["yes"] for a in answers if a["yes"] is not None]
    return {
        "run_id": run_id,
        "p_eval": sum(valid) / len(valid) if valid else None,
        "n_valid": len(valid),
        "flattened": flattened,
        "answers": answers,
    }


async def run(limit, real, concurrency):
    cfg = load_config()
    ph = cfg["posthoc"]
    model = target_model(cfg)
    out_path = OUT / ("posthoc_real.jsonl" if real else "posthoc.jsonl")
    prev = [r for r in read_jsonl(out_path) if r.get("p_eval") is not None]
    done = {r["run_id"] for r in prev}
    if real:
        items = [(f"real|{r['id']}", _msgs.validate_python(r["messages"])) for r in read_jsonl(real)]
    else:
        items = [(r["run_id"], _msgs.validate_python(r["final_messages"])) for r in read_jsonl(OUT / "records.jsonl")]
    items = [i for i in items[:limit] if i[0] not in done and i[1]]
    print(f"asking {len(items)} transcripts x {len(ph['phrasings'])} phrasings x {ph['samples_per_phrasing']}")
    sem = asyncio.Semaphore(concurrency)
    new = await asyncio.gather(
        *(ask(model, sem, rid, m, ph["phrasings"], ph["samples_per_phrasing"], ph["temperature"]) for rid, m in items),
        return_exceptions=True,
    )
    ok = [r for r in new if isinstance(r, dict)]
    for e in (r for r in new if not isinstance(r, dict)):
        print("error:", repr(e)[:300])
    write_jsonl(out_path, prev + ok)
    print(f"wrote {len(prev) + len(ok)} to {out_path.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--real")
    ap.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    asyncio.run(run(a.limit, a.real, a.concurrency))
