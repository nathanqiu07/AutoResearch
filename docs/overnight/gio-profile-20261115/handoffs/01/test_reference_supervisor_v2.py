import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


class Process:
    def __init__(self, pid, rc=0):
        self.pid, self.rc = pid, rc
    def poll(self):
        return self.rc


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).with_name("reference_supervisor_v2.py")
        self.assertTrue(source.exists(), "successor supervisor is required")
        spec = importlib.util.spec_from_file_location("reference_supervisor_v2", source)
        self.s = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.s)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "run"; self.run.mkdir()
        self.started = []
        self.clock = lambda: datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)

    def row(self, name):
        packet = self.root / name; packet.mkdir()
        plan = packet / "plan.json"; plan.write_text('{}')
        lease = packet / "lease.json"; lease.write_text('{}')
        return {"job_id": name, "plan_path": str(plan), "plan_sha256": self.s.sha(plan),
                "path": str(lease), "sha256": self.s.sha(lease), "claim_path": str(self.root / (name + '-claim.json')),
                "max_calls": 200, "max_usd": "0.70", "max_seconds": 900}

    def terminal(self, row, hold=0):
        packet = Path(row['plan_path']).parent
        output = packet / 'output'; output.mkdir()
        report = output / 'report.json'; report.write_text('{}')
        (packet / 'completion.json').write_text(json.dumps({'job_id': row['job_id'], 'report_sha256': self.s.sha(report),
            'budgets': [{'spent_usd': .01, 'reserved_usd': hold}], 'attempts': 1, 'failures': {}}))

    def launch(self, row, log):
        self.started.append(row['job_id'])
        return Process(len(self.started) + 100, None)

    def supervisor(self, rows, unknown=0):
        return self.s.Supervisor(rows, self.run, self.launch, prior_unknown=unknown, now=self.clock)

    def test_second_completed_unknown_is_recorded_before_any_new_admission(self):
        old, new = self.row('old'), self.row('new')
        self.terminal(old, hold=.2)
        supervisor = self.supervisor([new], unknown=1)
        supervisor.active[1] = (Process(1), io.StringIO(), old)
        supervisor.step()
        self.assertEqual(self.started, [])
        self.assertEqual(supervisor.unknown, 2)
        self.assertEqual(supervisor.stop, 'two_new_uncertain_packets_inspection_required')
        self.assertEqual(len(list(self.run.glob('*-terminal.json'))), 1)

    def test_completed_known_frees_slot_and_new_job_is_admitted_exactly_once(self):
        old, new = self.row('old'), self.row('new')
        self.terminal(old)
        supervisor = self.supervisor([new])
        supervisor.active[1] = (Process(1), io.StringIO(), old)
        supervisor.step(); supervisor.step()
        self.assertEqual(self.started, ['new'])
        self.assertEqual(len(supervisor.active), 1)
        for _, log, _ in supervisor.active.values(): log.close()

    def test_concurrency_stopfile_deadline_and_carried_unknown_are_enforced(self):
        rows = [self.row('job%d' % i) for i in range(4)]
        supervisor = self.supervisor(rows)
        supervisor.step(); self.assertEqual(len(supervisor.active), 2)
        (self.run.parent / 'STOP_ADMISSIONS').write_text('stop')
        supervisor.step(); self.assertEqual(len(self.started), 2)
        for _, log, _ in supervisor.active.values(): log.close()
        (self.run.parent / 'STOP_ADMISSIONS').unlink()
        self.started.clear()
        supervisor = self.supervisor(rows, unknown=2); supervisor.step(); self.assertEqual(self.started, [])
        supervisor = self.supervisor(rows); supervisor.now=lambda: datetime(2026,11,15,16,44,tzinfo=timezone.utc)
        supervisor.step(); self.assertEqual(self.started, [])

    def test_missing_terminal_evidence_blocks_new_work_and_preserves_tranche(self):
        old,new=self.row('old'),self.row('new')
        supervisor=self.supervisor([new]); supervisor.active[1]=(Process(1),io.StringIO(),old)
        supervisor.step()
        self.assertEqual(self.started, [])
        self.assertEqual(supervisor.unknown, 1)
        self.assertEqual(supervisor.stop,'terminal_evidence_failure')
        self.assertEqual(supervisor.completed[0]['entire_tranche_remains_reserved_usd'],.7)

    def test_claim_appearing_after_preflight_cannot_be_admitted(self):
        row=self.row('new'); Path(row['claim_path']).write_text('{}')
        supervisor=self.supervisor([row]); supervisor.step()
        self.assertEqual(self.started, [])
        self.assertEqual(supervisor.stop,'claim_or_launch_marker_appeared')

    def test_prior_terminal_and_claims_exclude_every_old_attempt_and_carry_unknown(self):
        old,new=self.row('old'),self.row('new'); prior=self.root/'prior'; execution=prior/'execution'; execution.mkdir(parents=True)
        record={'job_id':'old','outcome':'terminal_with_unknown_hold'}
        self.s.write(execution/'old-started.json',{'job_id':'old'})
        self.s.write(execution/'old-terminal.json',record)
        terminal={'status':'stopped','attempted_packets':1,'unattempted_packets':1,'new_uncertain_packets':1,'completed':[record],'all_tranches_still_reserved':True,'no_retry':True}
        claim={'issued_index_sha256':'index-sha'}
        self.s.write(prior/'supervisor-terminal.json',terminal); self.s.write(prior/'SUPERVISOR_CLAIM.json',claim)
        Path(old['claim_path']).write_text(json.dumps({'job_id':'old','plan_sha256':old['plan_sha256'],'lease_sha256':old['sha256']}))
        dispatch={'index':{'sha256':'index-sha'},'prior_terminal':{'path':str(prior/'supervisor-terminal.json'),'sha256':self.s.sha(prior/'supervisor-terminal.json')},'prior_claim':{'path':str(prior/'SUPERVISOR_CLAIM.json'),'sha256':self.s.sha(prior/'SUPERVISOR_CLAIM.json')}}
        eligible, unknown, excluded=self.s.prior_state(dispatch,[old,new])
        self.assertEqual([r['job_id'] for r in eligible],['new']);self.assertEqual(unknown,1);self.assertEqual(excluded,['old'])
        Path(new['claim_path']).write_text(json.dumps({'job_id':'new','plan_sha256':new['plan_sha256'],'lease_sha256':new['sha256']}))
        with self.assertRaisesRegex(ValueError,'unreconciled_claim'):
            self.s.prior_state(dispatch,[old,new])


if __name__ == '__main__': unittest.main()
