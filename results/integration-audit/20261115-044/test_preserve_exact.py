"""Synthetic-only tests of opaque retention and rejection boundaries."""
import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest import mock

import preserve_exact as subject


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RetentionBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def row(self, name, data, roles=None):
        path = self.root / name
        path.write_bytes(data)
        return {'path': str(path), 'sha256': sha(data),
                'logical_size_bytes_observed': len(data), 'roles': roles or ['synthetic.input']}

    def reuse(self, row):
        data = Path(row['path']).read_bytes()
        blob = self.tar([('kept.json', data, tarfile.REGTYPE, 0o600)])
        path = self.private / 'existing.tar.gz'
        path.write_bytes(blob)
        path.chmod(0o600)
        return {'archive_sha256': sha(blob), 'members': [
            {'source_path': row['path'], 'archive_member': 'kept.json',
             'sha256': row['sha256'], 'size_bytes': len(data)}]}, path

    @staticmethod
    def tar(entries):
        target = io.BytesIO()
        with tarfile.open(fileobj=target, mode='w:gz', format=tarfile.USTAR_FORMAT) as archive:
            for name, data, kind, mode in entries:
                info = tarfile.TarInfo(name)
                info.type, info.mode = kind, mode
                info.size = len(data) if kind == tarfile.REGTYPE else 0
                if kind == tarfile.SYMTYPE:
                    info.linkname = '/unapproved'
                archive.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
        return target.getvalue()

    def invoke(self, rows, reuse=None, old=None, excluded=None):
        return subject.retain(rows, excluded or [], reuse or {'members': []}, old,
                              self.private / 'new.tar.gz')

    def test_preserves_all_roles_deduplicates_equal_bytes_and_reuses_existing_member(self):
        alias = self.row('retained.json', b'old')
        a = self.row('a.json', b'\x00opaque\xff', ['role.one', 'role.two'])
        b = self.row('b.json', b'\x00opaque\xff')
        c = self.row('c.json', b'different')
        reuse, old = self.reuse(alias)
        result = self.invoke([alias, a, b, c], reuse, old)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['logical_count'], 4)
        self.assertEqual(result['new_member_count'], 2)
        self.assertEqual(result['reused_logical_count'], 1)
        self.assertEqual(result['source_checks_before'], 4)
        self.assertEqual(result['source_checks_after'], 4)
        self.assertEqual(result['logical_inputs'][1]['roles'], ['role.one', 'role.two'])
        self.assertEqual(result['logical_inputs'][0]['storage'], 'existing_archive')
        self.assertEqual(result['logical_inputs'][1]['archive_member'], result['logical_inputs'][2]['archive_member'])
        self.assertEqual(stat.S_IMODE((self.private / 'new.tar.gz').stat().st_mode), 0o600)
        self.assertTrue(result['all_sources_unchanged'])

    def test_wrong_actual_hash_is_rejected_before_deduplication(self):
        a = self.row('a', b'same')
        b = self.row('b', b'evil')
        b['sha256'] = a['sha256']
        with self.assertRaises(subject.BoundaryError):
            self.invoke([a, b])
        self.assertFalse((self.private / 'new.tar.gz').exists())

    def test_observed_size_mismatch_is_rejected(self):
        row = self.row('a', b'data')
        row['logical_size_bytes_observed'] += 1
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row])

    def test_source_symlink_is_rejected(self):
        row = self.row('a', b'data')
        link = self.root / 'link'
        link.symlink_to(row['path'])
        row['path'] = str(link)
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row])

    def test_parent_symlink_is_rejected(self):
        folder = self.root / 'actual'
        folder.mkdir()
        row = self.row('actual/a', b'data')
        (self.root / 'linked').symlink_to(folder, target_is_directory=True)
        row['path'] = str(self.root / 'linked/a')
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row])

    def test_nonregular_source_is_rejected_without_opening_fifo(self):
        row = self.row('a', b'data')
        os.unlink(row['path'])
        os.mkfifo(row['path'])
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row])

    def test_existing_destination_is_not_overwritten(self):
        row = self.row('a', b'data')
        dest = self.private / 'new.tar.gz'
        dest.write_bytes(b'keep')
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row])
        self.assertEqual(dest.read_bytes(), b'keep')

    def test_private_directory_mode_must_be_0700(self):
        row = self.row('a', b'data')
        self.private.chmod(0o755)
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row])

    def test_duplicate_logical_path_is_rejected(self):
        row = self.row('a', b'data')
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row, dict(row)])

    def test_excluded_overlap_is_rejected_and_unreferenced_exclusion_is_not_opened(self):
        row = self.row('a', b'data')
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row], excluded=[dict(row)])
        trap = dict(row, path=str(self.root / 'nonexistent-excluded'))
        result = self.invoke([row], excluded=[trap])
        self.assertIsInstance(result, dict)
        self.assertEqual(result['logical_count'], 1)

    def test_relative_dotdot_glob_and_duplicate_roles_are_rejected(self):
        row = self.row('a', b'data')
        candidates = [dict(row, path='a'), dict(row, path=str(self.root) + '/../a'),
                      dict(row, path=str(self.root / '*.json')),
                      dict(row, roles=['same', 'same'])]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(subject.BoundaryError):
                    subject.validate_rows([candidate], [])

    def test_reused_archive_hash_and_member_must_match(self):
        row = self.row('a', b'data')
        reuse, old = self.reuse(row)
        reuse['archive_sha256'] = '0' * 64
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row], reuse, old)
        reuse['archive_sha256'] = sha(old.read_bytes())
        reuse['members'][0]['sha256'] = '1' * 64
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row], reuse, old)

    def test_reuse_member_without_exact_approved_source_is_rejected(self):
        row = self.row('a', b'data')
        reuse, old = self.reuse(row)
        reuse['members'][0]['source_path'] = str(self.root / 'unapproved')
        with self.assertRaises(subject.BoundaryError):
            self.invoke([row], reuse, old)

    def test_source_changed_after_write_leaves_private_failed_archive(self):
        row = self.row('a', b'data')
        original = subject.read_regular
        calls = 0
        def changing(path):
            nonlocal calls
            if str(path) == row['path']:
                calls += 1
                if calls == 2:
                    Path(path).write_bytes(b'changed')
            return original(path)
        with mock.patch.object(subject, 'read_regular', side_effect=changing):
            with self.assertRaises(subject.BoundaryError):
                self.invoke([row])
        dest = self.private / 'new.tar.gz'
        self.assertTrue(dest.exists())
        self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o600)

    def test_archive_extra_missing_unsafe_link_and_mode_are_rejected(self):
        expected = {'objects/' + sha(b'a'): {'sha256': sha(b'a'), 'size_bytes': 1}}
        name = next(iter(expected))
        variants = [[], [(name, b'a', tarfile.REGTYPE, 0o600), ('extra', b'b', tarfile.REGTYPE, 0o600)],
                    [('../escape', b'a', tarfile.REGTYPE, 0o600)],
                    [(name, b'', tarfile.SYMTYPE, 0o600)],
                    [(name, b'a', tarfile.REGTYPE, 0o644)],
                    [(name, b'b', tarfile.REGTYPE, 0o600)]]
        for entries in variants:
            with self.subTest(entries=entries):
                with self.assertRaises(subject.BoundaryError):
                    subject.verify_tar(self.tar(entries), expected)

    def test_deterministic_generated_archive_is_exact_and_sorted(self):
        objects = {sha(b'z'): b'z', sha(b'a'): b'a'}
        data = subject.pack_objects(objects)
        self.assertIsInstance(data, bytes)
        self.assertEqual(data, subject.pack_objects(dict(reversed(list(objects.items())))))
        expected = {'objects/' + h: {'sha256': h, 'size_bytes': len(b)} for h, b in objects.items()}
        result = subject.verify_tar(data, expected)
        self.assertEqual(result, sorted(expected))


if __name__ == '__main__':
    unittest.main(verbosity=2)
