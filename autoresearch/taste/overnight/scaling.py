"""Offline scaling design and integrity checks; never schedules or invokes models.

S/M/L are declared panel levels, not parameter counts or measured capability.
Manifests contain opaque item IDs and hashes, never targets, labels or profiles.
The caller must retain an independent frozen digest: self-hashing alone cannot
prevent a caller from replacing a whole design. Final reservation and execution
remain with the evaluator and the coordinator's existing leased runner.
"""
import json
import math

from .contracts import TOKEN_COUNT_METHOD, ProfileArtifact, canonical_json, digest, render_content


LEVELS = ('S', 'M', 'L')
DESIGN_FIELDS = {'schema_version', 'campaign_id', 'stage', 'contract_sha256', 'code_sha',
                 'panel_id', 'panel_kind', 'axis', 'models', 'common', 'methods',
                 'primary_method_id', 'fixed_profile', 'controls', 'diagnostic', 'deviations'}
COMMON_FIELDS = {'items', 'items_hash', 'task_context_hash', 'allowed_source_manifest_hash',
                 'personalization_cap', 'context_cap', 'cap_unit', 'truncation_rule', 'settings',
                 'renderer_implementation_hash', 'consumer_prompt_version',
                 'consumer_prompt_sha256', 'researcher_id', 'outcome_panel'}
METHOD_FIELDS = {'method_id', 'config_hashes', 'method_implementation_hash',
                 'profile_prompt_version', 'profile_prompt_sha256'}
DIAGNOSTIC_FIELDS = {'items', 'items_hash', 'task_context_hash', 'raw_evidence_hash',
                     'subset_manifest_hash', 'recorded_judgment_manifest_hash',
                     'withholding_receipt_hash', 'label_tier', 'profile_conditioning'}
PIN_FIELDS = {'kind', 'profile_id', 'content_sha256', 'method_id', 'extractor_level',
              'extractor', 'extractor_settings', 'replicate_id', 'config_id', 'code_sha',
              'allowed_source_manifest_hash', 'personalization_cap', 'researcher_id',
              'method_implementation_hash', 'renderer_implementation_hash',
              'prompt_version', 'prompt_sha256', 'weights_status', 'confidence_status',
              'token_count', 'token_count_method'}
UNAVAILABLE_PIN_FIELDS = {'kind', 'method_id', 'extractor_level', 'reason', 'evidence_sha256'}


def _copy(value):
    return json.loads(canonical_json(value))


def _fields(value, required, name):
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(name + ' has missing or undeclared fields')


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' requires nonempty text')


def _hash(value, name, length=64):
    if (not isinstance(value, str) or len(value) != length or
            any(char not in '0123456789abcdef' for char in value)):
        raise ValueError(name + ' requires an exact hexadecimal hash')


def _items(items):
    if not isinstance(items, list) or not items:
        raise ValueError('nonempty ordered item manifest required')
    seen = set()
    for item in items:
        _fields(item, {'item_id', 'option_order_id', 'context_sha256', 'options_sha256'}, 'item')
        _text(item['item_id'], 'item ID')
        _text(item['option_order_id'], 'option order ID')
        if item['item_id'] in seen:
            raise ValueError('duplicate item ID')
        seen.add(item['item_id'])
        _hash(item['context_sha256'], 'item context')
        _hash(item['options_sha256'], 'ordered options')


def _settings(value):
    if not isinstance(value, dict) or not {'temperature', 'max_tokens'} <= set(value):
        raise ValueError('explicit consumer settings required')
    if (isinstance(value['max_tokens'], bool) or not isinstance(value['max_tokens'], int)
            or value['max_tokens'] <= 0):
        raise ValueError('positive output bound required')
    temperature = value['temperature']
    if temperature is not None and (isinstance(temperature, bool) or
            not isinstance(temperature, (int, float)) or not math.isfinite(temperature)):
        raise ValueError('invalid temperature')


def _validate_design(spec):
    _fields(spec, DESIGN_FIELDS, 'scaling design')
    version2 = spec['schema_version'] == 'overnight-scaling-design-v2'
    if spec['schema_version'] not in ('overnight-scaling-design-v1', 'overnight-scaling-design-v2'):
        raise ValueError('unsupported scaling design schema')
    if spec['stage'] not in ('offline', 'dev', 'confirmation'):
        raise ValueError('unsupported stage')
    for key in ('campaign_id', 'panel_id'):
        _text(spec[key], key)
    _hash(spec['contract_sha256'], 'contract')
    _hash(spec['code_sha'], 'code', 40)
    if spec['axis'] != 'declared-model-level-not-parameter-count':
        raise ValueError('panel names do not establish parameter counts or capability')
    prefixes = {'offline': ('offline',), 'responses_api': ('openai-responses:', 'openai-responses-overnight:'),
                'cli': ('codex-cli:', 'claude-cli:', 'devin-cli:')}
    if spec['panel_kind'] not in prefixes:
        raise ValueError('unsupported panel transport')
    if spec['stage'] == 'offline' and spec['panel_kind'] != 'offline':
        raise ValueError('offline preparation requires a synthetic offline panel')
    common = spec['common']
    _fields(common, COMMON_FIELDS | ({'extractor_settings', 'effective_settings', 'documents_hash'} if version2 else set()),
            'common comparison inputs')
    if version2:
        _hash(common['documents_hash'], 'common full document records')
        _settings(common['extractor_settings'])
        if not isinstance(common['effective_settings'], dict):
            raise ValueError('explicit effective backend settings required')
    _items(common['items'])
    _settings(common['settings'])
    for key in ('items_hash', 'task_context_hash', 'allowed_source_manifest_hash',
                'renderer_implementation_hash', 'consumer_prompt_sha256'):
        _hash(common[key], key)
    for key in ('researcher_id', 'consumer_prompt_version'):
        _text(common[key], key)
    if type(common['personalization_cap']) is not int or common['personalization_cap'] not in (512, 2048, 8192):
        raise ValueError('unsupported personalization byte cap')
    if (isinstance(common['context_cap'], bool) or not isinstance(common['context_cap'], int)
            or common['context_cap'] < common['personalization_cap']):
        raise ValueError('context cap must accommodate the common personalization cap')
    if common['cap_unit'] != TOKEN_COUNT_METHOD or common['truncation_rule'] != 'reject-no-drop':
        raise ValueError('explicit conservative byte cap and no-drop rule required')
    if common['outcome_panel'] not in ('fidelity', 'utility'):
        raise ValueError('fidelity and utility must be separate outcome panels')
    if not isinstance(spec['models'], list) or [m.get('level') for m in spec['models']] != list(LEVELS):
        raise ValueError('declare S/M/L in order, including unavailable arms')
    differences, identities = {}, set()
    for model in spec['models']:
        if model.get('status') == 'unavailable':
            _fields(model, {'level', 'status', 'reason'}, 'unavailable model')
            _text(model['reason'], 'planned unavailability reason')
            continue
        _fields(model, {'level', 'status', 'identity', 'settings', 'adapter_sha256',
                        'verification_sha256', 'model_revision'} |
                ({'extractor_settings', 'effective_settings'} if version2 else set()), 'model')
        if model['status'] != 'available':
            raise ValueError('model availability must be declared before freezing')
        identity = model['identity']
        if not isinstance(identity, dict) or not {'class', 'label', 'model', 'endpoint'} <= set(identity):
            raise ValueError('exact backend identity and version required')
        for key in ('class', 'label', 'model'):
            _text(identity[key], 'backend ' + key)
        _text(model['model_revision'], 'model revision or explicit provider-unversioned status')
        if not identity['label'].startswith(prefixes[spec['panel_kind']]):
            raise ValueError('mixed or undeclared panel transport')
        if digest(identity) in identities:
            raise ValueError('panel levels require distinct backend identities')
        identities.add(digest(identity))
        _hash(model['adapter_sha256'], 'backend adapter')
        _hash(model['verification_sha256'], 'backend verification evidence')
        _settings(model['settings'])
        enforced = identity.get('enforced_settings', {})
        effective = model['effective_settings'] if version2 else model['settings']
        if not isinstance(enforced, dict) or not isinstance(effective, dict) or any(
                key not in effective or effective[key] != value for key, value in enforced.items()):
            raise ValueError('declared settings must include the actual enforced backend settings')
        if version2:
            _settings(model['extractor_settings'])
            if model['effective_settings'] != enforced:
                raise ValueError('effective settings must exactly match backend-enforced settings')
        setting_groups = ('settings', 'extractor_settings', 'effective_settings') if version2 else ('settings',)
        for group in setting_groups:
            for key in set(common[group]) | set(model[group]):
                expected, actual = common[group].get(key), model[group].get(key)
                if expected != actual or (key in common[group]) != (key in model[group]):
                    field = group + '.' + key if version2 else key
                    differences[(model['level'], field)] = (expected, actual)
    if not identities:
        raise ValueError('at least one model must be available')
    declared = {}
    if not isinstance(spec['deviations'], list):
        raise ValueError('settings deviations must be a list')
    for deviation in spec['deviations']:
        _fields(deviation, {'level', 'field', 'expected', 'actual', 'reason'}, 'deviation')
        key = (deviation['level'], deviation['field'])
        if key in declared:
            raise ValueError('duplicate settings deviation')
        _text(deviation['reason'], 'settings deviation reason')
        declared[key] = (deviation['expected'], deviation['actual'])
    if declared != differences:
        raise ValueError('settings deviation must describe every actual difference exactly')
    if not isinstance(spec['methods'], list) or len(spec['methods']) not in (2, 3):
        raise ValueError('declare two or three selected methods; no selection occurs here')
    methods = set()
    for method in spec['methods']:
        _fields(method, METHOD_FIELDS, 'method')
        _text(method['method_id'], 'method ID')
        if method['method_id'] in methods or '/' in method['method_id']:
            raise ValueError('duplicate or invalid method ID')
        methods.add(method['method_id'])
        expected_levels = {m['level'] for m in spec['models'] if m['status'] == 'available'}
        if not isinstance(method['config_hashes'], dict) or set(method['config_hashes']) != expected_levels:
            raise ValueError('per-level candidate profile config hashes required')
        for value in method['config_hashes'].values():
            _hash(value, 'candidate profile config')
        for key in ('method_implementation_hash', 'profile_prompt_sha256'):
            _hash(method[key], key)
        _text(method['profile_prompt_version'], 'profile prompt version')
    if spec['primary_method_id'] not in methods:
        raise ValueError('primary method must be declared by coordinator')
    _fields(spec['fixed_profile'], {'method_id', 'extractor_level'}, 'fixed profile reference')
    if (spec['fixed_profile']['method_id'] not in methods or
            spec['fixed_profile']['extractor_level'] not in LEVELS):
        raise ValueError('fixed profile must name a selected method and extractor')
    if not isinstance(spec['controls'], list) or len(spec['controls']) not in (2, 4):
        raise ValueError('declare the historical matched pair or all four mandatory controls')
    kinds = set()
    for control in spec['controls']:
        _fields(control, {'method_id', 'kind', 'implementation_sha256', 'config_hash'}, 'control')
        _text(control['method_id'], 'control method ID')
        if control['method_id'] in methods or '/' in control['method_id']:
            raise ValueError('duplicate or invalid control ID')
        methods.add(control['method_id'])
        kinds.add(control['kind'])
        _hash(control['implementation_sha256'], 'control implementation')
        _hash(control['config_hash'], 'control config')
    four_controls = {('no_profile', 'no_profile'), ('raw_evidence', 'raw_evidence'),
                     ('lexical_retrieval', 'retrieval'), ('semantic_retrieval', 'retrieval')}
    valid_controls = ({(c['method_id'], c['kind']) for c in spec['controls']} == four_controls
                      if len(spec['controls']) == 4 else kinds in ({'no_profile', 'raw_evidence'}, {'no_profile', 'retrieval'}))
    if not valid_controls:
        raise ValueError('required matched controls missing')
    diagnostic = spec['diagnostic']
    _fields(diagnostic, DIAGNOSTIC_FIELDS | ({'raw_control_config_hash', 'raw_implementation_sha256', 'documents_hash'}
            if version2 else set()), 'diagnostic')
    if version2:
        for field in ('raw_control_config_hash', 'raw_implementation_sha256', 'documents_hash'):
            _hash(diagnostic[field], field)
    _items(diagnostic['items'])
    for key in DIAGNOSTIC_FIELDS - {'items', 'label_tier', 'profile_conditioning'}:
        _hash(diagnostic[key], 'diagnostic ' + key)
    if diagnostic['label_tier'] != 'documented-judgment' or diagnostic['profile_conditioning'] is not False:
        raise ValueError('diagnostic requires independent recorded judgments and no candidate profile')


