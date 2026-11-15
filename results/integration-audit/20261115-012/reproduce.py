"""Synthetic method-ID decision binding through the actual shared run_job route.

This tests dispatch enforcement, not actual role05 retrieval selection or an
integrated live candidate. It constructs no external backend.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, body):
    with Path(path).open('x') as handle:
        json.dump(body, handle, indent=2, allow_nan=False)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source_root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    pin = json.loads((source / 'AUDIT_SOURCE.json').read_text())
    assert all(sha(source / name) == value for name, value in pin['files'].items())
    from tests import test_overnight_contracts as fixture
    from autoresearch.taste.overnight import runner, registry, contracts
    for module in (fixture, runner, registry, contracts):
        Path(module.__file__).resolve().relative_to(source)
    case = fixture.ContractTests()
    case.setUp()
    decision = {'context': 'SYNTHETIC retrieval decision', 'options': ['SYNTHETIC A', 'SYNTHETIC B']}
    cases = []
    for method in ('lexical_retrieval', 'profile_retrieval', 'semantic_retrieval'):
        registry.register_builder(method, fixture.fixture_builder, prompt_version='synthetic-route-v1', prompt_sha256='a' * 64)
        profile = case.build(method_id=method, decision=decision, code_sha=pin['source_commit'])
        config = case.prediction_config(profile)
        variants = {'exact': decision, 'changed_context': dict(decision, context=decision['context'] + ' CHANGED'),
                    'reversed_options': dict(decision, options=list(reversed(decision['options'])))}
        for variant, current in variants.items():
            backend = fixture.RecordingConsumer()
            item = dict(current, item_id='synthetic-item', researcher_id=profile.researcher_id,
                        option_order_id='ba' if variant == 'reversed_options' else 'ab')
            manifest = {'schema_version': 'overnight-job-v1', 'campaign_id': 'synthetic-route-audit',
                        'stage': 'offline', 'kind': 'predict', 'contract_sha256': 'c' * 64,
                        'config_hash': contracts.digest(config), 'source_manifest_hash': profile.allowed_source_manifest_hash,
                        'items_hash': contracts.digest([item]), 'profile_hash': profile.profile_id, 'method_id': method,
                        'extractor': profile.extractor, 'consumer': contracts.backend_identity(backend),
                        'personalization_cap': profile.personalization_cap,
                        'option_order_schedule': [{'item_id': item['item_id'], 'option_order_id': item['option_order_id']}],
                        'replicate_id': profile.replicate_id, 'code_sha': pin['source_commit'],
                        'allocation': {'max_calls': 1, 'max_seconds': 30, 'max_usd': 0, 'cost_mode': 'offline',
                                       'authorization_source': 'synthetic-audit-only'},
                        'retry_policy': {'max_attempts': 1, 'retry_uncertain': False},
                        'parent_job_ids': [], 'expected_outputs': ['result.json', 'traces']}
            manifest['job_id'] = runner.job_id(manifest)
            lease = {'job_id': manifest['job_id'], 'lease_id': 'synthetic-lease', 'owner': 'synthetic-audit',
                     'expires_at': '2099-01-01T00:00:00+00:00'}
            result = runner.run_job(manifest, lease, output_root=out / 'jobs', lease_root=out / 'leases',
                                    config=config, profile=profile, items=[item], consumer=backend)
            row = result['predictions'][0]
            expected = 'complete' if variant == 'exact' else 'unavailable'
            assert row['status'] == expected
            assert len(backend.prompts) == (1 if variant == 'exact' else 0)
            if variant != 'exact':
                assert row['error_code'] == 'retrieved_profile_decision_mismatch'
                assert result['usage']['attempted_calls'] == 0 and result['trace_hashes'] == []
            cases.append({'method': method, 'variant': variant, 'status': row['status'],
                          'error_code': row['error_code'], 'recording_calls': len(backend.prompts),
                          'job_id': manifest['job_id'], 'requests': backend.prompts})
    assert all(sha(source / name) == value for name, value in pin['files'].items())
    save(out / 'report.json', {'source_commit': pin['source_commit'], 'implementation_commit': pin['implementation_commit'],
          'source_pin_sha256': sha(source / 'AUDIT_SOURCE.json'), 'source_hashes': pin['files'],
          'probe_sha256': sha(__file__), 'argv': sys.argv, 'python': sys.version, 'real_model_calls': 0,
          'source_unchanged': True, 'verified_cases': len(cases), 'cases': cases,
          'scope': 'Actual run_job -> common prepare_payload/predict_profile; synthetic builders registered under the three retrieval IDs.',
          'limits': ['Does not rebuild actual role05 retrieval profiles or prove integrated candidate selection.',
                     'No real sources, final data, API calls, pricing, or preference evidence.',
                     'Other runner findings are tested separately and are not cleared by this route test.']})
    print(json.dumps({'verified_cases': len(cases), 'source_unchanged': True, 'real_model_calls': 0}))


if __name__ == '__main__':
    main()
