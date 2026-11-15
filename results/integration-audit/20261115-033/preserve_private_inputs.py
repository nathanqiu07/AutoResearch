"""Preserve exactly the hash-pinned private inputs of audit 033, without scanning."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--inventory-sha256', required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--recorded-data-root', required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    raw = args.inventory.read_bytes()
    assert sha(raw) == args.inventory_sha256
    records = [r for r in json.loads(raw)['files'] if r['kind'] == 'external']
    assert len(records) == 76 and len({r['path'] for r in records}) == 76
    assert not args.receipt.exists() and not args.archive.exists()
    args.archive.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    assert (args.archive.parent.stat().st_mode & 0o777) == 0o700
    pinned = []
    for i, record in enumerate(records):
        logical = PurePosixPath(record['path'])
        assert logical.is_absolute() and '..' not in logical.parts and logical.suffix == '.json'
        relative = logical.relative_to(PurePosixPath(args.recorded_data_root))
        source = (args.data_root / relative).resolve()
        source.relative_to(args.data_root.resolve())
        content = source.read_bytes()
        assert len(content) == record['size_bytes'] and sha(content) == record['sha256']
        pinned.append((dict(record, archive_member='inputs/%03d.json' % i), source, content))
    fd = os.open(str(args.archive), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for record, _, content in pinned:
                    member = tarfile.TarInfo(record['archive_member'])
                    member.size = len(content)
                    member.mode = 0o600
                    member.mtime = 0
                    archive.addfile(member, io.BytesIO(content))
    with tarfile.open(args.archive, 'r:gz') as archive:
        members = archive.getmembers()
        assert len(members) == 76
        for member, (record, source, _) in zip(members, pinned):
            assert member.isfile() and member.name == record['archive_member']
            assert sha(archive.extractfile(member).read()) == record['sha256']
            assert sha(source.read_bytes()) == record['sha256']
    content = args.archive.read_bytes()
    receipt = {
        'schema_version': 'private-audit-preservation-v1',
        'archive_path': str(args.archive), 'archive_sha256': sha(content),
        'archive_bytes': len(content), 'mode_octal': oct(args.archive.stat().st_mode & 0o777),
        'inventory_sha256': args.inventory_sha256,
        'files': [r for r, _, _ in pinned],
        'source_bytes_rechecked_unchanged': True,
        'archive_members_rechecked': 76,
        'scope': 'Only the 76 named approved JSON inputs. No directory scan, private labels, credentials, or active ledger.',
    }
    with args.receipt.open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps({'files': 76, 'archive_sha256': receipt['archive_sha256'], 'archive_bytes': len(content)}))


if __name__ == '__main__':
    main()
