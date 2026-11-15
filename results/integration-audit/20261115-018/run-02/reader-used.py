#!/usr/bin/env python3
"""Read pinned pilot metadata and emit only hashes, structural counts and statuses.

Does not import or execute project code, read environment variables, follow
private-label references, read ledger databases, or invoke a transport/backend.
Raw profile/source/decision/response text remains at the coordinator paths.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/private/tmp/gio-profile-20261115-coordinator')
INDEX_PATH = ROOT / 'pilot-completion-index-v1.json'
INDEX_HASH = '6fadfd0466ec959b1cbc5bb6852a135e604834aefd2cdadcb7a7cbb2ad922fb6'
PREPARED = {
 'df8239e96e542be91ebb1cb63b1b7937c97bb4d052ca89f33f6d2f4fe2120b9d': 'ec7278a07e0fe0b2033fcda325de1d0e071d14571ad573c396b4a7b00222a3f0',
 'c0e41ac85c806548b007f47f6ad08a9564ffe75ca4cd5a0a207ef4d936d4051a': '4dfcaccb489ce152f97d01e8321eed4898ec17c6723858723edf3de2914c900a',
}
RUNTIME_SHA = '0dcd4b43b82a5a271d195e0bcc6b67695281f37c'
ITEM_FIELDS = {'item_id', 'researcher_id', 'context', 'options', 'option_order_id'}
MUTABLE = {'job_id', 'lease', 'created_at', 'updated_at'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value).encode('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    reads, checks, jobs = {}, [], []
    schedules = defaultdict(list)
    failures = []

    def check(name, ok, job_id=None):
        entry = {'name': name, 'verified': bool(ok)}
        if job_id:
            entry['job_id'] = job_id
        checks.append(entry)
        if not ok:
            failures.append(entry)

    def read(path, expected=None):
        path = Path(path).resolve(strict=True)
        path.relative_to(ROOT.resolve())
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

    index = read(INDEX_PATH, INDEX_HASH)
    check('index_runtime_pin', index['runtime_sha'] == RUNTIME_SHA)
    check('exact_released_batches', {b['batch_id'] for b in index['batches']} == set(PREPARED))
    selection = None
    for batch in index['batches']:
        batch_id = batch['batch_id']
        expected_path = ROOT / 'receipts' / batch_id / 'preparation' / 'prepared.json'
        check('index_prepared_pointer', Path(batch['prepared']['path']).resolve() == expected_path.resolve() and
              batch['prepared']['sha256'] == PREPARED[batch_id])
        prepared = read(expected_path, PREPARED[batch_id])
        check('prepared_runtime_pin', prepared['code_sha'] == RUNTIME_SHA)
        check('prepared_batch_binding', prepared['batch_id'] == batch_id and prepared['prepared'] is True)
        check('exact_prepared_job_set', {digest(x) for x in prepared['jobs']} == {digest(x['packet']) for x in batch['jobs']} and
              len(prepared['jobs']) == len(batch['jobs']))
        current_selection = ref(prepared['pilot_selection'])
        if selection is not None:
            check('shared_selection', current_selection == selection)
        selection = current_selection
        selected = {s['researcher_id']: s for s in selection['selection']}
        for entry in batch['jobs']:
            packet = ref(entry['packet'])
            manifest, lease, config = packet['manifest'], packet['lease'], packet['config']
            jid = manifest['job_id']
            kind = manifest['kind']
            researcher = entry['researcher_id']
            method = manifest['method_id']
            result = ref(entry['result'])
            output = Path(entry['result']['path']).parent
            saved_manifest = read(output / 'manifest.json')
            claim = read(Path(prepared['roots']['lease']) / (jid + '.json'))
            release = ref(packet['release'])
            by_id = {item['item_id']: item for item in release['items']}
            items = [by_id[item_id] for item_id in packet['item_ids']]
            documents = release['sources']['documents']
            source_manifest = release['sources']['source_manifest']
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
            trace_paths = list(trace_dir.glob('*.json')) if trace_dir.exists() else []
            for number in range(1, attempts + 1):
                started_path = trace_dir / ('%04d-started.json' % number)
                completed_path = trace_dir / ('%04d-complete.json' % number)
                started, completed = read(started_path), read(completed_path)
                trace_hashes.extend([reads[str(started_path.resolve())]['sha256'], reads[str(completed_path.resolve())]['sha256']])
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

    for researcher in selected:
        for method in selection['methods']:
            if method == 'P1':
                check('failed_P1_not_silently_predicted', not schedules[(researcher, method)])
            else:
                actual = schedules[(researcher, method)]
                check('matched_control_schedule', actual == selected[researcher]['selected_items'])
    summary = {'build_jobs': sum(j['kind'] == 'build' for j in jobs), 'prediction_jobs': sum(j['kind'] == 'predict' for j in jobs),
               'recorded_calls': sum(j['recorded_calls'] for j in jobs),
               'extraction_calls': sum(j['recorded_calls'] for j in jobs if j['kind'] == 'build'),
               'completed_control_predictions': sum(j['counts']['complete'] for j in jobs if j['kind'] == 'predict'),
               'failed_P1_builds': sum(j['method'] == 'P1' and j['kind'] == 'build' and j['status'] == 'invalid' for j in jobs),
               'planned_predictions_from_selection': len(selection['methods']) * sum(len(x['selected_items']) for x in selection['selection']),
               'planned_P1_extractions_from_selection': len(selection['selection']),
               'reported_api_usd': sum(j['reported_api_usd'] for j in jobs),
               'trace_files': sum(j['trace_count'] for j in jobs)}
    check('released_pilot_counts', summary['recorded_calls'] == 34 and summary['extraction_calls'] == 2 and
          summary['completed_control_predictions'] == 32 and summary['failed_P1_builds'] == 2 and
          summary['planned_predictions_from_selection'] == 40 and summary['planned_P1_extractions_from_selection'] == 2)
    for path, record in reads.items():
        check('read_file_unchanged', sha(Path(path).read_bytes()) == record['sha256'])
    report = {'audit': 'pilot-runtime-18', 'reviewer_role': '/root/parallel_gap_audit', 'runtime_metadata_pin': RUNTIME_SHA,
              'created_at': datetime.now(timezone.utc).isoformat(), 'summary': summary,
              'check_counts': {'verified': sum(x['verified'] for x in checks), 'failed': len(failures)},
              'failures': failures, 'checks': checks, 'jobs': jobs, 'read_files': list(reads.values()),
              'reader_sha256': sha(Path(__file__).read_bytes()), 'argv': sys.argv,
              'limits': ['Recorded runtime SHA is checked across artifacts; actual runtime source and loaded-process provenance are a separate audit.',
                         '34 is recorded runner/backend attempts and started/completed trace pairs, not independently authenticated provider HTTP logs.',
                         'No private evaluator labels, environment file, credential, provider endpoint or ledger database was accessed.',
                         'No source/profile/decision/response content is emitted or copied. Only metadata/hashes/counts/settings/statuses are retained.',
                         'No scoring, fidelity, provider availability or invoice claim; source/span semantics are separately owned.',
                         'Selection implies 40 predictions plus 2 P1 extractions; actual 32 predictions plus 2 rejected P1 extractions are retained as incomplete coverage.']}
    with (out / 'report.json').open('x') as f:
        json.dump(report, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({'summary': summary, 'check_counts': report['check_counts'], 'failures': failures}, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
