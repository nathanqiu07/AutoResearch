import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('primary14_guards_helper','/private/tmp/gio_prepare_primary14_v1.py');s=load('primary14_guards_supervisor','/private/tmp/gio_primary14_supervisor_v1.py')
class Guards(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='gio-primary14-offline-guards-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.auth=h.read(h.ref('/private/tmp/gio-primary14-offline-proposal-v1/authority-TEMPLATE.json'));self.auth.update(state='authorized',authority='Synthetic offline test authority; no execution')
  snap=h.read(h.read(h.PREDECESSOR)['closed_ledger_snapshot']);self.state={'policy_rows':snap['policy_rows'],'reservation_rows':snap['reservation_rows'],'attempts':284,'known_nanos':3260300000,'known_usd':'3.26030','held_usd':'0','pending':0,'uncertain':0}
  self.policy=h.read(h.POLICY);self.base={'attempts':284,'spent':3260300000}
 def authref(self,value):
  p=self.root/('auth-%d.json'%len(list(self.root.iterdir())));return h.write(p,value)
 def validate(self,auth,initial=True,state=None):
  with patch.object(h.p,'validate_authority',return_value=({},self.policy,state or self.state,{},{})),patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('unexpected SQL')):
   return h.validate_authority(self.authref(auth),initial=initial)
 def test_exact_closed_baseline_and_known_prior_outcomes(self):
  self.assertEqual(self.validate(self.auth)[4],self.base)
 def test_authority_missingness_guard_policy_or_deadline_change_rejected(self):
  for key,value in [('state','proposal'),('authority',None),('unknown_denylist',{}),('predecessor',{}),('runtime_commit','f'*40),('deadline','2026-11-15T18:00:00Z'),('max_calls',15),('max_usd','2'),('max_inflight',3),('planned_descendant_slots',14),('unavailable_descendant_slots',0),('historical_unknown_holds_released',True)]:
   with self.subTest(key=key),self.assertRaises(ValueError):self.validate(dict(self.auth,**{key:value}))
 def test_old_rows_cannot_disappear_or_change(self):
  state=copy.deepcopy(self.state);state['reservation_rows'].pop()
  with self.assertRaisesRegex(ValueError,'reservations_changed'):self.validate(self.auth,state=state)
 def test_fresh_admission_rejects_new_activity_but_terminal_preserves_original_baseline(self):
  state=copy.deepcopy(self.state);state['reservation_rows'].append(['synthetic-new',1,1,'complete','{}']);state['attempts']+=1;state['known_nanos']+=1;state['known_usd']='3.260300001'
  with self.assertRaisesRegex(ValueError,'new_attempts'):self.validate(self.auth,state=state)
  self.assertEqual(self.validate(self.auth,initial=False,state=state)[4],self.base)
 def test_terminal_requires_full14_fresh_known_and_exact_cumulative_counts(self):
  native={'attempted_calls':14,'known_spent_nanos':100,'ledger_attempts':298,'ledger_spent_nanos':3260300100,'receipts':[{'receipt':{'path':'/fake/receipt','sha256':'a'*64}}]};actual={'attempts':298,'known_nanos':3260300100}
  def run(value,cache=0,diagnostic_error=False):
   with patch.object(s.g,'native_terminal',return_value=value),patch.object(s,'read',return_value={'usage':{'cache_hits':cache}}),patch.object(s,'ref',return_value={'path':'/fake/terminal','sha256':'b'*64}),patch.object(s.g,'diagnostic_terminal',side_effect=ValueError('diagnostic_failed') if diagnostic_error else None,return_value={'verified':True}),patch.object(s.h,'validate_authority',return_value=({}, {},actual,{},self.base)):
    return s.verify_completed({'prepared':{},'authority':{}},self.base,{}, {},{'output_root':'/fake'})
  self.assertEqual(run(native)['baseline'],self.base)
  for key,value in [('attempted_calls',13),('ledger_attempts',299),('ledger_spent_nanos',3260300101)]:
   with self.subTest(key=key),self.assertRaises(ValueError):run(dict(native,**{key:value}))
  with self.assertRaises(ValueError):run(native,cache=1)
  with self.assertRaises(ValueError):run(native,diagnostic_error=True)
if __name__=='__main__':unittest.main()
