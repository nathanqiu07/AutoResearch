"""Independent039 recovery bindings; raw payloads are hash-only, never parsed."""
import argparse
import ast
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile

PINS = {
 'recovery-map.json': '7da45e66e52a00b09bdbd11521a5b3da2d101b8b138fefd9917cd5db9396c67a',
 'reproduce_recovered.py': '84b68046face76b1a3ae81fefe903aed5e5e554a8146dbf01bc99a6ac0cd08cf',
 'recovered_inputs.py': '2664df47897e7ce97e8030020d12ab1c1b322c3a97b1801cecd94272e8d2f3f1',
 'reader-change-proof.json': 'f0b0bca4ce75e344d183112e917340540131bf9a3943aeca471b8fce40ba15a6',
 'preparation-01/recovered-input-map.json': '1c4cad7f68896c5dd9afc2b88bdf9f509d005a2343df395a1647a88964996dd3',
 'preparation-01/source-preservation.json': '5739108eeb64123967fe4a12096b7f47d7bf429082d1786e558bb1200daf1b30',
 'preparation-01/private-publication-preservation.json': '38101df5975c46fd837900e539e8596c7ba00f22cc3db67560c9fa768bb60d0e',
 'preparation-01/retained-verification.json': 'a8788ee7676d1666effe7b4b70a654e17f042053149ae851fa67903168bc66df',
 'replay-01/report.json': '8857cc2ef86cc62b3ee6e0f3b9a3f437784e73d231362ed20c32fed3f96d3572',
 'replay-01/recovered-execution.json': '37a6055635c7e055c33116b17718a72200ed3b74ffae1b4b92d1c536d8ffddae',
 'replay-01.invocation.json': 'ecec4f8314779d6567a12c3b0acebff788ad24ae84251fb5d27e7e6ef4e40d21',
}
ORIGINAL = 'df2e4c4d8f1b87e39969a637fa3b0e537c459234ecb4cc50813baf83cd76b409'
INVENTORY = 'e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5'
ORIGINAL_REPORT = '044d65b67b4a80551721e1ac4af86d1cad865be59a5465168da35ba300119290'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'original-reader', 'original-report', 'original-inventory', 'retained-root', 'source-archive', 'publication-archive', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    checks, opened = [], {}

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    def read(path, pin=None):
        data = path.read_bytes()
        if pin:
            check('pin:' + str(path), sha(data) == pin)
        opened[path] = {'sha256': sha(data), 'size_bytes': len(data)}
        return data

    raw = {n: read(a.stage / n, pin) for n, pin in PINS.items()}
    obj = {n: json.loads(b) for n, b in raw.items() if n.endswith('.json')}
    initial = obj['recovery-map.json']
    mapping = obj['preparation-01/recovered-input-map.json']
    original = read(a.original_reader, ORIGINAL)
    inventory_raw = read(a.original_inventory, INVENTORY)
    inventory = json.loads(inventory_raw)
    proof = obj['reader-change-proof.json']
    transformed = original.decode()
    check('six_declared_replacements', len(proof['changes']) == 6)
    for i, change in enumerate(proof['changes']):
        check('one_exact_old_occurrence:' + str(i), transformed.count(change['old']) == 1)
        transformed = transformed.replace(change['old'], change['new'])
    check('entire_remaining_reader_body_unchanged', transformed.encode() == raw['reproduce_recovered.py'])
    check('proof_identity', proof['original_sha256'] == ORIGINAL and proof['portable_sha256'] == PINS['reproduce_recovered.py'] and proof['adapter_sha256'] == PINS['recovered_inputs.py'])
    check('variant_inventory_original_reader_pins', mapping['original_reader_sha256'] == ORIGINAL and mapping['original_inventory_sha256'] == INVENTORY)
    identity = lambda r: tuple(r[k] for k in ('commit', 'path', 'sha256', 'size_bytes'))
    check('337_exact_inventory_identities', len(mapping['files']) == 337 and Counter(map(identity, mapping['files'])) == Counter(map(identity, inventory['files'])))
    expected = {}
    for row in initial['retained_mappings']:
        expected[identity(row)] = ('retained', row['retained_payload_relative_path'])
    for row in initial['missing_inputs']:
        expected[identity(row)] = ('source' if row['gap_kind'] == 'public_runtime_source_bytes' else 'publication', row['proposed_bundle_path'])
    for row in mapping['files']:
        check('explicit_store_identity:' + row['path'], (row['store'], row['relative_path']) == expected[identity(row)])
    check('exact234_90_13_store_counts', Counter(x['store'] for x in mapping['files']) == {'retained': 234, 'source': 90, 'publication': 13})
    retained = {r['relative_path']: r for r in mapping['files'] if r['store'] == 'retained'}
    check('210_unique_retained_files', len(retained) == 210)
    dirs = {a.retained_root.resolve()}
    for rel, row in retained.items():
        path = a.retained_root / rel
        check('retained_regular0600:' + rel, stat.S_ISREG(path.lstat().st_mode) and stat.S_IMODE(path.stat().st_mode) == 0o600)
        path.resolve().relative_to(a.retained_root.resolve())
        data = read(path, row['sha256'])
        check('retained_size:' + rel, len(data) == row['size_bytes'])
        parent = path.parent.resolve()
        while parent != a.retained_root.resolve():
            dirs.add(parent)
            parent = parent.parent
    check('retained_named_directories0700', all(stat.S_IMODE(p.stat().st_mode) == 0o700 for p in dirs))
    check('native_eval_not_read', all(not p.name.endswith('.eval') for p in opened))
    for store, archive_path, receipt_name, count, mode in [
            ('source', a.source_archive, 'preparation-01/source-preservation.json', 90, 0o644),
            ('publication', a.publication_archive, 'preparation-01/private-publication-preservation.json', 13, 0o600)]:
        receipt = obj[receipt_name]
        info = mapping['archives'][store]
        archive = read(archive_path, info['archive_sha256'])
        check(store + '.archive_identity_size', receipt['archive_sha256'] == info['archive_sha256'] and len(archive) == receipt['archive_size_bytes'] == info['archive_size_bytes'])
        check(store + '.archive_regular_mode', stat.S_ISREG(archive_path.lstat().st_mode) and stat.S_IMODE(archive_path.stat().st_mode) == mode)
        if store == 'publication':
            check('private_archive_parent0700', stat.S_IMODE(archive_path.parent.stat().st_mode) == 0o700)
        rows = {r['relative_path']: r for r in mapping['files'] if r['store'] == store}
        check(store + '.receipt_exact_logical_members', Counter(map(identity, receipt['files'])) == Counter(map(identity, rows.values())))
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:*') as tar:
            members = tar.getmembers()
            check(store + '.exact_member_set', len(members) == len(rows) == receipt['member_count'] == info['member_count'] == count and {m.name for m in members} == set(rows))
            for member in members:
                path = PurePosixPath(member.name)
                check(store + '.safe_member:' + member.name, member.isfile() and not path.is_absolute() and '..' not in path.parts and member.mode == mode)
                data = tar.extractfile(member).read()
                check(store + '.member_hash_size:' + member.name, sha(data) == rows[member.name]['sha256'] and len(data) == rows[member.name]['size_bytes'])
    before = json.loads(read(a.original_report, ORIGINAL_REPORT))
    after = obj['replay-01/report.json']
    different = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check('only_reader_and_argv_differ', different == ['argv', 'reader_sha256'])
    check('all1316_checks_identical_and_passed', before['checks'] == after['checks'] and len(after['checks']) == 1316 and all(x['verified'] for x in after['checks']))
    check('original_and_recovered_inventory_byte_identical', read(a.stage / 'replay-01/input-inventory.json') == inventory_raw)
    check('reader_used_exact_variant', read(a.stage / 'replay-01/reader-used.py') == raw['reproduce_recovered.py'])
    execution = obj['replay-01/recovered-execution.json']
    check('execution_exact_input_counts', (execution['logical_inputs_verified'], execution['retained_logical_refs'], execution['retained_physical_files_verified'], execution['source_archive_members_verified'], execution['publication_archive_members_verified']) == (337, 234, 210, 90, 13))
    check('execution_pins', execution['input_map_sha256'] == PINS['preparation-01/recovered-input-map.json'] and execution['original_checking_reader_sha256'] == ORIGINAL and execution['portable_reader_sha256'] == PINS['reproduce_recovered.py'] and execution['adapter_sha256'] == PINS['recovered_inputs.py'])
    check('execution_limits', execution['before_after_hashes_verified'] is True and execution['fallback_allowed'] is False and execution['owner_code_imported'] is False and execution['recorded_commit_path_labels_are_not_recovered_git_provenance'] is True)
    invocation = obj['replay-01.invocation.json']
    check('recorded_invocation_success', invocation['returncode'] == 0 and invocation['argv'][5:] == after['argv'])
    check('recorded_process_socket_guard', 'sys.addaudithook(deny)' in invocation['argv'][4] and 'subprocess.Popen' in invocation['argv'][4] and "event.startswith('socket.')" in invocation['argv'][4])
    adapter_tree = ast.parse(raw['recovered_inputs.py'])
    imports = {n.name for node in ast.walk(adapter_tree) if isinstance(node, ast.Import) for n in node.names}
    imports |= {node.module for node in ast.walk(adapter_tree) if isinstance(node, ast.ImportFrom)}
    check('adapter_stdlib_imports_only', imports == {'hashlib', 'io', 'json', 'pathlib', 'tarfile'})
    for path, pin in opened.items():
        check('unchanged:' + str(path), sha(path.read_bytes()) == pin['sha256'])
    result = {'schema_version': 'independent039-recovered-evidence-review-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
              'reader_sha256': sha(Path(__file__).read_bytes()), 'inputs': [{'path': str(p), **v} for p, v in sorted(opened.items())],
              'logical_inputs': 337, 'retained_files_hash_checked': 210, 'source_members_hash_checked': 90, 'private_publication_members_hash_checked': 13,
              'raw_payload_json_parsed': False, 'native_eval_read': False, 'owner_code_imported': False, 'full039_reader_rerun': False, 'model_calls': 0,
              'report_difference_fields': different, 'original_check_sequence_exact': True,
              'limits': ['Exact byte recovery and unchanged original assertions; no accounting or later-judging reinterpretation.', 'Recorded commit/path labels do not recreate Git history or complete environment.', 'Private member bytes were hashed without parsing or exporting their content.', 'Saved replay independently compared; original full checker was not rerun.']}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'retained_files': 210, 'source_members': 90, 'private_members': 13, 'report_difference_fields': different}))


if __name__ == '__main__':
    main()
