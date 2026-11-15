"""OPENAI_COMPAT_ENDPOINTS: per-model base URL for openai-compat (WS C2)."""
import json
import os
import unittest
from unittest import mock

from autoresearch.llm import OpenAICompatLLM, openai_compat_endpoint

TABLE = {"Qwen/Qwen3-30B": {"base_url": "https://target.example/v1", "key_env": "T_KEY"},
         "openai/gpt-oss": {"base_url": "https://judge.example/v1/", "key_env": "J_KEY", "usd_per_hour": 3.95},
         "Qwen/": {"base_url": "https://other.example/v1"}}


class EndpointTest(unittest.TestCase):
    def env(self, **kw):
        base = {"OPENAI_COMPAT_ENDPOINTS": json.dumps(TABLE), "T_KEY": "t", "J_KEY": "j",
                "OPENAI_COMPAT_BASE_URL": "https://default.example/v1", "OPENAI_COMPAT_API_KEY": "d"}
        base.update(kw)
        return mock.patch.dict(os.environ, base, clear=False)

    def test_longest_prefix_wins_and_key_comes_from_named_env(self):
        with self.env():
            a = OpenAICompatLLM("Qwen/Qwen3-30B-A3B")
            self.assertEqual((a.base_url, a.key), ("https://target.example/v1", "t"))
            b = OpenAICompatLLM("openai/gpt-oss-120b")
            self.assertEqual((b.base_url, b.key, b.usd_per_hour), ("https://judge.example/v1", "j", 3.95))
            c = OpenAICompatLLM("Qwen/Qwen3-235B")
            self.assertEqual((c.base_url, c.key), ("https://other.example/v1", "d"))

    def test_no_match_or_unset_keeps_old_behaviour(self):
        with self.env():
            d = OpenAICompatLLM("moonshotai/Kimi-K2.5")
            self.assertEqual((d.base_url, d.key), ("https://default.example/v1", "d"))
        with self.env(OPENAI_COMPAT_ENDPOINTS=""):
            self.assertEqual(openai_compat_endpoint("Qwen/Qwen3-30B-A3B"), {})
        with self.env():
            e = OpenAICompatLLM("Qwen/Qwen3-30B-A3B", base_url="https://explicit.example/v1")
            self.assertEqual(e.base_url, "https://explicit.example/v1")

    def test_bad_table_fails_loudly(self):
        with self.env(OPENAI_COMPAT_ENDPOINTS="{not json"):
            with self.assertRaises(RuntimeError):
                OpenAICompatLLM("Qwen/Qwen3-30B-A3B")
        with self.env(OPENAI_COMPAT_ENDPOINTS=json.dumps({"Qwen/": {"key_env": "x"}})):
            with self.assertRaises(RuntimeError):
                OpenAICompatLLM("Qwen/Qwen3-30B-A3B")


if __name__ == "__main__":
    unittest.main()
