"""Morning-only lease deadline; reuse the existing reservation and cost logic.

Import as morning_recovery.budget so the established top-level budget module
continues to provide Inspect usage accounting. The overnight deadline is intact.
This adapter is a local suballocation, not the project's global allocator.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading

import provider_budget as _legacy


OWNER_CHAT = '01a1de1f-bcb8-74a3-8076-0a3f9a27340a'
MORNING_DEADLINE_UTC = datetime(2026, 11, 15, 19, 45, tzinfo=timezone.utc)
ArmLedger = _legacy.ArmLedger


def parse_lease_expiry(expires_at: str) -> datetime:
    """Require a real aware expiry at or before the authorized morning stop."""
    if not isinstance(expires_at, str) or not expires_at:
        raise ValueError('Coordinator lease requires an aware expires_at timestamp')
    try:
        expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Coordinator lease expires_at must be a valid ISO timestamp') from exc
    if expiry.tzinfo is None or expiry.utcoffset() is None:
        raise ValueError('Coordinator lease expires_at must include a timezone')
    try:
        expiry = expiry.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError('Coordinator lease expires_at is outside supported UTC dates') from exc
    if expiry > MORNING_DEADLINE_UTC:
        raise ValueError('Coordinator lease expires_at exceeds morning deadline 2026-11-15T19:45:00Z')
    return expiry


def validate_execution_lease(lease, packet, settings):
    """Bind an issued local allocation to this owner and the exact packet pin.

    The caller separately validates all packet members, runtime code binding,
    credentials, and the exclusive global claim before dispatching any calls.
    """
    if not isinstance(lease, dict) or not isinstance(settings, dict):
        raise ValueError('Lease and settings must be objects')
    if lease.get('status') != 'issued':
        raise ValueError('Coordinator lease is not issued')
    if lease.get('owner_chat') != OWNER_CHAT:
        raise ValueError('Wrong lease owner')
    if not isinstance(lease.get('lease_id'), str) or not lease['lease_id'].strip():
        raise ValueError('Missing lease ID')
    packet_pin = hashlib.sha256((Path(packet)/'checksums.json').read_bytes()).hexdigest()
    if lease.get('packet_checksums_sha256') != packet_pin:
        raise ValueError('Lease is not bound to this packet')
    if parse_lease_expiry(lease.get('expires_at')) <= datetime.now(timezone.utc):
        raise ValueError('Expired lease')
    caps = lease.get('provider_allocations_usd')
    requested = settings.get('provider_allocations_usd')
    providers = {'openai', 'openrouter'}
    if (not isinstance(caps, dict) or set(caps) != providers
            or not isinstance(requested, dict) or set(requested) != providers):
        raise ValueError('Both provider allocations must be explicit in lease and packet')
    for name in providers:
        value = caps[name]
        if type(value) not in (int, float) or not 0 < value <= 500:
            raise ValueError('Invalid finite provider allocation: '+name)
        if type(requested[name]) not in (int, float) or requested[name] != value:
            raise ValueError('Lease allocation mismatch: '+name)
    return dict(caps)


class ProviderBudget(_legacy.ProviderBudget):
    """Replace only constructor expiry validation; all ledger methods are reused.

    ArmLedger requires a ProviderBudget instance, so subclassing preserves that
    existing type check. Every reservation still checks the real UTC time under
    the shared lock against this receipt's real expires_at; nothing is extended
    by a synthetic receipt, clock override, or mutation of the overnight module.
    """
    def __init__(self, path, allocations, lease):
        self.path = Path(path)
        if self.path.exists():
            raise FileExistsError('Refusing to reset an existing provider ledger')
        if not isinstance(allocations, dict) or set(allocations) != {'openai', 'openrouter'}:
            raise ValueError('Explicit OpenAI and OpenRouter allocations required')
        self._limits = {provider: _legacy._cap(value) for provider, value in allocations.items()}
        if not isinstance(lease, dict) or not isinstance(lease.get('provider_allocations_usd'), dict):
            raise ValueError('Coordinator receipt must identify provider allocations')
        self.expires_at = parse_lease_expiry(lease.get('expires_at'))
        leased = lease['provider_allocations_usd']
        for provider, amount in self._limits.items():
            if provider not in leased or amount > _legacy._cap(leased[provider]):
                raise ValueError('Local allocation exceeds coordinator receipt')
        encoded = _legacy._canonical(lease)
        self.lease = json.loads(encoded)
        self.lease_sha256 = hashlib.sha256(encoded.encode('utf-8')).hexdigest()
        self.entries = []
        self._charges = []
        self._arms = {}
        self.lock = threading.RLock()
        self.halted = False
        self.halt_reason = None
        _legacy._write(self.path, self.summary(), exclusive=True)
