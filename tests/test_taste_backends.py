import json
import subprocess
import unittest
from unittest.mock import patch


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
