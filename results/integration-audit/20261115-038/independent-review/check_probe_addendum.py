#!/usr/bin/env python3
"""Bounded independent byte/AST check; never execute or import retained sources."""
import argparse
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

RECEIPT = '3cb2042dc05e8609247b7a7ab8da33eb383d5b3bfd42dc5abe7130d6132a867f'
ARCHIVE = '762133227fb664f14aac88957453104552d11f80b569f5b2cb2c5df195e90058'
REPORT = 'f73ad4eb18d04a20e055debab94cc64a9ad753e720865230fccf56eff38fa1e0'
PINS = {
    'access': ('neutral-api-access-proposal-v1/neutral_api_probe.py',
               'scripts/neutral_api_probe.py',
               '0e13af78f829d62c028750b87811fcec2438e06f1f80db3ea618297ff0f7de26'),
    'readiness': ('readiness-probe-proposal-v1/neutral_readiness_probe.py',
                  'scripts/neutral_readiness_probe.py',
                  '48f256d87f20c59dbfdf8601ff5bed1f2ec75ea603de472b792fd19acec6242a'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(args):
    checks, inputs, records = [], {}, []

    def check(name, condition):
        checks.append({'check': name, 'passed': bool(condition)})
        if not condition:
            raise ValueError(name)

    def read(path, pin):
        path = Path(path)
        data = path.read_bytes()
        check('pin:' + str(path), sha(data) == pin)
        inputs[path] = data
        return data

    base = Path(args.addendum)
    receipt = json.loads(read(base / 'retained/retention-receipt.json', RECEIPT))
    report = json.loads(read(args.binding_report, REPORT))
    archive = read(base / 'retained/probe-scripts.tar.gz', ARCHIVE)
    raw = gzip.decompress(archive)
    check('receipt_archive_binding', receipt['archive_sha256'] == ARCHIVE)
    check('receipt_report_binding', receipt['binding_report_sha256'] == REPORT)
    check('archive_size', len(archive) == receipt['archive_bytes'])
    check('uncompressed_archive_hash', sha(raw) == receipt['uncompressed_tar_sha256'])
    check('canonical_gzip_mtime', archive[4:8] == bytes(4))
    rows = {row['kind']: row for row in receipt['files']}
    prior = {row['kind']: row for row in report['records']}
    check('two_exact_kinds', len(receipt['files']) == 2 and set(rows) == set(PINS) == set(prior))
    check('prior_checks', report['failed'] == 0 and report['passed'] == 38 and all(x['passed'] for x in report['checks']))
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as tar:
        members = tar.getmembers()
        check('exact_members', [x.name for x in members] == sorted(x[1] for x in PINS.values()))
        for kind, (relative, member_name, pin) in PINS.items():
            row, old = rows[kind], prior[kind]
            member = tar.getmember(member_name)
            path = PurePosixPath(member.name)
            check(kind + '.regular_safe_member', member.isfile() and not path.is_absolute() and '..' not in path.parts and '\\' not in member.name)
            check(kind + '.metadata', member.mode == 0o644 and member.uid == member.gid == member.mtime == 0)
            data = tar.extractfile(member).read()
            check(kind + '.archive_bytes', sha(data) == pin == row['sha256'] and len(data) == row['bytes'] == member.size)
            check(kind + '.recorded_original_path', row['original_path'] == '/private/tmp/gio-profile-20261115-coordinator/' + relative)
            check(kind + '.recorded_before_after', row['sha256_before'] == pin == row['sha256_after'])
            check(kind + '.git_not_inferred', row['immutable_git_membership'] == 'not_claimed')
            check(kind + '.historical_script_pin', old['recorded_script_sha256'] == row['summary_script_sha256_via_pinned035_report'] == pin)
            for key in ('dispatch_raw_sha256', 'dispatch_canonical_sha256', 'summary_raw_sha256'):
                check(kind + '.' + key, row[key] == old[key])
            if args.original_root:
                original = read(Path(args.original_root) / relative, pin)
                check(kind + '.current_original_equals_retained', original == data)
            tree = ast.parse(data)
            assignments = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PROMPT' for t in n.targets)]
            check(kind + '.one_top_level_prompt', len(assignments) == 1)
            node = assignments[0].value
            check(kind + '.literal_prompt', isinstance(node, ast.Constant) and isinstance(node.value, str))
            prompt_bytes = node.value.encode('utf-8')
            prompt_hash = sha(prompt_bytes)
            check(kind + '.all_recorded_prompt_hashes', bool(old['calls']) and all(c['recorded_prompt_sha256'] == prompt_hash for c in old['calls']))
            records.append({'kind': kind, 'archive_member': member_name, 'script_sha256': pin,
                            'prompt_literal_line': assignments[0].lineno,
                            'prompt_literal_sha256': prompt_hash, 'prompt_utf8_bytes': len(prompt_bytes),
                            'recorded_calls_bound': len(old['calls']), 'dispatch_raw_sha256': old['dispatch_raw_sha256'],
                            'dispatch_canonical_sha256': old['dispatch_canonical_sha256'],
                            'summary_raw_sha256': old['summary_raw_sha256']})
    check('source_byte_total', sum(x['bytes'] for x in rows.values()) == receipt['source_bytes'] == 21846)
    for path, data in inputs.items():
        check('unchanged:' + str(path), path.read_bytes() == data)
    result = {'schema_version': 'independent038-probe-script-review-v1',
              'passed': len(checks), 'failed': 0, 'checks': checks, 'records': records,
              'reader_sha256': sha(Path(__file__).read_bytes()),
              'inputs': [{'path': str(path), 'sha256': sha(data), 'bytes': len(data)} for path, data in sorted(inputs.items())],
              'originals_checked': bool(args.original_root), 'source_execution': False,
              'source_imports': 0, 'model_calls': 0, 'raw_dispatch_or_summary_reads': 0,
              'limits': ['Script bytes and literal prompt hashes only; no Git membership or network-execution inference.',
                         'System/backend/provider request behavior is not reconstructed by this static AST check.',
                         'Prior035 dispatch linkage is reused from its pinned metadata report, not independently rerun here.',
                         'Original038 historical unresolved map is retained unchanged.']}
    with Path(args.out).open('x') as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'script_files': 2, 'recorded_prompt_bindings': 3, 'originals_checked': bool(args.original_root)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--addendum', required=True)
    parser.add_argument('--binding-report', required=True)
    parser.add_argument('--original-root')
    parser.add_argument('--out', required=True)
    run(parser.parse_args())
