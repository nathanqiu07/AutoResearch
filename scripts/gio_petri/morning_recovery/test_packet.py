"""Offline handoff and isolation tests; all profile data here are fixtures."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch


GIO = Path(__file__).resolve().parents[1]
ROOT = GIO.parents[1]
if str(GIO) not in sys.path:
    sys.path.insert(0, str(GIO))
SOURCE = ROOT / 'results/gio-baseline-review-02/packet'
START = '2026-11-15T16:00:00+00:00'
LEASE = {'id': 'offline-morning-fixture',
         'expires_at': '2026-11-15T19:45:00Z',
         'provider_allocations_usd': {'openai': 15, 'openrouter': 5}}
AUTHORING = 'OFFLINE FIXTURE: author substantive reviewable code; preserve tools.'
SENTINEL = 'PROFILE_ONLY_9ad79 {literal} → café.\nUnknown stays unknown.'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def receipt(condition='rich', method='P8', text=SENTINEL):
    generic = method in ('generic', 'no_history')
    return {
        'schema_version': 'gio-auditor-context-v1',
        'condition_id': condition, 'method_id': method,
        'researcher_id': None if generic else 'fixture-person',
        'source_bundle_digest': None if generic else 'a' * 64,
        'model_facing_text': text,
        'provenance': {'fixture': True, 'unknown': None},
        'settings': {'extraction_only': True, 'max_tokens': 123},
        'implementation_commit': 'c' * 40,
        'checks_performed': ['Fixture envelope prepared offline'],
        'known_limits': ['Fabricated test input; no preference evidence'],
    }


class MorningPacketTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module('morning_recovery.packet')
        except ModuleNotFoundError:
            self.fail('The morning packet API has not been implemented')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.authoring = self.root / 'authoring.txt'
        self.authoring.write_text(AUTHORING)

    def write_receipt(self, body, name='context.json'):
        path = self.root / name
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + '\n')
        return path

    def prepare(self, bodies=None, out_name='packet'):
        if bodies is None:
            bodies = [receipt('baseline', 'no_history', 'No personal guidance.'),
                      receipt('generic', 'generic', 'Use sound general research judgment.'),
                      receipt()]
        paths = [self.write_receipt(b, 'input-' + str(i) + '.json')
                 for i, b in enumerate(bodies)]
        out = self.root / out_name
        settings = self.module.prepare_packet(paths, out, START, copy.deepcopy(LEASE),
                                               authoring_contract=self.authoring)
        return out, settings

    def test_load_preserves_text_identity_and_explicit_unknowns(self):
        body = receipt()
        path = self.write_receipt(body)
        raw = path.read_bytes()
        result = self.module.load_context(path, expected_sha256=digest(raw))
        for key, value in body.items():
            self.assertEqual(result[key], value, key)
        self.assertNotIn('history', result)
        self.assertNotIn('weights', result)
        self.assertNotIn('confidence', result)
        self.assertEqual(path.read_bytes(), raw)

    def test_expected_receipt_hash_rejects_even_whitespace_change(self):
        path = self.write_receipt(receipt())
        pinned = digest(path.read_bytes())
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.module.load_context(path, expected_sha256=pinned)

    def test_missing_or_mistyped_required_receipt_fields_are_rejected(self):
        for key in receipt():
            with self.subTest(missing=key):
                body = receipt()
                body.pop(key)
                with self.assertRaises(ValueError):
                    self.module.load_context(self.write_receipt(body))
        changes = {'method_id': '', 'researcher_id': 7, 'source_bundle_digest': 'bad',
                   'model_facing_text': '  ', 'provenance': [], 'settings': [],
                   'implementation_commit': '', 'checks_performed': 'not a list',
                   'known_limits': [False]}
        for key, value in changes.items():
            with self.subTest(mistyped=key):
                body = receipt()
                body[key] = value
                with self.assertRaises(ValueError):
                    self.module.load_context(self.write_receipt(body))

    def test_condition_ids_cannot_escape_paths_or_collide_silently(self):
        for identifier in ('../rich', '/tmp/rich', 'Rich', 'a-b', 'a' * 41, ''):
            with self.subTest(identifier=identifier):
                body = receipt(identifier)
                with self.assertRaises(ValueError):
                    self.module.load_context(self.write_receipt(body))
        with self.assertRaises(ValueError):
            self.prepare([receipt(), receipt()], 'duplicate-packet')
        self.assertFalse((self.root / 'duplicate-packet').exists())

    def test_null_source_identity_is_limited_to_nonpersonal_controls(self):
        for method in ('generic', 'no_history'):
            body = receipt('control', method)
            self.module.load_context(self.write_receipt(body))
        for field in ('researcher_id', 'source_bundle_digest'):
            body = receipt()
            body[field] = None
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.module.load_context(self.write_receipt(body))

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        path = self.root / 'ambiguous.json'
        for raw in ('{"condition_id":"a","condition_id":"b"}',
                    '{"settings":{"value":NaN}}', '{"settings":{"value":Infinity}}'):
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.module.load_context(path)

    def test_empty_conditions_are_rejected_without_output(self):
        with self.assertRaises(ValueError):
            self.prepare([], 'empty-packet')
        self.assertFalse((self.root / 'empty-packet').exists())

    def test_packet_preserves_seed_runtime_and_all_source_files(self):
        before = {p.name: p.read_bytes() for p in SOURCE.iterdir() if p.is_file()}
        original = json.loads(before['settings.json'])
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            out, settings = self.prepare()
            verified = self.module.verify_packet(out)
        self.assertEqual(verified, settings)
        self.assertEqual(settings['arms'], ['baseline', 'generic', 'rich'])
        self.assertEqual(settings['max_auditor_turns'], 30)
        self.assertEqual(settings['start_time'], START)
        for key in ('models', 'routing', 'generation', 'max_auditor_turns', 'cache',
                    'transport_retries', 'petri_judge_max_attempts', 'tools', 'epochs'):
            self.assertEqual(settings[key], original[key], key)
        for name in ('seed.json', 'seed.txt', 'review-instructions.txt'):
            self.assertEqual((out / name).read_bytes(), before[name], name)
        after = {p.name: p.read_bytes() for p in SOURCE.iterdir() if p.is_file()}
        self.assertEqual(after, before)

    def test_profile_is_only_an_auditor_suffix_with_lossless_template_escaping(self):
        out, settings = self.prepare()
        common = (out / 'common.template.txt').read_text()
        self.assertNotIn(SENTINEL, common)
        for arm in settings['arms']:
            template = (out / (arm + '.template.txt')).read_text()
            self.assertTrue(template.startswith(common))
            rendered = template.format(target_model='fixture-target',
                seed_instructions=(out / 'seed.txt').read_text(), max_turns=30,
                resources_prompt='fixture resources', today_date='2026-11-15')
            self.assertEqual(rendered.count(SENTINEL), 1 if arm == 'rich' else 0)
            context = json.loads((out / (arm + '.context.json')).read_text())
            self.assertEqual((out / (arm + '.context.txt')).read_text(), context['model_facing_text'])
        for name in ('seed.json', 'seed.txt', 'settings.json', 'review-instructions.txt'):
            self.assertNotIn(SENTINEL, (out / name).read_text(), name)

    def test_receipt_settings_cannot_override_runtime_roles_or_generation(self):
        body = receipt()
        body['settings'].update(models={'target': 'fixture-wrong-model'}, max_auditor_turns=1,
                                recipient='target', seed='fixture-wrong-seed')
        out, settings = self.prepare([body])
        original = json.loads((SOURCE / 'settings.json').read_text())
        for key in ('models', 'generation', 'max_auditor_turns'):
            self.assertEqual(settings[key], original[key])
        self.assertEqual((out / 'seed.txt').read_bytes(), (SOURCE / 'seed.txt').read_bytes())

    def test_changed_packet_context_or_template_is_rejected(self):
        for name in ('rich.context.txt', 'rich.context.json', 'rich.template.txt'):
            with self.subTest(name=name):
                out, _ = self.prepare(out_name='tamper-' + name)
                path = out / name
                path.write_bytes(path.read_bytes() + b' ')
                with self.assertRaises(ValueError):
                    self.module.verify_packet(out)

    def test_saved_p8_fallback_preserves_source_and_uses_existing_exporter(self):
        import neutral_profile_adapter
        from test_neutral_profile_adapter import fixture, seal
        body = fixture()
        body['documents_hash'] = 'd' * 64
        seal(body)
        source = self.write_receipt(body, 'p8-source.json')
        raw = source.read_bytes()
        export = self.root / 'p8-export'
        neutral_profile_adapter.export_saved_p8_context(source, export,
            expected_sha256=digest(raw), expected_profile_id=body['profile_id'],
            expected_researcher_id=body['researcher_id'], expected_replicate_id=0)
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            context = self.module.context_from_p8(export, condition_id='rich')
        self.assertEqual(context['schema_version'], 'gio-auditor-context-v1')
        self.assertEqual(context['condition_id'], 'rich')
        self.assertEqual(context['method_id'], 'P8')
        self.assertEqual(context['researcher_id'], body['researcher_id'])
        self.assertEqual(context['source_bundle_digest'], body['documents_hash'])
        self.assertEqual(context['model_facing_text'], (export / 'auditor-context.txt').read_text())
        self.assertEqual((export / 'profile-original.json').read_bytes(), raw)
        self.assertEqual(source.read_bytes(), raw)
        self.assertNotIn('history', context)
        self.assertNotIn('confidence', context)
        self.assertNotIn('weights', context)
        path = self.write_receipt(context, 'fallback-context.json')
        self.module.load_context(path, expected_sha256=digest(path.read_bytes()))

    def test_native_task_routes_profile_to_auditor_without_changing_target_or_judge(self):
        from run_matched import build_task
        seed = {'seed_id': 'fixture-seed', 'text': 'FIXTURE_UNCHANGED_SEED'}
        tools = [object()]
        world = object()
        with patch('inspect_ai.Task', side_effect=lambda **kw: kw), \
                patch('petri.solvers.auditor_agent.auditor_agent', side_effect=lambda **kw: kw), \
                patch('petri.scorers.judge.alignment_judge', return_value='fixture-judge') as judge, \
                patch('petri.cleanup.save_transcripts.save_transcripts', return_value='fixture-cleanup'), \
                patch('shutdown_setup.build_shutdown_tools', return_value=(tools, world)) as tool_factory:
            baseline, first_world = build_task(seed, 'COMMON', 30, START, self.root)
            rich, second_world = build_task(seed, 'COMMON\n' + SENTINEL, 30, START, self.root)
        self.assertIs(first_world, world)
        self.assertIs(second_world, world)
        self.assertEqual(baseline['dataset'], rich['dataset'])
        self.assertEqual(rich['dataset'][0].input, seed['text'])
        self.assertNotIn(SENTINEL, rich['dataset'][0].input)
        self.assertIs(rich['solver']['auditor_tools'], tools)
        self.assertEqual(rich['solver']['auditor_system_message'], 'COMMON\n' + SENTINEL)
        self.assertEqual(baseline['solver']['max_turns'], rich['solver']['max_turns'])
        self.assertEqual(judge.call_args_list[0], judge.call_args_list[1])
        self.assertEqual(tool_factory.call_args_list[0], tool_factory.call_args_list[1])
        for key in ('scorer', 'cleanup', 'metadata'):
            self.assertEqual(baseline[key], rich[key])


if __name__ == '__main__':
    unittest.main()
