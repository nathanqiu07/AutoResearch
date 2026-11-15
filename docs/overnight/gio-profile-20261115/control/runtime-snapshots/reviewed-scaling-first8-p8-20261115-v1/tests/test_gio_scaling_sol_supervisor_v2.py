import importlib.util,unittest
from datetime import datetime,timezone,timedelta
s=importlib.util.spec_from_file_location('supervisor','/private/tmp/gio_scaling_sol_supervisor_v2.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def stages(self):return [{'block':'core','request':'different'},{'block':'lexical','request':'shared'},{'block':'semantic','request':'shared'}]
 def test_same_input_repeat_follows_known_first(self):
  events=[]
  def admit(s):
   if s['block']=='semantic':self.assertIn(('known','lexical'),events)
   events.append(('admit',s['block']))
  done,reason=m.run_sequence(self.stages(),lambda s:events.append(('call',s['block'])) or 0,lambda s:events.append(('known',s['block'])) or s,admit)
  self.assertIsNone(reason);self.assertEqual(len(done),3);self.assertEqual(events.index(('known','lexical'))+1,events.index(('admit','semantic')))
 def test_unknown_lexical_never_admits_same_input_semantic(self):
  calls=[];admissions=[]
  def verify(s):
   if s['block']=='lexical':raise ValueError('unknown_usage')
   return s
  done,reason=m.run_sequence(self.stages(),lambda s:calls.append(s['block']) or 0,verify,lambda s:admissions.append(s['block']))
  self.assertEqual(reason,'terminal_verification_failed');self.assertEqual(calls,['core','lexical']);self.assertEqual(admissions,calls);self.assertEqual(len(done),1)
 def test_nonzero_and_missing_diagnostics_fail_stop(self):
  for failure in ('nonzero','diagnostics'):
   calls=[]
   def verify(s):raise FileNotFoundError('missing_diagnostics')
   done,reason=m.run_sequence(self.stages(),lambda s:calls.append(s['block']) or (2 if failure=='nonzero' else 0),verify,lambda s:None)
   self.assertEqual(calls,['core']);self.assertEqual(done,[]);self.assertIsNotNone(reason)
 def state(self):return {'pending':0,'uncertain':0,'attempts':10,'known_nanos':1000000000,'known_usd':'1','held_usd':'0'}
 def test_80_actual_plus_full_holds(self):
  now=datetime(2026,11,15,13,tzinfo=timezone.utc);st=self.state();st['held_usd']='2'
  m.admission_gate(st,{'attempts':10,'spent':1000000000},'77',6060,now)
  with self.assertRaises(ValueError):m.admission_gate(st,{'attempts':10,'spent':1000000000},'77.000000001',6060,now)
 def test_new_unexpected_attempt_or_deadline_blocks_admission(self):
  for change in ('attempt','deadline','unknown'):
   st=self.state();now=datetime(2026,11,15,15,9,tzinfo=timezone.utc)
   if change=='attempt':st['attempts']+=1
   if change=='deadline':now+=timedelta(seconds=1)
   if change=='unknown':st['uncertain']=1
   with self.assertRaises(ValueError):m.admission_gate(st,{'attempts':10,'spent':1000000000},1,6060,now)
 def test_invalid_first_complete_accounting_blocks_semantic(self):
  expected={'job_id':'j','manifest_sha256':'m','item_id':'i','item_sha256':'s'}
  row={'status':'complete','prediction':{'choice':0},**expected};result={'job_id':'j','manifest_hash':'m','status':'complete','counts':{'attempted':1,'complete':1,'error':0},'predictions':[row]}
  m.require_repeat_success(result,expected)
  for status in ('invalid','abstained','unavailable'):
   row['status']=status;result['status']='partial';result['counts']={'attempted':1,'complete':0,'error':1};calls=[]
   def admit(s):
    if s['block']=='semantic':m.require_repeat_success(result,expected)
   with self.assertRaises(ValueError):m.run_sequence(self.stages(),lambda s:calls.append(s['block']) or 0,lambda s:s,admit)
   self.assertEqual(calls,['core','lexical'])
 def test_diagnostic_denial_rejected(self):
  event={'sequence':0,'schema_version':'provider-boundary-diagnostics-v3','stage':'denied','exception_type':'ProviderRequestDenied','http_status':None,'request_sha256':'x','endpoint_body_sha256':'y'}
  with self.assertRaises(ValueError):m.g.validate_events([event],{'x':'y'},1)
if __name__=='__main__':unittest.main()
