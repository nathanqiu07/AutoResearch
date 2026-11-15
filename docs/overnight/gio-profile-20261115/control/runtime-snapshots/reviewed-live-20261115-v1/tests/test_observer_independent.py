"""Independent offline observer adversarial checks; synthetic values only."""
import hashlib,importlib.util,json,sys,unittest,urllib.error,urllib.request
from pathlib import Path
observer=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else Path('/private/tmp/gio_provider_diagnostics_v1.py')
s=importlib.util.spec_from_file_location('independent_observer',observer);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
class Response:
 status=200
 headers={'x-request-id':'SYNTHETIC_CREDENTIAL_CANARY'}
 def __init__(self,seen):self.seen=seen
 def __enter__(self):self.seen.append('enter');return self
 def __exit__(self,*args):self.seen.append(('exit',args[0]));return False
 def read(self,*args,**kwargs):self.seen.append(('read',args,kwargs));return b'SYNTHETIC_RESPONSE_CANARY'
class Checks(unittest.TestCase):
 def request(self):return urllib.request.Request('https://example.invalid/v1/responses',data=b'{"input":"SYNTHETIC_SOURCE_CANARY","model":"gpt-6-luna"}',headers={'Authorization':'Bearer SYNTHETIC_CREDENTIAL_CANARY'},method='POST')
 def fail_sink(self,event):raise OSError('SYNTHETIC_LOCAL_WRITE_ERROR')
 def test_header_response_source_credential_not_logged(self):
  events=[]
  with d.observe(events.append,opener=lambda *a,**k:Response([])):
   with urllib.request.urlopen(self.request(),timeout=180) as response:response.read(8000001)
  serialized=json.dumps(events)
  for canary in ('SYNTHETIC_CREDENTIAL_CANARY','SYNTHETIC_SOURCE_CANARY','SYNTHETIC_RESPONSE_CANARY'):self.assertNotIn(canary,serialized)
 def test_sink_failure_preserves_original_open_exception(self):
  original=urllib.error.HTTPError('https://example.invalid',503,'SYNTHETIC_ERROR_BODY_CANARY',{},None)
  def opener(*a,**k):raise original
  caught=None
  try:
   with d.observe(self.fail_sink,opener=opener):urllib.request.urlopen(self.request(),timeout=180)
  except BaseException as exc:caught=exc
  self.assertIs(caught,original)
 def test_sink_failure_does_not_skip_read_or_close(self):
  seen=[];req=self.request();calls=[]
  def opener(*a,**k):calls.append((a,k));return Response(seen)
  with d.observe(self.fail_sink,opener=opener):
   with urllib.request.urlopen(req,timeout=180) as response:self.assertEqual(response.read(8000001),b'SYNTHETIC_RESPONSE_CANARY')
  self.assertIs(calls[0][0][0],req);self.assertEqual(calls[0][1],{'timeout':180})
  self.assertEqual(seen,['enter',('read',(8000001,),{}),('exit',None)])
 def test_sink_failure_preserves_original_read_exception(self):
  original=TimeoutError('SYNTHETIC_ERROR_BODY_CANARY');seen=[]
  class Bad(Response):
   def read(self,*a,**k):raise original
  caught=None
  try:
   with d.observe(self.fail_sink,opener=lambda *a,**k:Bad(seen)):
    with urllib.request.urlopen(self.request(),timeout=180) as response:response.read(8000001)
  except BaseException as exc:caught=exc
  self.assertIs(caught,original);self.assertEqual(seen,['enter',('exit',TimeoutError)])
 def test_wire_metadata_canonical_identity_and_restoration(self):
  events=[];req=self.request();original=urllib.request.urlopen
  with d.observe(events.append,opener=lambda *a,**k:Response([])):
   with urllib.request.urlopen(req,timeout=180) as response:response.read(8000001)
  self.assertIs(urllib.request.urlopen,original)
  self.assertEqual(events[0]['wire_bytes_sha256'],hashlib.sha256(req.data).hexdigest())
  self.assertEqual(events[0]['request_sha256'],hashlib.sha256(d.canonical(json.loads(req.data)).encode()).hexdigest())
if __name__=='__main__':unittest.main()
