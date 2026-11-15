"""Recover only the pinned public archive into a fresh private directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest_raw = (args.checkpoint / 'manifest.json').read_bytes()
    assert hashlib.sha256(manifest_raw).hexdigest() == args.manifest_sha256
    manifest = json.loads(manifest_raw)
    records = [r for r in manifest['files'] if r['kind'] == 'committed_public_evidence']
    assert len(records) == 1
    record = records[0]
    relative = PurePosixPath(record['destination'])
    assert not relative.is_absolute() and '..' not in relative.parts
    source = args.checkpoint / relative
    assert source.is_file() and not source.is_symlink()
    raw = source.read_bytes()
    assert len(raw) == record['size_bytes']
    assert hashlib.sha256(raw).hexdigest() == record['sha256']
    assert not args.out.exists() and not args.out.is_symlink()
    with tarfile.open(source, 'r:gz') as archive:
        members = archive.getmembers()
        names = set()
        for member in members:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts and path.parts
            assert member.isdir() or member.isfile()
            assert member.name not in names
            names.add(member.name)
        args.out.mkdir(mode=0o700)
        copied = []
        for member in members:
            target = args.out / member.name
            target.resolve().relative_to(args.out.resolve())
            parent = target if member.isdir() else target.parent
            pending = []
            while not parent.exists():
                pending.append(parent)
                parent = parent.parent
            for directory in reversed(pending):
                directory.mkdir(mode=0o700)
            if member.isdir():
                continue
            content = archive.extractfile(member).read()
            assert len(content) == member.size
            with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as output:
                output.write(content)
            assert target.read_bytes() == content
            copied.append(member.name)
    print(json.dumps({'source_commit': manifest['source_commit'],
                      'archive_sha256': record['sha256'],
                      'public_files_recovered': len(copied),
                      'fresh_output': True,
                      'links_or_special_files': 0,
                      'model_calls': 0}))


if __name__ == '__main__':
    main()
