"""scripts/c2_e3b.py: the E3b condition comparison runs offline end to end (WS C2)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import c2_e3b  # noqa: E402


class E3bTest(unittest.TestCase):
    def test_offline_two_conditions_paired_by_seed(self):
        with tempfile.TemporaryDirectory() as d:
            rows = [json.loads(l) for l in (ROOT / "data/petri/seeds_v2.jsonl").read_text().splitlines()]
            ours = Path(d) / "ours.jsonl"
            ours.write_text("".join(json.dumps(dict(r, variant="ours")) + "\n" for r in rows))
            out = Path(d) / "e3b.json"
            c2_e3b.main(["--offline", "--condition", f"stock={ROOT / 'data/petri/seeds_v2.jsonl'}",
                         "--condition", f"ours={ours}", "--epochs", "2", "--out", str(out)])
            rep = json.loads(out.read_text())
            self.assertEqual(rep["conditions"]["stock"]["n"], 24)          # 12 dev seeds x 2 epochs
            self.assertEqual(rep["vs_stock"]["ours"]["awareness"]["n_seeds"], 12)
            self.assertIn("OFFLINE", rep["note"])
            self.assertIn("eval_awareness", rep["conditions"]["ours"]["petri_cross_check"])


if __name__ == "__main__":
    unittest.main()
