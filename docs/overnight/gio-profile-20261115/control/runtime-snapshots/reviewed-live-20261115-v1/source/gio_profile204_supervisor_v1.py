"""Finite root-launched four-batch prediction supervisor; never retries or resumes.
--check is read-only. Root supplies a pinned completed zero112 gate. Native f6
batches drain their own workers; one wrapper child runs at a time (max2 inside).
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys
from decimal import Decimal
from pathlib import Path
B=Path('/private/tmp/gio-profile-20261115-coordinator')
ROOT=B/'prediction-continuation2-supervisor-v1'
INDEX={'path':'/private/tmp/gio-profile-continuation2-rebound-predictions-v1/prepared-index.json','sha256':'f081af456e4a2bedb1368f4aba87ac5467ba0332eaac89541b88a55672c30dcd'}
POLICY={'path':str(B/'accounting/phase2-continuation2-policy.json'),'sha256':'71b438f39b95ca85f9c8b8bae6813d4ab78d6c7f26ccde3abd2c744ef1503553'}
AUTHORITY={'path':str(B/'accounting/phase2-continuation2-authorization-v1.json'),'sha256':'cf3e5becc024fd787dbf14591d012a5d14c77f7ea6053ebe581bee99bd48cfda'}
TEMPLATE={'path':'/private/tmp/gio-diagnostic-envelope-proposal-v2/profile-envelope-TEMPLATE.json','sha256':'02a97edbcbc1c0971f74a20ab88015269bad28feaea3cb3de6b1dc0c0606c138'}
WRAPPER={'path':'/private/tmp/gio_diagnostic_runtime_envelope_v2.py','sha256':'8e3a2f460254c3295f36c0d07a323bb1ccdafafad4ac11425cd3963a09b8d2b5'}
OBSERVER={'path':'/private/tmp/gio_provider_diagnostics_v3.py','sha256':'d2f3372e2689adf7bdef74fc6170fa25eca7bce4b4aa3de98b495633bf284233'}
ZERO={'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'}
ORDER=[('e07d5abce984e2b3f92d63cb72a0c74b5a5b2d0daab1a2b51a1f536dcd63d755',25,350),('91abbb579973ed26736ad81f6d3f9693fc2c28c32d1174df703bfdb97de6fb25',5,70),('67f55dfe4caf4d7249e6a53b34cb29ca24352b7fb834dd77108a244f405e4bbf',90,168),('766075a4418fe5a6dc6bb05017dbb5eeee60ef96fdac0310f09e09f32cd75e74',84,84)]
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def ref(p):p=Path(p);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def read(r):
 raw=Path(r['path']).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('pin_mismatch')
 return json.loads(raw)
def write(p,v):
 with Path(p).open('x') as f:f.write(canonical(v)+'\n');f.flush();os.fsync(f.fileno())
 return ref(p)
def require(condition,code):
 if not condition:raise ValueError(code)
def nanos(value):return int((Decimal(str(value))*Decimal(1000000000)).to_integral_value())
def wrapper_module():
 require(ref(WRAPPER['path'])==WRAPPER and ref(OBSERVER['path'])==OBSERVER,'wrapper_or_observer_changed')
 s=importlib.util.spec_from_file_location('finite_profile_envelope',WRAPPER['path']);w=importlib.util.module_from_spec(s);s.loader.exec_module(w);return w

def known_usage(usage,ceiling):
 n=usage.get('attempted_calls');detail=usage.get('budget_detail',{})
 require(type(n) is int and 0<=n<=ceiling,'invalid_attempt_accounting')
 require(usage.get('uncertain_attempts')==0 and usage.get('reserved_api_usd')==0,'unknown_or_held_usage')
 require(detail.get('reported_usage_complete') is True and detail.get('reserved_usd')==0 and detail.get('unknown_input_usage_attempts')==0 and detail.get('unknown_output_usage_attempts')==0,'incomplete_provider_accounting')
 return n

def validate_events(events,allowed,attempts):
 require(len(events)==attempts,'diagnostic_attempt_count_mismatch');seen=set()
 for i,event in enumerate(events):
  key=event.get('request_sha256')
  require(event.get('sequence')==i and event.get('schema_version')=='provider-boundary-diagnostics-v3','diagnostic_sequence_or_version_mismatch')
  require(event.get('stage')=='open' and event.get('exception_type') is None and event.get('http_status')==200,'diagnostic_unknown_error_or_denial')
  require(key in allowed and allowed[key]==event.get('endpoint_body_sha256') and key not in seen,'diagnostic_body_mismatch_or_duplicate');seen.add(key)

def native_terminal(prepared_ref,job_count,call_ceiling,*,zero=False):
 batch=read(prepared_ref);root=B/'receipts'/batch['batch_id']/'execution';summary_ref=ref(root/'summary.json');summary=read(summary_ref)
 require(summary.get('schema_version')=='overnight-batch-result-v1' and summary.get('batch_id')==batch['batch_id'] and summary.get('status')=='complete' and summary.get('stop_reason') is None,'native_batch_not_complete')
 counts=summary['counts'];require(counts['listed']==counts['dispatched']==job_count and counts['not_dispatched']==0,'native_dispatch_incomplete')
 ledger=summary['ledger'];require(ledger['uncertain']==0 and ledger['inflight']==0 and ledger['held_after_uncertain'] is False and ledger['reserved_usd']==0,'native_ledger_unknown_or_active')
 require(ledger['max_inflight']==2 and ledger['max_usd']==read(POLICY)['ledger']['max_usd'],'native_ledger_policy_mismatch')
 attempts=0;spent=0;statuses=[];receipts=[]
 for packet_ref in batch['jobs']:
  p=read(packet_ref);m=p['manifest'];jid=m['job_id'];receipt_ref=ref(root/jid/'receipt.json');r=read(receipt_ref);statuses.append(r['status'])
  require(r.get('schema_version')=='overnight-dispatch-receipt-v1' and r.get('job_id')==jid and r.get('manifest_sha256')==digest(m),'native_receipt_binding_mismatch')
  require(r['status'] in ('complete','partial') and r['result_path']==str(B/'output'/jid/'result.json'),'native_job_not_known_terminal')
  result_ref=ref(r['result_path']);result=read(result_ref)
  require(result['job_id']==jid and result['manifest_hash']==digest(m) and result['status']==r['status'] and result['usage']==r['usage'],'native_result_binding_mismatch')
  u=r['usage'];attempts+=known_usage(u,p['backend']['max_calls']);spent+=nanos(u['reported_api_usd'])
  if zero:require(r['status']=='complete' and u['attempted_calls']==u['uncertain_attempts']==u['cache_hits']==0,'zero_predecessor_not_zero_complete')
  receipts.append({'receipt':receipt_ref,'result':result_ref})
 require(len(statuses)==job_count and counts['complete']==statuses.count('complete') and counts['other']==statuses.count('partial') and attempts<=call_ceiling,'native_counts_mismatch')
 if zero:require(counts=={'listed':112,'dispatched':112,'complete':112,'not_dispatched':0,'other':0} and attempts==spent==ledger['attempts']==nanos(ledger['spent_usd'])==0,'zero_predecessor_accounting_mismatch')
 return {'summary':summary_ref,'attempted_calls':attempts,'known_spent_nanos':spent,'ledger_attempts':ledger['attempts'],'ledger_spent_nanos':nanos(ledger['spent_usd']),'receipts':receipts}

def diagnostic_terminal(envelope_ref,terminal_ref,allowed,attempts):
 envelope=read(envelope_ref);terminal=read(terminal_ref);output=Path(envelope['output_root'])
 require(Path(terminal_ref['path'])==output/'envelope-terminal.json','diagnostic_terminal_path_mismatch')
 require(envelope['script_sha256']==WRAPPER['sha256'] and envelope['observer']==OBSERVER and envelope['state']=='authorized' and envelope['kind']=='profile','diagnostic_envelope_mismatch')
 claim=read(ref(output/'ENVELOPE_CLAIM.json'))
 for record in (claim,terminal):require(record.get('canonical_envelope_sha256')==digest(envelope) and record.get('wrapper_script_sha256')==WRAPPER['sha256'],'diagnostic_provenance_mismatch')
 require(claim['envelope']==envelope,'diagnostic_claim_envelope_mismatch')
 require(terminal['status']=='complete' and terminal['entry_exit_code']==terminal['wrapper_exit_code']==0 and terminal['observer_sha256']==OBSERVER['sha256'],'diagnostic_terminal_not_complete')
 diag=terminal['diagnostics'];require(diag.get('diagnostic_write_failed') is False and diag.get('diagnostic_close_failed') is False and not diag.get('diagnostic_hash_failed',False) and diag.get('dropped_event_count')==0,'diagnostic_storage_failure')
 events_path=output/'events.jsonl';require(ref(events_path)['sha256']==terminal['events_sha256'],'diagnostic_event_hash_changed')
 events=[json.loads(line) for line in events_path.read_text().splitlines()]
 require(terminal['event_count']==len(events),'diagnostic_event_count_changed');validate_events(events,allowed,attempts)
 return {'envelope':envelope_ref,'terminal':terminal_ref,'events':ref(events_path),'actual_open_events':len(events)}

def predecessor(ref_):
 gate=read(ref_);require(gate.get('schema_version')=='zero112-predecessor-gate-v1' and gate.get('state')=='complete','passed_zero_predecessor_required')
 native=native_terminal(ZERO,112,0,zero=True);require(native['summary']==gate['summary'],'zero_predecessor_summary_binding')
 env=read(gate['envelope']);require(env['inputs']=={'batch':ZERO},'zero_predecessor_batch_binding')
 diag=diagnostic_terminal(gate['envelope'],gate['wrapper_terminal'],{},0)
 return {'gate':ref_,'native':native,'diagnostics':diag}

def run_sequence(stages,run,verify,admit=lambda stage:None):
 completed=[]
 for stage in stages:
  admit(stage)
  if run(stage)!=0:return completed,'child_nonzero'
  try:result=verify(stage)
  except Exception:return completed,'terminal_verification_failed'
  completed.append(result)
 return completed,None

def preflight(predecessor_ref):
 w=wrapper_module();index=read(INDEX);policy=read(POLICY);authority=read(AUTHORITY);template=read(TEMPLATE)
 require(policy['state']==authority['state']=='authorized' and policy['continuation_authorization']==AUTHORITY and index['policy']==POLICY,'root_authority_mismatch')
 require(not ROOT.exists(),'fresh_supervisor_root_required');previous=predecessor(predecessor_ref)
 proof=read(index['candidate_proof']);rows={j['job_id']:j for j in proof['jobs']};admissions={read(a['prepared'])['batch_id']:a for a in index['admissions']};stages=[];all_ids=[];cap=Decimal(0)
 require(len(admissions)==4 and index['jobs']==204 and index['request_slots']==672,'finite_index_counts_mismatch')
 for bid,jobs,calls in ORDER:
  a=admissions[bid];batch=read(a['prepared']);require(a['jobs']==jobs and a['max_calls']==calls and batch['max_workers']==2 and batch['ledger']==policy['ledger'] and batch['ledger_policy']==POLICY,'batch_allocation_mismatch')
  require(not (B/'receipts'/bid/'execution').exists(),'old_batch_execution_cannot_resume');allowed={};ids=[]
  for p_ref in batch['jobs']:
   p=read(p_ref);m=p['manifest'];jid=m['job_id'];require(jid in rows and m['kind']=='predict' and digest(m)==rows[jid]['manifest_sha256'],'unapproved_prediction_job')
   require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'job_already_claimed_or_started')
   ids.append(jid);all_ids.append(jid);cap+=Decimal(str(m['allocation']['max_usd']))
   for item in rows[jid]['items']:allowed[item['request_sha256']]=item['endpoint_body_sha256']
  require(len(ids)==jobs and sum(read(p)['backend']['max_calls'] for p in batch['jobs'])==calls and len(allowed)==calls,'batch_denominator_changed')
  env=dict(template,state='authorized',authorization=AUTHORITY,inputs={'batch':a['prepared']},denylist=policy['unknown_request_denylist'],output_root=str(B/'diagnostic-envelopes'/('profile204-'+bid)),supervisor_provenance={'script':ref(__file__),'index':INDEX,'predecessor_gate':predecessor_ref,'policy':POLICY})
  env.pop('example_only_requires_root_rebinding',None);w.validate(env)
  stages.append({'batch_id':bid,'prepared':a['prepared'],'jobs':jobs,'max_calls':calls,'allowed':allowed,'envelope':env})
 require(len(all_ids)==len(set(all_ids))==204 and cap==Decimal('5.376'),'aggregate_job_or_dollar_ceiling_changed')
 return w,stages,previous

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--predecessor',nargs=2,required=True,metavar=('FILE','SHA256'));ap.add_argument('--check',action='store_true');a=ap.parse_args();gate={'path':str(Path(a.predecessor[0]).resolve()),'sha256':a.predecessor[1]}
 w,stages,previous=preflight(gate)
 if a.check:print('Read-only check passed: four batches, 204 jobs, <=672 calls, <=5.376 USD; no claims, network or ledger writes.');return 0
 ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 write(ROOT/'SUPERVISOR_CLAIM.json',{'schema_version':'profile204-supervisor-claim-v1','script':ref(__file__),'index':INDEX,'policy':POLICY,'authority':AUTHORITY,'predecessor':gate,'ordered_batches':[s['batch_id'] for s in stages],'max_calls':672,'max_usd':'5.376','no_retry_or_resume':True})
 for n,s in enumerate(stages):s['envelope_ref']=write(ROOT/('envelope-%02d.json'%n),s['envelope'])
 state={'attempts':0,'spent':0};active=None
 def admit(s):
  nonlocal active
  require(w.now()<w.deadline('2026-11-15T17:00:00Z'),'deadline_before_batch_admission');predecessor(gate);w.validate(s['envelope']);require(not (ROOT/'STOP_ADMISSIONS').exists(),'coordinator_stopped_admissions')
  active=s['batch_id'];write(ROOT/(active+'-started.json'),{'batch_id':active,'envelope':s['envelope_ref'],'started_at':w.now().isoformat()})
 def launch(s):
  # Environment is inherited from the root's fresh credential-injecting child.
  # No shell, dotenv execution, retry, timeout kill, or credential output.
  with (ROOT/(s['batch_id']+'-stdout.txt')).open('xb') as out,(ROOT/(s['batch_id']+'-stderr.txt')).open('xb') as err:
   return subprocess.run([sys.executable,'-B',WRAPPER['path'],'--envelope',s['envelope_ref']['path'],'--envelope-sha256',s['envelope_ref']['sha256']],env=dict(os.environ),stdin=subprocess.DEVNULL,stdout=out,stderr=err,check=False).returncode
 def verify(s):
  native=native_terminal(s['prepared'],s['jobs'],s['max_calls']);diag=diagnostic_terminal(s['envelope_ref'],ref(Path(s['envelope']['output_root'])/'envelope-terminal.json'),s['allowed'],native['attempted_calls'])
  require(native['ledger_attempts']==state['attempts']+native['attempted_calls'] and native['ledger_spent_nanos']==state['spent']+native['known_spent_nanos'],'shared_ledger_unexpected_attempt_or_cost')
  state.update(attempts=native['ledger_attempts'],spent=native['ledger_spent_nanos']);record={'batch_id':s['batch_id'],'status':'known_terminal','native':native,'diagnostics':diag};write(ROOT/(s['batch_id']+'-verified.json'),record);return record
 try:completed,reason=run_sequence(stages,launch,verify,admit)
 except Exception:completed=[];reason='admission_or_child_launch_failed_inspect_existing_artifacts'
 terminal={'schema_version':'profile204-supervisor-terminal-v1','status':'complete' if reason is None else 'stopped','stop_reason':reason,'active_batch_at_last_admission':active,'completed_verified_batches':[p.name for p in ROOT.glob('*-verified.json')],'planned_batches':4,'planned_jobs':204,'planned_call_ceiling':672,'planned_dollar_ceiling':'5.376','known_verified_attempts':state['attempts'],'known_verified_spend_nanos':state['spent'],'completed_at':w.now().isoformat(),'predecessor':gate,'index':INDEX,'script':ref(__file__),'no_retry_or_resume':True,'child_process_terminal':True,'native_accounting_drain_verified':reason is None}
 write(ROOT/'supervisor-terminal.json',terminal);print(canonical(ref(ROOT/'supervisor-terminal.json')));return 0 if reason is None else 2
if __name__=='__main__':raise SystemExit(main())
