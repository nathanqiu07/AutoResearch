"""Offline token-accounting contract tests; no providers or old ledgers are touched."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from budget import Ledger, attach
from provider_budget import ArmLedger, ProviderBudget


class CacheAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        p=patch('provider_budget.datetime',wraps=datetime);clock=p.start();clock.now.return_value=datetime(2026,11,15,12,tzinfo=timezone.utc);self.addCleanup(p.stop)

    def ledgers(self):
        caps={'openai':3,'openrouter':1}
        lease={'provider_allocations_usd':caps,'lease_id':'offline-fixture','expires_at':'2026-11-15T17:00:00Z'}
        provider=ProviderBudget(self.root/'provider.json',caps,lease)
        return [('legacy',Ledger(self.root/'legacy.json',3)),('provider',ArmLedger(self.root/'arm.json',provider,'offline-fixture'))]

    def test_audit039_cache_read_is_priced_once_at_full_input_rate(self):
        usage=SimpleNamespace(input_tokens=11324,input_tokens_cache_read=9088,input_tokens_cache_write=None,output_tokens=9062)
        for name,ledger in self.ledgers():
            i=ledger.reserve('judge',32000);ledger.settle(i,usage)
            with self.subTest(ledger=name):
                self.assertAlmostEqual(ledger.held,.116135)
                entry=ledger.entries[i]
                self.assertEqual(entry['input_tokens'],11324)
                self.assertEqual(entry['input_tokens_cache_read'],9088)
                self.assertIsNone(entry['input_tokens_cache_write'])
                self.assertEqual(entry['total_input_tokens'],20412)
                self.assertEqual(entry['usage_contract'],'inspect-normalized-v1')
                saved=json.loads((ledger.provider_budget.path if name=='provider' else ledger.path).read_text())
                self.assertEqual(saved['priced_input_field'],'total_input_tokens')
                self.assertEqual(saved['cost_basis'],'same_saved_rates_full_input_estimate_or_retained_reservation_not_provider_invoice')

    def test_uncached_and_cache_write_counts_are_preserved(self):
        for name,ledger in self.ledgers():
            first=ledger.reserve('judge',32000);ledger.settle(first,SimpleNamespace(input_tokens=1000,output_tokens=100))
            second=ledger.reserve('judge',32000);ledger.settle(second,SimpleNamespace(input_tokens=1000,input_tokens_cache_read=200,input_tokens_cache_write=300,output_tokens=100))
            with self.subTest(ledger=name):
                self.assertAlmostEqual(ledger.entries[first]['charged_usd'],.00225)
                self.assertAlmostEqual(ledger.entries[second]['charged_usd'],.002875)
                self.assertEqual(ledger.entries[second]['total_input_tokens'],1500)

    def test_provider_total_contract_does_not_add_cache_details_again(self):
        usage=SimpleNamespace(input_tokens=20412,input_tokens_details=SimpleNamespace(cached_tokens=9088,cache_write_tokens=None),output_tokens=9062)
        for name,ledger in self.ledgers():
            i=ledger.reserve('judge',32000);ledger.settle(i,usage,usage_contract='openai-responses-total-v1')
            with self.subTest(ledger=name):
                self.assertAlmostEqual(ledger.held,.116135)
                self.assertEqual(ledger.entries[i]['input_tokens'],20412)
                self.assertEqual(ledger.entries[i]['total_input_tokens'],20412)
                self.assertEqual(ledger.entries[i]['input_tokens_cache_read'],9088)
                self.assertEqual(ledger.entries[i]['usage_contract'],'openai-responses-total-v1')

    def test_mixed_shape_is_rejected_without_releasing_hold(self):
        usage=SimpleNamespace(input_tokens=100,input_tokens_details=SimpleNamespace(cached_tokens=50),input_tokens_cache_read=50,output_tokens=0)
        for name,ledger in self.ledgers():
            i=ledger.reserve('judge',32000)
            with self.subTest(ledger=name),self.assertRaises(ValueError):ledger.settle(i,usage)
            self.assertEqual(ledger.entries[i]['status'],'invalid_usage_reservation_retained')
            self.assertAlmostEqual(ledger.held,.82)
            self.assertTrue(ledger.halted)

    def test_invalid_cache_counts_retain_hold(self):
        for invalid in (-1,True,1.5,float('nan'),float('inf'),'10',1_000_000_001):
            for name in ('legacy','provider'):
                with self.subTest(value=invalid,ledger=name),tempfile.TemporaryDirectory() as d:
                    root=Path(d)
                    if name=='legacy':ledger=Ledger(root/'ledger.json',3)
                    else:
                        caps={'openai':3,'openrouter':1};parent=ProviderBudget(root/'p.json',caps,{'provider_allocations_usd':caps,'expires_at':'2026-11-15T17:00:00Z'})
                        ledger=ArmLedger(root/'ledger.json',parent,'fixture')
                    i=ledger.reserve('judge',32000)
                    usage=SimpleNamespace(input_tokens=1,input_tokens_cache_write=invalid,output_tokens=0)
                    with self.assertRaises(ValueError):ledger.settle(i,usage)
                    self.assertAlmostEqual(ledger.held,.82)
                    self.assertEqual(ledger.entries[i]['status'],'invalid_usage_reservation_retained')

    def test_full_input_not_uncached_component_enforces_context_bound(self):
        usage=SimpleNamespace(input_tokens=1,input_tokens_cache_read=400000,output_tokens=0)
        for name,ledger in self.ledgers():
            i=ledger.reserve('judge',32000)
            with self.subTest(ledger=name),self.assertRaises(RuntimeError):ledger.settle(i,usage)
            self.assertEqual(ledger.entries[i]['total_input_tokens'],400001)
            self.assertEqual(ledger.entries[i]['status'],'BOUND_EXCEEDED_STOP')
            self.assertGreaterEqual(ledger.held,.82)
            self.assertTrue(ledger.halted)

    def test_legacy_reservation_cannot_be_settled_twice_after_any_terminal_state(self):
        cases={
            'invalid':SimpleNamespace(input_tokens=1,input_tokens_cache_read=-1,output_tokens=0),
            'unknown':None,
            'bound':SimpleNamespace(input_tokens=1,input_tokens_cache_read=400000,output_tokens=0),
            'success':SimpleNamespace(input_tokens=1,output_tokens=0),
        }
        for state,usage in cases.items():
            with self.subTest(state=state),tempfile.TemporaryDirectory() as d:
                ledger=Ledger(Path(d)/'ledger.json',3);i=ledger.reserve('judge',32000)
                if state=='invalid':
                    with self.assertRaises(ValueError):ledger.settle(i,usage)
                elif state in ('bound','unknown'):
                    with self.assertRaises(RuntimeError):ledger.settle(i,usage)
                else:ledger.settle(i,usage)
                before=json.loads(json.dumps(ledger.entries));held=ledger.held
                with self.assertRaises(ValueError):ledger.settle(i,SimpleNamespace(input_tokens=0,output_tokens=0))
                self.assertEqual(ledger.entries,before);self.assertEqual(ledger.held,held)

    def test_legacy_invalid_reservation_index_cannot_mutate_a_pending_entry(self):
        ledger=Ledger(self.root/'legacy.json',3);ledger.reserve('judge',32000)
        for index in (-1,True,0.0,'0',1):
            with self.subTest(index=index),self.assertRaises(ValueError):
                ledger.settle(index,SimpleNamespace(input_tokens=0,output_tokens=0))
            self.assertAlmostEqual(ledger.held,.82)
            self.assertEqual(ledger.entries[0]['status'],'pending')

    def test_legacy_transport_error_reservation_cannot_be_settled(self):
        ledger=Ledger(self.root/'legacy.json',3)
        calls=[]
        async def fail(*args):
            calls.append(args)
            raise OSError('Offline transport fixture')
        model=SimpleNamespace(api=SimpleNamespace(generate=fail),config=SimpleNamespace(max_tokens=32000))
        attach(model,'judge',ledger,self.root)
        with self.assertRaises(OSError):
            asyncio.run(model.api.generate([],[],'auto',model.config))
        self.assertEqual(len(calls),1)
        self.assertTrue(ledger.halted)
        self.assertEqual(ledger.entries[0]['error_type'],'OSError')
        self.assertAlmostEqual(ledger.held,.82)
        entries_before=json.loads(json.dumps(ledger.entries))
        saved_before=ledger.path.read_bytes()
        with self.assertRaises(ValueError):
            ledger.settle(0,SimpleNamespace(input_tokens=0,output_tokens=0))
        self.assertEqual(ledger.entries,entries_before)
        self.assertAlmostEqual(ledger.held,.82)
        self.assertEqual(ledger.path.read_bytes(),saved_before)

    def test_legacy_missing_usage_stops_next_attached_request_and_retains_hold(self):
        ledger=Ledger(self.root/'legacy.json',3)
        calls=[]
        async def missing_usage(*args):
            calls.append(args)
            return SimpleNamespace(stop_reason='stop',usage=None)
        model=SimpleNamespace(api=SimpleNamespace(generate=missing_usage),config=SimpleNamespace(max_tokens=32000))
        attach(model,'judge',ledger,self.root)
        with self.assertRaisesRegex(RuntimeError,'Missing usage'):
            asyncio.run(model.api.generate([],[],'auto',model.config))
        self.assertTrue(ledger.halted)
        self.assertEqual(ledger.entries[0]['status'],'unknown_usage_reservation_retained')
        self.assertAlmostEqual(ledger.held,.82)
        saved=json.loads(ledger.path.read_text())
        self.assertEqual(saved['entries'][0]['status'],'unknown_usage_reservation_retained')
        self.assertAlmostEqual(saved['charged_or_reserved_usd'],.82)
        with self.assertRaisesRegex(RuntimeError,'halted'):
            asyncio.run(model.api.generate([],[],'auto',model.config))
        self.assertEqual(len(calls),1)
        self.assertEqual(len(ledger.entries),1)

    def test_native_inspect_normalization_and_provider_total_agree(self):
        from inspect_ai.model import ModelUsage
        from budget import input_token_accounting
        usage=ModelUsage(input_tokens=1000,input_tokens_cache_read=200,input_tokens_cache_write=300,output_tokens=100)
        normalized=input_token_accounting(usage,contract='inspect-normalized-v1')
        raw={'input_tokens':1500,'input_tokens_details':{'cached_tokens':200,'cache_write_tokens':300},'output_tokens':100}
        total=input_token_accounting(raw,contract='openai-responses-total-v1')
        self.assertEqual(normalized.total_input_tokens,total.total_input_tokens)
        self.assertEqual(normalized.total_input_tokens,1500)
        with self.assertRaises(ValueError):input_token_accounting(raw,contract='inspect-normalized-v1')
        with self.assertRaises(ValueError):input_token_accounting(usage,contract='openai-responses-total-v1')
        with self.assertRaises(ValueError):input_token_accounting(usage,contract='guess')
        with self.assertRaises(ValueError):input_token_accounting({'input_tokens':10,'input_tokens_details':{'cached_tokens':11},'output_tokens':0},contract='openai-responses-total-v1')

if __name__=='__main__':unittest.main()
