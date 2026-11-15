"""Shared helpers: config, condition layout, and splitting target turns into reasoning vs output.

Condition layout (one folder per condition, split and seed):
    conditions/<condition>/<split>/<seed_id>/seed.txt
    conditions/<condition>/<split>/<seed_id>/auditor_prompt.txt
Every condition (stock, control, taste_mismatched, taste_real) uses this same layout,
so the runner never needs to know where a rewrite came from.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CONDITIONS = ROOT / "conditions"
# Results are kept apart per config, so Kimi and Sonnet runs never mix:
# config.yaml -> out/config/, config_sonnet45.yaml -> out/config_sonnet45/
OUT = ROOT / "out" / Path(os.environ.get("PIPELINE_CONFIG") or "config.yaml").stem
PLACEHOLDERS = ["{max_turns}", "{target_model}", "{seed_instructions}", "{today_date}", "{resources_prompt}"]


def load_config(path: str | Path | None = None) -> dict:
    """Config file: explicit path, else $PIPELINE_CONFIG, else config.yaml (Kimi target).
    Use PIPELINE_CONFIG=config_sonnet45.yaml for the Sonnet 4.5 extended-thinking target."""
    return yaml.safe_load(Path(path or os.environ.get("PIPELINE_CONFIG") or ROOT / "config.yaml").read_text())


def target_model(cfg: dict):
    """The target as an Inspect Model, with extended thinking if target_reasoning_tokens is set.
    Thinking (summaries on Claude 4.x) comes back as reasoning blocks, which the extractor
    routes to the reasoning-side judge."""
    from inspect_ai.model import GenerateConfig, get_model

    budget = cfg["models"].get("target_reasoning_tokens")
    if not budget:
        return get_model(cfg["models"]["target"])
    return get_model(cfg["models"]["target"], config=GenerateConfig(reasoning_tokens=budget, max_tokens=budget + 8000))


def iter_condition_seeds(condition: str, split: str):
    base = CONDITIONS / condition / split
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        yield d.name, d / "seed.txt", d / "auditor_prompt.txt"


def check_auditor_prompt(text: str) -> list[str]:
    """Problems that would make Petri crash or silently change the setup."""
    problems = [f"missing placeholder {p}" for p in PLACEHOLDERS if p not in text]
    stripped = text
    for p in PLACEHOLDERS:
        stripped = stripped.replace(p, "")
    stripped = stripped.replace("{{", "").replace("}}", "")
    if re.search(r"[{}]", stripped):
        problems.append("unescaped literal brace (use {{ and }})")
    return problems


# ---------------------------------------------------------------- reasoning vs output

_TAG_RE = re.compile(r"<(think|thinking|reasoning|scratchpad)>(.*?)</\1>", re.S | re.I)


def split_text(text: str) -> tuple[str, str]:
    """Pull <think>/<thinking>-style spans out of visible text."""
    reasoning = "\n".join(m.group(2).strip() for m in _TAG_RE.finditer(text))
    output = _TAG_RE.sub("", text).strip()
    return reasoning, output


def split_assistant(msg) -> tuple[str, str]:
    """Reasoning and visible output for one Inspect ChatMessageAssistant.

    Reasoning = native reasoning blocks (full CoT for Kimi, summaries for Claude) plus
    any thinking-tag scratchpad in the text. Output = remaining text plus tool calls,
    since a tool call is something the target visibly does.
    """
    reasoning_parts, output_parts = [], []
    content = msg.content
    if isinstance(content, str):
        content = [content]
    for c in content:
        if isinstance(c, str):
            r, o = split_text(c)
        elif getattr(c, "type", None) == "reasoning":
            r, o = (c.reasoning or "") if not getattr(c, "redacted", False) else "", ""
        elif getattr(c, "type", None) == "text":
            r, o = split_text(c.text)
        else:
            r, o = "", ""
        if r:
            reasoning_parts.append(r)
        if o:
            output_parts.append(o)
    for tc in getattr(msg, "tool_calls", None) or []:
        output_parts.append(f"[tool call] {tc.function}({json.dumps(tc.arguments, ensure_ascii=False)})")
    return "\n".join(reasoning_parts).strip(), "\n".join(output_parts).strip()


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
