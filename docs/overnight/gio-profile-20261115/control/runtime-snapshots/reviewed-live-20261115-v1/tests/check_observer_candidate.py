#!/usr/bin/env python3
"""Exercise the actual candidate observer with offline reconstructed requests."""
import importlib.util,json
from pathlib import Path
import urllib.request
from verify_unknown_identities import build_requests,file_sha,reference_hash,profile_hash,DENY,DENY_SHA
OBSERVER=Path('/private/tmp/gio_provider_diagnostics_v3.py')
EXPECTED='d2f3372e2689adf7bdef74fc6170fa25eca7bce4b4aa3de98b495633bf284233'
QUEUE=Path('/private/tmp/gio-profile-20261115-reference/continuation31-preparation-20261115T122009Z/queue.json')
assert file_sha(OBSERVER)==EXPECTED
spec=importlib.util.spec_from_file_location('actual_candidate_observer',OBSERVER)
observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
requests,reconstruction=build_requests()
denied={observer.BODY_IDENTITY:[],observer.ENDPOINT_IDENTITY:[]}
for kind,expected,request in requests:
 denied[observer.BODY_IDENTITY if kind=='profile' else observer.ENDPOINT_IDENTITY].append(expected)
class Response:
 status=200
 headers={}
 def __enter__(self): return self
 def __exit__(self,*args): return False
 def read(self,*args): return b'{}'
checks=[]; denied_count=0; forwarded_count=0
for kind,expected,request in requests:
 meta=observer.request_metadata(request)
 assert meta['request_sha256']==profile_hash(request)
 assert meta['endpoint_body_sha256']==reference_hash(request)
 for variant in ['actual_wire','reserialized_equivalent_body']:
  req=request if variant=='actual_wire' else urllib.request.Request(request.full_url,data=json.dumps(json.loads(request.data),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode(),method='POST')
  calls=[];events=[]
  def opener(*args,**kwargs): calls.append((args,kwargs));return Response()
  with observer.observe(events.append,opener=opener,identity_denylists=denied) as state:
   try:urllib.request.urlopen(req,timeout=7.25)
   except ValueError as exc:assert str(exc)=='request_identity_denied_no_dispatch'
   else:raise AssertionError('known unknown reached transport')
  assert calls==[] and len(events)==1 and events[0]['stage']=='denied_before_transport'
  assert state.summary()=={'diagnostic_write_failed':False,'dropped_event_count':0}
  denied_count+=1
 # A changed input must reach the synthetic transport unchanged; never the network.
 body=json.loads(request.data);body['input']+='\n__OFFLINE_IDENTITY_NEGATIVE__'
 changed=urllib.request.Request(request.full_url,data=json.dumps(body,ensure_ascii=False).encode(),method='POST')
 raw=changed.data; calls=[];events=[]
 def opener(*args,**kwargs):calls.append((args,kwargs));return Response()
 with observer.observe(events.append,opener=opener,identity_denylists=denied):
  with urllib.request.urlopen(changed,timeout=7.25) as response:assert response.read(99)==b'{}'
 assert len(calls)==1 and calls[0][0][0] is changed and calls[0][1]=={'timeout':7.25} and changed.data==raw
 assert len(events)==1 and events[0]['stage']=='open'; forwarded_count+=1
 checks.append({'kind':kind,'expected_hash':expected,'actual_identity_matches':True,
                'actual_and_reserialized_blocked_before_transport':True,
                'changed_input_forwarded_to_synthetic_opener_unchanged':True})
# Static input comparison only: every exact reference unknown is a preference
# prediction over a dataset context/options pair. Future model-generated fields
# are not guessed or enumerated here.
queue=json.loads(QUEUE.read_text()); assert queue['count']==31 and len(queue['jobs'])==31
inputs=set();row_count=0;users=[]
for job in queue['jobs']:
 plan_path=Path(job['plan']['path']);assert file_sha(plan_path)==job['plan']['sha256']
 records=plan_path.parent/'records.jsonl';assert file_sha(records)==job['plan']['snapshots']['records.jsonl']
 users.append(job['user_id'])
 for line in records.read_text().splitlines():
  row=json.loads(line);assert row['user_split']=='dev';choice=row['choice'];row_count+=1
  inputs.add((choice['context'],choice['a_text'],choice['b_text']))
static=[]
for kind,expected,request in requests:
 if kind!='reference':continue
 body=json.loads(request.data);payload=json.loads(body['input'].split('\nINPUT_JSON:\n',1)[1])
 assert sorted(payload)==['context','options','past_choices','persona','principles']
 match=(payload['context'],*payload['options']) in inputs
 assert not match
 static.append({'request_sha256':expected,'matching_fixed_context_options':False})
assert file_sha(OBSERVER)==EXPECTED
print(json.dumps({'status':'candidate observer exact-body checks passed; dispatcher authorization not assessed',
 'observer_path':str(OBSERVER),'observer_sha256':EXPECTED,'denylist_path':str(DENY),'denylist_sha256':DENY_SHA,
 'identity_denylists':denied,'checks':checks,'known_request_variants_denied_before_transport':denied_count,
 'changed_request_synthetic_forwards':forwarded_count,'network_calls':0,'raw_bodies_persisted':False,
 'unchanged_terminal_cache_prefixes':5,'queue_path':str(QUEUE),'queue_sha256':file_sha(QUEUE),
 'fixed_queue_user_count':len(users),'fixed_queue_record_count':row_count,'fixed_context_option_tuple_count':len(inputs),
 'static_reference_disjointness':static,
 'limits':['Static tuple disjointness excludes equality with these five known reference prediction requests under the current fixed methods; it does not enumerate all future generated bodies.',
 'M2 validation requests/persona and M3 principle scoring/target prediction requests contain model-generated text and selection results. Exact future bodies must be checked immediately before transport.',
 'Profile identity is compact sorted body JSON without endpoint. Reference identity is sorted endpoint-plus-body JSON using default separators. Never normalize text inside string fields.',
 'This is offline candidate semantic evidence, not authorization to launch or evidence of provider health.']},sort_keys=True,indent=2))
