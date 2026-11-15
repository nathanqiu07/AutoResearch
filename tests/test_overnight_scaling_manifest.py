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

    def test_one_deduplicated_execution_populates_all_declared_cell_aliases(self):
        job = self.jobs[0]
        job.pop('cell_id')
        job['cell_ids'] = ['candidate', 'candidate-alias']
        self.comparisons.append({'comparison_id': 'alias-paired', 'candidate_cell_id': 'candidate-alias',
                                 'baseline_cell_id': 'baseline'})
        report = self.report()
        self.assertEqual(report['unique_scored_jobs'], 2)
        self.assertEqual(report['logical_cell_count'], 3)
        self.assertEqual(report['cells']['candidate'], report['cells']['candidate-alias'])
        self.assertEqual(report['comparisons'][0]['strata'], report['comparisons'][1]['strata'])

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

    def test_four_mandatory_controls_keep_pending_retrieval_cells_visible(self):
        from autoresearch.taste.overnight.registry import get_builder
        spec = copy.deepcopy(self.manifest['design'])
        for method in ('lexical_retrieval', 'semantic_retrieval'):
            spec['controls'].append({'method_id': method, 'kind': 'retrieval',
                'implementation_sha256': get_builder(method).implementation_hash,
                'config_hash': digest({'method_id': method, 'personalization_cap': 2048, 'top_k': 3})})
        records = []
        by_id = {job['profile']['profile_id']: job['profile'] for b in self.bindings for job in b['jobs']}
        for pin in self.manifest['profile_pins']:
            records.append({'method_id': pin['method_id'], 'extractor_level': pin['extractor_level'], 'profile': by_id[pin['profile_id']]})
        manifest = self.scaling.build_manifest(spec, records)
        old_cells = {c['cell_id']: c for c in self.manifest['cells']}
        by_cell = {b['cell_id']: b for b in self.bindings}
        bindings = [copy.deepcopy(by_cell[c['cell_id']]) if c['cell_id'] in old_cells else
            {'cell_id': c['cell_id'], 'status': 'unavailable', 'reason': 'synthetic exact retrieval bundle pending'}
            for c in manifest['cells']]
        compiled = self.scaling.compile_driver_packets(manifest, bindings, runtime=self.runtime,
            expected_manifest_hash=manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
            expected_runtime_hash=digest(self.runtime))
        self.assertEqual(len(compiled['arms']), 28)
        self.assertEqual(len(compiled['cells']), 24)
        self.assertEqual(len(compiled['packets']), 18)
        pending = [c for c in compiled['cells'] if c['status'] == 'unavailable']
        self.assertEqual(len(pending), 6)
        self.assertEqual({a['method_id'] for a in compiled['arms'] if a['study'] == 'A'} &
            {'no_profile', 'raw_evidence', 'lexical_retrieval', 'semantic_retrieval'},
            {'no_profile', 'raw_evidence', 'lexical_retrieval', 'semantic_retrieval'})
        for order in (spec['controls'], list(reversed(spec['controls']))):
            reordered = self.scaling.build_manifest(dict(spec, controls=order), records)
            summary = self.scaling.summarize_results(reordered, [], expected_manifest_hash=reordered['manifest_sha256'])
            fixed = next(a for a in summary['arms'] if a['arm_id'] == 'B/S')
            self.assertEqual(fixed['personalization_gain']['baseline_arm_id'], 'A/raw_evidence/S')
        for change in ('drop', 'wrong_kind'):
            altered = copy.deepcopy(spec)
            if change == 'drop': altered['controls'].pop()
            if change == 'wrong_kind': altered['controls'][-1]['kind'] = 'raw_evidence'
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.scaling.build_manifest(altered, records)

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

    def test_identical_archival_and_raw_control_execution_is_reused(self):
        spec = copy.deepcopy(self.manifest['design'])
        spec['diagnostic'].update(items=spec['common']['items'], items_hash=spec['common']['items_hash'],
                                  task_context_hash=spec['common']['task_context_hash'])
        available = {j['profile']['profile_id']: j['profile'] for b in self.bindings for j in b['jobs']}
        profiles = [{'method_id': pin['method_id'], 'extractor_level': pin['extractor_level'],
                     'profile': available[pin['profile_id']]} for pin in self.manifest['profile_pins']]
        old_cells = {c['cell_id']: c for c in self.manifest['cells']}
        old_bindings = {b['cell_id']: b for b in self.bindings}
        self.manifest = self.scaling.build_manifest(spec, profiles)
        bindings = []
        for cell in self.manifest['cells']:
            if cell['cell_id'] in old_bindings:
                bindings.append(old_bindings[cell['cell_id']])
            else:
                source = next(b for b in self.bindings if old_cells[b['cell_id']]['conditioning']['kind'] == 'raw_evidence'
                              and old_cells[b['cell_id']]['consumer'] == cell['consumer'])
                bindings.append(dict(copy.deepcopy(source), cell_id=cell['cell_id']))
        self.bindings = bindings
        compiled = self.compile()
        self.assertEqual(len(compiled['packets']), 15)
        self.assertEqual(compiled['estimates']['max_attempts'], 30)
        self.assertEqual(sum(len(p['cell_ids']) == 2 for p in compiled['packets']), 3)

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
        annotated = copy.deepcopy(original)
        annotated['content']['summary'] = 'undeclared candidate-derived profile'
        annotated['content_sha256'] = digest(annotated['content'])
        from autoresearch.taste.overnight.contracts import render_content
        annotated['token_count'] = len(render_content(annotated['content']).encode())
        annotated.pop('profile_id')
        annotated['profile_id'] = digest(annotated)
        retrieval['jobs'][0]['profile'] = annotated
        with self.assertRaisesRegex(ValueError, 'raw|passage'):
            self.compile()
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


