"""Synthetic main-loop review: no scientific entrypoints, sockets or ledger reads."""
import importlib.util,json,sys,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
s=importlib.util.spec_from_file_location('review204','/private/tmp/gio_profile204_supervisor_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Checks(unittest.TestCase):
 def run_fixture(self,*,nonzero=None,bad_delta=None,bad_diag=None,admission_failure=None):
  td=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(td.cleanup);base=Path(td.name);root=base/'supervisor'
  stages=[]
  for n in range(4):
   out=base/('diagnostics-'+str(n));out.mkdir();(out/'envelope-terminal.json').write_text('{}')
   stages.append({'batch_id':'synthetic-'+str(n),'prepared':{'path':'/synthetic/prepared'+str(n),'sha256':str(n)*64},'jobs':1,'max_calls':1,'allowed':{},'envelope':{'output_root':str(out)}})
  calls=[];verifies=[];diagchecks=[];admissions=[]
  def validate(e):
   idx=int(Path(e['output_root']).name.rsplit('-',1)[1]);admissions.append(idx)
   if idx==admission_failure:raise ValueError('synthetic_admission_failure')
  w=SimpleNamespace(now=lambda:datetime(2026,11,15,12,tzinfo=timezone.utc),deadline=lambda _:datetime(2026,11,15,17,tzinfo=timezone.utc),validate=validate)
  def child(args,**kwargs):
   n=len(calls);calls.append(n);self.assertEqual(args[0:3],[sys.executable,'-B',m.WRAPPER['path']]);self.assertEqual(args[3],'--envelope');self.assertFalse(kwargs['check']);self.assertEqual(kwargs['stdin'],m.subprocess.DEVNULL)
   return SimpleNamespace(returncode=2 if n==nonzero else 0)
  def native(ref,jobs,ceiling):
   n=int(ref['path'][-1]);verifies.append(n)
   return {'attempted_calls':1,'known_spent_nanos':100,'ledger_attempts':n+1+(1 if n==bad_delta else 0),'ledger_spent_nanos':100*(n+1)}
  def diagnostic(er,tr,allowed,attempts):
   n=len(diagchecks);diagchecks.append(n)
   if n==bad_diag:raise ValueError('synthetic_missing_or_unknown_diagnostics')
   return {'synthetic':True}
  with patch.object(m,'ROOT',root),patch.object(m,'preflight',return_value=(w,stages,{})),patch.object(m,'predecessor',return_value={}),patch.object(m.subprocess,'run',side_effect=child),patch.object(m,'native_terminal',side_effect=native),patch.object(m,'diagnostic_terminal',side_effect=diagnostic),patch.object(sys,'argv',['supervisor','--predecessor','/synthetic/gate','a'*64]):code=m.main()
  terminal=json.loads((root/'supervisor-terminal.json').read_bytes())
  return code,calls,verifies,diagchecks,admissions,terminal
 def test_allfour_sequential_known_accounting(self):
  code,calls,verify,diag,admit,t=self.run_fixture();self.assertEqual((calls,verify,diag,admit),([0,1,2,3],)*4);self.assertEqual(code,0);self.assertEqual(t['known_verified_attempts'],4);self.assertEqual(t['known_verified_spend_nanos'],400)
 def test_child_nonzero_never_verifies_or_runs_next(self):
  for i in range(4):
   code,calls,verify,diag,admit,t=self.run_fixture(nonzero=i);self.assertEqual(calls,list(range(i+1)));self.assertEqual(verify,list(range(i)));self.assertEqual(t['stop_reason'],'child_nonzero');self.assertEqual(code,2)
 def test_extra_ledger_attempt_stops_before_next_child(self):
  for i in range(4):
   code,calls,verify,diag,admit,t=self.run_fixture(bad_delta=i);self.assertEqual(calls,list(range(i+1)));self.assertEqual(t['known_verified_attempts'],i);self.assertEqual(t['stop_reason'],'terminal_verification_failed');self.assertEqual(code,2)
 def test_diagnostic_failure_stops_before_next_child(self):
  for i in range(4):
   code,calls,verify,diag,admit,t=self.run_fixture(bad_diag=i);self.assertEqual(calls,list(range(i+1)));self.assertEqual(t['known_verified_attempts'],i);self.assertEqual(t['stop_reason'],'terminal_verification_failed');self.assertEqual(code,2)
 def test_failed_readmission_never_launches_stage(self):
  for i in range(4):
   code,calls,verify,diag,admit,t=self.run_fixture(admission_failure=i);self.assertEqual(calls,list(range(i)));self.assertEqual(t['known_verified_attempts'],i);self.assertEqual(t['stop_reason'],'admission_or_child_launch_failed_inspect_existing_artifacts');self.assertEqual(code,2)
if __name__=='__main__':unittest.main()
