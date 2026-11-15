"""Offline driver tests: real file fixtures, synthetic credentials, fake HTTP."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))


def load_driver():
    path = HERE / 'run_batch.py'
    if not path.exists():
        raise AssertionError('the assigned batch driver does not exist yet')
    spec = importlib.util.spec_from_file_location('overnight_run_batch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def peer_fixture_builder(documents, config, extractor):
    return {'content': {'fixture': True}}


class CampaignClock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


class DriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = load_driver()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.d = self.driver
        for target in (self.d, sys.modules['autoresearch.taste.overnight.runner'],
                       sys.modules['autoresearch.taste.overnight.backends']):
            clock = patch.object(target, 'datetime', CampaignClock)
            clock.start()
            self.addCleanup(clock.stop)
        self.sha = 'a' * 40
        self.document = {'document_id': 'doc1', 'researcher_id': 'r1', 'content': 'Evidence.',
                         'content_sha256': self.d.sha256_bytes(b'Evidence.'),
                         'permitted_spans': [{'start': 0, 'end': 9, 'text': 'Evidence.', 'speaker': 'r1'}]}
        self.sources = self.d.source_manifest([self.document])
        self.items = [{'item_id': 'i1', 'researcher_id': 'r1', 'context': 'Choose',
                       'options': ['A', 'B'], 'option_order_id': 'ab'},
                      {'item_id': 'i2', 'researcher_id': 'r1', 'context': 'Choose',
                       'options': ['B', 'A'], 'option_order_id': 'ba'}]
        release = {'schema_version': 'released-development-v2', 'scope': 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel',
                   'researcher_id': 'r1', 'sources': {'documents': [self.document],
                   'source_manifest': self.sources, 'allowed_source_manifest_hash': self.d.digest(self.sources)},
                   'items': self.items, 'items_sha256': self.d.digest(self.items)}
        self.release = self.write('release.json', release)
        self.env = self.base / 'synthetic.env'
        self.env.write_text('OPENAI_API_KEY=synthetic-unit-test-key\n')
        self.batch = {'schema_version': 'overnight-batch-v1', 'campaign_id': 'gio-profile-20261115',
                      'code_sha': self.sha, 'deadline': self.d.HARD_DEADLINE, 'max_workers': 2,
                      'max_total_attempts': 100, 'runtime_root': str(ROOT),
                      'release_schema_version': 'released-development-v2',
                      'release_scope': 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel',
                      'contract': self.write('contract.json', {'scope': 'development'}), 'env_file': str(self.env),
                      'ledger': {'path': str(self.base / 'ledger.sqlite'), 'max_usd': 9.999994875, 'max_inflight': 2},
                      'roots': {k: str(self.base / k) for k in ('output', 'lease', 'cache', 'receipts')}, 'jobs': []}
        self.packet = {'schema_version': 'overnight-packet-v1', 'release': self.release, 'item_ids': [],
                       'profile': None, 'registration': {'module': 'autoresearch.taste.overnight.baselines',
                       'function': 'register_baselines'},
                       'config': {'method_id': 'no_profile', 'researcher_id': 'r1', 'allowed_sources': self.sources,
                       'allowed_source_manifest_hash': self.d.digest(self.sources), 'personalization_cap': 128,
                       'replicate_id': 't0', 'code_sha': self.sha, 'extractor_settings': {'temperature': 0.0, 'max_tokens': 32}},
                       'backend': {'model': 'gpt-6-luna', 'reasoning': 'none', 'timeout': 1,
                                   'max_calls': 1, 'max_seconds': 30, 'max_usd': 0.01},
                       'manifest': {'schema_version': 'overnight-job-v1', 'campaign_id': 'gio-profile-20261115',
                       'stage': 'dev', 'kind': 'build', 'method_id': 'no_profile', 'personalization_cap': 128,
                       'replicate_id': 't0', 'consumer': None,
                       'allocation': {'authorization_source': 'synthetic test', 'max_calls': 1,
                                      'max_seconds': 30, 'max_usd': 0.01, 'cost_mode': 'priced_api'},
                       'retry_policy': {'max_attempts': 1, 'retry_uncertain': False},
                       'parent_job_ids': [], 'expected_outputs': ['profile.json', 'result.json']},
                       'lease': {'lease_id': 'lease0', 'owner': 'test', 'expires_at': self.d.HARD_DEADLINE}}

    def write(self, name, value):
        path = self.base / name
        raw = (json.dumps(value, sort_keys=True) + '\n').encode()
        path.write_bytes(raw)
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}

    def prepared(self, count=1):
        self.batch['jobs'] = []
        for i in range(count):
            packet = json.loads(json.dumps(self.packet))
            if packet['manifest']['kind'] == 'build':
                packet['config']['replicate_id'] = packet['manifest']['replicate_id'] = 't%d' % i
            packet['lease']['lease_id'] = 'lease%d' % i
            self.batch['jobs'].append(self.write('packet%d.json' % i, packet))
        ref = self.write('batch.json', self.batch)
        with patch.object(self.d, 'verify_runtime'):
            return self.d.prepare_batch(ref['path'], ref['sha256'])

    def test_exact_release_and_full_document_hash(self):
        job = self.prepared()['jobs'][0]
        self.assertEqual(job['manifest']['documents_hash'], self.d.digest([self.document]))
        self.assertEqual(job['manifest']['job_id'], self.d.job_id(job['manifest']))
        body = json.loads(Path(self.release['path']).read_text())
        body['sources']['documents'][0]['permitted_spans'][0]['speaker'] = 'other'
        Path(self.release['path']).write_text(json.dumps(body))
        with self.assertRaisesRegex(ValueError, 'file hash'):
            self.prepared()
        self.packet['release'] = self.write('changed.json', body)
        self.packet['manifest']['documents_hash'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'documents_hash'):
            self.prepared()

    def test_confirmation_unknown_method_and_wrong_hash_rejected(self):
        self.packet['manifest']['stage'] = 'confirmation'
        with self.assertRaises(ValueError): self.prepared()
        self.packet['manifest']['stage'] = 'dev'
        self.packet['manifest']['method_id'] = self.packet['config']['method_id'] = 'invented'
        with self.assertRaises(ValueError): self.prepared()

    def test_duplicate_items_unknown_ids_and_label_fields_rejected(self):
        for ids in (['i1', 'i1'], ['unknown']):
            self.packet['item_ids'] = ids
            with self.assertRaises(ValueError): self.prepared()
        body = json.loads(Path(self.release['path']).read_text())
        body['items'][0]['target'] = 'a'
        body['items_sha256'] = self.d.digest(body['items'])
        self.packet['release'] = self.write('labelled.json', body)
        self.packet['item_ids'] = ['i1']
        with self.assertRaises(ValueError): self.prepared()

    def test_strict_aggregate_calls_money_workers_and_deadline(self):
        for field, bad in [('max_workers', 3), ('max_workers', 1.0), ('max_total_attempts', 0), ('deadline', '2026-11-15T17:01:00Z'), ('deadline', '2026-11-15T08:00:00Z')]:
            old = self.batch[field]
            self.batch[field] = bad
            with self.assertRaises(ValueError): self.prepared()
            self.batch[field] = old
        self.batch['max_total_attempts'] = 1
        with self.assertRaises(ValueError): self.prepared(2)
        self.batch['max_total_attempts'] = 100
        self.batch['ledger']['max_usd'] = 500.000000001
        with self.assertRaises(ValueError): self.prepared()
        self.batch['ledger']['max_usd'] = 9.999994875
        self.packet['backend']['max_calls'] = 2
        with self.assertRaises(ValueError): self.prepared()

    def test_approved_profile_suballocation_stays_below_aggregate_cap(self):
        self.batch['ledger']['max_usd'] = 199.982398375
        result = self.prepared()
        self.assertEqual(result['ledger'].summary()['max_usd'], 199.982398375)

    def peer_packet(self):
        target = json.loads(Path(self.release['path']).read_bytes())
        target['target_bundle_sha256'] = 'e' * 64
        target_ref = self.write('parent-target.json', target)
        peer_doc = dict(self.document, document_id='peer-doc', researcher_id='r2')
        peer = dict(target, researcher_id='r2', sources={'documents': [peer_doc],
                    'source_manifest': self.d.source_manifest([peer_doc]),
                    'allowed_source_manifest_hash': self.d.digest(self.d.source_manifest([peer_doc]))})
        peer['items'] = [dict(item, researcher_id='r2', item_id='peer-' + item['item_id']) for item in self.items]
        peer['items_sha256'] = self.d.digest(peer['items'])
        peer_ref = self.write('parent-peer.json', peer)
        records = sorted([self.document, peer_doc], key=lambda d: d['document_id'])
        sources = self.d.source_manifest(records)
        derivative = dict(target, schema_version='released-development-v2-p7-peers-v1',
            approved_peer_sources=True,
            parent_releases=[{'researcher_id': 'r1', 'release': target_ref},
                             {'researcher_id': 'r2', 'release': peer_ref}],
            peer_policy={'allowed_method_id': 'P7', 'purpose': 'contrastive peer fitting',
                         'target_researcher_id': 'r1', 'peer_researcher_ids': ['r2'],
                         'no_heldout_sources': True},
            sources={'documents': records, 'source_manifest': sources,
                     'allowed_source_manifest_hash': self.d.digest(sources)})
        self.packet['manifest']['method_id'] = self.packet['config']['method_id'] = 'P7'
        self.packet['config'].update(allowed_sources=sources, allowed_source_manifest_hash=self.d.digest(sources))
        self.packet['registration'] = {'module': 'autoresearch.taste.overnight.profiles_hypotheses',
                                       'function': 'register_hypotheses_builders'}
        self.batch['release_schema_version'] = derivative['schema_version']
        return derivative

    def bind_peer(self, derivative):
        self.packet['release'] = self.write('peer-derivative.json', derivative)
        for key in ('approved_peer_sources', 'peer_policy', 'parent_releases'):
            self.packet['config'][key] = json.loads(json.dumps(derivative[key]))

    def test_p7_peer_derivative_exact_union_and_parent_hashes(self):
        derivative = self.peer_packet()
        self.bind_peer(derivative)
        with patch.object(self.d, '_register', return_value=SimpleNamespace()):
            prepared = self.prepared()
        self.assertEqual(len(prepared['jobs'][0]['documents']), 2)
        for mutate in ('record', 'parent_hash', 'parent_ref', 'extra_record'):
            changed = json.loads(json.dumps(derivative))
            if mutate == 'record': changed['sources']['documents'][0]['metadata'] = 'not approved'
            elif mutate == 'parent_hash': changed['parent_releases'][0]['release']['sha256'] = '0' * 64
            elif mutate == 'parent_ref': changed['parent_releases'][0]['researcher_id'] = 'r3'
            else: changed['sources']['documents'].append(dict(changed['sources']['documents'][0], document_id='extra'))
            changed['sources']['source_manifest'] = self.d.source_manifest(changed['sources']['documents'])
            changed['sources']['allowed_source_manifest_hash'] = self.d.digest(changed['sources']['source_manifest'])
            self.packet['config']['allowed_sources'] = changed['sources']['source_manifest']
            self.packet['config']['allowed_source_manifest_hash'] = changed['sources']['allowed_source_manifest_hash']
            self.bind_peer(changed)
            with self.assertRaises(ValueError): self.prepared()

    def test_p7_target_panel_and_declarations_cannot_change(self):
        derivative = self.peer_packet()
        for mutate in ('item', 'order', 'items_hash', 'target_hash', 'config', 'policy'):
            changed = json.loads(json.dumps(derivative))
            if mutate == 'item': changed['items'][0]['context'] = 'Changed'
            elif mutate == 'order': changed['items'].reverse()
            elif mutate == 'target_hash': changed['target_bundle_sha256'] = '0' * 64
            elif mutate == 'policy': changed['peer_policy']['no_heldout_sources'] = False
            changed['items_sha256'] = self.d.digest(changed['items'])
            if mutate == 'items_hash': changed['items_sha256'] = '0' * 64
            self.bind_peer(changed)
            if mutate == 'config': self.packet['config']['parent_releases'] = []
            with self.assertRaises(ValueError): self.prepared()

    def test_p7_prediction_and_profile_must_preserve_peer_declarations(self):
        from autoresearch.taste.overnight.registry import register_builder
        from autoresearch.taste.overnight.contracts import build_profile
        builder = register_builder('P7', peer_fixture_builder, prompt_version='peer-fixture',
                                   prompt_sha256='a' * 64)
        derivative = self.peer_packet()
        self.bind_peer(derivative)
        with patch.object(self.d, '_register', return_value=builder):
            built = self.prepared()
        job = built['jobs'][0]
        backend = self.d._backend(self.packet['backend'], built['ledger'])
        profile = build_profile(job['documents'], job['config'], backend)
        self.packet['manifest']['kind'] = 'predict'
        self.packet['manifest'].pop('consumer')
        self.packet['item_ids'] = ['i1', 'i2']
        self.packet['profile'] = self.write('peer-profile.json', profile.to_dict())
        self.packet['config'] = {'method_implementation_hash': profile.method_implementation_hash,
            'renderer_implementation_hash': profile.renderer_implementation_hash,
            'profile_prompt_version': profile.prompt_version, 'consumer_prompt_version': 'neutral-choice-v1',
            'settings': {'temperature': 0.0, 'max_tokens': 32}}
        for key in self.d.PEER_BINDINGS:
            self.packet['config'][key] = json.loads(json.dumps(derivative[key]))
        with patch.object(self.d, '_register', return_value=builder):
            self.prepared()
            self.packet['config']['parent_releases'] = []
            with self.assertRaisesRegex(ValueError, 'peer declarations'): self.prepared()
            self.packet['config']['parent_releases'] = derivative['parent_releases']
            changed = dict(job['config'], parent_releases=[])
            forged = build_profile(job['documents'], changed, backend)
            self.packet['profile'] = self.write('wrong-declarations.json', forged.to_dict())
            with self.assertRaisesRegex(ValueError, 'peer declarations'): self.prepared()

    def test_peer_opt_in_is_p7_derivative_only(self):
        derivative = self.peer_packet()
        self.bind_peer(derivative)
        self.packet['manifest']['method_id'] = self.packet['config']['method_id'] = 'P1'
        with self.assertRaises(ValueError): self.prepared()
        derivative['schema_version'] = self.batch['release_schema_version'] = 'released-development-v2'
        self.bind_peer(derivative)
        with self.assertRaises(ValueError): self.prepared()

    def test_env_parser_is_data_only_and_errors_hide_values(self):
        sentinel = self.base / 'must-not-exist'
        self.env.write_text("OTHER=$(touch ignored)\nexport OPENAI_API_KEY='$(touch %s)'\nOPENAI_ORG_ID=org-test # comment\n" % sentinel)
        values = self.d.read_credentials(self.env)
        self.assertEqual(values['OPENAI_API_KEY'], '$(touch %s)' % sentinel)
        self.assertEqual(values['OPENAI_ORG_ID'], 'org-test')
        self.assertNotIn('OTHER', values)
        self.assertFalse(sentinel.exists())
        self.env.write_text('OPENAI_API_KEY=first-secret\nOPENAI_API_KEY=second-secret\n')
        with self.assertRaises(ValueError) as raised: self.d.read_credentials(self.env)
        self.assertNotIn('secret', str(raised.exception))

    def test_runtime_rejects_other_checkout_and_wrong_commit(self):
        with self.assertRaises(ValueError): self.d.verify_runtime(self.base, self.sha)
        with self.assertRaises(ValueError): self.d.verify_runtime(ROOT, '0' * 40)

    def test_prepare_publishes_bound_packets_without_reading_env(self):
        self.env.unlink()
        prepared = self.prepared()
        ref = self.d.publish_prepared(prepared)
        with patch.object(self.d, 'verify_runtime'):
            restored = self.d.load_prepared(ref['path'], ref['sha256'])
        self.assertEqual(restored['jobs'][0]['manifest'], prepared['jobs'][0]['manifest'])
        self.assertEqual(restored['jobs'][0]['lease']['job_id'], prepared['jobs'][0]['manifest']['job_id'])
        with self.assertRaises(ValueError): self.d.load_prepared(ref['path'], 'f' * 64)

    def test_git_sha_dirty_files_and_outputs_in_git_rejected(self):
        self.batch['roots']['output'] = str(ROOT / 'should-not-write')
        with self.assertRaises(ValueError): self.prepared()
        repo = self.base / 'repo'
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()
        git('init')
        (repo / 'tracked.py').write_text('x = 1\n')
        git('add', 'tracked.py')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
        sha = git('rev-parse', 'HEAD')
        self.d.verify_checkout(repo, sha)
        with self.assertRaises(ValueError): self.d.verify_checkout(repo, '0' * 40)
        (repo / 'tracked.py').write_text('x = 2\n')
        with self.assertRaises(ValueError): self.d.verify_checkout(repo, sha)

    def test_two_workers_immutable_receipts_no_resume_and_env_restore(self):
        prepared = self.prepared(4)
        lock, active, peak = threading.Lock(), [0], [0]
        def run(manifest, lease, **kwargs):
            with lock:
                active[0] += 1
                peak[0] = max(active[0], peak[0])
            time.sleep(0.05)
            with lock: active[0] -= 1
            return {'job_id': manifest['job_id'], 'status': 'complete', 'counts': {'attempted': 1, 'complete': 1, 'error': 0}, 'usage': {'uncertain_attempts': 0}}
        with patch.object(self.d, 'run_job', run), patch.object(self.d, 'verify_runtime'), patch.dict(os.environ, {}, clear=True):
            result = self.d.execute_batch(prepared)
            self.assertEqual(peak[0], 2)
            self.assertEqual(result['counts']['complete'], 4)
            self.assertNotIn('OPENAI_API_KEY', os.environ)
            receipts = list(Path(self.batch['roots']['receipts']).rglob('receipt.json'))
            self.assertEqual(len(receipts), 4)
            self.assertNotIn('synthetic-unit-test-key', ''.join(p.read_text() for p in receipts))
            with self.assertRaises(FileExistsError): self.d.execute_batch(prepared)

    def test_uncertain_ledger_holds_and_records_all_skipped_jobs(self):
        self.batch['max_workers'] = 1
        prepared = self.prepared(3)
        called = []
        def run(manifest, lease, **kwargs):
            called.append(manifest['job_id'])
            ledger = prepared['ledger']
            reservation = ledger.reserve(0.001, {'test': True})
            ledger.finish(reservation, actual_usd=0, succeeded=False)
            return {'job_id': manifest['job_id'], 'status': 'partial', 'counts': {}, 'usage': {'uncertain_attempts': 1}}
        with patch.object(self.d, 'run_job', run), patch.object(self.d, 'verify_runtime'):
            result = self.d.execute_batch(prepared)
        self.assertEqual(len(called), 1)
        self.assertEqual(result['counts']['not_dispatched'], 2)
        self.assertTrue(result['ledger']['held_after_uncertain'])
        self.assertEqual(len(list(Path(self.batch['roots']['receipts']).rglob('receipt.json'))), 3)

    def test_invalid_later_packet_blocks_all_dispatch_and_credentials(self):
        self.batch['jobs'] = [self.write('good.json', self.packet), self.write('bad.json', {'schema_version': 'wrong'})]
        ref = self.write('batch.json', self.batch)
        with patch.object(self.d, 'verify_runtime'), patch.object(self.d, 'read_credentials') as credentials, patch('urllib.request.urlopen') as http:
            with self.assertRaises((ValueError, KeyError)):
                self.d.prepare_batch(ref['path'], ref['sha256'])
        credentials.assert_not_called()
        http.assert_not_called()

    def test_release_scope_and_schema_are_bound(self):
        self.batch['release_scope'] = 'not the approved release'
        with self.assertRaises(ValueError): self.prepared()
        self.batch['release_scope'] = 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel'
        self.batch['release_schema_version'] = 'confirmation-v1'
        with self.assertRaises(ValueError): self.prepared()

    def test_job_exception_is_secret_safe_and_stops_dispatch(self):
        self.batch['max_workers'] = 1
        prepared = self.prepared(2)
        def fail(*args, **kwargs):
            raise RuntimeError('SENSITIVE_EXCEPTION_VALUE')
        with patch.object(self.d, 'verify_runtime'), patch.object(self.d, 'run_job', fail):
            result = self.d.execute_batch(prepared)
        self.assertEqual(result['counts']['dispatched'], 1)
        self.assertEqual(result['counts']['not_dispatched'], 1)
        self.assertEqual(result['counts']['other'], 1)
        receipts = list(Path(self.batch['roots']['receipts']).rglob('receipt.json'))
        self.assertNotIn('SENSITIVE_EXCEPTION_VALUE', ''.join(p.read_text() for p in receipts))

    def test_pending_ledger_prevents_new_dispatch(self):
        prepared = self.prepared(2)
        prepared['ledger'].reserve(0.001, {'test': 'previous unfinished request'})
        with patch.object(self.d, 'verify_runtime'), patch.object(self.d, 'run_job') as runner:
            result = self.d.execute_batch(prepared)
        runner.assert_not_called()
        self.assertEqual(result['counts']['not_dispatched'], 2)
        self.assertEqual(result['ledger']['inflight'], 1)

    def test_real_runner_fake_http_and_profile_revalidation(self):
        prepared = self.prepared()
        with patch.object(self.d, 'verify_runtime'): result = self.d.execute_batch(prepared)
        self.assertEqual(result['counts']['complete'], 1)
        path = Path(self.batch['roots']['output']) / prepared['jobs'][0]['manifest']['job_id'] / 'profile.json'
        profile = json.loads(path.read_text())
        self.packet['profile'] = {'path': str(path), 'sha256': self.d.sha256_bytes(path.read_bytes())}
        self.packet['item_ids'] = ['i2', 'i1']
        self.packet['manifest']['kind'] = 'predict'
        self.packet['manifest'].pop('consumer')
        self.packet['config'] = {'method_implementation_hash': profile['method_implementation_hash'],
                                'renderer_implementation_hash': profile['renderer_implementation_hash'],
                                'profile_prompt_version': profile['prompt_version'], 'consumer_prompt_version': 'neutral-choice-v1',
                                'settings': {'temperature': 0.0, 'max_tokens': 32}}
        self.packet['backend']['max_calls'] = self.packet['manifest']['allocation']['max_calls'] = 2
        prepared = self.prepared()
        self.assertEqual([i['item_id'] for i in prepared['jobs'][0]['items']], ['i2', 'i1'])
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                return json.dumps({'status': 'completed', 'usage': {'input_tokens': 5, 'output_tokens': 5},
                    'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed', 'content': [{'type': 'output_text', 'text': '{"probabilities":[0.7,0.3],"rationale":"fixture"}'}]}]}).encode()
        with patch.object(self.d, 'verify_runtime'), patch('urllib.request.urlopen', return_value=Response()):
            result = self.d.execute_batch(prepared)
        self.assertEqual(result['counts']['complete'], 1)
        self.assertEqual(result['ledger']['attempts'], 2)
        body = json.loads(path.read_text())
        body['content'] = 'tampered'
        self.packet['profile'] = self.write('tampered-profile.json', body)
        with self.assertRaises(ValueError): self.prepared()


if __name__ == '__main__':
    unittest.main()
