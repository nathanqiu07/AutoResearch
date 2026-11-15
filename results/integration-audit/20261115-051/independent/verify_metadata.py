#!/usr/bin/env python3
"""Static audit of only the staged metadata and its enumerated public Git blobs."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(data):
    return hashlib.sha256(data).hexdigest()


def functions(tree):
    result = {}
    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + node.name
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[name] = node
                visit(node.body, name + '.')
    visit(tree.body)
    return result


def call_names(node):
    def name(value):
        if isinstance(value, ast.Name):
            return value.id
        if isinstance(value, ast.Attribute):
            return name(value.value) + '.' + value.attr
        return '<expression>'
    return [(call.lineno, name(call.func), call) for call in ast.walk(node) if isinstance(call, ast.Call)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    stage = Path(args.stage)
    out = Path(args.out)
    checks, commands = [], []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
    manifest_raw = (stage / 'safe-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    metadata = {}
    inputs = []
    check('manifest_count', manifest['file_count'] == len(manifest['files']) == 5)
    expected_names = {'README.md', 'assessment.json', 'call-sites.json', 'comparison.json', 'source-pins.json'}
    check('manifest_exact_named_files', set(manifest['files']) == expected_names)
    for name, pin in manifest['files'].items():
        path = stage / name
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        check('manifest_pin:' + name, digest(raw) == pin['sha256'] and len(raw) == pin['size_bytes'])
        metadata[name] = raw
        inputs.append({'path': name, 'sha256': digest(raw), 'size_bytes': len(raw)})
    pins = json.loads(metadata['source-pins.json'])
    comparison = json.loads(metadata['comparison.json'])
    sites = json.loads(metadata['call-sites.json'])
    assessment = json.loads(metadata['assessment.json'])
    blobs, trees, symbols = {}, {}, {}
    for pin in pins['git_blobs']:
        key = (pin['commit'], pin['path'])
        assert key not in blobs
        argv = ['git', '-C', pins['repository_context'], 'cat-file', 'blob', pin['commit'] + ':' + pin['path']]
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commands.append({'argv': argv, 'exit_code': proc.returncode,
                         'stdout_sha256': digest(proc.stdout), 'stdout_size_bytes': len(proc.stdout),
                         'stderr_sha256': digest(proc.stderr), 'stderr_size_bytes': len(proc.stderr)})
        check('git_object_pin:' + ':'.join(key), proc.returncode == 0 and
              digest(proc.stdout) == pin['sha256'] and len(proc.stdout) == pin['size_bytes'])
        if proc.returncode or digest(proc.stdout) != pin['sha256']:
            raise RuntimeError('public_git_pin_mismatch')
        blobs[key] = proc.stdout
        trees[key] = ast.parse(proc.stdout.decode())
        symbols[key] = functions(trees[key])
    check('exact_named_git_blob_count', len(blobs) == 12)
    slices, derived = {}, []
    for entry in pins['function_slices']:
        key = (entry['commit'], entry['path'])
        node = symbols[key][entry['symbol']]
        selected = b''.join(blobs[key].splitlines(keepends=True)[node.lineno - 1:node.end_lineno])
        check('function_pin:' + entry['commit'] + ':' + entry['symbol'],
              node.lineno == entry['start_line'] and node.end_lineno == entry['end_line']
              and digest(selected) == entry['source_slice_sha256'])
        slices[(entry['commit'], entry['path'], entry['symbol'])] = selected
        derived.append({'commit': entry['commit'], 'path': entry['path'], 'symbol': entry['symbol'],
                        'start_line': node.lineno, 'end_line': node.end_lineno,
                        'sha256': digest(selected)})
    check('exact_slice_count', len(slices) == 30)
    commits = sorted({entry['commit'] for entry in pins['function_slices']})
    for entry in comparison['function_comparisons']:
        selected = [slices[(commit, entry['path'], entry['symbol'])] for commit in commits]
        check('three_way_function_equality:' + entry['symbol'],
              len(selected) == 3 and selected[0] == selected[1] == selected[2]
              and digest(selected[0]) == entry['source_slice_sha256']
              and entry['byte_identical_across_all_three_commits'] is True)
    current = pins['ref_at_start']
    old = '0a541515f71e519cad0e4b0629336fd28cb509f0'
    draft = '9616fe8a3c550664d8aae0b72c938d936c0a7347'
    check('recorded_current_pin_consistent', current == pins['ref_at_end'] == sites['current_local_origin_main']
          == assessment['current_local_origin_main'])
    for entry in comparison['whole_file_comparisons']:
        path = entry['path']
        if 'current_equals_main_like' in entry:
            check('whole_file_main_comparison:' + path,
                  (blobs[(current, path)] == blobs[(old, path)]) == entry['current_equals_main_like'])
        if 'current_equals_draft' in entry:
            check('whole_file_draft_comparison:' + path,
                  (blobs[(current, path)] == blobs[(draft, path)]) == entry['current_equals_draft'])
        if 'all_three_blobs_identical' in entry:
            check('whole_file_three_way:' + path,
                  (blobs[(current, path)] == blobs[(old, path)] == blobs[(draft, path)]) == entry['all_three_blobs_identical'])
    # Validate each cited interval uses an allowed object; source references are
    # metadata only. We do not issue the author's broad grep/tree-list commands.
    references = [item['evidence'] for item in sites['positive_legacy_route']]
    references += [item['reference'] for item in assessment['current_logic_notes']]
    for index, entry in enumerate(references):
        key = (entry['commit'], entry['path'])
        check('callsite_reference_in_named_blob:' + str(index), key in blobs and
              1 <= entry['start_line'] <= entry['end_line'] <= len(blobs[key].splitlines()))
    cli = symbols[(current, 'autoresearch/cli.py')]['cmd_research']
    cli_calls = call_names(cli)
    for name, line in [('load_user_model', 330), ('TasteAdvisor', 332), ('OpenResearcher', 375)]:
        check('explicit_cli_call:' + name, any(number == line and target == name for number, target, _ in cli_calls))
    constructor = next(call for line, name, call in cli_calls if name == 'OpenResearcher' and line == 375)
    check('cli_passes_advisor', any(kw.arg == 'advisor' and isinstance(kw.value, ast.Name)
                                  and kw.value.id == 'advisor' for kw in constructor.keywords))
    condition = next(node for node in ast.walk(cli) if isinstance(node, ast.If) and node.lineno == 328)
    condition_ast = ast.dump(condition.test, include_attributes=False)
    expected_condition = ast.dump(ast.parse('args.taste_mode == "model" and slug', mode='eval').body,
                                  include_attributes=False)
    check('cli_model_and_slug_guard', condition_ast == expected_condition)
    inner = next(node for node in ast.walk(condition) if isinstance(node, ast.If) and node.lineno == 331)
    check('cli_nonempty_model_guard', ast.dump(inner.test, include_attributes=False) ==
          ast.dump(ast.parse('um is not None', mode='eval').body, include_attributes=False))
    factory = symbols[(current, 'autoresearch/taste/methods/__init__.py')]['create_method']
    registry = next(node.value for node in ast.walk(factory) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'registry' for target in node.targets))
    registry_keys = [key.value for key in registry.keys]
    check('factory_exact_m0_to_m7_keys', registry_keys == ['m' + str(index) for index in range(8)])
    check('no_p8_entry_in_explicit_factory', not any(key.lower() == 'p8' for key in registry_keys))
    loader = symbols[(current, 'autoresearch/taste/usermodel.py')]['load_model']
    check('loader_calls_legacy_factory', any(target == 'create_method' for _, target, _ in call_names(loader)))
    for line, expression in [(197, 'body.get("version") != 1'), (200, 'body.get("backend") != model.backend_identity')]:
        node = next(node for node in ast.walk(loader) if isinstance(node, ast.If) and node.lineno == line)
        check('loader_guard:' + str(line), ast.dump(node.test, include_attributes=False) ==
              ast.dump(ast.parse(expression, mode='eval').body, include_attributes=False)
              and any(isinstance(item, ast.Raise) for item in node.body))
    loop = symbols[(current, 'autoresearch/research/loop.py')]
    for symbol, target in [('OpenResearcher._d1', 'self.advisor.d1_scores'),
                           ('OpenResearcher._decide', 'self.advisor.decide'),
                           ('OpenResearcher.__init__', 'TasteAdvisor'),
                           ('OpenResearcher.priority', 'self._tscore.get')]:
        check('loop_consumer:' + symbol, any(name == target for _, name, _ in call_names(loop[symbol])))
    advisor = symbols[(current, 'autoresearch/research/advisor.py')]
    consult = advisor['TasteAdvisor.consult']
    guarded = next(node for node in consult.body if isinstance(node, ast.Try))
    check('normalization_outside_predict_try', all(line > guarded.end_lineno for line, name, _ in call_names(consult)
                                                 if name in ('choice_index', '_prob', '_distribution')))
    for symbol in ('_prob', '_distribution'):
        handlers = [node for node in ast.walk(advisor[symbol]) if isinstance(node, ast.ExceptHandler)]
        caught = [[item.id for item in handler.type.elts] for handler in handlers]
        check('conversion_handlers_unchanged:' + symbol, caught == [['TypeError', 'ValueError']])
    features = advisor['TasteAdvisor.d1_scores']
    feature_advice = next(call for line, name, call in call_names(features) if name == 'Advice' and line == 149)
    check('feature_branch_marks_advice_usable', isinstance(feature_advice.args[3], ast.Constant)
          and feature_advice.args[3].value is True)
    check('no_isfinite_call_in_feature_d1', not any(name.endswith('isfinite') for _, name, _ in call_names(features)))
    check('same_log_score_transform', any(name == 'math.log' and line == 521 for line, name, _ in call_names(loop['OpenResearcher._d1'])))
    # Ensure staged evidence did not change while being checked.
    check('manifest_unchanged', (stage / 'safe-manifest.json').read_bytes() == manifest_raw)
    for name, raw in metadata.items():
        check('stage_unchanged:' + name, (stage / name).read_bytes() == raw)
    report = {
        'schema_version': 'audit051-bounded-independent-static-review-v1',
        'status': 'no_actionable_mismatch' if all(item['passed'] for item in checks) else 'mismatch',
        'checks_passed': sum(item['passed'] for item in checks), 'checks_total': len(checks), 'checks': checks,
        'input_manifest_sha256': digest(manifest_raw), 'staged_inputs': inputs,
        'git_blob_count': len(blobs), 'function_slice_count': len(slices), 'three_way_functions': 10,
        'function_hash_recipe': 'AST function lineno/end_lineno select whole source lines, preserving original indentation and final newline.',
        'derived_function_pins': derived, 'git_read_commands': commands,
        'manual_source_assessment': {
            'legacy_conditional_route_supported': True,
            'route': 'cmd_research model mode with slug and loaded model constructs TasteAdvisor and passes it into OpenResearcher; the model-mode constructor also permits the feature-profile fallback.',
            'unchanged_function_scope_supported': True,
            'legacy_normalization_notes_supported': True,
            'no_demonstrated_selected_p8_call_supported_as_narrow_non_demonstration': True,
            'explicit_factory_keys': registry_keys,
            'factual_overreach_identified': [],
            'qualification': 'No demonstrated selected P8 call is a limited source-inspection conclusion, not proof of global unreachability, absence of externally supplied adapters, or safety of another runtime.'},
        'not_independently_rechecked': [
            'Historical audit001 README body/pin: it has a local path but no enumerated commit/path Git object in source-pins.json; restricted review did not open it.',
            'The author-reported absence of two named tree directories and broader reference-search completeness: no extra tree listing or grep was authorized or performed.',
            'Historical failing probe outcomes, actual current-run input validity/failures, external runtime branches, remote HEAD, and P8 execution reachability.'],
        'scope': 'Only five staged metadata files, their manifest, and the exact twelve enumerated immutable public Git blobs; AST parsing without import or execution.',
        'new_source_body_copies': 0, 'source_imports_or_execution': 0, 'private_data_reads': 0, 'model_calls': 0,
        'argv': sys.argv, 'verifier_sha256': digest(Path(__file__).read_bytes())}
    with out.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'checks_passed': report['checks_passed'],
                      'checks_total': report['checks_total'], 'report_sha256': digest(out.read_bytes())}, sort_keys=True))
    return 0 if all(item['passed'] for item in checks) else 1


if __name__ == '__main__':
    sys.exit(main())
