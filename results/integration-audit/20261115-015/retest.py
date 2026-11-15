#!/usr/bin/env python3
"""Retest semantic scale invariance using preserved synthetic audit evidence."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(body, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


class NoCalls:
    label, model = 'SYNTHETIC no-call extractor', 'SYNTHETIC scale-fix probe'

    def __init__(self):
        self.attempts = 0

    def complete(self, *args, **kwargs):
        self.attempts += 1
        raise AssertionError('A semantic reuse builder must not invoke an extractor')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--old-evidence', required=True, type=Path)
    parser.add_argument('--old-probe', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root, old, old_probe, out = (p.resolve() for p in (args.source_root, args.old_evidence, args.old_probe, args.out))
    out.mkdir(exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    pin = json.loads((root / 'AUDIT_SOURCE.json').read_text())
    before = {p: sha(root / p) for p in pin['files']}
    assert before == pin['files']
    assert not any('/handoffs/05/003' in p for p in before)
    old_before = {p.relative_to(old).as_posix(): sha(p) for p in old.rglob('*') if p.is_file()}
    old_report = json.loads((old / 'report.json').read_text())
    old_scaling = json.loads((old / 'subnormal-scaling-failure.json').read_text())
    assert sha(old_probe) == old_report['probe_sha256']
    assert old_report['claims_failed'] == ['cosine ranking is invariant to positive scaling for accepted finite vectors']
    fixture_path = root / 'docs/overnight/gio-profile-20261115/handoffs/05/004-semantic-fixture.json'
    fixture_hash = sha(fixture_path)
    assert fixture_hash == '8f2a601fd05fefdb8d383c0cf11e0afc98dadc54987650deaf1f2542e6cb1203'
    assert before['autoresearch/taste/overnight/retrieval.py'] == 'ea579653c0904612db4d3531e05c95660df659a1f6b89a9dd8fd0b77b45dca06'
    packet = json.loads(fixture_path.read_text())
    released = next(row for row in packet['records'] if row['method'] == 'semantic_retrieval')
    docs, base = packet['sources'], released['profile']['config']
    decision = base['decision']

    from autoresearch.taste.overnight import retrieval as r, baselines as b, contracts as k
    for module in (r, b, k):
        Path(module.__file__).resolve().relative_to(root)
    b.register_baselines()
    extractor = NoCalls()
    claims = []
    tolerance = 1e-12
    def claim(name, passed, evidence, limit=None):
        claims.append({'claim': name, 'status': 'verified' if passed else 'failed',
                       'evidence': evidence, 'limitation': limit})

    def evaluate(vectors, build=False):
        bundle = r.make_embedding_bundle(docs, base, decision, model='SYNTHETIC_SCALE_FIX', vectors=vectors,
                                        usage={'mode': 'offline_fixture', 'calls': 0})
        config = dict(base, embedding_bundle=bundle, embedding_bundle_sha256=bundle['bundle_sha256'],
                      embedding_model=bundle['model'], embedding_dimensions=bundle['dimensions'])
        ranked = r.rank_semantic(docs, config, decision, bundle)
        _, units = r._unit_vectors(vectors, len(vectors))
        scores = [sum(a * value for a, value in zip(units[0], unit)) for unit in units[1:]]
        row = {'vectors': vectors, 'unit_vectors': units, 'unit_norms': [math.hypot(*unit) for unit in units],
               'cosine_scores': scores, 'ranking': [chunk['document_id'] for chunk in ranked],
               'bundle_sha256': bundle['bundle_sha256']}
        if build:
            profile = k.build_profile(docs, config, extractor)
            row['profile'] = profile.to_dict()
            row['bundle'] = bundle
        return row

    old_tiny = old_scaling['subnormal']['bundle']['vectors']
    old_normal = old_scaling['same-directions-normal-scale']['bundle']['vectors']
    new_tiny, new_normal = evaluate(old_tiny, build=True), evaluate(old_normal, build=True)
    original = {'old': old_scaling, 'new': {'subnormal': new_tiny, 'normal': new_normal},
                'exact_original_vectors_reused': True,
                'adaptation': 'Regenerated bundle request hashes for current retrieval bytes; original vectors, documents and decision remain unchanged.'}
    save(out / 'original-case-old-new.json', original)
    claim('original subnormal ranking defect is fixed',
          old_scaling['subnormal']['ranking'] == ['fit-a', 'fit-b'] and
          old_scaling['same-directions-normal-scale']['ranking'] == ['fit-b', 'fit-a'] and
          new_tiny['ranking'] == new_normal['ranking'] == ['fit-b', 'fit-a'] and
          new_tiny['profile']['status'] == new_normal['profile']['status'] == 'complete',
          'original-case-old-new.json')

    tiny = float.fromhex('0x0.0000000000001p-1022')
    scales = [('minimum-subnormal', tiny), ('subnormal', 1e-320), ('small-normal', 1e-200),
              ('ordinary', 1.0), ('large', 1e200), ('near-maximum', 1.7e308)]
    grid = []
    for query, passage_a, passage_b in itertools.product(scales, repeat=3):
        row = evaluate([[query[1], 0], [passage_a[1], passage_a[1]], [passage_b[1], 0]])
        row['scales'] = {'query': query[0], 'passage_a': passage_a[0], 'passage_b': passage_b[0]}
        grid.append(row)
    signed = []
    for label, scale in scales:
        row = evaluate([[scale, scale], [-scale, -scale], [scale, -scale]])
        row['scale'] = label
        signed.append(row)
    all_rows = grid + signed
    max_norm_error = max(abs(norm - 1) for row in all_rows for norm in row['unit_norms'])
    min_cos = min(score for row in all_rows for score in row['cosine_scores'])
    max_cos = max(score for row in all_rows for score in row['cosine_scores'])
    save(out / 'scale-grid.json', {'scales': scales, 'rows': grid, 'signed_rows': signed,
                                 'tolerance': tolerance, 'max_unit_norm_error': max_norm_error,
                                 'min_cosine': min_cos, 'max_cosine': max_cos})
    claim('rankings preserve direction under independent tiny/normal/large scaling',
          len(grid) == 216 and all(row['ranking'] == ['fit-b', 'fit-a'] for row in all_rows),
          'scale-grid.json', 'Synthetic two-dimensional direction families, not exhaustive floating-point proof.')
    claim('tested unit norms and cosine bounds hold within floating-point tolerance',
          max_norm_error <= tolerance and min_cos >= -1 - tolerance and max_cos <= 1 + tolerance and
          all(math.isfinite(score) for row in all_rows for score in row['cosine_scores']),
          'scale-grid.json', 'Tolerance is 1e-12; no promise of exact real-number arithmetic.')

    large = evaluate([[1, 0], [1.7e308, 1.7e308], [1.7e308, 0]], build=True)
    save(out / 'large-finite-norm.json', large)
    claim('large finite vectors avoid former raw-norm overflow rejection',
          large['ranking'] == ['fit-b', 'fit-a'] and large['profile']['status'] == 'complete',
          'large-finite-norm.json', 'Intentional behavior change: finite vectors formerly rejected for raw norm overflow now normalize safely.')

    rejected = {}
    for name, vectors in [('zero', [[1, 0], [0, 0], [1, 0]]),
                          ('nonfinite', [[1, 0], [float('inf'), 0], [1, 0]]),
                          ('boolean', [[1, 0], [True, 0], [1, 0]]),
                          ('dimension', [[1, 0], [1], [1, 0]]),
                          ('huge-integer', [[1, 0], [10 ** 1000, 0], [1, 0]])]:
        try:
            evaluate(vectors)
            rejected[name] = {'outcome': 'accepted'}
        except Exception as exc:
            rejected[name] = {'outcome': 'rejected', 'exception_type': type(exc).__name__, 'message': str(exc)}
    save(out / 'invalid-vector-controls.json', rejected)
    claim('zero/nonfinite/malformed vectors remain rejected',
          all(row['outcome'] == 'rejected' for row in rejected.values()), 'invalid-vector-controls.json')

    old_bundle = old_scaling['subnormal']['bundle']
    old_cfg = dict(base, embedding_bundle=old_bundle, embedding_bundle_sha256=old_bundle['bundle_sha256'],
                   embedding_model=old_bundle['model'], embedding_dimensions=old_bundle['dimensions'])
    try:
        r.rank_semantic(docs, old_cfg, decision, old_bundle)
        old_bundle_result = {'outcome': 'accepted'}
    except Exception as exc:
        old_bundle_result = {'outcome': 'rejected', 'exception_type': type(exc).__name__, 'message': str(exc)}
    old_policy = {x['method_id']: x['prompt_sha256'] for x in old_report['registration_metadata']}
    new_policy = {x['method_id']: x['prompt_sha256'] for x in b.registration_metadata()}
    policy = {'old_retrieval_sha256': old_report['source_hashes']['autoresearch/taste/overnight/retrieval.py'],
              'new_retrieval_sha256': r.implementation_hash(), 'old_policy_hashes': old_policy,
              'new_policy_hashes': new_policy, 'old_bundle_under_new_code': old_bundle_result,
              'changed_methods': [name for name in new_policy if old_policy[name] != new_policy[name]]}
    save(out / 'source-and-policy-pins.json', policy)
    claim('helper and policy hashes change and old bundles cannot be silently reranked',
          policy['old_retrieval_sha256'] != policy['new_retrieval_sha256'] and
          len(policy['changed_methods']) == 7 and old_bundle_result['outcome'] == 'rejected',
          'source-and-policy-pins.json', 'Does not test shared runner attribution, scheduling or already-rendered profile dispatch.')

    source_by_id = {doc['document_id']: doc['content'] for doc in docs}
    preservation = []
    for name, row in [('tiny', new_tiny), ('normal', new_normal), ('large', large)]:
        profile = row['profile']
        preservation.append({'case': name, 'status': profile['status'],
            'within_cap': len(k.render_content(profile['content']).encode('utf-8')) <= profile['personalization_cap'],
            'exact_source_spans': all(p['text'] == source_by_id[p['document_id']][p['start']:p['end']]
                                     for p in profile['content']['passages']),
            'reuse_calls': profile['fit_usage']['calls']})
    save(out / 'profile-preservation.json', preservation)
    claim('fixed ranking preserves source spans, cap and zero-call reuse',
          extractor.attempts == 0 and all(row['status'] == 'complete' and row['within_cap'] and
          row['exact_source_spans'] and row['reuse_calls'] == 0 for row in preservation), 'profile-preservation.json')

    assert before == {p: sha(root / p) for p in pin['files']}
    assert old_before == {p.relative_to(old).as_posix(): sha(p) for p in old.rglob('*') if p.is_file()}
    assert sha(old_probe) == old_report['probe_sha256']
    report = {'source_commit': pin['source_commit'], 'implementation_commit': pin['implementation_commit'],
              'old_source_commit': old_report['source_commit'], 'old_implementation_commit': old_report['implementation_commit'],
              'argv': sys.argv, 'probe_sha256': sha(__file__), 'preserved_old_probe_sha256': sha(old_probe),
              'source_hashes': before, 'source_files_verified': len(before), 'source_unchanged': True,
              'old_evidence_hashes': old_before, 'old_evidence_unchanged': True,
              'fixture_sha256': fixture_hash, 'handoff003_ingested': False, 'real_model_calls': 0,
              'extractor_attempts': extractor.attempts, 'claims': claims,
              'claims_verified': [row['claim'] for row in claims if row['status'] == 'verified'],
              'claims_failed': [row['claim'] for row in claims if row['status'] == 'failed'],
              'claims_unverified': ['Provider-origin coordinate range and frequency of the old numerical defect',
                                    'Real provider availability, authenticity, quality, usage or cost',
                                    'Shared runner dispatch, live job authorization and final evaluation'],
              'adaptations': ['Replayed the preserved 009 probe unmodified against its original snapshot first.',
                              'Regenerated only current-code bundle metadata; original tiny and normal vector lists reused exactly.',
                              'New finite large-norm acceptance is tested as intended hardening, not scored as a regression.',
                              'No handoff 003 or real DEV readiness/data was archived or read.'],
              'live_execution_relevance': 'Fixes a demonstrated synthetic numerical edge case and broadens safe finite-vector range. '
                  'No evidence here establishes that ordinary provider vectors trigger the old defect; this is robustness hardening, '
                  'not proof of a live-data failure. Adopting the new code requires new policy pins and regenerated embedding bundles/profiles.'}
    save(out / 'report.json', report)
    print(json.dumps({'report': str(out / 'report.json'), 'verified': len(report['claims_verified']),
                      'failed': report['claims_failed'], 'grid_cases': len(grid), 'signed_cases': len(signed),
                      'max_unit_norm_error': max_norm_error, 'cosine_range': [min_cos, max_cos],
                      'real_model_calls': 0, 'source_unchanged': True}, sort_keys=True))
    return 1 if report['claims_failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
