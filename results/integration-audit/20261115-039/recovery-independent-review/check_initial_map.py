"""Independent metadata-only partition check for the additive039 recovery map."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath

PINS = {'recovery-map.json': '7da45e66e52a00b09bdbd11521a5b3da2d101b8b138fefd9917cd5db9396c67a',
        'PROPOSAL.md': 'fccf27b8b8f3490ceb838f9079fc33fd97c8f30525eec6c7015d53160a591205',
        'MAP_MANIFEST.json': 'b42c893bea91f2446861fab0f4b7f2da7fcb0de276b2d27f2961d9ab2c636be7'}
INVENTORY = 'e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5'
METADATA = {'manifest.json': '472782172c20204b57579f30db62bcd35bdfe6cb0f9409418114f31e26fb28a5',
            'receipt.json': '2e6daeee9d45c58e2f3df225132406dc04516e0e51a382030ff554b79b5a74e1',
            'index.json': '3e8100619f3450ccdfe4821fd40068d9adc66b824e2b52bc3f7d247c076bdd01'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('recovery-root', 'inventory', 'metadata-root', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    checks, inputs = [], {}

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    def read(path, pin):
        data = path.read_bytes()
        check('pin:' + str(path), sha(data) == pin)
        inputs[path] = data
        return data

    core = {n: read(a.recovery_root / n, pin) for n, pin in PINS.items()}
    mapping = json.loads(core['recovery-map.json'])
    allowlist = json.loads(core['MAP_MANIFEST.json'])
    for row in allowlist['files']:
        data = read(a.recovery_root / row['path'], row['sha256'])
        check('allowlist_size:' + row['path'], len(data) == row['size_bytes'])
    inventory = json.loads(read(a.inventory, INVENTORY))['files']
    metadata = {n: json.loads(read(a.metadata_root / n, pin)) for n, pin in METADATA.items()}
    manifest, receipt, index = (metadata[n] for n in ('manifest.json', 'receipt.json', 'index.json'))
    fields = ('commit', 'path', 'sha256', 'size_bytes')
    identity = lambda row: tuple(row[k] for k in fields)
    original = Counter(map(identity, inventory))
    mapped = mapping['retained_mappings']
    missing = mapping['missing_inputs']
    check('exact337_partition', Counter(map(identity, mapped + missing)) == original and len(original) == len(inventory) == 337)
    check('unique_commit_path', len({(r['commit'], r['path']) for r in inventory}) == 337)
    check('owner_metadata_binding', receipt['manifest_sha256'] == index['manifest_sha256'] == METADATA['manifest.json'] and index['receipt_sha256'] == METADATA['receipt.json'])
    check('owner213_files', len(manifest['files']) == manifest['file_count'] == receipt['file_count'] == index['recorded_file_count'] == 213)
    unique_payloads = set()
    for row in mapped:
        path = row['retained_payload_relative_path']
        parsed = PurePosixPath(path)
        check('safe_retained_path:' + path, bool(parsed.parts) and not parsed.is_absolute() and '..' not in parsed.parts and not path.endswith('.eval'))
        member = manifest['files'][path]
        check('exact_metadata_join:' + row['path'], member['source_sha256'] == member['copy_sha256'] == row['sha256'] and member['bytes'] == row['size_bytes'])
        expected = 'results/gio-matched-shutdown-05/' + path
        if row['commit'] == mapping['audit_publication_commit']:
            check('publication_relative_identity:' + row['path'], row['path'] == expected)
        else:
            check('executed_runner_identity:' + row['path'], row['commit'] == mapping['audit_executed_source'] and row['path'] == 'scripts/gio_petri/' + PurePosixPath(path).name and path.startswith('runner_source/'))
        unique_payloads.add(path)
    check('234_refs210_payloads', len(mapped) == 234 and len(unique_payloads) == 210)
    check('exact_three_eval_exclusions', set(manifest['files']) - unique_payloads == set(receipt['native_eval_files']) == set(mapping['unneeded_native_eval_members']) and len(receipt['native_eval_files']) == 3)
    check('counts_by_commit', Counter(x['commit'] for x in mapped) == {mapping['audit_publication_commit']: 210, mapping['audit_executed_source']: 24})
    check('retained_unique_bytes', sum(manifest['files'][n]['bytes'] for n in unique_payloads) == mapping['retained_unique_payload_bytes'] == 15276639)
    counts = Counter(x['gap_kind'] for x in missing)
    check('90_runtime13_private_partition', counts == {'public_runtime_source_bytes': 90, 'publication_or_review_record_keep_private_until_content_review': 13})
    check('missing_byte_totals', sum(x['size_bytes'] for x in missing if x['gap_kind'] == 'public_runtime_source_bytes') == 1265625 and sum(x['size_bytes'] for x in missing if x['gap_kind'] != 'public_runtime_source_bytes') == 244752)
    check('no_conflicts_or_hash_only_alternates', mapping['path_hash_conflicts'] == mapping['hash_only_alternates'] == [])
    check('initial_map_honest_scope', mapping['payload_bytes_read_or_copied'] is False and mapping['git_objects_read_or_copied'] is False)
    for path, raw in inputs.items():
        check('unchanged:' + str(path), path.read_bytes() == raw)
    report = {'schema_version': 'independent039-recovery-initial-map-v1', 'passed': len(checks), 'failed': 0,
              'checks': checks, 'logical_inputs': 337, 'retained_refs': 234, 'retained_unique_files': 210,
              'new_runtime_source_files': 90, 'new_private_records': 13, 'unneeded_eval_files': 3,
              'inputs': [{'path': str(p), 'sha256': sha(b), 'bytes': len(b)} for p, b in sorted(inputs.items())],
              'reader_sha256': sha(Path(__file__).read_bytes()), 'raw_payload_bytes_read': False,
              'git_objects_read': False, 'model_calls': 0,
              'scope': 'Metadata partition only. Retained payload bytes and final recovery adapter are separate later checks.'}
    with a.out.open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'logical_inputs': 337, 'raw_payload_bytes_read': False}))


if __name__ == '__main__':
    main()
