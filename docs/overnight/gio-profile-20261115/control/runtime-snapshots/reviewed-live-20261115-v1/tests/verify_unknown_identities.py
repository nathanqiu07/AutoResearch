#!/usr/bin/env python3
"""Offline-only unknown-request reconstruction; stdout/artifacts contain metadata only.

build_requests() retains exact bodies only in memory for an independent observer
consumer. It replays existing caches, never calls a provider, never writes caches.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import urllib.request

sys.dont_write_bytecode = True
RUNTIME = Path('/Users/giordanorogers/.codex/worktrees/gio-overnight-reference/AutoResearch-overnight-control')
ROOT = Path('/private/tmp/gio-profile-20261115-reference')
DENY = Path('/private/tmp/gio-profile-incident-1154-review-v1/combined-provider-unknown-denylist.json')
DENY_SHA = '8804a408fd50f1617f4a4004b05d7a6453fc94b16b30e7fca061d6548d977750'
CASES = [
 ('prism:user949', 'm3', ROOT/'panel-01', '970b0250ee8dabc2697b1f9238e9af8fc6b97529d448c40db1cefd9cbc47df20'),
 ('prism:user542', 'm2', ROOT/'expansion64-20261115T1030Z/single-user/user-016', '07dce1746df8add55316a78b4daa5f1b5fc970481658430b90c920a1bf2146af'),
 ('prism:user784', 'm1', ROOT/'expansion64-20261115T1030Z/single-user/user-030', 'ab348ae8891196294f5ec63f8eefbb6570a03a6528528f8aa26d5fad9495b92d'),
 ('prism:user341', 'm2', ROOT/'expansion64-20261115T1030Z/single-user/user-033', 'f518fde206aaa61d435483d4cf8004aa2aa90bfc1fc0f3a368db116bf292dd50'),
 ('prism:user496', 'm2', ROOT/'expansion64-20261115T1030Z/single-user/user-034', '9f578c13992fccde020f875f62302f7a6dfea56d7889b7d0a8519e041e13ab29'),
]
def sha(value): return hashlib.sha256(value).hexdigest()
def file_sha(p): return sha(Path(p).read_bytes())
def reference_hash(request):
 return sha(json.dumps({'endpoint':request.full_url,'body':json.loads(request.data)},ensure_ascii=False,sort_keys=True).encode())
def profile_hash(request):
 return sha(json.dumps(json.loads(request.data),ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode())

def forbid_network(event, args):
 if event.startswith('socket.'):
  raise RuntimeError('offline verifier prohibits all socket operations')
sys.addaudithook(forbid_network)

class Captured(BaseException):
 def __init__(self, request): self.request=request

def capture(request,*args,**kwargs): raise Captured(request)
urllib.request.urlopen = capture

def cache_snapshot(path):
 return {str(p.relative_to(path)):file_sha(p) for p in sorted(path.rglob('*')) if p.is_file()}

def build_requests():
 assert file_sha(DENY)==DENY_SHA
 deny=json.loads(DENY.read_text())
 requests=[]; metadata=[]
 sys.path.insert(0,str(RUNTIME))
 spec=importlib.util.spec_from_file_location('frozen_reference_wrapper',RUNTIME/'scripts/overnight_labeled_reference.py')
 wrapper=importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
 from autoresearch.llm import Budget
 from autoresearch.taste.methods import create_method
 from autoresearch.taste.prefdata import load_records
 # A deliberately fake credential satisfies the unchanged backend's presence check.
 # No real credential is loaded. Socket audit prohibition is process-wide.
 os.environ['OPENAI_API_KEY']='offline-synthetic-no-network'
 os.environ.pop('OPENAI_ORG_ID',None); os.environ.pop('OPENAI_PROJECT_ID',None)
 for user,method,packet,expected in CASES:
  plan=json.loads((packet/'plan.json').read_text())
  assert plan['runtime']['commit']=='63a2c21d1096700f816f4edf71048bcfd4891927'
  assert all(file_sha(RUNTIME/name)==value for name,value in plan['runtime']['files'].items())
  assert user in plan['user_ids'] and plan['user_partition']=='dev' and not plan['final']
  manifest=json.loads((packet/'manifest.json').read_text())
  records=list(load_records(packet/'records.jsonl'))
  assert all(r.user_split=='dev' for r in records)
  by_id={r.choice.identity:r.choice for r in records}
  split=manifest['users'][user]
  history,val,target=([by_id[i] for i in split[s]] for s in ('history','val','test'))
  cache=packet/'cache'; before=cache_snapshot(cache)
  backend=wrapper.ReferenceBackend(plan['model'],budget=Budget(max_calls=10000,max_seconds=600),max_usd=5)
  model=create_method(method,backend,seed=0,cache_dir=cache,max_calls=10000,**plan['method_config'])
  phase='fit'; target_id=None
  try:
   model.fit(history,val)
   phase='target_prediction'
   for row in target:
    target_id=row.identity
    model.predict(row.context,[row.a_text,row.b_text])
  except Captured as exc:
   request=exc.request
  else: raise AssertionError('No absent request reached')
  assert before==cache_snapshot(cache), 'Cache changed'
  actual=reference_hash(request)
  assert actual==expected and actual in deny['request_sha256'], 'Reference identity differs'
  requests.append(('reference',expected,request))
  metadata.append({'kind':'reference','user_id':user,'method':method,'phase':phase,
   'packet':str(packet),'plan_sha256':file_sha(packet/'plan.json'),
   'records_sha256':file_sha(packet/'records.jsonl'),'manifest_sha256':file_sha(packet/'manifest.json'),
   'cache_entries':len(before),'cache_snapshot_sha256':sha(json.dumps(before,sort_keys=True).encode()),
   'cache_hits_before_missing_request':model.cost['cache_hits'],'cache_unchanged':True,
   'canonical_request_sha256':actual,'profile_convention_sha256':profile_hash(request),
   'raw_body_sha256':sha(request.data),'body_bytes':len(request.data),'target_example_id':target_id,
   'expected_hash_match':True,'actual_runtime_request_constructed':True})
 for item in deny['profile_unknowns']:
  p=Path(item['started_trace']['path']); assert file_sha(p)==item['started_trace']['sha256']
  trace=json.loads(p.read_text()); b=trace['backend']; s=trace['settings']; e=b['enforced_settings']
  body={'model':b['model'],'instructions':s['system'],'input':trace['prompt'],
   'max_output_tokens':s['max_tokens'],'reasoning':{'effort':e['reasoning_effort']},
   'store':False,'service_tier':'default','prompt_cache_options':e['prompt_cache_options']}
  request=urllib.request.Request(b['endpoint'],data=json.dumps(body,ensure_ascii=False,allow_nan=False).encode(),method='POST')
  actual=profile_hash(request); assert actual==item['request_sha256']
  requests.append(('profile',actual,request))
  metadata.append({'kind':'profile','job_id':item['job_id'],'attempt':item['attempt'],
   'trace_path':str(p),'trace_sha256':file_sha(p),'canonical_request_sha256':actual,
   'reference_convention_sha256':reference_hash(request),'expected_hash_match':True,
   'adapter_implementation_sha256':e['adapter_implementation_sha256'],
   'reconstruction_basis':'saved started trace with frozen body fields; no raw body persisted'})
 assert len(requests)==9
 return requests,metadata

if __name__=='__main__':
 requests,metadata=build_requests()
 print(json.dumps({'denylist_path':str(DENY),'denylist_sha256':DENY_SHA,'network_prohibited':True,
  'real_credentials_loaded':False,'cache_writes':False,'raw_bodies_persisted':False,
  'requests':metadata},sort_keys=True,indent=2))
