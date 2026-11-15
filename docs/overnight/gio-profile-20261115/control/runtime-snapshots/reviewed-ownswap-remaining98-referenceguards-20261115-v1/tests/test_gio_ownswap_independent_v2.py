"""Ownswap control review: real successor constructors, fake transport/accounting."""
import ast
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load('/private/tmp/gio_prepare_ownswap_v2.py', 'ownswap_independent_helper')
w = load('/private/tmp/gio_diagnostic_runtime_envelope_ownswap_v1.py', 'ownswap_independent_wrapper')
READY = Path('/private/tmp/gio-ownswap-offline-proposal-v2-ready')


class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.n = 0

    def put(self, value):
        self.n += 1
        return h.write(self.root / ('fixture-%02d.json' % self.n), value)

    def test_actual28_successor_wires_through_unchanged_wrapper(self):
        h.runtime()
        from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend
        from autoresearch.taste.overnight.contracts import ProfileArtifact, backend_identity
        from autoresearch.taste.overnight.consumer import prepare_payload
        packets, metadata = h.make_drafts()
        envelope = h.read(h.ref(READY / 'envelope-TEMPLATE.json'))
        envelope.update(state='authorized', authorization=self.put({'state': 'authorized', 'synthetic': True}),
            inputs={'batch': self.put({'code_sha': h.COMMIT, 'max_workers': 2,
                                      'max_total_attempts': 28, 'jobs': [{}, {}]})},
            output_root=str(self.root / 'diagnostics'))
        original_validate = w.validate

        def validate(value):
            checked = copy.deepcopy(value)
            checked['output_root'] = str(h.B / 'diagnostic-envelopes' / ('never-created-' + self.root.name))
            return original_validate(checked)

        seen, costs, reads = [], [], []

        class Ledger(DollarLedger):
            deadline = datetime(2099, 1, 1, tzinfo=timezone.utc)
            def __init__(self): pass
            def reserve(self, cost, metadata): costs.append(cost); return 'synthetic'
            def finish(self, *args, **kwargs): pass

        class Response:
            status = 200
            headers = {'x-request-id': 'synthetic-sensitive-correlation'}
            def __enter__(self): return self
            def __exit__(self, *args): reads.append('close')
            def read(self, size):
                reads.append(size)
                return json.dumps(dict(status='completed', usage=dict(input_tokens=1, output_tokens=1),
                    output=[dict(type='message', role='assistant', status='completed', content=[dict(
                        type='output_text', text='synthetic-response-not-persisted')])])).encode()

        def opener(request, timeout):
            seen.append((request.data, request.full_url, timeout))
            return Response()

        def entry(path, run_name):
            self.assertEqual(Path(path), h.R / h.DRIVER_REL)
            for packet in packets:
                profile = ProfileArtifact.from_dict(h.read(packet['profile']))
                for item in h.read(packet['release'])['items']:
                    prepared = prepare_payload(profile, item['context'], item['options'], packet['config'])
                    backend = OpenAIResponsesBackend(model='gpt-6-luna', reasoning='medium', timeout=60,
                        ledger=Ledger(), max_usd=packet['backend']['max_usd'])
                    self.assertEqual(backend_identity(backend), packet['manifest']['consumer'])
                    backend.complete(prepared['prompt'], system=prepared['system'], **packet['config']['settings'])
            raise SystemExit(0)

        with patch.object(w, 'validate', side_effect=validate), patch.object(w.runpy, 'run_path', side_effect=entry), \
                patch('urllib.request.urlopen', side_effect=opener), patch('sqlite3.connect', side_effect=AssertionError('SQL')), \
                patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-key-only'}, clear=True):
            self.assertEqual(w.execute(envelope), 0)
        expected = [r for row in metadata for r in row['requests']]
        self.assertEqual(len(seen), 28)
        self.assertEqual(reads, [8_000_001, 'close'] * 28)
        for (wire, endpoint, timeout), pin, cost in zip(seen, expected, costs):
            body = json.loads(wire)
            self.assertEqual(timeout, 60)
            self.assertEqual(h.hashlib.sha256(wire).hexdigest(), pin['wire_bytes_sha256'])
            self.assertEqual(h.digest(body), pin['request_sha256'])
            self.assertEqual(h.hashlib.sha256(json.dumps({'endpoint': endpoint, 'body': body},
                ensure_ascii=False, sort_keys=True).encode()).hexdigest(), pin['endpoint_body_sha256'])
            self.assertEqual(cost, h.Decimal(pin['max_usd_reservation']))
        self.assertEqual(sum(costs), h.Decimal('0.135373000'))
        events = (self.root / 'diagnostics/events.jsonl').read_text()
        self.assertEqual(len(events.splitlines()), 28)
        self.assertNotIn('synthetic-sensitive', events)
        self.assertNotIn('synthetic-key-only', events)
        self.assertNotIn('synthetic-response', events)

    def fixture_authority(self):
        # Root-shaped synthetic metadata; never issued or passed to execution.
        authority = h.read(h.ref(READY / 'execution-authority-TEMPLATE.json'))
        authority.update(state='authorized', authority='Synthetic offline only',
            assignment_authority=self.put(dict(h.assignment_template(), state='authorized', authority='Synthetic only')),
            predecessor={'path': '/synthetic-predecessor', 'sha256': '0' * 64})
        policy = dict(h.policy_template(), state='authorized', authority='Synthetic only', predecessor=authority['predecessor'])
        return authority, policy

    def test_separate_execution_authority_scope_limits_guard_and_deadline_fail_before_sql(self):
        auth, policy = self.fixture_authority()
        auth['policy'] = self.put(policy)
        for field, value in [('state', 'proposal'), ('scope', 'other'), ('max_calls', 29), ('max_usd', 2),
                             ('max_inflight', 3), ('unknown_denylist', {}), ('runtime_commit', 'f' * 40),
                             ('deadline', '2026-11-15T18:00:00Z'), ('historical_unknown_holds_released', True)]:
            with self.subTest(field=field), patch('sqlite3.connect', side_effect=AssertionError('early SQL')), \
                    self.assertRaisesRegex(ValueError, 'root_ownswap_execution_authority'):
                h.validate_execution_authority(self.put(dict(auth, **{field: value})))

    def test_capacity_accounting_cannot_create_unissued_money(self):
        auth, policy = self.fixture_authority()
        for field, value in [('profile_cap_usd', 201), ('committed_before_usd', 79),
                             ('unissued_after_usd', '111.218371215'), ('new_study_allocation_usd', 2)]:
            bad = copy.deepcopy(policy)
            bad['capacity_accounting'][field] = value
            auth['policy'] = self.put(bad)
            with self.subTest(field=field), patch('sqlite3.connect', side_effect=AssertionError('early SQL')), \
                    self.assertRaisesRegex(ValueError, 'profile_capacity_accounting'):
                h.validate_execution_authority(self.put(auth))


if __name__ == '__main__':
    unittest.main()
