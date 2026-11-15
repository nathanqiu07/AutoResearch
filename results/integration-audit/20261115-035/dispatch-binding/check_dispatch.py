#!/usr/bin/env python3
"""Bind two approved neutral dispatch records to saved summaries; never call providers."""
import argparse
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path

RUNTIME='f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
PINS={
'access':{'raw':'c2325220e5e5107126b5e9402693f8fba0d173d5adaa2a7e6cfb952cb8d0ea05','semantic':'bf9fe4406e47cb077e6c7bf964948d79c3c97e09d560b3efbc76492efd564471','summary':'4886347fdc74eca0d7378e7a1ce57aacaf89c875dc334553deef2545c13179b1'},
'readiness':{'raw':'a7f9c9efee581ba5b9233df83682a73d93f19f909d2dfdf014d3e99bcd57d2bf','semantic':'b2c169306768f2a21a2931d13c7dff8f542430a307a5ae7ad942c793067ba8db','summary':'39d14e76f1828574f539d52d366b4e5da1d0bdb7da603d6feffb3691a5b9a668'}}
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
def strict(b):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate JSON key')
   d[k]=v
  return d
 return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def bind(dispatch,summary,backend,add):
 pricing=next(ast.literal_eval(n.value) for n in ast.parse(backend.decode()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PRICING_VERSION' for t in n.targets))
 add('canonical_dispatch_to_summary',digest(dispatch)==summary['dispatch_sha256'])
 add('runtime_identity',dispatch['runtime_commit']==summary['runtime_commit']==RUNTIME)
 add('backend_raw_identity',dispatch['runtime_backend_sha256']==summary['runtime_backend_sha256']==sha(backend))
 add('recorded_script_identity',dispatch['script_sha256']==summary['script_sha256'])
 add('recorded_policy_identity',dispatch['policy']['sha256']==summary['policy_sha256'])
 add('one_call_per_declared_probe',dispatch['max_calls']==len(dispatch['probes'])==summary['attempted_calls']==len(summary['calls']))
 add('ordered_models',[p['model'] for p in dispatch['probes']]==[c['model'] for c in summary['calls']])
 add('terminal_status',summary['status']=='complete' and all(c['status']=='complete' for c in summary['calls']))
 add('declared_total_allocation',sum(Decimal(str(p['max_usd'])) for p in dispatch['probes'])<=Decimal(str(dispatch['max_usd'])))
 calls=[]
 for i,(probe,call) in enumerate(zip(dispatch['probes'],summary['calls'])):
  settings=call['settings'];cost=call['cost'];name='call'+str(i)+'.'
  add(name+'settings_digest',digest(settings)==call['settings_sha256'])
  add(name+'declared_settings',settings['model']==probe['model'] and settings['max_tokens']==dispatch['settings']['max_tokens'] and settings['timeout_cap_seconds']==dispatch['settings']['timeout'] and settings['enforced_settings']['reasoning_effort']==dispatch['settings']['reasoning'])
  add(name+'exact_source_settings',settings=={'model':probe['model'],'max_tokens':dispatch['settings']['max_tokens'],'temperature':0.0,'timeout_cap_seconds':dispatch['settings']['timeout'],
      'enforced_settings':{'adapter_implementation_sha256':digest(backend.decode()),'pricing_version':pricing,'reasoning_effort':dispatch['settings']['reasoning'],'store':False,'tools':[],'service_tier':'default','temperature':'not_sent','prompt_cache_options':{'mode':'implicit','ttl':'30m'}}})
  add(name+'adapter_identity',settings['enforced_settings']['adapter_implementation_sha256']==digest(backend.decode()))
  add(name+'allocation',Decimal(str(cost['max_usd']))==Decimal(str(probe['max_usd'])) and Decimal(str(cost['spent_usd']))+Decimal(str(cost['reserved_usd']))<=Decimal(str(probe['max_usd'])))
  add(name+'complete_recorded_usage',cost['attempted_calls']==1 and cost['reported_usage_complete'] is True and cost['unknown_input_usage_attempts']==0 and cost['unknown_output_usage_attempts']==0)
  calls.append({'model':probe['model'],'settings_sha256':call['settings_sha256'],'max_tokens':settings['max_tokens'],'reasoning':dispatch['settings']['reasoning'],'timeout_cap_seconds':settings['timeout_cap_seconds'],'recorded_max_usd':str(probe['max_usd']),'recorded_known_usd':str(cost['spent_usd']),'recorded_prompt_sha256':call['prompt_sha256'],'recorded_system_sha256':call['system_sha256'],'prompt_system_reconstructed':False})
 return calls

def run(a):
 records={};checked={};all_checks=[]
 def read(path,pin):
  b=Path(path).read_bytes()
  if sha(b)!=pin:raise ValueError('Input hash mismatch')
  checked[str(path)]=(b,pin);return b
 inv=strict(read(a.dispatch_inventory,a.dispatch_inventory_sha256));frozen=strict(read(a.frozen_inputs,a.frozen_inputs_sha256));source=strict(read(a.source_reference,a.source_reference_sha256))
 for inventory in (inv,frozen):
  rows=inventory['files']
  if len({r['path'] for r in rows})!=len(rows) or digest({r['path']:r['sha256'] for r in rows})!=inventory['input_set_sha256']:raise ValueError('Inventory identity mismatch')
 def by_hash(inventory,pin):
  rows=[r for r in inventory['files'] if r['sha256']==pin]
  if len(rows)!=1:raise ValueError('Ambiguous or missing pinned input')
  r=rows[0];b=read(r['read_path'],pin)
  if len(b)!=r['bytes']:raise ValueError('Input size mismatch')
  records[r['path']]={k:v for k,v in r.items() if k!='roles'};return strict(b)
 if len(inv['files'])!=2 or {r['sha256'] for r in inv['files']}!={p['raw'] for p in PINS.values()}:raise ValueError('Unexpected dispatch inventory')
 backend_path=Path(a.source_root)/'autoresearch/taste/overnight/backends.py';backend=read(backend_path,source['files']['autoresearch/taste/overnight/backends.py'])
 results=[]
 for kind,pins in PINS.items():
  dispatch=by_hash(inv,pins['raw']);summary=by_hash(frozen,pins['summary'])
  def add(name,ok):
   all_checks.append({'check':kind+'.'+name,'passed':bool(ok)})
   if not ok:raise ValueError('Failed check: '+kind+'.'+name)
  add('approved_semantic_pin',digest(dispatch)==pins['semantic'])
  calls=bind(dispatch,summary,backend,add)
  results.append({'kind':kind,'dispatch_raw_sha256':pins['raw'],'dispatch_canonical_sha256':digest(dispatch),'summary_raw_sha256':pins['summary'],'recorded_script_sha256':dispatch['script_sha256'],'script_present_in_pinned92_source_map':dispatch['script_sha256'] in source['files'].values(),'probe_text_present_in_dispatch':any(k in dispatch for k in ('prompt','system')) or any(any(k in p for k in ('prompt','system')) for p in dispatch['probes']),'calls':calls})
 for path,(old,pin) in checked.items():
  if Path(path).read_bytes()!=old:raise ValueError('Input changed after read')
 report={'schema_version':'audit035-dispatch-binding-v1','reader_sha256':sha(Path(__file__).read_bytes()),'passed':len(all_checks),'failed':0,'checks':all_checks,'records':results,'raw_inputs_before_after_verified':True,
 'closes':['Exact raw file pins and canonical semantic dispatch linkage to the saved summary.','Ordered model, max-token, reasoning, timeout and per-probe allocation bindings; source backend identity and recorded terminal usage.'],
 'limits':['No new provider call or probe was executed; no authenticated network traffic or provider invoice verified.','The dispatches contain no prompt/system text. Their script hashes match saved summaries, but the two script byte hashes are absent from the pinned 92-file source inventory. Prompt/system hashes remain recorded-only; probe input text was not reconstructed.','This addendum does not join uncertain build jobs to canonical provider requests or alter the frozen 500-input report, manifest or archive.','Current ledger state, authorization beyond these saved dispatch records and profile/score quality are outside scope.']}
 out=Path(a.out);out.mkdir(exist_ok=False)
 (out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');(out/'accessed-inputs.json').write_text(json.dumps({'files':list(records.values()),'metadata_inputs':[{'read_path':p,'sha256':h,'bytes':len(b)} for p,(b,h) in checked.items() if p not in {r['read_path'] for r in records.values()}]},indent=2,sort_keys=True)+'\n')
 print(json.dumps({'passed':len(all_checks),'failed':0,'dispatches':2,'recorded_calls':sum(len(r['calls']) for r in results),'probe_input_text_reconstructed':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ('dispatch-inventory','dispatch-inventory-sha256','frozen-inputs','frozen-inputs-sha256','source-reference','source-reference-sha256','source-root','out'):p.add_argument('--'+name,required=True)
 run(p.parse_args())
