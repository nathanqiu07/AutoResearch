"""Bind actual P7/P3 joint descendants without selection or execution."""
import copy
import hashlib
import importlib.util
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OWN_ROOT = HERE.parents[3]
RUNTIME_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
READY = {'path': '/private/tmp/gio-remaining8-native-admissions-v2/ready-index.json', 'sha256': '9fabeceb3ef9c4006e5881c4c3daf90304f1476479da3dc0978049a5d7e87d78'}
TERMINAL = {'path': '/private/tmp/gio-profile-20261115-coordinator/remaining8-build-supervisor-v2/supervisor-terminal.json', 'sha256': '3595ed30aa8982f8acc77dc36aebd63e2d3d266cf1eb7cbf8179aa77550be6c4'}
VERIFIED = [
    {'path': '/private/tmp/gio-profile-20261115-coordinator/remaining8-build-supervisor-v2/verified-P7.json', 'sha256': 'fa95b16730c9648815d3e3c9f0ebbf5696f02c01653c15c1547f936fc2d71eb3'},
    {'path': '/private/tmp/gio-profile-20261115-coordinator/remaining8-build-supervisor-v2/verified-P3.json', 'sha256': '714499f912de319d05488967c470adb65759dac81d30badbd0ca954db0886867'}]
PREDECESSOR = {'path': '/private/tmp/gio-profile-20261115-coordinator/accounting/remaining8-closed-predecessor-v1.json', 'sha256': 'dcb4f58e868a343465367529dc033465dc937e527054f18eeae1f40d9c25728b'}
TYPED_DENYLIST = {'path': '/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json', 'sha256': '7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'}
PRIOR_READY = {'path': '/private/tmp/gio-profile-20261115-scaling/mechanical-readiness-only-selected-v1-92l7vewk/safe-readiness-report.json', 'sha256': 'ec31be71a741cfe4c986ff5f0183a3f7c6045418aef69ba9ee25c7ac382c2b94'}
HELPER_SHA = '740f4517d67379af5bc75d772495114599c58dc83424e4c164b0605ec2b9dcad'
COMPILER_SHA = '1d5e646c35c48d6cc8b50ae6cdeb4db3927fe702e27e58bdb48b4cdfb8588b11'


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
    compiler_path = OWN_ROOT / 'autoresearch/taste/overnight/scaling.py'
    assert sha(helper_path) == HELPER_SHA and sha(compiler_path) == COMPILER_SHA
    helper = load('remaining8_leaf_helper', helper_path)
    compiler = load('autoresearch.taste.overnight.remaining8_compiler', compiler_path)
    driver_path = runtime_root / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
    driver = load('remaining8_frozen_driver', driver_path)
    used = {}
    def approved(ref, raw=False):
        helper._reference(ref)
        p = Path(ref['path'])
        assert 'lease' not in p.parts and 'native-claims' not in p.parts
        assert p.suffix not in ('.sqlite', '.sqlite3', '.db') and p.name not in ('result.json', 'claim.json', '.env')
        data = p.read_bytes()
        assert hashlib.sha256(data).hexdigest() == ref['sha256'], 'input file hash changed'
        used[str(p)] = ref['sha256']
        return data.decode('utf-8') if raw else json.loads(data)

    ready, terminal, predecessor = approved(READY), approved(TERMINAL), approved(PREDECESSOR)
    assert terminal['index'] == READY and terminal['completed_verified_batches'] == VERIFIED
    assert terminal['status'] == predecessor['state'] == 'complete' and predecessor['supervisor_terminal'] == TERMINAL
    assert predecessor['verified_batches'] == VERIFIED and predecessor['next_execution_authorized'] is False
    assert terminal['child_process_terminal'] is True and terminal['native_accounting_drain_verified'] is True
    assert terminal['future_prediction_jobs_admitted'] == ready['future_prediction_jobs_admitted'] == 0
    assert [a['block'] for a in ready['admissions']] == ['P7', 'P3']
    assert ready['jobs'] == ready['max_calls'] == terminal['planned_jobs'] == terminal['planned_call_ceiling'] == 8
    assert terminal['known_verified_attempts'] - terminal['baseline']['attempts'] == 8
    assert terminal['known_verified_spend_nanos'] - terminal['baseline']['spent'] == 538445000
    assert ready['unknown_denylist'] == TYPED_DENYLIST
    approved(TYPED_DENYLIST)  # Pin only; owner01 performs both-convention admission checks.
    prior = approved(PRIOR_READY)
    selection = approved(prior['selection'])
    configs = {c['method_id']: c for c in selection['selected_configs'] if c['method_id'] in ('P7', 'P3')}
    assert set(configs) == {'P7', 'P3'} and selection['common_personalization_cap'] == 8192
    original_drafts = {r['packet']['sha256']: r for r in prior['drafts']}
    runtime = prior['runtime']
    assert sha(driver_path) == runtime['driver_sha256']
    assert sha(runtime_root / 'autoresearch/taste/overnight/backends.py') == runtime['backend_sha256']
    private = Path(tempfile.mkdtemp(prefix='remaining8-valid-descendants-v1-', dir='/private/tmp/gio-profile-20261115-scaling'))
    def save(name, body):
        p = private / name
        data = (canonical_json(body) + '\n').encode()
        with p.open('xb') as stream:
            stream.write(data)
        p.chmod(0o600)
        return {'path': str(p), 'sha256': hashlib.sha256(data).hexdigest()}

    parents, coverage, packets, batches, seen = [], [], [], [], set()
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix='isolated-test-ledger-', dir=private) as temporary:
        ledger = backends.DollarLedger(Path(temporary) / 'ledger.sqlite', max_usd=500, deadline='2099-01-01T00:00:00Z')
        with patch('urllib.request.urlopen', side_effect=AssertionError('no HTTP in descendant binding')) as http, \
             patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('no completion in descendant binding')) as complete:
            for admission, verified_ref in zip(ready['admissions'], VERIFIED):
                method = admission['block']
                verified, prepared, evidence = approved(verified_ref), approved(admission['prepared']), approved(admission['evidence'])
                assert verified['block'] == evidence['block'] == method and evidence['scientific_fields_unchanged'] is True
                assert verified['diagnostics']['actual_open_events'] == verified['native']['attempted_calls'] == 4
                assert prepared['code_sha'] == RUNTIME_SHA and admission['jobs'] == admission['max_calls'] == 4
                schema = 'released-development-v2-p7-peers-v1' if method == 'P7' else 'released-development-v2'
                assert prepared['release_schema_version'] == admission['release_schema_version'] == schema
                summary = approved(verified['native']['summary'])
                assert summary['batch_id'] == prepared['batch_id'] and summary['status'] == 'complete'
                assert summary['counts']['listed'] == summary['counts']['dispatched'] == 4 and summary['counts']['not_dispatched'] == 0
                config = configs[method]
                assert config['personalization_cap'] == 8192
                instances = {m['researcher_id']: m for m in config['researcher_mappings']}
                dependencies = [d for d in prior['pending_dependencies'] if d.get('cell', '').startswith(config['config_id'] + '/') and d.get('build_draft')]
                assert len(dependencies) == 4 and all(d['study'] == 'A' for d in dependencies)
                mappings = {m['job_id']: m for m in evidence['mappings']}
                outcomes = {o['job_id']: o for o in verified['native']['outcomes']}
                assert len(mappings) == len(outcomes) == len(prepared['jobs']) == 4
                batch_packets, batch_parent_cost = [], 0
                for actual_ref in prepared['jobs']:
                    actual = approved(actual_ref)
                    jid = actual['manifest']['job_id']
                    assert jid == job_id(actual['manifest']) and jid in mappings and jid in outcomes
                    mapping, outcome = mappings.pop(jid), outcomes.pop(jid)
                    old_ref = mapping['original_draft']
                    old = approved(old_ref)
                    assert original_drafts[old_ref['sha256']]['packet'] == old_ref
                    stripped = copy.deepcopy(actual['manifest'])
                    stripped.pop('job_id')
                    stripped['allocation']['authorization_source'] = None
                    assert digest(stripped) == digest(old['manifest'])
                    assert digest(actual['config']) == digest(old['config']) and actual['release']['sha256'] == old['release']['sha256']
                    assert digest(actual['backend']) == digest(old['backend']) and actual['backend']['max_calls'] == 1
                    assert actual['manifest']['method_id'] == method and actual['manifest']['kind'] == 'build'
                    profile = ProfileArtifact.from_dict(approved(outcome['profile'])).to_dict()
                    receipt = approved(outcome['receipt'])
                    assert receipt['job_id'] == jid and receipt['manifest_sha256'] == digest(actual['manifest'])
                    assert receipt['status'] == profile['status'] == outcome['status']
                    assert receipt['usage']['attempted_calls'] == outcome['attempted_calls'] == 1
                    assert receipt['usage']['cache_hits'] == receipt['usage']['uncertain_attempts'] == 0
                    assert receipt['usage']['budget_detail']['reported_usage_complete'] is True
                    assert Decimal(str(receipt['usage']['reported_api_usd'])) * 1_000_000_000 == outcome['known_spent_nanos']
                    batch_parent_cost += outcome['known_spent_nanos']
                    assert digest(profile['config']) == digest(actual['config'])
                    assert profile['code_sha'] == RUNTIME_SHA and profile['replicate_id'] == 0 and profile['personalization_cap'] == 8192
                    assert profile['method_id'] == method and profile['extractor'] == actual['manifest']['extractor']
                    researcher, extractor = profile['researcher_id'], profile['extractor']['model']
                    assert researcher in instances and extractor in ('gpt-6-sol', 'gpt-6-astra')
                    assert (method, researcher, extractor) not in seen
                    seen.add((method, researcher, extractor))
                    release = approved(actual['release'])
                    instance = instances[researcher]
                    assert release['schema_version'] == schema and release['scope'] == prepared['release_scope']
                    assert release['researcher_id'] == researcher and release['items_sha256'] == instance['items_sha256']
                    assert release['target_bundle_sha256'] == instance['target_bundle_sha256']
                    assert actual['manifest']['source_manifest_hash'] == instance['source_manifest_hash']
                    assert len(release['items']) == 14 and digest(release['items']) == release['items_sha256']
                    peer_parents = None
                    peer_proof = None
                    if method == 'P7':
                        peer_parents = [{'researcher_id': p['researcher_id'], 'release_json': approved(p['release'], raw=True)} for p in release['parent_releases']]
                        peer_proof = compiler._peer_release_proof(release, peer_parents, method)
                    parent = {'method_id': method, 'actual_build_job_id': jid, 'actual_prepared_packet': actual_ref,
                        'actual_manifest_sha256': digest(actual['manifest']), 'original_unleased_build_draft': old_ref,
                        'actual_profile': outcome['profile'], 'profile_id': profile['profile_id'], 'researcher_id': researcher,
                        'extractor': extractor, 'parent_status': profile['status'], 'parent_error_code': profile['error_code'],
                        'rendered_utf8_bytes': profile['token_count'], 'count_method': profile['token_count_method'], 'profile_byte_cap': 8192,
                        'release': actual['release'], 'release_schema_version': schema, 'peer_evidence': peer_proof,
                        'receipt': outcome['receipt'], 'result_reference_only_not_opened': outcome['result'],
                        'classification_owner': '04; recorded artifact status/error only',
                        'known_build_spend_nanos_once': outcome['known_spent_nanos']}
                    parents.append(parent)
                    matches = [d for d in dependencies if d['build_draft'] == old_ref]
                    assert len(matches) == 1
                    dependency = matches[0]
                    assert dependency['study'] == 'A' and dependency['consumer'] == extractor
                    packet_ref, request_pins = None, []
                    if profile['status'] == 'complete':
                        driver._register(actual['registration'], method)
                        identity = backend_identity(backends.OpenAIResponsesBackend(model=extractor, reasoning='medium', ledger=ledger, max_usd=10, timeout=60))
                        settings = {k: selection['consumer_settings'][k] for k in ('temperature', 'max_tokens')}
                        draft = helper.prediction_packet(profile, release, profile_ref=outcome['profile'], release_ref=actual['release'],
                            origin_job_id=jid, identity=identity, settings=settings, timeout=selection['consumer_settings']['timeout'],
                            logical_cap=8192, runtime=runtime, contract_sha256=actual['manifest']['contract_sha256'],
                            registration=actual['registration'], selection_sha256=prior['selection']['sha256'],
                            index_sha256=selection['original_complete_index']['sha256'], selected_cell_id=dependency['cell'], studies=['A'],
                            compiler=compiler, peer_parent_releases=peer_parents)
                        draft['manifest']['scaling_actual_parent_lineage'] = parent
                        assert draft['manifest']['parent_job_ids'] == [jid]
                        assert draft['lease'] is None and draft['manifest']['allocation']['authorization_source'] is None
                        test = copy.deepcopy(draft)
                        test['lease'] = {'lease_id': 'discarded-remaining8-bind-test', 'owner': 'readiness-only', 'expires_at': runtime['deadline']}
                        test['manifest']['allocation']['authorization_source'] = 'discarded-in-memory-test-only-no-execution-authority'
                        batch = {'campaign_id': selection['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                            'release_schema_version': schema, 'release_scope': release['scope'],
                            'contract': {'sha256': actual['manifest']['contract_sha256']}, 'ledger': {'max_usd': 500}}
                        with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                            driver._prepare_packet(test, batch, ledger)
                        packet_ref = save('unleased-%s-prediction-%02d.json' % (method, len(packets)), draft)
                        request_pins = draft['manifest']['scaling_payload_pins']
                        packets.append({'packet': packet_ref, 'study': 'A', 'method_id': method, 'researcher_id': researcher,
                            'extractor': extractor, 'consumer': extractor, 'actual_parent_job_id': jid,
                            'profile_id': profile['profile_id'], 'profile': outcome['profile'], 'release': actual['release'],
                            'release_schema_version': schema, 'release_scope': release['scope'], 'peer_evidence': peer_proof,
                            'settings': settings, 'effective_consumer': identity, 'max_calls': draft['backend']['max_calls'],
                            'max_seconds': draft['backend']['max_seconds'], 'timeout': draft['backend']['timeout'],
                            'max_usd_reservation': draft['backend']['max_usd'], 'request_pins': request_pins,
                            'status': 'unleased-ready-pending-owner-typed11-admission'})
                        batch_packets.append(packets[-1])
                    else:
                        assert profile['status'] == 'invalid' and (method, researcher, extractor) == ('P3', 'neel_nanda', 'gpt-6-astra')
                    for number, item in enumerate(release['items']):
                        coverage.append({'coverage_row_id': digest({'study': 'A', 'parent': jid, 'consumer': extractor, 'item_id': item['item_id']}),
                            'study': 'A', 'researcher_id': researcher, 'method_id': method, 'extractor': extractor, 'consumer': extractor,
                            'actual_parent_job_id': jid, 'profile_id': profile['profile_id'], 'profile_reference': outcome['profile'],
                            'parent_status': profile['status'], 'parent_error_code': profile['error_code'],
                            'item_id': item['item_id'], 'option_order_id': item['option_order_id'], 'item_sha256': digest(item),
                            'status': 'unleased_ready' if packet_ref else 'unavailable_invalid_parent',
                            'prediction_attempted': False, 'prediction_outcome': None, 'packet': packet_ref,
                            'request_identity': request_pins[number] if packet_ref else None, 'frozen_dependency': dependency,
                            'source_manifest_sha256': actual['manifest']['source_manifest_hash'], 'items_sha256': release['items_sha256'],
                            'context_sha256': hashlib.sha256(item['context'].encode()).hexdigest(), 'options_sha256': digest(item['options'])})
                assert not mappings and not outcomes and batch_parent_cost == verified['native']['known_spent_nanos']
                assert all(p['release_schema_version'] == schema and p['release_scope'] == prepared['release_scope'] for p in batch_packets)
                batches.append({'method_id': method, 'release_schema_version': schema, 'release_scope': prepared['release_scope'],
                    'execution_authorized': False, 'packets': [p['packet'] for p in batch_packets], 'jobs': len(batch_packets),
                    'max_calls': sum(p['max_calls'] for p in batch_packets),
                    'max_usd_reservation': str(sum((Decimal(str(p['max_usd_reservation'])) for p in batch_packets), Decimal(0))),
                    'source_actual_admission': admission, 'source_verified': verified_ref,
                    'parent_build_known_spend_nanos_once': batch_parent_cost})
            assert ledger.summary()['attempts'] == http.call_count == complete.call_count == 0
    assert seen == {(m, r, e) for m in ('P7', 'P3') for r in ('chris_olah', 'neel_nanda') for e in ('gpt-6-sol', 'gpt-6-astra')}
    assert [p['method_id'] for p in parents] == ['P7'] * 4 + ['P3'] * 4
    assert [p['method_id'] for p in packets] == ['P7'] * 4 + ['P3'] * 3
    assert Counter(p['parent_status'] for p in parents) == {'complete': 7, 'invalid': 1}
    assert len(coverage) == len({r['coverage_row_id'] for r in coverage}) == 112
    assert Counter(r['status'] for r in coverage) == {'unleased_ready': 98, 'unavailable_invalid_parent': 14}
    assert sum(p['known_build_spend_nanos_once'] for p in parents) == 538445000
    for path, expected in used.items():
        assert sha(path) == expected, 'input changed during binding'
    total = sum((Decimal(str(p['max_usd_reservation'])) for p in packets), Decimal(0))
    index = {'schema_version': 'remaining8-actual-descendant-bindings-v1', 'status': 'valid-descendants-prepared-invalid-coverage-retained',
        'selection': prior['selection'], 'original_readiness_index': PRIOR_READY, 'actual_parent_admissions': READY,
        'parent_terminal': TERMINAL, 'parent_outcome_indexes': VERIFIED, 'closed_predecessor': PREDECESSOR,
        'typed_denylist_future_owner_admission': TYPED_DENYLIST, 'runtime_sha': RUNTIME_SHA,
        'helper_sha256': HELPER_SHA, 'compiler_sha256': COMPILER_SHA, 'generator_sha256': sha(__file__),
        'parents': parents, 'new_descendant_coverage_rows': coverage, 'ready_prediction_packets': packets,
        'homogeneous_proposed_batches': batches,
        'counts': {'actual_parent_builds': 8, 'complete_parents': 7, 'invalid_parents': 1,
            'new_planned_joint_A_rows': 112, 'new_unleased_ready_rows': 98, 'new_unavailable_invalid_parent_rows': 14,
            'ready_prediction_packets': 7, 'driver_preparation_checks': 7, 'new_prediction_call_ceiling': 98,
            'P7_ready_packets': 4, 'P7_ready_rows': 56, 'P3_ready_packets': 3, 'P3_ready_rows': 42,
            'schema_homogeneous_proposed_batches': 2},
        'observed_parent_build_known_spend_nanos_once': 538445000,
        'cumulative_same_ledger_attempts_from_owner_metadata': terminal['known_verified_attempts'],
        'cumulative_same_ledger_spend_nanos_from_owner_metadata': terminal['known_verified_spend_nanos'],
        'new_prediction_max_usd_sum': str(total), 'api_calls_by_binder': 0, 'completion_calls_by_binder': 0,
        'isolated_test_ledger_attempts': 0, 'execution_authorized': False, 'original_inputs_unchanged': True, 'all_saved_packets_unleased': True,
        'limits': ['Only seven complete actual P7/P3 parents receive joint A descendants; all112 planned rows remain,including14unavailable Neel/Astra/P3 rows.',
            'No primary P8 packets are duplicated; original unavailable Neel/Luna/P3 rep0 remains unavailable and is not replaced by new Sol/Astra profiles.',
            'P7 approved target-plus-peer fit evidence differs from P3 target-only evidence. Peer source counts/bytes/parent pins retained; cross-method comparison does not hold evidence constant.',
            'P7 and P3 proposed batches are separate and each has one exact release schema/scope; original P7-then-P3 order retained.',
            'No repair,regeneration,substitution,reselection or replicate switch.04 owns classification/scoring; no result body,gold label or private target read.',
            'Typed11 is owner01/coordinator future both-convention admission responsibility,not a Role09 all-clear claim.0007 clarification remains unchanged.',
            'No live ledger,native claims,lease issuance,producer or provider call. Test authority discarded; temporary test ledger removed.',
            'Exact outgoing-request collisions,budget/holds/deadline/lease and dispatch remain coordinator-only. Cost maxima are reservations,not actual spend or permission.'],
        'input_hashes': [{'path': p, 'sha256': h} for p,h in sorted(used.items())]}
    ref = save('remaining8-ready-index.json', index)
    print(json.dumps({'ready_index': ref, 'counts': index['counts'], 'new_prediction_max_usd_sum': index['new_prediction_max_usd_sum'],
        'api_calls_by_binder': 0, 'execution_authorized': False}, sort_keys=True))


if __name__ == '__main__':
    main()
