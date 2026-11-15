"""Synthetic whole-capsule inventory and permission controls; no raw inputs."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

PIN = '7e82584d4834cccb79e1dc4967e465ca58d2d72aa6334ae4426fab47805355ba'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verifier', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if sha(a.verifier.read_bytes()) != PIN:
        raise ValueError('Verifier hash mismatch')
    a.out.mkdir(mode=0o700)
    cases = []
    for name in ('valid', 'extra_file', 'extra_directory', 'file_mode', 'directory_mode', 'symlink_file', 'copied_manifest', 'receipt_pin'):
        with tempfile.TemporaryDirectory(prefix='synthetic041-', dir=a.out) as temp:
            base = Path(temp)
            root = base / 'capsule'
            root.mkdir(mode=0o700)
            (root / 'public').mkdir(mode=0o700)
            (root / 'metadata').mkdir(mode=0o700)
            content = b'synthetic public source\n'
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode='w') as tar:
                member = tarfile.TarInfo('nested/file.txt')
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
            plain = buf.getvalue()
            archive = gzip.compress(plain, mtime=0)
            inventory = {'source_commit': 'synthetic', 'archive_destination': 'public/synthetic.tar.gz',
                         'archive_sha256': sha(archive), 'uncompressed_tar_sha256': sha(plain), 'file_count': 1,
                         'files': [{'path': 'nested/file.txt', 'sha256': sha(content), 'size_bytes': len(content),
                                    'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()}]}
            metadata = (json.dumps(inventory) + '\n').encode()
            records = []
            for path, data, kind in [('public/synthetic.tar.gz', archive, 'committed_public_evidence'), ('metadata/public-files.json', metadata, 'public_blob_inventory')]:
                target = root / path
                target.write_bytes(data)
                target.chmod(0o600)
                records.append({'source': path, 'destination': path, 'sha256': sha(data), 'size_bytes': len(data), 'kind': kind})
            manifest = (json.dumps({'source_commit': 'synthetic', 'files': records}) + '\n').encode()
            external_manifest = base / 'manifest.json'
            external_manifest.write_bytes(manifest)
            copied = root / 'manifest.json'
            copied.write_bytes(manifest)
            copied.chmod(0o600)
            receipt = root / 'copy-receipt.json'
            receipt.write_text(json.dumps({'manifest_sha256': sha(manifest), 'files_copied_and_verified': 2}))
            receipt.chmod(0o600)
            if name == 'extra_file':
                (root / 'extra.txt').write_bytes(b'synthetic')
            elif name == 'extra_directory':
                (root / 'extra').mkdir(mode=0o700)
            elif name == 'file_mode':
                (root / 'public/synthetic.tar.gz').chmod(0o644)
            elif name == 'directory_mode':
                (root / 'public').chmod(0o755)
            elif name == 'symlink_file':
                outside = base / 'outside.tar.gz'
                outside.write_bytes(archive)
                (root / 'public/synthetic.tar.gz').unlink()
                (root / 'public/synthetic.tar.gz').symlink_to(outside)
            elif name == 'copied_manifest':
                copied.write_bytes(b'changed synthetic metadata')
            elif name == 'receipt_pin':
                receipt.write_text(json.dumps({'manifest_sha256': '0' * 64, 'files_copied_and_verified': 2}))
            output = base / 'verification.json'
            argv = [sys.executable, '-I', '-B', str(a.verifier), '--root', str(root), '--manifest', str(external_manifest), '--manifest-sha256', sha(manifest), '--copied', '--out', str(output)]
            cp = subprocess.run(argv, capture_output=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            passed = (cp.returncode == 0) == (name == 'valid') and output.exists() == (name == 'valid')
            cases.append({'case': name, 'passed': passed, 'expected_success': name == 'valid', 'argv': argv,
                          'exit_code': cp.returncode, 'stdout': cp.stdout.decode(), 'stderr': cp.stderr.decode()})
            if not passed:
                raise ValueError('Synthetic capsule control failed: ' + name)
    report = {'schema_version': 'independent041-capsule-controls-v1', 'passed': len(cases), 'failed': 0,
              'verifier_sha256': PIN, 'cases': cases, 'temporary_synthetic_files_removed': True,
              'private_gap_or_owner_payload_read': False, 'full039_reader_rerun': False, 'model_calls': 0,
              'test_sha256': sha(Path(__file__).read_bytes())}
    with (a.out / 'report.json').open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(cases), 'failed': 0, 'positive': 1, 'negative': 7}))


if __name__ == '__main__':
    main()
