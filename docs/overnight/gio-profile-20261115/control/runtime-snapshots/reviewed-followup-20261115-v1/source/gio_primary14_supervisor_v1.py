"""Finite one-child primary14 prediction supervisor. No retry, followup, repair or ledger rotation.
--check reads pinned metadata, replays frozen payload construction and opens SQL read-only.
"""
import argparse,importlib.util,hashlib,os,subprocess,sys
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode=True
HELPER={'path':'/private/tmp/gio_prepare_primary14_v1.py','sha256':'181fcd09bdce74fcb94b99f9d86118cebd304167544e03b65a88a1b5e8a00dd2'}
GATES={'path':'/private/tmp/gio_profile204_supervisor_v1.py','sha256':'67d526c126ff58d88305fc2f4ccdd2ee0278cf3d55d784716c53507398a973aa'}
def load(name,source):
 p=Path(source['path'])
 if hashlib.sha256(p.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('dependency_pin_mismatch')
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('primary14_helper',HELPER);g=load('primary14_terminal_helpers',GATES);g.POLICY=h.POLICY
B=h.B;ROOT=B/'p8-primary14-supervisor-v1';read,ref,require,write=h.read,h.ref,h.require,g.write

def admission_gate(state,baseline,now):
 h.h.budget_gate(state,h.TOTAL);h.h.time_gate(now,900)
 require(state['attempts']==baseline['attempts'] and state['known_nanos']==baseline['spent'],'unexpected_shared_scaling_ledger_activity')
def run_one(launch,verify):
 if launch()!=0:return None,'child_nonzero'
 try:return verify(),None
 except Exception:return None,'terminal_verification_failed'
def preflight(index_ref):
 index=read(index_ref);require(index['schema_version']=='p8-primary14-admission-index-v1' and index['state']=='prepared_not_executed' and index['script']==HELPER and index['jobs']==1 and index['max_calls']==14 and Decimal(index['max_usd'])==Decimal(h.TOTAL) and index['planned_descendant_slots']==84 and index['unavailable_descendant_slots']==70 and index['automatic_followup'] is False,'exact_primary14_index_required')
 auth,policy,current,_,baseline=h.validate_authority(index['authority'],initial=True)
 require(index['policy']==h.POLICY and index['proposal']==auth['proposal'] and index['predecessor']==h.PREDECESSOR and index['bindings']==h.BINDINGS and index['unknown_denylist']==h.DENY and index['baseline']==baseline,'primary14_index_authority_mismatch')
 require(not ROOT.exists(),'fresh_primary14_supervisor_root_required');batch=read(index['prepared']);bid=batch['batch_id'];require(not (B/'receipts'/bid/'execution').exists(),'old_primary14_batch_cannot_resume')
 require(batch['max_workers']==2 and batch['max_total_attempts']==14 and batch['ledger']==policy['ledger'] and batch['ledger_policy']==h.POLICY and batch['deadline']==h.DEADLINE and len(batch['jobs'])==1 and batch['primary14_authority']==index['authority'],'primary14_batch_limits_mismatch')
 proposal=read(index['proposal']);row=h.capture();require(row==proposal['draft'],'captured_requests_changed')
 p=read(batch['jobs'][0]);expected=h.bind(read(h.DRAFT),index['authority']);normalized=dict(p)
 for key in ('release','profile'):
  require(p[key]['sha256']==expected[key]['sha256'] and Path(p[key]['path']).read_bytes()==Path(expected[key]['path']).read_bytes(),'primary14_input_bytes_changed');normalized[key]=expected[key]
 require(normalized==expected,'primary14_scientific_packet_changed');jid=p['manifest']['job_id'];require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'primary14_job_already_started')
 allowed={r['request_sha256']:r['endpoint_body_sha256'] for r in row['requests']};require(len(allowed)==14,'primary14_denominator_changed')
 w=g.wrapper_module();env=dict(read(g.TEMPLATE),state='authorized',authorization=index['authority'],inputs={'batch':index['prepared']},denylist=h.DENY,output_root=str(B/'diagnostic-envelopes'/('p8-primary14-'+bid)),supervisor_provenance={'script':ref(__file__),'index':index_ref,'policy':h.POLICY,'predecessor_gate':h.PREDECESSOR})
 env.pop('example_only_requires_root_rebinding',None);w.validate(env);admission_gate(current,baseline,datetime.now(timezone.utc))
 return w,index,policy,batch,baseline,allowed,env

