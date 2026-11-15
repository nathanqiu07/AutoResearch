"""Private, unleased mechanical check of approved saved P1s; no provider calls."""
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
COMPILER_SHA256 = 'cdafe348558fbf2dfbede6e66608f02d39e858ba7aaf4727afaf49d71d7400aa'
INDEX = {'path': '/private/tmp/gio-profile-20261115-coordinator/first-p1-handoff-v1/index.json',
         'sha256': 'd60849589fefe1016b4167ad6fba0a5fc1a4c09efb87ec0441202dcdb29f1a26'}
ACCESS = {'path': '/private/tmp/gio-profile-20261115-coordinator/neutral-api-access-v1/summary.json',
          'sha256': '4886347fdc74eca0d7378e7a1ce57aacaf89c875dc334553deef2545c13179b1'}
PARENT_REFS = {
    'chris_olah': {'path': '/private/tmp/gio-profile-20261115-evaluator/released/0156620f0a5fc0ff5c601ac3a14cf1db3f07a30655262a200690988be63c6f0b/bundle.json',
                  'sha256': '712d8190e5e9be352e4f77a2bba5e8605f0fd63d99dcbb541e2a0d9a27f65a7e'},
    'neel_nanda': {'path': '/private/tmp/gio-profile-20261115-evaluator/released/ca17633f4317c25d4da5fe31e2bdedfd3b9339f05151981d9a67843545e29aa9/bundle.json',
                   'sha256': '25f43ce5ba0cc560654dd6d0dae98e810fc4845a42b0e4125d71f4e4c431af3c'}}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved(ref):
    raw = Path(ref['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ref['sha256'], 'approved input hash differs'
    return json.loads(raw)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runtime_root = Path(sys.argv[1]).resolve()
    assert subprocess.check_output(['git', '-C', str(runtime_root), 'rev-parse', 'HEAD'], text=True).strip() == RUNTIME_SHA
    assert not subprocess.check_output(['git', '-C', str(runtime_root), 'status', '--porcelain'], text=True).strip()
    compiler_path = OWN_ROOT / 'autoresearch/taste/overnight/scaling.py'
    assert sha(compiler_path) == COMPILER_SHA256
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime_root))
    from autoresearch.taste.overnight import backends, consumer, profiles_summary
    from autoresearch.taste.overnight.contracts import ProfileArtifact, backend_identity, canonical_json, digest, sha256_text
    from autoresearch.taste.overnight.registry import get_builder
    compiler = load('autoresearch.taste.overnight.scaling_readiness', compiler_path)
    driver = load('phase2_p1_readiness_driver', runtime_root / 'docs/overnight/gio-profile-20261115/control/run_batch.py')
    profiles_summary.register_summary_builders()
    index, access = approved(INDEX), approved(ACCESS)
    assert index['runtime_sha'] == access['runtime_commit'] == RUNTIME_SHA
    assert index['calls_authorized_by_this_handoff'] == 0
    assert {p['researcher_id'] for p in index['profiles']} == set(PARENT_REFS)
    parent_handoff = json.loads(subprocess.check_output(['git', '-C', str(runtime_root), 'show',
        RUNTIME_SHA + ':docs/overnight/gio-profile-20261115/handoffs/04/008-peer-fit-ready.json']))
    assert {p['researcher_id']: p['release'] for p in parent_handoff['inputs']} == PARENT_REFS
    assert '09' in parent_handoff['next_consumer']
    ordinary_path = HERE / 'driver-fixture-phase2-v1-148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6.json'
    assert sha(ordinary_path) == '148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6'
    template = json.loads(ordinary_path.read_text())
    runtime = copy.deepcopy(template['runtime'])
    for key, relative in (('driver_sha256', 'docs/overnight/gio-profile-20261115/control/run_batch.py'),
            ('runner_sha256', 'autoresearch/taste/overnight/runner.py'), ('backend_sha256', 'autoresearch/taste/overnight/backends.py')):
        assert sha(runtime_root / relative) == runtime[key]
    base = Path('/private/tmp/gio-profile-20261115-scaling')
    base.mkdir(exist_ok=True, mode=0o700)
    private = Path(tempfile.mkdtemp(prefix='mechanical-readiness-only-real-p1-v1-', dir=base))

    def save(name, body):
        raw = (canonical_json(body) + '\n').encode()
        path = private / name
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o600)
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}

    reports = []
    with tempfile.TemporaryDirectory(prefix='isolated-test-ledger-', dir=private) as temp:
        ledger = backends.DollarLedger(Path(temp) / 'ledger.sqlite', max_usd=100, deadline='2099-01-01T00:00:00Z')
        with patch('urllib.request.urlopen', side_effect=AssertionError('readiness forbids HTTP')) as http, \
                patch.object(backends.OpenAIResponsesBackend, 'complete', side_effect=AssertionError('readiness forbids completion')) as complete:
            for entry in index['profiles']:
                researcher = entry['researcher_id']
                profile = ProfileArtifact.from_dict(approved(entry['profile'])).to_dict()
                release = approved(PARENT_REFS[researcher])
                assert profile['profile_id'] == entry['profile_id'] and profile['code_sha'] == RUNTIME_SHA
                assert profile['status'] == 'complete' and profile['method_id'] == 'P1'
                assert profile['personalization_cap'] == entry['personalization_cap'] == 512
                assert profile['config']['evidence_policy'] == entry['evidence_policy'] == 'explicit-only'
                assert profile['documents_hash'] == digest(release['sources']['documents'])
                assert profile['allowed_source_manifest_hash'] == release['sources']['allowed_source_manifest_hash'] == entry['source_manifest_hash']
                assert profile['renderer_implementation_hash'] == consumer.implementation_hash() == runtime['renderer_implementation_hash']
                assert release['items_sha256'] == digest(release['items'])
                models = []
                for level, model_id in zip(('S', 'M', 'L'), ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra')):
                    engine = backends.OpenAIResponsesBackend(model=model_id, reasoning='medium', ledger=ledger, max_usd=10, timeout=180)
                    if level == 'S':
                        assert backend_identity(engine) == profile['extractor']
                    else:
                        receipt = next(c for c in access['calls'] if c['model'] == model_id)
                        assert receipt['status'] == 'complete' and receipt['settings']['enforced_settings'] == engine.enforced_settings
                    models.append({'level': level, 'status': 'available', 'identity': backend_identity(engine),
                        'model_revision': 'provider-unversioned-public-api-model-id',
                        'settings': {'temperature': 0.0, 'max_tokens': 8192},
                        'extractor_settings': profile['extractor_settings'], 'effective_settings': engine.enforced_settings,
                        'adapter_sha256': runtime['backend_sha256'],
                        'verification_sha256': entry['profile']['sha256'] if level == 'S' else ACCESS['sha256']})
                spec = copy.deepcopy(template['manifest']['design'])
                spec.update(panel_id='mechanical-readiness-only-not-selection-' + researcher, models=models,
                    contract_sha256=parent_handoff['contract_sha256'])
                spec['common'].update(researcher_id=researcher, personalization_cap=512, context_cap=8192,
                    items=[{'item_id': i['item_id'], 'option_order_id': i['option_order_id'],
                            'context_sha256': sha256_text(i['context']), 'options_sha256': digest(i['options'])} for i in release['items']],
                    items_hash=release['items_sha256'], task_context_hash=digest([i['context'] for i in release['items']]),
                    documents_hash=profile['documents_hash'], allowed_source_manifest_hash=profile['allowed_source_manifest_hash'],
                    settings=models[0]['settings'], extractor_settings=profile['extractor_settings'])
                profiles = []
                absent_reason = 'not assigned: mechanical consumer-only readiness, not finalist selection or scaling'
                absent_hash = digest({'reason': absent_reason, 'saved_profile_sha256': entry['profile']['sha256']})
                for method in spec['methods']:
                    builder = get_builder(method['method_id'])
                    method.update(method_implementation_hash=builder.implementation_hash,
                        profile_prompt_version=builder.prompt_version, profile_prompt_sha256=builder.prompt_sha256,
                        config_hashes={level: absent_hash for level in ('S', 'M', 'L')})
                    for level in ('S', 'M', 'L'):
                        if method['method_id'] == 'P1' and level == 'S':
                            method['config_hashes'][level] = profile['config_id']
                            profiles.append({'method_id': 'P1', 'extractor_level': 'S', 'profile': profile})
                        else:
                            profiles.append({'method_id': method['method_id'], 'extractor_level': level,
                                'status': 'planned-unavailable', 'reason': absent_reason, 'evidence_sha256': absent_hash})
                # Required study scaffolding is explicitly unassigned; only B cells get bindings.
                for control in spec['controls']:
                    control['config_hash'] = absent_hash
                diagnostic = spec['diagnostic']
                diagnostic.update(items=spec['common']['items'], items_hash=spec['common']['items_hash'],
                    task_context_hash=spec['common']['task_context_hash'], documents_hash=profile['documents_hash'],
                    raw_evidence_hash=profile['allowed_source_manifest_hash'], raw_control_config_hash=absent_hash,
                    subset_manifest_hash=absent_hash, recorded_judgment_manifest_hash=absent_hash, withholding_receipt_hash=absent_hash)
                manifest = compiler.build_manifest(spec, profiles)
                fixed_cells = {a['cell_id'] for a in manifest['arms'] if a['study'] == 'B'}
                bindings = []
                for cell in manifest['cells']:
                    if cell['cell_id'] not in fixed_cells:
                        bindings.append({'cell_id': cell['cell_id'], 'status': 'unavailable', 'reason': absent_reason})
                        continue
                    bindings.append({'cell_id': cell['cell_id'], 'status': 'ready', 'release_ref': PARENT_REFS[researcher], 'release': release,
                        'jobs': [{'item_ids': [i['item_id'] for i in release['items']], 'profile_ref': entry['profile'], 'profile': profile,
                            'origin_job_id': entry['job_id'], 'registration': {'module': 'autoresearch.taste.overnight.profiles_summary',
                                'function': 'register_summary_builders'}, 'limits': {'max_calls': len(release['items']),
                                'max_seconds': 600, 'max_usd': 10, 'timeout': 180}}]})
                compiled = compiler.compile_driver_packets(manifest, bindings, runtime=runtime,
                    expected_manifest_hash=manifest['manifest_sha256'], expected_bindings_hash=digest(bindings), expected_runtime_hash=digest(runtime))
                assert len(compiled['packets']) == 3 and len(compiled['profile_dependencies']) == 1
                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
                batch = {'campaign_id': spec['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                    'release_schema_version': runtime['release_schema_version'], 'release_scope': runtime['release_scope'],
                    'contract': {'sha256': spec['contract_sha256']}, 'ledger': {'max_usd': 100}}
                packet_refs = []
                for record in compiled['packets']:
                    draft = record['packet']
                    assert draft['manifest']['profile_hash'] == entry['profile_id'] and draft['profile'] == entry['profile']
                    assert draft['lease'] is None and draft['manifest']['allocation']['authorization_source'] is None
                    packet_refs.append(save(researcher + '-' + draft['backend']['model'] + '-unleased-draft.json', draft))
                    packet = copy.deepcopy(draft)
                    packet['lease'] = {'lease_id': 'mechanical-readiness-test-only', 'owner': 'readiness-test', 'expires_at': runtime['deadline']}
                    packet['manifest']['allocation']['authorization_source'] = 'mechanical-readiness-test-only-no-execution-authority'
                    with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                        driver._prepare_packet(packet, batch, ledger)
                bundle = save(researcher + '-private-readiness-bindings.json', {'purpose': 'mechanical-readiness-only-not-selection-or-results',
                    'runtime': runtime, 'manifest': manifest, 'bindings': bindings, 'compilation': compiled})
                reports.append({'researcher_id': researcher, 'profile_ref': entry['profile'], 'profile_id': entry['profile_id'],
                    'origin_job_id': entry['job_id'], 'release_ref': PARENT_REFS[researcher], 'source_manifest_sha256': profile['allowed_source_manifest_hash'],
                    'documents_sha256': profile['documents_hash'], 'profile_config_sha256': profile['config_id'],
                    'profile_content_sha256': profile['content_sha256'], 'profile_prompt_sha256': profile['prompt_sha256'],
                    'cap_utf8_bytes': 512, 'profile_rendered_utf8_bytes': profile['token_count'], 'extractor': profile['extractor'],
                    'extractor_settings': profile['extractor_settings'], 'consumer_settings': models[0]['settings'],
                    'consumer_models': [m['identity']['model'] for m in models], 'effective_consumer_settings': models[0]['effective_settings'],
                    'context_cap_utf8_bytes': spec['common']['context_cap'], 'n_fit_documents': len(release['sources']['documents']),
                    'n_ordered_items': len(release['items']), 'n_semantic_targets': release['n_semantic_targets'],
                    'n_dev_source_groups': release['n_dev_source_groups'], 'tier': release['tier'], 'items_sha256': release['items_sha256'],
                    'manifest_sha256': manifest['manifest_sha256'], 'bindings_sha256': digest(bindings),
                    'compilation_sha256': compiled['compilation_sha256'], 'driver_preparation_checks': 3,
                    'private_bundle': bundle, 'unleased_drafts': packet_refs})
            assert ledger.summary()['attempts'] == http.call_count == complete.call_count == 0
    # Recheck originals after all preparation. Nothing was rewritten or relabeled.
    for entry in index['profiles']:
        approved(entry['profile'])
        approved(PARENT_REFS[entry['researcher_id']])
    report = {'schema_version': 'real-p1-mechanical-readiness-v1', 'status': 'mechanical-preparation-passed',
        'purpose': 'readiness-only; not selection, scaling observations or evidence of model quality',
        'runtime_sha': RUNTIME_SHA, 'compiler_source_sha256': COMPILER_SHA256,
        'generator_sha256': sha(Path(__file__)), 'index_ref': INDEX, 'api_access_receipt_ref': ACCESS,
        'runtime': runtime, 'runtime_sha256': digest(runtime), 'private_directory': str(private), 'researchers': reports,
        'driver_preparation_checks': 6, 'api_calls': 0, 'completion_calls': 0, 'isolated_test_ledger_attempts': 0,
        'original_inputs_unchanged': True, 'private_payloads_printed': False,
        'limitations': ['only B fixed-profile consumer cells prepared; required unassigned study scaffolding is not a selected matrix',
            'A/C aliases of identical B executions are inventory references only; no joint extraction experiment ran',
            'test authority was discarded in memory; all saved drafts have null leases/authorization',
            'preparation uses a fixed test clock; real deadline/ledger/lease admission must be checked by coordinator',
            'max_calls14,max_seconds600,max_usd10,timeout180 are readiness-only placeholders, not allocation',
            'no scoring, true labels, private target bundles, provider calls or live ledger were accessed',
            'profiles were predeclared first cap512 explicit-only P1 instances, not winners']}
    ref = save('safe-readiness-report.json', report)
    print(json.dumps({'status': report['status'], 'safe_report': ref, 'private_directory': str(private),
        'driver_preparation_checks': 6, 'api_calls': 0, 'completion_calls': 0, 'original_inputs_unchanged': True}, sort_keys=True))


if __name__ == '__main__':
    main()
