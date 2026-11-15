"""Pure leaf-job preparation helpers; selection, leases and dispatch stay external."""
import copy
import hashlib
import json
import math
import re
from decimal import Decimal, ROUND_CEILING

from autoresearch.taste.overnight.contracts import digest
from autoresearch.taste.overnight.runner import job_id


def _hash(value, size=64):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % size, value):
        raise ValueError('explicit pinned hexadecimal hash required')


def _reference(value):
    from pathlib import Path
    if not isinstance(value, dict) or set(value) != {'path', 'sha256'} or not isinstance(value['path'], str) or not Path(value['path']).is_absolute():
        raise ValueError('exact absolute path/SHA256 reference required')
    _hash(value['sha256'])


def validate_continuation_case(case, row, mapping, raw_payloads):
    """Prove one explicitly listed continued admission; no general path aliasing."""
    if (case.get('cell_id') != row['cell_id'] or mapping['cell_id'] != row['cell_id']
            or case.get('status') != 'complete' or case.get('actual_claim_matches') is not True
            or case.get('original_semantic_identity_unchanged') is not True
            or case.get('changed_reference_fields') != ['build_prepared', 'build_packet', 'release']
            or case.get('profile_id') != mapping['profile_id'] or mapping['profile_id'] != row['profile_id']
            or case.get('original_index_packet') != row['build_packet']
            or case.get('original_index_prepared') != row['original_prepared']
            or case.get('actual_packet') != mapping['build_packet']
            or case.get('actual_prepared') != mapping['build_prepared']
            or case.get('actual_result') != mapping['build_result']):
        raise ValueError('continuation case does not bind exact original and selected admission')
    def read(reference):
        _reference(reference)
        raw = raw_payloads.get(reference['path'])
        if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != reference['sha256']:
            raise ValueError('continuation evidence bytes differ from pinned reference')
        return json.loads(raw)
    old, actual = read(case['original_index_packet']), read(case['actual_packet'])
    for field in ('schema_version', 'manifest', 'config', 'backend', 'registration', 'item_ids', 'profile'):
        if digest(old[field]) != digest(actual[field]):
            raise ValueError('continuation changed original semantic packet identity: ' + field)
    manifest = actual['manifest']
    if (manifest['job_id'] != row['job_id'] or job_id(manifest) != row['job_id']
            or manifest['config_hash'] != digest(actual['config'])
            or manifest['source_manifest_hash'] != row['source_manifest_hash']
            or manifest['documents_hash'] != row['documents_hash']
            or old['release'] != row['release'] or actual['release'] != mapping['release']
            or old['release']['sha256'] != actual['release']['sha256']):
        raise ValueError('continuation changed job, config, source or release content identity')
    claim = read(case['actual_claim'])
    if claim.get('status') != 'claimed' or digest(claim.get('manifest')) != digest(manifest) or digest(claim.get('lease')) != digest(actual['lease']):
        raise ValueError('actual continuation claim differs from actual manifest/lease')
    prepared, original = read(case['actual_prepared']), read(case['original_index_prepared'])
    if (case['actual_packet'] not in prepared.get('jobs', [])
            or case['original_index_packet'] not in original.get('jobs', [])
            or prepared.get('rebound_from') != case['original_index_prepared']
            or prepared.get('rebind_evidence') != case['rebind_evidence']):
        raise ValueError('continuation prepared admission lineage differs')
    evidence = read(case['rebind_evidence'])
    if (evidence.get('schema_version') != 'unattempted-rebind-evidence-v1'
            or evidence.get('old_prepared') != case['original_index_prepared']
            or evidence.get('no_retry') is not True or evidence.get('manifest_and_job_ids_unchanged') is not True
            or evidence.get('claims_and_outputs_preserved') is not True
            or type(evidence.get('calls_performed')) is not int or evidence['calls_performed'] != 0
            or type(evidence.get('ledger_mutations')) is not int or evidence['ledger_mutations'] != 0):
        raise ValueError('continuation rebind evidence does not prove zero-call preservation')
    records = [r for r in evidence['mappings'] if r['job_id'] == row['job_id']]
    absences = [r for r in evidence['evidence'] if r['job_id'] == row['job_id']]
    if len(records) != 1 or len(absences) != 1:
        raise ValueError('continuation rebind job evidence absent or ambiguous')
    record, absent = records[0], absences[0]
    if (record['old_packet'] != row['build_packet'] or record['manifest_sha256'] != digest(manifest)
            or record['old_lease_id'] != old['lease']['lease_id'] or record['new_lease_id'] != actual['lease']['lease_id']
            or absent.get('runner_claim_absent') is not True or absent.get('output_and_started_traces_absent') is not True
            or not isinstance(absent.get('execution_listings'), list)):
        raise ValueError('continuation old absence or exact lease/manifest mapping differs')
    # The hash-pinned owner evidence records historical absence; never re-read
    # live ledger/claim state to infer historical absence or execution permission.
    return {'cell_id': row['cell_id'], 'origin_job_id': row['job_id'], 'original_packet': row['build_packet'],
        'actual_packet': mapping['build_packet'], 'actual_claim': case['actual_claim'], 'rebind_evidence': case['rebind_evidence']}


