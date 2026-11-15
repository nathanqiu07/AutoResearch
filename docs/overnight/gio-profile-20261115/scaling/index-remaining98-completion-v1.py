"""Join closed P7/P3 completion metadata to the unchanged 112 planned slots."""
import copy
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
import tempfile

BINDINGS = {'path': '/private/tmp/gio-profile-20261115-scaling/remaining8-valid-descendants-v1-j6dcoyqb/remaining8-ready-index.json', 'sha256': '91299be67bd68c21377d44f05f5fdafe5d020e968ec2607a0e485728633e274b'}
READY = {'path': '/private/tmp/gio-remaining98-native-admissions-v1/ready-index.json', 'sha256': '89b89e9276adc093195673638eb12d57e4ca93eab64665f4dfa266c6967dfdff'}
TERMINAL = {'path': '/private/tmp/gio-profile-20261115-coordinator/remaining98-prediction-supervisor-v1/supervisor-terminal.json', 'sha256': '0c99f78924a51c1b20fa18d7fcf8b42160f091791e3a689e38370c2d4af367e5'}
VERIFIED = [
    {'path': '/private/tmp/gio-profile-20261115-coordinator/remaining98-prediction-supervisor-v1/verified-P7.json', 'sha256': '1d8e874c7d73ea0539378eb51fae7e6e6fd13daa118cc2f0bfeb981034aa9530'},
    {'path': '/private/tmp/gio-profile-20261115-coordinator/remaining98-prediction-supervisor-v1/verified-P3.json', 'sha256': '3567c511a7dedf291137e88101bc3a71796fbf91c16a15633bfcc31a36b3a247'}]
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

    source, ready, terminal = read(BINDINGS), read(READY), read(TERMINAL)
    assert ready['bindings'] == BINDINGS and terminal['index'] == READY
    assert terminal['completed_verified_batches'] == VERIFIED and terminal['status'] == 'complete'
    assert terminal['child_process_terminal'] is True and terminal['native_accounting_drain_verified'] is True
    assert ready['jobs'] == terminal['planned_jobs'] == 7
    assert ready['max_calls'] == terminal['planned_call_ceiling'] == 98
    assert ready['planned_descendant_slots'] == terminal['planned_descendant_slots'] == 112
    assert ready['unavailable_descendant_slots'] == terminal['unavailable_descendant_slots'] == 14
    baseline = {'attempts': 306, 'spent': 3883810000}
    assert ready['baseline'] == terminal['baseline'] == baseline
    assert ready['predecessor'] == source['closed_predecessor']
    assert ready['unknown_denylist'] == source['typed_denylist_future_owner_admission']
    assert [a['block'] for a in ready['admissions']] == ['P7', 'P3']
    assert source['runtime_sha'] == RUNTIME_SHA
    source_records = {r['packet']['sha256']: r for r in source['ready_prediction_packets']}
    assert len(source_records) == 7
    rows = copy.deepcopy(source['new_descendant_coverage_rows'])
    assert len(rows) == len({r['coverage_row_id'] for r in rows}) == 112
    pending = {(r['packet']['sha256'], r['item_id']): r for r in rows if r['status'] == 'unleased_ready'}
    assert len(pending) == 98
    jobs, batches, actual_ids, seen_drafts = [], [], set(), set()
    prior_attempts, prior_spend = baseline['attempts'], baseline['spent']
    for admission, verification_ref, source_batch in zip(ready['admissions'], VERIFIED, source['homogeneous_proposed_batches']):
        method = admission['block']
        prepared, evidence, verified = read(admission['prepared']), read(admission['evidence']), read(verification_ref)
        assert evidence['block'] == verified['block'] == source_batch['method_id'] == method
        assert evidence['scientific_fields_unchanged'] is True and verified['baseline'] == baseline
        assert prepared['code_sha'] == RUNTIME_SHA
        schema = 'released-development-v2-p7-peers-v1' if method == 'P7' else 'released-development-v2'
        assert admission['release_schema_version'] == prepared['release_schema_version'] == source_batch['release_schema_version'] == schema
        assert prepared['release_scope'] == source_batch['release_scope']
        summary = read(verified['native']['summary'])
        assert summary['batch_id'] == prepared['batch_id'] and summary['status'] == 'complete'
        assert summary['counts'] == {'complete': admission['jobs'], 'dispatched': admission['jobs'], 'listed': admission['jobs'], 'not_dispatched': 0, 'other': 0}
        actual_packets = {}
        for ref in prepared['jobs']:
            packet = read(ref)
            jid = packet['manifest']['job_id']
            assert jid not in actual_packets
            actual_packets[jid] = (ref, packet)
        receipts = {}
        for refs in verified['native']['receipts']:
            receipt = read(refs['receipt'])
            assert receipt['job_id'] not in receipts
            receipts[receipt['job_id']] = (refs, receipt)
        assert len(actual_packets) == len(receipts) == len(evidence['mappings']) == admission['jobs'] == source_batch['jobs']
        batch_cost, batch_calls, batch_job_ids, ordered_drafts = 0, 0, [], []
        for mapping in evidence['mappings']:
            jid = mapping['job_id']
            assert jid not in actual_ids
            actual_ids.add(jid)
            actual_ref, actual = actual_packets.pop(jid)
            refs, receipt = receipts.pop(jid)
            record = source_records[mapping['original_draft']['sha256']]
            assert mapping['original_draft'] == record['packet'] and record['packet']['sha256'] not in seen_drafts
            seen_drafts.add(record['packet']['sha256'])
            ordered_drafts.append(record['packet'])
            assert mapping['only_changed_fields'] == ['lease', 'manifest.job_id', 'manifest.allocation.authorization_source']
            original, bound = read(record['packet']), read(mapping['bound_packet'])
            assert digest(actual['manifest']) == digest(bound['manifest'])
            for key in ('config', 'backend', 'item_ids', 'registration', 'schema_version'):
                assert digest(actual[key]) == digest(bound[key]) == digest(original[key]), key
            for key in ('profile', 'release'):
                assert actual[key]['sha256'] == bound[key]['sha256'] == original[key]['sha256'], key
            manifest = actual['manifest']
            stripped = copy.deepcopy(manifest)
            stripped.pop('job_id')
            stripped['allocation']['authorization_source'] = None
            assert digest(stripped) == digest(original['manifest']), 'admission changed scientific identity'
            assert manifest['kind'] == 'predict' and manifest['method_id'] == record['method_id'] == method
            assert manifest['code_sha'] == RUNTIME_SHA and manifest['scaling_studies'] == ['A']
            assert manifest['consumer'] == record['effective_consumer']
            assert manifest['consumer']['model'] == record['extractor'] == record['consumer']
            assert manifest['personalization_cap'] == manifest['scaling_logical_cap'] == 8192
            assert manifest['parent_job_ids'] == [record['actual_parent_job_id']]
            assert manifest['profile_hash'] == record['profile_id'] and actual['profile']['sha256'] == record['profile']['sha256']
            assert actual['release']['sha256'] == record['release']['sha256'] and record['release_schema_version'] == schema
            assert actual['config']['settings'] == record['settings'] == {'max_tokens': 8192, 'temperature': 0.0}
            assert actual['backend']['timeout'] == record['timeout'] == 60
            assert manifest.get('scaling_peer_evidence') == record['peer_evidence']
            assert receipt['manifest_sha256'] == digest(manifest) and receipt['status'] == 'complete'
            assert receipt['counts'] == {'attempted': 14, 'complete': 14, 'error': 0}
            assert receipt['result_path'] == refs['result']['path']
            usage = receipt['usage']
            assert usage['attempted_calls'] == 14 and usage['cache_hits'] == usage['uncertain_attempts'] == 0
            assert usage['budget_detail']['reported_usage_complete'] is True
            cost = Decimal(str(usage['reported_api_usd'])) * 1_000_000_000
            assert cost == cost.to_integral_value()
            cost = int(cost)
            batch_cost += cost
            batch_calls += 14
            batch_job_ids.append(jid)
            requests, pins = mapping['requests'], manifest['scaling_payload_pins']
            assert pins == record['request_pins'] and len(requests) == len(pins) == 14
            assert [r['item_id'] for r in requests] == actual['item_ids']
            assert len({p['item_id'] for p in pins}) == 14
            for request, pin in zip(requests, pins):
                row = pending.pop((record['packet']['sha256'], pin['item_id']))
                assert row['request_identity'] == pin and row['packet'] == record['packet']
                assert row['actual_parent_job_id'] == record['actual_parent_job_id']
                assert row['profile_id'] == record['profile_id'] and row['profile_reference'] == record['profile']
                assert row['item_sha256'] == request['item_sha256'] == pin['item_sha256']
                assert row['option_order_id'] == pin['option_order_id'] and request['item_id'] == pin['item_id']
                assert request['request_sha256'] == pin['wire_request_sha256'] and request['wire_bytes_sha256'] == pin['wire_bytes_sha256']
                assert request['input_token_upper_bound'] == pin['input_token_upper_bound']
                assert Decimal(str(request['max_usd_reservation'])) == Decimal(str(pin['max_usd_reservation']))
                row.update({'status': 'complete', 'prediction_attempted': True, 'prediction_outcome': 'complete',
                    'original_draft_status': 'unleased_ready', 'actual_prediction_job_id': jid,
                    'actual_prepared_packet': actual_ref, 'completion_receipt': refs['receipt'],
                    'result_reference_only_not_opened': refs['result'],
                    'endpoint_body_sha256_owner_proof': request['endpoint_body_sha256'],
                    'new_draw': True, 'cache_hit': False, 'cost_owner_job_id': jid,
                    'cost_allocation': 'actual job cost counted once; no per-item cost split'})
            jobs.append({'job_id': jid, 'method_id': method, 'researcher_id': record['researcher_id'],
                'actual_manifest_sha256': digest(manifest), 'actual_prepared_packet': actual_ref,
                'original_unleased_draft': record['packet'], 'admission_evidence': admission['evidence'],
                'completion_receipt': refs['receipt'], 'result_reference_only_not_opened': refs['result'],
                'profile_reference_only_not_opened': actual['profile'], 'profile_id': manifest['profile_hash'],
                'release_reference_only_not_opened': actual['release'], 'release_schema_version': schema,
                'parent_job_ids': manifest['parent_job_ids'], 'consumer': manifest['consumer'], 'extractor': manifest['extractor'],
                'source_manifest_sha256': manifest['source_manifest_hash'], 'documents_sha256': manifest['documents_hash'],
                'items_sha256': manifest['items_hash'], 'option_order_schedule': manifest['option_order_schedule'],
                'peer_evidence': record['peer_evidence'], 'settings': actual['config']['settings'],
                'timeout': actual['backend']['timeout'], 'request_slots': 14, 'cache_hits': 0, 'uncertain_attempts': 0,
                'known_estimated_spend_nanos_once': cost, 'cost_basis': usage['budget_detail']['cost_basis']})
        assert not actual_packets and not receipts and ordered_drafts == source_batch['packets']
        assert batch_calls == verified['native']['attempted_calls'] == verified['diagnostics']['actual_open_events'] == admission['max_calls']
        assert batch_cost == verified['native']['known_spent_nanos']
        assert verified['native']['ledger_attempts'] == prior_attempts + batch_calls
        assert verified['native']['ledger_spent_nanos'] == prior_spend + batch_cost
        prior_attempts, prior_spend = verified['native']['ledger_attempts'], verified['native']['ledger_spent_nanos']
        batches.append({'method_id': method, 'batch_id': prepared['batch_id'], 'prepared': admission['prepared'],
            'admission_evidence': admission['evidence'], 'owner_verification': verification_ref,
            'summary': verified['native']['summary'], 'owner_terminal_diagnostics': verified['diagnostics'],
            'release_schema_version': schema, 'release_scope': prepared['release_scope'], 'actual_job_ids': batch_job_ids,
            'completed_jobs': len(batch_job_ids), 'completed_calls': batch_calls, 'known_estimated_spend_nanos_once': batch_cost})
    assert not pending and len(jobs) == 7 and len(seen_drafts) == 7
    assert Counter(r['status'] for r in rows) == {'complete': 98, 'unavailable_invalid_parent': 14}
    assert Counter(r['method_id'] for r in rows if r['status'] == 'complete') == {'P7': 56, 'P3': 42}
    for old, new in zip(source['new_descendant_coverage_rows'], rows):
        if old['status'] == 'unavailable_invalid_parent':
            assert old == new and new['prediction_attempted'] is False and new['prediction_outcome'] is None
    assert len(source['parents']) == 8 and Counter(p['parent_status'] for p in source['parents']) == {'complete': 7, 'invalid': 1}
    invalid = next(p for p in source['parents'] if p['parent_status'] == 'invalid')
    assert (invalid['method_id'], invalid['researcher_id'], invalid['extractor']) == ('P3', 'neel_nanda', 'gpt-6-astra')
    assert invalid['rendered_utf8_bytes'] == 8197 and invalid['profile_byte_cap'] == 8192
    total = sum(j['known_estimated_spend_nanos_once'] for j in jobs)
    assert total == 1050250000 and prior_attempts == terminal['known_verified_attempts'] == 404
    assert prior_spend == terminal['known_verified_spend_nanos'] == 4934060000
    for path, h in inputs.items():
        assert reference(path)['sha256'] == h, 'metadata changed during assembly'
    result = {'schema_version': 'remaining98-completion-metadata-v1', 'status': 'completed-valid-descendants-with-invalid-coverage-retained-not-scored',
        'selection': source['selection'], 'source_bindings': BINDINGS, 'actual_admission_index': READY,
        'terminal': TERMINAL, 'owner_verifications': VERIFIED, 'execution_runtime_sha': RUNTIME_SHA,
        'generator_sha256': reference(__file__)['sha256'], 'completed_at': terminal['completed_at'],
        'parents': source['parents'], 'new_descendant_coverage_rows': rows, 'completed_jobs': jobs,
        'completed_schema_homogeneous_batches': batches,
        'counts': {'actual_parent_builds': 8, 'complete_parents': 7, 'invalid_parents': 1,
            'planned_joint_A_rows': 112, 'completed_new_jobs': 7, 'completed_new_draws': 98,
            'unavailable_invalid_parent_rows': 14, 'P7_completed_jobs': 4, 'P7_completed_rows': 56,
            'P3_completed_jobs': 3, 'P3_completed_rows': 42,
            'distinct_completed_new_body_identities': len({r['request_identity']['wire_request_sha256'] for r in rows if r['status'] == 'complete'}),
            'cache_hits': 0, 'uncertain_attempts': 0},
        'incremental_prediction_known_estimated_spend_nanos_once': total,
        'incremental_prediction_known_estimated_spend_usd_once': str(Decimal(total) / 1_000_000_000),
        'prior_parent_build_known_spend_nanos_once': source['observed_parent_build_known_spend_nanos_once'],
        'same_ledger_baseline_from_closed_owner_metadata': baseline,
        'cumulative_same_ledger_attempts_from_closed_owner_metadata': prior_attempts,
        'cumulative_same_ledger_spend_nanos_from_closed_owner_metadata': prior_spend,
        'api_calls_by_indexer': 0, 'execution_authorized': False, 'scores_or_labels_read': False,
        'result_profile_source_bodies_read': False, 'native_claims_or_live_sqlite_read': False,
        'limits': ['Closed receipts bind98 requests to7 complete jobs; no prediction contents,labels or scores were read.',
            'All112 planned slots retained;14 Neel/Astra/P3 rows remain unavailable/unattempted after an8197byte parent exceeded8192cap by5bytes.04 owns classification/scoring.',
            'All8 parent records copied unchanged. P7 retains approved target-plus-peer evidence; P3 remains target-only; cross-method comparisons do not hold evidence constant.',
            'Actual P7/P3 batches preserve separate homogeneous schema/scope and original order; no P8/primary14 work duplicated or original Luna/P3 missing profile replaced.',
            '98 new calls/$1.050250 are incremental;404calls/$4.934060 are cumulative. Costs count once per actual job and are conservative usage estimates,not invoices.',
            'Ordered reversals remain paired judgments,not independent cases. Completion establishes no fidelity,capability ordering or cross-researcher finding.',
            'This is no admission/native-claim/unknown-guard/body-content audit. Owner01 proofs and0007 clarification retain their scope; no new all-clear claim.',
            'No provider calls,preparation,leases,claims,live-ledger reads,repairs,substitutions or new selection.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(inputs.items())]}
    directory = Path(tempfile.mkdtemp(prefix='remaining98-completion-metadata-v1-', dir='/private/tmp/gio-profile-20261115-scaling'))
    path = directory / 'completion-index.json'
    path.write_text(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    path.chmod(0o600)
    print(json.dumps({'completion_index': reference(path), 'counts': result['counts'],
        'incremental_prediction_known_estimated_spend_usd_once': result['incremental_prediction_known_estimated_spend_usd_once'],
        'api_calls_by_indexer': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
