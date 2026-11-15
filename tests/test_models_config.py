"""configs/models.json and model-family checks (WS C2)."""
import unittest

from autoresearch.llm import LLM, OfflineLLM
from autoresearch.research.measure import Models
from autoresearch.research.models_config import config_warnings, family_warnings, load_models_config, model_family


class Fake(LLM):
    def __init__(self, name, model):
        self.name, self.model = name, model

    def complete(self, *a, **k):
        return ""


class FamilyTest(unittest.TestCase):
    def test_families_from_specs_and_inspect_ids(self):
        cases = {"anthropic:claude-sonnet-5-5": "anthropic", "claude-cli:sonnet": "anthropic", "haiku": "anthropic",
                 "openai:gpt-5": "openai", "openai/gpt-5": "openai", "openai-compat:Qwen/Qwen3-32B": "qwen",
                 "openai-api/modal/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8": "qwen",
                 "openai-api/tinker/moonshotai/Kimi-K2.5": "moonshot", "anthropic/claude-sonnet-5-5": "anthropic",
                 "openai-compat:meta-llama/Llama-3.3-70B": "meta", "something-else": "unknown"}
        for spec, fam in cases.items():
            self.assertEqual(model_family(spec), fam, spec)

    def test_catches_same_family_across_backends(self):
        m = Models(generator=Fake("anthropic", "claude-sonnet-5-5"), target=Fake("openai-compat", "Qwen/Qwen3-32B"),
                   judge=Fake("anthropic", "claude-sonnet-5-5"),
                   heldout_judges=[Fake("claude-cli", "opus"), Fake("openai", "gpt-5")])
        w = family_warnings(m)
        self.assertTrue(any("claude-cli:opus" in x for x in w))
        self.assertFalse(any("gpt-5" in x for x in w))

    def test_offline_is_silent(self):
        off = OfflineLLM()
        self.assertEqual(family_warnings(Models(off, off, off, heldout_judges=[off, off])), [])

    def test_committed_config_is_clean(self):
        cfg = load_models_config()
        self.assertEqual(config_warnings(cfg), [])
        self.assertEqual(len(cfg["roles"]["heldout_judges"]), 2)

    def test_config_warnings(self):
        cfg = {"roles": {"generator": "anthropic:claude-x", "heldout_judges": ["anthropic:claude-y"]},
               "petri": {"dev": {"target": "openai/gpt-5", "auditor": "a", "judge": "openai/gpt-5-mini"}}}
        w = " | ".join(config_warnings(cfg))
        for s in ("two held-out judges", "generator's family", "petri.final.target missing",
                  "Petri judge is from the target's family", "role 'dev_target' missing"):
            self.assertIn(s, w)


if __name__ == "__main__":
    unittest.main()
