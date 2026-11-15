"""Independent first4 review: fake HTTP, memory-only budget, no real ledger or calls."""
import copy,hashlib,importlib.util,json,os,socket,sys,tempfile,unittest,urllib.request
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('p8_independent','/private/tmp/gio_p8_first4_supervisor_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sys.path.insert(0,str(m.h.R))
from autoresearch.llm import Budget
from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
from autoresearch.taste.overnight.contracts import build_profile,ProfileArtifact
from autoresearch.taste.overnight.profiles_hypotheses import register_hypotheses_builders
PROPOSAL={'path':'/private/tmp/gio-p8-first4-offline-proposal-v1/proposal.json','sha256':'385b0f9c71425620f24d98e1949bf8e9af2813cac07684284f34af44d71d5d07'}
def forbidden(*a,**k):raise AssertionError('independent_review_network_or_database_forbidden')
class MemoryLedger(DollarLedger):
 def __init__(self):self.deadline=datetime.now(timezone.utc)+timedelta(hours=1);self.reservations=[];self.finished=[]
 def reserve(self,cost,metadata):self.reservations.append((cost,metadata));return 'synthetic'
 def finish(self,identifier,*,actual_usd,succeeded):self.finished.append((actual_usd,succeeded))
 def summary(self):return {'synthetic':True}
 _connect=forbidden
class Response:
 status=200
 def __init__(self,text):self.text=text;self.read_sizes=[];self.closed=False
 def __enter__(self):return self
 def __exit__(self,*a):self.closed=True
 def read(self,n):
  self.read_sizes.append(n);return json.dumps({'status':'completed','usage':{'input_tokens':20,'output_tokens':10},'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':self.text}]}]}).encode()
