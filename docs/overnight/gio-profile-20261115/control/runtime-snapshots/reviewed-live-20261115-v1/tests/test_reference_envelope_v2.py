"""Synthetic-only reference integration over actual frozen63 native code/pins."""
import copy,hashlib,importlib.util,json,os,sys,tempfile,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
W=Path('/private/tmp/gio_diagnostic_runtime_envelope_v2.py')
spec=importlib.util.spec_from_file_location('review_reference_wrapper',W)
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
T=Path('/private/tmp/gio-diagnostic-envelope-proposal-v2/reference-envelope-TEMPLATE.json')
template=json.loads(T.read_bytes());R=Path(template['runtime_root']);sys.path.insert(0,str(R))
from autoresearch.taste.backends import OpenAILLM
from autoresearch.llm import Budget
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
class Response:
 status=200
 headers={'x-request-id':'SYNTHETIC_HEADER_CANARY'}
 def __init__(self,seen):self.seen=seen
 def __enter__(self):self.seen.append('enter');return self
 def __exit__(self,*args):self.seen.append('close');return False
 def read(self,n):
  self.seen.append(('read',n))
  return json.dumps({'status':'completed','usage':{'input_tokens':20,'output_tokens':10},'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'SYNTHETIC_RESPONSE'}]}]}).encode()
class Checks(unittest.TestCase):
 def test_actual_reference_pins_cli_wire_read_and_accounting(self):
  self.assertEqual(Path(sys.modules[OpenAILLM.__module__].__file__).resolve(),R/'autoresearch/taste/backends.py')
  with tempfile.TemporaryDirectory(dir='/private/tmp') as td:
   root=Path(td);auth=root/'auth.json';auth.write_text('{"state":"authorized","synthetic":true}')
   env=copy.deepcopy(template);env.update(state='authorized',authorization=ref(auth),output_root=str(root/'diagnostics'))
   original=w.validate
   def validate(e):
    v=copy.deepcopy(e);v['output_root']='/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes/never-created-'+root.name
    return original(v)
   seen=[];captured=[];backend=OpenAILLM(budget=Budget(max_calls=1,max_seconds=600),max_usd=.04,timeout=60)
   def opener(request,*args,**kwargs):captured.append((request,args,kwargs));return Response(seen)
   def entry(path,run_name):
    self.assertEqual(Path(path),R/template['entrypoint']);self.assertEqual(run_name,'__main__');self.assertEqual(Path.cwd(),R)
    self.assertEqual(sys.argv[1:],['run','--plan',template['inputs']['plan']['path'],'--lease',template['inputs']['lease']['path']])
    self.assertEqual(backend.complete('SYNTHETIC_PROMPT_é',system='SYNTHETIC_SYSTEM',max_tokens=1024),'SYNTHETIC_RESPONSE')
    raise SystemExit(0)
   with patch.object(w,'validate',side_effect=validate),patch.object(w.runpy,'run_path',side_effect=entry),patch.object(urllib.request,'urlopen',side_effect=opener),patch.dict(os.environ,{'OPENAI_API_KEY':'SYNTHETIC_KEY'},clear=True):
    self.assertEqual(w.execute(env),0)
   self.assertEqual(len(captured),1);request,args,kwargs=captured[0]
   body={'model':'gpt-6-luna','instructions':'SYNTHETIC_SYSTEM','input':'SYNTHETIC_PROMPT_é','max_output_tokens':1024,'reasoning':{'effort':'none'},'store':False,'service_tier':'default'}
   self.assertEqual(request.data,json.dumps(body,ensure_ascii=False).encode());self.assertEqual(request.full_url,OpenAILLM.base_url);self.assertEqual(kwargs,{'timeout':60});self.assertEqual(args,())
   self.assertEqual(seen,['enter',('read',8000001),'close']);self.assertEqual(backend.budget.calls,1);self.assertEqual(backend.cost_summary()['reserved_usd'],0)
   events=[json.loads(line) for line in (root/'diagnostics/events.jsonl').read_text().splitlines()]
   expected=hashlib.sha256(json.dumps({'endpoint':OpenAILLM.base_url,'body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
   self.assertTrue(events);self.assertTrue(all(e['endpoint_body_sha256']==expected for e in events))
   raw=json.dumps(events);self.assertNotIn('SYNTHETIC',raw)
   terminal=json.loads((root/'diagnostics/envelope-terminal.json').read_bytes());self.assertEqual(terminal['status'],'complete');self.assertEqual(terminal['canonical_envelope_sha256'],w.digest(env))
if __name__=='__main__':unittest.main()
