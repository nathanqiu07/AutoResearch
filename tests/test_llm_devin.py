"""devin-cli backend: one isolated `devin -p` call per completion, billed to the Devin account."""
import json
import os
import unittest
from unittest import mock

from autoresearch.llm import Budget, BudgetExceeded, DevinCLILLM, get_llm


def fake_devin(reply="pong", prompt_tokens=20000, cached=19000, written=200, out=5):
    seen = {}

    def run(cmd, **kw):
        seen["cmd"], seen["cwd"] = cmd, kw["cwd"]
        seen["prompt"] = open(cmd[cmd.index("--prompt-file") + 1]).read()
        seen["config"] = json.load(open(cmd[cmd.index("--config") + 1]))
        steps = [{"source": "system", "message": "You are Devin"}, {"source": "user", "message": "x"},
                 {"source": "agent", "message": reply, "metrics": {
                     "prompt_tokens": prompt_tokens, "completion_tokens": out, "cached_tokens": cached,
                     "extra": {"cache_creation_input_tokens": written}}}]
        with open(cmd[cmd.index("--export") + 1], "w") as f:
            json.dump({"steps": steps}, f)
        return mock.Mock(returncode=0, stdout="banner\n" + reply, stderr="")
    return run, seen


class DevinCLITest(unittest.TestCase):
    def test_returns_the_reply_and_charges_devin_list_price(self):
        run, seen = fake_devin()
        with mock.patch("subprocess.run", side_effect=run):
            llm = get_llm("devin-cli", "claude-sonnet-5-5-medium")
            self.assertEqual(llm.complete("ping", system="Be terse."), "pong")
        self.assertIn("Be terse.", seen["prompt"])
        self.assertIn("ping", seen["prompt"])
        # Sonnet 5.5 on Devin: $2/M input, $0.10/M cached input, $10/M output.
        fresh = 20000 - 19000 - 200
        self.assertAlmostEqual(llm.budget.cost_usd, (fresh * 2 + 200 * 2.5 + 19000 * 0.1 + 5 * 10) / 1e6)
        self.assertEqual((llm.budget.input_tokens, llm.budget.output_tokens), (20000, 5))

    def test_call_reads_no_rules_and_may_use_no_tools(self):
        run, seen = fake_devin()
        with mock.patch("subprocess.run", side_effect=run):
            DevinCLILLM("claude-sonnet-5-5-medium").complete("ping")
        self.assertFalse(any(seen["config"]["read_config_from"].values()))
        self.assertIn("exec", seen["config"]["permissions"]["deny"])
        self.assertFalse(os.path.exists(seen["cwd"]))   # ran in a temporary directory, now removed

    def test_refuses_calls_once_cost_cap_is_reached(self):
        run, _ = fake_devin(prompt_tokens=60000, cached=0, written=0)
        with mock.patch("subprocess.run", side_effect=run) as call:
            llm = DevinCLILLM("claude-sonnet-5-5-medium", budget=Budget(max_cost_usd=0.2))
            llm.complete("ping")
            with self.assertRaises(BudgetExceeded):
                for _ in range(3):
                    llm.complete("ping")
        self.assertLess(call.call_count, 4)


if __name__ == "__main__":
    unittest.main()
