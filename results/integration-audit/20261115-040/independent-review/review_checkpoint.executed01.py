"""Independent checkpoint metadata/hash review; private archives stay opaque."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile

COMMIT = 'f6ef2ee9cf9af5ad3d889412291cd213a3575432'
MANIFEST = 'ac6eb133abd7d0996812e951d7745d4da265cd3ede746ab841e4083530378320'
PUBLIC = 'f4be302b38f298637f2756eeec3d4d0a1707d2e0211290e29d08151bd9802317'
PREFIXES = ['results/integration-audit', 'docs/user-models/integration-audit',
            'docs/superpowers/plans/2026-11-15-user-model-integration-audit.md',
            'scripts/user_model_audit', 'tests/test_user_model_profile_audit.py',
            'tests/test_user_model_packet_audit.py']
BASE37 = 'results/integration-audit/20261115-037/'
BASE36 = 'results/integration-audit/20261115-036/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from dicts(child)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('package', 'source-root', 'checkpoint', 'recovered-public', 'out'):
        ap.add_argument('--' + key, type=Path, required=True)
    a = ap.parse_args()
    checks, opened, receipts = [], {}, []

    def check(name, value):
        checks.append({'name': name, 'verified': bool(value)})
        if not value:
            raise ValueError(name)

    def read(path, pin=None):
        raw = path.read_bytes()
        if pin:
            check('pin:' + str(path), sha(raw) == pin)
        opened[path] = {'sha256': sha(raw), 'bytes': len(raw)}
        return raw

    def relative(name):
        value = PurePosixPath(name)
        check('safe_path:' + name, bool(value.parts) and not value.is_absolute() and '..' not in value.parts and '\\' not in name)
        return value

    def package(name):
        return read(a.package / name)

    manifest_raw = package('copy-manifest.json')
    check('approved_manifest_pin', sha(manifest_raw) == MANIFEST)
    manifest = json.loads(manifest_raw)
    receipt_raw = package('copy-receipt.json')
    receipt = json.loads(receipt_raw)
    check('commit_and_paths', manifest['source_commit'] == COMMIT and manifest['public_git_paths'] == PREFIXES)
    check('20_entries16_private', len(manifest['files']) == 20 and sum(x['kind'] == 'private_archive' for x in manifest['files']) == manifest['private_archive_count'] == 16)
    check('total_bytes', sum(x['size_bytes'] for x in manifest['files']) == receipt['bytes_copied'] == 60591548)
    check('receipt_identity', receipt['manifest_sha256'] == MANIFEST and receipt['source_commit'] == COMMIT and receipt['files_copied_and_verified'] == 20)
    check('receipt_destination', Path(receipt['destination']).resolve() == a.checkpoint.resolve())
    check('copied_manifest_exact', read(a.checkpoint / 'manifest.json') == manifest_raw)
    check('copied_receipt_exact', read(a.checkpoint / 'copy-receipt.json') == receipt_raw)
    expected_files = {'manifest.json', 'copy-receipt.json'}
    for row in manifest['files']:
        src = a.source_root / relative(row['source'])
        dst = a.checkpoint / relative(row['destination'])
        check('unique_destination:' + row['destination'], row['destination'] not in expected_files)
        expected_files.add(row['destination'])
        check('regular_source_and_destination:' + row['destination'], stat.S_ISREG(src.lstat().st_mode) and stat.S_ISREG(dst.lstat().st_mode))
        src.resolve().relative_to(a.source_root.resolve())
        dst.resolve().relative_to(a.checkpoint.resolve())
        source = read(src, row['sha256'])
        destination = read(dst, row['sha256'])
        check('exact_copy_and_size:' + row['destination'], source == destination and len(source) == row['size_bytes'])
    actual_files, actual_dirs = set(), {'.'}
    for path in a.checkpoint.rglob('*'):
        mode = path.lstat().st_mode
        name = str(path.relative_to(a.checkpoint))
        if stat.S_ISREG(mode):
            actual_files.add(name)
            check('checkpoint_file_mode:' + name, stat.S_IMODE(mode) == 0o600)
        else:
            check('checkpoint_regular_or_directory:' + name, stat.S_ISDIR(mode))
            actual_dirs.add(name)
            check('checkpoint_dir_mode:' + name, stat.S_IMODE(mode) == 0o700)
    check('exact22_checkpoint_files', actual_files == expected_files and len(actual_files) == 22)
    check('exact_checkpoint_dirs', actual_dirs == {'.', 'private'} and stat.S_IMODE(a.checkpoint.stat().st_mode) == 0o700)
    public_row, = [x for x in manifest['files'] if x['kind'] == 'committed_public_evidence']
    check('public_archive_pin', public_row['sha256'] == PUBLIC)
    raw_public = read(a.checkpoint / public_row['destination'], PUBLIC)
    argv = ['git', '--no-optional-locks', '-C', str(a.source_root), 'ls-tree', '-rz', COMMIT, '--'] + PREFIXES
    cp = subprocess.run(argv, capture_output=True, env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'})
    check('git_tree_success', cp.returncode == 0)
    tree = {}
    for entry in cp.stdout.split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        check('regular_git_blob:' + path.decode(), kind == 'blob' and mode in ('100644', '100755'))
        tree[path.decode()] = (mode, blob)
    public_files, tar_names = {}, set()
    recovered_dirs = {a.recovered_public}
    with tarfile.open(fileobj=io.BytesIO(raw_public), mode='r:gz') as tar:
        for member in tar.getmembers():
            path = relative(member.name)
            check('unique_tar_path:' + member.name, member.name not in tar_names)
            tar_names.add(member.name)
            check('safe_tar_type:' + member.name, member.isfile() or member.isdir())
            if member.isdir():
                continue
            content = tar.extractfile(member).read()
            check('archive_git_blob:' + member.name,
                  member.name in tree and hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == tree[member.name][1])
            public_files[member.name] = content
            recovered = a.recovered_public / path
            check('recovered_public_bytes:' + member.name, stat.S_ISREG(recovered.lstat().st_mode) and recovered.read_bytes() == content and stat.S_IMODE(recovered.stat().st_mode) == 0o600)
            parent = recovered.parent
            while parent != a.recovered_public:
                recovered_dirs.add(parent)
                parent = parent.parent
    check('exact2419_public_file_scope', set(public_files) == set(tree) and len(public_files) == 2419)
    check('no038_or_later_audit_package', all(not (x.startswith('results/integration-audit/20261115-') and int(x.split('/')[2].split('-')[-1]) >= 38) for x in public_files if x.count('/') >= 3))
    check('recovered_dirs_private', all(stat.S_IMODE(p.stat().st_mode) == 0o700 and not p.is_symlink() for p in recovered_dirs))
    for helper in ('copy_private_checkpoint_portable.py', 'verify_checkpoint.py'):
        check('exact036_helper:' + helper, package(helper) == public_files[BASE36 + helper] == read(a.checkpoint / helper))
    check('new_recover_helper_not_in_sealed_checkpoint', 'recover_public.py' not in expected_files and all(not x.startswith('results/integration-audit/20261115-040/') for x in public_files))
    for row in manifest['files']:
        if row['kind'] != 'private_archive':
            continue
        raw = public_files[row['receipt']]
        if row.get('receipt_sha256'):
            check('receipt_pin:' + row['destination'], sha(raw) == row['receipt_sha256'])
        value = json.loads(raw)
        matching = [x for x in dicts(value) if row['sha256'] in (x.get('sha256'), x.get('archive_sha256')) and row['size_bytes'] in (x.get('bytes'), x.get('archive_bytes'), x.get('size_bytes'))]
        check('archive_receipt_hash_size:' + row['destination'], bool(matching))
        receipts.append({'archive': row['destination'], 'receipt': row['receipt'], 'receipt_sha256': sha(raw), 'archive_sha256': row['sha256'], 'size_bytes': row['size_bytes']})
    dispatch = json.loads(public_files['results/integration-audit/20261115-035/dispatch-binding/private-preservation.json'])
    check('two_dispatch_explicit_inventory', dispatch['input_count'] == dispatch['archive_members'] == len(dispatch['members']) == len(dispatch['inventory']['files']) == 2)
    check('inherited500_prose_preserved_and_qualified', '500' in dispatch['overlap_limit'] and '500' in package('RECOVERY.md').decode() and 'two-dispatch' in package('RECOVERY.md').decode())
    left_raw = public_files[BASE37 + 'final/report.json']
    right_raw = package('durable-037-replay/report.json')
    left, right = json.loads(left_raw), json.loads(right_raw)
    check('replay6336_passed', right['check_counts'] == {'verified': 6336, 'failed': 0} and len(right['checks']) == 6336 and all(x['verified'] for x in right['checks']))
    differences = sorted(k for k in set(left) | set(right) if left.get(k) != right.get(k))
    check('only_argv_and_check_order_differ', differences == ['argv', 'checks'])
    check('check_multiset_exact', Counter(map(canon, left['checks'])) == Counter(map(canon, right['checks'])))
    moved = [i for i, (x, y) in enumerate(zip(left['checks'], right['checks'])) if x != y]
    check('only364_known_family_moved', len(moved) == 364 and all(left['checks'][i]['name'].startswith('034_row_and_trace_hash_overlap:') and right['checks'][i]['name'].startswith('034_row_and_trace_hash_overlap:') for i in moved))
    inventory = package('durable-037-replay/input-inventory.json')
    check('inventory_byte_exact', inventory == public_files[BASE37 + 'final/input-inventory.json'])
    check('executed_reader_matches_committed_reader', package('durable-037-replay/reader-used.py') == public_files[BASE37 + 'read_full_sparse.py'] and right['reader_sha256'] == sha(public_files[BASE37 + 'read_full_sparse.py']))
    comparison = json.loads(package('durable-037-comparison.json'))
    check('saved_comparison_pins', comparison['left_report_sha256'] == sha(left_raw) and comparison['right_report_sha256'] == sha(right_raw) and comparison['left_inventory_sha256'] == comparison['right_inventory_sha256'] == sha(inventory))
    check('saved_comparison_booleans', comparison['passed'] and comparison['checks_multiset_including_multiplicity_equal'] and comparison['all_remaining_fields_and_arrays_exactly_equal'] and comparison['inventory_byte_identical'] and comparison['check_order_normalization_explicitly_enabled'])
    commands = {name: json.loads(package(name)) for name in ('public-archive.invocation.json', 'copy.invocation.json', 'public-recovery.invocation.json', 'durable-037-extraction.invocation.json', 'durable-037-replay.invocation.json', 'durable-037-comparison.invocation.json')}
    check('all_saved_commands_exit0', all(x['exit_code'] == 0 for x in commands.values()))
    check('public_command_exact_scope', commands['public-archive.invocation.json']['argv'] == ['git', 'archive', '--format=tar.gz', COMMIT] + PREFIXES)
    replay_argv = commands['durable-037-replay.invocation.json']['argv']
    check('report_argv_binding', replay_argv[3:] == right['argv'] and replay_argv[1:3] == ['-I', '-B'])
    check('archive_mode_not_original_data_mode', '--archive-root' in replay_argv and '--preservation' in replay_argv and '--data-root' not in replay_argv and '--recorded-data-root' not in replay_argv)
    extraction = commands['durable-037-extraction.invocation.json']['argv']
    check('checkpoint_private_archive_used', Path(extraction[extraction.index('--archive') + 1]).resolve() == (a.checkpoint / 'private/full-sparse-execution-20261115-v1.tar.gz').resolve())
    check('recovered_reader_used', Path(replay_argv[3]).resolve() == (a.recovered_public / BASE37 / 'read_full_sparse.py').resolve())
    preservation = json.loads(public_files[BASE37 + 'private-preservation.json'])
    logical_index = replay_argv[replay_argv.index('--index') + 1]
    check('logical_index_is_pinned_archive_mapping', len([x for x in preservation['files'] if x.get('path') == logical_index and x['sha256'] == right['index_sha256']]) == 1)
    tests = json.loads(package('repository-tests.json'))
    check('recorded_repository_suite', tests['source_commit'] == COMMIT and (tests['tests_run'], tests['tests_passed'], tests['tests_skipped'], tests['exit_code']) == (677, 675, 2, 0) and sha(package('repository-tests.log')) == tests['log_sha256'])
    for path, pin in opened.items():
        check('unchanged:' + str(path), sha(path.read_bytes()) == pin['sha256'])
    result = {'schema_version': 'independent040-checkpoint-review-v1', 'checks': checks,
              'passed': len(checks), 'failed': 0, 'source_commit': COMMIT, 'manifest_sha256': MANIFEST,
              'reader_sha256': sha(Path(__file__).read_bytes()), 'files_checked': len(expected_files),
              'private_archive_copies_hash_checked': 16, 'private_archive_bodies_parsed': 0,
              'public_archive_files_matched_to_git': len(public_files), 'receipts': receipts,
              'git_tree_invocation': {'argv': argv, 'exit_code': cp.returncode, 'stdout_sha256': sha(cp.stdout), 'stderr': cp.stderr.decode()},
              'replay_comparison': {'left_report_sha256': sha(left_raw), 'right_report_sha256': sha(right_raw), 'inventory_sha256': sha(inventory), 'moved_positions': len(moved), 'moved_family': '034_row_and_trace_hash_overlap:', 'other_fields_and_arrays_exact': True, 'multiplicity_exact': True},
              'inputs': [{'path': str(path), **pin} for path, pin in sorted(opened.items())],
              'source_mapping_note': 'The recorded index path is a logical key. Frozen helper lines32-57 resolve exact path/hash to a member under archive-root; no original-path fallback exists in archive mode.',
              'full037_reader_repeated': False, 'model_calls': 0,
              'limits': ['Same-machine byte retention, not off-device backup or full environment recovery.', 'Sixteen private archives checked as opaque bytes; member content was not reparsed.', 'Saved replay comparison independently checked; its full reader was not rerun.', 'Public scope ends at037. New recover_public.py belongs to040, outside the sealed checkpoint.', 'No historical runtime-loaded-code or authenticated provider-execution attestation.']}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'private_archive_bodies_parsed': 0, 'public_git_files': len(public_files), 'replay_moved_positions': len(moved)}))


if __name__ == '__main__':
    main()
