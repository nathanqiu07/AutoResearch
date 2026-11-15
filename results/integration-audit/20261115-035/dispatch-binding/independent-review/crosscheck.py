"""Bounded independent metadata check; never imports the reviewed checker/backend."""
import argparse
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path

PINS = {
    'safe-manifest.json': '95d5ca8be9107113b4e9b6f3b8e136ffc03a0dd3240a24f58269858d2516b980',
    'check_dispatch.py': '2df15f586f0cb6db42e5474c830e0f803d5fc9fac5b406c608644fbe2d0f1390',
    'final/report.json': 'f73ad4eb18d04a20e055debab94cc64a9ad753e720865230fccf56eff38fa1e0',
}
DATA = [
    ('access', 'c2325220e5e5107126b5e9402693f8fba0d173d5adaa2a7e6cfb952cb8d0ea05', 'bf9fe4406e47cb077e6c7bf964948d79c3c97e09d560b3efbc76492efd564471', '4886347fdc74eca0d7378e7a1ce57aacaf89c875dc334553deef2545c13179b1', ['gpt-6-sol', 'gpt-6-astra'], ['0.125', '0.5']),
    ('readiness', 'a7f9c9efee581ba5b9233df83682a73d93f19f909d2dfdf014d3e99bcd57d2bf', 'b2c169306768f2a21a2931d13c7dff8f542430a307a5ae7ad942c793067ba8db', '39d14e76f1828574f539d52d366b4e5da1d0bdb7da603d6feffb3691a5b9a668', ['gpt-6-luna'], ['0.02']),
]
def sha(b):
    return hashlib.sha256(b).hexdigest()
def canonical(v):
    return sha(json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode())
def unique_pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError('duplicate key')
        d[k] = v
    return d
