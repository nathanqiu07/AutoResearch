#!/usr/bin/env python3
"""Opaque retention of one pinned custody allowlist. No body parsing or replay.

The production CLI accepts only the versioned control hashes below. Paths are
never globbed, expanded, recursively discovered, or obtained from payload bodies.
Core functions accept small synthetic fixtures for boundary tests. They are not
an alternative production authorization mechanism.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile


PINS = {
    'allowlist': 'f403b554deefa55230486f09c31f469250cc415bf60b3dff41b2cf5e4b5420eb',
    'custody': 'b20e0ece59ca334a7b51e7072faa784f7050bc68258375e79dc2c4373e195c20',
    'reuse_receipt': '017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0',
    'reuse_archive': '28e03a21179eb9d12c9c78663027477c67adbca4ac31c16393b303e3b15583dd',
}
ARCHIVE_NAME = 'profile204-private-retention-20261115-v1.tar.gz'
HEX = re.compile(r'[0-9a-f]{64}\Z')
ROW_KEYS = {'path', 'sha256', 'roles', 'logical_size_bytes_observed'}


class BoundaryError(Exception):
    """A stable safe code, never an exception containing payload prose."""


def need(condition, code):
    if not condition:
        raise BoundaryError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_absolute(path):
    value = str(path)
    need(value.startswith('/') and value != '/', 'absolute_file_path_required')
    need(str(PurePosixPath(value)) == value, 'noncanonical_path')
    need(not any(part in ('.', '..') for part in value.split('/')), 'dot_path_component')
    need(not any(char in value for char in '*?[]\x00'), 'pattern_or_null_path')
    return value


def open_parent(path):
    """Walk only the explicit path with no-follow directory descriptors."""
    value = canonical_absolute(path)
    parts = value.split('/')[1:]
    descriptor = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                      dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, parts[-1]
    except OSError:
        os.close(descriptor)
        raise BoundaryError('unsafe_or_missing_parent') from None


def snapshot(info):
    return {'size_bytes': info.st_size, 'mode': oct(stat.S_IMODE(info.st_mode)),
            'device': info.st_dev, 'inode': info.st_ino,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def read_regular(path):
    """Opaque bytes only; prevent parent/file symlinks and blocking special files."""
    parent, name = open_parent(path)
    descriptor = None
    try:
        initial = os.stat(name, dir_fd=parent, follow_symlinks=False)
        need(stat.S_ISREG(initial.st_mode), 'source_not_regular')
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(descriptor)
        need(stat.S_ISREG(before.st_mode) and snapshot(initial) == snapshot(before),
             'source_changed_before_read')
        blocks = []
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            blocks.append(block)
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        need(snapshot(before) == snapshot(after) == snapshot(current), 'source_changed_during_read')
        data = b''.join(blocks)
        need(len(data) == after.st_size, 'source_short_read')
        return data, snapshot(after)
    except OSError:
        raise BoundaryError('source_open_or_read_failed') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def validate_rows(rows, excluded):
    need(isinstance(rows, list) and bool(rows), 'empty_or_invalid_allowlist')
    paths = set()
    sizes = {}
    for row in rows:
        need(isinstance(row, dict) and set(row) == ROW_KEYS, 'invalid_tuple_schema')
        path = canonical_absolute(row['path'])
        need(path not in paths, 'duplicate_logical_path')
        paths.add(path)
        digest, size, roles = row['sha256'], row['logical_size_bytes_observed'], row['roles']
        need(isinstance(digest, str) and bool(HEX.fullmatch(digest)), 'invalid_hash')
        need(type(size) is int and size >= 0, 'invalid_size')
        need(isinstance(roles, list) and bool(roles)
             and all(isinstance(role, str) and role for role in roles)
             and len(set(roles)) == len(roles), 'invalid_roles')
        need(digest not in sizes or sizes[digest] == size, 'inconsistent_hash_size')
        sizes[digest] = size
        name = PurePosixPath(path).name.lower()
        need(not (name == '.env' or name.startswith('.env.') or
                  name.endswith(('.sqlite', '.sqlite3', '.db', '-wal', '-shm', '.lock'))),
             'forbidden_storage_filename')
    need(isinstance(excluded, list), 'invalid_exclusions')
    excluded_paths = [canonical_absolute(row['path']) for row in excluded]
    need(len(set(excluded_paths)) == len(excluded_paths), 'duplicate_excluded_path')
    need(not paths.intersection(excluded_paths), 'excluded_path_in_allowlist')
    return {'logical_count': len(rows), 'declared_distinct_hashes': len(sizes),
            'logical_bytes': sum(row['logical_size_bytes_observed'] for row in rows),
            'declared_distinct_bytes': sum(sizes.values())}


def pack_objects(objects):
    """No source pathname is used as a new archive member pathname."""
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='wb', filename='', mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for digest in sorted(objects):
                data = objects[digest]
                need(HEX.fullmatch(digest) and sha(data) == digest, 'object_hash_mismatch')
                info = tarfile.TarInfo('objects/' + digest)
                info.size, info.mode = len(data), 0o600
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                archive.addfile(info, io.BytesIO(data))
    return compressed.getvalue()


def verify_tar(data, expected):
    """Verify exact regular relative members as bytes; never extract or parse bodies."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            need(names == sorted(expected), 'archive_inventory_mismatch')
            for member in members:
                path = PurePosixPath(member.name)
                need(not path.is_absolute() and '..' not in path.parts
                     and str(path) == member.name, 'unsafe_archive_path')
                need(member.isfile() and member.type == tarfile.REGTYPE
                     and member.mode == 0o600 and not member.pax_headers
                     and member.uid == member.gid == member.mtime == 0
                     and member.uname == member.gname == '', 'unsafe_archive_metadata')
                wanted = expected[member.name]
                need(member.size == wanted['size_bytes'], 'archive_member_size_mismatch')
                stream = archive.extractfile(member)
                need(stream is not None, 'archive_member_unreadable')
                with stream:
                    body = stream.read()
                need(len(body) == wanted['size_bytes'] and sha(body) == wanted['sha256'],
                     'archive_member_hash_mismatch')
            return names
    except (tarfile.TarError, OSError, EOFError):
        raise BoundaryError('archive_parse_failed') from None


