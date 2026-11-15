"""scripts/modal_pool.py: per-step Modal workspace pooling with dollar ledgers (WS C2)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("modal_pool", Path(__file__).resolve().parents[1] / "scripts" / "modal_pool.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)


class ModalPoolTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        self.entries = [{"label": "nathan", "profile": "nqiu07", "budget_usd": 40},
                        {"label": "abhi", "profile": "abhi", "budget_usd": 40}]

    def tearDown(self):
        self.dir.cleanup()

    def test_gpu_cost(self):
        self.assertAlmostEqual(mp.gpu_cost(4, 60, 3.95), 15.80)

    def test_reuses_first_workspace_until_full_then_moves_on(self):
        a = mp.pick(self.entries, "r1", 4, 150, self.root)            # $39.50 held of $40
        self.assertEqual(a["label"], "nathan")
        b = mp.pick(self.entries, "r2", 1, 20, self.root)             # $1.32 does not fit nathan's $0.50
        self.assertEqual(b["label"], "abhi")

    def test_close_replaces_the_hold_with_the_actual(self):
        mp.pick(self.entries, "r1", 4, 150, self.root)
        self.assertAlmostEqual(mp.close("nathan", "r1", 4, 30, self.root), mp.gpu_cost(4, 30))
        d = json.loads((self.root / "modal_ledger_nathan.json").read_text())
        self.assertEqual(d["open"], {})
        self.assertAlmostEqual(d["spent_usd"], round(mp.gpu_cost(4, 30), 4))
        self.assertEqual(mp.pick(self.entries, "r2", 4, 60, self.root)["label"], "nathan")   # room again

    def test_a_crashed_step_keeps_its_worst_case(self):
        mp.pick(self.entries, "crashed", 4, 150, self.root)
        self.assertEqual(mp.pick(self.entries, "next", 4, 60, self.root)["label"], "abhi")

    def test_refuses_when_no_workspace_fits(self):
        with self.assertRaises(SystemExit) as cm:
            mp.pick(self.entries, "big", 4, 24 * 60, self.root)
        self.assertIn("no Modal workspace has room", str(cm.exception))

    def test_profiles_parsed_from_modal_toml(self):
        toml = self.root / "modal.toml"
        toml.write_text('[nqiu07]\ntoken_id = "x"\ntoken_secret = "y"\nactive = true\n\n[abhi]\ntoken_id = "z"\n')
        self.assertEqual(mp.modal_profiles(toml), {"nqiu07": True, "abhi": False})

    def test_status_lists_ledgers(self):
        mp.pick(self.entries, "r1", 4, 30, self.root)
        self.assertIn("modal_ledger_nathan", mp.status(self.root))


if __name__ == "__main__":
    unittest.main()