def validate_consumer_binding(binding, consumer_identity):
    """Check a declared binding without loading or weakening existing UserModel guards."""
    if binding.get('kind') == 'backend_bound':
        if binding.get('backend') != consumer_identity:
            raise ValueError('backend-bound model cannot change consumer; refit or use neutral content')
    elif binding.get('kind') == 'neutral_profile':
        if binding.get('weights_status') != 'unavailable' or binding.get('confidence_status') != 'uncalibrated':
            raise ValueError('neutral transfer cannot carry learned weights or calibration')
    else:
        raise ValueError('unsupported profile binding; legacy compatibility is unverified')


def _validate_pins(spec, pins):
    models = {m['level']: m for m in spec['models']}
    methods = {m['method_id']: m for m in spec['methods']}
    expected = {(method, level) for method in methods for level, model in models.items()
                if model['status'] == 'available'}
    actual, replicates = set(), {}
    version2 = spec['schema_version'] == 'overnight-scaling-design-v2'
    for pin in pins:
        unavailable = pin.get('kind') == 'unavailable_profile'
        _fields(pin, UNAVAILABLE_PIN_FIELDS if unavailable else
                PIN_FIELDS | ({'documents_hash'} if version2 else set()), 'profile pin')
        key = (pin['method_id'], pin['extractor_level'])
        if key not in expected or key in actual:
            raise ValueError('duplicate, unexpected or unavailable profile pin')
        actual.add(key)
        if unavailable:
            _text(pin['reason'], 'planned profile unavailability')
            _hash(pin['evidence_sha256'], 'unavailable profile evidence')
            continue
        replicate = pin['replicate_id']
        if isinstance(replicate, bool) or not isinstance(replicate, (str, int)):
            raise ValueError('explicit extraction replicate required')
        if key[0] in replicates and replicates[key[0]] != replicate:
            raise ValueError('extraction replicate must be matched across levels')
        replicates[key[0]] = replicate
        model, method, common = models[key[1]], methods[key[0]], spec['common']
        if pin['kind'] != 'neutral_profile':
            raise ValueError('consumer-only study requires a neutral profile')
        validate_consumer_binding(pin, model['identity'])
        if pin['config_id'] != method['config_hashes'][key[1]]:
            raise ValueError('profile configuration differs from selected candidate config hash')
        if (type(pin['token_count']) is not int or not 0 < pin['token_count'] <= common['personalization_cap']
                or pin['token_count_method'] != TOKEN_COUNT_METHOD):
            raise ValueError('candidate profile requires nonempty content within byte cap')
        for field in ('profile_id', 'content_sha256', 'config_id', 'allowed_source_manifest_hash',
                      'method_implementation_hash', 'renderer_implementation_hash', 'prompt_sha256'):
            _hash(pin[field], 'profile ' + field)
        expected_settings = model['extractor_settings'] if version2 else model['settings']
        if version2:
            _hash(pin['documents_hash'], 'full profile documents')
            if pin['documents_hash'] != common['documents_hash']:
                raise ValueError('profile full document records differ from common source pin')
            if pin['code_sha'] != spec['code_sha']:
                raise ValueError('profile runtime code pin differs; no implicit migration')
        if pin['extractor'] != model['identity'] or pin['extractor_settings'] != expected_settings:
            raise ValueError('profile extractor provenance does not match panel')
        for field in ('allowed_source_manifest_hash', 'personalization_cap', 'researcher_id',
                      'renderer_implementation_hash'):
            if pin[field] != common[field]:
                raise ValueError('profile/common mismatch: ' + field)
        for field, source in (('method_implementation_hash', 'method_implementation_hash'),
                              ('prompt_version', 'profile_prompt_version'),
                              ('prompt_sha256', 'profile_prompt_sha256')):
            if pin[field] != method[source]:
                raise ValueError('profile/method pin mismatch: ' + field)
    if actual != expected:
        raise ValueError('all available method/extractor profiles must be pinned')


def _assemble(spec, pins):
    _validate_design(spec)
    _validate_pins(spec, pins)
    models = {m['level']: m for m in spec['models']}
    profiles = {(p['method_id'], p['extractor_level']): p for p in pins}
    methods = {m['method_id']: m for m in spec['methods']}
    cells, arms = {}, []

    def add(arm_id, study, estimand, consumer_level, method=None, extractor_level=None, control=None):
        required = {consumer_level}
        if extractor_level:
            required.add(extractor_level)
        absent = [level for level in LEVELS if level in required and models[level]['status'] == 'unavailable']
        arm = {'arm_id': arm_id, 'study': study, 'estimand': estimand,
               'consumer_level': consumer_level, 'extractor_level': extractor_level,
               'method_id': method or (control['method_id'] if control else None)}
        unavailable_profile = profiles.get((method, extractor_level), {}) if method else {}
        if absent:
            arm.update(status='planned-unavailable', cell_id=None,
                       reason='; '.join(level + ': ' + models[level]['reason'] for level in absent))
        elif unavailable_profile.get('kind') == 'unavailable_profile':
            arm.update(status='planned-unavailable', cell_id=None, reason=unavailable_profile['reason'])
        else:
            common = _copy(spec['common'])
            if method:
                conditioning = _copy(profiles[(method, extractor_level)])
                conditioning['candidate_config_hash'] = methods[method]['config_hashes'][extractor_level]
            elif control:
                conditioning = _copy(control)
            else:
                diagnostic = spec['diagnostic']
                common.update(items=diagnostic['items'], items_hash=diagnostic['items_hash'],
                              task_context_hash=diagnostic['task_context_hash'],
                              allowed_source_manifest_hash=diagnostic['raw_evidence_hash'],
                              outcome_panel='fidelity')
                conditioning = {k: v for k, v in diagnostic.items()
                                if k not in ('items', 'items_hash', 'task_context_hash')}
                conditioning['kind'] = 'archival_raw_evidence'
                if spec['schema_version'] == 'overnight-scaling-design-v2':
                    common['documents_hash'] = diagnostic['documents_hash']
            consumer = {key: models[consumer_level][key]
                        for key in ('identity', 'settings', 'adapter_sha256', 'verification_sha256', 'model_revision')}
            if spec['schema_version'] == 'overnight-scaling-design-v2':
                consumer['effective_settings'] = models[consumer_level]['effective_settings']
            cell = {'campaign_id': spec['campaign_id'], 'stage': spec['stage'],
                    'contract_sha256': spec['contract_sha256'], 'code_sha': spec['code_sha'],
                    'panel_id': spec['panel_id'], 'panel_kind': spec['panel_kind'],
                    'common': common, 'conditioning': conditioning, 'consumer': consumer,
                    'consumer_instance_policy': 'fresh-adapter-no-learned-state-transfer'}
            cell_id = digest(cell)
            cells[cell_id] = dict(cell, cell_id=cell_id)
            arm.update(status='planned', cell_id=cell_id, reason=None)
        arms.append(arm)

    for method in spec['methods']:
        for level in LEVELS:
            add('A/' + method['method_id'] + '/' + level, 'A', 'joint-extraction-consumer',
                level, method['method_id'], level)
    for control in spec['controls']:
        for level in LEVELS:
            add('A/' + control['method_id'] + '/' + level, 'A', 'matched-control', level, control=control)
    fixed = spec['fixed_profile']
    for level in LEVELS:
        add('B/' + level, 'B', 'fixed-profile-consumer', level, fixed['method_id'], fixed['extractor_level'])
    for extractor_level in ('S', 'L'):
        for consumer_level in ('S', 'L'):
            add('C/' + extractor_level + '/' + consumer_level, 'C', 'extractor-consumer-cross',
                consumer_level, spec['primary_method_id'], extractor_level)
    for level in LEVELS:
        add('D/' + level, 'D', 'raw-evidence-judgment-inference', level)
    body = {'schema_version': 'overnight-scaling-manifest-v1', 'design': spec, 'profile_pins': pins,
            'authorization': 'none-manifest-only', 'arms': arms, 'cells': list(cells.values()),
            'deviations': spec['deviations']}
    body['manifest_sha256'] = manifest_hash(body)
    return body


