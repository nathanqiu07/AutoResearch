"""Immutable synthetic quote-only v2 artifacts; zero network/model-service calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from autoresearch.taste.overnight.contracts import build_profile, digest, source_manifest
from autoresearch.taste.overnight.profiles_hypotheses import register_hypotheses_builders, registration_metadata
from tests.test_overnight_profiles_hypotheses import Extractor, document, quote_statement


def main():
    register_hypotheses_builders()
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    target = document('target-fit', 'target', 'Prefer small tests.')
    peer = document('peer-fit', 'peer', 'Prefer large tests.')
    other = document('target-later', 'target', 'Prefer large tests.')
    examples = {
        'P7': ([target, peer], {'contrasts': [{'relation': 'different',
            'target': quote_statement(target), 'peer': quote_statement(peer)}]}),
        'P8': ([target, other], {'hypotheses': [
            {'id': 'small', 'statement': quote_statement(target), 'weight': None},
            {'id': 'large', 'statement': quote_statement(other), 'weight': None}],
            'relations': [{'kind': 'incompatible_evidence', 'hypothesis_ids': ['small', 'large'],
                           'statement': None}]}),
    }
    artifacts = []

    def build(method, docs, response, cap, policy, case, expected=None):
        sources = source_manifest(docs)
        config = {'method_id': method, 'researcher_id': 'target', 'allowed_sources': sources,
                  'allowed_source_manifest_hash': digest(sources), 'personalization_cap': cap,
                  'replicate_id': 0, 'code_sha': sha, 'approved_peer_sources': True,
                  'evidence_policy': policy, 'extractor_settings': {'temperature': 0, 'max_tokens': 4096}}
        raw = json.dumps(response)
        backend = Extractor(raw)
        profile = build_profile(docs, config, backend)
        assert len(backend.calls) == 1
        if expected is None:
            expected = 'invalid' if profile.token_count > cap else 'complete'
        assert profile.status == expected
        assert profile.fit_usage['raw_response_sha256'] == hashlib.sha256(raw.encode()).hexdigest()
        artifacts.append({'case': case, 'documents': docs, 'profile': profile.to_dict(),
                          'raw_extractor_response': raw, 'extraction_request': backend.calls[0]})

    for method, (docs, response) in examples.items():
        for cap in (512, 2048, 8192):
            for policy in ('explicit-only', 'marked-inference'):
                build(method, docs, response, cap, policy, 'core-grid')

    source = document('t', 'target', 'Use tests. Use tests.')
    for case, quote in [('ambiguous', 'Use tests.'), ('absent', 'Use experiments.'),
                        ('legacy-offsets', 'Use tests. Use tests.')]:
        value = quote_statement(source)
        value['sources'][0]['quote'] = quote
        if case == 'legacy-offsets':
            value['sources'][0].update(start=0, end=len(source['content']))
        response = {'hypotheses': [{'id': 'h', 'statement': value, 'weight': None}], 'relations': []}
        build('P8', [source], response, 2048, 'explicit-only', case, 'invalid')

    metadata = [{**x, 'function': x['function'].__module__ + ':' + x['function'].__name__}
                for x in registration_metadata()]
    body = {'schema_version': 'synthetic-quote-only-profiles-v2', 'code_commit': sha,
            'model_service_calls': 0, 'artifacts': artifacts, 'registration': metadata,
            'lineage': {'supersedes_fixture_sha256':
                        '96ccb33e7a5680516a62f6185ac8583c8ba43a7236ba25077996f088241347ab',
                        'policy': 'New builds only; old artifacts stay unchanged and historical.'}}
    raw = (json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
    checksum = hashlib.sha256(raw).hexdigest()
    path = Path(__file__).parent / ('synthetic-profiles-v2-' + checksum + '.json')
    if path.exists():
        assert path.read_bytes() == raw
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'location': str(path.relative_to(ROOT)), 'sha256': checksum,
                      'code_commit': sha, 'fixture_cells': len(artifacts),
                      'model_service_calls': 0, 'registration': metadata}, indent=2))


if __name__ == '__main__':
    main()
