"""Independently verify narrow041 Git bytes and hash-only private gap copy."""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile

COMMIT = 'b35c0f8f47f40b28a0aa6338fb7f626ce0db2b0f'
PACKAGE = 'results/integration-audit/20261115-039'
HANDOFF = 'docs/user-models/integration-audit/handoffs/20261115-039.json'
PINS = {
    'copy-source/metadata/public-files.json': '8c3f71e9fb5e7bc1ee5f9d6527766653f7eede3192cf3e1ec37f3a83b33e9145',
    'copy-source/metadata/external-dependencies.json': '140423bec54c3981de54f3ca2c5aba98012bc8aad222ea35b76cc33367f2fc4f',
    'copy-source/metadata/reused-tools.json': '3420189cb6ac8c39021cf1688159bad8391388c5b3790e82d8ac029c366d9785',
    'copy-source/public/audit039-b35c0f8.tar.gz': '5f3fbf155da75bc0845b726ddbd7bba6cb45f5e4ca0579d5abf26684cfdbaafd',
    'verify_capsule.py': '7e82584d4834cccb79e1dc4967e465ca58d2d72aa6334ae4426fab47805355ba',
}
GAP = 'b05776948990821e627b4c902f505ad9a36fd86132b67999de2881c431faa492'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'git-root', 'private-gap', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    checks, inputs, commands = [], {}, []

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    def read(path, pin=None):
        data = path.read_bytes()
        if pin:
            check('pin:' + str(path), sha(data) == pin)
        inputs[path] = {'sha256': sha(data), 'size_bytes': len(data)}
        return data

    def git(args):
        argv = ['git', '--no-optional-locks', '-C', str(a.git_root)] + args
        cp = subprocess.run(argv, capture_output=True, env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'})
        check('git_success:' + args[0], cp.returncode == 0)
        commands.append({'argv': argv, 'exit_code': cp.returncode, 'stdout_sha256': sha(cp.stdout), 'stderr_sha256': sha(cp.stderr)})
        return cp.stdout

    raw = {n: read(a.stage / n, pin) for n, pin in PINS.items()}
    inventory = json.loads(raw['copy-source/metadata/public-files.json'])
    dependencies = json.loads(raw['copy-source/metadata/external-dependencies.json'])
    reused = json.loads(raw['copy-source/metadata/reused-tools.json'])
    expected = {r['path']: r for r in inventory['files']}
    check('exact_public_inventory_scope', inventory['source_commit'] == COMMIT and inventory['git_paths'] == [PACKAGE, HANDOFF] and len(expected) == len(inventory['files']) == inventory['file_count'] == 141 and sum(n.startswith(PACKAGE + '/') for n in expected) == 140 and HANDOFF in expected)
    tree = {}
    for entry in git(['ls-tree', '-rz', COMMIT, '--', PACKAGE, HANDOFF]).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, pin = metadata.decode().split()
        check('git_regular_blob:' + name.decode(), kind == 'blob' and mode in ('100644', '100755'))
        tree[name.decode()] = (mode, pin)
    check('retained_inventory_matches_actual_git_scope', set(expected) == set(tree))
    for name, row in expected.items():
        check('actual_git_identity:' + name, (row['git_mode'], row['git_blob_sha1']) == tree[name])
    archive = raw['copy-source/public/audit039-b35c0f8.tar.gz']
    unpacked = gzip.decompress(archive)
    check('archive_inventory_pins', sha(archive) == inventory['archive_sha256'] and sha(unpacked) == inventory['uncompressed_tar_sha256'])
    allowed_dirs = {str(p) for name in expected for p in PurePosixPath(name).parents if str(p) != '.'}
    payload, names = {}, set()
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as tar:
        check('git_archive_commit_marker', tar.pax_headers.get('comment') == COMMIT)
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            check('safe_unique_public_member:' + member.name, not path.is_absolute() and '..' not in path.parts and str(path) == member.name and member.name not in names)
            names.add(member.name)
            if member.isdir():
                check('expected_parent_directory:' + member.name, member.name in allowed_dirs)
                continue
            check('regular_exact_public_file:' + member.name, member.isfile() and member.name in expected)
            data = tar.extractfile(member).read()
            row = expected[member.name]
            check('public_bytes_match_git_and_inventory:' + member.name, sha(data) == row['sha256'] and len(data) == row['size_bytes'] and blob(data) == tree[member.name][1])
            payload[member.name] = data
    check('all141_public_files_present', set(payload) == set(expected))
    for row in reused['files']:
        data = read(a.stage / 'copy-source' / row['destination'], row['sha256'])
        original = git(['cat-file', 'blob', COMMIT + ':' + row['source_path']])
        check('exact_reused_tool:' + row['destination'], data == original and blob(data) == row['git_blob_sha1'] and row['source_commit'] == COMMIT and row['exact_reuse'] is True)
    check('exact_three_reused_tools', {r['source_path'] for r in reused['files']} == {'results/integration-audit/20261115-036/copy_private_checkpoint_portable.py', 'results/integration-audit/20261115-040/recover_public.py', 'results/integration-audit/20261115-040/independent-review/test_recovery_boundaries.py'})
    gap_copy = a.stage / 'copy-source' / dependencies['private_gap_destination']
    gap = read(a.private_gap, GAP)
    check('exact43236_private_gap_copy', read(gap_copy, GAP) == gap and len(gap) == 43236)
    check('gap_regular_private_modes', all(stat.S_ISREG(p.lstat().st_mode) and stat.S_IMODE(p.stat().st_mode) == 0o600 for p in (a.private_gap, gap_copy)) and stat.S_IMODE(gap_copy.parent.stat().st_mode) == stat.S_IMODE(a.private_gap.parent.stat().st_mode) == 0o700)
    mapping_bytes = payload[dependencies['input_map_public_path']]
    check('exact_recovery_map_pin', sha(mapping_bytes) == dependencies['input_map_sha256'] == '1c4cad7f68896c5dd9afc2b88bdf9f509d005a2343df395a1647a88964996dd3')
    mapping = json.loads(mapping_bytes)
    retained = [r for r in mapping['files'] if r['store'] == 'retained']
    check('owner_dependency_234_refs210_files', len(retained) == dependencies['owner_logical_references'] == 234 and len({r['relative_path'] for r in retained}) == dependencies['owner_payload_files'] == 210)
    check('90_source13_private_dependency', Counter(r['store'] for r in mapping['files']) == {'retained': 234, 'source': 90, 'publication': 13} and mapping['archives']['publication']['archive_sha256'] == dependencies['private_gap_sha256'] == GAP and sha(payload[dependencies['source_archive_public_path']]) == dependencies['source_archive_sha256'] == mapping['archives']['source']['archive_sha256'])
    check('dependency_limits_explicit', dependencies['owner_payload_not_copied_or_read'] is True and dependencies['old16_private_archives_copied'] is False and dependencies['private_gap_contents_read_or_extracted'] is False)
    for path, pin in inputs.items():
        check('unchanged:' + str(path), sha(path.read_bytes()) == pin['sha256'])
    result = {'schema_version': 'independent041-preparation-review-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
              'source_commit': COMMIT, 'public_files_git_blob_verified': 141, 'private_gap_hash_only_bytes': 43236,
              'reused_tools_git_objects': 3, 'owner_payload_read': False, 'private_archive_contents_parsed': False, 'model_calls': 0,
              'inputs': [{'path': str(p), **v} for p, v in sorted(inputs.items())], 'git_commands': commands,
              'reader_sha256': sha(Path(__file__).read_bytes()),
              'limits': ['Preparation evidence only; external copied destination and root replay will be checked separately after final pins.', 'Existing owner210 payload dependency remains; this is not self-contained raw-data or environment retention.']}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'actual_git_files': 141, 'private_gap_bytes_hash_only': 43236}))


if __name__ == '__main__':
    main()