def parse(b):
    return json.loads(b, object_pairs_hook=unique_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', required=True); ap.add_argument('--out', required=True)
    args = ap.parse_args(); stage = Path(args.stage); checks = []; read = {}
    def check(name, value):
        checks.append({'name': name, 'passed': bool(value)})
        if not value:
            raise AssertionError(name)
    def load(path, expected=None):
        p = Path(path); b = p.read_bytes(); read[str(p)] = sha(b)
        if expected is not None: check('hash:' + p.name, sha(b) == expected)
        return b
    for rel, expected in PINS.items(): load(stage / rel, expected)
    manifest = parse(load(stage / 'safe-manifest.json'))
    check('safe_manifest_count', manifest['file_count'] == len(manifest['files']) == 26)
    check('safe_paths_distinct', len({r['path'] for r in manifest['files']}) == 26)
    for row in manifest['files']:
        rel = Path(row['path'])
        check('safe_path:' + str(rel), not rel.is_absolute() and '..' not in rel.parts and 'private-replay' not in rel.parts)
        check('regular_file:' + str(rel), (stage / rel).is_file() and not (stage / rel).is_symlink())
        b = load(stage / rel, row['sha256']); check('size:' + str(rel), len(b) == row['bytes'])
    accessed = parse(load(stage / 'final/accessed-inputs.json'))
    inv = parse(load(stage / 'final-invocation.json')); argv = inv['argv']
    check('saved_returncode', inv['returncode'] == 0)
    def flag(s): return argv[argv.index(s) + 1]
    source = parse(load(flag('--source-reference'), flag('--source-reference-sha256')))
    check('source_metadata_pin', sha(Path(flag('--source-reference')).read_bytes()) == '73cfe25b30075a3fef51cc4f249f2572b736404d98ce32c96f11a5863d657a18')
    check('source_count', source['file_count'] == len(source['files']) == 92)
    backend = load(Path(flag('--source-root')) / 'autoresearch/taste/overnight/backends.py', source['files']['autoresearch/taste/overnight/backends.py'])
    check('backend_pin', sha(backend) == '6ece37e0a623e8d0a7e3b916925532d1c239a0a82269d98cc2d40fb8563a232d')
    pricing = next(ast.literal_eval(n.value) for n in ast.parse(backend).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PRICING_VERSION' for t in n.targets))
    inventories = []
    for kind in ['--dispatch-inventory', '--frozen-inputs']:
        x = parse(load(flag(kind), flag(kind + '-sha256'))); inventories.append(x)
        check(kind + ':unique_logical_paths', len(x['files']) == len({r['path'] for r in x['files']}))
        check(kind + ':input_set', canonical({r['path']: r['sha256'] for r in x['files']}) == x['input_set_sha256'])
    check('inventory_counts', [len(x['files']) for x in inventories] == [2, 500])
    check('four_exact_data_inputs', {r['sha256'] for r in accessed['files']} == {x[i] for x in DATA for i in [1, 3]} and len(accessed['files']) == 4)
    records = {}
    for row in accessed['files']:
        records[row['sha256']] = parse(load(row['read_path'], row['sha256']))
        check('relocated_read', row['read_path'] != row['path'] and '/private-replay/inputs/' in row['read_path'])
        check('input_membership', any(any(r['path'] == row['path'] and r['sha256'] == row['sha256'] and r['bytes'] == row['bytes'] for r in x['files']) for x in inventories))
    summaries = []
    for kind, raw, canon, summary_hash, models, allocations in DATA:
        d, s = records[raw], records[summary_hash]
        check(kind + ':canonical_to_frozen_summary', canonical(d) == canon == s['dispatch_sha256'])
        check(kind + ':ordered_models', [p['model'] for p in d['probes']] == [c['model'] for c in s['calls']] == models)
        check(kind + ':allocations', [str(p['max_usd']) for p in d['probes']] == allocations)
        check(kind + ':declared_settings', d['settings'] == {'max_tokens': 8192, 'reasoning': 'medium', 'timeout': 180})
        check(kind + ':runtime', d['runtime_commit'] == s['runtime_commit'] == source['commit'] == 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca')
        check(kind + ':backend', d['runtime_backend_sha256'] == s['runtime_backend_sha256'] == sha(backend))
        check(kind + ':script_recorded_only', d['script_sha256'] == s['script_sha256'] and d['script_sha256'] not in source['files'].values())
        check(kind + ':no_probe_text_or_script_path', not {'prompt', 'system', 'script_path'}.intersection(d) and all(not {'prompt', 'system'}.intersection(p) for p in d['probes']))
        check(kind + ':statuses_and_counts', s['status'] == 'complete' and d['max_calls'] == s['attempted_calls'] == len(s['calls']) == len(models) and all(c['status'] == 'complete' for c in s['calls']))
        for i, c in enumerate(s['calls']):
            expected = {'model': models[i], 'max_tokens': 8192, 'temperature': 0.0, 'timeout_cap_seconds': 180, 'enforced_settings': {'reasoning_effort': 'medium', 'store': False, 'tools': [], 'service_tier': 'default', 'temperature': 'not_sent', 'prompt_cache_options': {'mode': 'implicit', 'ttl': '30m'}, 'pricing_version': pricing, 'adapter_implementation_sha256': canonical(backend.decode())}}
            check(kind + ':settings:' + str(i), c['settings'] == expected and canonical(c['settings']) == c['settings_sha256'])
            cost = c['cost']; check(kind + ':cost:' + str(i), Decimal(str(cost['max_usd'])) == Decimal(allocations[i]) and Decimal(str(cost['spent_usd'])) + Decimal(str(cost['reserved_usd'])) <= Decimal(allocations[i]))
            check(kind + ':usage:' + str(i), cost['attempted_calls'] == 1 and cost['reported_usage_complete'] is True and cost['unknown_input_usage_attempts'] == cost['unknown_output_usage_attempts'] == 0)
        summaries.append({'kind': kind, 'models_in_order': models, 'per_probe_allocations_usd': allocations, 'dispatch_raw_sha256': raw, 'dispatch_canonical_sha256': canon, 'summary_raw_sha256': summary_hash})
    final = parse(load(stage / 'final/report.json'))
    check('saved_report_consistency', final['passed'] == len(final['checks']) == 38 and final['failed'] == 0 and all(r['passed'] is True for r in final['checks']))
    testinv = parse(load(stage / 'tests-invocation.json'))
    check('saved_test_evidence', testinv['returncode'] == 0 and 'Ran 5 tests' in (stage / 'tests.stderr.txt').read_text() and (stage / 'tests.stderr.txt').read_text().endswith('OK\n'))
    check('all_read_bytes_unchanged', all(sha(Path(p).read_bytes()) == h for p, h in read.items()))
    result = {'schema_version': 'audit035-independent-dispatch-review-crosscheck-v1', 'passed': len(checks), 'failed': 0, 'checks': checks, 'records': summaries, 'read_file_sha256': read, 'implementation_imports': 0, 'provider_calls': 0, 'saved_owner_checks_not_rerun': 38, 'saved_owner_synthetic_tests_not_rerun': 5}
    with Path(args.out).open('x') as f: json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0}))

if __name__ == '__main__': main()
