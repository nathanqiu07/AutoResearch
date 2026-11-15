#!/usr/bin/env python3
"""Finite original-eight additive-inspection adapter; coordinator-reviewed dispatch only, no retries.

Reuse the reviewed reference31 observation and terminal-first admission machinery.
Only per-packet accounting, first8 input validation and the final denominator differ.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal

PREVIOUS={'path':'/private/tmp/gio_reference_primary31_observed_v1.py','sha256':'a3939689b396e03fae1cf660e6e9eb5f913745a0fa92aa3fc4ca6cd2181f2137'}
RUNTIME='/Users/giordanorogers/.codex/worktrees/gio-reference-original-eight/AutoResearch-overnight-control'
COMMIT='3de7299e533204642b11f1345975e786534b5367'
SCRIPT_SHA='e08f3cfa05054b4db211ef6d3c5ee7590a2209af6e41b8b09759d344003aa7f2'
PREPARED_PATH='/private/tmp/gio-profile-20261115-reference/original-first8-methods-runtime-3de7299/prepared-index.json'
PREPARED_SHA='55791bc3636dd1c38c6267fab947edb580578d6fd742ded01f1d48290dc8ae43'
OUT=Path('/private/tmp/gio-profile-20261115-coordinator/reference-original-first8-observed-v4')
DIAGNOSTICS=Path('/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/reference-original-first8-observed-v4')
PRIMARY=Path('/private/tmp/gio-profile-20261115-coordinator/reference-primary31-observed-v1')
INCIDENT={'path':'/private/tmp/gio-profile-20261115-reference/incidents/observed31-stop-1329-v1/incident-handoff.json','sha256':'fd7163a0032bcf79434587d921d111991ff9b617d9ba7a5e5b956a98555212dd'}
STOPPED={'path':str(PRIMARY/'supervisor-terminal.json'),'sha256':'7bb0b12ee3f00ad22d44a2b145c3033ea6d8e7448fd0d29528fe0a8500a65c38'}
PREDECESSOR_ADAPTER={'path':'/private/tmp/gio_reference_first8_observed_v1.py','sha256':'96ccc5a8e90075deee2f324933c4992f249305083cf5f22ef50dc98ca48ba3ac'}
EXPANDED={'path':'/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json','sha256':'7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'}
APPROVED_WRAPPER={'path':'/private/tmp/gio_diagnostic_runtime_envelope_first8_v1.py','sha256':'a4d654709439ec85c776e2281a352ab163d24edbe0e613762e5ad9baf3a8329e'}
GUARD_REPLAY={'path':'/private/tmp/gio-reference31-exact-deny-verification-v1/verification-receipt.json','sha256':'5cf8244a73b5fd2cc9c0fbc53d6605cf0f282fa09980ee1b977e44130202d83b'}
LATEST=datetime(2026,11,15,16,29,tzinfo=timezone.utc)
DEADLINE='2026-11-15T17:00:00Z'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_ref(ref):
    if sha(ref['path'])!=ref['sha256']:raise ValueError('pinned_artifact_changed')
    return json.loads(Path(ref['path']).read_text())
def load(ref,name):
    if sha(ref['path'])!=ref['sha256']:raise ValueError('pinned_runtime_changed')
    spec=importlib.util.spec_from_file_location(name,ref['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
previous=load(PREVIOUS,'previous_observed_scheduler')
write=previous.write

def runtime():return load({'path':str(Path(RUNTIME)/'scripts/overnight_labeled_reference.py'),'sha256':SCRIPT_SHA},'first8_runtime')
def prepared():return read_ref({'path':PREPARED_PATH,'sha256':PREPARED_SHA})

def verify_runtime():
    if subprocess.check_output(['git','-C',RUNTIME,'rev-parse','HEAD'],text=True).strip()!=COMMIT:raise ValueError('runtime_commit_changed')
    if subprocess.check_output(['git','-C',RUNTIME,'status','--porcelain','--untracked-files=no'],text=True).strip():raise ValueError('runtime_dirty')
    if runtime().runtime_identity()!=prepared()['runtime_identity']:raise ValueError('runtime_files_changed')

def verify_primary(ref):
    if ref!=STOPPED:raise ValueError('exact_stopped_predecessor_required')
    t=read_ref(ref)
    if (t['status']!='stopped' or t['attempted_packets']!=29 or t['unattempted_packets']!=2 or
        t['additional_unknown_packets']!=2 or t['historical_unknowns']!=5 or t['total_historical_and_new_unknown']!=7 or
        t['aggregate_reference_reserved_usd']!='46.90' or t['all_tranches_still_reserved'] is not True or len(t['completed'])!=29):raise ValueError('predecessor_not_exactly_drained')
    for row in t['completed']:
        if row!=json.loads((PRIMARY/'execution'/(row['job_id']+'-terminal.json')).read_text()):raise ValueError('predecessor_terminal_row_changed')
    # Unknown outcomes stay unknown. The root inspection authorizes only new work.
    return t

def verify_expanded_guard(ref):
    if ref!=EXPANDED:raise ValueError('exact_expanded_guard_pin_required')
    read_ref(GUARD_REPLAY)
    old=read_ref(previous.DENY)['identity_denylists'];new=read_ref(ref)
    if new['schema_version']!='provider-unknown-wire-denylist-v2':raise ValueError('typed_guard_schema_changed')
    incident=read_ref(INCIDENT);events=[u['unknown_event'] for u in incident['unknowns']]
    endpoint=set(old['endpoint_body_sorted_json_sha256'])|{e['endpoint_body_sha256'] for e in events}
    old_body=set(old['body_compact_json_sha256']);extra_body={e['request_sha256'] for e in events}
    typed=new['identity_denylists']
    if (set(typed)!={'body_compact_json_sha256','endpoint_body_sorted_json_sha256'} or
        set(typed['endpoint_body_sorted_json_sha256'])!=endpoint or
        set(typed['body_compact_json_sha256']) != old_body|extra_body):
        raise ValueError('expanded_guard_missing_or_changed_historical_identities')
    return new

def verify_incident_inspection(ref,dispatch):
    inspection=read_ref(ref);expected={'schema_version':'reference-first8-incident-inspection-v1','state':'authorized','inspected_by':'root',
        'incident':INCIDENT,'stopped_predecessor':STOPPED,'predecessor_adapter':PREDECESSOR_ADAPTER,
        'historical_reference_unknowns':7,'original_plan_denylist':previous.DENY,'expanded_external_denylist':dispatch['typed_denylist'],
        'runtime_commit':COMMIT,'prepared_index':dispatch['prepared_index'],'release_prior_holds':False,'retry_or_resume_unknown_requests':False,
        'all_prior_reservations_retained_usd':'46.90','fixed_first8_disjoint_work_authorized':True,'current_provider_availability_reviewed':True}
    for k,v in expected.items():
        if inspection.get(k)!=v or type(inspection.get(k)) is not type(v):raise ValueError('incident_inspection_contract_changed:'+k)
    at=datetime.fromisoformat(inspection['inspected_at'].replace('Z','+00:00'))
    approved=datetime.fromisoformat(dispatch['inspected_at'].replace('Z','+00:00'))
    if at.tzinfo is None or at<datetime(2026,11,15,13,29,56,tzinfo=timezone.utc) or at>approved:raise ValueError('incident_inspection_chronology')
    incident=read_ref(INCIDENT);dispositions=inspection['untouched_dispositions']
    if [d['job_id'] for d in dispositions]!=[r['job_id'] for r in incident['untouched']]:raise ValueError('exact_two_untouched_dispositions_required')
    for original,d in zip(incident['untouched'],dispositions):
        lease=read_ref(original['lease']);original_plan=read_ref(original['plan']);packet=Path(original['plan']['path']).parent
        if d['status']=='withheld_not_started':
            if any(Path(x).exists() for x in original['absent_markers']):raise ValueError('withheld_job_started')
        elif d['status']=='known_terminal':
            terminal=read_ref(d['terminal']);diagnostic=read_ref(d['diagnostics_verified'])
            completion=json.loads((packet/'completion.json').read_text());claim=json.loads(Path(original['claim_path']).read_text())
            if (terminal['job_id']!=original['job_id'] or terminal['outcome']!='terminal_known_usage' or terminal['returncode']!=0 or terminal['reported_hold_usd']!=0 or
                terminal['completion_sha256']!=sha(packet/'completion.json') or terminal['report_sha256']!=sha(packet/'output/report.json') or
                completion['job_id']!=original['job_id'] or completion['report_sha256']!=terminal['report_sha256'] or
                any(b['reserved_usd']!=0 for b in completion['budgets']) or diagnostic['observed_terminal_valid'] is not True or diagnostic['actual_wrapper_returncode']!=0 or
                claim['job_id']!=original['job_id'] or claim['plan_sha256']!=original['plan']['sha256'] or claim['lease_sha256']!=original['lease']['sha256']):raise ValueError('untouched_continuation_not_known_terminal')
            budgets=completion['budgets']
            if (len(budgets)!=1 or not Decimal('0')<=Decimal(str(budgets[0]['spent_usd']))<=Decimal(str(lease['max_usd'])) or
                type(completion['attempts']) is not int or not 0<=completion['attempts']<=lease['max_calls']):raise ValueError('untouched_continuation_accounting')
            # Reuse the frozen runtime's exact envelope/event binding validator.
            evidence={'plan':{k:original['plan'][k] for k in ('path','sha256')},**{k:d[k] for k in ('envelope_claim','envelope_terminal','events')}}
            values={'plan':original_plan,'diagnostics_verified':diagnostic,**{k:read_ref(d[k]) for k in ('envelope_claim','envelope_terminal')}}
            runtime().recovery903_diagnostics(evidence,values,d['events']['path'])
        else:raise ValueError('unsupported_untouched_disposition')
    if dispatch.get('recovery903_replacement') is not None and dispositions[1]['status']!='known_terminal':raise ValueError('903_replacement_requires_known_separate_recovery')
    return inspection

def rows_for(dispatch):
    index=prepared();rows=dispatch['jobs']
    if len(rows)!=8 or [r['user_id'] for r in rows]!=[r['user_id'] for r in index['users']]:raise ValueError('exact_original_eight_required')
    if any(len({r[k] for r in rows})!=8 for k in ('job_id','path','claim_path','plan_path')):raise ValueError('duplicate_dispatch_identity')
    replacement=dispatch.get('recovery903_replacement')
    for expected,row in zip(index['users'],rows):
        ref=expected['plan']
        if expected['user_id']=='prism:user903' and replacement is not None:
            ref=replacement
            rp=read_ref(ref)
            if rp['recovery903_enabled'] is not True:raise ValueError('replacement_requires_known_recovery')
        if row['plan_path']!=ref['path'] or row['plan_sha256']!=ref['sha256']:raise ValueError('prepared_plan_changed')
        p=read_ref(ref)
        if p['user_ids']!=[row['user_id']] or p['n_predictions']!=expected['n_planned_cells'] or p['runtime']!=index['runtime_identity']:raise ValueError('scope_or_runtime_changed')
        if row['max_calls']!=p['limits']['max_calls'] or row['max_usd']!=p['limits']['max_usd']:raise ValueError('packet_cap_changed')
    if sum(read_ref({'path':r['plan_path'],'sha256':r['plan_sha256']})['n_predictions'] for r in rows)!=228:raise ValueError('planned_denominator_changed')
    return rows

def verify_row(row):
    r=runtime();plan=Path(row['plan_path']);lease=read_ref({'path':row['path'],'sha256':row['sha256']})
    for key in ('job_id','claim_path','max_usd','max_calls','plan_sha256'):
        if lease[key]!=row[key]:raise ValueError('lease_binding_changed')
    r.validate_execution(plan,row['path'])
    for p in [Path(row['claim_path'])]+[plan.parent/n for n in ('LAUNCH_USED.json','output','completion.json','final-cache-manifest.json')]:
        if p.exists():raise ValueError('already_consumed_or_started')

def make_envelope(index,row,dispatch,authorization=None):
    return {'schema_version':'diagnostic-runtime-envelope-v2','script_sha256':dispatch['wrapper']['sha256'],
        'state':'authorized' if authorization else 'proposed_not_authorized','observer':previous.OBSERVER,
        'deadline':DEADLINE,'denylist':dispatch['typed_denylist'],'authorization':authorization,'kind':'reference',
        'runtime_root':RUNTIME,'runtime_commit':COMMIT,'entrypoint':'scripts/overnight_labeled_reference.py',
        'runtime_files':index['runtime_identity']['files'],'inputs':{'plan':{'path':row['plan_path'],'sha256':row['plan_sha256']},
        'lease':{'path':row['path'],'sha256':row['sha256']}},'output_root':str(DIAGNOSTICS/row['job_id'])}

def validate_dispatch(d,now):
    if now.tzinfo is None or now>=LATEST:raise ValueError('latest_packet_start_or_naive_clock')
    expected={'schema_version':'reference-original-first8-dispatch-v4','state':'authorized','inspected_by':'root',
        'script_sha256':sha(__file__),'prepared_index':{'path':PREPARED_PATH,'sha256':PREPARED_SHA},
        'runtime_commit':COMMIT,'observer':previous.OBSERVER,'wrapper':APPROVED_WRAPPER,'typed_denylist':EXPANDED,'actual_request_guard_verification':GUARD_REPLAY,'original_plan_denylist':previous.DENY,'previous_scheduler':PREVIOUS,'predecessor_adapter':PREDECESSOR_ADAPTER,
        'all_prior_reservations_retained_usd':'46.90','release_prior_holds':False,'historical_reference_unknowns':7,
        'max_concurrent':2,'first_two_serial':True,'allow_retry_or_resume':False,'planned_cells':228,
        'deadline':DEADLINE,'latest_packet_start':'2026-11-15T16:29:00Z','output_root':str(OUT),
        'diagnostics_root':str(DIAGNOSTICS),'no_other_reference_dispatcher_or_process':True,
        'stop_after_first_additional_unknown_or_invalid_accounting':True,'stop_on_diagnostic_failure_or_historical_denial':True}
    for k,v in expected.items():
        if d.get(k)!=v or type(d.get(k)) is not type(v):raise ValueError('dispatch_contract_changed:'+k)
    at=datetime.fromisoformat(d['inspected_at'].replace('Z','+00:00'))
    if at.tzinfo is None or at>now:raise ValueError('invalid_inspection_time')
    rows=rows_for(d);reserve=sum(Decimal(str(r['max_usd'])) for r in rows)
    if reserve>Decimal('2.20') or Decimal(d['new_allocation_usd'])!=reserve or Decimal(d['aggregate_reference_reserved_usd'])!=Decimal('46.90')+reserve:raise ValueError('allocation_contract_changed')
    verify_primary(d['primary_terminal']);verify_expanded_guard(d['typed_denylist']);verify_incident_inspection(d['incident_inspection'],d);verify_runtime()
    wrapper=load(d['wrapper'],'approved_first8_envelope')
    if sha(previous.OBSERVER['path'])!=previous.OBSERVER['sha256']:raise ValueError('observer_changed')
    for row in rows:verify_row(row);wrapper.validate(make_envelope(prepared(),row,d),check_only=True)
    if OUT.exists() or DIAGNOSTICS.exists():raise ValueError('fresh_output_roots_required')
    return rows,wrapper

class FirstEightSupervisor(previous.ContinuationSupervisor):
    def __init__(self,rows,run,launch,*,guard,now=None):
        previous.prior.v2.Supervisor.__init__(self,rows,run,launch,prior_unknown=7,now=now);self.guard=guard
    def gates(self):
        if self.unknown>7:self.stop='first_additional_unknown_inspection_required'
        elif self.stop is None:
            if (self.run.parent/'STOP_ADMISSIONS').exists():self.stop='coordinator_stop_admissions'
            elif self.now()>=LATEST:self.stop='latest_packet_start_reached'
    def poll(self):
        # Same terminal-first accounting contract, with each row's issued cap.
        for pid,(process,log,row) in list(self.active.items()):
            rc=process.poll()
            if rc is None:continue
            log.close();del self.active[pid];packet=Path(row['plan_path']).parent
            record={'job_id':row['job_id'],'returncode':rc,'entire_tranche_remains_reserved_usd':row['max_usd'],'finished_at':self.now().isoformat()}
            try:
                cp=packet/'completion.json';report=packet/'output/report.json';c=json.loads(cp.read_text())
                if c['job_id']!=row['job_id'] or c['report_sha256']!=sha(report) or len(c['budgets'])!=1:raise ValueError('terminal_binding')
                spent,held=(Decimal(str(c['budgets'][0][k])) for k in ('spent_usd','reserved_usd'));cap=Decimal(str(row['max_usd']));attempts=c['attempts']
                if (not spent.is_finite() or not held.is_finite() or min(spent,held)<0 or spent+held>cap or
                    type(attempts) is not int or not 0<=attempts<=row['max_calls']):raise ValueError('invalid_accounting')
                record.update(completion_sha256=sha(cp),report_sha256=sha(report),known_spent_usd=float(spent),reported_hold_usd=float(held),wrapper_attempts=attempts,failures=c['failures'],
                    historical_guard_denials=c['historical_guard_denials'],outcome='terminal_with_unknown_hold' if held else 'terminal_known_usage')
                self.unknown+=bool(held)
                if c['historical_guard_denials']:self.stop='historical_denial_inspection_required'
                elif rc:self.stop='nonzero_exit_inspection_required'
            except Exception:self.unknown+=1;record['outcome']='missing_or_invalid_terminal_evidence';self.stop='terminal_evidence_failure'
            write(self.run/(row['job_id']+'-terminal.json'),record);self.completed.append(record)
        self.gates()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dispatch',required=True);ap.add_argument('--dispatch-sha256',required=True);ap.add_argument('--check',action='store_true');a=ap.parse_args()
    ref={'path':a.dispatch,'sha256':a.dispatch_sha256};dispatch=read_ref(ref);rows,wrapper=validate_dispatch(dispatch,datetime.now(timezone.utc))
    if a.check:print(json.dumps({'status':'offline_passed_no_claim','packets':8,'planned_cells':228}));return
    if not os.environ.get('OPENAI_API_KEY'):raise ValueError('credential_environment_required')
    # Private import only: choose the exact reviewed wrapper without editing any shared file.
    previous.WRAPPER=dispatch['wrapper']
    OUT.mkdir(mode=0o700);run=OUT/'execution';run.mkdir(mode=0o700);envelopes=OUT/'envelopes';envelopes.mkdir(mode=0o700)
    write(OUT/'SUPERVISOR_CLAIM.json',{'script_sha256':sha(__file__),'dispatch':ref,'prepared_index':dispatch['prepared_index'],
        'runtime_commit':COMMIT,'wrapper':dispatch['wrapper'],'observer':previous.OBSERVER,'incident_inspection':dispatch['incident_inspection'],'expanded_external_denylist':dispatch['typed_denylist'],'planned_cells':228,'no_retry':True,'all_prior_reservations_retained_usd':'46.90','aggregate_reference_reserved_usd':dispatch['aggregate_reference_reserved_usd']})
    environment=dict(os.environ);environment['PYTHONDONTWRITEBYTECODE']='1'
    def guard(row):
        if read_ref(ref)!=dispatch:raise ValueError('dispatch_changed')
        verify_primary(dispatch['primary_terminal']);verify_expanded_guard(dispatch['typed_denylist']);verify_incident_inspection(dispatch['incident_inspection'],dispatch);verify_runtime();verify_row(row)
        if sha(dispatch['wrapper']['path'])!=dispatch['wrapper']['sha256']:raise ValueError('wrapper_changed')
        wrapper.validate(make_envelope(prepared(),row,dispatch,ref))
    def launch(row,log):
        if datetime.now(timezone.utc)>=LATEST or (OUT/'STOP_ADMISSIONS').exists():raise ValueError('admission_deadline_or_stop')
        envelope=make_envelope(prepared(),row,dispatch,ref);path=envelopes/(row['job_id']+'.json');write(path,envelope)
        process=subprocess.Popen([sys.executable,dispatch['wrapper']['path'],'--envelope',str(path),'--envelope-sha256',sha(path)],cwd=RUNTIME,env=environment,stdout=log,stderr=log)
        return previous.ObservedProcess(process,envelope,run/(row['job_id']+'-diagnostics-verified.json'))
    supervisor=FirstEightSupervisor(rows,run,launch,guard=guard)
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
        'dispatch':ref,'attempted_packets':supervisor.next_index,'unattempted_packets':len(rows)-supervisor.next_index,'completed':supervisor.completed,
        'unattempted_job_ids':[r['job_id'] for r in rows[supervisor.next_index:]],
        'unresolved_admitted_job_ids':[r['job_id'] for r in rows[:supervisor.next_index] if r['job_id'] not in {x['job_id'] for x in supervisor.completed}],'planned_cells':228,'prepared_index':dispatch['prepared_index'],
        'historical_unknowns':7,'additional_unknown_packets':supervisor.unknown-7,'all_tranches_still_reserved':True,
        'aggregate_reference_reserved_usd':dispatch['aggregate_reference_reserved_usd'],'no_retry':True})
    print(json.dumps({'status':'stopped' if supervisor.stop else 'complete','attempted_packets':supervisor.next_index,'additional_unknown':supervisor.unknown-7}))
if __name__=='__main__':main()
