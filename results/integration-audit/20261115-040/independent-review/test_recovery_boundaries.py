"""Synthetic subprocess tests of the pinned040 public recovery helper only."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--helper', type=Path, required=True)
    p.add_argument('--helper-sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    source = a.helper.read_bytes()
    if sha(source) != a.helper_sha256:
        raise ValueError('Helper pin mismatch')
    a.out.mkdir(mode=0o700)
    cases = []
    definitions = [
        ('valid_nested_regular', [('nested/file.txt', 'file')], True),
        ('valid_file_before_directory', [('nested/file.txt', 'file'), ('nested', 'dir')], True),
        ('reject_traversal', [('../escape.txt', 'file')], False),
        ('reject_absolute', [('/synthetic-escape.txt', 'file')], False),
        ('reject_symlink', [('link', 'symlink')], False),
        ('reject_hardlink', [('link', 'hardlink')], False),
        ('reject_fifo', [('fifo', 'fifo')], False),
        ('reject_duplicate', [('same.txt', 'file'), ('same.txt', 'file')], False),
        ('reject_existing_output', [('file.txt', 'file')], False),
        ('reject_manifest_pin', [('file.txt', 'file')], False),
        ('reject_archive_pin', [('file.txt', 'file')], False),
    ]
    for name, members, expected_success in definitions:
        with tempfile.TemporaryDirectory(prefix='synthetic040-', dir=a.out) as root:
            root = Path(root)
            checkpoint = root / 'checkpoint'
            checkpoint.mkdir(mode=0o700)
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
                for member_name, kind in members:
                    info = tarfile.TarInfo(member_name)
                    if kind == 'dir':
                        info.type = tarfile.DIRTYPE
                        tar.addfile(info)
                    elif kind == 'file':
                        data = b'synthetic public evidence\n'
                        info.size = len(data)
                        tar.addfile(info, io.BytesIO(data))
                    else:
                        info.type = {'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE, 'fifo': tarfile.FIFOTYPE}[kind]
                        if kind != 'fifo':
                            info.linkname = '../outside'
                        tar.addfile(info)
            archive = buffer.getvalue()
            (checkpoint / 'public.tar.gz').write_bytes(archive)
            manifest = {'source_commit': 'synthetic', 'files': [{'kind': 'committed_public_evidence', 'destination': 'public.tar.gz', 'size_bytes': len(archive), 'sha256': sha(archive)}]}
            if name == 'reject_archive_pin':
                manifest['files'][0]['sha256'] = '0' * 64
            raw = (json.dumps(manifest, sort_keys=True) + '\n').encode()
            (checkpoint / 'manifest.json').write_bytes(raw)
            pin = '0' * 64 if name == 'reject_manifest_pin' else sha(raw)
            output = root / 'recovered'
            sentinel = None
            if name == 'reject_existing_output':
                output.mkdir()
                sentinel = output / 'sentinel'
                sentinel.write_bytes(b'existing synthetic file')
            argv = [sys.executable, '-I', '-B', str(a.helper), '--checkpoint', str(checkpoint), '--manifest-sha256', pin, '--out', str(output)]
            result = subprocess.run(argv, capture_output=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            passed = (result.returncode == 0) == expected_success
            if expected_success:
                actual_files = [q for q in output.rglob('*') if q.is_file()]
                passed = passed and len(actual_files) == 1 and actual_files[0].read_bytes() == b'synthetic public evidence\n'
                passed = passed and all(stat.S_IMODE(q.stat().st_mode) == (0o700 if q.is_dir() else 0o600) for q in [output, *output.rglob('*')])
            elif sentinel is not None:
                passed = passed and sentinel.read_bytes() == b'existing synthetic file' and list(output.iterdir()) == [sentinel]
            else:
                passed = passed and not output.exists()
            passed = passed and not (root / 'escape.txt').exists()
            record = {'case': name, 'expected_success': expected_success, 'passed': passed,
                      'argv': argv, 'exit_code': result.returncode, 'stdout': result.stdout.decode(),
                      'stderr': result.stderr.decode(), 'archive_sha256': sha(archive), 'manifest_sha256': sha(raw),
                      'synthetic_only': True, 'temporary_case_files_removed_after_check': True}
            cases.append(record)
            if not passed:
                raise ValueError('Boundary control failed: ' + name)
    if a.helper.read_bytes() != source:
        raise ValueError('Helper changed during tests')
    report = {'schema_version': 'independent040-public-recovery-controls-v1',
              'cases': cases, 'passed': len(cases), 'failed': 0,
              'helper_sha256': a.helper_sha256, 'checker_sha256': sha(Path(__file__).read_bytes()),
              'retained_runtime_imported_or_executed': False, 'raw_checkpoint_inputs_read': False,
              'model_calls': 0, 'scope': 'Exact helper invoked with standard Python assertions enabled. Not a general concurrency/adversarial-host or optimized-Python proof.'}
    with (a.out / 'report.json').open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(cases), 'failed': 0, 'positive_cases': 2, 'negative_cases': 9}))


if __name__ == '__main__':
    main()
