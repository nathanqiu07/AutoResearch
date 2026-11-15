"""Synthetic filesystem tests; never open released pilot evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location('reader', Path(__file__).with_name('read_metadata.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class DataPathTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(reader, 'DataPaths'), 'Reader has no portable data-root mapper')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.local = self.base / 'relocated'
        self.local.mkdir()
        self.recorded = self.base / 'original'
        self.paths = reader.DataPaths(self.local, self.recorded)

    def test_recorded_pointer_reads_relocated_bytes_without_original(self):
        target = self.local / 'result.json'
        target.write_text('{"synthetic":true}')
        self.assertEqual(self.paths.map(self.recorded / 'result.json').read_text(), '{"synthetic":true}')
        self.assertFalse(self.recorded.exists())

    def test_remapping_is_optional_for_local_pointers(self):
        target = self.local / 'result.json'
        target.write_text('{}')
        paths = reader.DataPaths(self.local)
        self.assertEqual(paths.map(target), target)
        with self.assertRaises(ValueError):
            paths.map(self.recorded / 'result.json')

    def test_relative_traversal_and_prefix_sibling_are_rejected(self):
        for path in ('result.json', self.recorded / '..' / 'result.json',
                     self.base / 'original-extra' / 'result.json'):
            with self.subTest(path=str(path)), self.assertRaises(ValueError):
                self.paths.map(path, must_exist=False)

    def test_symlink_escape_is_rejected_before_read(self):
        outside = self.base / 'outside.json'
        outside.write_text('{"must_not_read":true}')
        (self.local / 'escaped.json').symlink_to(outside)
        with self.assertRaises(ValueError):
            self.paths.map(self.recorded / 'escaped.json')

    def test_trace_discovery_uses_only_relocated_directory(self):
        local_traces = self.local / 'traces'
        original_traces = self.recorded / 'traces'
        local_traces.mkdir()
        original_traces.mkdir(parents=True)
        (local_traces / '0001-started.json').write_text('{}')
        (original_traces / 'extra.json').write_text('{}')
        self.assertEqual(self.paths.trace_files(original_traces), [local_traces / '0001-started.json'])
        self.assertEqual(self.paths.trace_files(self.recorded / 'missing'), [])

    def test_trace_symlink_escape_is_rejected(self):
        traces = self.local / 'traces'
        traces.mkdir()
        outside = self.base / 'outside.json'
        outside.write_text('{}')
        (traces / '0001-started.json').symlink_to(outside)
        with self.assertRaises(ValueError):
            self.paths.trace_files(self.recorded / 'traces')

    def test_data_root_alias_and_canonical_path_map_to_same_file(self):
        target = self.local / 'result.json'
        target.write_text('{}')
        alias = self.base / 'alias'
        alias.symlink_to(self.local, target_is_directory=True)
        paths = reader.DataPaths(alias, self.recorded)
        self.assertEqual(paths.map(alias / 'result.json'), target)
        self.assertEqual(paths.map(self.recorded / 'result.json'), target)


if __name__ == '__main__':
    unittest.main(verbosity=2)
