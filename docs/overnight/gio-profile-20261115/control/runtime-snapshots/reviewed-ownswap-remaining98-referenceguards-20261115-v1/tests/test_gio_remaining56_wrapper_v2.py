"""Offline only: immutable native pins, synthetic plan/lease, stub runpy/fake HTTP."""
import ast,copy,hashlib,importlib.util,json,os,sys,tempfile,unittest,urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
W=Path('/private/tmp/gio_diagnostic_runtime_envelope_remaining56_v2.py')
s=importlib.util.spec_from_file_location('remaining56_wrapper',W);w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
R=w.REFERENCE_ROOT;sys.path.insert(0,str(R))
s=importlib.util.spec_from_file_location('remaining56_native',R/'scripts/overnight_labeled_reference.py');native=importlib.util.module_from_spec(s);s.loader.exec_module(native)
from autoresearch.llm import Budget
INDEX=Path('/private/tmp/gio-profile-20261115-reference/remaining56-runtime-9664557/prepared-index.json')
assert hashlib.sha256(INDEX.read_bytes()).hexdigest()=='45556f9e6cb00f5ede2ac53d545108ee4d6c8decaa4e740944118c43315c8b73'
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
  self.env={'schema_version':'diagnostic-runtime-envelope-v2','script_sha256':w.sha(W),'state':'authorized','authorization':ref(a),'observer':{'path':str(w.OBSERVER),'sha256':w.OBSERVER_SHA},'kind':'reference','runtime_root':str(R),'runtime_commit':w.RUNTIMES['reference'][0],'entrypoint':'scripts/overnight_labeled_reference.py','runtime_files':files,'deadline':'2026-11-15T17:00:00Z','denylist':w.DENYLIST,'inputs':{'plan':ref(p),'lease':ref(l)},'output_root':'/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/never-created-'+self.root.name}
 def test_native_exact_pins_protocol_and_cli(self):
  entry,args,blocked=w.validate(self.env,check_only=True);self.assertEqual(entry,R/'scripts/overnight_labeled_reference.py');self.assertEqual(args,['run','--plan',self.env['inputs']['plan']['path'],'--lease',self.env['inputs']['lease']['path']]);self.assertEqual(len(blocked['body_compact_json_sha256']),7);self.assertEqual(len(blocked['endpoint_body_sorted_json_sha256']),8)
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
  old=ast.parse(Path('/private/tmp/gio_diagnostic_runtime_envelope_first8_v1.py').read_text());new=ast.parse(W.read_text())
  for name in ['EventLog','execute','digest','pinned','deadline','write']:
   x=next(n for n in old.body if getattr(n,'name',None)==name);y=next(n for n in new.body if getattr(n,'name',None)==name);self.assertEqual(ast.dump(x),ast.dump(y))
 def test_exact_typed_guard_pin_required_even_for_superset_or_missing_namespace(self):
  original=json.loads(Path(w.DENYLIST['path']).read_text())
  for value in [original,dict(original,identity_denylists={'body_compact_json_sha256':list(w.PROFILE)})]:
   copied=self.root/'different-guard.json';copied.write_text(json.dumps(value));env=copy.deepcopy(self.env);env['denylist']=ref(copied)
   with self.assertRaisesRegex(ValueError,'exact_remaining56_typed12_guard'):w.validate(env,check_only=True)
 def test_lease_protocol_mismatch_and_unrelated_first8_runtime_rejected(self):
  lease_path=Path(self.env['inputs']['lease']['path']);lease=json.loads(lease_path.read_text());lease['protocol']='original-first8-v1';lease_path.write_text(json.dumps(lease));env=copy.deepcopy(self.env);env['inputs']['lease']=ref(lease_path)
  with self.assertRaisesRegex(ValueError,'reference_plan_or_lease'):w.validate(env,check_only=True)
  env=copy.deepcopy(self.env);env['runtime_root']='/Users/giordanorogers/.codex/worktrees/gio-reference-original-eight/AutoResearch-overnight-control'
  with self.assertRaisesRegex(ValueError,'exact_remaining56_runtime'):w.validate(env,check_only=True)
