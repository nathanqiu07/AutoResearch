"""Offline checks: real provider serialization and missing/stale model handoff gates."""
import json
from pathlib import Path
import tempfile
import unittest
from roles import roles
from prepare import model_principles, sha
from inspect_ai.tool import ToolDef
from petri.tools import default_auditor_tools

class PrepTests(unittest.TestCase):
    def test_provider_pins_and_reasoning(self):
        r=roles('offline-placeholder','offline-placeholder')
        for role in ('target','auditor'):
            params=r[role].api.completion_params(r[role].config,True)
            p=params['extra_body']['provider']
            self.assertFalse(p['allow_fallbacks'])
            self.assertEqual(r[role].api.client.max_retries,0)
            self.assertEqual(len(p['only']),1)
        self.assertTrue(r['target'].api.completion_params(r['target'].config,True)['extra_body']['reasoning']['enabled'])
        self.assertEqual(r['target'].config.max_tokens,16384)
    def test_native_model_cleanup(self):
        import asyncio
        async def close_all():
            models=roles('offline-placeholder','offline-placeholder')
            for model in models.values():
                await model.__aexit__(None,None,None)
                self.assertTrue(model._closed)
        asyncio.run(close_all())
    def test_real_tool_schema_names(self):
        names=[ToolDef(t).name for t in default_auditor_tools()]
        self.assertIn('send_message',names)
        self.assertNotIn('execute',names)
        self.assertEqual(len(names),len(set(names)))
    def test_filter_handoff_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/'model.json';h=Path(d)/'handoff.json'
            m.write_text(json.dumps({'method':'m3','artifacts':{'principles':['Prefer X'], 'metadata':{'history_ids':['a']}}}))
            data={'status':'refit_complete','heldout_untouched':True,'model_sha256':sha(m),
              'original_split_ids':{'learning':['a','z'],'validation':['b'],'dev':['c']},
              'kept_split_ids':{'learning':['a'],'validation':['b'],'dev':['c']},
              'filter_manifest_sha256':'example','refit_run_path':'example'}
            h.write_text(json.dumps(data));self.assertEqual(model_principles(m,h)[0],['Prefer X'])
            data['kept_split_ids']['learning']=['c'];h.write_text(json.dumps(data))
            with self.assertRaises(AssertionError):model_principles(m,h)
            data['kept_split_ids']['learning']=['a'];data['model_sha256']='stale';h.write_text(json.dumps(data))
            with self.assertRaises(AssertionError):model_principles(m,h)
class RunnerGateTests(unittest.TestCase):
    def test_prepare_and_validate_without_model_calls(self):
        import sys
        from unittest.mock import patch
        import prepare,run_baseline
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=root/'model.json';h=root/'handoff.json';packet=root/'packet'
            m.write_text(json.dumps({'method':'m3','artifacts':{'principles':['Fixture principle'], 'metadata':{'history_ids':['a']}}}))
            h.write_text(json.dumps({'status':'refit_complete','heldout_untouched':True,'model_sha256':sha(m),
              'original_split_ids':{'learning':['a'],'validation':['b'],'dev':['c']},
              'kept_split_ids':{'learning':['a'],'validation':['b'],'dev':['c']},
              'filter_manifest_sha256':'fixture','refit_run_path':'fixture'}))
            with patch.object(sys,'argv',['prepare','--out',str(packet),'--model',str(m),'--handoff',str(h)]):prepare.main()
            args=['run','--packet',str(packet),'--out',str(root/'never-created'),
                  '--prior-spend-usd','5','--pair-budget-usd','5']
            with patch.object(sys,'argv',args),patch.object(run_baseline,'roles',side_effect=AssertionError('Must not call models')):
                run_baseline.main()
            self.assertFalse((root/'never-created').exists())
            (packet/'seed.txt').write_text('modified')
            with patch.object(sys,'argv',args),self.assertRaises(SystemExit):run_baseline.main()

class BudgetTests(unittest.TestCase):
    def test_reservation_blocks_before_call(self):
        from budget import Ledger
        with tempfile.TemporaryDirectory() as d:
            ledger=Ledger(Path(d)/'ledger.json',0.01)
            with self.assertRaises(RuntimeError):ledger.reserve('judge',32000)
            self.assertEqual(ledger.entries,[])
    def test_missing_usage_keeps_reservation(self):
        from budget import Ledger
        with tempfile.TemporaryDirectory() as d:
            ledger=Ledger(Path(d)/'ledger.json',2)
            i=ledger.reserve('judge',32000);before=ledger.held
            ledger.settle(i,None);self.assertEqual(ledger.held,before)
    def test_failure_halts_other_roles(self):
        import asyncio
        from types import SimpleNamespace
        from budget import Ledger,attach
        async def fail(*a):raise RuntimeError('fixture failure')
        with tempfile.TemporaryDirectory() as d:
            ledger=Ledger(Path(d)/'ledger.json',2)
            model=SimpleNamespace(api=SimpleNamespace(generate=fail),config=SimpleNamespace(max_tokens=32000))
            attach(model,'judge',ledger,Path(d))
            with self.assertRaises(RuntimeError):asyncio.run(model.api.generate([],[],'auto',model.config))
            self.assertTrue(ledger.halted)
            with self.assertRaises(RuntimeError):ledger.reserve('target',100)
if __name__=='__main__':unittest.main()

