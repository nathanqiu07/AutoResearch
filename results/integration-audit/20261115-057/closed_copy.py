#!/usr/bin/env python3
"""One authorized opaque copy. Production authority is fixed; no recursive reads."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import re
import secrets
import stat
import sys
import tarfile

COPIER_ID = {'agent': 'gio-overnight-audit', 'chat_id': '01a1de44-b76b-7290-9753-ba528b42819e'}
ROLES = ('allowlist', 'custody_review', 'retention_map', 'proposed_tuples', 'summary', 'gaps', 'metadata_pins')
FIELDS = {'path', 'sha256', 'roles', 'logical_size_bytes_observed'}
HEX = re.compile(r'[0-9a-f]{64}\Z')
SCHEMAS = {
    'allowlist': 'closed-scaling-ownswap-private-retention-exact-allowlist-v1',
    'custody_review': 'closed-scaling-ownswap-retention-custody-review-v1',
    'retention_map': 'scaling-ownswap-first-order-retention-map-v1',
    'proposed_tuples': 'scaling-ownswap-retention-proposed-tuples-v1',
    'summary': 'scaling-ownswap-private-retention-inventory-summary-v3',
    'gaps': 'scaling-ownswap-retention-gaps-v1',
    'metadata_pins': 'scaling-ownswap-retention-metadata-pins-v1',
}
TRUE_FLAGS = ('require_copy_time_source_hash_and_size_match', 'require_exact_allowed_tuple_union',
              'require_regular_files_and_safe_paths', 'require_staged_atomic_write_and_fsync',
              'require_independent_destination_rehash_and_manifest_verification', 'no_existing_destination_overwrite')
FALSE_FLAGS = ('excluded_tuple_reads_or_copies_authorized', 'reuse_existing_archives_authorized',
               'reuse_existing_archives_only_on_verified_exact_hash_match', 'old_private_archive_metadata_transfer_authorized',
               'private_payloads_in_git', 'credentials_or_env_files', 'sqlite_wal_shm_or_live_databases',
               'raw_development_or_final_label_bundles', 'provider_cache_traversal', 'recursive_reference_following',
               'model_calls', 'source_or_scientific_edits')
CONTROL_LIMIT = 32 * 1024 * 1024


class BoundaryError(Exception):
    """Only fixed safe reason codes, never original paths or payload prose."""


def require(ok, code):
    if not ok:
        raise BoundaryError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def bad_constant(_):
        raise BoundaryError('nonfinite_json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise BoundaryError('invalid_json') from None


def canonical_path(path, source=False):
    require(isinstance(path, str) and path.startswith('/') and path != '/', 'absolute_path_required')
    parts = path.split('/')[1:]
    require(all(p and p not in ('.', '..') for p in parts), 'noncanonical_path')
    require(str(PurePosixPath(path)) == path and not any(c in path for c in '*?[]\\')
            and all(ord(c) >= 32 for c in path), 'unsafe_path')
    if source:
        names = [p.lower() for p in parts]
        forbidden = ('.sqlite', '.sqlite3', '.db', '.wal', '.shm', '.lock', '-wal', '-shm',
                     '.tar', '.tar.gz', '.tgz', '.zip', '.7z')
        require(not any(n == '.env' or n.startswith('.env.') or n.endswith(forbidden)
                        or n in ('.git', '.ssh', '.aws', 'archives', 'credentials', 'id_rsa', 'id_ed25519')
                        for n in names), 'forbidden_source_path')
    return parts


def open_dir(path, private=False):
    parts = [] if path == '/' else canonical_path(path)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        if private:
            require(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700, 'directory_not_private')
        return fd
    except BaseException:
        os.close(fd)
        raise


def state(s):
    return dict(size_bytes=s.st_size, mode=oct(stat.S_IMODE(s.st_mode)), device=s.st_dev,
                inode=s.st_ino, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)


def read_regular(path, expected_size=None, maximum=None):
    parts = canonical_path(str(path))
    parent = None
    fd = None
    try:
        parent = open_dir('/' + '/'.join(parts[:-1]) if len(parts) > 1 else '/')
        initial = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        require(stat.S_ISREG(initial.st_mode), 'not_regular')
        if expected_size is not None:
            require(initial.st_size == expected_size, 'size_mismatch')
        if maximum is not None:
            require(initial.st_size <= maximum, 'file_too_large')
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and state(before) == state(initial), 'changed_before_read')
        chunks = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            require(bool(chunk), 'short_read')
            chunks.append(chunk)
            remaining -= len(chunk)
        require(os.read(fd, 1) == b'', 'size_changed_during_read')
        after = os.fstat(fd)
        current = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        require(state(before) == state(after) == state(current), 'changed_during_read')
        return b''.join(chunks), state(after)
    except OSError:
        raise BoundaryError('unsafe_or_unreadable_file') from None
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


def tuple_identity(row, extra=False, source=True):
    require(isinstance(row, dict) and (FIELDS <= set(row) if extra else set(row) == FIELDS), 'tuple_schema')
    canonical_path(row['path'], source=source)
    h, size, roles = row['sha256'], row['logical_size_bytes_observed'], row['roles']
    require(isinstance(h, str) and HEX.fullmatch(h) is not None, 'tuple_hash')
    require(type(size) is int and size >= 0, 'tuple_size')
    require(isinstance(roles, list) and roles and all(isinstance(r, str) and r for r in roles)
            and len(set(roles)) == len(roles), 'tuple_roles')
    return row['path'], h, tuple(sorted(roles)), size


def identities(rows, extra=False, source=True):
    require(isinstance(rows, list), 'tuple_list')
    ids = [tuple_identity(r, extra, source) for r in rows]
    require(len(ids) == len(set(ids)) == len({r[0] for r in ids}), 'duplicate_tuple_or_path')
    sizes = {}
    for _, h, _, n in ids:
        require(h not in sizes or sizes[h] == n, 'inconsistent_hash_size')
        sizes[h] = n
    return set(ids)


def reference_equal(value, ref):
    return isinstance(value, dict) and value.get('path') == ref['path'] and value.get('sha256') == ref['sha256']


def validate_controls(authority, documents):
    require(authority['schema_version'] == 'root-exact-private-retention-authority-v2'
            and authority['state'] == 'authorized_exact_copy', 'authority_state')
    require(authority['named_copier'] == COPIER_ID, 'named_copier')
    require(set(authority['references']) == set(ROLES) and set(documents) == set(ROLES), 'control_union')
    require(authority['tuple_fields'] == ['path', 'sha256', 'roles', 'logical_size_bytes_observed'], 'authority_tuple_fields')
    require(authority['permissions'] == {'directories': '0700', 'files': '0600'}, 'authority_modes')
    require(all(authority.get(k) is True for k in TRUE_FLAGS)
            and all(authority.get(k) is False for k in FALSE_FLAGS), 'authority_boundary_flags')
    canonical_path(authority['destination'])
    refs = authority['references']
    for role in ROLES:
        require(set(refs[role]) == {'path', 'sha256'} and isinstance(refs[role]['sha256'], str)
                and HEX.fullmatch(refs[role]['sha256']), 'control_reference')
        canonical_path(refs[role]['path'])
        require(documents[role]['schema_version'] == SCHEMAS[role], 'control_schema')
    allowed = documents['allowlist']
    custody = documents['custody_review']
    mapped = documents['retention_map']
    proposed = documents['proposed_tuples']
    summary = documents['summary']
    require(reference_equal(allowed['source_map'], refs['retention_map'])
            and reference_equal(allowed['source_proposed_tuples'], refs['proposed_tuples'])
            and reference_equal(proposed['source_map'], refs['retention_map'])
            and reference_equal(custody['exact_allowlist'], refs['allowlist'])
            and mapped['pins_sha256'] == refs['metadata_pins']['sha256'], 'control_cross_binding')
    for field, role in [('retention-map', 'retention_map'), ('proposed-tuples', 'proposed_tuples'),
                        ('summary', 'summary'), ('gaps', 'gaps'), ('metadata-pins', 'metadata_pins')]:
        require(reference_equal(custody['source_refs'][field], refs[role]), 'custody_source_binding')
    for field, role in [('inventory', 'retention_map'), ('proposed_tuples', 'proposed_tuples'),
                        ('gap_inventory', 'gaps'), ('metadata_pins', 'metadata_pins')]:
        require(reference_equal(summary[field], refs[role]), 'summary_source_binding')
    require(allowed['raw_copy_performed'] is False and allowed['root_copy_authority_required'] is True
            and proposed['copy_authorized'] is False and proposed['raw_copy_performed'] is False
            and custody['copy_authority_granted_by_this_review'] is False
            and custody['live_ledger_access'] is False and custody['private_groundtruth_accessed'] is False
            and type(custody['model_calls']) is int and custody['model_calls'] == 0
            and type(custody['raw_copies_made']) is int and custody['raw_copies_made'] == 0, 'custody_scope')
    a = identities(allowed['allowed'])
    # Exclusions are metadata only: never opened, even when intentionally forbidden source types.
    e = identities(allowed['excluded'], extra=True, source=False)
    p = identities(proposed['proposed'], source=False)
    mrows = []
    for row in mapped['inputs']:
        require(row['observed_lstat']['kind'] == 'regular', 'map_not_regular')
        mrows.append({k: row[k] for k in ('path', 'sha256', 'roles')} |
                     {'logical_size_bytes_observed': row['observed_lstat']['size_bytes']})
    m = identities(mrows, source=False)
    require(a.isdisjoint(e) and {r[0] for r in a}.isdisjoint({r[0] for r in e})
            and a | e == p == m, 'exact_partition')
    sizes = {r[1]: r[3] for r in a}
    counts = dict(allowed=len(a), excluded=len(e), unique_objects=len(sizes),
                  logical_bytes=sum(r[3] for r in a), object_bytes=sum(sizes.values()))
    for field, key in [('allowed_logical_tuples', 'allowed'), ('excluded_logical_tuples', 'excluded'),
                       ('declared_unique_hashes', 'unique_objects'), ('declared_logical_bytes', 'logical_bytes')]:
        require(type(authority[field]) is int and authority[field] == counts[key], 'authority_counts')
    sc = custody['scope_counts']
    require(sc['allowed_tuples'] == len(a) and sc['excluded_tuples'] == len(e)
            and sc['proposed_tuples'] == len(p) and sc['allowed_declared_unique_content_hashes'] == len(sizes)
            and sc['allowed_logical_bytes_lstat'] == counts['logical_bytes'], 'custody_counts')
    require(summary['logical_path_hash_tuples'] == len(p)
            and summary['declared_unique_content_hashes'] == len({r[1] for r in p})
            and summary['logical_bytes_lstat'] == sum(r[3] for r in p), 'summary_counts')
    return counts


def load_bundle(authority_path, expected_hash):
    raw, info = read_regular(authority_path, maximum=CONTROL_LIMIT)
    require(sha(raw) == expected_hash, 'authority_pin')
    authority = strict_json(raw)
    require(set(authority['references']) == set(ROLES), 'control_union')
    raws = {'authority': raw}
    records = [('authority', str(authority_path), raw, info)]
    documents = {}
    for role in ROLES:
        ref = authority['references'][role]
        require(set(ref) == {'path', 'sha256'}, 'control_reference')
        body, info = read_regular(ref['path'], maximum=CONTROL_LIMIT)
        require(sha(body) == ref['sha256'], 'control_pin')
        raws[role] = body
        records.append((role, ref['path'], body, info))
        documents[role] = strict_json(body)
    counts = validate_controls(authority, documents)
    recheck(records)
    return dict(authority=authority, documents=documents, raw_controls=raws,
                records=records, authority_sha256=expected_hash, counts=counts)


def recheck(records):
    for _, path, original, before in records:
        raw, after = read_regular(path, expected_size=len(original))
        require(raw == original and after == before, 'control_changed')


def atomic_write(directory, name, data):
    require(isinstance(name, str) and name not in ('', '.', '..') and '/' not in name, 'unsafe_output_name')
    parent = None
    temp = None
    fd = None
    try:
        parent = open_dir(str(directory), private=True)
        temp = '.stage-' + secrets.token_hex(16)
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        os.fchmod(fd, 0o600)
        remaining = memoryview(data)
        while remaining:
            n = os.write(fd, remaining)
            require(n > 0, 'short_write')
            remaining = remaining[n:]
        os.fsync(fd)
        os.close(fd)
        fd = None
        # Atomic publish with EEXIST rejection, unlike rename/replace.
        os.link(temp, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(temp, dir_fd=parent)
        temp = None
        os.fsync(parent)
        saved, info = read_regular(str(directory) + '/' + name, expected_size=len(data))
        require(saved == data and info['mode'] == '0o600', 'destination_file_verification')
    except OSError:
        raise BoundaryError('exclusive_atomic_write_failed') from None
    finally:
        if fd is not None:
            os.close(fd)
        if temp is not None and parent is not None:
            os.unlink(temp, dir_fd=parent)
        if parent is not None:
            os.close(parent)


def make_private_directory(path):
    parts = canonical_path(path)
    parent = open_dir('/' + '/'.join(parts[:-1]) if len(parts) > 1 else '/', private=True)
    try:
        os.mkdir(parts[-1], mode=0o700, dir_fd=parent)
        os.fsync(parent)
    except OSError:
        raise BoundaryError('destination_exists_or_unsafe') from None
    finally:
        os.close(parent)
    fd = open_dir(path, private=True)
    try:
        return os.fstat(fd).st_ino, os.fstat(fd).st_dev
    finally:
        os.close(fd)


def pack_objects(objects):
    target = io.BytesIO()
    with gzip.GzipFile(fileobj=target, mode='wb', filename='', mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for h, body in sorted(objects.items()):
                require(HEX.fullmatch(h) and sha(body) == h, 'object_pin')
                member = tarfile.TarInfo('objects/' + h)
                member.size, member.mode = len(body), 0o600
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ''
                archive.addfile(member, io.BytesIO(body))
    return target.getvalue()


def verify_objects(raw, expected):
    try:
        tar_bytes = gzip.decompress(raw)
        require(len(tar_bytes) % 512 == 0, 'tar_block_length')
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r:') as archive:
            members = archive.getmembers()
            end = 0
            require(not archive.pax_headers, 'object_metadata')
            for member in members:
                require(member.offset == end and tar_bytes[end + 257:end + 263] == b'ustar\x00', 'tar_header')
                end += 512 + ((member.size + 511) // 512) * 512
            require(len(tar_bytes) - end >= 1024 and not any(tar_bytes[end:]), 'tar_trailing_data')
            require([m.name for m in members] == ['objects/' + h for h in sorted(expected)], 'object_inventory')
            for m in members:
                h = m.name.removeprefix('objects/')
                require(m.type == tarfile.REGTYPE and m.mode == 0o600 and m.uid == m.gid == m.mtime == 0
                        and m.uname == m.gname == '' and not m.pax_headers and m.linkname == '', 'object_metadata')
                require(m.size == expected[h], 'object_size')
                stream = archive.extractfile(m)
                require(stream is not None, 'object_unreadable')
                with stream:
                    body = stream.read()
                require(len(body) == expected[h] and sha(body) == h, 'object_hash')
    except (tarfile.TarError, OSError, EOFError, ValueError):
        raise BoundaryError('invalid_object_archive') from None


def tree_names(path):
    fd = open_dir(path, private=True)
    try:
        return sorted(os.listdir(fd))
    finally:
        os.close(fd)


def verify_destination(destination, authority_hash, require_completion=True):
    # Reads only this fixed destination tree. Embedded original paths remain strings.
    expected_top = ['controls', 'manifest.json', 'mapping.json', 'objects.tar.gz']
    if require_completion:
        expected_top.append('completion.json')
    require(tree_names(destination) == sorted(expected_top), 'destination_tree')
    roles = ('authority',) + ROLES
    require(tree_names(destination + '/controls') == sorted(r + '.json' for r in roles), 'destination_controls_tree')
    bodies = {}
    for name in ['controls/' + r + '.json' for r in roles] + ['mapping.json', 'objects.tar.gz', 'manifest.json'] + (['completion.json'] if require_completion else []):
        raw, info = read_regular(destination + '/' + name)
        require(info['mode'] == '0o600', 'destination_mode')
        bodies[name] = raw
    authority_raw = bodies['controls/authority.json']
    require(sha(authority_raw) == authority_hash, 'destination_authority_pin')
    authority = strict_json(authority_raw)
    docs = {}
    for role in ROLES:
        raw = bodies['controls/' + role + '.json']
        require(sha(raw) == authority['references'][role]['sha256'], 'destination_control_pin')
        docs[role] = strict_json(raw)
    counts = validate_controls(authority, docs)
    manifest = strict_json(bodies['manifest.json'])
    expected_files = sorted(set(bodies) - {'manifest.json', 'completion.json'})
    require(manifest['schema_version'] == 'closed-scaling-ownswap-private-manifest-v2'
            and manifest['authority_sha256'] == authority_hash and manifest['counts'] == counts, 'manifest_scope')
    require(manifest['files'] == [dict(path=n, sha256=sha(bodies[n]), size_bytes=len(bodies[n])) for n in expected_files], 'manifest_files')
    mapping = strict_json(bodies['mapping.json'])
    pins = {'authority': authority_hash, **{r: authority['references'][r]['sha256'] for r in ROLES}}
    require(mapping['schema_version'] == 'closed-scaling-ownswap-private-mapping-v2'
            and mapping['authority_sha256'] == authority_hash and mapping['control_pins'] == pins
            and mapping['counts'] == counts, 'mapping_scope')
    rows = docs['allowlist']['allowed']
    require(mapping['inputs'] == [dict(r, archive_member='objects/' + r['sha256']) for r in rows], 'mapping_union')
    require(mapping['source_checks_before'] == mapping['source_checks_after'] == len(rows)
            and mapping['all_sources_unchanged'] is True and mapping['controls_before_after_equal'] is True, 'mapping_state_claims')
    require(len(mapping['source_states']) == len(rows), 'mapping_states')
    for row, recorded in zip(rows, mapping['source_states']):
        require(set(recorded) == {'path', 'before', 'after'} and recorded['path'] == row['path']
                and recorded['before'] == recorded['after']
                and recorded['before']['size_bytes'] == row['logical_size_bytes_observed'], 'mapping_state_identity')
        require(set(recorded['before']) == {'size_bytes', 'mode', 'device', 'inode', 'mtime_ns', 'ctime_ns'}, 'mapping_state_fields')
    verify_objects(bodies['objects.tar.gz'], {r['sha256']: r['logical_size_bytes_observed'] for r in rows})
    if require_completion:
        completion = strict_json(bodies['completion.json'])
        require(completion['schema_version'] == 'closed-scaling-ownswap-copy-complete-v2'
                and completion['status'] == 'complete' and completion['authority_sha256'] == authority_hash
                and completion['manifest_sha256'] == sha(bodies['manifest.json']) and completion['counts'] == counts
                and completion['copier_sha256'] == mapping['copier_sha256']
                and completion['no_source_payload_parsing'] is True and completion['prior_archive_dependencies'] == 0,
                'completion_binding')
    return dict(status='verified', counts=counts, manifest_sha256=sha(bodies['manifest.json']),
                archive_sha256=sha(bodies['objects.tar.gz']))


def preserve(bundle, copier_sha256):
    require(isinstance(copier_sha256, str) and HEX.fullmatch(copier_sha256), 'copier_pin')
    authority, docs = bundle['authority'], bundle['documents']
    counts = validate_controls(authority, docs)
    recheck(bundle['records'])
    destination = authority['destination']
    rows = docs['allowlist']['allowed']
    require(all(not r['path'].startswith(destination + '/') and r['path'] != destination for r in rows), 'destination_source_overlap')
    identity = make_private_directory(destination)
    root_fd = open_dir(destination, private=True)
    def root_unchanged():
        fd = open_dir(destination, private=True)
        try:
            current = os.fstat(fd)
            require((current.st_ino, current.st_dev) == identity, 'destination_root_changed')
        finally:
            os.close(fd)
    try:
        make_private_directory(destination + '/controls')
        for role in ('authority',) + ROLES:
            atomic_write(destination + '/controls', role + '.json', bundle['raw_controls'][role])
        objects, states = {}, []
        for row in rows:
            canonical_path(row['path'], source=True)
            body, before = read_regular(row['path'], expected_size=row['logical_size_bytes_observed'])
            require(sha(body) == row['sha256'], 'source_pin')
            if row['sha256'] in objects:
                require(objects[row['sha256']] == body, 'same_hash_different_bytes')
            else:
                objects[row['sha256']] = body
            states.append(dict(path=row['path'], before=before))
        require(len(objects) == counts['unique_objects'] and sum(map(len, objects.values())) == counts['object_bytes'], 'actual_counts')
        packed = pack_objects(objects)
        verify_objects(packed, {h: len(b) for h, b in objects.items()})
        root_unchanged()
        atomic_write(destination, 'objects.tar.gz', packed)
        for row, record in zip(rows, states):
            body, after = read_regular(row['path'], expected_size=row['logical_size_bytes_observed'])
            require(sha(body) == row['sha256'] and body == objects[row['sha256']] and after == record['before'], 'source_changed')
            record['after'] = after
        recheck(bundle['records'])
        root_unchanged()
        pins = {role: sha(raw) for role, raw in bundle['raw_controls'].items()}
        mapping = dict(schema_version='closed-scaling-ownswap-private-mapping-v2',
                       authority_sha256=bundle['authority_sha256'], control_pins=pins,
                       inputs=[dict(r, archive_member='objects/' + r['sha256']) for r in rows],
                       source_states=states, counts=counts, source_checks_before=len(rows), source_checks_after=len(rows),
                       all_sources_unchanged=True, controls_before_after_equal=True, copier_sha256=copier_sha256,
                       limitations=['Opaque byte preservation; no semantic payload inspection, execution, scoring or provider claim.',
                                    'Before/after equality is bounded observation, not continuous custody.',
                                    'No prior archive dependencies; nested references remain uninterpreted.'])
        atomic_write(destination, 'mapping.json', encode(mapping))
        files = []
        for name in sorted(['controls/' + r + '.json' for r in ('authority',) + ROLES] + ['objects.tar.gz', 'mapping.json']):
            raw, info = read_regular(destination + '/' + name)
            require(info['mode'] == '0o600', 'destination_mode')
            files.append(dict(path=name, sha256=sha(raw), size_bytes=len(raw)))
        manifest = dict(schema_version='closed-scaling-ownswap-private-manifest-v2', authority_sha256=bundle['authority_sha256'], files=files, counts=counts)
        atomic_write(destination, 'manifest.json', encode(manifest))
        verified = verify_destination(destination, bundle['authority_sha256'], require_completion=False)
        root_unchanged()
        completion = dict(schema_version='closed-scaling-ownswap-copy-complete-v2', status='complete',
                          authority_sha256=bundle['authority_sha256'], manifest_sha256=verified['manifest_sha256'],
                          counts=counts, copier_sha256=copier_sha256, no_source_payload_parsing=True, prior_archive_dependencies=0)
        atomic_write(destination, 'completion.json', encode(completion))
        final = verify_destination(destination, bundle['authority_sha256'])
        root_unchanged()
        return dict(status='complete', counts=counts, manifest_sha256=final['manifest_sha256'],
                    archive_sha256=final['archive_sha256'], authority_sha256=bundle['authority_sha256'], copier_sha256=copier_sha256)
    except BaseException:
        # Only remove our own completion marker; retain incomplete private evidence.
        try:
            os.unlink('completion.json', dir_fd=root_fd)
            os.fsync(root_fd)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(root_fd)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise BoundaryError('invalid_arguments')


def main(argv=None):
    try:
        parser = SafeParser(description=__doc__)
        parser.add_argument('action', choices=('preflight', 'preserve'))
        parser.add_argument('--authority', required=True)
        parser.add_argument('--authority-sha256', required=True)
        args = parser.parse_args(argv)
        require(HEX.fullmatch(args.authority_sha256), 'authority_pin_format')
        bundle = load_bundle(args.authority, expected_hash=args.authority_sha256)
        require(bundle['authority']['named_copier'] == COPIER_ID and bundle['counts']['allowed'] == 1814
                and bundle['counts']['excluded'] == 15 and bundle['counts']['unique_objects'] == 1526
                and bundle['counts']['logical_bytes'] == 84896695, 'production_scope')
        code_raw, _ = read_regular(os.path.abspath(__file__), maximum=CONTROL_LIMIT)
        if args.action == 'preflight':
            result = dict(status='metadata_preflight_only', counts=bundle['counts'], copier_sha256=sha(code_raw), payloads_opened=0, copies_made=0)
        else:
            result = preserve(bundle, copier_sha256=sha(code_raw))
        public = {k: result[k] for k in ('status', 'counts', 'copier_sha256')}
        public.update(payloads_opened=0, copies_made=0) if args.action == 'preflight' else None
        print(json.dumps(public, sort_keys=True))
        return 0
    except BoundaryError as error:
        # BoundaryError messages in this module are fixed category literals.
        print(json.dumps({'status': 'stopped', 'reason': str(error), 'success': False}), file=sys.stderr)
        return 1
    except Exception:
        # Never reveal original paths, parser excerpts, payload text or argv.
        print(json.dumps({'status': 'stopped', 'reason': 'unexpected_io_or_metadata_failure', 'success': False}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
