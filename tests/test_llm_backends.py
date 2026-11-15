"""API backend behaviour: thinking shape per model, lineup prices, per-model OpenAI prices,
and the spend cap stopping every paid path. No test touches the network: urlopen is mocked."""
import json
import os
import unittest
from unittest import mock

from autoresearch import llm as L
from autoresearch.llm import Budget, BudgetExceeded


class FakeServer:
    """Stands in for urllib.request.urlopen; counts requests and keeps their bodies."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.sent = []

    def __call__(self, req, timeout=0):
        self.sent.append(json.loads(req.data))
        payload = self.payload

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps(payload).encode()
        return Resp()


ANTHROPIC_REPLY = {"content": [{"type": "thinking", "thinking": "hmm, a test"},
                               {"type": "text", "text": "answer"}],
                   "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}
OPENAI_REPLY = {"status": "completed", "output": [
    {"type": "reasoning", "summary": [{"type": "summary_text", "text": "hmm"}]},
    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]}],
    "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}


class ThinkingShapeTests(unittest.TestCase):
    def _run(self, model, max_tokens=1200):
        server = FakeServer({"content": [{"type": "thinking", "thinking": "a thought"},
                                         {"type": "text", "text": "hi"}],
                             "usage": {"input_tokens": 3, "output_tokens": 9}})
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
                mock.patch.object(L.urllib.request, "urlopen", server):
            result = L.AnthropicLLM(model, Budget()).complete_with_reasoning("q", max_tokens=max_tokens)
        return result, server.sent[0]

    def test_sonnet_4_5_sends_manual_budget_thinking_and_parses_the_block(self):
        result, body = self._run("claude-sonnet-4-5+thinking")
        self.assertEqual(result, ("a thought", "hi"))
        self.assertEqual(body["thinking"], {"type": "enabled", "budget_tokens": L.AnthropicLLM.THINKING_HEADROOM})
        self.assertGreater(body["max_tokens"], body["thinking"]["budget_tokens"])
        self.assertGreaterEqual(body["thinking"]["budget_tokens"], 1024)
        self.assertNotIn("temperature", body)

    def test_sonnet_4_6_keeps_adaptive_thinking(self):
        _, body = self._run("claude-sonnet-4-6+thinking")
        self.assertEqual(body["thinking"], {"type": "adaptive", "display": "summarized"})
        self.assertNotIn("temperature", body)

    def test_manual_thinking_rule_by_model_id(self):
        for model in ("claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-1", "claude-opus-4-0",
                      "claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-7-sonnet-latest",
                      "claude-sonnet-4-5-20250929"):
            self.assertTrue(L.anthropic_needs_manual_thinking(model), model)
        for model in ("claude-sonnet-4-6", "claude-opus-4-6", "claude-sonnet-5-5", "claude-opus-5-5",
                      "claude-haiku-5-5"):
            self.assertFalse(L.anthropic_needs_manual_thinking(model), model)


class LineupPriceTests(unittest.TestCase):
    def test_lineup_models_have_prices_that_flow_through_cost_helpers(self):
        self.assertEqual(L.PRICES_PER_MTOK["claude-sonnet-4-5"], (3.0, 15.0))
        self.assertEqual(L.PRICES_PER_MTOK["gpt-5"], (1.25, 10.0))
        self.assertEqual(L.PRICES_PER_MTOK["gpt-5.1"], (1.25, 10.0))
        self.assertAlmostEqual(L.list_price_usd("gpt-5", 1_000_000, 1_000_000), 11.25)
        cost, _ = L.anthropic_usage_cost("claude-sonnet-4-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000})
        self.assertAlmostEqual(cost, 18.0)

    def test_lineup_specs_start_without_an_env_price(self):
        env = {"OPENAI_API_KEY": "test-key", "ANTHROPIC_API_KEY": "test-key"}
        with mock.patch.dict(os.environ, env):
            os.environ.pop("OPENAI_PRICE_PER_MTOK", None)
            self.assertEqual(L.get_llm("offline", "openai:gpt-5+thinking", Budget()).label, "openai:gpt-5+thinking")
            self.assertEqual(L.get_llm("offline", "openai:gpt-5.1", Budget()).label, "openai:gpt-5.1")
            self.assertEqual(L.get_llm("offline", "anthropic:claude-sonnet-4-5+thinking", Budget()).label,
                             "anthropic:claude-sonnet-4-5+thinking")
            with self.assertRaises(RuntimeError):
                L.get_llm("offline", "openai:made-up-model", Budget())


class OpenAIPlainCompleteHeadroomTest(unittest.TestCase):
    def test_plain_complete_leaves_room_for_default_reasoning(self):
        # gpt-6-luna reasons by default even when no reasoning is asked for, and those tokens count
        # against max_output_tokens: at max_tokens=2500 the control rewriter came back "incomplete"
        # with no text (2026-11-14). Plain complete must leave the same headroom as the thinking path.
        server = FakeServer(OPENAI_REPLY)
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
                mock.patch("urllib.request.urlopen", server):
            self.assertEqual(L.OpenAIResponsesLLM("gpt-6-luna", Budget()).complete("q", max_tokens=2500), "answer")
        body = server.sent[0]
        self.assertEqual(body["max_output_tokens"], 2500 + L.OpenAIResponsesLLM.THINKING_HEADROOM)
        self.assertNotIn("reasoning", body)      # the model's own default effort is unchanged


class OpenAIPriceEnvTests(unittest.TestCase):
    def _prices(self, model, env_price):
        env = {"OPENAI_API_KEY": "test-key"}
        if env_price is not None:
            env["OPENAI_PRICE_PER_MTOK"] = env_price
        with mock.patch.dict(os.environ, env):
            if env_price is None:
                os.environ.pop("OPENAI_PRICE_PER_MTOK", None)
            return L.OpenAIResponsesLLM(model, Budget()).prices

    def test_bare_form_applies_to_the_instance_model(self):
        prices = self._prices("made-up-model", "2,8")
        self.assertEqual(prices["made-up-model"], (2.0, 8.0))
        self.assertEqual(prices["gpt-5"], (1.25, 10.0))     # other entries untouched

    def test_bare_form_overrides_a_table_price_for_the_instance_model(self):
        self.assertEqual(self._prices("gpt-5", "2,8")["gpt-5"], (2.0, 8.0))

    def test_per_model_form_prices_several_models_in_one_run(self):
        env_price = "made-up-a=2,8;made-up-b=0.5,1.5"
        self.assertEqual(self._prices("made-up-a", env_price)["made-up-a"], (2.0, 8.0))
        prices_b = self._prices("made-up-b", env_price)
        self.assertEqual(prices_b["made-up-b"], (0.5, 1.5))
        self.assertEqual(prices_b["made-up-a"], (2.0, 8.0))

    def test_per_model_form_without_the_instance_model_falls_back_to_the_table_or_refuses(self):
        self.assertEqual(self._prices("gpt-5", "other=2,8")["gpt-5"], (1.25, 10.0))
        with self.assertRaises(RuntimeError):
            self._prices("made-up-model", "other=2,8")

    def test_malformed_values_name_the_variable_and_the_value(self):
        for bad in ("2", "2,x", "2,8,9", "=2,8", "m=2", "m=2,x", "m=2,8;", "m=2,8;n", "-1,8", "m=nan,8"):
            with self.assertRaises(RuntimeError, msg=bad) as ctx:
                self._prices("made-up-model", bad)
            self.assertIn("OPENAI_PRICE_PER_MTOK", str(ctx.exception), bad)
            self.assertIn(repr(bad), str(ctx.exception), bad)


class SpendCapStopsBackendsTests(unittest.TestCase):
    """Each call costs $3 (1M input tokens at $3/M). With a $5 cap the first two calls run
    ($6 recorded), and the third must raise before any request is sent."""

    def _assert_cap_holds(self, make_llm, reply, call):
        server = FakeServer(reply)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "OPENAI_API_KEY": "test-key",
                                          "OPENAI_PRICE_PER_MTOK": "3,0"}), \
                mock.patch.object(L.urllib.request, "urlopen", server):
            budget = Budget(max_cost_usd=5.0)
            llm = make_llm(budget)
            call(llm)
            call(llm)
            self.assertEqual(len(server.sent), 2)
            self.assertGreaterEqual(budget.cost_usd, 5.0)
            with self.assertRaises(BudgetExceeded):
                call(llm)
            self.assertEqual(len(server.sent), 2, "a request was sent after the cap was reached")

    def test_anthropic_complete(self):
        self._assert_cap_holds(lambda b: L.AnthropicLLM("claude-sonnet-4-6", b), ANTHROPIC_REPLY,
                               lambda m: m.complete("q"))

    def test_anthropic_complete_with_reasoning_thinking_on(self):
        self._assert_cap_holds(lambda b: L.AnthropicLLM("claude-sonnet-4-5+thinking", b), ANTHROPIC_REPLY,
                               lambda m: m.complete_with_reasoning("q"))

    def test_anthropic_complete_with_reasoning_thinking_off(self):
        self._assert_cap_holds(lambda b: L.AnthropicLLM("claude-sonnet-4-6", b), ANTHROPIC_REPLY,
                               lambda m: m.complete_with_reasoning("q"))

    def test_openai_complete(self):
        self._assert_cap_holds(lambda b: L.OpenAIResponsesLLM("made-up-model", b), OPENAI_REPLY,
                               lambda m: m.complete("q"))

    def test_openai_complete_with_reasoning_thinking_on(self):
        self._assert_cap_holds(lambda b: L.OpenAIResponsesLLM("made-up-model+thinking", b), OPENAI_REPLY,
                               lambda m: m.complete_with_reasoning("q"))

    def test_openai_complete_with_reasoning_thinking_off(self):
        self._assert_cap_holds(lambda b: L.OpenAIResponsesLLM("made-up-model", b), OPENAI_REPLY,
                               lambda m: m.complete_with_reasoning("q"))

    def test_openai_compat_has_no_price_so_the_cap_alone_never_stops_it(self):
        server = FakeServer({"choices": [{"message": {"content": "hi", "reasoning_content": "r"}}],
                             "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}})
        with mock.patch.dict(os.environ, {"OPENAI_COMPAT_BASE_URL": "http://vllm.invalid/v1"}), \
                mock.patch.object(L.urllib.request, "urlopen", server):
            budget = Budget(max_cost_usd=0.01)
            llm = L.OpenAICompatLLM("qwen3", budget)
            for _ in range(5):
                llm.complete("q")
                llm.complete_with_reasoning("q")
            self.assertEqual(len(server.sent), 10)
            self.assertEqual(budget.cost_usd, 0.0)
            # Only a cost recorded by another backend on a SHARED Budget stops it.
            budget.charge(0, 0, 1.0)
            with self.assertRaises(BudgetExceeded):
                llm.complete("q")
            self.assertEqual(len(server.sent), 10)


if __name__ == "__main__":
    unittest.main()


class VllmPlainThinkingTests(unittest.TestCase):
    """Probe questions go through plain complete(); a thinking model must not spend the 300-token cap reasoning."""

    def _run(self, mode):
        from unittest import mock
        from autoresearch import llm as L
        sent = []

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self):
                return json.dumps({"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}).encode()

        def fake_urlopen(req, timeout=0):
            sent.append(json.loads(req.data))
            return Resp()
        env = {"OPENAI_COMPAT_BASE_URL": "http://localhost:1/v1"}
        if mode is not None:
            env["OPENAI_COMPAT_PLAIN_THINKING"] = mode
        with mock.patch.dict(os.environ, env), mock.patch.object(L.urllib.request, "urlopen", fake_urlopen):
            if mode is None:
                os.environ.pop("OPENAI_COMPAT_PLAIN_THINKING", None)
            m = L.OpenAICompatLLM("Qwen/Qwen3-30B-A3B", L.Budget())
            m.complete("probe", max_tokens=300)
            m.complete_with_reasoning("task", max_tokens=1200)
        return sent

    def test_off_disables_thinking_on_plain_calls_only(self):
        plain, reasoning = self._run("off")
        self.assertEqual(plain["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(plain["max_tokens"], 300)
        self.assertNotIn("chat_template_kwargs", reasoning)

    def test_headroom_keeps_thinking_and_raises_the_cap(self):
        plain, _ = self._run("headroom")
        self.assertEqual(plain["max_tokens"], 8300)
        self.assertNotIn("chat_template_kwargs", plain)

    def test_unset_sends_plain_calls_unchanged(self):
        plain, reasoning = self._run(None)
        self.assertEqual((plain["max_tokens"], "chat_template_kwargs" in plain), (300, False))
        self.assertEqual(reasoning["max_tokens"], 9200)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self._run("maybe")
