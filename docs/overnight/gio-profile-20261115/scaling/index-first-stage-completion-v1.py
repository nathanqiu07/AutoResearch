"""Read closed admission/receipt metadata only; no producer or execution path."""
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import tempfile

MODELS = {
    'gpt-6-sol': {
        'ready': {'path': '/private/tmp/gio-scaling-sol-native-admissions-v1/ready-index.json', 'sha256': 'ba96f2c68641e9d2f6bc281e8657f068ee88691261c016c5069b34b9240946e2'},
        'terminal': {'path': '/private/tmp/gio-profile-20261115-coordinator/scaling-sol-supervisor-v2/supervisor-terminal.json', 'sha256': '563d56a7ec180a8c0562eef06eaf1f81f68ae5f1469289a4d77dbfa82baa7e78'}},
    'gpt-6-astra': {
        'ready': {'path': '/private/tmp/gio-scaling-astra-native-admissions-v1/ready-index.json', 'sha256': '7a38c2686d87e1631566e381af43246d35eb83e71d8890508675d8fbb3f4c011'},
        'terminal': {'path': '/private/tmp/gio-profile-20261115-coordinator/scaling-astra-supervisor-v1/supervisor-terminal.json', 'sha256': 'a58489d8b922eaeb8f05a03346d231f0f8228f864c8aacf42a6328068670bcc4'}}}
BINDINGS = {'path': '/private/tmp/gio-profile-20261115-scaling/mechanical-ready-completed-packing-v1-e7jycsx_/prediction-ready-index.json',
            'sha256': '2f29c267b7eab6da7e28e53868a5427da3ec0d36494fda3864d81e39d61e0822'}
