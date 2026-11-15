"""configs/models.json: Nathan's lineup and its checks (WS C2)."""
import unittest

from autoresearch.llm import split_spec
from autoresearch.research.models_config import config_warnings, load_models_config, research_args
from autoresearch.research.petri_measure import spec_to_inspect


class ModelsConfigTest(unittest.TestCase):
    def setUp(self):
        self.cfg = load_models_config()

    def test_committed_config_has_the_agreed_lineup_and_is_clean(self):
        r = self.cfg["roles"]
        self.assertEqual(r["dev_target"], "openai-compat:Qwen/Qwen3-30B-A3B")
        self.assertEqual(r["heldout_targets"], ["anthropic:claude-sonnet-4-5+thinking", "openai:gpt-5+thinking"])
        self.assertEqual(r["dev_judge"], "anthropic:claude-haiku-4-5")
        self.assertEqual(r["heldout_judges"], ["openai:gpt-5.1"])
        self.assertEqual(config_warnings(self.cfg), [])
        for spec in [r["generator"], r["dev_target"], r["dev_judge"]] + r["heldout_targets"] + r["heldout_judges"]:
            self.assertIsNotNone(split_spec(spec)[0], f"{spec} must name a backend")

    def test_petri_targets_are_the_same_models(self):
        r, p = self.cfg["roles"], self.cfg["petri"]
        self.assertEqual(spec_to_inspect(r["dev_target"])[0], p["dev"]["target"])
        self.assertEqual([spec_to_inspect(t)[0] for t in r["heldout_targets"]], p["final"]["targets"])
        self.assertEqual(spec_to_inspect("anthropic:claude-sonnet-4-5+thinking"), ("anthropic/claude-sonnet-4-5", True))

    def test_research_args(self):
        dev = research_args(self.cfg)
        self.assertEqual(dev[dev.index("--target") + 1], "openai-compat:Qwen/Qwen3-30B-A3B")
        fin = research_args(self.cfg, "final", "openai:gpt-5+thinking")
        self.assertIn("--heldout-judges", fin)
        self.assertEqual(fin[fin.index("--heldout-target") + 1], "openai:gpt-5+thinking")
        with self.assertRaises(ValueError):
            research_args(self.cfg, "final", "openai:gpt-4")

    def test_warnings(self):
        cfg = {"roles": {"generator": "anthropic:claude-x", "dev_target": "claude-cli:haiku",
                         "heldout_targets": ["anthropic:claude-y"], "dev_judge": "anthropic:claude-z",
                         "heldout_judges": ["claude-cli:opus"]},
               "petri": {"dev": {"target": "a", "auditor": "b", "judge": "c"}}}
        w = " | ".join(config_warnings(cfg))
        for s in ("shares the generator's family", "runs through claude-cli", "no headline judge",
                  "petri.final.targets missing"):
            self.assertIn(s, w)


if __name__ == "__main__":
    unittest.main()
