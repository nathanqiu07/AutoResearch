"""Offline source, quote, projection and handoff boundary tests."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from autoresearch.taste.overnight.contracts import ProfileArtifact

try:
    from scripts.gio_recovery import rich_profiles as rich
except ModuleNotFoundError:
    rich = None


class RichProfilesTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(rich, 'The offline rich-profile builder is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.text = 'Prefer matched controls. Preserve negative results. In 2024 I changed my view.'
        self.bundle = {'schema_version': 'gio-source-bundle-v1', 'bundle_id': 'fixture',
                       'researchers': ['researcher'], 'sources': [{
                           'source_id': 'fit-1', 'researcher_id': 'researcher',
                           'author': 'researcher', 'title': 'Methodology', 'url': 'https://example.test/method',
                           'text': self.text, 'provenance': {
                               'role': 'fit', 'release_id': 'release-fixture',
                               'text_sha256': hashlib.sha256(self.text.encode()).hexdigest(),
                               'permitted_spans': [{'start': 0, 'end': len(self.text), 'speaker': 'researcher'}]}}]}
        self.bundle_path = self.root / 'bundle.json'
        self.save_bundle()
        self.response = {'hypotheses': [
            {'id': 'h1', 'weight': None, 'statement': self.statement('Prefer matched controls.', 'preference')},
            {'id': 'h2', 'weight': None, 'statement': self.statement('Preserve negative results.', 'belief')},
            {'id': 'h3', 'weight': None, 'statement': self.statement('Preserve negative results.', 'description', 'inferred', 'When designing an audit')}],
            'relations': [{'kind': 'extraction_uncertainty', 'hypothesis_ids': ['h1', 'h3'], 'statement': None},
                          {'kind': 'stated_change', 'hypothesis_ids': ['h1', 'h2'],
                           'statement': self.statement('In 2024 I changed my view.', 'description', date='2024')}]}

    def statement(self, quote, kind, evidence='explicit', conditions=None, date=None):
        return {'text': quote, 'kind': kind, 'evidence_status': evidence,
                'conditions': conditions, 'date': date,
                'sources': [{'document_id': 'fit-1', 'quote': quote}]}

    def save_bundle(self):
        self.bundle_path.write_text(json.dumps(self.bundle, indent=2))

    def build(self, response=None, **kwargs):
        p = self.root / 'response.json'
        p.write_text(json.dumps(self.response if response is None else response, indent=2))
        return rich.build_from_response(self.bundle_path, 'researcher', p,
                                        code_sha='a' * 40, **kwargs)

    def test_prepare_uses_exact_file_bytes_and_only_attributed_fit_segments(self):
        packet = rich.prepare_request(self.bundle_path, 'researcher')
        self.assertEqual(packet['source_bundle_digest'], hashlib.sha256(self.bundle_path.read_bytes()).hexdigest())
        self.assertIn(self.text, packet['prompt'])
        self.assertEqual(packet['api_calls'], 0)
        self.assertEqual(packet['source_manifest'][0]['document_id'], 'fit-1')
        self.bundle_path.write_text(self.bundle_path.read_text() + '\n')
        self.assertNotEqual(packet['source_bundle_digest'], rich.prepare_request(self.bundle_path, 'researcher')['source_bundle_digest'])

    def test_tampered_nonfit_unreleased_and_wrong_author_sources_rejected(self):
        original = copy.deepcopy(self.bundle)
        for mutation in ['text', 'role', 'release', 'researcher', 'speaker']:
            with self.subTest(mutation=mutation):
                self.bundle = copy.deepcopy(original)
                s = self.bundle['sources'][0]
                if mutation == 'text': s['text'] += 'tampered'
                if mutation == 'role': s['provenance']['role'] = 'test'
                if mutation == 'release': s['provenance']['release_id'] = ''
                if mutation == 'researcher': s['researcher_id'] = 'other'
                if mutation == 'speaker': s['provenance']['permitted_spans'][0]['speaker'] = 'other'
                self.save_bundle()
                with self.assertRaises(ValueError): rich.prepare_request(self.bundle_path, 'researcher')

    def test_quotes_resolve_locally_and_all_meanings_survive_projection(self):
        result = self.build()
        self.assertEqual(result['status'], 'complete')
        profile = ProfileArtifact.from_dict(result['artifact'])
        self.assertEqual(profile.content['hypotheses'][0]['statement']['sources'][0]['start'], 0)
        self.assertEqual(profile.content['hypotheses'][0]['statement']['sources'][0]['end'], 24)
        projection = result['handoff']['model_facing_text']
        for value in ['h1', 'h2', 'h3', 'preference', 'belief', 'description', 'inferred',
                      'When designing an audit', '2024', 'extraction_uncertainty', 'stated_change']:
            self.assertIn(value, projection)
        self.assertEqual(result['handoff']['schema_version'], 'gio-auditor-context-v1')
        self.assertEqual(result['handoff']['method_id'], 'rich-p8-task-v1')
        self.assertEqual(profile.method_id, 'P8')
        self.assertEqual(profile.config['builder_variant'], 'morning-task-rich-v1')
        self.assertEqual(result['handoff']['source_bundle_digest'], hashlib.sha256(self.bundle_path.read_bytes()).hexdigest())
        self.assertEqual(len(result['provenance']['citations']), 3)

    def test_external_response_does_not_claim_zero_total_execution_usage(self):
        usage = self.build()['artifact']['fit_usage']
        self.assertIsNone(usage['attempted_calls'])
        self.assertEqual(usage['offline_builder_api_calls'], 0)
        self.assertEqual(usage['execution_status'], 'externally_supplied_unverified')

    def test_missing_ambiguous_and_outside_span_quotes_rejected_without_repair(self):
        original = copy.deepcopy(self.bundle)
        for mode in ['missing', 'ambiguous', 'outside']:
            with self.subTest(mode=mode):
                self.bundle = copy.deepcopy(original)
                self.save_bundle()
                response = copy.deepcopy(self.response)
                if mode == 'missing': response['hypotheses'][0]['statement']['sources'][0]['quote'] = 'Not in source'
                if mode == 'ambiguous':
                    s = self.bundle['sources'][0]; s['text'] += ' Prefer matched controls.'
                    s['provenance']['text_sha256'] = hashlib.sha256(s['text'].encode()).hexdigest()
                    s['provenance']['permitted_spans'][0]['end'] = len(s['text']); self.save_bundle()
                if mode == 'outside':
                    self.bundle['sources'][0]['provenance']['permitted_spans'][0]['end'] = 24; self.save_bundle()
                result = self.build(response)
                self.assertEqual(result['status'], 'invalid')
                self.assertNotIn('handoff', result)

    def test_request_binding_rejects_drift_and_preserves_declared_settings(self):
        settings = {'model': 'test-extractor', 'max_tokens': 8192, 'temperature': 0.0}
        prepared = self.root / 'prepared-request'
        rich.prepare_request(self.bundle_path, 'researcher', out_dir=prepared, settings=settings)
        result = self.build(request_path=prepared / 'request.json')
        self.assertEqual(result['handoff']['settings'], settings)
        self.bundle_path.write_text(self.bundle_path.read_text() + '\n')
        with self.assertRaises(ValueError): self.build(request_path=prepared / 'request.json')

    def test_prepare_excludes_other_researcher_segments(self):
        self.bundle['researchers'].append('other')
        other = copy.deepcopy(self.bundle['sources'][0])
        other.update(source_id='other-fit', author='other', researcher_id='other', text='Other private methodology.')
        other['provenance']['text_sha256'] = hashlib.sha256(other['text'].encode()).hexdigest()
        other['provenance']['permitted_spans'] = [{'start': 0, 'end': len(other['text']), 'speaker': 'other'}]
        self.bundle['sources'].append(other); self.save_bundle()
        packet = rich.prepare_request(self.bundle_path, 'researcher')
        self.assertNotIn(other['text'], packet['prompt'])
        self.assertEqual(len(packet['source_manifest']), 1)

    def test_collaborative_attribution_reaches_extractor_as_source_data(self):
        source = self.bundle['sources'][0]
        source['authors'] = ['Researcher', 'Collaborator']
        source['provenance']['attribution_basis'] = 'Researcher wrote the essay; Collaborator helped frame and revise it.'
        source['provenance']['text_extent'] = 'Selected collaborative methodology section.'
        self.save_bundle()
        packet = rich.prepare_request(self.bundle_path, 'researcher')
        payload = json.loads(packet['prompt'].split('SOURCE DATA (JSON):\n', 1)[1])
        attribution = payload['sources'][0]['attribution']
        self.assertEqual(attribution['authors'], ['Researcher', 'Collaborator'])
        self.assertEqual(attribution['attribution_basis'], source['provenance']['attribution_basis'])
        self.assertEqual(attribution['text_extent'], source['provenance']['text_extent'])
        self.assertEqual(payload['sources'][0]['segments'][0]['start'], 0)
        self.assertEqual(payload['sources'][0]['segments'][0]['content'], self.text)

    def test_new_public_fit_scope_accepts_development_lineage_without_old_release(self):
        provenance = self.bundle['sources'][0]['provenance']
        provenance.pop('release_id')
        provenance.update(fit_scope='morning_petri_only', original_source_id='public-original-methodology',
                          attribution_basis='Author-owned article with verified byline.',
                          split_eligibility='dev', source_review_disposition='approved_morning_petri_only')
        self.save_bundle()
        packet = rich.prepare_request(self.bundle_path, 'researcher')
        self.assertEqual(packet['source_manifest'][0]['document_id'], 'fit-1')
        result = self.build()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['provenance']['sources'][0]['provenance']['split_eligibility'], 'dev')
        provenance.pop('fit_scope'); self.save_bundle()
        with self.assertRaises(ValueError): rich.prepare_request(self.bundle_path, 'researcher')

    def test_schema_weights_and_unsupported_change_rejected(self):
        for mode in ['weight', 'link', 'inferred_change']:
            with self.subTest(mode=mode):
                response = copy.deepcopy(self.response)
                if mode == 'weight': response['hypotheses'][0]['weight'] = 0.9
                if mode == 'link': response['relations'][0]['hypothesis_ids'][1] = 'absent'
                if mode == 'inferred_change': response['relations'][1]['statement']['evidence_status'] = 'inferred'
                self.assertEqual(self.build(response)['status'], 'invalid')

    def test_provenance_budget_is_separate_and_overflow_retains_full_candidate(self):
        first = self.build()
        self.bundle['sources'][0]['url'] += 'x' * 30000
        self.save_bundle()
        second = self.build(text_cap=len(first['handoff']['model_facing_text'].encode()))
        self.assertEqual(second['status'], 'complete')
        self.assertEqual(first['handoff']['model_facing_text'], second['handoff']['model_facing_text'])
        out = self.root / 'oversize'
        failed = self.build(text_cap=10, out_dir=out)
        self.assertEqual(failed['status'], 'invalid')
        self.assertEqual(failed['error_code'], 'model_facing_text_cap_exceeded')
        self.assertGreater(len((out / 'model-facing.txt').read_bytes()), 10)
        self.assertEqual(len(json.loads((out / 'candidate.json').read_text())['hypotheses']), 3)
        self.assertFalse((out / 'profile-handoff.json').exists())
        self.assertTrue((out / 'extraction-response.json').exists())

    def test_structured_cap_failure_keeps_candidate_and_no_handoff(self):
        result = self.build(structured_cap=10)
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(len(result['candidate']['hypotheses']), 3)
        self.assertNotIn('handoff', result)

    def test_outputs_never_overwrite_and_raw_response_bytes_retained(self):
        out = self.root / 'built'
        self.build(out_dir=out)
        self.assertEqual((out / 'extraction-response.json').read_bytes(), (self.root / 'response.json').read_bytes())
        handoff = json.loads((out / 'profile-handoff.json').read_text())
        self.assertEqual(handoff['structured_artifact_sha256'], hashlib.sha256((out / 'profile-original.json').read_bytes()).hexdigest())
        before = (out / 'profile-handoff.json').read_bytes()
        with self.assertRaises(FileExistsError): self.build(out_dir=out)
        self.assertEqual(before, (out / 'profile-handoff.json').read_bytes())

    def test_invalid_json_is_preserved_and_cli_runs_without_network(self):
        bad = self.root / 'bad.json'; bad.write_text('{broken')
        out = self.root / 'bad-output'
        result = rich.build_from_response(self.bundle_path, 'researcher', bad, code_sha='a' * 40, out_dir=out)
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual((out / 'extraction-response.json').read_bytes(), bad.read_bytes())
        done = subprocess.run([sys.executable, rich.__file__, 'prepare', '--bundle', str(self.bundle_path),
                               '--researcher', 'researcher', '--out-dir', str(self.root / 'prepared')],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.root / 'prepared' / 'request.json').exists())

    @unittest.skipUnless(os.environ.get('GIO_SAVED_P8_ADAPTER'), 'Optional existing downstream adapter path not supplied')
    def test_existing_saved_p8_exporter_accepts_complete_neutral_artifact(self):
        spec = importlib.util.spec_from_file_location('existing_p8_adapter', os.environ['GIO_SAVED_P8_ADAPTER'])
        adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
        out = self.root / 'compatible'; result = self.build(out_dir=out)
        p = out / 'profile-original.json'
        context = adapter.render_saved_p8_context(p, expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                    expected_profile_id=result['artifact']['profile_id'], expected_researcher_id='researcher', expected_replicate_id=0)
        self.assertTrue(context)


if __name__ == '__main__':
    unittest.main()
