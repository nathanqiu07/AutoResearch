"""Independent synthetic baseline/control handoff audit; no live backend."""
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, body):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(body, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write('\n')


class RecordingBackend:
    label = 'synthetic-independent-audit'
    model = 'fixture-v1'
    base_url = ''

    def __init__(self):
        self.calls = []

    def complete(self, prompt, **settings):
        self.calls.append({'prompt': prompt, 'settings': settings})
        return '{"probabilities":[0.4,0.6],"rationale":"Synthetic audit plumbing only"}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.source_root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    pin = json.loads((root / 'AUDIT_SOURCE.json').read_text())
    before = {name: sha(root / name) for name in pin['files']}
    assert before == pin['files']
    from autoresearch.taste.overnight import baselines as b, retrieval as r, contracts as k, consumer as c
    for module in (b, r, k, c):
        Path(module.__file__).resolve().relative_to(root)
    fixture_path = root / 'docs/overnight/gio-profile-20261115/handoffs/05/001-offline-fixture.json'
    fixture = json.loads(fixture_path.read_text())
    b.register_baselines()
    rows = {row['method']: row for row in fixture['records']}
    observations = {}

    def pred_config(profile):
        return {'method_implementation_hash': profile.method_implementation_hash,
                'renderer_implementation_hash': c.implementation_hash(),
                'profile_prompt_version': profile.prompt_version,
                'consumer_prompt_version': c.PROMPT_VERSION,
                'settings': {'temperature': 0.0, 'max_tokens': 128}}

    def invoke(profile, decision, wrapper=True):
        backend = RecordingBackend()
        try:
            function = b.predict_baseline if wrapper else c.predict_profile
            prediction = function(profile, decision['context'], decision['options'], backend, pred_config(profile))
            result = {'status': 'complete', 'prediction': asdict(prediction)}
        except c.ProfileFailure as exc:
            result = {'status': exc.status, 'error_code': exc.code}
        return dict(result, calls=backend.calls)

    loaded = {}
    for method, row in rows.items():
        profile = k.ProfileArtifact.from_dict(row['profile'])
        loaded[method] = profile
        run = invoke(profile, profile.config['decision'])
        assert run['status'] == row['status']
        if row['status'] == 'complete':
            payload = json.loads(run['calls'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])
            assert payload == row['payload']
            assert k.digest(payload) == row['payload_sha256']
            assert run['prediction']['calibrated'] is False
        else:
            assert run['calls'] == [] and run['error_code'] == row['error_code']
        observations['saved_' + method] = run

    # Exact task/settings stay fixed while personal source and metadata vary.
    invariance = {}
    for method in ('no_profile', 'name_only'):
        variants = []
        for index in range(3):
            config = copy.deepcopy(rows[method]['profile']['config'])
            config['researcher_id'] = 'synthetic-person-' + str(index)
            config['researcher_name'] = 'SYNTHETIC FIXED NAME'
            config['synthetic_unused_profile'] = {'secret_personal_canary': 'META_' + str(index)}
            doc = {'document_id': 'fit-canary-' + str(index), 'researcher_id': config['researcher_id'],
                   'content': 'SYNTHETIC PERSONAL BODY ' + str(index),
                   'title': 'SYNTHETIC TITLE ' + str(index), 'chosen_label': 'SYNTHETIC NOT AN ACTUAL LABEL'}
            doc['content_sha256'] = k.sha256_text(doc['content'])
            sources = k.source_manifest([doc])
            config.update(allowed_sources=sources, allowed_source_manifest_hash=k.digest(sources))
            backend = RecordingBackend()
            profile = k.build_profile([doc], config, backend)
            assert backend.calls == []
            run = invoke(profile, config['decision'])
            assert run['status'] == 'complete'
            payload = json.loads(run['calls'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])
            assert payload['personalization'] == ('' if method == 'no_profile' else k.canonical_json({'name': 'SYNTHETIC FIXED NAME'}))
            variants.append(run)
        assert all(item['calls'] == variants[0]['calls'] for item in variants)
        invariance[method] = variants
    observations['personal_input_invariance'] = invariance

    # A retrieval artifact is specific to both context and ordered options.
    binding = {}
    for method in ('lexical_retrieval', 'profile_retrieval'):
        profile = loaded[method]
        decision = profile.config['decision']
        variants = {'context': dict(decision, context=decision['context'] + ' CHANGED'),
                    'option_order': dict(decision, options=list(reversed(decision['options'])))}
        binding[method] = {}
        for label, changed in variants.items():
            run = invoke(profile, changed)
            assert run['status'] == 'unavailable' and run['error_code'] == 'retrieved_profile_decision_mismatch'
            assert run['calls'] == []
            binding[method][label] = run
        # This exposes the documented route requirement, not a claimed integrated-runner bug.
        direct = invoke(profile, variants['context'], wrapper=False)
        assert direct['status'] == 'complete' and len(direct['calls']) == 1
        binding[method]['generic_consumer_without_binding'] = direct
    observations['decision_binding'] = binding

    spans = {}
    source_text = {doc['document_id']: doc['content'] for doc in fixture['sources']}
    for method in ('raw_evidence', 'lexical_retrieval', 'profile_retrieval'):
        profile = loaded[method]
        assert profile.allowed_source_manifest_hash == k.digest(k.source_manifest(fixture['sources']))
        assert len(k.render_content(profile.content).encode('utf-8')) <= profile.personalization_cap
        passages = profile.content['passages']
        for passage in passages:
            assert set(passage) == {'document_id', 'start', 'end', 'text'}
            assert passage['text'] == source_text[passage['document_id']][passage['start']:passage['end']]
        spans[method] = passages
    observations['exact_approved_spans'] = spans
    for method in ('memory_summary', 'profile_retrieval'):
        profile = loaded[method]
        frozen = profile.config['frozen_profile']
        content = profile.content if method == 'memory_summary' else profile.content['profile']
        assert content == frozen['content']
        assert profile.fit_usage['reused_profile_id'] == frozen['profile_id']
        assert profile.fit_usage['original_fit_usage'] == frozen['fit_usage']
    observations['frozen_content_reuse'] = True

    # Imported retrieval helper bytes are incorporated in each registration policy hash.
    metadata = {item['method_id']: item for item in b.registration_metadata()}
    for method, profile in loaded.items():
        assert profile.prompt_sha256 == metadata[method]['prompt_sha256']
    original_hash = r.implementation_hash
    try:
        r.implementation_hash = lambda: '0' * 64
        changed = {item['method_id']: item for item in b.registration_metadata()}
    finally:
        r.implementation_hash = original_hash
    assert all(metadata[method]['prompt_sha256'] != changed[method]['prompt_sha256'] for method in metadata)
    observations['retrieval_helper_policy_pin'] = {'real_hash': original_hash(), 'current': metadata, 'synthetic_hash_variant': changed}

    command = [sys.executable, '-B', '-m', 'unittest', 'tests.test_overnight_retrieval', 'tests.test_overnight_baselines']
    tests = subprocess.run(command, cwd=root, capture_output=True, text=True)
    (out / 'tests.stdout.txt').write_text(tests.stdout)
    (out / 'tests.stderr.txt').write_text(tests.stderr)
    assert tests.returncode == 0
    assert before == {name: sha(root / name) for name in pin['files']}
    save(out / 'observations.json', observations)
    report = {'source_commit': pin['source_commit'], 'implementation_commit': pin['implementation_commit'],
              'source_pin_sha256': sha(root / 'AUDIT_SOURCE.json'), 'source_hashes': before,
              'fixture_sha256': sha(fixture_path), 'probe_sha256': sha(__file__), 'argv': sys.argv,
              'python': sys.version, 'real_model_calls': 0, 'source_unchanged': True,
              'tests': {'argv': command, 'exit_code': tests.returncode},
              'verified': ['saved control payloads match all six complete fixtures; semantic unavailable stays unavailable',
                           'no-profile and name-only full-request invariance under personal source/metadata canaries',
                           'retrieval wrapper rejects changed context and option order before calls',
                           'same approved source set, exact spans and byte caps', 'exact frozen summary content reuse',
                           'imported retrieval helper hash affects registered policy hash'],
              'pending_integration': ['Generic predict_profile does not enforce retrieval decision binding; actual integrated runner must use adapter/equivalent guard.',
                                      'Role05 source predates shared contract fixes; regenerate artifacts on the integrated pinned renderer.',
                                      'Actual P1 output, approved DEV corpus, peer controls, semantic retrieval, live accuracy and scaling were not tested.']}
    save(out / 'report.json', report)
    print(json.dumps({'report': str(out / 'report.json'), 'source_unchanged': True, 'real_model_calls': 0}))


if __name__ == '__main__':
    main()
