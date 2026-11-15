"""Offline test of harness/tinker_proxy.py: a fake Tinker sampling client, the real Kimi K2.6
renderer (downloads its tokenizer once). Run in the Petri env:
    $AUTORESEARCH_PETRI_PYTHON -m unittest harness/test_tinker_proxy.py
"""
import json
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tinker_proxy as tp  # noqa: E402

KIMI = "moonshotai/Kimi-K2.6"
REPLY = ('maybe this is a test?</think>Checking.<|tool_calls_section_begin|><|tool_call_begin|>functions.bash:1'
         '<|tool_call_argument_begin|>{"command": "df -h"}<|tool_call_end|><|tool_calls_section_end|><|im_end|>')


class FakeSeq:
    def __init__(self, tokens):
        self.tokens, self.stop_reason = tokens, "stop"


class FakeClient:
    def __init__(self, tokens):
        self.tokens, self.prompts = tokens, []

    def sample(self, prompt, num_samples, sampling_params):
        self.prompts.append(prompt)
        outer = self

        class F:
            def result(self):
                return type("R", (), {"sequences": [FakeSeq(outer.tokens)]})()
        return F()


class ProxyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tinker_cookbook.model_info import get_recommended_renderer_name
        from tinker_cookbook.renderers import get_renderer
        from tinker_cookbook.tokenizer_utils import get_tokenizer
        tok = get_tokenizer(KIMI)
        cls.renderer = get_renderer(get_recommended_renderer_name(KIMI), tok, model_name=KIMI)
        cls.client = FakeClient(list(tok.encode(REPLY, allow_special_tokens=True)))
        backend = tp.Backend.__new__(tp.Backend)
        import tinker
        backend.tinker, backend.lock = tinker, threading.Lock()
        backend.models = {KIMI: (cls.client, cls.renderer)}
        cls.usage = tp.Usage(cap=10_000, path=None)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), tp.make_handler(backend, cls.usage, [KIMI]))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/v1/chat/completions"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def post(self, body):
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_tools_thinking_and_tool_calls_round_trip(self):
        body = {"model": KIMI, "max_tokens": 100, "messages": [
            {"role": "system", "content": "You are a build bot."}, {"role": "user", "content": "check disk"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "functions.bash:0", "type": "function",
                                                               "function": {"name": "bash", "arguments": "{\"command\": \"ls\"}"}}]},
            {"role": "tool", "tool_call_id": "functions.bash:0", "name": "bash", "content": "a.txt"}],
            "tools": [{"type": "function", "function": {"name": "bash", "description": "run a command",
                                                        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}}]}
        code, out = self.post(body)
        self.assertEqual(code, 200, out)
        msg = out["choices"][0]["message"]
        self.assertEqual(msg["reasoning_content"], "maybe this is a test?")
        self.assertEqual(msg["content"], "Checking.")
        self.assertEqual(msg["tool_calls"][0]["function"], {"name": "bash", "arguments": "{\"command\": \"df -h\"}"})
        self.assertEqual(out["choices"][0]["finish_reason"], "tool_calls")
        self.assertGreater(out["usage"]["prompt_tokens"], 20)

    def test_pooled_budget_end_to_end(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            prices = {KIMI: (2.205, 5.49)}
            # clamped to 4000 tokens, a request's worst case is ~$0.022: nathan's $0.01 never fits it,
            # abhi's $0.03 fits it until abhi's settled spend (~$0.0003 per fake reply) is topped up below
            pool = tp.Pool([("nathan", tp.Budget(f"{d}/n.json", 0.01, 0, prices)),
                            ("abhi", tp.Budget(f"{d}/a.json", 0.03, 0, prices))])
            backend = tp.Backend.__new__(tp.Backend)
            import tinker
            backend.tinker, backend.lock, backend.models = tinker, threading.Lock(), {}
            backend.renderers, backend.services, backend.key_envs = {KIMI: self.renderer}, {}, {}
            backend.clients = {("nathan", KIMI): self.client, ("abhi", KIMI): self.client}
            server = ThreadingHTTPServer(("127.0.0.1", 0),
                                         tp.make_handler(backend, tp.Usage(0, None), [KIMI], pool, ceiling=4000))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
            try:
                body = {"model": KIMI, "max_tokens": 100_000, "messages": [{"role": "user", "content": "hi"}]}

                def call():
                    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
                    try:
                        with urllib.request.urlopen(req) as r:
                            return r.status, json.loads(r.read())
                    except urllib.error.HTTPError as e:
                        return e.code, json.loads(e.read())

                self.assertEqual(call()[0], 200)
                served = {s["account"]: s["spent_usd"] for s in pool.summary()}
                self.assertEqual(served["nathan"], 0)        # skipped: its budget cannot hold the worst case
                self.assertGreater(served["abhi"], 0)        # served and billed to abhi's ledger
                abhi = pool.accounts["abhi"]
                abhi.settle(KIMI, 0, 0, 2_000)                # +$0.011 elsewhere: abhi can no longer hold $0.022
                code, out = call()
                self.assertEqual(code, 429)
                self.assertIn("every Tinker account", out["error"]["message"])
            finally:
                server.shutdown()

    def test_reply_cut_off_mid_thinking_is_reasoning_with_finish_length(self):
        # max_tokens ran out before </think>: the renderer calls it malformed and returns the half
        # thought as content. Passing that on as the answer made every A2 probe "unparseable".
        tok = self.renderer.tokenizer
        saved = self.client.tokens
        self.client.tokens = list(tok.encode("The user wants a probability. Let me weigh the cues", allow_special_tokens=True))
        try:
            code, out = self.post({"model": KIMI, "max_tokens": 12, "messages": [{"role": "user", "content": "p?"}]})
        finally:
            self.client.tokens = saved
        self.assertEqual(code, 200, out)
        choice = out["choices"][0]
        self.assertEqual(choice["finish_reason"], "length")
        self.assertIsNone(choice["message"]["content"])
        self.assertIn("weigh the cues", choice["message"]["reasoning_content"])

    def test_inspect_client_round_trip(self):
        # Petri talks to the target through Inspect's openai-api provider (openai-api/modal/<model>),
        # not our client: check its requests parse and its reply carries reasoning and the tool call.
        import asyncio
        import os
        from inspect_ai.model import ChatMessageTool, ChatMessageUser, ContentReasoning, get_model
        from inspect_ai.tool import ToolInfo, ToolParams
        from inspect_ai.tool._tool_params import ToolParam
        base = self.url.rsplit("/chat/completions", 1)[0]
        saved = {k: os.environ.get(k) for k in ("MODAL_BASE_URL", "MODAL_API_KEY")}
        os.environ.update(MODAL_BASE_URL=base, MODAL_API_KEY="local")
        try:
            model = get_model(f"openai-api/modal/{KIMI}")
            bash = ToolInfo(name="bash", description="run a command",
                            parameters=ToolParams(properties={"command": ToolParam(type="string")}, required=["command"]))
            first = asyncio.run(model.generate([ChatMessageUser(content="check disk")], tools=[bash]))
            msg = first.message
            reasoning = [c.reasoning for c in msg.content if isinstance(c, ContentReasoning)] \
                if isinstance(msg.content, list) else []
            self.assertEqual(reasoning, ["maybe this is a test?"])
            self.assertEqual(msg.tool_calls[0].function, "bash")
            self.assertEqual(msg.tool_calls[0].arguments, {"command": "df -h"})
            # second turn: Inspect replays the assistant turn (with its reasoning) and the tool result
            history = [ChatMessageUser(content="check disk"), msg,
                       ChatMessageTool(content="/dev/sda 40%", tool_call_id=msg.tool_calls[0].id, function="bash")]
            n_before = len(self.client.prompts)
            second = asyncio.run(model.generate(history, tools=[bash]))
            self.assertEqual(len(self.client.prompts), n_before + 1)
            self.assertFalse(second.message.error if hasattr(second.message, "error") else False)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_unknown_model_and_cap(self):
        self.assertEqual(self.post({"model": "x", "messages": []})[0], 400)
        self.usage.cap = 1
        try:
            self.assertEqual(self.post({"model": KIMI, "messages": [{"role": "user", "content": "hi"}]})[0], 429)
        finally:
            self.usage.cap = 10_000


if __name__ == "__main__":
    unittest.main()
