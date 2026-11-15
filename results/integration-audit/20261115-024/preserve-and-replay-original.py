#!/usr/bin/env python3
"""Preserve only audit024's exact approved inventory privately, then replay it.

No model/network/project-code execution. Raw bytes go only to the private archive
and private replay tree. Public output is metadata, hashes, counts and statuses.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile

INVENTORY_SHA = '4d90e111d4f02772246f5e9c5806fbcde45d11dd24c2c9a071f054edaac5e8ea'
READER_SHA = '84ddf25c5fa9316f1e2aeefbdd98dd6ecd6166de833ef94551a741d0880d8f05'
ORIGINAL_ROOT = Path('/private/tmp/gio-profile-20261115-coordinator')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    stage, repo, archive = args.stage.resolve(), args.repo.resolve(), args.archive.resolve()
    inventory_path = stage / 'input-inventory.json'
    raw_inventory = inventory_path.read_bytes()
    assert sha(raw_inventory) == INVENTORY_SHA, 'Inventory changed; stop before raw-file access'
    inventory = json.loads(raw_inventory)
    assert inventory['coordinator_root'] == str(ORIGINAL_ROOT)
    reader_path = stage / 'read_metadata.py'
    reader_bytes = reader_path.read_bytes()
    assert sha(reader_bytes) == READER_SHA, 'Reader changed; stop before preservation'
    original_report = json.loads((stage / 'run-03/report.json').read_text())
    assert original_report['reader_sha256'] == READER_SHA
    assert len(inventory['files']) == 695
    relative_archive = archive.relative_to(repo)
    assert str(relative_archive) == 'runs/user-model-integration-audit/private/control-20261115-v2.tar.gz'
    ignored = subprocess.run(['/usr/bin/git', '-C', str(repo), 'check-ignore', '-q', '--', str(relative_archive)],
                             env={'PATH': '/usr/bin:/bin'}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert ignored.returncode == 0, 'Archive destination is not ignored by Git'
    assert not archive.exists(), 'Refusing to replace an existing archive'
    replay = stage / 'private-replay'
    assert not replay.exists(), 'Refusing to replace an existing private replay tree'
    assert not (stage / 'run-04-relocated').exists(), 'Refusing to replace replay output'
    assert not (stage / 'private-preservation.json').exists(), 'Refusing to replace preservation receipt'

    # Validate the complete exact allowlist before creating any raw copy.
    payloads, members = {}, []
    for record in inventory['files']:
        source = Path(record['path'])
        assert source == source.resolve(strict=True), 'Original path unexpectedly resolves elsewhere'
        relative = source.relative_to(ORIGINAL_ROOT)
        assert not relative.is_absolute() and '..' not in relative.parts and relative.suffix == '.json'
        assert not any(x in relative.name.lower() for x in ('env', 'secret', 'label', 'key'))
        name = relative.as_posix()
        assert name not in payloads, 'Duplicate inventory member'
        raw = source.read_bytes()
        assert len(raw) == record['size_bytes'] and sha(raw) == record['sha256'], 'Approved source hash/size changed'
        payloads[name] = raw
        members.append({'member': name, 'original_path': str(source), 'sha256': record['sha256'], 'size_bytes': len(raw)})
    members.sort(key=lambda x: x['member'])

    archive.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(archive.parent, 0o700)
    descriptor = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as tar:
                for record in members:
                    info = tarfile.TarInfo(record['member'])
                    info.size = record['size_bytes']
                    info.mode, info.mtime, info.uid, info.gid = 0o600, 0, 0, 0
                    info.uname = info.gname = ''
                    tar.addfile(info, io.BytesIO(payloads[record['member']]))
        stream.flush()
        os.fsync(stream.fileno())
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    assert stat.S_IMODE(archive.parent.stat().st_mode) == 0o700
    del payloads

    # Verify all archive members before safe manual extraction. No extractall,
    # links, paths outside the replay root, or inherited source permissions.
    expected = {x['member']: x for x in members}
    with tarfile.open(archive, mode='r:gz') as tar:
        entries = tar.getmembers()
        assert len(entries) == len(expected) and {x.name for x in entries} == set(expected)
        for member in entries:
            record = expected[member.name]
            assert member.isfile() and member.mode == 0o600 and member.size == record['size_bytes']
            raw = tar.extractfile(member).read()
            assert len(raw) == record['size_bytes'] and sha(raw) == record['sha256'], 'Archive member hash mismatch'
        replay.mkdir(mode=0o700)
        for member in entries:
            destination = replay / member.name
            destination.resolve().relative_to(replay.resolve())
            destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            for parent in destination.parents:
                if parent == stage:
                    break
                os.chmod(parent, 0o700)
            raw = tar.extractfile(member).read()
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(raw)
    for record in members:
        path = replay / record['member']
        assert path.stat().st_size == record['size_bytes'] and sha(path.read_bytes()) == record['sha256']
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    output = stage / 'run-04-relocated'
    command = [sys.executable, '-I', str(reader_path), '--data-root', str(replay),
               '--recorded-data-root', str(ORIGINAL_ROOT), '--out', str(output)]
    result = subprocess.run(command, cwd=stage, env={'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'stdout.txt').write_text(result.stdout)
    (output / 'stderr.txt').write_text(result.stderr)
    (output / 'reader-used.py').write_bytes(reader_bytes)
    write_new(output / 'invocation.json', {'argv': command, 'cwd': str(stage),
               'environment': {'PYTHONDONTWRITEBYTECODE': '1'}, 'exit_code': result.returncode})
    assert result.returncode == 0, 'Relocated metadata reader failed; exact stderr is retained'
    final = json.loads((output / 'report.json').read_text())
    comparisons = {section: final[section] == original_report[section] for section in (
        'summary', 'batches', 'execution_summaries', 'matched_decision_hashes', 'jobs',
        'embedding_accounting_reference', 'check_counts', 'checks')}
    original_inputs = {x['path']: (x['sha256'], x['size_bytes']) for x in original_report['read_files']}
    mapped_inputs = {str(ORIGINAL_ROOT / Path(x['path']).relative_to(replay)): (x['sha256'], x['size_bytes']) for x in final['read_files']}
    comparisons['input_inventory_after_root_mapping'] = original_inputs == mapped_inputs
    comparisons['reader_sha256_unchanged'] = final['reader_sha256'] == original_report['reader_sha256'] == sha(reader_path.read_bytes()) == READER_SHA
    assert all(comparisons.values()), 'Relocated decisive metadata differs; reports are retained'
    for record in members:
        raw = Path(record['original_path']).read_bytes()
        assert len(raw) == record['size_bytes'] and sha(raw) == record['sha256'], 'Original changed during preservation'
    receipt = {'schema_version': 'private-control-audit-preservation-v1', 'audit': 'control-runtime-24',
               'archive_path': str(archive), 'archive_sha256': sha(archive.read_bytes()), 'archive_bytes': archive.stat().st_size,
               'archive_mode': '0600', 'private_directory_mode': '0700', 'gitignored': True,
               'source_inventory_sha256': INVENTORY_SHA, 'original_data_root': str(ORIGINAL_ROOT),
               'private_replay_root': str(replay), 'files': members, 'member_count': len(members),
               'all_archive_members_verified': True, 'all_extracted_files_verified': True, 'all_originals_unchanged': True,
               'original_report_sha256': sha((stage / 'run-03/report.json').read_bytes()),
               'relocated_report_sha256': sha((output / 'report.json').read_bytes()),
               'reader_sha256': READER_SHA, 'preservation_script_sha256': sha(Path(__file__).read_bytes()),
               'replay_exit_code': result.returncode, 'decisive_section_comparisons': comparisons,
               'contains_credentials': False, 'contains_private_evaluator_labels': False,
               'contents': 'Exactly 695 approved audit024 inputs. Raw data is private; this receipt contains only hashes, paths, counts and statuses.',
               'public_packaging_exclusions': [str(archive), str(replay)]}
    write_new(stage / 'private-preservation.json', receipt)
    print(json.dumps({'archive_sha256': receipt['archive_sha256'], 'archive_bytes': receipt['archive_bytes'],
                      'member_count': len(members), 'replay_exit_code': result.returncode,
                      'check_counts': final['check_counts'], 'all_decisive_sections_match': all(comparisons.values())}, indent=2))


if __name__ == '__main__':
    main()
