"""Join closed PRIMARY14 receipt metadata to frozen A/C coverage; no execution."""
import copy
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
import tempfile

BINDINGS = {'path': '/private/tmp/gio-profile-20261115-scaling/primary-ac-valid-descendants-v1-rf71pftd/primary-ac-ready-index.json', 'sha256': 'f394a9724c8da39b09fa57a1ac61dc76a9287da1748aeb7fdda9efb84934f2e6'}
TERMINAL = {'path': '/private/tmp/gio-profile-20261115-coordinator/p8-primary14-supervisor-v1/supervisor-terminal.json', 'sha256': '18d3377cf0023a99e5fa9bc8c6dc6fddcaa4d352dad7f7a6d49da02189ac5495'}
VERIFIED = {'path': '/private/tmp/gio-profile-20261115-coordinator/p8-primary14-supervisor-v1/verified.json', 'sha256': '8a3768e1f7ea55d3019670554b92dd9defe8a1bac6c707723710c32c7a0dabdb'}
BATCH_ID = '135214adef09e708204efd31f11977eb7f5877e8750aa52677d43e3933f3b6b4'
RUNTIME_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def reference(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    inputs = {}
    def read(ref):
        assert isinstance(ref, dict) and set(ref) == {'path', 'sha256'}
        path = Path(ref['path'])
        assert path.is_absolute() and path.suffix not in ('.sqlite', '.sqlite3', '.db')
        assert path.name not in ('result.json', 'profile.json', 'claim.json', '.env')
        assert 'lease' not in path.parts and 'native-claims' not in path.parts
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ref['sha256'], 'metadata reference hash changed'
        inputs[str(path)] = ref['sha256']
        return json.loads(raw)

    source, terminal, verified = read(BINDINGS), read(TERMINAL), read(VERIFIED)
    assert terminal['verified'] == VERIFIED and terminal['status'] == 'complete'
    assert terminal['child_process_terminal'] is True and terminal['native_accounting_drain_verified'] is True
    assert terminal['planned_jobs'] == 1 and terminal['planned_call_ceiling'] == 14
    assert terminal['planned_descendant_slots'] == 84 and terminal['unavailable_descendant_slots'] == 70
    ready = read(terminal['index'])
    assert ready['bindings'] == BINDINGS and ready['jobs'] == 1 and ready['max_calls'] == 14
    assert ready['baseline'] == terminal['baseline'] == verified['baseline'] == {'attempts': 284, 'spent': 3260300000}
    assert ready['unknown_denylist'] == source['typed_denylist_future_owner_admission']
    prepared, evidence = read(ready['prepared']), read(ready['evidence'])
    assert prepared['batch_id'] == BATCH_ID and prepared['code_sha'] == source['runtime_sha'] == RUNTIME_SHA
    assert prepared['admission_evidence'] == ready['evidence']
    assert len(prepared['jobs']) == len(source['ready_prediction_packets']) == 1
    assert evidence['scientific_fields_unchanged'] is True
    assert evidence['only_changed_fields'] == ['lease', 'manifest.job_id', 'manifest.allocation.authorization_source']
    record = source['ready_prediction_packets'][0]
    assert evidence['original_draft'] == record['packet']
    original, bound, actual = read(record['packet']), read(evidence['bound_packet']), read(prepared['jobs'][0])
    # Preparation may relocate references. Compare referenced bytes, then all
    # scientific manifest/config/backend/item fields. Never open the references.
    assert digest(actual['manifest']) == digest(bound['manifest'])
    for key in ('config', 'backend', 'item_ids', 'registration', 'schema_version'):
        assert digest(actual[key]) == digest(bound[key]) == digest(original[key]), key
    for key in ('profile', 'release'):
        assert actual[key]['sha256'] == bound[key]['sha256'] == original[key]['sha256'], key
    manifest = actual['manifest']
    assert manifest['job_id'] == evidence['job_id']
    stripped = copy.deepcopy(manifest)
    stripped.pop('job_id')
    stripped['allocation']['authorization_source'] = None
    assert digest(stripped) == digest(original['manifest']), 'admission changed scientific identity'
    assert manifest['code_sha'] == RUNTIME_SHA and manifest['kind'] == 'predict' and manifest['method_id'] == 'P8'
    assert manifest['consumer'] == record['effective_consumer'] and manifest['consumer']['model'] == 'gpt-6-sol'
    assert manifest['personalization_cap'] == manifest['scaling_logical_cap'] == 8192
    assert manifest['parent_job_ids'] == [record['actual_parent_job_id']]
    assert manifest['profile_hash'] == record['profile_id'] and actual['profile']['sha256'] == record['profile']['sha256']
    assert actual['config']['settings'] == record['settings'] == {'max_tokens': 8192, 'temperature': 0.0}
    assert actual['backend']['timeout'] == record['timeout'] == 60
    assert record['researcher_id'] == 'neel_nanda' and record['study'] == 'A'
    assert record['extractor'] == record['consumer'] == 'gpt-6-sol'
    assert len(verified['native']['receipts']) == 1
    receipt_refs = verified['native']['receipts'][0]
    receipt, summary = read(receipt_refs['receipt']), read(verified['native']['summary'])
    assert summary['batch_id'] == BATCH_ID and summary['status'] == 'complete'
    assert summary['counts'] == {'complete': 1, 'dispatched': 1, 'listed': 1, 'not_dispatched': 0, 'other': 0}
    assert receipt['job_id'] == manifest['job_id'] and receipt['manifest_sha256'] == digest(manifest)
    assert receipt['status'] == 'complete' and receipt['counts'] == {'attempted': 14, 'complete': 14, 'error': 0}
    assert receipt['result_path'] == receipt_refs['result']['path']
    usage = receipt['usage']
    assert usage['attempted_calls'] == 14 and usage['cache_hits'] == usage['uncertain_attempts'] == 0
    assert usage['budget_detail']['reported_usage_complete'] is True
    spend = Decimal(str(usage['reported_api_usd'])) * 1_000_000_000
    assert spend == spend.to_integral_value()
    spend = int(spend)
    assert spend == verified['native']['known_spent_nanos'] == 85065000
    assert verified['native']['attempted_calls'] == verified['diagnostics']['actual_open_events'] == 14
    assert verified['native']['ledger_attempts'] - terminal['baseline']['attempts'] == 14
    assert verified['native']['ledger_spent_nanos'] - terminal['baseline']['spent'] == spend
    requests, pins = evidence['requests'], manifest['scaling_payload_pins']
    assert pins == record['request_pins'] and len(requests) == len(pins) == 14
    assert [r['item_id'] for r in requests] == actual['item_ids']
    assert len({p['item_id'] for p in pins}) == 14
    rows = copy.deepcopy(source['new_descendant_coverage_rows'])
    assert len(rows) == 84 and len({r['coverage_row_id'] for r in rows}) == 84
    by_item = {r['item_id']: r for r in rows if r['status'] == 'unleased_ready'}
    assert len(by_item) == 14
    for request, pin in zip(requests, pins):
        row = by_item.pop(pin['item_id'])
        assert row['request_identity'] == pin and row['packet'] == record['packet']
        assert row['actual_parent_job_id'] == record['actual_parent_job_id']
        assert row['profile_id'] == record['profile_id'] and row['profile_reference'] == record['profile']
        assert row['item_sha256'] == request['item_sha256'] == pin['item_sha256']
        assert row['option_order_id'] == pin['option_order_id'] and request['item_id'] == pin['item_id']
        assert request['request_sha256'] == pin['wire_request_sha256']
        assert request['wire_bytes_sha256'] == pin['wire_bytes_sha256']
        assert request['input_token_upper_bound'] == pin['input_token_upper_bound']
        assert Decimal(str(request['max_usd_reservation'])) == Decimal(str(pin['max_usd_reservation']))
        row.update({'status': 'complete', 'prediction_attempted': True, 'prediction_outcome': 'complete',
            'original_draft_status': 'unleased_ready', 'actual_prediction_job_id': manifest['job_id'],
            'actual_prepared_packet': prepared['jobs'][0], 'completion_receipt': receipt_refs['receipt'],
            'result_reference_only_not_opened': receipt_refs['result'],
            'endpoint_body_sha256_owner_proof': request['endpoint_body_sha256'],
            'new_draw': True, 'cache_hit': False, 'cost_owner_job_id': manifest['job_id'],
            'cost_allocation': 'actual job cost counted once; no per-item cost split'})
    assert not by_item
    assert Counter(r['status'] for r in rows) == {'complete': 14, 'unavailable_invalid_parent': 70}
    for old, new in zip(source['new_descendant_coverage_rows'], rows):
        if old['status'] == 'unavailable_invalid_parent':
            assert old == new and new['prediction_attempted'] is False and new['prediction_outcome'] is None
    assert len(source['parents']) == 4 and Counter(p['parent_status'] for p in source['parents']) == {'complete': 1, 'invalid': 3}
    assert len(source['existing_completed_execution_aliases']) == 56
    assert len(source['C_large_large_aliases_of_A_rows']) == 28
    assert all(r['status'] == 'unavailable_invalid_parent' and r['additional_requests'] == 0 for r in source['C_large_large_aliases_of_A_rows'])
    views = {'A': [], 'C': []}
    for i, row in enumerate(rows):
        views[row['study']].append({'execution_slot_id': row['coverage_row_id'],
            'source_array': 'new_descendant_coverage_rows', 'source_index': i, 'status': row['status']})
    for i, alias in enumerate(source['existing_completed_execution_aliases']):
        slot = digest({k: alias[k] for k in ('historical_job_id', 'item_id', 'option_order_id')})
        assert alias['new_calls'] == alias['new_cost'] == 0
        for study in alias['studies']:
            views[study].append({'execution_slot_id': slot, 'source_array': 'existing_completed_execution_aliases',
                'source_index': i, 'status': alias['status']})
    by_coverage = {r['coverage_row_id']: r for r in rows}
    for i, alias in enumerate(source['C_large_large_aliases_of_A_rows']):
        row = by_coverage[alias['alias_of_A_row']]
        assert row['study'] == 'A' and alias['status'] == row['status']
        assert all(alias[k] == row[k] for k in ('researcher_id', 'item_id', 'consumer', 'extractor'))
        views['C'].append({'execution_slot_id': alias['alias_of_A_row'],
            'source_array': 'C_large_large_aliases_of_A_rows', 'source_index': i, 'status': alias['status']})
    slots_a = {r['execution_slot_id'] for r in views['A']}
    slots_c = {r['execution_slot_id'] for r in views['C']}
    assert len(views['A']) == len(slots_a) == 84 and len(views['C']) == len(slots_c) == 112
    assert len(slots_a & slots_c) == 56 and len(slots_a | slots_c) == 140
    for path, sha in inputs.items():
        assert reference(path)['sha256'] == sha, 'metadata changed during assembly'
    result = {'schema_version': 'primary14-completion-metadata-v1', 'status': 'completed-valid-descendant-with-invalid-coverage-retained-not-scored',
        'selection': source['selection'], 'source_bindings': BINDINGS,
        'actual_admission_index': terminal['index'], 'actual_prepared_batch': ready['prepared'],
        'admission_evidence': ready['evidence'], 'terminal': TERMINAL, 'owner_verification': VERIFIED,
        'owner_terminal_diagnostics': verified['diagnostics'], 'logical_views': views,
        'execution_runtime_sha': RUNTIME_SHA, 'generator_sha256': reference(__file__)['sha256'],
        'completed_at': terminal['completed_at'], 'parents': source['parents'],
        'new_descendant_coverage_rows': rows,
        'existing_completed_execution_aliases': source['existing_completed_execution_aliases'],
        'C_large_large_aliases_of_A_rows': source['C_large_large_aliases_of_A_rows'],
        'completed_job': {'job_id': manifest['job_id'], 'actual_manifest_sha256': digest(manifest),
            'actual_prepared_packet': prepared['jobs'][0], 'original_unleased_draft': record['packet'],
            'completion_receipt': receipt_refs['receipt'], 'result_reference_only_not_opened': receipt_refs['result'],
            'profile_reference_only_not_opened': actual['profile'], 'profile_id': manifest['profile_hash'],
            'parent_job_ids': manifest['parent_job_ids'], 'consumer': manifest['consumer'],
            'source_manifest_sha256': manifest['source_manifest_hash'], 'documents_sha256': manifest['documents_hash'],
            'items_sha256': manifest['items_hash'], 'option_order_schedule': manifest['option_order_schedule'],
            'extractor': manifest['extractor'], 'settings': actual['config']['settings'], 'timeout': actual['backend']['timeout'],
            'request_slots': 14, 'cache_hits': 0, 'uncertain_attempts': 0, 'known_estimated_spend_nanos_once': spend,
            'cost_basis': usage['budget_detail']['cost_basis']},
        'counts': {'actual_parent_builds': 4, 'complete_parents': 1, 'invalid_parents': 3,
            'new_planned_descendant_rows': 84, 'new_planned_A_rows': 56, 'new_planned_cross_C_rows': 28,
            'completed_new_jobs': 1, 'completed_new_draws': 14, 'new_unavailable_invalid_parent_rows': 70,
            'distinct_completed_new_body_identities': len({p['wire_request_sha256'] for p in pins}),
            'existing_completed_alias_rows': 56, 'C_large_large_alias_rows': 28,
            'unique_primary_A_C_execution_slots': 140, 'A_logical_rows': 84, 'C_logical_rows': 112,
            'A_C_shared_execution_slots': 56,
            'incremental_alias_calls': 0, 'incremental_alias_cost_nanos': 0},
        'incremental_prediction_known_estimated_spend_nanos_once': spend,
        'incremental_prediction_known_estimated_spend_usd_once': str(Decimal(spend) / 1_000_000_000),
        'prior_parent_build_known_spend_nanos_once': source['observed_parent_build_known_spend_nanos_once'],
        'cumulative_same_ledger_attempts_from_closed_owner_metadata': verified['native']['ledger_attempts'],
        'cumulative_same_ledger_spend_nanos_from_closed_owner_metadata': verified['native']['ledger_spent_nanos'],
        'api_calls_by_indexer': 0, 'execution_authorized': False, 'scores_or_labels_read': False,
        'result_profile_source_bodies_read': False, 'native_claims_or_live_sqlite_read': False,
        'limits': ['Receipt metadata binds all14 planned requests to a complete job; no prediction contents, labels or scores were read.',
            'Only Neel/Sol joint A completed.70 rows remain unavailable and unattempted because their frozen actual parents are invalid;04 owns classification and scoring.',
            'All four parent outcomes,56 prior completed aliases and28 C-large-large aliases are copied unchanged from the pinned coverage index; aliases add no calls/cost or independent observations.',
            'Ordered reversals are paired judgments, not independent cases. Completion does not establish fidelity or a cross-researcher finding.',
            'Recorded costs are conservative known-usage estimates, not invoice amounts.298 calls/$3.345365 is cumulative; this prediction increment is14/$0.085065.',
            'This is not a native-claim, unknown-request guard, baseline-content or scoring audit. Owner01 admission proofs and0007 denylist clarification retain their scope.',
            'Remaining P7/P3 extraction outcomes and descendants require separate actual-output handoffs; no repair, regeneration or substitution.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(inputs.items())]}
    directory = Path(tempfile.mkdtemp(prefix='primary14-completion-metadata-v1-', dir='/private/tmp/gio-profile-20261115-scaling'))
    path = directory / 'completion-index.json'
    path.write_text(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    path.chmod(0o600)
    print(json.dumps({'completion_index': reference(path), 'counts': result['counts'],
        'incremental_prediction_known_estimated_spend_usd_once': result['incremental_prediction_known_estimated_spend_usd_once'],
        'api_calls_by_indexer': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
