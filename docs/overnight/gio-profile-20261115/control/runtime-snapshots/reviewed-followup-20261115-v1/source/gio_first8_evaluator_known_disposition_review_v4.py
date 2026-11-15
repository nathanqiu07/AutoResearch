import ast, copy, hashlib, importlib.util, json, re, tempfile, types, unittest
from pathlib import Path
from unittest import mock
SOURCE=Path('/private/tmp/gio_reference_first8_observed_v4.py')
RUNTIME=Path('/Users/giordanorogers/.codex/worktrees/gio-reference-original-eight/AutoResearch-overnight-control/scripts/overnight_labeled_reference.py')
spec=importlib.util.spec_from_file_location('prior_tests','/private/tmp/test_gio_first8_observed_v4.py'); prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior);s=prior.s
node=next(n for n in ast.parse(RUNTIME.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='recovery903_diagnostics')
ns={'hashlib':hashlib,'json':json,'re':re,'Path':Path,'file_sha':s.sha}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(RUNTIME),'exec'),ns)
helper=ns['recovery903_diagnostics']
class KnownDispositionTests(unittest.TestCase):
 def setUp(self):
  self.base=prior.Tests();self.base.setUp();self.addCleanup(self.base.doCleanups)
  self.inc,self.dispatch,self.inspection,self.path=self.base.incident_fixture()
  self.original=s.read_ref(self.inc)['untouched']; self.data=[]
  def put(p,x):p=Path(p);p.write_text(json.dumps(x));return {'path':str(p),'sha256':s.sha(p)}
  self.put=put
  for orig,disp in zip(self.original,self.inspection['untouched_dispositions']):
   packet=Path(orig['plan']['path']).parent
   orig['plan']=put(packet/'plan.json',{'runtime':{'commit':'c'*40}})
   orig['lease']=put(packet/'lease.json',{'max_calls':2,'max_usd':.1})
   put(orig['claim_path'],{'job_id':orig['job_id'],'plan_sha256':orig['plan']['sha256'],'lease_sha256':orig['lease']['sha256']})
   (packet/'output').mkdir();report=put(packet/'output/report.json',{})
   completion=put(packet/'completion.json',{'job_id':orig['job_id'],'report_sha256':report['sha256'],'budgets':[{'spent_usd':.01,'reserved_usd':0}],'attempts':1})
   terminal={'job_id':orig['job_id'],'outcome':'terminal_known_usage','returncode':0,'reported_hold_usd':0,'completion_sha256':completion['sha256'],'report_sha256':report['sha256']}
   events=packet/'events.jsonl';events.write_text(json.dumps({'sequence':0,'stage':'completed','endpoint_body_sha256':'a'*64})+'\n')
   envelope={'kind':'reference','inputs':{'plan':orig['plan'],'lease':orig['lease']},'runtime_commit':'c'*40}
   identity=hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
   claim={'envelope':envelope,'canonical_envelope_sha256':identity}
   et={'canonical_envelope_sha256':identity,'scientific_runtime_commit':'c'*40,'status':'complete','entry_exit_code':0,'wrapper_exit_code':0,'events_sha256':s.sha(events),'event_count':1,'diagnostics':{'diagnostic_write_failed':False,'diagnostic_close_failed':False,'dropped_event_count':0}}
   etref=put(packet/'envelope-terminal.json',et)
   diag={'observed_terminal_valid':True,'actual_wrapper_returncode':0,'canonical_envelope_sha256':identity,'terminal_sha256':etref['sha256'],'events_sha256':s.sha(events),'event_count':1}
   disp.update(status='known_terminal',terminal=put(packet/'terminal.json',terminal),diagnostics_verified=put(packet/'diag.json',diag),envelope_claim=put(packet/'envelope-claim.json',claim),envelope_terminal=etref,events={'path':str(events),'sha256':s.sha(events)})
   self.data.append((terminal,diag,et))
  self.inc=put(self.inc['path'],{'untouched':self.original});self.inspection['incident']=self.inc
 def check(self):
  ref=self.put(self.path,self.inspection)
  with mock.patch.object(s,'INCIDENT',self.inc),mock.patch.object(s,'runtime',return_value=types.SimpleNamespace(recovery903_diagnostics=helper)):
   return s.verify_incident_inspection(ref,self.dispatch)
 def test_both_known_generic_diagnostic_helper_and_conditional903(self):
  self.assertEqual([x['job_id'] for x in self.check()['untouched_dispositions']],['535','903'])
  self.dispatch['recovery903_replacement']={'path':'synthetic-conditional-plan','sha256':'d'*64}
  self.check()
 def test_enriched_plan_refs_now_accept_both_known_dispositions(self):
  for orig in self.original:
   minimal=dict(orig['plan']);orig['plan']={**minimal,'n_records':30,'user_partition':'dev','method_config':{'k':5},'snapshots':{}}
   self.inc=self.put(self.inc['path'],{'untouched':self.original});self.inspection['incident']=self.inc
   with self.subTest(job=orig['job_id']):self.check()
   orig['plan']=minimal;self.inc=self.put(self.inc['path'],{'untouched':self.original});self.inspection['incident']=self.inc
   self.check()
 def test_each_known_job_rejects_altered_claim_plan(self):
  for i,orig in enumerate(self.original):
   p=Path(orig['claim_path']);good=p.read_text();x=json.loads(good);x['plan_sha256']='0'*64;p.write_text(json.dumps(x))
   with self.subTest(job=orig['job_id']),self.assertRaisesRegex(ValueError,'untouched_continuation_not_known_terminal'):self.check()
   p.write_text(good)
 def test_each_known_job_rejects_hold_and_bad_diagnostics(self):
  for i,disp in enumerate(self.inspection['untouched_dispositions']):
   for name,key,bad in [('terminal','reported_hold_usd',.01),('diagnostics_verified','observed_terminal_valid',False),('diagnostics_verified','events_sha256','0'*64)]:
    ref=disp[name];p=Path(ref['path']);good=p.read_text();x=json.loads(good);x[key]=bad;disp[name]=self.put(p,x)
    with self.subTest(job=disp['job_id'],field=key),self.assertRaises(ValueError):self.check()
    p.write_text(good);disp[name]=ref
 def test_each_known_job_rejects_close_and_write_failure(self):
  for i,disp in enumerate(self.inspection['untouched_dispositions']):
   for key in ['diagnostic_close_failed','diagnostic_write_failed']:
    eref=disp['envelope_terminal'];dref=disp['diagnostics_verified'];ep=Path(eref['path']);dp=Path(dref['path']);eg=ep.read_text();dg=dp.read_text()
    x=json.loads(eg);x['diagnostics'][key]=True;disp['envelope_terminal']=self.put(ep,x)
    d=json.loads(dg);d['terminal_sha256']=disp['envelope_terminal']['sha256'];disp['diagnostics_verified']=self.put(dp,d)
    with self.subTest(job=disp['job_id'],field=key),self.assertRaisesRegex(ValueError,'recovery diagnostic failure'):self.check()
    ep.write_text(eg);dp.write_text(dg);disp['envelope_terminal']=eref;disp['diagnostics_verified']=dref
if __name__=='__main__':unittest.main(verbosity=2)
