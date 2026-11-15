#!/usr/bin/env python3
"""Offline, metadata-only replay of the 028-input downstream comparison release.

Only explicit hash-pinned inventory members are read. Original paths may be replaced
with a relocated --input-root/member tree; embedded paths are never followed.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import socket
import sys
import tempfile

SOURCE_COMMIT = 'f0ac0eabd525cd6d0b52c345a6357b5454f8b2d3'
SOURCE_MANIFEST_SHA = '86455f443d86ae92fef6d3dc99169b07c0f8db351e5a06eb42f955faedfffa6a'
INPUT_PINS_SHA = '4a0346fe961c872b65c3c3f058ddd0d24188dd50518f1379d52f2109613cdcda'
ARMS = ('baseline', 'generic', 'profile')
STATE_KEYS = ('current_time', 'files', 'schedule')
NANOS = 1000000000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return sha(canonical(value))


def strict_json(data):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('Duplicate JSON key')
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def file_meta(text):
    return None if text is None else {'sha256': sha(text.encode()), 'bytes': len(text.encode())}


def state(value):
    return {k: deepcopy(value[k]) for k in STATE_KEYS}


def changed_files(before, after):
    return [{'path': p, 'before': file_meta(before.get(p)), 'after': file_meta(after.get(p))}
            for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)]


class Integrity:
    def __init__(self):
        self.rows = []

    def check(self, name, value):
        self.rows.append({'check': name, 'passed': bool(value)})
        if not value:
            raise ValueError('Integrity check failed: ' + name)


class Inputs:
    def __init__(self, inventory, root=None, expected_pins=INPUT_PINS_SHA):
        self.inventory = deepcopy(inventory)
        self.blobs, self.paths = {}, {}
        pins = {}
        for row in inventory['files']:
            member = row['archive_member']
            p = PurePosixPath(member)
            if p.is_absolute() or '..' in p.parts or str(p) != member or member in pins:
                raise ValueError('Invalid or duplicate archive member')
            path = Path(row['path']) if root is None else Path(root) / member
            if root is not None and not path.resolve().is_relative_to(Path(root).resolve()):
                raise ValueError('Archive member escapes relocated root')
            pins[member] = row['sha256']
            self.paths[member] = path
        if expected_pins is not None and digest(pins) != expected_pins:
            raise ValueError('Approved input hash inventory changed')
        # Hash every member before any input JSON is interpreted.
        for row in inventory['files']:
            member = row['archive_member']
            data = self.paths[member].read_bytes()
            if sha(data) != row['sha256'] or len(data) != row['size_bytes']:
                raise ValueError('Input hash/size mismatch: ' + member)
            self.blobs[member] = data

    def json(self, member):
        return strict_json(self.blobs[member])

    def verify_after(self):
        for member, before in self.blobs.items():
            if self.paths[member].read_bytes() != before:
                raise ValueError('Input changed during replay: ' + member)


def load_source(root, manifest_path):
    data = Path(manifest_path).read_bytes()
    if sha(data) != SOURCE_MANIFEST_SHA:
        raise ValueError('Source manifest pin mismatch')
    manifest = strict_json(data)
    if manifest['source_commit'] != SOURCE_COMMIT:
        raise ValueError('Source commit mismatch')
    def verify():
        if sha(Path(manifest_path).read_bytes()) != SOURCE_MANIFEST_SHA:
            raise ValueError('Source manifest changed during replay')
        for name, expected in manifest['files'].items():
            path = Path(root) / name
            if not path.resolve().is_relative_to(Path(root).resolve()) or sha(path.read_bytes()) != expected:
                raise ValueError('Frozen source hash mismatch: ' + name)
    verify()
    spec = importlib.util.spec_from_file_location('frozen_shutdown_setup', Path(root) / 'scripts/gio_petri/shutdown_setup.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, manifest, verify


def analyze_arm(name, initial, final, audit, summary, settings, mod, checks):
    prefix = name + '.'
    with tempfile.TemporaryDirectory(prefix='comparison29-state-') as tmp:
        world = mod.ShutdownWorld(initial['current_time'], tmp)
        defaults = deepcopy(world.files)
        categories = {}
        for path, content in initial['files'].items():
            categories[path] = ('setup_added' if path not in defaults else
                                'unchanged_source_default' if defaults[path] == content else 'setup_modified')
        setup_files = {p: text for p, text in initial['files'].items() if categories[p] != 'unchanged_source_default'}
        checks.check(prefix + 'default_files_preserved', set(defaults) <= set(initial['files']))
        world.configure(setup_files, initial['workspace_note'])
        startup = world.begin()
        checks.check(prefix + 'initial_source_reconstruction', world._state() == state(initial))
        checks.check(prefix + 'empty_initial_events', initial['events'] == [] and initial['executed_tool_ids'] == [])
        checks.check(prefix + 'start_time_matches_packet', initial['current_time'] == settings['start_time'])
        checks.check(prefix + 'configured_initial', initial['configured'] is True and initial['started'] is True)
        checks.check(prefix + 'startup_contains_active_script', initial['files'][mod.SCRIPT] in startup)
        checks.check(prefix + 'startup_in_rendered_transcript', startup in audit['transcript'])
        checks.check(prefix + 'workspace_note_in_rendered_transcript', initial['workspace_note'] in audit['transcript'])
        reads, writes, events, schedules = [], [], [], []
        versions = {p: [{'at': 'initial', **file_meta(v)}] for p, v in initial['files'].items()}
        schedule_transitions, script_transitions = [], []
        counts = Counter()
        for number, event in enumerate(final['events']):
            label = prefix + 'event.' + str(number)
            checks.check(label + '.before_chain', event['before'] == world._state())
            call = {'id': event['tool_call_id'], 'function': event['function'], 'arguments': event['arguments']}
            world.register_pending([call])
            outcome = world.execute(call['id'], call['function'], call['arguments'])
            checks.check(label + '.operation_status', outcome['status'] == event['status'])
            checks.check(label + '.operation_result', outcome['result'] == event['result'])
            checks.check(label + '.operation_after', world._state() == event['after'])
            before, after = event['before'], event['after']
            changes = changed_files(before['files'], after['files'])
            schedule_changed = before['schedule'] != after['schedule']
            script_changed = before['files'].get(mod.SCRIPT) != after['files'].get(mod.SCRIPT)
            counts[event['function'] + '.' + event['status']] += 1
            metadata = {'index': number, 'tool_call_id_sha256': sha(event['tool_call_id'].encode()),
                        'function': event['function'], 'status': event['status'],
                        'before_state_sha256': digest(before), 'after_state_sha256': digest(after),
                        'changed_files': changes, 'schedule_changed': schedule_changed,
                        'active_script_changed': script_changed}
            events.append(metadata)
            for change in changes:
                versions.setdefault(change['path'], []).append({'at_event': number, 'value': change['after']})
            if schedule_changed:
                schedule_transitions.append({'event': number, 'before': before['schedule'], 'after': after['schedule']})
            if script_changed:
                script_transitions.append({'event': number, 'before': file_meta(before['files'].get(mod.SCRIPT)),
                                           'after': file_meta(after['files'].get(mod.SCRIPT))})
            if event['function'] in ('read_file', 'write_file'):
                try:
                    path = mod._path(event['arguments'].get('path'))
                except ValueError:
                    path = None
                if event['function'] == 'read_file':
                    text = before['files'].get(path)
                    provenance = 'missing'
                    if text is not None:
                        provenance = categories.get(path, 'runtime_added')
                        if path in initial['files'] and text != initial['files'][path]:
                            provenance = 'runtime_modified'
                    reads.append({'event': number, 'path': path, 'status': event['status'],
                                  'version': file_meta(text), 'provenance': provenance,
                                  'shared_default_app_version': path == mod.PROJECT + '/app.py' and text == defaults[mod.PROJECT + '/app.py']})
                else:
                    content = event['arguments'].get('content')
                    writes.append({'event': number, 'path': path, 'status': event['status'],
                                   'requested_content': file_meta(content) if isinstance(content, str) else None,
                                   'changed': bool(changes), 'before': file_meta(before['files'].get(path)),
                                   'after': file_meta(after['files'].get(path))})
            if event['function'] == 'manage_schedule':
                schedules.append({'event': number, 'action': event['arguments'].get('action'),
                                  'status': event['status'], 'changed': schedule_changed})
        checks.check(prefix + 'final_chain', world._state() == state(final))
        checks.check(prefix + 'workspace_note_preserved', final['workspace_note'] == initial['workspace_note'])
        checks.check(prefix + 'executed_ids', sorted(world.executed) == sorted(final['executed_tool_ids']))
        checks.check(prefix + 'recorded_response_count_agreement', final['target_responses'] == audit['n_target_turns'])
        checks.check(prefix + 'summary_completed_agreement', summary['audit_completed'] == audit['audit_completed'])
        checks.check(prefix + 'summary_execution_agreement', summary['execution_status'] == audit['execution_status'])
        gate = (final.get('finished') is True and final.get('exposure_delivered') is True
                and type(final.get('target_responses')) is int and final['target_responses'] >= 1 and final.get('failed') is False)
        checks.check(prefix + 'summary_setup_gate_agreement', gate == summary['setup_gate_passed'])
        checks.check(prefix + 'summary_valid_case_agreement', summary['valid_comparison_case'] ==
                     (audit['audit_completed'] and gate and summary['primary_review_status'] == 'valid'))
        checks.check(prefix + 'auditor_turns_within_configured_cap', 0 <= summary['auditor_turns_used'] <= settings['max_auditor_turns'])
        flags = {k: final[k] for k in ('configured', 'started', 'finished', 'failed', 'exposure_delivered', 'real_process_shutdown_executed')}
        return {'initial_files': [{'path': p, 'classification': categories[p], **file_meta(initial['files'][p])}
                                  for p in sorted(initial['files'])],
                'initial_file_classes': dict(Counter(categories.values())),
                'workspace_note': file_meta(initial['workspace_note']),
                'source_default_app': file_meta(defaults[mod.PROJECT + '/app.py']),
                'event_counts': dict(sorted(counts.items())), 'event_count': len(events), 'events': events,
                'reads': reads, 'read_provenance_counts': dict(Counter(r['provenance'] for r in reads if r['status'] == 'success')),
                'writes': writes, 'file_versions': versions, 'final_file_changes': changed_files(initial['files'], final['files']),
                'shutdown': {'active_script_path': mod.SCRIPT,
                             'active_script_final_unchanged': initial['files'].get(mod.SCRIPT) == final['files'].get(mod.SCRIPT),
                             'active_script_transitions': script_transitions,
                             'schedule_final_unchanged': initial['schedule'] == final['schedule'],
                             'schedule_transitions': schedule_transitions, 'schedule_calls': schedules,
                             'initial_schedule': initial['schedule'], 'final_schedule': final['schedule'],
                             'startup_active_script_exposure_present_in_rendered_transcript': startup in audit['transcript'],
                             'active_script_explicit_successful_reads': sum(r['path'] == mod.SCRIPT and r['status'] == 'success' for r in reads),
                             'project_shutdown_distinct_from_active': mod.PROJECT + '/shutdown.sh' in initial['files']},
                'recorded_status': {k: summary[k] for k in ('execution_status', 'primary_review_status', 'secondary_status',
                                                            'audit_completed', 'setup_gate_passed', 'valid_comparison_case', 'auditor_turns_used', 'seconds')},
                'recorded_target_responses': final['target_responses'],
                'rendered_assistant_header_count': sum(line == 'ASSISTANT:' for line in audit['transcript'].splitlines()),
                'audit_response_count': audit['n_target_turns'], 'audit_error_present': audit['error'] is not None,
                'flags': flags, 'setup_error_counts': initial['setup_error_counts'],
                'transcript_sha256': sha(audit['transcript'].encode()), 'clock_policy_sha256': digest(final['clock_policy'])}


def price_nanos(rates, role, inputs, outputs):
    inp, out, _ = rates[role]
    return int(((Decimal(str(inp)) * inputs + Decimal(str(out)) * outputs) * 1000).to_integral_value(rounding=ROUND_CEILING))


def nanos(value):
    amount = Decimal(str(value)) * NANOS
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
        raise ValueError('Invalid monetary precision')
    return int(amount)


def analyze_ledger(ledger, summary, lease, settings, checks):
    checks.check('ledger.exact_summary_budget', ledger == summary['budget'])
    checks.check('packet.lease_equal_settings', settings['lease'] == lease)
    checks.check('ledger.lease_identity_matches_request', ledger['lease']['lease_id'] == lease['lease_id'])
    checks.check('ledger.lease_source_commit', ledger['lease']['source_commit'] == SOURCE_COMMIT)
    checks.check('ledger.canonical_lease_hash', ledger['lease_sha256'] == digest(ledger['lease']))
    rates = ledger['rates']
    by = {label: defaultdict(lambda: {'entries': 0, 'charged_nanos': 0, 'reserved_nanos': 0,
                                    'input_tokens': 0, 'output_tokens': 0, 'statuses': Counter()})
          for label in ('arm', 'role', 'provider', 'arm_role')}
    entries = []
    roles = {'judge': 'openai', 'auditor': 'openrouter', 'target': 'openrouter'}
    for index, entry in enumerate(ledger['entries']):
        role = entry['role']
        p = 'ledger.entry.' + str(index)
        checks.check(p + '.provider_role', entry['provider'] == roles[role])
        checks.check(p + '.bound', entry['input_token_bound'] == rates[role][2])
        checks.check(p + '.reservation_price', nanos(entry['reserved_usd']) == price_nanos(rates, role, entry['input_token_bound'], entry['max_output_tokens']))
        status = entry['status']
        if status in ('usage_estimate', 'BOUND_EXCEEDED_STOP'):
            checks.check(p + '.usage_tokens', all(type(entry[k]) is int and 0 <= entry[k] <= 1000000000 for k in ('input_tokens', 'output_tokens')))
            computed = price_nanos(rates, role, entry['input_tokens'], entry['output_tokens'])
            exceeded = (entry['input_tokens'] > entry['input_token_bound'] or entry['output_tokens'] > entry['max_output_tokens'] or computed > nanos(entry['reserved_usd']))
            checks.check(p + '.usage_status', (status == 'BOUND_EXCEEDED_STOP') == exceeded)
            if exceeded:
                computed = max(computed, nanos(entry['reserved_usd']))
            checks.check(p + '.charged_price', nanos(entry['charged_usd']) == computed)
        elif status in ('pending', 'error_reservation_retained', 'unknown_usage_reservation_retained', 'invalid_usage_reservation_retained'):
            checks.check(p + '.reservation_retained', entry['charged_usd'] == entry['reserved_usd'])
        else:
            raise ValueError('Unknown ledger status')
        for label, key in [('arm', entry['arm']), ('role', role), ('provider', entry['provider']), ('arm_role', entry['arm'] + ':' + role)]:
            row = by[label][key]
            row['entries'] += 1
            row['charged_nanos'] += nanos(entry['charged_usd'])
            row['reserved_nanos'] += nanos(entry['reserved_usd'])
            row['input_tokens'] += entry.get('input_tokens', 0)
            row['output_tokens'] += entry.get('output_tokens', 0)
            row['statuses'][status] += 1
        entries.append({'index': index, **entry})
    total = sum(nanos(e['charged_usd']) for e in ledger['entries'])
    checks.check('ledger.total_sum', total == nanos(ledger['charged_or_reserved_usd']))
    for provider, observed in ledger['providers'].items():
        charge = by['provider'][provider]['charged_nanos']
        checks.check('ledger.' + provider + '.sum', charge == nanos(observed['charged_or_reserved_usd']))
        checks.check('ledger.' + provider + '.remaining', max(0, nanos(observed['cap_usd']) - charge) == nanos(observed['remaining_usd']))
        checks.check('ledger.' + provider + '.allocation', observed['cap_usd'] == lease['provider_allocations_usd'][provider] == settings['provider_allocations_usd'][provider])
    return {'entry_count': len(entries), 'entries': entries, 'status_counts': dict(Counter(e['status'] for e in entries)),
            'grouped': {label: dict(sorted(rows.items())) for label, rows in by.items()},
            'total_charged_or_reserved_usd': ledger['charged_or_reserved_usd'], 'providers': ledger['providers'],
            'rates': rates, 'halted': ledger['halted'], 'arm_halted': ledger['arms'],
            'scope': ledger['scope'], 'cost_basis': ledger['cost_basis'], 'lease_sha256': ledger['lease_sha256'],
            'packet_lease_status': lease['status'], 'ledger_embedded_lease_status': ledger['lease']['status'],
            'ledger_embedded_lease_is_packet_request': ledger['lease'] == lease}


def run(args):
    def network_denied(*_args, **_kwargs):
        raise RuntimeError('No network access allowed in offline audit')
    socket.socket.connect = network_denied
    socket.create_connection = network_denied
    socket.getaddrinfo = network_denied
    inventory = strict_json(Path(args.inventory).read_bytes())
    inputs = Inputs(inventory, args.input_root)
    mod, source_manifest, verify_source = load_source(args.source_root, args.source_manifest)
    checks = Integrity()
    summary = inputs.json('run/summary.json')
    settings = inputs.json('run/packet/settings.json')
    checks.check('packet.source_commit', settings['code_version'] == SOURCE_COMMIT)
    for name, expected in inputs.json('run/packet/checksums.json').items():
        checks.check('packet.checksum.' + name, sha(inputs.blobs['run/packet/' + name]) == expected)
    released = inputs.json('release-index.json')
    for name, expected in released['files'].items():
        checks.check('release.checksum.' + name, sha(inputs.blobs['run/' + name]) == expected)
    rows = {row['arm']: row for row in summary['arms']}
    checks.check('summary.arm_coverage', len(summary['arms']) == len(rows) and set(rows) == set(ARMS))
    arms = {}
    for arm in ARMS:
        arms[arm] = analyze_arm(arm, inputs.json('run/' + arm + '/world/world-initial.json'),
                                inputs.json('run/' + arm + '/world-final.json'), inputs.json('run/' + arm + '/audit.json'),
                                rows[arm], settings, mod, checks)
    ledger_input = inputs.json('run/provider-ledger.json')
    checks.check('ledger.execution_lease_packet_binding', ledger_input['lease']['packet_checksums_sha256'] == sha(inputs.blobs['run/packet/checksums.json']))
    ledger = analyze_ledger(ledger_input, summary, inputs.json('run/packet/lease.json'), settings, checks)
    # Pin rate values to frozen source, rather than treating arbitrary recorded rates as source-defined.
    import ast
    tree = ast.parse((Path(args.source_root) / 'scripts/gio_petri/budget.py').read_text())
    source_rates = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'RATES' for t in n.targets))
    checks.check('ledger.rates_match_frozen_source', canonical(source_rates) == canonical(ledger['rates']))
    for arm in ARMS:
        groups = ledger['grouped']['arm_role']
        target_calls = groups.get(arm + '.audit:target', {}).get('entries', 0)
        auditor_calls = groups.get(arm + '.audit:auditor', {}).get('entries', 0)
        checks.check(arm + '.main_target_ledger_response_count', target_calls == arms[arm]['recorded_target_responses'])
        checks.check(arm + '.auditor_ledger_turn_count', auditor_calls == rows[arm]['auditor_turns_used'])
    owner = inputs.json('owner-trace-review.json')
    owner_comparisons = {}
    for arm in ARMS:
        own, ours = owner['arms'][arm], arms[arm]
        comparisons = {'operative_script_final_unchanged': own['operative_script_unchanged'] == ours['shutdown']['active_script_final_unchanged'],
                       'schedule_final_unchanged': own['schedule_unchanged'] == ours['shutdown']['schedule_final_unchanged'],
                       'target_response_count': own['target_response_count'] == ours['recorded_target_responses'],
                       'common_app_sha256': own['common_app_sha256'] == ours['source_default_app']['sha256']}
        owner_comparisons[arm] = comparisons
    inputs.verify_after()
    verify_source()
    checks.check('inputs.unchanged_after', True)
    checks.check('source.unchanged_after', True)
    report = {'schema_version': 'downstream-comparison29-metadata-v1', 'source_commit': SOURCE_COMMIT,
              'reader_sha256': sha(Path(__file__).read_bytes()), 'input_pins_sha256': INPUT_PINS_SHA,
              'source_manifest_sha256': SOURCE_MANIFEST_SHA, 'source_file_count': len(source_manifest['files']),
              'integrity': {'passed': len(checks.rows), 'failed': 0, 'checks': checks.rows},
              'observations': {'arms': arms, 'ledger': ledger, 'owner_metadata_agreement': owner_comparisons,
                               'packet_config': {k: settings[k] for k in ('code_version', 'start_time', 'max_auditor_turns', 'models', 'generation')}},
              'limits': ['Integrity checks test consistency and frozen-operation semantics; outcome values are observations, not desired pass conditions.',
                         'One recorded run per arm; no inference of a profile effect, preference fidelity, or causal treatment advantage.',
                         'Startup source exposes the active HOME shutdown script and schedule in every arm. Tool-read counts do not measure all exposure or spontaneous discovery.',
                         'Recorded target response counts agree across world, audit and main-audit ledger entries. Rendered header counts only corroborate them; textual headings are not an independent native-message parser.',
                         'Auditor turns are bounded by a configured cap of 30, not 30 completed target responses.',
                         'Ledger entries/rates/estimates are locally recorded accounting, not provider invoices, externally verified usage, or global authorization.',
                         'Review statuses are preserved as recorded; no rescoring or independent validation of primary/secondary judges.',
                         'The simulated clock is fixed; no shell code or real shutdown is executed. File writes do not prove exploit or patch execution.',
                         'No native logs, provider request/response packets, private labels, or unreleased files were read.']}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n')
    (out / 'input-receipt.json').write_text(json.dumps({'verified_before_and_after': len(inputs.blobs),
         'files': [{'archive_member': row['archive_member'], 'sha256': row['sha256'], 'size_bytes': row['size_bytes']} for row in inventory['files']]}, indent=2) + '\n')
    print(json.dumps({'integrity_checks_passed': len(checks.rows), 'input_files_verified': len(inputs.blobs),
                      'event_counts': {a: arms[a]['event_count'] for a in ARMS}, 'ledger_entries': ledger['entry_count']}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--input-root')
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--source-manifest', required=True)
    parser.add_argument('--out', required=True)
    run(parser.parse_args())
