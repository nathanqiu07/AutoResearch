"""Verify narrow capsule bytes and exact public Git-blob inventory; no extraction."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(name):
    p = PurePosixPath(name)
    if not p.parts or p.is_absolute() or '..' in p.parts or str(p) != name:
        raise ValueError('Unsafe or noncanonical relative path')
    return p


def verify_public(raw, inventory):
    if sha(raw) != inventory['archive_sha256']:
        raise ValueError('Public archive pin mismatch')
    unpacked = gzip.decompress(raw)
    if sha(unpacked) != inventory['uncompressed_tar_sha256']:
        raise ValueError('Uncompressed archive pin mismatch')
    expected = {row['path']: row for row in inventory['files']}
    if len(expected) != len(inventory['files']) or len(expected) != inventory['file_count']:
        raise ValueError('Duplicate or inconsistent public inventory')
    allowed_dirs = set()
    for name in expected:
        p = safe(name)
        allowed_dirs.update(str(parent) for parent in p.parents if str(parent) != '.')
    observed, names = set(), set()
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as archive:
        for member in archive.getmembers():
            name = str(safe(member.name))
            if name in names:
                raise ValueError('Duplicate public member')
            names.add(name)
            if member.isdir():
                if name not in allowed_dirs:
                    raise ValueError('Unexpected public directory')
                continue
            if not member.isfile() or name not in expected:
                raise ValueError('Unexpected, linked or special public member')
            data = archive.extractfile(member).read()
            row = expected[name]
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if len(data) != row['size_bytes'] or sha(data) != row['sha256'] or blob != row['git_blob_sha1']:
                raise ValueError('Public member content or Git-blob mismatch')
            observed.add(name)
    if observed != set(expected):
        raise ValueError('Missing public member')
    return len(observed)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--copied', action='store_true')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    os.umask(0o077)
    before = a.manifest.read_bytes()
    if sha(before) != a.manifest_sha256:
        raise ValueError('Copy manifest pin mismatch')
    manifest = json.loads(before)
    if not stat.S_ISDIR(a.root.lstat().st_mode) or stat.S_IMODE(a.root.stat().st_mode) != 0o700:
        raise ValueError('Root must be a private regular directory')
    names, contents = set(), {}
    for record in manifest['files']:
        name = str(safe(record['destination']))
        if name in names:
            raise ValueError('Duplicate destination')
        names.add(name)
        path = a.root / name
        for parent in path.parents:
            if parent == a.root.parent:
                break
            if not stat.S_ISDIR(parent.lstat().st_mode) or stat.S_IMODE(parent.stat().st_mode) != 0o700:
                raise ValueError('Nonprivate or linked directory')
        if not stat.S_ISREG(path.lstat().st_mode) or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise ValueError('Nonprivate or linked file')
        data = path.read_bytes()
        if len(data) != record['size_bytes'] or sha(data) != record['sha256']:
            raise ValueError('Capsule file pin mismatch')
        contents[name] = data
    extras = {'manifest.json', 'copy-receipt.json'} if a.copied else set()
    actual = set()
    allowed_dirs = {str(parent) for name in names for parent in PurePosixPath(name).parents if str(parent) != '.'}
    for path in a.root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Unexpected capsule link')
        if path.is_file():
            actual.add(str(path.relative_to(a.root)))
        elif not path.is_dir() or str(path.relative_to(a.root)) not in allowed_dirs or stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise ValueError('Extra, special or nonprivate capsule directory')
    if actual != names | extras:
        raise ValueError('Extra or missing capsule file')
    if a.copied:
        if (a.root / 'manifest.json').read_bytes() != before:
            raise ValueError('Copied manifest differs')
        receipt = json.loads((a.root / 'copy-receipt.json').read_bytes())
        if receipt['manifest_sha256'] != a.manifest_sha256 or receipt['files_copied_and_verified'] != len(names):
            raise ValueError('Copy receipt differs')
        if any(stat.S_IMODE((a.root / name).stat().st_mode) != 0o600 for name in extras):
            raise ValueError('Control metadata permissions differ')
    public = [row for row in manifest['files'] if row['kind'] == 'committed_public_evidence']
    indices = [row for row in manifest['files'] if row['kind'] == 'public_blob_inventory']
    if len(public) != 1 or len(indices) != 1:
        raise ValueError('Expected one public archive and inventory')
    inventory = json.loads(contents[indices[0]['destination']])
    if inventory['source_commit'] != manifest['source_commit'] or inventory['archive_destination'] != public[0]['destination']:
        raise ValueError('Public inventory identity differs')
    count = verify_public(contents[public[0]['destination']], inventory)
    for name, data in contents.items():
        if (a.root / name).read_bytes() != data:
            raise ValueError('Input changed during verification')
    if a.manifest.read_bytes() != before:
        raise ValueError('Manifest changed during verification')
    result = {'schema_version': 'audit041-capsule-verification-v1', 'manifest_sha256': a.manifest_sha256,
              'source_commit': manifest['source_commit'], 'files_verified': len(names),
              'public_files_matched_to_retained_git_blob_inventory': count,
              'private_archives_hash_verified_only': sum(row['kind'] == 'private_archive' for row in manifest['files']),
              'copied_controls_verified': a.copied, 'permissions_verified': 'files0600_directories0700',
              'original_git_objects_required_or_opened': False, 'private_archives_extracted': False,
              'external_owner_payload_read': False, 'model_calls': 0, 'reader_sha256': sha(Path(__file__).read_bytes())}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
