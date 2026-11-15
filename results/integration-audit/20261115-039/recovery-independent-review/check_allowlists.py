"""Check frozen original039 and additive safe-file allowlists without imports."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', type=Path, required=True)
    ap.add_argument('--recovery', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    checks, opened = [], {}

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    for label, root, pin, count in [('original', a.original, 'bbdc490610f1f43c9adf934c533e6bbbf94ee428a5e7220157f0d43d03f39182', 36), ('recovery', a.recovery, 'd89fefe324f1f756ca72181e2ec96b085799fb4606d28d03ae77149fadf46f0c', 41)]:
        path = root / 'SAFE_PACKAGE_MANIFEST.json'
        data = path.read_bytes()
        opened[path] = data
        check(label + '.manifest_pin', sha(data) == pin)
        manifest = json.loads(data)
        check(label + '.count', manifest['file_count'] == len(manifest['files']) == count)
        check(label + '.unique_paths', len({x['path'] for x in manifest['files']}) == count)
        for row in manifest['files']:
            path = PurePosixPath(row['path'])
            check(label + '.safe_path:' + str(path), not path.is_absolute() and '..' not in path.parts)
            value = (root / path).read_bytes()
            opened[root / path] = value
            check(label + '.hash_size:' + str(path), sha(value) == row['sha256'] and len(value) == row['size_bytes'])
    comparison = json.loads(opened[a.recovery / 'replay-comparison.json'])
    check('comparison_actual_diff_fields', comparison['differing_top_level_fields'] == ['argv', 'reader_sha256'])
    check('comparison_exact_order_and_inventory', comparison['inventory_byte_identical'] and comparison['all_other_fields_and_ordered_arrays_exactly_equal'] and comparison['original_checks_and_order_unchanged'])
    for path, data in opened.items():
        check('unchanged:' + str(path), path.read_bytes() == data)
    result = {'schema_version': 'independent039-recovery-allowlist-check-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
              'original_files_unchanged': 36, 'additive_files_verified': 41, 'private_archive_or_payload_read': False,
              'reader_sha256': sha(Path(__file__).read_bytes()), 'model_calls': 0}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'original': 36, 'additive': 41}))


if __name__ == '__main__':
    main()
