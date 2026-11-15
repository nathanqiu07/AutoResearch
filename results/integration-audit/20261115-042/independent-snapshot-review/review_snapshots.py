"""Compare exactly three pinned closed metadata snapshots; follow no pointers."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

PINS = {
    'index': '4681691129419c503c789efff4ad5aa66707b791004465823556844ed9d90461',
    'supervisor': '3646c813067dfce2c805e8de764e0d77c3b824d5ee2d4615304910c34a165076',
    'ledger': '4e35ccbe5d9bcc2cd4e66bd624fc620fc2440cb8840d05667966325362e58960',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Nonfinite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def usd_nanos(value):
    n = Decimal(str(value)) * 10**9
    if not n.is_finite() or n != n.to_integral_value():
        raise ValueError('Usage does not resolve to integer nanodollars')
    return int(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('index', 'supervisor', 'ledger', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    checks, raw, inputs = [], {}, []

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise ValueError(name)

    for name, pin in PINS.items():
        path = getattr(a, name)
        raw[name] = path.read_bytes()
        check(name + '.approved_raw_pin', sha(raw[name]) == pin)
        inputs.append({'role': name, 'path': str(path), 'sha256': pin, 'bytes': len(raw[name])})
    index, supervisor, ledger = (strict(raw[k]) for k in ('index', 'supervisor', 'ledger'))
    jobs, batches = index['jobs'], index['batches']
    rows = ledger['reservation_rows']
    check('index_schema_runtime_scope', index['schema_version'] == 'profile204-completion-provenance-v1' and index['runtime_sha'] == 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca' and index['source_condition'] == 'richer-fit-v1')
    check('three_terminal_statuses', index['status'] == 'complete_known_accounting' and supervisor['status'] == 'complete' and ledger['status'] == 'complete_no_pending_or_unknown')
    check('supervisor_pin_from_index', index['supervisor_terminal']['sha256'] == PINS['supervisor'])
    check('same_prepared_index_metadata', index['prepared_index'] == supervisor['index'])
    check('204_unique_complete_jobs', len(jobs) == len({j['job_id'] for j in jobs}) == 204 and Counter(j['status'] for j in jobs) == {'complete': 204})
    check('four_unique_batches', len(batches) == len({b['batch_id'] for b in batches}) == 4)
    batch_ids = {b['batch_id'] for b in batches}
    check('job_batch_membership', all(j['batch_id'] in batch_ids for j in jobs))
    check('supervisor_batch_membership', set(supervisor['completed_verified_batches']) == {b['batch_id'] + '-verified.json' for b in batches} and len(supervisor['completed_verified_batches']) == 4)
    check('supervisor_terminal_flags', supervisor['child_process_terminal'] is True and supervisor['native_accounting_drain_verified'] is True and supervisor['no_retry_or_resume'] is True and supervisor['stop_reason'] is None)
    requests = [r for j in jobs for r in j['requests']]
    check('672_complete_request_slots', len(requests) == sum(j['planned_request_count'] for j in jobs) == 672 and Counter(r['status'] for r in requests) == {'complete': 672})
    check('each_job_request_slots_and_usage_attempts', all(len(j['requests']) == j['planned_request_count'] == j['usage']['attempted_calls'] for j in jobs))
    check('all_request_digests_are_hashes', all(re.fullmatch('[0-9a-f]{64}', r['request_sha256']) for r in requests))
    request_counter = Counter(r['request_sha256'] for r in requests)
    check('672_unique_request_identities', len(request_counter) == 672 and set(request_counter.values()) == {1})
    check('ledger672_unique_reservations', len(rows) == len({r[0] for r in rows}) == 672 and all(isinstance(r, list) and len(r) == 5 for r in rows))
    check('ledger_row_numeric_columns', all(type(r[1]) is int and type(r[2]) is int and r[1] >= 0 and r[2] >= 0 for r in rows))
    check('all_ledger_rows_complete', Counter(r[3] for r in rows) == {'complete': 672})
    metadata = [strict(r[4]) for r in rows]
    check('ledger_metadata_exact_keys', all(set(m) == {'model', 'reasoning', 'request_sha256'} for m in metadata))
    ledger_counter = Counter(m['request_sha256'] for m in metadata)
    check('exact_request_multiset_join', request_counter == ledger_counter)
    index_execution = Counter((r['request_sha256'], j['backend']['model'], j['backend']['reasoning']) for j in jobs for r in j['requests'])
    ledger_execution = Counter((m['request_sha256'], m['model'], m['reasoning']) for m in metadata)
    check('request_model_reasoning_multiset_join', index_execution == ledger_execution)
    ledger_cost = {m['request_sha256']: row[2] for m, row in zip(metadata, rows)}
    check('each_job_cost_joins_ledger', all(sum(ledger_cost[r['request_sha256']] for r in j['requests']) == usd_nanos(j['usage']['reported_api_usd']) for j in jobs))
    job_cost = sum(usd_nanos(j['usage']['reported_api_usd']) for j in jobs)
    ledger_cost_total = sum(r[2] for r in rows)
    batch_cost = sum(b['known_spent_nanos'] for b in batches)
    check('all_known_usage_totals_equal', job_cost == ledger_cost_total == batch_cost == index['counts']['verified_known_spent_nanos'] == supervisor['known_verified_spend_nanos'] == ledger['known_spent_nanos'] == 124590125)
    check('all_attempt_denominators_equal', sum(j['usage']['attempted_calls'] for j in jobs) == sum(b['attempted_calls'] for b in batches) == index['counts']['verified_attempted_calls'] == index['counts']['observed_terminal_attempts'] == supervisor['known_verified_attempts'] == ledger['attempts'] == 672)
    grouped = defaultdict(list)
    for job in jobs:
        grouped[job['batch_id']].append(job)
    batch_summary = []
    for batch in batches:
        subset = grouped[batch['batch_id']]
        check('batch_job_request_usage_counts:' + batch['batch_id'], len(subset) == batch['planned_jobs'] and sum(len(j['requests']) for j in subset) == batch['planned_requests'] == batch['attempted_calls'] and sum(usd_nanos(j['usage']['reported_api_usd']) for j in subset) == batch['known_spent_nanos'] and batch['known_verified'] is True)
        check('batch_diagnostic_count_metadata:' + batch['batch_id'], batch['diagnostics']['actual_open_events'] == batch['attempted_calls'])
        batch_summary.append({k: batch[k] for k in ('batch_id', 'planned_jobs', 'planned_requests', 'attempted_calls', 'known_spent_nanos')})
    check('index_count_summary_matches', index['counts']['job_status_counts'] == {'complete': 204} and index['counts']['request_status_counts'] == {'complete': 672} and index['counts']['planned_jobs'] == supervisor['planned_jobs'] == 204 and index['counts']['planned_requests'] == supervisor['planned_call_ceiling'] == 672 and index['counts']['verified_batches'] == supervisor['planned_batches'] == 4)
    check('no_pending_uncertain_or_current_holds', ledger['pending'] == ledger['uncertain'] == ledger['retained_hold_nanos'] == 0)
    check('job_usage_complete_no_unknown_or_reserved', all(j['usage']['reported_usage_complete'] is True and all(j['usage'][k] == 0 for k in ('cache_hits', 'uncertain_attempts', 'unknown_input_usage_attempts', 'unknown_output_usage_attempts', 'reserved_api_usd')) for j in jobs))
    check('request_cache_error_metadata', all(r['cache_provenance']['hit'] is False and r['error_code'] is None for r in requests) and index['counts']['observed_terminal_cache_hits'] == index['counts']['observed_terminal_unknown_attempts'] == 0)
    check('no_new_alias_observations_reported', all(j['new_independent_observations_from_aliases'] == 0 for j in jobs) and index['unchanged_planned_coverage']['additional_independent_observations_from_aliases'] == 0)
    coverage = index['unchanged_planned_coverage']
    check('closed_candidate_exclusion_counts', coverage['candidate_jobs_before_collision_exclusion'] - len(coverage['whole_jobs_excluded']) == 204 and coverage['candidate_requests_before_collision_exclusion'] - coverage['excluded_planned_request_count'] == 672)
    check('excluded_jobs_and_collision_requests_absent', not set(coverage['whole_jobs_excluded']) & {j['job_id'] for j in jobs} and all(c['request_sha256'] not in request_counter for c in coverage['unknown_collisions']))
    check('metadata_compiler_declares_no_scoring_calls_or_ledger_access', index['accuracy_or_selection_computed'] is False and index['model_calls_by_compiler'] == index['ledger_access_by_compiler'] == 0 and ledger['read_only_transaction'] is True)
    check('known_spend_below_recorded_ceiling', Decimal(job_cost) / 10**9 <= Decimal(supervisor['planned_dollar_ceiling']))
    for name in PINS:
        check(name + '.unchanged', getattr(a, name).read_bytes() == raw[name])
    result = {
        'schema_version': 'independent-profile204-closed-snapshot-review-v1', 'passed': len(checks), 'failed': 0, 'checks': checks,
        'reader_sha256': sha(Path(__file__).read_bytes()), 'inputs': inputs,
        'summary': {'unique_complete_jobs': 204, 'unique_complete_batches': 4, 'complete_request_slots': 672, 'unique_request_digests': 672, 'unique_complete_reservations': 672,
                    'known_spent_nanos': job_cost, 'known_spent_usd': format(Decimal(job_cost) / 10**9, 'f'), 'retained_hold_nanos': 0, 'pending': 0, 'uncertain': 0,
                    'historical_row1_amount_sum_nanos_not_added_to_spend_or_holds': sum(r[1] for r in rows),
                    'request_identity_multiset_sha256': sha(canonical(sorted(request_counter.items()))),
                    'request_model_reasoning_multiset_sha256': sha(canonical(sorted((list(k), v) for k, v in index_execution.items())))},
        'batches': batch_summary,
        'ledger_positional_contract': {'reservation_id': 0, 'historical_amount_not_current_hold': 1, 'amount_summing_to_recorded_known_spend': 2, 'status': 3, 'request_model_reasoning_json': 4},
        'limits': [
            'Only these three pinned closed snapshots were read. No referenced result/profile/trace/source/policy file, label or SQLite database was opened.',
            'Request digest equality is a metadata join, not independent reconstruction of effective prompts/settings or proof of physical authenticated HTTP calls.',
            'Row positions are interpreted from this fixed snapshot layout and corroborating totals; external ledger schema and logical_snapshot_sha256 recipe were not consulted or reconstructed.',
            'The row1 historical amount sum is not outstanding hold or additive cost; all rows are complete and the snapshot records zero retained holds.',
            'This finite continuation is not the full richer/sparse corpus. Earlier uncertain outcomes, holds, excluded plans and alias overlap are not reclassified or added.',
            'Supervisor closure/diagnostic events and compiler no-call flags are checked as saved metadata, not live process or provider attestations.',
            'No prediction scoring, control-binding re-audit, price/invoice validation or execution-quality inference.'],
        'referenced_paths_followed': 0, 'private_labels_read': False, 'active_ledger_read': False, 'model_calls': 0,
    }
    with a.out.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'passed': len(checks), 'failed': 0, **result['summary']}))


if __name__ == '__main__':
    main()
