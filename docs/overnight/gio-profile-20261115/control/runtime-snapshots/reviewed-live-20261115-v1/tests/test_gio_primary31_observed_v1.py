import importlib.util
import io
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path
spec=importlib.util.spec_from_file_location('s','/private/tmp/gio_reference_primary31_observed_v1.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class Proc:
    def __init__(self,pid,rc=None):self.pid=pid;self.rc=rc
    def poll(self):return self.rc
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/private/tmp');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.run=self.root/'execution';self.run.mkdir();self.started=[];self.processes=[]
    def row(self,n):
        p=self.root/n;p.mkdir();plan=p/'plan.json';plan.write_text('{}');lease=p/'lease.json';lease.write_text('{}')
        return {'job_id':n,'plan_path':str(plan),'plan_sha256':s.sha(plan),'path':str(lease),'sha256':s.sha(lease),'claim_path':str(self.root/(n+'-claim')),'max_calls':200}
    def terminal(self,row,held=0):
        p=Path(row['plan_path']).parent;(p/'output').mkdir();report=p/'output/report.json';report.write_text('{}');(p/'completion.json').write_text(json.dumps({'job_id':row['job_id'],'report_sha256':s.sha(report),'budgets':[{'spent_usd':.01,'reserved_usd':held}],'attempts':1,'failures':{}}))
    def launch(self,row,log):
        self.started.append(row['job_id']);p=Proc(len(self.started));self.processes.append(p);return p
    def supervisor(self,rows):return s.ContinuationSupervisor(rows,self.run,self.launch,guard=lambda row:None,now=lambda:datetime(2026,11,15,12,tzinfo=timezone.utc))
    def close(self,x):
        for _,log,_ in x.active.values():log.close()
    def test_initial_pair_serial_then_remaining_max2(self):
        rows=[self.row(str(i)) for i in range(5)];x=self.supervisor(rows)
        x.step();self.assertEqual(self.started,['0']);x.step();self.assertEqual(self.started,['0'])
        self.terminal(rows[0]);self.processes[0].rc=0;x.step();self.assertEqual(self.started,['0','1'])
        x.step();self.assertEqual(self.started,['0','1'])
        self.terminal(rows[1]);self.processes[1].rc=0;x.step();self.assertEqual(self.started,['0','1','2','3']);self.assertEqual(len(x.active),2);self.close(x)
    def test_first_new_unknown_stops_before_any_next_admission_and_drains(self):
        old,other,new=[self.row(n) for n in ['old','other','new']];self.terminal(old,.1);x=self.supervisor([new]);p=Proc(2);x.active={1:(Proc(1,0),io.StringIO(),old),2:(p,io.StringIO(),other)}
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,6);self.assertEqual(len(x.active),1)
        self.terminal(other);p.rc=0;x.step();self.assertFalse(x.active);self.assertEqual(self.started,[]);self.assertEqual(x.unknown,6)
    def test_missing_accounting_and_nonzero_exit_stop(self):
        old,new=self.row('old'),self.row('new');x=self.supervisor([new]);x.active[1]=(Proc(1,0),io.StringIO(),old);x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,6)
    def test_claim_stopfile_deadline_block(self):
        row=self.row('a');Path(row['claim_path']).write_text('{}');x=self.supervisor([row]);x.step();self.assertEqual(self.started,[])
        Path(row['claim_path']).unlink();(self.root/'STOP_ADMISSIONS').write_text('stop');x=self.supervisor([row]);x.step();self.assertEqual(self.started,[])
        (self.root/'STOP_ADMISSIONS').unlink();x=self.supervisor([row]);x.now=lambda:datetime(2026,11,15,16,44,tzinfo=timezone.utc);x.step();self.assertEqual(self.started,[])
    def test_unknown_completed_during_guard_is_polled_before_admission(self):
        old,new=self.row('old'),self.row('new');x=self.supervisor([new]);x.next_index=0
        process=Proc(8);x.active[8]=(process,io.StringIO(),old)
        # Simulate post-pair capacity2 with one existing process.
        x.capacity=lambda:2
        def guard(row):self.terminal(old,.1);process.rc=0
        x.guard=guard;x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,6)
    def test_nonzero_known_terminal_still_stops(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);x=self.supervisor([new]);x.active[1]=(Proc(1,1),io.StringIO(),old)
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.stop,'nonzero_exit_inspection_required')
    def test_nonfinite_accounting_stops_and_retains_baseline(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);cp=Path(old['plan_path']).parent/'completion.json';c=json.loads(cp.read_text());c['budgets'][0]['spent_usd']=float('nan');cp.write_text(json.dumps(c));x=self.supervisor([new]);x.active[1]=(Proc(1,0),io.StringIO(),old)
        x.step();self.assertEqual(self.started,[]);self.assertEqual(x.unknown,6)
    def test_guard_failure_does_not_admit(self):
        x=self.supervisor([self.row('j')]);x.guard=lambda row:(_ for _ in ()).throw(ValueError('changed'));x.step();self.assertEqual(self.started,[]);self.assertEqual(x.stop,'current_inspection_or_artifact_guard_failed')
    def test_exact_inspection_scope_pins_and_holds_required(self):
        good=s.receipt_template('script');good.update(status='authorized',inspected_by='root',inspected_at='2026-11-15T12:00:00Z')
        s.validate_receipt(good,'script',datetime(2026,11,15,12,1,tzinfo=timezone.utc))
        for key,val in [('status','proposed_not_authorized'),('historical_unknown_total',0),('release_prior_holds',True),('aggregate_reference_reserved_usd','0'),('max_concurrent',3),('allow_retry_or_resume',True),('observer',{}),('typed_denylist',{}),('queue',{}),('exact_primary_jobs',30)]:
            value=dict(good);value[key]=val
            with self.subTest(key=key),self.assertRaises(ValueError):s.validate_receipt(value,'script',datetime(2026,11,15,12,1,tzinfo=timezone.utc))
    def test_envelope_exact_plan_lease_runtime_and_authority(self):
        index=s.read_ref(s.QUEUE);rows=s.rows_for(index);authority={'path':'/private/tmp/test-inspection','sha256':'a'*64}
        env=s.make_envelope(index,rows[0],authority)
        self.assertEqual(env['inputs'],{'plan':{'path':rows[0]['plan_path'],'sha256':rows[0]['plan_sha256']},'lease':{'path':rows[0]['path'],'sha256':rows[0]['sha256']}})
        self.assertEqual(env['authorization'],authority);self.assertEqual(env['observer'],s.OBSERVER);self.assertEqual(env['denylist'],s.DENY)
        self.assertEqual(env['runtime_files'],index['runtime_identity']['files']);self.assertEqual(env['state'],'authorized')
        self.assertEqual(s.make_envelope(index,rows[0])['state'],'proposed_not_authorized')
    def test_diagnostic_invalid_terminal_forces_nonzero_and_single_receipt(self):
        process=Proc(1,0);path=self.root/'checked.json';wrapped=s.ObservedProcess(process,{},path)
        with mock.patch.object(s,'verify_observed_terminal',side_effect=ValueError('missing')):
            self.assertEqual(wrapped.poll(),2);self.assertEqual(wrapped.poll(),2)
        self.assertFalse(json.loads(path.read_text())['observed_terminal_valid'])
    def test_diagnostic_valid_terminal_preserves_real_returncode(self):
        process=Proc(1,7);wrapped=s.ObservedProcess(process,{},self.root/'checked.json')
        with mock.patch.object(s,'verify_observed_terminal',return_value={'terminal_sha256':'x'}):self.assertEqual(wrapped.poll(),7)
    def test_diagnostic_write_failure_does_not_prevent_drain(self):
        process=Proc(1,0);wrapped=s.ObservedProcess(process,{},self.root/'checked.json')
        with mock.patch.object(s,'verify_observed_terminal',return_value={}),mock.patch.object(s,'write',side_effect=OSError('sink')):
            self.assertEqual(wrapped.poll(),2);self.assertEqual(wrapped.poll(),2)
    def test_diagnostic_failure_stops_next_admission(self):
        old,new=self.row('old'),self.row('new');self.terminal(old);x=self.supervisor([new])
        wrapped=s.ObservedProcess(Proc(7,0),{},self.root/'checked.json');x.active[7]=(wrapped,io.StringIO(),old)
        with mock.patch.object(s,'verify_observed_terminal',side_effect=ValueError('bad')):x.step()
        self.assertEqual(self.started,[]);self.assertFalse(x.active);self.assertEqual(x.stop,'nonzero_exit_inspection_required')
    def test_observed_terminal_bindings_events_and_denial(self):
        root=self.root/'diagnostics';root.mkdir();env={'output_root':str(root),'runtime_commit':'fixed'}
        wrapper=s.observer_runtime();identity=wrapper.digest(env)
        claim={'canonical_envelope_sha256':identity,'wrapper_script_sha256':s.WRAPPER['sha256'],'envelope':env}
        (root/'ENVELOPE_CLAIM.json').write_text(json.dumps(claim))
        events=root/'events.jsonl';events.write_text(json.dumps({'sequence':0,'stage':'open'})+'\n')
        terminal={'canonical_envelope_sha256':identity,'wrapper_script_sha256':s.WRAPPER['sha256'],
            'scientific_runtime_commit':'fixed','observer_sha256':s.OBSERVER['sha256'],'status':'complete',
            'entry_exit_code':0,'wrapper_exit_code':0,'no_retry_or_resume':True,
            'diagnostics':{'diagnostic_write_failed':False,'dropped_event_count':0,'diagnostic_close_failed':False},
            'events_sha256':s.sha(events),'event_count':1}
        path=root/'envelope-terminal.json';path.write_text(json.dumps(terminal));self.assertEqual(s.verify_observed_terminal(env)['event_count'],1)
        for key,val in [('canonical_envelope_sha256','bad'),('observer_sha256','bad'),('events_sha256','bad'),('event_count',2),('diagnostics',{'diagnostic_write_failed':True})]:
            bad=dict(terminal);bad[key]=val;path.write_text(json.dumps(bad))
            with self.subTest(key=key),self.assertRaises(ValueError):s.verify_observed_terminal(env)
        events.write_text(json.dumps({'sequence':0,'stage':'denied_before_transport'})+'\n');terminal['events_sha256']=s.sha(events);path.write_text(json.dumps(terminal))
        with self.assertRaises(ValueError):s.verify_observed_terminal(env)
if __name__=='__main__':unittest.main()
