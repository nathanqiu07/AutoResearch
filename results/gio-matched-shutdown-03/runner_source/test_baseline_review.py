"""Offline contract checks for the approved 30-turn baseline wrapper."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import run_baseline

ROOT=Path(__file__).resolve().parents[2]

class BaselineReviewTests(unittest.TestCase):
    def test_primary_survives_secondary_judge_failure(self):
        row={'transcript':'Observed conversation','reasoning':'Observed reasoning','error':None,'petri_judge_status':'failed'}
        run_baseline.require_audit_evidence('success',row,True)
        with self.assertRaises(RuntimeError):run_baseline.require_audit_evidence('success',row,False)
        with self.assertRaises(RuntimeError):run_baseline.require_audit_evidence('error',row,True)

    def test_primary_api_failure_is_recorded(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as d:
            judge=Mock();judge.complete.side_effect=RuntimeError('sensitive provider body')
            with self.assertRaises(RuntimeError):run_baseline.run_primary_review(judge,'prompt',{},Path(d))
            result=json.loads((Path(d)/'primary-review.json').read_text())
            self.assertEqual(result['status'],'review_failed')
            self.assertEqual(result['phase'],'primary_review_api')
            self.assertNotIn('sensitive',json.dumps(result))

    def test_settings_reject_model_drift(self):
        settings=json.loads((ROOT/'results/gio-baseline-review-01/settings.json').read_text())
        self.assertEqual(run_baseline.validate_settings(settings),10)
        settings['max_auditor_turns']=30
        self.assertEqual(run_baseline.validate_settings(settings),30)
        settings['models']['judge']='different-model'
        with self.assertRaises(ValueError):run_baseline.validate_settings(settings)

    def test_stop_metadata_pending_tool_is_not_confirmed_action(self):
        sample=SimpleNamespace(store={'AuditStore:auditor':{'messages':[
            {'role':'assistant','tool_calls':[{'function':'send_tool_call_result'}]}]*30},
            'AuditStore:target':{'messages':[{'role':'assistant','tool_calls':[{'id':'edit1','function':'bash'}]}], 'tools':[]}})
        tools,structure=run_baseline.review_context(sample,30)
        self.assertEqual(structure['termination'],'turn_limit')
        self.assertEqual(structure['pending_target_tool_ids'],['edit1'])
        sample.store['AuditStore:target']['messages'].append({'role':'tool','tool_call_id':'edit1','content':'done'})
        self.assertEqual(run_baseline.review_context(sample,30)[1]['pending_target_tool_ids'],[])

    def test_natural_end_recorded(self):
        sample=SimpleNamespace(store={'AuditStore:auditor':{'messages':[
            {'role':'assistant','tool_calls':[{'function':'end_conversation'}]}]},
            'AuditStore:target':{'messages':[],'tools':[]}})
        self.assertEqual(run_baseline.review_context(sample,30)[1]['termination'],'auditor_ended')

    def test_review_packet_exact_seed_prompt_and_roles(self):
        import prepare_review
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'packet'
            prepare_review.prepare(ROOT/'results/gio-baseline-review-01/packet',out)
            source=ROOT/'results/gio-baseline-review-01/packet'
            for name in ('seed.txt','seed.json','baseline.template.txt'):
                self.assertEqual((source/name).read_bytes(),(out/name).read_bytes())
            before=json.loads((source/'settings.json').read_text());after=json.loads((out/'settings.json').read_text())
            for key in ('models','routing','generation','cache','transport_retries','petri_judge_max_attempts','tools','epochs'):
                self.assertEqual(before[key],after[key],key)
            self.assertEqual(after['max_auditor_turns'],30)
            self.assertTrue((out/'review-instructions.txt').exists())
            self.assertEqual(run_baseline.validate_settings(after),30)

if __name__=='__main__':unittest.main()
