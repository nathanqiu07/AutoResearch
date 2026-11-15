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
    if spec['schema_version'] != 'overnight-scaling-design-v1':
        raise ValueError('unsupported scaling design schema')
    if spec['stage'] not in ('offline', 'dev', 'confirmation'):
        raise ValueError('unsupported stage')
    for key in ('campaign_id', 'panel_id'):
        _text(spec[key], key)
    _hash(spec['contract_sha256'], 'contract')
    _hash(spec['code_sha'], 'code', 40)
    if spec['axis'] != 'declared-model-level-not-parameter-count':
        raise ValueError('panel names do not establish parameter counts or capability')
    prefixes = {'offline': ('offline',), 'responses_api': ('openai-responses:',),
                'cli': ('codex-cli:', 'claude-cli:', 'devin-cli:')}
    if spec['panel_kind'] not in prefixes:
        raise ValueError('unsupported panel transport')
    if spec['stage'] == 'offline' and spec['panel_kind'] != 'offline':
        raise ValueError('offline preparation requires a synthetic offline panel')
    common = spec['common']
    _fields(common, COMMON_FIELDS, 'common comparison inputs')
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
                        'verification_sha256', 'model_revision'}, 'model')
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
        if not isinstance(enforced, dict) or any(
                key not in model['settings'] or model['settings'][key] != value
                for key, value in enforced.items()):
            raise ValueError('declared settings must include the actual enforced backend settings')
        for key in set(common['settings']) | set(model['settings']):
            expected, actual = common['settings'].get(key), model['settings'].get(key)
            if expected != actual or (key in common['settings']) != (key in model['settings']):
                differences[(model['level'], key)] = (expected, actual)
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
    if not isinstance(spec['controls'], list) or len(spec['controls']) != 2:
        raise ValueError('declare no-profile and one matched raw/retrieval control')
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
    if kinds not in ({'no_profile', 'raw_evidence'}, {'no_profile', 'retrieval'}):
        raise ValueError('required matched controls missing')
    diagnostic = spec['diagnostic']
    _fields(diagnostic, DIAGNOSTIC_FIELDS, 'diagnostic')
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
    for pin in pins:
        unavailable = pin.get('kind') == 'unavailable_profile'
        _fields(pin, UNAVAILABLE_PIN_FIELDS if unavailable else PIN_FIELDS, 'profile pin')
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
        if pin['extractor'] != model['identity'] or pin['extractor_settings'] != model['settings']:
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
            consumer = {key: models[consumer_level][key]
                        for key in ('identity', 'settings', 'adapter_sha256', 'verification_sha256', 'model_revision')}
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
    baseline = next(c['method_id'] for c in manifest['design']['controls'] if c['kind'] != 'no_profile')

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
