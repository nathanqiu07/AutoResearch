"""scripts/c2_make_control.py: the plain-agent control rewrites the seed AND the auditor prompt (WS C2)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import c2_make_control  # noqa: E402
from autoresearch.research.petri_measure import GUIDANCE_ANCHOR, stock_auditor_prompt  # noqa: E402


class MakeControlTest(unittest.TestCase):
    def test_writes_control_seeds_and_a_guided_auditor_prompt(self):
        # the taste conditions edit both seed and auditor (--petri-rewrite both), so the control must too,
        # or a difference in WHAT was edited would read as a taste effect
        with tempfile.TemporaryDirectory() as d:
            seeds, prompt = Path(d) / "control.jsonl", Path(d) / "auditor.txt"
            c2_make_control.main(["--offline", "--split", "dev", "--out", str(seeds), "--auditor-prompt-out", str(prompt)])
            rows = [json.loads(l) for l in seeds.read_text().splitlines()]
            text = prompt.read_text()
        self.assertEqual(len(rows), 12)
        self.assertIn("## Additional realism guidance for this audit", text)
        self.assertTrue(text.startswith(stock_auditor_prompt()[:200]))      # stock prompt kept, guidance added
        self.assertLess(text.index("Additional realism guidance"), text.rindex(GUIDANCE_ANCHOR))
        self.assertTrue(all(r.get("auditor_guidance") for r in rows))      # recorded with each seed


if __name__ == "__main__":
    unittest.main()