def manifest_hash(manifest):
    return digest({key: value for key, value in manifest.items() if key != 'manifest_sha256'})


def build_manifest(spec, profiles):
    """Build a fully pinned plan from approved neutral artifacts, without model calls.

    Profile records contain method_id, extractor_level and profile (artifact dict).
    Returned manifest omits all profile text. Finalists and model verification are
    supplied by their owners; synthetic preparation does not select or verify them.
    """
    spec = _copy(spec)
    _validate_design(spec)
    pins = []
    for record in profiles:
        if record.get('status') == 'planned-unavailable':
            _fields(record, {'method_id', 'extractor_level', 'status', 'reason', 'evidence_sha256'},
                    'unavailable profile record')
            pins.append(dict({k: v for k, v in record.items() if k != 'status'}, kind='unavailable_profile'))
            continue
        _fields(record, {'method_id', 'extractor_level', 'profile'}, 'profile record')
        profile = ProfileArtifact.from_dict(record['profile']).to_dict()
        if (profile['status'] != 'complete' or profile.get('intentional_empty')
                or not render_content(profile['content'])):
            raise ValueError('candidate profile must be complete and nonempty; failures stay unavailable')
        if profile['method_id'] != record['method_id']:
            raise ValueError('profile record method mismatch')
        pin = {key: profile[key] for key in PIN_FIELDS - {'kind', 'extractor_level'}}
        if spec['schema_version'] == 'overnight-scaling-design-v2':
            if 'documents_hash' not in profile:
                raise ValueError('v2 profile requires full documents hash')
            pin['documents_hash'] = profile['documents_hash']
        pin.update(kind='neutral_profile', extractor_level=record['extractor_level'])
        pins.append(pin)
    pins.sort(key=lambda p: (p['method_id'], LEVELS.index(p['extractor_level'])))
    return _assemble(spec, pins)


def validate_manifest(manifest, *, expected_manifest_hash=None):
    """Reconstruct all arms/cells; compare with an independently retained freeze hash."""
    if manifest.get('schema_version') != 'overnight-scaling-manifest-v1':
        raise ValueError('unsupported scaling manifest schema')
    actual = manifest_hash(manifest)
    if manifest.get('manifest_sha256') != actual:
        raise ValueError('scaling manifest hash mismatch')
    if expected_manifest_hash is not None and expected_manifest_hash != actual:
        raise ValueError('manifest changed after external freeze')
    reconstructed = _assemble(_copy(manifest['design']), _copy(manifest['profile_pins']))
    if manifest != reconstructed:
        raise ValueError('undeclared, missing or edited scaling arm/cell')
    return actual


def result_inventory(manifest, results, *, expected_manifest_hash):
    """Join evaluator-supplied results, preserving missing/unavailable/failed arms.

    This does not score labels. Confirmation results and the returned inventory
    must stay inside evaluator-only storage. Every cell result is unique; aliases
    reference it without counting its cost or calls a second time.
    """
    validate_manifest(manifest, expected_manifest_hash=expected_manifest_hash)
    cells = {cell['cell_id']: cell for cell in manifest['cells']}
    found = {}
    for result in results:
        _fields(result, {'cell_id', 'status', 'reason', 'items', 'usage'}, 'cell result')
        cell_id = result['cell_id']
        if cell_id not in cells or cell_id in found:
            raise ValueError('unknown or duplicate result cell')
        if result['status'] not in ('complete', 'partial', 'failed', 'unavailable', 'empty', 'invalid', 'abstained', 'unsupported'):
            raise ValueError('invalid execution result status')
        if result['status'] != 'complete':
            _text(result['reason'], 'execution failure reason')
        expected_items = cells[cell_id]['common']['items']
        rows = result['items']
        if not isinstance(rows, list):
            raise ValueError('result items must be a list')
        seen = set()
        for row in rows:
            _fields(row, {'item_id', 'option_order_id', 'context_sha256', 'options_sha256',
                          'status', 'score'}, 'result item')
            matching = [i for i in expected_items if i['item_id'] == row['item_id']]
            if (not matching or row['item_id'] in seen or
                    any(row[key] != matching[0][key] for key in matching[0])):
                raise ValueError('result item/order/context differs from frozen inputs')
            seen.add(row['item_id'])
            if row['status'] not in ('complete', 'failed', 'unavailable', 'abstained', 'invalid', 'empty', 'unsupported'):
                raise ValueError('invalid item status')
            score = row['score']
            if row['status'] == 'complete':
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
                    raise ValueError('complete evaluator score must be finite')
            elif score is not None:
                raise ValueError('failed item cannot silently receive a successful score')
        if result['status'] == 'complete' and (len(rows) != len(expected_items) or
                any(r['status'] != 'complete' for r in rows)):
            raise ValueError('complete cell omitted or failed expected items')
        found[cell_id] = _copy(result)
    return [dict(_copy(arm), status=(found[arm['cell_id']]['status'] if arm['cell_id'] in found else
                                   'missing-result' if arm['status'] == 'planned' else arm['status']),
                 result=found.get(arm['cell_id'])) for arm in manifest['arms']]


def summarize_results(manifest, results, *, expected_manifest_hash):
    """Describe supplied scores without inferring labels, winners or capability.

    Means cover explicitly completed rows only. Every unpaired, failed and missing
    row remains visible; no failure-to-zero policy is silently invented. A valid
    uncertainty interval needs the evaluator's independent-group policy, which is
    not supplied by this manifest, so interval uncertainty remains unmeasured.
    """
    inventory = result_inventory(manifest, results, expected_manifest_hash=expected_manifest_hash)
    cells = {cell['cell_id']: cell for cell in manifest['cells']}
    by_cell = {result['cell_id']: result for result in results}
    by_arm = {arm['arm_id']: arm for arm in inventory}
    controls = manifest['design']['controls']
    baseline = next((c['method_id'] for c in controls if c['kind'] == 'raw_evidence'), None)
    if baseline is None:  # Historical two-control manifests may use one retrieval baseline.
        baseline = next(c['method_id'] for c in controls if c['kind'] == 'retrieval')

    def item_rows(arm):
        expected = (cells[arm['cell_id']]['common']['items'] if arm['cell_id'] else
                    manifest['design']['diagnostic']['items'] if arm['study'] == 'D' else
                    manifest['design']['common']['items'])
        actual = {row['item_id']: row for row in (arm['result']['items'] if arm['result'] else [])}
        return [dict(item, status=actual[item['item_id']]['status'], score=actual[item['item_id']]['score'])
                if item['item_id'] in actual else dict(item, status=(
                    'planned-unavailable' if arm['status'] == 'planned-unavailable' else 'missing-result'), score=None)
                for item in expected]

    summaries = []
    for arm in inventory:
        rows = item_rows(arm)
        scores = [row['score'] for row in rows if row['status'] == 'complete']
        absolute = {'items': rows, 'expected_count': len(rows), 'complete_count': len(scores),
                    'failed_count': sum(row['status'] not in ('complete', 'missing-result', 'planned-unavailable') for row in rows),
                    'planned_unavailable_count': sum(row['status'] == 'planned-unavailable' for row in rows),
                    'missing_count': sum(row['status'] == 'missing-result' for row in rows),
                    'available_case_mean': sum(scores) / len(scores) if scores else None}
        gain = None
        if arm['estimand'] in ('joint-extraction-consumer', 'fixed-profile-consumer', 'extractor-consumer-cross'):
            matched = by_arm['A/' + baseline + '/' + arm['consumer_level']]
            baseline_rows = {row['item_id']: row for row in item_rows(matched)}
            pairs = []
            for row in rows:
                base = baseline_rows[row['item_id']]
                paired = row['status'] == base['status'] == 'complete'
                pairs.append({'item_id': row['item_id'], 'option_order_id': row['option_order_id'],
                              'candidate_status': row['status'], 'baseline_status': base['status'],
                              'difference': row['score'] - base['score'] if paired else None})
            differences = [p['difference'] for p in pairs if p['difference'] is not None]
            gain = {'baseline_arm_id': matched['arm_id'], 'items': pairs,
                    'paired_count': len(differences), 'unpaired_count': len(rows) - len(differences),
                    'paired_mean': sum(differences) / len(differences) if differences else None}
        summaries.append({'arm_id': arm['arm_id'], 'cell_id': arm['cell_id'], 'status': arm['status'],
                          'reason': arm['result']['reason'] if arm['result'] else arm['reason'],
                          'outcome_panel': 'fidelity' if arm['study'] == 'D' else
                          manifest['design']['common']['outcome_panel'], 'estimand': arm['estimand'],
                          'absolute': absolute, 'personalization_gain': gain,
                          'uncertainty': {'status': 'not-estimated',
                                          'reason': 'evaluator independent-group interval policy not supplied'}})
    unique_results = []
    attempted, costs, cost_statuses = 0, [], []
    for cell_id in cells:
        result = by_cell.get(cell_id)
        unique_results.append({'cell_id': cell_id, 'status': result['status'] if result else 'missing-result',
                               'result': _copy(result) if result else None})
        if result:
            usage = result['usage']
            if not isinstance(usage, dict) or type(usage.get('attempted_calls')) is not int or usage['attempted_calls'] < 0:
                raise ValueError('result usage requires nonnegative attempted calls')
            attempted += usage['attempted_calls']
            cost = usage.get('reported_api_usd')
            if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float))
                                     or not math.isfinite(cost) or cost < 0):
                raise ValueError('invalid reported API cost')
            if usage.get('cost_status') not in ('offline', 'unavailable', 'measured', 'estimated'):
                raise ValueError('explicit cost status required')
            costs.append(cost)
            cost_statuses.append(usage['cost_status'])
    known = (bool(costs) and all(cost is not None for cost in costs) and
             all(status in ('measured', 'estimated') for status in cost_statuses))
    return {'schema_version': 'overnight-scaling-summary-v1',
            'manifest_sha256': manifest['manifest_sha256'], 'arms': summaries, 'cells': unique_results,
            'usage': {'attempted_calls': attempted, 'observed_cells': len(results),
                      'missing_cells': len(cells) - len(results),
                      'reported_api_usd': sum(costs) if known else None,
                      'known_reported_api_usd': sum(c for c in costs if c is not None),
                      'cost_status': ('measured' if all(s == 'measured' for s in cost_statuses)
                                      else 'estimated') if known else 'unavailable'},
            'interpretation': 'descriptive-only; no parameter-count law or independent capability ordering'}


