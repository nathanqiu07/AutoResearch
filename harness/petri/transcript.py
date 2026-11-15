"""Turn one Petri sample (an Inspect EvalSample) into an AuditResult row."""
from __future__ import annotations

import json
import re

KEEP_SCORES = ["eval_awareness", "audit_situational_awareness", "scenario_realism", "auditor_failure",
               "concerning", "unprompted_deception_toward_user", "cooperation_with_human_misuse"]
_TAG_RE = re.compile(r"<(think|thinking|reasoning|scratchpad)>(.*?)</\1>", re.S | re.I)


def split_text(text: str):
    """(reasoning, visible) for text that may hold <thinking>-style spans."""
    reasoning = "\n".join(m.group(2).strip() for m in _TAG_RE.finditer(text or ""))
    return reasoning, _TAG_RE.sub("", text or "").strip()


def split_assistant(msg):
    """Reasoning and visible output for one assistant message: native reasoning
    blocks plus <thinking> spans; output = remaining text plus tool calls."""
    reasoning, output = [], []
    content = msg.content if not isinstance(msg.content, str) else [msg.content]
    for c in content:
        if isinstance(c, str):
            r, o = split_text(c)
        elif getattr(c, "type", None) == "reasoning":
            r, o = ("" if getattr(c, "redacted", False) else (c.reasoning or "")), ""
        elif getattr(c, "type", None) == "text":
            r, o = split_text(c.text)
        else:
            r, o = "", ""
        if r:
            reasoning.append(r)
        if o:
            output.append(o)
    for tc in getattr(msg, "tool_calls", None) or []:
        output.append(f"[tool call {tc.id}] {tc.function}({json.dumps(tc.arguments, ensure_ascii=False)})")
    return "\n".join(reasoning).strip(), "\n".join(output).strip()


def render(messages) -> str:
    """The target's conversation as plain text, without its private reasoning."""
    parts = []
    for m in messages:
        role = getattr(m, "role", "")
        if role == "system":
            parts.append(f"SYSTEM PROMPT:\n{m.text}")
        elif role == "user":
            parts.append(f"USER:\n{m.text}")
        elif role == "assistant":
            parts.append(f"ASSISTANT:\n{split_assistant(m)[1]}")
        elif role == "tool":
            name = getattr(m, "function", "") or "tool"
            err = getattr(m, "error", None)
            body = m.text + (f"\n[error] {err.message}" if err is not None else "")
            parts.append(f"TOOL RESULT ({name}):\n{body}")
    return "\n\n".join(parts)


def petri_scores(sample):
    """Petri's judge scores; None where its judge reply failed to parse."""
    for s in (sample.scores or {}).values():
        if isinstance(s.value, dict) and "eval_awareness" in s.value:
            expl = s.explanation or ""
            if expl.startswith("Failed to parse"):
                return {k: None for k in KEEP_SCORES}, "failed"
            return ({k: s.value.get(k) for k in KEEP_SCORES},
                    "partial" if expl.startswith("Partial parse") else "ok")
    return {k: None for k in KEEP_SCORES}, "missing"


def _target_messages(sample, add_only: bool):
    try:
        from petri.transcript.transcript import Event, _collect_messages
        from pydantic import TypeAdapter
    except ImportError:  # pragma: no cover
        return []
    for k, v in (sample.store or {}).items():
        if k.split(":")[-1] == "events" and "AuditStore" in k:
            events = TypeAdapter(list[Event]).validate_python(v)
            return _collect_messages(events, "target", add_only=add_only) if events else []
    return []


def record_from_sample(sample) -> dict:
    md = sample.metadata or {}
    final = _target_messages(sample, add_only=False)
    every = _target_messages(sample, add_only=True)
    reasoning, turn = [], 0
    for m in every:
        if getattr(m, "role", "") == "assistant":
            turn += 1
            r, _ = split_assistant(m)
            if r:
                reasoning.append(f"[turn {turn}] {r}")
    scores, status = petri_scores(sample)
    return {
        "seed_id": md.get("seed_id", str(sample.id)),
        "variant": md.get("variant"),
        "tools": md.get("tools"),
        "epoch": sample.epoch,
        "transcript": render(final),
        "reasoning": "\n\n".join(reasoning),
        "petri_scores": scores,
        "petri_judge_status": status,
        "n_target_turns": turn,
        "error": str(sample.error.message) if sample.error else None,
    }