def private_directory(path):
    # Check the directory itself through the same no-follow parent traversal.
    parent, name = open_parent(path)
    descriptor = None
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        need(stat.S_IMODE(os.fstat(descriptor).st_mode) == 0o700, 'private_directory_not_0700')
    except OSError:
        raise BoundaryError('private_directory_unsafe') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def require_absent(path):
    parent, name = open_parent(path)
    try:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise BoundaryError('destination_exists')
    finally:
        os.close(parent)


def exclusive_write(path, data):
    parent, name = open_parent(path)
    descriptor = None
    try:
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        os.fchmod(descriptor, 0o600)
        view = memoryview(data)
        while view:
            count = os.write(descriptor, view)
            need(count > 0, 'destination_short_write')
            view = view[count:]
        os.fsync(descriptor)
    except OSError:
        raise BoundaryError('exclusive_destination_write_failed') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)
    saved, info = read_regular(path)
    need(saved == data and info['mode'] == '0o600', 'destination_verification_failed')


def reuse_inputs(rows, reuse, reuse_archive):
    members = reuse.get('members')
    need(isinstance(members, list), 'invalid_reuse_receipt')
    if not members:
        need(reuse_archive is None, 'unused_reuse_archive')
        return {}, None, None
    need(reuse_archive is not None, 'missing_reuse_archive')
    data, state = read_regular(reuse_archive)
    need(state['mode'] == '0o600', 'reuse_archive_not_0600')
    need(sha(data) == reuse.get('archive_sha256'), 'reuse_archive_hash_mismatch')
    expected = {m['archive_member']: {'sha256': m['sha256'], 'size_bytes': m['size_bytes']}
                for m in members}
    need(len(expected) == len(members), 'duplicate_reuse_member')
    verify_tar(data, expected)
    aliases = {m['source_path']: m for m in members}
    need(len(aliases) == len(members), 'duplicate_reuse_source')
    by_path = {row['path']: row for row in rows}
    for path, member in aliases.items():
        need(path in by_path, 'reuse_source_not_approved')
        row = by_path[path]
        need((row['sha256'], row['logical_size_bytes_observed']) ==
             (member['sha256'], member['size_bytes']), 'reuse_tuple_mismatch')
    return aliases, data, state


def expected_mapping(rows, aliases):
    mapped = []
    for row in rows:
        item = dict(row)
        item['storage'] = 'existing_archive' if row['path'] in aliases else 'new_archive'
        item['archive_member'] = (aliases[row['path']]['archive_member'] if row['path'] in aliases
                                  else 'objects/' + row['sha256'])
        mapped.append(item)
    return mapped


