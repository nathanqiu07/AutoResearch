"""Independent bounded review: no live entrypoint, credentials or ledger writes."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load('/private/tmp/gio_prepare_primary14_v1.py', 'primary14_independent_helper')
s = load('/private/tmp/gio_primary14_supervisor_v1.py', 'primary14_independent_supervisor')
INDEX = {'path': '/private/tmp/gio-primary14-native-admissions-v1/ready-index.json',
         'sha256': '033a46b9f4f5a80b7926088f6d1b7936b9e1de94bda92135cd1584416fd540d6'}


class Review(unittest.TestCase):
    def test_real_frozen_backend_emits_exact14_declared_wires(self):
        h.p.runtime()
        from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend
        from autoresearch.taste.overnight.contracts import ProfileArtifact, digest
        from autoresearch.taste.overnight.consumer import prepare_payload
        packet = h.read(h.DRAFT)
        profile = ProfileArtifact.from_dict(h.read(packet['profile']))
        release = h.read(packet['release'])
        planned = h.capture()['requests']
        captured, reads, reservations = [], [], []

        class Ledger(DollarLedger):
            deadline = datetime(2099, 1, 1, tzinfo=timezone.utc)
            def __init__(self): pass
            def reserve(self, amount, metadata):
                reservations.append(amount)
                return 'synthetic'
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

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-only'}, clear=True), \
                patch('urllib.request.urlopen', side_effect=transport), \
                patch('sqlite3.connect', side_effect=AssertionError('no SQL')):
            for item in release['items']:
                payload = prepare_payload(profile, item['context'], item['options'], packet['config'])
                backend = OpenAIResponsesBackend(model='gpt-6-sol', reasoning='medium', timeout=60,
                    ledger=Ledger(), max_usd=1)
                backend.complete(payload['prompt'], system=payload['system'], **packet['config']['settings'])
        self.assertEqual(len(captured), 14)
        self.assertEqual(reads, [8_000_001, 'close'] * 14)
        for (request, timeout), expected, cost in zip(captured, planned, reservations):
            body = json.loads(request.data)
            self.assertEqual(timeout, 60)
            self.assertEqual(h.hashlib.sha256(request.data).hexdigest(), expected['wire_bytes_sha256'])
            self.assertEqual(digest(body), expected['request_sha256'])
            endpoint = json.dumps(dict(endpoint=request.full_url, body=body), ensure_ascii=False, sort_keys=True).encode()
            self.assertEqual(h.hashlib.sha256(endpoint).hexdigest(), expected['endpoint_body_sha256'])
            self.assertEqual(cost, h.Decimal(expected['max_usd_reservation']))
        self.assertEqual(sum(reservations), h.Decimal('1.51148'))

    def test_invalid_index_rejected_before_sql_or_claim(self):
        original = h.read(INDEX)
        for field, value in [('jobs', 2), ('max_calls', 15), ('planned_descendant_slots', 14),
                             ('unavailable_descendant_slots', 0), ('automatic_followup', True)]:
            with tempfile.TemporaryDirectory() as temp:
                ref = h.write(Path(temp) / 'index.json', dict(original, **{field: value}))
                with patch('sqlite3.connect', side_effect=AssertionError('early SQL')), \
                        self.subTest(field=field), self.assertRaises(ValueError):
                    s.preflight(ref)

    def main_case(self, exit_code, verify_error):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'supervisor'
            baseline = dict(attempts=284, spent=3260300000)
            index = dict(authority={}, prepared={})
            wrapper = SimpleNamespace(validate=lambda env: None,
                now=lambda: datetime(2026, 11, 15, 14, tzinfo=timezone.utc))
            with patch.object(s, 'ROOT', root), \
                    patch.object(s, 'preflight', return_value=(wrapper, index, {}, {}, baseline, {}, {})), \
                    patch.object(s.h, 'validate_authority', return_value=({}, {}, {}, {}, baseline)), \
                    patch.object(s, 'admission_gate'), \
                    patch.object(s.subprocess, 'run', return_value=SimpleNamespace(returncode=exit_code)) as child, \
                    patch.object(s, 'verify_completed', side_effect=ValueError('synthetic unknown') if verify_error else None,
                                 return_value={'known': True}) as verify, \
                    patch.object(s.sys, 'argv', ['supervisor', '--ready-index', '/synthetic', '0' * 64]), \
                    patch('urllib.request.urlopen', side_effect=AssertionError('network')):
                code = s.main()
            terminal = json.loads((root / 'supervisor-terminal.json').read_text())
            self.assertEqual(child.call_count, 1)
            self.assertEqual(verify.call_count, int(exit_code == 0))
            self.assertTrue(terminal['no_retry_or_followup'])
            self.assertEqual(terminal['planned_descendant_slots'], 84)
            self.assertEqual(terminal['unavailable_descendant_slots'], 70)
            return code, terminal

    def test_main_child_nonzero_stops_without_terminal_repair(self):
        code, terminal = self.main_case(2, False)
        self.assertEqual(code, 2)
        self.assertEqual(terminal['stop_reason'], 'child_nonzero')
        self.assertIsNone(terminal['verified'])

    def test_main_unknown_or_missing_diagnostic_stops_without_retry(self):
        code, terminal = self.main_case(0, True)
        self.assertEqual(code, 2)
        self.assertEqual(terminal['stop_reason'], 'terminal_verification_failed')
        self.assertFalse(terminal['native_accounting_drain_verified'])

    def test_main_known_complete_requires_verified_receipt(self):
        code, terminal = self.main_case(0, False)
        self.assertEqual(code, 0)
        self.assertEqual(terminal['status'], 'complete')
        self.assertIsNotNone(terminal['verified'])


if __name__ == '__main__':
    unittest.main()
