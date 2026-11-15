"""Changed two-batch supervisor boundary cases; all children and ledgers fake."""
from contextlib import ExitStack
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('remaining8_independent', '/private/tmp/gio_remaining8_supervisor_v2.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class BoundaryTests(unittest.TestCase):
    def exercise(self, failure):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary) / 'supervisor'
            base = dict(attempts=298, spent=3345365000)
            state = dict(attempts=298, known_nanos=3345365000, known_usd='3.345365',
                         held_usd='0', pending=0, uncertain=0)
            launches = []

            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return cls(2026, 11, 15, 16, 43 if launches and failure == 'deadline' else 0,
                               tzinfo=timezone.utc)

            wrapper = SimpleNamespace(now=lambda: Clock.now(), validate=lambda value: None)
            index = dict(authority={'path': '/synthetic/auth', 'sha256': '0' * 64})
            stages = [dict(block=name, prepared={'path': '/synthetic/' + name, 'sha256': '0' * 64},
                           allowed={}, envelope={'output_root': str(Path(temporary) / name)}) for name in ('P7', 'P3')]

            def authority(*args, **kwargs):
                return {}, {}, dict(state), {}, base

            def launch(*args, **kwargs):
                launches.append(args[0])
                state.update(attempts=state['attempts'] + 4, known_nanos=state['known_nanos'] + 100)
                state['known_usd'] = str(state['known_nanos'] / 1e9)
                if failure == 'stop' and len(launches) == 1:
                    (root / 'STOP_ADMISSIONS').write_text('synthetic coordinator stop')
                return SimpleNamespace(returncode=2 if failure == 'second_nonzero' and len(launches) == 2 else 0)

            def native(*args):
                if failure == 'second_unknown' and len(launches) == 2:
                    raise ValueError('synthetic unknown')
                return dict(attempted_calls=4, known_spent_nanos=100,
                            ledger_attempts=state['attempts'], ledger_spent_nanos=state['known_nanos'])

            for obj, name, value in [(m, 'ROOT', root), (m, 'datetime', Clock)]:
                stack.enter_context(patch.object(obj, name, value))
            stack.enter_context(patch.object(m, 'preflight', return_value=(wrapper, index, {}, base, stages)))
            stack.enter_context(patch.object(m.h, 'validate_authority', side_effect=authority))
            stack.enter_context(patch.object(m.subprocess, 'run', side_effect=launch))
            stack.enter_context(patch.object(m, 'native_terminal', side_effect=native))
            stack.enter_context(patch.object(m.g, 'diagnostic_terminal', return_value={'known': True}))
            stack.enter_context(patch.object(m, 'ref', side_effect=lambda p: {'path': str(p), 'sha256': '0' * 64}))
            stack.enter_context(patch('sys.argv', ['supervisor', '--ready-index', '/synthetic/index', '0' * 64]))
            stack.enter_context(patch('builtins.print'))
            stack.enter_context(patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')))
            stack.enter_context(patch('sqlite3.connect', side_effect=AssertionError('SQL forbidden')))
            code = m.main()
            terminal = json.loads((root / 'supervisor-terminal.json').read_text())
            self.assertEqual(code, 2)
            self.assertEqual(terminal['status'], 'stopped')
            self.assertEqual(len(terminal['completed_verified_batches']), 1)
            self.assertEqual(terminal['known_verified_attempts'], 302)
            self.assertEqual(terminal['known_verified_spend_nanos'], 3345365100)
            self.assertEqual(terminal['future_prediction_jobs_admitted'], 0)
            self.assertTrue(terminal['no_retry_or_followup'])
            return len(launches), terminal['stop_reason']

    def test_second_unknown_retains_first_verified_block_without_retry(self):
        self.assertEqual(self.exercise('second_unknown'), (2, 'terminal_verification_failed'))

    def test_second_nonzero_retains_first_verified_block_without_retry(self):
        self.assertEqual(self.exercise('second_nonzero'), (2, 'child_nonzero'))

    def test_remaining_time_is_rechecked_before_second_block(self):
        self.assertEqual(self.exercise('deadline'), (1, 'admission_or_child_launch_failed_inspect_existing_artifacts'))

    def test_coordinator_stop_between_blocks_prevents_second(self):
        self.assertEqual(self.exercise('stop'), (1, 'admission_or_child_launch_failed_inspect_existing_artifacts'))


if __name__ == '__main__':
    unittest.main()
