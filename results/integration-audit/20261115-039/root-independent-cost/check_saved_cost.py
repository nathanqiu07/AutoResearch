"""Recompute saved call usage with the saved ledger rates, never current prices."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess


COMMIT = 'c80937c7f92dd6ad05eee319e64f16799f0a193e'
BASE = 'results/gio-matched-shutdown-05'
MANIFEST = '18ffab491bed3a6fe513b5aff9769152b93d9a1958cde45ed17ce27134c61230'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sha = lambda raw: hashlib.sha256(raw).hexdigest()

    def read(relative, expected=None):
        assert '..' not in Path(relative).parts and not Path(relative).is_absolute()
        raw = subprocess.check_output(['git', '-C', str(args.git_root), 'show',
                                       COMMIT + ':' + BASE + '/' + relative])
        if expected is not None:
            assert sha(raw) == expected
        return json.loads(raw), sha(raw)

    manifest, _ = read('artifact_checksums.json', MANIFEST)
    ledger, ledger_pin = read('provider-ledger.json', manifest['provider-ledger.json'])
    rates = ledger['rates']
    rows = []
    total = Decimal(0)
    cached_input_uncached_rate = Decimal(0)
    roles = Counter()
    for relative, pin in sorted(manifest.items()):
        match = re.fullmatch(r'(baseline|generic|profile)/(calls|secondary-calls|review-calls|environment-review-calls)/call-\d+-(auditor|target|judge)\.json', relative)
        if match is None:
            continue
        raw, _ = read(relative, pin)
        assert raw['error'] is None
        response = raw['response']
        usage = response['usage']
        role = match.group(3)
        input_key = 'input_tokens' if 'input_tokens' in usage else 'prompt_tokens'
        output_key = 'output_tokens' if 'output_tokens' in usage else 'completion_tokens'
        detail_key = input_key + '_details'
        input_tokens, output_tokens = usage[input_key], usage[output_key]
        cached = (usage.get(detail_key) or {}).get('cached_tokens') or 0
        assert all(type(x) is int and x >= 0 for x in (input_tokens, output_tokens, cached))
        assert cached <= input_tokens
        input_rate, output_rate = (Decimal(str(x)) for x in rates[role][:2])
        amount = (input_tokens * input_rate + output_tokens * output_rate) / Decimal(1000000)
        cached_amount = cached * input_rate / Decimal(1000000)
        total += amount
        cached_input_uncached_rate += cached_amount
        roles[role] += 1
        billing = response.get('billing')
        rows.append({'path': BASE + '/' + relative, 'sha256': pin, 'arm': match.group(1),
                     'role': role, 'raw_usage_input_path': 'response.usage.' + input_key,
                     'raw_usage_cached_path': 'response.usage.' + detail_key + '.cached_tokens',
                     'raw_usage_output_path': 'response.usage.' + output_key,
                     'input_tokens': input_tokens, 'cached_input_tokens': cached,
                     'output_tokens': output_tokens,
                     'all_input_at_saved_uncached_rate_usd': str(amount),
                     'cached_input_at_saved_uncached_rate_usd': str(cached_amount),
                     'raw_usage_cost': usage.get('cost'),
                     'billing_field_type': type(billing).__name__,
                     'billing_field_keys': sorted(billing) if isinstance(billing, dict) else None})
    assert len(rows) == len(ledger['entries']) == 78
    ledger_sum = sum(Decimal(str(r['charged_usd'])) for r in ledger['entries'])
    saved_total = Decimal(str(ledger['charged_or_reserved_usd']))
    assert abs(ledger_sum - saved_total) < Decimal('0.000000000001')
    report = {'publication_commit': COMMIT, 'manifest_sha256': MANIFEST,
              'provider_ledger_sha256': ledger_pin,
              'ledger_cost_basis': ledger['cost_basis'],
              'saved_rates_per_million': rates, 'saved_call_records': len(rows),
              'roles': dict(roles), 'cached_input_rows': sum(r['cached_input_tokens'] > 0 for r in rows),
              'paid_cached_input_rows': sum(Decimal(r['cached_input_at_saved_uncached_rate_usd']) > 0 for r in rows),
              'paid_cached_input_tokens': sum(r['cached_input_tokens'] for r in rows if Decimal(r['cached_input_at_saved_uncached_rate_usd']) > 0),
              'recorded_total_usd': str(saved_total),
              'all_raw_input_at_same_saved_uncached_rates_usd': str(total),
              'difference_usd': str(total - saved_total),
              'cached_input_at_same_saved_uncached_rates_usd': str(cached_input_uncached_rate),
              'difference_equals_cached_component_with_rounding_tolerance': abs(total - saved_total - cached_input_uncached_rate) < Decimal('0.000000000001'),
              'rows': rows,
              'limits': ['Arithmetic over saved records and saved configured rates only; not current pricing, an invoice or authenticated provider traffic.',
                         'This check does not identify third-party normalizer source or join individual ledger entries to calls.',
                         'An all-input uncached-rate estimate is not the actual cached-input price; no budget-overrun claim.'],
              'model_calls': 0}
    with args.out.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['rows', 'limits', 'saved_rates_per_million']}))


if __name__ == '__main__':
    main()