def validate_descriptive_selection(selection, contract, original_index, *, contract_ref, index_ref, continuation_proof=None, continuation_payloads=None):
    """Accept coordinator-selected IDs, never rank scores or choose a finalist."""
    _reference(contract_ref)
    _reference(index_ref)
    if contract.get('schema_version') != 'development-scaling-selection-contract-v1':
        raise ValueError('unsupported coordinator scaling contract')
    shape = contract['final_receipt_shape']
    if not isinstance(selection, dict) or set(selection) != set(shape):
        raise ValueError('final descriptive selection has missing or undeclared fields')
    constants = ('schema_version', 'status', 'campaign_id', 'runtime_sha', 'models', 'extractor_settings',
                 'consumer_settings', 'controls', 'studies', 'source_condition', 'deadline', 'max_concurrent')
    if any(json.dumps(selection[key], sort_keys=True, allow_nan=False) != json.dumps(shape[key], sort_keys=True, allow_nan=False) for key in constants):
        raise ValueError('selection differs from the frozen descriptive contract')
    for key in ('execution_authorized', 'confirmation_authorized', 'fidelity_winner_claim', 'finalists_frozen'):
        if selection[key] is not False:
            raise ValueError('selection cannot grant execution, final-test or winner authority')
    if (type(selection['max_usd']) not in (int, float) or not math.isfinite(selection['max_usd'])
            or not 0 < selection['max_usd'] <= shape['max_usd']):
        raise ValueError('selection ceiling exceeds the frozen maximum')
    if selection['contract'] != contract_ref or selection['selection_policy'] != contract_ref:
        raise ValueError('selection policy/contract reference changed')
    if (selection['original_complete_index'] != index_ref
            or original_index.get('schema_version') != 'phase2-profile-extraction-coverage-v1'
            or original_index.get('runtime_sha') != selection['runtime_sha']
            or original_index.get('private_labels_included') is not False):
        raise ValueError('original index identity/schema/runtime differs')
    references = ('promotion_policy', 'three_replicate_score_receipt', 'original_complete_index',
        'sparse_completion_index', 'replicate_build_completion_index', 'replicate_prediction_completion_index',
        'control_inputs', 'semantic_index')
    for key in references:
        _reference(selection[key])
    for key in ('original_complete_index', 'sparse_completion_index', 'replicate_build_completion_index'):
        if selection[key]['sha256'] != shape[key]['sha256']:
            raise ValueError('selection changed a contract-pinned input index')
    if selection['diagnostic_panel'] is not None:
        _reference(selection['diagnostic_panel'])
    cap = selection['common_personalization_cap']
    if type(cap) is not int or cap not in (512, 2048, 8192):
        raise ValueError('explicit supported common byte cap required')
    configs = selection['selected_configs']
    if not isinstance(configs, list) or len(configs) > 3:
        raise ValueError('at most three explicitly selected method families allowed')
    config_fields = set(shape['selected_configs'][0])
    mapping_fields = set(shape['selected_configs'][0]['researcher_mappings'][0])
    rows, ids, methods = {}, set(), set()
    for row in original_index['cells']:
        if not isinstance(row.get('cell_id'), str) or row['cell_id'] in rows or type(row.get('replicate_id')) is not int:
            raise ValueError('original index has duplicate or malformed instances')
        rows[row['cell_id']] = row
    continuations = {}
    if continuation_proof is not None:
        if (continuation_proof.get('schema_version') != 'scaling-continuation-compatibility-v1'
                or continuation_proof.get('original_index') != index_ref):
            raise ValueError('unsupported continuation proof or original index')
        for case in continuation_proof['cases']:
            if case['cell_id'] in continuations:
                raise ValueError('duplicate continuation proof case')
            continuations[case['cell_id']] = case
    inventory = []
    for config in configs:
        if not isinstance(config, dict) or set(config) != config_fields:
            raise ValueError('selected configuration fields differ from contract')
        method, config_id = config['method_id'], config['config_id']
        if method not in {'P' + str(i) for i in range(1, 9)} or method in methods or not isinstance(config_id, str) or config_id in ids:
            raise ValueError('distinct exact configuration IDs and method families required')
        if (type(config['personalization_cap']) is not int or config['personalization_cap'] != cap
                or type(config['instance_replicate_id']) is not int or config['instance_replicate_id'] != 0
                or config['evidence_policy'] not in ('explicit-only', 'marked-inference')):
            raise ValueError('selected cap, evidence policy or replicate differs')
        expected_id = '%s-c%d-%s' % (method, cap, config['evidence_policy'])
        if config_id != expected_id:
            raise ValueError('selected config ID does not name its actual config')
        ids.add(config_id)
        methods.add(method)
        mappings = config['researcher_mappings']
        if (not isinstance(mappings, list) or len(mappings) != 2
                or {m.get('researcher_id') for m in mappings} != {'neel_nanda', 'chris_olah'}):
            raise ValueError('both researcher mappings must remain explicit')
        for mapping in mappings:
            if not isinstance(mapping, dict) or set(mapping) != mapping_fields:
                raise ValueError('selected researcher mapping differs from contract')
            row = rows.get(mapping['cell_id'])
            if row is None:
                raise ValueError('selected mapping lacks an original indexed rep0 cell')
            if (row['replicate_id'] != 0 or row['researcher_id'] != mapping['researcher_id']
                    or row['method'] != method or type(row['cap']) is not int or row['cap'] != cap
                    or row['evidence_policy'] != config['evidence_policy']):
                raise ValueError('selected mapping is not the actual original rep0 configuration')
            matches = {'build_prepared': 'original_prepared', 'build_packet': 'build_packet', 'build_result': 'result',
                       'release': 'release', 'source_manifest_hash': 'source_manifest_hash',
                       'items_sha256': 'items_sha256', 'target_bundle_sha256': 'target_bundle_sha256'}
            changed = {key for key, source in matches.items() if mapping[key] != row[source]}
            continuation = None
            if changed:
                if changed != {'build_prepared', 'build_packet', 'release'} or row['cell_id'] not in continuations:
                    raise ValueError('selected mapping changed original request/source identity')
                continuation = validate_continuation_case(continuations[row['cell_id']], row, mapping, continuation_payloads or {})
            for key in ('build_prepared', 'build_packet', 'build_result', 'release'):
                _reference(mapping[key])
            available = row['dispatch_status'] == 'complete' and row.get('profile') is not None
            if mapping['status'] != ('complete' if available else 'unavailable_rep0'):
                raise ValueError('selected mapping hides the original profile status')
            if (mapping['profile'] != (row.get('profile') if available else None)
                    or mapping['profile_id'] != (row.get('profile_id') if available else None)):
                raise ValueError('selected mapping substituted a saved profile')
            if available:
                _reference(mapping['profile'])
                _hash(mapping['profile_id'])
            inventory.append({'config_id': config_id, 'researcher_id': mapping['researcher_id'],
                'cell_id': row['cell_id'], 'replicate_id': 0, 'status': ('missing-profile-reference' if row['dispatch_status'] == 'complete' and not available else row['dispatch_status']),
                'error_code': row.get('error_code'), 'origin_job_id': row['job_id'],
                'profile_id': mapping['profile_id'], 'profile': copy.deepcopy(mapping['profile']), 'continuation': continuation})
    if configs and selection['primary_config_id'] not in ids:
        raise ValueError('primary configuration is not explicitly selected')
    return {'status': 'accepted-descriptive-selection' if len(configs) >= 2 else 'insufficient-planned-panel',
            'selected_instances': inventory, 'unselected_index_cells': len(rows) - len(inventory),
            'selection_authority': 'coordinator-receipt-only-no-ranking-performed'}


