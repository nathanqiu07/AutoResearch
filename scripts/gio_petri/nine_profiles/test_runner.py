import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import Budget, ArmLedger, default_config, prepare, verify


class RunnerTests(unittest.TestCase):
    def test_profile_preserved_and_packet_tamper_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'out'
            text = 'Long profile with literal {seed_instructions} and café.\n'*100
            prepare(text, 'carlini_P2', out, default_config(), 3)
            self.assertEqual((out/'profile.md').read_text(), text)
            self.assertEqual(len(verify(out)['arms']), 3)
            rendered = (out/'packet/r1.template.txt').read_text().format(
                max_turns=30, target_model='x', seed_instructions='SEED',
                today_date='DATE', resources_prompt='')
            self.assertIn(text, rendered)
            (out/'profile.md').write_text('changed')
            with self.assertRaises(ValueError): verify(out)

    def test_money_and_call_limits_are_enforced_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = default_config(); cfg['max_calls_per_replicate'] = 1
            b = Budget(Path(tmp)/'budget.json', cfg, 1)
            a = ArmLedger(Path(tmp)/'a.json', b, 'r1.audit')
            i = a.reserve('target', 8192)
            a.settle(i, {'input_tokens':100, 'output_tokens':100})
            self.assertAlmostEqual(b.held, .001125)
            with self.assertRaises(RuntimeError): a.reserve('target', 8192)
            self.assertEqual(len(b.entries), 1)

    def test_unknown_usage_halts_and_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Budget(Path(tmp)/'budget.json', default_config(), 1)
            a = ArmLedger(Path(tmp)/'a.json', b, 'r1.audit')
            i=a.reserve('auditor',8192); bound=b.held
            with self.assertRaises(RuntimeError): a.settle(i,None)
            self.assertEqual(b.held,bound)
            self.assertTrue(b.halted)
            with self.assertRaises(RuntimeError): a.reserve('judge',16384)

    def test_output_cannot_be_reused_and_invalid_config_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'; cfg=default_config()
            prepare('profile','x',out,cfg,1)
            with self.assertRaises(FileExistsError): prepare('profile','x',out,cfg,1)
            cfg['roles']['target']['input_usd_per_million']=-1
            with self.assertRaises(ValueError): prepare('profile','x',Path(tmp)/'bad',cfg,1)

if __name__=='__main__':unittest.main()