def grouped_paired_report(mapping, jobs, score_packets, comparisons, *, expected_mapping_hash,
                          expected_jobs_hash, expected_scores_hash, expected_analysis_hash, rule):
    """Report evaluator-scored fidelity without treating option reversals as samples.

    The evaluator supplies opaque semantic/source-group mappings and scored rows.
    Missing/invalid predictions already graded by that owner contribute zero to
    accuracy, as in score_predictions. Missing *score reports* remain unmeasured.
    Utility requires its downstream owner's separate metric/failure contract.
    """
    import random
    if (digest(mapping) != expected_mapping_hash or digest(jobs) != expected_jobs_hash
            or digest(score_packets) != expected_scores_hash
            or digest({'comparisons': comparisons, 'rule': rule}) != expected_analysis_hash):
        raise ValueError('evaluator mapping, job bindings or scored packets changed')
    _fields(mapping, {'schema_version', 'outcome_panel', 'target_bundle_sha256', 'items'}, 'evaluator mapping')
    if mapping['schema_version'] != 'scaling-evaluator-map-v1' or mapping['outcome_panel'] != 'fidelity':
        raise ValueError('fidelity schema only; utility requires downstream scored-row contract')
    _hash(mapping['target_bundle_sha256'], 'evaluator target bundle')
    _fields(rule, {'schema_version', 'seed', 'samples', 'confidence', 'minimum_groups', 'unit', 'estimand'}, 'bootstrap rule')
    if (rule['schema_version'] != 'source-group-bootstrap-v1' or type(rule['seed']) is not int
            or type(rule['samples']) is not int or not 100 <= rule['samples'] <= 100_000
            or rule['confidence'] != 0.95 or type(rule['minimum_groups']) is not int
            or rule['minimum_groups'] < 2 or rule['unit'] != 'source_group'
            or rule['estimand'] != 'equal-semantic-item-mean'):
        raise ValueError('declare reproducible source-group bootstrap with at least two groups')
    indexed, semantics = {}, {}
    if not isinstance(mapping['items'], list) or not mapping['items']:
        raise ValueError('nonempty evaluator mapping required')
    for item in mapping['items']:
        _fields(item, {'item_id', 'semantic_item_id', 'researcher_id', 'group_id', 'tier', 'schedule_hash'}, 'mapped item')
        for field in ('item_id', 'semantic_item_id', 'researcher_id', 'group_id'):
            _text(item[field], field)
        _hash(item['schedule_hash'], 'evaluator item schedule')
        if item['tier'] not in ('A', 'B') or item['item_id'] in indexed:
            raise ValueError('duplicate item or non-source-backed tier')
        indexed[item['item_id']] = item
        semantic = semantics.setdefault(item['semantic_item_id'], [])
        if semantic and any(semantic[0][k] != item[k] for k in ('researcher_id', 'group_id', 'tier')):
            raise ValueError('semantic judgment crosses researcher, source group or evidence tier')
        semantic.append(item)
    job_index, cell_items = {}, {}
    for job in jobs:
        _fields(job, {'job_id', 'manifest_sha256', 'item_ids', 'target_bundle_sha256',
                      'parent_target_bundle_sha256'} | ({'cell_ids'} if 'cell_ids' in job else {'cell_id'}), 'scored job binding')
        aliases = job['cell_ids'] if 'cell_ids' in job else [job['cell_id']]
        if not isinstance(aliases, list) or not aliases or any(not isinstance(c, str) or not c for c in aliases) or len(set(aliases)) != len(aliases):
            raise ValueError('explicit unique execution cell aliases required')
        _hash(job['job_id'], 'job ID')
        _hash(job['manifest_sha256'], 'job manifest')
        _hash(job['target_bundle_sha256'], 'job target bundle')
        if job['parent_target_bundle_sha256'] != mapping['target_bundle_sha256']:
            raise ValueError('scored job parent target bundle differs from evaluator mapping')
        ids = job['item_ids']
        if (job['job_id'] in job_index or not isinstance(ids, list) or not ids
                or len(set(ids)) != len(ids) or any(i not in indexed for i in ids)):
            raise ValueError('duplicate job or invalid scored job subset')
        job_index[job['job_id']] = dict(job, cell_ids=aliases)
        for cell_id in aliases:
            seen = cell_items.setdefault(cell_id, set())
            if seen & set(ids):
                raise ValueError('cell repeats a scheduled item across jobs')
            seen.update(ids)
    if not cell_items or any(ids != set(indexed) for ids in cell_items.values()):
        raise ValueError('every cell must bind the identical full mapped item set')
    scored = {cell: {} for cell in cell_items}
    seen_jobs = set()
    statuses = {'complete', 'ok', 'failed', 'unavailable', 'unsupported', 'empty', 'invalid', 'abstained', 'missing'}
    allowed_report = {'job_id', 'manifest_sha256', 'target_bundle_sha256', 'per_item',
                      'n_items', 'accuracy', 'failures', 'n_groups', 'probability_coverage',
                      'brier_valid_only', 'by_researcher', 'by_tier', 'missing_item_ids'}
    for packet in score_packets:
        _fields(packet, {'job_id', 'report', 'status_by_item'}, 'evaluator scored packet')
        job = job_index.get(packet['job_id'])
        if job is None or packet['job_id'] in seen_jobs:
            raise ValueError('unknown or duplicate scored job')
        seen_jobs.add(packet['job_id'])
        report = packet['report']
        if (not isinstance(report, dict) or set(report) - allowed_report
                or any(report.get(k) != value for k, value in {
                    'job_id': job['job_id'], 'manifest_sha256': job['manifest_sha256'],
                    'target_bundle_sha256': job['target_bundle_sha256']}.items())):
            raise ValueError('evaluator report job/manifest/target binding mismatch')
        if not isinstance(report.get('per_item'), list) or not isinstance(packet['status_by_item'], dict):
            raise ValueError('scored rows and explicit prediction statuses required')
        if set(packet['status_by_item']) != set(job['item_ids']):
            raise ValueError('prediction statuses differ from frozen job items')
        seen_items = set()
        for row in report['per_item']:
            _fields(row, {'item_id', 'researcher_id', 'group_id', 'tier', 'correct', 'failure', 'brier', 'schedule_hash'}, 'scored item')
            item = indexed.get(row['item_id'])
            if (item is None or row['item_id'] not in job['item_ids'] or row['item_id'] in seen_items
                    or any(row[k] != item[k] for k in ('researcher_id', 'group_id', 'tier', 'schedule_hash'))):
                raise ValueError('scored item mapping or schedule mismatch')
            seen_items.add(row['item_id'])
            status = packet['status_by_item'][row['item_id']]
            if (type(row['correct']) is not bool or type(row['failure']) is not bool or status not in statuses
                    or (status not in ('complete', 'ok') and not row['failure'])
                    or (row['failure'] and (row['correct'] or row['brier'] is not None))):
                raise ValueError('scored row contradicts evaluator failure semantics')
            brier = row['brier']
            if brier is not None and (type(brier) not in (int, float) or not math.isfinite(brier) or not 0 <= brier <= 1):
                raise ValueError('invalid evaluator Brier score')
            for cell_id in job['cell_ids']:
                scored[cell_id][row['item_id']] = dict(row, prediction_status=status)
        if seen_items != set(job['item_ids']):
            raise ValueError('evaluator report omitted a bound item; missing predictions require explicit failure rows')

    cells = {}
    for cell, rows in scored.items():
        collapsed = []
        for semantic_id, variants in sorted(semantics.items()):
            present = [rows[i['item_id']] for i in variants if i['item_id'] in rows]
            complete = len(present) == len(variants)
            valid_brier = [r['brier'] for r in present if r['brier'] is not None]
            collapsed.append({'semantic_item_id': semantic_id, 'researcher_id': variants[0]['researcher_id'],
                'group_id': variants[0]['group_id'], 'tier': variants[0]['tier'],
                'ordered_item_count': len(variants), 'scored_ordered_count': len(present),
                'failed_ordered_count': sum(r['failure'] for r in present),
                'missing_ordered_count': len(variants) - len(present),
                'accuracy': sum(int(r['correct']) for r in present) / len(variants) if complete else None,
                'valid_brier_count': len(valid_brier),
                'brier_valid_only': sum(valid_brier) / len(valid_brier) if valid_brier else None,
                'status_by_item': {i['item_id']: rows[i['item_id']]['prediction_status'] if i['item_id'] in rows
                                   else 'missing-score-report' for i in variants}})
        strata = []
        for researcher, tier in sorted({(i['researcher_id'], i['tier']) for i in collapsed}):
            subset = [i for i in collapsed if (i['researcher_id'], i['tier']) == (researcher, tier)]
            available = [i['accuracy'] for i in subset if i['accuracy'] is not None]
            strata.append({'researcher_id': researcher, 'tier': tier, 'semantic_item_count': len(subset),
                'source_group_count': len({i['group_id'] for i in subset}),
                'ordered_item_count': sum(i['ordered_item_count'] for i in subset),
                'failed_ordered_count': sum(i['failed_ordered_count'] for i in subset),
                'missing_ordered_count': sum(i['missing_ordered_count'] for i in subset),
                'accuracy': sum(available) / len(subset) if len(available) == len(subset) else None,
                'observed_semantic_accuracy': sum(available) / len(available) if available else None,
                'scored_semantic_count': len(available)})
        cells[cell] = {'semantic_items': collapsed, 'strata': strata}
    paired, comparison_ids = [], set()
    for comparison in comparisons:
        _fields(comparison, {'comparison_id', 'candidate_cell_id', 'baseline_cell_id'}, 'paired comparison')
        _text(comparison['comparison_id'], 'comparison ID')
        if comparison['comparison_id'] in comparison_ids:
            raise ValueError('duplicate comparison ID')
        comparison_ids.add(comparison['comparison_id'])
        if any(comparison[k] not in cells for k in ('candidate_cell_id', 'baseline_cell_id')):
            raise ValueError('comparison references undeclared cell')
        left = cells[comparison['candidate_cell_id']]['semantic_items']
        right = {i['semantic_item_id']: i for i in cells[comparison['baseline_cell_id']]['semantic_items']}
        strata = []
        for researcher, tier in sorted({(i['researcher_id'], i['tier']) for i in left}):
            subset = [i for i in left if (i['researcher_id'], i['tier']) == (researcher, tier)]
            differences, groups = [], {}
            for item in subset:
                base = right[item['semantic_item_id']]
                value = item['accuracy'] - base['accuracy'] if item['accuracy'] is not None and base['accuracy'] is not None else None
                differences.append({'semantic_item_id': item['semantic_item_id'], 'group_id': item['group_id'],
                                    'difference': value})
                if value is not None:
                    groups.setdefault(item['group_id'], []).append(value)
            values = [r['difference'] for r in differences if r['difference'] is not None]
            complete = len(values) == len(subset)
            interval, status = None, 'incomplete-score-coverage'
            if complete and len(groups) < rule['minimum_groups']:
                status = 'insufficient-independent-groups'
            elif complete:
                rng, names = random.Random(rule['seed']), sorted(groups)
                draws = []
                for _ in range(rule['samples']):
                    sampled = [groups[rng.choice(names)] for _ in names]
                    draws.append(sum(map(sum, sampled)) / sum(map(len, sampled)))
                draws.sort()
                interval = [draws[int(0.025 * len(draws))], draws[min(len(draws) - 1, int(0.975 * len(draws)))]]
                status = 'descriptive-source-group-bootstrap'
            strata.append({'researcher_id': researcher, 'tier': tier, 'semantic_item_count': len(subset),
                'ordered_item_count': sum(i['ordered_item_count'] for i in subset),
                'source_group_count': len({i['group_id'] for i in subset}), 'paired_group_count': len(groups),
                'paired_semantic_count': len(values), 'unpaired_semantic_count': len(subset) - len(values),
                'difference': sum(values) / len(values) if complete else None,
                'available_paired_difference': sum(values) / len(values) if values else None,
                'items': differences, 'ci95': interval, 'uncertainty_status': status})
        paired.append(dict(comparison, strata=strata))
    return {'schema_version': 'scaling-grouped-fidelity-report-v1', 'outcome_panel': 'fidelity',
            'mapping_sha256': expected_mapping_hash, 'jobs_sha256': expected_jobs_hash,
            'scores_sha256': expected_scores_hash, 'analysis_sha256': expected_analysis_hash, 'rule': _copy(rule), 'cells': cells, 'comparisons': paired,
            'unique_scored_jobs': len(seen_jobs), 'logical_cell_count': len(cells),
            'interpretation': 'Case-specific descriptive evidence; source groups are resampled within researcher and tier. '
                              'Two researchers do not define a researcher population; no population interval is reported.'}


