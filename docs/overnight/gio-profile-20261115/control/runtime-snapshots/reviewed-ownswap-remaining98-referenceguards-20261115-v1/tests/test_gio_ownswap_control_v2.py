import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('ownswap_control_helper','/private/tmp/gio_prepare_ownswap_v2.py');w=load('ownswap_control_wrapper','/private/tmp/gio_diagnostic_runtime_envelope_ownswap_v1.py')
class Control(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='gio-ownswap-offline-control-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.n=0
 def put(self,v):self.n+=1;return h.write(self.root/('%03d.json'%self.n),v)
 def test_actual_two_complementary_native_packets_admit_with_no_ledger_network(self):
  driver=h.runtime();from autoresearch.taste.overnight.backends import DollarLedger
  packets,rows=h.make_drafts();authority=dict(h.assignment_template(),state='authorized',authority='Synthetic offline fixture; not issued');auth=self.put(authority);template=h.read(h.TEMPLATE);batch=copy.deepcopy(template);batch.update(code_sha=h.COMMIT,runtime_root=str(h.R),max_total_attempts=28,ledger=h.policy_template()['ledger']);ledger=object.__new__(DollarLedger);prepared=[]
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('SQL')):
   for packet in packets:
    bound=h.bind(packet,auth);j=driver._prepare_packet(bound,batch,ledger);prepared.append(j);self.assertEqual(j['manifest']['allocation']['authorization_source'],auth['sha256']);self.assertEqual(j['packet']['assignment_authority'],auth);self.assertEqual(len(j['items']),14);self.assertNotEqual(j['profile'].researcher_id,j['items'][0]['researcher_id']);self.assertEqual(j['profile'].to_dict(),h.read(packet['profile']))
   driver.validate_assignment_batch(prepared,28)
  self.assertEqual(sum(h.Decimal(x['max_usd']) for x in rows),h.Decimal('0.135373000'))
  for bad in ([prepared[0]],[prepared[0],prepared[0]]):
   with self.assertRaises(ValueError):driver.validate_assignment_batch(bad,28)
 def test_assignment_authority_cannot_change_scope_runtime_slots_or_donors(self):
  packets,_=h.make_drafts();auth=dict(h.assignment_template(),state='authorized',authority='Synthetic offline fixture')
  for k,v in [('state','proposal'),('authority',None),('max_calls',29),('runtime_code_sha','f'*40),('assignment_sha256s',[]),('scope','other')]:
   with self.subTest(k=k),self.assertRaises(ValueError):h.bind(packets[0],self.put(dict(auth,**{k:v})))
 def test_new_ledger_template_is_separate_and_capacity_conserved(self):
  p=h.policy_template();self.assertEqual(p['ledger'],{'path':str(h.B/'ledger/profile-ownswap-v1.sqlite'),'max_usd':1,'max_inflight':2});a=p['capacity_accounting'];self.assertEqual(h.Decimal(a['unissued_before_usd'])-h.Decimal(a['unissued_after_usd']),1);self.assertEqual(h.Decimal(a['committed_before_usd'])+h.Decimal(a['unissued_before_usd']),192);self.assertFalse(p['historical_unknown_holds_released']);self.assertEqual(p['prior_scaling_allocation_usd'],80)
 def test_old80ledger_or_wrong_allocation_rejected_before_any_sql(self):
  root=Path('/private/tmp/gio-ownswap-offline-proposal-v2-ready');auth=h.read(h.ref(root/'execution-authority-TEMPLATE.json'));auth.update(state='authorized',authority='Synthetic offline',assignment_authority=self.put(dict(h.assignment_template(),state='authorized',authority='Synthetic offline')),predecessor={'path':'/unused/never-read','sha256':'0'*64});p=dict(h.policy_template(),state='authorized',authority='Synthetic offline',predecessor=auth['predecessor'])
  for spec in [dict(p['ledger'],max_usd=80),dict(p['ledger'],path=str(h.B/'ledger/profile-openai-scaling-v1.sqlite')),dict(p['ledger'],max_inflight=3)]:
   aa=dict(auth,policy=self.put(dict(p,ledger=spec)))
   with patch('sqlite3.connect',side_effect=AssertionError('SQL must not be reached')),self.assertRaisesRegex(ValueError,'dedicated_one_dollar'):h.validate_execution_authority(self.put(aa))
 def envelope(self):
  env=h.read({'path':'/private/tmp/gio-diagnostic-envelope-proposal-v2/profile-envelope-TEMPLATE.json','sha256':'02a97edbcbc1c0971f74a20ab88015269bad28feaea3cb3de6b1dc0c0606c138'});env.update(state='proposal',script_sha256=h.ref(w.__file__)['sha256'],runtime_root=str(h.R),runtime_commit=h.COMMIT,denylist=h.DENY,inputs={'batch':self.put({'code_sha':h.COMMIT,'max_workers':2,'max_total_attempts':28,'jobs':[{},{}]})},output_root=str(h.B/'diagnostic-envelopes'/('ownswap-offline-check-'+self.root.name)))
  keys=set(env['runtime_files'])|{'autoresearch/taste/overnight/cross_subject_assignment.py','autoresearch/taste/overnight/profiles_hypotheses.py'};env['runtime_files']={k:h.ref(h.R/k)['sha256'] for k in keys};return env
 def test_actual_native_wrapper_pins_and_required_assignment_guard(self):
  env=self.envelope();entry,args,deny=w.validate(env,check_only=True);self.assertEqual(entry,h.R/h.DRIVER_REL);self.assertEqual(args[0],'execute');self.assertEqual(len(deny['body_compact_json_sha256']),6);self.assertEqual(len(deny['endpoint_body_sorted_json_sha256']),7)
  for k,v in [('runtime_commit','f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'),('denylist',{'path':'/wrong','sha256':'0'*64})]:
   with self.subTest(k=k),self.assertRaises(ValueError):w.validate(dict(env,**{k:v}),check_only=True)
  bad=copy.deepcopy(env);bad['runtime_files'].pop('autoresearch/taste/overnight/cross_subject_assignment.py')
  with self.assertRaises(ValueError):w.validate(bad,check_only=True)
  bad=copy.deepcopy(env);bad['inputs']['batch']=self.put({'code_sha':h.COMMIT,'max_workers':2,'max_total_attempts':14,'jobs':[{}]})
  with self.assertRaises(ValueError):w.validate(bad,check_only=True)
if __name__=='__main__':unittest.main()
