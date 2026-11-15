import copy, importlib.util, unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
MODULE=Path('/private/tmp/gio_p8_first4_supervisor_v1.py')
def module():
 if not MODULE.exists():return None
 s=importlib.util.spec_from_file_location('p8_supervisor_tests',MODULE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Tests(unittest.TestCase):
 def setUp(self):self.m=module();self.assertIsNotNone(self.m,'first4 supervisor not implemented')
 def data(self,status='invalid'):
  manifest={'job_id':'j','kind':'build','method_id':'P8','code_sha':'code','config_hash':'config','source_manifest_hash':'source','extractor':{'model':'gpt-6-sol'}}
  usage={'attempted_calls':1,'uncertain_attempts':0,'cache_hits':0,'reserved_api_usd':0,'reported_api_usd':.01,'budget_detail':{'reported_usage_complete':True,'reserved_usd':0,'unknown_input_usage_attempts':0,'unknown_output_usage_attempts':0}}
  packet={'manifest':manifest,'backend':{'max_calls':1}}
  receipt={'job_id':'j','manifest_sha256':self.m.h.digest(manifest),'status':status,'usage':usage}
  result={'job_id':'j','manifest_hash':self.m.h.digest(manifest),'status':status,'usage':copy.deepcopy(usage),'code_sha':'code','config_hash':'config','source_manifest_hash':'source','actual_backend':manifest['extractor'],'predictions':[],'counts':{'attempted':1,'complete':int(status=='complete'),'error':int(status!='complete')}}
  return packet,receipt,result
 def test_known_invalid_empty_and_complete_are_retained(self):
  for status in ('invalid','empty','complete','unavailable'):
   p,r,x=self.data(status);self.assertEqual(self.m.check_build_result(p,r,x)['status'],status)
 def test_unknown_usage_or_cache_replay_not_fresh(self):
  for key in ('uncertain_attempts','cache_hits'):
   p,r,x=self.data();r['usage'][key]=x['usage'][key]=1
   with self.assertRaises(ValueError):self.m.check_build_result(p,r,x)
 def test_no_attempt_or_duplicate_attempt_rejected(self):
  for n in (0,2):
   p,r,x=self.data();r['usage']['attempted_calls']=x['usage']['attempted_calls']=n
   with self.assertRaises(ValueError):self.m.check_build_result(p,r,x)
 def test_result_identity_or_status_mismatch_rejected(self):
  for key in ('manifest_hash','config_hash','source_manifest_hash','status'):
   p,r,x=self.data();x[key]='altered'
   with self.assertRaises(ValueError):self.m.check_build_result(p,r,x)
 def test_same80_budget_and_nonzero_baseline_preserved(self):
  state={'attempts':280,'known_nanos':1000000000,'known_usd':'1','held_usd':'0','pending':0,'uncertain':0}
  self.m.admission_gate(state,{'attempts':280,'spent':1000000000},datetime(2026,11,15,16,42,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):self.m.admission_gate(state,{'attempts':0,'spent':0},datetime(2026,11,15,16,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):self.m.admission_gate(state,{'attempts':280,'spent':1000000000},datetime(2026,11,15,16,42,1,tzinfo=timezone.utc))
 def test_nonzero_never_verifies_or_retries(self):
  calls=[]
  status=self.m.run_one(lambda:calls.append('launch') or 2,lambda:calls.append('verify'))
  self.assertEqual(status,(None,'child_nonzero'));self.assertEqual(calls,['launch'])
 def test_unknown_terminal_never_retries(self):
  calls=[]
  def verify():calls.append('verify');raise ValueError('unknown')
  status=self.m.run_one(lambda:calls.append('launch') or 0,verify)
  self.assertEqual(status,(None,'terminal_verification_failed'));self.assertEqual(calls,['launch','verify'])
if __name__=='__main__':unittest.main()
