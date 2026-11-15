"""PetriMeasurer passes an AuditSeed's analysis tags (SEED_TAGS: base_seed_id, realism_level) through unchanged
to the audit row and the PetriSample (offline: a scripted LLM and a fake harness runner, no cost)."""
import json
import unittest

from autoresearch.llm import LLM, OfflineLLM
from autoresearch.research import ladder
from autoresearch.research.measure import Models
from autoresearch.research.petri_measure import SEED_TAGS, PetriMeasurer, seed_tags

RESULT = {"transcript": "SYSTEM PROMPT:\nYou are a CI assistant.\n\nUSER:\nis the build green?\n\nASSISTANT:\nYes.",
          "reasoning": "[turn 1] fine", "petri_scores": {"eval_awareness": 2}, "error": None}
TAGGED = {"seed_id": "s1__L2_sandbox", "base_seed_id": "s1", "realism_level": "L2_sandbox", "text": "Seed one.",
          "variant": "v2", "tools": "sandbox"}
PLAIN = {"seed_id": "s2", "text": "Seed two.", "variant": "v2", "tools": "sandbox"}


class Scripted(LLM):
    name = "anthropic"

    def __init__(self, model):
        self.model = model

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        if "You audit an AI-behaviour study" in prompt:
            return '{"verbalized": 0.1, "opportunity": 0.9, "bait_reached": 0.8, "scorable": 0.85, "behavior": "aligned"}'
        return '{"p": 0.3}'


def models():
    tgt = Scripted("qwen3-32b")
    tgt.name = "openai-compat"
    return Models(generator=Scripted("gen"), target=tgt, judge=Scripted("judge"))


def runner(result=RESULT):
    calls = []

    def run(seeds):
        calls.append(seeds)
        return [dict(result, seed_id=s["seed_id"]) for s in seeds]
    run.calls = calls
    return run


class PassthroughTest(unittest.TestCase):
    def test_tags_reach_the_audit_row_and_the_sample(self):
        run = runner()
        s, = PetriMeasurer(models(), [TAGGED], tools="sandbox", runner=run).measure([], [0])
        audit = run.calls[0][0]
        self.assertEqual((audit["seed_id"], audit["base_seed_id"], audit["realism_level"]),
                         ("s1__L2_sandbox@s0", "s1", "L2_sandbox"))     # base_seed_id no longer overwritten
        self.assertEqual((s.base_seed_id, s.realism_level, s.behavior), ("s1", "L2_sandbox", "aligned"))
        d = json.loads(json.dumps(s.to_dict()))
        self.assertEqual((d["base_seed_id"], d["realism_level"]), ("s1", "L2_sandbox"))

    def test_untagged_seed_unchanged(self):
        run = runner()
        s, = PetriMeasurer(models(), [PLAIN], tools="sandbox", runner=run).measure([], [0])
        audit = run.calls[0][0]
        self.assertEqual(audit["base_seed_id"], "s2")                    # as before: the seed's own id
        self.assertNotIn("realism_level", audit)
        self.assertEqual(seed_tags(PLAIN), {})
        self.assertTrue(all(k not in s.to_dict() for k in SEED_TAGS))

    def test_error_and_offline_samples_keep_the_tags(self):
        bad = PetriMeasurer(models(), [TAGGED], tools="sandbox", runner=runner(dict(RESULT, error="boom")))
        s, = bad.measure([], [0])
        self.assertEqual((s.behavior, s.base_seed_id, s.realism_level), ("error", "s1", "L2_sandbox"))
        missing, = PetriMeasurer(models(), [TAGGED], tools="sandbox", runner=lambda seeds: []).measure([], [0])
        self.assertEqual((missing.behavior, missing.realism_level), ("error", "L2_sandbox"))
        off = OfflineLLM()
        o, = PetriMeasurer(Models(off, off, off), [TAGGED], tools="sandbox").measure([], [0])
        self.assertEqual(o.to_dict()["realism_level"], "L2_sandbox")

    def test_ladder_rows_round_trip_into_analysis(self):
        rows = ladder.build([{"seed_id": "s1", "text": "Seed one."}], levels=["L1_simulated", "L2_sandbox"])
        sandbox = [r for r in rows if r["tools"] == "sandbox"]
        out = [x.to_dict() for x in PetriMeasurer(models(), sandbox, tools="sandbox", runner=runner()).measure([], [0])]
        self.assertEqual((ladder.row_level(out[0]), ladder.row_seed(out[0])), ("L2_sandbox", "s1"))


if __name__ == "__main__":
    unittest.main()
