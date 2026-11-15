"""Per-provider local allocation shared by all matched arms in one process.

The coordinator must issue nonoverlapping allocations before construction. This
module pins that receipt and enforces its local ceilings; it is not the project's
global allocator. Output files cannot be reopened to reset spending. The parent
ledger is authoritative and is persisted before its per-arm views.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import threading
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from uuid import uuid4

from budget import RATES


PROVIDERS = {'judge': 'openai', 'auditor': 'openrouter', 'target': 'openrouter'}
NANOS = 1_000_000_000


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _cap(value):
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError):
        finite = False
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not finite or value <= 0:
        raise ValueError('Allocation must be finite and positive')
    result = int((Decimal(str(value))*NANOS).to_integral_value(rounding=ROUND_FLOOR))
    if result <= 0:
        raise ValueError('Allocation is below ledger precision')
    return result


def _price(role, inputs, outputs):
    inp, out, _ = RATES[role]
    cost = (Decimal(str(inp))*inputs+Decimal(str(out))*outputs)*1000
    return int(cost.to_integral_value(rounding=ROUND_CEILING))


def _write(path, value, *, exclusive=False):
    data = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return
    temporary = path.with_name(path.name+'.tmp-'+uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class ProviderBudget:
    def __init__(self, path, allocations, lease):
        self.path = Path(path)
        if self.path.exists():
            raise FileExistsError('Refusing to reset an existing provider ledger')
        if not isinstance(allocations, dict) or set(allocations) != {'openai', 'openrouter'}:
            raise ValueError('Explicit OpenAI and OpenRouter allocations required')
        self._limits = {provider: _cap(value) for provider, value in allocations.items()}
        if not isinstance(lease, dict) or not isinstance(lease.get('provider_allocations_usd'), dict):
            raise ValueError('Coordinator receipt must identify provider allocations')
        leased = lease['provider_allocations_usd']
        for provider, amount in self._limits.items():
            if provider not in leased or amount > _cap(leased[provider]):
                raise ValueError('Local allocation exceeds coordinator receipt')
        encoded = _canonical(lease)
        self.lease = json.loads(encoded)
        self.lease_sha256 = hashlib.sha256(encoded.encode('utf-8')).hexdigest()
        self.entries = []
        self._charges = []
        self._arms = {}
        self.lock = threading.RLock()
        self.halted = False
        _write(self.path, self.summary(), exclusive=True)

    @property
    def held(self):
        with self.lock:
            return sum(self._charges)/NANOS

    def _provider_held(self, provider):
        return sum(charge for entry, charge in zip(self.entries, self._charges) if entry['provider'] == provider)

    def summary(self):
        with self.lock:
            providers = {provider: {'cap_usd': limit/NANOS,
                'charged_or_reserved_usd': self._provider_held(provider)/NANOS,
                'remaining_usd': max(0, limit-self._provider_held(provider))/NANOS}
                for provider, limit in self._limits.items()}
            return json.loads(_canonical({'providers': providers, 'charged_or_reserved_usd': self.held,
                'entries': self.entries, 'halted': self.halted,
                'arms': {name: {'halted': arm.halted} for name, arm in self._arms.items()},
                'lease': self.lease, 'lease_sha256': self.lease_sha256,
                'scope': 'local_suballocation_not_global_project_ledger',
                'cost_basis': 'conservative_uncached_usage_estimate_or_retained_reservation',
                'rates': RATES}))

    def save(self):
        with self.lock:
            _write(self.path, self.summary())


class ArmLedger:
    """Implements the Ledger interface consumed by budget.attach."""
    def __init__(self, path, provider_budget, arm):
        if not isinstance(provider_budget, ProviderBudget):
            raise ValueError('Shared ProviderBudget required')
        if not isinstance(arm, str) or not arm.strip():
            raise ValueError('Named arm required')
        self.path = Path(path)
        self.provider_budget = provider_budget
        self.arm = arm
        self.lock = provider_budget.lock
        self.entries = []
        self._indices = []
        self.halted = False
        self.cap = sum(provider_budget._limits.values())/NANOS
        with self.lock:
            if arm in provider_budget._arms:
                raise ValueError('Arm already registered; cannot reset its ledger')
            _write(self.path, self._summary(), exclusive=True)
            provider_budget._arms[arm] = self
            provider_budget.save()

    @property
    def held(self):
        with self.lock:
            return sum(self.provider_budget._charges[index] for index in self._indices)/NANOS

    def _summary(self):
        return {'arm': self.arm, 'cap_usd': self.cap,
            'cap_scope': 'shared_across_all_arms_with_separate_provider_limits',
            'provider_cap_usd': {provider: amount/NANOS for provider, amount in self.provider_budget._limits.items()},
            'charged_or_reserved_usd': self.held, 'entries': self.entries, 'halted': self.halted,
            'lease_sha256': self.provider_budget.lease_sha256}

    def save(self):
        with self.lock:
            for entry in self.entries:
                if entry.get('error_type') and entry['status'] == 'pending':
                    entry['status'] = 'error_reservation_retained'
            self.provider_budget.save()
            _write(self.path, self._summary())

    def reserve(self, role, max_tokens):
        if (role not in PROVIDERS or type(max_tokens) is not int
                or not 0 < max_tokens <= RATES[role][2]):
            raise ValueError('Known role and positive integer output cap required')
        provider = PROVIDERS[role]
        amount = _price(role, RATES[role][2], max_tokens)
        parent = self.provider_budget
        with self.lock:
            if self.halted or parent.halted:
                raise RuntimeError('Ledger halted after previous failure')
            if parent._provider_held(provider)+amount > parent._limits[provider]:
                raise RuntimeError('Provider allocation cannot reserve request; no call made')
            index = len(self.entries)
            entry = {'role': role, 'provider': provider, 'arm': self.arm,
                'reserved_usd': amount/NANOS, 'charged_usd': amount/NANOS,
                'status': 'pending', 'max_output_tokens': max_tokens, 'input_token_bound': RATES[role][2]}
            self._indices.append(len(parent.entries))
            parent.entries.append(entry)
            parent._charges.append(amount)
            self.entries.append(entry)
            self.save()
            return index

    def settle(self, index, usage):
        parent = self.provider_budget
        with self.lock:
            if type(index) is not int or not 0 <= index < len(self.entries):
                raise ValueError('Unknown reservation')
            entry = self.entries[index]
            if entry['status'] != 'pending':
                raise ValueError('Reservation already settled or failed')
            if usage is None:
                entry['status'] = 'unknown_usage_reservation_retained'
                self.halted = True
                self.save()
                raise RuntimeError('Missing usage; reservation retained and arm stopped')
            inputs, outputs = getattr(usage, 'input_tokens', None), getattr(usage, 'output_tokens', None)
            if any(type(value) is not int or not 0 <= value <= 1_000_000_000 for value in (inputs, outputs)):
                entry['status'] = 'invalid_usage_reservation_retained'
                self.halted = True
                self.save()
                raise ValueError('Invalid usage; reservation retained and arm stopped')
            charge = _price(entry['role'], inputs, outputs)
            parent_index = self._indices[index]
            exceeded = (inputs > entry['input_token_bound'] or outputs > entry['max_output_tokens']
                        or charge > parent._charges[parent_index])
            if exceeded:
                charge = max(charge, parent._charges[parent_index])
            parent._charges[parent_index] = charge
            entry.update(charged_usd=charge/NANOS, input_tokens=inputs, output_tokens=outputs,
                         status='BOUND_EXCEEDED_STOP' if exceeded else 'usage_estimate')
            if exceeded:
                self.halted = parent.halted = True
            self.save()
            if exceeded:
                raise RuntimeError('Cost or token bound exceeded; all arms stopped')
