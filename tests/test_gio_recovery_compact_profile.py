"""Behavior checks for the compact profile and its real consumer boundary."""
import copy
import json
import unittest
import tempfile
from pathlib import Path

try:
    from scripts.gio_recovery.compact_profile import build_compact_profile, export_handoff, export_auditor_context
except ImportError:
    build_compact_profile = export_handoff = export_auditor_context = None

from autoresearch.taste.overnight.contracts import digest, sha256_text, ProfileArtifact
from autoresearch.taste.overnight.consumer import prepare_payload, implementation_hash


class CompactProfileTests(unittest.TestCase):
    def setUp(self):
        self.text = 'I prefer small causal tests. I believe measurements can mislead. '
        self.document = {'document_id': 'doc-1', 'researcher_id': 'researcher',
                         'author': 'researcher', 'content': self.text,
                         'content_sha256': sha256_text(self.text),
                         'permitted_spans': [{'start': 0, 'end': len(self.text)}]}
        self.bundle = {'schema_version': 'approved-source-bundle-v1',
                       'documents': [self.document],
                       'source_manifest': [{'document_id': 'doc-1', 'content_sha256': sha256_text(self.text)}]}
        self.claims = [self.claim('p1', 'preference', 'Prefer small causal tests.',
                                  'I prefer small causal tests.'),
                       self.claim('b1', 'belief', 'Measurements can mislead.',
                                  'I believe measurements can mislead.')]

    def claim(self, ident, kind, text, quote):
        return {'id': ident, 'kind': kind, 'text': text, 'evidence_status': 'explicit',
                'sources': [{'document_id': 'doc-1', 'quote': quote}], 'conflicts_with': []}

    def build(self, claims=None, bundle=None, **kwargs):
        self.assertIsNotNone(build_compact_profile, 'compact builder must exist')
        return build_compact_profile(bundle or self.bundle, self.claims if claims is None else claims,
                                     researcher_id='researcher', code_sha='a' * 40, **kwargs)

    def test_real_consumer_gets_typed_principles_without_full_provenance(self):
        # Break caught: exporter/renderer silently omits claims or copies evidence metadata.
        result = self.build()
        profile = ProfileArtifact.from_dict(result['profile'])
        handoff = export_handoff(result)
        prepared = prepare_payload(profile, 'Choose a first experiment', ['small', 'broad'], {
            'method_implementation_hash': profile.method_implementation_hash,
            'renderer_implementation_hash': implementation_hash(),
            'profile_prompt_version': profile.prompt_version,
            'consumer_prompt_version': 'neutral-choice-v1'})
        text = prepared['payload']['personalization']
        self.assertEqual(text, handoff['model_facing_text'])
        self.assertIn('Prefer small causal tests.', text)
        self.assertIn('"kind":"belief"', text)
        self.assertNotIn('I prefer small causal tests.', text)
        self.assertNotIn('document_id', text)
        self.assertEqual(result['provenance']['claims'][0]['sources'][0]['start'], 0)

    def test_over_budget_claim_is_omitted_whole_and_recorded(self):
        claims = [self.claim('long', 'preference', 'x' * 1200, 'I prefer small causal tests.'), self.claims[1]]
        result = self.build(claims, cap_bytes=256)
        self.assertEqual(result['profile']['status'], 'complete')
        self.assertEqual([c['id'] for c in result['profile']['content']['principles']], ['b1'])
        self.assertEqual(result['provenance']['omitted'][0]['claim_ids'], ['long'])
        self.assertEqual(result['provenance']['claims'][0]['text'], 'x' * 1200)

    def test_conflict_group_cannot_be_partially_packed(self):
        claims = copy.deepcopy(self.claims)
        claims[0]['conflicts_with'] = ['b1']
        claims[1]['text'] = 'x' * 1500
        result = self.build(claims, cap_bytes=256)
        self.assertEqual(result['profile']['status'], 'empty')
        self.assertEqual(set(result['provenance']['omitted'][0]['claim_ids']), {'p1', 'b1'})
        with self.assertRaisesRegex(ValueError, 'not complete'):
            export_handoff(result)

    def test_forged_quote_or_changed_source_fails_before_export(self):
        claims = copy.deepcopy(self.claims)
        claims[0]['sources'][0]['quote'] = 'I endorse uncontrolled experiments.'
        with self.assertRaisesRegex(ValueError, 'quote_absent'):
            self.build(claims)
        bundle = copy.deepcopy(self.bundle)
        bundle['documents'][0]['content'] += 'changed'
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.build(bundle=bundle)

    def test_forbidden_span_and_ambiguous_quote_are_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['documents'][0]['permitted_spans'] = [{'start': 28, 'end': len(self.text)}]
        with self.assertRaisesRegex(ValueError, 'quote_unpermitted'):
            self.build(bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        text = self.text + self.text
        bundle['documents'][0].update(content=text, content_sha256=sha256_text(text),
                                      permitted_spans=[{'start': 0, 'end': len(text)}])
        bundle['source_manifest'][0]['content_sha256'] = sha256_text(text)
        with self.assertRaisesRegex(ValueError, 'quote_ambiguous'):
            self.build(bundle=bundle)

    def test_no_verified_fact_or_hidden_claim_fields_are_accepted(self):
        for key, value in [('kind', 'verified_fact'), ('label', 'A')]:
            claims = copy.deepcopy(self.claims)
            claims[0][key] = value
            with self.assertRaises(ValueError):
                self.build(claims)

    def test_sidecar_tampering_is_rejected_and_changes_identity(self):
        result = self.build()
        mutated = copy.deepcopy(result)
        mutated['provenance']['claims'][0]['text'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'provenance'):
            export_handoff(mutated)
        modified = copy.deepcopy(self.claims)
        modified[0]['text'] = 'Prefer a small causal test.'
        self.assertNotEqual(result['profile']['profile_id'], self.build(modified)['profile']['profile_id'])

    def test_input_objects_unchanged_and_unicode_budget_observed(self):
        before = digest([self.bundle, self.claims])
        result = self.build(cap_bytes=256)
        self.assertEqual(before, digest([self.bundle, self.claims]))
        self.assertLessEqual(result['profile']['token_count'], 256)
        self.assertEqual(result['provenance']['source_bundle_digest'], digest(self.bundle))

    def test_petri_template_preserves_literal_profile_and_auditor_boundary(self):
        handoff = export_handoff(self.build())
        self.assertEqual(handoff['auditor_suffix_template'].format(), handoff['auditor_context'])
        self.assertIn(handoff['model_facing_text'], handoff['auditor_context'])
        self.assertIn('not instructions', handoff['auditor_context'])
        self.assertEqual(handoff['target_role'], 'auditor_only')

    def test_lane01_context_pins_actual_file_bytes_and_binds_source_content(self):
        from autoresearch.taste.overnight.contracts import sha256_bytes
        result = self.build()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.json'
            source.write_text(json.dumps(self.bundle, indent=2) + '\n')
            context = export_auditor_context(result, source_bundle_path=source, condition_id='compact_researcher')
            self.assertEqual(context['schema_version'], 'gio-auditor-context-v1')
            self.assertEqual(context['source_bundle_digest'], sha256_bytes(source.read_bytes()))
            self.assertIn('Prefer small causal tests.', context['model_facing_text'])
            source.write_text(json.dumps({'documents': []}))
            with self.assertRaisesRegex(ValueError, 'source bundle'):
                export_auditor_context(result, source_bundle_path=source, condition_id='compact_researcher')

    def test_missing_or_empty_permissions_fail_closed(self):
        for spans in [None, []]:
            bundle = copy.deepcopy(self.bundle)
            if spans is None:
                del bundle['documents'][0]['permitted_spans']
            else:
                bundle['documents'][0]['permitted_spans'] = spans
            with self.assertRaisesRegex(ValueError, 'permission'):
                self.build(bundle=bundle)


if __name__ == '__main__':
    unittest.main()