def fixture():
 register_hypotheses_builders();proposal=m.read(PROPOSAL);built=[]
 for n,row in enumerate(proposal['drafts']):
  draft=m.read(row['packet']);packet=m.h.bind(draft,{'path':'/synthetic/review-not-issued','sha256':'0'*64});documents=m.read(draft['release'])['sources']['documents'];ledger=MemoryLedger();backend=OpenAIResponsesBackend(model=draft['backend']['model'],reasoning='medium',ledger=ledger,max_usd=draft['backend']['max_usd'],timeout=180,budget=Budget(max_calls=1,max_seconds=240));seen=[];response=Response('{}' if n%2==0 else '{"hypotheses":[],"relations":[]}')
  def opener(request,*a,**k):seen.append((request,a,k));return response
  with patch.object(socket.socket,'connect',forbidden),patch.object(socket,'create_connection',forbidden),patch.object(urllib.request,'urlopen',side_effect=opener),patch.dict(os.environ,{'OPENAI_API_KEY':'SYNTHETIC_KEY'},clear=True):artifact=build_profile(documents,draft['config'],backend)
  built.append((row,packet,artifact,backend,ledger,seen,response))
 return built
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.built=fixture()
 def test_exact_frozen_builder_backend_wire_capture_and_reservation(self):
  total=Decimal(0)
  for row,p,artifact,backend,ledger,seen,response in self.built:
   self.assertEqual(len(seen),1);request,a,k=seen[0];raw=request.data;body=json.loads(raw);pin=row['request'];self.assertEqual(a,());self.assertEqual(k,{'timeout':180.0});self.assertEqual(hashlib.sha256(raw).hexdigest(),pin['wire_bytes_sha256']);self.assertEqual(m.h.digest(body),pin['request_sha256']);self.assertEqual(hashlib.sha256(json.dumps({'endpoint':request.full_url,'body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest(),pin['endpoint_body_sha256']);self.assertEqual(len(raw)+1024,pin['input_token_upper_bound']);self.assertLess(len(raw)+1024+body['max_output_tokens'],272000);self.assertEqual(str(ledger.reservations[0][0]),pin['max_usd_reservation']);self.assertEqual(ledger.reservations[0][1]['request_sha256'],pin['request_sha256']);self.assertEqual(ledger.finished[0][1],True);self.assertEqual(response.read_sizes,[8000001]);self.assertTrue(response.closed);self.assertEqual(body['max_output_tokens'],16384);self.assertEqual(body['reasoning'],{'effort':'medium'});self.assertNotIn('temperature',body);self.assertNotIn('tools',body);total+=ledger.reservations[0][0]
  self.assertEqual(total,Decimal('2.289455'));self.assertEqual([x[2].status for x in self.built],['invalid','empty','invalid','empty'])
 def materialize(self,base):
  def put(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v));return m.ref(p)
  batch={'batch_id':'synthetic-four','jobs':[]};spent=Decimal(0)
  for row,p,artifact,backend,ledger,seen,response in self.built:
   manifest=p['manifest'];jid=manifest['job_id'];status=artifact.status;usage={'attempted_calls':1,'uncertain_attempts':0,'cache_hits':0,'reserved_api_usd':0,'reported_api_usd':float(backend.spent_usd),'budget_detail':backend.cost_summary()};result={'schema_version':'overnight-result-v1','job_id':jid,'manifest_hash':m.h.digest(manifest),'status':status,'usage':usage,'code_sha':manifest['code_sha'],'config_hash':manifest['config_hash'],'source_manifest_hash':manifest['source_manifest_hash'],'actual_backend':manifest['extractor'],'predictions':[],'counts':{'attempted':1,'complete':0,'error':1},'profile':artifact.to_dict(),'profile_hash':artifact.profile_id};result_ref=put(base/'output'/jid/'result.json',result);put(base/'output'/jid/'profile.json',artifact.to_dict());put(base/'lease'/(jid+'.json'),{'manifest':manifest,'lease':p['lease'],'status':'claimed'});batch['jobs'].append(put(base/'packets'/(jid+'.json'),p));put(base/'receipts/synthetic-four/execution'/jid/'receipt.json',{'schema_version':'overnight-dispatch-receipt-v1','job_id':jid,'manifest_sha256':m.h.digest(manifest),'status':status,'usage':usage,'result_path':result_ref['path']});spent+=backend.spent_usd
  put(base/'receipts/synthetic-four/execution/summary.json',{'schema_version':'overnight-batch-result-v1','batch_id':'synthetic-four','status':'complete','stop_reason':None,'counts':{'listed':4,'dispatched':4,'not_dispatched':0,'complete':0,'other':4},'ledger':{'inflight':0,'uncertain':0,'reserved_usd':0,'held_after_uncertain':False,'max_inflight':2,'max_usd':80,'attempts':284,'spent_usd':float(Decimal('2.89938')+spent)}});return put(base/'prepared.json',batch)
 def test_native_invalid_empty_artifacts_remain_known_terminal(self):
  with tempfile.TemporaryDirectory(dir='/private/tmp') as td:
   base=Path(td);pr=self.materialize(base)
   with patch.object(m,'B',base):result=m.native_terminal(pr)
   self.assertEqual(result['attempted_calls'],4);self.assertEqual([r['status'] for r in result['outcomes']],['invalid','empty','invalid','empty']);self.assertEqual(result['ledger_attempts'],284)
 def test_native_extra_attempt_or_unknown_fails(self):
  for change in ('attempted_calls','uncertain_attempts'):
   with tempfile.TemporaryDirectory(dir='/private/tmp') as td:
    base=Path(td);pr=self.materialize(base);batch=m.read(pr);p=m.read(batch['jobs'][0]);jid=p['manifest']['job_id'];rp=base/'receipts/synthetic-four/execution'/jid/'receipt.json';xp=base/'output'/jid/'result.json';r=json.loads(rp.read_text());x=json.loads(xp.read_text());r['usage'][change]=x['usage'][change]=2 if change=='attempted_calls' else 1;rp.write_text(json.dumps(r));xp.write_text(json.dumps(x))
    with patch.object(m,'B',base),self.assertRaises(ValueError):m.native_terminal(pr)
 def test_native_source_integrity_tamper_rejected(self):
  with tempfile.TemporaryDirectory(dir='/private/tmp') as td:
   base=Path(td);pr=self.materialize(base);jid=m.read(m.read(pr)['jobs'][0])['manifest']['job_id'];p=base/'output'/jid/'profile.json';v=json.loads(p.read_text());v['documents_hash']='tampered';p.write_text(json.dumps(v))
   with patch.object(m,'B',base),self.assertRaises(ValueError):m.native_terminal(pr)
 def test_duplicate_and_unknown_diagnostics_rejected(self):
  e={'sequence':0,'schema_version':'provider-boundary-diagnostics-v3','stage':'open','http_status':200,'exception_type':None,'request_sha256':'a','endpoint_body_sha256':'b'}
  with self.assertRaises(ValueError):m.g.validate_events([e,dict(e,sequence=1)],{'a':'b'},2)
  with self.assertRaises(ValueError):m.g.validate_events([dict(e,stage='denied',exception_type='ProviderRequestDenied')],{'a':'b'},1)
if __name__=='__main__':unittest.main()
