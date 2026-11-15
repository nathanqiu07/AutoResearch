"""Synthetic-only local Git fixtures. No retained owner source/test is executed."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import verify_copy as checker


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


class CopyBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.audit = self.root / 'audit'
        self.owner = self.root / 'owner'
        for repository in (self.audit, self.owner):
            repository.mkdir()
            self.git(repository, 'init', '-q')
        self.snapshot = self.owner / checker.SNAPSHOT
        (self.snapshot / 'source').mkdir(parents=True)
        (self.snapshot / 'tests').mkdir()
        rows, proposed, manifest = [], [], []
        for index in range(20):
            name = ('source/' if index < 9 else 'tests/') + str(index) + '.py'
            # Inert bytes; deliberately not Python and never parsed or imported.
            data = (('synthetic-%02d|' % index).encode() * 1000)[:7837 if index < 19 else 7845]
            self.assertEqual(len(data), 7837 if index < 19 else 7845)
            (self.snapshot / name).write_bytes(data)
            original = '/unavailable-original-synthetic/' + str(index)
            rows.append({'index': index, 'original_path': original, 'proposed_relative_path': name,
                         'sha256': sha(data), 'size_bytes': len(data), 'decision': 'allow_exact_source_copy'})
            role = 'source' if index < 9 else 'test'
            proposed.append({'original_path': original, 'proposed_relative_path': name,
                             'sha256': sha(data), 'bytes': len(data), 'role': role})
            manifest.append({'original_path': original, 'destination': name, 'sha256': sha(data),
                             'bytes': len(data), 'role': role})
        proposal = {'schema_version': 'source-only-retention-proposal-v1', 'files': proposed,
                    'file_count': 20, 'total_bytes': 156748, 'proposed_repository_root': checker.SNAPSHOT}
        proposal_raw = encoded(proposal)
        decision = {'schema_version': 'audit052-source-publication-decision-v1',
                    'status': 'allow_exact_source_copy_for_all_20_reviewed_files',
                    'proposal': {'path': '/unavailable-original-synthetic/proposal', 'sha256': sha(proposal_raw),
                                 'size_bytes': len(proposal_raw)},
                    'proposed_repository_root': checker.SNAPSHOT, 'allowed_file_count': 20,
                    'allowed_bytes': 156748, 'files': rows, 'excluded_files': []}
        self.decision_raw = encoded(decision)
        receipt = {'payload_files': 20, 'payload_bytes': 156748, 'proposal_sha256': sha(proposal_raw),
                   'audit_decision_sha256': sha(self.decision_raw), 'all_original_and_destination_hashes_match': True,
                   'all_sources_ast_parsed_without_execution': True, 'private_inputs_followed': False,
                   'source_imports_or_execution': False, 'provider_calls': 0,
                   'scientific_outcomes_or_launch_authority_changed': False}
        self.receipt_raw = encoded(receipt)
        bodies = {'README.md': b'synthetic metadata\n', 'source-proposal.json': proposal_raw,
                  'audit-decision.json': self.decision_raw, 'COPY_RECEIPT.json': self.receipt_raw,
                  'SOURCE_MANIFEST.json': encoded({'schema_version': 'retained-source-manifest-v1', 'files': manifest})}
        for name, body in bodies.items():
            (self.snapshot / name).write_bytes(body)
        decision_path = self.audit / checker.DECISION_PATH
        decision_path.parent.mkdir(parents=True)
        decision_path.write_bytes(self.decision_raw)
        self.audit_commit = self.commit(self.audit)
        self.owner_commit = self.commit(self.owner)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def git(repository, *args):
        return subprocess.check_output(['git', '-C', str(repository), *args], stderr=subprocess.PIPE)

    def commit(self, repository):
        self.git(repository, 'add', '.')
        self.git(repository, '-c', 'user.name=Synthetic Audit', '-c', 'user.email=synthetic@example.invalid',
                 'commit', '-q', '-m', 'synthetic fixture', '--allow-empty')
        return self.git(repository, 'rev-parse', 'HEAD').decode().strip()

    def run_checker(self):
        out = self.root / 'report'
        argv = ['verify_copy.py', '--audit-repo', str(self.audit), '--coordinator-repo', str(self.owner),
                '--snapshot-commit', self.owner_commit, '--out', str(out)]
        with mock.patch.multiple(checker, DECISION_COMMIT=self.audit_commit, DECISION_HASH=sha(self.decision_raw),
                                 SNAPSHOT_COMMIT=self.owner_commit, RECEIPT_HASH=sha(self.receipt_raw), create=True):
            with mock.patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()):
                try:
                    status = checker.main()
                except (AssertionError, KeyError, OSError, ValueError, RuntimeError):
                    status = 1
        path = out / 'report.json'
        return status, json.loads(path.read_bytes()) if path.exists() else None

    def assert_failed_check(self, expected):
        status, report = self.run_checker()
        self.assertEqual(status, 1)
        self.assertIsNotNone(report)
        self.assertEqual(report['status'], 'failed')
        self.assertTrue(any(item['name'] == expected and not item['passed'] for item in report['checks']))

    def test_matched_20_file_copy_and_25_git_objects_pass(self):
        status, report = self.run_checker()
        self.assertEqual(status, 0)
        self.assertEqual(report['total_files'], 25)
        self.assertTrue(report['git']['all_objects_equal_local'])
        self.assertTrue(report['git']['tree_inventory_exact'])

    def test_missing_git_member_cannot_pass_on_valid_local_copy(self):
        self.git(self.owner, 'rm', '-q', checker.SNAPSHOT + '/README.md')
        self.owner_commit = self.commit(self.owner)
        (self.snapshot / 'README.md').write_bytes(b'synthetic metadata\n')
        self.assert_failed_check('git_exact_snapshot_inventory')

    def test_wrong_git_blob_cannot_pass_on_valid_local_copy(self):
        path = self.snapshot / 'source/0.py'
        saved = path.read_bytes()
        path.write_bytes(b'different committed bytes')
        self.owner_commit = self.commit(self.owner)
        path.write_bytes(saved)
        self.assert_failed_check('git_all_objects_equal_local')

    def test_wrong_actual_payload_hash_fails(self):
        path = self.snapshot / 'source/0.py'
        path.write_bytes(b'x' * len(path.read_bytes()))
        self.assert_failed_check('payload_hash:source/0.py')

    def test_extra_file_fails_without_reading_its_body(self):
        path = self.snapshot / 'unapproved.txt'
        path.write_bytes(b'do not read')
        original = checker.regular_bytes
        def restricted(value):
            self.assertNotEqual(Path(value), path)
            return original(value)
        with mock.patch.object(checker, 'regular_bytes', side_effect=restricted):
            self.assert_failed_check('exact_local_file_inventory')

    def test_source_manifest_role_mismatch_fails(self):
        path = self.snapshot / 'SOURCE_MANIFEST.json'
        value = json.loads(path.read_bytes())
        value['files'][0]['role'] = 'wrong'
        path.write_bytes(encoded(value))
        self.assert_failed_check('source_manifest_exact_ordered_tuples_and_roles')

    def test_copy_receipt_pin_and_claim_change_fails(self):
        path = self.snapshot / 'COPY_RECEIPT.json'
        value = json.loads(path.read_bytes())
        value['provider_calls'] = 1
        path.write_bytes(encoded(value))
        self.assert_failed_check('copied_receipt_hash')

    def test_payload_symlink_is_rejected(self):
        path = self.snapshot / 'source/0.py'
        saved = self.root / 'outside'
        saved.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(saved)
        status, _ = self.run_checker()
        self.assertEqual(status, 1)

    def test_change_after_first_read_is_required_failure(self):
        path = self.snapshot / 'source/0.py'
        original = checker.regular_bytes
        calls = 0
        def changing(value):
            nonlocal calls
            if Path(value) == path:
                calls += 1
                if calls == 2:
                    path.write_bytes(b'changed after comparison')
            return original(value)
        with mock.patch.object(checker, 'regular_bytes', side_effect=changing):
            self.assert_failed_check('destination_unchanged_during_verification:source/0.py')


if __name__ == '__main__':
    unittest.main(verbosity=2)