PEER_RELEASE_SCHEMA = 'released-development-v2-p7-peers-v1'
PEER_BINDINGS = ('approved_peer_sources', 'peer_policy', 'parent_releases')


def _peer_release_proof(release, parent_json, method):
    """Validate exact fit-release bytes supplied by the coordinator, without I/O."""
    from pathlib import Path
    from .contracts import source_manifest, validate_documents, sha256_text
    if method != 'P7' or release.get('approved_peer_sources') is not True:
        raise ValueError('peer release is approved for P7 only')
    policy = release.get('peer_policy')
    _fields(policy, {'allowed_method_id', 'purpose', 'target_researcher_id', 'peer_researcher_ids',
                     'no_heldout_sources'}, 'peer policy')
    if (policy['allowed_method_id'] != 'P7' or policy['purpose'] != 'contrastive peer fitting'
            or policy['target_researcher_id'] != release['researcher_id'] or policy['no_heldout_sources'] is not True):
        raise ValueError('peer policy differs from approved fitting contract')
    peers = policy['peer_researcher_ids']
    if (not isinstance(peers, list) or not peers or any(not isinstance(p, str) or not p for p in peers)
            or peers != sorted(set(peers)) or release['researcher_id'] in peers):
        raise ValueError('exact distinct sorted peer researchers required')
    expected = sorted([release['researcher_id']] + peers)
    parents = release.get('parent_releases')
    if (not isinstance(parents, list) or not isinstance(parent_json, list)
            or [p.get('researcher_id') if isinstance(p, dict) else None for p in parents] != expected
            or [p.get('researcher_id') if isinstance(p, dict) else None for p in parent_json] != expected):
        raise ValueError('peer parent identities differ from approved policy')

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate field in peer parent JSON')
            result[key] = value
        return result

    records, target, counts = {}, None, []
    parent_fields = {'schema_version', 'scope', 'researcher_id', 'sources', 'items', 'items_sha256', 'target_bundle_sha256'}
    # 04's approved v3 parents retain these label-free release summaries.
    release_metadata = {'fit_source_hashes_unchanged', 'n_dev_source_groups', 'n_ordered_items',
                        'n_semantic_targets', 'parent_version', 'tier'}
    def validate_shapes(body, derivative=False):
        if not isinstance(body, dict):
            raise ValueError('peer release must be an object')
        _fields(body, parent_fields | (set(PEER_BINDINGS) if derivative else set()) |
                (set(body) & release_metadata), 'label-free peer release')
        for key in release_metadata & set(body):
            value = body[key]
            if ((key.startswith('n_') and (type(value) is not int or value < 0))
                    or (key == 'fit_source_hashes_unchanged' and type(value) is not bool)
                    or (key in ('tier', 'parent_version') and type(value) not in (str, int))):
                raise ValueError('peer release metadata has unsupported type')
        sources = body['sources']
        if not isinstance(sources, dict):
            raise ValueError('peer sources must be an object')
        sources_extra = set(sources) & {'schema_version', 'heldout'}
        _fields(sources, {'documents', 'source_manifest', 'allowed_source_manifest_hash'} | sources_extra, 'peer sources')
        if 'schema_version' in sources_extra:
            _text(sources['schema_version'], 'peer source schema')
        if 'heldout' in sources_extra:
            _fields(sources['heldout'], {'confirmation', 'dev'}, 'heldout counts only')
            for count in sources['heldout'].values():
                _fields(count, {'count'}, 'heldout count only')
                if type(count['count']) is not int or count['count'] < 0:
                    raise ValueError('heldout source count must be nonnegative integer')

    validate_shapes(release, derivative=True)
    from .runner import ITEM_FIELDS
    for parent, raw_parent in zip(parents, parent_json):
        _fields(parent, {'researcher_id', 'release'}, 'peer parent reference')
        _fields(parent['release'], {'path', 'sha256'}, 'peer parent file reference')
        reference = parent['release']
        if not isinstance(reference['path'], str) or not Path(reference['path']).is_absolute():
            raise ValueError('absolute peer parent file reference required')
        _hash(reference['sha256'], 'peer parent file')
        _fields(raw_parent, {'researcher_id', 'release_json'}, 'peer parent byte proof')
        raw = raw_parent['release_json']
        if not isinstance(raw, str) or len(raw.encode('utf-8')) > 64_000_000 or sha256_text(raw) != reference['sha256']:
            raise ValueError('peer parent release bytes differ from frozen file hash')
        body = json.loads(raw, object_pairs_hook=unique_object)
        validate_shapes(body)
        if (body['schema_version'] != 'released-development-v2' or body['scope'] != release['scope']
                or body['researcher_id'] != parent['researcher_id']):
            raise ValueError('peer parent must be its declared original target-only fit release')
        _hash(body['target_bundle_sha256'], 'opaque peer parent target bundle')
        docs, sources = body['sources']['documents'], body['sources']['source_manifest']
        validate_documents(docs, {'researcher_id': body['researcher_id'], 'allowed_sources': sources,
                                 'allowed_source_manifest_hash': body['sources']['allowed_source_manifest_hash']})
        if sources != source_manifest(docs):
            raise ValueError('peer parent source manifest differs from its records')
        if not isinstance(body['items'], list) or digest(body['items']) != body['items_sha256']:
            raise ValueError('peer parent item digest mismatch')
        seen_items = set()
        for item in body['items']:
            _fields(item, ITEM_FIELDS, 'label-free peer parent item')
            if item['researcher_id'] != body['researcher_id'] or not isinstance(item['item_id'], str) or not item['item_id'] or item['item_id'] in seen_items:
                raise ValueError('peer parent item identity mismatch')
            seen_items.add(item['item_id'])
        for doc in docs:
            if doc.get('split_eligibility') in ('dev', 'confirmation', 'test', 'quarantine', 'heldout'):
                raise ValueError('peer parent contains a known non-fit source')
            identifier = doc['document_id']
            if identifier in records and records[identifier] != doc:
                raise ValueError('conflicting peer parent document records')
            records[identifier] = doc
        counts.append({'researcher_id': body['researcher_id'],
                       'role': 'target' if body['researcher_id'] == release['researcher_id'] else 'peer',
                       'source_count': len(docs), 'full_content_utf8_bytes': sum(len(d['content'].encode('utf-8')) for d in docs),
                       'parent_file_sha256': reference['sha256']})
        if body['researcher_id'] == release['researcher_id']:
            target = body
    if release['sources']['documents'] != [records[key] for key in sorted(records)]:
        raise ValueError('peer derivative is not the exact sorted union of parent fit records')
    if any(release.get(key) != target[key] for key in ('items', 'items_sha256', 'target_bundle_sha256')):
        raise ValueError('peer derivative changed the target item schedule or opaque target bundle')
    return {'source_condition': 'approved-target-plus-peer-fit-evidence', 'parents': counts,
            'comparison_limit': 'cross-source-condition comparisons do not hold evidence constant'}


