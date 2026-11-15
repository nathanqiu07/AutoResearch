"""Synthetic evidence only: no researcher corpus or evaluation labels."""
import copy
import importlib.util
import json
import unittest

from autoresearch.llm import LLM
from autoresearch.taste.overnight.contracts import (
    build_profile, digest, render_content, sha256_text, source_manifest,
)


def document(identifier, researcher, text, **extra):
    return dict(document_id=identifier, researcher_id=researcher, content=text,
                content_sha256=sha256_text(text), document_group=identifier,
                permitted_spans=[dict(start=0, end=len(text), text=text, speaker=researcher)],
                **extra)


def statement(doc, **extra):
    return dict(text=doc['content'], kind='preference', evidence_status='explicit',
                conditions=None, date=None,
                sources=[dict(document_id=doc['document_id'], start=0,
                              end=len(doc['content']), quote=doc['content'])], **extra)


class Extractor(LLM):
    name = 'offline-synthetic-hypotheses'
    model = 'fixture-v1'

    def __init__(self, result, failure=False):
        super().__init__()
        self.result, self.failure, self.calls = result, failure, []

    def complete(self, prompt, **settings):
        self.calls.append((prompt, settings))
        if self.failure:
            raise RuntimeError('synthetic failure')
        return self.result if isinstance(self.result, str) else json.dumps(self.result)


class HypothesesBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # An assertion (rather than an import error) exposes the missing feature.
        if importlib.util.find_spec('autoresearch.taste.overnight.profiles_hypotheses'):
            from autoresearch.taste.overnight import profiles_hypotheses
            cls.module = profiles_hypotheses
            cls.module.register_hypotheses_builders()
        else:
            cls.module = None

    def setUp(self):
        self.assertIsNotNone(self.module, 'P7 and P8 builders must exist')
        self.target = document('t', 'target', 'Prefer small tests.')
        self.peer = document('p', 'peer', 'Prefer large tests.')
        self.docs = [self.target, self.peer]

    def config(self, method, docs=None, **extra):
        docs = self.docs if docs is None else docs
        sources = source_manifest(docs)
        config = dict(method_id=method, researcher_id='target', allowed_sources=sources,
                      allowed_source_manifest_hash=digest(sources), personalization_cap=8192,
                      replicate_id=0, code_sha='a' * 40, approved_peer_sources=True,
                      evidence_policy='explicit-only', extractor_settings={'temperature': 0, 'max_tokens': 4096})
        config.update(extra)
        return config

    def contrast(self, relation='different', target=None, peer=None):
        return {'contrasts': [{'relation': relation,
                              'target': statement(self.target) if target is None else target,
                              'peer': statement(self.peer) if peer is None else peer}]}

    def hypotheses(self, docs=None):
        docs = [self.target] if docs is None else docs
        return {'hypotheses': [{'id': 'h' + str(i), 'statement': statement(doc), 'weight': None}
                               for i, doc in enumerate(docs)], 'relations': []}

    def run_builder(self, method, result, docs=None, **extra):
        docs = self.docs if docs is None else docs
        backend = Extractor(result)
        profile = build_profile(docs, self.config(method, docs, **extra), backend)
        return profile, backend

    def test_p7_keeps_both_exact_supporting_spans(self):
        profile, backend = self.run_builder('P7', self.contrast())
        self.assertEqual(profile.status, 'complete')
        record = profile.content['contrasts'][0]
        self.assertEqual(record['status'], 'supported')
        self.assertEqual(record['target']['sources'][0]['quote'], 'Prefer small tests.')
        self.assertEqual(record['peer']['sources'][0]['document_id'], 'p')
        self.assertEqual(profile.fit_usage['independent_source_groups'], 2)
        self.assertEqual(len(backend.calls), 1)

    def test_missing_peer_bundle_is_unavailable_without_call(self):
        profile, backend = self.run_builder('P7', self.contrast(), [self.target])
        self.assertEqual(profile.status, 'unavailable')
        self.assertEqual(profile.error_code, 'approved_peer_evidence_unavailable')
        self.assertEqual(backend.calls, [])

    def test_silence_is_not_disagreement(self):
        response = self.contrast()
        response['contrasts'][0]['peer'] = None
        profile, _ = self.run_builder('P7', response)
        self.assertEqual(profile.status, 'unsupported')
        self.assertEqual(profile.content['contrasts'][0]['reason'], 'missing_peer_support')
        self.assertEqual(profile.content['contrasts'][0]['relation'], 'unresolved')

    def test_shared_preference_is_preserved(self):
        self.peer = document('p', 'peer', 'I prefer small tests.')
        self.docs = [self.target, self.peer]
        profile, _ = self.run_builder('P7', self.contrast('shared'))
        self.assertEqual(profile.status, 'complete')
        self.assertEqual(profile.content['contrasts'][0]['relation'], 'shared')

    def test_source_groups_prevent_independent_support_from_collaboration(self):
        self.target['project_group'] = self.peer['project_group'] = 'joint-project'
        profile, _ = self.run_builder('P7', self.contrast())
        self.assertEqual(profile.status, 'unsupported')
        self.assertEqual(profile.fit_usage['independent_source_groups'], 1)
        self.assertEqual(profile.content['contrasts'][0]['reason'], 'dependent_target_peer_support')

    def test_repeated_documents_do_not_inflate_support_count(self):
        duplicate = document('t-copy', 'target', self.target['content'])
        response = self.contrast()
        response['contrasts'][0]['target']['sources'] += statement(duplicate)['sources']
        profile, _ = self.run_builder('P7', response, self.docs + [duplicate])
        self.assertEqual(profile.status, 'complete')
        self.assertEqual(profile.fit_usage['independent_source_groups'], 2)

    def test_exact_allowlist_blocks_unapproved_peer_before_call(self):
        config = self.config('P7', [self.target])
        backend = Extractor(self.contrast())
        with self.assertRaisesRegex(ValueError, 'source set'):
            build_profile(self.docs, config, backend)
        self.assertEqual(backend.calls, [])

    def test_known_nonfit_peer_never_reaches_extractor(self):
        self.peer['split_eligibility'] = 'confirmation'
        profile, backend = self.run_builder('P7', self.contrast())
        self.assertEqual(profile.status, 'invalid')
        self.assertEqual(backend.calls, [])

    def test_bad_provenance_is_invalid_instead_of_empty_success(self):
        for change in ('unknown', 'quote', 'offset', 'attribution', 'wrong_side'):
            docs, response = copy.deepcopy(self.docs), self.contrast()
            span = response['contrasts'][0]['peer']['sources'][0]
            if change == 'unknown':
                span['document_id'] = 'held-out-unknown'
            elif change == 'quote':
                span['quote'] = 'invented'
            elif change == 'offset':
                span['start'] = True
            elif change == 'attribution':
                docs[1]['permitted_spans'][0]['speaker'] = 'someone-else'
            else:
                response['contrasts'][0]['peer'] = statement(self.target)
            with self.subTest(change=change):
                profile, _ = self.run_builder('P7', response, docs)
                self.assertEqual(profile.status, 'invalid')

    def test_missing_attributed_span_cannot_be_filled_by_coauthorship(self):
        self.peer.pop('permitted_spans')
        self.peer['author'] = 'target and peer'
        profile, backend = self.run_builder('P7', self.contrast())
        self.assertEqual(profile.status, 'unavailable')
        self.assertEqual(backend.calls, [])

    def test_evidence_policy_never_promotes_inference_to_explicit(self):
        response = self.contrast()
        response['contrasts'][0]['target']['evidence_status'] = 'inferred'
        rejected, _ = self.run_builder('P7', response)
        self.assertEqual(rejected.status, 'invalid')
        self.assertEqual(rejected.error_code, 'inference_not_allowed')
        accepted, _ = self.run_builder('P7', response, evidence_policy='marked-inference')
        self.assertEqual(accepted.status, 'complete')
        self.assertEqual(accepted.content['contrasts'][0]['target']['evidence_status'], 'inferred')

    def test_p8_conflicts_preserve_hypotheses_unknown_dates_and_weights(self):
        later = document('t2', 'target', 'Prefer large tests.', published_at='2026-11-14')
        response = self.hypotheses([self.target, later])
        response['relations'] = [{'kind': 'incompatible_evidence', 'hypothesis_ids': ['h0', 'h1'],
                                  'statement': None}]
        profile, _ = self.run_builder('P8', response, [self.target, later])
        self.assertEqual(profile.status, 'complete')
        self.assertEqual(len(profile.content['hypotheses']), 2)
        self.assertEqual(profile.content['relations'][0]['kind'], 'incompatible_evidence')
        self.assertEqual([h['weight'] for h in profile.content['hypotheses']], [None, None])
        self.assertEqual([h['statement']['date'] for h in profile.content['hypotheses']], [None, None])
        self.assertEqual(profile.weights_status, 'unavailable')

    def test_stated_change_requires_its_own_exact_evidence(self):
        later = document('t2', 'target', 'I changed from small tests to large tests in 2026.')
        response = self.hypotheses([self.target, later])
        relation = {'kind': 'stated_change', 'hypothesis_ids': ['h0', 'h1'], 'statement': None}
        response['relations'] = [relation]
        bad, _ = self.run_builder('P8', response, [self.target, later])
        self.assertEqual(bad.status, 'invalid')
        relation['statement'] = statement(later)
        good, _ = self.run_builder('P8', response, [self.target, later])
        self.assertEqual(good.status, 'complete')
        self.assertEqual(good.content['relations'][0]['statement']['sources'][0]['quote'], later['content'])

    def test_unsupported_date_is_not_invented_from_publication_time(self):
        self.target['published_at'] = '2026-11-14'
        response = self.hypotheses()
        response['hypotheses'][0]['statement']['date'] = '2026-11-14'
        profile, _ = self.run_builder('P8', response, [self.target])
        self.assertEqual(profile.status, 'invalid')
        self.assertEqual(profile.error_code, 'date_not_in_evidence')

    def test_p8_rejects_invented_weights_dangling_relations_and_peer_hypotheses(self):
        for change in ('weight', 'dangling', 'peer'):
            response = self.hypotheses()
            if change == 'weight':
                response['hypotheses'][0]['weight'] = 0.8
            elif change == 'dangling':
                response['relations'] = [{'kind': 'extraction_uncertainty', 'hypothesis_ids': ['h0', 'absent'],
                                          'statement': None}]
            else:
                response['hypotheses'][0]['statement'] = statement(self.peer)
            with self.subTest(change=change):
                profile, _ = self.run_builder('P8', response)
                self.assertEqual(profile.status, 'invalid')

    def test_all_caps_count_full_utf8_payload_without_truncating_conflicts(self):
        later = document('t2', 'target', '大きい試験が好きです。' * 30)
        response = self.hypotheses([self.target, later])
        response['relations'] = [{'kind': 'incompatible_evidence', 'hypothesis_ids': ['h1', 'h0'],
                                  'statement': None}]
        for cap in (512, 2048, 8192):
            with self.subTest(cap=cap):
                profile, _ = self.run_builder('P8', response, [self.target, later], personalization_cap=cap)
                byte_count = len(render_content(profile.content).encode('utf-8'))
                self.assertEqual(profile.token_count, byte_count)
                self.assertEqual(profile.status, 'invalid' if byte_count > cap else 'complete')
                self.assertEqual(len(profile.content['hypotheses']), 2)
                self.assertEqual(len(profile.content['relations']), 1)

    def test_small_hypothesis_can_fit_512_byte_cap(self):
        profile, _ = self.run_builder('P8', self.hypotheses(), [self.target], personalization_cap=512)
        self.assertEqual(profile.status, 'complete')
        self.assertLessEqual(profile.token_count, 512)

    def test_deterministic_hypothesis_order_does_not_use_recency_weights(self):
        other = document('t2', 'target', 'Prefer large tests.')
        response = self.hypotheses([self.target, other])
        first, _ = self.run_builder('P8', response, [self.target, other])
        response['hypotheses'].reverse()
        second, _ = self.run_builder('P8', response, [other, self.target])
        self.assertEqual(first.content, second.content)

    def test_empty_invalid_and_failed_outputs_remain_distinct(self):
        empty, _ = self.run_builder('P8', {'hypotheses': [], 'relations': []}, [self.target])
        self.assertEqual(empty.status, 'empty')
        for raw in ('not json', '{"hypotheses":[],"hypotheses":[],"relations":[]}',
                    '{"hypotheses":NaN,"relations":[]}', {'status': 'complete'}):
            with self.subTest(raw=raw):
                profile, _ = self.run_builder('P8', raw, [self.target])
                self.assertEqual(profile.status, 'invalid')
        backend = Extractor({}, failure=True)
        failed = build_profile([self.target], self.config('P8', [self.target]), backend)
        self.assertEqual(failed.status, 'unavailable')
        self.assertEqual(failed.fit_usage['attempted_calls'], 1)
        self.assertEqual(len(backend.calls), 1)

    def test_prompt_only_contains_permitted_text_and_no_target_context(self):
        self.target['content'] += ' Unattributed appendix.'
        self.target['content_sha256'] = sha256_text(self.target['content'])
        response = self.hypotheses([document('t', 'target', 'Prefer small tests.')])
        profile, backend = self.run_builder('P8', response, [self.target])
        self.assertEqual(profile.status, 'complete')
        self.assertNotIn('Unattributed appendix', backend.calls[0][0])
        self.assertIn('Prefer small tests.', backend.calls[0][0])
        blocked, backend = self.run_builder('P8', response, [self.target], context='held-out question')
        self.assertEqual(blocked.status, 'invalid')
        self.assertEqual(backend.calls, [])


if __name__ == '__main__':
    unittest.main()