def peer_driver_fixture(root, ordinary_fixture=None, scaling_module=None, ledger=None):
    """Fresh synthetic P7 build; unavailable non-P7 arms keep peer scope explicit."""
    import hashlib
    from unittest.mock import patch
    from autoresearch.taste.overnight import backends, profiles_hypotheses, scaling
    from autoresearch.taste.overnight.contracts import build_profile, canonical_json, source_manifest, sha256_text
    from autoresearch.taste.overnight.registry import get_builder
    scaling = scaling_module or scaling
    if ordinary_fixture is None:
        original, ordinary, runtime, ledger = driver_fixture(root)
    else:
        original, ordinary, runtime = copy.deepcopy((ordinary_fixture['manifest'], ordinary_fixture['bindings'], ordinary_fixture['runtime']))
        ledger = ledger or backends.DollarLedger(root / 'synthetic-peer-ledger.sqlite', max_usd=1, deadline='2099-01-01T00:00:00Z')
    spec = copy.deepcopy(original['design'])
    target = copy.deepcopy(ordinary[0]['release'])
    target['target_bundle_sha256'] = digest('synthetic-parent-target-bundle')
    target.update(fit_source_hashes_unchanged=True, n_dev_source_groups=1, n_ordered_items=len(target['items']),
                  n_semantic_targets=1, parent_version='synthetic-v3', tier='A')
    target['sources'].update(schema_version='synthetic-sources-v1', heldout={'dev': {'count': 1}, 'confirmation': {'count': 1}})
    text = 'Synthetic peer recommends broad exploration.'
    peer_doc = {'document_id': 'synthetic-peer-fit', 'researcher_id': 'synthetic-peer', 'content': text,
        'content_sha256': sha256_text(text), 'permitted_spans': [{'start': 0, 'end': len(text), 'speaker': 'synthetic-peer', 'text': text}]}
    peer = copy.deepcopy(target)
    peer.update(researcher_id='synthetic-peer', items=[], items_sha256=digest([]), target_bundle_sha256=digest('synthetic-peer-target-bundle'))
    peer['sources'] = {'documents': [peer_doc], 'source_manifest': source_manifest([peer_doc]),
                       'allowed_source_manifest_hash': digest(source_manifest([peer_doc]))}
    def file_ref(body):
        raw = (canonical_json(body) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        path = root / (sha + '.json')
        if path.exists():
            assert path.read_bytes() == raw
        else:
            with path.open('xb') as stream:
                stream.write(raw)
        return {'path': str(path), 'sha256': sha}
    parents = [{'researcher_id': body['researcher_id'], 'release': file_ref(body)} for body in (target, peer)]
    parent_json = [{'researcher_id': body['researcher_id'], 'release_json': canonical_json(body) + '\n'} for body in (target, peer)]
    documents = sorted(target['sources']['documents'] + [peer_doc], key=lambda d: d['document_id'])
    release = copy.deepcopy(target)
    release.update(schema_version='released-development-v2-p7-peers-v1', approved_peer_sources=True,
        peer_policy={'allowed_method_id': 'P7', 'purpose': 'contrastive peer fitting',
            'target_researcher_id': 'synthetic', 'peer_researcher_ids': ['synthetic-peer'], 'no_heldout_sources': True},
        parent_releases=parents, sources={'documents': documents, 'source_manifest': source_manifest(documents),
            'allowed_source_manifest_hash': digest(source_manifest(documents))})
    runtime['release_schema_version'] = release['schema_version']
    spec['common'].update(documents_hash=digest(documents), allowed_source_manifest_hash=digest(source_manifest(documents)))
    spec.update(primary_method_id='P7', fixed_profile={'method_id': 'P7', 'extractor_level': 'S'})
    profiles_hypotheses.register_hypotheses_builders()
    builder = get_builder('P7')
    method = {'method_id': 'P7', 'config_hashes': {}, 'method_implementation_hash': builder.implementation_hash,
              'profile_prompt_version': builder.prompt_version, 'profile_prompt_sha256': builder.prompt_sha256}
    def statement(doc):
        source = {'document_id': doc['document_id'], 'quote': doc['content']}
        if 'quote-only' not in builder.prompt_version:
            source.update(start=0, end=len(doc['content']))
        return {'text': doc['content'], 'kind': 'preference', 'evidence_status': 'explicit',
                'conditions': None, 'date': None, 'sources': [source]}
    response = canonical_json({'contrasts': [{'relation': 'different', 'target': statement(target['sources']['documents'][0]),
                                            'peer': statement(peer_doc)}]})
    profiles, by_id = [], {}
    with patch('urllib.request.urlopen', side_effect=AssertionError('offline peer fixture forbids HTTP')) as http:
        for model in spec['models']:
            engine = backends.OpenAIResponsesBackend(model=model['identity']['model'], reasoning='medium', ledger=ledger, max_usd=.01, timeout=1)
            config = {'method_id': 'P7', 'researcher_id': 'synthetic', 'replicate_id': 0, 'code_sha': spec['code_sha'],
                'personalization_cap': spec['common']['personalization_cap'], 'extractor_settings': model['extractor_settings'],
                'allowed_sources': release['sources']['source_manifest'], 'allowed_source_manifest_hash': release['sources']['allowed_source_manifest_hash'],
                'evidence_policy': 'explicit-only', **{key: release[key] for key in ('approved_peer_sources', 'peer_policy', 'parent_releases')}}
            with patch.object(engine, 'complete', return_value=response) as fake:
                body = build_profile(documents, config, engine).to_dict()
            assert fake.call_count == 1 and body['status'] == 'complete', body.get('error_code')
            profiles.append({'method_id': 'P7', 'extractor_level': model['level'], 'profile': body})
            by_id[body['profile_id']] = body
            method['config_hashes'][model['level']] = body['config_id']
            profiles.append({'method_id': 'P2', 'extractor_level': model['level'], 'status': 'planned-unavailable',
                             'reason': 'synthetic peer release is P7 only', 'evidence_sha256': digest('synthetic-P7-only')})
        assert http.call_count == 0 and ledger.summary()['attempts'] == 0
    spec['methods'] = [method, spec['methods'][1]]
    manifest = scaling.build_manifest(spec, profiles)
    bindings = []
    for cell in manifest['cells']:
        condition = cell['conditioning']
        if condition.get('method_id') != 'P7':
            bindings.append({'cell_id': cell['cell_id'], 'status': 'unavailable', 'reason': 'peer release is P7-only; target-only control belongs to separate source condition'})
            continue
        body = by_id[condition['profile_id']]
        bindings.append({'cell_id': cell['cell_id'], 'status': 'ready', 'release': release, 'release_ref': file_ref(release),
            'peer_parent_releases': parent_json, 'jobs': [{'item_ids': [i['item_id'] for i in release['items']],
                'profile': body, 'profile_ref': file_ref(body), 'origin_job_id': digest(['synthetic-peer-build', body['profile_id']]),
                'registration': {'module': 'autoresearch.taste.overnight.profiles_hypotheses', 'function': 'register_hypotheses_builders'},
                'limits': {'max_calls': len(release['items']), 'max_seconds': 30, 'max_usd': .01, 'timeout': 1}}]})
    return manifest, bindings, runtime, ledger


class ScalingPeerDriverTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from autoresearch.taste.overnight import scaling
        self.scaling = scaling
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest, self.bindings, self.runtime, self.ledger = peer_driver_fixture(Path(self.temp.name))

    def compile(self, bindings=None):
        bindings = self.bindings if bindings is None else bindings
        return self.scaling.compile_driver_packets(self.manifest, bindings, runtime=self.runtime,
            expected_manifest_hash=self.manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
            expected_runtime_hash=digest(self.runtime))

    def test_peer_profile_reuse_preserves_driver_declarations_and_absent_controls(self):
        compiled = self.compile()
        self.assertTrue(compiled['packets'])
        for entry in compiled['packets']:
            packet = entry['packet']
            self.assertEqual(packet['manifest']['method_id'], 'P7')
            binding = next(b for b in self.bindings if b['cell_id'] == entry['cell_id'])
            for key in ('approved_peer_sources', 'peer_policy', 'parent_releases'):
                self.assertEqual(packet['config'][key], binding['release'][key])
                self.assertEqual(packet['config'][key], binding['jobs'][0]['profile']['config'][key])
            self.assertIsNone(packet['lease'])
            self.assertIsNone(packet['manifest']['allocation']['authorization_source'])
            evidence = packet['manifest']['scaling_peer_evidence']
            self.assertEqual({r['role'] for r in evidence['parents']}, {'target', 'peer'})
            self.assertTrue(all(r['source_count'] == 1 and r['full_content_utf8_bytes'] > 0 for r in evidence['parents']))
        self.assertTrue(any(cell['status'] == 'unavailable' for cell in compiled['cells']))
        fixed = [a for a in self.manifest['arms'] if a['study'] == 'B']
        self.assertEqual(len({next(c['conditioning']['profile_id'] for c in self.manifest['cells'] if c['cell_id'] == a['cell_id']) for a in fixed}), 1)
        self.assertEqual(self.ledger.summary()['attempts'], 0)

    def test_peer_parent_lineage_and_exact_target_schedule_fail_closed(self):
        for change in ('missing', 'bytes', 'parent_hash', 'foreign', 'policy', 'target_items', 'union', 'duplicate_json', 'parent_identity', 'outcomes', 'heldout_outcomes'):
            bindings = copy.deepcopy(self.bindings)
            ready = next(b for b in bindings if b['status'] == 'ready')
            if change == 'missing': ready.pop('peer_parent_releases')
            if change == 'bytes': ready['peer_parent_releases'][0]['release_json'] += ' '
            if change == 'parent_hash': ready['release']['parent_releases'][0]['release']['sha256'] = '0' * 64
            if change == 'foreign': ready['release']['peer_policy']['peer_researcher_ids'] = ['unapproved-peer']
            if change == 'policy': ready['release']['peer_policy']['no_heldout_sources'] = False
            if change == 'target_items': ready['release']['target_bundle_sha256'] = '0' * 64
            if change == 'union': ready['release']['sources']['documents'][0]['permitted_spans'][0]['end'] -= 1
            if change == 'duplicate_json':
                from autoresearch.taste.overnight.contracts import sha256_text
                raw = ready['peer_parent_releases'][0]['release_json'].rstrip()
                raw = raw[:-1] + ',"researcher_id":"synthetic"}'
                ready['peer_parent_releases'][0]['release_json'] = raw
                ready['release']['parent_releases'][0]['release']['sha256'] = sha256_text(raw)
            if change in ('parent_identity', 'outcomes', 'heldout_outcomes'):
                from autoresearch.taste.overnight.contracts import canonical_json, sha256_text
                parent = json.loads(ready['peer_parent_releases'][0]['release_json'])
                if change == 'parent_identity': parent['researcher_id'] = 'unapproved-peer'
                if change == 'outcomes': parent['targets'] = [{'answer': 'synthetic-forbidden'}]
                if change == 'heldout_outcomes': parent['sources']['heldout']['dev']['targets'] = []
                raw = canonical_json(parent)
                ready['peer_parent_releases'][0]['release_json'] = raw
                ready['release']['parent_releases'][0]['release']['sha256'] = sha256_text(raw)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(bindings)

    def test_peer_profile_cannot_carry_different_policy_or_lineage(self):
        for key in ('approved_peer_sources', 'peer_policy', 'parent_releases'):
            bindings = copy.deepcopy(self.bindings)
            ready = next(b for b in bindings if b['status'] == 'ready')
            ready['release'].pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.compile(bindings)

    def test_derivative_metadata_cannot_embed_outcome_records(self):
        for change in ('count_object', 'sources_targets', 'heldout_targets'):
            bindings = copy.deepcopy(self.bindings)
            release = next(b for b in bindings if b['status'] == 'ready')['release']
            if change == 'count_object': release['n_semantic_targets'] = {'targets': [{'chosen': 'synthetic-answer'}]}
            if change == 'sources_targets': release['sources']['targets'] = [{'chosen': 'synthetic-answer'}]
            if change == 'heldout_targets': release['sources']['heldout'] = {'dev': {'count': 1, 'targets': []}, 'confirmation': {'count': 1}}
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(bindings)

    def test_peer_profile_metadata_mismatch_rejects_before_frozen_profile_comparison(self):
        for key, value in (('approved_peer_sources', False), ('peer_policy', {}), ('parent_releases', [])):
            bindings = copy.deepcopy(self.bindings)
            body = next(b for b in bindings if b['status'] == 'ready')['jobs'][0]['profile']
            body['config'][key] = value
            body['config_id'] = digest(body['config'])
            body.pop('profile_id')
            body['profile_id'] = digest(body)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'peer declarations'):
                self.compile(bindings)

    def test_ordinary_release_cannot_opt_into_peer_metadata(self):
        manifest, bindings, runtime, _ = driver_fixture(Path(self.temp.name))
        bindings[0]['release']['approved_peer_sources'] = True
        with self.assertRaisesRegex(ValueError, 'peer'):
            self.scaling.compile_driver_packets(manifest, bindings, runtime=runtime,
                expected_manifest_hash=manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
                expected_runtime_hash=digest(runtime))

    def test_non_p7_profile_and_release_cannot_use_peer_condition(self):
        manifest, bindings, runtime, _ = driver_fixture(Path(self.temp.name))
        for mode in ('profile_config', 'peer_release'):
            changed = copy.deepcopy(bindings)
            body = changed[0]['jobs'][0]['profile']
            if mode == 'profile_config':
                body['config']['approved_peer_sources'] = True
                body['config_id'] = digest(body['config'])
                body.pop('profile_id')
                body['profile_id'] = digest(body)
            else:
                peer = next(b for b in self.bindings if b['status'] == 'ready')
                changed[0]['release'] = peer['release']
                changed[0]['peer_parent_releases'] = peer['peer_parent_releases']
                runtime = copy.deepcopy(runtime)
                runtime['release_schema_version'] = self.runtime['release_schema_version']
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'peer|P7'):
                self.scaling.compile_driver_packets(manifest, changed, runtime=runtime,
                    expected_manifest_hash=manifest['manifest_sha256'], expected_bindings_hash=digest(changed),
                    expected_runtime_hash=digest(runtime))


class ScalingSelectionBuildHelperTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest, self.bindings, self.runtime, _ = driver_fixture(Path(self.temp.name))
        path = ROOT / 'docs/overnight/gio-profile-20261115/scaling/selected_scaling_bindings_v1.py'
        self.assertTrue(path.exists(), 'selected scaling build helper must exist')
        loader = importlib.util.spec_from_file_location('selected_scaling_helper_test', path)
        self.helper = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(self.helper)
        from autoresearch.taste.overnight.runner import job_id
        binding = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'P1')
        profile = binding['jobs'][0]['profile']
        config = copy.deepcopy(profile['config'])
        self.original = {'schema_version': 'overnight-packet-v1', 'release': binding['release_ref'],
            'item_ids': [], 'profile': None, 'config': config, 'registration': binding['jobs'][0]['registration'],
            'backend': {'model': 'gpt-6-luna', 'reasoning': 'medium', 'max_calls': 1, 'max_seconds': 240, 'max_usd': .04, 'timeout': 180},
            'lease': {'lease_id': 'old-authority'}, 'manifest': {'schema_version': 'overnight-job-v1',
                'campaign_id': 'gio-profile-20261115', 'stage': 'dev', 'kind': 'build',
                'method_id': 'P1', 'code_sha': self.runtime['code_sha'], 'config_hash': digest(config),
                'contract_sha256': self.manifest['design']['contract_sha256'], 'source_manifest_hash': profile['allowed_source_manifest_hash'],
                'documents_hash': profile['documents_hash'], 'items_hash': digest([]), 'option_order_schedule': [],
                'personalization_cap': profile['personalization_cap'], 'replicate_id': profile['replicate_id'],
                'extractor': profile['extractor'], 'consumer': None, 'profile_hash': None,
                'deadline': '2026-11-15T17:00:00Z', 'retry_policy': {'max_attempts': 1, 'retry_uncertain': False},
                'parent_job_ids': [], 'expected_outputs': ['profile.json', 'result.json'],
                'allocation': {'authorization_source': 'old-authorization', 'max_calls': 1, 'max_seconds': 240,
                    'max_usd': .04, 'cost_mode': 'priced_api'}}}
        self.original['manifest']['job_id'] = job_id(self.original['manifest'])
        self.limits = {'max_calls': 1, 'max_seconds': 240, 'max_usd': 2.0, 'timeout': 180}

    def build(self, original=None, target=None):
        original = self.original if original is None else original
        from autoresearch.taste.overnight.registry import get_builder
        from autoresearch.taste.overnight.consumer import implementation_hash
        builder = get_builder('P1')
        return self.helper.new_extractor_build_draft(original,
            target_identity=target or self.manifest['design']['models'][1]['identity'], limits=self.limits,
            expected_runtime_sha=self.runtime['code_sha'], expected_origin_job_id=self.original['manifest']['job_id'],
            selection_sha256='a' * 64, index_sha256='b' * 64, selection_cell_id='synthetic-selected-cell',
            expected_build_pins={'method_implementation_hash': builder.implementation_hash,
                'profile_prompt_version': builder.prompt_version, 'profile_prompt_sha256': builder.prompt_sha256,
                'renderer_implementation_hash': implementation_hash()})

    def test_new_build_preserves_config_and_replaces_execution_identity_without_authority(self):
        before = copy.deepcopy(self.original)
        packet = self.build()
        self.assertEqual(self.original, before)
        self.assertEqual(packet['config'], before['config'])
        self.assertEqual(packet['manifest']['config_hash'], before['manifest']['config_hash'])
        self.assertEqual(packet['manifest']['extractor']['model'], 'gpt-6-sol')
        self.assertNotIn('job_id', packet['manifest'])
        self.assertIsNone(packet['lease'])
        self.assertIsNone(packet['manifest']['allocation']['authorization_source'])
        self.assertIsNone(packet['profile'])
        self.assertEqual(packet['manifest']['parent_job_ids'], [before['manifest']['job_id']])
        self.assertEqual(packet['config']['extractor_settings'], before['config']['extractor_settings'])

    def test_rejects_stale_source_identity_or_reextracting_luna(self):
        from autoresearch.taste.overnight.runner import job_id
        for change in ('config', 'runtime', 'replicate', 'luna', 'identity'):
            source = copy.deepcopy(self.original)
            target = copy.deepcopy(self.manifest['design']['models'][1]['identity'])
            if change == 'config': source['config']['extractor_settings']['max_tokens'] += 1
            if change == 'runtime': source['manifest']['code_sha'] = 'f' * 40
            if change == 'replicate': source['config']['replicate_id'] = 1
            if change == 'luna': target = self.manifest['design']['models'][0]['identity']
            if change == 'identity': target['enforced_settings']['temperature'] = 0.0
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.build(source, target)

    def test_required_replicates_do_not_fall_back_to_r0_and_failures_have_no_fake_profiles(self):
        rows = [{'cell_id': 'cell', 'replicate_id': 0, 'dispatch_status': 'invalid', 'job_id': 'c' * 64}]
        pending = self.helper.lookup_required_instance(rows, cell_id='cell', replicate_id=1)
        self.assertEqual(pending['status'], 'missing-required-instance')
        failed = self.helper.lookup_required_instance(rows, cell_id='cell', replicate_id=0)
        self.assertEqual(failed['status'], 'invalid')
        self.assertNotIn('profile', failed)
        with self.assertRaises(ValueError):
            self.helper.lookup_required_instance(rows + rows, cell_id='cell', replicate_id=0)

    def test_replica_bool_or_float_cannot_match_an_integer(self):
        for replica in (True, 1.0):
            with self.subTest(replica=repr(replica)), self.assertRaises(ValueError):
                self.helper.lookup_required_instance([{'cell_id': 'cell', 'replicate_id': replica,
                    'dispatch_status': 'complete', 'profile': {'path': '/synthetic', 'sha256': 'a' * 64}}],
                    cell_id='cell', replicate_id=1)

    def test_runtime_method_prompt_and_renderer_pins_must_match_approved_values(self):
        from autoresearch.taste.overnight.registry import get_builder
        from autoresearch.taste.overnight.consumer import implementation_hash
        builder = get_builder('P1')
        expected = {'method_implementation_hash': builder.implementation_hash,
            'profile_prompt_version': builder.prompt_version, 'profile_prompt_sha256': builder.prompt_sha256,
            'renderer_implementation_hash': implementation_hash()}
        for key in expected:
            wrong = dict(expected, **{key: 'wrong-version' if key == 'profile_prompt_version' else '0' * 64})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'runtime.*pins'):
                self.helper.new_extractor_build_draft(self.original,
                    target_identity=self.manifest['design']['models'][1]['identity'], limits=self.limits,
                    expected_runtime_sha=self.runtime['code_sha'], expected_origin_job_id=self.original['manifest']['job_id'],
                    selection_sha256='a' * 64, index_sha256='b' * 64, selection_cell_id='cell', expected_build_pins=wrong)

    def test_new_sol_and_astra_builds_pass_existing_driver_preparation_without_calls(self):
        import importlib.util
        from datetime import datetime, timezone
        from unittest.mock import patch
        from autoresearch.taste.overnight import backends
        path = ROOT / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
        loader = importlib.util.spec_from_file_location('selected_scaling_build_driver', path)
        driver = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(driver)
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
        ledger = backends.DollarLedger(Path(self.temp.name) / 'build-test-ledger.sqlite', max_usd=10,
                                      deadline='2099-01-01T00:00:00Z')
        batch = {'campaign_id': 'gio-profile-20261115', 'code_sha': self.runtime['code_sha'],
            'deadline': '2026-11-15T17:00:00Z', 'release_schema_version': self.runtime['release_schema_version'],
            'release_scope': self.runtime['release_scope'], 'contract': {'sha256': self.manifest['design']['contract_sha256']},
            'ledger': {'max_usd': 10}}
        ids = []
        with patch('urllib.request.urlopen', side_effect=AssertionError('no HTTP')) as http, \
                patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('no calls')) as complete:
            for model in self.manifest['design']['models'][1:]:
                draft = self.build(target=model['identity'])
                packet = copy.deepcopy(draft)
                packet['lease'] = {'lease_id': 'synthetic-test-only', 'owner': 'test', 'expires_at': batch['deadline']}
                packet['manifest']['allocation']['authorization_source'] = 'synthetic-test-only'
                with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                    prepared = driver._prepare_packet(packet, batch, ledger)
                ids.append(prepared['manifest']['job_id'])
                self.assertEqual(prepared['config'], self.original['config'])
                self.assertIsNone(draft['lease'])
                self.assertIsNone(draft['manifest']['allocation']['authorization_source'])
            self.assertEqual(http.call_count + complete.call_count + ledger.summary()['attempts'], 0)
        self.assertEqual(len(set(ids + [self.original['manifest']['job_id']])), 3)


