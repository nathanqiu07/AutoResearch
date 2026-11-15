import copy, importlib.util, json, pathlib, unittest
from datetime import datetime, timezone
from unittest.mock import patch
H=pathlib.Path('/private/tmp/gio_prepare_primary14_v1.py')
S=pathlib.Path('/private/tmp/gio_primary14_supervisor_v1.py')
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Primary14(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.h=load(H,'primary14_test_helper') if H.exists() else None
  cls.s=load(S,'primary14_test_supervisor') if S.exists() else None
 def test_exact_draft_preserved_and_no_extra_cell(self):
  self.assertIsNotNone(self.h,'primary14 admission helper not implemented')
  h=self.h;d=h.read(h.DRAFT);before=copy.deepcopy(d);p=h.bind(d,{'path':'/synthetic/auth','sha256':'a'*64});self.assertEqual(d,before)
  p['lease']=None;p['manifest'].pop('job_id');p['manifest']['allocation']['authorization_source']=None;self.assertEqual(p,d)
  for change in ('model','max_calls','max_seconds'):
   bad=copy.deepcopy(d);bad['backend'][change]={'model':'gpt-6-astra','max_calls':15,'max_seconds':901}[change]
   with self.assertRaises(ValueError):h.bind(bad,{'path':'/synthetic/auth','sha256':'a'*64})
 def test_actual14_capture_no_network_or_ledger(self):
  self.assertIsNotNone(self.h,'primary14 admission helper not implemented')
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('ledger')):row=self.h.capture()
  self.assertEqual(len(row['requests']),14);self.assertEqual(len({r['request_sha256'] for r in row['requests']}),14);self.assertEqual(row['max_usd'],'1.51148')
 def test_each_identity_namespace_blocks(self):
  self.assertIsNotNone(self.h,'primary14 admission helper not implemented')
  for key in ('body_compact_json_sha256','endpoint_body_sorted_json_sha256'):
   deny={'body_compact_json_sha256':[],'endpoint_body_sorted_json_sha256':[]};deny[key]=['x'];info={'request_sha256':'x' if key.startswith('body') else 'y','endpoint_body_sha256':'x' if key.startswith('endpoint') else 'y'}
   with self.assertRaisesRegex(ValueError,'historical_unknown'):self.h.p.reject_unknown(info,deny)
 def test_budget_deadline_and_baseline_guard(self):
  self.assertIsNotNone(self.s,'primary14 supervisor not implemented')
  state={'pending':0,'uncertain':0,'known_usd':'3.26030','held_usd':'0','attempts':284,'known_nanos':3260300000};base={'attempts':284,'spent':3260300000}
  self.s.admission_gate(state,base,datetime(2026,11,15,16,30,tzinfo=timezone.utc))
  for key,val in [('uncertain',1),('pending',1),('known_usd','79'),('attempts',285),('known_nanos',3260300001)]:
   with self.assertRaises(ValueError):self.s.admission_gate(dict(state,**{key:val}),base,datetime(2026,11,15,16,30,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):self.s.admission_gate(state,base,datetime(2026,11,15,16,36,tzinfo=timezone.utc))
 def test_one_child_no_retry_on_nonzero_or_unknown(self):
  self.assertIsNotNone(self.s,'primary14 supervisor not implemented')
  calls=[]
  self.assertEqual(self.s.run_one(lambda:calls.append('launch') or 2,lambda:1),(None,'child_nonzero'));self.assertEqual(calls,['launch'])
  def bad():raise ValueError('unknown_or_missing_diagnostics')
  calls=[];self.assertEqual(self.s.run_one(lambda:calls.append('launch') or 0,bad),(None,'terminal_verification_failed'));self.assertEqual(calls,['launch'])
  self.assertEqual(self.s.run_one(lambda:0,lambda:{'known':True}),({'known':True},None))
if __name__=='__main__':unittest.main()
