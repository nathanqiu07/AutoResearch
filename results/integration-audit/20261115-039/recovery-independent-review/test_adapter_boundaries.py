"""Independent synthetic tests; import only the pinned audit input adapter."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

PIN = '2664df47897e7ce97e8030020d12ab1c1b322c3a97b1801cecd94272e8d2f3f1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    raw = (json.dumps(value, sort_keys=True) + '\n').encode()
    path.write_bytes(raw)
    return sha(raw)


def archive(path, name, data, kind='regular'):
    with tarfile.open(path, 'w') as tar:
        member = tarfile.TarInfo(name)
        member.mode = 0o600
        if kind == 'regular':
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
        else:
            member.type = tarfile.SYMTYPE
            member.linkname = 'outside'
            tar.addfile(member)
    raw = path.read_bytes()
    return {'archive_sha256': sha(raw), 'archive_size_bytes': len(raw), 'member_count': 1}


class BoundaryChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='synthetic039-', dir=OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.retained = self.root / 'retained'
        self.retained.mkdir()
        self.data = b'synthetic byte content\n'
        (self.retained / 'item').write_bytes(self.data)
        self.rows = [{'commit': commit, 'path': name, 'sha256': sha(self.data), 'size_bytes': len(self.data)} for commit, name in [('a', 'same'), ('b', 'same'), ('a', 'source'), ('a', 'publication')]]
        self.inventory = self.root / 'inventory.json'
        self.inventory_pin = dump(self.inventory, {'files': self.rows})
        self.source, self.publication = self.root / 'source.tar', self.root / 'publication.tar'
        stores = [('retained', 'item'), ('retained', 'item'), ('source', 'source/item'), ('publication', 'publication/item')]
        self.map = {'original_inventory_sha256': self.inventory_pin, 'original_reader_sha256': 'synthetic',
                    'files': [{**r, 'store': store, 'relative_path': relative} for r, (store, relative) in zip(self.rows, stores)],
                    'archives': {'source': archive(self.source, 'source/item', self.data), 'publication': archive(self.publication, 'publication/item', self.data)}}
        self.mapfile = self.root / 'map.json'

    def construct(self):
        pin = dump(self.mapfile, self.map)
        return ADAPTER.RecoveryInputs(self.mapfile, pin, self.inventory, self.inventory_pin, self.retained, self.source, self.publication)

    def read_all(self, reader):
        for row in self.rows:
            self.assertEqual(reader.read(row['commit'], row['path']), self.data)

    def test_positive_mixed_stores_shared_physical_file(self):
        reader = self.construct()
        self.read_all(reader)
        result = reader.finish()
        self.assertEqual((result['logical_inputs_verified'], result['retained_logical_refs'], result['retained_physical_files_verified']), (4, 2, 1))
        self.assertFalse(result['fallback_allowed'])

    def test_unknown_identity_never_falls_back(self):
        reader = self.construct()
        with self.assertRaisesRegex(ValueError, 'Unmapped input; no fallback'):
            reader.read('unapproved', str(self.inventory))

    def test_missing_retained_file_never_falls_back(self):
        reader = self.construct()
        (self.retained / 'item').unlink()
        with self.assertRaises(FileNotFoundError):
            reader.read('a', 'same')

    def test_unsafe_path_rejected_before_access(self):
        self.map['files'][0]['relative_path'] = '../escape'
        with self.assertRaisesRegex(ValueError, 'Unsafe relative path'):
            self.construct()

    def test_parent_symlink_escape_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'item').write_bytes(self.data)
        (self.retained / 'linked').symlink_to(outside, target_is_directory=True)
        self.map['files'][0]['relative_path'] = 'linked/item'
        reader = self.construct()
        with self.assertRaisesRegex(ValueError, 'escapes retained root'):
            reader.read('a', 'same')

    def test_archive_member_hash_checked_beyond_archive_pin(self):
        self.map['archives']['source'] = archive(self.source, 'source/item', b'changed synthetic bytes')
        with self.assertRaisesRegex(ValueError, 'Archive member hash/size mismatch'):
            self.construct()

    def test_archive_symlink_member_rejected(self):
        self.map['archives']['source'] = archive(self.source, 'source/item', self.data, 'symlink')
        with self.assertRaisesRegex(ValueError, 'not regular'):
            self.construct()

    def test_duplicate_logical_mapping_rejected(self):
        self.map['files'].append(self.map['files'][0].copy())
        with self.assertRaisesRegex(ValueError, 'duplicate mapped identity'):
            self.construct()

    def test_metadata_drift_rejected_at_finish(self):
        reader = self.construct()
        self.read_all(reader)
        self.inventory.write_bytes(b'changed synthetic inventory')
        with self.assertRaisesRegex(ValueError, 'changed during replay'):
            reader.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sha(args.adapter.read_bytes()) != PIN:
        raise ValueError('Audit adapter pin mismatch')
    args.out.mkdir(mode=0o700)
    OUTPUT = args.out
    spec = importlib.util.spec_from_file_location('independent_synthetic_audit_adapter', args.adapter)
    ADAPTER = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ADAPTER)
    def deny(event, details):
        if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
            raise RuntimeError('Synthetic adapter tests prohibit network and processes')
    sys.addaudithook(deny)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BoundaryChecks))
    report = {'schema_version': 'independent039-adapter-boundary-tests-v1',
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'adapter_sha256': PIN, 'test_sha256': sha(Path(__file__).read_bytes()),
              'owner_code_imported': False, 'raw_approved_payloads_read': False, 'model_calls': 0,
              'network_and_subprocess_denied': True, 'temporary_synthetic_fixtures_removed': True}
    dump(OUTPUT / 'report.json', report)
    sys.exit(0 if result.wasSuccessful() else 1)
