"""Independent adversarial cases using only the pinned author's synthetic fixture.

The fixture constructor is reused; no producer tests or production controls run.
All additional race schedules, access guards, mutations and assertions are ours.
"""
import copy
import gzip
import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile
import unittest
from unittest import mock

os.umask(0o077)
import closed_copy as c
import fixture_from_author as fixture


class IndependentBoundaries(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CopierTests()
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def no_completion(self):
        self.assertFalse((self.f.dest / 'completion.json').exists())

    def test_positive_opaque_copy_and_verifier_never_reopen_originals(self):
        self.assertEqual(self.f.run_copy()['status'], 'complete')
        real = c.read_regular
        seen = []
        def destination_only(path, *args, **kwargs):
            self.assertTrue(str(path).startswith(str(self.f.dest) + '/'))
            seen.append(str(path))
            return real(path, *args, **kwargs)
        with mock.patch.object(c, 'read_regular', side_effect=destination_only):
            self.assertEqual(c.verify_destination(str(self.f.dest), self.f.pin)['status'], 'verified')
        self.assertEqual(len(seen), 12)
        for p in self.f.dest.rglob('*'):
            self.assertEqual(stat.S_IMODE(p.lstat().st_mode), 0o700 if p.is_dir() else 0o600)

    def test_existing_excluded_sentinel_and_nested_pointer_never_opened(self):
        excluded = Path(self.f.excluded[0]['path'])
        excluded.write_bytes(b'EXCLUDED-SYNTHETIC-CONTENT')
        real = c.read_regular
        opened = []
        control_paths = {str(self.f.auth_path)} | {r['path'] for r in self.f.auth['references'].values()}
        payload_paths = {row['path'] for row in self.f.rows}
        def bounded(path, *args, **kwargs):
            name = str(path)
            self.assertTrue(name in control_paths | payload_paths or name.startswith(str(self.f.dest) + '/'))
            self.assertNotEqual(name, str(excluded))
            opened.append(name)
            return real(path, *args, **kwargs)
        with mock.patch.object(c, 'read_regular', side_effect=bounded):
            self.assertEqual(self.f.run_copy()['status'], 'complete')
        self.assertNotIn('/unfollowed/nonexistent', opened)
        self.assertEqual(excluded.read_bytes(), b'EXCLUDED-SYNTHETIC-CONTENT')
        for path in payload_paths:
            self.assertEqual(opened.count(path), 2)

    def test_forced_equal_hash_unequal_bytes_hits_byte_equality_guard(self):
        path = Path(self.f.rows[1]['path'])
        path.write_bytes(b'FAKEHASH')
        real = c.sha
        def synthetic_collision(body):
            return self.f.rows[0]['sha256'] if body == b'FAKEHASH' else real(body)
        with mock.patch.object(c, 'sha', side_effect=synthetic_collision):
            with self.assertRaisesRegex(c.BoundaryError, '^same_hash_different_bytes$'):
                self.f.run_copy()
        self.no_completion()

    def test_same_byte_replacement_between_stat_and_open_rejected(self):
        path = Path(self.f.rows[0]['path'])
        raw = path.read_bytes()
        real = os.open
        changed = False
        def swap(name, flags, *args, **kwargs):
            nonlocal changed
            if name == path.name and kwargs.get('dir_fd') is not None and not changed:
                changed = True
                other = path.with_name('replacement')
                other.write_bytes(raw)
                os.replace(other, path)
            return real(name, flags, *args, **kwargs)
        with mock.patch('os.open', side_effect=swap):
            with self.assertRaisesRegex(c.BoundaryError, '^changed_before_read$'):
                c.read_regular(str(path))
        self.assertTrue(changed)

    def test_mid_read_same_length_mutation_rejected(self):
        path = Path(self.f.rows[0]['path'])
        inode = path.stat().st_ino
        real = os.read
        changed = False
        def mutate(fd, count):
            nonlocal changed
            body = real(fd, count)
            if body and not changed and os.fstat(fd).st_ino == inode:
                changed = True
                path.write_bytes(b'MUTATED!')
            return body
        with mock.patch('os.read', side_effect=mutate):
            with self.assertRaisesRegex(c.BoundaryError, '^changed_during_read$'):
                c.read_regular(str(path))
        self.assertTrue(changed)

    def test_ancestor_symlink_race_never_reads_redirected_target(self):
        first = Path(self.f.rows[0]['path'])
        outside = self.f.root / 'unapproved'
        outside.mkdir(mode=0o700)
        for row in self.f.rows:
            (outside / Path(row['path']).name).write_bytes(b'UNAPPROVED-REDIRECT')
        forbidden_inodes = {p.stat().st_ino for p in outside.iterdir()}
        anchored = self.f.root / 'anchored-original'
        real_open, real_read = os.open, os.read
        changed = False
        def redirect(name, flags, *args, **kwargs):
            nonlocal changed
            if name == first.name and kwargs.get('dir_fd') is not None and not changed:
                changed = True
                self.f.src.rename(anchored)
                self.f.src.symlink_to(outside, target_is_directory=True)
            return real_open(name, flags, *args, **kwargs)
        def guarded_read(fd, count):
            self.assertNotIn(os.fstat(fd).st_ino, forbidden_inodes)
            return real_read(fd, count)
        with mock.patch('os.open', side_effect=redirect), mock.patch('os.read', side_effect=guarded_read):
            with self.assertRaisesRegex(c.BoundaryError, '^unsafe_or_unreadable_file$'):
                self.f.run_copy()
        self.assertTrue(changed)
        self.no_completion()

    def test_post_archive_same_byte_replacement_rejected(self):
        real = c.atomic_write
        def swap(directory, name, body):
            result = real(directory, name, body)
            if name == 'objects.tar.gz':
                path = Path(self.f.rows[0]['path'])
                replacement = path.with_name('replacement')
                replacement.write_bytes(path.read_bytes())
                os.replace(replacement, path)
            return result
        with mock.patch.object(c, 'atomic_write', side_effect=swap):
            with self.assertRaisesRegex(c.BoundaryError, '^source_changed$'):
                self.f.run_copy()
        self.no_completion()

    def test_control_hash_mutation_stops_before_payload_and_destination(self):
        self.f.auth_path.write_bytes(self.f.auth_path.read_bytes() + b' ')
        real = c.read_regular
        reads = []
        def track(path, *args, **kwargs):
            reads.append(str(path))
            return real(path, *args, **kwargs)
        with mock.patch.object(c, 'read_regular', side_effect=track):
            with self.assertRaisesRegex(c.BoundaryError, '^authority_pin$'):
                self.f.run_copy()
        self.assertEqual(reads, [str(self.f.auth_path)])
        self.assertFalse(self.f.dest.exists())

    def test_control_mutation_after_archive_leaves_no_completion(self):
        real = c.atomic_write
        def mutate(directory, name, body):
            result = real(directory, name, body)
            if name == 'objects.tar.gz':
                self.f.auth_path.write_bytes(self.f.auth_path.read_bytes() + b' ')
            return result
        with mock.patch.object(c, 'atomic_write', side_effect=mutate):
            with self.assertRaisesRegex(c.BoundaryError, '^size_mismatch$'):
                self.f.run_copy()
        self.no_completion()

    def test_post_publication_failure_removes_completion_but_keeps_evidence(self):
        real = c.atomic_write
        def fail(directory, name, body):
            result = real(directory, name, body)
            if name == 'completion.json':
                raise c.BoundaryError('synthetic_after_completion_publish')
            return result
        with mock.patch.object(c, 'atomic_write', side_effect=fail):
            with self.assertRaisesRegex(c.BoundaryError, '^synthetic_after_completion_publish$'):
                self.f.run_copy()
        self.no_completion()
        self.assertEqual(c.verify_destination(str(self.f.dest), self.f.pin, require_completion=False)['status'], 'verified')

    def test_final_verifier_failure_removes_completion(self):
        real = c.verify_destination
        def fail(destination, pin, require_completion=True):
            result = real(destination, pin, require_completion=require_completion)
            if require_completion:
                raise c.BoundaryError('synthetic_final_verifier_failure')
            return result
        with mock.patch.object(c, 'verify_destination', side_effect=fail):
            with self.assertRaisesRegex(c.BoundaryError, '^synthetic_final_verifier_failure$'):
                self.f.run_copy()
        self.no_completion()

    def test_existing_destination_and_exclusive_file_publish_preserved(self):
        self.f.dest.mkdir(mode=0o700)
        sentinel = self.f.dest / 'keep'
        sentinel.write_bytes(b'unchanged')
        with self.assertRaisesRegex(c.BoundaryError, '^destination_exists_or_unsafe$'):
            self.f.run_copy()
        self.assertEqual(sentinel.read_bytes(), b'unchanged')
        with self.assertRaisesRegex(c.BoundaryError, '^exclusive_atomic_write_failed$'):
            c.atomic_write(str(self.f.dest), 'keep', b'overwrite')
        self.assertEqual(sentinel.read_bytes(), b'unchanged')
        self.assertEqual(sorted(p.name for p in self.f.dest.iterdir()), ['keep'])

    def test_archive_exact_duplicate_mode_link_and_trailing_data_guards(self):
        body = b'object'
        digest = hashlib.sha256(body).hexdigest()
        expected = {digest: len(body)}
        positive = c.pack_objects({digest: body})
        self.assertIsNone(c.verify_objects(positive, expected))
        for duplicate, mode, kind in [(True, 0o600, tarfile.REGTYPE), (False, 0o644, tarfile.REGTYPE),
                                       (False, 0o600, tarfile.SYMTYPE)]:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for _ in range(2 if duplicate else 1):
                    member = tarfile.TarInfo('objects/' + digest)
                    member.mode, member.type = mode, kind
                    member.size = len(body) if kind == tarfile.REGTYPE else 0
                    if kind == tarfile.SYMTYPE:
                        member.linkname = '/unapproved-never-read'
                    archive.addfile(member, io.BytesIO(body) if kind == tarfile.REGTYPE else None)
            with self.subTest(case=(duplicate, mode, kind)), self.assertRaises(c.BoundaryError):
                c.verify_objects(gzip.compress(buffer.getvalue()), expected)
        trailing = gzip.compress(gzip.decompress(positive) + b'X' * 512)
        with self.assertRaisesRegex(c.BoundaryError, '^tar_trailing_data$'):
            c.verify_objects(trailing, expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
