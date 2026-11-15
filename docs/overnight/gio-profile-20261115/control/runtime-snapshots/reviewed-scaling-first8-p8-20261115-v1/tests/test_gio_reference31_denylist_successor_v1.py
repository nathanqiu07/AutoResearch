"""Redacted-hash denial and synthetic serialization checks; no raw unknown bodies read.
SHA substitutions test actual recorded lookup values without reconstructing targets.
"""
import copy,hashlib,importlib.util,json,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
D=Path('/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json');DS='7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'
assert hashlib.sha256(D.read_bytes()).hexdigest()==DS
deny=json.loads(D.read_text());oldref=deny['prior_denylist'];assert hashlib.sha256(Path(oldref['path']).read_bytes()).hexdigest()==oldref['sha256'];old=json.loads(Path(oldref['path']).read_text())
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
obs=load('deny_review_observer','/private/tmp/gio_provider_diagnostics_v3.py')
ENDPOINT='https://api.openai.com/v1/responses'
def fixture(n):
 body={'model':'synthetic-neutral','input':'SYNTHETIC_ONLY_é_'+str(n),'max_output_tokens':1}
 raw1=json.dumps(body,ensure_ascii=False).encode();raw2=json.dumps(dict(reversed(list(body.items()))),ensure_ascii=True,indent=2).encode()
 return body,[urllib.request.Request(ENDPOINT,data=raw,method='POST') for raw in (raw1,raw2)]
class Response:
 status=200;headers={}
class Tests(unittest.TestCase):
 def test_preserves_old9_and_adds_both_recorded_namespaces(self):
  self.assertEqual(len(deny['identity_denylists'][obs.BODY_IDENTITY]),6);self.assertEqual(len(deny['identity_denylists'][obs.ENDPOINT_IDENTITY]),7)
  for k in (obs.BODY_IDENTITY,obs.ENDPOINT_IDENTITY):self.assertTrue(set(old['identity_denylists'][k])<=set(deny['identity_denylists'][k]))
  for row in deny['additions']:
   raw=Path(row['source_events']['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['source_events']['sha256']);events=[json.loads(x) for x in raw.decode().splitlines()];event=events[row['source_event_sequence']];self.assertEqual(obs.sha(obs.canonical(event).encode()),row['source_event_sha256']);self.assertEqual(event['request_sha256'],row[obs.BODY_IDENTITY]);self.assertEqual(event['endpoint_body_sha256'],row[obs.ENDPOINT_IDENTITY]);self.assertEqual(event['exception_type'],'URLError');self.assertIsNone(event['http_status'])
 def test_actual_recorded_hash_lookups_deny_both_serializations_without_forwarding(self):
  real_sha=obs.sha
  for n,row in enumerate(deny['additions']):
   body,requests=fixture(n);canonical_body=obs.canonical(body).encode();canonical_endpoint=json.dumps({'endpoint':ENDPOINT,'body':body},ensure_ascii=False,sort_keys=True).encode()
   for convention,preimage in ((obs.BODY_IDENTITY,canonical_body),(obs.ENDPOINT_IDENTITY,canonical_endpoint)):
    # Explicitly substituted SHA result; synthetic body, not claimed raw incident replay.
    def substituted(raw):return row[convention] if raw==preimage else real_sha(raw)
    for request in requests:
     events=[];forwarded=[]
     with patch.object(obs,'sha',side_effect=substituted),obs.observe(events.append,opener=lambda *a,**k:forwarded.append((a,k)),identity_denylists=deny['identity_denylists']):
      with self.assertRaisesRegex(ValueError,'request_identity_denied_no_dispatch'):urllib.request.urlopen(request,timeout=60)
     self.assertEqual(forwarded,[]);self.assertEqual(len(events),1);self.assertEqual(events[0]['stage'],'denied_before_transport')
 def test_unmodified_sha_semantic_serialization_invariance(self):
  for n in range(2):
   _,requests=fixture(n);left,right=map(obs.request_metadata,requests);self.assertNotEqual(left['wire_bytes_sha256'],right['wire_bytes_sha256']);self.assertEqual(left['request_sha256'],right['request_sha256']);self.assertEqual(left['endpoint_body_sha256'],right['endpoint_body_sha256'])
 def test_distinct_synthetic_request_forwards_exact_object_once(self):
  _,requests=fixture('distinct');request=requests[0];seen=[];events=[];response=Response()
  def opener(*a,**k):seen.append((a,k));return response
  with obs.observe(events.append,opener=opener,identity_denylists=deny['identity_denylists']):result=urllib.request.urlopen(request,timeout=17)
  self.assertIs(result.response,response);self.assertEqual(seen,[((request,),{'timeout':17})]);self.assertEqual(events[0]['stage'],'open')
 def test_generic_profile_reference_and_first8_wrappers_accept_superset_unchanged(self):
  sources=[('/private/tmp/gio_diagnostic_runtime_envelope_v2.py','8e3a2f460254c3295f36c0d07a323bb1ccdafafad4ac11425cd3963a09b8d2b5','/private/tmp/gio-diagnostic-envelope-proposal-v2/profile-envelope-TEMPLATE.json'),('/private/tmp/gio_diagnostic_runtime_envelope_v2.py','8e3a2f460254c3295f36c0d07a323bb1ccdafafad4ac11425cd3963a09b8d2b5','/private/tmp/gio-diagnostic-envelope-proposal-v2/reference-envelope-TEMPLATE.json'),('/private/tmp/gio_diagnostic_runtime_envelope_first8_v1.py','a4d654709439ec85c776e2281a352ab163d24edbe0e613762e5ad9baf3a8329e','/private/tmp/gio-first8-wrapper-proposal-v1/envelope-TEMPLATE.json')]
  for n,(path,sha,template) in enumerate(sources):
   self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),sha);w=load('compat_'+str(n),path);e=json.loads(Path(template).read_text());e['denylist']={'path':str(D),'sha256':DS};e['output_root']='/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/never-created-deny-superset-review-'+str(n);original=w.pinned
   if n==2:
    e['inputs']['lease']={'path':'/synthetic/not-issued-first8-lease','sha256':'synthetic'}
    def pinned(r):return {'protocol':'original-first8-v1','plan_sha256':e['inputs']['plan']['sha256']} if r==e['inputs']['lease'] else original(r)
    with patch.object(w,'pinned',side_effect=pinned):entry,args,blocked=w.validate(e,check_only=True)
   else:entry,args,blocked=w.validate(e,check_only=True)
   self.assertEqual(blocked,deny['identity_denylists'])
if __name__=='__main__':unittest.main()
