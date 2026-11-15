#!/usr/bin/env python3
"""Read pinned control-v2 metadata; export hashes, structural counts and statuses.

Does not import or execute project code, read environment variables, follow
private-label references, read ledger databases, or invoke a transport/backend.
Raw profile/source/decision/response text remains under the supplied data root.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

INDEX_HASH = '513f75d2cebed5dadd59032b01bbcad7101989d99e2411e2708f650ed087c9b4'
ORIGINAL_INDEX_HASH = '6fadfd0466ec959b1cbc5bb6852a135e604834aefd2cdadcb7a7cbb2ad922fb6'
PREPARED = {
 'df8239e96e542be91ebb1cb63b1b7937c97bb4d052ca89f33f6d2f4fe2120b9d': 'ec7278a07e0fe0b2033fcda325de1d0e071d14571ad573c396b4a7b00222a3f0',
 'c0e41ac85c806548b007f47f6ad08a9564ffe75ca4cd5a0a207ef4d936d4051a': '4dfcaccb489ce152f97d01e8321eed4898ec17c6723858723edf3de2914c900a',
 '1c12f782508bf0137a7a85311da74092eb62544b371a9d8a68cbc7682abf1d27': '37daa1302fc1d7642da66bd6a2807a0261bdc9eb2992945caaccfc62287f7b03',
 'c56d86db3b2192f1fad130e33fc6702a0e16d9174d46664386272ac519adf69d': 'a33656f7c630fd07e4d6815427de2c78a5f59be89190088ad8329861bafee3de',
}
CONTROLS = {'no_profile', 'name_only', 'raw_evidence', 'lexical_retrieval'}
RUNTIME_SHA = '0dcd4b43b82a5a271d195e0bcc6b67695281f37c'
ITEM_FIELDS = {'item_id', 'researcher_id', 'context', 'options', 'option_order_id'}
MUTABLE = {'job_id', 'lease', 'created_at', 'updated_at'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value).encode('utf-8'))


class DataPaths:
    """Map recorded absolute pointers into one local root without reading the old root."""

    def __init__(self, data_root, recorded_data_root=None):
        self.input_root = Path(data_root).absolute()
        self.root = self.input_root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('data root must be a directory')
        self.recorded_root = Path(recorded_data_root) if recorded_data_root is not None else None
        if self.recorded_root is not None and (
                not self.recorded_root.is_absolute() or '..' in self.recorded_root.parts):
            raise ValueError('recorded data root must be an absolute path without traversal')

    def map(self, path, *, must_exist=True):
        path = Path(path)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('reader requires an absolute pointer without traversal')
        for prefix in (self.root, self.input_root, self.recorded_root):
            if prefix is None:
                continue
            try:
                relative = path.relative_to(prefix)
            except ValueError:
                continue
            mapped = (self.root / relative).resolve(strict=must_exist)
            mapped.relative_to(self.root)
            return mapped
        raise ValueError('reader refuses pointer outside supplied data roots')

    def trace_files(self, directory):
        directory = self.map(directory, must_exist=False)
        if not directory.exists():
            return []
        if not directory.is_dir():
            raise ValueError('trace path must be a directory')
        return sorted(self.map(path) for path in directory.glob('*.json'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', type=Path, required=True,
                        help='Local directory containing the pinned completion index and evidence tree')
    parser.add_argument('--recorded-data-root', type=Path,
                        help='Original absolute root embedded in references; map it to --data-root without rewriting bytes')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    paths = DataPaths(args.data_root, args.recorded_data_root)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    reads, checks, jobs = {}, [], []
    schedules, batch_schedules = defaultdict(list), defaultdict(list)
    selections, releases, profiles_used, build_jobs, prediction_parents = {}, {}, defaultdict(set), {}, []
    full_identities, source_lineage, decision_cells = set(), defaultdict(set), defaultdict(dict)
    batch_summaries, execution_summaries, submitted_job_ids = [], [], []
    failures = []

    def check(name, ok, job_id=None):
        entry = {'name': name, 'verified': bool(ok)}
        if job_id:
            entry['job_id'] = job_id
        checks.append(entry)
        if not ok:
            failures.append(entry)

    def read(path, expected=None):
        path = paths.map(path)
        # Every file is an explicitly referenced metadata/release/profile/trace
        # JSON or a derivation of a released job ID, never an arbitrary traversal.
        if path.suffix != '.json' or any(x in path.name.lower() for x in ('env', 'secret', 'label', 'key')):
            raise ValueError('reader refuses nonapproved filename category')
        raw = path.read_bytes()
        hashed = sha(raw)
        reads[str(path)] = {'path': str(path), 'sha256': hashed, 'size_bytes': len(raw)}
        if expected:
            check('referenced_file_hash', hashed == expected)
        return json.loads(raw)

    def ref(value):
        return read(value['path'], value['sha256'])

    index = read(paths.root / 'control-v2-completion-index-v1.json', INDEX_HASH)
    check('index_runtime_pin', index['runtime_sha'] == RUNTIME_SHA)
    check('exact_released_batches', {b['batch_id'] for b in index['batches']} == set(PREPARED))
    check('original_index_pin', index['original_pilot_index']['sha256'] == ORIGINAL_INDEX_HASH)
    original = ref(index['original_pilot_index'])
    check('original_batches_preserved_exactly', index['batches'][:2] == original['batches'])
    selection_settings = None
    for batch in index['batches']:
        batch_id = batch['batch_id']
        expected_path = paths.root / 'receipts' / batch_id / 'preparation' / 'prepared.json'
        check('index_prepared_pointer', paths.map(batch['prepared']['path']) == paths.map(expected_path) and
              batch['prepared']['sha256'] == PREPARED[batch_id])
        prepared = read(expected_path, PREPARED[batch_id])
        check('prepared_runtime_pin', prepared['code_sha'] == RUNTIME_SHA)
        check('prepared_batch_binding', prepared['batch_id'] == batch_id and prepared['prepared'] is True)
        check('exact_prepared_job_set', {digest(x) for x in prepared['jobs']} == {digest(x['packet']) for x in batch['jobs']} and
              len(prepared['jobs']) == len(batch['jobs']))
        selection = ref(prepared['pilot_selection'])
        selection_hash = prepared['pilot_selection']['sha256']
        if selection_hash in selections:
            check('selection_version_unchanged', selections[selection_hash] == selection)
        selections[selection_hash] = selection
        current_settings = {k: selection[k] for k in ('consumer_settings', 'extraction_settings', 'model', 'reasoning', 'personalization_cap', 'replicate_id')}
        if selection_settings is not None:
            check('settings_frozen_across_versions', selection_settings == current_settings)
        selection_settings = current_settings
        selected = {s['researcher_id']: s for s in selection['selection']}
        batch_job_start = len(jobs)
        if 'execution_summary' in batch:
            execution = ref(batch['execution_summary'])
            check('execution_summary_jobs_complete', execution['batch_id'] == batch_id and execution['status'] == 'complete' and
                  execution['stop_reason'] is None and execution['counts'] == {'complete': len(batch['jobs']), 'dispatched': len(batch['jobs']),
                  'listed': len(batch['jobs']), 'not_dispatched': 0, 'other': 0})
            execution_summaries.append({'batch_id': batch_id, 'counts': execution['counts'], 'status': execution['status'], 'ledger': execution['ledger']})
        for entry in batch['jobs']:
            packet = ref(entry['packet'])
            manifest, lease, config = packet['manifest'], packet['lease'], packet['config']
            jid = manifest['job_id']
            submitted_job_ids.append(jid)
            kind = manifest['kind']
            researcher = entry['researcher_id']
            method = manifest['method_id']
            result = ref(entry['result'])
            output = paths.map(entry['result']['path']).parent
            saved_manifest = read(output / 'manifest.json')
            claim = read(paths.map(prepared['roots']['lease']) / (jid + '.json'))
            release = ref(packet['release'])
            by_id = {item['item_id']: item for item in release['items']}
            items = [by_id[item_id] for item_id in packet['item_ids']]
            documents = release['sources']['documents']
            source_manifest = release['sources']['source_manifest']
            if researcher in releases:
                check('released_full_items_stable', releases[researcher] == release['items'], jid)
            else:
                releases[researcher] = release['items']
            source_lineage[researcher].add((manifest['source_manifest_hash'], digest(documents), packet['release']['sha256']))
            expected_identity = manifest['extractor' if kind == 'build' else 'consumer']
            settings = config['extractor_settings' if kind == 'build' else 'settings']

            check('job_id_semantic_hash', jid == digest({k: v for k, v in manifest.items() if k not in MUTABLE}), jid)
            check('packet_index_binding', jid == entry['job_id'] and kind == entry['kind'] and method == entry['method'], jid)
            check('manifest_file_and_index_binding', saved_manifest == manifest and entry['manifest_sha256'] == digest(manifest), jid)
            check('lease_exact_binding', claim['manifest'] == manifest and claim['lease'] == lease and
                  claim['status'] == 'claimed' and lease['job_id'] == jid, jid)
            check('result_manifest_binding', result['job_id'] == jid and result['manifest_hash'] == digest(manifest) and
                  result['config_hash'] == digest(config) == manifest['config_hash'] and result['code_sha'] == RUNTIME_SHA == manifest['code_sha'], jid)
            check('result_index_binding', result['status'] == entry['status'] and result['usage'] == entry['usage'], jid)
            check('dev_label_free_inputs', manifest['stage'] == result['stage'] == 'dev' and all(set(x) == ITEM_FIELDS for x in release['items']), jid)
            check('source_hash_chain', digest(source_manifest) == release['sources']['allowed_source_manifest_hash'] ==
                  manifest['source_manifest_hash'] == result['source_manifest_hash'] and digest(documents) == manifest['documents_hash'] and
                  all(sha(d['content'].encode('utf-8')) == d['content_sha256'] for d in documents), jid)
            check('selection_settings', settings == selection['extraction_settings' if kind == 'build' else 'consumer_settings'] and
                  packet['backend']['model'] == selection['model'] and packet['backend']['reasoning'] == selection['reasoning'] and
                  manifest['personalization_cap'] == selection['personalization_cap'] and manifest['replicate_id'] == selection['replicate_id'], jid)
            check('actual_backend_identity', result['actual_backend'] == expected_identity and expected_identity['model'] == packet['backend']['model'] and
                  expected_identity['enforced_settings']['reasoning_effort'] == packet['backend']['reasoning'], jid)
            check('declared_budget_and_retry', manifest['retry_policy'] == {'max_attempts': 1, 'retry_uncertain': False} and
                  manifest['allocation']['cost_mode'] == 'priced_api' and all(packet['backend'][k] == manifest['allocation'][k]
                  for k in ('max_calls', 'max_seconds', 'max_usd')), jid)

            profile_ref = packet['profile'] if kind == 'predict' else None
            profile = ref(profile_ref) if profile_ref else read(output / 'profile.json')
            if kind == 'build':
                build_jobs[jid] = {'profile_id': profile['profile_id'], 'status': profile['status'], 'method': method,
                                   'researcher_id': researcher, 'source_manifest_hash': profile['allowed_source_manifest_hash']}
                check('built_profile_result_binding', profile == result['profile'] and profile['profile_id'] == result['profile_hash'], jid)
                # Retrieval builders bind one selected decision/order. Other
                # builds carry no items; verify exact packet inputs in both cases.
                build_schedule = [{'item_id': x['item_id'], 'option_order_id': x['option_order_id']} for x in items]
                check('build_inputs_hash', digest(documents) == manifest['documents_hash'] and manifest['items_hash'] == digest(items) and
                      manifest['option_order_schedule'] == build_schedule and
                      all(x in selected[researcher]['selected_items'] for x in build_schedule), jid)
            else:
                schedule = [{'item_id': x['item_id'], 'option_order_id': x['option_order_id']} for x in items]
                check('prediction_profile_binding', profile['profile_id'] == manifest['profile_hash'] == result['profile_hash'], jid)
                check('selected_schedule_hash', digest(items) == manifest['items_hash'] and schedule == manifest['option_order_schedule'] and
                      all(x in selected[researcher]['selected_items'] for x in schedule), jid)
                schedules[(researcher, method)].extend(schedule)
                batch_schedules[(batch_id, researcher, method)].extend(schedule)
                profiles_used[(researcher, method)].add(profile['profile_id'])
                full_identities.add(digest(expected_identity))
                prediction_parents.append({'job_id': jid, 'parent_job_ids': manifest['parent_job_ids'], 'profile_id': profile['profile_id'],
                                           'method': method, 'researcher_id': researcher, 'source_manifest_hash': manifest['source_manifest_hash']})
                for item in items:
                    cell = (researcher, item['item_id'], item['option_order_id'])
                    check('no_duplicate_method_decision_cell', method not in decision_cells[cell], jid)
                    decision_cells[cell][method] = digest({'context': item['context'], 'options': item['options']})
                check('prediction_row_hashes', len(result['predictions']) == len(items) and all(
                      row['item_id'] == item['item_id'] and row['item_sha256'] == digest(item) and row['items_sha256'] == digest(items) and
                      row['job_id'] == jid and row['manifest_sha256'] == digest(manifest) and row['actual_consumer'] == expected_identity
                      for row, item in zip(result['predictions'], items)), jid)
            check('profile_hash_chain', profile['profile_id'] == digest({k: v for k, v in profile.items() if k != 'profile_id'}) and
                  profile['content_sha256'] == digest(profile['content']) and profile['config_id'] == digest(profile['config']) and
                  profile['allowed_source_manifest_hash'] == manifest['source_manifest_hash'], jid)

            attempts = result['usage']['attempted_calls']
            trace_hashes, trace_summaries = [], []
            trace_dir = output / 'traces'
            trace_paths = paths.trace_files(trace_dir)
            for number in range(1, attempts + 1):
                started_path = trace_dir / ('%04d-started.json' % number)
                completed_path = trace_dir / ('%04d-complete.json' % number)
                started, completed = read(started_path), read(completed_path)
                trace_hashes.extend([reads[str(paths.map(started_path))]['sha256'], reads[str(paths.map(completed_path))]['sha256']])
                key = digest({'manifest': {k: v for k, v in manifest.items() if k not in MUTABLE},
                              'prompt': started['prompt'], 'settings': started['settings']})
                check('trace_request_binding', started['attempt'] == number and started['status'] == 'started' and
                      started['backend'] == expected_identity and {k: v for k, v in started['settings'].items() if k != 'system'} == settings and
                      started['cache_key'] == key, jid)
                check('trace_completion_binding', completed['attempt'] == number and completed['status'] == 'complete' and
                      completed['cache_key'] == key and completed['response_sha256'] == sha(completed['response'].encode('utf-8')), jid)
                if kind == 'predict':
                    check('prediction_trace_cache_binding', result['predictions'][number - 1]['cache_provenance'] == {'hit': False, 'key': key}, jid)
                trace_summaries.append({'attempt': number, 'status': completed['status'], 'request_cache_key': key,
                                        'started_file_sha256': trace_hashes[-2], 'complete_file_sha256': trace_hashes[-1],
                                        'response_sha256': completed['response_sha256']})
            check('trace_hash_sequence_exact', result['trace_hashes'] == trace_hashes and len(trace_paths) == len(trace_hashes), jid)
            check('attempts_and_usage_consistent', attempts == result['usage']['budget_detail']['attempted_calls'] and
                  result['usage']['uncertain_attempts'] == 0 and result['usage']['cache_hits'] == 0 and
                  result['usage']['reserved_api_usd'] == 0 and result['usage']['budget_detail']['reported_usage_complete'] is True, jid)
            if kind == 'predict':
                check('prediction_counts_consistent', result['counts'] == {'attempted': len(items), 'complete': len(items), 'error': 0} and
                      attempts == len(items) and all(row['status'] == 'complete' and row['error_code'] is None for row in result['predictions']), jid)
            else:
                complete = int(profile['status'] == 'complete')
                check('build_counts_consistent', result['counts'] == {'attempted': 1, 'complete': complete, 'error': 1 - complete} and
                      result['status'] == profile['status'] and attempts == (1 if method == 'P1' else 0), jid)
            jobs.append({'job_id': jid, 'batch_id': batch_id, 'kind': kind, 'method': method, 'researcher_id': researcher,
                         'status': result['status'], 'profile_status': profile['status'], 'profile_error_code': profile.get('error_code'),
                         'profile_id': profile['profile_id'], 'profile_content_sha256': profile['content_sha256'],
                         'counts': result['counts'], 'recorded_calls': attempts, 'trace_count': len(trace_hashes),
                         'manifest_sha256': digest(manifest), 'source_manifest_hash': manifest['source_manifest_hash'],
                         'selected_schedule_sha256': digest(manifest['option_order_schedule']), 'settings': settings,
                         'model': packet['backend']['model'], 'reasoning': packet['backend']['reasoning'],
                         'api_adapter_identity_sha256': expected_identity['enforced_settings']['adapter_implementation_sha256'],
                         'reported_api_usd': result['usage']['reported_api_usd'], 'traces': trace_summaries})
        subset = jobs[batch_job_start:]
        batch_summaries.append({'batch_id': batch_id, 'selection_sha256': selection_hash, 'jobs': len(subset),
                               'build_jobs': sum(j['kind'] == 'build' for j in subset), 'prediction_jobs': sum(j['kind'] == 'predict' for j in subset),
                               'recorded_calls': sum(j['recorded_calls'] for j in subset),
                               'prediction_rows': sum(j['counts']['complete'] for j in subset if j['kind'] == 'predict')})
        prediction_methods = {j['method'] for j in subset if j['kind'] == 'predict'}
        if prediction_methods:
            check('exact_submitted_prediction_methods', prediction_methods == CONTROLS)
            for researcher in selected:
                for method in CONTROLS:
                    check('batch_exact_selected_schedule', batch_schedules[(batch_id, researcher, method)] == selected[researcher]['selected_items'])

    check('no_duplicate_jobs_between_batches', len(submitted_job_ids) == len(set(submitted_job_ids)))
    for row in prediction_parents:
        parents = row['parent_job_ids']
        expected = {k: row[k] for k in ('profile_id', 'method', 'researcher_id', 'source_manifest_hash')}
        check('prediction_uses_exact_completed_parent_profile', len(parents) == 1 and parents[0] in build_jobs and
              build_jobs[parents[0]] == dict(expected, status='complete'), row['job_id'])
    check('single_frozen_consumer_identity', len(full_identities) == 1)
    for researcher, released in releases.items():
        expected_schedule = Counter((x['item_id'], x['option_order_id']) for x in released)
        check('released_ordered_ids_unique', len(expected_schedule) == len(released))
        check('one_frozen_source_lineage', len(source_lineage[researcher]) == 1)
        for method in CONTROLS:
            actual = schedules[(researcher, method)]
            check('exact_full_control_coverage_no_duplicates', Counter((x['item_id'], x['option_order_id']) for x in actual) == expected_schedule)
            if method != 'lexical_retrieval':
                check('same_static_profile_reused_across_batches', len(profiles_used[(researcher, method)]) == 1)
        check('failed_P1_not_silently_predicted', not schedules[(researcher, 'P1')])
    for cell, methods in decision_cells.items():
        check('matched_decision_across_all_controls', set(methods) == CONTROLS and len(set(methods.values())) == 1)
    selection_versions = list(selections.values())
    check('exact_two_selection_versions', len(selection_versions) == 2)
    for researcher in releases:
        groups = [{(x['item_id'], x['option_order_id']) for s in version['selection'] if s['researcher_id'] == researcher for x in s['selected_items']}
                  for version in selection_versions]
        expected = {(x['item_id'], x['option_order_id']) for x in releases[researcher]}
        check('pilot_and_continuation_disjoint_complete', len(groups) == 2 and not (groups[0] & groups[1]) and groups[0] | groups[1] == expected)
    summary = {'build_jobs': sum(j['kind'] == 'build' for j in jobs), 'prediction_jobs': sum(j['kind'] == 'predict' for j in jobs),
               'recorded_calls': sum(j['recorded_calls'] for j in jobs),
               'extraction_calls': sum(j['recorded_calls'] for j in jobs if j['kind'] == 'build'),
               'completed_control_predictions': sum(j['counts']['complete'] for j in jobs if j['kind'] == 'predict'),
               'failed_P1_builds': sum(j['method'] == 'P1' and j['kind'] == 'build' and j['status'] == 'invalid' for j in jobs),
               'expected_control_predictions': len(CONTROLS) * sum(len(x) for x in releases.values()),
               'matched_ordered_decisions': len(decision_cells),
               'unique_static_profiles': sum(len(ids) for (researcher, method), ids in profiles_used.items() if method != 'lexical_retrieval'),
               'unique_retrieval_profiles': sum(len(ids) for (researcher, method), ids in profiles_used.items() if method == 'lexical_retrieval'),
               'reported_api_usd': str(sum((Decimal(str(j['reported_api_usd'])) for j in jobs), Decimal(0))),
               'trace_files': sum(j['trace_count'] for j in jobs)}
    check('released_control_v2_counts', summary['recorded_calls'] == 114 and summary['extraction_calls'] == 2 and
          summary['completed_control_predictions'] == summary['expected_control_predictions'] == 112 and summary['failed_P1_builds'] == 2 and
          summary['matched_ordered_decisions'] == 28 and [b['prediction_rows'] for b in batch_summaries] == [0, 32, 0, 80])
    final_ledger = execution_summaries[-1]['ledger']
    check('recorded_phase1_ledger_reconciles_embedding_calls', final_ledger['attempts'] == summary['recorded_calls'] + 2 == 116 and
          Decimal(str(final_ledger['spent_usd'])) == Decimal(summary['reported_api_usd']) + Decimal('0.00007848') and
          final_ledger['reserved_usd'] == final_ledger['uncertain'] == final_ledger['inflight'] == 0)
    for path, record in reads.items():
        check('read_file_unchanged', sha(paths.map(path).read_bytes()) == record['sha256'])
    report = {'audit': 'control-runtime-24', 'reviewer_role': '/root/parallel_gap_audit', 'runtime_metadata_pin': RUNTIME_SHA,
              'created_at': datetime.now(timezone.utc).isoformat(), 'summary': summary,
              'check_counts': {'verified': sum(x['verified'] for x in checks), 'failed': len(failures)},
              'failures': failures, 'checks': checks, 'jobs': jobs, 'batches': batch_summaries, 'execution_summaries': execution_summaries,
              'read_files': list(reads.values()), 'matched_decision_hashes': [
                  {'researcher_id': cell[0], 'item_identity_sha256': digest(cell[1:]), 'context_options_sha256': next(iter(methods.values())),
                   'methods': sorted(methods)} for cell, methods in sorted(decision_cells.items())],
              'reader_sha256': sha(Path(__file__).read_bytes()), 'argv': sys.argv,
              'data_root': str(paths.root),
              'recorded_data_root': str(paths.recorded_root) if paths.recorded_root is not None else None,
              'limits': ['Recorded runtime SHA is checked across artifacts; actual runtime source and loaded-process provenance are a separate audit.',
                         '114 is indexed runner/backend attempts; 116 is a recorded campaign-ledger snapshot including two separately audited embedding calls.',
                         'Cost reconciliation uses the pinned two-call embedding amount from audit021, not a new active-ledger query or provider invoice.',
                         'No private evaluator labels, environment file, credential, provider endpoint or ledger database was accessed.',
                         'No source/profile/decision/response content is emitted or copied. Only metadata/hashes/counts/settings/statuses are retained.',
                         'No scoring, fidelity, provider availability or invoice claim; source/span semantics are separately owned.',
                         'All 112 cells concern the four controls. P1 and semantic prediction performance are not claimed; newer handoffs remain outside this fixed audit.']}
    with (out / 'report.json').open('x') as f:
        json.dump(report, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({'summary': summary, 'check_counts': report['check_counts'], 'failures': failures}, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
