"""Verify copied041 capsule and saved replay; no full reader or private parsing."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat

MANIFEST = '4daf780ebdd3b2e53846273242840c44f8b599669dbe18db8b6ec8b01264ca29'
RECEIPT = 'c8811b9272cf594489188f328f8ca5f5a56a32aa91f3d4a78244bff27b350ea2'
SAFE = 'ad18cf3aa306cff7b2f3b79b2bc9a8f42e803518d6d047682cf99b2213de28f3'
REPORT = 'e3876406644d2b00202575040764ec1a483be62fa8ebfdae04e59852d60a4a0d'
COMMIT = 'b35c0f8f47f40b28a0aa6338fb7f626ce0db2b0f'
PACKAGE = 'results/integration-audit/20261115-039'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'capsule', 'root-evidence', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    checks, opened = [], {}

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    def read(path, pin=None):
        raw = path.read_bytes()
        if pin:
            check('pin:' + str(path), sha(raw) == pin)
        opened[path] = {'sha256': sha(raw), 'bytes': len(raw)}
        return raw

    safe = json.loads(read(a.stage / 'safe-manifest.json', SAFE))
    check('31_frozen_author_inputs', safe['file_count'] == len(safe['files']) == 31)
    for name, pin in safe['files'].items():
        data = read(a.stage / name, pin['sha256'])
        check('safe_input_size:' + name, len(data) == pin['bytes'])
    check('both_payload_archives_excluded_from_public_allowlist', 'copy-source/private/downstream05-audit039-publication-gap-v1.tar.gz' not in safe['files'] and 'copy-source/public/audit039-b35c0f8.tar.gz' not in safe['files'])
    manifest_bytes = read(a.stage / 'copy-manifest.json', MANIFEST)
    manifest = json.loads(manifest_bytes)
    receipt_bytes = read(a.stage / 'copy-receipt.json', RECEIPT)
    receipt = json.loads(receipt_bytes)
    check('10_payloads_total_bytes_commit', len(manifest['files']) == receipt['files_copied_and_verified'] == 10 and sum(r['size_bytes'] for r in manifest['files']) == receipt['bytes_copied'] == 1060424 and manifest['source_commit'] == receipt['source_commit'] == COMMIT)
    check('receipt_manifest_and_destination_binding', receipt['manifest_sha256'] == MANIFEST and Path(receipt['destination']).resolve() == a.capsule.resolve())
    expected = {'manifest.json', 'copy-receipt.json'}
    for row in manifest['files']:
        source_path, destination_path = PurePosixPath(row['source']), PurePosixPath(row['destination'])
        check('safe_paths:' + row['destination'], not source_path.is_absolute() and '..' not in source_path.parts and not destination_path.is_absolute() and '..' not in destination_path.parts and row['destination'] not in expected)
        expected.add(row['destination'])
        src, dst = a.stage / 'copy-source' / source_path, a.capsule / destination_path
        check('regular_copy_inputs_outputs:' + row['destination'], stat.S_ISREG(src.lstat().st_mode) and stat.S_ISREG(dst.lstat().st_mode))
        source = read(src, row['sha256'])
        check('copy_hash_size:' + row['destination'], read(dst, row['sha256']) == source and len(source) == row['size_bytes'])
    check('copied_control_bytes_exact', read(a.capsule / 'manifest.json') == manifest_bytes and read(a.capsule / 'copy-receipt.json') == receipt_bytes)
    actual, directories = set(), {'.'}
    for path in a.capsule.rglob('*'):
        mode = path.lstat().st_mode
        relative = str(path.relative_to(a.capsule))
        if stat.S_ISREG(mode):
            actual.add(relative)
            check('capsule_file0600:' + relative, stat.S_IMODE(mode) == 0o600)
        else:
            check('capsule_directory0700:' + relative, stat.S_ISDIR(mode) and stat.S_IMODE(mode) == 0o700)
            directories.add(relative)
    check('exact12_files_five_directories', actual == expected and len(actual) == 12 and directories == {'.', 'metadata', 'private', 'public', 'tools'} and stat.S_IMODE(a.capsule.stat().st_mode) == 0o700)
    public = a.root_evidence / 'recovered-public'
    inventory = json.loads(read(a.capsule / 'metadata/public-files.json'))
    check('public_inventory_source_scope', inventory['source_commit'] == COMMIT and inventory['file_count'] == 141)
    for row in inventory['files']:
        path = public / row['path']
        check('recovered_public_regular0600:' + row['path'], stat.S_ISREG(path.lstat().st_mode) and stat.S_IMODE(path.stat().st_mode) == 0o600)
        check('recovered_public_hash_size:' + row['path'], len(read(path, row['sha256'])) == row['size_bytes'])
    original = json.loads(read(public / PACKAGE / 'run-03/report.json', '044d65b67b4a80551721e1ac4af86d1cad865be59a5465168da35ba300119290'))
    replay_raw = read(a.root_evidence / 'replay/report.json', REPORT)
    replay = json.loads(replay_raw)
    different = sorted(k for k in set(original) | set(replay) if original.get(k) != replay.get(k))
    check('only_argv_reader_identity_differ', different == ['argv', 'reader_sha256'])
    check('all1316_original_checks_ordered_exact', original['checks'] == replay['checks'] and len(replay['checks']) == 1316 and all(r['verified'] for r in replay['checks']))
    old_inventory = read(public / PACKAGE / 'run-03/input-inventory.json', 'e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5')
    check('replay_inventory_byte_identical', read(a.root_evidence / 'replay/input-inventory.json') == old_inventory)
    reader = read(a.root_evidence / 'replay/reader-used.py', '84b68046face76b1a3ae81fefe903aed5e5e554a8146dbf01bc99a6ac0cd08cf')
    check('reader_used_identity', sha(reader) == replay['reader_sha256'])
    comparison = json.loads(read(a.root_evidence / 'comparison.json'))
    direct = json.loads(read(a.root_evidence / 'direct-comparison.json'))
    check('both_saved_comparisons_agree', comparison['differing_top_level_fields'] == direct['different_fields'] == different and comparison['recovered_report_sha256'] == direct['replay_report_sha256'] == REPORT and comparison['all_other_fields_and_ordered_arrays_exactly_equal'] and direct['all_other_fields_and_ordered_arrays_equal'] and comparison['inventory_byte_identical'] and direct['inventory_byte_identical'])
    invocation = json.loads(read(a.root_evidence / 'replay.invocation.json'))
    argv = invocation['argv']
    check('recorded_replay_success_and_argv', invocation['exit_code'] == 0 and argv[5:] == replay['argv'])
    wrapper = argv[4]
    check('saved_process_socket_checkout_guard', "event.startswith('socket.')" in wrapper and 'subprocess.Popen' in wrapper and 'sys.addaudithook(deny)' in wrapper and 'Original checkout/Git access forbidden' in wrapper and "p.startswith('/Users/giordanorogers/.codex/worktrees/')" in wrapper)
    check('new_capsule_private_gap_used', Path(argv[argv.index('--publication-archive') + 1]).resolve() == (a.capsule / 'private/downstream05-audit039-publication-gap-v1.tar.gz').resolve())
    check('recovered_public_reader_used', Path(argv[5]).resolve() == (public / PACKAGE / 'recovery/reproduce_recovered.py').resolve())
    dependency = json.loads(read(a.capsule / 'metadata/external-dependencies.json'))
    check('owner_payload_explicit_dependency', argv[argv.index('--retained-root') + 1] == dependency['owner_payload_recorded_location'] and dependency['owner_payload_files'] == 210 and dependency['owner_logical_references'] == 234 and manifest['external_owner_payload_copied'] is False)
    execution = json.loads(read(a.root_evidence / 'replay/recovered-execution.json'))
    check('replay_store_counts_and_no_fallback', (execution['logical_inputs_verified'], execution['retained_physical_files_verified'], execution['source_archive_members_verified'], execution['publication_archive_members_verified']) == (337, 210, 90, 13) and execution['fallback_allowed'] is False)
    for path, pin in opened.items():
        check('unchanged:' + str(path), sha(path.read_bytes()) == pin['sha256'])
    report = {'schema_version': 'independent041-copy-replay-review-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
              'copy_manifest_sha256': MANIFEST, 'copy_receipt_sha256': RECEIPT, 'author_safe_manifest_sha256': SAFE,
              'capsule_files': 12, 'payload_manifest_entries': 10, 'public_files_recovered': 141,
              'root_replay_report_sha256': REPORT, 'root_replay_checks_identical_in_order': 1316,
              'report_difference_fields': different, 'owner_payload_read_by_reviewer': False,
              'private_gap_archive_parsed': False, 'full039_reader_rerun': False, 'model_calls': 0,
              'inputs': [{'path': str(p), **pin} for p, pin in sorted(opened.items())],
              'reader_sha256': sha(Path(__file__).read_bytes()),
              'limits': ['Existing external210 owner files remain required. Not a self-contained raw-data or environment capsule.', 'Replay equality and guard are saved evidence; no new historical process/provider attestation.', 'Preparation Git verification is separate; copied verification itself uses pinned retained inventory.']}
    with a.out.open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'capsule_files': 12, 'replay_checks_exact': 1316}))


if __name__ == '__main__':
    main()
