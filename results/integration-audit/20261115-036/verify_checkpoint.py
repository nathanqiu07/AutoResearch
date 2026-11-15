"""Verify a copied checkpoint against its manifest and committed public tree.

No private archive extraction, original-input reads, backend imports or calls.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--git-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw = (args.checkpoint / 'manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.manifest_sha256
    manifest = json.loads(raw)
    assert not args.out.exists()
    names = set()
    for record in manifest['files']:
        relative = PurePosixPath(record['destination'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert str(relative) not in names
        names.add(str(relative))
        path = args.checkpoint / relative
        assert stat.S_ISREG(path.lstat().st_mode)
        path.resolve().relative_to(args.checkpoint.resolve())
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == record['sha256']
        assert len(content) == record['size_bytes']
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(args.checkpoint.stat().st_mode) == 0o700
    public = [r for r in manifest['files'] if r['kind'] == 'committed_public_evidence']
    assert len(public) == 1
    paths = ['results/integration-audit', 'docs/user-models/integration-audit',
             'docs/superpowers/plans/2026-11-15-user-model-integration-audit.md',
             'scripts/user_model_audit', 'tests/test_user_model_profile_audit.py',
             'tests/test_user_model_packet_audit.py']
    argv = ['git', '-C', str(args.git_root), 'ls-tree', '-r',
            manifest['source_commit'], '--'] + paths
    expected = {}
    for line in subprocess.check_output(argv).splitlines():
        metadata, name = line.split(b'\t', 1)
        mode, kind, pin = metadata.split()
        assert kind == b'blob'
        expected[name.decode()] = pin.decode()
    observed = set()
    with tarfile.open(args.checkpoint / public[0]['destination'], 'r:gz') as archive:
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            assert not name.is_absolute() and '..' not in name.parts
            assert member.isdir() or member.isfile()
            if member.isdir():
                continue
            assert member.name not in observed
            observed.add(member.name)
            content = archive.extractfile(member).read()
            git_blob = b'blob ' + str(len(content)).encode() + b'\0' + content
            assert hashlib.sha1(git_blob).hexdigest() == expected[member.name]
    assert observed == set(expected)
    report = {
        'manifest_sha256': args.manifest_sha256,
        'source_commit': manifest['source_commit'],
        'files_verified': len(names),
        'private_archives_verified': sum(r['kind'] == 'private_archive' for r in manifest['files']),
        'public_files_matched_to_git_blobs': len(expected),
        'all_destination_files_mode': '0o600',
        'checkpoint_directory_mode': '0o700',
        'private_archives_extracted': False,
        'original_input_paths_read': False,
        'model_calls': 0,
        'git_tree_argv': argv,
    }
    with args.out.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'git_tree_argv'}))


if __name__ == '__main__':
    main()
