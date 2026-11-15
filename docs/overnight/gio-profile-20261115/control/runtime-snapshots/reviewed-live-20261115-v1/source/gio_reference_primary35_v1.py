#!/usr/bin/env python3
"""Offline-proposed finite PRIMARY continuation: exact35, no new allocation or retry.
Reuses the hash-pinned v2 terminal-first scheduler. Root supplies credentials and
an explicit new inspection receipt after BOTH newmethods jobs are known terminal.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE=Path('/private/tmp/gio-profile-20261115-coordinator')
OUT=BASE/'reference-primary35-continuation-v1'
NEWMETHODS=BASE/'reference-newmethods-inspected-v1'
INPUT=Path('/private/tmp/gio_reference_primary35_input_v1.json')
INPUT_SHA='e45c979699ab7e320322229e5df4faeef0d8a88379543a2cdfbf9bb2ff927110'
SCHEDULER=Path('/Users/giordanorogers/.codex/worktrees/gio-overnight-infrastructure/AutoResearch-overnight-control/docs/overnight/gio-profile-20261115/handoffs/01/reference_supervisor_v2.py')
SCHEDULER_SHA='74127010f1725ca19a08f03090cdd79879093159f75f43372f588d3cc679ffb1'
NM_HELPER=Path('/private/tmp/gio_launch_reference_inspected_v1.py')
NM_HELPER_SHA='a0cb3a4d98ef54f4b3305b14b87d6c247918aca344609f8a2e62f1d313a06c53'
NM_TERMINAL_SHA='85f39cd051ab2baa7f123bbced4ebfdc85a0a63a9ba0b968e0c8cb1a246b903b'
NM_INSPECTION_SHA='b5287cde7f2c87a2d410bc50d8baa104e91ebb5b96a61cf902e807d4af224c8c'
LATEST=datetime(2026,11,15,16,44,tzinfo=timezone.utc)

def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path, expected, name):
    if sha(path)!=expected:raise ValueError('dependency_pin_changed')
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

v2=load(SCHEDULER,SCHEDULER_SHA,'reviewed_v2_scheduler')
write,read_ref=v2.write,v2.read_ref

def receipt_template(script_sha):
    return {'schema_version':'reference-primary35-inspection-v1','status':'proposed_not_authorized',
        'inspected_by':None,'inspected_at':None,'script_sha256':script_sha,'input_index_sha256':INPUT_SHA,
        'incident_sha256':'f12554304847572521bfee9ed352eabfe5d89863692c60b220c2d655761e8bdf',
        'newmethods_terminal':{'path':str(NEWMETHODS/'supervisor-terminal.json'),'sha256':NM_TERMINAL_SHA},'newmethods_successfully_terminal':True,
        'no_other_reference_dispatcher_or_process':True,'reference_lane_exclusive':True,
        'primary_reserved_usd':'44.90','newmethods_reserved_usd':'2.00','aggregate_reference_reserved_usd':'46.90',
        'new_allocation_usd':'0.00','release_prior_holds':False,'historical_unknown_total':3,
        'historical_primary_v2_unknown':2,'historical_original_user949_unknown':1,
        'allow_retry_or_resume':False,'exact_primary_job_count':35,'initial_pair_sequential':True,
        'max_concurrent':2,'stop_after_first_additional_unknown_or_invalid_accounting':True,
        'latest_launch':'2026-11-15T16:44:00Z','deadline':'2026-11-15T17:00:00Z','output_root':str(OUT)}

def validate_receipt(receipt,script_sha,now):
    if now.tzinfo is None or now>=LATEST:raise ValueError('latest_launch_or_naive_clock')
    expected=receipt_template(script_sha);expected.update(status='authorized',inspected_by='root')
    for k,v in expected.items():
        if k in ['inspected_at','newmethods_terminal']:continue
        if receipt.get(k)!=v or type(receipt.get(k)) is not type(v):raise ValueError('inspection_mismatch:'+k)
    at=datetime.fromisoformat(receipt['inspected_at'].replace('Z','+00:00'))
    if at.tzinfo is None or at>now:raise ValueError('inspection_time_invalid')
    ref=receipt.get('newmethods_terminal')
    if (not isinstance(ref,dict) or set(ref)!={'path','sha256'} or
        ref['path']!=str(NEWMETHODS/'supervisor-terminal.json') or ref['sha256']!=NM_TERMINAL_SHA):
        raise ValueError('exact_newmethods_terminal_required')

def verify_newmethods(receipt):
    terminal=read_ref(receipt['newmethods_terminal'])
    helper=load(NM_HELPER,NM_HELPER_SHA,'reviewed_newmethods_terminal_guard')
    index=helper.pinned(helper.INDEX,helper.INDEX_SHA)
    claim=json.loads((NEWMETHODS/'SUPERVISOR_CLAIM.json').read_text())
    if (claim['script_sha256']!=NM_HELPER_SHA or claim['inspection_sha256']!=NM_INSPECTION_SHA or
        terminal['status']!='complete' or terminal['no_retry'] is not True or
        terminal['all_reservations_retained_usd']!='46.90' or
        [r['job_id'] for r in terminal['outcomes']]!=helper.JOB_IDS):
        raise ValueError('newmethods_not_both_successfully_terminal')
    helper.pinned(claim['inspection_path'],NM_INSPECTION_SHA)
    finished=datetime.fromisoformat(terminal['completed_at'])
    inspected=datetime.fromisoformat(receipt['inspected_at'].replace('Z','+00:00'))
    if finished.tzinfo is None or inspected<finished:raise ValueError('inspection_predates_newmethods_completion')
    for row,outcome in zip(index['jobs'],terminal['outcomes']):
        expected=helper.inspect_terminal(row,0)
        actual=json.loads((NEWMETHODS/(row['job_id']+'-terminal.json')).read_text())
        if outcome!=expected or actual!=expected:raise ValueError('newmethods_terminal_evidence_changed')

def verify_runtime(index):
    runtime=Path(index['runtime_root'])
    if (index['runtime_commit']!=v2.RUNTIME_COMMIT or
        subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True).strip()!=v2.RUNTIME_COMMIT or
        subprocess.check_output(['git','-C',str(runtime),'status','--porcelain','--untracked-files=no'],text=True).strip()):
        raise ValueError('runtime_not_frozen')
    plan=read_ref({'path':index['jobs'][0]['plan_path'],'sha256':index['jobs'][0]['plan_sha256']})
    identity=plan['runtime']
    if identity['commit']!=v2.RUNTIME_COMMIT or identity['python']!=list(sys.version_info[:3]):raise ValueError('runtime_python_mismatch')
    for name,expected in identity['files'].items():
        if sha(runtime/name)!=expected:raise ValueError('runtime_file_changed')

def verify_row(row):
    lease=read_ref({'path':row['path'],'sha256':row['sha256']})
    plan=read_ref({'path':row['plan_path'],'sha256':row['plan_sha256']})
    expected={'job_id':row['job_id'],'claim_path':row['claim_path'],'plan_sha256':row['plan_sha256'],
        'state':'authorized','role':'10','provider':'openai','model':'gpt-6-luna','methods':['m0','m1','m2','m3'],
        'max_usd':.7,'max_seconds':900,'max_calls':row['max_calls'],'deadline':v2.DEADLINE,'user_partition':'dev','final_authorized':False}
    if any(lease.get(k)!=v for k,v in expected.items()):raise ValueError('lease_changed')
    if plan['worst_case_backend_calls']!=row['max_calls'] or plan['user_ids']!=[row['user_id']]:raise ValueError('plan_changed')
    packet=Path(row['plan_path']).parent
    for p in [Path(row['claim_path'])]+[packet/n for n in ['LAUNCH_USED.json','output','completion.json','launcher.log','cache']]:
        if p.exists():raise ValueError('already_claimed_or_started')
    for name,expected in plan['snapshots'].items():
        if sha(packet/name)!=expected:raise ValueError('packet_snapshot_changed')

def artifact_preflight():
    index=read_ref({'path':str(INPUT),'sha256':INPUT_SHA})
    incident=read_ref(index['incident']);proof=read_ref(index['neverstarted_proof']);issued=read_ref(index['issued_index'])
    for ref in proof['source_files'].values():read_ref(ref)
    rows=index['jobs'];original={r['job_id']:r for r in issued['leases']}
    if len(rows)!=35 or [r['job_id'] for r in rows]!=[r['job_id'] for r in proof['neverstarted_primary_jobs_in_frozen_order']]:raise ValueError('exact35_required')
    if any(r!=original[r['job_id']] for r in rows):raise ValueError('issued_row_changed')
    if index['first_pair_job_ids']!=[r['job_id'] for r in incident['bounded_next_primary']['jobs']] or sum(r['max_calls'] for r in rows[:2])!=240:raise ValueError('first_pair_changed')
    if len(set(r['job_id'] for r in rows))!=35 or any(r['user_id']=='prism:user949' for r in rows):raise ValueError('duplicate_or_forbidden_user')
    if sum(r['max_calls'] for r in rows)!=6215:raise ValueError('call_bound_changed')
    verify_runtime(index)
    for row in rows:verify_row(row)
    if OUT.exists():raise ValueError('fresh_supervisor_root_required')
    return index

class ContinuationSupervisor(v2.Supervisor):
    def __init__(self,rows,run,launch,*,guard,now=None):
        super().__init__(rows,run,launch,prior_unknown=3,now=now)
        self.guard=guard
    def gates(self):
        if self.unknown>3:self.stop='first_additional_unknown_inspection_required'
        elif self.stop is None:
            if (self.run.parent/'STOP_ADMISSIONS').exists():self.stop='coordinator_stop_admissions'
            elif self.now()>=LATEST:self.stop='latest_packet_start_reached'
    def capacity(self):
        return 1 if self.next_index<2 or len(self.completed)<2 else 2
    def step(self):
        self.poll()  # Reviewed v2 observes terminal children before every admission.
        while self.stop is None and len(self.active)<self.capacity() and self.next_index<len(self.rows):
            self.poll()
            if self.stop is not None:break
            row=self.rows[self.next_index];packet=Path(row['plan_path']).parent
            if any(p.exists() for p in [Path(row['claim_path'])]+[packet/n for n in ['LAUNCH_USED.json','output','completion.json']]):
                self.stop='claim_or_launch_marker_appeared';break
            if sha(row['path'])!=row['sha256'] or sha(row['plan_path'])!=row['plan_sha256']:
                self.stop='packet_identity_changed';break
            try:self.guard(row)
            except Exception:self.stop='current_inspection_or_artifact_guard_failed';break
            self.poll()  # Re-observe exits after potentially slow hash/inspection checks.
            if self.stop is not None:break
            write(self.run/(row['job_id']+'-admitted.json'),{'job_id':row['job_id'],'lease_sha256':row['sha256'],'plan_sha256':row['plan_sha256'],'admitted_at':self.now().isoformat()})
            self.next_index+=1
            self.gates()
            if self.stop is not None:break
            log=(self.run/(row['job_id']+'.log')).open('x')
            try:process=self.launch(row,log)
            except Exception:
                log.close();self.unknown+=1;self.stop='launch_failure_inspection_required';break
            self.active[process.pid]=(process,log,row)
            write(self.run/(row['job_id']+'-started.json'),{'job_id':row['job_id'],'pid':process.pid,'started_at':self.now().isoformat()})

def main():
    ap=argparse.ArgumentParser(description=__doc__);mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-artifacts',action='store_true');mode.add_argument('--execute',action='store_true')
    ap.add_argument('--inspection');ap.add_argument('--inspection-sha256');args=ap.parse_args()
    index=artifact_preflight()
    if args.check_artifacts:
        print(json.dumps({'status':'offline_artifacts_passed_no_authority_or_claim','primary_jobs':35,'initial_pair_calls':240,'remaining33_calls':5975,'total_calls':6215,'newmethods_terminal_present':(NEWMETHODS/'supervisor-terminal.json').exists()}));return
    if not args.inspection or not args.inspection_sha256:raise ValueError('new_pinned_root_inspection_required')
    def approval():
        receipt=read_ref({'path':args.inspection,'sha256':args.inspection_sha256})
        validate_receipt(receipt,sha(__file__),datetime.now(timezone.utc));verify_newmethods(receipt)
        return receipt
    receipt=approval()
    if not os.environ.get('OPENAI_API_KEY'):raise ValueError('credential_environment_required')
    OUT.mkdir(mode=0o700)
    write(OUT/'SUPERVISOR_CLAIM.json',{'input_index_sha256':INPUT_SHA,'script_sha256':sha(__file__),
        'inspection':{'path':args.inspection,'sha256':args.inspection_sha256},'newmethods_terminal':receipt['newmethods_terminal'],
        'historical_unknowns':index['historical_unknowns'],'exact_primary_jobs':35,'first_pair_sequential':True,
        'max_concurrent_after_pair':2,'all_primary_reservations_retained_usd':'44.90','aggregate_reference_reserved_usd':'46.90','no_retry':True})
    run=OUT/'execution';run.mkdir();environment=dict(os.environ);environment['PYTHONDONTWRITEBYTECODE']='1'
    def guard(row):approval();verify_runtime(index);verify_row(row)
    def launch(row,log):
        if datetime.now(timezone.utc)>=LATEST or (OUT/'STOP_ADMISSIONS').exists():raise ValueError('admission_deadline_or_stop')
        return subprocess.Popen([sys.executable,'scripts/overnight_labeled_reference.py','run','--plan',row['plan_path'],'--lease',row['path']],cwd=index['runtime_root'],env=environment,stdout=log,stderr=log)
    supervisor=ContinuationSupervisor(index['jobs'],run,launch,guard=guard)
    try:
        while supervisor.active or supervisor.next_index<len(index['jobs']):
            supervisor.step()
            if supervisor.stop and not supervisor.active:break
            if supervisor.active:time.sleep(5)
    except BaseException:
        supervisor.stop='supervisor_interrupted_no_more_admissions'
        while supervisor.active:
            supervisor.poll()
            if supervisor.active:time.sleep(5)
    write(OUT/'supervisor-terminal.json',{'status':'stopped' if supervisor.stop else 'complete','reason':supervisor.stop,
        'input_index_sha256':INPUT_SHA,'attempted_packets':supervisor.next_index,'unattempted_packets':35-supervisor.next_index,
        'completed':supervisor.completed,'historical_unknowns':index['historical_unknowns'],
        'additional_unknown_packets':supervisor.unknown-3,'total_historical_and_new_unknown':supervisor.unknown,
        'all_tranches_still_reserved':True,'primary_reserved_usd':'44.90','aggregate_reference_reserved_usd':'46.90','no_retry':True})
    print(json.dumps({'status':'stopped' if supervisor.stop else 'complete','attempted_packets':supervisor.next_index,'additional_unknown':supervisor.unknown-3}))

if __name__=='__main__':main()
