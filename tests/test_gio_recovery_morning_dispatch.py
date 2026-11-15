import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
try:
 from scripts.gio_recovery.morning_dispatch import Registry, file_ref
except ImportError:
 Registry=None
NOW=datetime(2026,11,15,18,tzinfo=timezone.utc)
class MorningDispatchTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(Registry,'morning dispatch helper is not implemented')
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.policy={'schema_version':'gio-morning-budget-v1','state':'issued','campaign_id':'test','provider_allocations_usd':{'openai':200,'openrouter':200},'max_inflight':2,'producer_limits':{'lane01':1,'lane02':2},'admission_deadline':'2026-11-15T19:45:00Z','drain_deadline':'2026-11-15T20:00:00Z'}
  self.registry=Registry.create(self.root/'registry.sqlite',self.policy)
 def lease(self,name='one',producer='lane01',cap=10,attempts=3):
  packet=self.root/name;packet.mkdir();(packet/'settings.json').write_text(json.dumps({'arm':name}));(packet/'checksums.json').write_text(json.dumps({'settings.json':hashlib.sha256((packet/'settings.json').read_bytes()).hexdigest()}))
  d={'status':'issued','owner_chat':'owner','lease_id':name,'packet_checksums_sha256':hashlib.sha256((packet/'checksums.json').read_bytes()).hexdigest(),'expires_at':'2026-11-15T19:45:00Z','provider_allocations_usd':{'openai':cap,'openrouter':cap},'producer_id':producer,'max_inflight':self.policy['producer_limits'][producer],'max_attempts':attempts,'output_root':str(self.root/(name+'-out'))}
  p=self.root/(name+'.json');p.write_text(json.dumps(d));return file_ref(p),packet,d
 def admitted(self,name='one',producer='lane01',cap=10,attempts=3):
  ref,packet,d=self.lease(name,producer,cap,attempts);self.registry.register(ref,packet,now=NOW);self.registry.claim(name,now=NOW);return d
 def test_once_only_claim_and_bound_packet(self):
  ref,packet,d=self.lease();self.registry.register(ref,packet,now=NOW);self.registry.claim('one',now=NOW)
  with self.assertRaises(ValueError):self.registry.claim('one',now=NOW)
  with self.assertRaises(ValueError):self.registry.register(ref,packet,now=NOW)
  ref2,packet2,d2=self.lease('two');(packet2/'settings.json').write_text('changed')
  with self.assertRaises(ValueError):self.registry.register(ref2,packet2,now=NOW)
 def test_aggregate_allocation_and_no_reset(self):
  self.admitted(cap=150);ref,packet,_=self.lease('two',cap=51)
  with self.assertRaises(ValueError):self.registry.register(ref,packet,now=NOW)
  with self.assertRaises(FileExistsError):Registry.create(self.root/'registry.sqlite',self.policy)
 def test_concurrency_shared_across_registry_instances(self):
  self.admitted('one','lane02');self.admitted('two','lane02')
  def reserve(i):
   try:return Registry(self.root/'registry.sqlite').reserve_call('one' if i%2 else 'two','openai',str(i).zfill(64),1,now=NOW)
   except ValueError:return None
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(reserve,range(6)))
  self.assertEqual(sum(x is not None for x in results),2)
 def test_producer_limit_is_shared_between_its_leases(self):
  self.admitted('one');self.admitted('two');self.registry.reserve_call('one','openai','a'*64,1,now=NOW)
  with self.assertRaises(ValueError):self.registry.reserve_call('two','openrouter','b'*64,1,now=NOW)
 def test_unknown_retains_cost_and_blocks_identity_and_lease(self):
  self.admitted('one');self.admitted('two','lane02');self.admitted('three');call=self.registry.reserve_call('one','openai','a'*64,2,now=NOW);self.registry.settle_call(call,None)
  with self.assertRaises(ValueError):self.registry.reserve_call('one','openai','b'*64,1,now=NOW)
  with self.assertRaises(ValueError):self.registry.reserve_call('two','openai','a'*64,1,now=NOW)
  with self.assertRaises(ValueError):self.registry.reserve_call('three','openai','c'*64,1,now=NOW)
  index=self.registry.result_index('one',{});self.assertEqual(index['accounting']['openai']['held_usd'],2);self.assertEqual(index['accounting']['openai']['unknown_attempts'],1)
 def test_attempt_cap_and_cost_cap_and_deadline(self):
  self.admitted(attempts=1,cap=1);call=self.registry.reserve_call('one','openai','a'*64,1,now=NOW);self.registry.settle_call(call,.25)
  with self.assertRaises(ValueError):self.registry.reserve_call('one','openai','b'*64,.1,now=NOW)
  self.admitted('two')
  with self.assertRaises(ValueError):self.registry.reserve_call('two','openai','b'*64,11,now=NOW)
  with self.assertRaises(ValueError):self.registry.reserve_call('two','openai','b'*64,1,now=datetime(2026,11,15,19,45,tzinfo=timezone.utc))
 def test_bound_violation_retained_and_no_double_settlement(self):
  self.admitted();call=self.registry.reserve_call('one','openai','a'*64,1,now=NOW)
  with self.assertRaises(ValueError):self.registry.settle_call(call,2)
  with self.assertRaises(ValueError):self.registry.settle_call(call,.1)
  self.assertEqual(self.registry.result_index('one',{})['accounting']['openai']['known_usd'],2)
 def test_index_retains_missing_outputs_and_hashes_actual_artifacts(self):
  d=self.admitted();out=Path(d['output_root']);out.mkdir();(out/'summary.json').write_text('{"state":"failed"}')
  index=self.registry.result_index('one',{'summary':'summary.json','trace':'trace.json'})
  self.assertEqual(index['artifacts']['summary'],file_ref(out/'summary.json'));self.assertIsNone(index['artifacts']['trace']);self.assertIn('trace',index['missing_artifacts']);self.assertEqual(index['accounting']['openai']['known_attempts'],0)
  with self.assertRaises(ValueError):self.registry.result_index('one',{'escape':'../one.json'})
 def test_openai_only_lease_zero_openrouter_and_disabled_provider(self):
  ref,packet,d=self.lease();d['provider_allocations_usd']['openrouter']=0;Path(ref['path']).write_text(json.dumps(d));ref=file_ref(ref['path'])
  self.registry.register(ref,packet,now=NOW);self.registry.claim('one',now=NOW)
  self.registry.reserve_call('one','openai','a'*64,1,now=NOW)
  with self.assertRaises(ValueError):self.registry.reserve_call('one','openrouter','b'*64,0,now=NOW)
 def test_root_budget_adapter_enforces_producer_suballocations(self):
  budget={'schema_version':'gio-morning-aggregate-allocation-v1','state':'allocated_new_sprint','campaign_id':'root','new_sprint_shared_allocation_usd':{'openai':'200','openrouter':'200'},'suballocations_usd':{'lane01':{'openai':'5','openrouter':'1'}},'global_max_concurrent_provider_calls':9,'admission_cutoff':'2026-11-15T19:45:00Z','demo_deadline':'2026-11-15T20:00:00Z'}
  registry=Registry.create(self.root/'root.sqlite',budget,producer_limits={'lane01':1})
  ref,packet,d=self.lease(cap=6)
  with self.assertRaises(ValueError):registry.register(ref,packet,now=NOW)
if __name__=='__main__':unittest.main()
