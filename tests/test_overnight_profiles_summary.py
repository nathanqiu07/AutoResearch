import copy
import importlib.util
import json
import unittest

from autoresearch.taste.overnight import contracts


TEXT = 'I prefer a small controlled test before a large trial.'
DOCS = [{'document_id': 'synthetic-fit', 'researcher_id': 'synthetic', 'content': TEXT,
         'content_sha256': contracts.sha256_text(TEXT), 'published_at': None}]


def statement(status='explicit'):
    return {'text': 'Start with a small controlled test.', 'kind': 'preference',
            'evidence_status': status, 'conditions': None, 'date': None,
            'sources': [{'document_id': 'synthetic-fit', 'start': 0, 'end': len(TEXT), 'quote': TEXT}]}


class Extractor:
    label = 'offline-summary-fixture'
    name = 'offline-summary-fixture'
    model = 'fixture-v1'

    def __init__(self, response):
        self.response, self.calls = response, []

    def complete(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response if isinstance(self.response, str) else json.dumps(self.response)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('autoresearch.taste.overnight.profiles_summary'),
                             'P1-P3 builders are not implemented')
        from autoresearch.taste.overnight import profiles_summary
        self.m = profiles_summary
        self.config = {'method_id': 'P1', 'researcher_id': 'synthetic', 'evidence_policy': 'explicit-only',
                       'personalization_cap': 8192, 'replicate_id': 0, 'code_sha': 'b' * 40,
                       'extractor_settings': {'temperature': 0.0, 'max_tokens': 2048},
                       'allowed_sources': contracts.source_manifest(DOCS),
                       'allowed_source_manifest_hash': contracts.digest(contracts.source_manifest(DOCS))}

    def build(self, response=None, method='P1', **changes):
        response = {'summary': [statement()]} if response is None else response
        backend = Extractor(response)
        result = getattr(self.m, 'build_' + method.lower())(copy.deepcopy(DOCS),
                        dict(self.config, method_id=method, **changes), backend)
        return result, backend

    def test_unknown_extractor_settings_are_rejected_before_call(self):
        for method in ('P1', 'P2', 'P3'):
            for extra in ({'top_p':0.1}, {'top_p':0.9}, {'reasoning':'high'}, {'seed':1}):
                with self.subTest(method=method,extra=extra):
                    out,backend=self.build(method=method,extractor_settings=dict(self.config['extractor_settings'],**extra))
                    self.assertEqual(out['status'],'invalid')
                    self.assertEqual(backend.calls,[])
                    self.assertEqual(out['fit_usage']['attempted_calls'],0)

    def test_omitted_supported_settings_have_pinned_effective_defaults(self):
        for supplied,expected in [({},{'temperature':0.0,'max_tokens':2048}),
                                  ({'temperature':0.5},{'temperature':0.5,'max_tokens':2048}),
                                  ({'max_tokens':100},{'temperature':0.0,'max_tokens':100})]:
            with self.subTest(supplied=supplied):
                out,backend=self.build(extractor_settings=supplied)
                self.assertEqual(out['status'],'complete')
                self.assertEqual(out['fit_usage']['effective_extractor_settings'],expected)
                self.assertEqual({k:backend.calls[0][1][k] for k in expected},expected)
                self.assertEqual(self.m.prompt_spec('P1')['extractor_settings_defaults'],
                                 {'temperature':0.0,'max_tokens':2048})

    def test_plain_and_task_guided_summary_are_distinct_fixed_prompts(self):
        p1, first = self.build()
        p2, second = self.build(method='P2')
        self.assertEqual(p1['status'], 'complete')
        self.assertEqual(p2['status'], 'complete')
        self.assertNotEqual(first.calls[0][0], second.calls[0][0])
        self.assertIn('without imposing a research-taste taxonomy', first.calls[0][0])
        self.assertIn('choose research questions', second.calls[0][0])
        self.assertEqual(p1['content'], p2['content'])

    def test_explicit_only_rejects_inference_without_silent_deletion(self):
        response = {'summary': [statement('inferred')]}
        result, _ = self.build(response)
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(result['content'], response)
        self.assertEqual(result['error_code'], 'inference_not_allowed')
        accepted, _ = self.build(response, evidence_policy='marked-inference')
        self.assertEqual(accepted['status'], 'complete')
        self.assertEqual(accepted['content']['summary'][0]['evidence_status'], 'inferred')

    def test_exact_source_spans_and_quotes_are_required(self):
        for field, value in [('document_id', 'unapproved'), ('quote', 'invented'),
                             ('start', True), ('end', len(TEXT) + 1), ('start', -1)]:
            s = statement(); s['sources'][0][field] = value
            with self.subTest(field=field, value=value):
                result, _ = self.build({'summary': [s]})
                self.assertEqual(result['status'], 'invalid')

    def test_claims_without_provenance_are_not_accepted(self):
        s = statement(); s['sources'] = []
        result, _ = self.build({'summary': [s]})
        self.assertEqual(result['status'], 'invalid')

    def test_permitted_span_boundary_is_enforced_when_supplied(self):
        docs = copy.deepcopy(DOCS)
        docs[0]['permitted_spans'] = [{'start': 2, 'end': len(TEXT)}]
        out = self.m.build_p1(docs, self.config, Extractor({'summary': [statement()]}))
        self.assertEqual(out['status'], 'invalid')

    def test_unknown_or_extra_fields_are_rejected_not_dropped(self):
        for response in [{'summary': [statement()], 'weights': {'a': 1}},
                         {'summary': [dict(statement(), confidence=1.0)]}]:
            with self.subTest(response=response):
                result, _ = self.build(response)
                self.assertEqual(result['status'], 'invalid')
                self.assertEqual(result['content'], response)

    def test_schema_requires_all_questions_and_preserves_unknowns(self):
        answers = {q: {'status': 'unknown', 'statements': []} for q in self.m.QUESTIONS}
        key = next(iter(answers)); answers[key] = {'status': 'supported', 'statements': [statement()]}
        response = {'answers': answers}
        result, _ = self.build(response, method='P3')
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(result['content']['answers']), 10)
        self.assertEqual(sum(x['status'] == 'unknown' for x in answers.values()), 9)
        del answers[key]
        result, _ = self.build(response, method='P3')
        self.assertEqual(result['status'], 'invalid')

    def test_all_unknown_schema_and_empty_summary_are_explicitly_empty(self):
        result, _ = self.build({'summary': []})
        self.assertEqual(result['status'], 'empty')
        result, _ = self.build({'answers': {q: {'status': 'unknown', 'statements': []}
                                          for q in self.m.QUESTIONS}}, method='P3')
        self.assertEqual(result['status'], 'empty')

    def test_unsupported_policy_and_decision_conditioning_fail_before_call(self):
        for change in [{'evidence_policy': 'anything'}, {'context': 'held-out question'},
                       {'options': ['a', 'b']}, {'chosen': 'a'}]:
            with self.subTest(change=change):
                result, backend = self.build(**change)
                self.assertEqual(result['status'], 'invalid')
                self.assertEqual(backend.calls, [])

    def test_document_extra_fields_never_reach_extraction_request(self):
        docs = copy.deepcopy(DOCS); docs[0]['chosen'] = 'ANSWER_SENTINEL'
        backend = Extractor({'summary': [statement()]})
        self.m.build_p1(docs, self.config, backend)
        self.assertNotIn('ANSWER_SENTINEL', backend.calls[0][0])

    def test_bad_input_hash_rejected_before_extractor(self):
        docs = copy.deepcopy(DOCS); docs[0]['content'] += 'altered'
        backend = Extractor({'summary': [statement()]})
        result = self.m.build_p1(docs, self.config, backend)
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(backend.calls, [])

    def test_backend_failure_is_unavailable_and_not_retried(self):
        result, backend = self.build(RuntimeError('fixture failure'))
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(len(backend.calls), 1)

    def test_malformed_json_is_invalid_and_trace_hashes_are_present(self):
        result, _ = self.build('not json')
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(len(result['fit_usage']['request_sha256']), 64)
        self.assertEqual(result['fit_usage']['response_sha256'], contracts.sha256_text('not json'))

    def test_malformed_nested_json_is_an_explicit_invalid_result(self):
        for key, value in [('kind', {}), ('evidence_status', []), ('sources', 'not a list')]:
            bad = statement(); bad[key] = value
            with self.subTest(key=key):
                result, _ = self.build({'summary': [bad]})
                self.assertEqual(result['status'], 'invalid')

    def test_duplicate_json_keys_are_rejected(self):
        result, _ = self.build('{"summary":[],"summary":[]}')
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(result['error_code'], 'malformed_extraction_json')

    def test_only_permitted_source_segments_reach_prompt(self):
        docs = copy.deepcopy(DOCS)
        docs[0]['content'] = TEXT + ' WITHHELD_SENTINEL'
        docs[0]['content_sha256'] = contracts.sha256_text(docs[0]['content'])
        docs[0]['permitted_spans'] = [{'start': 0, 'end': len(TEXT)}]
        docs[0]['version_evidence'] = {'hidden_note': 'METADATA_SENTINEL'}
        config = dict(self.config, allowed_sources=contracts.source_manifest(docs),
                      allowed_source_manifest_hash=contracts.digest(contracts.source_manifest(docs)))
        backend = Extractor({'summary': [statement()]})
        result = self.m.build_p1(docs, config, backend)
        self.assertEqual(result['status'], 'complete')
        self.assertNotIn('WITHHELD_SENTINEL', backend.calls[0][0])
        self.assertNotIn('METADATA_SENTINEL', backend.calls[0][0])

    def test_registration_shared_contract_cap_and_deterministic_content(self):
        entries = self.m.registration_metadata()
        self.assertEqual({e['method_id'] for e in entries}, {'P1', 'P2', 'P3'})
        self.m.register_summary_builders()
        backend = Extractor({'summary': [statement()]})
        a = contracts.build_profile(DOCS, self.config, backend)
        b = contracts.build_profile(DOCS, dict(self.config, replicate_id=1), Extractor({'summary': [statement()]}))
        self.assertEqual(a.content_sha256, b.content_sha256)
        self.assertNotEqual(a.profile_id, b.profile_id)
        small = contracts.build_profile(DOCS, dict(self.config, personalization_cap=10), Extractor({'summary': [statement()]}))
        self.assertEqual(small.status, 'invalid')
        self.assertEqual(small.error_code, 'personalization_cap_exceeded')
        self.assertEqual(small.content, a.content)


if __name__ == '__main__':
    unittest.main()