def retain(rows, excluded, reuse, reuse_archive, destination):
    counts = validate_rows(rows, excluded)
    destination = Path(canonical_absolute(destination))
    private_directory(destination.parent)
    require_absent(destination)
    aliases, reuse_bytes, reuse_state = reuse_inputs(rows, reuse, reuse_archive)
    objects, source_states = {}, {}
    # Every logical source is opened independently and checked against its pin.
    # Hash equality cannot skip a source read. Byte equality precedes deduplication.
    for row in rows:
        data, state = read_regular(row['path'])
        need(len(data) == row['logical_size_bytes_observed'] and sha(data) == row['sha256'],
             'approved_source_pin_mismatch')
        source_states[row['path']] = state
        if row['path'] not in aliases:
            digest = row['sha256']
            if digest in objects:
                need(objects[digest] == data, 'equal_hash_unequal_bytes')
            else:
                objects[digest] = data
    archive_bytes = pack_objects(objects)
    expected = {'objects/' + h: {'sha256': h, 'size_bytes': len(b)} for h, b in objects.items()}
    verify_tar(archive_bytes, expected)
    private_directory(destination.parent)
    exclusive_write(destination, archive_bytes)
    copied, copied_state = read_regular(destination)
    verify_tar(copied, expected)
    need(copied == archive_bytes and copied_state['mode'] == '0o600', 'archive_copy_mismatch')
    # On a later failure the exclusive 0600 archive stays private and is not
    # represented as successful retention. The CLI writes a quarantine receipt.
    for row in rows:
        data, state = read_regular(row['path'])
        need(sha(data) == row['sha256'] and len(data) == row['logical_size_bytes_observed']
             and state == source_states[row['path']], 'original_changed_after_copy')
    if reuse_archive is not None:
        data, state = read_regular(reuse_archive)
        need(data == reuse_bytes and state == reuse_state, 'existing_archive_changed')
    private_directory(destination.parent)
    mapping = expected_mapping(rows, aliases)
    return dict(counts, schema_version='profile204-private-retention-receipt-v1',
                archive_path=str(destination), archive_sha256=sha(copied),
                archive_size_bytes=len(copied), archive_mode='0o600',
                new_member_count=len(objects), new_uncompressed_bytes=sum(map(len, objects.values())),
                new_logical_count=len(rows) - len(aliases),
                new_logical_bytes=sum(r['logical_size_bytes_observed'] for r in rows if r['path'] not in aliases),
                reused_logical_count=len(aliases), reuse_archive_sha256=reuse.get('archive_sha256'),
                reuse_archive_path=str(reuse_archive) if reuse_archive is not None else None,
                logical_inputs=mapping, source_checks_before=len(rows), source_checks_after=len(rows),
                all_sources_unchanged=True, source_states=source_states,
                all_new_member_bytes_verified=True, all_existing_member_bytes_verified=True,
                deduplication='Each logical source actual hash/size checked; same-hash new sources byte-compared before deduplication.',
                body_semantic_parsing=False, model_calls=0, scoring=False, execution_or_consumer_replay=False,
                limits=['Custody is typed permission, not a secret-free or label-free content attestation.',
                        'Opaque bodies were not decoded, semantically inspected, or followed for references.',
                        'Source before/after equality is an observed bounded copy check, not continuous filesystem custody.',
                        'The three reused snapshots require the separate existing archive.'])


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def load_pinned(path, digest):
    raw, state = read_regular(path)
    need(sha(raw) == digest, 'control_file_pin_mismatch')
    try:
        value = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise BoundaryError('invalid_control_json') from None
    return value, raw, state


def controls(args):
    saved = {}
    loaded = {}
    for name in ('allowlist', 'custody', 'reuse_receipt'):
        path = getattr(args, name)
        value, raw, state = load_pinned(path, PINS[name])
        loaded[name], saved[name] = value, (path, raw, state)
    allowed, custody, reuse = loaded['allowlist'], loaded['custody'], loaded['reuse_receipt']
    need(allowed['schema_version'] == 'profile204-private-retention-exact-allowlist-v1'
         and custody['schema_version'] == 'profile204-retention-custody-review-v1', 'wrong_control_schema')
    need(custody['exact_allowlist']['sha256'] == PINS['allowlist'], 'custody_allowlist_binding')
    need(custody['excluded'] == allowed['excluded'], 'custody_exclusions_binding')
    counts = validate_rows(allowed['allowed'], allowed['excluded'])
    need((counts['logical_count'], counts['declared_distinct_hashes'], len(allowed['excluded']))
         == (3016, 2816, 6), 'wrong_approved_counts')
    need(reuse['archive_sha256'] == PINS['reuse_archive'] and len(reuse['members']) == 3,
         'wrong_reuse_pin_or_count')
    return allowed, reuse, saved


def unchanged_controls(saved):
    for path, raw, state in saved.values():
        current, current_state = read_regular(path)
        need(current == raw and current_state == state, 'control_changed_during_operation')


