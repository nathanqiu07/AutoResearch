"""Synthetic binding controls; no released inputs."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('check_dispatch',Path(__file__).with_name('check_dispatch.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BindingTests(unittest.TestCase):
 def fixture(self):
  backend=b"PRICING_VERSION = 'synthetic'\n"
  d={'runtime_commit':m.RUNTIME,'runtime_backend_sha256':m.sha(backend),'script_sha256':'a'*64,'policy':{'sha256':'b'*64},'max_calls':2,'max_usd':'0.2','probes':[{'model':'synthetic-A','max_usd':'0.1'},{'model':'synthetic-B','max_usd':'0.1'}],'settings':{'max_tokens':8,'reasoning':'medium','timeout':1}}
  calls=[]
  for p in d['probes']:
   settings={'model':p['model'],'max_tokens':8,'temperature':0.0,'timeout_cap_seconds':1,'enforced_settings':{'adapter_implementation_sha256':m.digest(backend.decode()),'pricing_version':'synthetic','reasoning_effort':'medium','store':False,'tools':[],'service_tier':'default','temperature':'not_sent','prompt_cache_options':{'mode':'implicit','ttl':'30m'}}}
   calls.append({'model':p['model'],'status':'complete','settings':settings,'settings_sha256':m.digest(settings),'cost':{'max_usd':0.1,'spent_usd':0.01,'reserved_usd':0,'attempted_calls':1,'reported_usage_complete':True,'unknown_input_usage_attempts':0,'unknown_output_usage_attempts':0},'prompt_sha256':'c'*64,'system_sha256':'d'*64})
  s={'runtime_commit':m.RUNTIME,'runtime_backend_sha256':m.sha(backend),'script_sha256':'a'*64,'policy_sha256':'b'*64,'attempted_calls':2,'calls':calls,'status':'complete','dispatch_sha256':m.digest(d)}
  return d,s,backend
 def add(self,name,value):
  if not value:raise ValueError(name)
 def test_valid_binding(self):
  d,s,b=self.fixture();self.assertEqual(len(m.bind(d,s,b,self.add)),2)
 def test_raw_format_and_canonical_hash_are_distinct(self):
  d,_,_=self.fixture();a=json.dumps(d,sort_keys=True).encode();b=json.dumps(d,sort_keys=True,indent=2).encode();self.assertNotEqual(m.sha(a),m.sha(b));self.assertEqual(m.digest(m.strict(a)),m.digest(m.strict(b)))
 def test_reordered_models_rejected(self):
  d,s,b=self.fixture();s['calls'].reverse()
  with self.assertRaisesRegex(ValueError,'ordered_models'):m.bind(d,s,b,self.add)
 def test_extra_enforced_tool_rejected(self):
  d,s,b=self.fixture();s['calls'][0]['settings']['enforced_settings']['tools']=['synthetic'];s['calls'][0]['settings_sha256']=m.digest(s['calls'][0]['settings'])
  with self.assertRaisesRegex(ValueError,'exact_source_settings'):m.bind(d,s,b,self.add)
 def test_changed_allocation_rejected(self):
  d,s,b=self.fixture();s['calls'][0]['cost']['max_usd']=0.2
  with self.assertRaisesRegex(ValueError,'allocation'):m.bind(d,s,b,self.add)
if __name__=='__main__':unittest.main(verbosity=2)
