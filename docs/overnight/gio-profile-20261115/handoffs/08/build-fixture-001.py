"""Generate immutable synthetic P7/P8 examples; never calls a model service."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from autoresearch.taste.overnight.contracts import build_profile, digest, render_content, source_manifest
from autoresearch.taste.overnight.profiles_hypotheses import register_hypotheses_builders, registration_metadata
from tests.test_overnight_profiles_hypotheses import Extractor, document, statement


def write_addressed(folder, prefix, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    checksum = hashlib.sha256(raw).hexdigest()
    path = folder / (prefix + '-' + checksum + '.json')
    if path.exists():
        assert path.read_bytes() == raw, 'existing addressed artifact differs'
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    return {'location': str(path.relative_to(ROOT)), 'sha256': checksum, 'visibility': 'shared-dev'}


def main():
    folder = Path(__file__).resolve().parent
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    register_hypotheses_builders()
    target = document('target-fit', 'target', 'Prefer small tests.')
    peer = document('peer-fit', 'peer', 'Prefer large tests.')
    other = document('target-later', 'target', 'Prefer large tests.')
    examples = {
        'P7': ([target, peer], {'contrasts': [{'relation': 'different',
                                             'target': statement(target), 'peer': statement(peer)}]}),
        'P8': ([target, other], {'hypotheses': [
            {'id': 'small', 'statement': statement(target), 'weight': None},
            {'id': 'large', 'statement': statement(other), 'weight': None}],
            'relations': [{'kind': 'incompatible_evidence', 'hypothesis_ids': ['small', 'large'],
                           'statement': None}]}),
    }
    artifacts = []
    for method, (docs, response) in examples.items():
        for cap in (512, 2048, 8192):
            for policy in ('explicit-only', 'marked-inference'):
                sources = source_manifest(docs)
                config = {'method_id': method, 'researcher_id': 'target', 'allowed_sources': sources,
                          'allowed_source_manifest_hash': digest(sources), 'personalization_cap': cap,
                          'replicate_id': 0, 'code_sha': sha, 'approved_peer_sources': True,
                          'evidence_policy': policy, 'extractor_settings': {'temperature': 0, 'max_tokens': 4096}}
                backend = Extractor(response)
                profile = build_profile(docs, config, backend)
                assert len(backend.calls) == 1
                assert profile.status == ('invalid' if profile.token_count > cap else 'complete')
                artifacts.append({'documents': docs, 'profile': profile.to_dict(),
                                  'extraction_request': backend.calls[0]})
    output = write_addressed(folder, 'synthetic-profiles', {'schema_version': 'synthetic-profiles-v1',
        'code_commit': sha, 'model_service_calls': 0, 'artifacts': artifacts})

    # Fixture input for role05 only, not a production control or fidelity result.
    # Same fixed envelope and JSON padding field in all arms; provenance remains
    # attached to original speakers, including the intentionally swapped profile.
    shared_text = 'Use matched controls.'
    target = document('t', 'target', shared_text + ' Prefer small tests.')
    peer = document('p', 'peer', shared_text + ' Prefer large tests.')
    controls = {}
    for arm, docs in [('own', [target]), ('swapped', [peer]), ('shared', [target, peer])]:
        claims = []
        for doc in docs:
            claim = statement(doc)
            if arm == 'shared':
                claim['text'] = shared_text
                claim['sources'][0].update(end=len(shared_text), quote=shared_text)
            claims.append(claim)
        controls[arm] = {'statements': claims, 'padding': ''}
    size = max(len(render_content(value).encode('utf-8')) for value in controls.values())
    for value in controls.values():
        value['padding'] = ' ' * (size - len(render_content(value).encode('utf-8')))
    assert len({len(render_content(value).encode('utf-8')) for value in controls.values()}) == 1
    control_output = write_addressed(folder, 'synthetic-controls', {
        'schema_version': 'synthetic-equal-byte-controls-v1', 'documents': [target, peer],
        'content_by_arm': controls, 'content_hashes': {key: digest(value) for key, value in controls.items()},
        'rendered_utf8_bytes': size, 'tokenizer_equivalence': 'unverified',
        'policy': 'Same envelope and explicit whitespace padding; role05 owns production controls.'})
    metadata = [{**entry, 'function': entry['function'].__module__ + ':' + entry['function'].__name__}
                for entry in registration_metadata()]
    print(json.dumps({'code_commit': sha, 'outputs': [output, control_output], 'registration': metadata,
                      'fixture_cells': len(artifacts), 'model_service_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