def compile_driver_packets(manifest, bindings, *, runtime, expected_manifest_hash,
                           expected_bindings_hash, expected_runtime_hash):
    """Translate a frozen design to unleased driver packet drafts, without I/O.

    Approved release/profile bodies are supplied by the coordinator. Returned
    packets contain only file references and label-free hashes/settings. Authority
    fields remain null: only the coordinator can supply authorization and leases.
    Existing frozen profile dependencies are reused; this never requests a new
    extraction or relabels an artifact's runtime. Utility/CLI keep explicit gaps.
    """
    from pathlib import Path
    from .contracts import source_manifest, validate_documents, sha256_text
    from .consumer import prepare_payload, implementation_hash, PROMPT_VERSION, SYSTEM, INSTRUCTION
    from .runner import ITEM_FIELDS
    validate_manifest(manifest, expected_manifest_hash=expected_manifest_hash)
    if digest(bindings) != expected_bindings_hash or digest(runtime) != expected_runtime_hash:
        raise ValueError('approved bindings or runtime pins changed')
    _fields(runtime, {'schema_version', 'code_sha', 'driver_sha256', 'runner_sha256', 'backend_sha256',
        'renderer_implementation_hash', 'consumer_prompt_version', 'consumer_prompt_sha256',
        'deadline', 'release_schema_version', 'release_scope'}, 'driver runtime')
    if runtime['schema_version'] != 'scaling-driver-runtime-v1':
        raise ValueError('unsupported driver runtime schema')
    _hash(runtime['code_sha'], 'runtime code', 40)
    for field in ('driver_sha256', 'runner_sha256', 'backend_sha256', 'renderer_implementation_hash', 'consumer_prompt_sha256'):
        _hash(runtime[field], field)
    spec = manifest['design']
    if spec['schema_version'] != 'overnight-scaling-design-v2':
        raise ValueError('driver adapter requires v2 request/effective settings and full document pins')
    if spec['code_sha'] != runtime['code_sha']:
        raise ValueError('runtime code differs from frozen design; no artifact migration')
    if (runtime['renderer_implementation_hash'] != implementation_hash() or
            runtime['consumer_prompt_version'] != PROMPT_VERSION or
            runtime['consumer_prompt_sha256'] != digest({'version': PROMPT_VERSION, 'system': SYSTEM, 'instruction': INSTRUCTION})):
        raise ValueError('runtime renderer or consumer prompt differs from loaded pinned implementation')
    for field in ('renderer_implementation_hash', 'consumer_prompt_version', 'consumer_prompt_sha256'):
        if spec['common'][field] != runtime[field]:
            raise ValueError('frozen design consumer differs from runtime: ' + field)
    cell_index = {cell['cell_id']: cell for cell in manifest['cells']}
    provided = {}
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get('cell_id') not in cell_index or binding['cell_id'] in provided:
            raise ValueError('duplicate or unknown driver cell binding')
        provided[binding['cell_id']] = binding
    if set(provided) != set(cell_index):
        raise ValueError('every unique cell requires an explicit ready or unavailable binding')
    packets, cells, dependencies, raw_hashes, executions = [], [], {}, {}, {}
    registrations = {
        'P1': ('profiles_summary', 'register_summary_builders'),
        'P2': ('profiles_summary', 'register_summary_builders'),
        'P3': ('profiles_summary', 'register_summary_builders'),
        'P4': ('profiles_principles', 'register_principle_builders'),
        'P5': ('profiles_principles', 'register_principle_builders'),
        'P6': ('profiles_principles', 'register_principle_builders'),
        'P7': ('profiles_hypotheses', 'register_hypotheses_builders'),
        'P8': ('profiles_hypotheses', 'register_hypotheses_builders')}
    for name in ('no_profile', 'name_only', 'raw_evidence', 'lexical_retrieval', 'semantic_retrieval', 'memory_summary', 'profile_retrieval'):
        registrations[name] = ('baselines', 'register_baselines')

    def ref(value):
        _fields(value, {'path', 'sha256'}, 'driver file reference')
        if not isinstance(value['path'], str) or not Path(value['path']).is_absolute():
            raise ValueError('driver file references must have explicit absolute paths')
        _hash(value['sha256'], 'driver input file')

    for cell_id, cell in cell_index.items():
        binding = provided[cell_id]
        if binding.get('status') == 'unavailable':
            _fields(binding, {'cell_id', 'status', 'reason'}, 'unavailable driver binding')
            _text(binding['reason'], 'unavailable dependency reason')
            cells.append({'cell_id': cell_id, 'status': 'unavailable', 'reason': binding['reason'], 'packet_ids': []})
            continue
        peer_release = isinstance(binding.get('release'), dict) and binding['release'].get('schema_version') == PEER_RELEASE_SCHEMA
        _fields(binding, {'cell_id', 'status', 'release_ref', 'release', 'jobs'} |
                ({'peer_parent_releases'} if peer_release else set()), 'ready driver binding')
        if binding['status'] != 'ready':
            raise ValueError('driver binding availability must be explicit')
        unsupported = ('downstream-utility-owner-required' if cell['common']['outcome_panel'] == 'utility' else
                       'separate-cli-driver-required' if spec['panel_kind'] == 'cli' else
                       'current-driver-requires-development-responses-api' if spec['stage'] != 'dev' or spec['panel_kind'] != 'responses_api' else None)
        if unsupported:
            cells.append({'cell_id': cell_id, 'status': 'unsupported', 'reason': unsupported, 'packet_ids': [],
                          'handoff': _copy(cell)})
            continue
        ref(binding['release_ref'])
        release, common = binding['release'], cell['common']
        if (not isinstance(release, dict) or release.get('schema_version') != runtime['release_schema_version']
                or release.get('scope') != runtime['release_scope'] or release.get('researcher_id') != common['researcher_id']):
            raise ValueError('release schema/scope/researcher differs from runtime or frozen cell')
        peer_proof = None
        if peer_release:
            peer_proof = _peer_release_proof(release, binding['peer_parent_releases'], cell['conditioning'].get('method_id'))
        elif any(key in release for key in PEER_BINDINGS):
            raise ValueError('ordinary releases cannot carry peer metadata')
        documents = release['sources']['documents']
        if digest(documents) != common['documents_hash']:
            raise ValueError('release full source records differ from frozen common evidence scope')
        sources = source_manifest(documents)
        if (release['sources']['source_manifest'] != sources or
                release['sources']['allowed_source_manifest_hash'] != digest(sources) or
                digest(sources) != common['allowed_source_manifest_hash']):
            raise ValueError('release source manifest differs from frozen cell')
        validate_documents(documents, {'researcher_id': common['researcher_id'], 'allowed_sources': sources,
                                      'allowed_source_manifest_hash': digest(sources), 'approved_peer_sources': peer_release})
        all_items = release['items']
        if not isinstance(all_items, list) or digest(all_items) != release.get('items_sha256'):
            raise ValueError('release items hash mismatch')
        item_index = {}
        for item in all_items:
            _fields(item, ITEM_FIELDS, 'label-free released item')
            if item['item_id'] in item_index or item['researcher_id'] != common['researcher_id']:
                raise ValueError('duplicate or wrong-researcher release item')
            item_index[item['item_id']] = item
        wanted_ids = [item['item_id'] for item in common['items']]
        if any(i not in item_index for i in wanted_ids):
            raise ValueError('release missing frozen items')
        wanted = [item_index[i] for i in wanted_ids]
        metadata = [{'item_id': i['item_id'], 'option_order_id': i['option_order_id'],
                     'context_sha256': sha256_text(i['context']), 'options_sha256': digest(i['options'])} for i in wanted]
        if digest(wanted) != common['items_hash'] or metadata != common['items']:
            raise ValueError('exact shared item/order/context hash mismatch')
        if cell['consumer']['adapter_sha256'] != runtime['backend_sha256']:
            raise ValueError('consumer backend code pin differs from runtime')
        identity, settings = cell['consumer']['identity'], cell['consumer']['settings']
        if set(settings) != {'temperature', 'max_tokens'}:
            raise ValueError('driver request settings must be exactly temperature/max_tokens')
        if cell['consumer']['effective_settings'] != identity.get('enforced_settings'):
            raise ValueError('effective backend settings differ from frozen identity')
        flattened, cell_packets = [], []
        if not isinstance(binding['jobs'], list) or not binding['jobs']:
            raise ValueError('ready cell must supply explicit profile/item jobs')
        for job in binding['jobs']:
            _fields(job, {'item_ids', 'profile_ref', 'profile', 'origin_job_id', 'registration', 'limits'}, 'driver job binding')
            ids = job['item_ids']
            if not isinstance(ids, list) or not ids or any(i not in wanted_ids for i in ids):
                raise ValueError('explicit frozen item subset required')
            flattened.extend(ids)
            selected = [item_index[i] for i in ids]
            ref(job['profile_ref'])
            _hash(job['origin_job_id'], 'profile origin job')
            profile = ProfileArtifact.from_dict(job['profile'])
            body = profile.to_dict()
            if peer_release:
                if body['method_id'] != 'P7' or any(key not in body['config'] or body['config'][key] != release[key] for key in PEER_BINDINGS):
                    raise ValueError('P7 profile peer declarations differ from approved release')
            elif any(key in body['config'] for key in PEER_BINDINGS):
                raise ValueError('ordinary profile cannot carry peer metadata')
            if (body.get('code_sha') != runtime['code_sha'] or body.get('documents_hash') != digest(documents)
                    or body['researcher_id'] != common['researcher_id'] or body['allowed_source_manifest_hash'] != digest(sources)
                    or body['personalization_cap'] != common['personalization_cap']):
                raise ValueError('profile runtime/full sources/researcher/cap mismatch; no relabeling')
            validate_documents(documents, body['config'])
            validate_consumer_binding({'kind': 'neutral_profile', 'weights_status': body['weights_status'],
                                       'confidence_status': body['confidence_status']}, identity)
            condition = cell['conditioning']
            if condition['kind'] == 'neutral_profile':
                for key in (PIN_FIELDS | {'documents_hash'}) - {'kind', 'extractor_level'}:
                    if body.get(key) != condition[key]:
                        raise ValueError('frozen neutral profile pin changed: ' + key)
            else:
                method = 'raw_evidence' if condition['kind'] == 'archival_raw_evidence' else condition['method_id']
                if body['method_id'] != method:
                    raise ValueError('control/diagnostic profile method differs from declared intervention')
                policy_hash = (condition['raw_control_config_hash'] if condition['kind'] == 'archival_raw_evidence'
                               else condition['config_hash'])
                if control_policy_hash(body['config']) != policy_hash:
                    raise ValueError('control policy config differs from frozen condition')
                allowed_methods = {'no_profile': {'no_profile'}, 'raw_evidence': {'raw_evidence'},
                                   'retrieval': {'lexical_retrieval', 'semantic_retrieval'},
                                   'archival_raw_evidence': {'raw_evidence'}}
                if method not in allowed_methods.get(condition['kind'], set()):
                    raise ValueError('control method does not implement the declared evidence condition')
                if method == 'no_profile' and (render_content(body['content']) or body.get('intentional_empty') is not True):
                    raise ValueError('no-profile control must be intentionally empty')
                if method in ('lexical_retrieval', 'semantic_retrieval'):
                    validate_raw_passage_scope(body['content'], documents)
                    if (len(selected) != 1 or body['config'].get('decision') !=
                            {k: selected[0][k] for k in ('context', 'options')} or
                            body['config'].get('consumer_identity') != identity):
                        raise ValueError('retrieval profile decision/consumer binding mismatch')
                if method == 'raw_evidence':
                    if not isinstance(body['content'], dict) or set(body['content']) != {'passages'} or 'frozen_profile' in body['config']:
                        raise ValueError('raw diagnostic/control cannot carry candidate-derived profile content')
                    validate_raw_passage_scope(body['content'], documents)
                    if condition['kind'] == 'archival_raw_evidence' and body['method_implementation_hash'] != condition['raw_implementation_sha256']:
                        raise ValueError('diagnostic raw baseline implementation differs from frozen policy')
                    for item_id in ids:
                        key = (condition['kind'], item_id)
                        if key in raw_hashes and raw_hashes[key] != body['content_sha256']:
                            raise ValueError('raw evidence content changed across model levels')
                        raw_hashes[key] = body['content_sha256']
                if condition['kind'] != 'archival_raw_evidence' and body['method_implementation_hash'] != condition['implementation_sha256']:
                    raise ValueError('control implementation differs from frozen condition')
            method = body['method_id']
            declared_registration = registrations.get(method)
            if not declared_registration or job['registration'] != {
                'module': 'autoresearch.taste.overnight.' + declared_registration[0], 'function': declared_registration[1]}:
                raise ValueError('method registration is not supported by pinned driver')
            limits = job['limits']
            _fields(limits, {'max_calls', 'max_seconds', 'max_usd', 'timeout'}, 'requested limits')
            if (type(limits['max_calls']) is not int or limits['max_calls'] < len(ids) or
                    any(type(limits[k]) not in (int, float) or not math.isfinite(limits[k]) or limits[k] <= 0
                        for k in ('max_seconds', 'max_usd', 'timeout')) or limits['timeout'] >= limits['max_seconds']):
                raise ValueError('finite feasible request limits required; these are not an allocation')
            config = {'method_implementation_hash': body['method_implementation_hash'],
                'renderer_implementation_hash': runtime['renderer_implementation_hash'],
                'profile_prompt_version': body['prompt_version'], 'consumer_prompt_version': runtime['consumer_prompt_version'],
                'settings': settings}
            if peer_release:
                config.update({key: _copy(release[key]) for key in PEER_BINDINGS})
            payload_pins = []
            for item in selected:
                prepared = prepare_payload(profile, item['context'], item['options'], config)
                if len((prepared['system'] + prepared['prompt']).encode('utf-8')) > common['context_cap']:
                    raise ValueError('rendered request exceeds frozen common context byte cap')
                payload_pins.append({'item_id': item['item_id'], 'payload_sha256': prepared['payload_sha256'],
                                     'rendered_profile_sha256': prepared['rendered_profile_sha256']})
            allocation = {k: limits[k] for k in ('max_calls', 'max_seconds', 'max_usd')}
            allocation.update(cost_mode='priced_api', authorization_source=None)
            plan = {'schema_version': 'overnight-job-v1', 'campaign_id': spec['campaign_id'], 'stage': 'dev', 'kind': 'predict',
                'contract_sha256': spec['contract_sha256'], 'config_hash': digest(config), 'source_manifest_hash': digest(sources),
                'documents_hash': digest(documents), 'items_hash': digest(selected), 'profile_hash': profile.profile_id,
                'method_id': method, 'extractor': profile.extractor, 'consumer': identity,
                'personalization_cap': common['personalization_cap'],
                'option_order_schedule': [{'item_id': i['item_id'], 'option_order_id': i['option_order_id']} for i in selected],
                'replicate_id': profile.replicate_id, 'code_sha': runtime['code_sha'], 'deadline': runtime['deadline'],
                'allocation': allocation, 'retry_policy': {'max_attempts': 1, 'retry_uncertain': False},
                'parent_job_ids': [job['origin_job_id']], 'expected_outputs': ['result.json', 'traces'],
                'scaling_cell_id': cell_id, 'scaling_manifest_sha256': expected_manifest_hash,
                'scaling_bindings_sha256': expected_bindings_hash, 'scaling_runtime_sha256': expected_runtime_hash,
                'scaling_context_cap': common['context_cap'], 'scaling_payload_pins': payload_pins,
                'scaling_permitted_spans_sha256': digest([{'document_id': d['document_id'],
                    'permitted_spans': d.get('permitted_spans', [])} for d in documents])}
            if peer_proof is not None:
                plan['scaling_peer_evidence'] = peer_proof
            packet = {'schema_version': 'overnight-packet-v1', 'release': _copy(binding['release_ref']),
                'item_ids': ids, 'profile': _copy(job['profile_ref']), 'config': config, 'manifest': plan,
                'lease': None, 'backend': dict(limits, model=identity['model'], reasoning=identity['enforced_settings']['reasoning_effort']),
                'registration': job['registration']}
            execution = _copy(packet)
            execution['manifest'].pop('scaling_cell_id')
            # Identical bytes at another path are the same input; preserve the first
            # concrete reference for the driver and all cell aliases for analysis.
            for field in ('release', 'profile'):
                execution[field] = {'sha256': execution[field]['sha256']}
            packet_id = digest(execution)
            if packet_id in executions:
                executions[packet_id]['cell_ids'].append(cell_id)
            else:
                entry = {'packet_id': packet_id, 'cell_id': cell_id, 'cell_ids': [cell_id],
                         'status': 'awaiting-coordinator-authority', 'packet': packet}
                executions[packet_id] = entry
                packets.append(entry)
            cell_packets.append(packet_id)
            dependency = dependencies.setdefault(profile.profile_id, {'profile_id': profile.profile_id,
                'method_id': method, 'content_sha256': profile.content_sha256, 'profile_ref': job['profile_ref'],
                'origin_job_id': job['origin_job_id'], 'mode': 'reuse-existing-frozen-profile', 'packet_ids': []})
            if dependency['origin_job_id'] != job['origin_job_id'] or dependency['profile_ref'] != job['profile_ref']:
                raise ValueError('same frozen profile has contradictory origin or file reference')
            if packet_id not in dependency['packet_ids']:
                dependency['packet_ids'].append(packet_id)
        if flattened != wanted_ids:
            raise ValueError('job partitions must preserve every frozen item exactly once and in order')
        cells.append({'cell_id': cell_id, 'status': 'compiled', 'reason': None, 'packet_ids': cell_packets})
    final_ids = {}
    for entry in packets:
        entry['packet']['manifest']['scaling_cell_ids'] = sorted(entry['cell_ids'])
        final_ids[entry['packet_id']] = digest(entry['packet'])
        entry['packet_id'] = final_ids[entry['packet_id']]
    for cell in cells:
        cell['packet_ids'] = [final_ids[i] for i in cell['packet_ids']]
    for dependency in dependencies.values():
        dependency['packet_ids'] = [final_ids[i] for i in dependency['packet_ids']]
    output = {'schema_version': 'scaling-driver-drafts-v1', 'manifest_sha256': expected_manifest_hash,
        'bindings_sha256': expected_bindings_hash, 'runtime_sha256': expected_runtime_hash,
        'runtime': _copy(runtime), 'arms': _copy(manifest['arms']), 'cells': cells, 'packets': packets,
        'profile_dependencies': list(dependencies.values()), 'authority': 'none; coordinator must supply allocation source and leases',
        'estimates': {'max_attempts': sum(p['packet']['backend']['max_calls'] for p in packets),
            'requested_usd_ceiling': sum(p['packet']['backend']['max_usd'] for p in packets),
            'new_extraction_calls': 0, 'status': 'requested-ceilings-not-spend-or-authorization'}}
    output['compilation_sha256'] = digest(output)
    return _copy(output)



