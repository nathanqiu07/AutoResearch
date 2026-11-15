"""Bind completed zero-call packing outputs; no admission or provider calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUNTIME_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
READY = {'path': '/private/tmp/gio-profile-20261115-scaling-zero-packing-continuation2-v1/ready-index.json',
         'sha256': 'd28d4f3ebd9268b8895e7265c26a976d6bbbb19a4e4e40a113f421a5a2ea2feb'}
SUMMARY = {'path': '/private/tmp/gio-profile-20261115-coordinator/receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/execution/summary.json',
           'sha256': '37986983154cbb308afa7d8d1fd874038932edf003bcab76aa15d00677b6f352'}
HELPER_SHA = '740f4517d67379af5bc75d772495114599c58dc83424e4c164b0605ec2b9dcad'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runtime_root = Path(sys.argv[1]).resolve()
    assert subprocess.check_output(['git', '-C', str(runtime_root), 'rev-parse', 'HEAD'], text=True).strip() == RUNTIME_SHA
    assert not subprocess.check_output(['git', '-C', str(runtime_root), 'status', '--porcelain'], text=True).strip()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime_root))
    from autoresearch.taste.overnight import backends
    from autoresearch.taste.overnight.contracts import ProfileArtifact, backend_identity, canonical_json, digest
    from autoresearch.taste.overnight.runner import job_id
    helper_path = HERE / 'selected_scaling_bindings_v1.py'
    assert sha(helper_path) == HELPER_SHA
    helper = load('completed_packing_leaf_helper', helper_path)
    driver_path = runtime_root / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
    driver = load('completed_packing_frozen_driver', driver_path)
    used = {}

    def approved(ref):
        helper._reference(ref)
        data = Path(ref['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == ref['sha256'], 'input file hash changed'
        used[ref['path']] = ref['sha256']
        return json.loads(data)

    ready, summary = approved(READY), approved(SUMMARY)
    assert ready['runtime_sha'] == RUNTIME_SHA and ready['jobs'] == 112
    assert ready['api_calls_ceiling'] == ready['new_embedding_calls'] == 0
    assert summary['batch_id'] == ready['batch']['sha256'] and summary['status'] == 'complete'
    assert summary['counts'] == {'complete': 112, 'dispatched': 112, 'listed': 112, 'not_dispatched': 0, 'other': 0}
    # ready-index is the historical pre-execution receipt; terminal summary above
    # is the completion evidence. Do not reinterpret its old state as execution.
    prepared, proof, prior = approved(ready['prepared']), approved(ready['proof']), approved(ready['readiness'])
    selection = approved(prior['selection'])
    assert prepared['batch_id'] == summary['batch_id'] and prepared['code_sha'] == RUNTIME_SHA
    assert ready['prepared']['sha256'] == '337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'
    assert proof['readiness'] == ready['readiness'] and proof['selected_jobs'] == len(proof['jobs']) == 112
    assert proof['effective_max_api_calls'] == 0 and proof['all_original_leases_remain_null'] is True
    runtime = prior['runtime']
    assert sha(driver_path) == runtime['driver_sha256']
    assert sha(runtime_root / 'autoresearch/taste/overnight/backends.py') == runtime['backend_sha256']
    original_drafts = {r['packet']['sha256']: r for r in prior['drafts']}
    pending = {r['build_draft']['sha256']: r for r in prior['pending_dependencies']
               if r['status'] == 'deterministic-control-packing-pending'}
    assert len(pending) == 112
    prepared_refs = {r['sha256']: r for r in prepared['jobs']}
    assert len(prepared_refs) == 112
    private = Path(tempfile.mkdtemp(prefix='mechanical-ready-completed-packing-v1-', dir='/private/tmp/gio-profile-20261115-scaling'))

    def save(name, body):
        data = (canonical_json(body) + '\n').encode()
        path = private / name
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o600)
        return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}

    records, seen_jobs, seen_cells, checks = [], set(), set(), 0
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)

    with tempfile.TemporaryDirectory(prefix='isolated-test-ledger-', dir=private) as temporary:
        ledger = backends.DollarLedger(Path(temporary) / 'ledger.sqlite', max_usd=500, deadline='2099-01-01T00:00:00Z')
        with patch('urllib.request.urlopen', side_effect=AssertionError('no HTTP in binding')) as http, \
             patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('no completion in binding')) as complete:
            for admitted in proof['jobs']:
                old_ref, new_ref = admitted['original_draft'], admitted['prepared_packet']
                assert old_ref['sha256'] in pending and original_drafts[old_ref['sha256']]['packet'] == old_ref
                assert new_ref == prepared_refs[new_ref['sha256']]
                old, actual = approved(old_ref), approved(new_ref)
                original_record, dependency = original_drafts[old_ref['sha256']], pending[old_ref['sha256']]
                assert old['lease'] is None and old['manifest']['allocation']['authorization_source'] is None
                assert digest(old['manifest']) == admitted['original_unleased_manifest_sha256']
                assert old['backend']['max_calls'] == actual['backend']['max_calls'] == admitted['max_calls'] == 0
                assert old['config']['method_id'] in ('lexical_retrieval', 'semantic_retrieval')
                assert actual['manifest']['kind'] == 'build' and actual['manifest']['profile_hash'] is None
                assert actual['manifest']['job_id'] == admitted['job_id'] == job_id(actual['manifest'])
                assert admitted['job_id'] not in seen_jobs
                seen_jobs.add(admitted['job_id'])
                # Admission changes authority/job ID and copied release path only;
                # preserve the original scientific draft exactly.
                assert digest({k: v for k, v in actual.items() if k not in ('lease', 'manifest', 'release')}) == digest({k: v for k, v in old.items() if k not in ('lease', 'manifest', 'release')})
                assert actual['release']['sha256'] == old['release']['sha256'] == admitted['release']['sha256']
                stripped = copy.deepcopy(actual['manifest'])
                stripped.pop('job_id')
                stripped['allocation']['authorization_source'] = None
                assert digest(stripped) == digest(old['manifest'])
                assert admitted['config_sha256'] == actual['manifest']['config_hash'] == digest(actual['config'])
                receipt_path = Path(summary['receipts_root']) / admitted['job_id'] / 'receipt.json'
                receipt_ref = {'path': str(receipt_path), 'sha256': sha(receipt_path)}
                receipt = approved(receipt_ref)
                assert receipt['job_id'] == admitted['job_id'] and receipt['status'] == 'complete'
                assert receipt['manifest_sha256'] == digest(actual['manifest']) and receipt['usage']['attempted_calls'] == 0
                profile_path = Path(receipt['result_path']).parent / 'profile.json'
                profile_ref = {'path': str(profile_path), 'sha256': sha(profile_path)}
                profile = ProfileArtifact.from_dict(approved(profile_ref)).to_dict()
                release = approved(actual['release'])
                assert profile['status'] == 'complete' and digest(profile['config']) == digest(actual['config'])
                assert profile['config_id'] == actual['manifest']['config_hash'] and profile['code_sha'] == RUNTIME_SHA
                assert profile['documents_hash'] == admitted['documents_sha256'] == actual['manifest']['documents_hash']
                assert profile['allowed_source_manifest_hash'] == admitted['source_manifest_sha256']
                assert len(actual['item_ids']) == 1
                driver._register(actual['registration'], profile['method_id'])
                model = actual['backend']['model']
                assert model in ('gpt-6-sol', 'gpt-6-astra') and model == dependency['consumer']
                identity = backend_identity(backends.OpenAIResponsesBackend(model=model, reasoning='medium', ledger=ledger, max_usd=10, timeout=60))
                assert identity == profile['config']['consumer_identity'] == actual['manifest']['extractor']
                key = (profile['method_id'], profile['researcher_id'], actual['item_ids'][0], model)
                assert key not in seen_cells
                seen_cells.add(key)
                settings = {k: selection['consumer_settings'][k] for k in ('temperature', 'max_tokens')}
                draft = helper.prediction_packet(profile, release, profile_ref=profile_ref, release_ref=actual['release'],
                    origin_job_id=admitted['job_id'], identity=identity, settings=settings,
                    timeout=selection['consumer_settings']['timeout'], logical_cap=selection['common_personalization_cap'],
                    runtime=runtime, contract_sha256=actual['manifest']['contract_sha256'], registration=actual['registration'],
                    selection_sha256=prior['selection']['sha256'], index_sha256=selection['original_complete_index']['sha256'],
                    selected_cell_id=dependency['cell'], studies=['A-control'], item_ids=actual['item_ids'])
                lineage = {'original_unleased_build_draft': old_ref, 'original_unleased_manifest_sha256': digest(old['manifest']),
                    'actual_build_packet': new_ref, 'actual_build_job_id': admitted['job_id'],
                    'actual_build_manifest_sha256': digest(actual['manifest']), 'actual_build_receipt': receipt_ref,
                    'completed_profile': profile_ref, 'profile_id': profile['profile_id'], 'packing_ready_index': READY,
                    'packing_terminal_summary': SUMMARY, 'resolved_dependency': dependency}
                draft['manifest']['scaling_completed_packing_lineage'] = lineage
                assert draft['manifest']['parent_job_ids'] == [admitted['job_id']]
                test_packet = copy.deepcopy(draft)
                test_packet['lease'] = {'lease_id': 'discarded-packing-bind-test', 'owner': 'readiness-only', 'expires_at': runtime['deadline']}
                test_packet['manifest']['allocation']['authorization_source'] = 'discarded-in-memory-test-only-no-execution-authority'
                batch = {'campaign_id': selection['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                    'release_schema_version': release['schema_version'], 'release_scope': release['scope'],
                    'contract': {'sha256': actual['manifest']['contract_sha256']}, 'ledger': {'max_usd': 500}}
                with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                    driver._prepare_packet(test_packet, batch, ledger)
                checks += 1
                packet_ref = save('prediction-draft-%03d.json' % len(records), draft)
                pin = draft['manifest']['scaling_payload_pins'][0]
                records.append({'status': 'unleased-ready-pending-coordinator-v3-admission', 'packet': packet_ref,
                    'draft_manifest_sha256': digest(draft['manifest']), 'method_id': profile['method_id'],
                    'researcher_id': profile['researcher_id'], 'item_id': pin['item_id'], 'option_order_id': pin['option_order_id'],
                    'model': model, 'consumer': identity, 'settings': settings, 'timeout': draft['backend']['timeout'],
                    'max_calls': 1, 'max_seconds': draft['backend']['max_seconds'], 'max_usd': draft['backend']['max_usd'],
                    'profile_id': profile['profile_id'], 'profile_sha256': profile_ref['sha256'], 'lineage': lineage,
                    'request_identity': pin, 'endpoint': identity['endpoint'], 'studies': ['A-control']})
            assert checks == len(seen_cells) == 112 and seen_jobs == {r['job_id'] for r in proof['jobs']}
            assert ledger.summary()['attempts'] == http.call_count == complete.call_count == 0
    # Stage B + all mandatory controls only. Existing historical aliases and ready
    # B/raw/empty packets retain their exact earlier file identities.
    stage_prior = [r for r in prior['drafts'] if r['kind'] == 'predict'
                   and (r['method_id'] in selection['controls'] or 'B' in r['studies'])]
    assert len(stage_prior) == 74 and sum(r['status'] == 'historical-execution-alias' for r in stage_prior) == 62
    for record in stage_prior:
        draft = approved(record['packet'])
        assert draft['lease'] is None and draft['manifest']['allocation']['authorization_source'] is None
    totals = {}
    for model in ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra'):
        new = [r for r in records if r['model'] == model]
        existing = [r for r in stage_prior if r['model'] == model and r['status'] == 'unleased-draft']
        retrieval = sum((Decimal(str(r['max_usd'])) for r in new), Decimal(0))
        other = sum((Decimal(str(r['max_usd_reservation'])) for r in existing), Decimal(0))
        totals[model] = {'new_retrieval_calls': len(new), 'existing_ready_B_raw_no_profile_calls': sum(r['max_calls'] for r in existing),
            'retrieval_max_usd': str(retrieval), 'B_raw_no_profile_max_usd': str(other), 'stage_max_usd': str(retrieval + other),
            'historical_alias_rows': sum(r['n_items'] for r in stage_prior if r['model'] == model and r['status'] == 'historical-execution-alias')}
    for path, expected in used.items():
        assert sha(path) == expected, 'input changed during binding'
    index = {'schema_version': 'scaling-completed-packing-prediction-ready-v1',
        'status': 'unleased-ready-pending-coordinator-v3-admission', 'runtime_sha': RUNTIME_SHA,
        'selection': prior['selection'], 'packing_ready_index': READY, 'packing_terminal_summary': SUMMARY,
        'packing_prepared': ready['prepared'], 'packing_admission_proof': ready['proof'], 'original_readiness': ready['readiness'],
        'helper_sha256': HELPER_SHA, 'recipe_sha256': sha(__file__), 'resolved_dependencies': 112, 'prediction_packets': records,
        'stage': {'name': 'first-B-plus-four-mandatory-controls', 'prior_packet_references': stage_prior,
            'new_retrieval_packet_count': 112, 'new_paid_call_ceiling': 280, 'historical_alias_rows': 140,
            'logical_ordered_rows': 420, 'D_extra_calls': 0, 'D_aliases': prior['diagnostic_aliases'], 'by_model': totals,
            'max_usd_sum': str(sum((Decimal(v['stage_max_usd']) for v in totals.values()), Decimal(0)))},
        'driver_preparation_checks': checks, 'api_calls': 0, 'completion_calls': 0, 'isolated_test_ledger_attempts': 0,
        'execution_authorized': False, 'all_drafts_unleased': True, 'original_inputs_unchanged': True,
        'admission': 'Owner01 reviewed v3 must compare BOTH unknown-request conventions for each actual request; no static all9 clearance claimed.',
        'limitations': ['No separate construction/source/parity audit; root/05 own that prior check. This binds exact completed artifacts and driver inputs.',
            'Actual new packing build IDs are prediction parents; original unleased draft lineage is retained separately.',
            'Only B and mandatory controls are staged. Future paid A/C extractions and their consumers remain separate later dependencies.',
            'All proposals require coordinator budget/holds/deadline/lease checks. No current ledger or provider health inference.',
            'Semantic option reversal can change retrieved context; pipeline sensitivity is not isolated consumer position sensitivity.',
            'Profile/source/decision bodies remain private. Endpoint and BODY/wire hashes are exposed for owner v3, without inventing normalized reference hashes.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(used.items())]}
    ref = save('prediction-ready-index.json', index)
    print(json.dumps({'ready_index': ref, 'new_prediction_packets': 112, 'driver_checks': checks,
        'stage_new_paid_call_ceiling': 280, 'stage_max_usd_sum': index['stage']['max_usd_sum'], 'by_model': totals,
        'api_calls': 0, 'execution_authorized': False}, sort_keys=True))


if __name__ == '__main__':
    main()
