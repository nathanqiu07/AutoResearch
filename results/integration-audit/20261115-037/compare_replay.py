"""Compare audit037 reports exactly, except argv and explicitly allowed check order."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--left', type=Path, required=True)
    p.add_argument('--right', type=Path, required=True)
    p.add_argument('--left-inventory', type=Path, required=True)
    p.add_argument('--right-inventory', type=Path, required=True)
    p.add_argument('--allow-check-order', action='store_true')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    raw_left, raw_right = a.left.read_bytes(), a.right.read_bytes()
    left, right = json.loads(raw_left), json.loads(raw_right)
    differing = sorted(k for k in set(left) | set(right) if left.get(k) != right.get(k))
    left.pop('argv')
    right.pop('argv')
    exact_without_argv = left == right
    check_order_equal = left['checks'] == right['checks']
    multiset_equal = Counter(map(canonical, left['checks'])) == Counter(map(canonical, right['checks']))
    if a.allow_check_order:
        left.pop('checks')
        right.pop('checks')
    report_equal = left == right and (multiset_equal if a.allow_check_order else True)
    inventory_left, inventory_right = a.left_inventory.read_bytes(), a.right_inventory.read_bytes()
    inventory_equal = inventory_left == inventory_right
    result = {'schema_version':'audit037-replay-comparison-v1',
              'differing_top_level_fields':differing,
              'report_equal_except_argv':exact_without_argv,
              'check_order_normalization_explicitly_enabled':a.allow_check_order,
              'check_sequence_equal':check_order_equal,
              'checks_multiset_including_multiplicity_equal':multiset_equal,
              'all_remaining_fields_and_arrays_exactly_equal':left == right,
              'inventory_byte_identical':inventory_equal,
              'left_report_sha256':sha(raw_left),'right_report_sha256':sha(raw_right),
              'left_inventory_sha256':sha(inventory_left),'right_inventory_sha256':sha(inventory_right),
              'passed':report_equal and inventory_equal}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
