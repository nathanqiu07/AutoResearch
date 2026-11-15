"""Check three-snapshot preservation/replay metadata without opening snapshots."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ('proposal-stage', 'preservation-stage', 'external-stage', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    checks, opened = [], {}

    def ck(name, value):
        checks.append({'check': name, 'passed': bool(value)})
        if not value:
            raise ValueError('Failed additive metadata check: ' + name)

    def read(path, pin, size=None):
        data = path.read_bytes()
        ck('pin:' + path.name, sha(data) == pin and (size is None or len(data) == size))
        opened[str(path)] = data
        return json.loads(data)

    pins = read(a.proposal_stage / 'input-pins.json', '83fa9350f5a2077eaeff2ccad95c72449e1c17db4a851a056a124aab4a6b076d')
    wanted = {(r['path'], r['sha256'], r['size_bytes']) for r in pins['inputs'] if r['role'] != 'archive_metadata'}
    safe = read(a.preservation_stage / 'safe-manifest.json', '3be2d1cdf738eda6890cb1b0d58cf177539eb0292931fb7b74c5e19101a1c281')
    ck('18_safe_addendum_files', len(safe['files']) == safe['file_count'] == 18)
    for row in safe['files']:
        path = a.preservation_stage / row['path']
        data = path.read_bytes()
        ck('safe_file:' + row['path'], len(data) == row['size_bytes'] and sha(data) == row['sha256'])
        opened[str(path)] = data
    receipt = read(a.preservation_stage / 'private-preservation.json', '017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0')
    ck('only_three_approved_snapshots', len(receipt['members']) == receipt['member_count'] == 3 and {(r['source_path'], r['sha256'], r['size_bytes']) for r in receipt['members']} == wanted)
    ck('archive_pin_and_size', receipt['archive_sha256'] == '28e03a21179eb9d12c9c78663027477c67adbca4ac31c16393b303e3b15583dd' and receipt['archive_size_bytes'] == 405070 and receipt['uncompressed_input_bytes'] == sum(r['size_bytes'] for r in receipt['members']) == 1890004)
    ck('recorded_before_after_member_hashes', all(r['archived_sha256'] == r['sha256'] == r['source_sha256_after'] and r['archived_size_bytes'] == r['size_bytes'] == r['source_size_bytes_after'] and r['source_bytes_unchanged'] for r in receipt['members']) and receipt['all_sources_before_after_equal'] and receipt['all_archive_member_bytes_equal_sources'])
    ck('recorded_private_permissions', receipt['archive_mode'] == '0o600' and receipt['private_directory_mode'] == '0o700' and all(r['member_mode'] == '0o600' for r in receipt['members']))
    ck('preserver_code_pin', receipt['preserver_sha256'] == sha(opened[str(a.preservation_stage / 'archive_closed_metadata.py')]))
    copy = read(a.external_stage / 'copy-manifest.json', '9ec883bfea68fd529d7bba16835e10db89eb10cfb41155c6d8f152b170eb5061')
    ck('hash_based_not_git_membership', copy['source_commit'] is None and 'no Git membership claimed' in copy['source_identity_basis'])
    ck('28_bundle_entries_and_size', len(copy['files']) == len({r['destination'] for r in copy['files']}) == 28 and sum(r['size_bytes'] for r in copy['files']) == 477732)
    archives = [r for r in copy['files'] if r['kind'] == 'private_archive']
    ck('only_one_three_snapshot_archive_copied', len(archives) == 1 and archives[0]['sha256'] == receipt['archive_sha256'] and archives[0]['size_bytes'] == receipt['archive_size_bytes'])
    by_destination = {r['destination']: r for r in copy['files']}
    ck('exact_preservation_package_in_bundle', all(by_destination['preservation/' + r['path']]['sha256'] == r['sha256'] and by_destination['preservation/' + r['path']]['size_bytes'] == r['size_bytes'] for r in safe['files']))
    ck('exact_frozen_reader_in_both_locations', by_destination['preservation/review_snapshots.py']['sha256'] == by_destination['independent-snapshot-review/review_snapshots.py']['sha256'] == '24ca671a2d62c3783af775de395197c8eecac0de496a56a125fc2fab688d570e')
    comparisons = read(a.external_stage / 'root-recovery/comparison.json', '3072b947ef81ded7df73eee3100c6da49af5d760d4f6164cc161d19ab6b87e9b')
    external = read(a.external_stage / 'root-recovery/external-verification.json', 'be3ff906fc92c6a36f60da41580d3f2efeab456a568819f69eb3f61dec5b1f8f')
    extraction = read(a.external_stage / 'root-recovery/extraction.json', '9e0ef815bdbcde5af29ed0df4fbed3f6db33a5e6b97850e7a019ae8b91592df2')
    replay = read(a.external_stage / 'root-recovery/replay-report.json', '3e1b33f84ca06cc077827ef8ee26340eb11ae3746df928b2e8325150ec79b0b4')
    original_pin = by_destination['independent-snapshot-review/report.json']['sha256']
    original = read(a.external_stage / 'copy-source/independent-snapshot-review/report.json', original_pin, by_destination['independent-snapshot-review/report.json']['size_bytes'])
    ck('external_copy_verification_links', external['manifest_sha256'] == '9ec883bfea68fd529d7bba16835e10db89eb10cfb41155c6d8f152b170eb5061' and external['private_archive_sha256'] == receipt['archive_sha256'] and external['payload_files_verified'] == 28 and external['actual_files_including_metadata'] == 30 and external['payload_bytes'] == 477732 and external['source_git_membership_claim'] is False)
    ck('exact_extraction_member_pins', {(r['member'], r['sha256'], r['size_bytes']) for r in extraction['files']} == {(r['archive_member'], r['sha256'], r['size_bytes']) for r in receipt['members']} and extraction['archive_sha256'] == receipt['archive_sha256'] and extraction['receipt_sha256'] == '017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0' and extraction['original_source_paths_read'] is False and extraction['referenced_paths_followed'] == 0)
    ck('45_saved_replay_checks', replay['passed'] == len(replay['checks']) == 45 and replay['failed'] == 0 and replay['referenced_paths_followed'] == 0 and replay['model_calls'] == 0)
    ck('replay_input_pins_match_receipt', {(r['sha256'], r['bytes']) for r in replay['inputs']} == {(r['sha256'], r['size_bytes']) for r in receipt['members']} and len(replay['inputs']) == 3)
    left, right = deepcopy(original), deepcopy(replay)
    differences = []
    for old, new in zip(left['inputs'], right['inputs']):
        differences.append({'role': old['role'], 'original': old.pop('path'), 'recovered': new.pop('path')})
    ck('only_three_input_paths_differ', left == right and differences == comparisons['changed_paths'] and comparisons['all_other_fields_and_ordered_arrays_identical'] is True and comparisons['original_report_sha256'] == original_pin and comparisons['replayed_report_sha256'] == sha(opened[str(a.external_stage / 'root-recovery/replay-report.json')]))
    for name, data in opened.items():
        ck('metadata_unchanged:' + Path(name).name, Path(name).read_bytes() == data)
    result = {'schema_version': 'audit042-independent-preservation-metadata-review-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
              'reader_sha256': sha(Path(__file__).read_bytes()), 'opened_metadata': [{'path': name, 'sha256': sha(data), 'size_bytes': len(data)} for name, data in opened.items()],
              'retention_scope': {'approved_metadata_snapshots': 3, 'archive_bytes': 405070, 'archive_sha256': receipt['archive_sha256'], 'uncompressed_metadata_bytes': 1890004, 'external_payload_files': 28, 'external_total_files_with_controls': 30, 'external_payload_bytes': 477732},
              'root_saved_replay_checks': 45, 'all_other_report_fields_and_arrays_equal': True,
              'scope': {'snapshot_or_archive_payloads_read': False, 'referenced_bodies_read_or_statted': False, 'snapshot_reconciliation_repeated': False, 'owner_or_preserver_imports': False, 'model_calls': 0},
              'limits': ['This is an independent metadata-chain and code review, not a fresh hash/read of archive or snapshot bytes.',
                         'Preservation and root replay cover only the three explicitly approved snapshots, not the broader3022-reference retention map.',
                         'The frozen map remains an as-of comparison; its then-unretained entrypoints were captured later, without rewriting the historical map.',
                         'Raw eligibility remains pending; path roles and zero catalog overlap do not authorize copying private profile/prompt/response/selection bodies.']}
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'snapshot_members': 3, 'saved_replay_checks': 45, 'raw_payloads_read': False}))


if __name__ == '__main__':
    main()
