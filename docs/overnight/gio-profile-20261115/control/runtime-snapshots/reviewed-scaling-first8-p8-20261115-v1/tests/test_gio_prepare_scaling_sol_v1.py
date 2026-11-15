import copy,importlib.util,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
s=importlib.util.spec_from_file_location('prepare','/private/tmp/gio_prepare_scaling_sol_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def draft(self):return {'lease':None,'manifest':{'kind':'predict','allocation':{'authorization_source':None},'scientific':['unchanged']},'backend':{'model':'gpt-6-sol'},'items':[{'context':'unicode🧪','options':['x','y']}]}
 def test_bind_only_authority_and_identity(self):
  d=self.draft();before=copy.deepcopy(d);p=m.bind(d,{'path':'p','sha256':'p'},{'path':'q','sha256':'q'});self.assertEqual(d,before);self.assertEqual(p['manifest']['job_id'],m.semantic_id(p['manifest']));p['lease']=None;p['manifest'].pop('job_id');p['manifest']['allocation']['authorization_source']=None;self.assertEqual(p,d)
 def test_reject_rebinding_or_other_model(self):
  for field in ['lease','model']:
   d=self.draft()
   if field=='lease':d['lease']={}
   else:d['backend']['model']='gpt-6-astra'
   with self.assertRaises(ValueError):m.bind(d,{}, {})
 def test_exact80_and_full_holds(self):
  st={'pending':0,'uncertain':0,'known_usd':'10','held_usd':'1'};m.budget_gate(st,'69')
  with self.assertRaises(ValueError):m.budget_gate(st,'69.000000001')
 def test_unknown_pending_fail_closed(self):
  for f in ['pending','uncertain']:
   st={'pending':0,'uncertain':0,'known_usd':'0','held_usd':'0'};st[f]=1
   with self.assertRaises(ValueError):m.budget_gate(st,0)
 def test_schedule_and_margin(self):
  exact=datetime(2026,11,15,15,9,tzinfo=timezone.utc);m.time_gate(exact,6060)
  with self.assertRaises(ValueError):m.time_gate(exact+timedelta(seconds=1),6060)
  with self.assertRaises(ValueError):m.time_gate(exact.replace(tzinfo=None),6060)
 def test_authority_before_connection(self):
  with patch.object(m,'read',return_value={'state':'prepared'}),patch.object(m,'ledger_read') as rd:
   with self.assertRaises(ValueError):m.validate_authority({}, {})
   rd.assert_not_called()
if __name__=='__main__':unittest.main()
