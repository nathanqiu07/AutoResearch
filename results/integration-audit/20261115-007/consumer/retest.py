#!/usr/bin/env python3
"""Synthetic regression retest; never edits the pinned snapshot or old evidence."""
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
        json.dump(body, f, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def synthetic_builder(documents, config, extractor):
    return config['synthetic_builder_result']


class Recorder:
    label = 'SYNTHETIC consumer retest recorder'
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
    parser.add_argument('--old-evidence', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path, help='New output directory')
    args = parser.parse_args()
    root, old, out = args.source_root.resolve(), args.old_evidence.resolve(), args.out.resolve()
    out.mkdir(exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    pin = json.loads((root / 'AUDIT_SOURCE.json').read_text())
    before = {p: sha(root / p) for p in pin['files']}
    assert before == pin['files'], 'Snapshot does not match AUDIT_SOURCE.json'
    old_before = {p.relative_to(old).as_posix(): sha(p) for p in sorted(old.rglob('*')) if p.is_file()}
    old_report = json.loads((old / 'run-01/report.json').read_text())
    old_cap = json.loads((old / 'run-01/loaded-cap-bypass.json').read_text())
    old_statuses = json.loads((old / 'run-01/explicit-consumer-failure-statuses.json').read_text())
    old_huge = json.loads((old / 'run-01/oversized-integer-response.json').read_text())
    fixture_path = root / 'docs/overnight/gio-profile-20261115/infrastructure/fixture-v3.json'
    fixture = json.loads(fixture_path.read_text())
    assert sha(fixture_path) == 'cb6e8beecb6976e837be5d588471d0f5ac5c45cd4df02533b31bcabb640127e7'

    from autoresearch.taste.overnight import consumer as c, contracts as k, registry as r
    from autoresearch.llm import Budget
    from autoresearch.taste.methods.m0_none import NoHistory
    from autoresearch.taste.usermodel import load_model
    for module in (c, k, r):
        Path(module.__file__).resolve().relative_to(root)
    for method, empty in [('synthetic-consumer-retest', False), ('synthetic-empty-retest', True)]:
        r.register_builder(method, synthetic_builder, prompt_version='synthetic-retest-v1',
                           prompt_sha256=k.sha256_text('SYNTHETIC retest prompt'), allows_empty=empty)
    context, options = 'SYNTHETIC consumer decision', ['SYNTHETIC_A', 'SYNTHETIC_B']

    def build(result, **changes):
        config = dict(fixture['profile']['config'], method_id='synthetic-consumer-retest',
                      personalization_cap=8192, synthetic_builder_result=result)
        config.update(changes)
        return k.build_profile(fixture['documents'], config, Recorder())

    def prediction_config(profile):
        return {'method_implementation_hash': profile.method_implementation_hash,
                'renderer_implementation_hash': c.implementation_hash(),
                'profile_prompt_version': profile.prompt_version,
                'consumer_prompt_version': c.PROMPT_VERSION,
                'settings': {'temperature': 0.0, 'max_tokens': 128}}

    def rehash(body):
        body = json.loads(json.dumps(body))
        body['content_sha256'] = k.digest(body['content'])
        body['config_id'] = k.digest(body['config'])
        body.pop('profile_id', None)
        body['profile_id'] = k.digest(body)
        return body

    def invoke(profile, raw=None):
        recorder = Recorder(raw)
        try:
            prediction = c.predict_profile(profile, context, options, recorder, prediction_config(profile))
            result = {'outcome': 'prediction', 'prediction': asdict(prediction)}
        except Exception as exc:
            result = {'outcome': 'exception', 'exception_type': type(exc).__name__,
                      'status': getattr(exc, 'status', None), 'code': getattr(exc, 'code', None),
                      'message': str(exc)}
        return {**result, 'backend_calls': len(recorder.requests), 'requests': recorder.requests}

    def typed_failure(run, status, code, calls):
        return (run['outcome'] == 'exception' and run['exception_type'] == 'ProfileFailure'
                and run['status'] == status and run['code'] == code and run['backend_calls'] == calls)

    claims = []
    def claim(name, passed, artifact, limitation=None):
        claims.append({'claim': name, 'status': 'verified' if passed else 'failed',
                       'artifact': artifact, 'limitation': limitation})

    # Preserve exactly the previous 545-byte rich content, rebuilt with current pins.
    rich = old_cap['profile']['content']
    normal = build({'content': rich, 'status': 'complete'})
    normal_run = invoke(normal)
    assert normal_run['outcome'] == 'prediction', 'Positive setup failed; no regression result may be inferred'
    payload = json.loads(normal_run['requests'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])
    count = len(payload['personalization'].encode('utf-8'))
    assert count == 545
    save(out / 'rich-positive.json', {'profile': normal.to_dict(), 'run': normal_run})
    claim('rich JSON preservation remains intact', json.loads(payload['personalization']) == rich and
          set(payload) == {'context', 'options', 'personalization'}, 'rich-positive.json')

    cap_body = normal.to_dict()
    cap_body['personalization_cap'] = cap_body['config']['personalization_cap'] = 1
    cap_body = rehash(cap_body)
    assert cap_body['content_sha256'] == k.digest(rich)
    assert cap_body['config_id'] == k.digest(cap_body['config'])
    assert cap_body['profile_id'] == k.digest({key: value for key, value in cap_body.items() if key != 'profile_id'})
    try:
        k.ProfileArtifact.from_dict(cap_body)
        decoder = {'outcome': 'accepted'}
    except Exception as exc:
        decoder = {'outcome': 'rejected', 'exception_type': type(exc).__name__, 'message': str(exc)}
    # Exercise revalidation inside predict_profile too, bypassing only the public constructor.
    raw_artifact = k.ProfileArtifact(k.canonical_json(cap_body))
    cap_run = invoke(raw_artifact)
    cap_passed = (decoder.get('exception_type') == 'ValueError' and
                  decoder.get('message') == 'complete profile exceeds personalization cap' and
                  typed_failure(cap_run, 'invalid', 'invalid_serialized_profile', 0))
    save(out / 'loaded-cap-old-new.json', {'old': old_cap, 'new': {'profile': cap_body,
         'decoder': decoder, 'consumer_boundary': cap_run, 'actual_rendered_bytes': count},
         'setup': 'Current pins; both cap copies=1; content/config/profile hashes recomputed; rendered count unchanged=545.'})
    claim('loaded 545-byte profile with cap=1 is rejected before backend invocation', cap_passed,
          'loaded-cap-old-new.json', 'Not a tokenizer test or a claim about every possible serialized invalidity.')

    response_results = {}
    for status in ('invalid', 'unavailable', 'unsupported', 'empty', 'abstained'):
        raw = json.dumps({'status': status, 'probabilities': [0.25, 0.75],
                          'rationale': 'SYNTHETIC failed response with fallback probabilities'})
        run = invoke(normal, raw)
        response_results[status] = {'old': old_statuses[status], 'new': run}
    response_passed = all(typed_failure(row['new'], status, 'consumer_' + status, 1)
                          for status, row in response_results.items())
    unknown = invoke(normal, '{"status":"SYNTHETIC_UNKNOWN","probabilities":[0.25,0.75]}')
    save(out / 'consumer-statuses-old-new.json', {'cases': response_results, 'new_unknown_status_control': unknown})
    claim('explicit consumer failure statuses remain failed outcomes', response_passed and
          typed_failure(unknown, 'invalid', 'unknown_consumer_status', 1), 'consumer-statuses-old-new.json')

    huge_run = invoke(normal, old_huge['raw_response'])
    save(out / 'huge-integer-old-new.json', {'old': old_huge, 'new': huge_run,
                                          'response_reused_byte_for_byte': True})
    claim('same 400-digit probability produces typed invalid failure',
          typed_failure(huge_run, 'invalid', 'invalid_probability_distribution', 1), 'huge-integer-old-new.json')

    empty_cases = []
    for i in range(3):
        profile = build({'content': {}, 'status': 'complete'}, method_id='synthetic-empty-retest', replicate_id=i,
                        synthetic_personal_canary={'identity': 'SYNTHETIC_PERSON_' + str(i),
                        'history': ['SYNTHETIC_HISTORY_' + str(i)], 'principles': ['SYNTHETIC_PRINCIPLE_' + str(i)]})
        body = profile.to_dict()
        body['extractor']['label'] = 'SYNTHETIC_EXTRACTOR_' + str(i)
        # New consistency checks require the duplicated researcher ID to agree.
        body['researcher_id'] = body['config']['researcher_id'] = 'SYNTHETIC_RESEARCHER_' + str(i)
        body = rehash(body)
        loaded = k.ProfileArtifact.from_dict(body)
        empty_cases.append({'profile': body, 'run': invoke(loaded)})
    empty_passed = all(row['run']['outcome'] == 'prediction' and
                       row['run']['requests'] == empty_cases[0]['run']['requests'] for row in empty_cases)
    empty_payload = json.loads(empty_cases[0]['run']['requests'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])
    save(out / 'empty-invariance.json', {'cases': empty_cases, 'adaptation':
         'Changed researcher_id in both artifact/config and recomputed config_id/profile_id; all cases loaded and made one synthetic call.'})
    claim('normal empty controls preserve complete request invariance', empty_passed and
          empty_payload['personalization'] == '', 'empty-invariance.json', 'Tested empty content with differing metadata, not a malformed nonempty control.')

    declared = {}
    for status in ('empty', 'unsupported', 'invalid', 'unavailable', 'abstained'):
        declared[status] = invoke(build({'content': rich, 'status': status, 'error_code': 'SYNTHETIC_' + status}))
    save(out / 'declared-profile-statuses.json', declared)
    claim('noncomplete profile statuses stop before backend calls', all(typed_failure(run, status,
          'SYNTHETIC_' + status, 0) for status, run in declared.items()), 'declared-profile-statuses.json')
    oversized = invoke(build({'content': rich, 'status': 'complete'}, personalization_cap=1))
    save(out / 'builder-cap-control.json', oversized)
    claim('build-time cap enforcement remains intact', typed_failure(oversized, 'invalid',
          'personalization_cap_exceeded', 0), 'builder-cap-control.json')

    calibration = {}
    for name, fields in [('learned-weights', {'weights_status': 'learned'}), ('calibrated', {'calibrated': True})]:
        calibration[name] = invoke(build(dict({'content': rich, 'status': 'complete'}, **fields)))
    calibration['raw_backend_claim'] = invoke(normal, '{"probabilities":[0.25,0.75],"calibrated":true}')
    save(out / 'calibration-controls.json', calibration)
    claim('learned weights and calibration remain separated', all(typed_failure(calibration[name], 'invalid',
          'learned_weights_or_calibration_not_neutral', 0) for name in ('learned-weights', 'calibrated')) and
          normal_run['prediction']['calibrated'] is False and
          calibration['raw_backend_claim']['prediction']['calibrated'] is False, 'calibration-controls.json')

    legacy_backend = Recorder()
    legacy_backend.budget = Budget()
    legacy_path = out / 'synthetic-legacy-m0.json'
    NoHistory(legacy_backend).save(legacy_path)
    guards = {}
    for field in ('label', 'endpoint', 'class'):
        alternate = Recorder()
        if field == 'label': alternate.label = 'SYNTHETIC_CHANGED'
        if field == 'endpoint': alternate.base_url = 'SYNTHETIC_CHANGED'
        if field == 'class': alternate = type('SyntheticDifferentRecorder', (Recorder,), {})()
        alternate.budget = Budget()
        try:
            load_model(legacy_path, alternate)
            guards[field] = {'outcome': 'accepted'}
        except Exception as exc:
            guards[field] = {'outcome': 'exception', 'exception_type': type(exc).__name__, 'message': str(exc)}
        guards[field]['backend_calls'] = len(alternate.requests)
    save(out / 'legacy-backend-controls.json', guards)
    claim('legacy backend identity guards remain intact', all(row.get('exception_type') == 'ValueError' and
          'saved model backend differs' in row.get('message', '') and row['backend_calls'] == 0
          for row in guards.values()), 'legacy-backend-controls.json')

    after = {p: sha(root / p) for p in pin['files']}
    old_after = {p.relative_to(old).as_posix(): sha(p) for p in sorted(old.rglob('*')) if p.is_file()}
    assert before == after and old_before == old_after
    verified = [x['claim'] for x in claims if x['status'] == 'verified']
    failed = [x['claim'] for x in claims if x['status'] == 'failed']
    report = {'source_commit': pin['source_commit'], 'implementation_commit': pin['implementation_commit'],
              'old_source_commit': old_report['source_commit'], 'old_implementation_commit': old_report['implementation_commit'],
              'source_root': str(root), 'old_evidence_root': str(old), 'argv': sys.argv,
              'python_version': sys.version, 'script_sha256': sha(__file__),
              'source_pin_sha256': sha(root / 'AUDIT_SOURCE.json'), 'source_hashes': before,
              'source_files_verified': len(before), 'source_unchanged': before == after,
              'old_evidence_hashes': old_before, 'old_evidence_unchanged': old_before == old_after,
              'fixture_v3_sha256': sha(fixture_path), 'real_model_calls': 0,
              'claims': claims, 'claims_verified': verified, 'claims_failed': failed,
              'claims_unverified': ['Live backend behavior and malformed-output frequency',
                                    'Researcher fidelity, scientific utility or calibration quality',
                                    'Tokenizer-specific usage or runner job-cap binding',
                                    'All source/registry/runner/confirmation enforcement; reviewed separately'],
              'probe_adaptations': ['Rebuilt the exact old 545-byte rich content with current method/renderer pins.',
                                    'Low-cap variant changes both cap copies and rehashes config/content/profile.',
                                    'Decoder rejection is recorded separately; raw ProfileArtifact then tests consumer revalidation.',
                                    'Empty metadata canaries change both researcher_id copies and rehash config/profile before loading.',
                                    'Old huge-integer response reused byte for byte; old status cases use identical response fields.'],
              'limits': ['Synthetic fixtures and generated variants only; no real labels, corpus, final data, or live calls.',
                         'Old evidence and snapshot never modified. Setup errors are not counted as verified fixes.']}
    save(out / 'report.json', report)
    print(json.dumps({'report': str(out / 'report.json'), 'claims_verified': len(verified), 'claims_failed': failed,
                      'source_files_verified': len(before), 'source_unchanged': True,
                      'old_evidence_unchanged': True, 'real_model_calls': 0}, sort_keys=True))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
