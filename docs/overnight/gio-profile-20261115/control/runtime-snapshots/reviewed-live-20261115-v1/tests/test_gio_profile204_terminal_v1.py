import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sp=importlib.util.spec_from_file_location('s','/private/tmp/gio_profile204_supervisor_v1.py');s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def put(self,path,data):
  p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return s.ref(p)
 def usage(self,calls):return {'attempted_calls':calls,'uncertain_attempts':0,'cache_hits':0,'reserved_api_usd':0,'reported_api_usd':calls*.000000125,'budget_detail':{'reported_usage_complete':True,'reserved_usd':0,'unknown_input_usage_attempts':0,'unknown_output_usage_attempts':0}}
 def native(self,n,calls=0):
  jobs=[]
  for i in range(n):
   jid='synthetic-'+str(i);m={'kind':'build' if not calls else 'predict','job_id':jid};p={'manifest':m,'backend':{'max_calls':calls}};jobs.append(self.put('packets/'+jid+'.json',p));u=self.usage(calls)
   result={'job_id':jid,'manifest_hash':s.digest(m),'status':'complete','usage':u};result_ref=self.put('output/'+jid+'/result.json',result)
   self.put('receipts/batch/execution/'+jid+'/receipt.json',{'schema_version':'overnight-dispatch-receipt-v1','job_id':jid,'manifest_sha256':s.digest(m),'status':'complete','usage':u,'result_path':result_ref['path']})
  batch=self.put('prepared.json',{'batch_id':'batch','jobs':jobs})
  self.put('receipts/batch/execution/summary.json',{'schema_version':'overnight-batch-result-v1','batch_id':'batch','status':'complete','stop_reason':None,'counts':{'listed':n,'dispatched':n,'complete':n,'not_dispatched':0,'other':0},'ledger':{'uncertain':0,'inflight':0,'held_after_uncertain':False,'reserved_usd':0,'max_inflight':2,'max_usd':199.34296134,'attempts':n*calls,'spent_usd':n*calls*.000000125}})
  return batch
 def diagnostic(self):
  env={'script_sha256':s.WRAPPER['sha256'],'observer':s.OBSERVER,'state':'authorized','kind':'profile','output_root':str(self.root/'diagnostic')};envref=self.put('envelope.json',env);identity={'canonical_envelope_sha256':s.digest(env),'wrapper_script_sha256':s.WRAPPER['sha256']}
  self.put('diagnostic/ENVELOPE_CLAIM.json',dict(identity,envelope=env))
  event={'sequence':0,'schema_version':'provider-boundary-diagnostics-v3','stage':'open','exception_type':None,'http_status':200,'request_sha256':'a','endpoint_body_sha256':'b'}
  ep=self.root/'diagnostic/events.jsonl';ep.write_text(json.dumps(event)+'\n')
  terminal=dict(identity,status='complete',entry_exit_code=0,wrapper_exit_code=0,observer_sha256=s.OBSERVER['sha256'],diagnostics={'diagnostic_write_failed':False,'diagnostic_close_failed':False,'dropped_event_count':0},events_sha256=s.ref(ep)['sha256'],event_count=1)
  tr=self.put('diagnostic/envelope-terminal.json',terminal);return envref,tr
 def test_exact112_zero_native_gate(self):
  batch=self.native(112)
  with patch.object(s,'B',self.root):r=s.native_terminal(batch,112,0,zero=True)
  self.assertEqual(r['attempted_calls'],0);self.assertEqual(len(r['receipts']),112)
 def test_zero_paid_call_refused(self):
  batch=self.native(112,1)
  with patch.object(s,'B',self.root),self.assertRaises(ValueError):s.native_terminal(batch,112,0,zero=True)
 def test_native_result_identity_tampering_refused(self):
  batch=self.native(1,1);p=self.root/'output/synthetic-0/result.json';r=json.loads(p.read_text());r['manifest_hash']='changed';p.write_text(json.dumps(r))
  with patch.object(s,'B',self.root),self.assertRaises(ValueError):s.native_terminal(batch,1,1)
 def test_known_native_prediction_terminal(self):
  batch=self.native(1,1)
  with patch.object(s,'B',self.root):r=s.native_terminal(batch,1,1)
  self.assertEqual(r['attempted_calls'],1);self.assertEqual(r['known_spent_nanos'],125)
 def test_bound_diagnostic_success_then_event_tampering(self):
  er,tr=self.diagnostic();s.diagnostic_terminal(er,tr,{'a':'b'},1)
  ep=self.root/'diagnostic/events.jsonl';ep.write_text(ep.read_text()+'\n')
  with self.assertRaises(ValueError):s.diagnostic_terminal(er,tr,{'a':'b'},1)
 def test_diagnostic_failure_and_wrong_envelope_rejected(self):
  er,tr=self.diagnostic();t=s.read(tr);t['diagnostics']['diagnostic_write_failed']=True;tr=self.put('diagnostic/envelope-terminal.json',t)
  with self.assertRaises(ValueError):s.diagnostic_terminal(er,tr,{'a':'b'},1)
  t['diagnostics']['diagnostic_write_failed']=False;t['canonical_envelope_sha256']='bad';tr=self.put('diagnostic/envelope-terminal.json',t)
  with self.assertRaises(ValueError):s.diagnostic_terminal(er,tr,{'a':'b'},1)
if __name__=='__main__':unittest.main()
