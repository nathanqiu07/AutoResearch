#!/usr/bin/env python3
"""Verify an existing private archive and replay into fresh explicit directories.

The archive is never modified. Only approved member bytes enter the new private
replay tree; public outputs contain metadata only. No original source path is read.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile

INVENTORY_SHA = '4d90e111d4f02772246f5e9c5806fbcde45d11dd24c2c9a071f054edaac5e8ea'
READER_SHA = '84ddf25c5fa9316f1e2aeefbdd98dd6ecd6166de833ef94551a741d0880d8f05'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--archive-sha256', required=True)
    parser.add_argument('--recorded-root', type=Path)
    parser.add_argument('--replay-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    STAGE, REPO, ARCHIVE = args.stage.resolve(), args.repo.resolve(), args.archive.resolve()
    replay, output, receipt_path = args.replay_root.resolve(), args.out.resolve(), args.receipt.resolve()
    assert not replay.exists() and not output.exists() and not receipt_path.exists(), 'Outputs must be fresh; no overwrite'
    assert sha(ARCHIVE.read_bytes()) == args.archive_sha256, 'Archive byte hash mismatch'
    raw_inventory = (STAGE / 'input-inventory.json').read_bytes()
    assert sha(raw_inventory) == INVENTORY_SHA
    inventory = json.loads(raw_inventory)
    ORIGINAL = args.recorded_root or Path(inventory['coordinator_root'])
    assert ORIGINAL.is_absolute() and '..' not in ORIGINAL.parts and str(ORIGINAL) == inventory['coordinator_root']
    assert len(inventory['files']) == 695
    members = []
    for record in inventory['files']:
        source = Path(record['path'])
        relative = source.relative_to(ORIGINAL)
        assert source.is_absolute() and '..' not in relative.parts
        members.append({'member': relative.as_posix(), 'original_path': str(source),
                        'sha256': record['sha256'], 'size_bytes': record['size_bytes']})
    members.sort(key=lambda x: x['member'])
    expected = {x['member']: x for x in members}
    assert len(expected) == len(members)
    assert stat.S_IMODE(ARCHIVE.stat().st_mode) == 0o600
    assert stat.S_IMODE(ARCHIVE.parent.stat().st_mode) == 0o700
    ignored = subprocess.run(['/usr/bin/git', '-C', str(REPO), 'check-ignore', '-q', '--', str(ARCHIVE.relative_to(REPO))],
                             env={'PATH': '/usr/bin:/bin'}, capture_output=True)
    assert ignored.returncode == 0
    with tarfile.open(ARCHIVE, 'r:gz') as tar:
        rows = tar.getmembers()
        assert len(rows) == len(expected) and {row.name for row in rows} == set(expected)
        for row in rows:
            record = expected[row.name]
            assert row.isfile() and row.mode == 0o600 and row.size == record['size_bytes']
            raw = tar.extractfile(row).read()
            assert len(raw) == record['size_bytes'] and sha(raw) == record['sha256']
        replay.mkdir(parents=True, mode=0o700)
        for row in rows:
            path = replay / row.name
            path.resolve().relative_to(replay)
            path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            for parent in path.parents:
                if parent == replay.parent:
                    break
                os.chmod(parent, 0o700)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(tar.extractfile(row).read())
    assert stat.S_IMODE(replay.stat().st_mode) == 0o700
    for record in members:
        path = replay / record['member']
        path.resolve(strict=True).relative_to(replay)
        raw = path.read_bytes()
        assert len(raw) == record['size_bytes'] and sha(raw) == record['sha256']
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    reader_bytes = (STAGE / 'read_metadata.py').read_bytes()
    assert sha(reader_bytes) == READER_SHA
    command = [sys.executable, '-I', str(STAGE / 'read_metadata.py'), '--data-root', str(replay),
               '--recorded-data-root', str(ORIGINAL), '--out', str(output)]
    result = subprocess.run(command, cwd=STAGE, env={'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'stdout.txt').write_text(result.stdout)
    (output / 'stderr.txt').write_text(result.stderr)
    (output / 'reader-used.py').write_bytes(reader_bytes)
    (output / 'invocation.json').write_text(json.dumps({'argv': command, 'cwd': str(STAGE),
        'environment': {'PYTHONDONTWRITEBYTECODE': '1'}, 'exit_code': result.returncode}, indent=2, sort_keys=True) + '\n')
    assert result.returncode == 0, 'Reader failure retained in output directory'
    before = json.loads((STAGE / 'run-03/report.json').read_text())
    after = json.loads((output / 'report.json').read_text())
    invocation = json.loads((output / 'invocation.json').read_text())
    assert invocation['exit_code'] == 0 and after['check_counts'] == {'verified': 3091, 'failed': 0}
    sections = ('summary', 'batches', 'execution_summaries', 'matched_decision_hashes', 'jobs', 'embedding_accounting_reference', 'check_counts')
    comparisons = {name: before[name] == after[name] for name in sections}
    enc = lambda checks: Counter(json.dumps(row, sort_keys=True, separators=(',', ':')) for row in checks)
    comparisons['checks_multiset'] = enc(before['checks']) == enc(after['checks'])
    comparisons['reader_sha256_unchanged'] = before['reader_sha256'] == after['reader_sha256'] == sha((STAGE / 'read_metadata.py').read_bytes()) == READER_SHA
    original_files = {x['path']: (x['sha256'], x['size_bytes']) for x in before['read_files']}
    mapped_files = {str(ORIGINAL / Path(x['path']).relative_to(replay)): (x['sha256'], x['size_bytes']) for x in after['read_files']}
    comparisons['input_inventory_after_root_mapping'] = original_files == mapped_files
    assert all(comparisons.values())
    receipt = {'schema_version': 'private-control-audit-preservation-v1', 'audit': 'control-runtime-24',
               'archive_path': str(ARCHIVE), 'archive_sha256': sha(ARCHIVE.read_bytes()), 'archive_bytes': ARCHIVE.stat().st_size,
               'archive_mode': '0600', 'private_directory_mode': '0700', 'gitignored': True,
               'source_inventory_sha256': INVENTORY_SHA, 'original_data_root': str(ORIGINAL), 'private_replay_root': str(replay),
               'files': members, 'member_count': len(members), 'all_archive_members_verified': True,
               'all_extracted_files_verified': True, 'original_paths_accessed': False,
               'original_report_sha256': sha((STAGE / 'run-03/report.json').read_bytes()),
               'relocated_report_sha256': sha((output / 'report.json').read_bytes()),
               'reader_sha256': READER_SHA,
               'preservation_script_run_sha256': sha((STAGE / 'preserve-and-replay-original.py').read_bytes()),
               'corrected_preservation_script_sha256': sha((STAGE / 'preserve_and_replay.py').read_bytes()),
               'receipt_verifier_sha256': sha(Path(__file__).read_bytes()), 'replay_exit_code': invocation['exit_code'],
               'decisive_section_comparisons': comparisons, 'checks_array_order_identical': before['checks'] == after['checks'],
               'comparison_note': 'Diagnostic checks order is incidental; duplicate-preserving multiset equality is verified. Original mismatch and scripts are retained.',
               'contains_credentials': False, 'contains_private_evaluator_labels': False,
               'contents': 'Exactly the 695 approved input inventory members; raw bytes remain private. This receipt contains paths/hashes/counts/statuses only.',
               'public_packaging_exclusions': [str(ARCHIVE), str(replay)]}
    assert sha(ARCHIVE.read_bytes()) == args.archive_sha256, 'Archive changed during replay'
    with receipt_path.open('x') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'archive_sha256': receipt['archive_sha256'], 'archive_bytes': receipt['archive_bytes'],
                      'member_count': len(members), 'replay_exit_code': 0, 'checks': after['check_counts'],
                      'all_decisive_sections_match': all(comparisons.values())}, indent=2))


if __name__ == '__main__':
    main()
