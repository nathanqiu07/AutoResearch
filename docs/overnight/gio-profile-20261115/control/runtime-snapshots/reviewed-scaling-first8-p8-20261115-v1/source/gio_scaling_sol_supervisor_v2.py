"""Exactly Sol core84 -> lexical28 -> semantic28. Root launches after review.
--check is read-only; no retries, resume, Astra, ledger rotation or model changes.
Existing native batches drain their own max2 workers; one wrapper child at a time.
"""
import argparse,importlib.util,json,os,subprocess,sys
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
HELPER={'path':'/private/tmp/gio_prepare_scaling_sol_v1.py','sha256':'2e0e29c5dd73c334fb9ce86f1b3ee984f2f14e161c4c84427ed859a23c7c243c'}
GATES={'path':'/private/tmp/gio_profile204_supervisor_v1.py','sha256':'67d526c126ff58d88305fc2f4ccdd2ee0278cf3d55d784716c53507398a973aa'}
INDEX={'path':'/private/tmp/gio-scaling-sol-native-admissions-v1/ready-index.json','sha256':'ba96f2c68641e9d2f6bc281e8657f068ee88691261c016c5069b34b9240946e2'}
B=Path('/private/tmp/gio-profile-20261115-coordinator');ROOT=B/'scaling-sol-supervisor-v2'
def load(name,source):
 import hashlib
 p=Path(source['path'])
 if hashlib.sha256(p.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('dependency_pin_mismatch')
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('sol_admission_helpers',HELPER);g=load('sol_terminal_gates',GATES)
read,ref,require,write=h.read,h.ref,h.require,g.write

def admission_gate(state,expected,remaining_cost,remaining_seconds,now):
 h.budget_gate(state,remaining_cost);h.time_gate(now,remaining_seconds)
 require(state['attempts']==expected['attempts'] and state['known_nanos']==expected['spent'],'unexpected_shared_scaling_ledger_activity')

def run_sequence(stages,run,verify,admit):
 """No admission occurs before the preceding child is known and verified."""
 completed=[]
 for stage in stages:
  admit(stage)
  if run(stage)!=0:return completed,'child_nonzero'
  try:result=verify(stage)
  except Exception:return completed,'terminal_verification_failed'
  completed.append(result)
 return completed,None

def require_repeat_success(result, expected):
 require(result.get('job_id')==expected['job_id'] and result.get('manifest_hash')==expected['manifest_sha256'] and result.get('status')=='complete','paired_first_result_not_complete')
 rows=result.get('predictions',[])
 require(len(rows)==1 and result.get('counts')=={'attempted':1,'complete':1,'error':0},'paired_first_item_not_complete')
 row=rows[0]
 require(row.get('status')=='complete' and row.get('prediction') is not None and row.get('item_id')==expected['item_id'] and row.get('item_sha256')==expected['item_sha256'] and row.get('job_id')==expected['job_id'] and row.get('manifest_sha256')==expected['manifest_sha256'],'paired_first_item_not_complete')

def repeat_predecessor(stage):
 expected=stage['paired_first'];verified=ref(ROOT/(expected['batch_id']+'-verified.json'));record=read(verified)
 require(record.get('status')=='known_terminal' and record.get('batch_id')==expected['batch_id'] and record.get('block')=='lexical_retrieval','paired_first_batch_not_verified')
 matches=[x['result'] for x in record['native']['receipts'] if x['result']['path']==str(B/'output'/expected['job_id']/'result.json')]
 require(len(matches)==1,'paired_first_result_receipt_missing');require_repeat_success(read(matches[0]),expected)
 return {'verified_lexical_batch':verified,'successful_first_result':matches[0],'item_id':expected['item_id']}

def preflight():
 index=read(INDEX);plan=read(h.PLAN);policy,state,_=h.validate_authority(index['policy'],index['predecessor'],empty=True)
 require(index['script']==HELPER and index['plan']==h.PLAN and index['model']=='gpt-6-sol' and index['state']=='prepared_not_executed' and index['jobs']==62 and index['max_calls']==140 and Decimal(index['max_usd'])==Decimal('13.6901') and index['astra_admitted'] is False,'exact_sol_admission_index_required')
 require(not ROOT.exists(),'fresh_sol_supervisor_root_required');g.POLICY=index['policy']
 w=g.wrapper_module();authority=policy['scaling_authorization'];auth=read(authority)
 require(auth['state']=='authorized' and auth['runtime_commit']==h.COMMIT and auth['scaling_plan']==h.PLAN and auth['profile204_predecessor']==index['predecessor'] and auth['scaling_limit_nanos']==80000000000 and auth['maximum_inflight']==2 and auth['deadline']==h.DEADLINE and auth['historical_unknown_holds_released'] is False,'scaling_authority_mismatch')
 deny=read(policy['unknown_request_denylist']);require(deny['identity_denylists']==read(plan['denylist'])['identity_denylists'],'historical_denylist_changed')
 blocks=plan['tranches'][0]['batches'];require([a['block'] for a in index['admissions']]==h.BLOCKS and len(blocks)==3,'exact_sol_three_batch_order_required')
 stages=[];ids=[]
 for a,block in zip(index['admissions'],blocks):
  batch=read(a['prepared']);bid=batch['batch_id'];require(not (B/'receipts'/bid/'execution').exists(),'old_batch_cannot_resume')
  require(batch['max_workers']==2 and batch['ledger']==policy['ledger'] and batch['ledger_policy']==index['policy'] and batch['deadline']==h.DEADLINE and batch['max_total_attempts']==block['max_calls'],'native_batch_allocation_mismatch')
  require(a['jobs']==block['native_jobs']==len(batch['jobs']) and a['calls']==block['max_calls'] and Decimal(a['max_usd'])==Decimal(block['max_usd']) and a['two_slot_job_budget_schedule_seconds']==block['two_slot_job_budget_schedule_seconds'],'block_limits_mismatch')
  allowed={};cap=Decimal(0)
  for packet_ref,row in zip(batch['jobs'],block['jobs']):
   packet=read(packet_ref);expected=h.bind(read(row['packet']),index['policy'],index['predecessor'])
   # Native publication relocates these byte-identical source files into its immutable receipt.
   normalized=dict(packet)
   for key in ('profile','release'):
    require(packet[key]['sha256']==expected[key]['sha256'] and read(packet[key])==read(expected[key]),'published_source_content_changed');normalized[key]=expected[key]
   require(normalized==expected,'prepared_scientific_packet_changed')
   jid=packet['manifest']['job_id'];ids.append(jid);require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'job_already_claimed_or_started');cap+=Decimal(str(packet['manifest']['allocation']['max_usd']))
   for r in row['requests']:
    key=r['request_sha256'];require(key not in allowed,'unexpected_within_batch_repeat');require(key not in deny['identity_denylists']['body_compact_json_sha256'] and r['endpoint_body_sha256'] not in deny['identity_denylists']['endpoint_body_sorted_json_sha256'],'historical_unknown_identity_collision');allowed[key]=r['endpoint_body_sha256']
  require(len(allowed)==a['calls'] and cap==Decimal(block['max_usd']),'block_denominator_or_cap_changed')
  env=dict(read(g.TEMPLATE),state='authorized',authorization=authority,inputs={'batch':a['prepared']},denylist=policy['unknown_request_denylist'],output_root=str(B/'diagnostic-envelopes'/('scaling-sol-'+bid)),supervisor_provenance={'script':ref(__file__),'index':INDEX,'policy':index['policy'],'predecessor_gate':index['predecessor']})
  env.pop('example_only_requires_root_rebinding',None);w.validate(env)
  stages.append({'block':a['block'],'batch_id':bid,'prepared':a['prepared'],'jobs':a['jobs'],'max_calls':a['calls'],'max_usd':a['max_usd'],'schedule_seconds':a['two_slot_job_budget_schedule_seconds'],'allowed':allowed,'envelope':env})
 require(len(ids)==len(set(ids))==62 and sum(s['max_calls'] for s in stages)==140,'sol_denominator_changed')
 repeats=[d for d in plan['duplicates'] if all(x['model']=='gpt-6-sol' for x in d['rows'])]
 require(len(repeats)==1,'exact_sol_paired_repeat_required');first=[r for r in repeats[0]['rows'] if r['method']=='lexical_retrieval'];require(len(first)==1,'paired_first_not_unique')
 original=read(first[0]['packet']);bound=h.bind(original,index['policy'],index['predecessor']);pin=first[0]['pin']
 require(repeats[0]['request_sha256'] in stages[1]['allowed'] and repeats[0]['request_sha256'] in stages[2]['allowed'],'paired_repeat_batch_binding_changed')
 stages[2]['paired_first']={'batch_id':stages[1]['batch_id'],'job_id':bound['manifest']['job_id'],'manifest_sha256':h.digest(bound['manifest']),'item_id':pin['item_id'],'item_sha256':pin['item_sha256']}
 for n,s in enumerate(stages):
  s['remaining_max_usd']=str(sum((Decimal(x['max_usd']) for x in stages[n:]),Decimal(0)));s['remaining_schedule_seconds']=sum(x['schedule_seconds'] for x in stages[n:])
 admission_gate(state,{'attempts':0,'spent':0},stages[0]['remaining_max_usd'],stages[0]['remaining_schedule_seconds'],datetime.now(timezone.utc))
 return w,index,policy,stages

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');args=ap.parse_args();sys.dont_write_bytecode=True
 w,index,policy,stages=preflight()
 if args.check:print('Read-only check passed: Sol core84 -> lexical28 -> semantic28, 62 jobs, <=140 calls, <=13.6901 USD; dedicated 80 USD ledger; no claims, network or writes.');return 0
 ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 write(ROOT/'SUPERVISOR_CLAIM.json',{'schema_version':'scaling-sol-supervisor-claim-v2','script':ref(__file__),'index':INDEX,'policy':index['policy'],'authority':policy['scaling_authorization'],'predecessor':index['predecessor'],'ordered_batches':[s['batch_id'] for s in stages],'max_calls':140,'max_usd':'13.6901','no_retry_or_resume':True,'astra_admitted':False})
 for n,s in enumerate(stages):s['envelope_ref']=write(ROOT/('envelope-%02d.json'%n),s['envelope'])
 state={'attempts':0,'spent':0};active=None
 def admit(s):
  nonlocal active
  _,actual,_=h.validate_authority(index['policy'],index['predecessor']);admission_gate(actual,state,s['remaining_max_usd'],s['remaining_schedule_seconds'],datetime.now(timezone.utc))
  require(not (ROOT/'STOP_ADMISSIONS').exists(),'coordinator_stopped_admissions');w.validate(s['envelope'])
  repeat_gate=repeat_predecessor(s) if s['block']=='semantic_retrieval' else None
  active=s['batch_id'];write(ROOT/(active+'-started.json'),{'batch_id':active,'block':s['block'],'envelope':s['envelope_ref'],'started_at':w.now().isoformat(),'successful_paired_first':repeat_gate})
 def launch(s):
  # Root injects credentials into this fresh child's environment; no shell or parsing.
  with (ROOT/(s['batch_id']+'-stdout.txt')).open('xb') as out,(ROOT/(s['batch_id']+'-stderr.txt')).open('xb') as err:
   return subprocess.run([sys.executable,'-B',g.WRAPPER['path'],'--envelope',s['envelope_ref']['path'],'--envelope-sha256',s['envelope_ref']['sha256']],env=dict(os.environ),stdin=subprocess.DEVNULL,stdout=out,stderr=err,check=False).returncode
 def verify(s):
  native=g.native_terminal(s['prepared'],s['jobs'],s['max_calls']);diag=g.diagnostic_terminal(s['envelope_ref'],ref(Path(s['envelope']['output_root'])/'envelope-terminal.json'),s['allowed'],native['attempted_calls'])
  require(native['ledger_attempts']==state['attempts']+native['attempted_calls'] and native['ledger_spent_nanos']==state['spent']+native['known_spent_nanos'],'shared_ledger_unexpected_attempt_or_cost')
  actual=h.ledger_read(policy['ledger']['path']);h.budget_gate(actual,0);require(actual['attempts']==native['ledger_attempts'] and actual['known_nanos']==native['ledger_spent_nanos'],'terminal_ledger_changed')
  state.update(attempts=native['ledger_attempts'],spent=native['ledger_spent_nanos']);record={'batch_id':s['batch_id'],'block':s['block'],'status':'known_terminal','native':native,'diagnostics':diag};write(ROOT/(s['batch_id']+'-verified.json'),record);return record
 try:completed,reason=run_sequence(stages,launch,verify,admit)
 except Exception:reason='admission_or_child_launch_failed_inspect_existing_artifacts'
 terminal={'schema_version':'scaling-sol-supervisor-terminal-v2','status':'complete' if reason is None else 'stopped','stop_reason':reason,'active_batch_at_last_admission':active,'completed_verified_batches':[p.name for p in ROOT.glob('*-verified.json')],'planned_batches':3,'planned_jobs':62,'planned_call_ceiling':140,'planned_dollar_ceiling':'13.6901','known_verified_attempts':state['attempts'],'known_verified_spend_nanos':state['spent'],'completed_at':w.now().isoformat(),'predecessor':index['predecessor'],'index':INDEX,'script':ref(__file__),'no_retry_or_resume':True,'child_process_terminal':True,'native_accounting_drain_verified':reason is None,'astra_admitted':False,'all_six_planned_batches_preserved':True}
 write(ROOT/'supervisor-terminal.json',terminal);print(g.canonical(ref(ROOT/'supervisor-terminal.json')));return 0 if reason is None else 2
if __name__=='__main__':raise SystemExit(main())
