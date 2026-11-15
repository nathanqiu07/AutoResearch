"""Offline checks for shared local allocations and failure accounting."""
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from budget import attach
from provider_budget import ArmLedger, ProviderBudget


class ProviderBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        clock_patch = patch('provider_budget.datetime', wraps=datetime)
        self.clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.clock.now.return_value = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)

    def make_budget(self, openai=2, openrouter=1):
        allocations = {'openai': openai, 'openrouter': openrouter}
        lease = {'lease_id': 'offline-fixture', 'provider_allocations_usd': allocations.copy(),
                 'expires_at': '2026-11-15T17:00:00Z'}
        return ProviderBudget(self.root/'providers.json', allocations, lease)

    def arm(self, budget, name='baseline'):
        return ArmLedger(self.root/(name+'.json'), budget, name)

    def test_nonfinite_and_nonpositive_caps_are_rejected(self):
        for invalid in (float('nan'), float('inf'), -float('inf'), 0, -1, True, '5', 10**400):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.make_budget(openai=invalid)
        self.assertFalse((self.root/'providers.json').exists())

    def test_local_cap_cannot_exceed_or_omit_leased_provider(self):
        with self.assertRaises(ValueError):
            ProviderBudget(self.root/'providers.json', {'openai': 15, 'openrouter': 5},
                           {'provider_allocations_usd': {'openai': 1, 'openrouter': 5},
                            'expires_at': '2026-11-15T17:00:00Z'})
        with self.assertRaises(ValueError):
            ProviderBudget(self.root/'providers.json', {'openai': 1},
                           {'provider_allocations_usd': {'openai': 1, 'openrouter': 5},
                            'expires_at': '2026-11-15T17:00:00Z'})

    def test_provider_caps_do_not_borrow_from_each_other(self):
        parent = self.make_budget(openai=.8, openrouter=5)
        arm = self.arm(parent)
        with self.assertRaises(RuntimeError):
            arm.reserve('judge', 32000)
        arm.reserve('auditor', 4096)
        state = parent.summary()
        self.assertEqual(state['providers']['openai']['charged_or_reserved_usd'], 0)
        self.assertAlmostEqual(state['providers']['openrouter']['charged_or_reserved_usd'], .02584576)

    def test_two_arms_share_one_provider_allocation(self):
        parent = self.make_budget(openai=1.5)
        arms = [self.arm(parent, name) for name in ('baseline', 'profile')]
        def attempt(arm):
            try:
                return arm.reserve('judge', 32000)
            except RuntimeError:
                return None
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, arms))
        self.assertEqual(sum(item is not None for item in results), 1)
        self.assertAlmostEqual(parent.summary()['providers']['openai']['charged_or_reserved_usd'], .82)

    def test_settle_uses_recorded_usage_and_releases_unused_reservation(self):
        parent = self.make_budget(openai=1)
        first = self.arm(parent)
        i = first.reserve('judge', 32000)
        first.settle(i, SimpleNamespace(input_tokens=1000, output_tokens=100))
        self.assertAlmostEqual(first.held, .00225)
        self.arm(parent, 'profile').reserve('judge', 32000)
        self.assertAlmostEqual(parent.summary()['providers']['openai']['charged_or_reserved_usd'], .82225)
        with self.assertRaises(ValueError):
            first.settle(i, SimpleNamespace(input_tokens=0, output_tokens=0))

    def test_attach_error_retains_charge_and_only_halts_failed_arm(self):
        parent = self.make_budget(openai=2)
        first = self.arm(parent)
        async def fail(*args):
            raise RuntimeError('offline fixture')
        model = SimpleNamespace(api=SimpleNamespace(generate=fail), config=SimpleNamespace(max_tokens=32000))
        attach(model, 'judge', first, self.root)
        with self.assertRaises(RuntimeError):
            asyncio.run(model.api.generate([], [], 'auto', model.config))
        self.assertTrue(first.halted)
        with self.assertRaises(RuntimeError):
            first.reserve('target', 100)
        second = self.arm(parent, 'profile')
        second.reserve('judge', 32000)
        saved = json.loads(parent.path.read_text())
        self.assertAlmostEqual(saved['providers']['openai']['charged_or_reserved_usd'], 1.64)
        self.assertEqual(saved['entries'][0]['error_type'], 'RuntimeError')
        self.assertEqual(saved['entries'][0]['status'], 'error_reservation_retained')
        self.assertFalse(parent.halted)

    def test_missing_usage_retains_reservation_and_halts_arm(self):
        parent = self.make_budget(openai=2)
        first = self.arm(parent)
        i = first.reserve('judge', 32000)
        with self.assertRaises(RuntimeError):
            first.settle(i, None)
        self.assertAlmostEqual(first.held, .82)
        self.assertTrue(first.halted)
        self.assertFalse(parent.halted)
        self.arm(parent, 'profile').reserve('judge', 32000)

    def test_usage_exceeding_bound_halts_all_arms_and_keeps_known_cost(self):
        parent = self.make_budget(openai=2)
        first = self.arm(parent)
        second = self.arm(parent, 'profile')
        i = first.reserve('judge', 32000)
        with self.assertRaises(RuntimeError):
            first.settle(i, SimpleNamespace(input_tokens=500000, output_tokens=32000))
        self.assertTrue(parent.halted)
        self.assertAlmostEqual(first.held, .945)
        with self.assertRaises(RuntimeError):
            second.reserve('target', 100)

    def test_invalid_usage_cannot_release_money(self):
        for index, invalid in enumerate((-1, float('nan'), float('inf'), True, 1.5, 10**400)):
            directory = self.root/str(index)
            directory.mkdir()
            parent = ProviderBudget(directory/'providers.json', {'openai': 2, 'openrouter': 1},
                {'provider_allocations_usd': {'openai': 2, 'openrouter': 1},
                 'expires_at': '2026-11-15T17:00:00Z'})
            arm = ArmLedger(directory/'baseline.json', parent, 'baseline')
            i = arm.reserve('judge', 32000)
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                arm.settle(i, SimpleNamespace(input_tokens=invalid, output_tokens=0))
            self.assertAlmostEqual(arm.held, .82)
            self.assertTrue(arm.halted)
            self.assertFalse(parent.halted)

    def test_existing_budget_cannot_be_reset_and_lease_is_frozen(self):
        allocations = {'openai': 2, 'openrouter': 1}
        lease = {'provider_allocations_usd': allocations.copy(), 'lease_id': 'fixture',
                 'expires_at': '2026-11-15T17:00:00Z'}
        parent = ProviderBudget(self.root/'providers.json', allocations, lease)
        original = json.dumps(lease, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        lease['provider_allocations_usd']['openai'] = 999
        self.assertEqual(parent.summary()['lease_sha256'], hashlib.sha256(original.encode()).hexdigest())
        self.assertEqual(parent.summary()['lease']['provider_allocations_usd']['openai'], 2)
        with self.assertRaises(FileExistsError):
            ProviderBudget(parent.path, allocations, lease)
        self.arm(parent)
        with self.assertRaises((ValueError, FileExistsError)):
            self.arm(parent)

    def test_reservation_requires_known_role_and_positive_integer_output_cap(self):
        parent = self.make_budget()
        arm = self.arm(parent)
        for maximum in (None, 0, -1, True, 3.4, float('nan'), 10**400):
            with self.subTest(maximum=maximum), self.assertRaises(ValueError):
                arm.reserve('judge', maximum)
        with self.assertRaises(ValueError):
            arm.reserve('other', 100)
        self.assertEqual(arm.entries, [])

    def test_expiry_is_required_aware_valid_and_within_campaign(self):
        allocations = {'openai': 2, 'openrouter': 1}
        invalid = [None, '', 123, True, {}, 'not-a-date', '2026-11-15',
                   '2026-11-15T17:00:00', '2026-11-15T17:00:00.000001Z',
                   '2026-11-15T18:00:00+00:00']
        for value in invalid:
            lease = {'provider_allocations_usd': allocations.copy(), 'expires_at': value}
            with self.subTest(value=value), self.assertRaises(ValueError):
                ProviderBudget(self.root/'providers.json', allocations, lease)
            self.assertFalse((self.root/'providers.json').exists())
        with self.assertRaises(ValueError):
            ProviderBudget(self.root/'providers.json', allocations,
                           {'provider_allocations_usd': allocations.copy()})

    def test_offset_expiry_is_compared_as_an_instant(self):
        allocations = {'openai': 2, 'openrouter': 1}
        parent = ProviderBudget(self.root/'providers.json', allocations,
            {'provider_allocations_usd': allocations.copy(),
             'expires_at': '2026-11-15T08:30:00-08:00'})
        arm = self.arm(parent)
        self.clock.now.return_value = datetime(2026, 11, 15, 16, 30, tzinfo=timezone.utc)
        with self.assertRaisesRegex(RuntimeError, 'expired'):
            arm.reserve('target', 100)
        self.assertEqual(parent.entries, [])

    def test_each_role_can_reserve_immediately_before_expiry(self):
        parent = self.make_budget()
        arm = self.arm(parent)
        self.clock.now.return_value = (datetime(2026, 11, 15, 17, tzinfo=timezone.utc)
                                      - timedelta(microseconds=1))
        for role, maximum in [('judge', 32000), ('auditor', 4096), ('target', 16384)]:
            arm.reserve(role, maximum)
        self.assertEqual(len(parent.entries), 3)
        self.assertFalse(parent.halted)

    def test_exact_and_after_expiry_halt_all_roles_before_api_or_entries(self):
        for offset in (0, 1):
            directory = self.root/str(offset)
            allocations = {'openai': 2, 'openrouter': 1}
            parent = ProviderBudget(directory/'providers.json', allocations,
                {'provider_allocations_usd': allocations.copy(),
                 'expires_at': '2026-11-15T17:00:00Z'})
            arm = ArmLedger(directory/'baseline.json', parent, 'baseline')
            self.clock.now.return_value = (datetime(2026, 11, 15, 17, tzinfo=timezone.utc)
                                          + timedelta(microseconds=offset))
            calls = []
            async def generate(*args):
                calls.append(args)
                raise AssertionError('Expired lease reached API')
            for role, maximum in [('judge', 32000), ('auditor', 4096), ('target', 16384)]:
                model = SimpleNamespace(api=SimpleNamespace(generate=generate),
                                        config=SimpleNamespace(max_tokens=maximum))
                attach(model, role, arm, directory)
                with self.subTest(offset=offset, role=role), self.assertRaisesRegex(RuntimeError, 'expired'):
                    asyncio.run(model.api.generate([], [], 'auto', model.config))
            self.assertEqual(calls, [])
            self.assertEqual(parent.entries, [])
            self.assertEqual(arm.entries, [])
            self.assertEqual(parent.held, 0)
            saved = json.loads(parent.path.read_text())
            self.assertTrue(saved['halted'])
            self.assertEqual(saved['halt_reason'], 'lease_expired')
            self.assertEqual(saved['entries'], [])

    def test_expiry_preserves_holds_and_admitted_call_can_settle(self):
        parent = self.make_budget()
        admitted = self.arm(parent)
        pending = admitted.reserve('judge', 32000)
        uncertain = self.arm(parent, 'uncertain')
        unknown = uncertain.reserve('auditor', 4096)
        with self.assertRaises(RuntimeError):
            uncertain.settle(unknown, None)
        prior_entries = json.loads(json.dumps(parent.entries))
        prior_held = parent.held
        self.clock.now.return_value = datetime(2026, 11, 15, 18, tzinfo=timezone.utc)
        late_arm = self.arm(parent, 'late')
        with self.assertRaisesRegex(RuntimeError, 'expired'):
            late_arm.reserve('target', 100)
        self.assertEqual(parent.entries, prior_entries)
        self.assertEqual(parent.held, prior_held)
        admitted.settle(pending, SimpleNamespace(input_tokens=1000, output_tokens=100))
        self.assertEqual(parent.entries[0]['status'], 'usage_estimate')
        self.assertEqual(parent.entries[1], prior_entries[1])
        self.assertTrue(parent.halted)
        self.assertEqual(parent.summary()['halt_reason'], 'lease_expired')


if __name__ == '__main__':
    unittest.main()