def lookup_required_instance(cells, *, cell_id, replicate_id):
    """Never infer an instance from another replicate or promotion/selection flag."""
    if not isinstance(cell_id, str) or not cell_id or type(replicate_id) is not int or replicate_id < 0:
        raise ValueError('explicit cell ID and nonnegative replicate required')
    candidates = [row for row in cells if row.get('cell_id') == cell_id]
    if any(type(row.get('replicate_id')) is not int or row['replicate_id'] < 0 for row in candidates):
        raise ValueError('index instance requires an exact nonnegative integer replicate')
    matches = [row for row in candidates if row['replicate_id'] == replicate_id]
    if len(matches) > 1:
        raise ValueError('duplicate index instance')
    if not matches:
        return {'cell_id': cell_id, 'replicate_id': replicate_id, 'status': 'missing-required-instance'}
    row = matches[0]
    status = row.get('dispatch_status')
    if not isinstance(status, str) or not status:
        raise ValueError('index instance requires explicit status')
    result = {'cell_id': cell_id, 'replicate_id': replicate_id, 'status': status,
              'reported_status': status, 'origin_job_id': row.get('job_id'), 'error_code': row.get('error_code')}
    if status == 'complete':
        if row.get('profile') is None:
            result['status'] = 'missing-profile-reference'
        else:
            result['profile'] = copy.deepcopy(row['profile'])
            result['profile_id'] = row.get('profile_id')
    return result


