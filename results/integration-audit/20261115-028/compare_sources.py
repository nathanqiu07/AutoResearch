#!/usr/bin/env python3
"""Pin/export source-only Git objects and compare uncertainty guard dependencies.

No source data, live job artifacts, credentials, environment or ledger access.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

NEW = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
OLD = '7bb1589127ba386d74dd00c029659f195ffe28b8'
GUARD_FILES = [
    'autoresearch/taste/overnight/backends.py', 'autoresearch/taste/overnight/runner.py',
    'autoresearch/taste/overnight/consumer.py', 'autoresearch/taste/overnight/contracts.py',
    'autoresearch/taste/overnight/registry.py', 'autoresearch/llm.py', 'autoresearch/taste/usermodel.py',
    'autoresearch/__init__.py', 'autoresearch/taste/__init__.py', 'autoresearch/taste/overnight/__init__.py',
    'tests/__init__.py', 'tests/test_overnight_contracts.py',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def declarations(raw):
    result = {}
    def walk(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                result[name] = ast.dump(node, include_attributes=False)
                if isinstance(node, ast.ClassDef):
                    walk(node.body, name + '.')
    walk(ast.parse(raw).body)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--old-source', type=Path, required=True)
    p.add_argument('--stage', type=Path, required=True)
    args = p.parse_args()
    stage = args.stage.resolve()
    source = stage / 'source'
    source.mkdir(parents=True, exist_ok=False)
    git = lambda *rest: subprocess.check_output(['/usr/bin/git', '-C', str(args.repo), *rest],
                          env={'PATH': '/usr/bin:/bin'}, stderr=subprocess.DEVNULL)
    assert git('rev-parse', NEW + '^{commit}').decode().strip() == NEW
    old_metadata = json.loads((args.old_source / 'AUDIT_SOURCE.json').read_text())
    assert old_metadata['source_commit'] == OLD
    assert all(sha((args.old_source / name).read_bytes()) == digest for name, digest in old_metadata['files'].items())
    # Source only. No handoff/data/results directories or runtime files copied.
    names = git('ls-tree', '-r', '-z', '--name-only', NEW, 'autoresearch', 'tests').decode().split('\0')
    hashes = {}
    for name in sorted(x for x in names if x.endswith('.py')):
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        raw = git('show', NEW + ':' + name)
        dest = source / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        hashes[name] = sha(raw)
    (source / 'AUDIT_SOURCE.json').write_text(json.dumps({'source_commit': NEW, 'implementation_commit': NEW,
        'method': 'immutable git show of tracked autoresearch/tests Python files only', 'files': hashes}, indent=2, sort_keys=True) + '\n')
    differences, symbols = [], {}
    (stage / 'diffs').mkdir()
    for name in GUARD_FILES:
        before, after = (args.old_source / name).read_bytes(), (source / name).read_bytes()
        row = {'path': name, 'old_sha256': sha(before), 'new_sha256': sha(after), 'byte_identical': before == after}
        if before != after:
            target = 'diffs/' + name.replace('/', '__') + '.diff'
            diff = ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                               fromfile=OLD + '/' + name, tofile=NEW + '/' + name))
            (stage / target).write_text(diff)
            row['diff_path'] = target
        differences.append(row)
        old_decls, new_decls = declarations(before), declarations(after)
        symbols[name] = {'unchanged': sorted(k for k in old_decls.keys() & new_decls.keys() if old_decls[k] == new_decls[k]),
                         'changed': sorted(k for k in old_decls.keys() & new_decls.keys() if old_decls[k] != new_decls[k]),
                         'added': sorted(new_decls.keys() - old_decls.keys()), 'removed': sorted(old_decls.keys() - new_decls.keys())}
    # Record all package imports that can initialize when the fixtures import
    # the guard. Conservative static closure includes function-local imports;
    # it is broader than the particular dynamic path, not a complete call graph.
    all_paths = set(hashes)
    def modules(parts):
        if not parts:
            return []
        base = '/'.join(parts)
        return [x for x in (base + '.py', base + '/__init__.py') if x in all_paths]
    queue, seen = list(GUARD_FILES), set()
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        package = name.split('/')[:-1]
        tree = ast.parse((source / name).read_bytes())
        deps = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    parts = alias.name.split('.')
                    for end in range(1, len(parts) + 1):
                        deps.update(modules(parts[:end]))
            elif isinstance(n, ast.ImportFrom):
                base = package[:len(package) - n.level + 1] if n.level else []
                parts = base + (n.module.split('.') if n.module else [])
                deps.update(modules(parts))
                for alias in n.names:
                    deps.update(modules(parts + [alias.name]))
        queue.extend(deps - seen)
    closure = []
    for name in sorted(seen):
        old_path = args.old_source / name
        closure.append({'path': name, 'new_sha256': hashes[name],
                        'old_sha256': sha(old_path.read_bytes()) if old_path.exists() else None,
                        'byte_identical': old_path.exists() and sha(old_path.read_bytes()) == hashes[name]})
    report = {'old_source_commit': OLD, 'new_source_commit': NEW, 'source_files_exported': len(hashes),
              'guard_files': differences, 'declaration_comparisons': symbols, 'conservative_import_closure': closure,
              'scope': 'Source/dependency comparison only; no actual failure artifacts or live process/SQLite state inspected.',
              'compare_script_sha256': sha(Path(__file__).read_bytes())}
    (stage / 'source-comparison.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'source_files_exported': len(hashes), 'changed_guard_files': [x['path'] for x in differences if not x['byte_identical']],
                      'import_closure_files': len(closure), 'changed_import_closure': [x['path'] for x in closure if not x['byte_identical']]}, indent=2))


if __name__ == '__main__':
    main()
