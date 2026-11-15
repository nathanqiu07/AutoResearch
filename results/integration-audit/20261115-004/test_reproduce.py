"""Synthetic, offline checks for the committed-object evidence reader."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('reproduce.py')


class CommittedEvidenceTests(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.exists(), 'committed-evidence reproducer is not implemented')
        spec = importlib.util.spec_from_file_location('reproduce', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_reader_uses_pinned_blob_despite_worktree_and_later_commit_changes(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args],
                                      capture_output=True, text=True, check=True).stdout.strip()
            git('init', '-q')
            (root / 'evidence').mkdir()
            file = root / 'evidence/settings.json'
            file.write_text('{"model":"committed"}')
            git('add', 'evidence/settings.json')
            git('-c', 'user.name=Synthetic Test', '-c', 'user.email=test@example.invalid',
                'commit', '-qm', 'Synthetic fixture')
            pinned = git('rev-parse', 'HEAD')
            file.write_text('{"model":"later"}')
            git('add', 'evidence/settings.json')
            git('-c', 'user.name=Synthetic Test', '-c', 'user.email=test@example.invalid',
                'commit', '-qm', 'Later synthetic fixture')
            file.write_text('{"model":"dirty"}')
            (root / 'evidence/untracked.json').write_text('{"private":"ignore"}')
            source = module.GitSource(root, pinned)
            self.assertEqual(source.read_tree('evidence'), {'settings.json': b'{"model":"committed"}'})
            self.assertEqual(file.read_text(), '{"model":"dirty"}')

    def test_manifest_reports_missing_and_changed_committed_bytes(self):
        module = self.module()
        result = module.check_manifest({'a': b'changed'}, {'a': '0' * 64, 'missing': '1' * 64})
        self.assertEqual(result['checked'], 2)
        self.assertEqual(result['matching'], 0)
        self.assertEqual(result['entries'][1]['actual_sha256'], None)

    def test_settings_difference_retains_missing_versus_null(self):
        module = self.module()
        diff = module.setting_differences({'gone': None}, {'added': None})
        self.assertEqual(diff['added']['prepared'], {'present': False})
        self.assertEqual(diff['added']['executed'], {'present': True, 'value': None})
        self.assertEqual(diff['gone']['prepared'], {'present': True, 'value': None})
        self.assertEqual(diff['gone']['executed'], {'present': False})

    def test_output_directory_is_never_reused(self):
        self.module()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'out'
            out.mkdir()
            marker = out / 'keep.txt'
            marker.write_text('keep')
            result = subprocess.run(['python3', str(SCRIPT), '--source-root', temporary,
                                     '--source-commit', 'HEAD', '--out', str(out)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), 'keep')
            self.assertEqual(sorted(p.name for p in out.iterdir()), ['keep.txt'])


if __name__ == '__main__':
    unittest.main()
