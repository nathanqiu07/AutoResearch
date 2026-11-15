"""Independent 98-request transport replay and inter-block stop checks; no real calls."""
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load('remaining98_independent_helper', '/private/tmp/gio_prepare_remaining98_v1.py')
m = load('remaining98_independent_supervisor', '/private/tmp/gio_remaining98_supervisor_v1.py')


class Review(unittest.TestCase):
    def test_all98_real_f6_adapter_wires_prices_and_reads(self):
        h.p.runtime()
        from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend
        from autoresearch.taste.overnight.contracts import ProfileArtifact, digest
        from autoresearch.taste.overnight.consumer import prepare_payload
        captured, reservations, reads = [], [], []

        class Ledger(DollarLedger):
            deadline = datetime(2099, 1, 1, tzinfo=timezone.utc)
            def __init__(self): pass
            def reserve(self, amount, metadata):
                reservations.append(amount)
                return 'synthetic-only'
            def finish(self, *args, **kwargs): pass

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): reads.append('close')
            def read(self, size):
                reads.append(size)
                return json.dumps(dict(status='completed', usage=dict(input_tokens=1, output_tokens=1),
                    output=[dict(type='message', role='assistant', status='completed', content=[dict(
                        type='output_text', text='synthetic')])])).encode()

        def transport(request, timeout):
            captured.append((request, timeout))
            return Response()

        planned = []
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-only'}, clear=True), \
                patch('urllib.request.urlopen', side_effect=transport), \
                patch('sqlite3.connect', side_effect=AssertionError('SQL forbidden')):
            for row in h.capture_rows():
                packet = h.read(row['packet'])
                profile = ProfileArtifact.from_dict(h.read(packet['profile']))
                for item in h.read(packet['release'])['items']:
                    payload = prepare_payload(profile, item['context'], item['options'], packet['config'])
                    backend = OpenAIResponsesBackend(model=row['model'], reasoning='medium', timeout=60,
                        ledger=Ledger(), max_usd=Decimal(row['max_usd']))
                    backend.complete(payload['prompt'], system=payload['system'], **packet['config']['settings'])
                planned.extend(row['requests'])
        self.assertEqual(len(captured), 98)
        self.assertEqual(reads, [8_000_001, 'close'] * 98)
        for (request, timeout), expected, reservation in zip(captured, planned, reservations):
            body = json.loads(request.data)
            self.assertEqual(timeout, 60)
            self.assertEqual(hashlib.sha256(request.data).hexdigest(), expected['wire_bytes_sha256'])
            self.assertEqual(digest(body), expected['request_sha256'])
            endpoint_body = json.dumps(dict(endpoint=request.full_url, body=body),
                ensure_ascii=False, sort_keys=True).encode()
            self.assertEqual(hashlib.sha256(endpoint_body).hexdigest(), expected['endpoint_body_sha256'])
            self.assertEqual(reservation, Decimal(expected['max_usd_reservation']))
        self.assertEqual(sum(reservations), Decimal('26.589370'))

    def boundary_case(self, failure):
        with tempfile.TemporaryDirectory(prefix='gio-remaining98-independent-') as td, ExitStack() as stack:
            root = Path(td) / 'supervisor'
            base = dict(attempts=306, spent=3883810000)
            state = dict(attempts=306, known_nanos=3883810000, known_usd='3.883810',
                         held_usd='0', pending=0, uncertain=0)
            launched = []

            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return cls(2026, 11, 15, 16 if launched and failure == 'deadline' else 14,
                               21 if launched and failure == 'deadline' else 0, tzinfo=timezone.utc)

            wrapper = SimpleNamespace(now=lambda: Clock.now(), validate=lambda value: None)
            index = dict(authority={'path': '/synthetic/auth', 'sha256': '0' * 64})
            stages = [dict(block=name, jobs=jobs, max_calls=calls,
                           prepared={'path': '/synthetic/' + name, 'sha256': '0' * 64},
                           allowed={}, envelope={'output_root': str(Path(td) / name)})
                      for name, jobs, calls in [('P7', 4, 56), ('P3', 3, 42)]]

            def authority(*args, **kwargs): return {}, {}, dict(state), {}, base
            def launch(*args, **kwargs):
                launched.append(args[0])
                state.update(attempts=362, known_nanos=3883810100, known_usd='3.8838101')
                if failure == 'stop': (root / 'STOP_ADMISSIONS').write_text('synthetic stop')
                return SimpleNamespace(returncode=0)
            def native(*args):
                return dict(attempted_calls=56, known_spent_nanos=100,
                            ledger_attempts=362, ledger_spent_nanos=3883810100)

            stack.enter_context(patch.object(m, 'ROOT', root))
            stack.enter_context(patch.object(m, 'datetime', Clock))
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
            self.assertEqual(m.main(), 2)
            terminal = json.loads((root / 'supervisor-terminal.json').read_text())
            self.assertEqual(len(launched), 1)
            self.assertEqual(terminal['known_verified_attempts'], 362)
            self.assertEqual(len(terminal['completed_verified_batches']), 1)
            self.assertEqual(terminal['status'], 'stopped')
            self.assertTrue(terminal['no_retry_or_followup'])
            self.assertEqual(terminal['unavailable_descendant_slots'], 14)

    def test_time_fit_rechecked_before_p3(self): self.boundary_case('deadline')
    def test_coordinator_stop_rechecked_before_p3(self): self.boundary_case('stop')


if __name__ == '__main__': unittest.main()
