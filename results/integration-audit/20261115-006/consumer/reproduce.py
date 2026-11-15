#!/usr/bin/env python3
"""Read-only synthetic consumer audit of a supplied CONTRACT_READY snapshot."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(body, f, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        f.write('\n')


def synthetic_builder(documents, config, extractor):
    return config['synthetic_builder_result']


class Recorder:
    label = 'SYNTHETIC consumer audit recorder'
    model = 'SYNTHETIC fixed-response-v1'
    base_url = ''

    def __init__(self, raw=None):
        self.raw = raw if raw is not None else '{"probabilities":[0.25,0.75],"rationale":"SYNTHETIC fixed reply"}'
        self.requests = []

    def complete(self, prompt, **settings):
        self.requests.append({'prompt': prompt, 'settings': settings})
        return self.raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path, help='A new output directory')
    args = parser.parse_args()
    root, out = args.source_root.resolve(), args.out.resolve()
    out.mkdir(exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    source_pin = json.loads((root / 'AUDIT_SOURCE.json').read_text())
    relevant = ['autoresearch/taste/overnight/consumer.py', 'autoresearch/taste/overnight/contracts.py',
                'autoresearch/taste/overnight/registry.py', 'autoresearch/taste/usermodel.py',
                'autoresearch/taste/methods/m0_none.py',
                'docs/overnight/gio-profile-20261115/infrastructure/fixture-v1.json',
                'docs/overnight/gio-profile-20261115/infrastructure/README.md']
    before = {p: sha(root / p) for p in relevant}
    for p, digest in before.items():
        assert source_pin['files'][p] == digest, p
    from autoresearch.taste.overnight import consumer as c, contracts as k, registry as r
    from autoresearch.llm import Budget
    from autoresearch.taste.methods.m0_none import NoHistory
    from autoresearch.taste.usermodel import load_model
    for module in (c, k, r):
        Path(module.__file__).resolve().relative_to(root)
    fixture = json.loads((root / relevant[-2]).read_text())
    documents = fixture['documents']
    context, options = 'SYNTHETIC consumer decision', ['SYNTHETIC_A', 'SYNTHETIC_B']
    r.register_builder('synthetic-consumer-audit', synthetic_builder,
                       prompt_version='synthetic-audit-v1', prompt_sha256=k.sha256_text('SYNTHETIC audit prompt'))
    r.register_builder('synthetic-empty-control', synthetic_builder, allows_empty=True,
                       prompt_version='synthetic-audit-v1', prompt_sha256=k.sha256_text('SYNTHETIC audit prompt'))

    def build(result, **changes):
        config = dict(fixture['profile']['config'], method_id='synthetic-consumer-audit',
                      personalization_cap=8192, synthetic_builder_result=result)
        config.update(changes)
        return k.build_profile(documents, config, Recorder())

    def prediction_config(profile):
        return {'method_implementation_hash': profile.method_implementation_hash,
                'renderer_implementation_hash': c.implementation_hash(),
                'profile_prompt_version': profile.prompt_version,
                'consumer_prompt_version': c.PROMPT_VERSION,
                'settings': {'temperature': 0.0, 'max_tokens': 128}}

    def checked_profile(body):
        body = json.loads(json.dumps(body))
        body['content_sha256'] = k.digest(body['content'])
        body.pop('profile_id', None)
        body['profile_id'] = k.digest(body)
        return k.ProfileArtifact.from_dict(body)

    def invoke(profile, response=None):
        recorder = Recorder(response)
        try:
            prediction = c.predict_profile(profile, context, options, recorder, prediction_config(profile))
            result = {'outcome': 'prediction', 'prediction': asdict(prediction)}
        except Exception as exc:
            result = {'outcome': 'exception', 'exception_type': type(exc).__name__,
                      'status': getattr(exc, 'status', None), 'code': getattr(exc, 'code', None),
                      'message': str(exc)}
        return {**result, 'requests': recorder.requests, 'backend_calls': len(recorder.requests)}

    rich = {'prose': 'SYNTHETIC prose é', 'atomic_claims': [{'claim': 'SYNTHETIC claim', 'source_ids': ['synthetic-fit-1']}],
            'conditions': [{'if': 'SYNTHETIC uncertainty', 'then': 'SYNTHETIC replicate'}],
            'examples': [{'context': 'SYNTHETIC past', 'choice': 'SYNTHETIC example'}],
            'hierarchy': {'parent': {'children': ['SYNTHETIC child']}},
            'contrasts': {'favored': 'SYNTHETIC_A', 'disfavored': 'SYNTHETIC_B'},
            'dated_hypotheses': [{'date': '2020-01-01', 'text': 'SYNTHETIC hypothesis'}],
            'unknown_future_field': [None, False, 1, 1.25, {'': 'SYNTHETIC empty key', 'a.b': 'SYNTHETIC dot key'}]}
    normal = build({'content': rich, 'status': 'complete'})
    normal_run = invoke(normal)
    payload = json.loads(normal_run['requests'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])
    assert json.loads(payload['personalization']) == rich
    assert set(payload) == {'context', 'options', 'personalization'}
    assert normal_run['prediction']['calibrated'] is False
    save(out / 'rich-profile.json', normal.to_dict())
    save(out / 'rich-request.json', normal_run)

    empty_runs = []
    for i in range(3):
        profile = build({'content': {}, 'status': 'complete'}, method_id='synthetic-empty-control',
                        replicate_id=i, synthetic_personal_canary={'identity': 'SYNTHETIC_PERSON_' + str(i),
                        'history': ['SYNTHETIC_HISTORY_' + str(i)], 'principles': ['SYNTHETIC_PRINCIPLE_' + str(i)]})
        body = profile.to_dict()
        body['extractor']['label'] = 'SYNTHETIC_EXTRACTOR_' + str(i)
        body['researcher_id'] = 'SYNTHETIC_RESEARCHER_' + str(i)
        empty_runs.append(invoke(checked_profile(body)))
    assert all(run['requests'] == empty_runs[0]['requests'] for run in empty_runs)
    assert json.loads(empty_runs[0]['requests'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])['personalization'] == ''
    save(out / 'no-profile-request-invariance.json', empty_runs)

    statuses = {}
    for status in ('empty', 'unsupported', 'invalid', 'unavailable', 'abstained'):
        run = invoke(build({'content': rich, 'status': status, 'error_code': 'SYNTHETIC_' + status}))
        assert run['exception_type'] == 'ProfileFailure' and run['status'] == status and run['backend_calls'] == 0
        statuses[status] = run
    oversize = build({'content': rich, 'status': 'complete'}, personalization_cap=1)
    oversize_run = invoke(oversize)
    assert oversize_run['status'] == 'invalid' and oversize_run['backend_calls'] == 0
    assert oversize_run['code'] == 'personalization_cap_exceeded'
    save(out / 'declared-profile-failures.json', statuses)
    save(out / 'builder-cap-enforcement.json', {'profile': oversize.to_dict(), 'run': oversize_run})

    # Generated serialized variant: integrity hashes are valid, semantic cap is inconsistent.
    low_cap_body = normal.to_dict()
    low_cap_body['personalization_cap'] = 1
    low_cap_body['config']['personalization_cap'] = 1
    low_cap_body['config_id'] = k.digest(low_cap_body['config'])
    low_cap_profile = checked_profile(low_cap_body)
    low_cap_run = invoke(low_cap_profile)
    assert low_cap_run['outcome'] == 'prediction' and low_cap_run['backend_calls'] == 1
    assert len(payload['personalization'].encode('utf-8')) > low_cap_profile.personalization_cap
    save(out / 'loaded-cap-bypass.json', {'profile': low_cap_profile.to_dict(), 'run': low_cap_run})

    # The public consumer parser recognizes abstention, but ignores other explicit failure statuses.
    response_statuses = {}
    for status in ('invalid', 'unavailable', 'unsupported', 'empty', 'abstained'):
        run = invoke(normal, json.dumps({'status': status, 'probabilities': [0.25, 0.75],
                                        'rationale': 'SYNTHETIC failed response with fallback probabilities'}))
        response_statuses[status] = run
        if status == 'abstained':
            assert run['outcome'] == 'exception' and run['status'] == 'abstained'
        else:
            assert run['outcome'] == 'prediction'
    save(out / 'explicit-consumer-failure-statuses.json', response_statuses)

    huge_integer_response = '{"probabilities":[' + '9' * 400 + ',0],"rationale":"SYNTHETIC invalid number"}'
    huge_run = invoke(normal, huge_integer_response)
    assert huge_run['exception_type'] == 'OverflowError' and huge_run['status'] is None
    save(out / 'oversized-integer-response.json', {'raw_response': huge_integer_response, 'run': huge_run})

    calibration = {}
    for label, extra in [('learned-weights', {'weights_status': 'learned'}), ('calibrated', {'calibrated': True})]:
        profile = build(dict({'content': rich, 'status': 'complete'}, **extra))
        run = invoke(profile)
        assert run['status'] == 'invalid' and run['backend_calls'] == 0
        assert run['code'] == 'learned_weights_or_calibration_not_neutral'
        calibration[label] = run
    raw_claim_run = invoke(normal, '{"probabilities":[0.25,0.75],"calibrated":true}')
    assert raw_claim_run['prediction']['calibrated'] is False
    calibration['backend_calibration_claim_ignored'] = raw_claim_run
    save(out / 'calibration-separation.json', calibration)

    legacy_recorder = Recorder()
    legacy_recorder.budget = Budget()
    legacy = NoHistory(legacy_recorder)
    legacy_path = out / 'synthetic-legacy-m0.json'
    legacy.save(legacy_path)
    legacy_guards = {}
    for field in ('label', 'endpoint', 'class'):
        replacement = Recorder()
        replacement.budget = Budget()
        if field == 'label': replacement.label = 'SYNTHETIC_CHANGED'
        if field == 'endpoint': replacement.base_url = 'SYNTHETIC_CHANGED'
        if field == 'class': replacement = type('SyntheticDifferentRecorder', (Recorder,), {})()
        try:
            load_model(legacy_path, replacement)
            raise AssertionError('legacy guard failed: ' + field)
        except ValueError as exc:
            legacy_guards[field] = str(exc)
        assert replacement.requests == []
    save(out / 'legacy-backend-guards.json', legacy_guards)

    after = {p: sha(root / p) for p in relevant}
    assert before == after
    result = {'source_commit': source_pin['source_commit'], 'implementation_commit': source_pin['implementation_commit'],
              'source_root': str(root), 'source_pin_sha256': sha(root / 'AUDIT_SOURCE.json'),
              'source_hashes': before, 'source_unchanged': before == after,
              'argv': sys.argv, 'python_version': sys.version, 'probe_sha256': sha(__file__),
              'real_model_calls': 0, 'data_scope': 'Released synthetic fixture and generated synthetic variants only',
              'verified_passes': ['arbitrary rich JSON preservation', 'normal no-profile complete request invariance',
                                  'all noncomplete profile statuses fail before backend call', 'build-time cap enforcement',
                                  'declared learned weights and calibration rejected', 'returned predictions uncalibrated',
                                  'legacy label/endpoint/class mismatch guards unchanged'],
              'verified_failures': ['loaded profile cap is not rechecked at consumer boundary',
                                    'explicit failed consumer statuses other than abstained are accepted',
                                    'invalid huge integer escapes ProfileFailure as OverflowError'],
              'limits': ['No real sources, labels, final data, or live calls.',
                         'Serialized cap probe recomputes hashes; it tests semantic validation, not hash tampering.',
                         'No claim that the normal builder produces inconsistent cap metadata.',
                         'No live output frequency, model quality, or production contamination assessed.',
                         'Source manifest, registry, and implementation-pin enforcement are reviewed separately.']}
    save(out / 'report.json', result)
    print(json.dumps({'report': str(out / 'report.json'), 'verified_failure_count': 3,
                      'source_unchanged': True, 'real_model_calls': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
