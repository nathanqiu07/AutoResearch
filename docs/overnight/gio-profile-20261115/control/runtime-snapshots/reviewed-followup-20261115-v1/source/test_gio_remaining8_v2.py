import copy,importlib.util,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
H=Path('/private/tmp/gio_prepare_remaining8_v2.py');S=Path('/private/tmp/gio_remaining8_supervisor_v2.py')
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Remaining8(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.h=load('remaining8_tests_helper',H) if H.exists() else None;cls.s=load('remaining8_tests_supervisor',S) if S.exists() else None
 def test_exact_eight_original_builds_capture_no_network_ledger(self):
  self.assertIsNotNone(self.h,'remaining8 helper missing')
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('ledger')):rows=self.h.capture_rows()
  self.assertEqual([r['draft_number'] for r in rows],[10,11,13,14,16,17,19,20]);self.assertEqual(len({r['request']['request_sha256'] for r in rows}),8)
  self.assertTrue(all(r['historical_luna_mapping_status']=='unavailable_rep0' for r in rows[-2:]))
 def test_bind_only_exact_original_packet_preserves_science(self):
  self.assertIsNotNone(self.h,'remaining8 helper missing');h=self.h
  for row in h.read(h.INVENTORY)['drafts']:
   d=h.read(row['packet']);saved=copy.deepcopy(d);p=h.bind(d,{'path':'/synthetic/auth','sha256':'a'*64});self.assertEqual(d,saved)
   p['lease']=None;p['manifest'].pop('job_id');p['manifest']['allocation']['authorization_source']=None;self.assertEqual(p,d)
  for key,val in [('replicate_id',1),('method_id','P8'),('personalization_cap',512)]:
   bad=copy.deepcopy(saved);bad['config'][key]=val
   with self.assertRaises(ValueError):h.bind(bad,{'path':'/synthetic/auth','sha256':'a'*64})
 def test_strict_budget_time_and_fresh_baseline(self):
  self.assertIsNotNone(self.s,'remaining8 supervisor missing');state={'pending':0,'uncertain':0,'known_usd':'4','held_usd':'0','attempts':298,'known_nanos':4000000000};base={'attempts':298,'spent':4000000000}
  self.s.admission_gate(state,base,datetime(2026,11,15,16,34,tzinfo=timezone.utc))
  for key,val in [('known_usd','61'),('uncertain',1),('pending',1),('attempts',299),('known_nanos',4000000001)]:
   with self.assertRaises(ValueError):self.s.admission_gate(dict(state,**{key:val}),base,datetime(2026,11,15,16,34,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):self.s.admission_gate(state,base,datetime(2026,11,15,16,34,1,tzinfo=timezone.utc))
 def test_single_batch_never_retries(self):
  self.assertIsNotNone(self.s,'remaining8 supervisor missing');calls=[]
  self.assertEqual(self.s.run_one(lambda:calls.append(1) or 1,lambda:None),(None,'child_nonzero'));self.assertEqual(calls,[1])
  def bad():raise ValueError('unknown')
  self.assertEqual(self.s.run_one(lambda:0,bad),(None,'terminal_verification_failed'))
if __name__=='__main__':unittest.main()