def control_policy_hash(config):
    """Bind every control choice; omit only separately checked source/runtime/query fields."""
    separate = {'researcher_id', 'allowed_sources', 'allowed_source_manifest_hash',
                'replicate_id', 'code_sha', 'extractor_settings', 'decision', 'consumer_identity'}
    return digest({key: value for key, value in config.items() if key not in separate})


def validate_raw_passage_scope(content, documents):
    """Reject frozen raw passages outside approved spans; never construct a fallback."""
    by_id = {d['document_id']: d for d in documents}
    if not isinstance(content, dict) or set(content) != {'passages'}:
        raise ValueError('raw/retrieval controls require only permitted passages, no profile annotations')
    passages = content['passages']
    if not isinstance(passages, list) or not passages:
        raise ValueError('raw evidence requires approved permitted passages')
    for passage in passages:
        _fields(passage, {'document_id', 'start', 'end', 'text'}, 'permitted raw passage')
        document = by_id.get(passage.get('document_id'))
        start, end = passage.get('start'), passage.get('end')
        if (document is None or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(document['content'])
                or passage.get('text') != document['content'][start:end]):
            raise ValueError('raw passage does not match permitted source bytes')
        spans = document.get('permitted_spans')
        if not isinstance(spans, list) or not any(isinstance(s, dict) and type(s.get('start')) is int
                and type(s.get('end')) is int and s['start'] <= start < end <= s['end']
                and s.get('speaker') == document['researcher_id'] for s in spans):
            raise ValueError('raw passage lies outside evaluator-permitted source spans')