def new_extractor_build_draft(original_packet, *, target_identity, limits, expected_runtime_sha,
                              expected_origin_job_id, selection_sha256, index_sha256, selection_cell_id,
                              expected_build_pins):
    """Create a distinct Sol/Astra extraction request while preserving exact config.

    The caller supplies coordinator-frozen selection/index hashes and validated
    runtime identities. This is an unleased draft, never a granted allocation.
    No saved Luna profile is modified or re-extracted by this function.
    """
    for value in (expected_origin_job_id, selection_sha256, index_sha256):
        _hash(value)
    _hash(expected_runtime_sha, 40)
    if not isinstance(selection_cell_id, str) or not selection_cell_id:
        raise ValueError('explicit selected index cell required')
    source = copy.deepcopy(original_packet)
    if source.get('schema_version') != 'overnight-packet-v1':
        raise ValueError('original build packet schema mismatch')
    manifest, config = source['manifest'], source['config']
    if (manifest.get('schema_version') != 'overnight-job-v1' or manifest.get('stage') != 'dev'
            or manifest.get('kind') != 'build' or manifest.get('code_sha') != expected_runtime_sha
            or manifest.get('job_id') != expected_origin_job_id or job_id(manifest) != expected_origin_job_id):
        raise ValueError('original build runtime or job identity mismatch')
    if source.get('profile') is not None or manifest.get('profile_hash') is not None or manifest.get('consumer') is not None:
        raise ValueError('original packet is not an unconditioned extraction build')
    if digest(config) != manifest.get('config_hash'):
        raise ValueError('original build config hash mismatch')
    for field in ('method_id', 'personalization_cap', 'replicate_id', 'code_sha'):
        if config.get(field) != manifest.get(field):
            raise ValueError('original config and manifest differ: ' + field)
    if config['method_id'] not in {'P' + str(i) for i in range(1, 9)}:
        raise ValueError('only assigned P1-P8 extraction methods supported')
    if config.get('allowed_source_manifest_hash') != manifest.get('source_manifest_hash'):
        raise ValueError('original build source hash mismatch')
    settings = config.get('extractor_settings')
    if (not isinstance(settings, dict) or set(settings) != {'temperature', 'max_tokens'}
            or type(settings['max_tokens']) is not int or settings['max_tokens'] <= 0
            or type(settings['temperature']) not in (int, float) or not math.isfinite(settings['temperature'])
            or not 0 <= settings['temperature'] <= 2):
        raise ValueError('exact valid extraction call settings required')
    identity = copy.deepcopy(target_identity)
    origin_identity = manifest.get('extractor', {})
    if (origin_identity.get('model') != 'gpt-6-luna' or identity.get('model') not in ('gpt-6-sol', 'gpt-6-astra')
            or identity.get('label') != 'openai-responses-overnight:' + identity.get('model', '')
            or identity.get('class') != origin_identity.get('class')
            or identity.get('endpoint') != origin_identity.get('endpoint')
            or identity.get('enforced_settings') != origin_identity.get('enforced_settings')
            or identity.get('enforced_settings', {}).get('temperature') != 'not_sent'):
        raise ValueError('new extractor must preserve declared API settings and use Sol or Astra')
    if not isinstance(limits, dict) or set(limits) != {'max_calls', 'max_seconds', 'max_usd', 'timeout'}:
        raise ValueError('explicit new build ceilings required')
    if (type(limits['max_calls']) is not int or limits['max_calls'] != 1
            or any(type(limits[k]) not in (int, float) or not math.isfinite(limits[k]) or limits[k] <= 0
                   for k in ('max_seconds', 'max_usd', 'timeout')) or limits['timeout'] >= limits['max_seconds']):
        raise ValueError('one-call extraction ceiling and feasible finite timeout required')
    if 'decision' not in config and source['item_ids']:
        raise ValueError('global profile build must not acquire decision items')
    if 'decision' in config and len(source['item_ids']) != 1:
        raise ValueError('decision build requires its exact single-item binding')
    from autoresearch.taste.overnight.registry import get_builder
    from autoresearch.taste.overnight.consumer import implementation_hash
    builder = get_builder(config['method_id'])
    actual_build_pins = {'method_implementation_hash': builder.implementation_hash,
        'profile_prompt_version': builder.prompt_version, 'profile_prompt_sha256': builder.prompt_sha256,
        'renderer_implementation_hash': implementation_hash()}
    if expected_build_pins != actual_build_pins:
        raise ValueError('imported runtime method/prompt/renderer pins differ from approved pins')
    manifest.pop('job_id')
    manifest.update(extractor=identity, profile_hash=None, consumer=None,
        allocation={**{k: limits[k] for k in ('max_calls', 'max_seconds', 'max_usd')},
                    'cost_mode': 'priced_api', 'authorization_source': None},
        parent_job_ids=list(dict.fromkeys(manifest['parent_job_ids'] + [expected_origin_job_id])),
        scaling_study='A-joint-extraction-consumer-build', scaling_selection_sha256=selection_sha256,
        scaling_profile_index_sha256=index_sha256, scaling_selected_cell_id=selection_cell_id,
        scaling_origin_build_job_id=expected_origin_job_id,
        scaling_build_pins=actual_build_pins)
    if manifest['retry_policy'] != {'max_attempts': 1, 'retry_uncertain': False} or 'profile.json' not in manifest['expected_outputs']:
        raise ValueError('original retry/output contract changed')
    return {'schema_version': 'overnight-packet-v1', 'release': source['release'], 'item_ids': source['item_ids'],
        'profile': None, 'config': config, 'manifest': manifest, 'lease': None,
        'backend': {**copy.deepcopy(limits), 'model': identity['model'],
                    'reasoning': identity['enforced_settings']['reasoning_effort']}, 'registration': source['registration']}


