"""Synthetic full supervisor loop. No scientific entrypoints, environment or live ledger."""
import contextlib, importlib.util, io, json, sys, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
s = importlib.util.spec_from_file_location('independent_sol_v2', '/private/tmp/gio_scaling_sol_supervisor_v2.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
class FrozenTime:
    @classmethod
    def now(cls, tz=None): return datetime(2026,11,15,12,tzinfo=timezone.utc)
class Checks(unittest.TestCase):
    def fixture(self, *, nonzero=None, bad_delta=None, bad_diag=None, bad_admit=None, bad_live=None, pair='complete'):
        td = tempfile.TemporaryDirectory(dir='/private/tmp'); self.addCleanup(td.cleanup)
        base = Path(td.name); root = base/'supervisor'; stages=[]
        for n, block in enumerate(('core','lexical_retrieval','semantic_retrieval')):
            out=base/('diagnostics-'+str(n)); out.mkdir(); (out/'envelope-terminal.json').write_text('{}')
            stages.append({'block':block,'batch_id':'synthetic-'+str(n),'prepared':{'path':'/synthetic/prepared'+str(n),'sha256':str(n)*64},'jobs':1,'max_calls':1,'allowed':{},'envelope':{'output_root':str(out)},'remaining_max_usd':'1','remaining_schedule_seconds':1})
        expected={'batch_id':'synthetic-1','job_id':'paired-lexical','manifest_sha256':'a'*64,'item_id':'synthetic-item','item_sha256':'b'*64}
        stages[2]['paired_first']=expected
        result={'job_id':expected['job_id'],'manifest_hash':expected['manifest_sha256'],'status':'complete','counts':{'attempted':1,'complete':1,'error':0},'predictions':[dict(expected, status='complete', prediction={})]}
        if pair=='invalid': result['status']='partial'; result['predictions'][0]['status']='invalid'
        if pair=='wrong_item': result['predictions'][0]['item_id']='wrong-item'
        if pair=='wrong_manifest': result['manifest_hash']='wrong-manifest'
        result_path=base/'output'/expected['job_id']/'result.json'; result_path.parent.mkdir(parents=True); result_path.write_text(json.dumps(result))
        calls=[]; checks=[]; diagnostics=[]; admissions=[]
        w=SimpleNamespace(now=lambda:FrozenTime.now(), validate=lambda env:None)
        index={'policy':{'path':'/synthetic/policy','sha256':'c'*64},'predecessor':{'path':'/synthetic/predecessor','sha256':'d'*64}}
        policy={'scaling_authorization':{'path':'/synthetic/authority','sha256':'e'*64},'ledger':{'path':'/synthetic/ledger'}}
        def state(n): return {'attempts':n,'known_nanos':n*100,'held_nanos':0,'known_usd':str(n/10000000),'held_usd':'0','pending':0,'uncertain':0}
        def authority(*args,**kwargs):
            n=len(calls); admissions.append(n)
            if n==bad_admit: raise ValueError('synthetic_admission_failure')
            return policy,state(n),{}
        def child(args,**kwargs):
            n=len(calls); calls.append(n)
            self.assertEqual(args[:3],[sys.executable,'-B',m.g.WRAPPER['path']]); self.assertEqual(kwargs['env'],{}); self.assertFalse(kwargs['check'])
            return SimpleNamespace(returncode=2 if n==nonzero else 0)
        def native(ref,jobs,ceiling):
            n=int(ref['path'][-1]); checks.append(n)
            return {'attempted_calls':1,'known_spent_nanos':100,'ledger_attempts':n+1+(1 if n==bad_delta else 0),'ledger_spent_nanos':100*(n+1),'receipts':[{'result':m.ref(result_path)}] if n==1 else []}
        def diagnostic(*args):
            n=len(diagnostics); diagnostics.append(n)
            if n==bad_diag: raise ValueError('synthetic_denial_or_missing_diagnostics')
            return {'synthetic':True}
        def ledger(path):
            n=len(calls); st=state(n)
            if n-1==bad_live: st['uncertain']=1
            return st
        with patch.object(m,'B',base),patch.object(m,'ROOT',root),patch.object(m,'datetime',FrozenTime),patch.object(m,'preflight',return_value=(w,index,policy,stages)),patch.object(m.h,'validate_authority',side_effect=authority),patch.object(m.h,'ledger_read',side_effect=ledger),patch.object(m.subprocess,'run',side_effect=child),patch.object(m.g,'native_terminal',side_effect=native),patch.object(m.g,'diagnostic_terminal',side_effect=diagnostic),patch.object(m.os,'environ',{}),patch.object(sys,'argv',['synthetic-sol']),contextlib.redirect_stdout(io.StringIO()): code=m.main()
        terminal=json.loads((root/'supervisor-terminal.json').read_text())
        return code,calls,checks,diagnostics,admissions,terminal,root
    def test_exact_three_stage_main_with_specific_known_complete_pair(self):
        code,calls,checks,diags,admissions,t,root=self.fixture()
        self.assertEqual(code,0); self.assertEqual((calls,checks,diags,admissions),([0,1,2],)*4)
        self.assertEqual(t['known_verified_attempts'],3); self.assertEqual(t['known_verified_spend_nanos'],300)
        self.assertFalse(t['astra_admitted']); self.assertEqual(t['planned_batches'],3)
        self.assertIsNotNone(json.loads((root/'synthetic-2-started.json').read_text())['successful_paired_first'])
    def test_nonzero_stops_without_next_or_verification(self):
        for n in range(3):
            code,calls,checks,_,_,t,_=self.fixture(nonzero=n)
            self.assertEqual(code,2); self.assertEqual(calls,list(range(n+1))); self.assertEqual(checks,list(range(n))); self.assertEqual(t['stop_reason'],'child_nonzero')
    def test_unknown_or_missing_diagnostics_stops_before_next(self):
        for n in range(3):
            code,calls,_,_,_,t,_=self.fixture(bad_diag=n)
            self.assertEqual(code,2); self.assertEqual(calls,list(range(n+1))); self.assertEqual(t['known_verified_attempts'],n); self.assertEqual(t['stop_reason'],'terminal_verification_failed')
    def test_cumulative_attempt_mismatch_stops(self):
        for n in range(3):
            code,calls,_,_,_,t,_=self.fixture(bad_delta=n)
            self.assertEqual(code,2); self.assertEqual(calls,list(range(n+1))); self.assertEqual(t['known_verified_attempts'],n)
    def test_live_unknown_after_known_summary_stops(self):
        for n in range(3):
            code,calls,_,_,_,t,_=self.fixture(bad_live=n)
            self.assertEqual(code,2); self.assertEqual(calls,list(range(n+1))); self.assertEqual(t['known_verified_attempts'],n)
    def test_failed_readmission_does_not_launch(self):
        for n in range(3):
            code,calls,_,_,_,t,_=self.fixture(bad_admit=n)
            self.assertEqual(code,2); self.assertEqual(calls,list(range(n))); self.assertEqual(t['stop_reason'],'admission_or_child_launch_failed_inspect_existing_artifacts')
    def test_specific_pair_invalid_or_misbound_stops_before_semantic(self):
        for problem in ('invalid','wrong_item','wrong_manifest'):
            code,calls,_,_,_,t,root=self.fixture(pair=problem)
            self.assertEqual(code,2); self.assertEqual(calls,[0,1]); self.assertEqual(t['known_verified_attempts'],2)
            self.assertFalse((root/'synthetic-2-started.json').exists()); self.assertEqual(t['stop_reason'],'admission_or_child_launch_failed_inspect_existing_artifacts')
if __name__=='__main__': unittest.main()
