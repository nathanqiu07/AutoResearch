"""Finite two-batch supervisor for exactly seven frozen P7/P3 joint prediction jobs.
Root executes after explicit authority; --check reads pinned metadata and replays frozen prediction payloads.
No automatic followup, method change, retry, repair, resume or ledger rotation.
"""
import argparse, importlib.util, json, os, subprocess, sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode=True
HELPER={'path':'/private/tmp/gio_prepare_remaining98_v1.py','sha256':'9b9ac646ca117802a0b09eaab3336188b2c1ed4917317baadea6b7845695e19d'}
GATES={'path':'/private/tmp/gio_profile204_supervisor_v1.py','sha256':'67d526c126ff58d88305fc2f4ccdd2ee0278cf3d55d784716c53507398a973aa'}
def load(name,source):
    import hashlib
    p=Path(source['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('dependency_pin_mismatch')
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('remaining98_helpers',HELPER);g=load('remaining98_terminal_helpers',GATES);g.POLICY=h.POLICY
B=h.B;ROOT=B/'remaining98-prediction-supervisor-v1';read,ref,require,write=h.read,h.ref,h.require,g.write

def admission_gate(state,baseline,now,*,expected_attempts=None,expected_spent=None,remaining_blocks=2):
    require(remaining_blocks in (1,2),'invalid_remaining_block_count');h.h.budget_gate(state,h.TOTAL if remaining_blocks==2 else '10.132720');h.h.time_gate(now,1800*remaining_blocks)
    require(state['attempts']==(baseline['attempts'] if expected_attempts is None else expected_attempts) and state['known_nanos']==(baseline['spent'] if expected_spent is None else expected_spent),'unexpected_shared_scaling_ledger_activity')

def native_terminal(prepared_ref,jobs,calls):
    native=g.native_terminal(prepared_ref,jobs,calls);require(native['attempted_calls']==calls,'full_declared_known_attempts_required')
    for row in native['receipts']:
        receipt=read(row['receipt']);require(receipt['usage']['attempted_calls']==14 and receipt['usage']['cache_hits']==0,'each_prediction_job_requires14_fresh_known_calls')
    return native

def run_one(launch,verify):
    if launch()!=0:return None,'child_nonzero'
    try:return verify(),None
    except Exception:return None,'terminal_verification_failed'

def preflight(index_ref):
    index=read(index_ref);require(index['schema_version']=='remaining98-prediction-admission-index-v1' and index['state']=='prepared_not_executed' and index['script']==HELPER and index['jobs']==7 and index['max_calls']==98 and Decimal(index['max_usd'])==Decimal(h.TOTAL) and index['planned_descendant_slots']==112 and index['unavailable_descendant_slots']==14,'exact_remaining98_index_required')
    auth,policy,current,_,baseline=h.validate_authority(index['authority'],initial=True)
    require(index['policy']==h.POLICY and index['proposal']==auth['proposal'] and index['predecessor']==h.PREDECESSOR and index['baseline']==baseline and index['bindings']==h.BINDINGS and index['ownswap_completed_gate']==auth['ownswap_completed_gate'] and index['unknown_denylist']==h.DENY and index['automatic_followup'] is False,'remaining98_index_authority_mismatch')
    require(not ROOT.exists(),'fresh_remaining98_supervisor_root_required');proposal=read(index['proposal']);rows=h.capture_rows();blocks=h.batch_blocks(rows);require(rows==proposal['drafts'] and blocks==proposal['blocks'] and [a['block'] for a in index['admissions']]==['P7','P3'],'remaining98_blocks_changed')
    stages=[];ids=[];w=g.wrapper_module()
    for admission,block in zip(index['admissions'],blocks):
        batch=read(admission['prepared']);bid=batch['batch_id'];require(not (B/'receipts'/bid/'execution').exists(),'old_remaining98_batch_cannot_resume')
        require(admission['jobs']==block['jobs'] and admission['max_calls']==block['max_calls'] and Decimal(admission['max_usd'])==Decimal(block['max_usd']) and admission['release_schema_version']==block['release_schema_version'] and batch['release_schema_version']==block['release_schema_version'] and batch['remaining98_block']==block['block'] and batch['remaining98_authority']==index['authority'] and batch['max_workers']==2 and batch['max_total_attempts']==block['max_calls'] and batch['ledger']==policy['ledger'] and batch['ledger_policy']==h.POLICY and batch['deadline']==h.DEADLINE and len(batch['jobs'])==block['jobs'],'remaining98_homogeneous_batch_limits_mismatch')
        allowed={};cap=Decimal(0)
        for pr,row in zip(batch['jobs'],block['rows']):
            p=read(pr);expected=h.bind(read(row['packet']),index['authority']);normalized=dict(p)
            for key in ('release','profile'):
                require(p[key]['sha256']==expected[key]['sha256'] and Path(p[key]['path']).read_bytes()==Path(expected[key]['path']).read_bytes(),'remaining98_input_bytes_changed');normalized[key]=expected[key]
            require(normalized==expected,'remaining98_scientific_packet_changed');jid=p['manifest']['job_id'];ids.append(jid)
            require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'remaining98_job_already_started');cap+=Decimal(str(p['backend']['max_usd']))
            for request in row['requests']:allowed[request['request_sha256']]=request['endpoint_body_sha256']
        require(len(allowed)==block['max_calls'] and cap==Decimal(block['max_usd']),'remaining98_block_denominator_changed')
        env=dict(read(g.TEMPLATE),state='authorized',authorization=index['authority'],inputs={'batch':admission['prepared']},denylist=h.DENY,output_root=str(B/'diagnostic-envelopes'/('remaining98-prediction-v1-'+block['block']+'-'+bid)),supervisor_provenance={'script':ref(__file__),'index':index_ref,'policy':h.POLICY,'predecessor_gate':index['predecessor']});env.pop('example_only_requires_root_rebinding',None);w.validate(env);stages.append({'block':block['block'],'prepared':admission['prepared'],'jobs':block['jobs'],'max_calls':block['max_calls'],'allowed':allowed,'envelope':env})
    require(len(ids)==len(set(ids))==7,'remaining98_denominator_changed');admission_gate(current,baseline,datetime.now(timezone.utc));return w,index,policy,baseline,stages

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ready-index',nargs=2,required=True);ap.add_argument('--check',action='store_true');args=ap.parse_args();index_ref={'path':str(Path(args.ready_index[0]).resolve()),'sha256':args.ready_index[1]};w,index,policy,baseline,stages=preflight(index_ref)
    if args.check:print('Read-only remaining98 check passed: P7four/56 then P3three/42,26.589370USD,same80ledger, known ownswap28 gate; no calls,claims or writes.');return 0
    ROOT.mkdir(mode=0o700,parents=True,exist_ok=False);write(ROOT/'SUPERVISOR_CLAIM.json',{'schema_version':'remaining98-prediction-supervisor-claim-v1','script':ref(__file__),'index':index_ref,'authority':index['authority'],'policy':h.POLICY,'baseline':baseline,'ordered_blocks':['P7','P3'],'max_calls':98,'max_usd':h.TOTAL,'no_retry_or_followup':True})
    for stage in stages:stage['envelope_ref']=write(ROOT/('envelope-'+stage['block']+'.json'),stage['envelope'])
    verified=[];reason=None;expected_attempts=baseline['attempts'];expected_spent=baseline['spent']
    for n,stage in enumerate(stages):
        def launch():
            with (ROOT/(stage['block']+'-stdout.txt')).open('xb') as out,(ROOT/(stage['block']+'-stderr.txt')).open('xb') as err:
                return subprocess.run([sys.executable,'-B',g.WRAPPER['path'],'--envelope',stage['envelope_ref']['path'],'--envelope-sha256',stage['envelope_ref']['sha256']],env=dict(os.environ),stdin=subprocess.DEVNULL,stdout=out,stderr=err,check=False).returncode
        def verify():
            native=native_terminal(stage['prepared'],stage['jobs'],stage['max_calls']);diagnostics=g.diagnostic_terminal(stage['envelope_ref'],ref(Path(stage['envelope']['output_root'])/'envelope-terminal.json'),stage['allowed'],native['attempted_calls'])
            require(native['ledger_attempts']==expected_attempts+stage['max_calls'] and native['ledger_spent_nanos']==expected_spent+native['known_spent_nanos'],'remaining98_cumulative_ledger_mismatch')
            _,_,actual,_,confirmed=h.validate_authority(index['authority']);require(confirmed==baseline and actual['attempts']==native['ledger_attempts'] and actual['known_nanos']==native['ledger_spent_nanos'],'remaining98_actual_ledger_mismatch');return {'block':stage['block'],'native':native,'diagnostics':diagnostics,'baseline':baseline}
        try:
            _,_,actual,_,confirmed=h.validate_authority(index['authority'],initial=(n==0));require(confirmed==baseline,'remaining8_baseline_changed');admission_gate(actual,baseline,datetime.now(timezone.utc),expected_attempts=expected_attempts,expected_spent=expected_spent,remaining_blocks=2-n);require(not (ROOT/'STOP_ADMISSIONS').exists(),'coordinator_stopped_admissions');w.validate(stage['envelope']);write(ROOT/('started-'+stage['block']+'.json'),{'prepared':stage['prepared'],'envelope':stage['envelope_ref'],'started_at':w.now().isoformat()});result,reason=run_one(launch,verify)
            if reason is not None:break
            verified.append(write(ROOT/('verified-'+stage['block']+'.json'),result));expected_attempts=result['native']['ledger_attempts'];expected_spent=result['native']['ledger_spent_nanos']
        except Exception:reason='admission_or_child_launch_failed_inspect_existing_artifacts';break
    terminal={'schema_version':'remaining98-prediction-supervisor-terminal-v1','status':'complete' if reason is None and len(verified)==2 else 'stopped','stop_reason':reason,'index':index_ref,'script':ref(__file__),'baseline':baseline,'completed_verified_batches':verified,'known_verified_attempts':expected_attempts,'known_verified_spend_nanos':expected_spent,'planned_jobs':7,'planned_call_ceiling':98,'planned_dollar_ceiling':h.TOTAL,'child_process_terminal':True,'native_accounting_drain_verified':reason is None and len(verified)==2,'no_retry_or_followup':True,'planned_descendant_slots':112,'unavailable_descendant_slots':14,'completed_at':w.now().isoformat()};print(h.canonical(write(ROOT/'supervisor-terminal.json',terminal)));return 0 if terminal['status']=='complete' else 2
if __name__=='__main__':raise SystemExit(main())
