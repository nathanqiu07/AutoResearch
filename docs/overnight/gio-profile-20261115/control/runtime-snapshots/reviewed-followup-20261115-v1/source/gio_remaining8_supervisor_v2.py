"""Finite two-batch supervisor for exactly eight frozen P7/P3 extraction jobs.
Root executes after explicit authority; --check only reads and captures fake builder requests.
No prediction launch, method change, retry, repair, resume or ledger rotation.
"""
import argparse, importlib.util, json, os, subprocess, sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode=True
HELPER={'path':'/private/tmp/gio_prepare_remaining8_v2.py','sha256':'3147f75f847f683a348393edd627a6e25acbe026d213e896183e74ceca175186'}
GATES={'path':'/private/tmp/gio_profile204_supervisor_v1.py','sha256':'67d526c126ff58d88305fc2f4ccdd2ee0278cf3d55d784716c53507398a973aa'}
def load(name,source):
    import hashlib
    p=Path(source['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('dependency_pin_mismatch')
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('remaining8_helpers',HELPER);g=load('remaining8_terminal_helpers',GATES)
B=h.B;ROOT=B/'remaining8-build-supervisor-v2';read,ref,require,write=h.read,h.ref,h.require,g.write

def admission_gate(state,baseline,now,*,expected_attempts=None,expected_spent=None,remaining_blocks=2):
    h.h.budget_gate(state,Decimal('9.63453')*remaining_blocks);h.h.time_gate(now,480*remaining_blocks)
    require(remaining_blocks in (1,2),'invalid_remaining_block_count')
    require(state['attempts']==(baseline['attempts'] if expected_attempts is None else expected_attempts) and state['known_nanos']==(baseline['spent'] if expected_spent is None else expected_spent),'unexpected_shared_scaling_ledger_activity')

def check_build_result(packet,receipt,result):
    m=packet['manifest'];mh=h.digest(m);usage=receipt['usage'];status=receipt['status']
    require(receipt['job_id']==result['job_id']==m['job_id'] and receipt['manifest_sha256']==result['manifest_hash']==mh,'build_result_identity_mismatch')
    require(status==result['status'] and status in {'complete','invalid','empty','unsupported','unavailable','abstained'} and result['usage']==usage,'build_result_status_or_usage_mismatch')
    require(result['code_sha']==m['code_sha'] and result['config_hash']==m['config_hash'] and result['source_manifest_hash']==m['source_manifest_hash'] and result['actual_backend']==m['extractor'],'build_provenance_mismatch')
    require(result['predictions']==[] and result['counts']=={'attempted':1,'complete':int(status=='complete'),'error':int(status!='complete')},'build_count_mismatch')
    require(g.known_usage(usage,1)==1 and usage['cache_hits']==0,'extraction_must_be_one_fresh_known_call')
    return {'status':status,'attempted_calls':1,'known_spent_nanos':g.nanos(usage['reported_api_usd'])}

def native_terminal(prepared_ref):
    batch=read(prepared_ref);bid=batch['batch_id'];out=B/'receipts'/bid/'execution';summary_ref=ref(out/'summary.json');summary=read(summary_ref)
    require(summary['schema_version']=='overnight-batch-result-v1' and summary['batch_id']==bid and summary['status']=='complete' and summary['stop_reason'] is None,'native_remaining8_not_complete')
    c=summary['counts'];require(c['listed']==c['dispatched']==4 and c['not_dispatched']==0,'remaining8_incomplete_dispatch')
    ledger=summary['ledger'];require(ledger['inflight']==ledger['uncertain']==ledger['reserved_usd']==0 and ledger['held_after_uncertain'] is False and ledger['max_inflight']==2 and ledger['max_usd']==80,'remaining8_unresolved_accounting')
    sys.path.insert(0,str(h.R))
    from autoresearch.taste.overnight.contracts import ProfileArtifact
    rows=[];spent=0
    for packet_ref in batch['jobs']:
        p=read(packet_ref);m=p['manifest'];jid=m['job_id'];rr=ref(out/jid/'receipt.json');receipt=read(rr)
        require(receipt['schema_version']=='overnight-dispatch-receipt-v1' and receipt['result_path']==str(B/'output'/jid/'result.json'),'remaining8_receipt_path_mismatch')
        result_ref=ref(receipt['result_path']);result=read(result_ref);meta=check_build_result(p,receipt,result)
        claim_ref=ref(B/'lease'/(jid+'.json'));claim=read(claim_ref);require(claim['manifest']==m and claim['lease']==p['lease'] and claim['status']=='claimed','remaining8_claim_mismatch')
        profile_ref=None
        if 'profile' in result:
            profile_ref=ref(B/'output'/jid/'profile.json');body=read(profile_ref);require(body==result['profile'],'profile_file_result_mismatch');profile=ProfileArtifact.from_dict(body)
            require(profile.config==p['config'] and profile.profile_id==result['profile_hash'] and profile.status==result['status'] and profile.code_sha==h.COMMIT and profile.documents_hash==m['documents_hash'] and profile.allowed_source_manifest_hash==m['source_manifest_hash'] and profile.extractor==m['extractor'],'profile_provenance_mismatch')
        else:require(result['status']!='complete','complete_build_missing_profile')
        rows.append({'job_id':jid,'receipt':rr,'result':result_ref,'claim':claim_ref,'profile':profile_ref,**meta});spent+=meta['known_spent_nanos']
    require(c['complete']==sum(r['status']=='complete' for r in rows) and c['other']==sum(r['status']!='complete' for r in rows),'remaining8_summary_status_mismatch')
    return {'summary':summary_ref,'attempted_calls':4,'known_spent_nanos':spent,'ledger_attempts':ledger['attempts'],'ledger_spent_nanos':g.nanos(ledger['spent_usd']),'outcomes':rows}

def run_one(launch,verify):
    if launch()!=0:return None,'child_nonzero'
    try:return verify(),None
    except Exception:return None,'terminal_verification_failed'

def preflight(index_ref):
    index=read(index_ref);require(index['schema_version']=='remaining8-build-admission-index-v2' and index['state']=='prepared_not_executed' and index['script']==HELPER and index['jobs']==index['max_calls']==8 and Decimal(index['max_usd'])==Decimal(h.TOTAL) and index['future_prediction_jobs_admitted']==0,'exact_remaining8_index_required')
    auth,policy,current,_,baseline=h.validate_authority(index['authority'],initial=True)
    require(index['policy']==h.POLICY and index['proposal']==auth['proposal'] and index['predecessor']==auth['primary14_predecessor'] and index['baseline']==baseline and index['inventory']==h.INVENTORY and index['unknown_denylist']==h.DENY and index['automatic_followup'] is False,'remaining8_index_authority_mismatch')
    require(not ROOT.exists(),'fresh_remaining8_supervisor_root_required');proposal=read(index['proposal']);rows=h.capture_rows();blocks=h.batch_blocks(rows);require(rows==proposal['drafts'] and blocks==proposal['blocks'] and [a['block'] for a in index['admissions']]==['P7','P3'],'remaining8_blocks_changed')
    stages=[];ids=[];w=g.wrapper_module()
    for admission,block in zip(index['admissions'],blocks):
        batch=read(admission['prepared']);bid=batch['batch_id'];require(not (B/'receipts'/bid/'execution').exists(),'old_remaining8_batch_cannot_resume')
        require(admission['jobs']==admission['max_calls']==4 and Decimal(admission['max_usd'])==Decimal('9.63453') and admission['release_schema_version']==block['release_schema_version'] and batch['release_schema_version']==block['release_schema_version'] and batch['remaining8_block']==block['block'] and batch['remaining8_authority']==index['authority'] and batch['max_workers']==2 and batch['max_total_attempts']==4 and batch['ledger']==policy['ledger'] and batch['ledger_policy']==h.POLICY and batch['deadline']==h.DEADLINE and len(batch['jobs'])==4,'remaining8_homogeneous_batch_limits_mismatch')
        allowed={};cap=Decimal(0)
        for pr,row in zip(batch['jobs'],block['rows']):
            p=read(pr);expected=h.bind(read(row['packet']),index['authority']);normalized=dict(p)
            require(p['release']['sha256']==expected['release']['sha256'] and Path(p['release']['path']).read_bytes()==Path(expected['release']['path']).read_bytes(),'remaining8_source_bytes_changed');normalized['release']=expected['release'];require(normalized==expected,'remaining8_scientific_packet_changed');jid=p['manifest']['job_id'];ids.append(jid)
            require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'remaining8_job_already_started');request=row['request'];allowed[request['request_sha256']]=request['endpoint_body_sha256'];cap+=Decimal(str(p['backend']['max_usd']))
        require(len(allowed)==4 and cap==Decimal('9.63453'),'remaining8_block_denominator_changed')
        env=dict(read(g.TEMPLATE),state='authorized',authorization=index['authority'],inputs={'batch':admission['prepared']},denylist=h.DENY,output_root=str(B/'diagnostic-envelopes'/('remaining8-build-v2-'+block['block']+'-'+bid)),supervisor_provenance={'script':ref(__file__),'index':index_ref,'policy':h.POLICY,'predecessor_gate':index['predecessor']});env.pop('example_only_requires_root_rebinding',None);w.validate(env);stages.append({'block':block['block'],'prepared':admission['prepared'],'allowed':allowed,'envelope':env})
    require(len(ids)==len(set(ids))==8,'remaining8_denominator_changed');admission_gate(current,baseline,datetime.now(timezone.utc));return w,index,policy,baseline,stages

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ready-index',nargs=2,required=True);ap.add_argument('--check',action='store_true');args=ap.parse_args();index_ref={'path':str(Path(args.ready_index[0]).resolve()),'sha256':args.ready_index[1]};w,index,policy,baseline,stages=preflight(index_ref)
    if args.check:print('Read-only remaining8 v2 check passed: P7four then P3four homogeneous batches, eight calls maximum,19.26906USD,same80ledger; no calls,claims or writes.');return 0
    ROOT.mkdir(mode=0o700,parents=True,exist_ok=False);write(ROOT/'SUPERVISOR_CLAIM.json',{'schema_version':'remaining8-build-supervisor-claim-v2','script':ref(__file__),'index':index_ref,'authority':index['authority'],'policy':h.POLICY,'baseline':baseline,'ordered_blocks':['P7','P3'],'max_calls':8,'max_usd':h.TOTAL,'no_retry_or_followup':True})
    for stage in stages:stage['envelope_ref']=write(ROOT/('envelope-'+stage['block']+'.json'),stage['envelope'])
    verified=[];reason=None;expected_attempts=baseline['attempts'];expected_spent=baseline['spent']
    for n,stage in enumerate(stages):
        def launch():
            with (ROOT/(stage['block']+'-stdout.txt')).open('xb') as out,(ROOT/(stage['block']+'-stderr.txt')).open('xb') as err:
                return subprocess.run([sys.executable,'-B',g.WRAPPER['path'],'--envelope',stage['envelope_ref']['path'],'--envelope-sha256',stage['envelope_ref']['sha256']],env=dict(os.environ),stdin=subprocess.DEVNULL,stdout=out,stderr=err,check=False).returncode
        def verify():
            native=native_terminal(stage['prepared']);diagnostics=g.diagnostic_terminal(stage['envelope_ref'],ref(Path(stage['envelope']['output_root'])/'envelope-terminal.json'),stage['allowed'],native['attempted_calls'])
            require(native['ledger_attempts']==expected_attempts+4 and native['ledger_spent_nanos']==expected_spent+native['known_spent_nanos'],'remaining8_cumulative_ledger_mismatch')
            _,_,actual,_,confirmed=h.validate_authority(index['authority']);require(confirmed==baseline and actual['attempts']==native['ledger_attempts'] and actual['known_nanos']==native['ledger_spent_nanos'],'remaining8_actual_ledger_mismatch');return {'block':stage['block'],'native':native,'diagnostics':diagnostics,'baseline':baseline}
        try:
            _,_,actual,_,confirmed=h.validate_authority(index['authority'],initial=(n==0));require(confirmed==baseline,'primary14_baseline_changed');admission_gate(actual,baseline,datetime.now(timezone.utc),expected_attempts=expected_attempts,expected_spent=expected_spent,remaining_blocks=2-n);require(not (ROOT/'STOP_ADMISSIONS').exists(),'coordinator_stopped_admissions');w.validate(stage['envelope']);write(ROOT/('started-'+stage['block']+'.json'),{'prepared':stage['prepared'],'envelope':stage['envelope_ref'],'started_at':w.now().isoformat()});result,reason=run_one(launch,verify)
            if reason is not None:break
            verified.append(write(ROOT/('verified-'+stage['block']+'.json'),result));expected_attempts=result['native']['ledger_attempts'];expected_spent=result['native']['ledger_spent_nanos']
        except Exception:reason='admission_or_child_launch_failed_inspect_existing_artifacts';break
    terminal={'schema_version':'remaining8-build-supervisor-terminal-v2','status':'complete' if reason is None and len(verified)==2 else 'stopped','stop_reason':reason,'index':index_ref,'script':ref(__file__),'baseline':baseline,'completed_verified_batches':verified,'known_verified_attempts':expected_attempts,'known_verified_spend_nanos':expected_spent,'planned_jobs':8,'planned_call_ceiling':8,'planned_dollar_ceiling':h.TOTAL,'child_process_terminal':True,'native_accounting_drain_verified':reason is None and len(verified)==2,'no_retry_or_followup':True,'future_prediction_jobs_admitted':0,'completed_at':w.now().isoformat()};print(h.canonical(write(ROOT/'supervisor-terminal.json',terminal)));return 0 if terminal['status']=='complete' else 2
if __name__=='__main__':raise SystemExit(main())
