"""Zero-call private binding recipe. Does not select, lease, dispatch or score."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OWN_ROOT = HERE.parents[3]
RUNTIME_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
CONTRACT = {'path': '/private/tmp/gio-profile-20261115-coordinator/development-scaling-selection-contract-v1.json', 'sha256': '57e79808a8e82f362a5d4f2f12e07bd1bf203a6cba9ec49c2eebcd4d14220569'}
ADOPTION = {'path': '/private/tmp/gio-profile-20261115-coordinator/development-scaling-adoption-v1.json', 'sha256': 'f45f64dd3f5b57e2f891873ccb44d2c628392fd16607d863c048e73c537e66f1'}
ADOPTION_VERIFICATION = {'path': '/private/tmp/gio-profile-20261115-coordinator/development-scaling-adoption-verification-v1.json', 'sha256': 'ba3923c7d84dde72d2c4e85d933f06a0619dcb56203e09aed6d41720e6f97eb8'}
CONTROL_RECEIPT = {'path': '/private/tmp/gio-profile-20261115-coordinator/scaling-sparse-control-inputs-v1.json', 'sha256': '43d0bef054c05c98599e1c6964f7695fe19856b6635f0b10fc2b0c6522017427'}
DENYLIST = {'path': '/private/tmp/gio-profile-incident-1154-review-v1/combined-provider-unknown-denylist.json', 'sha256': '8804a408fd50f1617f4a4004b05d7a6453fc94b16b30e7fca061d6548d977750'}
SEMANTIC_ROOT = Path('/Users/giordanorogers/.codex/worktrees/gio-labeled-reference/AutoResearch-overnight-control')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--runtime-root', required=True)
    args.add_argument('--selection', required=True)
    args.add_argument('--selection-sha256', required=True)
    args.add_argument('--continuation-proof')
    args.add_argument('--continuation-proof-sha256')
    args = args.parse_args()
    runtime_root = Path(args.runtime_root).resolve()
    assert subprocess.check_output(['git', '-C', str(runtime_root), 'rev-parse', 'HEAD'], text=True).strip() == RUNTIME_SHA
    assert not subprocess.check_output(['git', '-C', str(runtime_root), 'status', '--porcelain'], text=True).strip()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime_root))
    from autoresearch.taste.overnight import backends, consumer
    from autoresearch.taste.overnight.contracts import backend_identity, canonical_json, digest
    from autoresearch.taste.overnight.registry import get_builder
    from autoresearch.taste.overnight.runner import job_id
    compiler = load('autoresearch.taste.overnight.scaling_selection_compiler', OWN_ROOT / 'autoresearch/taste/overnight/scaling.py')
    helper = load('scaling_selection_leaf_helpers', HERE / 'selected_scaling_bindings_v1.py')
    driver = load('scaling_selection_frozen_driver', runtime_root / 'docs/overnight/gio-profile-20261115/control/run_batch.py')
    used = {}

    def approved(ref, raw=False):
        helper._reference(ref)
        data = Path(ref['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == ref['sha256'], 'input file hash changed'
        used[ref['path']] = ref['sha256']
        return data.decode('utf-8') if raw else json.loads(data)

    selection_ref = {'path': str(Path(args.selection).resolve()), 'sha256': args.selection_sha256}
    selection, contract = approved(selection_ref), approved(CONTRACT)
    adoption, adoption_verification = approved(ADOPTION), approved(ADOPTION_VERIFICATION)
    assert adoption['selection'] == selection_ref and adoption['execution_authorized'] is False
    assert adoption_verification['adoption'] == ADOPTION and adoption_verification['execution_authorized'] is False
    assert adoption_verification['selection_body_unchanged'] is True
    index = approved(selection['original_complete_index'])
    proof, proof_payloads = None, {}
    if args.continuation_proof:
        assert args.continuation_proof_sha256 == '5c0c4d5cc9f161b6dd112cde5ac7b0bb17689ef4e7722617f3ba36303ccc59fc'
        proof = approved({'path': str(Path(args.continuation_proof).resolve()), 'sha256': args.continuation_proof_sha256})
        assert proof['proposal']['sha256'] == selection_ref['sha256']
        for case in proof['cases']:
            for key in ('original_index_packet', 'actual_packet', 'actual_claim', 'actual_prepared', 'original_index_prepared', 'rebind_evidence'):
                proof_payloads[case[key]['path']] = approved(case[key], raw=True)
    validation = helper.validate_descriptive_selection(selection, contract, index, contract_ref=CONTRACT,
        index_ref=selection['original_complete_index'], **({'continuation_proof': proof, 'continuation_payloads': proof_payloads} if proof else {}))
    # This recipe never reads the score receipt, result files, or private target bundles.
    sparse = approved(selection['sparse_completion_index'])
    repeat_build = approved(selection['replicate_build_completion_index'])
    repeat_predict = approved(selection['replicate_prediction_completion_index'])
    control_receipt = approved(CONTROL_RECEIPT)
    assert selection['control_inputs'] == control_receipt['control_inputs']
    assert selection['semantic_index'] == control_receipt['semantic_index']
    controls = approved(selection['control_inputs'])
    semantic = approved(selection['semantic_index'])
    semantic_refs = {}
    for item in semantic['items']:
        ref = {'path': str(SEMANTIC_ROOT / item['bundle_path']), 'sha256': item['file_sha256']}
        bundle = approved(ref)
        assert digest({k: v for k, v in bundle.items() if k != 'bundle_sha256'}) == bundle['bundle_sha256'] == item['bundle_sha256']
        semantic_refs[(item['researcher_id'], item['item_id'])] = (ref, bundle)
    diagnostic = approved(selection['diagnostic_panel']) if selection['diagnostic_panel'] else None
    denylist = approved(DENYLIST)
    denied_requests = set(denylist['request_sha256'])
    assert len(denied_requests) == 9 and all(isinstance(h, str) and len(h) == 64 for h in denied_requests)
    template_path = HERE / 'driver-fixture-phase2-v1-148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6.json'
    assert sha(template_path) == '148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6'
    runtime = json.loads(template_path.read_text())['runtime']
    for key, relative in (('driver_sha256', 'docs/overnight/gio-profile-20261115/control/run_batch.py'),
            ('runner_sha256', 'autoresearch/taste/overnight/runner.py'), ('backend_sha256', 'autoresearch/taste/overnight/backends.py')):
        assert sha(runtime_root / relative) == runtime[key]
    assert runtime['code_sha'] == selection['runtime_sha'] == RUNTIME_SHA
    private_base = Path('/private/tmp/gio-profile-20261115-scaling')
    private_base.mkdir(exist_ok=True, mode=0o700)
    private = Path(tempfile.mkdtemp(prefix='mechanical-readiness-only-selected-v1-', dir=private_base))

    def save(name, body):
        data = (canonical_json(body) + '\n').encode()
        path = private / name
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o600)
        return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}

    inventory, drafts, aliases, pending, prep_count, future_calls = [], [], [], [], 0, []
    models = [m['model'] for m in selection['models']]
    consumer_settings = {k: selection['consumer_settings'][k] for k in ('temperature', 'max_tokens')}
    jobs = {j['job_id']: j for j in sparse['jobs']}
    original_rows = {r['cell_id']: r for r in index['cells']}
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)

    with tempfile.TemporaryDirectory(prefix='isolated-test-ledger-', dir=private) as temporary:
        ledger = backends.DollarLedger(Path(temporary) / 'ledger.sqlite', max_usd=500, deadline='2099-01-01T00:00:00Z')
        with patch('urllib.request.urlopen', side_effect=AssertionError('zero-call preparation forbids HTTP')) as http, \
             patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('zero-call preparation forbids completion')) as complete:
            identities = {m: backend_identity(backends.OpenAIResponsesBackend(model=m, reasoning='medium', ledger=ledger,
                max_usd=100, timeout=60)) for m in models}

            def register(packet):
                driver._register(packet['registration'], packet['manifest']['method_id'])

            def check(draft, release):
                nonlocal prep_count
                assert draft['lease'] is None and draft['manifest']['allocation']['authorization_source'] is None
                candidate = copy.deepcopy(draft)
                candidate['lease'] = {'lease_id': 'discarded-mechanical-test-only', 'owner': 'readiness-only', 'expires_at': runtime['deadline']}
                candidate['manifest']['allocation']['authorization_source'] = 'discarded-in-memory-test-only-no-execution-authority'
                batch = {'campaign_id': selection['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                    'release_schema_version': release['schema_version'], 'release_scope': release['scope'],
                    'contract': {'sha256': draft['manifest']['contract_sha256']}, 'ledger': {'max_usd': 500}}
                with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                    driver._prepare_packet(candidate, batch, ledger)
                prep_count += 1

            def add(draft, release, label, status='unleased-draft'):
                check(draft, release)
                ref = save('draft-%04d.json' % len(drafts), draft)
                record = {'label': label, 'status': status, 'packet': ref, 'kind': draft['manifest']['kind'],
                    'method_id': draft['manifest']['method_id'], 'model': draft['backend']['model'],
                    'n_items': len(draft['item_ids']), 'max_calls': draft['backend']['max_calls'],
                    'max_usd_reservation': draft['backend']['max_usd'], 'max_seconds': draft['backend']['max_seconds'],
                    'profile_id': draft['manifest'].get('profile_hash'), 'payload_pins_sha256': digest(draft['manifest'].get('scaling_payload_pins', [])),
                    'per_request_max_usd': (draft['backend']['max_usd'] if draft['manifest']['kind'] == 'build' else
                        [{'item_id': pin['item_id'], 'max_usd': pin['max_usd_reservation'], 'input_bound': pin['input_token_upper_bound']} for pin in draft['manifest']['scaling_payload_pins']]), 'studies': draft['manifest'].get('scaling_studies', ['A'])}
                outgoing = [p['wire_request_sha256'] for p in draft['manifest'].get('scaling_payload_pins', [])]
                record['canonical_outgoing_request_sha256s'] = outgoing
                record['uncertain_request_collisions'] = sorted(denied_requests.intersection(outgoing))
                if record['uncertain_request_collisions'] and status != 'historical-execution-alias':
                    record['status'] = 'unavailable-uncertain-request-collision'
                record['admission_gate'] = 'coordinator must check exact outgoing identity against then-current denylist; build/future profile identities unresolved'
                drafts.append(record)
                return record

            def peer_proof(release):
                if release['schema_version'] != 'released-development-v2-p7-peers-v1':
                    return None
                return [{'researcher_id': p['researcher_id'], 'release_json': approved(p['release'], raw=True)} for p in release['parent_releases']]

            def predict(profile, release, profile_ref, release_ref, origin, identity, registration, cell, studies, item_ids=None):
                return helper.prediction_packet(profile, release, profile_ref=profile_ref, release_ref=release_ref,
                    origin_job_id=origin, identity=identity, settings=consumer_settings, timeout=selection['consumer_settings']['timeout'],
                    logical_cap=selection['common_personalization_cap'], runtime=runtime, contract_sha256=contract_sha,
                    registration=registration, selection_sha256=selection_ref['sha256'], index_sha256=selection['original_complete_index']['sha256'],
                    selected_cell_id=cell, studies=studies, item_ids=item_ids, compiler=compiler, peer_parent_releases=peer_proof(release))

            def reuse_matches(draft, profile):
                matches = []
                for historical in sparse['jobs']:
                    if (historical['kind'] != 'predict' or historical['status'] != 'complete'
                            or historical.get('profile_id') != profile['profile_id'] or historical.get('item_ids') != draft['item_ids']):
                        continue
                    old = approved(historical['packet'])
                    if (old['manifest']['code_sha'] == RUNTIME_SHA and historical['actual_backend'] == draft['manifest']['consumer']
                            and old['manifest']['consumer'] == draft['manifest']['consumer']
                            and old['config'] == draft['config'] and old['backend']['timeout'] == draft['backend']['timeout']
                            and all(old['manifest'][k] == draft['manifest'][k] for k in ('documents_hash', 'source_manifest_hash', 'items_hash', 'option_order_schedule', 'profile_hash'))):
                        assert job_id(old['manifest']) == historical['job_id']
                        # With the exact profile/config/item/runtime/backend, f6 serialization is deterministic.
                        assert approved(old['profile']) == profile
                        matches.append({'job_id': historical['job_id'], 'packet': historical['packet'],
                            'trace_sha256s': historical['trace_sha256s'], 'proof': 'same exact profile/config/source/items/order/runtime/backend/timeout',
                            'wire_pins_sha256': digest(draft['manifest']['scaling_payload_pins'])})
                return matches

            for config in selection['selected_configs']:
                for mapping in config['researcher_mappings']:
                    row = original_rows[mapping['cell_id']]
                    source = approved(mapping['build_packet'])
                    release = approved(mapping['release'])
                    register(source)
                    assert source['manifest']['job_id'] == row['job_id']
                    contract_sha = source['manifest']['contract_sha256']
                    builder = get_builder(config['method_id'])
                    pins = {'method_implementation_hash': builder.implementation_hash, 'profile_prompt_version': builder.prompt_version,
                        'profile_prompt_sha256': builder.prompt_sha256, 'renderer_implementation_hash': consumer.implementation_hash()}
                    for model in models[1:]:
                        timeout = selection['extractor_settings']['timeout']
                        limits = {'max_calls': 1, 'max_seconds': timeout + 60, 'timeout': timeout,
                            'max_usd': helper.reservation_ceiling(model, selection['extractor_settings']['max_tokens'])}
                        draft = helper.new_extractor_build_draft(source, target_identity=identities[model], limits=limits,
                            expected_runtime_sha=RUNTIME_SHA, expected_origin_job_id=row['job_id'], selection_sha256=selection_ref['sha256'],
                            index_sha256=selection['original_complete_index']['sha256'], selection_cell_id=mapping['cell_id'], expected_build_pins=pins)
                        built = add(draft, release, mapping['cell_id'] + '/A/' + model)
                        future_calls.append({'cell': mapping['cell_id'], 'study': 'A', 'model': model, 'depends_on': built['packet'],
                            'bounds': helper.future_prediction_bounds(release['items'], model, consumer_settings, selection['common_personalization_cap'])})
                        pending.append({'cell': mapping['cell_id'], 'study': 'A', 'consumer': model, 'status': 'extractor-pending', 'build_draft': built['packet'], 'profile': None})
                        if config['config_id'] == selection['primary_config_id'] and model == 'gpt-6-astra':
                            future_calls.append({'cell': mapping['cell_id'], 'study': 'C', 'model': 'gpt-6-luna', 'depends_on': built['packet'],
                                'bounds': helper.future_prediction_bounds(release['items'], 'gpt-6-luna', consumer_settings, selection['common_personalization_cap'])})
                            pending.append({'cell': mapping['cell_id'], 'study': 'C', 'consumer': 'gpt-6-luna', 'extractor': model, 'status': 'extractor-pending', 'build_draft': built['packet'], 'profile': None})
                    if mapping['status'] != 'complete':
                        pending.append({'cell': mapping['cell_id'], 'study': 'A', 'consumer': 'gpt-6-luna', 'status': row['dispatch_status'], 'error_code': row.get('error_code'), 'profile': None})
                        continue
                    profile = approved(mapping['profile'])
                    assert profile['profile_id'] == mapping['profile_id']
                    consumers = models if config['config_id'] == selection['primary_config_id'] else models[:1]
                    for model in consumers:
                        studies = (['A'] if model == 'gpt-6-luna' else [])
                        if config['config_id'] == selection['primary_config_id']:
                            studies += ['B'] + (['C'] if model != 'gpt-6-sol' else [])
                        draft = predict(profile, release, mapping['profile'], mapping['release'], row['job_id'], identities[model], source['registration'], mapping['cell_id'], studies)
                        matches = reuse_matches(draft, profile)
                        record = add(draft, release, mapping['cell_id'] + '/' + model,
                            'historical-execution-alias' if len(matches) == 1 else 'unleased-draft')
                        if matches:
                            record['historical_matches'] = matches
                            if len(matches) != 1:
                                record['status'] = 'ambiguous-historical-reuse-pending'
                        inventory.append({'cell': mapping['cell_id'], 'profile_id': profile['profile_id'], 'consumer': model, 'draft': record['packet'],
                            'source_condition': 'target-plus-approved-peer-fit' if config['method_id'] == 'P7' else 'original_sparse_fit_v2',
                            'evidence': draft['manifest'].get('scaling_peer_evidence'), 'studies': studies})

            # Select controls only by exact required method/cap/researcher/item schedule.
            for method in selection['controls']:
                for researcher in ('neel_nanda', 'chris_olah'):
                    expected_n = 14 if method in ('lexical_retrieval', 'semantic_retrieval') else 1
                    matches = []
                    for historical in sparse['jobs']:
                        if historical['kind'] != 'predict' or historical['method_id'] != method or historical['researcher_id'] != researcher:
                            continue
                        packet = approved(historical['packet'])
                        wanted_cap = 2048 if method == 'no_profile' else selection['common_personalization_cap']
                        if packet['manifest']['personalization_cap'] == wanted_cap:
                            matches.append((historical, packet))
                    assert len(matches) == expected_n, 'exact sparse control schedule missing or ambiguous'
                    for historical, source in matches:
                        register(source)
                        profile = approved(historical['profile_file'])
                        release = approved(historical['release'])
                        contract_sha = source['manifest']['contract_sha256']
                        origin = source['manifest']['parent_job_ids'][0]
                        cell = '%s/%s/%s' % (method, researcher, digest(source['item_ids']))
                        for model in models:
                            if method in ('lexical_retrieval', 'semantic_retrieval') and model != 'gpt-6-luna':
                                original_build = approved(jobs[origin]['packet'])
                                assert job_id(original_build['manifest']) == origin
                                draft = copy.deepcopy(original_build)
                                draft['lease'] = None
                                draft['config']['consumer_identity'] = identities[model]
                                if method == 'semantic_retrieval':
                                    ref, bundle = semantic_refs[(researcher, source['item_ids'][0])]
                                    assert draft['config']['embedding_bundle'] == bundle
                                manifest = draft['manifest']
                                manifest.pop('job_id')
                                manifest.update(config_hash=digest(draft['config']), extractor=identities[model],
                                    parent_job_ids=list(dict.fromkeys(manifest['parent_job_ids'] + [origin])),
                                    scaling_study='A-deterministic-control-packing', scaling_selection_sha256=selection_ref['sha256'],
                                    scaling_original_build_job_id=origin)
                                limits = {'max_calls': 0, 'max_seconds': 120, 'max_usd': 0.000000001, 'timeout': 60}
                                manifest['allocation'] = {**{k: limits[k] for k in ('max_calls', 'max_seconds', 'max_usd')}, 'cost_mode': 'priced_api', 'authorization_source': None}
                                draft['backend'] = {**limits, 'model': model, 'reasoning': 'medium'}
                                record = add(draft, release, cell + '/' + model)
                                selected_items = [i for i in release['items'] if i['item_id'] in source['item_ids']]
                                future_calls.append({'cell': cell, 'study': 'A-control', 'model': model, 'depends_on': record['packet'],
                                    'bounds': helper.future_prediction_bounds(selected_items, model, consumer_settings, selection['common_personalization_cap'])})
                                pending.append({'cell': cell, 'study': 'A-control', 'consumer': model, 'status': 'deterministic-control-packing-pending',
                                    'build_draft': record['packet'], 'profile': None, 'new_embedding_calls': 0})
                                continue
                            studies = ['A-control'] + (['D'] if method == 'raw_evidence' and diagnostic else [])
                            draft = predict(profile, release, historical['profile_file'], historical['release'], origin, identities[model], source['registration'], cell, studies, source['item_ids'])
                            reuse = reuse_matches(draft, profile)
                            record = add(draft, release, cell + '/' + model, 'historical-execution-alias' if len(reuse) == 1 else 'unleased-draft')
                            record['historical_matches'] = reuse
                            if model == 'gpt-6-luna':
                                assert len(reuse) == 1, 'canonical Luna control reuse must be exact and unique'
                            if method == 'raw_evidence' and diagnostic:
                                diagnostic_row = next(r for r in diagnostic['researchers'] if r['researcher_id'] == researcher)
                                fields = diagnostic_row['diagnostic_source_fields']
                                assert diagnostic_row['release']['sha256'] == historical['release']['sha256']
                                assert fields['documents_hash'] == profile['documents_hash']
                                assert fields['items_hash'] == digest(release['items']) == draft['manifest']['items_hash']
                                assert fields['raw_evidence_hash'] == profile['allowed_source_manifest_hash']
                                assert fields['profile_conditioning'] is False
                                assert fields['items'] == [{'item_id': i['item_id'], 'option_order_id': i['option_order_id'],
                                    'context_sha256': hashlib.sha256(i['context'].encode()).hexdigest(), 'options_sha256': digest(i['options'])} for i in release['items']]
                                assert fields['task_context_hash'] == digest([i['context'] for i in release['items']])
                                approved(diagnostic_row['subset'])
                                approved(diagnostic_row['withholding_receipt'])
                                aliases.append({'study': 'D', 'canonical_control_draft': record['packet'], 'consumer': model, 'researcher_id': researcher,
                                    'diagnostic_panel': selection['diagnostic_panel'], 'new_independent_observations': 0, 'additional_calls': 0})
            assert ledger.summary()['attempts'] == http.call_count == complete.call_count == 0
    for path, expected in used.items():
        assert sha(path) == expected, 'input changed during preparation'
    call_plan = {}
    for model in models:
        ready = [d for d in drafts if d['model'] == model and d['status'] == 'unleased-draft']
        future = [f for f in future_calls if f['model'] == model]
        call_plan[model] = {'ready_paid_extraction_calls': sum(d['max_calls'] for d in ready if d['kind'] == 'build'),
            'ready_prediction_calls': sum(d['max_calls'] for d in ready if d['kind'] == 'predict'),
            'future_prediction_calls': sum(len(f['bounds']) for f in future),
            'zero_call_packing_builds': sum(d['kind'] == 'build' and d['max_calls'] == 0 for d in ready),
            'ready_reservation_max_usd': round(sum(d['max_usd_reservation'] for d in ready), 9),
            'future_reservation_max_usd': round(sum(b['max_usd'] for f in future for b in f['bounds']), 9),
            'job_wall_ceiling_sum_seconds': sum(d['max_seconds'] for d in ready) + sum(len(f['bounds']) * 60 + 60 for f in future),
            'api_timeout_sum_seconds': sum(d['max_calls'] * (180 if d['kind'] == 'build' else 60) for d in ready) + sum(len(f['bounds']) * 60 for f in future),
            'future_bounds': future}
    report = {'schema_version': 'selected-scaling-mechanical-readiness-v1', 'status': 'mechanically-prepared-unleased-coordinator-adopted-selection',
        'selection': selection_ref, 'contract': CONTRACT, 'runtime': runtime, 'compiler_source_sha256': sha(OWN_ROOT / 'autoresearch/taste/overnight/scaling.py'),
        'helper_source_sha256': sha(HERE / 'selected_scaling_bindings_v1.py'), 'recipe_source_sha256': sha(__file__), 'validation': validation,
        'finite_call_plan': call_plan, 'uncertain_request_denylist': DENYLIST,
        'new_request_collision_count': sum(bool(d['uncertain_request_collisions']) and d['status'] != 'historical-execution-alias' for d in drafts),
        'worst_case_proposal_usd': round(sum(p['ready_reservation_max_usd'] + p['future_reservation_max_usd'] for p in call_plan.values()), 9),
        'api_timeout_sum_seconds': sum(p['api_timeout_sum_seconds'] for p in call_plan.values()),
        'job_wall_ceiling_sum_seconds': sum(p['job_wall_ceiling_sum_seconds'] for p in call_plan.values()),
        'staged_proposal_requires_coordinator_adoption': [
            '0: finish all112 deterministic lexical/semantic packing builds (zero provider/embedding calls), then replace future bounds with exact outgoing hashes/prices.',
            '1: primary saved-profile StudyB plus four mandatory controls, paired across researcher/item/consumer. Fixed order: semantic item IDs, researcher IDs, model panel S/M/L, then control declaration order and primary B; retain both option orders together.',
            '2: selected primary StudyA Sol/Astra extraction, then its valid joint consumers and C cross-consumer cells; same fixed researcher/model/item order.',
            '3: remaining selected StudyA configurations in receipt order P7 then P3; preserve unavailable Neel P3 rep0 and future failed/empty profiles.',
            'Before each admission, coordinator requires exact request noncollision, actual spend + active holds + proposed reservation <=80 and timeout fitting deadline. Mark untouched tail unavailable-budget-or-deadline without changing matched settings.',
            'These priorities are a proposal, not a second scheduler; root alone grants leases and dispatches.'], 'drafts': drafts, 'profile_bindings': inventory, 'pending_dependencies': pending, 'diagnostic_aliases': aliases,
        'original_index_counts': index.get('counts'), 'replicate_build_counts': repeat_build.get('build_status_counts'),
        'replicate_prediction_index': selection['replicate_prediction_completion_index'], 'control_inputs': selection['control_inputs'],
        'semantic_index': selection['semantic_index'], 'semantic_bundle_files_verified': len(semantic_refs), 'driver_preparation_checks': prep_count,
        'api_calls': 0, 'completion_calls': 0, 'isolated_test_ledger_attempts': 0, 'execution_authorized': False, 'adoption': ADOPTION, 'adoption_verification': ADOPTION_VERIFICATION,
        'original_inputs_unchanged': True, 'all_saved_drafts_unleased': True, 'private_payloads_printed': False,
        'limits': ['All budgets are conservative proposals; coordinator alone allocates and schedules before the deadline.',
            'No API admission health is implied. Current provider interruption/recovery remains with coordinator/01.',
            'Peer P7 has extra approved fit sources; cross-source-condition comparisons do not hold evidence constant.',
            'No extraction-pending profile is replaced with an old Luna or another replicate profile.',
            'Source-defined D aliases exact raw controls and creates no extra observations.',
            'CLI and utility execution require their separate owners and are not provided here.',
            'Historical execution alias drafts are evidence records, not requests to replay completed calls.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(used.items())]}
    report_ref = save('safe-readiness-report.json', report)
    print(json.dumps({'safe_report': report_ref, 'private_directory': str(private), 'drafts': len(drafts),
        'build_drafts': sum(d['kind']=='build' for d in drafts), 'prediction_drafts': sum(d['kind']=='predict' for d in drafts),
        'historical_aliases': sum(d['status']=='historical-execution-alias' for d in drafts), 'pending_dependencies': len(pending),
        'diagnostic_aliases': len(aliases), 'driver_preparation_checks': prep_count, 'api_calls': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
