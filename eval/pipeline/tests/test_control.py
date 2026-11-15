"""Offline test of control.py's rewrite parsing and validation with a mock rewriter."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import control
from inspect_ai.model import ModelOutput
GOOD = "<seed>Line one\nline two</seed><auditor_prompt>Run {max_turns} turns on {target_model}. Seed: {seed_instructions}. {today_date} {resources_prompt} JSON {{x}}</auditor_prompt>"
BAD = "<seed>x</seed><auditor_prompt>no placeholders {oops}</auditor_prompt>"
class M:
    def __init__(self, outs): self.outs = list(outs)
    async def generate(self, msgs, **k): return ModelOutput.from_content("m", self.outs.pop(0))
s, p, prob = asyncio.run(control.rewrite(M([BAD, GOOD]), "orig", "orig {max_turns}", ""))
assert prob == [] and "\n" not in s and "{seed_instructions}" in p, (s, p, prob)
s, p, prob = asyncio.run(control.rewrite(M([BAD, BAD, BAD]), "orig", "orig", ""))
assert s == "orig" and prob, prob
print("control rewrite ok")
