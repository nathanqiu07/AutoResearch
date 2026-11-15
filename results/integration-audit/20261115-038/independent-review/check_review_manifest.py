"""Verify the frozen review allowlist and compare independent prompt metadata."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

PIN = 'e7962a1defc312b40f2093c1b6ecdc45718ca86e136d99cdadfb4eec127af8a3'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--independent-addendum', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    checks, inputs = [], {}

    def check(name, value):
        checks.append({'check': name, 'passed': bool(value)})
        if not value:
            raise ValueError(name)

    manifest_bytes = (a.stage / 'review-input-manifest.json').read_bytes()
    check('frozen_manifest_pin', digest(manifest_bytes) == PIN)
    manifest = json.loads(manifest_bytes)
    check('54_frozen_review_inputs', len(manifest['files']) == manifest['file_count'] == 54)
    for name, pin in manifest['files'].items():
        path = PurePosixPath(name)
        check('safe_path:' + name, not path.is_absolute() and '..' not in path.parts)
        data = (a.stage / name).read_bytes()
        check('hash_and_size:' + name, digest(data) == pin['sha256'] and len(data) == pin['bytes'])
        inputs[name] = data
    original = json.loads(inputs['main-safe-manifest.json'])
    check('original26_unchanged', original['file_count'] == len(original['files']) == 26 and all(manifest['files'][n] == pin for n, pin in original['files'].items()))
    author = json.loads(inputs['probe-script-addendum/static-prompt-binding.json'])
    independent_bytes = a.independent_addendum.read_bytes()
    independent = json.loads(independent_bytes)
    check('independent47_passed', independent['passed'] == 47 and independent['failed'] == 0)
    ours = {x['kind']: x for x in independent['records']}
    for row in author['records']:
        other = ours[row['kind']]
        for name in ('archive_member', 'script_sha256', 'dispatch_raw_sha256', 'summary_raw_sha256'):
            check(row['kind'] + '.' + name, row[name] == other[name])
        literal = row['module_level_prompt_literal']
        check(row['kind'] + '.independent_prompt_metadata',
              literal == {'line': other['prompt_literal_line'], 'sha256': other['prompt_literal_sha256'], 'utf8_bytes': other['prompt_utf8_bytes']}
              and row['matching_recorded_calls'] == other['recorded_calls_bound'])
    for name, data in inputs.items():
        check('unchanged:' + name, (a.stage / name).read_bytes() == data)
    check('manifest_unchanged', (a.stage / 'review-input-manifest.json').read_bytes() == manifest_bytes)
    report = {'schema_version': 'independent038-review-input-check-v1',
              'passed': len(checks), 'failed': 0, 'checks': checks,
              'review_input_manifest_sha256': PIN, 'review_input_files': 54,
              'original_allowlist_files_unchanged': 26,
              'independent_addendum_sha256': digest(independent_bytes),
              'reader_sha256': digest(Path(__file__).read_bytes()),
              'source_execution': False, 'source_imports': 0, 'model_calls': 0}
    with a.out.open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, 'review_input_files': 54, 'original_allowlist_unchanged': True}))


if __name__ == '__main__':
    main()
