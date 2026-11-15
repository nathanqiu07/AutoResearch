"""Morning coordinator admission and accounting hooks; never executes a model.

Native producers must call reserve_call before every provider request, then
settle_call exactly once. Merely claiming a lease does not enforce call limits.
Unknown calls retain their full bound and halt that producer. No reset/resume API.
Old campaign reservations remain outside this separately issued suballocation.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

PROVIDERS = ('openai', 'openrouter')
NANOS = 1_000_000_000
ADMISSION_DEADLINE = datetime(2026, 11, 15, 19, 45, tzinfo=timezone.utc)
DRAIN_DEADLINE = datetime(2026, 11, 15, 20, tzinfo=timezone.utc)


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('Aware timestamp required')
    return result.astimezone(timezone.utc)


def nanos(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Numeric USD required')
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0 or (positive and amount <= 0):
        raise ValueError('Invalid USD amount')
    return int((amount * NANOS).to_integral_value(rounding=ROUND_CEILING))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def file_ref(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Regular nonsymlink file required')
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_ref(reference):
    if file_ref(reference['path'])['sha256'] != reference['sha256']:
        raise ValueError('Pinned file changed')
    return json.loads(Path(reference['path']).read_text())


def verify_packet(packet, checksum):
    packet = Path(packet).resolve()
    checks = read_ref({'path': str(packet / 'checksums.json'), 'sha256': checksum})
    if not isinstance(checks, dict) or not checks:
        raise ValueError('Nonempty packet manifest required')
    members = list(packet.rglob('*'))
    if any(p.is_symlink() for p in members):
        raise ValueError('Packet symlink refused')
    actual = {str(p.relative_to(packet)) for p in members if p.is_file()}
    if actual != set(checks) | {'checksums.json'}:
        raise ValueError('Packet file union changed')
    for name, digest in checks.items():
        if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe packet member')
        if file_ref(packet / name)['sha256'] != digest:
            raise ValueError('Packet member changed')
    return str(packet)


class Registry:
    def __init__(self, path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise ValueError('Explicitly initialized registry required')

    @classmethod
    def create(cls, path, policy, *, producer_limits=None):
        if policy.get('schema_version') == 'gio-morning-aggregate-allocation-v1':
            if policy.get('state') != 'allocated_new_sprint' or not producer_limits:
                raise ValueError('Root allocation and explicit producer limits required')
            original = policy
            suballocations = original['suballocations_usd']
            if not set(producer_limits) <= set(suballocations):
                raise ValueError('Producer has no root suballocation')
            policy = {'schema_version': 'gio-morning-budget-v1', 'state': 'issued',
                      'campaign_id': original['campaign_id'],
                      'aggregate_policy_sha256': hashlib.sha256(canonical(original).encode()).hexdigest(),
                      'provider_allocations_usd': {k: float(v) for k, v in original['new_sprint_shared_allocation_usd'].items()},
                      'producer_allocations_usd': {p: {k: float(v) for k, v in caps.items()} for p, caps in suballocations.items()},
                      'producer_limits': dict(producer_limits),
                      'max_inflight': original['global_max_concurrent_provider_calls'],
                      'admission_deadline': original['admission_cutoff'], 'drain_deadline': original['demo_deadline']}
        if policy.get('schema_version') != 'gio-morning-budget-v1' or policy.get('state') != 'issued' or not policy.get('campaign_id'):
            raise ValueError('Issued morning policy required')
        caps = policy['provider_allocations_usd']
        if set(caps) != set(PROVIDERS) or any(not 0 < nanos(v) <= 200 * NANOS for v in caps.values()):
            raise ValueError('Initial envelope is at most 200 USD per provider')
        maximum = policy['max_inflight']
        limits = policy['producer_limits']
        if type(maximum) is not int or not 1 <= maximum <= 9 or not limits or any(type(v) is not int or not 1 <= v <= maximum for v in limits.values()):
            raise ValueError('Invalid coordinator concurrency ceiling')
        if not stamp(policy['admission_deadline']) <= ADMISSION_DEADLINE or not stamp(policy['admission_deadline']) < stamp(policy['drain_deadline']) <= DRAIN_DEADLINE:
            raise ValueError('Morning deadline exceeded')
        path = Path(path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        with sqlite3.connect(str(path)) as db:
            db.executescript('CREATE TABLE policy (body TEXT NOT NULL); CREATE TABLE leases (id TEXT PRIMARY KEY, packet_sha TEXT UNIQUE NOT NULL, body TEXT NOT NULL, reference TEXT NOT NULL, packet TEXT NOT NULL, state TEXT NOT NULL); CREATE TABLE calls (id INTEGER PRIMARY KEY, lease_id TEXT NOT NULL, provider TEXT NOT NULL, request_sha TEXT NOT NULL, reserved INTEGER NOT NULL, charged INTEGER, state TEXT NOT NULL);')
            db.execute('INSERT INTO policy VALUES (?)', (canonical(policy),))
        return cls(path)

    @contextmanager
    def _db(self, write=False):
        db = sqlite3.connect(self.path.as_uri() + '?mode=' + ('rw' if write else 'ro'), uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            if write:
                db.execute('BEGIN IMMEDIATE')
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def _policy(self, db):
        return json.loads(db.execute('SELECT body FROM policy').fetchone()[0])

    def _lease(self, db, lease_id):
        row = db.execute('SELECT * FROM leases WHERE id=?', (lease_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown lease')
        return row, json.loads(row['body'])

    def _time(self, policy, lease, now):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or now >= min(stamp(policy['admission_deadline']), stamp(lease['expires_at'])):
            raise ValueError('Paid admission deadline reached')

    def register(self, lease_ref, packet, *, now=None):
        lease = read_ref(lease_ref)
        packet = verify_packet(packet, lease['packet_checksums_sha256'])
        if lease.get('status') != 'issued' or not all(isinstance(lease.get(k), str) and lease[k] for k in ('lease_id', 'owner_chat', 'producer_id', 'output_root')):
            raise ValueError('Issued producer lease required')
        caps = lease['provider_allocations_usd']
        if set(caps) != set(PROVIDERS) or any(nanos(v) > 200 * NANOS for v in caps.values()) or not any(nanos(v) > 0 for v in caps.values()):
            raise ValueError('Invalid provider allocation')
        if not Path(lease['output_root']).is_absolute() or Path(lease['output_root']).exists():
            raise ValueError('Fresh absolute output root required')
        with self._db(True) as db:
            policy = self._policy(db)
            self._time(policy, lease, now)
            if stamp(lease['expires_at']) > stamp(policy['admission_deadline']):
                raise ValueError('Lease exceeds campaign deadline')
            limit = policy['producer_limits'].get(lease['producer_id'], 0)
            if type(lease.get('max_inflight')) is not int or not 1 <= lease['max_inflight'] <= limit or type(lease.get('max_attempts')) is not int or lease['max_attempts'] < 1:
                raise ValueError('Explicit producer attempt/concurrency bounds required')
            existing = [json.loads(r[0]) for r in db.execute('SELECT body FROM leases')]
            if 'producer_allocations_usd' in policy:
                producer_cap = policy['producer_allocations_usd'][lease['producer_id']]
                for provider in PROVIDERS:
                    allocated = sum(nanos(r['provider_allocations_usd'][provider]) for r in existing if r['producer_id'] == lease['producer_id'])
                    if allocated + nanos(caps[provider]) > nanos(producer_cap[provider]):
                        raise ValueError('Producer suballocation exceeded')
            for provider in PROVIDERS:
                if sum(nanos(r['provider_allocations_usd'][provider]) for r in existing) + nanos(caps[provider]) > nanos(policy['provider_allocations_usd'][provider]):
                    raise ValueError('Aggregate provider envelope exceeded')
            try:
                db.execute('INSERT INTO leases VALUES (?,?,?,?,?,?)', (lease['lease_id'], lease['packet_checksums_sha256'], canonical(lease), canonical(lease_ref), packet, 'registered'))
            except sqlite3.IntegrityError as exc:
                raise ValueError('Lease or packet already registered; no retry') from exc
        return lease['lease_id']

    def claim(self, lease_id, *, now=None):
        with self._db(True) as db:
            row, lease = self._lease(db, lease_id)
            self._time(self._policy(db), lease, now)
            if row['state'] != 'registered':
                raise ValueError('Lease already claimed; no retry')
            read_ref(json.loads(row['reference']))
            verify_packet(row['packet'], row['packet_sha'])
            if Path(lease['output_root']).exists():
                raise ValueError('Output root already exists')
            db.execute("UPDATE leases SET state='claimed' WHERE id=?", (lease_id,))
        return lease

    def reserve_call(self, lease_id, provider, request_sha256, max_usd, *, now=None):
        if provider not in PROVIDERS or not isinstance(request_sha256, str) or not re.fullmatch('[0-9a-f]{64}', request_sha256):
            raise ValueError('Explicit provider and request SHA256 required')
        amount = nanos(max_usd)
        with self._db(True) as db:
            row, lease = self._lease(db, lease_id)
            policy = self._policy(db)
            self._time(policy, lease, now)
            if nanos(lease['provider_allocations_usd'][provider]) == 0:
                raise ValueError('Provider is not allocated to this lease')
            if row['state'] != 'claimed':
                raise ValueError('Unclaimed or halted lease')
            halted = db.execute("SELECT body FROM leases WHERE state='halted'").fetchall()
            if any(json.loads(r['body'])['producer_id'] == lease['producer_id'] for r in halted):
                raise ValueError('Producer halted after uncertain or exceeded bound')
            if db.execute("SELECT 1 FROM calls WHERE state='bound_exceeded'").fetchone():
                raise ValueError('Campaign needs inspection after exceeded bound')
            if db.execute("SELECT 1 FROM calls WHERE provider=? AND request_sha=? AND (state IN ('pending','unknown') OR lease_id=?)", (provider, request_sha256, lease_id)).fetchone():
                raise ValueError('Pending, unknown or same-lease request cannot repeat')
            calls = list(db.execute('SELECT * FROM calls WHERE lease_id=?', (lease_id,)))
            if len(calls) >= lease['max_attempts']:
                raise ValueError('Attempt ceiling reached')
            used = sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in calls if r['provider'] == provider)
            if used + amount > nanos(lease['provider_allocations_usd'][provider]):
                raise ValueError('Provider allocation cannot reserve call')
            active = list(db.execute("SELECT calls.lease_id, leases.body FROM calls JOIN leases ON calls.lease_id=leases.id WHERE calls.state='pending'"))
            producer_active = sum(json.loads(r['body'])['producer_id'] == lease['producer_id'] for r in active)
            if len(active) >= policy['max_inflight'] or producer_active >= policy['producer_limits'][lease['producer_id']] or sum(r['lease_id'] == lease_id for r in active) >= lease['max_inflight']:
                raise ValueError('Coordinator concurrency ceiling reached')
            cursor = db.execute("INSERT INTO calls (lease_id,provider,request_sha,reserved,state) VALUES (?,?,?,?,'pending')", (lease_id, provider, request_sha256, amount))
            return cursor.lastrowid

    def settle_call(self, call_id, actual_usd):
        charge = None if actual_usd is None else nanos(actual_usd)
        exceeded = False
        with self._db(True) as db:
            row = db.execute('SELECT * FROM calls WHERE id=?', (call_id,)).fetchone()
            if row is None or row['state'] != 'pending':
                raise ValueError('Only pending calls may settle once')
            exceeded = charge is not None and charge > row['reserved']
            state = 'unknown' if charge is None else ('bound_exceeded' if exceeded else 'known')
            db.execute('UPDATE calls SET charged=?, state=? WHERE id=?', (charge, state, call_id))
            if charge is None or exceeded:
                db.execute("UPDATE leases SET state='halted' WHERE id=?", (row['lease_id'],))
        if exceeded:
            raise ValueError('Actual cost exceeded reservation; retained and lease halted')

    def result_index(self, lease_id, artifacts):
        with self._db() as db:
            row, lease = self._lease(db, lease_id)
            calls = list(db.execute('SELECT * FROM calls WHERE lease_id=? ORDER BY id', (lease_id,)))
            policy = self._policy(db)
        accounting = {}
        for provider in PROVIDERS:
            selected = [c for c in calls if c['provider'] == provider]
            accounting[provider] = {'known_attempts': sum(c['charged'] is not None for c in selected), 'unknown_attempts': sum(c['state'] == 'unknown' for c in selected), 'pending_attempts': sum(c['state'] == 'pending' for c in selected), 'known_usd': sum(c['charged'] or 0 for c in selected) / NANOS, 'held_usd': sum(c['reserved'] for c in selected if c['charged'] is None) / NANOS}
        root = Path(lease['output_root']).resolve()
        refs = {}
        for name, relative in artifacts.items():
            candidate = Path(relative)
            if candidate.is_absolute() or '..' in candidate.parts:
                raise ValueError('Artifact must be inside declared output root')
            path = root / candidate
            if path.is_symlink() or root not in path.resolve().parents:
                raise ValueError('Artifact escapes output root')
            refs[name] = file_ref(path) if path.is_file() else None
        return {'schema_version': 'gio-morning-result-index-v1', 'campaign_id': policy['campaign_id'], 'lease': json.loads(row['reference']), 'lease_id': lease_id, 'producer_id': lease['producer_id'], 'registry_state': row['state'], 'packet_checksums': {'path': str(Path(row['packet']) / 'checksums.json'), 'sha256': row['packet_sha']}, 'accounting': accounting, 'artifacts': refs, 'missing_artifacts': [name for name, ref in refs.items() if ref is None], 'no_automatic_retry': True, 'call_hook_coverage': 'Only requests passed through reserve_call/settle_call are represented; producer integration must establish complete coverage.', 'scope': 'Accounting/index only; native producer result and evaluator determine execution/scientific status.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--policy', required=True); init.add_argument('--sha256', required=True); init.add_argument('--producer-limits', help='JSON object of explicit producer concurrency ceilings for root BUDGET format')
    register = sub.add_parser('register'); register.add_argument('--lease', required=True); register.add_argument('--sha256', required=True); register.add_argument('--packet', required=True)
    claim = sub.add_parser('claim'); claim.add_argument('--lease-id', required=True)
    index = sub.add_parser('index'); index.add_argument('--lease-id', required=True); index.add_argument('--artifacts', required=True, help='JSON mapping of labels to relative output paths')
    args = parser.parse_args()
    if args.command == 'init':
        Registry.create(args.registry, read_ref({'path': args.policy, 'sha256': args.sha256}), producer_limits=json.loads(args.producer_limits) if args.producer_limits else None); result = {'status': 'initialized'}
    else:
        registry = Registry(args.registry)
        if args.command == 'register': result = {'registered': registry.register({'path': args.lease, 'sha256': args.sha256}, args.packet)}
        elif args.command == 'claim': result = {'claimed': registry.claim(args.lease_id)['lease_id']}
        else: result = registry.result_index(args.lease_id, json.loads(Path(args.artifacts).read_text()))
    print(json.dumps(result, sort_keys=True, allow_nan=False))

if __name__ == '__main__':
    main()
