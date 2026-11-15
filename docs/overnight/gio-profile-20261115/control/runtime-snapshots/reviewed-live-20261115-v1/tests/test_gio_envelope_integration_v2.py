"""Offline wrapper integration: actual native pins, stub entrypoint, real f6 backend.
All outputs and SQLite are synthetic temporary files; native jobs never execute.
"""
import copy,hashlib,importlib.util,json,os,runpy,sys,tempfile,threading,unittest,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
wrapper=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else Path('/private/tmp/gio_diagnostic_runtime_envelope_v1.py')
s=importlib.util.spec_from_file_location('independent_envelope',wrapper);w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
R=Path('/Users/giordanorogers/.codex/worktrees/gio-overnight-phase2-runtime/AutoResearch-overnight-control');sys.path.insert(0,str(R))
from autoresearch.taste.overnight import backends
from autoresearch.llm import Budget
BATCH=Path('/private/tmp/gio-profile-20261115-coordinator/receipts/640775f0680757dfe9bb7ff339a3325a483c7848d78edc4b207c7fcf72690025/preparation/prepared.json')
def ref(p):p=Path(p);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
class Response:
 status=200
 headers={'x-request-id':'SYNTHETIC_SECRET_HEADER'}
 def __init__(self,history):self.history=history
 def __enter__(self):self.history.append('enter');return self
 def __exit__(self,*args):self.history.append('close');return False
 def read(self,n):
  self.history.append(('read',n))
  return json.dumps({'status':'completed','usage':{'input_tokens':20,'output_tokens':10},'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'SYNTHETIC_SUCCESS'}]}]}).encode()
class Checks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.ledger=backends.DollarLedger(self.root/'synthetic.sqlite',max_usd=1,deadline=w.DEADLINE,max_inflight=2)
  auth=self.root/'synthetic-auth.json';auth.write_text(json.dumps({'state':'authorized','purpose':'offline synthetic fixture only'}));deny=self.root/'deny.json';deny.write_text(json.dumps({'schema_version':'provider-unknown-wire-denylist-v2','identity_denylists':{'body_compact_json_sha256':sorted(w.PROFILE),'endpoint_body_sorted_json_sha256':sorted(w.REFERENCE)}}))
  entry=w.RUNTIMES['profile'][1];names={entry,'autoresearch/llm.py','autoresearch/taste/backends.py','autoresearch/taste/overnight/backends.py','autoresearch/taste/overnight/runner.py','autoresearch/taste/overnight/consumer.py','autoresearch/taste/overnight/contracts.py'}
  self.envelope={'schema_version':'diagnostic-runtime-envelope-v2','script_sha256':w.sha(wrapper),'state':'authorized','kind':'profile','runtime_root':str(R),'runtime_commit':w.RUNTIMES['profile'][0],'entrypoint':entry,'observer':{'path':str(w.OBSERVER),'sha256':w.OBSERVER_SHA},'deadline':w.DEADLINE,'runtime_files':{n:w.sha(R/n) for n in names},'denylist':ref(deny),'inputs':{'batch':ref(BATCH)},'output_root':str(self.root/'outputs'),'authorization':ref(auth)}
  native=copy.deepcopy(self.envelope);native['output_root']='/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/not-created-'+self.root.name
  self.entry,self.args,self.blocked=w.validate(native)
  self.history=[];self.requests=[]
 def backend(self):return backends.OpenAIResponsesBackend(model='gpt-6-luna',reasoning='medium',ledger=self.ledger,max_usd=.04,timeout=180,budget=Budget(max_calls=1,max_seconds=600,max_cost_usd=.04))
 def opener(self,request,*args,**kwargs):self.requests.append((request,args,kwargs));return Response(self.history)
 def execute(self,entry_stub,opener=None,clock=None):
  actual_validate=w.validate
  def temp_output_validation(env):
   copied=copy.deepcopy(env);copied['output_root']='/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/not-created-'+self.root.name
   return actual_validate(copied)
  def checked_stub(path,run_name):
   self.assertEqual(Path(path),self.entry);self.assertEqual(run_name,'__main__');self.assertEqual(sys.argv,[str(self.entry)]+self.args);self.assertEqual(Path.cwd(),R)
   return entry_stub()
  with patch.object(w,'validate',side_effect=temp_output_validation),patch.object(w.runpy,'run_path',side_effect=checked_stub),patch.object(urllib.request,'urlopen',side_effect=opener or self.opener),patch.dict(os.environ,{'OPENAI_API_KEY':'SYNTHETIC_KEY'},clear=True):
   if clock:
    with patch.object(w,'now',side_effect=clock):return w.execute(self.envelope)
   return w.execute(self.envelope)
 def terminal(self):return json.loads((self.root/'outputs/envelope-terminal.json').read_bytes())
 def test_native_pins_profile_argv_and_success_read_budget(self):
  def stub():self.assertEqual(self.backend().complete('SYNTHETIC_INPUT',system='SYNTHETIC_SYSTEM',max_tokens=2048,temperature=0),'SYNTHETIC_SUCCESS');raise SystemExit(0)
  self.assertEqual(self.execute(stub),0);self.assertEqual(self.args,['execute','--file',str(BATCH),'--sha256',ref(BATCH)['sha256']]);self.assertEqual(len(self.requests),1)
  self.assertEqual(self.requests[0][2],{'timeout':180});self.assertEqual(self.history,['enter',('read',8000001),'close']);self.assertEqual(self.ledger.summary()['uncertain'],0);self.assertEqual(self.terminal()['status'],'complete');self.assertEqual(self.terminal()['canonical_envelope_sha256'],w.digest(self.envelope));self.assertEqual(self.terminal()['wrapper_script_sha256'],w.sha(wrapper));self.assertEqual(json.loads((self.root/'outputs/ENVELOPE_CLAIM.json').read_text())['canonical_envelope_sha256'],w.digest(self.envelope))
  raw=(self.root/'outputs/events.jsonl').read_text();self.assertNotIn('SYNTHETIC_INPUT',raw);self.assertNotIn('SYNTHETIC_SECRET_HEADER',raw)
 def test_native_exit_code_is_preserved(self):
  def stub():raise SystemExit(7)
  self.assertEqual(self.execute(stub),7);self.assertEqual(self.requests,[]);self.assertEqual(self.terminal()['entry_exit_code'],7)
 def test_deadline_stops_before_transport_and_retains_native_hold(self):
  times=[]
  def clock():
   times.append(1);return datetime(2026,11,15,16,59,59,tzinfo=timezone.utc) if len(times)<3 else datetime(2026,11,15,17,0,0,tzinfo=timezone.utc)
  def stub():
   with self.assertRaises(RuntimeError):self.backend().complete('SYNTHETIC_INPUT',max_tokens=2048)
   raise SystemExit(2)
  self.assertEqual(self.execute(stub,clock=clock),2);self.assertEqual(self.requests,[]);self.assertEqual(self.ledger.summary()['uncertain'],1)
 def test_two_inflight_calls_finish_after_sink_failure_no_later_transport(self):
  barrier=threading.Barrier(2)
  def opener(request,*a,**k):self.requests.append((request,a,k));barrier.wait(timeout=5);return Response(self.history)
  def sink(*a,**k):raise OSError('SYNTHETIC_LOG_FAILURE')
  def stub():
   with ThreadPoolExecutor(max_workers=2) as pool:
    fs=[pool.submit(self.backend().complete,'SYNTHETIC_INPUT_'+str(i),max_tokens=2048) for i in range(2)]
    self.assertEqual([f.result() for f in fs],['SYNTHETIC_SUCCESS']*2)
   with self.assertRaises(RuntimeError):self.backend().complete('SYNTHETIC_LATER_INPUT',max_tokens=2048)
   raise SystemExit(2)
  with patch.object(w.EventLog,'__call__',side_effect=sink):self.assertEqual(self.execute(stub,opener),2)
  self.assertEqual(len(self.requests),2);self.assertEqual(self.history.count('close'),2);self.assertEqual(self.ledger.summary()['attempts'],3);self.assertEqual(self.ledger.summary()['uncertain'],1);self.assertTrue(self.terminal()['diagnostics']['diagnostic_write_failed'])
 def test_log_close_failure_keeps_safe_terminal(self):
  original=w.EventLog.close
  def close(log):original(log);raise OSError('SYNTHETIC_CLOSE_CANARY')
  def stub():raise SystemExit(7)
  with patch.object(w.EventLog,'close',side_effect=close,autospec=True):code=self.execute(stub)
  self.assertNotEqual(code,0);self.assertEqual(self.terminal()['status'],'stopped');self.assertNotIn('SYNTHETIC_CLOSE_CANARY',json.dumps(self.terminal()));self.assertEqual(self.terminal()['entry_exit_code'],7);self.assertTrue(self.terminal()['diagnostics']['diagnostic_close_failed'])
if __name__=='__main__':unittest.main()
