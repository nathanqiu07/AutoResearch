"""Copy a hash-pinned set, making each newly needed directory private.

Additive portable variant; the original executed checkpoint copier is unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_relative(name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('Unsafe manifest path')
    return p


def make_private_parents(path):
    """Create missing directories individually; leave existing parents alone."""
    missing = []
    parent = path
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    raw_manifest = args.manifest.read_bytes()
    assert sha(raw_manifest) == args.manifest_sha256
    manifest = json.loads(raw_manifest)
    assert not args.destination.exists() and not args.receipt.exists()
    sources = []
    names = set()
    for record in manifest['files']:
        source = args.source_root / safe_relative(record['source'])
        source.resolve().relative_to(args.source_root.resolve())
        assert stat.S_ISREG(source.lstat().st_mode)
        name = safe_relative(record['destination'])
        assert str(name) not in names
        names.add(str(name))
        raw = source.read_bytes()
        assert sha(raw) == record['sha256'] and len(raw) == record['size_bytes']
        sources.append((record, source, raw))
    make_private_parents(args.destination.parent)
    args.destination.mkdir(mode=0o700)
    os.chmod(args.destination, 0o700)
    for record, source, raw in sources:
        destination = args.destination / safe_relative(record['destination'])
        make_private_parents(destination.parent)
        fd = os.open(str(destination), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(raw)
        assert sha(destination.read_bytes()) == record['sha256']
        assert sha(source.read_bytes()) == record['sha256']
        assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    copied_manifest = args.destination / 'manifest.json'
    with copied_manifest.open('xb') as output:
        output.write(raw_manifest)
    copied_manifest.chmod(0o600)
    receipt = {
        'schema_version': 'private-checkpoint-copy-v1',
        'source_commit': manifest['source_commit'],
        'manifest_sha256': args.manifest_sha256,
        'destination': str(args.destination),
        'files_copied_and_verified': len(sources),
        'bytes_copied': sum(len(raw) for _, _, raw in sources),
        'all_original_bytes_unchanged': True,
        'all_destination_files_mode': '0o600',
        'destination_directory_mode': '0o700',
        'limitations': ['Same-machine copy, not off-device backup.',
                       'Only the exact manifest inventory is retained; later audit packages require a later checkpoint.'],
    }
    receipt_bytes = (json.dumps(receipt, indent=2) + '\n').encode()
    with args.receipt.open('xb') as output:
        output.write(receipt_bytes)
    with (args.destination / 'copy-receipt.json').open('xb') as output:
        output.write(receipt_bytes)
    (args.destination / 'copy-receipt.json').chmod(0o600)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
