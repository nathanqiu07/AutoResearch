"""Full one-child supervisor with synthetic accounting, files and subprocess only."""
import contextlib, importlib.util, io, json, sys, tempfile, unittest
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
s=importlib.util.spec_from_file_location('first4_main','/private/tmp/gio_p8_first4_supervisor_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Frozen:
 @classmethod
 def now(cls,tz=None):return datetime(2026,11,15,12,tzinfo=timezone.utc)
class Tests(unittest.TestCase):
 def fixture(self,failure=None):
  td=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(td.cleanup);base=Path(td.name);root=base/'supervisor';diag=base/'diagnostic';diag.mkdir();(diag/'envelope-terminal.json').write_text('{}')
  baseline={'attempts':280,'spent':1000000000};index={'authority':{'path':'/synthetic/auth','sha256':'a'*64},'prepared':{'path':'/synthetic/prepared','sha256':'b'*64}};env={'output_root':str(diag)};calls=[];checks=[]
  w=SimpleNamespace(now=lambda:Frozen.now(),validate=lambda e:None)
  def state(n):return {'attempts':280+n,'known_nanos':1000000000+n*100,'known_usd':str(1+n/10000000),'held_usd':'0','pending':0,'uncertain':0}
  def authority(*a,**k):
   if failure=='admission':raise ValueError('synthetic_admission')
   n=4 if calls else 0;actual=state(n)
   if failure=='unexpected_attempt' and calls:actual['attempts']+=1
   return {},{},actual,{},baseline
  def child(args,**kw):calls.append('child');self.assertEqual(args[:3],[sys.executable,'-B',m.g.WRAPPER['path']]);self.assertEqual(kw['env'],{});return SimpleNamespace(returncode=2 if failure=='nonzero' else 0)
  def native(*a):
   checks.append('native')
   if failure=='unknown':raise ValueError('synthetic_unknown')
   return {'attempted_calls':4,'known_spent_nanos':400,'ledger_attempts':284,'ledger_spent_nanos':1000000400,'outcomes':[{'status':x} for x in ('complete','invalid','empty','unavailable')]}
  def diagnostic(*a):
   checks.append('diagnostic')
   if failure=='diagnostic':raise ValueError('synthetic_missing_diagnostics')
   return {'synthetic':True}
  with patch.object(m,'ROOT',root),patch.object(m,'datetime',Frozen),patch.object(m,'preflight',return_value=(w,index,{}, {},baseline,{},env)),patch.object(m.h,'validate_authority',side_effect=authority),patch.object(m.subprocess,'run',side_effect=child),patch.object(m,'native_terminal',side_effect=native),patch.object(m.g,'diagnostic_terminal',side_effect=diagnostic),patch.object(m.os,'environ',{}),patch.object(sys,'argv',['first4','--ready-index','/synthetic/index','c'*64]),contextlib.redirect_stdout(io.StringIO()):code=m.main()
  terminal=json.loads((root/'supervisor-terminal.json').read_text());return code,calls,checks,terminal
 def test_one_known_batch_preserves_noncomplete_scientific_outputs(self):
  code,calls,checks,t=self.fixture();self.assertEqual(code,0);self.assertEqual(calls,['child']);self.assertEqual(checks,['native','diagnostic']);self.assertEqual(t['status'],'complete');self.assertIsNotNone(t['verified']);self.assertEqual(t['future_prediction_jobs_admitted'],0)
 def test_nonzero_no_verify_or_retry(self):
  code,calls,checks,t=self.fixture('nonzero');self.assertEqual(code,2);self.assertEqual(calls,['child']);self.assertEqual(checks,[]);self.assertEqual(t['stop_reason'],'child_nonzero')
 def test_unknown_diagnostic_or_cumulative_mismatch_never_completes(self):
  for failure in ('unknown','diagnostic','unexpected_attempt'):
   code,calls,checks,t=self.fixture(failure);self.assertEqual(code,2);self.assertEqual(calls,['child']);self.assertIsNone(t['verified']);self.assertFalse(t['native_accounting_drain_verified'])
 def test_failed_readmission_creates_no_child(self):
  code,calls,checks,t=self.fixture('admission');self.assertEqual(code,2);self.assertEqual(calls,[]);self.assertEqual(checks,[]);self.assertEqual(t['status'],'stopped')
if __name__=='__main__':unittest.main()
