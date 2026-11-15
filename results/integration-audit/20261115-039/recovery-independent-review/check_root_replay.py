"""Compare saved root039 replay only; never execute its reader or read raw data."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', type=Path, required=True)
    ap.add_argument('--root-package', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    inputs, checks = {}, []

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    def read(path, pin=None):
        data = path.read_bytes()
        if pin:
            check('pin:' + str(path), sha(data) == pin)
        inputs[path] = data
        return data

    old = json.loads(read(a.original / 'run-03/report.json', '044d65b67b4a80551721e1ac4af86d1cad865be59a5465168da35ba300119290'))
    new = json.loads(read(a.root_package / 'root-recovered-replay/report.json', '1e67f69451abef441e342adee5869388436a8cee0853a9dbd1f821459a91f6e8'))
    before = read(a.original / 'run-03/input-inventory.json', 'e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5')
    after = read(a.root_package / 'root-recovered-replay/input-inventory.json', 'e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5')
    check('inventory_byte_identical', before == after)
    differing = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    check('only_reader_and_argv_differ', differing == ['argv', 'reader_sha256'])
    check('all1316_checks_in_order', old['checks'] == new['checks'] and len(new['checks']) == 1316 and all(c['verified'] for c in new['checks']))
    reader = read(a.root_package / 'root-recovered-replay/reader-used.py', '84b68046face76b1a3ae81fefe903aed5e5e554a8146dbf01bc99a6ac0cd08cf')
    check('reader_used_matches_report', sha(reader) == new['reader_sha256'])
    comparison = json.loads(read(a.root_package / 'root-recovery-comparison.json'))
    check('saved_comparison_matches_independent_result', comparison['recovered_report_sha256'] == sha(inputs[a.root_package / 'root-recovered-replay/report.json']) and comparison['differing_top_level_fields'] == differing and comparison['inventory_byte_identical'] and comparison['all_other_fields_and_ordered_arrays_exactly_equal'] and comparison['original_checks_and_order_unchanged'])
    for path, raw in inputs.items():
        check('unchanged:' + str(path), path.read_bytes() == raw)
    result = {'schema_version': 'independent039-root-recovery-comparison-v1', 'passed': len(checks), 'failed': 0,
              'checks': checks, 'difference_fields': differing, 'original_checks_exact_in_order': 1316,
              'inputs': [{'path': str(p), 'sha256': sha(b), 'bytes': len(b)} for p, b in sorted(inputs.items())],
              'reader_sha256': sha(Path(__file__).read_bytes()), 'full039_reader_rerun': False, 'model_calls': 0,
              'scope': 'Saved report, reader identity and inventory comparison only; no new assertion about OS-level historical input access.'}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'original_checks_exact_in_order': 1316}))


if __name__ == '__main__':
    main()