class ScalingDescriptiveSelectionContractTests(unittest.TestCase):
    """Synthetic receipts exercise validation without opening referenced artifacts."""

    def setUp(self):
        import importlib.util
        path = ROOT / 'docs/overnight/gio-profile-20261115/scaling/selected_scaling_bindings_v1.py'
        loader = importlib.util.spec_from_file_location('descriptive_selection_helper_test', path)
        self.helper = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(self.helper)
        self.contract_ref = self.ref('coordinator-contract')
        self.index_ref = self.ref('original-index')
        self.index = {'schema_version': 'phase2-profile-extraction-coverage-v1',
            'runtime_sha': 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca',
            'private_labels_included': False, 'cells': []}
        configs = []
        # Deliberately nonalphabetical: the validator must not choose or rank.
        for method in ('P2', 'P1', 'P3'):
            mappings = []
            for researcher in ('chris_olah', 'neel_nanda'):
                cell_id = '%s-%s-rep0' % (method, researcher)
                row = {'cell_id': cell_id, 'replicate_id': 0, 'method': method,
                    'researcher_id': researcher, 'cap': 512, 'evidence_policy': 'explicit-only',
                    'dispatch_status': 'complete', 'job_id': digest(cell_id + '-job'),
                    'original_prepared': self.ref(cell_id + '-prepared'),
                    'build_packet': self.ref(cell_id + '-packet'), 'result': self.ref(cell_id + '-result'),
                    'release': self.ref(researcher + '-release'),
                    'source_manifest_hash': digest(researcher + '-sources'),
                    'items_sha256': digest(researcher + '-items-with-context-and-order'),
                    'target_bundle_sha256': digest(researcher + '-target-bundle'),
                    'profile': self.ref(cell_id + '-profile'), 'profile_id': digest(cell_id + '-profile-body'),
                    'selected': False}
                self.index['cells'].append(row)
                mappings.append({'researcher_id': researcher, 'status': 'complete', 'cell_id': cell_id,
                    'build_prepared': copy.deepcopy(row['original_prepared']),
                    'build_packet': copy.deepcopy(row['build_packet']), 'build_result': copy.deepcopy(row['result']),
                    'release': copy.deepcopy(row['release']), 'source_manifest_hash': row['source_manifest_hash'],
                    'profile': copy.deepcopy(row['profile']), 'profile_id': row['profile_id'],
                    'items_sha256': row['items_sha256'], 'target_bundle_sha256': row['target_bundle_sha256']})
            configs.append({'config_id': method + '-c512-explicit-only', 'method_id': method,
                'personalization_cap': 512, 'evidence_policy': 'explicit-only',
                'instance_replicate_id': 0, 'researcher_mappings': mappings})
        self.selection = {'schema_version': 'development-scaling-selection-v1',
            'status': 'frozen_descriptive_selection', 'campaign_id': 'gio-profile-20261115',
            'runtime_sha': self.index['runtime_sha'], 'contract': copy.deepcopy(self.contract_ref),
            'selection_policy': copy.deepcopy(self.contract_ref), 'promotion_policy': self.ref('promotion-policy'),
            'three_replicate_score_receipt': self.ref('aggregate-receipt'),
            'original_complete_index': copy.deepcopy(self.index_ref),
            'sparse_completion_index': self.ref('sparse-completion'),
            'replicate_build_completion_index': self.ref('replicate-builds'),
            'replicate_prediction_completion_index': self.ref('replicate-predictions'),
            'common_personalization_cap': 512, 'primary_config_id': 'P2-c512-explicit-only',
            'selected_configs': configs,
            'models': [{'level': 'S', 'model': 'gpt-6-luna'}, {'level': 'M', 'model': 'gpt-6-sol'},
                       {'level': 'L', 'model': 'gpt-6-astra'}],
            'extractor_settings': {'reasoning': 'medium', 'max_tokens': 16384, 'temperature': 0.0,
                                   'effective_temperature': 'not_sent', 'timeout': 180},
            'consumer_settings': {'reasoning': 'medium', 'max_tokens': 8192, 'temperature': 0.0,
                                  'effective_temperature': 'not_sent', 'timeout': 60},
            'controls': ['no_profile', 'raw_evidence', 'lexical_retrieval', 'semantic_retrieval'],
            'control_inputs': self.ref('sparse-controls'), 'semantic_index': self.ref('semantic-bundles'),
            'studies': {
                'A': 'all selected configs and controls at3models; joint extraction+consumer, explicit futureSol/Astra dependencies',
                'B': 'primary config saved exact Luna rep0 profile perresearcher across3consumers',
                'C': 'primary config S/Lextractor x S/Lconsumer; exact existingA/Bcells referenced once',
                'D': 'only evaluator source-defined answer-known subset/withholding receipt if supplied; fixed raw evidence, no profile. Missing receipt => explicit unavailable, no invented label/subset.'},
            'diagnostic_panel': None, 'source_condition': 'original_sparse_fit_v2', 'max_usd': 80,
            'deadline': '2026-11-15T17:00:00Z', 'max_concurrent': 2,
            'execution_authorized': False, 'confirmation_authorized': False,
            'fidelity_winner_claim': False, 'finalists_frozen': False}
        # All payloads and hashes are synthetic; only the public receipt schema is reproduced.
        self.contract = {'schema_version': 'development-scaling-selection-contract-v1',
                         'final_receipt_shape': copy.deepcopy(self.selection)}

    @staticmethod
    def ref(name):
        return {'path': '/synthetic/' + name + '.json', 'sha256': digest(name)}

    def validate(self, selection=None, index=None):
        return self.helper.validate_descriptive_selection(
            self.selection if selection is None else selection, self.contract,
            self.index if index is None else index, contract_ref=self.contract_ref, index_ref=self.index_ref)

    def test_accepts_two_or_three_explicit_families_without_ranking_or_mutating_inputs(self):
        for count in (2, 3):
            selection = copy.deepcopy(self.selection)
            selection['selected_configs'] = selection['selected_configs'][:count]
            before = copy.deepcopy((selection, self.contract, self.index))
            result = self.validate(selection)
            with self.subTest(count=count):
                self.assertEqual(result['status'], 'accepted-descriptive-selection')
                self.assertEqual([r['config_id'] for r in result['selected_instances']],
                    ['P2-c512-explicit-only'] * 2 + ['P1-c512-explicit-only'] * 2
                    + (['P3-c512-explicit-only'] * 2 if count == 3 else []))
                self.assertEqual([r['researcher_id'] for r in result['selected_instances']],
                                 ['chris_olah', 'neel_nanda'] * count)
                self.assertEqual(result['unselected_index_cells'], 6 - 2 * count)
                self.assertEqual(result['selection_authority'], 'coordinator-receipt-only-no-ranking-performed')
                self.assertEqual((selection, self.contract, self.index), before)
                self.assertEqual(result['selected_instances'][0]['origin_job_id'], self.index['cells'][0]['job_id'])

    def test_less_than_two_explicit_families_stays_insufficient_without_filling_from_index(self):
        for count in (0, 1):
            selection = copy.deepcopy(self.selection)
            selection['selected_configs'] = selection['selected_configs'][:count]
            result = self.validate(selection)
            with self.subTest(count=count):
                self.assertEqual(result['status'], 'insufficient-planned-panel')
                self.assertEqual(len(result['selected_instances']), 2 * count)
                self.assertEqual(result['unselected_index_cells'], 6 - 2 * count)

    def test_invalid_empty_and_missing_profiles_remain_unavailable(self):
        for dispatch, expected in (('invalid', 'invalid'), ('empty', 'empty'),
                                   ('complete', 'missing-profile-reference')):
            selection, index = copy.deepcopy(self.selection), copy.deepcopy(self.index)
            row, mapping = index['cells'][0], selection['selected_configs'][0]['researcher_mappings'][0]
            row.update(dispatch_status=dispatch, error_code='synthetic-error' if dispatch == 'invalid' else None,
                       profile=None, profile_id=None)
            mapping.update(status='unavailable_rep0', profile=None, profile_id=None)
            result = self.validate(selection, index)
            actual = result['selected_instances'][0]
            with self.subTest(dispatch=dispatch):
                self.assertEqual(actual['status'], expected)
                self.assertIsNone(actual['profile'])
                self.assertIsNone(actual['profile_id'])
                self.assertEqual(actual['error_code'], row['error_code'])
                self.assertEqual(len(result['selected_instances']), 6)

    def test_unavailable_original_instance_cannot_borrow_another_saved_profile(self):
        selection, index = copy.deepcopy(self.selection), copy.deepcopy(self.index)
        index['cells'][0].update(dispatch_status='invalid', profile=None, profile_id=None)
        mapping = selection['selected_configs'][0]['researcher_mappings'][0]
        mapping['profile'] = copy.deepcopy(index['cells'][1]['profile'])
        mapping['profile_id'] = index['cells'][1]['profile_id']
        with self.assertRaises(ValueError):
            self.validate(selection, index)

    def test_only_integer_rep0_instances_can_be_bound(self):
        for value in (1, 2, True, False, 0.0, 1.0):
            for location in ('selection', 'index'):
                selection, index = copy.deepcopy(self.selection), copy.deepcopy(self.index)
                if location == 'selection':
                    selection['selected_configs'][0]['instance_replicate_id'] = value
                else:
                    index['cells'][0]['replicate_id'] = value
                with self.subTest(value=repr(value), location=location), self.assertRaises(ValueError):
                    self.validate(selection, index)

    def test_mismatched_original_references_and_item_context_pins_reject(self):
        fields = ('build_prepared', 'build_packet', 'build_result', 'release', 'profile',
                  'profile_id', 'source_manifest_hash', 'items_sha256', 'target_bundle_sha256')
        for field in fields:
            selection = copy.deepcopy(self.selection)
            mapping = selection['selected_configs'][0]['researcher_mappings'][0]
            mapping[field] = self.ref('changed-' + field) if isinstance(mapping[field], dict) else digest('changed-' + field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(selection)

    def test_common_cap_and_exact_config_identity_cannot_be_changed(self):
        for change in ('common', 'config', 'index', 'bool', 'float', 'id', 'policy'):
            selection, index = copy.deepcopy(self.selection), copy.deepcopy(self.index)
            config = selection['selected_configs'][0]
            if change == 'common': selection['common_personalization_cap'] = 2048
            if change == 'config': config['personalization_cap'] = 2048
            if change == 'index': index['cells'][0]['cap'] = 2048
            if change == 'bool': selection['common_personalization_cap'] = True
            if change == 'float': config['personalization_cap'] = 512.0
            if change == 'id': config['config_id'] = 'P2-c2048-explicit-only'
            if change == 'policy': config['evidence_policy'] = 'marked-inference'
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(selection, index)

    def test_missing_duplicate_or_foreign_researcher_is_not_a_complete_panel(self):
        for change in ('missing', 'duplicate', 'foreign', 'cell', 'primary'):
            selection = copy.deepcopy(self.selection)
            mappings = selection['selected_configs'][0]['researcher_mappings']
            if change == 'missing': mappings.pop()
            if change == 'duplicate': mappings[1] = copy.deepcopy(mappings[0])
            if change == 'foreign': mappings[1]['researcher_id'] = 'unreleased_person'
            if change == 'cell': mappings[0]['cell_id'] = 'unknown-cell'
            if change == 'primary': selection['primary_config_id'] = 'P8-c512-explicit-only'
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(selection)

    def test_duplicate_families_or_more_than_three_configs_reject(self):
        for change in ('duplicate', 'four'):
            selection = copy.deepcopy(self.selection)
            if change == 'duplicate': selection['selected_configs'][1] = copy.deepcopy(selection['selected_configs'][0])
            else: selection['selected_configs'].append(copy.deepcopy(selection['selected_configs'][0]))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(selection)

    def test_authority_flags_and_ceilings_cannot_be_escalated(self):
        for field in ('execution_authorized', 'confirmation_authorized', 'fidelity_winner_claim', 'finalists_frozen'):
            for value in (True, 0, None):
                selection = copy.deepcopy(self.selection)
                selection[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.validate(selection)
        for value in (81, 0, -1, True, float('nan'), float('inf')):
            selection = copy.deepcopy(self.selection)
            selection['max_usd'] = value
            with self.subTest(ceiling=value), self.assertRaises(ValueError):
                self.validate(selection)
        selection = copy.deepcopy(self.selection)
        selection['max_usd'] = 20
        self.assertEqual(self.validate(selection)['status'], 'accepted-descriptive-selection')

    def test_malformed_refs_and_changed_frozen_index_hashes_reject(self):
        for field in ('promotion_policy', 'three_replicate_score_receipt', 'replicate_prediction_completion_index',
                      'control_inputs', 'semantic_index', 'diagnostic_panel'):
            for value in ({'path': 'relative.json', 'sha256': 'a' * 64},
                          {'path': '/synthetic/file.json', 'sha256': 'not-a-hash'},
                          {'path': '/synthetic/file.json', 'sha256': 'a' * 64, 'authorized': True}):
                selection = copy.deepcopy(self.selection)
                selection[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.validate(selection)
        for field in ('contract', 'selection_policy', 'original_complete_index',
                      'sparse_completion_index', 'replicate_build_completion_index'):
            selection = copy.deepcopy(self.selection)
            selection[field] = self.ref('changed-index')
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(selection)

    def test_changed_settings_controls_runtime_and_source_condition_reject(self):
        changes = (('consumer_settings', 'reasoning', 'high'), ('extractor_settings', 'max_tokens', 8192),
                   ('consumer_settings', 'effective_temperature', 'sent'),
                   ('consumer_settings', 'max_tokens', '8192'), ('extractor_settings', 'timeout', 60))
        for section, field, value in changes:
            selection = copy.deepcopy(self.selection)
            selection[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                self.validate(selection)
        for field, value in (('runtime_sha', '0' * 40), ('controls', ['raw_evidence']),
                             ('source_condition', 'different-peer-condition'), ('max_concurrent', 3)):
            selection = copy.deepcopy(self.selection)
            selection[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(selection)

    def test_numeric_settings_types_cannot_masquerade_as_contract_values(self):
        for section, field, value in (('consumer_settings', 'max_tokens', 8192.0),
                                      ('extractor_settings', 'temperature', False),
                                      ('extractor_settings', 'timeout', 180.0)):
            selection = copy.deepcopy(self.selection)
            selection[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                self.validate(selection)

    def test_missing_or_undeclared_receipt_fields_reject(self):
        for change in ('missing', 'extra', 'private-labels'):
            selection, index = copy.deepcopy(self.selection), copy.deepcopy(self.index)
            if change == 'missing': selection.pop('consumer_settings')
            if change == 'extra': selection['execute_now'] = True
            if change == 'private-labels': index['private_labels_included'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(selection, index)


class ScalingSelectedPredictionPacketTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest, self.bindings, self.runtime, self.ledger = driver_fixture(Path(self.temp.name))
        path = ROOT / 'docs/overnight/gio-profile-20261115/scaling/selected_scaling_bindings_v1.py'
        loader = importlib.util.spec_from_file_location('selected_prediction_helper_test', path)
        self.helper = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(self.helper)
        self.binding = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'P1')
        self.identities = [copy.deepcopy(m['identity']) for m in self.manifest['design']['models']]
        self.settings = {'temperature': 0.0, 'max_tokens': 128}

    def packet(self, binding=None, **overrides):
        binding = self.binding if binding is None else binding
        job = binding['jobs'][0]
        kwargs = {'profile_ref': job['profile_ref'], 'release_ref': binding['release_ref'],
            'origin_job_id': job['origin_job_id'], 'identity': self.identities[0], 'settings': self.settings,
            'timeout': 60, 'logical_cap': 2048, 'runtime': self.runtime,
            'contract_sha256': self.manifest['design']['contract_sha256'], 'registration': job['registration'],
            'selection_sha256': digest('synthetic-selected-receipt'), 'index_sha256': digest('synthetic-index'),
            'selected_cell_id': binding['cell_id'], 'studies': ['B', 'A', 'B']}
        kwargs.update(overrides)
        return self.helper.prediction_packet(job['profile'], binding['release'], **kwargs)

    def test_three_consumers_preserve_saved_profile_and_emit_unleased_distinct_requests(self):
        from unittest.mock import patch
        from autoresearch.taste.overnight import backends
        original = copy.deepcopy(self.binding)
        with patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('no model calls')), \
                patch('urllib.request.urlopen', side_effect=AssertionError('no HTTP')), \
                patch.object(backends.DollarLedger, 'reserve', side_effect=AssertionError('no reservations')):
            packets = [self.packet(identity=identity) for identity in self.identities]
        self.assertEqual(self.binding, original)
        self.assertEqual(len({p['manifest']['scaling_execution_identity_sha256'] for p in packets}), 3)
        self.assertEqual(self.ledger.summary()['attempts'], 0)
        for packet, identity in zip(packets, self.identities):
            with self.subTest(model=identity['model']):
                manifest = packet['manifest']
                self.assertEqual(packet['profile'], original['jobs'][0]['profile_ref'])
                self.assertEqual(manifest['profile_hash'], original['jobs'][0]['profile']['profile_id'])
                self.assertEqual(manifest['extractor'], original['jobs'][0]['profile']['extractor'])
                self.assertEqual(manifest['consumer'], identity)
                self.assertEqual(manifest['documents_hash'], digest(original['release']['sources']['documents']))
                self.assertEqual(manifest['source_manifest_hash'], original['release']['sources']['allowed_source_manifest_hash'])
                self.assertEqual(packet['config']['settings'], self.settings)
                self.assertEqual(manifest['config_hash'], digest(packet['config']))
                self.assertEqual(manifest['scaling_studies'], ['A', 'B'])
                self.assertEqual(manifest['parent_job_ids'], [original['jobs'][0]['origin_job_id']])
                self.assertEqual(packet['backend']['max_calls'], 2)
                self.assertEqual(packet['backend']['reasoning'], 'medium')
                self.assertIsNone(packet['lease'])
                self.assertIsNone(manifest['allocation']['authorization_source'])
                self.assertNotIn('job_id', manifest)
        self.assertLess(packets[0]['backend']['max_usd'], packets[1]['backend']['max_usd'])
        self.assertLess(packets[1]['backend']['max_usd'], packets[2]['backend']['max_usd'])

    def test_actual_ordered_items_and_settings_are_execution_identity_inputs(self):
        ordinary = self.packet()
        reversed_order = self.packet(item_ids=['synthetic-item-2', 'synthetic-item-1'])
        self.assertEqual(reversed_order['item_ids'], ['synthetic-item-2', 'synthetic-item-1'])
        self.assertEqual(reversed_order['manifest']['option_order_schedule'], [
            {'item_id': 'synthetic-item-2', 'option_order_id': 'ba'},
            {'item_id': 'synthetic-item-1', 'option_order_id': 'ab'}])
        self.assertEqual([p['item_sha256'] for p in reversed_order['manifest']['scaling_payload_pins']],
                         [digest(i) for i in reversed(self.binding['release']['items'])])
        different_settings = self.packet(settings={'temperature': 0.0, 'max_tokens': 256})
        changed = copy.deepcopy(self.binding)
        changed['release']['items'][0]['context'] += ' Additional synthetic context.'
        changed['release']['items_sha256'] = digest(changed['release']['items'])
        different_context = self.packet(changed)
        changed = copy.deepcopy(self.binding)
        changed['release']['items'][0]['options'].reverse()
        changed['release']['items'][0]['option_order_id'] = 'ba-changed'
        changed['release']['items_sha256'] = digest(changed['release']['items'])
        different_options = self.packet(changed)
        packets = [ordinary, reversed_order, different_settings, different_context, different_options]
        self.assertEqual(len({p['manifest']['scaling_execution_identity_sha256'] for p in packets}), 5)
        for different in packets[1:]:
            self.assertEqual(different['manifest']['profile_hash'], ordinary['manifest']['profile_hash'])
        self.assertNotEqual(different_settings['manifest']['scaling_payload_pins'][0]['wire_request_sha256'],
                            ordinary['manifest']['scaling_payload_pins'][0]['wire_request_sha256'])

    def test_saved_profile_and_source_record_tampering_rejects(self):
        for change in ('profile-content', 'source-record', 'source-manifest', 'source-hash', 'researcher', 'runtime'):
            binding, runtime = copy.deepcopy(self.binding), copy.deepcopy(self.runtime)
            if change == 'profile-content': binding['jobs'][0]['profile']['content']['prose'] = 'changed'
            if change == 'source-record': binding['release']['sources']['documents'][0]['permitted_spans'][0]['end'] -= 1
            if change == 'source-manifest': binding['release']['sources']['source_manifest'][0]['content_sha256'] = '0' * 64
            if change == 'source-hash': binding['release']['sources']['allowed_source_manifest_hash'] = '0' * 64
            if change == 'researcher': binding['release']['researcher_id'] = 'foreign'
            if change == 'runtime': runtime['code_sha'] = '0' * 40
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.packet(binding, runtime=runtime)

    def test_label_free_item_hash_and_unique_schedule_are_required(self):
        for change in ('hash', 'label', 'duplicate', 'researcher'):
            binding = copy.deepcopy(self.binding)
            item = binding['release']['items'][0]
            if change == 'hash': item['context'] += ' changed'
            if change == 'label': item['chosen'] = 'synthetic-forbidden'
            if change == 'duplicate': binding['release']['items'].append(copy.deepcopy(item))
            if change == 'researcher': item['researcher_id'] = 'foreign'
            if change != 'hash': binding['release']['items_sha256'] = digest(binding['release']['items'])
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.packet(binding)
        for ids in ([], ['missing'], ['synthetic-item-1', 'synthetic-item-1']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.packet(item_ids=ids)

    def test_only_intentionally_empty_no_profile_may_alias_another_cap(self):
        empty = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'no_profile')
        canonical, alias = self.packet(empty), self.packet(empty, logical_cap=512)
        self.assertEqual(alias['manifest']['personalization_cap'], 2048)
        self.assertEqual(alias['manifest']['scaling_logical_cap'], 512)
        self.assertEqual(alias['profile'], canonical['profile'])
        self.assertEqual(alias['manifest']['profile_hash'], canonical['manifest']['profile_hash'])
        self.assertEqual(alias['manifest']['scaling_payload_pins'], canonical['manifest']['scaling_payload_pins'])
        self.assertEqual(alias['manifest']['scaling_execution_identity_sha256'], canonical['manifest']['scaling_execution_identity_sha256'])
        self.assertIn('scaling_empty_control_alias', alias['manifest'])
        self.assertNotIn('scaling_empty_control_alias', canonical['manifest'])
        for method in ('P1', 'raw_evidence'):
            binding = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == method)
            with self.subTest(method=method), self.assertRaises(ValueError):
                self.packet(binding, logical_cap=512)
        changed = copy.deepcopy(empty)
        profile = changed['jobs'][0]['profile']
        profile['intentional_empty'] = False
        profile.pop('profile_id')
        profile['profile_id'] = digest(profile)
        with self.assertRaises(ValueError):
            self.packet(changed, logical_cap=512)

    def test_retrieval_profile_requires_its_exact_consumer_and_decision(self):
        from autoresearch.taste.overnight.contracts import build_profile
        original = next(b for b in self.bindings if b['jobs'][0]['profile']['method_id'] == 'raw_evidence')
        binding = copy.deepcopy(original)
        config = copy.deepcopy(binding['jobs'][0]['profile']['config'])
        item = binding['release']['items'][0]
        config.update(method_id='lexical_retrieval', top_k=1,
                      decision={k: item[k] for k in ('context', 'options')}, consumer_identity=self.identities[0])
        class NoCalls:
            def complete(self, *args, **kwargs):
                raise AssertionError('lexical fixture cannot call a model')
        backend = NoCalls()
        backend._overnight_identity = self.identities[0]
        binding['jobs'][0]['profile'] = build_profile(binding['release']['sources']['documents'], config, backend).to_dict()
        packet = self.packet(binding, item_ids=[item['item_id']])
        self.assertEqual(packet['backend']['max_calls'], 1)
        self.assertEqual(packet['manifest']['method_id'], 'lexical_retrieval')
        with self.assertRaisesRegex(ValueError, 'consumer binding'):
            self.packet(binding, item_ids=[item['item_id']], identity=self.identities[1])
        with self.assertRaisesRegex(ValueError, 'decision'):
            self.packet(binding, item_ids=['synthetic-item-2'])

    def test_context_bound_rejects_oversized_payload_before_any_execution(self):
        binding = copy.deepcopy(self.binding)
        binding['release']['items'][0]['context'] = 'x' * 272000
        binding['release']['items_sha256'] = digest(binding['release']['items'])
        with self.assertRaisesRegex(ValueError, 'context bound'):
            self.packet(binding)

    def test_consumer_settings_malformed_identity_and_timeout_reject(self):
        for settings in ({'temperature': False, 'max_tokens': 128}, {'temperature': float('nan'), 'max_tokens': 128},
                         {'temperature': 0.0, 'max_tokens': True}, {'temperature': 0.0, 'max_tokens': 128.0},
                         {'temperature': 0.0, 'max_tokens': 0}, {'temperature': 0.0, 'max_tokens': 65537}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                self.packet(settings=settings)
        for timeout in (0, True, float('inf'), 601):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.packet(timeout=timeout)
        for field, value in (('model', 'unapproved-model'), ('class', 'ForeignBackend'),
                             ('endpoint', 'https://invalid.example/v1/responses'), ('label', 'foreign-label')):
            identity = copy.deepcopy(self.identities[0])
            identity[field] = value
            with self.subTest(identity_field=field), self.assertRaises(ValueError):
                self.packet(identity=identity)
        identity = copy.deepcopy(self.identities[0])
        identity['enforced_settings']['temperature'] = 'sent'
        with self.assertRaises(ValueError):
            self.packet(identity=identity)

    def test_peer_proof_preserves_lineage_and_rejects_changed_parent_or_policy(self):
        from autoresearch.taste.overnight import scaling
        _, bindings, runtime, _ = peer_driver_fixture(Path(self.temp.name))
        binding = next(b for b in bindings if b['status'] == 'ready')
        packet = self.packet(binding, runtime=runtime, compiler=scaling,
                             peer_parent_releases=binding['peer_parent_releases'])
        self.assertIn('scaling_peer_evidence', packet['manifest'])
        for field in ('approved_peer_sources', 'peer_policy', 'parent_releases'):
            self.assertEqual(packet['config'][field], binding['release'][field])
        with self.assertRaisesRegex(ValueError, 'peer parent proof'):
            self.packet(binding, runtime=runtime, compiler=scaling)
        for change in ('bytes', 'policy', 'profile-policy'):
            changed = copy.deepcopy(binding)
            if change == 'bytes': changed['peer_parent_releases'][0]['release_json'] += ' '
            if change == 'policy': changed['release']['peer_policy']['peer_researcher_ids'] = ['foreign-peer']
            if change == 'profile-policy':
                profile = changed['jobs'][0]['profile']
                profile['config']['peer_policy']['purpose'] = 'changed'
                profile['config_id'] = digest(profile['config'])
                profile.pop('profile_id')
                profile['profile_id'] = digest(profile)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.packet(changed, runtime=runtime, compiler=scaling,
                            peer_parent_releases=changed['peer_parent_releases'])
        ordinary = copy.deepcopy(self.binding)
        ordinary['release']['approved_peer_sources'] = True
        with self.assertRaisesRegex(ValueError, 'peer declarations'):
            self.packet(ordinary)


class ScalingReservationCeilingTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        path = ROOT / 'docs/overnight/gio-profile-20261115/scaling/selected_scaling_bindings_v1.py'
        loader = importlib.util.spec_from_file_location('scaling_reservation_helper_test', path)
        self.helper = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(self.helper)

    def test_model_specific_frozen_cache_write_bounds_do_not_reuse_luna_prices(self):
        from unittest.mock import patch
        from autoresearch.taste.overnight import backends
        # f6 input rates include the conservative 1.25x 30-minute cache-write
        # multiplier. Pin this arithmetic fixture independently of checkout rates.
        frozen_rates = {'gpt-6-luna': ('0.125', '0.50'), 'gpt-6-sol': ('2.5', '10'),
                        'gpt-6-astra': ('12.5', '50')}
        with patch.object(backends, 'RATES', frozen_rates):
            # (1000 input * input rate + 200 output * output rate) / 1e6.
            for model, expected in (('gpt-6-luna', .000225), ('gpt-6-sol', .0045), ('gpt-6-astra', .0225)):
                with self.subTest(model=model):
                    self.assertEqual(self.helper.reservation_ceiling(model, 200, 1000), expected)
                    self.assertGreater(self.helper.reservation_ceiling(model, 200), expected)

    def test_context_limit_is_strict_and_default_bound_is_the_largest_admitted(self):
        for model in ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra'):
            self.assertEqual(self.helper.reservation_ceiling(model, 8192),
                             self.helper.reservation_ceiling(model, 8192, 263807))
            with self.subTest(model=model), self.assertRaises(ValueError):
                self.helper.reservation_ceiling(model, 8192, 263808)
        for bound in (-1, True, 10.0):
            with self.subTest(bound=bound), self.assertRaises(ValueError):
                self.helper.reservation_ceiling('gpt-6-luna', 128, bound)
        for output in (0, -1, True, 1.0, 65537):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.helper.reservation_ceiling('gpt-6-luna', output)
        with self.assertRaises(ValueError):
            self.helper.reservation_ceiling('unknown-model', 128)


class ScalingContinuationProofTests(unittest.TestCase):
    ref = staticmethod(ScalingDescriptiveSelectionContractTests.ref)

    def setUp(self):
        ScalingDescriptiveSelectionContractTests.setUp(self)

    def continuation_fixture(self, change=None):
        """Rehash changed synthetic evidence so tests reach semantic checks."""
        import hashlib
        from autoresearch.taste.overnight.runner import job_id
        row = copy.deepcopy(self.index['cells'][0])
        mapping = copy.deepcopy(self.selection['selected_configs'][0]['researcher_mappings'][0])
        raw_payloads = {}
        def save(name, body):
            raw = json.dumps(body, sort_keys=True) + '\n'
            path = '/synthetic/continuation/' + name + '.json'
            raw_payloads[path] = raw
            return {'path': path, 'sha256': hashlib.sha256(raw.encode()).hexdigest()}
        release = {'schema_version': 'synthetic-source-metadata-v1',
                   'source_manifest_hash': row['source_manifest_hash'], 'items_sha256': row['items_sha256']}
        old_release, actual_release = save('old-release', release), save('actual-release', release)
        config = {'method_id': 'P2', 'personalization_cap': 512, 'replicate_id': 0,
                  'extractor_settings': {'temperature': 0.0, 'max_tokens': 16384},
                  'allowed_source_manifest_hash': row['source_manifest_hash']}
        manifest = {'schema_version': 'overnight-job-v1', 'campaign_id': 'gio-profile-20261115',
            'stage': 'dev', 'kind': 'build', 'method_id': 'P2', 'code_sha': self.index['runtime_sha'],
            'contract_sha256': self.contract_ref['sha256'], 'config_hash': digest(config),
            'source_manifest_hash': row['source_manifest_hash'], 'documents_hash': digest('synthetic-source-records'),
            'items_hash': digest([]), 'profile_hash': None, 'personalization_cap': 512, 'replicate_id': 0,
            'extractor': {'model': 'gpt-6-luna'}, 'consumer': None, 'option_order_schedule': [],
            'allocation': {'max_calls': 1, 'max_usd': 1, 'max_seconds': 240},
            'retry_policy': {'max_attempts': 1, 'retry_uncertain': False}, 'parent_job_ids': [],
            'expected_outputs': ['profile.json', 'result.json']}
        manifest['job_id'] = job_id(manifest)
        row.update(job_id=manifest['job_id'], documents_hash=manifest['documents_hash'], release=old_release)
        mapping['release'] = actual_release
        old = {'schema_version': 'overnight-packet-v1', 'manifest': copy.deepcopy(manifest),
            'config': copy.deepcopy(config), 'backend': {'model': 'gpt-6-luna', 'reasoning': 'medium',
                'max_calls': 1, 'max_tokens': 16384, 'timeout': 180},
            'registration': {'module': 'autoresearch.taste.overnight.profiles_summary', 'function': 'register_summary_builders'},
            'item_ids': [], 'profile': None, 'release': old_release,
            'lease': {'lease_id': 'synthetic-old-lease', 'owner': 'coordinator', 'expires_at': '2026-11-15T17:00:00Z'}}
        actual = copy.deepcopy(old)
        actual.update(release=actual_release, lease={'lease_id': 'synthetic-new-lease',
                      'owner': 'coordinator', 'expires_at': '2026-11-15T17:00:00Z'})
        if change == 'old-manifest': old['manifest']['personalization_cap'] = 2048
        if change == 'old-manifest-type': old['manifest']['replicate_id'] = False
        if change == 'old-config-type': old['config']['extractor_settings']['temperature'] = False
        if change == 'backend-type': actual['backend']['max_calls'] = True
        if change == 'actual-manifest': actual['manifest']['personalization_cap'] = 2048
        if change == 'actual-config': actual['config']['extractor_settings']['max_tokens'] = 8192
        if change == 'both-config':
            old['config']['extractor_settings']['max_tokens'] = 8192
            actual['config']['extractor_settings']['max_tokens'] = 8192
        if change == 'backend': actual['backend']['model'] = 'gpt-6-sol'
        if change == 'registration': actual['registration']['module'] = 'foreign.module'
        if change == 'item-order': actual['item_ids'] = ['extra-item']
        if change == 'profile': actual['profile'] = self.ref('borrowed-profile')
        if change == 'source-pin': row['source_manifest_hash'] = digest('changed-sources')
        if change == 'document-pin': row['documents_hash'] = digest('changed-records')
        if change == 'job-id': row['job_id'] = digest('changed-job')
        if change == 'release-content':
            actual_release = save('actual-release', dict(release, items_sha256=digest('different-items')))
            actual['release'] = mapping['release'] = actual_release
        row['build_packet'] = save('old-packet', old)
        mapping['build_packet'] = save('actual-packet', actual)
        row['original_prepared'] = save('old-prepared', {'prepared': True, 'jobs': [row['build_packet']]})
        evidence = {'schema_version': 'unattempted-rebind-evidence-v1', 'old_prepared': row['original_prepared'],
            'no_retry': True, 'manifest_and_job_ids_unchanged': True, 'claims_and_outputs_preserved': True,
            'calls_performed': 0, 'ledger_mutations': 0,
            'mappings': [{'job_id': row['job_id'], 'old_packet': row['build_packet'],
                'manifest_sha256': digest(actual['manifest']), 'old_lease_id': old['lease']['lease_id'],
                'new_lease_id': actual['lease']['lease_id']}],
            'evidence': [{'job_id': row['job_id'], 'runner_claim_absent': True,
                'output_and_started_traces_absent': True, 'execution_listings': []}]}
        if change == 'evidence-calls': evidence['calls_performed'] = 1
        if change == 'evidence-bool': evidence['calls_performed'] = False
        if change == 'evidence-float': evidence['ledger_mutations'] = 0.0
        if change == 'evidence-retry': evidence['no_retry'] = False
        if change == 'evidence-preserved': evidence['claims_and_outputs_preserved'] = False
        if change == 'record-missing': evidence['mappings'] = []
        if change == 'record-duplicate': evidence['mappings'] *= 2
        if change == 'record-manifest': evidence['mappings'][0]['manifest_sha256'] = digest('changed-manifest')
        if change == 'record-old-packet': evidence['mappings'][0]['old_packet'] = self.ref('foreign-old-packet')
        if change == 'record-old-lease': evidence['mappings'][0]['old_lease_id'] = 'foreign-old-lease'
        if change == 'record-new-lease': evidence['mappings'][0]['new_lease_id'] = 'foreign-new-lease'
        if change == 'absence-missing': evidence['evidence'] = []
        if change == 'absence-duplicate': evidence['evidence'] *= 2
        if change == 'claim-existed': evidence['evidence'][0]['runner_claim_absent'] = False
        if change == 'trace-existed': evidence['evidence'][0]['output_and_started_traces_absent'] = False
        if change == 'listings-missing': evidence['evidence'][0].pop('execution_listings')
        evidence_ref = save('rebind-evidence', evidence)
        prepared = {'prepared': True, 'jobs': [mapping['build_packet']],
                    'rebound_from': row['original_prepared'], 'rebind_evidence': evidence_ref}
        if change == 'prepared-packet': prepared['jobs'] = []
        if change == 'rebound-missing': prepared.pop('rebound_from')
        if change == 'rebound-wrong': prepared['rebound_from'] = self.ref('different-prepared')
        if change == 'evidence-missing': prepared.pop('rebind_evidence')
        mapping['build_prepared'] = save('actual-prepared', prepared)
        claim = {'status': 'claimed', 'manifest': copy.deepcopy(actual['manifest']), 'lease': copy.deepcopy(actual['lease'])}
        if change == 'claim-status': claim['status'] = 'unknown'
        if change == 'claim-manifest': claim['manifest']['personalization_cap'] = 2048
        if change == 'claim-manifest-type': claim['manifest']['replicate_id'] = False
        if change == 'claim-lease': claim['lease']['lease_id'] = 'foreign-lease'
        claim_ref = save('actual-claim', claim)
        case = {'cell_id': row['cell_id'], 'status': 'complete', 'actual_claim_matches': True,
            'original_semantic_identity_unchanged': True,
            'changed_reference_fields': ['build_prepared', 'build_packet', 'release'],
            'profile_id': row['profile_id'], 'original_index_packet': row['build_packet'],
            'original_index_prepared': row['original_prepared'], 'actual_packet': mapping['build_packet'],
            'actual_prepared': mapping['build_prepared'], 'actual_result': mapping['build_result'],
            'actual_claim': claim_ref, 'rebind_evidence': evidence_ref}
        return case, row, mapping, raw_payloads

    def test_exact_listed_continuation_preserves_original_execution_and_saved_profile(self):
        case, row, mapping, payloads = self.continuation_fixture()
        before = copy.deepcopy((case, row, mapping, payloads))
        result = self.helper.validate_continuation_case(case, row, mapping, payloads)
        self.assertEqual((case, row, mapping, payloads), before)
        self.assertEqual(result['origin_job_id'], row['job_id'])
        self.assertEqual(result['original_packet'], row['build_packet'])
        self.assertEqual(result['actual_packet'], mapping['build_packet'])
        self.assertEqual(result['actual_claim'], case['actual_claim'])
        self.assertEqual(result['rebind_evidence'], case['rebind_evidence'])
        self.assertEqual(mapping['profile_id'], row['profile_id'])
        self.assertEqual(mapping['release']['sha256'], row['release']['sha256'])
        self.assertNotEqual(mapping['release']['path'], row['release']['path'])

    def test_every_read_evidence_reference_requires_its_exact_bytes(self):
        for field in ('original_index_packet', 'actual_packet', 'actual_claim', 'original_index_prepared',
                      'actual_prepared', 'rebind_evidence'):
            for mode in ('missing', 'changed'):
                case, row, mapping, payloads = self.continuation_fixture()
                if mode == 'missing': payloads.pop(case[field]['path'])
                else: payloads[case[field]['path']] += ' '
                with self.subTest(field=field, mode=mode), self.assertRaisesRegex(ValueError, 'evidence bytes'):
                    self.helper.validate_continuation_case(case, row, mapping, payloads)

    def test_rehashed_semantic_packet_and_source_identity_changes_reject(self):
        for change in ('old-manifest', 'old-manifest-type', 'old-config-type', 'backend-type',
                       'actual-manifest', 'actual-config', 'both-config', 'backend', 'registration', 'item-order', 'profile', 'source-pin', 'document-pin', 'job-id', 'release-content'):
            args = self.continuation_fixture(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.helper.validate_continuation_case(*args)

    def test_rehashed_claim_and_preparation_lineage_changes_reject(self):
        for change in ('claim-status', 'claim-manifest', 'claim-manifest-type', 'claim-lease', 'prepared-packet',
                       'rebound-missing', 'rebound-wrong', 'evidence-missing'):
            args = self.continuation_fixture(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.helper.validate_continuation_case(*args)

    def test_rebind_proof_requires_zero_calls_exact_lease_mapping_and_unique_absence_record(self):
        for change in ('evidence-calls', 'evidence-bool', 'evidence-float', 'evidence-retry', 'evidence-preserved',
                       'record-missing', 'record-duplicate', 'record-manifest', 'record-old-packet',
                       'record-old-lease', 'record-new-lease', 'absence-missing', 'absence-duplicate',
                       'claim-existed', 'trace-existed', 'listings-missing'):
            args = self.continuation_fixture(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.helper.validate_continuation_case(*args)

    def test_case_cannot_relabel_profile_cell_or_allow_other_changed_references(self):
        for field, value in (('cell_id', 'another-cell'), ('profile_id', digest('another-profile')),
                             ('actual_claim_matches', 1), ('original_semantic_identity_unchanged', False),
                             ('changed_reference_fields', ['build_prepared', 'build_packet', 'release', 'profile']),
                             ('changed_reference_fields', ['build_prepared', 'build_packet'])):
            case, row, mapping, payloads = self.continuation_fixture()
            case[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.helper.validate_continuation_case(case, row, mapping, payloads)

    def test_selection_accepts_changed_refs_only_with_exact_listed_continuation_proof(self):
        case, row, mapping, payloads = self.continuation_fixture()
        selection, index = copy.deepcopy(self.selection), copy.deepcopy(self.index)
        selection['selected_configs'][0]['researcher_mappings'][0] = mapping
        index['cells'][0] = row
        proof = {'schema_version': 'scaling-continuation-compatibility-v1',
                 'original_index': self.index_ref, 'cases': [case]}
        kwargs = {'contract_ref': self.contract_ref, 'index_ref': self.index_ref,
                  'continuation_proof': proof, 'continuation_payloads': payloads}
        result = self.helper.validate_descriptive_selection(selection, self.contract, index, **kwargs)
        self.assertEqual(result['status'], 'accepted-descriptive-selection')
        self.assertEqual(result['selected_instances'][0]['continuation']['actual_packet'], mapping['build_packet'])
        self.assertIsNone(result['selected_instances'][1]['continuation'])
        for change in ('missing-proof', 'unlisted-case', 'additional-ref', 'subset-ref', 'duplicate-case', 'wrong-index'):
            changed, arguments = copy.deepcopy(selection), copy.deepcopy(kwargs)
            if change == 'missing-proof': arguments.pop('continuation_proof')
            if change == 'unlisted-case': arguments['continuation_proof']['cases'] = []
            if change == 'additional-ref': changed['selected_configs'][0]['researcher_mappings'][0]['build_result'] = self.ref('foreign-result')
            if change == 'subset-ref': changed['selected_configs'][0]['researcher_mappings'][0]['release'] = row['release']
            if change == 'duplicate-case': arguments['continuation_proof']['cases'] *= 2
            if change == 'wrong-index': arguments['continuation_proof']['original_index'] = self.ref('foreign-index')
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.helper.validate_descriptive_selection(changed, self.contract, index, **arguments)


class ScalingFuturePredictionBoundTests(unittest.TestCase):
    def setUp(self):
        ScalingReservationCeilingTests.setUp(self)

    def test_future_bound_covers_nested_json_escaping_and_unicode(self):
        from autoresearch.taste.overnight.contracts import canonical_json, render_content
        from autoresearch.taste.overnight.consumer import SYSTEM, INSTRUCTION
        item = {'item_id': 'synthetic-order', 'context': 'Context with "quotes" and 雪',
                'options': ['backslash \\ option', 'line\nbreak option']}
        settings = {'temperature': 0.0, 'max_tokens': 8192}
        for content in ('\\' * 220, '"' * 220, '\x00' * 70, '\n' * 220, '雪' * 150, {'key': ['\\"' * 90]}):
            rendered = render_content(content)
            self.assertLessEqual(len(rendered.encode()), 512)
            for model in ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra'):
                body = {'model': model, 'instructions': SYSTEM,
                    'input': INSTRUCTION + '\nINPUT_JSON:\n' + canonical_json({'context': item['context'], 'options': item['options'], 'personalization': rendered}),
                    'max_output_tokens': 8192, 'reasoning': {'effort': 'medium'}, 'store': False,
                    'service_tier': 'default', 'prompt_cache_options': {'mode': 'implicit', 'ttl': '30m'}}
                actual = len(json.dumps(body, ensure_ascii=False, allow_nan=False).encode()) + 1024
                bound = self.helper.future_prediction_bounds([item], model, settings, 512)[0]
                with self.subTest(content_type=type(content).__name__, model=model):
                    self.assertGreaterEqual(bound['input_bound'], actual)
                    self.assertGreaterEqual(bound['max_usd'], self.helper.reservation_ceiling(model, 8192, actual))

    def test_future_bound_preserves_each_item_and_rejects_context_overflow(self):
        items = [{'item_id': 'order-b', 'context': 'short', 'options': ['a', 'b']},
                 {'item_id': 'order-a', 'context': 'x' * 300, 'options': ['a', 'b']}]
        bounds = self.helper.future_prediction_bounds(items, 'gpt-6-astra', {'max_tokens': 8192}, 8192)
        self.assertEqual([b['item_id'] for b in bounds], ['order-b', 'order-a'])
        self.assertGreater(bounds[1]['max_usd'], bounds[0]['max_usd'])
        items[0]['context'] = 'x' * 272000
        with self.assertRaises(ValueError):
            self.helper.future_prediction_bounds(items, 'gpt-6-astra', {'max_tokens': 8192}, 8192)
