#!/usr/bin/env python3
"""Retain only two explicitly released probe scripts; never import or run them."""
import argparse
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

PINS = {
    'access': '0e13af78f829d62c028750b87811fcec2438e06f1f80db3ea618297ff0f7de26',
    'readiness': '48f256d87f20c59dbfdf8601ff5bed1f2ec75ea603de472b792fd19acec6242a',
}
NAMES = {'access': 'neutral_api_probe.py', 'readiness': 'neutral_readiness_probe.py'}
REPORT_PIN = 'f73ad4eb18d04a20e055debab94cc64a9ad753e720865230fccf56eff38fa1e0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def screen(data):
    """Fail closed on recognized credential literals; report no literal values."""
    text = data.decode('utf-8')
    tree = ast.parse(text)
    findings = []
    pattern = r'-----BEGIN (?:[A-Z ]*PRIVATE KEY)|(?:sk|ghp|gho|ghu|github_pat)[-_][A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16}'
    if re.search(pattern, text):
        findings.append('recognized_credential_or_private_key_pattern')
    sensitive = re.compile(r'password|secret|api_key|credential|access_token|authorization', re.I)
    for node in ast.walk(tree):
        names = []
        value = None
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [n.id for target in targets for n in ast.walk(target) if isinstance(n, ast.Name)]
            value = node.value
        elif isinstance(node, ast.keyword):
            names, value = [node.arg or ''], node.value
        if any(sensitive.search(name) for name in names) and isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
            findings.append('sensitive_literal_binding_at_line_' + str(node.lineno))
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and sensitive.search(key.value) and isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
                    findings.append('sensitive_literal_dict_value_at_line_' + str(node.lineno))
    if findings:
        raise ValueError('Credential screen rejected input: ' + ', '.join(findings))
    return {'python_ast_parse': 'passed', 'recognized_credential_patterns': 0,
            'sensitive_nonempty_literal_bindings': 0,
            'scope': 'Static literal screening only; no environment access, imports or execution.'}


def run(args):
    out = Path(args.out_dir)
    if out.exists():
        raise ValueError('Output directory already exists')
    report_path = Path(args.binding_report)
    report_bytes = report_path.read_bytes()
    if sha(report_bytes) != REPORT_PIN:
        raise ValueError('Binding report pin mismatch')
    report = json.loads(report_bytes)
    if report['passed'] != 38 or report['failed'] != 0:
        raise ValueError('Unexpected prior report result')
    records = {row['kind']: row for row in report['records']}
    payloads, rows = {}, []
    for kind in ('access', 'readiness'):
        path = Path(getattr(args, kind + '_script'))
        data = path.read_bytes()
        if sha(data) != PINS[kind]:
            raise ValueError(kind + ' source pin mismatch')
        screened = screen(data)
        record = records[kind]
        if record['recorded_script_sha256'] != PINS[kind]:
            raise ValueError(kind + ' historical script hash mismatch')
        member = 'scripts/' + NAMES[kind]
        payloads[member] = data
        rows.append({'kind': kind, 'original_path': str(path), 'archive_member': member,
                     'sha256': sha(data), 'bytes': len(data), 'sha256_before': sha(data),
                     'sha256_after': None, 'credential_literal_screen': screened,
                     'dispatch_raw_sha256': record['dispatch_raw_sha256'],
                     'dispatch_canonical_sha256': record['dispatch_canonical_sha256'],
                     'summary_raw_sha256': record['summary_raw_sha256'],
                     'summary_script_sha256_via_pinned035_report': record['recorded_script_sha256'],
                     'immutable_git_membership': 'not_claimed'})
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for member, data in sorted(payloads.items()):
            info = tarfile.TarInfo(member)
            info.size, info.mode, info.mtime, info.uid, info.gid = len(data), 0o644, 0, 0, 0
            tar.addfile(info, io.BytesIO(data))
    raw = buf.getvalue()
    archive = gzip.compress(raw, mtime=0)
    for row in rows:
        after = Path(row['original_path']).read_bytes()
        row['sha256_after'] = sha(after)
        if after != payloads[row['archive_member']]:
            raise ValueError('Original changed during capture')
    if report_path.read_bytes() != report_bytes:
        raise ValueError('Binding report changed during capture')
    receipt = {'schema_version': 'audit038-probe-script-retention-v1',
               'archive_file': 'probe-scripts.tar.gz', 'archive_sha256': sha(archive),
               'archive_bytes': len(archive), 'uncompressed_tar_sha256': sha(raw),
               'source_file_count': len(rows), 'source_bytes': sum(row['bytes'] for row in rows),
               'files': rows, 'binding_report_sha256': REPORT_PIN,
               'binding_report_public_path': 'results/integration-audit/20261115-035/dispatch-binding/final/report.json',
               'binding_source': 'Prior035 report verified raw/canonical dispatch and saved summary linkage; no raw data records reopened here.',
               'reader_sha256': sha(Path(__file__).read_bytes()),
               'model_calls': 0, 'source_imports': 0, 'source_execution': False,
               'environment_or_credentials_read': False,
               'closes': ['Exact two script-byte recovery at the previously recorded hashes.'],
               'limits': ['No immutable Git membership is inferred.',
                          'No authenticated network execution, credentials, invoice or provider availability is proved.',
                          'Probe input reconstruction was not performed; unknown build-request joins remain outside scope.',
                          'Original038 maps and audit035 artifacts remain unchanged.']}
    out.mkdir()
    (out / 'probe-scripts.tar.gz').write_bytes(archive)
    (out / 'retention-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'files': len(rows), 'source_bytes': receipt['source_bytes'],
                      'archive_sha256': sha(archive), 'originals_unchanged': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('access-script', 'readiness-script', 'binding-report', 'out-dir'):
        parser.add_argument('--' + name, required=True)
    run(parser.parse_args())
