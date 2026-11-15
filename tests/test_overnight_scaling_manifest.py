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


class GroupedScalingReportTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import scaling
        self.scaling = scaling
        self.mapping = {'schema_version': 'scaling-evaluator-map-v1', 'outcome_panel': 'fidelity',
                        'target_bundle_sha256': 'a' * 64, 'items': []}
        # Three judgments: j1 is shown in both option orders, j2/j3 once.
        for item, semantic, group, order in [('i1', 'j1', 'g1', 'ab'), ('i1r', 'j1', 'g1', 'ba'),
                                             ('i2', 'j2', 'g1', 'ab'), ('i3', 'j3', 'g2', 'ab')]:
            self.mapping['items'].append({'item_id': item, 'semantic_item_id': semantic,
                'researcher_id': 'r1', 'group_id': group, 'tier': 'A',
                'schedule_hash': digest([item, order])})
        self.jobs = [{'cell_id': cell, 'job_id': digest(cell), 'manifest_sha256': digest(['job', cell]),
                      'item_ids': ['i1', 'i1r', 'i2', 'i3'],
                      'target_bundle_sha256': 'a' * 64, 'parent_target_bundle_sha256': 'a' * 64} for cell in ('candidate', 'baseline')]
        self.comparisons = [{'comparison_id': 'paired', 'candidate_cell_id': 'candidate',
                             'baseline_cell_id': 'baseline'}]
        self.rule = {'schema_version': 'source-group-bootstrap-v1', 'seed': 17,
                     'samples': 2000, 'confidence': 0.95, 'minimum_groups': 2,
                     'unit': 'source_group', 'estimand': 'equal-semantic-item-mean'}
        self.packets = []
        for job, correct in zip(self.jobs, ([True, False, True, False], [False, False, False, False])):
            rows = []
            for mapping, hit in zip(self.mapping['items'], correct):
                rows.append({key: mapping[key] for key in ('item_id', 'researcher_id', 'group_id', 'tier', 'schedule_hash')})
                rows[-1].update(correct=hit, failure=False, brier=0.0 if hit else 1.0)
            report = {'job_id': job['job_id'], 'manifest_sha256': job['manifest_sha256'],
                      'target_bundle_sha256': self.mapping['target_bundle_sha256'], 'per_item': rows}
            self.packets.append({'job_id': job['job_id'], 'report': report,
                                 'status_by_item': {i['item_id']: 'complete' for i in self.mapping['items']}})

    def report(self):
        return self.scaling.grouped_paired_report(self.mapping, self.jobs, self.packets, self.comparisons,
            expected_mapping_hash=digest(self.mapping), expected_jobs_hash=digest(self.jobs),
            expected_scores_hash=digest(self.packets),
            expected_analysis_hash=digest({'comparisons': self.comparisons, 'rule': self.rule}), rule=self.rule)

    def test_reverse_orders_collapse_and_judgments_have_equal_weight(self):
        report = self.report()
        candidate = report['cells']['candidate']['strata'][0]
        self.assertEqual(candidate['semantic_item_count'], 3)
        self.assertEqual(candidate['ordered_item_count'], 4)
        self.assertEqual(candidate['source_group_count'], 2)
        self.assertEqual(candidate['accuracy'], 0.5)  # (0.5 + 1 + 0) / 3
        compared = report['comparisons'][0]['strata'][0]
        self.assertEqual(compared['difference'], 0.5)
        self.assertEqual(compared['ci95'], [0.0, 0.75])
        self.assertEqual(compared['ci95'], self.report()['comparisons'][0]['strata'][0]['ci95'])
        self.assertEqual(compared['researcher_id'], 'r1')
        self.assertEqual(compared['tier'], 'A')

    def test_one_group_has_no_interval_even_with_many_option_orders(self):
        for item in self.mapping['items']:
            item['group_id'] = 'g1'
        for packet in self.packets:
            for row in packet['report']['per_item']:
                row['group_id'] = 'g1'
        compared = self.report()['comparisons'][0]['strata'][0]
        self.assertIsNone(compared['ci95'])
        self.assertEqual(compared['uncertainty_status'], 'insufficient-independent-groups')

    def test_empty_and_missing_predictions_remain_failure_zeros(self):
        for index, status in [(0, 'empty'), (1, 'missing')]:
            row = self.packets[0]['report']['per_item'][index]
            row.update(correct=False, failure=True, brier=None)
            self.packets[0]['status_by_item'][row['item_id']] = status
        candidate = self.report()['cells']['candidate']
        self.assertEqual(candidate['strata'][0]['accuracy'], 1 / 3)
        self.assertEqual(candidate['strata'][0]['failed_ordered_count'], 2)
        self.assertEqual(candidate['semantic_items'][0]['status_by_item'], {'i1': 'empty', 'i1r': 'missing'})

    def test_absent_score_report_is_missing_evidence_not_graded_zero(self):
        self.packets.pop(0)
        report = self.report()
        candidate = report['cells']['candidate']['strata'][0]
        self.assertIsNone(candidate['accuracy'])
        self.assertEqual(candidate['missing_ordered_count'], 4)
        compared = report['comparisons'][0]['strata'][0]
        self.assertEqual(compared['unpaired_semantic_count'], 3)
        self.assertIsNone(compared['difference'])
        self.assertIsNone(compared['ci95'])

    def test_wrong_score_or_mapping_bindings_and_missing_rows_reject(self):
        for change in ('duplicate', 'omitted', 'schedule', 'job', 'bundle', 'failure', 'semantic_group', 'utility'):
            case = GroupedScalingReportTests()
            case.setUp()
            row = case.packets[0]['report']['per_item'][0]
            if change == 'duplicate': case.packets[0]['report']['per_item'].append(dict(row))
            if change == 'omitted': case.packets[0]['report']['per_item'].pop()
            if change == 'schedule': row['schedule_hash'] = 'b' * 64
            if change == 'job': case.packets[0]['report']['job_id'] = 'b' * 64
            if change == 'bundle': case.packets[0]['report']['target_bundle_sha256'] = 'b' * 64
            if change == 'failure': row.update(failure=True, correct=True)
            if change == 'semantic_group': case.mapping['items'][1]['group_id'] = 'g2'
            if change == 'utility': case.mapping['outcome_panel'] = 'utility'
            with self.subTest(change=change), self.assertRaises(ValueError): case.report()

    def test_real_evaluator_subset_reports_bind_distinct_target_bundles(self):
        from autoresearch.taste.overnight.evaluation import score_predictions, prediction_input
        targets = []
        self.mapping['items'] = self.mapping['items'][:2]
        for mapped in self.mapping['items']:
            target = {'item_id': mapped['item_id'], 'researcher_id': 'r1', 'group_id': 'g1',
                      'tier': 'A', 'context': 'synthetic choice', 'options': ['left', 'right'],
                      'option_order_id': mapped['item_id'], 'chosen_index': 0}
            targets.append(target)
            mapped['schedule_hash'] = digest(prediction_input(target))
        parent = {'schema_version': 'validated-target-bundle-v1', 'items': targets,
                  'items_sha256': digest([prediction_input(t) for t in targets])}
        parent_hash = digest(parent)
        self.mapping['target_bundle_sha256'] = parent_hash
        self.jobs, self.packets = [], []
        for cell in ('candidate', 'baseline'):
            for target in targets:
                bundle = {'schema_version': 'validated-target-bundle-v1', 'items': [target],
                          'items_sha256': digest([prediction_input(target)])}
                bundle['target_bundle_sha256'] = digest(bundle)
                job = {'cell_id': cell, 'job_id': digest([cell, target['item_id']]),
                       'manifest_sha256': digest(['manifest', cell, target['item_id']]),
                       'item_ids': [target['item_id']], 'target_bundle_sha256': bundle['target_bundle_sha256'],
                       'parent_target_bundle_sha256': parent_hash}
                self.jobs.append(job)
                predictions = [{'item_id': target['item_id'], 'item_sha256': digest(prediction_input(target)),
                    'items_sha256': bundle['items_sha256'], 'job_id': job['job_id'],
                    'manifest_sha256': job['manifest_sha256'], 'status': 'complete',
                    'prediction': {'choice': 'a', 'confidence': 1.0, 'probabilities': [1.0, 0.0]}}]
                report = score_predictions(bundle, predictions, expected_target_bundle_sha256=bundle['target_bundle_sha256'],
                    expected_job_id=job['job_id'], expected_manifest_sha256=job['manifest_sha256'])
                self.packets.append({'job_id': job['job_id'], 'report': report,
                                     'status_by_item': {target['item_id']: 'complete'}})
        self.assertNotEqual(self.jobs[0]['target_bundle_sha256'], self.jobs[1]['target_bundle_sha256'])
        report = self.report()
        self.assertEqual(report['cells']['candidate']['strata'][0]['accuracy'], 1.0)
        self.assertEqual(report['cells']['candidate']['strata'][0]['semantic_item_count'], 1)

    def test_tiers_and_researchers_are_separate_descriptive_panels(self):
        self.mapping['items'][2].update(researcher_id='r2', tier='B')
        for packet in self.packets:
            packet['report']['per_item'][2].update(researcher_id='r2', tier='B')
        strata = self.report()['comparisons'][0]['strata']
        self.assertEqual([(s['researcher_id'], s['tier']) for s in strata], [('r1', 'A'), ('r2', 'B')])
        self.assertIsNone(strata[1]['ci95'])


