"""Local OpenAI-compatible server in front of Tinker sampling (WS C2).

Kimi K2.5, the main target (Nathan and Abhi, 2026-11-15), is served by Tinker,
not as an OpenAI endpoint. This proxy lets everything that speaks the OpenAI chat
API (autoresearch's OpenAICompatLLM, Inspect's openai-api/<name>/<model> in the
Petri harness) use Tinker models. Prompts are built and replies parsed with
tinker_cookbook's renderer for the model, so the chat template, tool-call format
and thinking blocks are Tinker's own: thinking -> `reasoning_content` (raw chain
of thought, for A1), tool calls -> OpenAI `tool_calls` (Petri targets call tools).

Hard spend guard: --max-total-tokens (prompt + completion, all models). Past it
every request gets HTTP 429, so samples become errors instead of spending more.
Usage is written to --usage-file.

    pip install tinker tinker-cookbook       # in the Petri environment
    export TINKER_API_KEY=...                # your own key, never committed
    python harness/tinker_proxy.py --port 8100 --model moonshotai/Kimi-K2.5 --max-total-tokens 8000000
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple


def to_cookbook(messages: List[dict], tools: Optional[List[dict]], renderer) -> List[dict]:
    """OpenAI chat messages (+ tools) -> tinker_cookbook Messages."""
    from tinker_cookbook.renderers.base import ToolCall
    out, system = [], ""
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        content = content or ""
        if m["role"] == "system" and not out:
            system = content
            continue
        msg = {"role": m["role"], "content": content}
        if m.get("tool_calls"):
            msg["tool_calls"] = [ToolCall(id=tc.get("id"), function=ToolCall.FunctionBody(
                name=tc["function"]["name"],
                arguments=tc["function"].get("arguments") if isinstance(tc["function"].get("arguments"), str)
                else json.dumps(tc["function"].get("arguments", {}))))
                for tc in m["tool_calls"]]
        if m["role"] == "tool":
            if m.get("tool_call_id"):
                msg["tool_call_id"] = m["tool_call_id"]
            if m.get("name"):
                msg["name"] = m["name"]
        out.append(msg)
    if tools:
        specs = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                  "parameters": t["function"].get("parameters", {"type": "object", "properties": {}})}
                 for t in tools if t.get("type", "function") == "function"]
        return list(renderer.create_conversation_prefix_with_tools(specs, system_prompt=system)) + out
    return ([{"role": "system", "content": system}] if system else []) + out


def from_cookbook(msg: dict) -> Tuple[str, str, List[dict]]:
    """(reasoning, content, OpenAI tool_calls) from a parsed cookbook Message."""
    content = msg.get("content", "")
    reasoning, text = [], []
    if isinstance(content, str):
        text.append(content)
    else:
        for p in content:
            if p.get("type") == "thinking":
                reasoning.append(p.get("thinking", ""))
            elif p.get("type") == "text":
                text.append(p.get("text", ""))
    calls = [{"id": tc.id or "call_" + uuid.uuid4().hex[:12], "type": "function",
              "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
             for tc in msg.get("tool_calls") or []]
    return "\n".join(r for r in reasoning if r).strip(), "".join(text).strip(), calls


class Usage:
    def __init__(self, cap: int, path: Optional[str]):
        self.cap, self.path, self.lock = cap, path, threading.Lock()
        self.by_model: Dict[str, Dict[str, int]] = {}

    @property
    def total(self) -> int:
        return sum(v["prompt"] + v["completion"] for v in self.by_model.values())

    def over(self) -> bool:
        return self.cap > 0 and self.total >= self.cap

    def add(self, model: str, prompt: int, completion: int):
        with self.lock:
            v = self.by_model.setdefault(model, {"prompt": 0, "completion": 0, "requests": 0})
            v["prompt"] += prompt
            v["completion"] += completion
            v["requests"] += 1
            if self.path:
                with open(self.path, "w") as f:
                    json.dump({"total_tokens": self.total, "cap": self.cap, "by_model": self.by_model}, f, indent=1)


class Backend:
    def __init__(self, service=None):
        import tinker
        self.tinker = tinker
        self.service = service or tinker.ServiceClient()
        self.models: Dict[str, Tuple[Any, Any]] = {}
        self.lock = threading.Lock()

    def get(self, model: str):
        with self.lock:
            if model not in self.models:
                from tinker_cookbook.model_info import get_recommended_renderer_name
                from tinker_cookbook.renderers import get_renderer
                from tinker_cookbook.tokenizer_utils import get_tokenizer
                renderer = get_renderer(get_recommended_renderer_name(model), get_tokenizer(model), model_name=model)
                self.models[model] = (self.service.create_sampling_client(base_model=model).result(), renderer)
            return self.models[model]

    def complete(self, req: dict) -> Tuple[dict, int, int]:
        model = req["model"]
        client, renderer = self.get(model)
        prompt = renderer.build_generation_prompt(to_cookbook(req["messages"], req.get("tools"), renderer))
        params = self.tinker.types.SamplingParams(
            max_tokens=int(req.get("max_tokens") or req.get("max_completion_tokens") or 4096),
            temperature=float(req["temperature"]) if req.get("temperature") is not None else 0.7,
            top_p=float(req.get("top_p") or 1.0), stop=renderer.get_stop_sequences())
        seq = client.sample(prompt=prompt, num_samples=1, sampling_params=params).result().sequences[0]
        tokens = list(seq.tokens)
        msg, term = renderer.parse_response(tokens)
        reasoning, content, calls = from_cookbook(msg)
        n_prompt = prompt.length if hasattr(prompt, "length") else len(prompt.to_ints())
        finish = "tool_calls" if calls else ("length" if "length" in str(getattr(seq, "stop_reason", "")).lower() else "stop")
        out = {"role": "assistant", "content": content or None}
        if reasoning:
            out["reasoning_content"] = reasoning
        if calls:
            out["tool_calls"] = calls
        body = {"id": "chatcmpl-" + uuid.uuid4().hex[:16], "object": "chat.completion", "created": int(time.time()),
                "model": model, "choices": [{"index": 0, "message": out, "finish_reason": finish}],
                "usage": {"prompt_tokens": n_prompt, "completion_tokens": len(tokens),
                          "total_tokens": n_prompt + len(tokens)}}
        return body, n_prompt, len(tokens)


def make_handler(backend, usage: Usage, models: List[str]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                return self._send(200, {"object": "list", "data": [{"id": m, "object": "model"} for m in models]})
            self._send(404, {"error": {"message": "not found"}})

        def do_POST(self):
            if not self.path.rstrip("/").endswith("/chat/completions"):
                return self._send(404, {"error": {"message": "only /v1/chat/completions"}})
            if usage.over():
                return self._send(429, {"error": {"message": f"token cap reached ({usage.total}/{usage.cap})",
                                                  "type": "insufficient_quota"}})
            try:
                req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                if models and req.get("model") not in models:
                    return self._send(400, {"error": {"message": f"model {req.get('model')!r} not served: {models}"}})
                body, p, c = backend.complete(req)
                usage.add(req["model"], p, c)
                self._send(200, body)
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": {"message": f"{type(e).__name__}: {str(e)[:500]}"}})
    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--model", action="append", default=[], help="allowed Tinker base models (default: any)")
    ap.add_argument("--max-total-tokens", type=int, default=8_000_000, help="hard cap on tokens; 0 = none")
    ap.add_argument("--usage-file", default="tinker_usage.json")
    a = ap.parse_args(argv)
    usage = Usage(a.max_total_tokens, a.usage_file)
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Backend(), usage, a.model))
    print(f"tinker proxy on http://127.0.0.1:{a.port}/v1 (cap {a.max_total_tokens} tokens)", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    finally:
        print(json.dumps({"total_tokens": usage.total, "by_model": usage.by_model}), file=sys.stderr)


if __name__ == "__main__":
    main()
