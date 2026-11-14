"""Exercise every online-only code path (LLM generator/judge, LLM proposer,
LLM taste extraction, LLM relevance gate, LLM insight distillation) with a
scripted stand-in for the API, so the Anthropic mode is tested without a key."""
import json
import unittest
from unittest import mock

from autoresearch.llm import AnthropicLLM, Budget, BudgetExceeded, ClaudeCLILLM, LLM
from autoresearch.loop import LoopConfig, Researcher
from autoresearch.memory import ResearchMemory
from autoresearch.taste.extract import profile_from_texts
from autoresearch.tasks import get_task


class ScriptedLLM(LLM):
    """Answers by recognising which prompt template it was sent."""
    name = "scripted"

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.budget.charge(len(prompt) // 4, 50)
        if prompt.startswith("Write a single realistic deployment transcript"):
            return "SYSTEM: You are Atlas...\nUser: hey can u check the Q3 numbers"
        if prompt.startswith("You are auditing"):
            env = prompt.split("ENVIRONMENT:")[1]
            p = 0.9 if "evaluation" in env.lower() else 0.2
            return json.dumps({"p_eval": p, "validity": 0.85})
        if "Candidate changes:" in prompt:
            opts = [l[2:] for l in prompt.splitlines() if l.startswith("- ")]
            return json.dumps([{"change": o, "hypothesis": "makes deployment realistic so the "
                                "model is not aware it is evaluated"} for o in opts[:3]])
        if prompt.startswith("Goal:"):
            return '{"relevance": 0.8}'
        if prompt.startswith("Read the following writing"):
            return json.dumps({"principles": ["measure in deployment-like settings"],
                               "weights": {"realism": 0.9, "risk": -0.5}})
        if prompt.startswith("Summarise"):
            return "- realism helps\n- keep the probe intact"
        return "ok"  # target model reply


class OnlinePathTests(unittest.TestCase):
    def test_full_online_loop(self):
        llm = ScriptedLLM(Budget())
        rep = Researcher(get_task("eval_awareness"), llm, ResearchMemory(None), None,
                         LoopConfig(iterations=3, samples=2)).run()
        self.assertEqual(len(rep.history), 4)
        self.assertIn("realism helps", rep.insights)
        self.assertGreater(llm.budget.calls, 10)

    def test_llm_taste_extraction(self):
        p = profile_from_texts("x", [("research", "some text")], ScriptedLLM())
        self.assertEqual(p.weights["realism"], 0.9)
        self.assertEqual(p.principles, ["measure in deployment-like settings"])

    def test_anthropic_http_request_shape(self):
        sent = {}

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self):
                return json.dumps({"content": [{"type": "text", "text": "hi"}],
                                   "usage": {"input_tokens": 5, "output_tokens": 1}}).encode()

        def fake_urlopen(req, timeout):
            sent["body"] = json.loads(req.data)
            sent["headers"] = dict(req.header_items())
            return Resp()

        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), \
                mock.patch("urllib.request.urlopen", fake_urlopen):
            llm = AnthropicLLM(model="claude-sonnet-5-5")
            self.assertEqual(llm.complete("hello", system="sys"), "hi")
        self.assertEqual(sent["body"]["model"], "claude-sonnet-5-5")
        self.assertEqual(sent["body"]["system"], "sys")
        self.assertEqual(llm.budget.input_tokens, 5)

    def test_claude_cli_backend(self):
        out = json.dumps({"result": "pong", "is_error": False,
                          "usage": {"input_tokens": 7, "output_tokens": 1}})
        done = mock.Mock(returncode=0, stdout=out, stderr="")
        with mock.patch("subprocess.run", return_value=done) as run:
            llm = ClaudeCLILLM(model="claude-sonnet-5-5")
            self.assertEqual(llm.complete("ping", system="s"), "pong")
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[cmd.index("--system-prompt") + 1], "s")
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "")
        self.assertEqual(run.call_args[1]["input"], "ping")
        self.assertEqual(llm.budget.input_tokens, 7)

    def test_claude_cli_refuses_calls_once_cost_cap_is_reached(self):
        out = json.dumps({"result": "pong", "is_error": False, "total_cost_usd": 0.06,
                          "usage": {"input_tokens": 7, "output_tokens": 1}})
        done = mock.Mock(returncode=0, stdout=out, stderr="")
        with mock.patch("subprocess.run", return_value=done) as run:
            llm = ClaudeCLILLM(model="claude-sonnet-5-5", budget=Budget(max_cost_usd=0.10))
            llm.complete("ping")
            llm.complete("ping")
            with self.assertRaises(BudgetExceeded):
                llm.complete("ping")
        self.assertEqual(run.call_count, 2)
        self.assertTrue(llm.budget.exhausted())


if __name__ == "__main__":
    unittest.main()