class AdditiveGuardTests(unittest.TestCase):
 def test_old_typed11_preserved_and_only_one_unknown_added(self):
  old_path=Path('/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json')
  self.assertEqual(hashlib.sha256(old_path.read_bytes()).hexdigest(),'7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe')
  old=json.loads(old_path.read_text());new=w.pinned(w.DENYLIST)
  added={'body_compact_json_sha256':'92e5c50ed2582ac0ef62294932f75d7be0232bcdf71836feb5ba2b8c6256d6ce','endpoint_body_sorted_json_sha256':'875949ac69d84213402ca429152aa351e43daefbc4acff988f80278d68d4a1bd'}
  for key,value in added.items():self.assertEqual(set(new['identity_denylists'][key]),set(old['identity_denylists'][key])|{value})
  self.assertEqual(new['historical_unknown_attempts'],12);self.assertEqual(new['identity_entries'],15)
  self.assertFalse(new['authorizes_execution_or_retry']);self.assertFalse(new['releases_any_reservation'])
  self.assertEqual(new['prior_denylist'],ref(old_path))
 def test_successor_diff_only_pin_and_fixed_guard_error_name(self):
  original=Path('/private/tmp/gio_diagnostic_runtime_envelope_remaining56_v1.py')
  self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),'c790245dfa0dab6676e6e42ecdd285cbff8637832a252009435828c56f574b78')
  tree=ast.parse(W.read_text());prior=ast.parse(original.read_text())
  old_deny=next(n.value for n in prior.body if isinstance(n,ast.Assign) and any(getattr(t,'id',None)=='DENYLIST' for t in n.targets))
  for node in tree.body:
   if isinstance(node,ast.Assign) and any(getattr(t,'id',None)=='DENYLIST' for t in node.targets):node.value=old_deny
  for node in ast.walk(tree):
   if isinstance(node,ast.Constant) and node.value=='exact_remaining56_typed12_guard_required':node.value='exact_remaining56_typed11_guard_required'
  self.assertEqual(ast.dump(tree),ast.dump(prior))
 def test_new_unknown_does_not_overlap98_reviewed_wires(self):
  path=Path('/private/tmp/gio-remaining98-offline-proposal-v1/proposal.json')
  self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'f4a3f205971944477a8d428ab3e482d828bc9307867ed814bd5313be1b486696')
  requests=[request for draft in json.loads(path.read_text())['drafts'] for request in draft['requests']]
  self.assertEqual(len(requests),98);deny=w.pinned(w.DENYLIST)['identity_denylists']
  self.assertFalse({r['request_sha256'] for r in requests}&set(deny['body_compact_json_sha256']))
  self.assertFalse({r['endpoint_body_sha256'] for r in requests}&set(deny['endpoint_body_sorted_json_sha256']))
 def test_reconstructed_unknown_denied_by_each_namespace_in_offline_subprocess(self):
  import subprocess
  code=r'''
import hashlib,importlib.util,json,urllib.request
from pathlib import Path
def load(name,path,sha):
 assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=load('offline_unknown_reconstruction','/private/tmp/gio-profile-20261115-reference/incidents/remaining56-stop-1433-v1/reconstruct_unknown.py','a25e48cb051f0bba510a677aab38f628f6e64493b64de0bb9f48e2d0a7960479')
o=load('observer','/private/tmp/gio_provider_diagnostics_v3.py','d2f3372e2689adf7bdef74fc6170fa25eca7bce4b4aa3de98b495633bf284233')
request,meta=r.build_request();assert meta['source_cache_unchanged'] and meta['network_calls']==0
expected={'body_compact_json_sha256':'92e5c50ed2582ac0ef62294932f75d7be0232bcdf71836feb5ba2b8c6256d6ce','endpoint_body_sorted_json_sha256':'875949ac69d84213402ca429152aa351e43daefbc4acff988f80278d68d4a1bd'}
assert all(meta[key]==value for key,value in expected.items())
calls=[];events=[]
def opener(*args,**kwargs):calls.append((args,kwargs));raise AssertionError('denied request reached transport')
reserialized=urllib.request.Request(request.full_url,data=json.dumps(json.loads(request.data),sort_keys=True,ensure_ascii=False,indent=2).encode(),headers={'Authorization':'Bearer synthetic-only'})
for candidate in (request,reserialized):
 for kind,value in expected.items():
  with o.observe(events.append,opener=opener,identity_denylists={kind:[value]}):
   try:urllib.request.urlopen(candidate,timeout=60)
   except ValueError as exc:assert str(exc)=='request_identity_denied_no_dispatch'
   else:raise AssertionError('unknown request not denied')
assert not calls and len(events)==4 and all(e['stage']=='denied_before_transport' for e in events)
print(json.dumps({'exact_namespace_denials':2,'equivalent_reserialization_denials':2,'underlying_transport_calls':0,'source_cache_unchanged':True}))
'''
  completed=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,check=True)
  self.assertEqual(json.loads(completed.stdout),{'exact_namespace_denials':2,'equivalent_reserialization_denials':2,'underlying_transport_calls':0,'source_cache_unchanged':True})
if __name__=='__main__':unittest.main()
