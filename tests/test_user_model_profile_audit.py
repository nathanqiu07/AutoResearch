import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'scripts' / 'user_model_audit'
sys.path.insert(0, str(ROOT))
SOURCE_ROOT = os.environ.get('GIO_AUDIT_SOURCE_ROOT', str(Path(__file__).resolve().parents[1]))

class ProfileAuditTests(unittest.TestCase):
    def test_reports_empty_channels_without_calling_it_a_winner(self):
        from profile_audit import summarize_channels
        result = summarize_channels({'principles': [], 'persona': '', 'exemplars': [],
                                     'weights': {'rigor': 0.0}, 'assumptions': {}})
        self.assertTrue(result['empty_text_conditioning'])
        self.assertEqual(result['principles'], 0)
        self.assertFalse(result['nonzero_weights'])

    def test_nonempty_examples_and_persona_remain_distinct(self):
        from profile_audit import summarize_channels
        result = summarize_channels({'principles': ['conditional rule'], 'persona': 'Contextual preference',
                                     'exemplars': [{'chosen': 'b'}], 'weights': {}, 'assumptions': {}})
        self.assertEqual(result['principles'], 1)
        self.assertEqual(result['exemplars'], 1)
        self.assertGreater(result['persona_chars'], 0)
        self.assertFalse(result['empty_text_conditioning'])

    def test_json_rejects_nonfinite_values(self):
        from profile_audit import read_json
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.json'
            p.write_text('{"confidence": NaN}')
            with self.assertRaises(ValueError):
                read_json(p)

    def test_json_rejects_overflowed_floats(self):
        from profile_audit import read_json
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.json'
            p.write_text('{"weight": 1e9999}')
            with self.assertRaises(ValueError):
                read_json(p)

    def test_json_rejects_duplicate_keys(self):
        from profile_audit import read_json
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.json'
            p.write_text('{"method":"m0", "method":"m3"}')
            with self.assertRaises(ValueError):
                read_json(p)

    def test_output_refuses_overwrite(self):
        from profile_audit import write_report
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'report.json'
            write_report(p, {'mode': 'offline_audit'})
            with self.assertRaises(FileExistsError):
                write_report(p, {'mode': 'changed'})
            self.assertEqual(json.loads(p.read_text()), {'mode': 'offline_audit'})

class ProfileAuditIntegrationTests(unittest.TestCase):
    def test_actual_loader_and_predictor_preserve_principle_conditioning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / 'model.json'
            fixture = {'version': 1, 'method': 'm3', 'seed': 0, 'config': {},
                       'backend': {'label': 'offline-audit-fixture', 'endpoint': '', 'class': 'FixtureLLM'},
                       'artifacts': {'principles': ['A conditional preference.'], 'persona': '',
                                     'exemplars': [], 'weights': {}, 'assumptions': {}, 'metadata': {'prompt_version': 'archived-other-version'}},
                       'cost': {}}
            artifact.write_text(json.dumps(fixture))
            report = root / 'report.json'
            run = subprocess.run([sys.executable, str(ROOT / 'profile_audit.py'), '--source-root',
                                  SOURCE_ROOT, '--artifact', str(artifact),
                                  '--out', str(report)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            output = json.loads(report.read_text())
            row = output['artifacts'][0]
            self.assertEqual(row['prediction_channels']['principles'], ['A conditional preference.'])
            self.assertEqual(row['adviser_principles'], ['A conditional preference.'])
            self.assertTrue(all(row['roundtrip'].values()))
            self.assertTrue(row['artifact_unchanged'])
            self.assertEqual(json.loads(artifact.read_text()), fixture)
            self.assertEqual(row['live_backend_compatibility'], 'not_tested')
            self.assertFalse(row['prompt_version_matches'])
            self.assertNotEqual(row['runtime_prompt_version'], row['saved_prompt_version'])

class ProfileAuditBoundaryTests(unittest.TestCase):
    def run_fixture(self, directory, source=SOURCE_ROOT, learned=False, weights=None):
        root = Path(directory)
        artifact = root / 'model.json'
        fixture = {'version': 1, 'method': 'm4' if learned else 'm3', 'seed': 0, 'config': {},
                   'backend': {'label': 'fixture', 'endpoint': '', 'class': 'FixtureLLM'},
                   'artifacts': {'principles': [], 'persona': '', 'exemplars': [],
                                 'weights': weights or {}, 'assumptions': {},
                                 'metadata': {'weights_status': 'learned'} if learned else {}}, 'cost': {}}
        artifact.write_text(json.dumps(fixture))
        report = root / 'report.json'
        environment = dict(os.environ, PYTHONPATH=SOURCE_ROOT)
        run = subprocess.run([sys.executable, str(ROOT / 'profile_audit.py'), '--source-root',
                              source, '--artifact', str(artifact), '--out', str(report)],
                             capture_output=True, text=True, env=environment)
        return run, json.loads(report.read_text()) if report.exists() else None

    def test_missing_source_cannot_borrow_imports_from_pythonpath(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'empty_source'
            source.mkdir()
            run, report = self.run_fixture(directory, str(source))
            self.assertNotEqual(run.returncode, 0)
            self.assertIsNone(report)

    def test_learned_weights_capture_each_option_feature_prompt(self):
        from autoresearch.taste.profile import FEATURES
        with tempfile.TemporaryDirectory() as directory:
            run, report = self.run_fixture(directory, learned=True,
                                           weights={feature: 0.5 for feature in FEATURES})
            self.assertEqual(run.returncode, 0, run.stderr)
            row = report['artifacts'][0]
            self.assertIsNone(row['prediction_error'])
            self.assertEqual(len(row['prediction_requests']), 2)
            self.assertEqual([r['request_kind'] for r in row['prediction_requests']],
                             ['option_features', 'option_features'])
            self.assertIsNone(row['prediction_channels'])

    def test_change_after_first_inspection_invalidates_whole_batch(self):
        import profile_audit
        with tempfile.TemporaryDirectory() as directory:
            self.run_fixture(directory)
            root = Path(directory)
            first, second = root / 'model.json', root / 'second.json'
            second.write_bytes(first.read_bytes())
            output = root / 'batch.json'
            inspect = profile_audit.audit_artifact
            def mutate_between_inputs(path, source):
                if path == second:
                    first.write_bytes(first.read_bytes() + b'\n')
                return inspect(path, source)
            argv = ['profile_audit.py', '--source-root', SOURCE_ROOT, '--artifact', str(first),
                    '--artifact', str(second), '--out', str(output)]
            with patch.object(sys, 'argv', argv), patch.object(profile_audit, 'audit_artifact',
                                                              side_effect=mutate_between_inputs):
                status = profile_audit.main()
            self.assertEqual(status, 1)
            self.assertFalse(json.loads(output.read_text())['all_inputs_unchanged'])

    def test_predictor_error_is_not_a_successful_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            run, report = self.run_fixture(directory, learned=True, weights={'wrong_feature': 1.0})
            self.assertNotEqual(run.returncode, 0)
            self.assertIsNotNone(report['artifacts'][0]['prediction_error'])
            self.assertFalse(report['all_predictions_completed'])

if __name__ == '__main__':
    unittest.main()
