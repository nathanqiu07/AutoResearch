#!/usr/bin/env python3
"""Synthetic-only semantic retrieval audit against separately pinned snapshots."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clone(value):
    return json.loads(json.dumps(value))


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(body, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


class NoCalls:
    label, model = 'SYNTHETIC no-call extractor', 'SYNTHETIC fixture'

    def __init__(self):
        self.attempts = 0

    def complete(self, *args, **kwargs):
        self.attempts += 1
        raise AssertionError('Synthetic baseline must not invoke extractor')


class Recorder:
    def __init__(self):
        self.requests = []

    def complete(self, prompt, **settings):
        self.requests.append({'prompt': prompt, 'settings': settings})
        return '{"probabilities":[0.4,0.6],"rationale":"SYNTHETIC plumbing only"}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--old-release', action='store_true')
    args = parser.parse_args()
    root, out, fixture_path = args.source_root.resolve(), args.out.resolve(), args.fixture.resolve()
    out.mkdir(exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    pin = json.loads((root / 'AUDIT_SOURCE.json').read_text())
    before = {p: sha(root / p) for p in pin['files']}
    assert before == pin['files'], 'source pin mismatch'
    assert sha(fixture_path) == 'aa6e17c2e91e5eab6ffd4fc233159de1ffdf535b060470adec6d932bd0f26fe5'
    packet = json.loads(fixture_path.read_text())
    record = next(row for row in packet['records'] if row['method'] == 'semantic_retrieval')
    docs, cfg = clone(packet['sources']), clone(record['profile']['config'])
    decision = cfg['decision']
    from autoresearch.taste.overnight import retrieval as r, baselines as b, contracts as k, consumer as c
    for module in (r, b, k, c):
        Path(module.__file__).resolve().relative_to(root)
    b.register_baselines()
    extractor = NoCalls()
    if args.old_release:
        old_profile = k.build_profile(docs, cfg, extractor)
        result = {'release': 'old', 'source_commit': pin['source_commit'],
                  'implementation_commit': pin['implementation_commit'], 'source_hashes': before,
                  'argv': sys.argv, 'probe_sha256': sha(__file__), 'fixture_sha256': sha(fixture_path),
                  'semantic_helper_exists': hasattr(r, 'rank_semantic'),
                  'semantic_status_with_new_synthetic_bundle': old_profile.status,
                  'semantic_error_code': old_profile.error_code,
                  'registration_metadata': b.registration_metadata(),
                  'extractor_attempts': extractor.attempts, 'real_model_calls': 0,
                  'limits': ['Old code evaluated separately; no attempt to migrate old artifacts.']}
        assert not result['semantic_helper_exists'] and old_profile.status == 'unavailable'
        assert extractor.attempts == 0
        assert before == {p: sha(root / p) for p in pin['files']}
        result['source_unchanged'] = True
        save(out / 'report.json', result)
        print(json.dumps({'release': 'old', 'semantic_status': old_profile.status, 'real_model_calls': 0}))
        return 0

    results, claims = {}, []
    def claim(name, passed, evidence, limit=None):
        claims.append({'claim': name, 'status': 'verified' if passed else 'failed',
                       'evidence': evidence, 'limitation': limit})

    def bundle_config(bundle, base=None):
        return dict(cfg if base is None else base, embedding_bundle=bundle,
                    embedding_bundle_sha256=bundle['bundle_sha256'],
                    embedding_model=bundle['model'], embedding_dimensions=bundle['dimensions'])

    def rehash_bundle(bundle):
        value = clone(bundle)
        value.pop('bundle_sha256', None)
        value['bundle_sha256'] = k.digest(value)
        return value

    def rank_attempt(documents, config, query, bundle):
        try:
            ranking = r.rank_semantic(documents, config, query, bundle)
            return {'outcome': 'accepted', 'ranking': [x['document_id'] for x in ranking]}
        except Exception as exc:
            return {'outcome': 'rejected', 'exception_type': type(exc).__name__, 'message': str(exc)}

    bundle = clone(cfg['embedding_bundle'])
    rank = r.rank_semantic(docs, cfg, decision, bundle)
    inputs = r.embedding_inputs(docs, cfg, decision)
    chunks = r.chunk_documents(docs, cfg)
    assert [x['document_id'] for x in rank] == ['fit-b', 'fit-a']
    assert inputs == [r.decision_query(decision)] + [x['text'] for x in chunks]
    assert bundle['request']['input_hashes'] == [k.sha256_text(text) for text in inputs]
    profile = k.build_profile(docs, cfg, extractor)
    assert profile.status == 'complete' and extractor.attempts == 0
    save(out / 'positive.json', {'source_documents': docs, 'config': cfg, 'inputs': inputs,
                                'chunks': chunks, 'ranking': rank, 'profile': profile.to_dict()})
    claim('released bundle ranks synthetic vectors and binds exact embedding inputs', True, 'positive.json')

    binding = {}
    for name, changed_decision in [('context', dict(decision, context='SYNTHETIC_CHANGED')),
                                   ('option-order', dict(decision, options=list(reversed(decision['options'])))),
                                   ('extra-label-field', dict(decision, chosen='SYNTHETIC_FORBIDDEN'))]:
        binding[name] = rank_attempt(docs, cfg, changed_decision, bundle)
    for name, changes in [('chunk-width', {'chunk_chars': 12}), ('model', {'embedding_model': 'SYNTHETIC_OTHER'}),
                          ('dimension', {'embedding_dimensions': 3}), ('boolean-dimension', {'embedding_dimensions': True})]:
        binding[name] = rank_attempt(docs, dict(cfg, **changes), decision, bundle)
    changed_docs = clone(docs)
    changed_docs[0]['content'] += ' SYNTHETIC_CHANGED'
    changed_docs[0]['content_sha256'] = k.sha256_text(changed_docs[0]['content'])
    changed_cfg = dict(cfg, allowed_sources=k.source_manifest(changed_docs),
                       allowed_source_manifest_hash=k.digest(k.source_manifest(changed_docs)))
    binding['changed-approved-source-content'] = rank_attempt(changed_docs, changed_cfg, decision, bundle)
    smaller = docs[:1]
    smaller_cfg = dict(cfg, allowed_sources=k.source_manifest(smaller),
                       allowed_source_manifest_hash=k.digest(k.source_manifest(smaller)))
    binding['changed-approved-source-set'] = rank_attempt(smaller, smaller_cfg, decision, bundle)
    tampered = clone(bundle)
    tampered['vectors'][1] = [1, 0]
    binding['unrehashed-vector-change'] = rank_attempt(docs, cfg, decision, tampered)
    for field, replacement in [('chunk_hashes', ['0' * 64] * len(chunks)),
                               ('input_hashes', ['0' * 64] * len(inputs)),
                               ('implementation_hash', '0' * 64), ('input_policy', 'SYNTHETIC_OTHER_POLICY')]:
        changed = clone(bundle)
        changed['request'][field] = replacement
        changed = rehash_bundle(changed)
        binding['rehashed-request-' + field] = rank_attempt(docs, bundle_config(changed), decision, changed)
    changed = clone(bundle)
    changed['dimensions'] = 3
    changed = rehash_bundle(changed)
    binding['rehashed-bundle-dimension'] = rank_attempt(docs, dict(bundle_config(changed), embedding_dimensions=2), decision, changed)
    save(out / 'binding-rejections.json', binding)
    claim('source/chunk/query/model/dimension/hash mismatches are rejected',
          all(row['outcome'] == 'rejected' for row in binding.values()), 'binding-rejections.json',
          'Consistency only; self-declared model and usage metadata do not authenticate a provider.')

    vector_cases = {'zero-query': [[0, 0], [0, 1], [1, 0]],
                    'zero-document': [[1, 0], [0, 0], [1, 0]],
                    'nonfinite-nan': [[1, 0], [float('nan'), 0], [1, 0]],
                    'nonfinite-inf': [[1, 0], [float('inf'), 0], [1, 0]],
                    'boolean': [[1, 0], [True, 0], [1, 0]],
                    'wrong-dimension': [[1, 0], [1], [1, 0]],
                    'wrong-count': [[1, 0], [0, 1]],
                    'huge-integer': [[1, 0], [10 ** 1000, 0], [1, 0]],
                    'overflow-norm': [[1, 0], [1.7e308, 1.7e308], [1, 0]]}
    vectors_result = {}
    for name, values in vector_cases.items():
        try:
            r.make_embedding_bundle(docs, cfg, decision, model='SYNTHETIC_BAD_VECTORS', vectors=values,
                                    usage={'mode': 'offline_fixture', 'calls': 0})
            vectors_result[name] = {'outcome': 'accepted'}
        except Exception as exc:
            vectors_result[name] = {'outcome': 'rejected', 'exception_type': type(exc).__name__, 'message': str(exc)}
    save(out / 'invalid-vector-rejections.json', vectors_result)
    claim('tested zero/nonfinite/malformed/overflow vectors are rejected',
          all(row['outcome'] == 'rejected' for row in vectors_result.values()), 'invalid-vector-rejections.json')

    tiny = float.fromhex('0x0.0000000000001p-1022')
    tiny_vectors, scaled_vectors = [[1, 0], [tiny, tiny], [1, 0]], [[1, 0], [1, 1], [1, 0]]
    scaling_runs = {}
    for name, values in [('subnormal', tiny_vectors), ('same-directions-normal-scale', scaled_vectors)]:
        item = r.make_embedding_bundle(docs, cfg, decision, model='SYNTHETIC_SCALING_CHECK', vectors=values,
                                       usage={'mode': 'offline_fixture', 'calls': 0})
        conf = bundle_config(item)
        ranked = r.rank_semantic(docs, conf, decision, item)
        _, unit = r._unit_vectors(values, len(inputs))
        built = k.build_profile(docs, conf, extractor)
        scaling_runs[name] = {'bundle': item, 'normalized_vectors': unit,
                              'unit_norms': [math.hypot(*v) for v in unit],
                              'query_dot_scores': [sum(a * b for a, b in zip(unit[0], v)) for v in unit[1:]],
                              'ranking': [x['document_id'] for x in ranked],
                              'profile_status': built.status,
                              'packed_order': [p['document_id'] for p in built.content['passages']]}
    save(out / 'subnormal-scaling-failure.json', scaling_runs)
    claim('cosine ranking is invariant to positive scaling for accepted finite vectors',
          scaling_runs['subnormal']['ranking'] == scaling_runs['same-directions-normal-scale']['ranking'],
          'subnormal-scaling-failure.json', 'Failure uses minimum positive IEEE-754 subnormal coordinates; no claim about provider output frequency.')

    cap_results = []
    original_by_id = {d['document_id']: d['content'] for d in docs}
    for cap in (0, 10, 70, 95, 128, 256, 512):
        current = k.build_profile(docs, dict(cfg, personalization_cap=cap), extractor)
        row = {'cap': cap, 'status': current.status, 'error_code': current.error_code,
               'rendered_bytes': len(k.render_content(current.content).encode('utf-8'))}
        if current.status == 'complete':
            row['content'] = current.content
            row['within_cap'] = row['rendered_bytes'] <= cap
            row['exact_source_spans'] = all(set(p) == {'document_id', 'start', 'end', 'text'} and
                                           p['text'] == original_by_id[p['document_id']][p['start']:p['end']]
                                           for p in current.content['passages'])
        cap_results.append(row)
    save(out / 'cap-and-source-preservation.json', cap_results)
    claim('complete semantic profiles fit declared byte caps and preserve exact source spans',
          all(row.get('within_cap', True) and row.get('exact_source_spans', True) for row in cap_results),
          'cap-and-source-preservation.json', 'Byte bounds are not measured tokenizer usage.')

    consumer_cfg = {'method_implementation_hash': profile.method_implementation_hash,
                    'renderer_implementation_hash': c.implementation_hash(),
                    'profile_prompt_version': profile.prompt_version,
                    'consumer_prompt_version': c.PROMPT_VERSION,
                    'settings': {'temperature': 0.0, 'max_tokens': 128}}
    adapter = {}
    for name, query in [('matching', decision), ('changed-context', dict(decision, context='SYNTHETIC_CHANGED')),
                         ('changed-option-order', dict(decision, options=list(reversed(decision['options']))))]:
        consumer = Recorder()
        try:
            prediction = b.predict_baseline(profile, query['context'], query['options'], consumer, consumer_cfg)
            row = {'outcome': 'prediction', 'prediction': asdict(prediction)}
        except Exception as exc:
            row = {'outcome': 'exception', 'exception_type': type(exc).__name__,
                   'status': getattr(exc, 'status', None), 'code': getattr(exc, 'code', None)}
        adapter[name] = dict(row, consumer_calls=len(consumer.requests), requests=consumer.requests)
    payload = json.loads(adapter['matching']['requests'][0]['prompt'].split('INPUT_JSON:\n', 1)[1])
    adapter['matching']['only_selected_source_spans_in_personalization'] = (
        json.loads(payload['personalization']) == profile.content and set(payload) == {'context', 'options', 'personalization'})
    save(out / 'semantic-adapter.json', adapter)
    claim('predict_baseline applies semantic decision binding before the consumer',
          adapter['matching']['outcome'] == 'prediction' and
          adapter['matching']['only_selected_source_spans_in_personalization'] and
          all(adapter[name].get('code') == 'retrieved_profile_decision_mismatch' and adapter[name]['consumer_calls'] == 0
              for name in ('changed-context', 'changed-option-order')), 'semantic-adapter.json',
          'Only the adapter is exercised; actual shared runner dispatch remains unverified and pending owner integration.')

    # This is deliberately fake producer metadata; no live job or provider is asserted.
    producer_usage = {'mode': 'live', 'producer_job_id': 'SYNTHETIC_NOT_A_REAL_PRODUCER_JOB',
                      'response_sha256': 'a' * 64, 'calls': 7, 'input_tokens': 123,
                      'reported_api_usd': 0.01, 'evidence_status': 'SYNTHETIC_DECLARATION_ONLY'}
    producer_bundle = r.make_embedding_bundle(docs, cfg, decision, model='SYNTHETIC_DECLARED_MODEL',
        vectors=[[1, 0], [0, 1], [1, 0]], usage=producer_usage)
    reuse_profiles = [k.build_profile(docs, bundle_config(producer_bundle), extractor) for _ in range(2)]
    usage_record = {'fake_producer_usage': producer_usage,
                    'reuse_fit_usage': [p.fit_usage for p in reuse_profiles],
                    'extractor_attempts': extractor.attempts,
                    'provider_authenticity': 'not_verified', 'actual_production_cost': 'not_verified'}
    save(out / 'reuse-and-producer-usage.json', usage_record)
    claim('pure reuse makes zero extraction calls and preserves declared producer usage separately',
          extractor.attempts == 0 and all(p.status == 'complete' and p.fit_usage['calls'] == 0 and
          p.fit_usage['cost_status'] == 'no_model_calls' and p.fit_usage['embedding_production_usage'] == producer_usage
          for p in reuse_profiles), 'reuse-and-producer-usage.json',
          'Metadata consistency is not proof of a real producer job, provider, usage or cost; coordinator accounting is not tested.')
    missing_usage = {}
    for name, usage in [('missing-producer', {'mode': 'live', 'response_sha256': 'a' * 64}),
                         ('missing-response', {'mode': 'live', 'producer_job_id': 'SYNTHETIC_JOB'}),
                         ('invalid-response-hash', {'mode': 'live', 'producer_job_id': 'SYNTHETIC_JOB', 'response_sha256': 'wrong'})]:
        altered = clone(bundle)
        altered['usage'] = usage
        altered = rehash_bundle(altered)
        result = k.build_profile(docs, bundle_config(altered), extractor)
        missing_usage[name] = {'status': result.status, 'error_code': result.error_code}
    save(out / 'producer-provenance-schema-rejections.json', missing_usage)
    claim('missing required live producer metadata makes semantic input unavailable',
          all(row == {'status': 'unavailable', 'error_code': 'invalid_embedding_bundle'} for row in missing_usage.values()),
          'producer-provenance-schema-rejections.json')

    after = {p: sha(root / p) for p in pin['files']}
    assert before == after and extractor.attempts == 0
    report = {'release': 'new', 'source_commit': pin['source_commit'], 'implementation_commit': pin['implementation_commit'],
              'source_root': str(root), 'archive_sha256': pin['archive_sha256'], 'source_hashes': before,
              'source_unchanged': True, 'source_files_verified': len(before), 'argv': sys.argv,
              'probe_sha256': sha(__file__), 'fixture_sha256': sha(fixture_path), 'real_model_calls': 0,
              'extractor_attempts': extractor.attempts, 'registration_metadata': b.registration_metadata(),
              'claims': claims, 'claims_verified': [x['claim'] for x in claims if x['status'] == 'verified'],
              'claims_failed': [x['claim'] for x in claims if x['status'] == 'failed'],
              'claims_unverified': ['Provider authenticity, availability, quality, actual production usage and cost',
                                    'That query/document embeddings came from one actual provider call with identical settings',
                                    'Shared runner dispatch and coordinator producer-job accounting',
                                    'Real source/label isolation, preference fidelity, final evaluation'],
              'limits': ['Released synthetic fixture and generated synthetic variants only.',
                         'Live producer absence is an announced pending integration step, not counted as a bug.',
                         'The source branch includes its own pinned neutral dependencies; no silent migration to other infrastructure releases.']}
    save(out / 'report.json', report)
    print(json.dumps({'report': str(out / 'report.json'), 'verified': len(report['claims_verified']),
                      'failed': report['claims_failed'], 'real_model_calls': 0, 'source_unchanged': True}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
