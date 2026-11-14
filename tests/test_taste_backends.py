import json
import io
import subprocess
import unittest
from unittest.mock import patch
from autoresearch.llm import Budget


class CodexBackendTests(unittest.TestCase):
    def test_reads_final_message_usage_and_uses_isolated_execution(self):
        from autoresearch.taste.backends import CodexLLM
        events = [{"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok":true}'}},
                  {"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 4}}]
        response = subprocess.CompletedProcess([], 0, "\n".join(map(json.dumps, events)), "")
        with patch("autoresearch.taste.backends.subprocess.run", return_value=response) as run:
            llm = CodexLLM(model="test-model")
            self.assertEqual(llm.complete("q"), '{"ok":true}')
        args, kwargs = run.call_args
        self.assertIn("--ignore-user-config", args[0])
        self.assertIn("--ephemeral", args[0])
        self.assertIn("read-only", args[0])
        self.assertEqual(kwargs["input"].count("q"), 1)
        self.assertEqual(llm.budget.output_tokens, 4)

    def test_tool_activity_and_failed_turns_are_not_valid_predictions(self):
        from autoresearch.taste.backends import CodexLLM
        for event in ({"type": "item.completed", "item": {"type": "command_execution"}},
                      {"type": "turn.failed", "error": {"message": "failed"}}):
            response = subprocess.CompletedProcess([], 0, json.dumps(event), "")
            with patch("autoresearch.taste.backends.subprocess.run", return_value=response):
                with self.assertRaises(RuntimeError):
                    CodexLLM().complete("q")


class OpenAIBackendTests(unittest.TestCase):
    def backend(self, **kwargs):
        from autoresearch.taste import backends
        self.assertTrue(hasattr(backends, "OpenAILLM"), "direct OpenAI backend is missing")
        return backends.OpenAILLM(**kwargs)

    def response(self, **overrides):
        data = {"status": "completed", "output": [{"type": "message", "role": "assistant",
                "status": "completed", "content": [{"type": "output_text", "text": '{"ok":true}'}]}],
                "usage": {"input_tokens": 10, "output_tokens": 5}}
        data.update(overrides)
        return io.BytesIO(json.dumps(data).encode())

    def test_schema_usage_and_bounded_timeout(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "private-test-key", "OPENAI_ORG_ID": "org-test",
                                      "OPENAI_PROJECT_ID": "proj-test"}), \
             patch("urllib.request.urlopen", return_value=self.response()) as network:
            llm = self.backend(max_usd=.01, budget=Budget(max_seconds=10), timeout=30)
            self.assertEqual(llm.complete("question", system="instruction", max_tokens=20), '{"ok":true}')
        request = network.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["model"], "gpt-6-luna")
        self.assertEqual(body["reasoning"], {"effort": "none"})
        self.assertEqual(body["service_tier"], "default")
        self.assertFalse(body["store"])
        self.assertNotIn("temperature", body)
        self.assertNotIn("tools", body)
        self.assertEqual(body["max_output_tokens"], 20)
        self.assertEqual(request.get_header("Openai-organization"), "org-test")
        self.assertLessEqual(network.call_args.kwargs["timeout"], 10)
        self.assertEqual(llm.budget.input_tokens, 10)
        self.assertEqual(llm.budget.calls, 1)
        self.assertGreater(llm.budget.cost_usd, 0)
        self.assertEqual(llm.cost_summary()["reserved_usd"], 0)
        self.assertNotIn("private-test-key", repr(llm.cost_summary()))

    def test_budget_and_unknown_model_reject_before_network(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "private-test-key"}), \
             patch("urllib.request.urlopen") as network:
            with self.assertRaises(ValueError):
                self.backend(model="unpriced-model", max_usd=1)
            for kwargs in [{"max_usd": 1e-10}, {"max_usd": 1, "budget": Budget(max_calls=0)}]:
                with self.assertRaises(RuntimeError):
                    self.backend(**kwargs).complete("question")
            with self.assertRaises(ValueError):
                self.backend(max_usd=1).complete("x" * 272000)
            network.assert_not_called()

    def test_failed_requests_keep_reservation_without_secret_leak_or_retry(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "private-test-key"}), \
             patch("urllib.request.urlopen", side_effect=RuntimeError("private-test-key")) as network:
            llm = self.backend(max_usd=.00025)
            with self.assertRaises(RuntimeError) as error:
                llm.complete("question", max_tokens=100)
            self.assertNotIn("private-test-key", str(error.exception))
            self.assertTrue(error.exception.__suppress_context__)
            self.assertEqual(network.call_count, 1)
            self.assertGreater(llm.cost_summary()["reserved_usd"], 0)
            self.assertEqual(llm.budget.calls, 1)
            with self.assertRaisesRegex(RuntimeError, "reserve"):
                llm.complete("question", max_tokens=100)
            self.assertEqual(network.call_count, 1)

    def test_partial_refusal_malformed_and_empty_outputs_fail(self):
        cases = [{"status": "incomplete"}, {"output": []}, {"output": [{"type": "function_call"}]},
                 {"usage": {}}, {"output": [{"type": "message", "status": "completed", "role": "assistant",
                  "content": [{"type": "refusal", "refusal": "cannot"}]}]}]
        for case in cases:
            with patch.dict("os.environ", {"OPENAI_API_KEY": "private-test-key"}), \
                 patch("urllib.request.urlopen", return_value=self.response(**case)):
                llm = self.backend(max_usd=.1)
                with self.assertRaises(RuntimeError):
                    llm.complete("question")
                self.assertGreater(llm.cost_summary()["reserved_usd"], 0)
