import importlib.util,tempfile,types,unittest,json
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('remaining98_sequence_tests','/private/tmp/gio_remaining98_supervisor_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return cls(2026,11,15,14,tzinfo=timezone.utc)
class Sequence(unittest.TestCase):
 def exercise(self,failure=None):
  with tempfile.TemporaryDirectory(prefix='gio-remaining98-sequence-') as td,ExitStack() as e:
   root=Path(td)/'supervisor';base={'attempts':306,'spent':3883810000};state={'attempts':306,'known_nanos':3883810000,'known_usd':'3.883810','held_usd':'0','pending':0,'uncertain':0};launches=[];validations=[]
   w=types.SimpleNamespace(now=lambda:Clock.now(),validate=lambda env:None);index={'authority':{'path':'/synthetic/auth','sha256':'a'*64}};stages=[{'block':name,'jobs':4 if name=='P7' else 3,'max_calls':56 if name=='P7' else 42,'prepared':{'path':'/synthetic/'+name,'sha256':'b'*64},'allowed':{},'envelope':{'output_root':str(Path(td)/name)}} for name in ('P7','P3')]
   def authority(*a,**kw):
    validations.append(1);v=dict(state)
    if failure=='readmission' and len(validations)==3:v['attempts']+=1
    return {},{},v,{},base
   def run(*a,**kw):
    launches.append(1);state.update(attempts=state['attempts']+(56 if len(launches)==1 else 42),known_nanos=state['known_nanos']+100);state['known_usd']=str(state['known_nanos']/1000000000);return types.SimpleNamespace(returncode=2 if failure=='nonzero' or (failure=='second_nonzero' and len(launches)==2) else 0)
   def native(*a):
    if failure=='unknown' or (failure=='second_unknown' and len(launches)==2):raise ValueError('unresolved_unknown')
    return {'attempted_calls':56 if len(launches)==1 else 42,'known_spent_nanos':100,'ledger_attempts':state['attempts']+(1 if failure=='cumulative' else 0),'ledger_spent_nanos':state['known_nanos'],'outcomes':[{'status':'invalid'},{'status':'empty'}]*2}
   def diagnostic(*a):
    if failure=='diagnostics':raise ValueError('missing_or_denied_diagnostics')
    return {'known':True}
   e.enter_context(patch.object(m,'ROOT',root));e.enter_context(patch.object(m,'datetime',Clock));e.enter_context(patch.object(m,'preflight',return_value=(w,index,{},base,stages)));e.enter_context(patch.object(m.h,'validate_authority',side_effect=authority));e.enter_context(patch.object(m.subprocess,'run',side_effect=run));e.enter_context(patch.object(m,'native_terminal',side_effect=native));e.enter_context(patch.object(m.g,'diagnostic_terminal',side_effect=diagnostic));e.enter_context(patch.object(m,'ref',side_effect=lambda p:{'path':str(p),'sha256':'0'*64}));e.enter_context(patch('sys.argv',['supervisor','--ready-index','/synthetic/index','0'*64]));e.enter_context(patch('builtins.print'))
   rc=m.main();terminal=json.loads((root/'supervisor-terminal.json').read_text());return rc,len(launches),terminal
 def test_known_p7_growth_permits_p3_and_reaches404(self):
  rc,n,t=self.exercise();self.assertEqual((rc,n,t['status'],len(t['completed_verified_batches'])),(0,2,'complete',2));self.assertEqual(t['known_verified_attempts'],404)
 def test_unknown_p7_prevents_p3(self):self.assertEqual(self.exercise('unknown')[:2],(2,1))
 def test_nonzero_p7_prevents_p3(self):self.assertEqual(self.exercise('nonzero')[:2],(2,1))
 def test_missing_diagnostics_prevents_p3(self):self.assertEqual(self.exercise('diagnostics')[:2],(2,1))
 def test_cumulative_mismatch_prevents_p3(self):self.assertEqual(self.exercise('cumulative')[:2],(2,1))
 def test_changed_accounting_at_readmission_prevents_p3(self):self.assertEqual(self.exercise('readmission')[:2],(2,1))
 def test_second_unknown_preserves_first_known_batch(self):
  rc,n,t=self.exercise('second_unknown');self.assertEqual((rc,n,len(t['completed_verified_batches']),t['known_verified_attempts']),(2,2,1,362))
 def test_second_nonzero_preserves_first_known_batch(self):
  rc,n,t=self.exercise('second_nonzero');self.assertEqual((rc,n,len(t['completed_verified_batches']),t['known_verified_attempts']),(2,2,1,362))
if __name__=='__main__':unittest.main()
