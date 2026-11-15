import copy,importlib.util,unittest
from unittest.mock import patch
s=importlib.util.spec_from_file_location('prepare','/private/tmp/gio_prepare_scaling_astra_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def state(self,spent=1000000000):
  rows=[['sol-request',100000000,spent,'complete','{}']];policy=[[1,'policy']]
  snapshot={'schema_version':'closed-ledger-logical-snapshot-v1','policy_rows':policy,'reservation_rows':rows,'pending':0,'uncertain':0,'retained_hold_nanos':0,'known_spent_nanos':spent,'attempts':1,'logical_snapshot_sha256':m.digest({'policy_rows':policy,'reservation_rows':rows})}
  current={'policy_rows':copy.deepcopy(policy),'reservation_rows':copy.deepcopy(rows),'pending':0,'uncertain':0,'known_usd':str(spent/1e9),'held_usd':'0'};return current,snapshot
 def test_baseline_and_exact80_boundary(self):
  current,snapshot=self.state(11546000000);self.assertEqual(m.validate_baseline(current,snapshot,initial=True)['spent'],11546000000)
  current,snapshot=self.state(11546000001)
  with self.assertRaises(ValueError):m.validate_baseline(current,snapshot,initial=True)
 def test_no_admission_after_unrelated_attempt(self):
  current,snapshot=self.state();current['reservation_rows'].append(['new',1,1,'complete','{}'])
  with self.assertRaises(ValueError):m.validate_baseline(current,snapshot,initial=True)
  m.validate_baseline(current,snapshot,initial=False)
 def test_no_reset_or_changed_old_reservation(self):
  current,snapshot=self.state();current['reservation_rows'][0][2]=0
  with self.assertRaises(ValueError):m.validate_baseline(current,snapshot,initial=False)
 def test_pending_or_uncertain_blocks_even_with_headroom(self):
  for key in ('pending','uncertain'):
   current,snapshot=self.state();current[key]=1
   with self.assertRaises(ValueError):m.validate_baseline(current,snapshot,initial=False)
 def test_separate_authority_before_any_ledger_connection(self):
  with patch.object(m,'read',return_value={'state':'prepared'}),patch.object(m.h,'validate_authority') as live:
   with self.assertRaises(ValueError):m.validate_astra_authority({})
   live.assert_not_called()
 def test_full_authority_reconciles_sol_before_admission(self):
  current,snapshot=self.state();snapshot['source_path']=str(m.B/'ledger/profile-openai-scaling-v1.sqlite')
  auth={'schema_version':'scaling-astra-authorization-v1','state':'authorized','scope':m.SCOPE,'authority':'synthetic root','policy':m.POLICY,'scaling_plan':m.PLAN,'runtime_commit':m.COMMIT,'deadline':m.DEADLINE,'max_inflight':2,'max_calls':140,'max_usd':'68.454','historical_unknown_holds_released':False,'sol_predecessor':{'path':'pre'},'sol_supervisor':{'path':'script','sha256':'script-pin'}}
  terminal={'schema_version':'scaling-sol-supervisor-terminal-v2','status':'complete','stop_reason':None,'child_process_terminal':True,'native_accounting_drain_verified':True,'planned_jobs':62,'completed_verified_batches':['a','b','c'],'index':m.SOL_INDEX,'script':auth['sol_supervisor'],'known_verified_attempts':1,'known_verified_spend_nanos':1000000000}
  summary={'batch_id':'last','status':'complete','stop_reason':None,'ledger':{'inflight':0,'uncertain':0,'reserved_usd':0,'held_after_uncertain':False,'attempts':1,'spent_usd':1}}
  pre={'schema_version':'scaling-sol-astra-predecessor-v1','state':'complete','supervisor_terminal':{'path':'terminal'},'final_batch_summary':{'path':'summary'},'closed_ledger_snapshot':{'path':'snapshot'}}
  policy={'ledger':{'path':snapshot['source_path']},'profile204_predecessor':{'path':'old'}}
  fixtures={'auth':auth,'pre':pre,'terminal':terminal,'summary':summary,'snapshot':snapshot,m.SOL_INDEX['path']:{'admissions':[{'prepared':{'path':'last'}}]},'last':{'batch_id':'last'},m.POLICY['path']:policy}
  with patch.object(m,'read',side_effect=lambda r:fixtures[r['path']]),patch.object(m,'ref',return_value=auth['sol_supervisor']),patch.object(m.h,'validate_authority',return_value=(policy,current,{})):
   self.assertEqual(m.validate_astra_authority({'path':'auth'},initial=True)[-1],{'attempts':1,'spent':1000000000})
   terminal['known_verified_spend_nanos']=0
   with self.assertRaises(ValueError):m.validate_astra_authority({'path':'auth'},initial=True)
 def test_only_authority_changes_and_sol_rejected(self):
  draft={'lease':None,'manifest':{'kind':'predict','allocation':{'authorization_source':None}},'backend':{'model':'gpt-6-astra'},'items':['same']};before=copy.deepcopy(draft);p=m.bind(draft,{'path':'auth','sha256':'pin'});self.assertEqual(draft,before);p['lease']=None;p['manifest'].pop('job_id');p['manifest']['allocation']['authorization_source']=None;self.assertEqual(p,draft);draft['backend']['model']='gpt-6-sol'
  with self.assertRaises(ValueError):m.bind(draft,{})
if __name__=='__main__':unittest.main()
