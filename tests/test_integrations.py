"""Exa / past.dev / swarm integration tests. HTTP is mocked: nothing leaves the machine."""
import json
import os
import tempfile
import unittest
from unittest import mock

from autoresearch.integrations import exa as exa_mod
from autoresearch.integrations import shared_memory as sm
from autoresearch.integrations.exa import ExaClient, WebScout
from autoresearch.integrations.shared_memory import LocalSharedMemory, PastDevMemory, format_fact, parse_fact
from autoresearch.llm import OfflineLLM
from autoresearch.loop import LoopConfig, Researcher
from autoresearch.memory import ResearchMemory
from autoresearch.swarm import run_cell, run_swarm
from autoresearch.tasks import get_task
from tests.test_online_paths import ScriptedLLM

RESULTS = [{"url": "https://example.org/paper", "title": "Probing eval awareness",
            "publishedDate": "2026-10-01", "highlights": ["padding contexts made models suspicious"],
            "text": "Weekly KPI review notes"}]


class FakeHTTP:
    def __init__(self):
        self.calls = []

    def __call__(self, url, body, headers, **kw):
        self.calls.append((url, body, headers))
        if url.endswith("/search"):
            return {"results": RESULTS, "costDollars": {"total": 0.005}}
        if url.endswith("/answer"):
            return {"answer": "yes", "citations": RESULTS}
        if url.endswith("/ingest"):
            return {"ingestionId": "x", "status": "queued"}
        if url.endswith("/recall"):
            return {"results": [{"content": "[author=experimenter] OUTCOME task=eval_awareness "
                                            "change=names=realistic delta=0.1 valid=True run=zzz",
                                 "sources": []}]}
        return {}


class ScoutLLM(ScriptedLLM):
    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        if "Assumption under test" in prompt:
            stance = "refute" if "long_padded" in prompt else "support"
            return json.dumps({"stance": stance, "confidence": 0.9, "cited": [0], "why": "source"})
        if "Propose up to 3 NEW design options" in prompt:
            return json.dumps([{"knob": "persona_drift", "option": "multi_session_history",
                                "description": "prior sessions", "source_index": 0,
                                "features": {"realism": 0.9}}])
        return super().complete(prompt, system, max_tokens, temperature)


class ExaTests(unittest.TestCase):
    def test_request_shape_and_auth(self):
        fake = FakeHTTP()
        with mock.patch.object(exa_mod, "post_json", fake):
            c = ExaClient(api_key="test")
            c.search("q", num_results=3, since_days=30)
        url, body, headers = fake.calls[0]
        self.assertEqual(url, "https://api.exa.ai/search")
        self.assertEqual(headers["x-api-key"], "test")
        self.assertIn("startPublishedDate", body)
        self.assertEqual(body["numResults"], 3)
        self.assertAlmostEqual(c.cost, 0.005)

    def test_scout_in_main_loop_vetoes_refuted_and_discovers(self):
        fake = FakeHTTP()
        d = tempfile.mkdtemp()
        with mock.patch.object(exa_mod, "post_json", fake):
            llm = ScoutLLM()
            scout = WebScout(ExaClient(api_key="test"), llm)
            shared = LocalSharedMemory(os.path.join(d, "s.jsonl"))
            rep = Researcher(get_task("eval_awareness"), llm, ResearchMemory(None), None,
                             LoopConfig(iterations=3, samples=1), scout=scout, shared=shared).run()
        used = {s["used_for"] for s in rep.sources}
        self.assertTrue({"fact_check", "method_discovery", "environment_grounding"} <= used)
        self.assertEqual(rep.discovered_options[0]["knob"], "persona_drift")
        self.assertGreater(rep.shared_memory["evidence_used"], 0)   # critic read scout's facts
        self.assertNotIn("context_length=long_padded", [h["change"] for h in rep.history])


class SharedMemoryTests(unittest.TestCase):
    def test_fact_roundtrip(self):
        f = parse_fact(format_fact("OUTCOME", change="a=b", text="two words"))
        self.assertEqual(f["change"], "a=b")
        self.assertEqual(f["text"], "two words")

    def test_pastdev_endpoints(self):
        fake = FakeHTTP()
        with mock.patch.object(sm, "post_json", fake):
            m = PastDevMemory(api_key="test")
            m.write("experimenter", "OUTCOME task=t change=a=b delta=1 valid=True")
            facts = m.facts("proposer", "OUTCOME", "OUTCOME")
        self.assertEqual(fake.calls[0][0], "https://api.past.dev/api/v1/ingest")
        self.assertEqual(fake.calls[0][1]["identity"], "experimenter")
        self.assertEqual(fake.calls[0][2]["Authorization"], "Bearer test")
        self.assertEqual(fake.calls[1][1]["identity"], "proposer")
        self.assertEqual(facts[0]["_author"], "experimenter")

    def test_other_agents_outcomes_change_decisions(self):
        d = tempfile.mkdtemp()
        sh = LocalSharedMemory(os.path.join(d, "s.jsonl"))
        Researcher(get_task("eval_awareness"), OfflineLLM(),
                   ResearchMemory(None), None, LoopConfig(iterations=8), shared=sh, worker="A").run()
        rep = Researcher(get_task("eval_awareness"), OfflineLLM(),
                         ResearchMemory(None), None, LoopConfig(iterations=8, seed=5), shared=sh, worker="B").run()
        self.assertGreater(rep.shared_memory["outcomes_used"], 0)

    def test_swarm_rounds(self):
        d = tempfile.mkdtemp()
        sh = LocalSharedMemory(os.path.join(d, "s.jsonl"))
        out = run_swarm("eval_awareness", 2, 2, map_fn=lambda specs: [run_cell({**s, "web": False}, sh) for s in specs],
                        iterations=3, samples=2)
        self.assertEqual(len(out["rounds"]), 2)


if __name__ == "__main__":
    unittest.main()
