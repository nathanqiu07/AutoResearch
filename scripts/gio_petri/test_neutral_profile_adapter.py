"""Offline exporter tests. All profiles here are synthetic fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import neutral_profile_adapter as adapter


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def seal(body):
    body['content_sha256'] = digest(body['content'])
    body['config_id'] = digest(body['config'])
    body['token_count'] = len(canonical(body['content']).encode())
    body.pop('profile_id', None)
    body['profile_id'] = digest(body)
    return body


def fixture():
    sources = [{'document_id': 'fixture-document', 'content_sha256': 'b' * 64}]
    config = dict(method_id='P8', researcher_id='fixture-person', replicate_id=0,
                  personalization_cap=8192, code_sha='c' * 40,
                  extractor_settings={'max_tokens': 16384, 'temperature': 0},
                  allowed_sources=sources, allowed_source_manifest_hash=digest(sources),
                  evidence_policy='explicit-only')
    statement = dict(text='Sometimes {x} → café.\nNo permanent rule.',
                     kind='belief', evidence_status='explicit', conditions=None,
                     date=None, sources=[dict(document_id='fixture-document',
                                             start=0, end=4, quote='Test')])
    content = {'hypotheses': [dict(id='h2', statement=copy.deepcopy(statement), weight=None),
                              dict(id='h1', statement=statement, weight=None)],
               'relations': [dict(kind='extraction_uncertainty',
                                  hypothesis_ids=['h2', 'h1'], statement=None)]}
    body = {k: copy.deepcopy(v) for k, v in config.items()
            if k not in ('allowed_sources', 'evidence_policy')}
    body.update(schema_version='neutral-profile-v1', status='complete',
                compatibility_status='pinned', confidence_status='uncalibrated',
                weights_status='unavailable', intentional_empty=False, error_code=None,
                token_count_method='utf8-bytes-upper-bound-v1', config=config,
                content=content, prompt_version='synthetic-fixture',
                extractor={'model': 'fixture-no-model'}, fit_usage={'attempted_calls': 0},
                extra_provenance={'fixture': True, 'unknown': None})
    return seal(body)


class NeutralProfileAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.json'
        self.body = fixture()
        self.write()

    def write(self):
        self.raw = (json.dumps(self.body, ensure_ascii=False, indent=2) + '\n').encode()
        self.source.write_bytes(self.raw)
        self.identity = dict(expected_sha256=hashlib.sha256(self.raw).hexdigest(),
                             expected_profile_id=self.body['profile_id'],
                             expected_researcher_id='fixture-person', expected_replicate_id=0)

    def render(self):
        return adapter.render_saved_p8_context(self.source, **self.identity)

    def reject_changed_body(self, change, message=None):
        change(self.body)
        seal(self.body)
        self.write()
        with self.assertRaisesRegex(ValueError, message or '.'):
            self.render()

    def test_preserves_every_content_value_order_null_and_original_status(self):
        text, provenance = self.render()
        payload = json.loads(text.split(adapter.CONTENT_MARKER, 1)[1])
        self.assertEqual(payload['content'], self.body['content'])
        self.assertEqual(payload['confidence_status'], 'uncalibrated')
        self.assertEqual(payload['weights_status'], 'unavailable')
        self.assertEqual(payload['method_id'], 'P8')
        self.assertNotIn('history', payload)
        self.assertNotIn('confidence', payload)
        self.assertEqual(provenance['original_metadata'], {k: v for k, v in self.body.items() if k != 'content'})
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_external_identity_and_source_mutation_rejected(self):
        for key, value in [('expected_sha256', '0' * 64), ('expected_profile_id', '0' * 64),
                           ('expected_researcher_id', 'someone-else'), ('expected_replicate_id', 1),
                           ('expected_replicate_id', False)]:
            with self.subTest(key=key):
                identity = dict(self.identity, **{key: value})
                with self.assertRaises(ValueError):
                    adapter.render_saved_p8_context(self.source, **identity)
        self.source.write_bytes(self.raw + b' ')
        with self.assertRaises(ValueError):
            self.render()

    def test_rejects_unsupported_or_incomplete_artifact(self):
        original = copy.deepcopy(self.body)
        for key, value in [('schema_version', 'other'), ('method_id', 'M2'),
                           ('status', 'invalid'), ('compatibility_status', 'unverified'),
                           ('confidence_status', 'calibrated'), ('weights_status', 'available')]:
            with self.subTest(key=key):
                self.body = copy.deepcopy(original)
                self.reject_changed_body(lambda b: b.update({key: value}))

    def test_rejects_tampered_internal_hashes_even_if_external_hash_matches(self):
        for key in ('content_sha256', 'config_id', 'profile_id', 'allowed_source_manifest_hash'):
            with self.subTest(key=key):
                self.body = fixture()
                self.body[key] = '0' * 64
                self.write()
                with self.assertRaises(ValueError):
                    self.render()

    def test_rejects_inconsistent_config_cap_or_boolean_count(self):
        cases = [lambda b: b['config'].update(researcher_id='other'),
                 lambda b: b.update(personalization_cap=1),
                 lambda b: b.update(replicate_id=False),
                 lambda b: b.pop('code_sha')]
        for change in cases:
            self.body = fixture()
            self.reject_changed_body(change)
        self.body = fixture()
        self.body['token_count'] = True
        self.body.pop('profile_id')
        self.body['profile_id'] = digest(self.body)
        self.write()
        with self.assertRaises(ValueError):
            self.render()

    def test_rejects_ambiguous_json(self):
        for raw in (b'{"schema_version":1,"schema_version":2}', b'{"x":NaN}'):
            self.source.write_bytes(raw)
            self.identity['expected_sha256'] = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):
                self.render()

    def test_rejects_malformed_content_or_invented_weights(self):
        changes = [lambda b: b['content'].update(hypotheses=[]),
                   lambda b: b['content']['hypotheses'][0].update(weight=0.8),
                   lambda b: b['content']['hypotheses'][0].update(id='h1'),
                   lambda b: b['content']['relations'][0].update(hypothesis_ids=['h1', 'missing']),
                   lambda b: b['content']['hypotheses'][0]['statement']['sources'][0].update(document_id='unknown'),
                   lambda b: b['content']['hypotheses'][0]['statement'].pop('date')]
        for change in changes:
            self.body = fixture()
            self.reject_changed_body(change)

    def test_template_suffix_survives_braces_and_has_explicit_role_boundary(self):
        text, _ = self.render()
        suffix = adapter.auditor_template_suffix(text)
        base = 'Frozen seed: {seed}\n'
        rendered = (base + suffix).format(seed='unchanged')
        self.assertEqual(rendered, 'Frozen seed: unchanged\n' + text)
        for role in ('target', 'judge'):
            with self.assertRaises(ValueError):
                adapter.auditor_template_suffix(text, recipient=role)

    def test_export_is_offline_exact_private_and_never_overwrites(self):
        out = self.root / 'export'
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            adapter.export_saved_p8_context(self.source, out, **self.identity)
            adapter.verify_export(out)
        self.assertEqual((out / 'profile-original.json').read_bytes(), self.raw)
        self.assertEqual(set(p.name for p in out.iterdir()), {'profile-original.json',
                         'auditor-context.txt', 'auditor-suffix.template.txt',
                         'provenance.json', 'checksums.json'})
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in out.iterdir()))
        with self.assertRaises(FileExistsError):
            adapter.export_saved_p8_context(self.source, out, **self.identity)
        (out / 'auditor-context.txt').write_text('corrupted')
        with self.assertRaises(ValueError):
            adapter.verify_export(out)

    def test_invalid_input_creates_no_output(self):
        out = self.root / 'export'
        self.identity['expected_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            adapter.export_saved_p8_context(self.source, out, **self.identity)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
