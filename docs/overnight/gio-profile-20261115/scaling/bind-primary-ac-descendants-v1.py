"""Bind actual valid primary P8 descendants; retain invalid-parent coverage."""
import copy
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUNTIME_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
READY = {'path': '/private/tmp/gio-p8-first4-native-admissions-v1/ready-index.json', 'sha256': 'ccbc64f715632f2f621e54b3d7e30d7e357a5397cfc99fd1458c9bfd3e0b580f'}
TERMINAL = {'path': '/private/tmp/gio-profile-20261115-coordinator/p8-first4-supervisor-v1/supervisor-terminal.json', 'sha256': '485336a94b54c6af8ddbd51db77d0b20d179b0d45c31b76e43ac1ea8e4d31eff'}
VERIFIED = {'path': '/private/tmp/gio-profile-20261115-coordinator/p8-first4-supervisor-v1/verified.json', 'sha256': '10f2f1ffb05099d3755809b5d56ad67e4fd3d7be8de77cd1da15f1ba8887149c'}
TYPED_DENYLIST = {'path': '/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json', 'sha256': '7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'}
PRIOR_READY = {'path': '/private/tmp/gio-profile-20261115-scaling/mechanical-readiness-only-selected-v1-92l7vewk/safe-readiness-report.json', 'sha256': 'ec31be71a741cfe4c986ff5f0183a3f7c6045418aef69ba9ee25c7ac382c2b94'}
COMPLETION = {'path': '/private/tmp/gio-profile-20261115-scaling/first-stage-completion-metadata-v1-iat6jrgt/completion-index.json', 'sha256': 'd6906181c9043f0a75f0194277eb5a1566931aaf55eada91868236e4a3a19880'}
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
    helper = load('actual_primary_ac_leaf_helper', helper_path)
    driver_path = runtime_root / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
    driver = load('actual_primary_ac_frozen_driver', driver_path)
    used = {}
    def approved(ref):
        helper._reference(ref)
        p = Path(ref['path'])
        assert 'lease' not in p.parts and p.suffix not in ('.sqlite', '.sqlite3', '.db')
        assert p.name != 'result.json'  # Result references stay opaque; profiles carry status.
        raw = p.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ref['sha256'], 'input file hash changed'
        used[str(p)] = ref['sha256']
        return json.loads(raw)

    ready, terminal, verified = approved(READY), approved(TERMINAL), approved(VERIFIED)
    assert terminal['index'] == READY and terminal['verified'] == VERIFIED and terminal['status'] == 'complete'
    assert terminal['child_process_terminal'] is True and terminal['native_accounting_drain_verified'] is True
    assert terminal['future_prediction_jobs_admitted'] == ready['future_prediction_jobs_admitted'] == 0
    assert verified['diagnostics']['actual_open_events'] == verified['native']['attempted_calls'] == 4
    assert verified['native']['known_spent_nanos'] == 360_920_000
    assert verified['native']['ledger_attempts'] - verified['baseline']['attempts'] == 4
    assert verified['native']['ledger_spent_nanos'] - verified['baseline']['spent'] == 360_920_000
    prepared, evidence = approved(ready['prepared']), approved(ready['evidence'])
    prior, completion = approved(PRIOR_READY), approved(COMPLETION)
    selection = approved(prior['selection'])
    approved(TYPED_DENYLIST)  # Pin only; no Role09 collision clearance or guard implementation.
    assert prepared['code_sha'] == RUNTIME_SHA and evidence['scientific_fields_unchanged'] is True
    primary = next(c for c in selection['selected_configs'] if c['config_id'] == selection['primary_config_id'])
    assert primary['method_id'] == 'P8' and primary['personalization_cap'] == 8192 and primary['evidence_policy'] == 'explicit-only'
    original_instances = {m['researcher_id']: m for m in primary['researcher_mappings']}
    original_drafts = {r['packet']['sha256']: r for r in prior['drafts']}
    selected_dependencies = [r for r in prior['pending_dependencies'] if r.get('cell', '').startswith(primary['config_id'] + '/')]
    assert len(selected_dependencies) == 6
    mappings = {m['job_id']: m for m in evidence['mappings']}
    outcomes = {o['job_id']: o for o in verified['native']['outcomes']}
    assert len(mappings) == len(outcomes) == len(prepared['jobs']) == 4
    runtime = prior['runtime']
    assert sha(driver_path) == runtime['driver_sha256']
    assert sha(runtime_root / 'autoresearch/taste/overnight/backends.py') == runtime['backend_sha256']
    private = Path(tempfile.mkdtemp(prefix='primary-ac-valid-descendants-v1-', dir='/private/tmp/gio-profile-20261115-scaling'))
    def save(name, body):
        p = private / name
        data = (canonical_json(body) + '\n').encode()
        with p.open('xb') as stream:
            stream.write(data)
        p.chmod(0o600)
        return {'path': str(p), 'sha256': hashlib.sha256(data).hexdigest()}

    parents, coverage, packets, c_joint_aliases, seen = [], [], [], [], set()
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix='isolated-test-ledger-', dir=private) as temporary:
        ledger = backends.DollarLedger(Path(temporary) / 'ledger.sqlite', max_usd=500, deadline='2099-01-01T00:00:00Z')
        with patch('urllib.request.urlopen', side_effect=AssertionError('no HTTP in descendant binding')) as http, \
             patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('no completion in descendant binding')) as complete:
            for actual_ref in prepared['jobs']:
                actual = approved(actual_ref)
                jid = actual['manifest']['job_id']
                assert jid == job_id(actual['manifest']) and jid in mappings and jid in outcomes
                mapping, outcome = mappings[jid], outcomes[jid]
                old_ref = mapping['original_draft']
                old = approved(old_ref)
                assert original_drafts[old_ref['sha256']]['packet'] == old_ref
                stripped = copy.deepcopy(actual['manifest'])
                stripped.pop('job_id')
                stripped['allocation']['authorization_source'] = None
                assert digest(stripped) == digest(old['manifest'])
                assert digest(actual['config']) == digest(old['config'])
                assert actual['release']['sha256'] == old['release']['sha256']
                assert actual['backend']['max_calls'] == old['backend']['max_calls'] == 1
                assert actual['manifest']['method_id'] == 'P8' and actual['manifest']['kind'] == 'build'
                profile = ProfileArtifact.from_dict(approved(outcome['profile'])).to_dict()
                receipt = approved(outcome['receipt'])
                assert receipt['job_id'] == jid and receipt['manifest_sha256'] == digest(actual['manifest'])
                assert receipt['status'] == profile['status'] == outcome['status']
                assert receipt['usage']['attempted_calls'] == outcome['attempted_calls'] == 1
                assert digest(profile['config']) == digest(actual['config'])
                assert profile['code_sha'] == RUNTIME_SHA and profile['replicate_id'] == 0 and profile['personalization_cap'] == 8192
                assert profile['method_id'] == 'P8' and profile['extractor'] == actual['manifest']['extractor']
                researcher, extractor = profile['researcher_id'], profile['extractor']['model']
                assert researcher in original_instances and extractor in ('gpt-6-sol', 'gpt-6-astra')
                assert (researcher, extractor) not in seen
                seen.add((researcher, extractor))
                release = approved(actual['release'])
                mapping0 = original_instances[researcher]
                assert release['researcher_id'] == researcher and release['items_sha256'] == mapping0['items_sha256']
                assert release['target_bundle_sha256'] == mapping0['target_bundle_sha256']
                assert actual['manifest']['source_manifest_hash'] == mapping0['source_manifest_hash']
                assert len(release['items']) == 14 and digest(release['items']) == release['items_sha256']
                parent = {'actual_build_job_id': jid, 'actual_prepared_packet': actual_ref,
                    'actual_manifest_sha256': digest(actual['manifest']), 'original_unleased_build_draft': old_ref,
                    'actual_profile': outcome['profile'], 'profile_id': profile['profile_id'], 'researcher_id': researcher,
                    'extractor': extractor, 'parent_status': profile['status'], 'parent_error_code': profile['error_code'],
                    'rendered_utf8_bytes': profile['token_count'], 'count_method': profile['token_count_method'], 'profile_byte_cap': 8192,
                    'receipt': outcome['receipt'], 'result_reference_only_not_opened': outcome['result'],
                    'classification_owner': '04; recorded artifact status/error only, no new failure classification',
                    'known_build_spend_nanos_once': outcome['known_spent_nanos']}
                parents.append(parent)
                dependencies = [d for d in selected_dependencies if d['build_draft'] == old_ref]
                assert len(dependencies) == (2 if extractor == 'gpt-6-astra' else 1)
                for dependency in dependencies:
                    study, model = dependency['study'], dependency['consumer']
                    assert (study == 'A' and model == extractor) or (study == 'C' and extractor == 'gpt-6-astra' and model == 'gpt-6-luna')
                    packet_ref, request_pins = None, []
                    if profile['status'] == 'complete':
                        driver._register(actual['registration'], 'P8')
                        identity = backend_identity(backends.OpenAIResponsesBackend(model=model, reasoning='medium', ledger=ledger, max_usd=10, timeout=60))
                        settings = {k: selection['consumer_settings'][k] for k in ('temperature', 'max_tokens')}
                        draft = helper.prediction_packet(profile, release, profile_ref=outcome['profile'], release_ref=actual['release'],
                            origin_job_id=jid, identity=identity, settings=settings, timeout=selection['consumer_settings']['timeout'],
                            logical_cap=8192, runtime=runtime, contract_sha256=actual['manifest']['contract_sha256'],
                            registration=actual['registration'], selection_sha256=prior['selection']['sha256'],
                            index_sha256=selection['original_complete_index']['sha256'], selected_cell_id=dependency['cell'], studies=[study])
                        draft['manifest']['scaling_actual_parent_lineage'] = parent
                        assert draft['manifest']['parent_job_ids'] == [jid]
                        test = copy.deepcopy(draft)
                        test['lease'] = {'lease_id': 'discarded-primary-ac-bind-test', 'owner': 'readiness-only', 'expires_at': runtime['deadline']}
                        test['manifest']['allocation']['authorization_source'] = 'discarded-in-memory-test-only-no-execution-authority'
                        batch = {'campaign_id': selection['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                            'release_schema_version': release['schema_version'], 'release_scope': release['scope'],
                            'contract': {'sha256': actual['manifest']['contract_sha256']}, 'ledger': {'max_usd': 500}}
                        with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                            driver._prepare_packet(test, batch, ledger)
                        packet_ref = save('unleased-prediction-%02d.json' % len(packets), draft)
                        request_pins = draft['manifest']['scaling_payload_pins']
                        packets.append({'packet': packet_ref, 'study': study, 'researcher_id': researcher, 'extractor': extractor,
                            'consumer': model, 'actual_parent_job_id': jid, 'profile_id': profile['profile_id'], 'profile': outcome['profile'],
                            'settings': settings, 'effective_consumer': identity, 'max_calls': draft['backend']['max_calls'],
                            'max_seconds': draft['backend']['max_seconds'], 'timeout': draft['backend']['timeout'],
                            'max_usd_reservation': draft['backend']['max_usd'], 'request_pins': request_pins,
                            'status': 'unleased-ready-pending-owner-typed11-admission'})
                    else:
                        assert profile['status'] == 'invalid'
                    for number, item in enumerate(release['items']):
                        row_id = digest({'study': study, 'parent': jid, 'consumer': model, 'item_id': item['item_id']})
                        row = {'coverage_row_id': row_id, 'study': study, 'researcher_id': researcher,
                            'method_id': 'P8', 'extractor': extractor, 'consumer': model, 'actual_parent_job_id': jid,
                            'profile_id': profile['profile_id'], 'profile_reference': outcome['profile'],
                            'parent_status': profile['status'], 'parent_error_code': profile['error_code'],
                            'item_id': item['item_id'], 'option_order_id': item['option_order_id'], 'item_sha256': digest(item),
                            'status': 'unleased_ready' if packet_ref else 'unavailable_invalid_parent',
                            'prediction_attempted': False, 'prediction_outcome': None, 'packet': packet_ref,
                            'request_identity': request_pins[number] if packet_ref else None,
                            'frozen_dependency': dependency, 'source_manifest_sha256': actual['manifest']['source_manifest_hash'],
                            'items_sha256': release['items_sha256'], 'context_sha256': hashlib.sha256(item['context'].encode()).hexdigest(),
                            'options_sha256': digest(item['options'])}
                        coverage.append(row)
                        if study == 'A' and extractor == 'gpt-6-astra':
                            c_joint_aliases.append({'study': 'C', 'extractor': extractor, 'consumer': model,
                                'researcher_id': researcher, 'item_id': item['item_id'], 'alias_of_A_row': row_id,
                                'status': row['status'], 'additional_requests': 0})
            assert ledger.summary()['attempts'] == http.call_count == complete.call_count == 0
    assert seen == {(r, m) for r in original_instances for m in ('gpt-6-sol', 'gpt-6-astra')}
    assert Counter(p['parent_status'] for p in parents) == {'complete': 1, 'invalid': 3}
    assert sum(p['known_build_spend_nanos_once'] for p in parents) == verified['native']['known_spent_nanos']
    assert len(coverage) == 84 and Counter(r['status'] for r in coverage) == {'unleased_ready': 14, 'unavailable_invalid_parent': 70}
    assert len(packets) == 1 and packets[0]['researcher_id'] == 'neel_nanda' and packets[0]['consumer'] == 'gpt-6-sol'
    existing = []
    for row in completion['luna_alias_rows']:
        if row['method_id'] == 'P8':
            researcher = next(r for r,m in original_instances.items() if m['profile_id'] == row['profile_id'])
            existing.append({'studies': ['A', 'C'], 'researcher_id': researcher, 'extractor': 'gpt-6-luna',
                'consumer': 'gpt-6-luna', 'item_id': row['item_id'], 'option_order_id': row['option_order_id'],
                'profile_id': row['profile_id'], 'historical_job_id': row['historical_job_id'], 'historical_packet': row['historical_packet'],
                'status': 'historical_completed_alias', 'new_calls': 0, 'new_cost': 0, 'lineage': row})
    by_job = {j['job_id']: j for j in completion['new_jobs']}
    for row in completion['new_request_rows']:
        if row['method_id'] == 'P8' and row['model'] == 'gpt-6-astra':
            job = by_job[row['job_id']]
            assert job['profile_id'] == original_instances[row['researcher_id']]['profile_id']
            existing.append({'studies': ['C'], 'researcher_id': row['researcher_id'], 'extractor': 'gpt-6-luna',
                'consumer': 'gpt-6-astra', 'item_id': row['item_id'], 'option_order_id': row['option_order_id'],
                'profile_id': job['profile_id'], 'historical_job_id': row['job_id'], 'historical_packet': job['actual_prepared_packet'],
                'status': 'first_stage_completed_alias', 'new_calls': 0, 'new_cost': 0, 'lineage': row})
    assert len(existing) == 56 and len(c_joint_aliases) == 28
    for path, expected in used.items():
        assert sha(path) == expected, 'input changed during binding'
    index = {'schema_version': 'primary-ac-actual-descendant-bindings-v1', 'status': 'valid-descendant-prepared-invalid-coverage-retained',
        'selection': prior['selection'], 'actual_parent_admissions': READY, 'parent_terminal': TERMINAL,
        'parent_outcome_index': VERIFIED, 'typed_denylist_future_owner_admission': TYPED_DENYLIST,
        'runtime_sha': RUNTIME_SHA, 'helper_sha256': HELPER_SHA, 'generator_sha256': sha(__file__),
        'parents': parents, 'new_descendant_coverage_rows': coverage, 'ready_prediction_packets': packets,
        'existing_completed_execution_aliases': existing, 'C_large_large_aliases_of_A_rows': c_joint_aliases,
        'counts': {'actual_parent_builds': 4, 'complete_parents': 1, 'invalid_parents': 3,
            'new_planned_descendant_rows': 84, 'new_unleased_ready_rows': 14, 'new_unavailable_invalid_parent_rows': 70,
            'new_planned_A_rows': 56, 'new_planned_cross_C_rows': 28, 'existing_completed_alias_rows': 56,
            'unique_primary_A_C_execution_slots': 140, 'A_logical_rows': 84, 'C_logical_rows': 112,
            'C_large_large_alias_rows': 28, 'driver_preparation_checks': 1, 'new_prediction_call_ceiling': 14},
        'observed_parent_build_known_spend_nanos_once': 360_920_000, 'cumulative_same_ledger_attempts_from_owner_metadata': 284,
        'cumulative_same_ledger_spend_nanos_from_owner_metadata': 3_260_300_000,
        'new_prediction_max_usd_sum': packets[0]['max_usd_reservation'], 'api_calls_by_binder': 0,
        'completion_calls_by_binder': 0, 'isolated_test_ledger_attempts': 0, 'execution_authorized': False,
        'original_inputs_unchanged': True, 'all_saved_packets_unleased': True,
        'limits': ['HTTP/accounting completion is separate from profile validity. Only one actual complete parent receives a descendant packet.',
            'All70 invalid-parent prediction rows remain unavailable/unattempted; no repair, regeneration, substitution, selection or replicate change.',
            'P8 artifact error codes/counts are preserved;04 owns safe failure classification and scoring. No result body, gold label or private target read.',
            'Existing Luna-profile A/C cells reuse exactly completed original/first-stage executions; StudyB Luna-to-Sol is never substituted for new Sol-to-Sol StudyA.',
            'C Astra-to-Astra aliases the same A joint rows, including their unavailable status; it adds no requests. Counts distinguish logical arms from execution slots.',
            'Typed11 denylist is a future owner01/coordinator admission requirement, not a Role09 all-clear claim. Both identity conventions and originals remain owner-managed.',
            'No live ledger, native claims, lease issuance, producer or provider call. Test authority discarded; temporary test ledger removed.',
            'Budget/holds/deadline/lease and exact outgoing-request checks remain coordinator-only before the14 possible calls.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(used.items())]}
    index_ref = save('primary-ac-ready-index.json', index)
    print(json.dumps({'ready_index': index_ref, 'counts': index['counts'], 'new_prediction_max_usd_sum': index['new_prediction_max_usd_sum'],
        'api_calls_by_binder': 0, 'execution_authorized': False}, sort_keys=True))


if __name__ == '__main__':
    main()