def reservation_ceiling(model, max_tokens, input_bound=None):
    """Frozen adapter price upper bound, not billing or an allocation grant."""
    from autoresearch.taste.overnight.backends import RATES
    if model not in RATES or type(max_tokens) is not int or not 1 <= max_tokens <= 65536:
        raise ValueError('unsupported frozen model/output bound')
    # f6 rejects input_bound + max_tokens >= 272000. Build prompts are not run
    # here, so their conservative bound covers every request this adapter admits.
    bound = 271999 - max_tokens if input_bound is None else input_bound
    if type(bound) is not int or bound < 0 or bound + max_tokens >= 272000:
        raise ValueError('request exceeds frozen short-context bound')
    inp, out = map(Decimal, RATES[model])
    return float(((Decimal(bound) * inp + Decimal(max_tokens) * out) / Decimal(1_000_000)).quantize(
        Decimal('0.000000001'), rounding=ROUND_CEILING))


def prediction_packet(profile_body, release, *, profile_ref, release_ref, origin_job_id, identity,
                      settings, timeout, logical_cap, runtime, contract_sha256, registration,
                      selection_sha256, index_sha256, selected_cell_id, studies, item_ids=None,
                      compiler=None, peer_parent_releases=None):
    """Prepare one exact saved-profile consumer request; never rebuild its profile."""
    from autoresearch.taste.overnight.contracts import ProfileArtifact, validate_documents, source_manifest, render_content
    from autoresearch.taste.overnight.consumer import prepare_payload, implementation_hash, PROMPT_VERSION, SYSTEM, INSTRUCTION
    from autoresearch.taste.overnight.registry import get_builder
    from autoresearch.taste.overnight.runner import ITEM_FIELDS
    for reference in (profile_ref, release_ref):
        _reference(reference)
    for value in (origin_job_id, selection_sha256, index_sha256, contract_sha256):
        _hash(value)
    if (not isinstance(settings, dict) or set(settings) != {'temperature', 'max_tokens'}
            or type(settings['temperature']) not in (int, float) or not 0 <= settings['temperature'] <= 2
            or not math.isfinite(settings['temperature']) or type(settings['max_tokens']) is not int):
        raise ValueError('explicit valid consumer call settings required')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('explicit finite positive consumer timeout required')
    profile = ProfileArtifact.from_dict(profile_body)
    builder = get_builder(profile.method_id)
    if (profile.code_sha != runtime['code_sha'] or profile.status != 'complete'
            or profile.method_implementation_hash != builder.implementation_hash
            or profile.prompt_version != builder.prompt_version or profile.prompt_sha256 != builder.prompt_sha256
            or profile.renderer_implementation_hash != implementation_hash()
            or runtime['renderer_implementation_hash'] != implementation_hash()
            or runtime['consumer_prompt_version'] != PROMPT_VERSION
            or runtime['consumer_prompt_sha256'] != digest({'version': PROMPT_VERSION, 'system': SYSTEM, 'instruction': INSTRUCTION})):
        raise ValueError('saved profile method/prompt/renderer/runtime pins differ')
    if type(logical_cap) is not int or logical_cap not in (512, 2048, 8192):
        raise ValueError('explicit common byte cap required')
    canonical_empty_alias = (profile.method_id == 'no_profile' and profile.intentional_empty
                             and profile.token_count == 0)
    if profile.personalization_cap != logical_cap and not canonical_empty_alias:
        raise ValueError('saved profile cap differs; no profile retagging')
    if (identity.get('class') != 'OpenAIResponsesBackend'
            or identity.get('endpoint') != 'https://api.openai.com/v1/responses'
            or identity.get('label') != 'openai-responses-overnight:' + identity.get('model', '')
            or identity.get('model') not in ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra')
            or identity.get('enforced_settings') != profile.extractor.get('enforced_settings')
            or identity.get('enforced_settings', {}).get('temperature') != 'not_sent'):
        raise ValueError('consumer API identity/settings differ from frozen panel')
    docs, sources = release['sources']['documents'], source_manifest(release['sources']['documents'])
    if (profile.documents_hash != digest(docs) or profile.allowed_source_manifest_hash != digest(sources)
            or release['sources']['source_manifest'] != sources
            or release['sources']['allowed_source_manifest_hash'] != digest(sources)
            or profile.researcher_id != release['researcher_id']):
        raise ValueError('saved profile/release full records or source hashes differ')
    validate_documents(docs, profile.config)
    from autoresearch.taste.overnight.scaling import validate_raw_passage_scope, validate_consumer_binding
    validate_consumer_binding({'kind': 'neutral_profile', 'weights_status': profile.weights_status,
        'confidence_status': profile.confidence_status}, identity)
    if profile.method_id == 'no_profile' and (render_content(profile.content) or profile.intentional_empty is not True):
        raise ValueError('no-profile control must be intentionally empty')
    if profile.method_id in ('raw_evidence', 'lexical_retrieval', 'semantic_retrieval'):
        validate_raw_passage_scope(profile.content, docs)
    if profile.method_id == 'raw_evidence' and (not isinstance(profile.content, dict)
            or set(profile.content) != {'passages'} or 'frozen_profile' in profile.config):
        raise ValueError('raw control cannot carry candidate-derived profile content')
    if (profile.method_id in ('lexical_retrieval', 'semantic_retrieval')
            and profile.config.get('consumer_identity') != identity):
        raise ValueError('retrieval profile requires a new exact consumer binding')
    config = {'method_implementation_hash': profile.method_implementation_hash,
        'renderer_implementation_hash': implementation_hash(), 'profile_prompt_version': profile.prompt_version,
        'consumer_prompt_version': PROMPT_VERSION, 'settings': copy.deepcopy(settings)}
    peer_fields = ('approved_peer_sources', 'peer_policy', 'parent_releases')
    if release['schema_version'] == 'released-development-v2-p7-peers-v1':
        if compiler is None or peer_parent_releases is None:
            raise ValueError('exact peer parent proof required')
        proof = compiler._peer_release_proof(release, peer_parent_releases, profile.method_id)
        if any(profile.config.get(k) != release[k] for k in peer_fields):
            raise ValueError('saved peer profile declarations changed')
        config.update({k: copy.deepcopy(release[k]) for k in peer_fields})
    else:
        proof = None
        if any(k in release or k in profile.config for k in peer_fields):
            raise ValueError('ordinary consumer cannot acquire peer declarations')
    if digest(release['items']) != release['items_sha256']:
        raise ValueError('release item hash differs')
    by_id = {}
    for item in release['items']:
        if (not isinstance(item, dict) or set(item) != ITEM_FIELDS or item['researcher_id'] != profile.researcher_id
                or not isinstance(item['item_id'], str) or item['item_id'] in by_id):
            raise ValueError('exact label-free released items required')
        by_id[item['item_id']] = item
    ids = list(by_id) if item_ids is None else list(item_ids)
    if not ids or len(set(ids)) != len(ids) or any(i not in by_id for i in ids):
        raise ValueError('explicit unique released item order required')
    items, pins, total = [by_id[i] for i in ids], [], Decimal(0)
    if profile.method_id in ('lexical_retrieval', 'semantic_retrieval') and (len(items) != 1
            or profile.config.get('decision') != {k: items[0][k] for k in ('context', 'options')}):
        raise ValueError('retrieval decision binding differs from exact single item')
    for item in items:
        prepared = prepare_payload(profile, item['context'], item['options'], config)
        wire = {'model': identity['model'], 'instructions': prepared['system'], 'input': prepared['prompt'],
            'max_output_tokens': settings['max_tokens'], 'reasoning': {'effort': identity['enforced_settings']['reasoning_effort']},
            'store': False, 'service_tier': 'default', 'prompt_cache_options': {'mode': 'implicit', 'ttl': '30m'}}
        raw = json.dumps(wire, ensure_ascii=False, allow_nan=False).encode('utf-8')
        total += Decimal(str(reservation_ceiling(identity['model'], settings['max_tokens'], len(raw) + 1024)))
        pins.append({'item_id': item['item_id'], 'item_sha256': digest(item), 'option_order_id': item['option_order_id'],
            'payload_sha256': prepared['payload_sha256'], 'rendered_profile_sha256': prepared['rendered_profile_sha256'],
            'wire_request_sha256': digest(wire), 'wire_bytes_sha256': hashlib.sha256(raw).hexdigest(),
            'input_token_upper_bound': len(raw) + 1024, 'max_usd_reservation': reservation_ceiling(identity['model'], settings['max_tokens'], len(raw) + 1024),
            'prompt_utf8_sha256': hashlib.sha256(prepared['prompt'].encode()).hexdigest(),
            'system_utf8_sha256': hashlib.sha256(prepared['system'].encode()).hexdigest()})
    limits = {'max_calls': len(ids), 'max_seconds': len(ids) * timeout + 60, 'max_usd': float(total), 'timeout': timeout}
    manifest = {'schema_version': 'overnight-job-v1', 'campaign_id': 'gio-profile-20261115', 'stage': 'dev', 'kind': 'predict',
        'contract_sha256': contract_sha256, 'code_sha': runtime['code_sha'], 'deadline': runtime['deadline'],
        'method_id': profile.method_id, 'replicate_id': profile.replicate_id, 'personalization_cap': profile.personalization_cap,
        'config_hash': digest(config), 'source_manifest_hash': digest(sources), 'documents_hash': digest(docs),
        'items_hash': digest(items), 'option_order_schedule': [{'item_id': i['item_id'], 'option_order_id': i['option_order_id']} for i in items],
        'extractor': profile.extractor, 'consumer': copy.deepcopy(identity), 'profile_hash': profile.profile_id,
        'allocation': {**{k: limits[k] for k in ('max_calls', 'max_seconds', 'max_usd')}, 'cost_mode': 'priced_api', 'authorization_source': None},
        'retry_policy': {'max_attempts': 1, 'retry_uncertain': False}, 'parent_job_ids': [origin_job_id],
        'expected_outputs': ['result.json', 'traces'], 'scaling_selection_sha256': selection_sha256,
        'scaling_profile_index_sha256': index_sha256, 'scaling_selected_cell_id': selected_cell_id,
        'scaling_studies': sorted(set(studies)), 'scaling_logical_cap': logical_cap, 'scaling_payload_pins': pins}
    if proof is not None:
        manifest['scaling_peer_evidence'] = proof
    if profile.personalization_cap != logical_cap:
        manifest['scaling_empty_control_alias'] = {'actual_profile_cap': profile.personalization_cap,
            'logical_comparator_cap': logical_cap, 'proof': 'intentional-empty profile; identical actual rendered payload required for reuse'}
    execution = digest({'runtime_sha': runtime['code_sha'], 'method_id': profile.method_id, 'profile_id': profile.profile_id,
        'documents_hash': digest(docs), 'sources_hash': digest(sources), 'items_hash': digest(items),
        'identity': identity, 'settings': settings, 'timeout': timeout, 'payload_pins': pins})
    manifest['scaling_execution_identity_sha256'] = execution
    return {'schema_version': 'overnight-packet-v1', 'release': copy.deepcopy(release_ref), 'profile': copy.deepcopy(profile_ref),
        'item_ids': ids, 'config': config, 'manifest': manifest, 'lease': None,
        'backend': {**limits, 'model': identity['model'], 'reasoning': identity['enforced_settings']['reasoning_effort']},
        'registration': copy.deepcopy(registration)}


