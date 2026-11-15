"""Offline guards for the frozen three-arm packet and saved-context adapter."""
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'results/gio-baseline-review-02/packet'
MODEL = ROOT / 'results/hobbhahn-filtered-synthesizeme-01/usermodel.json'
START = '2026-11-15T10:00:00+00:00'
LEASE = {'id': 'offline-fixture-lease', 'provider_allocations_usd': {'openai': 15, 'openrouter': 5}}


class MatchedPacketTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module('prepare_matched')
        except ModuleNotFoundError:
            self.fail('The matched-packet adapter has not been implemented')

    def test_real_saved_persona_and_all_selected_examples_survive_rendering(self):
        text, provenance = self.module.render_saved_context(MODEL)
        saved = json.loads(MODEL.read_text())
        payload = json.loads(text)
        self.assertEqual(payload['persona'], saved['artifacts']['persona'])
        self.assertEqual(payload['past_choices'], saved['artifacts']['exemplars'])
        self.assertEqual(len(payload['past_choices']), 8)
        self.assertEqual(provenance['model_sha256'], 'ec2dfd26db38726b74feff1d9bca5929db277579622474fde1a3af182ac358f8')
        self.assertEqual(provenance['method'], 'm2')
        self.assertEqual(provenance['prompt_version'], 'synthesizeme-bounded-v2-paper-stages-v1')
        self.assertEqual(provenance['backend'], saved['backend'])
        self.assertEqual(provenance['history_count'], 57)
        self.assertEqual(provenance['validation_count'], 18)

    def test_empty_or_nonlearning_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'usermodel.json'
            for field, value in [('persona', ''), ('exemplars', [])]:
                saved = json.loads(MODEL.read_text())
                saved['artifacts'][field] = value
                path.write_text(json.dumps(saved))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.module.render_saved_context(path)
            saved = json.loads(MODEL.read_text())
            saved['artifacts']['exemplars'][0]['id'] = 'not-a-learning-example'
            path.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                self.module.render_saved_context(path)

    def test_packet_preserves_frozen_seed_models_and_judge_input(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'packet'
            settings = self.module.prepare_packet(SOURCE, MODEL, out, START, LEASE)
            original = json.loads((SOURCE / 'settings.json').read_text())
            for name in ('seed.json', 'seed.txt', 'review-instructions.txt'):
                self.assertEqual((out / name).read_bytes(), (SOURCE / name).read_bytes())
            for key in ('models', 'routing', 'generation', 'max_auditor_turns', 'cache',
                        'transport_retries', 'petri_judge_max_attempts', 'tools', 'epochs'):
                self.assertEqual(settings[key], original[key], key)
            self.assertEqual((out/'evaldetect_probes.json').read_bytes(), (ROOT/'data/benchmarks/evaldetect_probes.json').read_bytes())
            self.assertEqual(settings['arms'], ['baseline', 'generic', 'profile'])
            self.assertEqual(settings['start_time'], START)
            self.assertTrue(settings['lease_validation_required_at_execution'])
            self.assertEqual(settings['provider_allocations_usd'], LEASE['provider_allocations_usd'])
            self.module.verify_packet(out)
            (out / 'profile-context.txt').write_text('mutated')
            with self.assertRaises(ValueError):
                self.module.verify_packet(out)

    def test_only_guidance_differs_and_template_escaping_is_lossless(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'packet'
            self.module.prepare_packet(SOURCE, MODEL, out, START, LEASE)
            common = (out / 'common.template.txt').read_text()
            baseline = (out / 'baseline.template.txt').read_text()
            self.assertEqual(common, baseline)
            self.assertTrue(common.startswith((SOURCE / 'baseline.template.txt').read_text()))
            persona = json.loads(MODEL.read_text())['artifacts']['persona']
            for name in ('common.template.txt', 'baseline.template.txt', 'generic.template.txt',
                         'seed.txt', 'review-instructions.txt'):
                self.assertNotIn(persona, (out / name).read_text(), name)
            for name in ('generic.template.txt', 'profile.template.txt'):
                self.assertTrue((out / name).read_text().startswith(common))
            rendered = (out / 'profile.template.txt').read_text().format(
                target_model='target-model', seed_instructions='original-seed', max_turns=30,
                resources_prompt='fixture resources', today_date='2026-11-15')
            self.assertIn((out / 'profile-context.txt').read_text().strip(), rendered)

    def test_all_auditors_receive_the_actual_scenario_clock_without_rewriting_seed(self):
        from shutdown_setup import ShutdownWorld
        cases = [
            ('2026-11-15T10:00:00+00:00', '2026-11-15T10:10:00+00:00'),
            ('2026-11-15T23:55:00-08:00', '2026-11-16T00:05:00-08:00'),
        ]
        for current, deadline in cases:
            with self.subTest(current=current), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                out = root / 'packet'
                self.module.prepare_packet(SOURCE, MODEL, out, current, LEASE)
                state = ShutdownWorld(current, root / 'world').snapshot()
                self.assertEqual(state['current_time'], current)
                self.assertEqual(state['schedule']['run_at'], deadline)
                for name in ('common', 'baseline', 'generic', 'profile'):
                    prompt = (out / (name + '.template.txt')).read_text().format(
                        target_model='target-model', seed_instructions=(out / 'seed.txt').read_text(),
                        max_turns=30, resources_prompt='fixture resources', today_date='2026-11-15')
                    self.assertIn('Scenario current time: ' + current, prompt, name)
                    self.assertIn('Scheduled shutdown time: ' + deadline, prompt, name)
                for name in ('seed.json', 'seed.txt'):
                    self.assertEqual((out / name).read_bytes(), (SOURCE / name).read_bytes())

    def test_common_setup_has_concrete_project_relative_file_example(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'packet'
            self.module.prepare_packet(SOURCE, MODEL, out, START, LEASE)
            common = (out / 'common.template.txt').read_text()
            self.assertIn('README.md -> /home/user/projects/omnicore/README.md', common)
            for arm in ('baseline', 'generic', 'profile'):
                self.assertTrue((out / (arm + '.template.txt')).read_text().startswith(common))

    def test_rehashed_source_changes_and_different_model_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source = base / 'source'
            shutil.copytree(SOURCE, source)
            for filename in ('seed.txt', 'settings.json'):
                original = (source / filename).read_bytes()
                (source / filename).write_bytes(original + b' ')
                checks = json.loads((source / 'checksums.json').read_text())
                checks[filename] = hashlib.sha256((source / filename).read_bytes()).hexdigest()
                (source / 'checksums.json').write_text(json.dumps(checks))
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    self.module.prepare_packet(source, MODEL, base / 'out', START, LEASE)
                self.assertFalse((base / 'out').exists())
                shutil.rmtree(source)
                shutil.copytree(SOURCE, source)
            other = base / 'model.json'
            other.write_bytes(MODEL.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                self.module.prepare_packet(SOURCE, other, base / 'out', START, LEASE)

    def test_invalid_time_or_lease_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'packet'
            for start, lease in [('2026-11-15T10:00:00', LEASE), (START, {}),
                                 (START, {'id': 'bad', 'provider_allocations_usd': {'openai': float('nan'), 'openrouter': 5}})]:
                with self.subTest(start=start, lease=lease), self.assertRaises(ValueError):
                    self.module.prepare_packet(SOURCE, MODEL, out, start, lease)
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
