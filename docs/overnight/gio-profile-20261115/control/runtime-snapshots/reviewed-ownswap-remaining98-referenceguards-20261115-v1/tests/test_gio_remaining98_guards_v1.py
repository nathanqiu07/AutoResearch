import copy,importlib.util,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('remaining98_guard_helper','/private/tmp/gio_prepare_remaining98_v1.py');s=load('remaining98_guard_supervisor','/private/tmp/gio_remaining98_supervisor_v1.py')
class Guards(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='gio-remaining98-offline-guards-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.n=0;self.auth=h.read(h.ref('/private/tmp/gio-remaining98-offline-proposal-v1/authority-TEMPLATE.json'));self.auth.update(state='authorized',authority='Synthetic offline test; no execution');snap=h.read(h.read(h.PREDECESSOR)['closed_ledger_snapshot']);self.base={'attempts':306,'spent':3883810000};self.current={'policy_rows':snap['policy_rows'],'reservation_rows':snap['reservation_rows'],'attempts':306,'known_nanos':3883810000,'known_usd':'3.883810','held_usd':'0','pending':0,'uncertain':0};self.policy=h.read(h.POLICY)
 def put(self,v):self.n+=1;return h.write(self.root/('%d.json'%self.n),v)
 def validate(self,current,*,initial=False,auth=None):
  with patch.object(h,'ownswap_gate',return_value={'immutable_known28':True}),patch.object(h.h,'validate_authority',return_value=(self.policy,current,{})),patch('sqlite3.connect',side_effect=AssertionError('SQL forbidden')):return h.validate_authority(self.put(auth or self.auth),initial=initial)
 def test306_initial_and_authorized56growth_preserve_baseline(self):
  self.assertEqual(self.validate(self.current,initial=True)[4],self.base);c=copy.deepcopy(self.current);c['reservation_rows']+= [['synthetic-p7-%d'%n,1,1,'complete','{}'] for n in range(56)];c.update(attempts=362,known_nanos=3883810056,known_usd='3.883810056');self.assertEqual(self.validate(c)[4],self.base);s.admission_gate(c,self.base,datetime(2026,11,15,15,tzinfo=timezone.utc),expected_attempts=362,expected_spent=3883810056,remaining_blocks=1)
  with self.assertRaises(ValueError):self.validate(c,initial=True)
  with self.assertRaises(ValueError):s.admission_gate(dict(c,attempts=363),self.base,datetime(2026,11,15,15,tzinfo=timezone.utc),expected_attempts=362,expected_spent=3883810056,remaining_blocks=1)
 def test_mutated_original306row_rejected_even_after_authorized_growth(self):
  c=copy.deepcopy(self.current);c['reservation_rows'][0][2]+=1
  with self.assertRaises(ValueError):self.validate(c)
  c=copy.deepcopy(self.current);c['reservation_rows'].pop()
  with self.assertRaises(ValueError):self.validate(c)
 def test_authority_gates_denominator_deadline_and_ownswap_identity(self):
  for key,value in [('state','proposal'),('max_calls',99),('max_usd','27'),('max_inflight',3),('planned_descendant_slots',98),('unavailable_descendant_slots',0),('deadline','2026-11-15T18:00:00Z'),('ownswap_completed_gate',{}),('unknown_denylist',{}),('historical_unknown_holds_released',True)]:
   with self.subTest(key=key),self.assertRaises(ValueError):self.validate(self.current,auth=dict(self.auth,**{key:value}))
 def test_exact_dedicated28_snapshot_cannot_grow_or_have_holds(self):
  gate=h.read(h.OWN_GATE);snap=h.read(gate['closed_ledger_snapshot']);c={'policy_rows':snap['policy_rows'],'reservation_rows':snap['reservation_rows'],'attempts':28,'known_nanos':5598000,'pending':0,'uncertain':0,'held_nanos':0}
  with patch.object(h.h,'ledger_read',return_value=c):self.assertEqual(h.ownswap_gate(h.OWN_GATE)['known_spent_nanos'],5598000)
  for key,value in [('attempts',29),('uncertain',1),('pending',1),('held_nanos',1),('known_nanos',5598001)]:
   with self.subTest(key=key),patch.object(h.h,'ledger_read',return_value=dict(c,**{key:value})),self.assertRaises(ValueError):h.ownswap_gate(h.OWN_GATE)
 def test_full_timefit_and80_headroom_rechecked(self):
  s.admission_gate(self.current,self.base,datetime(2026,11,15,15,50,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):s.admission_gate(self.current,self.base,datetime(2026,11,15,15,50,1,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):s.admission_gate(dict(self.current,known_usd='54'),self.base,datetime(2026,11,15,15,tzinfo=timezone.utc))
if __name__=='__main__':unittest.main()
