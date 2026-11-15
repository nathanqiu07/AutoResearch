"""Synthetic own/swapped fixtures only; no corpus, credentials or network."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autoresearch.taste.overnight import consumer, runner
from autoresearch.taste.overnight.contracts import (backend_identity, build_profile,
    canonical_json, digest, sha256_bytes, source_manifest)
from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend
from autoresearch.taste.overnight.profiles_hypotheses import register_hypotheses_builders
from tests.test_overnight_profiles_hypotheses import document, quote_statement, Extractor

ORIGIN = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
RUNTIME = 'a' * 40
STUDY = 'exploratory-own-versus-swapped-p8-v1'
SCOPE = 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel'
PEOPLE = ('chris_olah', 'neel_nanda')


def raw(value):
    return (canonical_json(value) + '\n').encode()


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 11, 15, 9, tzinfo=timezone.utc)


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import cross_subject_assignment as assignment
        self.a = assignment
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for module in (runner, __import__('autoresearch.taste.overnight.backends', fromlist=['datetime'])):
            clock = patch.object(module, 'datetime', Clock)
            clock.start()
            self.addCleanup(clock.stop)
        register_hypotheses_builders()
        self.backend = OpenAIResponsesBackend(model='gpt-6-luna', reasoning='medium', timeout=60,
            ledger=DollarLedger(self.root / 'ledger.sqlite', max_usd=1,
                deadline='2026-11-15T17:00:00Z', max_inflight=2), max_usd=.2)
        self.releases, self.profiles = {}, {}
        for person in PEOPLE:
            docs = [document('synthetic-' + person, person, 'Synthetic preference for small tests.')]
            sources = source_manifest(docs)
            items = [dict(item_id=person + '-%02d' % i, researcher_id=person,
                context='Synthetic decision %d' % i, options=['Synthetic A', 'Synthetic B'],
                option_order_id='ab') for i in range(14)]
            self.releases[person] = dict(schema_version='released-development-v2', scope=SCOPE,
                researcher_id=person, sources=dict(documents=docs, source_manifest=sources,
                allowed_source_manifest_hash=digest(sources)), items=items, items_sha256=digest(items),
                target_bundle_sha256=digest({'synthetic_target': person}))
            cfg = dict(method_id='P8', researcher_id=person, allowed_sources=sources,
                allowed_source_manifest_hash=digest(sources), personalization_cap=8192,
                replicate_id=0, code_sha=ORIGIN, evidence_policy='explicit-only',
                extractor_settings=dict(temperature=0.0, max_tokens=16384))
            self.profiles[person] = build_profile(docs, cfg, Extractor({'hypotheses': [
                {'id': 'h1', 'statement': quote_statement(docs[0]), 'weight': None}], 'relations': []}))
        self.binding = dict(schema_version='exploratory-own-versus-swapped-p8-feasibility-binding-v1',
            frozen_runtime=ORIGIN, primary_config_id='P8-c8192-explicit-only',
            execution_authorized=False, final_test_authorized=False,
            consumer_and_settings=dict(consumer=backend_identity(self.backend),
                settings=dict(temperature=0.0, max_tokens=8192), timeout=60),
            profiles=[], swapped_prospective_bindings=[])
        for donor, target in (PEOPLE, PEOPLE[::-1]):
            profile, release = self.profiles[donor], self.releases[donor]
            pref = dict(path='/unused/' + donor, sha256=sha256_bytes(raw(profile.to_dict())))
            dref = dict(path='/unused/' + donor, sha256=sha256_bytes(raw(release)))
            tref = dict(path='/unused/' + target, sha256=sha256_bytes(raw(self.releases[target])))
            self.binding['profiles'].append(dict(researcher_id=donor, profile=pref,
                profile_id=profile.profile_id, fit_release=dref, donor_documents_hash=profile.documents_hash,
                donor_source_manifest_hash=profile.allowed_source_manifest_hash))
            for item in self.releases[target]['items']:
                self.binding['swapped_prospective_bindings'].append(dict(donor_researcher_id=donor,
                    target_researcher_id=target, donor_fit_release=dref, true_donor_profile=pref,
                    true_donor_profile_id=profile.profile_id, true_donor_documents_hash=profile.documents_hash,
                    true_donor_source_manifest_hash=profile.allowed_source_manifest_hash, target_release=tref,
                    target_bundle_sha256=self.releases[target]['target_bundle_sha256'],
                    target_items_sha256=self.releases[target]['items_sha256'], target_item_id=item['item_id'],
                    target_item_sha256=digest(item), target_option_order_id=item['option_order_id']))
        self.binding_sha = sha256_bytes(raw(self.binding))
        p = patch.object(self.a, 'BINDING_SHA256', self.binding_sha)
        p.start()
        self.addCleanup(p.stop)
        self.assignments = [self.declaration(d, t) for d, t in (PEOPLE, PEOPLE[::-1])]
        self.authority = dict(schema_version='own-swapped-p8-authorization-v1', state='authorized',
            authority='synthetic test only', scope=STUDY, binding_sha256=self.binding_sha,
            runtime_code_sha=RUNTIME, assignment_sha256s=sorted(digest(a) for a in self.assignments),
            max_calls=28, final_test_authorized=False)
        for a in self.assignments:
            a['authority_sha256'] = sha256_bytes(raw(self.authority))
        self.select()

    def declaration(self, donor, target):
        p, t = self.profiles[donor], self.releases[target]
        return dict(schema_version='declared-cross-subject-p8-v1', study=STUDY, condition='swapped',
            binding_sha256=self.binding_sha, donor_researcher_id=donor, target_researcher_id=target,
            profile_origin_code_sha=ORIGIN, donor_profile_id=p.profile_id,
            donor_profile_file_sha256=sha256_bytes(raw(p.to_dict())),
            donor_release_sha256=sha256_bytes(raw(self.releases[donor])), donor_documents_hash=p.documents_hash,
            donor_source_manifest_hash=p.allowed_source_manifest_hash,
            target_release_sha256=sha256_bytes(raw(t)), target_bundle_sha256=t['target_bundle_sha256'],
            target_items_sha256=t['items_sha256'], ordered_items=[dict(item_id=i['item_id'],
                item_sha256=digest(i), option_order_id=i['option_order_id']) for i in t['items']])

    def select(self, index=0):
        a = self.assignments[index]
        self.profile = self.profiles[a['donor_researcher_id']]
        self.items = self.releases[a['target_researcher_id']]['items']
        self.docs = self.releases[a['donor_researcher_id']]['sources']['documents']
        self.config = dict(method_implementation_hash=self.profile.method_implementation_hash,
            renderer_implementation_hash=consumer.implementation_hash(),
            profile_prompt_version=self.profile.prompt_version, consumer_prompt_version=consumer.PROMPT_VERSION,
            settings=dict(temperature=0.0, max_tokens=8192))
        self.evidence = dict(binding=raw(self.binding), authority=raw(self.authority),
            target_release=raw(self.releases[a['target_researcher_id']]),
            donor_release=raw(self.releases[a['donor_researcher_id']]), profile=raw(self.profile.to_dict()))
        self.manifest = dict(schema_version='overnight-job-v1', campaign_id='gio-profile-20261115',
            stage='dev', kind='predict', code_sha=RUNTIME, contract_sha256='c' * 64,
            deadline='2026-11-15T17:00:00Z', config_hash=digest(self.config), documents_hash=digest(self.docs),
            source_manifest_hash=self.profile.allowed_source_manifest_hash, items_hash=digest(self.items),
            profile_hash=self.profile.profile_id, method_id='P8', personalization_cap=8192,
            extractor=self.profile.extractor, consumer=backend_identity(self.backend), replicate_id=0,
            allocation=dict(max_calls=14, max_seconds=1380, max_usd=.2, cost_mode='priced_api',
                authorization_source=a['authority_sha256']), retry_policy=dict(max_attempts=1, retry_uncertain=False),
            parent_job_ids=[], expected_outputs=['result.json', 'traces'], profile_assignment=copy.deepcopy(a),
            option_order_schedule=[dict(item_id=i['item_id'], option_order_id=i['option_order_id']) for i in self.items])
        self.rehash()

    def rehash(self):
        self.manifest['job_id'] = runner.job_id(self.manifest)
        self.lease = dict(job_id=self.manifest['job_id'], lease_id='synthetic', owner='test',
            expires_at='2026-11-15T17:00:00Z')

    def validate(self):
        return runner._validate(self.manifest, self.lease, self.config, self.profile,
            self.items, self.docs, assignment_evidence=self.evidence)

    def test_exact_assignment_passes_without_changing_artifact_or_payload(self):
        before = raw(self.profile.to_dict())
        expected = consumer.prepare_payload(self.profile, self.items[0]['context'], self.items[0]['options'], self.config)
        self.validate()
        self.assertEqual(before, self.evidence['profile'])
        self.assertEqual(before, raw(self.profile.to_dict()))
        self.assertEqual(set(expected['payload']), {'context', 'options', 'personalization'})

    def test_ordinary_cross_subject_and_one_sided_evidence_reject(self):
        del self.manifest['profile_assignment']
        self.rehash()
        with self.assertRaises(ValueError): self.validate()
        self.evidence = None
        with self.assertRaisesRegex(ValueError, 'researcher mismatch'): self.validate()

    def test_changed_declaration_fields_reject_before_claim(self):
        original = copy.deepcopy(self.manifest)
        for field in self.assignments[0]:
            with self.subTest(field=field):
                self.manifest = copy.deepcopy(original)
                self.manifest['profile_assignment'][field] = 'wrong'
                self.rehash()
                with self.assertRaises(ValueError): self.validate()
        self.assertFalse((self.root / 'leases').exists())

    def test_any_changed_or_missing_raw_evidence_rejects(self):
        original = dict(self.evidence)
        for key in original:
            for mode in ('changed', 'missing'):
                with self.subTest(key=key, mode=mode):
                    self.evidence = dict(original)
                    if mode == 'changed': self.evidence[key] += b' '
                    else: del self.evidence[key]
                    with self.assertRaises(ValueError): self.validate()

    def test_wrong_stage_method_origin_items_and_sources_reject(self):
        original = copy.deepcopy(self.manifest)
        for field, value in [('stage', 'confirmation'), ('kind', 'build'), ('method_id', 'P7'),
                ('personalization_cap', 2048), ('replicate_id', 1), ('documents_hash', '0' * 64),
                ('code_sha', ORIGIN), ('consumer', {})]:
            self.manifest = copy.deepcopy(original)
            self.manifest[field] = value
            self.rehash()
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate()
        self.manifest = original
        self.items = self.items[::-1]
        self.manifest['items_hash'] = digest(self.items)
        self.manifest['option_order_schedule'] = [dict(item_id=i['item_id'], option_order_id=i['option_order_id']) for i in self.items]
        self.rehash()
        with self.assertRaises(ValueError): self.validate()

    def test_batch_requires_both_complete_complementary_jobs(self):
        jobs = []
        for index in range(2):
            self.select(index)
            jobs.append(dict(manifest=copy.deepcopy(self.manifest)))
        self.a.validate_assignment_batch(jobs, 28)
        for bad in ([jobs[0]], jobs + [jobs[0]], [jobs[0], jobs[0]], [jobs[0], {'manifest': {}}]):
            with self.assertRaises(ValueError): self.a.validate_assignment_batch(bad, 28)
        with self.assertRaises(ValueError): self.a.validate_assignment_batch(jobs, 29)

    def driver_fixture(self):
        path = Path(__file__).resolve().parents[1] / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
        spec = importlib.util.spec_from_file_location('cross_subject_driver_test', path)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        for name, value in [('datetime', Clock), ('verify_runtime', lambda *args: None)]:
            p = patch.object(driver, name, value)
            p.start()
            self.addCleanup(p.stop)

        def write(name, value):
            destination = self.root / name
            destination.write_bytes(value if type(value) is bytes else raw(value))
            return dict(path=str(destination), sha256=sha256_bytes(destination.read_bytes()))

        self.write = write
        packets = []
        for index in range(2):
            self.select(index)
            packet = dict(schema_version='overnight-packet-v1', manifest=copy.deepcopy(self.manifest),
                lease=dict(self.lease, lease_id='synthetic-%d' % index), config=copy.deepcopy(self.config),
                item_ids=[i['item_id'] for i in self.items],
                release=write('target-%d.json' % index, self.evidence['target_release']),
                profile=write('profile-%d.json' % index, self.evidence['profile']),
                profile_source_release=write('donor-%d.json' % index, self.evidence['donor_release']),
                assignment_binding=write('binding-%d.json' % index, self.evidence['binding']),
                assignment_authority=write('authority-%d.json' % index, self.evidence['authority']),
                backend=dict(model='gpt-6-luna', reasoning='medium', timeout=60,
                    max_calls=14, max_seconds=1380, max_usd=.2),
                registration=dict(module='autoresearch.taste.overnight.profiles_hypotheses',
                    function='register_hypotheses_builders'))
            # Native preparation fills these computable fields from the batch.
            for key in ('contract_sha256', 'job_id'):
                packet['manifest'].pop(key)
            packet['lease'].pop('job_id')
            packets.append(packet)
        batch = dict(schema_version='overnight-batch-v1', campaign_id='gio-profile-20261115',
            code_sha=RUNTIME, deadline='2026-11-15T17:00:00Z', max_workers=2, max_total_attempts=28,
            runtime_root=str(path.parents[4]), release_schema_version='released-development-v2',
            release_scope=SCOPE, contract=write('contract.json', {'synthetic': True}),
            env_file=str(self.root / 'DO_NOT_READ.env'),
            ledger=dict(path=str(self.root / 'ledger.sqlite'), max_usd=1, max_inflight=2),
            roots={k: str(self.root / k) for k in ('output', 'lease', 'cache', 'receipts')}, jobs=[])
        return driver, batch, packets

    def prepare(self, driver, batch, packets):
        batch['jobs'] = [self.write('packet-%d.json' % i, p) for i, p in enumerate(packets)]
        ref = self.write('batch.json', batch)
        return driver.prepare_batch(ref['path'], ref['sha256'])

    def test_driver_snapshots_reload_after_original_evidence_deleted(self):
        d, batch, packets = self.driver_fixture()
        prepared = self.prepare(d, batch, packets)
        result = d.publish_prepared(prepared)
        before = [j['manifest']['job_id'] for j in prepared['jobs']]
        for packet in packets:
            for field in ('release', 'profile', 'profile_source_release', 'assignment_binding', 'assignment_authority'):
                Path(packet[field]['path']).unlink()
        loaded = d.load_prepared(result['path'], result['sha256'])
        self.assertEqual(before, [j['manifest']['job_id'] for j in loaded['jobs']])
        for job in loaded['jobs']:
            self.assertEqual(job['documents'], self.releases[job['profile'].researcher_id]['sources']['documents'])
            self.assertNotEqual(job['profile'].researcher_id, job['items'][0]['researcher_id'])
        self.assertFalse(Path(batch['env_file']).exists())
        self.assertFalse(Path(batch['roots']['lease']).exists())

    def test_driver_rejects_partial_extra_or_unbound_assignment(self):
        d, batch, packets = self.driver_fixture()
        with self.assertRaises(ValueError): self.prepare(d, batch, packets[:1])
        for field in ('profile_source_release', 'assignment_binding', 'assignment_authority'):
            changed = copy.deepcopy(packets)
            del changed[0][field]
            with self.subTest(field=field), self.assertRaises(ValueError): self.prepare(d, batch, changed)
        changed = copy.deepcopy(packets)
        del changed[0]['manifest']['profile_assignment']
        with self.assertRaises(ValueError): self.prepare(d, batch, changed)
        changed = copy.deepcopy(packets)
        changed[0]['backend']['timeout'] = 59
        with self.assertRaises(ValueError): self.prepare(d, batch, changed)

    def test_runner_real_adapter_fake_http_preserves_wire_and_metadata(self):
        d, batch, packets = self.driver_fixture()
        prepared = self.prepare(d, batch, packets)
        sent, reads = [], []
        response = raw(dict(status='completed', output=[dict(type='message', role='assistant', status='completed', content=[dict(type='output_text',
            text='{"probabilities":[0.6,0.4],"rationale":"synthetic"}')])],
            usage=dict(input_tokens=10, output_tokens=10)))

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): reads.append('closed')
            def read(self, size):
                reads.append(size)
                return response

        def transport(request, timeout):
            sent.append((request.data, timeout))
            return Response()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-test-only'}, clear=True), \
                patch('urllib.request.urlopen', side_effect=transport):
            results = [d._execute_one(job, prepared) for job in prepared['jobs']]
        self.assertEqual(len(sent), 28)
        self.assertEqual(reads, [8_000_001, 'closed'] * 28)
        cursor = 0
        for job, result in zip(prepared['jobs'], results):
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(result['usage']['attempted_calls'], 14)
            self.assertEqual(result['usage']['cache_hits'], 0)
            self.assertEqual(result['profile_assignment'], job['manifest']['profile_assignment'])
            for item, row in zip(job['items'], result['predictions']):
                body = json.loads(sent[cursor][0])
                payload = consumer.prepare_payload(job['profile'], item['context'], item['options'], job['config'])
                self.assertEqual(body['input'], payload['prompt'])
                self.assertEqual(body['instructions'], payload['system'])
                self.assertEqual(sent[cursor][1], 60)
                self.assertEqual(row['target_researcher_id'], item['researcher_id'])
                self.assertEqual(row['donor_researcher_id'], job['profile'].researcher_id)
                self.assertEqual(row['option_order_id'], item['option_order_id'])
                cursor += 1

    def test_runner_rejects_evidence_tampering_before_claim_or_transport(self):
        self.evidence['authority'] += b' '
        with patch('urllib.request.urlopen') as transport, self.assertRaises(ValueError):
            runner.run_job(self.manifest, self.lease, output_root=self.root / 'output',
                lease_root=self.root / 'leases', config=self.config, profile=self.profile,
                items=self.items, documents=self.docs, consumer=self.backend, assignment_evidence=self.evidence)
        transport.assert_not_called()
        self.assertFalse((self.root / 'leases').exists())

    def test_rehashed_but_unapproved_authority_cannot_admit_swaps(self):
        for field, value in [('state', 'proposed'), ('runtime_code_sha', ORIGIN),
                ('binding_sha256', '0' * 64), ('assignment_sha256s', []), ('max_calls', 29),
                ('final_test_authorized', True), ('scope', 'other'), ('authority', '')]:
            changed = dict(self.authority, **{field: value})
            self.evidence['authority'] = raw(changed)
            self.manifest['profile_assignment']['authority_sha256'] = sha256_bytes(raw(changed))
            self.manifest['allocation']['authorization_source'] = sha256_bytes(raw(changed))
            self.rehash()
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate()

    def test_assignment_cannot_change_campaign_deadline_or_cost_mode(self):
        original = copy.deepcopy(self.manifest)
        for field, value in [('campaign_id', 'different'), ('deadline', '2099-01-01T00:00:00Z')]:
            self.manifest = copy.deepcopy(original)
            self.manifest[field] = value
            self.rehash()
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate()
        self.manifest = copy.deepcopy(original)
        self.manifest['allocation']['cost_mode'] = 'unpriced_cli'
        self.rehash()
        with self.assertRaises(ValueError): self.validate()

    def test_direct_runner_rejects_changed_timeout_before_claim(self):
        self.backend.timeout = 59
        with patch('urllib.request.urlopen') as transport, self.assertRaises(ValueError):
            runner.run_job(self.manifest, self.lease, output_root=self.root / 'output',
                lease_root=self.root / 'leases', config=self.config, profile=self.profile,
                items=self.items, documents=self.docs, consumer=self.backend, assignment_evidence=self.evidence)
        transport.assert_not_called()
        self.assertFalse((self.root / 'leases').exists())


if __name__ == '__main__':
    unittest.main()
