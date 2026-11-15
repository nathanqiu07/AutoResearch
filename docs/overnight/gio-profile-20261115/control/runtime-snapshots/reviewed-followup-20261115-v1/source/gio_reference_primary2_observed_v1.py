#!/usr/bin/env python3
"""Finite two-job continuation of untouched original leases. Coordinator inspection is required to execute.
Reuses reviewed terminal-first scheduler over unchanged63 runtime, observed externally.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
import hashlib

BASE=Path('/private/tmp/gio-profile-20261115-coordinator')
OUT=BASE/'reference-primary2-observed-v1'
DIAGNOSTICS=BASE/'diagnostic-envelopes/reference2-observed-v1'
PRIOR_LAUNCHER=Path('/private/tmp/gio_reference_primary35_v1.py')
PRIOR_LAUNCHER_SHA='7b5d8c4f23145c3ed61fa65feec235ca972c76605ae7ca14ac456205f89805b2'
QUEUE={'path': '/private/tmp/gio-profile-20261115-reference/two-untouched-continuation-v1/queue.json', 'sha256': '983f5561aae0f42fbb34cd155ed171b5742c220ebb062e147d83dd7d9d633e5e'}
PROOF={'path': '/private/tmp/gio-profile-20261115-reference/incidents/observed31-stop-1329-v1/incident-handoff.json', 'sha256': 'fd7163a0032bcf79434587d921d111991ff9b617d9ba7a5e5b956a98555212dd'}
OLD_TERMINAL={'path': '/private/tmp/gio-profile-20261115-coordinator/reference-primary31-observed-v1/supervisor-terminal.json', 'sha256': '7bb0b12ee3f00ad22d44a2b145c3033ea6d8e7448fd0d29528fe0a8500a65c38'}
WRAPPER={'path':'/private/tmp/gio_diagnostic_runtime_envelope_v2.py','sha256':'8e3a2f460254c3295f36c0d07a323bb1ccdafafad4ac11425cd3963a09b8d2b5'}
OBSERVER={'path':'/private/tmp/gio_provider_diagnostics_v3.py','sha256':'d2f3372e2689adf7bdef74fc6170fa25eca7bce4b4aa3de98b495633bf284233'}
DENY={'path':'/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json','sha256':'7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'}
LEGACY_DENY={'path':'/private/tmp/gio-profile-incident-1154-review-v1/combined-provider-unknown-denylist.json','sha256':'8804a408fd50f1617f4a4004b05d7a6453fc94b16b30e7fca061d6548d977750'}
GUARD_REPLAY={'path':'/private/tmp/gio-reference31-exact-deny-verification-v1/verification-receipt.json','sha256':'5cf8244a73b5fd2cc9c0fbc53d6605cf0f282fa09980ee1b977e44130202d83b'}
LATEST=datetime(2026,11,15,16,44,tzinfo=timezone.utc)
DEADLINE='2026-11-15T17:00:00Z'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(ref,name):
    if sha(ref['path'])!=ref['sha256']:raise ValueError('reviewed_dependency_changed')
    spec=importlib.util.spec_from_file_location(name,ref['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
prior=load({'path':str(PRIOR_LAUNCHER),'sha256':PRIOR_LAUNCHER_SHA},'reviewed_primary35')
write,read_ref=prior.write,prior.read_ref

def observer_runtime():return load(WRAPPER,'reviewed_observed_runtime')
def make_envelope(index,row,authorization=None):
    return {'schema_version':'diagnostic-runtime-envelope-v2','script_sha256':WRAPPER['sha256'],
        'state':'authorized' if authorization else 'proposed_not_authorized','observer':OBSERVER,
        'deadline':DEADLINE,'denylist':DENY,'authorization':authorization,'kind':'reference',
        'runtime_root':index['runtime_root'],'runtime_commit':index['runtime_identity']['commit'],
        'entrypoint':'scripts/overnight_labeled_reference.py','runtime_files':index['runtime_identity']['files'],
        'inputs':{'plan':{'path':row['plan_path'],'sha256':row['plan_sha256']},'lease':{'path':row['path'],'sha256':row['sha256']}},
        'output_root':str(DIAGNOSTICS/row['job_id'])}

def verify_dependencies():
    wrapper=observer_runtime()
    if sha(OBSERVER['path'])!=OBSERVER['sha256']:raise ValueError('observer_changed')
    denied=read_ref(DENY);read_ref(GUARD_REPLAY)
    if denied['schema_version']!='provider-unknown-wire-denylist-v2':raise ValueError('typed_denylist_required')
    typed=denied['identity_denylists']
    if (set(typed)!={'body_compact_json_sha256','endpoint_body_sorted_json_sha256'} or
        len(typed['body_compact_json_sha256'])!=6 or len(typed['endpoint_body_sorted_json_sha256'])!=7 or
        not wrapper.PROFILE<=set(typed['body_compact_json_sha256']) or not wrapper.REFERENCE<=set(typed['endpoint_body_sorted_json_sha256'])):raise ValueError('expanded_guard_changed')
    return wrapper

def rows_for(index):
    proof=read_ref(PROOF);rows=index['jobs']
    if len(rows)!=2 or [r['job_id'] for r in rows]!=[r['job_id'] for r in proof['untouched']]:raise ValueError('exact_two_untouched_required')
    for row,original in zip(rows,proof['untouched']):
        if (row['path']!=original['lease']['path'] or row['sha256']!=original['lease']['sha256'] or
            row['plan_path']!=original['plan']['path'] or row['plan_sha256']!=original['plan']['sha256'] or
            row['claim_path']!=original['claim_path'] or row['user_id']!=original['user_id']):raise ValueError('original_lease_or_plan_changed')
    if sum(r['max_calls'] for r in rows)!=449:raise ValueError('call_bound_changed')
    return rows

def artifact_preflight():
    index=read_ref(QUEUE);proof=read_ref(PROOF);old=read_ref(OLD_TERMINAL)
    if (old['status']!='stopped' or old['attempted_packets']!=29 or old['unattempted_packets']!=2 or
        old['total_historical_and_new_unknown']!=7 or old['aggregate_reference_reserved_usd']!='46.90' or
        old['all_tranches_still_reserved'] is not True or len(old['completed'])!=29):raise ValueError('stopped_drained_predecessor_changed')
    predecessor=Path(OLD_TERMINAL['path']).parent
    for row in old['completed']:
        if row!=json.loads((predecessor/'execution'/(row['job_id']+'-terminal.json')).read_text()):raise ValueError('predecessor_terminal_record_changed')
    rows=rows_for(index)
    prior.verify_runtime({'runtime_root':index['runtime_root'],'runtime_commit':index['runtime_identity']['commit'],'jobs':rows})
    wrapper=verify_dependencies()
    for row in rows:
        prior.verify_row(row)
        wrapper.validate(make_envelope(index,row),check_only=True)
    if OUT.exists() or DIAGNOSTICS.exists():raise ValueError('fresh_queue_and_diagnostics_roots_required')
    return index,rows

def receipt_template(script_sha):
    return {'schema_version':'reference-primary2-observed-inspection-v1','status':'proposed_not_authorized',
        'inspected_by':None,'inspected_at':None,'script_sha256':script_sha,'queue':QUEUE,'proof':PROOF,
        'prior_terminal':OLD_TERMINAL,'observed_wrapper':WRAPPER,'observer':OBSERVER,'typed_denylist':DENY,
        'original_denylist':LEGACY_DENY,'actual_request_guard_verification':GUARD_REPLAY,'exact_primary_jobs':2,'max_calls':449,
        'primary_reserved_usd':'44.90','aggregate_reference_reserved_usd':'46.90','new_allocation_usd':'0.00',
        'release_prior_holds':False,'historical_unknown_total':7,'allow_retry_or_resume':False,
        'initial_pair_sequential':True,'max_concurrent':2,'stop_after_first_additional_unknown_or_invalid_accounting':True,
        'stop_on_diagnostic_failure_or_denial':True,'no_other_reference_dispatcher_or_process':True,
        'latest_launch':'2026-11-15T16:44:00Z','deadline':DEADLINE,'output_root':str(OUT),'diagnostics_root':str(DIAGNOSTICS)}

def validate_receipt(receipt,script_sha,now):
    if now.tzinfo is None or now>=LATEST:raise ValueError('latest_launch_or_naive_clock')
    expected=receipt_template(script_sha);expected.update(status='authorized',inspected_by='root')
    for k,v in expected.items():
        if k=='inspected_at':continue
        if receipt.get(k)!=v or type(receipt.get(k)) is not type(v):raise ValueError('inspection_mismatch:'+k)
    at=datetime.fromisoformat(receipt['inspected_at'].replace('Z','+00:00'))
    if at.tzinfo is None or at>now:raise ValueError('invalid_inspection_time')

def verify_observed_terminal(envelope):
    wrapper=observer_runtime();root=Path(envelope['output_root'])
    claim=json.loads((root/'ENVELOPE_CLAIM.json').read_text());terminal=json.loads((root/'envelope-terminal.json').read_text())
    identity=wrapper.digest(envelope)
    if (claim['canonical_envelope_sha256']!=identity or claim['wrapper_script_sha256']!=WRAPPER['sha256'] or claim['envelope']!=envelope or
        terminal['canonical_envelope_sha256']!=identity or terminal['wrapper_script_sha256']!=WRAPPER['sha256'] or
        terminal['scientific_runtime_commit']!=envelope['runtime_commit'] or terminal['observer_sha256']!=OBSERVER['sha256'] or
        terminal['status']!='complete' or terminal['entry_exit_code']!=0 or terminal['wrapper_exit_code']!=0 or
        terminal['no_retry_or_resume'] is not True):raise ValueError('observed_terminal_binding_or_status')
    diagnostics=terminal['diagnostics']
    if (diagnostics.get('diagnostic_write_failed') is not False or diagnostics.get('dropped_event_count')!=0 or
        diagnostics.get('diagnostic_close_failed') is not False or diagnostics.get('diagnostic_hash_failed',False) is not False):raise ValueError('diagnostic_failure')
    events=root/'events.jsonl'
    if terminal['events_sha256']!=sha(events):raise ValueError('diagnostic_events_changed')
    rows=[json.loads(line) for line in events.read_text().splitlines()]
    if len(rows)!=terminal['event_count'] or [r['sequence'] for r in rows]!=list(range(len(rows))):raise ValueError('diagnostic_event_count_or_order')
    if any(r['stage']=='denied_before_transport' for r in rows):raise ValueError('historical_request_denied')
    return {'canonical_envelope_sha256':identity,'terminal_sha256':sha(root/'envelope-terminal.json'),'events_sha256':sha(events),'event_count':len(rows)}

class ObservedProcess:
    def __init__(self,process,envelope,receipt):self.process,self.envelope,self.receipt=process,envelope,receipt;self.pid=process.pid;self.checked=False;self.result=None
    def poll(self):
        if self.checked:return self.result
        rc=self.process.poll()
        if rc is None:return None
        result={'actual_wrapper_returncode':rc,'observed_terminal_valid':False}
        try:result.update(verify_observed_terminal(self.envelope),observed_terminal_valid=True);self.result=rc
        except Exception:result['reason']='missing_invalid_or_failed_diagnostics';self.result=rc or 2
        try:write(self.receipt,result)
        except Exception:self.result=rc or 2  # Stop admissions while still allowing scheduler drain.
        self.checked=True
        return self.result

class ContinuationSupervisor(prior.ContinuationSupervisor):
    def __init__(self,rows,run,launch,*,guard,now=None):
        prior.v2.Supervisor.__init__(self,rows,run,launch,prior_unknown=7,now=now);self.guard=guard
    def gates(self):
        if self.unknown>7:self.stop='first_additional_unknown_inspection_required'
        elif self.stop is None:
            if (self.run.parent/'STOP_ADMISSIONS').exists():self.stop='coordinator_stop_admissions'
            elif self.now()>=LATEST:self.stop='latest_packet_start_reached'

def main():
    ap=argparse.ArgumentParser(description=__doc__);mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-artifacts',action='store_true');mode.add_argument('--execute',action='store_true')
    ap.add_argument('--inspection');ap.add_argument('--inspection-sha256');a=ap.parse_args()
    index,rows=artifact_preflight()
    if a.check_artifacts:print(json.dumps({'status':'offline_passed_no_authority_or_claim','jobs':2,'max_calls':449,'first_pair_sequential':True,'max_concurrent':2}));return
    if not a.inspection or not a.inspection_sha256:raise ValueError('explicit_root_inspection_required')
    authorization={'path':a.inspection,'sha256':a.inspection_sha256}
    def approval():
        r=read_ref(authorization);validate_receipt(r,sha(__file__),datetime.now(timezone.utc));return r
    approval()
    if not os.environ.get('OPENAI_API_KEY'):raise ValueError('credential_environment_required')
    OUT.mkdir(mode=0o700);run=OUT/'execution';run.mkdir();envelopes=OUT/'envelopes';envelopes.mkdir()
    write(OUT/'SUPERVISOR_CLAIM.json',{'script_sha256':sha(__file__),'queue':QUEUE,'proof':PROOF,'inspection':authorization,
        'observer':OBSERVER,'wrapper':WRAPPER,'denylist':DENY,'historical_unknowns':7,'no_retry':True,
        'first_pair_sequential':True,'max_concurrent':2,'aggregate_reference_reserved_usd':'46.90'})
    environment=dict(os.environ);environment['PYTHONDONTWRITEBYTECODE']='1'
    def guard(row):
        approval();verify_dependencies();prior.verify_runtime({'runtime_root':index['runtime_root'],'runtime_commit':index['runtime_identity']['commit'],'jobs':[row]});prior.verify_row(row)
        observer_runtime().validate(make_envelope(index,row,authorization))
    def launch(row,log):
        if datetime.now(timezone.utc)>=LATEST or (OUT/'STOP_ADMISSIONS').exists():raise ValueError('stop_or_admission_deadline')
        envelope=make_envelope(index,row,authorization);path=envelopes/(row['job_id']+'.json');write(path,envelope)
        process=subprocess.Popen([sys.executable,WRAPPER['path'],'--envelope',str(path),'--envelope-sha256',sha(path)],cwd=index['runtime_root'],env=environment,stdout=log,stderr=log)
        return ObservedProcess(process,envelope,run/(row['job_id']+'-diagnostics-verified.json'))
    supervisor=ContinuationSupervisor(rows,run,launch,guard=guard)
    try:
        while supervisor.active or supervisor.next_index<len(rows):
            supervisor.step()
            if supervisor.stop and not supervisor.active:break
            if supervisor.active:time.sleep(5)
    except BaseException:
        supervisor.stop='supervisor_interrupted_no_more_admissions'
        while supervisor.active:
            supervisor.poll()
            if supervisor.active:time.sleep(5)
    write(OUT/'supervisor-terminal.json',{'status':'stopped' if supervisor.stop else 'complete','reason':supervisor.stop,
        'queue':QUEUE,'attempted_packets':supervisor.next_index,'unattempted_packets':2-supervisor.next_index,
        'completed':supervisor.completed,'historical_unknowns':7,'additional_unknown_packets':supervisor.unknown-7,
        'total_historical_and_new_unknown':supervisor.unknown,'all_tranches_still_reserved':True,
        'primary_reserved_usd':'44.90','aggregate_reference_reserved_usd':'46.90','no_retry':True})
    print(json.dumps({'status':'stopped' if supervisor.stop else 'complete','attempted_packets':supervisor.next_index,'additional_unknown':supervisor.unknown-7}))
if __name__=='__main__':main()