BINDING_REVIEW = {'path': '/private/tmp/gio-role05-scaling-bindings-review-v1/wire-binding-check.json',
                  'sha256': '8cd9edfe03f2f6ad1ce74f7c6ac15d361e01348fcafbaf1f9ae8269d2e10f107'}
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
        # No native claims, live SQLite, result bodies, score files, target
        # bundles, profile bodies or released source/item bodies are opened.
        assert path.is_absolute() and path.suffix not in ('.sqlite', '.sqlite3', '.db')
        assert path.name not in ('result.json', 'profile.json', 'claim.json')
        assert 'lease' not in path.parts and 'native-claims' not in path.parts
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ref['sha256'], 'metadata reference hash changed'
        inputs[str(path)] = ref['sha256']
        return json.loads(raw)

    bindings = read(BINDINGS)
    read(BINDING_REVIEW)
    prior = bindings['stage']['prior_packet_references']
    source_records = {r['packet']['sha256']: r for r in prior + bindings['prediction_packets']}
    assert len(source_records) == 186
    jobs, rows, aliases, batches, accounting, terminals = [], [], [], [], {}, {}
    actual_jobs = set()
    for model, pinned in MODELS.items():
        ready, terminal = read(pinned['ready']), read(pinned['terminal'])
        terminals[model] = terminal
        assert ready['model'] == model and ready['jobs'] == 62 and ready['max_calls'] == 140
        assert terminal['index'] == pinned['ready'] and terminal['status'] == 'complete'
        assert terminal['child_process_terminal'] is True and terminal['native_accounting_drain_verified'] is True
        assert terminal['planned_jobs'] == 62 and terminal['planned_call_ceiling'] == 140
        verified = {}
        for name in terminal['completed_verified_batches']:
            ref = reference(Path(pinned['terminal']['path']).parent / name)
            body = read(ref)
            assert body['status'] == 'known_terminal' and body['batch_id'] not in verified
            verified[body['batch_id']] = (ref, body)
        model_cost, model_attempts, model_jobs = 0, 0, 0
        for admission in ready['admissions']:
            prepared = read(admission['prepared'])
            evidence = read(admission['evidence'])
            batch_id = prepared['batch_id']
            verification_ref, verification = verified.pop(batch_id)
            assert prepared['code_sha'] == RUNTIME_SHA and evidence['scientific_fields_unchanged'] is True
            assert verification['block'] == admission['block'] == evidence['block']
            summary = read(verification['native']['summary'])
            assert summary['status'] == 'complete' and summary['batch_id'] == batch_id
            assert summary['counts'] == {'complete': admission['jobs'], 'dispatched': admission['jobs'], 'listed': admission['jobs'], 'not_dispatched': 0, 'other': 0}
            prepared_by_job = {}
            for packet_ref in prepared['jobs']:
                packet = read(packet_ref)
                jid = packet['manifest']['job_id']
                assert jid not in prepared_by_job
                prepared_by_job[jid] = (packet_ref, packet)
            receipts = {}
            for record in verification['native']['receipts']:
                receipt = read(record['receipt'])
                assert receipt['job_id'] not in receipts
                receipts[receipt['job_id']] = (record['receipt'], record['result'], receipt)
            assert len(prepared_by_job) == len(receipts) == len(evidence['mapping']) == admission['jobs']
            batch_cost, batch_attempts = 0, 0
            for mapping in evidence['mapping']:
                jid = mapping['job_id']
                assert jid not in actual_jobs
                actual_jobs.add(jid)
                packet_ref, packet = prepared_by_job.pop(jid)
                receipt_ref, result_ref, receipt = receipts.pop(jid)
                source_ref = mapping['original_draft']
                source_record = source_records[source_ref['sha256']]
                assert source_record['packet'] == source_ref
                source = read(source_ref)
                original = packet['manifest']
                assert original['code_sha'] == RUNTIME_SHA and original['kind'] == 'predict'
                assert original['consumer']['model'] == model == packet['backend']['model']
                assert digest(source['config']) == digest(packet['config'])
                assert packet['profile']['sha256'] == source['profile']['sha256'] and packet['release']['sha256'] == source['release']['sha256']
                stripped = json.loads(json.dumps(original))
                stripped.pop('job_id')
                stripped['allocation']['authorization_source'] = None
                assert digest(stripped) == digest(source['manifest'])
                assert receipt['manifest_sha256'] == digest(original) and receipt['status'] == 'complete'
                requests = mapping['requests']
                assert [r['item_id'] for r in requests] == packet['item_ids']
                assert receipt['counts'] == {'attempted': len(requests), 'complete': len(requests), 'error': 0}
                usage = receipt['usage']
                assert usage['attempted_calls'] == len(requests) and usage['cache_hits'] == usage['uncertain_attempts'] == 0
                assert usage['budget_detail']['reported_usage_complete'] is True
                cost_nanos = Decimal(str(usage['reported_api_usd'])) * 1_000_000_000
                assert cost_nanos == cost_nanos.to_integral_value()
                cost_nanos = int(cost_nanos)
                batch_cost += cost_nanos
                batch_attempts += len(requests)
                method = original['method_id']
                researcher = source_record.get('researcher_id')
                if researcher is None:
                    found = [r for r in ('neel_nanda', 'chris_olah') if '/' + r + '/' in source_record['label']]
                    assert len(found) == 1
                    researcher = found[0]
                alias_cap = original.get('scaling_empty_control_alias')
                assert original['scaling_logical_cap'] == 8192
                if method == 'no_profile':
                    assert original['personalization_cap'] == 2048 and alias_cap['actual_profile_cap'] == 2048 and alias_cap['logical_comparator_cap'] == 8192
                else:
                    assert original['personalization_cap'] == 8192
                record = {'job_id': jid, 'model': model, 'method_id': method, 'researcher_id': researcher,
                    'stage_intervention': 'B-fixed-Luna-primary' if method == 'P8' else 'mandatory-control',
                    'actual_prepared_packet': packet_ref, 'actual_manifest_sha256': digest(original),
                    'admission_mapping_packet': mapping['packet'], 'original_unleased_draft': source_ref,
                    'admission_evidence': admission['evidence'], 'completion_receipt': receipt_ref,
                    'result_reference_only_not_opened': result_ref, 'profile_reference_only_not_opened': packet['profile'],
                    'profile_id': original['profile_hash'], 'profile_parent_job_ids': original['parent_job_ids'],
                    'source_manifest_sha256': original['source_manifest_hash'], 'documents_sha256': original['documents_hash'],
                    'items_sha256': original['items_hash'], 'option_order_schedule': original['option_order_schedule'],
                    'actual_profile_cap': original['personalization_cap'], 'logical_cap': 8192,
                    'empty_control_alias': alias_cap, 'status': receipt['status'], 'request_slots': len(requests),
                    'attempted_calls': len(requests), 'cache_hits': 0, 'uncertain_attempts': 0,
                    'known_estimated_spend_nanos_once': cost_nanos, 'cost_basis': usage['budget_detail']['cost_basis'],
                    'execution_code_sha': original['code_sha'], 'consumer': original['consumer'],
                    'settings': packet['config']['settings'], 'timeout': packet['backend']['timeout']}
                jobs.append(record)
                pins = original['scaling_payload_pins']
                assert len(pins) == len(requests)
                for request, pin in zip(requests, pins):
                    assert request['item_id'] == pin['item_id'] and request['option_order_id'] == pin['option_order_id']
                    assert request['item_sha256'] == pin['item_sha256'] and request['request_sha256'] == pin['wire_request_sha256']
                    assert request['wire_bytes_sha256'] == pin['wire_bytes_sha256']
                    rows.append({'job_id': jid, 'model': model, 'method_id': method, 'researcher_id': researcher,
                        'item_id': request['item_id'], 'option_order_id': request['option_order_id'], 'item_sha256': request['item_sha256'],
                        'body_sha256': request['request_sha256'], 'endpoint_body_sha256_owner_proof': request['endpoint_body_sha256'],
                        'wire_bytes_sha256': request['wire_bytes_sha256'], 'draft_cache_key_reference': request['draft_cache_key'],
                        'status': 'complete', 'new_draw': True, 'cache_hit': False, 'cost_owner_job_id': jid,
                        'cost_allocation': 'job total counted once; no invented per-item spend split'})
            assert not prepared_by_job and not receipts
            assert batch_attempts == verification['native']['attempted_calls'] == admission['calls']
            assert batch_cost == verification['native']['known_spent_nanos']
            assert verification['diagnostics']['actual_open_events'] == batch_attempts
            batches.append({'model': model, 'block': admission['block'], 'batch_id': batch_id,
                'prepared': admission['prepared'], 'verification': verification_ref, 'summary': verification['native']['summary'],
                'jobs': admission['jobs'], 'request_slots': batch_attempts, 'known_estimated_spend_nanos_once': batch_cost})
            model_cost += batch_cost
            model_attempts += batch_attempts
            model_jobs += admission['jobs']
        assert not verified and model_jobs == 62 and model_attempts == 140
        if model == 'gpt-6-sol':
            assert terminal['known_verified_attempts'] == model_attempts and terminal['known_verified_spend_nanos'] == model_cost
        else:
            prior_terminal = terminals['gpt-6-sol']
            assert terminal['baseline'] == {'attempts': prior_terminal['known_verified_attempts'], 'spent': prior_terminal['known_verified_spend_nanos']}
            assert terminal['tranche_known_verified_attempts'] == terminal['known_verified_attempts'] - terminal['baseline']['attempts'] == model_attempts
            assert terminal['tranche_known_verified_spend_nanos'] == terminal['known_verified_spend_nanos'] - terminal['baseline']['spent'] == model_cost
        accounting[model] = {'jobs': model_jobs, 'new_draws': model_attempts,
            'incremental_known_estimated_spend_nanos': model_cost, 'incremental_known_estimated_spend_usd': str(Decimal(model_cost) / 1_000_000_000),
            'terminal_cumulative_attempts': terminal['known_verified_attempts'],
            'terminal_cumulative_spend_nanos': terminal['known_verified_spend_nanos'], 'terminal': pinned['terminal']}
    for source_record in prior:
        if source_record['status'] != 'historical-execution-alias':
            continue
        draft = read(source_record['packet'])
        assert len(source_record['historical_matches']) == 1
        historical = source_record['historical_matches'][0]
        historical_packet = read(historical['packet'])
        assert historical_packet['manifest']['job_id'] == historical['job_id']
        assert historical_packet['manifest']['consumer'] == draft['manifest']['consumer']
        assert draft['manifest']['consumer']['model'] == 'gpt-6-luna'
        assert digest(historical_packet['config']) == digest(draft['config'])
        for key in ('profile_hash', 'documents_hash', 'source_manifest_hash', 'items_hash', 'option_order_schedule'):
            assert historical_packet['manifest'][key] == draft['manifest'][key]
        assert historical_packet['backend']['timeout'] == draft['backend']['timeout']
        assert historical_packet['profile']['sha256'] == draft['profile']['sha256']
        manifest = draft['manifest']
        for pin in manifest['scaling_payload_pins']:
            aliases.append({'historical_job_id': historical['job_id'], 'historical_packet': historical['packet'],
                'source_draft': source_record['packet'], 'method_id': manifest['method_id'], 'model': 'gpt-6-luna',
                'profile_id': manifest['profile_hash'], 'profile_reference_only_not_opened': draft['profile'],
                'actual_profile_cap': manifest['personalization_cap'], 'logical_cap': manifest['scaling_logical_cap'],
                'empty_control_alias': manifest.get('scaling_empty_control_alias'), 'item_id': pin['item_id'],
                'option_order_id': pin['option_order_id'], 'item_sha256': pin['item_sha256'],
                'body_sha256': pin['wire_request_sha256'], 'wire_bytes_sha256': pin['wire_bytes_sha256'],
                'new_draw': False, 'incremental_stage_calls': 0, 'incremental_stage_cost_nanos': 0,
                'reuse_proof': historical['proof'], 'original_trace_sha256s': historical['trace_sha256s']})
    by_body = defaultdict(list)
    for row in rows:
        by_body[row['body_sha256']].append({k: row[k] for k in ('job_id', 'model', 'method_id', 'researcher_id', 'item_id', 'option_order_id')})
    duplicates = [{'body_sha256': h, 'logical_draws': group} for h,group in sorted(by_body.items()) if len(group) > 1]
    assert len(jobs) == 124 and len(rows) == 280 and len(by_body) == 278 and len(aliases) == 140
    assert len(duplicates) == 2
    for group in duplicates:
        draws = group['logical_draws']
        assert len(draws) == 2 and {r['method_id'] for r in draws} == {'lexical_retrieval', 'semantic_retrieval'}
        assert len({(r['model'], r['researcher_id'], r['item_id'], r['option_order_id']) for r in draws}) == 1
        assert draws[0]['researcher_id'] == 'neel_nanda'
    total_nanos = sum(v['incremental_known_estimated_spend_nanos'] for v in accounting.values())
    assert total_nanos == terminals['gpt-6-astra']['known_verified_spend_nanos'] == 2_899_380_000
    assert Counter(r['method_id'] for r in rows) == {'P8': 56, 'no_profile': 56, 'raw_evidence': 56, 'lexical_retrieval': 56, 'semantic_retrieval': 56}
    for path, h in inputs.items():
        assert reference(path)['sha256'] == h, 'metadata changed during index assembly'
    result = {'schema_version': 'scaling-first-stage-completion-metadata-v1', 'status': 'complete-metadata-only-not-scored',
        'selection': bindings['selection'], 'source_bindings': BINDINGS, 'binding_review': BINDING_REVIEW,
        'actual_admissions_and_terminals': MODELS, 'execution_runtime_sha': RUNTIME_SHA,
        'generator_sha256': reference(__file__)['sha256'], 'new_jobs': jobs, 'new_request_rows': rows, 'luna_alias_rows': aliases,
        'batches': batches, 'accounting': accounting, 'duplicate_wire_groups': duplicates,
        'counts': {'new_jobs': 124, 'new_request_slots': 280, 'completed_new_draws': 280, 'distinct_new_body_identities': 278,
            'historical_luna_alias_jobs': 62, 'historical_luna_alias_rows': 140, 'logical_ordered_rows': 420,
            'baseline_new_jobs': 120, 'baseline_new_draws': 224, 'primary_B_new_jobs': 4, 'primary_B_new_draws': 56,
            'new_request_cache_hits': 0, 'new_uncertain_attempts': 0, 'D_additional_calls': 0},
        'total_incremental_known_estimated_spend_nanos_once': total_nanos,
        'total_incremental_known_estimated_spend_usd_once': str(Decimal(total_nanos) / 1_000_000_000),
        'api_calls_by_indexer': 0, 'execution_authorized': False, 'scores_or_labels_read': False,
        'result_profile_source_bodies_read': False, 'native_claims_or_live_sqlite_read': False,
        'limits': ['Costs are conservative known usage estimates, not invoice amounts. Costs are counted once per actual job; Luna aliases add zero stage cost/calls.',
            'Astra terminal280 attempts/2.899380USD is cumulative; Astra increment is140 attempts/2.387300USD after Sol140/0.512080USD.',
            '280 actual completed draws have278 distinct BODY identities; two lexical/semantic same-input pairs are retained, not independent evidence or automatically deduplicated observations.',
            'Ordered reversals remain paired judgments, not independent cases. Semantic reversal can alter retrieval context; fidelity scoring/group maps remain04-owned.',
            'Canonical no-profile cap2048 artifact is an empty-render alias into logical8192; no profile identity retagging.',
            'This metadata index is not a second driver, native-claim audit, baseline content audit or score report. Existing owner01 dual-convention admission and05 baseline checks remain separate.',
            'Future four primary P8 builds and their56 joint+28 crossed consumers require a separate actual-output handoff; none inferred here.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(inputs.items())]}
    directory = Path(tempfile.mkdtemp(prefix='first-stage-completion-metadata-v1-', dir='/private/tmp/gio-profile-20261115-scaling'))
    path = directory / 'completion-index.json'
    path.write_text(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    path.chmod(0o600)
    print(json.dumps({'completion_index': reference(path), 'counts': result['counts'], 'accounting': accounting,
        'total_incremental_known_estimated_spend_usd_once': result['total_incremental_known_estimated_spend_usd_once'], 'api_calls_by_indexer': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
