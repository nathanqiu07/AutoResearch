"""Audit committed baseline provenance using only pinned git object bytes.

Standard library plus git. No working-tree evidence, raw runs, private reports,
project imports, network calls, or inference. Output must be a new directory.
Exit 0 writes evidence; inspect report checks rather than treating exit 0 as a
scientific or exact-reconstruction verdict.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PREFIX = 'results/gio-baseline-review-01'
RUNTIME_PATHS = (
    'harness/petri/run_audits.py', 'harness/petri/transcript.py',
    'autoresearch/llm.py', 'autoresearch/research/measure.py',
    'autoresearch/research/petri_measure.py',
    'data/benchmarks/evaldetect_probes.json', 'harness/petri/requirements.txt',
    'eval/vendor/VERSIONS.txt', 'eval/vendor/petri-v2.tar.gz',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class GitSource:
    def __init__(self, root, commit):
        self.root = Path(root).resolve()
        self.commands = []
        self.commit = self.resolve(commit)

    def git(self, *args, missing_ok=False):
        argv = ['git', '--no-optional-locks', '-C', str(self.root), *args]
        env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0',
                   GIT_NO_REPLACE_OBJECTS='1')
        result = subprocess.run(argv, capture_output=True, env=env)
        self.commands.append({'argv': argv, 'exit_code': result.returncode,
                              'stdout_bytes': len(result.stdout),
                              'stdout_sha256': sha(result.stdout),
                              'stderr': result.stderr.decode('utf-8', errors='replace')})
        if result.returncode:
            if missing_ok:
                return None
            raise ValueError(result.stderr.decode('utf-8', errors='replace').strip())
        return result.stdout

    def resolve(self, revision):
        return self.git('rev-parse', '--verify', '--end-of-options',
                        revision + '^{commit}').decode().strip()

    def read_tree(self, prefix, commit=None):
        revision = commit or self.commit
        listing = self.git('ls-tree', '-rz', '--full-tree', revision, '--', prefix)
        result = {}
        for entry in listing.split(b'\0'):
            if not entry:
                continue
            metadata, path = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            name = path.decode()
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError('Evidence must be ordinary committed files: ' + name)
            if not name.startswith(prefix.rstrip('/') + '/'):
                raise ValueError('Unexpected git tree path: ' + name)
            relative = name[len(prefix.rstrip('/')) + 1:]
            result[relative] = self.git('cat-file', 'blob', oid)
        return result

    def read_file(self, path, commit=None):
        return self.git('cat-file', 'blob', (commit or self.commit) + ':' + path,
                        missing_ok=True)


def parse(data):
    return json.loads(data.decode('utf-8'))


def check_manifest(files, manifest):
    entries = []
    for name, expected in sorted(manifest.items()):
        actual = sha(files[name]) if name in files else None
        entries.append({'path': name, 'expected_sha256': expected,
                        'actual_sha256': actual, 'matches': actual == expected})
    return {'checked': len(entries), 'matching': sum(x['matches'] for x in entries),
            'entries': entries}


def setting_differences(prepared, executed):
    def side(obj, key):
        return {'present': True, 'value': obj[key]} if key in obj else {'present': False}
    return {key: {'prepared': side(prepared, key), 'executed': side(executed, key)}
            for key in sorted(prepared.keys() | executed.keys())
            if side(prepared, key) != side(executed, key)}


def audit(source):
    files = source.read_tree(PREFIX)
    if not files:
        raise ValueError('No committed baseline artifacts at the requested source commit')
    settings = parse(files['settings.json'])
    prepared = parse(files['packet/settings.json'])
    version = files['CODE_VERSION'].decode().strip()
    resolved_version = source.resolve(version)
    summary = parse(files['summary.json'])
    manifests = {}
    for name, subdir in (('artifact_checksums.json', ''), ('runner_checksums.json', 'runner_source/'),
                         ('packet/checksums.json', 'packet/')):
        subset = {key[len(subdir):]: value for key, value in files.items() if key.startswith(subdir)}
        manifests[name] = check_manifest(subset, parse(files[name]))
    runner = []
    for path, data in sorted(files.items()):
        if path.startswith('runner_source/') and path.endswith('.py'):
            script_path = 'scripts/gio_petri/' + path.split('/')[-1]
            historical = source.read_file(script_path, resolved_version)
            published = source.read_file(script_path)
            runner.append({'path': path, 'sha256': sha(data),
                           'present_at_code_version': historical is not None,
                           'code_version_sha256': sha(historical) if historical is not None else None,
                           'source_commit_script_sha256': sha(published) if published is not None else None,
                           'matches_source_commit_script': data == published})
    runtime = []
    for path in RUNTIME_PATHS:
        data = source.read_file(path, resolved_version)
        runtime.append({'path': path, 'present_at_code_version': data is not None,
                        'sha256': sha(data) if data is not None else None})
    readme_path = 'docs/user-models/baseline-review-01/README.md'
    readme = source.read_file(readme_path)
    vendor = source.read_file('eval/vendor/VERSIONS.txt', resolved_version)
    covered = set(parse(files['artifact_checksums.json']))
    return {
        'scope': 'committed artifact provenance only; no measurement interpretation',
        'source_commit': source.commit,
        'artifact_path': PREFIX,
        'evidence_reads': 'pinned git objects only; no local raw or working-tree evidence',
        'file_inventory': [{'path': path, 'bytes': len(data), 'sha256': sha(data)}
                           for path, data in sorted(files.items())],
        'manifests': manifests,
        'uncovered_files_excluding_manifest_itself': sorted(set(files) - covered - {'artifact_checksums.json'}),
        'code_versions': {
            'CODE_VERSION': version, 'resolved_execution_commit': resolved_version,
            'executed_settings': settings.get('code_version'),
            'execution_matches': version == settings.get('code_version'),
            'prepared_packet': prepared.get('code_version'),
            'preserved_prepared_version': settings.get('prepared_packet_code_version'),
            'preparation_matches': prepared.get('code_version') == settings.get('prepared_packet_code_version'),
        },
        'preparation_to_execution_differences': setting_differences(prepared, settings),
        'fixed_settings_equal': {key: key in settings and key in prepared and settings[key] == prepared[key]
                                 for key in ('models', 'routing', 'generation', 'seed_id')},
        'summary_is_single_score_record': summary == [parse(files['baseline/score.json'])],
        'summary_contains_code_version': any('code_version' in row for row in summary),
        'runner_sources': runner,
        'runtime_sources_at_code_version': runtime,
        'saved_dependency_metadata': parse(files['dependencies.json']),
        'vendor_versions_at_code_version': vendor.decode().strip() if vendor is not None else None,
        'committed_readme': {'path': readme_path, 'sha256': sha(readme) if readme else None,
                             'documents_local_raw_location': bool(readme and b'runs/gio-baseline-review-01/' in readme)},
        'reconstruction_limits': [
            'Runner snapshots supplement the execution commit; CODE_VERSION alone does not include them.',
            'Saved package versions do not attest the complete installed environment, Python version, or package source hashes.',
            'A vendored Petri source commit does not prove that exact source was installed for execution.',
            'These records do not attest all execution-time imported source bytes or an execution-time working-tree diff.',
            'Local raw records are outside this reproducer scope and are not inspected or verified.',
        ],
        'statistical_comparability': 'not_assessed',
    }


def findings(report):
    checks = '\n'.join('- `%s`: %s/%s hashes match.' % (name, value['matching'], value['checked'])
                       for name, value in report['manifests'].items())
    versions = report['code_versions']
    gaps = '\n'.join('- ' + line for line in report['reconstruction_limits'])
    fixed = ', '.join('%s=%s' % (key, value) for key, value in report['fixed_settings_equal'].items())
    return f'''# Baseline committed-evidence provenance

Source commit: `{report['source_commit']}`. Artifact path: `{PREFIX}`.
All {len(report['file_inventory'])} artifact files were read from this commit's git
objects. Working-tree contents and local raw records were not inspected.

{checks}
- Files outside the artifact manifest, excluding the manifest itself: {report['uncovered_files_excluding_manifest_itself']}.
- Execution version agrees with settings: {versions['execution_matches']} (`{versions['CODE_VERSION']}`).
- Copied preparation version agrees with `prepared_packet_code_version`: {versions['preparation_matches']} (`{versions['prepared_packet']}`).
- Preparation-to-execution differences: {len(report['preparation_to_execution_differences'])} top-level fields, all preserved in `report.json`.
- Fixed settings agree: {fixed}.
- Summary equals the single score record: {report['summary_is_single_score_record']}.
- Runner snapshots present: {len(report['runner_sources'])}; absent from execution commit: {sum(not row['present_at_code_version'] for row in report['runner_sources'])}; matching published scripts: {sum(row['matches_source_commit_script'] for row in report['runner_sources'])}.
- Committed README documents deliberately local raw records: {report['committed_readme']['documents_local_raw_location']}.

The older copied preparation code version is intentional metadata when the
preparation-version check passes. Saved runner code applies the baseline-only
execution settings and retains that preparation version. The complete settings
differences and runner hashes are available for review; no scientific approval
is inferred from a passing integrity check.

The saved runner computes its repository root relative to its file. To reconstruct
the source layout, restore the archived runner files under `scripts/gio_petri/`,
alongside the recorded execution commit, instead of executing the archive in place.

Reconstruction limits:

{gaps}

`command.json` records this invocation and tool hash. `git-commands.json` records
every git read, exit, stderr, and stdout hash. `stdout.txt` and `stderr.txt` contain
the reproducer outcome. No network calls, inference, or project-module imports
were performed.
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(str(exc))
    source = None
    error = ''
    stdout = ''
    status = 0
    try:
        source = GitSource(args.source_root, args.source_commit)
        report = audit(source)
        (args.out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        (args.out / 'findings.md').write_text(findings(report))
        stdout = json.dumps({'source_commit': source.commit, 'public_files': len(report['file_inventory']),
                             'checksums': {key: [value['matching'], value['checked']]
                                           for key, value in report['manifests'].items()},
                             'statistical_comparability': 'not_assessed'}, indent=2) + '\n'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        status = 2
        error = type(exc).__name__ + ': ' + str(exc) + '\n'
    command = {'argv': [sys.executable, str(Path(__file__).resolve()), *(argv if argv is not None else sys.argv[1:])],
               'source_commit_requested': args.source_commit, 'exit_code': status,
               'tool_sha256': sha(Path(__file__).read_bytes()),
               'evidence_scope': 'committed git objects only; local raw records never read'}
    for name, data in (('command.json', command), ('git-commands.json', source.commands if source else [])):
        (args.out / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    (args.out / 'stdout.txt').write_text(stdout)
    (args.out / 'stderr.txt').write_text(error)
    sys.stdout.write(stdout)
    sys.stderr.write(error)
    return status


if __name__ == '__main__':
    sys.exit(main())
