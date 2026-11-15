import importlib.util,io,json,unittest,urllib.error,urllib.request
sp=importlib.util.spec_from_file_location('d','/private/tmp/gio_provider_diagnostics_v3.py');d=importlib.util.module_from_spec(sp);sp.loader.exec_module(d)
class Response:
 status=200
 headers={'x-request-id':'req_safe-123'}
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self,*args,**kwargs):return b'{"safe":"response text must never be logged"}'
class Tests(unittest.TestCase):
 def request(self):return urllib.request.Request('https://api.openai.com/v1/responses',data=b'{"input":"PRIVATE PROMPT","model":"gpt-6-luna"}',headers={'Authorization':'Bearer SECRET'},method='POST')
 def test_exact_transport_and_payload_passthrough(self):
  req=self.request();events=[];seen=[]
  def opener(*a,**k):seen.append((a,k));return Response()
  with d.observe(events.append,opener=opener):
   with urllib.request.urlopen(req,timeout=180) as r:self.assertEqual(r.read(),Response().read())
  self.assertIs(seen[0][0][0],req);self.assertEqual(seen[0][1],{'timeout':180});self.assertEqual(events[-1]['http_status'],200);self.assertEqual(events[-1]['provider_request_id_sha256'],d.sha(b'req_safe-123'))
  text=json.dumps(events);self.assertNotIn('PRIVATE PROMPT',text);self.assertNotIn('SECRET',text);self.assertNotIn('response text',text)
 def test_http_failure_class_status_and_safe_id_without_body(self):
  events=[];err=urllib.error.HTTPError('https://secret','429','SECRET MESSAGE',{'x-request-id':'req_ok'},io.BytesIO(b'SECRET BODY'));err.code=429
  def opener(*a,**k):raise err
  with self.assertRaises(urllib.error.HTTPError):
   with d.observe(events.append,opener=opener):urllib.request.urlopen(self.request(),timeout=180)
  self.assertEqual(events[-1]['exception_type'],'HTTPError');self.assertEqual(events[-1]['http_status'],429);self.assertNotIn('SECRET',json.dumps(events))
 def test_unsafe_request_id_dropped(self):self.assertIsNone(d.safe_request_id({'x-request-id':'secret\nheader'}))
 def test_read_failure_recorded_and_rethrown(self):
  class Bad(Response):
   def read(self,*a,**k):raise TimeoutError('SECRET')
  events=[]
  with self.assertRaises(TimeoutError):
   with d.observe(events.append,opener=lambda *a,**k:Bad()):
    with urllib.request.urlopen(self.request(),timeout=12) as r:r.read()
  self.assertEqual(events[-1]['exception_type'],'TimeoutError');self.assertEqual(events[-1]['stage'],'read');self.assertNotIn('SECRET',json.dumps(events))
 def test_unknown_request_denied_before_transport(self):
  req=self.request();events=[];calls=[];key=d.request_metadata(req)['request_sha256']
  with self.assertRaises(ValueError):
   with d.observe(events.append,opener=lambda *a,**k:calls.append(1),denylist={key}):urllib.request.urlopen(req,timeout=180)
  self.assertEqual(calls,[]);self.assertEqual(events[-1]['stage'],'denied_before_transport')
 def test_original_opener_restored_after_error(self):
  original=urllib.request.urlopen
  with self.assertRaises(RuntimeError):
   with d.observe(lambda event:None):raise RuntimeError()
  self.assertIs(urllib.request.urlopen,original)
 def test_header_canary_is_only_hashed(self):
  class Canary(Response):headers={'x-request-id':'SYNTHETIC_CREDENTIAL_CANARY'}
  events=[]
  with d.observe(events.append,opener=lambda *a,**k:Canary()):
   with urllib.request.urlopen(self.request()) as r:r.read()
  self.assertNotIn('SYNTHETIC_CREDENTIAL_CANARY',json.dumps(events));self.assertEqual(events[-1]['provider_request_id_sha256'],d.sha(b'SYNTHETIC_CREDENTIAL_CANARY'))
 def test_sink_failure_preserves_successful_read_and_close_then_blocks_next(self):
  history=[]
  class Tracked(Response):
   def __enter__(self):history.append('enter');return self
   def read(self,*a,**k):history.append('read');return b'ok'
   def __exit__(self,*a):history.append('close');return False
  def sink(event):raise OSError('SECRET')
  with d.observe(sink,opener=lambda *a,**k:Tracked()) as state:
   with urllib.request.urlopen(self.request()) as r:self.assertEqual(r.read(),b'ok')
   self.assertTrue(state.diagnostic_write_failed)
   with self.assertRaises(d.DiagnosticWriteFailure):urllib.request.urlopen(self.request())
  self.assertEqual(history,['enter','read','close']);self.assertEqual(state.dropped_event_count,1)
 def test_sink_failure_preserves_original_http_exception_identity(self):
  original=urllib.error.HTTPError('u',503,'SECRET',{},None)
  def opener(*a,**k):raise original
  def sink(event):raise OSError('write error')
  with d.observe(sink,opener=opener) as state:
   with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(self.request())
  self.assertIs(caught.exception,original);self.assertTrue(state.diagnostic_write_failed)
 def test_sink_failure_preserves_original_read_exception_and_close(self):
  original=TimeoutError('SECRET');closed=[];count=[]
  class Bad(Response):
   def read(self,*a,**k):raise original
   def __exit__(self,*a):closed.append(1);return False
  def sink(event):
   count.append(1)
   if len(count)>1:raise OSError('write error')
  with d.observe(sink,opener=lambda *a,**k:Bad()) as state:
   with self.assertRaises(TimeoutError) as caught:
    with urllib.request.urlopen(self.request()) as r:r.read()
  self.assertIs(caught.exception,original);self.assertEqual(closed,[1]);self.assertTrue(state.diagnostic_write_failed)
 def test_distinct_reference_convention_and_block_before_transport(self):
  req=self.request();events=[];calls=[]
  expected=d.sha(json.dumps({'endpoint':req.full_url,'body':json.loads(req.data)},ensure_ascii=False,sort_keys=True).encode('utf-8'))
  meta=d.request_metadata(req)
  self.assertEqual(meta['endpoint_body_sha256'],expected);self.assertNotEqual(meta['request_sha256'],expected)
  with self.assertRaises(ValueError):
   with d.observe(events.append,opener=lambda *a,**k:calls.append(1),identity_denylists={d.ENDPOINT_IDENTITY:[expected]}):urllib.request.urlopen(req,timeout=60)
  self.assertEqual(calls,[]);self.assertEqual(events[-1]['stage'],'denied_before_transport');self.assertNotIn(req.full_url,json.dumps(events))
 def test_named_body_convention_denies_before_transport(self):
  req=self.request();calls=[];key=d.request_metadata(req)['request_sha256']
  with self.assertRaises(ValueError):
   with d.observe(lambda e:None,opener=lambda *a,**k:calls.append(1),identity_denylists={d.BODY_IDENTITY:[key]}):urllib.request.urlopen(req)
  self.assertEqual(calls,[])
 def test_unicode_and_default_separators_exact(self):
  req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps({'b':'é','a':{'z':1}},ensure_ascii=False).encode())
  expected=d.sha(json.dumps({'endpoint':req.full_url,'body':json.loads(req.data)},ensure_ascii=False,sort_keys=True).encode())
  wrong=d.sha(d.canonical({'endpoint':req.full_url,'body':json.loads(req.data)}).encode())
  self.assertEqual(d.request_metadata(req)['endpoint_body_sha256'],expected);self.assertNotEqual(expected,wrong)
 def test_unknown_identity_convention_rejected(self):
  with self.assertRaises(ValueError):
   with d.observe(lambda e:None,identity_denylists={'made_up_hash':[]}):pass
if __name__=='__main__':unittest.main()
