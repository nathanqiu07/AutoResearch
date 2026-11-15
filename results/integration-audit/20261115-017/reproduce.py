"""Pinned pilot driver/source review with invented releases and fake HTTP only.

Never invokes the CLI/live entrypoint, real credentials, referenced private
release paths, or evaluator labels. Fresh output directory required.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.source_root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pin = json.loads((root / 'AUDIT_SOURCE.json').read_text())
    assert all(sha(root / path) == value for path, value in pin['files'].items())
    # Use no ambient secrets, and fail closed if any test attempts an actual socket.
    os.environ.clear()
    os.environ.update(PATH=os.defpath, PYTHONDONTWRITEBYTECODE='1', OPENAI_API_KEY='synthetic-audit-key')
    def no_network(*args, **kwargs):
        raise AssertionError('Real network is forbidden in this synthetic audit')
    sys.path.insert(0, str(root))
    control = root / 'docs/overnight/gio-profile-20261115/control'
    tests = load_module('pilot_driver_tests', control / 'test_run_batch.py')
    excluded = 'test_git_sha_dirty_files_and_outputs_in_git_rejected'
    names = [name for name in unittest.defaultTestLoader.getTestCaseNames(tests.DriverTests) if name != excluded]
    stream = io.StringIO()
    with patch.object(socket.socket, 'connect', no_network), patch('socket.create_connection', no_network):
        run = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(tests.DriverTests(name) for name in names))
    (out / 'owner-tests-output.txt').write_text(stream.getvalue())
    dump(out / 'owner-tests-command.json', {'argv': [sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]],
         'selected_tests': names, 'exit_code': 0 if run.wasSuccessful() else 1,
         'excluded': {excluded: 'Selective git archive has no .git directory; this combined test assumes its own source root is a worktree.'}})
    assert run.wasSuccessful(), 'Targeted driver tests failed; inspect output'
    driver = load_module('pilot_route_driver', control / 'run_batch.py')
    from autoresearch.taste.overnight import runner, backends
    from autoresearch.taste.overnight.evaluation import review_document
    from autoresearch.taste.overnight.contracts import canonical_json, digest, backend_identity, source_manifest, sha256_bytes

    selection = json.loads((control / 'pilot-selection-v1.json').read_text())
    policy = json.loads((control / 'RUN_POLICY.json').read_text())
    methods = selection['methods']
    assert methods == ['no_profile', 'name_only', 'raw_evidence', 'lexical_retrieval', 'P1']
    selection_check = {'methods': methods, 'researchers': len(selection['selection']),
                       'ordered_inputs': sum(row['ordered_items'] for row in selection['selection']),
                       'declared_semantic_pairs': sum(row['semantic_pairs'] for row in selection['selection']),
                       'ordered_id_lists_unique': all(len({x['item_id'] for x in row['selected_items']}) == row['ordered_items'] for row in selection['selection']),
                       'order_label_counts': [dict(Counter(x['option_order_id'] for x in row['selected_items'])) for row in selection['selection']],
                       'receipt_and_bundle_verification': 'unverified; private referenced paths never opened'}
    selection_check['expected_predictions'] = selection_check['ordered_inputs'] * len(methods)
    selection_check['expected_extractions'] = len(selection['selection'])
    selection_check['expected_calls'] = selection_check['expected_predictions'] + selection_check['expected_extractions']
    assert selection_check['expected_calls'] == policy['budget_policy']['pilot_unchanged']['planned_calls'] == 42
    dump(out / 'selection-check.json', selection_check)

    def ref(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(value) + '\n')
        return {'path': str(path), 'sha256': sha(path)}

    call_log, current = [], {'phase': 'valid', 'method': None, 'researcher': None}
    invalid_extraction = [False]
    class Response:
        status = 200
        def __init__(self, text): self.text = text
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size):
            return json.dumps({'status': 'completed', 'usage': {'input_tokens': 5, 'output_tokens': 5},
                'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                            'content': [{'type': 'output_text', 'text': self.text}]}]}).encode()
    def fake_http(request, **kwargs):
        body = json.loads(request.data)
        payload = json.loads(body['input'].split('INPUT_JSON:\n', 1)[1])
        extraction = 'documents' in payload
        call_log.append({'phase': current['phase'], 'method': current['method'], 'researcher': current['researcher'],
                         'kind': 'extraction' if extraction else 'prediction', 'request': body, 'payload': payload})
        if extraction:
            doc = payload['documents'][0]
            span = doc['segments'][0]
            statement = {'text': 'Prefer controlled tests.', 'kind': 'preference', 'evidence_status': 'explicit',
                         'conditions': None, 'date': None,
                         'sources': [{'document_id': doc['document_id'], 'start': span['start'], 'end': span['end'],
                                      'quote': 'INVALID QUOTE' if invalid_extraction[0] else span['content']}]}
            return Response(canonical_json({'summary': [statement]}))
        return Response('{"probabilities":[0.6,0.4],"rationale":"Synthetic routing fixture"}')

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', no_network))
        stack.enter_context(patch('socket.create_connection', no_network))
        stack.enter_context(patch('urllib.request.urlopen', side_effect=fake_http))
        for module in (driver, runner, backends):
            stack.enter_context(patch.object(module, 'datetime', Clock))
        # The selective archive has no .git; source identity is independently hash-verified.
        stack.enter_context(patch.object(driver, 'verify_runtime'))
        batch = {'campaign_id': 'gio-profile-20261115', 'code_sha': pin['source_commit'],
                 'deadline': driver.HARD_DEADLINE, 'release_schema_version': driver.RELEASE_SCHEMA,
                 'release_scope': driver.RELEASE_SCOPE, 'contract': {'sha256': 'a' * 64},
                 'env_file': str(out / 'unused-synthetic-credentials-path'),
                 'runtime_root': str(root), 'ledger': {'max_usd': 0.5}, 'max_workers': 2,
                 'roots': {name: str(out / 'valid-run' / name) for name in ('output', 'lease', 'cache', 'receipts')}}
        ledger = backends.DollarLedger(out / 'valid-run' / 'ledger.sqlite', max_usd=0.5,
                                       deadline=driver.HARD_DEADLINE, max_inflight=2)
        prepared = {'batch': batch, 'ledger': ledger}
        routes, invalid_jobs, invalid_profiles = [], [], []
        all_releases = []

        def packet(release_ref, researcher, docs, items, method, *, profile=None, decision=None, invalid=False):
            spec = {'model': selection['model'], 'reasoning': selection['reasoning'], 'timeout': 60,
                    'max_calls': (1 if method == 'P1' else 0) if profile is None else len(items),
                    'max_seconds': 300, 'max_usd': 0.5}
            identity = backend_identity(driver._backend(spec, ledger))
            if profile is None:
                config = {'method_id': method, 'researcher_id': researcher, 'allowed_sources': source_manifest(docs),
                          'allowed_source_manifest_hash': digest(source_manifest(docs)), 'personalization_cap': 2048,
                          'replicate_id': 0, 'code_sha': pin['source_commit'], 'extractor_settings': selection['extraction_settings'],
                          'evidence_policy': 'explicit-only'}
                if method == 'name_only': config['researcher_name'] = researcher
                if method == 'lexical_retrieval': config.update(decision=decision, consumer_identity=identity, top_k=1)
                if invalid: config['synthetic_invalid_probe'] = True
                profile_ref, kind = None, 'build'
            else:
                config = {'method_implementation_hash': profile['method_implementation_hash'],
                          'renderer_implementation_hash': profile['renderer_implementation_hash'],
                          'profile_prompt_version': profile['prompt_version'], 'consumer_prompt_version': 'neutral-choice-v1',
                          'settings': selection['consumer_settings']}
                profile_ref = ref(out / 'profile-inputs' / (profile['profile_id'] + '.json'), profile)
                kind = 'predict'
            allocation = {'authorization_source': 'synthetic fixture only', 'cost_mode': 'priced_api',
                          **{key: spec[key] for key in ('max_calls', 'max_seconds', 'max_usd')}}
            manifest = {'schema_version': 'overnight-job-v1', 'campaign_id': batch['campaign_id'],
                        'stage': 'dev', 'kind': kind, 'method_id': method, 'personalization_cap': 2048,
                        'replicate_id': 0, 'consumer': None if kind == 'build' else identity,
                        'allocation': allocation, 'retry_policy': {'max_attempts': 1, 'retry_uncertain': False},
                        'parent_job_ids': [], 'expected_outputs': ['result.json', 'traces']}
            return {'schema_version': 'overnight-packet-v1', 'release': release_ref,
                    'item_ids': [item['item_id'] for item in items], 'profile': profile_ref,
                    'config': config, 'manifest': manifest, 'backend': spec,
                    'registration': {'module': 'autoresearch.taste.overnight.' + ('profiles_summary' if method == 'P1' else 'baselines'),
                                     'function': 'register_summary_builders' if method == 'P1' else 'register_baselines'},
                    'lease': {'lease_id': 'synthetic', 'owner': 'synthetic-audit', 'expires_at': driver.HARD_DEADLINE}}

        def perform(p):
            job = driver._prepare_packet(p, batch, ledger)
            result = driver._execute_one(job, prepared)
            assert result['status'] == 'complete', result
            return result, job

        for researcher in ('synthetic-researcher-a', 'synthetic-researcher-b'):
            docs = []
            for token, allowed in (('alpha', 'Alpha controlled experiments are preferable to guesswork.'),
                                   ('beta', 'Beta replication should happen before expansion.')):
                content = allowed + '\nOUTSIDE_PERMITTED_SENTINEL_' + token.upper()
                docs.append({'document_id': researcher + '-' + token, 'researcher_id': researcher,
                             'content': content, 'content_sha256': sha256_bytes(content.encode()),
                             'permitted_spans': [{'start': 0, 'end': len(allowed), 'text': allowed, 'speaker': researcher}],
                             'canonical_url': 'https://example.invalid/synthetic/' + token,
                             'version_evidence': {'basis': 'invented frozen fixture'}, 'author': researcher,
                             'contribution': 'Attributed passage within synthetic surrounding context',
                             'fetch_status': 'complete',
                             'source_review': {'disposition': 'approved_atemporal', 'reviewer': 'synthetic-evaluator',
                                               'grouping_reviewed': True, 'attribution_basis': 'invented first-span attribution'}})
            assert all(review_document(doc)['status'] == 'eligible' for doc in docs)
            items = []
            for pair, (context, options) in enumerate((('Choose an alpha controlled experiment.', ['Alpha test', 'Guesswork']),
                                                       ('Choose a beta replication plan.', ['Beta replication', 'Expansion']))):
                for order in (0, 1):
                    items.append({'item_id': '%s-p%s-o%s' % (researcher, pair, order), 'researcher_id': researcher,
                                  'context': context, 'options': options if order == 0 else list(reversed(options)),
                                  'option_order_id': 'paired-order-' + str(order)})
            release = {'schema_version': driver.RELEASE_SCHEMA, 'scope': driver.RELEASE_SCOPE, 'researcher_id': researcher,
                       'sources': {'documents': docs, 'source_manifest': source_manifest(docs),
                                   'allowed_source_manifest_hash': digest(source_manifest(docs))},
                       'items': items, 'items_sha256': digest(items)}
            release_ref = ref(out / 'synthetic-releases' / (researcher + '.json'), release)
            all_releases.append((researcher, docs, items, release_ref))
            for method in methods:
                current.update(phase='valid', method=method, researcher=researcher)
                schedules = []
                groups = [[item] for item in items] if method == 'lexical_retrieval' else [items]
                for group in groups:
                    decision = {key: group[0][key] for key in ('context', 'options')} if method == 'lexical_retrieval' else None
                    build, built_job = perform(packet(release_ref, researcher, docs,
                                                      group if decision else [], method, decision=decision))
                    prediction, predicted_job = perform(packet(release_ref, researcher, docs, group, method, profile=build['profile']))
                    schedules.extend(row['item_id'] for row in prediction['predictions'])
                    routes.append({'researcher': researcher, 'method': method, 'build_job_id': build['job_id'],
                                   'predict_job_id': prediction['job_id'], 'profile': build['profile'],
                                   'items': group, 'build_calls': build['usage']['attempted_calls'],
                                   'prediction_calls': prediction['usage']['attempted_calls'],
                                   'source_hash': predicted_job['manifest']['source_manifest_hash'],
                                   'documents_hash': predicted_job['manifest']['documents_hash']})
                assert schedules == [item['item_id'] for item in items]

        valid_calls = list(call_log)
        assert len(valid_calls) == 42
        assert Counter(row['kind'] for row in valid_calls) == {'prediction': 40, 'extraction': 2}
        prediction_calls = [row for row in valid_calls if row['kind'] == 'prediction']
        conditions = {}
        for method in methods:
            subset = [row for row in prediction_calls if row['method'] == method]
            personalization = [row['payload']['personalization'] for row in subset]
            assert len(subset) == 8
            conditions[method] = {'prediction_calls': len(subset),
                                  'empty_personalizations': sum(value == '' for value in personalization),
                                  'outside_permitted_marker_count': sum('OUTSIDE_PERMITTED_SENTINEL' in value for value in personalization),
                                  'personalization_sha256': [sha256_bytes(value.encode()) for value in personalization]}
        assert conditions['no_profile']['empty_personalizations'] == 8
        assert all(json.loads(row['payload']['personalization']) == {'name': row['researcher']}
                   for row in prediction_calls if row['method'] == 'name_only')
        assert conditions['raw_evidence']['outside_permitted_marker_count'] == 8
        assert conditions['lexical_retrieval']['outside_permitted_marker_count'] == 8
        assert conditions['P1']['outside_permitted_marker_count'] == 0
        assert all('OUTSIDE_PERMITTED_SENTINEL' not in row['request']['input'] for row in valid_calls if row['kind'] == 'extraction')
        assert len({row['request']['instructions'] for row in prediction_calls}) == 1
        assert all(row['request']['max_output_tokens'] == 8192 and row['request']['model'] == 'gpt-6-luna'
                   and row['request']['reasoning'] == {'effort': 'medium'} for row in prediction_calls)

        # Match the restricted-span case to explicit whole-document and no-span-default variants.
        researcher, original_docs, source_items, _ = all_releases[0]
        variant_controls = []
        for variant in ('full-document', 'default-no-span'):
            docs = json.loads(json.dumps(original_docs))
            for doc in docs:
                if variant == 'full-document':
                    doc['permitted_spans'] = [{'start': 0, 'end': len(doc['content']),
                                               'text': doc['content'], 'speaker': researcher}]
                else:
                    del doc['permitted_spans']
            release = {'schema_version': driver.RELEASE_SCHEMA, 'scope': driver.RELEASE_SCOPE, 'researcher_id': researcher,
                       'sources': {'documents': docs, 'source_manifest': source_manifest(docs),
                                   'allowed_source_manifest_hash': digest(source_manifest(docs))},
                       'items': source_items, 'items_sha256': digest(source_items)}
            release_ref = ref(out / 'synthetic-releases' / (variant + '.json'), release)
            for method in methods:
                current.update(phase='span-control-' + variant, method=method, researcher=researcher)
                one_item = [source_items[0]]
                decision = {key: one_item[0][key] for key in ('context', 'options')} if method == 'lexical_retrieval' else None
                built, _ = perform(packet(release_ref, researcher, docs, one_item if decision else [], method, decision=decision))
                predicted, _ = perform(packet(release_ref, researcher, docs, one_item, method, profile=built['profile']))
                baseline = next(row for row in routes if row['researcher'] == researcher and row['method'] == method)
                content_equal = built['profile']['content'] == baseline['profile']['content']
                if method in ('no_profile', 'name_only', 'raw_evidence', 'lexical_retrieval'):
                    assert content_equal
                else:
                    assert not content_equal
                    assert 'OUTSIDE_PERMITTED_SENTINEL' in canonical_json(built['profile']['content'])
                variant_controls.append({'variant': variant, 'method': method, 'build_status': built['status'],
                                         'prediction_status': predicted['status'], 'content_equals_restricted': content_equal,
                                         'document_review_statuses': [review_document(doc)['status'] for doc in docs],
                                         'note': 'No-span default is a fallback/schema probe; evaluator review correctly quarantines it.' if variant == 'default-no-span' else 'Whole-document attributed-span control.'})
        dump(out / 'span-variant-controls.json', variant_controls)

        # Invalid P1s remain invalid; batch completion means only all submitted jobs finished.
        invalid_extraction[0] = True
        current.update(phase='invalid-P1', method='P1', researcher='synthetic')
        for researcher, docs, items, release_ref in all_releases:
            invalid_jobs.append(driver._prepare_packet(packet(release_ref, researcher, docs, [], 'P1', invalid=True), batch, ledger))
        invalid_prepared = {'batch': batch, 'ledger': ledger, 'jobs': invalid_jobs,
                            'batch_id': digest({'purpose': 'synthetic-invalid-P1'}), 'batch_sha256': 'b' * 64}
        with patch.object(driver, 'read_credentials', return_value={'OPENAI_API_KEY': 'synthetic-audit-key'}):
            summary = driver.execute_batch(invalid_prepared)
        assert summary['status'] == 'complete' and summary['counts']['complete'] == 0 and summary['counts']['other'] == 2
        receipts = []
        prediction_rejections = []
        for job, (researcher, docs, items, release_ref) in zip(invalid_jobs, all_releases):
            where = Path(batch['roots']['output']) / job['manifest']['job_id']
            failed = json.loads((where / 'result.json').read_text())
            profile = json.loads((where / 'profile.json').read_text())
            assert failed['status'] == profile['status'] == 'invalid' and profile['error_code'] == 'invalid_source_span'
            receipt_path = Path(summary['receipts_root']) / job['manifest']['job_id'] / 'receipt.json'
            receipt = json.loads(receipt_path.read_text()); receipts.append(receipt)
            assert receipt['status'] == 'invalid'
            before = len(call_log)
            try:
                driver._prepare_packet(packet(release_ref, researcher, docs, items, 'P1', profile=profile), batch, ledger)
                raise AssertionError('Invalid profile was accepted for prediction')
            except ValueError as exc:
                prediction_rejections.append({'status': getattr(exc, 'status', None), 'code': getattr(exc, 'code', None)})
            assert len(call_log) == before
        dump(out / 'invalid-P1-accounting.json', {'batch_summary': summary, 'receipts': receipts,
             'prediction_preparation_rejections': prediction_rejections,
             'unsubmitted_expected_prediction_rows': 8,
             'interpretation': 'Generic batch complete means submitted jobs finished; experiment/report layer must show the eight absent P1 predictions. This alone is not a driver defect.'})

    assert all(sha(root / path) == value for path, value in pin['files'].items())
    dump(out / 'synthetic-call-bodies.json', call_log)
    dump(out / 'conditioning.json', conditions)
    dump(out / 'synthetic-routes.json', routes)
    report = {'source_commit': pin['source_commit'], 'source_files_verified_before_and_after': len(pin['files']),
              'common_runtime_matches_7bb1589': all(row['matches'] for row in pin['runtime_comparison']),
              'common_runtime_files': len(pin['runtime_comparison']), 'targeted_owner_tests': run.testsRun,
              'owner_test_failures': len(run.failures) + len(run.errors), 'excluded_owner_test': excluded,
              'selection_expectation': selection_check, 'valid_synthetic_prediction_calls': 40,
              'valid_synthetic_extraction_calls': 2, 'invalid_P1_extraction_calls': 2,
              'additional_span_variant_controls': len(variant_controls),
              'paired_schedule_all_methods': 'verified on synthetic fixture; actual released schedule unverified',
              'conditioning_gap': 'Raw/lexical include full approved document text while P1 restricts to attributed permitted_spans; matched full/default controls confirm the difference.',
              'gap_interpretation': 'Conditional evidence/attribution-policy discrepancy, not a proven authorization violation or proof of actual pilot leakage. Source approval covers full document records; generic driver is not a span restriction enforcer.',
              'invalid_P1_handling': 'invalid preserved in profile/result/receipt; prediction preparation rejects it',
              'actual_released_packets_receipts': 'not received or read; owner-reported live outcome remains unverified',
              'network': 'all HTTP responses synthetic; socket connections forbidden', 'credentials': 'synthetic only; ambient environment cleared'}
    dump(out / 'report.json', report)
    dump(out / 'command.json', {'argv': [sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]],
                               'exit_code': 0, 'reproducer_sha256': sha(__file__)})
    stdout = json.dumps({key: value for key, value in report.items() if key != 'selection_expectation'}, indent=2) + '\n'
    (out / 'stdout.txt').write_text(stdout); (out / 'stderr.txt').write_text('')
    print(stdout, end='')


if __name__ == '__main__':
    main()