def verify_completed(index,baseline,allowed,envelope,env):
 native=g.native_terminal(index['prepared'],1,14)
 require(native['attempted_calls']==14,'primary14_not_all_attempted')
 receipt=read(native['receipts'][0]['receipt']);require(receipt['usage']['cache_hits']==0,'primary14_requires_fresh_requests')
 diagnostics=g.diagnostic_terminal(envelope,ref(Path(env['output_root'])/'envelope-terminal.json'),allowed,native['attempted_calls'])
 require(native['ledger_attempts']==baseline['attempts']+14 and native['ledger_spent_nanos']==baseline['spent']+native['known_spent_nanos'],'primary14_cumulative_ledger_mismatch')
 _,_,actual,_,confirmed=h.validate_authority(index['authority']);require(confirmed==baseline and actual['attempts']==native['ledger_attempts'] and actual['known_nanos']==native['ledger_spent_nanos'],'primary14_actual_ledger_mismatch')
 return {'native':native,'diagnostics':diagnostics,'baseline':baseline}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ready-index',nargs=2,required=True);ap.add_argument('--check',action='store_true');args=ap.parse_args();index_ref={'path':str(Path(args.ready_index[0]).resolve()),'sha256':args.ready_index[1]};w,index,policy,batch,baseline,allowed,env=preflight(index_ref)
 if args.check:print('Read-only primary14 check passed: one Neel/Sol joint job, 14 slots, 1.51148 USD, same80 ledger, typed11 denylist; no calls, claims or writes.');return 0
 ROOT.mkdir(mode=0o700,parents=True,exist_ok=False);write(ROOT/'SUPERVISOR_CLAIM.json',{'schema_version':'p8-primary14-supervisor-claim-v1','script':ref(__file__),'index':index_ref,'authority':index['authority'],'policy':h.POLICY,'baseline':baseline,'prepared':index['prepared'],'max_calls':14,'max_usd':h.TOTAL,'no_retry_or_followup':True})
 envelope=write(ROOT/'envelope.json',env);verified=None;reason=None
 def launch():
  with (ROOT/'stdout.txt').open('xb') as out,(ROOT/'stderr.txt').open('xb') as err:
   return subprocess.run([sys.executable,'-B',g.WRAPPER['path'],'--envelope',envelope['path'],'--envelope-sha256',envelope['sha256']],env=dict(os.environ),stdin=subprocess.DEVNULL,stdout=out,stderr=err,check=False).returncode
 try:
  _,_,actual,_,confirmed=h.validate_authority(index['authority'],initial=True);require(confirmed==baseline,'first4_baseline_changed');admission_gate(actual,baseline,datetime.now(timezone.utc));require(not (ROOT/'STOP_ADMISSIONS').exists(),'coordinator_stopped_admissions');w.validate(env)
  write(ROOT/'started.json',{'prepared':index['prepared'],'envelope':envelope,'started_at':w.now().isoformat()});result,reason=run_one(launch,lambda:verify_completed(index,baseline,allowed,envelope,env))
  if result is not None:verified=write(ROOT/'verified.json',result)
 except Exception:reason='admission_or_child_launch_failed_inspect_existing_artifacts'
 terminal={'schema_version':'p8-primary14-supervisor-terminal-v1','status':'complete' if reason is None else 'stopped','stop_reason':reason,'index':index_ref,'script':ref(__file__),'baseline':baseline,'verified':verified,'planned_jobs':1,'planned_call_ceiling':14,'planned_dollar_ceiling':h.TOTAL,'planned_descendant_slots':84,'unavailable_descendant_slots':70,'child_process_terminal':True,'native_accounting_drain_verified':reason is None,'no_retry_or_followup':True,'completed_at':w.now().isoformat()}
 print(h.canonical(write(ROOT/'supervisor-terminal.json',terminal)));return 0 if reason is None else 2
if __name__=='__main__':raise SystemExit(main())
