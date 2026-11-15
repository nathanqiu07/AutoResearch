"""Prepare only the committed039 public tree and exact private13-record archive."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile

COMMIT = 'b35c0f8f47f40b28a0aa6338fb7f626ce0db2b0f'
PACKAGE = 'results/integration-audit/20261115-039'
HANDOFF = 'docs/user-models/integration-audit/handoffs/20261115-039.json'
GAP_SHA = 'b05776948990821e627b4c902f505ad9a36fd86132b67999de2881c431faa492'
TOOLS = {
    'copy_private_checkpoint_portable.py': 'results/integration-audit/20261115-036/copy_private_checkpoint_portable.py',
    'recover_public.py': 'results/integration-audit/20261115-040/recover_public.py',
    'test_existing_extractor.py': 'results/integration-audit/20261115-040/independent-review/test_recovery_boundaries.py',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ('repo', 'private-gap', 'stage'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    os.umask(0o077)
    root = a.stage / 'copy-source'
    root.mkdir(mode=0o700)
    commands = []

    def git(args):
        argv = ['git', '--no-optional-locks', '-C', str(a.repo)] + args
        run = subprocess.run(argv, capture_output=True, env={'PATH': '/usr/bin:/bin', 'TMPDIR': '/tmp', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'})
        commands.append({'argv': argv, 'returncode': run.returncode, 'stderr_sha256': sha(run.stderr)})
        if run.returncode:
            raise ValueError('Pinned Git read failed')
        return run.stdout

    def write(name, data):
        path = root / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(data)
        path.chmod(0o600)

    tree = git(['ls-tree', '-r', '-z', COMMIT, '--', PACKAGE, HANDOFF])
    expected = {}
    for item in tree.split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, pin = metadata.split()
        if kind != b'blob' or mode not in (b'100644', b'100755'):
            raise ValueError('Nonregular committed public file')
        expected[name.decode()] = {'git_blob_sha1': pin.decode(), 'git_mode': mode.decode()}
    if len(expected) != 141 or sum(name.startswith(PACKAGE + '/') for name in expected) != 140 or HANDOFF not in expected:
        raise ValueError('Unexpected narrow Git tree membership')
    raw_tar = git(['archive', '--format=tar', COMMIT, '--', PACKAGE, HANDOFF])
    rows, payload = [], {}
    with tarfile.open(fileobj=io.BytesIO(raw_tar), mode='r:') as tar:
        if tar.pax_headers.get('comment') != COMMIT:
            raise ValueError('Git archive commit marker differs')
        for member in tar.getmembers():
            if member.isdir():
                continue
            if not member.isfile() or member.name not in expected or member.name in payload:
                raise ValueError('Unexpected public archive member')
            data = tar.extractfile(member).read()
            if blob(data) != expected[member.name]['git_blob_sha1']:
                raise ValueError('Public archive Git blob mismatch')
            payload[member.name] = data
            rows.append(dict(expected[member.name], path=member.name, sha256=sha(data), size_bytes=len(data)))
    if set(payload) != set(expected):
        raise ValueError('Missing public member')
    archive = gzip.compress(raw_tar, mtime=0)
    archive_name = 'public/audit039-b35c0f8.tar.gz'
    write(archive_name, archive)
    inventory = {'schema_version': 'audit041-public-git-inventory-v1', 'source_commit': COMMIT,
                 'git_paths': [PACKAGE, HANDOFF], 'file_count': 141, 'package_files': 140, 'handoff_files': 1,
                 'archive_destination': archive_name, 'archive_sha256': sha(archive),
                 'uncompressed_tar_sha256': sha(raw_tar), 'files': sorted(rows, key=lambda r: r['path'])}
    write('metadata/public-files.json', (json.dumps(inventory, indent=2, sort_keys=True) + '\n').encode())
    reused = []
    for name, source in TOOLS.items():
        data = git(['show', COMMIT + ':' + source])
        destination = ('tools/' if name != 'test_existing_extractor.py' else 'metadata/') + name
        write(destination, data)
        reused.append({'source_commit': COMMIT, 'source_path': source, 'destination': destination, 'sha256': sha(data), 'git_blob_sha1': blob(data), 'exact_reuse': True})
    write('metadata/reused-tools.json', (json.dumps({'files': reused}, indent=2, sort_keys=True) + '\n').encode())
    gap_path = a.private_gap
    if not stat.S_ISREG(gap_path.lstat().st_mode):
        raise ValueError('Private gap source is not a regular file')
    gap = gap_path.read_bytes()
    if len(gap) != 43236 or sha(gap) != GAP_SHA:
        raise ValueError('Private gap archive pin mismatch')
    gap_destination = 'private/downstream05-audit039-publication-gap-v1.tar.gz'
    write(gap_destination, gap)
    if gap_path.read_bytes() != gap:
        raise ValueError('Private gap source changed during capture')
    mapping = json.loads(payload[PACKAGE + '/recovery/preparation-01/recovered-input-map.json'])
    retained = [r for r in mapping['files'] if r['store'] == 'retained']
    if len(retained) != 234 or len({r['relative_path'] for r in retained}) != 210:
        raise ValueError('Owner dependency map differs')
    dependency = {'schema_version': 'audit041-explicit-dependencies-v1', 'owner_payload_not_copied_or_read': True,
                  'owner_payload_recorded_location': '/Users/giordanorogers/.local/share/autoresearch/archives/gio-matched-shutdown-05/payload',
                  'owner_payload_files': 210, 'owner_logical_references': 234,
                  'input_map_public_path': PACKAGE + '/recovery/preparation-01/recovered-input-map.json',
                  'input_map_sha256': sha(payload[PACKAGE + '/recovery/preparation-01/recovered-input-map.json']),
                  'source_archive_public_path': PACKAGE + '/recovery/runtime-source-gap.tar',
                  'source_archive_sha256': mapping['archives']['source']['archive_sha256'], 'source_archive_members': 90,
                  'private_gap_destination': gap_destination, 'private_gap_sha256': GAP_SHA, 'private_gap_members': 13,
                  'private_gap_contents_read_or_extracted': False, 'old16_private_archives_copied': False,
                  'limitations': ['Existing owner payload remains required; not a self-contained raw-data capsule.', 'No Git history, installed environment, provider availability or later judging repair recovered.']}
    write('metadata/external-dependencies.json', (json.dumps(dependency, indent=2, sort_keys=True) + '\n').encode())
    receipt = {'schema_version': 'audit041-preparation-v1', 'source_commit': COMMIT, 'commands': commands,
               'public_archive_sha256': sha(archive), 'public_archive_bytes': len(archive), 'public_files_git_blob_verified': 141,
               'private_gap_source': str(gap_path), 'private_gap_sha256_before': GAP_SHA, 'private_gap_sha256_after': sha(gap_path.read_bytes()),
               'private_gap_bytes': len(gap), 'private_gap_contents_read_or_extracted': False,
               'external_destination_created': False, 'owner_payload_read_or_copied': False,
               'reader_sha256': sha(Path(__file__).read_bytes())}
    with (a.stage / 'preparation-receipt.json').open('x') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'public_files': 141, 'public_archive_sha256': sha(archive), 'public_archive_bytes': len(archive), 'private_gap_bytes': len(gap), 'external_destination_created': False}))


if __name__ == '__main__':
    main()
