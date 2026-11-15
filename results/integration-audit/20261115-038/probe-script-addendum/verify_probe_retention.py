#!/usr/bin/env python3
"""Verify released probe-script bytes from retained artifacts, without imports."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict(data):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('Duplicate JSON key')
            value[key] = item
        return value
    return json.loads(data, object_pairs_hook=pairs)


def run(args):
    checked, opened = [], {}

    def check(name, result):
        checked.append({'check': name, 'passed': bool(result)})
        if not result:
            raise ValueError('Failed check: ' + name)

    def read(path, pin):
        path = Path(path)
        data = path.read_bytes()
        check('input_sha256:' + path.name, sha(data) == pin)
        opened[path] = data
        return data

    receipt = strict(read(args.receipt, args.receipt_sha256))
    report = strict(read(args.binding_report, receipt['binding_report_sha256']))
    check('prior_report_pin', receipt['binding_report_sha256'] == 'f73ad4eb18d04a20e055debab94cc64a9ad753e720865230fccf56eff38fa1e0')
    check('prior_binding_checks_passed', report['passed'] == 38 and report['failed'] == 0)
    archive = read(args.archive, receipt['archive_sha256'])
    check('compressed_byte_count', len(archive) == receipt['archive_bytes'])
    raw = gzip.decompress(archive)
    check('uncompressed_tar_pin', sha(raw) == receipt['uncompressed_tar_sha256'])
    pins = {'access': '0e13af78f829d62c028750b87811fcec2438e06f1f80db3ea618297ff0f7de26',
            'readiness': '48f256d87f20c59dbfdf8601ff5bed1f2ec75ea603de472b792fd19acec6242a'}
    members = {'access': 'scripts/neutral_api_probe.py',
               'readiness': 'scripts/neutral_readiness_probe.py'}
    records = {row['kind']: row for row in report['records']}
    rows = {row['kind']: row for row in receipt['files']}
    check('exact_receipt_scope', len(receipt['files']) == receipt['source_file_count'] == 2 and set(rows) == set(pins))
    check('no_git_membership_claim', all(row['immutable_git_membership'] == 'not_claimed' for row in rows.values()))
    resolved = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as tar:
        actual = tar.getmembers()
        check('exact_archive_members', [m.name for m in actual] == sorted(members.values()))
        for kind, pin in pins.items():
            row, record = rows[kind], records[kind]
            member = tar.getmember(members[kind])
            check(kind + '.member_identity', row['archive_member'] == member.name and member.isfile())
            check(kind + '.canonical_metadata', member.mtime == 0 and member.uid == 0 and member.gid == 0 and member.mode == 0o644)
            data = tar.extractfile(member).read()
            check(kind + '.retained_bytes', sha(data) == pin == row['sha256'] and len(data) == row['bytes'])
            check(kind + '.recorded_before_after_capture', row['sha256_before'] == row['sha256_after'] == pin)
            check(kind + '.recorded_literal_screen', row['credential_literal_screen']['recognized_credential_patterns'] == 0 and row['credential_literal_screen']['sensitive_nonempty_literal_bindings'] == 0)
            check(kind + '.prior_summary_script_binding', row['summary_script_sha256_via_pinned035_report'] == record['recorded_script_sha256'] == pin)
            for field in ('dispatch_raw_sha256', 'dispatch_canonical_sha256', 'summary_raw_sha256'):
                check(kind + '.' + field, row[field] == record[field])
            resolved.append({key: row[key] for key in ('kind', 'archive_member', 'sha256', 'bytes', 'dispatch_raw_sha256', 'dispatch_canonical_sha256', 'summary_raw_sha256')})
    check('source_byte_total', sum(row['bytes'] for row in rows.values()) == receipt['source_bytes'])
    for path, before in opened.items():
        check('input_unchanged:' + path.name, path.read_bytes() == before)
    result = {'schema_version': 'audit038-probe-script-verification-v1',
              'checks': checked, 'passed': len(checked), 'failed': 0,
              'reader_sha256': sha(Path(__file__).read_bytes()),
              'receipt_sha256': args.receipt_sha256, 'archive_sha256': receipt['archive_sha256'],
              'binding_report_sha256': receipt['binding_report_sha256'],
              'records': resolved, 'source_imports': 0, 'source_execution': False,
              'original_source_paths_opened': False, 'model_calls': 0,
              'closed': 'Exact script-byte recovery only, joined to prior035 dispatch/summary identities.',
              'limits': receipt['limits']}
    out = Path(args.out)
    with out.open('x') as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': len(checked), 'failed': 0, 'files': len(rows), 'archive_sha256': receipt['archive_sha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('archive', 'receipt', 'receipt-sha256', 'binding-report', 'out'):
        parser.add_argument('--' + name, required=True)
    run(parser.parse_args())
