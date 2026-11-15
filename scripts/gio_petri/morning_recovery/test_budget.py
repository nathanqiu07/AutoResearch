"""Offline morning lease boundaries; no credentials or model APIs."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import provider_budget as legacy
from budget import attach


class MorningBudgetTests(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module('morning_recovery.budget')
        except ModuleNotFoundError as exc:
            if exc.name != 'morning_recovery.budget':
                raise
            self.fail('Morning budget adapter is not implemented')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = self.root/'packet'
        self.packet.mkdir()
        (self.packet/'checksums.json').write_text('{}\n')
        self.caps = {'openai': 3, 'openrouter': 1}
        self.settings = {'provider_allocations_usd': self.caps.copy()}
        self.lease = {'status': 'issued', 'owner_chat': '01a1de1f-bcb8-74a3-8076-0a3f9a27340a',
                      'lease_id': 'morning-offline-fixture',
                      'packet_checksums_sha256': hashlib.sha256((self.packet/'checksums.json').read_bytes()).hexdigest(),
                      'expires_at': '2026-11-15T19:45:00Z',
                      'provider_allocations_usd': self.caps.copy()}
        self.clocks = []
        for name in ('provider_budget.datetime', 'morning_recovery.budget.datetime'):
            clock_patch = patch(name, wraps=datetime)
            self.clocks.append(clock_patch.start())
            self.addCleanup(clock_patch.stop)
        self.now(datetime(2026, 11, 15, 17, 30, tzinfo=timezone.utc))

    def now(self, value):
        for clock in self.clocks:
            clock.now.return_value = value

    def parent(self, directory=None, lease=None):
        directory = directory or self.root
        return self.m.ProviderBudget(directory/'providers.json', self.caps, lease or self.lease)

    def test_new_deadline_is_real_and_old_overnight_policy_is_unchanged(self):
        parent = self.parent()
        expected = datetime(2026, 11, 15, 19, 45, tzinfo=timezone.utc)
        self.assertEqual(self.m.MORNING_DEADLINE_UTC, expected)
        self.assertEqual(parent.expires_at, expected)
        self.assertIsInstance(parent, legacy.ProviderBudget)
        self.assertIs(self.m.ArmLedger, legacy.ArmLedger)
        self.assertIs(self.m.ProviderBudget.summary, legacy.ProviderBudget.summary)
        self.assertEqual(json.loads(parent.path.read_text())['lease'], self.lease)
        with self.assertRaises(ValueError):
            legacy.parse_lease_expiry(self.lease['expires_at'])
        self.assertEqual(legacy.CAMPAIGN_DEADLINE_UTC, datetime(2026, 11, 15, 17, tzinfo=timezone.utc))
        arm = self.m.ArmLedger(self.root/'arm.json', parent, 'smoke')
        arm.reserve('target', 16384)

    def test_missing_invalid_naive_or_late_expiry_is_rejected_before_creation(self):
        for value in (None, '', 123, True, 'not-a-date', '2026-11-15', '2026-11-15T19:45:00',
                      '2026-11-15T19:45:00.000001Z', '2026-11-15T12:45:01-07:00'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parent(lease={**self.lease, 'expires_at': value})
            self.assertFalse((self.root/'providers.json').exists())
        self.assertEqual(self.m.parse_lease_expiry('2026-11-15T11:45:00-08:00'),
                         self.m.MORNING_DEADLINE_UTC)

    def test_exact_packet_owner_issued_allocation_and_unexpired_lease_required(self):
        result = self.m.validate_execution_lease(self.lease, self.packet, self.settings)
        self.assertEqual(result, self.caps)
        bad = [{'status': 'proposed'}, {'owner_chat': 'other'}, {'lease_id': ''},
               {'packet_checksums_sha256': '0'*64}, {'expires_at': '2026-11-15T17:30:00Z'},
               {'expires_at': '2026-11-15T19:45:01Z'},
               {'provider_allocations_usd': {'openai': 4, 'openrouter': 1}},
               {'provider_allocations_usd': {'openai': 3}},
               {'provider_allocations_usd': {'openai': 3, 'openrouter': 1, 'other': 1}}]
        for change in bad:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.m.validate_execution_lease({**self.lease, **change}, self.packet, self.settings)
        for value in (0, -1, True, '3', float('nan'), float('inf'), 501, 10**400):
            caps = {'openai': value, 'openrouter': 1}
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.m.validate_execution_lease({**self.lease, 'provider_allocations_usd': caps},
                                               self.packet, {'provider_allocations_usd': caps})
        with self.assertRaises(ValueError):
            self.m.validate_execution_lease(self.lease, self.packet, {})

    def test_one_microsecond_before_deadline_all_roles_can_reserve(self):
        parent = self.parent()
        arm = self.m.ArmLedger(self.root/'arm.json', parent, 'smoke')
        self.now(self.m.MORNING_DEADLINE_UTC - timedelta(microseconds=1))
        for role, cap in (('judge', 32000), ('auditor', 4096), ('target', 16384)):
            arm.reserve(role, cap)
        self.assertEqual(len(parent.entries), 3)

    def test_exact_and_after_deadline_admit_no_role_or_mock_provider_call(self):
        for offset in (0, 1):
            directory = self.root/str(offset)
            parent = self.parent(directory)
            arm = self.m.ArmLedger(directory/'arm.json', parent, 'smoke')
            self.now(self.m.MORNING_DEADLINE_UTC + timedelta(microseconds=offset))
            calls = []
            async def fail_if_called(*args):
                calls.append(args)
                raise AssertionError('Expired morning lease reached provider')
            for role, cap in (('judge', 32000), ('auditor', 4096), ('target', 16384)):
                model = SimpleNamespace(api=SimpleNamespace(generate=fail_if_called),
                                        config=SimpleNamespace(max_tokens=cap))
                attach(model, role, arm, directory)
                with self.subTest(offset=offset, role=role), self.assertRaisesRegex(RuntimeError, 'expired'):
                    asyncio.run(model.api.generate([], [], 'auto', model.config))
            self.assertEqual(calls, [])
            saved = json.loads(parent.path.read_text())
            self.assertTrue(saved['halted'])
            self.assertEqual(saved['halt_reason'], 'lease_expired')
            self.assertEqual(saved['entries'], [])

    def test_earlier_lease_expiry_wins_over_morning_deadline(self):
        parent = self.parent(lease={**self.lease, 'expires_at': '2026-11-15T18:00:00Z'})
        arm = self.m.ArmLedger(self.root/'arm.json', parent, 'smoke')
        self.now(datetime(2026, 11, 15, 18, tzinfo=timezone.utc))
        with self.assertRaisesRegex(RuntimeError, 'expired'):
            arm.reserve('target', 16384)
        self.assertEqual(parent.entries, [])

    def test_cache_accounting_and_bounds_are_inherited(self):
        parent = self.parent()
        arm = self.m.ArmLedger(self.root/'arm.json', parent, 'smoke')
        index = arm.reserve('judge', 32000)
        arm.settle(index, SimpleNamespace(input_tokens=11324, input_tokens_cache_read=9088,
                                         input_tokens_cache_write=None, output_tokens=9062))
        self.assertAlmostEqual(parent.held, .116135)
        self.assertEqual(arm.entries[0]['total_input_tokens'], 20412)
        index = arm.reserve('judge', 32000)
        held = parent.held
        with self.assertRaises(RuntimeError):
            arm.settle(index, SimpleNamespace(input_tokens=1, input_tokens_cache_read=400000, output_tokens=0))
        self.assertTrue(parent.halted)
        self.assertGreaterEqual(parent.held, held)
        with self.assertRaises(RuntimeError):
            self.m.ArmLedger(self.root/'other.json', parent, 'other').reserve('target', 100)

    def test_unknown_and_pending_holds_survive_expiry_and_admitted_call_can_settle(self):
        parent = self.parent()
        pending = self.m.ArmLedger(self.root/'pending.json', parent, 'pending')
        uncertain = self.m.ArmLedger(self.root/'unknown.json', parent, 'unknown')
        index = pending.reserve('judge', 32000)
        unknown = uncertain.reserve('judge', 32000)
        with self.assertRaises(RuntimeError):
            uncertain.settle(unknown, None)
        previous = copy.deepcopy(parent.entries)
        self.now(self.m.MORNING_DEADLINE_UTC)
        with self.assertRaisesRegex(RuntimeError, 'expired'):
            pending.reserve('target', 100)
        self.assertEqual(parent.entries, previous)
        self.assertAlmostEqual(parent.held, 1.64)
        pending.settle(index, SimpleNamespace(input_tokens=1000, output_tokens=100))
        self.assertAlmostEqual(parent.held, .82225)
        self.assertEqual(parent.entries[1], previous[1])
        self.assertTrue(parent.halted)

    def test_constructor_cannot_exceed_receipt_or_reset_saved_ledger(self):
        with self.assertRaises(ValueError):
            self.parent(lease={**self.lease, 'provider_allocations_usd': {'openai': 2, 'openrouter': 1}})
        parent = self.parent()
        self.lease['provider_allocations_usd']['openai'] = 999
        self.assertEqual(parent.lease['provider_allocations_usd']['openai'], 3)
        with self.assertRaises(FileExistsError):
            self.parent()


if __name__ == '__main__':
    unittest.main()
