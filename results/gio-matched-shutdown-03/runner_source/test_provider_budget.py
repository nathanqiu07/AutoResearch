"""Offline checks for shared local allocations and failure accounting."""
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest

from budget import attach
from provider_budget import ArmLedger, ProviderBudget


class ProviderBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_budget(self, openai=2, openrouter=1):
        allocations = {'openai': openai, 'openrouter': openrouter}
        lease = {'lease_id': 'offline-fixture', 'provider_allocations_usd': allocations.copy()}
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
                           {'provider_allocations_usd': {'openai': 1, 'openrouter': 5}})
        with self.assertRaises(ValueError):
            ProviderBudget(self.root/'providers.json', {'openai': 1},
                           {'provider_allocations_usd': {'openai': 1, 'openrouter': 5}})

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
                {'provider_allocations_usd': {'openai': 2, 'openrouter': 1}})
            arm = ArmLedger(directory/'baseline.json', parent, 'baseline')
            i = arm.reserve('judge', 32000)
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                arm.settle(i, SimpleNamespace(input_tokens=invalid, output_tokens=0))
            self.assertAlmostEqual(arm.held, .82)
            self.assertTrue(arm.halted)
            self.assertFalse(parent.halted)

    def test_existing_budget_cannot_be_reset_and_lease_is_frozen(self):
        allocations = {'openai': 2, 'openrouter': 1}
        lease = {'provider_allocations_usd': allocations.copy(), 'lease_id': 'fixture'}
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


if __name__ == '__main__':
    unittest.main()