def create_output(path):
    # The operator's chosen output may use the conventional /tmp alias. It never
    # controls a source input; resolve it once, then use no-follow traversal.
    path = Path(path).resolve()
    parent, name = open_parent(path)
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent)
    except OSError:
        raise BoundaryError('output_directory_exists_or_unsafe') from None
    finally:
        os.close(parent)
    private_directory(path)
    return path


def verify_saved(args, rows, reuse):
    raw, _ = read_regular(args.receipt)
    receipt = json.loads(raw)
    aliases, _, _ = reuse_inputs(rows, reuse, args.reuse_archive)
    need(receipt['logical_inputs'] == expected_mapping(rows, aliases), 'receipt_mapping_mismatch')
    need(receipt['control_pins'] == PINS, 'receipt_control_pins_mismatch')
    new_rows = [row for row in rows if row['path'] not in aliases]
    expected = {'objects/' + r['sha256']: {'sha256': r['sha256'],
                'size_bytes': r['logical_size_bytes_observed']} for r in new_rows}
    data, state = read_regular(args.archive)
    need(sha(data) == receipt['archive_sha256'] and len(data) == receipt['archive_size_bytes']
         and state['mode'] == '0o600', 'saved_archive_pin_or_mode_mismatch')
    names = verify_tar(data, expected)
    need((receipt['logical_count'], receipt['new_logical_count'], receipt['new_member_count'],
          receipt['reused_logical_count']) == (3016, 3013, 2813, 3), 'saved_receipt_count_mismatch')
    return {'status': 'verified', 'scope': 'archive-byte and exact mapping verification only; no source body reads or execution',
            'receipt_sha256': sha(raw), 'archive_sha256': sha(data), 'archive_size_bytes': len(data),
            'new_members_verified': len(names), 'logical_mappings_verified': len(rows),
            'reused_members_verified': len(aliases), 'control_pins': PINS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preserve', 'verify'))
    for name in ('allowlist', 'custody', 'reuse-receipt', 'reuse-archive', 'out'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--private-dir')
    parser.add_argument('--receipt')
    parser.add_argument('--archive')
    args = parser.parse_args()
    out, destination = None, None
    try:
        allowed, reuse, saved = controls(args)
        out = create_output(args.out)
        if args.action == 'preserve':
            need(args.private_dir is not None, 'private_directory_required')
            directory = Path(canonical_absolute(args.private_dir))
            need(directory.parts[-3:] == ('runs', 'user-model-integration-audit', 'private'),
                 'wrong_private_directory_scope')
            private_directory(directory)
            destination = directory / ARCHIVE_NAME
            relative = 'runs/user-model-integration-audit/private/' + ARCHIVE_NAME
            ignore_argv = ['git', '-C', str(directory.parent.parent.parent), 'check-ignore', '--', relative]
            ignored = subprocess.run(ignore_argv, capture_output=True)
            need(ignored.returncode == 0 and ignored.stdout.decode().strip() == relative,
                 'private_archive_not_git_ignored')
            report = retain(allowed['allowed'], allowed['excluded'], reuse, args.reuse_archive, destination)
            need((report['new_logical_count'], report['new_member_count']) == (3013, 2813),
                 'actual_remaining_counts_mismatch')
            report.update(status='verified_private_retention', control_pins=PINS,
                          git_ignore_argv=ignore_argv, git_ignore_exit_code=ignored.returncode)
        else:
            need(args.receipt is not None and args.archive is not None, 'verify_arguments_required')
            report = verify_saved(args, allowed['allowed'], reuse)
        unchanged_controls(saved)
        report.update(argv=sys.argv, reader_sha256=sha(Path(__file__).read_bytes()))
        exclusive_write(out / 'receipt.json', json_bytes(report))
        print(json.dumps({'status': report['status'], 'action': args.action,
                          'archive_sha256': report['archive_sha256'],
                          'new_members': report.get('new_member_count', report.get('new_members_verified')),
                          'receipt_sha256': sha(json_bytes(report))}, sort_keys=True))
        return 0
    except (BoundaryError, OSError, ValueError, KeyError, TypeError) as error:
        # Do not interpolate unexpected parser/provider/payload strings.
        code = str(error) if isinstance(error, BoundaryError) else type(error).__name__
        failed = {'status': 'stopped', 'reason_code': code, 'argv': sys.argv,
                  'raw_archive_if_created_is_private_and_quarantined': str(destination) if destination else None,
                  'no_success_claim': True, 'model_calls': 0}
        if out is not None:
            exclusive_write(out / 'failure.json', json_bytes(failed))
        print(json.dumps(failed, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
