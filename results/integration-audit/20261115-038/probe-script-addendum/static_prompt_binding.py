#!/usr/bin/env python3
"""Hash literal PROMPT assignments without importing or executing source code."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prompt_literal(data):
    tree = ast.parse(data)
    assignments = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'PROMPT' for target in node.targets):
            assignments.append(node)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == 'PROMPT':
            assignments.append(node)
    if len(assignments) != 1:
        raise ValueError('Expected one module-level PROMPT assignment')
    node = assignments[0]
    if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
        raise ValueError('PROMPT must be a literal string')
    data = node.value.value.encode('utf-8')
    return {'line': node.lineno, 'utf8_bytes': len(data), 'sha256': sha(data)}


def run(args):
    paths = [Path(args.archive), Path(args.receipt), Path(args.binding_report)]
    before = {path: path.read_bytes() for path in paths}
    checks = []

    def check(name, value):
        checks.append({'check': name, 'passed': bool(value)})
        if not value:
            raise ValueError('Failed check: ' + name)

    check('receipt_pin', sha(before[paths[1]]) == args.receipt_sha256)
    receipt = json.loads(before[paths[1]])
    check('archive_pin', sha(before[paths[0]]) == receipt['archive_sha256'])
    check('prior_report_pin', sha(before[paths[2]]) == receipt['binding_report_sha256'] == 'f73ad4eb18d04a20e055debab94cc64a9ad753e720865230fccf56eff38fa1e0')
    report = json.loads(before[paths[2]])
    records = {row['kind']: row for row in report['records']}
    rows = []
    check('exact_two_receipt_kinds', len(receipt['files']) == 2 and {row['kind'] for row in receipt['files']} == {'access', 'readiness'})
    with tarfile.open(fileobj=io.BytesIO(before[paths[0]]), mode='r:gz') as tar:
        check('exact_member_list', sorted(m.name for m in tar.getmembers()) == sorted(row['archive_member'] for row in receipt['files']))
        for source in receipt['files']:
            kind = source['kind']
            member = tar.getmember(source['archive_member'])
            check(kind + '.regular_code_member', member.isfile() and member.name.endswith('.py'))
            data = tar.extractfile(member).read()
            check(kind + '.source_byte_pin', sha(data) == source['sha256'] == records[kind]['recorded_script_sha256'])
            literal = prompt_literal(data)
            calls = records[kind]['calls']
            check(kind + '.recorded_calls_present', len(calls) > 0)
            check(kind + '.literal_matches_all_recorded_prompt_hashes', all(call['recorded_prompt_sha256'] == literal['sha256'] for call in calls))
            rows.append({'kind': kind, 'archive_member': member.name, 'script_sha256': sha(data),
                         'module_level_prompt_literal': literal, 'matching_recorded_calls': len(calls),
                         'dispatch_raw_sha256': records[kind]['dispatch_raw_sha256'],
                         'summary_raw_sha256': records[kind]['summary_raw_sha256']})
    for path, data in before.items():
        check('input_unchanged:' + path.name, path.read_bytes() == data)
    result = {'schema_version': 'audit038-static-prompt-literal-binding-v1',
              'reader_sha256': sha(Path(__file__).read_bytes()),
              'receipt_sha256': args.receipt_sha256, 'archive_sha256': receipt['archive_sha256'],
              'binding_report_sha256': receipt['binding_report_sha256'],
              'checks': checks, 'passed': len(checks), 'failed': 0, 'records': rows,
              'source_imports': 0, 'source_execution': False, 'model_calls': 0,
              'prompt_prose_in_report': False,
              'closes': ['Exact literal PROMPT UTF-8 bytes match recorded prompt hashes in all three corresponding saved calls.'],
              'limits': ['Static literal matching is not an attestation that the literal reached the provider.',
                         'No system, caller transformation, complete request or authenticated network execution reconstruction.',
                         'No immutable Git membership inferred; old035 reports and original038 map unchanged.']}
    with Path(args.out).open('x') as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'matching_recorded_calls': sum(row['matching_recorded_calls'] for row in rows)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('archive', 'receipt', 'receipt-sha256', 'binding-report', 'out'):
        parser.add_argument('--' + name, required=True)
    run(parser.parse_args())
