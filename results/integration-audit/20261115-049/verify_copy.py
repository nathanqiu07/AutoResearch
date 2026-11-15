#!/usr/bin/env python3
"""Bounded read-only destination and Git-object comparison for audit 046's copy.

No retained source is imported, executed, semantically parsed or copied. Only
the five named snapshot metadata files are interpreted. Source/private paths
inside the decision, proposal and copied bodies are never opened or followed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

DECISION_COMMIT = '74b21b4d73fc2ceea78034a4764c26d71899f152'
DECISION_PATH = 'results/integration-audit/20261115-046/retention-decision.json'
DECISION_HASH = '8b965768fdbfe32a41c46b201ee1bfc9d443a5c1f647166fde2e6240757b17a4'
SNAPSHOT = 'docs/overnight/gio-profile-20261115/control/runtime-snapshots/reviewed-followup-20261115-v1'
METADATA = ['README.md', 'retention-proposal.json', 'audit046-retention-decision.json',
            'copy-verification.json', 'SHA256SUMS']


def sha(value):
    return hashlib.sha256(value).hexdigest()


def regular_bytes(path):
    """No symlink components; open an exact regular file with a stable identity."""
    path = Path(path)
    assert path.is_absolute() and '..' not in path.parts
    for parent in reversed(path.parents):
        assert stat.S_ISDIR(parent.lstat().st_mode) and not parent.is_symlink()
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        assert (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino)
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                                value.st_mtime_ns, value.st_ctime_ns)
        assert fields(before) == fields(after) == fields(path.lstat())
        data = b''.join(chunks)
        assert len(data) == before.st_size
        return data
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-repo', required=True)
    parser.add_argument('--coordinator-repo', required=True)
    parser.add_argument('--snapshot-commit', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    output = Path(args.out).resolve()
    output.mkdir(mode=0o700)
    audit = Path(args.audit_repo)
    coordinator = Path(args.coordinator_repo)
    assert audit.is_absolute() and coordinator.is_absolute()
    commands, checks, inventory = [], [], []

    def check(name, actual, expected=True):
        checks.append({'name': name, 'passed': actual == expected,
                       'actual': actual, 'expected': expected})

    def git(repo, *tail, allow_missing=False):
        argv = ['git', '-C', str(repo), *tail]
        process = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commands.append({'argv': argv, 'exit_code': process.returncode,
                         'stdout_sha256': sha(process.stdout), 'stdout_size_bytes': len(process.stdout),
                         'stderr_sha256': sha(process.stderr), 'stderr_size_bytes': len(process.stderr)})
        if process.returncode and not allow_missing:
            raise RuntimeError('required_git_read_failed')
        return process

    decision_raw = git(audit, 'cat-file', 'blob', DECISION_COMMIT + ':' + DECISION_PATH).stdout
    check('published_decision_object_hash', sha(decision_raw), DECISION_HASH)
    if sha(decision_raw) != DECISION_HASH:
        raise RuntimeError('decision_pin_mismatch')
    decision = json.loads(decision_raw)
    check('decision_status', decision['status'], 'allow_exact_27_for_coordinator_retention')
    check('decision_count', len(decision['files']), 27)
    check('decision_total_bytes', sum(row['size_bytes'] for row in decision['files']), 175124)
    check('decision_no_excluded_or_uncertain', [decision['excluded'], decision['uncertain']], [[], []])
    rows = decision['files']
    expected_paths = []
    for row in rows:
        path = PurePosixPath(row['proposed_repository_path'])
        assert not path.is_absolute() and '..' not in path.parts
        relative = str(path.relative_to(SNAPSHOT))
        assert PurePosixPath(relative).parts[0] in ('source', 'review')
        expected_paths.append(relative)
    check('unique_destinations', len(set(expected_paths)), 27)
    check('unique_proposal_indices', sorted(row['proposal_index'] for row in rows), list(range(27)))
    check('all_decisions_allow_exact_copy', all(row['decision'] == 'allow-for-owner-copy' for row in rows))
    root = coordinator / SNAPSHOT
    expected_inventory = set(expected_paths) | set(METADATA)
    # List names/types only in the exact snapshot and its two explicit folders.
    # Never descend into an unexpected directory or open an unlisted body.
    actual_files, actual_dirs, other_types = set(), set(), []
    for folder in ('', 'source', 'review'):
        current = root / folder
        assert stat.S_ISDIR(current.lstat().st_mode) and not current.is_symlink()
        with os.scandir(current) as listing:
            for item in listing:
                relative = (PurePosixPath(folder) / item.name).as_posix()
                info = item.stat(follow_symlinks=False)
                if stat.S_ISREG(info.st_mode):
                    actual_files.add(relative)
                elif stat.S_ISDIR(info.st_mode):
                    actual_dirs.add(relative)
                else:
                    other_types.append(relative)
    check('exact_local_file_inventory', sorted(actual_files), sorted(expected_inventory))
    check('exact_local_directory_inventory', sorted(actual_dirs), ['review', 'source'])
    check('no_other_local_file_types', other_types, [])
    local = {}
    for row, relative in zip(rows, expected_paths):
        data = regular_bytes(root / relative)
        digest = sha(data)
        check('payload_hash:' + relative, digest, row['source_sha256'])
        check('payload_size:' + relative, len(data), row['size_bytes'])
        local[relative] = data
        inventory.append({'relative_path': relative, 'category': 'approved_payload',
                          'sha256': digest, 'size_bytes': len(data),
                          'approved_sha256': row['source_sha256'], 'approved_size_bytes': row['size_bytes']})
    for relative in METADATA:
        data = regular_bytes(root / relative)
        local[relative] = data
        inventory.append({'relative_path': relative, 'category': 'snapshot_metadata',
                          'sha256': sha(data), 'size_bytes': len(data)})
    check('copied_decision_exact_bytes', local['audit046-retention-decision.json'] == decision_raw)
    check('copied_proposal_hash', sha(local['retention-proposal.json']), decision['proposal_sha256'])
    proposal = json.loads(local['retention-proposal.json'])
    projection = lambda row: (row['source_path'], row['source_sha256'], row['size_bytes'], row['proposed_repository_path'])
    proposed = [(row['original']['path'], row['original']['sha256'], row['bytes'], row['proposed_repository_path'])
                for row in proposal['files']]
    check('proposal_exact_ordered_tuples', proposed, [projection(row) for row in rows])
    check('proposal_totals', proposal['counts'], {'files': 27, 'bytes': 175124})
    sums = []
    for line in local['SHA256SUMS'].decode('ascii').splitlines():
        digest, relative = line.split('  ', 1)
        assert len(digest) == 64
        sums.append((relative, digest))
    check('sha256sums_exact_ordered_payload_mapping', sums,
          [(relative, row['source_sha256']) for relative, row in zip(expected_paths, rows)])
    copy = json.loads(local['copy-verification.json'])
    check('owner_copy_receipt_counts', [copy['files'], copy['bytes']], [27, 175124])
    check('owner_copy_receipt_proposal_binding', copy['proposal_sha256'], sha(local['retention-proposal.json']))
    check('owner_copy_receipt_decision_binding', copy['audit_decision_sha256'], DECISION_HASH)
    check('owner_copy_receipt_manifest_binding', copy['manifest_sha256'], sha(local['SHA256SUMS']))
    check('owner_reports_source_destination_equality', copy['source_and_destination_hashes_equal'])
    for key in ('originals_changed', 'sources_imported_or_executed', 'referenced_private_inputs_copied'):
        check('owner_reports_' + key, copy[key], False)
    # These flags remain owner assertions; this checker verifies destinations.
    head_before = git(coordinator, 'rev-parse', 'HEAD').stdout.decode().strip()
    commit = git(coordinator, 'rev-parse', args.snapshot_commit + '^{commit}').stdout.decode().strip()
    listing = git(coordinator, 'ls-tree', '-r', '-z', '--full-tree', commit, '--', SNAPSHOT).stdout
    entries = {}
    for entry in listing.split(b'\0'):
        if not entry:
            continue
        header, path_bytes = entry.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        relative = str(PurePosixPath(path_bytes.decode()).relative_to(SNAPSHOT))
        entries[relative] = {'mode': mode, 'type': kind, 'oid': oid}
    git_inventory_exact = set(entries) == expected_inventory
    git_members = []
    for relative in sorted(expected_inventory):
        record = entries.get(relative)
        matches = False
        digest = None
        size = None
        if record is not None and record['type'] == 'blob' and record['mode'] in ('100644', '100755'):
            data = git(coordinator, 'cat-file', 'blob', record['oid']).stdout
            digest, size = sha(data), len(data)
            matches = data == local[relative]
        git_members.append({'relative_path': relative, 'git_entry': record,
                            'object_sha256': digest, 'object_size_bytes': size,
                            'equals_local_bytes': matches})
    status = git(coordinator, 'status', '--porcelain=v1', '--untracked-files=all', '--', SNAPSHOT).stdout.decode()
    head_after = git(coordinator, 'rev-parse', 'HEAD').stdout.decode().strip()
    head_stable = head_before == head_after == commit
    git_bound = git_inventory_exact and all(item['equals_local_bytes'] for item in git_members)
    # Binding is a separate result, not an assumption needed for local copying.
    for relative in sorted(expected_inventory):
        check('destination_unchanged_during_verification:' + relative,
              regular_bytes(root / relative) == local[relative])
    report = {
        'schema_version': 'audit049-followup-copy-verification-v1',
        'status': 'verified' if all(item['passed'] for item in checks) else 'failed',
        'checks_passed': sum(item['passed'] for item in checks), 'checks_total': len(checks), 'checks': checks,
        'decision_source': {'commit': DECISION_COMMIT, 'path': DECISION_PATH, 'sha256': DECISION_HASH},
        'snapshot_relative_path': SNAPSHOT, 'payload_count': len(rows),
        'payload_bytes': sum(row['size_bytes'] for row in rows), 'metadata_count': len(METADATA),
        'metadata_bytes': sum(len(local[name]) for name in METADATA),
        'total_files': len(expected_inventory), 'total_bytes': sum(map(len, local.values())),
        'local_exact_inventory_verified': actual_files == expected_inventory and actual_dirs == {'review', 'source'} and not other_types,
        'git': {'inspected_commit': commit, 'head_before': head_before, 'head_after': head_after,
                'head_stable_and_equals_inspected_commit': head_stable, 'tree_inventory_exact': git_inventory_exact,
                'all_32_objects_equal_local': git_bound, 'current_head_binds_snapshot': git_bound and head_stable,
                'verified_snapshot_commit': commit if git_bound else None, 'scoped_status_porcelain': status,
                'members': git_members, 'remote_status': 'not_checked'},
        'inventory': sorted(inventory, key=lambda item: item['relative_path']),
        'scope_limits': ['Only the 27 exact copied destinations and five named snapshot metadata files were read.',
                         'No original/private paths or imports were followed; approved payload bodies were only hashed and byte-compared.',
                         'Owner assertions about original-file equality and immutability were checked for metadata consistency, not re-established by reading originals.',
                         'README scope was read; source semantics, secret screening, tests, dependency closure and scientific validity were not re-reviewed.',
                         'Local Git object binding does not establish remote publication. No remote query was made.',
                         'No source bodies were copied into this audit stage; this report and verifier are newly authored.'],
        'imports_or_execution_of_copied_sources': 0, 'original_source_body_reads': 0,
        'model_calls': 0, 'settings_changes': 0, 'argv': sys.argv,
        'verifier_sha256': sha(Path(__file__).read_bytes())}
    for name, value in [('report.json', report), ('git-read-commands.json', commands)]:
        with (output / name).open('x') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps({'status': report['status'], 'checks_passed': report['checks_passed'],
                      'checks_total': report['checks_total'], 'payload_count': len(rows),
                      'metadata_count': len(METADATA), 'current_head_binds_snapshot': git_bound and head_stable,
                      'verified_snapshot_commit': report['git']['verified_snapshot_commit'],
                      'report_sha256': sha((output / 'report.json').read_bytes())}, sort_keys=True))
    return 0 if report['status'] == 'verified' else 1


if __name__ == '__main__':
    sys.exit(main())