def group_released_pilot(mapping_bytes, report_bytes, *, expected_mapping_sha256, expected_report_sha256):
    """Validate Role04's released aggregate/map schema without reading private rows.

    Balanced paired orders allow its operational ordered accuracy to equal the
    equal-semantic-target mean. Aggregate totals do not identify source-group
    variances. No interval is reconstructed, no labels are inferred, and an
    unavailable build remains unavailable rather than a measured preference error.
    """
    from itertools import combinations
    from .contracts import sha256_bytes
    if sha256_bytes(mapping_bytes) != expected_mapping_sha256 or sha256_bytes(report_bytes) != expected_report_sha256:
        raise ValueError('released evaluator artifact byte hash mismatch')
    mapping, report = json.loads(mapping_bytes), json.loads(report_bytes)
    if (mapping.get('schema_version') != 'pilot-opaque-group-map-v1'
            or report.get('schema_version') != 'researcher-profile-pilot-score-v1'
            or report.get('opaque_group_mapping_sha256') != expected_mapping_sha256
            or report.get('selection_sha256') != mapping.get('pilot_selection_sha256')
            or report.get('campaign_id') != mapping.get('campaign_id')):
        raise ValueError('released pilot schema/provenance mismatch')
    groups, seen = {}, set()
    for item in mapping['mapping']:
        _fields(item, {'group_id', 'item_id', 'option_order_id', 'researcher_id', 'semantic_target_id', 'tier'}, 'opaque pilot item')
        for field, value in item.items():
            _text(value, field)
        if item['item_id'] in seen or item['tier'] not in ('A', 'B'):
            raise ValueError('duplicate pilot item or unsupported evidence tier')
        seen.add(item['item_id'])
        key = (item['researcher_id'], item['tier'], item['semantic_target_id'])
        variants = groups.setdefault(key, [])
        if variants and variants[0]['group_id'] != item['group_id']:
            raise ValueError('semantic target crosses source groups')
        variants.append(item)
    if not groups or any(len(v) != 2 or len({i['option_order_id'] for i in v}) != 2 for v in groups.values()):
        raise ValueError('released pilot requires two distinct scheduled orders per semantic target')
    counts, strata = {}, {}
    for researcher in sorted({key[0] for key in groups}):
        selected = [i for key, variants in groups.items() if key[0] == researcher for i in variants]
        counts[researcher] = {'ordered_items': len(selected),
            'semantic_targets': len({(i['tier'], i['semantic_target_id']) for i in selected}),
            'independent_source_groups': len({i['group_id'] for i in selected})}
        if mapping['counts'].get(researcher) != counts[researcher]:
            raise ValueError('opaque map denominator differs from its items')
        denominator = report['denominators'].get(researcher, {})
        if any(denominator.get(k) != v for k, v in counts[researcher].items()):
            raise ValueError('report denominator differs from opaque map')
        _hash(denominator.get('items_sha256'), 'pilot selected inputs')
        for tier in sorted({i['tier'] for i in selected}):
            subset = [i for i in selected if i['tier'] == tier]
            strata[(researcher, tier)] = {'ordered_items': len(subset),
                'semantic_targets': len({i['semantic_target_id'] for i in subset}),
                'independent_source_groups': len({i['group_id'] for i in subset})}
    if set(counts) != set(mapping['counts']) or set(counts) != set(report['denominators']):
        raise ValueError('extra or omitted researcher denominator')
    arms, indexed = [], {}
    for arm in report['arms']:
        key = (arm['researcher_id'], arm['tier'], arm['method_id'])
        expected = strata.get(key[:2])
        if key in indexed or expected is None or arm.get('status') not in ('scored', 'unavailable_build'):
            raise ValueError('duplicate, unknown or invalid pilot arm')
        for field, count in [('n_items', expected['ordered_items']), ('n_semantic_targets', expected['semantic_targets']),
                             ('n_source_groups', expected['independent_source_groups'])]:
            if type(arm.get(field)) is not int or arm[field] != count:
                raise ValueError('pilot arm denominator differs from mapped independent units')
        n = expected['ordered_items']
        if type(arm.get('n_correct')) is not int or not 0 <= arm['n_correct'] <= n:
            raise ValueError('invalid correct count')
        if not math.isclose(arm['accuracy_all_scheduled'], arm['n_correct'] / n, abs_tol=1e-12):
            raise ValueError('all-scheduled accuracy contradicts evaluator counts')
        order = arm['order_coupling']
        both, one, neither = (order[k] for k in ('both_orders_correct_pairs', 'exactly_one_order_correct_pairs', 'neither_order_correct_pairs'))
        if (any(type(x) is not int or x < 0 for x in (both, one, neither))
                or both + one + neither != expected['semantic_targets'] or 2 * both + one != arm['n_correct']):
            raise ValueError('order-coupling counts contradict scheduled semantic pairs')
        if arm['status'] == 'unavailable_build' and (arm['n_correct'] != 0 or arm['valid_choice_accuracy'] is not None
                or arm['valid_choice_coverage'] != 0 or arm['probability_coverage'] != 0 or arm['brier_valid_only'] is not None):
            raise ValueError('unavailable build cannot claim measured prediction coverage')
        indexed[key] = arm
        arms.append(dict(_copy(arm), equal_semantic_operational_accuracy=arm['accuracy_all_scheduled'],
                         evidence_status='unavailable-execution' if arm['status'] == 'unavailable_build' else 'scored-operational-pilot'))
    expected_pairs = set()
    for researcher, tier in strata:
        methods = sorted(key[2] for key in indexed if key[:2] == (researcher, tier))
        expected_pairs.update((researcher, tier, a, b) for a, b in combinations(methods, 2))
    paired, seen_pairs = [], set()
    for pair in report['paired_comparisons']:
        researcher, a, b = pair['researcher_id'], pair['method_a'], pair['method_b']
        possible = [key for key in strata if key[0] == researcher and (researcher, key[1], a) in indexed
                    and (researcher, key[1], b) in indexed]
        if len(possible) != 1 or a == b:
            raise ValueError('pilot pair lacks an unambiguous researcher/tier match')
        tier = possible[0][1]
        key = (researcher, tier, *sorted((a, b)))
        if key in seen_pairs:
            raise ValueError('duplicate pilot pair')
        seen_pairs.add(key)
        left, right = indexed[(researcher, tier, a)], indexed[(researcher, tier, b)]
        expected = strata[(researcher, tier)]
        if any(pair.get(k) != expected[field] for k, field in (
                ('n_ordered_items', 'ordered_items'), ('n_semantic_targets', 'semantic_targets'),
                ('n_source_groups', 'independent_source_groups'))):
            raise ValueError('paired denominator differs from mapped units')
        delta = left['accuracy_all_scheduled'] - right['accuracy_all_scheduled']
        if not math.isclose(pair['accuracy_difference_a_minus_b'], delta, abs_tol=1e-12):
            raise ValueError('paired operational difference contradicts arm counts')
        if expected['independent_source_groups'] < 2 and pair['accuracy_ci95'] is not None:
            raise ValueError('one source group cannot support a source-group interval')
        paired.append(dict(_copy(pair), tier=tier, accuracy_ci95=None,
            equal_semantic_operational_difference=delta,
            uncertainty_status='insufficient-independent-groups' if expected['independent_source_groups'] < 2
                               else 'requires-evaluator-grouped-scores'))
    if seen_pairs != expected_pairs:
        raise ValueError('pilot report omitted or added method comparisons')
    return {'schema_version': 'scaling-released-pilot-group-report-v1', 'outcome_panel': 'fidelity-operational-pilot',
        'mapping_file_sha256': expected_mapping_sha256, 'report_file_sha256': expected_report_sha256,
        'runtime_code_sha': report['runtime_code_sha'], 'evaluator_code_commit': report['evaluator_code_commit'],
        'selection_sha256': report['selection_sha256'], 'counts': counts, 'arms': arms, 'paired_comparisons': paired,
        'total_cost': _copy(report['total_cost']),
        'limitations': _copy(report['limitations']) + ['Balanced option reversals are repeated measurements of one judgment.',
            'Aggregate reports do not expose per-group outcomes; no bootstrap distribution was reconstructed.',
            'Researcher cases remain separate; two researchers do not justify population inference.',
            'Operational unavailable-as-wrong accuracy is not a measured prediction error or a utility result.']}
