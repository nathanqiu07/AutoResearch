import importlib.util,json,unittest
sp=importlib.util.spec_from_file_location('s','/private/tmp/gio_profile204_supervisor_v1.py');s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)
class Tests(unittest.TestCase):
 def test_order_is_exact_and_finite(self):self.assertEqual([x[1:] for x in s.ORDER],[(25,350),(5,70),(90,168),(84,84)]);self.assertEqual(sum(x[2] for x in s.ORDER),672)
 def test_known_usage_only(self):
  u={'attempted_calls':1,'uncertain_attempts':0,'reserved_api_usd':0,'budget_detail':{'reported_usage_complete':True,'reserved_usd':0,'unknown_input_usage_attempts':0,'unknown_output_usage_attempts':0}}
  self.assertEqual(s.known_usage(u,2),1)
  for key,val in [('uncertain_attempts',1),('reserved_api_usd',.001),('attempted_calls',3)]:
   bad=dict(u);bad[key]=val
   with self.assertRaises(ValueError):s.known_usage(bad,2)
  bad=dict(u,budget_detail=dict(u['budget_detail'],reported_usage_complete=False))
  with self.assertRaises(ValueError):s.known_usage(bad,2)
 def event(self):return {'sequence':0,'schema_version':'provider-boundary-diagnostics-v3','stage':'open','exception_type':None,'http_status':200,'request_sha256':'a','endpoint_body_sha256':'b'}
 def test_actual_events_bind_both_hashes_and_no_duplicate(self):
  e=self.event();s.validate_events([e],{'a':'b'},1)
  for bad in [dict(e,stage='denied_before_transport'),dict(e,endpoint_body_sha256='x'),dict(e,http_status=503),dict(e,exception_type='HTTPError')]:
   with self.assertRaises(ValueError):s.validate_events([bad],{'a':'b'},1)
  with self.assertRaises(ValueError):s.validate_events([e,dict(e,sequence=1)],{'a':'b'},2)
  with self.assertRaises(ValueError):s.validate_events([],{'a':'b'},1)
 def test_finite_loop_stops_before_next_on_unknown_nonzero_or_missing_diagnostics(self):
  for fail_at in range(4):
   called=[]
   def run(stage):called.append(stage);return 0
   def check(stage):
    if stage==fail_at:raise ValueError('unknown_or_missing_diagnostics')
   done,reason=s.run_sequence(list(range(4)),run,check)
   self.assertEqual(called,list(range(fail_at+1)));self.assertEqual(len(done),fail_at);self.assertEqual(reason,'terminal_verification_failed')
  called=[]
  done,reason=s.run_sequence(list(range(4)),lambda i:called.append(i) or 2,lambda i:None)
  self.assertEqual(called,[0]);self.assertEqual(reason,'child_nonzero');self.assertEqual(done,[])
 def test_all_four_known_admitted_once(self):
  called=[];checked=[]
  done,reason=s.run_sequence(list(range(4)),lambda i:called.append(i) or 0,lambda i:checked.append(i) or {'ok':True})
  self.assertEqual(called,list(range(4)));self.assertEqual(checked,list(range(4)));self.assertIsNone(reason);self.assertEqual(len(done),4)
 def test_predecessor_failure_prevents_first_admission(self):
  called=[]
  with self.assertRaises(ValueError):s.run_sequence([0],lambda i:called.append(i),lambda i:None,admit=lambda i:(_ for _ in ()).throw(ValueError('bad_predecessor')))
  self.assertEqual(called,[])
if __name__=='__main__':unittest.main()
