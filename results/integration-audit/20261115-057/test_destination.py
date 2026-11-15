"""Synthetic-only behavioral checks; never reads authority's real sources."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
ROLES = ['allowlist', 'custody_review', 'retention_map', 'proposed_tuples',
         'summary', 'gaps', 'metadata_pins']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packed(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


class Fixture:
    def __init__(self, root):
        self.root = root
        root.mkdir(mode=0o700)
        (root / 'controls').mkdir(mode=0o700)
        self.contents = {sha(b'alpha'): b'alpha', sha(b'beta'): b'beta'}
        self.allowed = [
            dict(path='/SOURCE_DO_NOT_READ/one', sha256=sha(b'alpha'), roles=['input'], logical_size_bytes_observed=5),
            dict(path='/SOURCE_DO_NOT_READ/alias', sha256=sha(b'alpha'), roles=['input', 'alias'], logical_size_bytes_observed=5),
            dict(path='/SOURCE_DO_NOT_READ/two', sha256=sha(b'beta'), roles=['trace'], logical_size_bytes_observed=4),
        ]
        self.excluded = [dict(path='/SOURCE_DO_NOT_READ/excluded', sha256=sha(b'excluded'), roles=['held'], logical_size_bytes_observed=8, reason='not approved')]
        proposed = self.allowed + [{k: v for k, v in self.excluded[0].items() if k != 'reason'}]
        self.controls = {role: {'schema_version': 'synthetic-metadata'} for role in ROLES}
        self.controls['allowlist'].update(allowed=self.allowed, excluded=self.excluded)
        self.controls['proposed_tuples']['proposed'] = proposed
        self.controls['retention_map']['inputs'] = [
            {k: v for k, v in row.items() if k != 'logical_size_bytes_observed'} |
            {'observed_lstat': {'size_bytes': row['logical_size_bytes_observed']}}
            for row in proposed]
        self.counts = dict(allowed=3, excluded=1, unique_objects=2, logical_bytes=14, object_bytes=9)
        self.authority = dict(
            schema_version='root-exact-private-retention-authority-v2', state='authorized_exact_copy',
            destination=str(root), references={}, allowed_logical_tuples=3, excluded_logical_tuples=1,
            declared_unique_hashes=2, declared_logical_bytes=14,
            tuple_fields=['path', 'sha256', 'roles', 'logical_size_bytes_observed'],
            permissions={'directories': '0700', 'files': '0600'},
            require_copy_time_source_hash_and_size_match=True, require_exact_allowed_tuple_union=True,
            require_regular_files_and_safe_paths=True, require_staged_atomic_write_and_fsync=True,
            require_independent_destination_rehash_and_manifest_verification=True,
            no_existing_destination_overwrite=True,
        )
        for key in ['excluded_tuple_reads_or_copies_authorized', 'reuse_existing_archives_only_on_verified_exact_hash_match',
                    'reuse_existing_archives_authorized', 'old_private_archive_metadata_transfer_authorized',
                    'private_payloads_in_git', 'credentials_or_env_files', 'sqlite_wal_shm_or_live_databases',
                    'raw_development_or_final_label_bundles', 'provider_cache_traversal',
                    'recursive_reference_following', 'model_calls', 'source_or_scientific_edits']:
            self.authority[key] = False
        states = []
        for row in self.allowed:
            stat = dict(size_bytes=row['logical_size_bytes_observed'], mode='0o644', device=1,
                        inode=len(states) + 1, mtime_ns=2, ctime_ns=3)
            states.append(dict(path=row['path'], before=stat, after=dict(stat)))
        self.mapping = dict(schema_version='closed-scaling-ownswap-private-mapping-v2', authority_sha256='',
            control_pins={}, inputs=[dict(r, archive_member='objects/' + r['sha256']) for r in self.allowed],
            source_states=states, counts=self.counts, source_checks_before=3, source_checks_after=3,
            all_sources_unchanged=True, controls_before_after_equal=True, copier_sha256='c' * 64,
            limitations=['Synthetic fixture; recorded source-state assertions only.'])
        self.archive()
        self.refresh_controls()

    def write(self, relative, value):
        data = value if isinstance(value, bytes) else packed(value)
        p = self.root / relative
        p.write_bytes(data)
        p.chmod(0o600)

    def archive(self, entries=None, trailing=b''):
        if entries is None:
            entries = [(f'objects/{h}', b, {}) for h, b in sorted(self.contents.items())]
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as tf:
            for name, data, attrs in entries:
                item = tarfile.TarInfo(name)
                item.size = len(data)
                item.mode = 0o600
                for key, value in attrs.items():
                    setattr(item, key, value)
                tf.addfile(item, io.BytesIO(data) if item.isreg() else None)
        self.write('objects.tar.gz', gzip.compress(raw.getvalue() + trailing, mtime=0))

    def refresh_controls(self):
        for role in ROLES:
            self.write(f'controls/{role}.json', self.controls[role])
            self.authority['references'][role] = dict(path=f'/SOURCE_DO_NOT_READ/{role}.json',
                                                      sha256=sha(packed(self.controls[role])))
        self.write('controls/authority.json', self.authority)
        self.authority_sha = sha(packed(self.authority))
        self.mapping['authority_sha256'] = self.authority_sha
        self.mapping['control_pins'] = {'authority': self.authority_sha} | {
            role: ref['sha256'] for role, ref in self.authority['references'].items()}
        self.refresh()

    def refresh(self):
        self.write('mapping.json', self.mapping)
        files = []
        names = [f'controls/{r}.json' for r in ['authority'] + ROLES] + ['mapping.json', 'objects.tar.gz']
        for name in sorted(names):
            data = (self.root / name).read_bytes()
            files.append(dict(path=name, sha256=sha(data), size_bytes=len(data)))
        manifest = dict(schema_version='closed-scaling-ownswap-private-manifest-v2',
                        authority_sha256=self.authority_sha, files=files, counts=self.counts)
        self.write('manifest.json', manifest)
        self.write('completion.json', dict(schema_version='closed-scaling-ownswap-copy-complete-v2',
            status='complete', authority_sha256=self.authority_sha, manifest_sha256=sha(packed(manifest)),
            counts=self.counts, copier_sha256='c' * 64, no_source_payload_parsing=True,
            prior_archive_dependencies=0))


class DestinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        path = HERE / 'verify_destination.py'
        if path.exists():
            spec = importlib.util.spec_from_file_location('independent_destination_verifier', path)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.assertIsNotNone(self.module, 'Verifier implementation is absent (expected RED).')
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-destination-', dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name).resolve() / 'destination')

    def verify(self, root=None, pin=None):
        return self.module.verify(root or self.f.root, pin or self.f.authority_sha)

    def reject(self, code):
        with self.assertRaises(self.module.VerificationError) as error:
            self.verify()
        self.assertEqual(error.exception.code, code)

    def entries(self):
        return [(f'objects/{h}', b, {}) for h, b in sorted(self.f.contents.items())]

    def test_valid_deduplicated_tree_never_opens_logical_source_identifiers(self):
        real_open = os.open
        def guarded(path, *args, **kwargs):
            self.assertNotIn('SOURCE_DO_NOT_READ', str(path))
            return real_open(path, *args, **kwargs)
        with patch('os.open', side_effect=guarded):
            report = self.verify()
        self.assertEqual(report['status'], 'verified')
        self.assertEqual(report['counts'], dict(allowed=3, excluded=1, unique_objects=2, logical_bytes=14, object_bytes=9))
        self.assertNotIn('SOURCE_DO_NOT_READ', json.dumps(report))

    def test_missing_archive_member(self):
        self.f.archive(self.entries()[:1]); self.f.refresh(); self.reject('archive_member_union')

    def test_excess_archive_member(self):
        entries = self.entries() + [('objects/' + sha(b'extra'), b'extra', {})]
        self.f.archive(sorted(entries)); self.f.refresh(); self.reject('archive_member_union')

    def test_duplicate_archive_member(self):
        e = self.entries(); self.f.archive([e[0], e[0], e[1]]); self.f.refresh(); self.reject('archive_duplicate')

    def test_unsafe_archive_member(self):
        self.f.archive([('../escape', b'x', {})]); self.f.refresh(); self.reject('archive_member_name')

    def test_absolute_archive_member(self):
        self.f.archive([('/escape', b'x', {})]); self.f.refresh(); self.reject('archive_member_name')

    def test_symlink_archive_member(self):
        e = self.entries(); e[0] = (e[0][0], b'', {'type': tarfile.SYMTYPE, 'linkname': '/SOURCE_DO_NOT_READ/link'})
        self.f.archive(e); self.f.refresh(); self.reject('archive_metadata')

    def test_corrupted_object_with_refreshed_archive_inventory(self):
        e = self.entries(); e[0] = (e[0][0], b'X' * len(e[0][1]), {})
        self.f.archive(e); self.f.refresh(); self.reject('archive_content_hash')

    def test_archive_wrong_member_mode(self):
        e = self.entries(); e[0] = (e[0][0], e[0][1], {'mode': 0o644})
        self.f.archive(e); self.f.refresh(); self.reject('archive_metadata')

    def test_nonzero_bytes_after_tar_end(self):
        self.f.archive(trailing=b'not-an-authorized-member'); self.f.refresh(); self.reject('archive_trailing_data')

    def test_mapping_tuple_union_mismatch_even_with_rebound_manifest(self):
        self.f.mapping['inputs'][0]['roles'] = ['changed']
        self.f.refresh(); self.reject('mapping_tuple_union')

    def test_allowed_and_proposed_union_mismatch_with_valid_control_pins(self):
        self.f.controls['proposed_tuples']['proposed'].pop()
        self.f.refresh_controls(); self.reject('proposed_tuple_union')

    def test_retention_map_union_mismatch_with_valid_control_pins(self):
        self.f.controls['retention_map']['inputs'].pop()
        self.f.refresh_controls(); self.reject('retention_map_tuple_union')

    def test_duplicate_allowed_tuple_not_hidden_by_set_deduplication(self):
        self.f.controls['allowlist']['allowed'].append(dict(self.f.allowed[0]))
        self.f.refresh_controls(); self.reject('duplicate_tuple')

    def test_wrong_file_mode(self):
        (self.f.root / 'mapping.json').chmod(0o644); self.reject('file_mode')

    def test_wrong_directory_mode(self):
        (self.f.root / 'controls').chmod(0o755); self.reject('directory_mode')

    def test_symlinked_destination_root(self):
        alias = self.f.root.parent / 'linked'; alias.symlink_to(self.f.root)
        with self.assertRaises(self.module.VerificationError) as error: self.verify(root=alias)
        self.assertEqual(error.exception.code, 'unsafe_root')

    def test_symlinked_output_member(self):
        file = self.f.root / 'objects.tar.gz'; file.unlink(); file.symlink_to('/SOURCE_DO_NOT_READ/archive')
        self.reject('nonregular_file')

    def test_excess_destination_file(self):
        self.f.write('extra.json', {}); self.reject('tree_inventory')

    def test_missing_destination_file(self):
        (self.f.root / 'completion.json').unlink(); self.reject('tree_inventory')

    def test_control_corruption_rejected_before_tuple_processing(self):
        self.f.write('controls/allowlist.json', {}); self.f.refresh(); self.reject('control_pin')

    def test_completion_manifest_mismatch(self):
        file = self.f.root / 'completion.json'; value = json.loads(file.read_text()); value['manifest_sha256'] = '0' * 64
        self.f.write('completion.json', value); self.reject('completion_binding')

    def test_wrong_authority_pin(self):
        with self.assertRaises(self.module.VerificationError) as error: self.verify(pin='0' * 64)
        self.assertEqual(error.exception.code, 'authority_pin')

    def test_source_state_assertion_cannot_claim_different_sizes(self):
        self.f.mapping['source_states'][0]['before']['size_bytes'] += 1
        self.f.refresh(); self.reject('recorded_source_state')

    def test_boolean_count_is_not_an_integer_count(self):
        self.f.mapping['counts'] = dict(self.f.counts, excluded=True)
        self.f.refresh(); self.reject('mapping_counts')

    def test_symlinked_ancestor_cannot_redirect_the_root(self):
        link = self.f.root.parent / 'ancestor-link'; link.symlink_to(self.f.root.parent)
        with self.assertRaises(self.module.VerificationError) as error:
            self.verify(root=link / 'destination')
        self.assertEqual(error.exception.code, 'unsafe_root')

    def test_duplicate_manifest_path_cannot_hide_a_missing_entry(self):
        value = json.loads((self.f.root / 'manifest.json').read_text())
        value['files'][1] = dict(value['files'][0])
        self.f.write('manifest.json', value); self.reject('manifest_inventory')

    def test_cli_success_and_rejection_do_not_print_private_locators(self):
        argv = [sys.executable, '-I', '-B', str(HERE / 'verify_destination.py'),
                '--root', str(self.f.root), '--authority-sha256', self.f.authority_sha]
        accepted = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(accepted.returncode, 0)
        self.assertEqual(json.loads(accepted.stdout)['status'], 'verified')
        self.assertEqual(set(json.loads(accepted.stdout)), {'status', 'counts', 'code_id'})
        self.assertEqual(accepted.stderr, '')
        (self.f.root / 'objects.tar.gz').unlink()
        (self.f.root / 'objects.tar.gz').symlink_to('/SOURCE_DO_NOT_READ/SECRET_PAYLOAD')
        rejected = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(json.loads(rejected.stdout), {'status': 'rejected', 'error_code': 'nonregular_file',
                                                      'code_id': 'independent-destination-verifier-v2'})
        self.assertEqual(rejected.stderr, '')
        for output in [accepted.stdout, rejected.stdout]:
            self.assertNotIn('SOURCE_DO_NOT_READ', output)
            self.assertNotIn(str(self.f.root), output)

    def test_cli_unknown_argument_does_not_echo_its_sensitive_value(self):
        sentinel = '/SYNTHETIC_PRIVATE/do-not-echo-0123456789abcdef'
        argv = [sys.executable, '-I', '-B', str(HERE / 'verify_destination.py'),
                '--root', str(self.f.root), '--authority-sha256', self.f.authority_sha,
                '--unexpected-sensitive-argument', sentinel]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertNotIn(sentinel, result.stdout + result.stderr)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'status': 'rejected', 'error_code': 'invalid_arguments',
                                                   'code_id': 'independent-destination-verifier-v2'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
