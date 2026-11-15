"""Synthetic tests of scaling comparability; these do not measure model quality."""
import copy
import json
import unittest
from pathlib import Path

from autoresearch.taste.overnight.contracts import digest, ProfileArtifact

ROOT = Path(__file__).resolve().parents[1]


def synthetic_inputs():
    fixture = json.loads((ROOT / 'docs/overnight/gio-profile-20261115/infrastructure/fixture-v3.json').read_text())
    models = []
    for level in ('S', 'M', 'L'):
        models.append({'level': level, 'status': 'available', 'identity': {
            'class': 'SyntheticBackend', 'label': 'offline-synthetic:' + level,
            'model': 'synthetic-' + level, 'endpoint': ''},
            'model_revision': 'synthetic-v1',
            'settings': {'temperature': 0.0, 'max_tokens': 128},
            'adapter_sha256': 'a' * 64, 'verification_sha256': 'b' * 64})
    methods, profiles = [], []
    for method_id in ('synthetic-primary', 'synthetic-secondary'):
        methods.append({'method_id': method_id, 'config_hashes': {},
                        'method_implementation_hash': fixture['profile']['method_implementation_hash'],
                        'profile_prompt_version': 'synthetic-v1',
                        'profile_prompt_sha256': fixture['profile']['prompt_sha256']})
        for model in models:
            body = copy.deepcopy(fixture['profile'])
            body.update(method_id=method_id, extractor=model['identity'],
                        extractor_settings=model['settings'])
            body['config'].update(method_id=method_id, extractor_settings=model['settings'])
            body['config_id'] = digest(body['config'])
            methods[-1]['config_hashes'][model['level']] = body['config_id']
            body.pop('profile_id')
            body['profile_id'] = digest(body)
            profiles.append({'method_id': method_id, 'extractor_level': model['level'],
                             'profile': ProfileArtifact.from_dict(body).to_dict()})
    spec = {'schema_version': 'overnight-scaling-design-v1', 'campaign_id': 'synthetic-campaign',
            'stage': 'offline', 'contract_sha256': 'c' * 64, 'code_sha': 'd' * 40,
            'panel_id': 'synthetic-panel', 'panel_kind': 'offline',
            'axis': 'declared-model-level-not-parameter-count', 'models': models,
            'common': {'items': [
                {'item_id': 'synthetic-item-1', 'option_order_id': 'ab',
                 'context_sha256': '1' * 64, 'options_sha256': '2' * 64},
                {'item_id': 'synthetic-item-2', 'option_order_id': 'ba',
                 'context_sha256': '3' * 64, 'options_sha256': '4' * 64}],
                'items_hash': '5' * 64, 'task_context_hash': '6' * 64,
                'allowed_source_manifest_hash': fixture['profile']['allowed_source_manifest_hash'],
                'personalization_cap': 2048, 'context_cap': 8192,
                'cap_unit': 'utf8-bytes-upper-bound-v1', 'truncation_rule': 'reject-no-drop',
                'settings': {'temperature': 0.0, 'max_tokens': 128},
                'renderer_implementation_hash': fixture['profile']['renderer_implementation_hash'],
                'consumer_prompt_version': 'neutral-choice-v1', 'consumer_prompt_sha256': '7' * 64,
                'researcher_id': 'synthetic', 'outcome_panel': 'fidelity'},
            'methods': methods, 'primary_method_id': 'synthetic-primary',
            'fixed_profile': {'method_id': 'synthetic-primary', 'extractor_level': 'S'},
            'controls': [
                {'method_id': 'synthetic-none', 'kind': 'no_profile',
                 'implementation_sha256': '8' * 64, 'config_hash': '9' * 64},
                {'method_id': 'synthetic-raw', 'kind': 'raw_evidence',
                 'implementation_sha256': 'a' * 64, 'config_hash': 'b' * 64}],
            'diagnostic': {'items': [{'item_id': 'synthetic-archival-1', 'option_order_id': 'ab',
                'context_sha256': 'c' * 64, 'options_sha256': 'd' * 64}],
                'items_hash': 'e' * 64, 'task_context_hash': 'f' * 64,
                'raw_evidence_hash': '0' * 64, 'subset_manifest_hash': '1' * 64,
                'recorded_judgment_manifest_hash': '2' * 64, 'withholding_receipt_hash': '3' * 64,
                'label_tier': 'documented-judgment', 'profile_conditioning': False},
            'deviations': []}
    return spec, profiles


class ScalingManifestTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import scaling
        self.scaling = scaling
        self.spec, self.profiles = synthetic_inputs()

    def build(self):
        return self.scaling.build_manifest(self.spec, self.profiles)

    def test_matrix_distinguishes_studies_and_deduplicates_only_identical_cells(self):
        manifest = self.build()
        # 12 joint + 3 fixed consumer + 4 cross + 3 inference arms.
        self.assertEqual(len(manifest['arms']), 22)
        # Cross S/S,L/L reuse joint; fixed S reuses joint S/S;
        # cross S/L reuses fixed L. No extra execution for those four aliases.
        self.assertEqual(len(manifest['cells']), 18)
        arms = {a['arm_id']: a for a in manifest['arms']}
        self.assertEqual(arms['A/synthetic-primary/S']['cell_id'], arms['C/S/S']['cell_id'])
        self.assertEqual(arms['B/S']['cell_id'], arms['A/synthetic-primary/S']['cell_id'])
        self.assertEqual(arms['B/L']['cell_id'], arms['C/S/L']['cell_id'])
        self.assertEqual({a['estimand'] for a in manifest['arms']}, {
            'joint-extraction-consumer', 'matched-control', 'fixed-profile-consumer',
            'extractor-consumer-cross', 'raw-evidence-judgment-inference'})
        for cell in manifest['cells']:
            if cell['conditioning']['kind'] != 'archival_raw_evidence':
                self.assertEqual(cell['common']['items'], self.spec['common']['items'])
        self.assertEqual(manifest['authorization'], 'none-manifest-only')

    def test_fixed_profile_content_is_exact_and_no_weights_transfer(self):
        manifest = self.build()
        cells = {c['cell_id']: c for c in manifest['cells']}
        fixed = [cells[a['cell_id']]['conditioning'] for a in manifest['arms'] if a['study'] == 'B']
        self.assertEqual(len({p['profile_id'] for p in fixed}), 1)
        self.assertEqual(len({p['content_sha256'] for p in fixed}), 1)
        changed = copy.deepcopy(self.profiles)
        changed[0]['profile']['content']['prose'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.scaling.build_manifest(self.spec, changed)
        legacy = {'kind': 'backend_bound', 'backend': self.spec['models'][0]['identity']}
        self.scaling.validate_consumer_binding(legacy, self.spec['models'][0]['identity'])
        with self.assertRaisesRegex(ValueError, 'backend-bound'):
            self.scaling.validate_consumer_binding(legacy, self.spec['models'][2]['identity'])
        changed = copy.deepcopy(self.profiles)
        changed[0]['profile']['weights_status'] = 'learned'
        changed[0]['profile'].pop('profile_id')
        changed[0]['profile']['profile_id'] = digest(changed[0]['profile'])
        with self.assertRaisesRegex(ValueError, 'weights|calibration'):
            self.scaling.build_manifest(self.spec, changed)

    def test_late_arm_or_input_changes_rejected_even_after_rehash(self):
        original = self.build()
        for change in ('drop', 'extra', 'items', 'order', 'context', 'cap', 'settings', 'profile'):
            altered = copy.deepcopy(original)
            if change == 'drop':
                altered['arms'].pop()
            elif change == 'extra':
                altered['arms'].append(dict(altered['arms'][0], arm_id='unregistered'))
            else:
                cell = altered['cells'][0]
                if change == 'items': cell['common']['items'].reverse()
                if change == 'order': cell['common']['items'][0]['option_order_id'] = 'ba'
                if change == 'context': cell['common']['task_context_hash'] = '0' * 64
                if change == 'cap': cell['common']['personalization_cap'] = 512
                if change == 'settings': cell['consumer']['settings']['max_tokens'] = 256
                if change == 'profile': cell['conditioning']['content_sha256'] = '0' * 64
            altered['manifest_sha256'] = self.scaling.manifest_hash(altered)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.scaling.validate_manifest(altered, expected_manifest_hash=original['manifest_sha256'])
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.scaling.validate_manifest(altered)

    def test_external_digest_rejects_a_coherently_rebuilt_late_design(self):
        original = self.build()
        self.spec['common']['items'].reverse()
        changed = self.build()
        # A new self-consistent document is valid as a new plan, never as the old freeze.
        self.scaling.validate_manifest(changed)
        with self.assertRaisesRegex(ValueError, 'external freeze'):
            self.scaling.validate_manifest(changed, expected_manifest_hash=original['manifest_sha256'])

    def test_planned_missing_model_keeps_all_arms_and_separates_failure(self):
        self.spec['models'][1] = {'level': 'M', 'status': 'unavailable', 'reason': 'not verified'}
        self.profiles = [p for p in self.profiles if p['extractor_level'] != 'M']
        for method in self.spec['methods']:
            method['config_hashes'].pop('M')
        manifest = self.build()
        missing = [a for a in manifest['arms'] if a['status'] == 'planned-unavailable']
        self.assertEqual(len(missing), 6)
        self.assertEqual(len(manifest['arms']), 22)
        self.assertTrue(all(a['reason'] == 'M: not verified' for a in missing))
        inventory = self.scaling.result_inventory(manifest, [], expected_manifest_hash=manifest['manifest_sha256'])
        self.assertEqual(sum(row['status'] == 'planned-unavailable' for row in inventory), 6)
        self.assertEqual(sum(row['status'] == 'missing-result' for row in inventory), 16)

    def test_settings_deviations_and_transports_must_be_explicit(self):
        self.spec['models'][1]['settings']['temperature'] = 0.5
        with self.assertRaisesRegex(ValueError, 'deviation'):
            self.build()
        self.spec['deviations'] = [{'level': 'M', 'field': 'temperature', 'expected': 0.0,
                                    'actual': 0.5, 'reason': 'synthetic unsupported setting'}]
        for record in self.profiles:
            if record['extractor_level'] == 'M':
                profile = record['profile']
                profile['extractor_settings']['temperature'] = 0.5
                profile['config']['extractor_settings']['temperature'] = 0.5
                profile['config_id'] = digest(profile['config'])
                method = next(m for m in self.spec['methods'] if m['method_id'] == record['method_id'])
                method['config_hashes']['M'] = profile['config_id']
                profile.pop('profile_id')
                profile['profile_id'] = digest(profile)
        manifest = self.build()
        self.assertEqual(len(manifest['deviations']), 1)
        self.spec['models'][1]['identity']['label'] = 'codex-cli:synthetic-M'
        with self.assertRaisesRegex(ValueError, 'panel|transport'):
            self.build()

    def test_diagnostic_has_raw_evidence_and_independent_recorded_judgments(self):
        manifest = self.build()
        diagnostic = [c for c in manifest['cells'] if c['conditioning']['kind'] == 'archival_raw_evidence']
        self.assertEqual(len(diagnostic), 3)
        self.assertTrue(all('profile_id' not in c['conditioning'] for c in diagnostic))
        for key, value in [('label_tier', 'inferred'), ('profile_conditioning', True),
                           ('withholding_receipt_hash', None)]:
            altered = copy.deepcopy(self.spec)
            altered['diagnostic'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.scaling.build_manifest(altered, self.profiles)

    def test_result_join_rejects_unknown_duplicate_changed_and_omitted_items(self):
        manifest = self.build()
        first = manifest['cells'][0]
        record = {'cell_id': first['cell_id'], 'status': 'failed', 'reason': 'synthetic error',
                  'items': [], 'usage': {'attempted_calls': 1, 'cost_status': 'unavailable'}}
        rows = self.scaling.result_inventory(manifest, [record], expected_manifest_hash=manifest['manifest_sha256'])
        self.assertEqual(sum(r['status'] == 'failed' for r in rows), 3)
        for records in ([record, record], [dict(record, cell_id='unknown')],
                        [dict(record, status='complete')]):
            with self.assertRaises(ValueError):
                self.scaling.result_inventory(manifest, records, expected_manifest_hash=manifest['manifest_sha256'])

    def test_summary_pairs_raw_baseline_and_keeps_missing_cells_items_and_cost(self):
        manifest = self.build()
        arms = {a['arm_id']: a for a in manifest['arms']}
        cells = {c['cell_id']: c for c in manifest['cells']}
        results = []
        for arm_id, scores in [('A/synthetic-primary/S', [1.0, 0.0]),
                               ('A/synthetic-raw/S', [0.0, 0.0])]:
            cell_id = arms[arm_id]['cell_id']
            rows = [dict(item, status='complete', score=score)
                    for item, score in zip(cells[cell_id]['common']['items'], scores)]
            results.append({'cell_id': cell_id, 'status': 'complete', 'reason': None,
                            'items': rows, 'usage': {'attempted_calls': 2,
                            'reported_api_usd': 0.1, 'cost_status': 'measured'}})
        summary = self.scaling.summarize_results(
            manifest, results, expected_manifest_hash=manifest['manifest_sha256'])
        self.assertEqual(len(summary['arms']), 22)
        self.assertEqual(len(summary['cells']), 18)
        self.assertEqual(summary['usage']['attempted_calls'], 4)
        self.assertAlmostEqual(summary['usage']['reported_api_usd'], 0.2)
        by_arm = {r['arm_id']: r for r in summary['arms']}
        primary = by_arm['A/synthetic-primary/S']
        self.assertEqual(primary['absolute']['available_case_mean'], 0.5)
        self.assertEqual(primary['personalization_gain']['paired_mean'], 0.5)
        self.assertEqual([p['difference'] for p in primary['personalization_gain']['items']], [1.0, 0.0])
        self.assertEqual(by_arm['A/synthetic-secondary/S']['status'], 'missing-result')
        self.assertEqual(by_arm['A/synthetic-secondary/S']['personalization_gain']['unpaired_count'], 2)
        self.assertIsNone(by_arm['D/S']['personalization_gain'])
        self.assertEqual(primary['outcome_panel'], 'fidelity')
        # One failed item cannot disappear into a successful cell or acquire a score.
        results[0]['status'] = 'partial'
        results[0]['reason'] = 'one failed prediction'
        results[0]['items'][1].update(status='failed', score=None)
        summary = self.scaling.summarize_results(manifest, results,
                    expected_manifest_hash=manifest['manifest_sha256'])
        primary = next(r for r in summary['arms'] if r['arm_id'] == 'A/synthetic-primary/S')
        self.assertEqual(primary['absolute']['failed_count'], 1)
        self.assertEqual(primary['personalization_gain']['paired_count'], 1)
        self.assertEqual(primary['personalization_gain']['unpaired_count'], 1)

    def test_result_usage_unknown_cost_and_bad_score_remain_visible(self):
        manifest = self.build()
        cell = manifest['cells'][0]
        result = {'cell_id': cell['cell_id'], 'status': 'failed', 'reason': 'failed',
                  'items': [], 'usage': {'attempted_calls': 1, 'cost_status': 'unavailable'}}
        summary = self.scaling.summarize_results(manifest, [result],
                    expected_manifest_hash=manifest['manifest_sha256'])
        self.assertIsNone(summary['usage']['reported_api_usd'])
        self.assertEqual(summary['usage']['cost_status'], 'unavailable')
        result['usage']['reported_api_usd'] = 0.0
        summary = self.scaling.summarize_results(manifest, [result],
                    expected_manifest_hash=manifest['manifest_sha256'])
        self.assertIsNone(summary['usage']['reported_api_usd'])
        self.assertEqual(summary['usage']['cost_status'], 'unavailable')
        result['items'] = [dict(cell['common']['items'][0], status='failed', score=1.0)]
        with self.assertRaisesRegex(ValueError, 'failed item'):
            self.scaling.summarize_results(manifest, [result],
                    expected_manifest_hash=manifest['manifest_sha256'])

    def test_empty_candidate_and_undeclared_config_are_rejected(self):
        for change in ('empty', 'config'):
            spec, profiles = synthetic_inputs()
            profile = profiles[0]['profile']
            if change == 'empty':
                profile.update(content={}, content_sha256=digest({}), token_count=0)
            else:
                profile['config']['new_method_setting'] = 'undeclared'
                profile['config_id'] = digest(profile['config'])
            profile.pop('profile_id')
            profile['profile_id'] = digest(profile)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.scaling.build_manifest(spec, profiles)

    def test_backend_enforced_settings_cannot_contradict_declared_settings(self):
        self.spec['models'][0]['identity']['enforced_settings'] = {'temperature': 0.9}
        with self.assertRaisesRegex(ValueError, 'enforced'):
            self.build()

    def test_planned_profile_unavailability_keeps_other_models_and_controls(self):
        original = self.profiles[0]
        self.profiles[0] = {'method_id': original['method_id'], 'extractor_level': 'S',
                            'status': 'planned-unavailable', 'reason': 'empty extraction',
                            'evidence_sha256': digest(original['profile'])}
        manifest = self.build()
        arms = {a['arm_id']: a for a in manifest['arms']}
        self.assertEqual(arms['A/synthetic-primary/S']['status'], 'planned-unavailable')
        self.assertEqual(arms['A/synthetic-secondary/S']['status'], 'planned')
        self.assertEqual(arms['A/synthetic-raw/S']['status'], 'planned')
        self.assertEqual(arms['B/L']['status'], 'planned-unavailable')
        self.assertEqual(arms['C/S/L']['status'], 'planned-unavailable')
        self.assertEqual(arms['C/L/S']['status'], 'planned')
        self.assertEqual(len(manifest['arms']), 22)
        summary = self.scaling.summarize_results(manifest, [],
                    expected_manifest_hash=manifest['manifest_sha256'])
        unavailable = next(a for a in summary['arms'] if a['arm_id'] == 'B/L')
        self.assertEqual(unavailable['reason'], 'empty extraction')
        self.assertEqual(unavailable['absolute']['planned_unavailable_count'], 2)
        self.assertEqual(unavailable['absolute']['missing_count'], 0)

    def test_empty_and_unsupported_results_remain_visible(self):
        manifest = self.build()
        cell = manifest['cells'][0]
        result = {'cell_id': cell['cell_id'], 'status': 'partial', 'reason': 'empty consumer output',
                  'items': [dict(cell['common']['items'][0], status='empty', score=None),
                            dict(cell['common']['items'][1], status='unsupported', score=None)],
                  'usage': {'attempted_calls': 2, 'cost_status': 'unavailable'}}
        rows = self.scaling.result_inventory(manifest, [result],
                    expected_manifest_hash=manifest['manifest_sha256'])
        self.assertEqual(rows[0]['result']['items'][0]['status'], 'empty')
        self.assertEqual(rows[0]['result']['items'][1]['status'], 'unsupported')

    def test_joint_extraction_replicates_cannot_change_across_levels(self):
        profile = self.profiles[1]['profile']
        profile['replicate_id'] = 9
        profile['config']['replicate_id'] = 9
        profile['config_id'] = digest(profile['config'])
        self.spec['methods'][0]['config_hashes']['M'] = profile['config_id']
        profile.pop('profile_id')
        profile['profile_id'] = digest(profile)
        with self.assertRaisesRegex(ValueError, 'replicate'):
            self.build()

    def test_design_rejects_undeclared_fields_and_wrong_profile_provenance(self):
        for mutate in ('extra', 'method', 'researcher', 'source', 'cap'):
            spec, profiles = synthetic_inputs()
            if mutate == 'extra': spec['diagnostic']['chosen'] = 'a'
            if mutate == 'method': profiles[0]['method_id'] = 'wrong'
            if mutate == 'researcher': spec['common']['researcher_id'] = 'other'
            if mutate == 'source': spec['common']['allowed_source_manifest_hash'] = '0' * 64
            if mutate == 'cap': spec['common']['personalization_cap'] = 512
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.scaling.build_manifest(spec, profiles)


if __name__ == '__main__':
    unittest.main()
