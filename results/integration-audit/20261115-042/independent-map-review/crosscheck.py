"""Independent aggregate042 proposal review; never open mapped reference bodies."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def hashes(value):
    if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from hashes(item)
    elif isinstance(value, list):
        for item in value:
            yield from hashes(item)


def stats(rows):
    by_hash = defaultdict(list)
    for row in rows:
        by_hash[row['sha256']].append(row['observed_lstat']['size_bytes'])
    if any(len(set(sizes)) != 1 for sizes in by_hash.values()):
        raise ValueError('One declared hash has inconsistent size observations')
    return {'logical_files': len(rows), 'declared_content_hashes': len(by_hash),
            'logical_path_bytes_lstat': sum(row['observed_lstat']['size_bytes'] for row in rows),
            'deduplicated_bytes_estimate': sum(sizes[0] for sizes in by_hash.values())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--audit-root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    checks, opened = [], {}

    def ck(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError('Failed metadata check: ' + name)

    def read(path, pin, size=None):
        data = path.read_bytes()
        ck('pin:' + path.name, sha(data) == pin and (size is None or len(data) == size))
        opened[str(path)] = data
        return json.loads(data)

    safe = read(a.stage / 'safe-manifest.json', '26d2d80f59180b2d65bfba8b4d68a60f06c8313996c95ec194f5ff3cd73c9c3d')
    ck('25_safe_files', len(safe['files']) == len({r['path'] for r in safe['files']}) == 25)
    public = {}
    for row in safe['files']:
        path = a.stage / row['path']
        raw = path.read_bytes()
        ck('safe_file:' + row['path'], sha(raw) == row['sha256'] and len(raw) == row['size_bytes'])
        opened[str(path)] = raw
        if row['path'].endswith('.json'):
            public[row['path']] = json.loads(raw)
    pins = public['input-pins.json']
    mapped = public['run-02/retention-map.json']
    report = public['run-02/report.json']
    scope = public['scope-proposal.json']
    proposal = public['run-02/new-content-proposal.json']
    ck('released_map_pin', sha(opened[str(a.stage / 'run-02/retention-map.json')]) == 'dbc08909d14ac12384c1cc36929e9751112e18c982cb838e04c22f6321d0adb7' == scope['map_sha256'])
    ck('released_scope_pin', sha(opened[str(a.stage / 'scope-proposal.json')]) == '44ffb04a44a9399f5ea64ce78ca74d8e8f801fb4cea9e079ee308263b7b24189')
    ck('map_input_pin', mapped['pins_sha256'] == report['pins_sha256'] == sha(opened[str(a.stage / 'input-pins.json')]))
    rows = mapped['inputs']
    identities = {(r['path'], r['sha256']) for r in rows}
    ck('3022_unique_identity_and_path', len(rows) == len(identities) == len({r['path'] for r in rows}) == 3022)
    ck('declared_hash_syntax', all(re.fullmatch('[0-9a-f]{64}', r['sha256']) for r in rows))
    ck('recorded_regular_sizes_only', all(r['observed_lstat']['kind'] == 'regular' and type(r['observed_lstat']['size_bytes']) is int and r['observed_lstat']['size_bytes'] >= 0 for r in rows))
    ck('no_asserted_retained_bytes', all(r['retention_status'] == 'not_in_compared_receipts' and r['receipt_matches'] == [] and r['retained_size_bytes'] is None for r in rows))
    occurrences = [(o['document'], o['json_pointer']) for r in rows for o in r['logical_occurrences']]
    ck('3637_unique_occurrences', len(occurrences) == len(set(occurrences)) == 3637)
    entries = {(r['path'], r['sha256']) for r in rows if any(o['json_pointer'] == '' for o in r['logical_occurrences'])}
    ck('three_entrypoints_distinguished', entries == {(r['path'], r['sha256']) for r in pins['inputs'] if r['role'] != 'archive_metadata'} and len(entries) == 3)
    role_consistent = True
    for row in rows:
        derived = set()
        for occ in row['logical_occurrences']:
            parts = occ['json_pointer'].split('/')
            if len(parts) >= 4 and parts[1] in ('jobs', 'batches'):
                derived.add(('job.' if parts[1] == 'jobs' else 'batch.') + parts[3])
            else:
                derived.add(occ['document'] + '.' + (parts[1] if len(parts) > 1 and parts[1] else 'entrypoint'))
        role_consistent &= derived == set(row['roles']) and len(row['roles']) == len(set(row['roles']))
    ck('roles_match_occurrence_pointers', role_consistent)
    by_hash = defaultdict(list)
    for row in rows:
        by_hash[row['sha256']].append(row)
    ck('2822_declared_hash_groups', len(by_hash) == 2822)
    repeated = [v for v in by_hash.values() if len(v) > 1]
    ck('four_release_duplicate_groups', sorted(map(len, repeated)) == [2, 3, 99, 100] and all(set(r['roles']) == {'job.release'} for group in repeated for r in group))
    ck('total_size_estimates', stats(rows) == scope['total'] == {'logical_files': 3022, 'declared_content_hashes': 2822, 'logical_path_bytes_lstat': 127940769, 'deduplicated_bytes_estimate': 108070501})
    proposed = {r['sha256']: r for r in proposal['files']}
    ck('new_content_groups_exact', len(proposed) == len(proposal['files']) == 2822 and set(proposed) == set(by_hash) and all(set(proposed[h]['logical_paths']) == {r['path'] for r in group} and proposed[h]['observed_size_bytes'] == group[0]['observed_lstat']['size_bytes'] and proposed[h]['size_consistent'] for h, group in by_hash.items()))
    buckets = {
        'saved_request_response_result_profile_bytes': {'job.trace_files', 'job.result', 'job.profile'},
        'execution_binding_and_batch_records': {'job.claim', 'job.manifest', 'job.prepared_packet', 'job.release', 'job.dispatch_receipt', 'job.prepared', 'batch.prepared', 'batch.summary', 'batch.verified_record'},
        'original_plan_rebind_and_candidate_provenance': {'job.original_candidate_packet', 'job.original_prepared', 'job.rebind_evidence', 'batch.original_prepared', 'batch.rebind_evidence', 'completion.candidate_proof', 'completion.prepared_index'},
        'compiler_supervisor_source_optional_separate_code_review': {'completion.script', 'completion.supervisor_source', 'supervisor.script'},
        'hold_coverage_context_not_needed_for_terminal_record_bytes': {'completion.unchanged_planned_coverage'},
        'closed_accounting_supervision_diagnostics_metadata': {'batch.diagnostics', 'completion.entrypoint', 'completion.policy', 'completion.supervisor_claim', 'completion.supervisor_terminal', 'ledger_snapshot.entrypoint', 'supervisor.entrypoint', 'supervisor.index', 'supervisor.predecessor'},
    }
    classified = defaultdict(list)
    shared_plan_index_rows = 0
    for row in rows:
        names = {key for key, roles in buckets.items() if set(row['roles']) & roles}
        if set(row['roles']) == {'completion.prepared_index', 'supervisor.index'}:
            # One shared index has two roles; the proposal intentionally places
            # its single logical identity in the original-plan category.
            names = {'original_plan_rebind_and_candidate_provenance'}
            shared_plan_index_rows += 1
        if len(names) != 1 or not set(row['roles']) <= set().union(*buckets.values()):
            raise ValueError('Ambiguous or unrecognized role classification')
        classified[next(iter(names))].append(row)
    ck('one_shared_plan_index_role_precedence', shared_plan_index_rows == 1)
    for name, group in classified.items():
        ck('category_partition:' + name, stats(group) == scope['mutually_exclusive_categories'][name])
    ck('categories_hash_disjoint', sum(len({r['sha256'] for r in group}) for group in classified.values()) == len(by_hash))
    held = classified['hold_coverage_context_not_needed_for_terminal_record_bytes']
    ck('four_exact_held_references', len(held) == 4 and {(r['path'], r['sha256']) for r in held} == {(r['path'], r['sha256']) for r in scope['hold_before_copy']} and all(r['roles'] == ['completion.unchanged_planned_coverage'] for r in held))
    profiles = [r for r in rows if 'job.profile' in r['roles']]
    ck('profile_estimate204', len(profiles) == 204 and stats(profiles)['logical_path_bytes_lstat'] == 93728648)
    for role, expected in scope['roles_nonadditive'].items():
        ck('role_totals:' + role, stats([r for r in rows if role in r['roles']]) == expected)
    metadata, hash_superset = {}, set()
    for row in pins['inputs']:
        if row['role'] != 'archive_metadata':
            continue  # Do not open the three terminal snapshots or their references.
        relative = PurePosixPath(row['relative_path'])
        if relative.is_absolute() or '..' in relative.parts or not str(relative).startswith('results/integration-audit/'):
            raise ValueError('Outside approved public receipt scope')
        data = read(a.audit_root / relative, row['sha256'], row['size_bytes'])
        metadata[str(relative)] = data
        hash_superset.update(hashes(data))
    ck('22_public_metadata_inputs_only', len(metadata) == 22)
    prefix = 'results/integration-audit/'
    checkpoint = metadata[prefix + '20261115-040/copy-manifest.json']
    archive_rows = [r for r in checkpoint['files'] if r['kind'] == 'private_archive']
    expected_archives = {r['sha256']: {'receipt': r['receipt'], 'bytes': r['size_bytes']} for r in archive_rows}
    for suffix in ('private-publication-preservation.json', 'source-preservation.json'):
        name = prefix + '20261115-039/recovery/preparation-01/' + suffix
        receipt = metadata[name]
        expected_archives[receipt['archive_sha256']] = {'receipt': name, 'bytes': receipt['archive_size_bytes']}
    ck('exact18_archive_scope', len(archive_rows) == 16 and len(expected_archives) == 18 and {r['archive_sha256'] for r in report['archive_catalogs']} == set(expected_archives))
    member_count = 0
    for catalog in report['archive_catalogs']:
        expected = expected_archives[catalog['archive_sha256']]
        receipt = metadata[expected['receipt']]
        if 'new_archives' in receipt:
            group = next(r for r in receipt['new_archives'] if r['sha256'] == catalog['archive_sha256'])
            count = len(group['members'])
            linked = group['member_count'] == count
        elif 'original_receipt' in receipt:
            original = metadata[str(PurePosixPath(expected['receipt']).parent / receipt['original_receipt'])]
            count = len(original['members'])
            linked = original['sha256'] == receipt['archive_sha256'] == catalog['archive_sha256']
        else:
            count = len(receipt.get('files', receipt.get('members')))
            linked = receipt['archive_sha256'] == catalog['archive_sha256']
        ck('catalog:' + catalog['archive_sha256'], linked and catalog['receipt'] == expected['receipt'] and catalog['archive_bytes'] == expected['bytes'] and catalog['catalog_members'] == count)
        member_count += count
    ck('zero_overlap_with_receipt_hash_superset', not set(by_hash) & hash_superset)
    source = metadata[prefix + '20261115-035/final/source-reference.json']
    ck('runtime_source_separate', report['runtime_source']['source_tar_sha256'] == source['sha256'] and source['sha256'] in hash_superset and source['file_count'] == len(source['files']) == 92 and report['runtime_source']['declared_commit'] == source['commit'])
    ck('path_screen_not_content_attestation', scope['named_path_screen']['matches'] == [] and scope['named_path_screen']['not_a_content_safety_test'] is True and 'cannot establish' in scope['potential_content_scope']['path_not_content_attestation'])
    for name, data in opened.items():
        ck('unchanged:' + Path(name).name, Path(name).read_bytes() == data)
    result = {'schema_version': 'audit042-independent-map-review-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
              'reader_sha256': sha(Path(__file__).read_bytes()), 'proposal_safe_manifest_sha256': '26d2d80f59180b2d65bfba8b4d68a60f06c8313996c95ec194f5ff3cd73c9c3d',
              'opened_metadata': [{'path': name, 'sha256': sha(data), 'size_bytes': len(data)} for name, data in opened.items()],
              'counts': {'logical_path_hash_identities': len(rows), 'declared_hashes': len(by_hash), 'occurrences': len(occurrences), 'explicit_occurrences_without_entrypoints': len(occurrences) - 3, 'archive_catalogs': len(expected_archives), 'catalog_member_entries': member_count, 'held_references': len(held)},
              'duplicate_content_group_path_counts': sorted(map(len, repeated)), 'size_estimates': stats(rows),
              'categories': {name: stats(group) for name, group in classified.items()},
              'scope': {'terminal_snapshots_opened': False, 'referenced_bodies_opened_or_statted': False, 'archive_payloads_opened': False, 'sqlite_opened': False, 'owner_or_mapper_imports': False, 'model_calls': 0},
              'limits': ['Map counts are independently reconstructed from frozen public metadata, not a fresh traversal of the three original terminal snapshots.',
                         'Public receipt catalogs are assertions about archived members; no archive payload is rehashed here.',
                         'Sizes and content hashes remain observations/declarations pending approved byte verification.',
                         'No raw eligibility or label-free attestation follows from path/role classification. Wider raw retention remains unapproved by this review.']}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'counts': result['counts'], 'size_estimates': result['size_estimates']}))


if __name__ == '__main__':
    main()
