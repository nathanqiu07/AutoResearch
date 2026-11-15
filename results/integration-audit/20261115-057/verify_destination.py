"""Read only one copied v2 destination. Never dereference logical source paths."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import re
import stat
import tarfile

ROLES = ('allowlist', 'custody_review', 'retention_map', 'proposed_tuples',
         'summary', 'gaps', 'metadata_pins')
CONTROL_NAMES = tuple('controls/' + x + '.json' for x in ('authority',) + ROLES)
MANIFEST_NAMES = set(CONTROL_NAMES) | {'mapping.json', 'objects.tar.gz'}
HEX = re.compile(r'[0-9a-f]{64}\Z')
TUPLE_FIELDS = ('path', 'sha256', 'roles', 'logical_size_bytes_observed')
CODE_ID = 'independent-destination-verifier-v2'


class VerificationError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise VerificationError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def bad_constant(_):
        raise VerificationError('nonfinite_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)


def fingerprint(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mode, s.st_mtime_ns, s.st_ctime_ns)


class Tree:
    """Fixed descriptor-relative reads; no path from metadata is opened."""
    def __init__(self, root):
        self.root = str(root)
        self.fd = self.controls = None
        require(self.root.startswith('/') and str(PurePosixPath(self.root)) == self.root
                and '..' not in PurePosixPath(self.root).parts, 'unsafe_root')
        current = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in PurePosixPath(self.root).parts[1:]:
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
                os.close(current)
                current = next_fd
            self.fd = current
            require(stat.S_IMODE(os.fstat(current).st_mode) == 0o700, 'directory_mode')
            require(set(os.listdir(current)) == {'controls', 'objects.tar.gz', 'mapping.json',
                                                 'manifest.json', 'completion.json'}, 'tree_inventory')
            s = os.stat('controls', dir_fd=current, follow_symlinks=False)
            require(stat.S_ISDIR(s.st_mode), 'unsafe_directory')
            require(stat.S_IMODE(s.st_mode) == 0o700, 'directory_mode')
            self.controls = os.open('controls', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            require(set(os.listdir(self.controls)) == {r + '.json' for r in ('authority',) + ROLES}, 'tree_inventory')
        except VerificationError:
            self.close()
            raise
        except OSError:
            if self.fd is None:
                os.close(current)
            self.close()
            raise VerificationError('unsafe_root') from None

    def close(self):
        if self.controls is not None:
            os.close(self.controls)
            self.controls = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def read(self, relative, limit=64 * 1024 * 1024):
        require(relative in MANIFEST_NAMES | {'manifest.json', 'completion.json'}, 'fixed_read_boundary')
        directory = self.controls if relative.startswith('controls/') else self.fd
        name = relative.rsplit('/', 1)[-1]
        before = os.stat(name, dir_fd=directory, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'nonregular_file')
        require(stat.S_IMODE(before.st_mode) == 0o600, 'file_mode')
        require(before.st_size <= limit, 'file_size_limit')
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        try:
            require(fingerprint(before) == fingerprint(os.fstat(fd)), 'file_changed')
            with os.fdopen(fd, 'rb', closefd=False) as handle:
                raw = handle.read(limit + 1)
            require(len(raw) == before.st_size and fingerprint(before) == fingerprint(os.fstat(fd)), 'file_changed')
            require(fingerprint(before) == fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)), 'file_changed')
            return raw
        finally:
            os.close(fd)


def tuple_key(row, map_row=False):
    path, h, roles = row['path'], row['sha256'], row['roles']
    size = row['observed_lstat']['size_bytes'] if map_row else row['logical_size_bytes_observed']
    require(isinstance(path, str) and path.startswith('/') and '\x00' not in path, 'tuple_shape')
    require(isinstance(h, str) and HEX.fullmatch(h), 'tuple_shape')
    require(isinstance(roles, list) and roles and all(isinstance(r, str) and r for r in roles)
            and len(roles) == len(set(roles)), 'tuple_shape')
    require(type(size) is int and size >= 0, 'tuple_shape')
    return path, h, tuple(roles), size


def tuples(rows, map_rows=False):
    require(isinstance(rows, list), 'tuple_shape')
    result = [tuple_key(row, map_rows) for row in rows]
    require(len(result) == len(set(result)) and len(result) == len({x[0] for x in result}), 'duplicate_tuple')
    return result


def counts_match(value, expected):
    return (isinstance(value, dict) and set(value) == set(expected)
            and all(type(n) is int and n >= 0 for n in value.values()) and value == expected)


def verify_archive(raw, expected):
    require(raw[:4] == b'\x1f\x8b\x08\x00' and raw[4:8] == b'\0' * 4, 'archive_format')
    seen = set()
    previous = ''
    with gzip.GzipFile(fileobj=io.BytesIO(raw), mode='rb') as stream:
        while True:
            header = stream.read(512)
            require(len(header) == 512, 'archive_truncated')
            if header == b'\0' * 512:
                rest = stream.read(1024 * 1024 + 1)
                require(len(rest) >= 512 and len(rest) % 512 == 0 and len(rest) <= 1024 * 1024
                        and not any(rest), 'archive_trailing_data')
                break
            require(header[257:265] == b'ustar\x0000', 'archive_format')
            info = tarfile.TarInfo.frombuf(header, 'utf-8', 'strict')
            require(re.fullmatch(r'objects/[0-9a-f]{64}', info.name), 'archive_member_name')
            require(info.name not in seen, 'archive_duplicate')
            require(info.name > previous, 'archive_member_order')
            previous = info.name
            require(info.type == tarfile.REGTYPE and info.mode == 0o600 and info.uid == info.gid == info.mtime == 0
                    and not info.uname and not info.gname and not info.linkname
                    and info.devmajor == info.devminor == 0, 'archive_metadata')
            h = info.name.split('/')[1]
            require(h in expected, 'archive_member_union')
            require(info.size == expected[h], 'archive_content_size')
            hasher = hashlib.sha256()
            left = info.size
            while left:
                block = stream.read(min(left, 1024 * 1024))
                require(block, 'archive_truncated')
                hasher.update(block)
                left -= len(block)
            require(hasher.hexdigest() == h, 'archive_content_hash')
            padding = stream.read((-info.size) % 512)
            require(len(padding) == (-info.size) % 512 and not any(padding), 'archive_padding')
            seen.add(info.name)
    require(seen == {'objects/' + h for h in expected}, 'archive_member_union')


def _verify(root, authority_sha256):
    require(isinstance(authority_sha256, str) and HEX.fullmatch(authority_sha256), 'authority_pin')
    tree = Tree(root)
    try:
        raw = {'controls/authority.json': tree.read('controls/authority.json')}
        require(digest(raw['controls/authority.json']) == authority_sha256, 'authority_pin')
        authority = strict_json(raw['controls/authority.json'])
        require(authority['schema_version'] == 'root-exact-private-retention-authority-v2'
                and authority['state'] == 'authorized_exact_copy', 'authority_scope')
        require(authority['destination'] == str(root), 'authority_destination')
        require(authority['tuple_fields'] == list(TUPLE_FIELDS)
                and authority['permissions'] == {'directories': '0700', 'files': '0600'}, 'authority_scope')
        for key in ('require_copy_time_source_hash_and_size_match', 'require_exact_allowed_tuple_union',
                    'require_regular_files_and_safe_paths', 'require_staged_atomic_write_and_fsync',
                    'require_independent_destination_rehash_and_manifest_verification', 'no_existing_destination_overwrite'):
            require(authority[key] is True, 'authority_scope')
        for key in ('excluded_tuple_reads_or_copies_authorized', 'reuse_existing_archives_only_on_verified_exact_hash_match',
                    'reuse_existing_archives_authorized', 'old_private_archive_metadata_transfer_authorized',
                    'private_payloads_in_git', 'credentials_or_env_files', 'sqlite_wal_shm_or_live_databases',
                    'raw_development_or_final_label_bundles', 'provider_cache_traversal', 'recursive_reference_following',
                    'model_calls', 'source_or_scientific_edits'):
            require(authority[key] is False, 'authority_scope')
        require(set(authority['references']) == set(ROLES), 'control_roles')
        controls = {}
        pins = {'authority': authority_sha256}
        for role in ROLES:
            name = 'controls/' + role + '.json'
            raw[name] = tree.read(name)
            pins[role] = digest(raw[name])
            require(pins[role] == authority['references'][role]['sha256'], 'control_pin')
            controls[role] = strict_json(raw[name])
        allowed = tuples(controls['allowlist']['allowed'])
        excluded = tuples(controls['allowlist']['excluded'])
        require(not ({x[0] for x in allowed} & {x[0] for x in excluded}), 'allowed_excluded_overlap')
        union = set(allowed + excluded)
        require(set(tuples(controls['proposed_tuples']['proposed'])) == union, 'proposed_tuple_union')
        require(set(tuples(controls['retention_map']['inputs'], True)) == union, 'retention_map_tuple_union')
        objects = {}
        for _, h, _, size in allowed:
            require(h not in objects or objects[h] == size, 'object_size_conflict')
            objects[h] = size
        counts = dict(allowed=len(allowed), excluded=len(excluded), unique_objects=len(objects),
                      logical_bytes=sum(x[3] for x in allowed), object_bytes=sum(objects.values()))
        for key, count_key in [('allowed_logical_tuples', 'allowed'), ('excluded_logical_tuples', 'excluded'),
                               ('declared_unique_hashes', 'unique_objects'), ('declared_logical_bytes', 'logical_bytes')]:
            require(type(authority[key]) is int and authority[key] == counts[count_key], 'authority_counts')
        raw['mapping.json'] = tree.read('mapping.json')
        mapping = strict_json(raw['mapping.json'])
        require(mapping['schema_version'] == 'closed-scaling-ownswap-private-mapping-v2'
                and mapping['authority_sha256'] == authority_sha256 and mapping['control_pins'] == pins, 'mapping_binding')
        require(tuples(mapping['inputs']) == allowed, 'mapping_tuple_union')
        for row in mapping['inputs']:
            require(set(row) == set(TUPLE_FIELDS) | {'archive_member'}
                    and row['archive_member'] == 'objects/' + row['sha256'], 'mapping_member')
        require(counts_match(mapping['counts'], counts), 'mapping_counts')
        require(mapping['all_sources_unchanged'] is True and mapping['controls_before_after_equal'] is True,
                'recorded_source_state')
        for key in ('source_checks_before', 'source_checks_after'):
            require(type(mapping[key]) is int and mapping[key] == counts['allowed'], 'recorded_source_state')
        require(len(mapping['source_states']) == len(allowed), 'recorded_source_state')
        for row, source in zip(mapping['source_states'], allowed):
            before = row['before']
            require(set(row) == {'path', 'before', 'after'} and row['path'] == source[0]
                    and before == row['after'] and before['size_bytes'] == source[3], 'recorded_source_state')
            require(set(before) == {'size_bytes', 'mode', 'device', 'inode', 'mtime_ns', 'ctime_ns'}, 'recorded_source_state')
            require(all(type(before[k]) is int and before[k] >= 0 for k in before if k != 'mode')
                    and isinstance(before['mode'], str) and re.fullmatch(r'0o[0-7]{3,4}', before['mode']), 'recorded_source_state')
        require(isinstance(mapping['copier_sha256'], str) and HEX.fullmatch(mapping['copier_sha256']), 'copier_identity')
        raw['objects.tar.gz'] = tree.read('objects.tar.gz', counts['object_bytes'] + counts['unique_objects'] * 2048 + 1024 * 1024)
        manifest_raw = tree.read('manifest.json')
        manifest = strict_json(manifest_raw)
        require(manifest['schema_version'] == 'closed-scaling-ownswap-private-manifest-v2'
                and manifest['authority_sha256'] == authority_sha256 and counts_match(manifest['counts'], counts), 'manifest_binding')
        files = manifest['files']
        require(isinstance(files, list) and len(files) == 10
                and [r['path'] for r in files] == sorted(MANIFEST_NAMES), 'manifest_inventory')
        for row in files:
            require(set(row) == {'path', 'sha256', 'size_bytes'} and type(row['size_bytes']) is int
                    and row['size_bytes'] == len(raw[row['path']]) and row['sha256'] == digest(raw[row['path']]), 'manifest_content')
        completion = strict_json(tree.read('completion.json'))
        require(completion['schema_version'] == 'closed-scaling-ownswap-copy-complete-v2'
                and completion['status'] == 'complete' and completion['authority_sha256'] == authority_sha256
                and completion['manifest_sha256'] == digest(manifest_raw) and counts_match(completion['counts'], counts)
                and completion['copier_sha256'] == mapping['copier_sha256']
                and completion['no_source_payload_parsing'] is True
                and type(completion['prior_archive_dependencies']) is int and completion['prior_archive_dependencies'] == 0,
                'completion_binding')
        verify_archive(raw['objects.tar.gz'], objects)
        return {'status': 'verified', 'counts': counts, 'code_id': CODE_ID}
    finally:
        tree.close()


def verify(root, authority_sha256):
    try:
        return _verify(str(root), authority_sha256)
    except VerificationError:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, OSError, EOFError, tarfile.TarError):
        raise VerificationError('malformed_destination') from None


def main():
    class SafeArgumentParser(argparse.ArgumentParser):
        def error(self, message):
            raise VerificationError('invalid_arguments')
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--authority-sha256', required=True)
    try:
        args = parser.parse_args()
        report = verify(args.root, args.authority_sha256)
    except VerificationError as error:
        print(json.dumps({'status': 'rejected', 'error_code': error.code, 'code_id': CODE_ID}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
