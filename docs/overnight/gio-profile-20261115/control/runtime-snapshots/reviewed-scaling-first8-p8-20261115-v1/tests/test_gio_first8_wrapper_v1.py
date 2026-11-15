"""Offline only: immutable native pins, synthetic plan/lease, stub runpy/fake HTTP."""
import ast,copy,hashlib,importlib.util,json,os,sys,tempfile,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
W=Path('/private/tmp/gio_diagnostic_runtime_envelope_first8_v1.py')
s=importlib.util.spec_from_file_location('first8_wrapper',W);w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
R=w.REFERENCE_ROOT;sys.path.insert(0,str(R))
s=importlib.util.spec_from_file_location('first8_native',R/'scripts/overnight_labeled_reference.py');native=importlib.util.module_from_spec(s);s.loader.exec_module(native)
from autoresearch.llm import Budget
INDEX=Path('/private/tmp/gio-profile-20261115-reference/original-first8-methods-runtime-3de7299/prepared-index.json')
assert hashlib.sha256(INDEX.read_bytes()).hexdigest()=='55791bc3636dd1c38c6267fab947edb580578d6fd742ded01f1d48290dc8ae43'
files=json.loads(INDEX.read_text())['runtime_identity']['files']
def ref(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
class Response:
 status=200;headers={'x-request-id':'SYNTHETIC_SECRET_CANARY'}
 def __init__(self,seen):self.seen=seen
 def __enter__(self):self.seen.append('enter');return self
 def __exit__(self,*a):self.seen.append('close');return False
 def read(self,n):
  self.seen.append(('read',n));return json.dumps({'status':'completed','usage':{'input_tokens':20,'output_tokens':10},'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'SYNTHETIC_RESPONSE'}]}]}).encode()
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  p=self.root/'synthetic-plan.json';p.write_text(json.dumps({'final':False,'protocol':w.PROTOCOL,'runtime':{'commit':w.RUNTIMES['reference'][0]}}));l=self.root/'test-only-not-issued-lease.json';l.write_text(json.dumps({'protocol':w.PROTOCOL,'plan_sha256':ref(p)['sha256']}));a=self.root/'synthetic-authority.json';a.write_text('{"state":"authorized","synthetic":true}')
  self.env={'schema_version':'diagnostic-runtime-envelope-v2','script_sha256':w.sha(W),'state':'authorized','authorization':ref(a),'observer':{'path':str(w.OBSERVER),'sha256':w.OBSERVER_SHA},'kind':'reference','runtime_root':str(R),'runtime_commit':w.RUNTIMES['reference'][0],'entrypoint':'scripts/overnight_labeled_reference.py','runtime_files':files,'deadline':'2026-11-15T17:00:00Z','denylist':ref(Path('/private/tmp/gio-diagnostic-envelope-proposal-v2/typed-denylist.json')),'inputs':{'plan':ref(p),'lease':ref(l)},'output_root':'/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/never-created-'+self.root.name}
 def test_native_exact_pins_protocol_and_cli(self):
  entry,args,blocked=w.validate(self.env,check_only=True);self.assertEqual(entry,R/'scripts/overnight_labeled_reference.py');self.assertEqual(args,['run','--plan',self.env['inputs']['plan']['path'],'--lease',self.env['inputs']['lease']['path']]);self.assertEqual(len(blocked['body_compact_json_sha256']),4);self.assertEqual(len(blocked['endpoint_body_sorted_json_sha256']),5)
 def test_other_protocol_commit_kind_or_root_rejected(self):
  for field,value in [('runtime_commit','63a2c21d1096700f816f4edf71048bcfd4891927'),('kind','profile'),('runtime_root',str(self.root))]:
   e=copy.deepcopy(self.env);e[field]=value
   with self.assertRaises((ValueError,FileNotFoundError)):w.validate(e,check_only=True)
  p=Path(self.env['inputs']['plan']['path']);x=json.loads(p.read_text());x['protocol']='newmethods-small-v1';p.write_text(json.dumps(x));self.env['inputs']['plan']=ref(p)
  with self.assertRaises(ValueError):w.validate(self.env,check_only=True)
 def test_missing_identity_namespace_rejected(self):
  d=self.root/'bad-deny.json';d.write_text(json.dumps({'schema_version':'provider-unknown-wire-denylist-v2','identity_denylists':{'body_compact_json_sha256':list(w.PROFILE)}}));self.env['denylist']=ref(d)
  with self.assertRaises(ValueError):w.validate(self.env,check_only=True)
 def test_transport_execution_and_diagnostics_are_unchanged(self):
  self.assertEqual(Path(sys.modules[native.OpenAILLM.__module__].__file__).resolve(),R/'autoresearch/taste/backends.py')
  env=copy.deepcopy(self.env);env['output_root']=str(self.root/'diagnostics');original=w.validate
  def validate(e):
   copy_e=copy.deepcopy(e);copy_e['output_root']=self.env['output_root'];return original(copy_e)
  seen=[];requests=[];backend=native.ReferenceBackend('gpt-6-luna',budget=Budget(max_calls=1,max_seconds=600),max_usd=.04,timeout=60,forbidden_wire_hashes=w.REFERENCE,forbidden_body_hashes=w.PROFILE,enforce_unique_requests=True)
  def opener(request,*a,**k):requests.append((request,a,k));return Response(seen)
  def entry(path,run_name):
   self.assertEqual(Path(path),R/'scripts/overnight_labeled_reference.py');self.assertEqual(Path.cwd(),R);self.assertEqual(sys.argv[1:],w.invocation(env));self.assertEqual(backend.complete('SYNTHETIC_PROMPT_é',system='SYNTHETIC_SYSTEM',max_tokens=1024),'SYNTHETIC_RESPONSE');raise SystemExit(0)
  with patch.object(w,'validate',side_effect=validate),patch.object(w.runpy,'run_path',side_effect=entry),patch.object(urllib.request,'urlopen',side_effect=opener),patch.dict(os.environ,{'OPENAI_API_KEY':'SYNTHETIC_KEY'},clear=True):self.assertEqual(w.execute(env),0)
  self.assertEqual(len(requests),1);request,a,k=requests[0];body={'model':'gpt-6-luna','instructions':'SYNTHETIC_SYSTEM','input':'SYNTHETIC_PROMPT_é','max_output_tokens':1024,'reasoning':{'effort':'none'},'store':False,'service_tier':'default'};self.assertEqual(request.data,json.dumps(body,ensure_ascii=False).encode());self.assertEqual(k,{'timeout':60});self.assertEqual(a,());self.assertEqual(seen,['enter',('read',8000001),'close']);self.assertEqual(backend.budget.calls,1);self.assertEqual(backend.cost_summary()['reserved_usd'],0)
  events=[json.loads(x) for x in (self.root/'diagnostics/events.jsonl').read_text().splitlines()];self.assertEqual(len(events),1);self.assertEqual(events[0]['request_sha256'],native.body_identity('gpt-6-luna','SYNTHETIC_PROMPT_é','SYNTHETIC_SYSTEM',1024));self.assertEqual(events[0]['endpoint_body_sha256'],native.wire_identity('gpt-6-luna','SYNTHETIC_PROMPT_é','SYNTHETIC_SYSTEM',1024));self.assertNotIn('SYNTHETIC',json.dumps(events));self.assertEqual(json.loads((self.root/'diagnostics/envelope-terminal.json').read_text())['status'],'complete')
 def test_unchanged_observer_and_execution_implementation(self):
  old=ast.parse(Path('/private/tmp/gio_diagnostic_runtime_envelope_v2.py').read_text());new=ast.parse(W.read_text())
  for name in ['EventLog','execute','digest','pinned','deadline','write']:
   x=next(n for n in old.body if getattr(n,'name',None)==name);y=next(n for n in new.body if getattr(n,'name',None)==name);self.assertEqual(ast.dump(x),ast.dump(y))
if __name__=='__main__':unittest.main()