def driver_fixture(root):
    import hashlib
    from autoresearch.taste.overnight import backends, consumer, baselines, profiles_summary
    from autoresearch.taste.overnight.contracts import backend_identity, build_profile, sha256_text
    from autoresearch.taste.overnight.registry import get_builder
    baselines.register_baselines()
    profiles_summary.register_summary_builders()
    code = '79874f7024d7ef6af72aae20aca8b1e82fa545e0'
    spec, originals = synthetic_inputs()
    fixture = json.loads((ROOT / 'docs/overnight/gio-profile-20261115/infrastructure/fixture-v3.json').read_text())
    documents = copy.deepcopy(fixture['documents'])
    for document in documents:
        document['permitted_spans'] = [{'start': 0, 'end': len(document['content']),
            'text': document['content'], 'speaker': document['researcher_id']}]
    ledger = backends.DollarLedger(root / 'synthetic-ledger.sqlite', max_usd=1, deadline='2099-01-01T00:00:00Z')
    engines = {level: backends.OpenAIResponsesBackend(model=model, reasoning='medium', ledger=ledger,
        max_usd=.01, timeout=1) for level, model in zip(('S', 'M', 'L'), ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra'))}
    models = []
    for level, engine in engines.items():
        models.append({'level': level, 'status': 'available', 'identity': backend_identity(engine),
            'settings': {'temperature': 0.0, 'max_tokens': 128},
            'extractor_settings': {'temperature': 0.0, 'max_tokens': 256},
            'effective_settings': engine.enforced_settings, 'model_revision': 'synthetic-provider-unversioned',
            'adapter_sha256': hashlib.sha256(Path(backends.__file__).read_bytes()).hexdigest(),
            'verification_sha256': 'b' * 64})
    items = [{'item_id': 'synthetic-item-1', 'researcher_id': 'synthetic', 'context': 'Choose a test.',
              'options': ['control', 'change'], 'option_order_id': 'ab'},
             {'item_id': 'synthetic-item-2', 'researcher_id': 'synthetic', 'context': 'Choose a test.',
              'options': ['change', 'control'], 'option_order_id': 'ba'}]
    def metadata(item):
        return {'item_id': item['item_id'], 'option_order_id': item['option_order_id'],
                'context_sha256': sha256_text(item['context']), 'options_sha256': digest(item['options'])}
    spec.update(schema_version='overnight-scaling-design-v2', campaign_id='gio-profile-20261115',
                stage='dev', panel_kind='responses_api', code_sha=code, models=models,
                primary_method_id='P1', fixed_profile={'method_id': 'P1', 'extractor_level': 'S'})
    spec['common'].update(items=[metadata(i) for i in items], items_hash=digest(items),
        settings=models[0]['settings'], extractor_settings=models[0]['extractor_settings'], documents_hash=digest(documents),
        effective_settings=models[0]['effective_settings'], renderer_implementation_hash=consumer.implementation_hash(),
        consumer_prompt_version=consumer.PROMPT_VERSION,
        consumer_prompt_sha256=digest({'version': consumer.PROMPT_VERSION, 'system': consumer.SYSTEM, 'instruction': consumer.INSTRUCTION}))
    profiles, methods, by_profile = [], [], {}
    for method_id in ('P1', 'P2'):
        builder = get_builder(method_id)
        method = {'method_id': method_id, 'config_hashes': {},
                  'method_implementation_hash': builder.implementation_hash,
                  'profile_prompt_version': builder.prompt_version, 'profile_prompt_sha256': builder.prompt_sha256}
        for model in models:
            body = copy.deepcopy(originals[0]['profile'])
            body.update(method_id=method_id, extractor=model['identity'], extractor_settings=model['extractor_settings'],
                code_sha=code, documents_hash=digest(documents), renderer_implementation_hash=consumer.implementation_hash(),
                method_implementation_hash=builder.implementation_hash, prompt_version=builder.prompt_version,
                prompt_sha256=builder.prompt_sha256)
            body['config'].update(method_id=method_id, extractor_settings=model['extractor_settings'], code_sha=code)
            body['config_id'] = digest(body['config'])
            body.pop('profile_id')
            body['profile_id'] = digest(body)
            profiles.append({'method_id': method_id, 'extractor_level': model['level'], 'profile': body})
            by_profile[body['profile_id']] = body
            method['config_hashes'][model['level']] = body['config_id']
        methods.append(method)
    spec['methods'] = methods
    spec['controls'] = [{'method_id': method, 'kind': method, 'implementation_sha256': get_builder(method).implementation_hash,
                         'config_hash': digest({'method_id': method, 'personalization_cap': 2048})} for method in ('no_profile', 'raw_evidence')]
    diagnostic_items = [dict(items[0], item_id='synthetic-archival-1')]
    spec['diagnostic'].update(items=[metadata(i) for i in diagnostic_items], items_hash=digest(diagnostic_items),
                              raw_evidence_hash=spec['common']['allowed_source_manifest_hash'],
                              raw_control_config_hash=spec['controls'][1]['config_hash'], documents_hash=digest(documents),
                              raw_implementation_sha256=get_builder('raw_evidence').implementation_hash)
    manifest = __import__('autoresearch.taste.overnight.scaling', fromlist=['build_manifest']).build_manifest(spec, profiles)
    runtime = {'schema_version': 'scaling-driver-runtime-v1', 'code_sha': code,
        'driver_sha256': hashlib.sha256((ROOT / 'docs/overnight/gio-profile-20261115/control/run_batch.py').read_bytes()).hexdigest(),
        'runner_sha256': hashlib.sha256((ROOT / 'autoresearch/taste/overnight/runner.py').read_bytes()).hexdigest(),
        'backend_sha256': models[0]['adapter_sha256'], 'renderer_implementation_hash': consumer.implementation_hash(),
        'consumer_prompt_version': consumer.PROMPT_VERSION, 'consumer_prompt_sha256': spec['common']['consumer_prompt_sha256'],
        'deadline': '2099-01-01T00:00:00Z', 'release_schema_version': 'released-development-v2',
        'release_scope': 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel'}
    def file_ref(name, body):
        path = root / name
        raw = (json.dumps(body, sort_keys=True) + '\n').encode()
        path.write_bytes(raw)
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}
    bindings = []
    for cell in manifest['cells']:
        diagnostic = cell['conditioning']['kind'] == 'archival_raw_evidence'
        selected = diagnostic_items if diagnostic else items
        release = {'schema_version': runtime['release_schema_version'], 'scope': runtime['release_scope'],
            'researcher_id': 'synthetic', 'sources': {'documents': documents,
            'source_manifest': fixture['profile']['config']['allowed_sources'],
            'allowed_source_manifest_hash': spec['common']['allowed_source_manifest_hash']},
            'items': selected, 'items_sha256': digest(selected)}
        condition = cell['conditioning']
        if condition['kind'] == 'neutral_profile':
            profile = by_profile[condition['profile_id']]
            registration = {'module': 'autoresearch.taste.overnight.profiles_summary', 'function': 'register_summary_builders'}
        else:
            method = 'raw_evidence' if diagnostic else condition['method_id']
            config = copy.deepcopy(profiles[0]['profile']['config'])
            config.update(method_id=method)
            profile = build_profile(documents, config, engines['S']).to_dict()
            registration = {'module': 'autoresearch.taste.overnight.baselines', 'function': 'register_baselines'}
        bindings.append({'cell_id': cell['cell_id'], 'status': 'ready',
            'release_ref': file_ref('release-' + cell['cell_id'] + '.json', release), 'release': release,
            'jobs': [{'item_ids': [i['item_id'] for i in selected], 'profile_ref': file_ref('profile-' + profile['profile_id'] + '.json', profile),
                      'profile': profile, 'origin_job_id': digest(['synthetic-build', profile['profile_id']]),
                      'registration': registration, 'limits': {'max_calls': len(selected), 'max_seconds': 30,
                      'max_usd': .01, 'timeout': 1}}]})
    return manifest, bindings, runtime, ledger


class ScalingDriverPacketTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from autoresearch.taste.overnight import scaling
        self.scaling = scaling
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest, self.bindings, self.runtime, self.ledger = driver_fixture(Path(self.temp.name))

    def compile(self):
        return self.scaling.compile_driver_packets(self.manifest, self.bindings, runtime=self.runtime,
            expected_manifest_hash=self.manifest['manifest_sha256'], expected_bindings_hash=digest(self.bindings),
            expected_runtime_hash=digest(self.runtime))

    def test_packets_match_driver_shapes_and_do_not_grant_authority(self):
        compiled = self.compile()
        self.assertEqual(len(compiled['packets']), 18)
        self.assertEqual(len(compiled['arms']), 22)
        self.assertEqual(compiled['estimates']['max_attempts'], 33)
        self.assertAlmostEqual(compiled['estimates']['requested_usd_ceiling'], .18)
        self.assertEqual(self.ledger.summary()['attempts'], 0)
        for entry in compiled['packets']:
            packet = entry['packet']
            self.assertIsNone(packet['lease'])
            self.assertIsNone(packet['manifest']['allocation']['authorization_source'])
            self.assertNotIn('job_id', packet['manifest'])
            self.assertEqual(packet['manifest']['code_sha'], self.runtime['code_sha'])
        self.assertEqual(len(compiled['profile_dependencies']), 8)
        # S-extracted P1 is used by all three consumers; existing extraction is never repeated.
        source = next(p for p in self.manifest['profile_pins'] if p['method_id'] == 'P1' and p['extractor_level'] == 'S')
        dependency = next(d for d in compiled['profile_dependencies'] if d['profile_id'] == source['profile_id'])
        self.assertEqual(len(dependency['packet_ids']), 3)

    def test_real_driver_preparation_accepts_packets_after_synthetic_authority(self):
        import importlib.util
        from datetime import datetime, timezone
        from unittest.mock import patch
        path = ROOT / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
        loader = importlib.util.spec_from_file_location('scaling_driver_test', path)
        driver = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(driver)
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
        compiled = self.compile()
        batch = {'campaign_id': 'gio-profile-20261115', 'release_schema_version': self.runtime['release_schema_version'],
                 'release_scope': self.runtime['release_scope'], 'ledger': {'max_usd': 1}, 'code_sha': self.runtime['code_sha'],
                 'deadline': '2026-11-15T17:00:00Z', 'contract': {'sha256': self.manifest['design']['contract_sha256']}}
        for entry in compiled['packets']:
            packet = copy.deepcopy(entry['packet'])
            packet['manifest']['deadline'] = batch['deadline']
            packet['lease'] = {'lease_id': 'synthetic-only', 'owner': 'synthetic-test', 'expires_at': batch['deadline']}
            packet['manifest']['allocation']['authorization_source'] = 'synthetic-test-only'
            with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                prepared = driver._prepare_packet(packet, batch, self.ledger)
            self.assertEqual(prepared['manifest']['scaling_cell_id'], entry['cell_id'])
        self.assertEqual(self.ledger.summary()['attempts'], 0)

    def test_late_input_profile_runtime_or_settings_changes_reject(self):
        for change in ('order', 'source', 'runtime', 'profile', 'settings', 'cap'):
            manifest, bindings, runtime = copy.deepcopy((self.manifest, self.bindings, self.runtime))
            if change == 'order': bindings[0]['jobs'][0]['item_ids'].reverse()
            if change == 'source': bindings[0]['release']['sources']['documents'][0]['content'] += '!'
            if change == 'runtime': runtime['code_sha'] = 'f' * 40
            if change == 'profile': bindings[0]['jobs'][0]['profile']['content']['prose'] = 'changed'
            if change == 'settings': manifest['cells'][0]['consumer']['settings']['max_tokens'] = 512
            if change == 'cap': bindings[0]['jobs'][0]['profile']['personalization_cap'] = 512
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.scaling.compile_driver_packets(manifest, bindings, runtime=runtime,
                    expected_manifest_hash=self.manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
                    expected_runtime_hash=digest(runtime))

    def test_unavailable_release_and_utility_leave_explicit_cells(self):
        missing = self.bindings[0]['cell_id']
        self.bindings[0] = {'cell_id': missing, 'status': 'unavailable', 'reason': 'approved profile not supplied'}
        compiled = self.compile()
        self.assertEqual(len(compiled['packets']), 17)
        cell = next(c for c in compiled['cells'] if c['cell_id'] == missing)
        self.assertEqual(cell['status'], 'unavailable')
        self.assertEqual(cell['reason'], 'approved profile not supplied')


class ScalingBaselineBindingTests(unittest.TestCase):
    setUp = ScalingDriverPacketTests.setUp
    compile = ScalingDriverPacketTests.compile

    def test_control_policy_and_permitted_span_escape_reject(self):
        control = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'raw_evidence')
        profile = control['jobs'][0]['profile']
        profile['config']['chunk_chars'] = 7
        profile['config_id'] = digest(profile['config'])
        profile.pop('profile_id')
        profile['profile_id'] = digest(profile)
        with self.assertRaisesRegex(ValueError, 'policy'):
            self.compile()

    def test_raw_passage_outside_allowed_span_rejects_without_fallback(self):
        # A new externally frozen release/profile still must obey its own permitted spans.
        control = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'raw_evidence')
        profile = control['jobs'][0]['profile']
        passage = profile['content']['passages'][0]
        passage['end'] += 1
        passage['text'] += '!'
        profile['content_sha256'] = digest(profile['content'])
        from autoresearch.taste.overnight.contracts import render_content
        profile['token_count'] = len(render_content(profile['content']).encode())
        profile.pop('profile_id')
        profile['profile_id'] = digest(profile)
        with self.assertRaisesRegex(ValueError, 'permitted'):
            self.compile()


    def test_no_profile_and_raw_passages_cannot_hide_extra_profile_content(self):
        from autoresearch.taste.overnight.contracts import render_content
        for method in ('no_profile', 'raw_evidence'):
            bindings = copy.deepcopy(self.bindings)
            profile = next(b['jobs'][0]['profile'] for b in bindings if b['jobs'][0]['profile']['method_id'] == method)
            if method == 'no_profile':
                profile['content'] = {'prose': 'undeclared personalization'}
            else:
                profile['content']['passages'][0]['summary'] = 'candidate-derived judgment'
            profile['content_sha256'] = digest(profile['content'])
            profile['token_count'] = len(render_content(profile['content']).encode())
            profile.pop('profile_id')
            profile['profile_id'] = digest(profile)
            with self.subTest(method=method), self.assertRaises(ValueError):
                self.scaling.compile_driver_packets(self.manifest, bindings, runtime=self.runtime,
                    expected_manifest_hash=self.manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
                    expected_runtime_hash=digest(self.runtime))

    def test_retrieval_profiles_bind_policy_decision_and_consumer(self):
        import hashlib
        from autoresearch.taste.overnight.contracts import build_profile
        spec = copy.deepcopy(self.manifest['design'])
        spec['controls'][1].update(method_id='lexical_retrieval', kind='retrieval',
            config_hash=digest({'method_id': 'lexical_retrieval', 'personalization_cap': 2048, 'top_k': 1}))
        available = {j['profile']['profile_id']: j['profile'] for b in self.bindings for j in b['jobs']}
        profiles = [{'method_id': pin['method_id'], 'extractor_level': pin['extractor_level'],
                     'profile': available[pin['profile_id']]} for pin in self.manifest['profile_pins']]
        old_cells = {c['cell_id']: c for c in self.manifest['cells']}
        prior = {b['cell_id']: b for b in self.bindings}
        self.manifest = self.scaling.build_manifest(spec, profiles)
        bindings = []
        class NoCalls:
            def complete(self, *args, **kwargs):
                raise AssertionError('retrieval fixture must not call a model')
        for cell in self.manifest['cells']:
            if cell['cell_id'] in prior:
                bindings.append(prior[cell['cell_id']])
                continue
            original = next(b for b in self.bindings if old_cells[b['cell_id']]['conditioning']['kind'] == 'raw_evidence'
                            and old_cells[b['cell_id']]['consumer'] == cell['consumer'])
            binding = copy.deepcopy(original)
            binding['cell_id'], binding['jobs'] = cell['cell_id'], []
            for item in binding['release']['items']:
                config = copy.deepcopy(original['jobs'][0]['profile']['config'])
                config.update(method_id='lexical_retrieval', top_k=1,
                              decision={k: item[k] for k in ('context', 'options')},
                              consumer_identity=cell['consumer']['identity'])
                backend = NoCalls()
                backend._overnight_identity = original['jobs'][0]['profile']['extractor']
                body = build_profile(binding['release']['sources']['documents'], config, backend).to_dict()
                path = Path(self.temp.name) / ('lexical-' + body['profile_id'] + '.json')
                raw = (json.dumps(body, sort_keys=True) + '\n').encode()
                path.write_bytes(raw)
                job = copy.deepcopy(original['jobs'][0])
                job.update(item_ids=[item['item_id']], profile=body,
                           profile_ref={'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()},
                           origin_job_id=digest(['synthetic-build', body['profile_id']]))
                job['limits']['max_calls'] = 1
                binding['jobs'].append(job)
            bindings.append(binding)
        self.bindings = bindings
        compiled = self.compile()
        self.assertEqual(len(compiled['packets']), 21)
        retrieval = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'lexical_retrieval')
        original = copy.deepcopy(retrieval['jobs'][0]['profile'])
        for field, value in [('consumer_identity', {'model': 'wrong'}), ('decision', {'context': 'wrong', 'options': ['a', 'b']}), ('top_k', 2)]:
            profile = copy.deepcopy(original)
            profile['config'][field] = value
            profile['config_id'] = digest(profile['config'])
            profile.pop('profile_id')
            profile['profile_id'] = digest(profile)
            retrieval['jobs'][0]['profile'] = profile
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'policy|decision/consumer'):
                self.compile()


class ReleasedPilotGroupingTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import scaling
        self.scaling = scaling
        self.map_hash = '6d4bc7b02542671e8577854c0849d342c2f994f9afec26ec247229e4e5ca779f'
        self.report_hash = '259229944069c079da3a8e9bc8b845ffe2a76b3228032e6af0ac28e5f0898d56'
        base = ROOT / 'docs/overnight/gio-profile-20261115/scaling'
        self.mapping = (base / ('released-' + self.map_hash + '.json')).read_bytes()
        self.report = (base / ('released-' + self.report_hash + '.json')).read_bytes()

    def test_actual_released_schema_retains_small_n_and_unavailable_builds(self):
        report = self.scaling.group_released_pilot(self.mapping, self.report,
            expected_mapping_sha256=self.map_hash, expected_report_sha256=self.report_hash)
        self.assertEqual(report['counts']['chris_olah'], {'ordered_items': 4, 'semantic_targets': 2, 'independent_source_groups': 1})
        self.assertEqual(len(report['paired_comparisons']), 20)
        self.assertTrue(all(p['accuracy_ci95'] is None for p in report['paired_comparisons']))
        self.assertTrue(all(p['uncertainty_status'] == 'insufficient-independent-groups' for p in report['paired_comparisons']))
        p1 = [a for a in report['arms'] if a['method_id'] == 'P1']
        self.assertEqual(len(p1), 2)
        self.assertTrue(all(a['status'] == 'unavailable_build' and a['valid_choice_accuracy'] is None for a in p1))
        self.assertEqual(report['outcome_panel'], 'fidelity-operational-pilot')

    def test_tampered_aggregate_counts_and_unbalanced_orders_reject(self):
        import hashlib
        for change in ('denominator', 'interval', 'order', 'pair'):
            mapping, report = json.loads(self.mapping), json.loads(self.report)
            if change == 'denominator': report['denominators']['chris_olah']['semantic_targets'] = 4
            if change == 'interval': report['paired_comparisons'][0]['accuracy_ci95'] = [0, 1]
            if change == 'order': mapping['mapping'][0]['semantic_target_id'] = 'new-target'
            if change == 'pair': report['paired_comparisons'].pop()
            raw_map, raw_report = json.dumps(mapping).encode(), json.dumps(report).encode()
            report['opaque_group_mapping_sha256'] = hashlib.sha256(raw_map).hexdigest()
            raw_report = json.dumps(report).encode()
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.scaling.group_released_pilot(raw_map, raw_report,
                    expected_mapping_sha256=hashlib.sha256(raw_map).hexdigest(),
                    expected_report_sha256=hashlib.sha256(raw_report).hexdigest())
