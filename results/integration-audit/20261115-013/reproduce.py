"""Retest claimed runner fixes, with matched positive controls. Synthetic only.

Usage: python3 -B reproduce.py --source-root PINNED_SNAPSHOT --out NEW_DIRECTORY
Optional --contract points to the separately supplied shared contract for hashing.
Exit zero means the audit completed; individual verified/failed/unverified results
are explicit in report.json. All runner-created artifacts are under --out.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def metadata_builder(documents, config, extractor):
    return {'content': {'ids_in_order': [doc['document_id'] for doc in documents],
                        'authors': [doc.get('author') for doc in documents]}}


def divergent_settings_builder(documents, config, extractor):
    extractor.complete('Synthetic extraction request', temperature=1.0, max_tokens=32)
    return {'content': 'Synthetic profile generated after a recorded fixture call.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract', type=Path)
    args = parser.parse_args()
    source, out = args.source_root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pin = json.loads((source / 'AUDIT_SOURCE.json').read_text())
    checked = [{'path': name, 'expected': expected, 'actual': sha(source / name)}
               for name, expected in pin['files'].items()]
    assert all(row['expected'] == row['actual'] for row in checked), 'Pinned source mismatch'
    dump(out / 'source-verification.json', {'source_commit': pin['source_commit'],
         'implementation_commit': pin['implementation_commit'],
         'audit_source_sha256': sha(source / 'AUDIT_SOURCE.json'), 'files': checked,
         'contract_sha256': sha(args.contract) if args.contract else None,
         'reproducer_sha256': sha(__file__)})
    command = [sys.executable, '-B', '-m', 'unittest', 'tests.test_overnight_runner', '-v']
    tests = subprocess.run(command, cwd=source, text=True, capture_output=True)
    dump(out / 'owner-tests-command.json', {'argv': command, 'cwd': str(source), 'exit_code': tests.returncode})
    (out / 'owner-tests-stdout.txt').write_text(tests.stdout)
    (out / 'owner-tests-stderr.txt').write_text(tests.stderr)
    sys.path.insert(0, str(source))
    from tests import test_overnight_contracts as fixture
    from autoresearch.taste.overnight import runner, registry
    from autoresearch.taste.overnight.contracts import backend_identity, digest, sha256_text

    class Recording(fixture.RecordingConsumer):
        def __init__(self, action=None, fail=False):
            super().__init__()
            self.action, self.fail = action, fail

        def complete(self, prompt, **settings):
            result = super().complete(prompt, **settings)
            if self.action:
                self.action(len(self.prompts))
            if self.fail:
                raise RuntimeError('synthetic uncertain transport')
            return result

    def setup():
        case = fixture.ContractTests()
        case.setUp()
        profile = case.build()
        config = case.prediction_config(profile)
        items = [{'item_id': 'synthetic-1', 'researcher_id': 'synthetic',
                  'context': 'Synthetic first question', 'options': ['left', 'right'], 'option_order_id': 'ab'}]
        return case, profile, config, items

    def manifest(profile, config, items, backend, **changes):
        value = {'schema_version': 'overnight-job-v1', 'campaign_id': 'synthetic-independent-runner-audit',
                 'stage': 'offline', 'kind': 'predict', 'contract_sha256': 'c' * 64,
                 'config_hash': digest(config), 'source_manifest_hash': profile.allowed_source_manifest_hash,
                 'items_hash': digest(items), 'profile_hash': profile.profile_id,
                 'method_id': profile.method_id, 'extractor': profile.extractor,
                 'consumer': backend_identity(backend), 'personalization_cap': profile.personalization_cap,
                 'option_order_schedule': [{'item_id': i['item_id'], 'option_order_id': i['option_order_id']} for i in items],
                 'replicate_id': profile.replicate_id, 'code_sha': pin['implementation_commit'],
                 'allocation': {'max_calls': 2, 'max_seconds': 30, 'max_usd': 0,
                                'cost_mode': 'offline', 'authorization_source': 'synthetic-fixture'},
                 'retry_policy': {'max_attempts': 1, 'retry_uncertain': False},
                 'parent_job_ids': [], 'expected_outputs': ['result.json', 'traces']}
        value.update(changes)
        value['job_id'] = runner.job_id(value)
        return value

    def invoke(name, body, profile, config, items, backend, cache=True, **kwargs):
        root = out / name
        lease = {'job_id': body['job_id'], 'lease_id': 'synthetic-lease', 'owner': 'synthetic-auditor',
                 'expires_at': '2099-01-01T00:00:00+00:00'}
        return runner.run_job(body, lease, output_root=root / 'outputs', lease_root=root / 'leases',
                              cache_root=root / 'cache' if cache else None, profile=profile,
                              config=config, items=items, consumer=backend, **kwargs)

    def traces(name, body):
        root = out / name / 'outputs' / body['job_id'] / 'traces'
        return [json.loads(path.read_text()) for path in sorted(root.glob('*-started.json'))]

    results = []
    prior_findings = {'mutable_inputs', 'elapsed_with_cache', 'missing_cost_mode',
                      'build_metadata_binding', 'build_settings_binding'}
    def record(case, status, expected, observed):
        row = {'case': case, 'status': status, 'expected': expected, 'observed': observed}
        if case in prior_findings:
            already_fixed = case == 'build_metadata_binding'
            row['comparison'] = {'original_source': '05c503e5f6170a690a13feb75cbe2dc65d430ba8',
                                 'original_status': 'failed',
                                 'previous_source': 'c840615c885464404147a1cdea12343569d331fc',
                                 'previous_status': 'fixed' if already_fixed else 'failed',
                                 'new_source': pin['source_commit'],
                                 'change': ('still_fixed' if already_fixed else 'fixed') if status == 'verified' else 'remaining'}
        results.append(row)
        dump(out / (case + '.json'), row)

    # Passing control: durable duplicate claim across concurrent workers.
    _, profile, config, items = setup()
    backend = Recording()
    body = manifest(profile, config, items, backend)
    def concurrent_worker(_):
        try:
            return invoke('control_concurrent', body, profile, config, items, backend)['status']
        except FileExistsError:
            return 'duplicate_claim_rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(concurrent_worker, (1, 2)))
    assert sorted(statuses) == ['complete', 'duplicate_claim_rejected'] and len(backend.prompts) == 1
    record('control_concurrent', 'verified', 'one synthetic execution under one canonical lease root',
           {'statuses': statuses, 'backend_calls': len(backend.prompts)})

    # Passing control: uncertain first call leaves traces, holds later calls, and retains claim.
    _, profile, config, items = setup()
    items.append(dict(items[0], item_id='synthetic-2', context='Second synthetic question'))
    backend = Recording(fail=True)
    body = manifest(profile, config, items, backend)
    result = invoke('control_uncertain', body, profile, config, items, backend)
    assert result['usage']['attempted_calls'] == 1 and result['usage']['uncertain_attempts'] == 1
    assert result['predictions'][1]['error_code'] == 'lane_held_after_uncertain_attempt'
    try:
        invoke('control_uncertain', body, profile, config, items, backend)
        duplicate = 'accepted'
    except FileExistsError:
        duplicate = 'rejected'
    assert duplicate == 'rejected' and len(backend.prompts) == 1
    record('control_uncertain', 'verified', 'failed call retained; no retry or second call',
           {'status': result['status'], 'usage': result['usage'], 'trace_hashes': result['trace_hashes'], 'duplicate': duplicate})

    # Exact former mutation case: caller changes remain outside frozen execution inputs.
    _, profile, config, items = setup()
    items.append(dict(items[0], item_id='synthetic-2', context='Original second synthetic question'))
    original_config, original_items = json.loads(json.dumps(config)), json.loads(json.dumps(items))
    def mutate_inputs(call_number):
        if call_number == 1:
            config['settings']['temperature'] = 1.5
            items[1]['context'] = 'Changed after hashing, before the second synthetic call'
    backend = Recording(action=mutate_inputs)
    body = manifest(profile, config, items, backend)
    result = invoke('mutable_inputs', body, profile, config, items, backend)
    actual = traces('mutable_inputs', body)
    payloads = [json.loads(prompt.split('INPUT_JSON:\n', 1)[1]) for prompt, _ in backend.prompts]
    assert result['status'] == 'complete' and len(actual) == 2
    assert all(row['settings']['temperature'] == 0.0 for row in actual)
    assert payloads[1]['context'] == original_items[1]['context']
    assert body['config_hash'] != digest(config) and body['items_hash'] != digest(items)
    assert result['predictions'][1]['item_sha256'] == digest(original_items[1])
    assert all(row['cache_provenance']['key'] == trace['cache_key'] for row, trace in zip(result['predictions'], actual))
    record('mutable_inputs', 'verified', 'every executed input/setting stays bound to validated immutable job inputs',
           {'job_id': body['job_id'], 'result_status': result['status'],
            'original_config': original_config, 'caller_config_after_mutation': config,
            'original_items': original_items, 'caller_items_after_mutation': items,
            'declared_config_hash': body['config_hash'], 'caller_config_hash_after_mutation': digest(config),
            'declared_items_hash': body['items_hash'], 'caller_items_hash_after_mutation': digest(items),
            'actual_payloads': payloads, 'second_executed_item_hash': result['predictions'][1]['item_sha256'],
            'actual_request_settings': [row['settings'] for row in actual],
            'first_row_cache_key': result['predictions'][0]['cache_provenance']['key'],
            'first_actual_cache_key': actual[0]['cache_key']})

    # Exact former wall-time case: expired cached and uncached paths must both stop.
    for use_cache in (False, True):
        _, profile, config, items = setup()
        items.append(dict(items[0], item_id='synthetic-2'))
        clock = [0.0]
        backend = Recording(action=lambda count: clock.__setitem__(0, 31.0))
        body = manifest(profile, config, items, backend)
        name = 'elapsed_with_cache' if use_cache else 'control_elapsed_without_cache'
        with patch.object(runner.time, 'monotonic', side_effect=lambda: clock[0]):
            result = invoke(name, body, profile, config, items, backend, cache=use_cache)
        assert result['predictions'][1]['error_code'] == 'allocation_exhausted'
        assert result['status'] == 'partial' and result['usage']['cache_hits'] == 0
        cache_files = list((out / name / 'cache').glob('*.json'))
        assert not use_cache or len(cache_files) == 1
        record(name, 'verified', 'stop producing predictions after max_seconds expires',
               {'max_seconds': 30, 'elapsed_seconds': result['usage']['elapsed_seconds'],
                'result_status': result['status'], 'counts': result['counts'], 'usage': result['usage'],
                'prediction_statuses': [row['status'] for row in result['predictions']],
                'cache_files_present': len(cache_files)})

    # Matched positive cache control: a timely hit still reuses a correctly linked entry.
    _, profile, config, items = setup()
    items.append(dict(items[0], item_id='synthetic-2'))
    backend = Recording()
    body = manifest(profile, config, items, backend)
    result = invoke('control_timely_cache', body, profile, config, items, backend)
    actual = traces('control_timely_cache', body)
    cache_files = list((out / 'control_timely_cache' / 'cache').glob('*.json'))
    assert result['status'] == 'complete' and result['counts']['complete'] == 2
    assert len(backend.prompts) == len(actual) == len(cache_files) == 1
    assert result['usage']['cache_hits'] == 1
    assert [row['cache_provenance']['hit'] for row in result['predictions']] == [False, True]
    assert all(row['cache_provenance']['key'] == actual[0]['cache_key'] == cache_files[0].stem for row in result['predictions'])
    record('control_timely_cache', 'verified', 'valid timely cache hit remains functional and correctly attributed',
           {'result_status': result['status'], 'usage': result['usage'],
            'backend_calls': len(backend.prompts), 'trace_cache_key': actual[0]['cache_key'],
            'prediction_cache_provenance': [row['cache_provenance'] for row in result['predictions']]})

    # Exact former missing-mode case: reject before claiming or writing output.
    _, profile, config, items = setup()
    backend = Recording()
    body = manifest(profile, config, items, backend)
    del body['allocation']['cost_mode']
    body['job_id'] = runner.job_id(body)
    try:
        invoke('missing_cost_mode', body, profile, config, items, backend)
        error = None
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    root = out / 'missing_cost_mode'
    claim_exists = (root / 'leases' / (body['job_id'] + '.json')).exists()
    result_exists = (root / 'outputs' / body['job_id'] / 'result.json').exists()
    assert error and error['type'] == 'ValueError' and 'cost_mode' in error['message']
    assert not claim_exists and not result_exists and not backend.prompts and not root.exists()
    record('missing_cost_mode', 'verified', 'reject malformed allocation before claiming or writing output',
           {'exception': error, 'claim_exists': claim_exists, 'result_exists': result_exists,
            'backend_calls': len(backend.prompts)})

    # Satisfy the new full-document hash before probing the original metadata change.
    case, profile, _, _ = setup()
    registry.register_builder('audit-metadata', metadata_builder, prompt_version='audit-v1', prompt_sha256='a' * 64)
    config = dict(case.config, method_id='audit-metadata', code_sha=pin['implementation_commit'],
                  extractor_settings={'temperature': 0.0, 'max_tokens': 128})
    documents = [dict(case.docs[0], author='Synthetic author A')]
    backend = Recording()
    body = manifest(profile, config, [], backend, kind='build', profile_hash=None, items_hash=None,
                    method_id='audit-metadata', extractor=backend_identity(backend),
                    code_sha=config['code_sha'], option_order_schedule=[], documents_hash=digest(documents))
    first = invoke('build_metadata_original', body, None, config, None, backend,
                   documents=documents, extractor=backend)
    changed_documents = [dict(documents[0], author='Synthetic author B')]
    try:
        invoke('build_metadata_changed', body, None, config, None, backend,
               documents=changed_documents, extractor=backend)
        changed_error = None
    except ValueError as exc:
        changed_error = {'type': type(exc).__name__, 'message': str(exc)}
    changed_claim_exists = (out / 'build_metadata_changed' / 'leases' / (body['job_id'] + '.json')).exists()
    updated = dict(body, documents_hash=digest(changed_documents))
    updated['job_id'] = runner.job_id(updated)
    second = invoke('build_metadata_rebound', updated, None, config, None, backend,
                    documents=changed_documents, extractor=backend)
    assert first['status'] == second['status'] == 'complete'
    assert changed_error and 'document records hash mismatch' in changed_error['message']
    assert not changed_claim_exists and first['job_id'] != second['job_id']
    assert first['profile']['documents_hash'] == body['documents_hash']
    assert second['profile']['documents_hash'] == updated['documents_hash']
    record('build_metadata_binding', 'verified', 'reject changed document metadata under old hash; accept explicitly rebound inputs with a new job ID',
           {'original_job_id': body['job_id'], 'updated_job_id': updated['job_id'],
            'original_documents_hash': body['documents_hash'], 'updated_documents_hash': updated['documents_hash'],
            'original_documents': documents, 'changed_documents': changed_documents,
            'unchanged_input_control_status': first['status'], 'changed_input_error': changed_error,
            'changed_input_claim_exists': changed_claim_exists, 'rebound_control_status': second['status'],
            'first_profile_hash': first['profile_hash'], 'second_profile_hash': second['profile_hash'],
            'backend_calls': len(backend.prompts),
            'isolation_note': 'Independent synthetic namespaces ensure metadata rejection, not a previous lease, determines the negative case.'})

    # Matched extraction control uses the identical builder's actual settings, then probe divergence.
    registry.register_builder('audit-settings', divergent_settings_builder, prompt_version='audit-v1', prompt_sha256='a' * 64)
    config = dict(case.config, method_id='audit-settings', code_sha=pin['implementation_commit'],
                  extractor_settings={'temperature': 0.0, 'max_tokens': 128})
    backend = Recording()
    body = manifest(profile, config, [], backend, kind='build', profile_hash=None, items_hash=None,
                    method_id='audit-settings', extractor=backend_identity(backend),
                    code_sha=config['code_sha'], option_order_schedule=[], documents_hash=digest(case.docs))
    result = invoke('build_settings_binding', body, None, config, None, backend,
                    documents=case.docs, extractor=backend)
    assert result['status'] == 'unavailable' and result['error_code'] == 'call_settings_differ_from_declared'
    assert result['usage']['attempted_calls'] == 0 and not backend.prompts and not result['trace_hashes']
    matched_config = dict(config, extractor_settings={'temperature': 1.0, 'max_tokens': 32})
    matched_backend = Recording()
    matched_body = manifest(profile, matched_config, [], matched_backend, kind='build', profile_hash=None, items_hash=None,
                            method_id='audit-settings', extractor=backend_identity(matched_backend),
                            code_sha=matched_config['code_sha'], option_order_schedule=[], documents_hash=digest(case.docs))
    matched = invoke('control_build_matched_settings', matched_body, None, matched_config, None, matched_backend,
                     documents=case.docs, extractor=matched_backend)
    actual = traces('control_build_matched_settings', matched_body)[0]['settings']
    assert matched['status'] == 'complete' and len(matched_backend.prompts) == 1
    assert actual == matched['profile']['extractor_settings'] == matched_config['extractor_settings']
    record('control_build_matched_settings', 'verified', 'the same builder completes when declared settings match its actual request',
           {'result_status': matched['status'], 'profile_settings': matched['profile']['extractor_settings'],
            'actual_trace_settings': actual, 'backend_calls': len(matched_backend.prompts)})
    record('build_settings_binding', 'verified', 'divergent settings are rejected before backend dispatch, with a matched successful control',
           {'result_status': result['status'], 'error_code': result['error_code'],
            'declared_settings': config['extractor_settings'], 'requested_settings': {'temperature': 1.0, 'max_tokens': 32},
            'backend_calls': len(backend.prompts), 'attempted_calls': result['usage']['attempted_calls'],
            'matched_control_status': matched['status']})

    # Verify actual immutable fixture v2's linked lease, manifest, trace, and cache evidence.
    fixture_root = source / 'docs/overnight/gio-profile-20261115/infrastructure/runner-fixture-v2'
    result_path = next((fixture_root / 'outputs').glob('*/result.json'))
    fixed_result = json.loads(result_path.read_text())
    fixed_manifest = json.loads(result_path.with_name('manifest.json').read_text())
    fixed_lease = json.loads((fixture_root / 'leases' / (fixed_manifest['job_id'] + '.json')).read_text())
    trace_files = sorted(result_path.parent.joinpath('traces').glob('*.json'))
    cache_files = list((fixture_root / 'cache').glob('*.json'))
    checks = {'semantic_job_id': runner.job_id(fixed_manifest) == fixed_manifest['job_id'],
              'manifest_hash': digest(fixed_manifest) == fixed_result['manifest_hash'],
              'lease_manifest': fixed_lease['manifest'] == fixed_manifest,
              'all_trace_hashes': sorted(sha(path) for path in trace_files) == sorted(fixed_result['trace_hashes']),
              'cache_response_hashes': all(json.loads(path.read_text())['response_sha256'] == sha256_text(json.loads(path.read_text())['response']) for path in cache_files),
              'cache_keys_match_filenames': all(json.loads(path.read_text())['cache_key'] == path.stem for path in cache_files)}
    assert all(checks.values())
    record('control_actual_fixture_v2', 'verified', 'actual committed fixture evidence links consistently', checks)
    assert all(sha(source / row['path']) == row['expected'] for row in checked), 'Source changed during audit'
    report = {'source_commit': pin['source_commit'], 'implementation_commit': pin['implementation_commit'],
              'owner_tests_exit_code': tests.returncode, 'cases': results,
              'source_hashes_verified_before_and_after': len(checked),
              'unverified': ['New API/shared-ledger adapter is present and separately audited; no transport or ledger assessment in this lane.',
                             'Retrieval decision binding is separately tested by root; no conclusion from these probes.',
                             'Evaluator confirmation/final-use authority is outside this retest; no final inputs or execution.',
                             'Real backend timeout/cost behavior and power-loss durability were not exercised.'],
              'no_live_calls': True, 'no_real_sources_or_labels': True, 'no_owner_code_changes': True}
    dump(out / 'report.json', report)
    dump(out / 'command.json', {'argv': [sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]],
                               'exit_code': 0, 'reproducer_sha256': sha(__file__)})
    stdout = json.dumps({'source_commit': pin['source_commit'], 'owner_tests_exit_code': tests.returncode,
                         'verified': [r['case'] for r in results if r['status'] == 'verified'],
                         'fixed': [r['case'] for r in results if r.get('comparison', {}).get('change') == 'fixed'],
                         'still_fixed': [r['case'] for r in results if r.get('comparison', {}).get('change') == 'still_fixed'],
                         'remaining': [r['case'] for r in results if r.get('comparison', {}).get('change') == 'remaining'],
                         'unverified': report['unverified']}, indent=2) + '\n'
    (out / 'stdout.txt').write_text(stdout)
    (out / 'stderr.txt').write_text('')
    print(stdout, end='')


if __name__ == '__main__':
    main()