def future_prediction_bounds(items, model, settings, personalization_cap):
    """Conservative per-item bounds while a future exact profile is unavailable.

    render_content is canonical JSON without literal control characters. Its
    UTF8 bytes expand by at most 4x through payload JSON then wire JSON quoting.
    The exact empty-personalization wire covers all other request bytes.
    """
    from autoresearch.taste.overnight.contracts import canonical_json
    from autoresearch.taste.overnight.consumer import SYSTEM, INSTRUCTION
    if type(personalization_cap) is not int or personalization_cap not in (512, 2048, 8192):
        raise ValueError('supported byte cap required for future bound')
    bounds = []
    for item in items:
        payload = {'context': item['context'], 'options': item['options'], 'personalization': ''}
        wire = {'model': model, 'instructions': SYSTEM, 'input': INSTRUCTION + '\nINPUT_JSON:\n' + canonical_json(payload),
            'max_output_tokens': settings['max_tokens'], 'reasoning': {'effort': 'medium'}, 'store': False,
            'service_tier': 'default', 'prompt_cache_options': {'mode': 'implicit', 'ttl': '30m'}}
        bound = len(json.dumps(wire, ensure_ascii=False, allow_nan=False).encode()) + 1024 + 4 * personalization_cap
        bounds.append({'item_id': item['item_id'], 'input_bound': bound,
            'max_usd': reservation_ceiling(model, settings['max_tokens'], bound)})
    return bounds
