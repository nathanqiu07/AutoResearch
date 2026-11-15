"""Offline test of harness/tinker_proxy.py: a fake Tinker sampling client, the real Kimi K2.5
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

KIMI = "moonshotai/Kimi-K2.5"
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

    def test_unknown_model_and_cap(self):
        self.assertEqual(self.post({"model": "x", "messages": []})[0], 400)
        self.usage.cap = 1
        try:
            self.assertEqual(self.post({"model": KIMI, "messages": [{"role": "user", "content": "hi"}]})[0], 429)
        finally:
            self.usage.cap = 10_000


if __name__ == "__main__":
    unittest.main()
