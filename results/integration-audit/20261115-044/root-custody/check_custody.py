"""Bind exact custody metadata to the frozen map; open no referenced body."""
import argparse
import hashlib
import json
from pathlib import Path

PINS = {
    'map': 'dbc08909d14ac12384c1cc36929e9751112e18c982cb838e04c22f6321d0adb7',
    'custody': 'b20e0ece59ca334a7b51e7072faa784f7050bc68258375e79dc2c4373e195c20',
    'allowlist': 'f403b554deefa55230486f09c31f469250cc415bf60b3dff41b2cf5e4b5420eb',
    'reuse_receipt': '017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('Duplicate metadata key')
            result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in PINS:
        p.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    data, originals, checks = {}, {}, []

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise ValueError(name)

    for name, expected in PINS.items():
        raw = getattr(a, name).read_bytes()
        check(name + '.exact_pin', sha(raw) == expected)
        originals[name] = raw
        data[name] = strict(raw)
    mapped, custody, allowed, receipt = (data[k] for k in PINS)
    check('custody_map_binding', custody['source_map']['sha256'] == PINS['map'])
    check('allowlist_map_binding', allowed['source_map']['sha256'] == PINS['map'])
    check('custody_allowlist_binding', custody['exact_allowlist']['sha256'] == PINS['allowlist'])
    check('same_six_exclusion_records', custody['excluded'] == allowed['excluded'])
    check('review_did_not_copy', allowed['raw_copy_performed'] is False and custody['raw_copies_made_by_reviewer'] == 0)
    check('review_no_live_or_private_access', custody['live_ledger_access'] is False and custody['private_groundtruth_accessed'] is False and custody['model_calls'] == 0)

    def identity(row, original=False):
        size = row['observed_lstat']['size_bytes'] if original else row['logical_size_bytes_observed']
        roles = tuple(sorted(row['roles']))
        if not roles or len(roles) != len(set(roles)):
            raise ValueError('Empty or repeated role')
        return row['path'], row['sha256'], roles, size

    m = [identity(row, True) for row in mapped['inputs']]
    permitted = [identity(row) for row in allowed['allowed']]
    excluded = [identity(row) for row in allowed['excluded']]
    check('exact_counts_and_no_duplicate_tuples', len(m) == len(set(m)) == 3022 and len(permitted) == len(set(permitted)) == 3016 and len(excluded) == len(set(excluded)) == 6)
    check('no_duplicate_path_identities', len({r[0] for r in m}) == len(m))
    check('allow_and_exclude_disjoint', not set(permitted).intersection(excluded))
    check('exact_map_partition_with_roles_and_sizes', set(m) == set(permitted).union(excluded))
    check('excluded_roles', sum('completion.unchanged_planned_coverage' in r[2] for r in excluded) == 4 and sum('completion.script' in r[2] or 'completion.supervisor_source' in r[2] for r in excluded) == 2)

    sizes = {}
    for _, digest, _, size in permitted:
        check_size = sizes.setdefault(digest, size)
        if check_size != size:
            raise ValueError('Same declared content hash has conflicting sizes')
    check('declared_unique_hashes_and_estimate', len(sizes) == 2816 and sum(sizes.values()) == 107081781)
    reuse = {(r['source_path'], r['sha256'], r['size_bytes']) for r in receipt['members']}
    check('exact_three_reused_member_identities', len(reuse) == 3 and receipt['member_count'] == 3)
    reused = [r for r in permitted if (r[0], r[1], r[3]) in reuse]
    remaining = [r for r in permitted if (r[0], r[1], r[3]) not in reuse]
    check('all_reused_members_are_authorized', len(reused) == 3 and {(r[0], r[1], r[3]) for r in reused} == reuse)
    new_sizes = {r[1]: r[3] for r in remaining}
    check('remaining_counts_and_estimates', len(remaining) == 3013 and len(new_sizes) == 2813 and sum(new_sizes.values()) == 105191777 and sum(r[3] for r in remaining) == 125062045)
    for name, raw in originals.items():
        check(name + '.unchanged', getattr(a, name).read_bytes() == raw)
    result = {
        'schema_version': 'audit044-root-custody-metadata-binding-v1',
        'passed': len(checks), 'failed': 0, 'checks': checks,
        'inputs': [{'role': k, 'path': str(getattr(a, k)), 'sha256': v} for k, v in PINS.items()],
        'reader_sha256': sha(Path(__file__).read_bytes()),
        'summary': {'mapped': 3022, 'approved': 3016, 'excluded': 6, 'reused': 3, 'new_logical_paths': 3013, 'new_declared_hashes': 2813, 'new_distinct_bytes_estimate': 105191777},
        'limits': ['Metadata tuple/role/size partition only; no actual payload hash or secret/label content verification.', 'No referenced body, archive payload, live database or nested pointer opened.', 'Existing user task authorization and source-owner custody decision remain distinct from byte verification.', 'Copy and final source/destination verification are separate subsequent evidence.'],
        'referenced_bodies_opened': 0, 'model_calls': 0,
    }
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), **result['summary']}))


if __name__ == '__main__':
    main()
