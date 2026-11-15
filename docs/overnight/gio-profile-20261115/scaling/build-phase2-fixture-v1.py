"""Rebuild synthetic profiles with frozen phase2 code; never perform API calls."""
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

RUNTIME_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
PARENT_SHA256 = 'ddc8d974e654be1ce2d7c8b28249e36d920bd60559288619a3785e4f55489031'
HERE = Path(__file__).resolve().parent


def main():
    runtime_root = Path(sys.argv[1]).resolve()
    assert subprocess.check_output(['git', '-C', str(runtime_root), 'rev-parse', 'HEAD'], text=True).strip() == RUNTIME_SHA
    assert not subprocess.check_output(['git', '-C', str(runtime_root), 'status', '--porcelain'], text=True).strip()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime_root))
    from autoresearch.taste.overnight import backends, baselines, consumer, profiles_summary, scaling
    from autoresearch.taste.overnight.contracts import backend_identity, build_profile, canonical_json, digest
    from autoresearch.taste.overnight.registry import get_builder
    parent_path = HERE / ('driver-fixture-v2-' + PARENT_SHA256 + '.json')
    assert hashlib.sha256(parent_path.read_bytes()).hexdigest() == PARENT_SHA256
    parent = json.loads(parent_path.read_text())
    spec = copy.deepcopy(parent['manifest']['design'])
    release = copy.deepcopy(parent['bindings'][0]['release'])
    documents = release['sources']['documents']
    # Only old synthetic design/items/documents are reused. Every profile is built anew.
    assert release['researcher_id'] == 'synthetic'
    baselines.register_baselines()
    profiles_summary.register_summary_builders()
    module_files = {'driver': 'docs/overnight/gio-profile-20261115/control/run_batch.py',
        'runner': 'autoresearch/taste/overnight/runner.py',
        'backend': 'autoresearch/taste/overnight/backends.py',
        'compiler': 'autoresearch/taste/overnight/scaling.py',
        'contracts': 'autoresearch/taste/overnight/contracts.py'}
    file_hashes = {key: hashlib.sha256((runtime_root / path).read_bytes()).hexdigest()
                   for key, path in module_files.items()}
    runtime = copy.deepcopy(parent['runtime'])
    runtime.update(code_sha=RUNTIME_SHA, driver_sha256=file_hashes['driver'], runner_sha256=file_hashes['runner'],
        backend_sha256=file_hashes['backend'], renderer_implementation_hash=consumer.implementation_hash(),
        deadline='2026-11-15T17:00:00Z')
    output_dir = HERE / 'phase2-v1-synthetic-inputs'
    output_dir.mkdir(exist_ok=True)

    def write_ref(body):
        raw = (canonical_json(body) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        path = output_dir / (sha + '.json')
        if path.exists():
            assert path.read_bytes() == raw
        else:
            with path.open('xb') as stream:
                stream.write(raw)
        return {'path': str(path), 'sha256': sha}

    with tempfile.TemporaryDirectory(prefix='scaling-phase2-offline-') as temp:
        ledger = backends.DollarLedger(Path(temp) / 'ledger.sqlite', max_usd=1, deadline='2099-01-01T00:00:00Z')
        engines = {level: backends.OpenAIResponsesBackend(model=model, reasoning='medium', ledger=ledger,
                    max_usd=.01, timeout=1) for level, model in
                    zip(('S', 'M', 'L'), ('gpt-6-luna', 'gpt-6-sol', 'gpt-6-astra'))}
        verification = {'evidence': 'offline mocked transport only; not model access or fidelity',
                        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        'runtime_sha': RUNTIME_SHA}
        models = copy.deepcopy(spec['models'])
        for model in models:
            engine = engines[model['level']]
            model.update(identity=backend_identity(engine), effective_settings=engine.enforced_settings,
                adapter_sha256=file_hashes['backend'], verification_sha256=digest(verification))
        spec.update(code_sha=RUNTIME_SHA, models=models, panel_id='synthetic-phase2-v1')
        spec['common'].update(renderer_implementation_hash=consumer.implementation_hash(),
                              effective_settings=models[0]['effective_settings'])
        profiles, methods, by_profile = [], [], {}
        response = canonical_json({'summary': [{'text': 'Prefer matched controls.', 'kind': 'preference',
            'evidence_status': 'explicit', 'conditions': None, 'date': None,
            'sources': [{'document_id': documents[0]['document_id'], 'quote': documents[0]['content']}]}]})
        # Reject all transport access even if fixture construction accidentally calls it.
        with patch('urllib.request.urlopen', side_effect=AssertionError('offline fixture forbids transport')) as http:
            for method_id in ('P1', 'P2'):
                builder = get_builder(method_id)
                method = {'method_id': method_id, 'config_hashes': {},
                    'method_implementation_hash': builder.implementation_hash,
                    'profile_prompt_version': builder.prompt_version, 'profile_prompt_sha256': builder.prompt_sha256}
                for model in models:
                    config = {'method_id': method_id, 'researcher_id': 'synthetic', 'replicate_id': 0,
                        'allowed_sources': release['sources']['source_manifest'],
                        'allowed_source_manifest_hash': release['sources']['allowed_source_manifest_hash'],
                        'personalization_cap': 2048, 'code_sha': RUNTIME_SHA,
                        'extractor_settings': model['extractor_settings'], 'evidence_policy': 'explicit-only'}
                    with patch.object(engines[model['level']], 'complete', return_value=response) as fake:
                        body = build_profile(documents, config, engines[model['level']]).to_dict()
                    assert fake.call_count == 1 and body['status'] == 'complete'
                    assert body['fit_usage']['quote_resolution_records'][0]['status'] == 'resolved'
                    profiles.append({'method_id': method_id, 'extractor_level': model['level'], 'profile': body})
                    by_profile[body['profile_id']] = body
                    method['config_hashes'][model['level']] = body['config_id']
                methods.append(method)
            spec['methods'] = methods
            controls = {}
            for control in spec['controls']:
                config = copy.deepcopy(profiles[0]['profile']['config'])
                config.pop('evidence_policy')
                config['method_id'] = control['method_id']
                body = build_profile(documents, config, engines['S']).to_dict()
                controls[control['method_id']] = body
                control.update(implementation_sha256=body['method_implementation_hash'],
                               config_hash=scaling.control_policy_hash(config))
            spec['diagnostic'].update(raw_control_config_hash=spec['controls'][1]['config_hash'],
                                      raw_implementation_sha256=controls['raw_evidence']['method_implementation_hash'])
            manifest = scaling.build_manifest(spec, profiles)
            bindings = []
            for cell in manifest['cells']:
                diagnostic = cell['conditioning']['kind'] == 'archival_raw_evidence'
                selected_release = copy.deepcopy(release)
                if diagnostic:
                    selected_release['items'] = [dict(release['items'][0], item_id='synthetic-archival-1')]
                    selected_release['items_sha256'] = digest(selected_release['items'])
                condition = cell['conditioning']
                if condition['kind'] == 'neutral_profile':
                    body = by_profile[condition['profile_id']]
                    registration = {'module': 'autoresearch.taste.overnight.profiles_summary', 'function': 'register_summary_builders'}
                else:
                    body = controls['raw_evidence' if diagnostic else condition['method_id']]
                    registration = {'module': 'autoresearch.taste.overnight.baselines', 'function': 'register_baselines'}
                ids = [item['item_id'] for item in selected_release['items']]
                bindings.append({'cell_id': cell['cell_id'], 'status': 'ready', 'release': selected_release,
                    'release_ref': write_ref(selected_release), 'jobs': [{'item_ids': ids, 'profile': body,
                    'profile_ref': write_ref(body), 'origin_job_id': digest(['mock-phase2-build', body['profile_id']]),
                    'registration': registration, 'limits': {'max_calls': len(ids), 'max_seconds': 30, 'max_usd': .01, 'timeout': 1}}]})
            compiled = scaling.compile_driver_packets(manifest, bindings, runtime=runtime,
                expected_manifest_hash=manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
                expected_runtime_hash=digest(runtime))
            loader = importlib.util.spec_from_file_location('phase2_driver_check', runtime_root / module_files['driver'])
            driver = importlib.util.module_from_spec(loader)
            loader.loader.exec_module(driver)
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
            batch = {'campaign_id': spec['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                'release_schema_version': runtime['release_schema_version'], 'release_scope': runtime['release_scope'],
                'contract': {'sha256': spec['contract_sha256']}, 'ledger': {'max_usd': 1}}
            for entry in compiled['packets']:
                # In-memory test-only placeholders are discarded; no granted lease is saved.
                packet = copy.deepcopy(entry['packet'])
                packet['lease'] = {'lease_id': 'synthetic-test-only', 'owner': 'synthetic-test', 'expires_at': runtime['deadline']}
                packet['manifest']['allocation']['authorization_source'] = 'synthetic-test-only-not-an-execution-lease'
                with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                    driver._prepare_packet(packet, batch, ledger)
            assert http.call_count == 0 and ledger.summary()['attempts'] == 0
            assert len(compiled['packets']) == 18 and compiled['estimates']['max_attempts'] == 33
    artifact = {'schema_version': 'scaling-phase2-fixture-v1', 'evidence_status': 'synthetic-offline-only',
        'parent_fixture_sha256': PARENT_SHA256, 'profile_lineage': 'fresh build_profile with six fixed mock responses; not migrated artifacts',
        'runtime_sha': RUNTIME_SHA, 'compiler_source_sha256': file_hashes['compiler'], 'runtime_file_sha256': file_hashes,
        'generator_sha256': verification['generator_sha256'], 'mock_extraction_calls': 6, 'api_calls': 0,
        'driver_prepare_checks': 18, 'persisted_authority': None, 'manifest': manifest, 'bindings': bindings,
        'runtime': runtime, 'compilation': compiled,
        'limitations': ['synthetic P1/P2 are not finalists', 'peer-P7 derivative needs a separately versioned compiler fix',
            'synthetic callable settings are consumer 128 and extractor 256 output tokens; not the live probe 8192 settings',
            'no measured fidelity, utility or model ordering; public model IDs are not parameter counts']}
    raw = (canonical_json(artifact) + '\n').encode()
    sha = hashlib.sha256(raw).hexdigest()
    path = HERE / ('driver-fixture-phase2-v1-' + sha + '.json')
    if path.exists():
        assert path.read_bytes() == raw
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'fixture': str(path), 'sha256': sha, 'manifest_sha256': manifest['manifest_sha256'],
        'bindings_sha256': digest(bindings), 'runtime_sha256': digest(runtime),
        'compilation_sha256': compiled['compilation_sha256'], 'api_calls': 0, 'driver_prepare_checks': 18}, sort_keys=True))


if __name__ == '__main__':
    main()
