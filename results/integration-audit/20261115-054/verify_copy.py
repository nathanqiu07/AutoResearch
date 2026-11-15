#!/usr/bin/env python3
"""Audit054: bounded destination/Git verification of audit052's approved copy.

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

DECISION_COMMIT = '0dbcf0536f2b0ea747e9ff7b9cfb20b4397391d5'
DECISION_PATH = 'results/integration-audit/20261115-052/decision.json'
DECISION_HASH = 'c4d72dc49b96fa27d30e1c8720c856e0b94c491f4ada7a5dfc014e0047affb7e'
SNAPSHOT_COMMIT = '32714e96d9d4102faf6298fb0291ca9834f62ecf'
RECEIPT_HASH = 'a003ac2f544fe3f1fd0c4eece64ed5057812b68fcbbca44542209e72069515c4'
SNAPSHOT = 'docs/overnight/gio-profile-20261115/control/runtime-snapshots/reviewed-ownswap-remaining98-referenceguards-20261115-v1'
METADATA = ['COPY_RECEIPT.json', 'README.md', 'SOURCE_MANIFEST.json',
            'audit-decision.json', 'source-proposal.json']


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
    if args.snapshot_commit != SNAPSHOT_COMMIT:
        raise RuntimeError('snapshot_commit_is_not_the_exact_released_pin')
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
    check('decision_schema', decision['schema_version'], 'audit052-source-publication-decision-v1')
    check('decision_status', decision['status'], 'allow_exact_source_copy_for_all_20_reviewed_files')
    check('decision_count', [len(decision['files']), decision['allowed_file_count']], [20, 20])
    check('decision_total_bytes', [sum(row['size_bytes'] for row in decision['files']), decision['allowed_bytes']], [156748, 156748])
    check('decision_no_excluded', decision['excluded_files'], [])
    check('decision_snapshot_root', decision['proposed_repository_root'], SNAPSHOT)
    rows = decision['files']
    expected_paths = []
    for row in rows:
        path = PurePosixPath(row['proposed_relative_path'])
        assert not path.is_absolute() and '..' not in path.parts
        relative = str(path)
        assert relative == row['proposed_relative_path'] and len(path.parts) == 2
        assert path.parts[0] in ('source', 'tests')
        expected_paths.append(relative)
    check('unique_destinations', len(set(expected_paths)), 20)
    check('unique_proposal_indices', sorted(row['index'] for row in rows), list(range(20)))
    check('all_decisions_allow_exact_copy', all(row['decision'] == 'allow_exact_source_copy' for row in rows))
    check('approved_directory_counts', [sum(path.startswith('source/') for path in expected_paths),
                                       sum(path.startswith('tests/') for path in expected_paths)], [9, 11])
    root = coordinator / SNAPSHOT
    expected_inventory = set(expected_paths) | set(METADATA)
    # List names/types only in the exact snapshot and its two explicit folders.
    # Never descend into an unexpected directory or open an unlisted body.
    actual_files, actual_dirs, other_types = set(), set(), []
    for folder in ('', 'source', 'tests'):
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
    check('exact_local_directory_inventory', sorted(actual_dirs), ['source', 'tests'])
    check('no_other_local_file_types', other_types, [])
    local = {}
    for row, relative in zip(rows, expected_paths):
        data = regular_bytes(root / relative)
        digest = sha(data)
        check('payload_hash:' + relative, digest, row['sha256'])
        check('payload_size:' + relative, len(data), row['size_bytes'])
        local[relative] = data
        inventory.append({'relative_path': relative, 'category': 'approved_payload',
                          'sha256': digest, 'size_bytes': len(data),
                          'approved_sha256': row['sha256'], 'approved_size_bytes': row['size_bytes']})
    for relative in METADATA:
        data = regular_bytes(root / relative)
        local[relative] = data
        inventory.append({'relative_path': relative, 'category': 'snapshot_metadata',
                          'sha256': sha(data), 'size_bytes': len(data)})
    check('copied_decision_exact_bytes', local['audit-decision.json'] == decision_raw)
    check('copied_proposal_hash', sha(local['source-proposal.json']), decision['proposal']['sha256'])
    check('copied_proposal_size', len(local['source-proposal.json']), decision['proposal']['size_bytes'])
    proposal = json.loads(local['source-proposal.json'])
    check('proposal_schema', proposal['schema_version'], 'source-only-retention-proposal-v1')
    check('proposal_snapshot_root', proposal['proposed_repository_root'], SNAPSHOT)
    projection = lambda row: (row['original_path'], row['sha256'], row['size_bytes'], row['proposed_relative_path'])
    proposed = [(row['original_path'], row['sha256'], row['bytes'], row['proposed_relative_path'])
                for row in proposal['files']]
    check('proposal_exact_ordered_tuples', proposed, [projection(row) for row in rows])
    check('proposal_totals', [proposal['file_count'], proposal['total_bytes']], [20, 156748])
    source_manifest = json.loads(local['SOURCE_MANIFEST.json'])
    check('source_manifest_schema', source_manifest['schema_version'], 'retained-source-manifest-v1')
    check('source_manifest_count', len(source_manifest['files']), 20)
    manifest_tuples = [(row['original_path'], row['sha256'], row['bytes'], row['destination'], row['role'])
                       for row in source_manifest['files']]
    proposal_with_roles = [(row['original_path'], row['sha256'], row['bytes'], row['proposed_relative_path'], row['role'])
                           for row in proposal['files']]
    check('source_manifest_exact_ordered_tuples_and_roles', manifest_tuples, proposal_with_roles)
    check('copied_receipt_hash', sha(local['COPY_RECEIPT.json']), RECEIPT_HASH)
    copy = json.loads(local['COPY_RECEIPT.json'])
    check('owner_copy_receipt_counts', [copy['payload_files'], copy['payload_bytes']], [20, 156748])
    check('owner_copy_receipt_proposal_binding', copy['proposal_sha256'], sha(local['source-proposal.json']))
    check('owner_copy_receipt_decision_binding', copy['audit_decision_sha256'], DECISION_HASH)
    check('owner_reports_source_destination_equality', copy['all_original_and_destination_hashes_match'])
    check('owner_reports_ast_parsing_without_execution', copy['all_sources_ast_parsed_without_execution'])
    for key in ('private_inputs_followed', 'source_imports_or_execution', 'scientific_outcomes_or_launch_authority_changed'):
        check('owner_reports_' + key, copy[key], False)
    check('owner_reports_zero_provider_calls', copy['provider_calls'], 0)
    # These flags remain owner assertions; this checker verifies destinations.
    head_before = git(coordinator, 'rev-parse', 'HEAD').stdout.decode().strip()
    commit = git(coordinator, 'rev-parse', args.snapshot_commit + '^{commit}').stdout.decode().strip()
    check('git_selected_commit_matches_task_pin', commit, SNAPSHOT_COMMIT)
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
    check('git_exact_snapshot_inventory', git_inventory_exact)
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
    check('git_all_objects_equal_local', all(item['equals_local_bytes'] for item in git_members))
    check('scoped_git_status_clean', status, '')
    # Git inventory/object equality and the released commit pin are required
    # checks, so local equality alone cannot produce a successful result.
    # HEAD position is reported separately: a later unrelated HEAD does not
    # change the identity of the exact released commit's immutable objects.
    for relative in sorted(expected_inventory):
        check('destination_unchanged_during_verification:' + relative,
              regular_bytes(root / relative) == local[relative])
    report = {
        'schema_version': 'audit054-source-copy-verification-v1',
        'status': 'verified' if all(item['passed'] for item in checks) else 'failed',
        'checks_passed': sum(item['passed'] for item in checks), 'checks_total': len(checks), 'checks': checks,
        'decision_source': {'commit': DECISION_COMMIT, 'path': DECISION_PATH, 'sha256': DECISION_HASH},
        'snapshot_relative_path': SNAPSHOT, 'payload_count': len(rows),
        'payload_bytes': sum(row['size_bytes'] for row in rows), 'metadata_count': len(METADATA),
        'metadata_bytes': sum(len(local[name]) for name in METADATA),
        'total_files': len(expected_inventory), 'total_bytes': sum(map(len, local.values())),
        'local_exact_inventory_verified': actual_files == expected_inventory and actual_dirs == {'source', 'tests'} and not other_types,
        'git': {'inspected_commit': commit, 'head_before': head_before, 'head_after': head_after,
                'head_stable_and_equals_inspected_commit': head_stable, 'tree_inventory_exact': git_inventory_exact,
                'all_objects_equal_local': git_bound, 'current_head_binds_snapshot': git_bound and head_stable,
                'verified_snapshot_commit': commit if git_bound else None, 'scoped_status_porcelain': status,
                'members': git_members, 'remote_status': 'not_checked'},
        'inventory': sorted(inventory, key=lambda item: item['relative_path']),
        'metadata_schemas': {'decision': decision['schema_version'], 'proposal': proposal['schema_version'],
                             'manifest': source_manifest['schema_version'], 'receipt_keys': sorted(copy)},
        'scope_limits': ['Only the 20 exact copied destinations and five named snapshot metadata files were read.',
                         'No original/private paths or imports were followed; approved payload bodies were only hashed and byte-compared.',
                         'Owner assertions about original-file equality, AST parsing, reference access and execution were checked for metadata consistency, not independently re-established.',
                         'README scope was read; source semantics, secret screening, tests, dependency closure and scientific validity were not re-reviewed.',
                         'Local Git object binding does not establish remote publication. No remote query was made.',
                         'Success requires local checks plus the exact released Git commit, complete tree/object equality and clean scoped status; HEAD position remains a separate observation.',
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
