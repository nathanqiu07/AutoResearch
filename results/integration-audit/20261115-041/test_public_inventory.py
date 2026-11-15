"""Synthetic controls for strict public archive inventory checks."""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verifier', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    os.umask(0o077)
    spec = importlib.util.spec_from_file_location('capsule_verifier', a.verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = b'synthetic retained public evidence\n'
    pin = hashlib.sha256(payload).hexdigest()
    blob = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    cases = []
    definitions = [('valid', [('nested/file.txt', 'file')], True),
                   ('traversal', [('../escape', 'file')], False),
                   ('absolute', [('/escape', 'file')], False),
                   ('symlink', [('nested/file.txt', 'symlink')], False),
                   ('hardlink', [('nested/file.txt', 'hardlink')], False),
                   ('extra', [('nested/file.txt', 'file'), ('extra', 'file')], False),
                   ('missing', [], False),
                   ('duplicate', [('nested/file.txt', 'file'), ('nested/file.txt', 'file')], False),
                   ('member_hash', [('nested/file.txt', 'file')], False),
                   ('archive_hash', [('nested/file.txt', 'file')], False)]
    for name, members, success in definitions:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as tar:
            for member, kind in members:
                info = tarfile.TarInfo(member)
                if kind == 'file':
                    info.size = len(payload)
                    tar.addfile(info, io.BytesIO(payload))
                else:
                    info.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                    info.linkname = '../outside'
                    tar.addfile(info)
        raw_tar = stream.getvalue()
        raw = gzip.compress(raw_tar, mtime=0)
        inventory = {'archive_sha256': hashlib.sha256(raw).hexdigest(), 'uncompressed_tar_sha256': hashlib.sha256(raw_tar).hexdigest(),
                     'file_count': 1, 'files': [{'path': 'nested/file.txt', 'sha256': pin, 'size_bytes': len(payload), 'git_blob_sha1': blob}]}
        if name == 'member_hash':
            inventory['files'][0]['sha256'] = '0' * 64
        if name == 'archive_hash':
            inventory['archive_sha256'] = '0' * 64
        error = None
        try:
            count = module.verify_public(raw, inventory)
            actual = count == 1
        except ValueError as exc:
            actual = False
            error = str(exc)
        passed = actual == success
        cases.append({'case': name, 'expected_success': success, 'passed': passed, 'error': error})
        if not passed:
            raise ValueError('Synthetic control failed: ' + name)
    with a.out.open('x') as f:
        json.dump({'schema_version': 'audit041-inventory-controls-v1', 'passed': len(cases), 'failed': 0, 'cases': cases,
                   'verifier_sha256': hashlib.sha256(a.verifier.read_bytes()).hexdigest(),
                   'synthetic_only': True, 'archive_files_extracted': False, 'model_calls': 0}, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(cases), 'failed': 0}))


if __name__ == '__main__':
    main()
