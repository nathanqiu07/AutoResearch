"""Exercise the new pure compiler with unchanged phase2 execution code."""
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
PARENT_SHA256 = '148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6'


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
    from autoresearch.taste.overnight.contracts import canonical_json, digest
    compiler_path = OWN_ROOT / 'autoresearch/taste/overnight/scaling.py'
    compiler = load('autoresearch.taste.overnight.scaling_preparation', compiler_path)
    helpers = load('scaling_peer_fixture_helpers', OWN_ROOT / 'tests/test_overnight_scaling_manifest.py')
    parent_path = HERE / ('driver-fixture-phase2-v1-' + PARENT_SHA256 + '.json')
    assert hashlib.sha256(parent_path.read_bytes()).hexdigest() == PARENT_SHA256
    ordinary = json.loads(parent_path.read_text())
    outputs = HERE / 'phase2-peer-v1-synthetic-inputs'
    outputs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='scaling-peer-offline-') as temp:
        ledger = backends.DollarLedger(Path(temp) / 'ledger.sqlite', max_usd=1, deadline='2099-01-01T00:00:00Z')
        with patch('urllib.request.urlopen', side_effect=AssertionError('offline fixture forbids transport')) as http:
            manifest, bindings, runtime, ledger = helpers.peer_driver_fixture(outputs, ordinary, compiler, ledger)
            compiled = compiler.compile_driver_packets(manifest, bindings, runtime=runtime,
                expected_manifest_hash=manifest['manifest_sha256'], expected_bindings_hash=digest(bindings),
                expected_runtime_hash=digest(runtime))
            driver = load('phase2_peer_driver', runtime_root / 'docs/overnight/gio-profile-20261115/control/run_batch.py')
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
            batch = {'campaign_id': manifest['design']['campaign_id'], 'code_sha': RUNTIME_SHA, 'deadline': runtime['deadline'],
                'release_schema_version': runtime['release_schema_version'], 'release_scope': runtime['release_scope'],
                'contract': {'sha256': manifest['design']['contract_sha256']}, 'ledger': {'max_usd': 1}}
            for entry in compiled['packets']:
                packet = copy.deepcopy(entry['packet'])
                packet['lease'] = {'lease_id': 'synthetic-test-only', 'owner': 'synthetic-test', 'expires_at': runtime['deadline']}
                packet['manifest']['allocation']['authorization_source'] = 'synthetic-test-only-not-an-execution-lease'
                with patch.object(driver, 'datetime', Clock), patch('autoresearch.taste.overnight.runner.datetime', Clock):
                    driver._prepare_packet(packet, batch, ledger)
            assert ledger.summary()['attempts'] == 0 and http.call_count == 0
    # Recompile the historical ordinary f6 fixture with the new compiler unchanged.
    previous = compiler.compile_driver_packets(ordinary['manifest'], ordinary['bindings'], runtime=ordinary['runtime'],
        expected_manifest_hash=ordinary['manifest']['manifest_sha256'], expected_bindings_hash=digest(ordinary['bindings']),
        expected_runtime_hash=digest(ordinary['runtime']))
    assert previous == ordinary['compilation']
    artifact = {'schema_version': 'scaling-phase2-peer-fixture-v1', 'evidence_status': 'synthetic-offline-only',
        'runtime_sha': RUNTIME_SHA, 'parent_fixture_sha256': PARENT_SHA256,
        'compiler_source_sha256': hashlib.sha256(compiler_path.read_bytes()).hexdigest(),
        'fixture_helper_sha256': hashlib.sha256((OWN_ROOT / 'tests/test_overnight_scaling_manifest.py').read_bytes()).hexdigest(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime_file_sha256': ordinary['runtime_file_sha256'],
        'profile_lineage': 'three freshly built P7 artifacts using current quote-only resolver and fixed mock response',
        'api_calls': 0, 'mock_extraction_calls': 3, 'persisted_authority': None,
        'driver_prepare_checks': len(compiled['packets']), 'ordinary_recompile_unchanged': True,
        'manifest': manifest, 'bindings': bindings, 'runtime': runtime, 'compilation': compiled,
        'limitations': ['peer P7 and target-only conditions do not hold evidence constant',
            'non-P7 candidate/control arms remain explicitly unavailable in peer-only source condition',
            'compiler preparation code differs from runtime; execution driver/runner/backend remain f6',
            'synthetic settings and outputs do not establish API response quality, ordering or fidelity']}
    raw = (canonical_json(artifact) + '\n').encode()
    sha = hashlib.sha256(raw).hexdigest()
    path = HERE / ('driver-fixture-phase2-peer-v1-' + sha + '.json')
    if path.exists():
        assert path.read_bytes() == raw
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'fixture': str(path), 'sha256': sha, 'compiler_source_sha256': artifact['compiler_source_sha256'],
        'manifest_sha256': manifest['manifest_sha256'], 'bindings_sha256': digest(bindings),
        'runtime_sha256': digest(runtime), 'compilation_sha256': compiled['compilation_sha256'],
        'driver_prepare_checks': len(compiled['packets']), 'max_attempts': compiled['estimates']['max_attempts'], 'api_calls': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
