import importlib.util
import io
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path
spec=importlib.util.spec_from_file_location('s','/private/tmp/gio_reference_first8_observed_v4.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class Proc:
    def __init__(self,pid,rc=None):self.pid=pid;self.rc=rc
    def poll(self):return self.rc
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.run=self.root/'execution';self.run.mkdir();self.started=[];self.processes=[]
    def row(self,n):
        p=self.root/n;p.mkdir();plan=p/'plan.json';plan.write_text('{}');lease=p/'lease.json';lease.write_text('{}')
        return {'job_id':n,'plan_path':str(plan),'plan_sha256':s.sha(plan),'path':str(lease),'sha256':s.sha(lease),'claim_path':str(self.root/(n+'-claim')),'max_calls':200,'max_usd':.08}
    def terminal(self,row,held=0):
        p=Path(row['plan_path']).parent;(p/'output').mkdir();report=p/'output/report.json';report.write_text('{}');(p/'completion.json').write_text(json.dumps({'job_id':row['job_id'],'report_sha256':s.sha(report),'budgets':[{'spent_usd':.01,'reserved_usd':held}],'attempts':1,'failures':{},'historical_guard_denials':[]}))
    def launch(self,row,log):
        self.started.append(row['job_id']);p=Proc(len(self.started));self.processes.append(p);return p
    def supervisor(self,rows):return s.FirstEightSupervisor(rows,self.run,self.launch,guard=lambda row:None,now=lambda:datetime(2026,11,15,12,tzinfo=timezone.utc))
    def close(self,x):
        for _,log,_ in x.active.values():log.close()
    def test_initial_pair_serial_then_remaining_max2(self):
        rows=[self.row(str(i)) for i in range(5)];x=self.supervisor(rows)
        x.step();self.assertEqual(self.started,['0']);x.step();self.assertEqual(self.started,['0'])
        self.terminal(rows[0]);self.processes[0].rc=0;x.step();self.assertEqual(self.started,['0','1'])
        x.step();self.assertEqual(self.started,['0','1'])
        self.terminal(rows[1]);self.processes[1].rc=0;x.step();self.assertEqual(self.started,['0','1','2','3']);self.assertEqual(len(x.active),2);self.close(x)
    def test_first_new_unknown_stops_before_any_next_admission_and_drains(self):
        old,other,new=[self.row(n) for n in ['old','other','new']];self.terminal(old,.01);x=self.supervisor([new]);p=Proc(2);x.active={1:(Proc(1,0),io.StringIO(),old),2:(p,io.StringIO(),other)}
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,8);self.assertEqual(len(x.active),1)
        self.terminal(other);p.rc=0;x.step();self.assertFalse(x.active);self.assertEqual(self.started,[]);self.assertEqual(x.unknown,8)
    def test_missing_accounting_and_nonzero_exit_stop(self):
        old,new=self.row('old'),self.row('new');x=self.supervisor([new]);x.active[1]=(Proc(1,0),io.StringIO(),old);x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,8)
    def test_claim_stopfile_deadline_block(self):
        row=self.row('a');Path(row['claim_path']).write_text('{}');x=self.supervisor([row]);x.step();self.assertEqual(self.started,[])
        Path(row['claim_path']).unlink();(self.root/'STOP_ADMISSIONS').write_text('stop');x=self.supervisor([row]);x.step();self.assertEqual(self.started,[])
        (self.root/'STOP_ADMISSIONS').unlink();x=self.supervisor([row]);x.now=lambda:datetime(2026,11,15,16,29,tzinfo=timezone.utc);x.step();self.assertEqual(self.started,[])
    def test_unknown_completed_during_guard_is_polled_before_admission(self):
        old,new=self.row('old'),self.row('new');x=self.supervisor([new]);x.next_index=0
        process=Proc(8);x.active[8]=(process,io.StringIO(),old)
        # Simulate post-pair capacity2 with one existing process.
        x.capacity=lambda:2
        def guard(row):self.terminal(old,.01);process.rc=0
        x.guard=guard;x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,8)
    def test_nonzero_known_terminal_still_stops(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);x=self.supervisor([new]);x.active[1]=(Proc(1,1),io.StringIO(),old)
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.stop,'nonzero_exit_inspection_required')
    def test_nonfinite_accounting_stops_and_retains_baseline(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);cp=Path(old['plan_path']).parent/'completion.json';c=json.loads(cp.read_text());c['budgets'][0]['spent_usd']=float('nan');cp.write_text(json.dumps(c));x=self.supervisor([new]);x.active[1]=(Proc(1,0),io.StringIO(),old)
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,8)
    def test_guard_failure_does_not_admit(self):
        x=self.supervisor([self.row('j')]);x.guard=lambda row:(_ for _ in ()).throw(ValueError('changed'));x.step();self.assertEqual(self.started,[]);self.assertEqual(x.stop,'current_inspection_or_artifact_guard_failed')
    def test_known_spend_over_own_tranche_cap_stops_before_next_admission(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);cp=Path(old['plan_path']).parent/'completion.json';c=json.loads(cp.read_text());c['budgets'][0]['spent_usd']=.081;cp.write_text(json.dumps(c));x=self.supervisor([new]);x.active[1]=(Proc(1,0),io.StringIO(),old)
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,8)
    def test_native_historical_denial_stops_even_with_known_usage_and_zero_exit(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);cp=Path(old['plan_path']).parent/'completion.json';c=json.loads(cp.read_text());c['historical_guard_denials']=[{'request_sha256':'a'*64}];cp.write_text(json.dumps(c));x=self.supervisor([new]);x.active[1]=(Proc(1,0),io.StringIO(),old)
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.stop,'historical_denial_inspection_required');self.assertEqual(x.unknown,7)
    def test_increased_conditional_cap_is_accounted_exactly(self):
        old=self.row('old');old['max_usd']=1.48;self.terminal(old);cp=Path(old['plan_path']).parent/'completion.json';c=json.loads(cp.read_text());c['budgets'][0]['spent_usd']=1.1;cp.write_text(json.dumps(c));x=self.supervisor([]);x.active[1]=(Proc(1,0),io.StringIO(),old)
        x.poll();self.assertIsNone(x.stop);self.assertEqual(x.completed[0]['entire_tranche_remains_reserved_usd'],1.48)
    def test_proposed_dispatch_is_never_authority(self):
        with self.assertRaisesRegex(ValueError,'dispatch_contract'):
            s.validate_dispatch({'state':'proposed_not_authorized'},datetime(2026,11,15,13,tzinfo=timezone.utc))
    def test_finite_input_scope_rejects_omissions_and_reordered_users(self):
        index=s.prepared();rows=[{'user_id':r['user_id']} for r in index['users']]
        for bad in (rows[:-1],list(reversed(rows))):
            with self.assertRaisesRegex(ValueError,'exact_original_eight'):
                s.rows_for({'jobs':bad})
    def test_exact_frozen_eight_inputs_and_fallback_caps(self):
        index=s.prepared();rows=[]
        for i,r in enumerate(index['users']):
            rows.append({'job_id':str(i),'path':'lease'+str(i),'claim_path':'claim'+str(i),'user_id':r['user_id'],'plan_path':r['plan']['path'],'plan_sha256':r['plan']['sha256'],'max_calls':r['limits']['max_calls'],'max_usd':r['limits']['max_usd']})
        actual=s.rows_for({'jobs':rows,'recovery903_replacement':None})
        self.assertEqual(len(actual),8);self.assertEqual(sum(r['max_calls'] for r in actual),367)
        self.assertEqual(sum(s.Decimal(str(r['max_usd'])) for r in actual),s.Decimal('.80'))
        rows[0]['plan_sha256']='x'
        with self.assertRaisesRegex(ValueError,'prepared_plan_changed'):s.rows_for({'jobs':rows})
    def test_stopped_predecessor_is_accepted_without_reclassifying_unknowns(self):
        terminal=s.verify_primary(s.STOPPED)
        self.assertEqual(terminal['status'],'stopped')
        self.assertEqual(terminal['total_historical_and_new_unknown'],7)
        self.assertEqual(sum(r['outcome']=='terminal_with_unknown_hold' for r in terminal['completed']),2)
    def test_original_complete_predecessor_requirement_is_not_reintroduced(self):
        with self.assertRaisesRegex(ValueError,'exact_stopped'):
            s.verify_primary({'path':s.STOPPED['path'],'sha256':'0'*64})
    def test_original_nine_guard_cannot_stand_in_for_expanded_external_guard(self):
        with self.assertRaisesRegex(ValueError,'expanded_guard'):
            s.verify_expanded_guard(s.previous.DENY)
    def test_expanded_guard_keeps_all_old_and_both_new_endpoint_identities(self):
        old=s.read_ref(s.previous.DENY);incident=s.read_ref(s.INCIDENT)
        old['identity_denylists']['endpoint_body_sorted_json_sha256']+= [u['unknown_event']['endpoint_body_sha256'] for u in incident['unknowns']]
        path=self.root/'expanded.json';path.write_text(json.dumps(old));ref={'path':str(path),'sha256':s.sha(path)}
        old['identity_denylists']['body_compact_json_sha256'] += [u['unknown_event']['request_sha256'] for u in incident['unknowns']]
        path.write_text(json.dumps(old));ref['sha256']=s.sha(path)
        with mock.patch.object(s,'EXPANDED',ref):s.verify_expanded_guard(ref)
        old['identity_denylists']['endpoint_body_sorted_json_sha256'].pop(0);path.write_text(json.dumps(old));ref['sha256']=s.sha(path)
        with mock.patch.object(s,'EXPANDED',ref),self.assertRaisesRegex(ValueError,'expanded_guard'):s.verify_expanded_guard(ref)
    def incident_fixture(self):
        rows=[]
        for job in ('535','903'):
            packet=self.root/job;packet.mkdir();plan=packet/'plan.json';plan.write_text('{}');lease=packet/'lease.json';lease.write_text('{}')
            rows.append({'job_id':job,'plan':{'path':str(plan),'sha256':s.sha(plan)},'lease':{'path':str(lease),'sha256':s.sha(lease)},'claim_path':str(self.root/(job+'-claim')),'absent_markers':[str(self.root/(job+'-claim'))]})
        ip=self.root/'incident.json';ip.write_text(json.dumps({'untouched':rows}));incident={'path':str(ip),'sha256':s.sha(ip)}
        dispatch={'typed_denylist':{'path':'expanded','sha256':'a'*64},'prepared_index':{'path':s.PREPARED_PATH,'sha256':s.PREPARED_SHA},'inspected_at':'2026-11-15T13:40:01Z','recovery903_replacement':None}
        inspection={'schema_version':'reference-first8-incident-inspection-v1','state':'authorized','inspected_by':'root','incident':incident,'stopped_predecessor':s.STOPPED,'predecessor_adapter':s.PREDECESSOR_ADAPTER,'historical_reference_unknowns':7,'original_plan_denylist':s.previous.DENY,'expanded_external_denylist':dispatch['typed_denylist'],'runtime_commit':s.COMMIT,'prepared_index':dispatch['prepared_index'],'release_prior_holds':False,'retry_or_resume_unknown_requests':False,'all_prior_reservations_retained_usd':'46.90','fixed_first8_disjoint_work_authorized':True,'current_provider_availability_reviewed':True,'inspected_at':'2026-11-15T13:40:00Z','untouched_dispositions':[{'job_id':r['job_id'],'status':'withheld_not_started'} for r in rows]}
        path=self.root/'inspection.json';path.write_text(json.dumps(inspection));return incident,dispatch,inspection,path
    def test_inspected_drained_incident_can_keep_both_untouched_jobs_withheld(self):
        incident,dispatch,inspection,path=self.incident_fixture()
        with mock.patch.object(s,'INCIDENT',incident):
            s.verify_incident_inspection({'path':str(path),'sha256':s.sha(path)},dispatch)
            Path(s.read_ref(incident)['untouched'][0]['claim_path']).write_text('{}')
            with self.assertRaisesRegex(ValueError,'withheld_job_started'):s.verify_incident_inspection({'path':str(path),'sha256':s.sha(path)},dispatch)
    def test_conditional903_cannot_bypass_its_distinct_recovery(self):
        incident,dispatch,inspection,path=self.incident_fixture();dispatch['recovery903_replacement']={'path':'x','sha256':'x'}
        with mock.patch.object(s,'INCIDENT',incident),self.assertRaisesRegex(ValueError,'903_replacement'):
            s.verify_incident_inspection({'path':str(path),'sha256':s.sha(path)},dispatch)
    def test_inspection_cannot_release_holds_or_retry_unknowns(self):
        incident,dispatch,inspection,path=self.incident_fixture()
        for key in ('release_prior_holds','retry_or_resume_unknown_requests'):
            bad=dict(inspection);bad[key]=True;path.write_text(json.dumps(bad))
            with mock.patch.object(s,'INCIDENT',incident),self.subTest(key=key),self.assertRaisesRegex(ValueError,'incident_inspection_contract'):
                s.verify_incident_inspection({'path':str(path),'sha256':s.sha(path)},dispatch)
    def test_actual_expanded_guard_and_approved_wrapper_are_pinned(self):
        d=s.verify_expanded_guard(s.EXPANDED)
        self.assertEqual(len(d['identity_denylists']['body_compact_json_sha256']),6)
        self.assertEqual(len(d['identity_denylists']['endpoint_body_sorted_json_sha256']),7)
        s.load(s.APPROVED_WRAPPER,'test_approved_first8_wrapper')
if __name__=='__main__':unittest.main()
