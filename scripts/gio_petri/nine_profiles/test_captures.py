import unittest,json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runner import check_inputs, author_meta_diagnostic
class Additions(unittest.TestCase):
 def fixture(self,root,text):
  (root/'calls').mkdir()
  for i,role in enumerate(('auditor','target','judge')):
   (root/'calls'/f'call-{i:04d}-{role}.json').write_text(json.dumps({'request':{'input':[{'content':[{'text':text if role=='auditor' else 'task'}]}]}}))
  (root/'audit-ledger.json').write_text(json.dumps({'entries':[{'role':r} for r in ('auditor','target','judge')]}))
 def test_delivery_then_leak_and_missing_capture(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);text='Long specific profile with {literal} braces';self.fixture(root,text)
   self.assertEqual(check_inputs(root,text)['status'],'passed_full_context_check')
   (root/'calls/call-0001-target.json').write_text(json.dumps({'request':{'input':[{'content':text}]}}))
   self.assertEqual(check_inputs(root,text)['status'],'failed')
   (root/'calls/call-0001-target.json').write_text(json.dumps({'request':{'input':[{'content':'task'}]}}))
   (root/'calls/call-0002-judge.json').unlink()
   self.assertEqual(check_inputs(root,text)['status'],'incomplete')
 def test_empty_control_is_not_everywhere_leak(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);self.fixture(root,'ordinary auditor instructions')
   self.assertEqual(check_inputs(root,'')['status'],'passed_no_profile_control')
 def test_author_meta_is_diagnostic_not_task_failure(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'world').mkdir()
   p=root/'world/attempted-target-inputs.jsonl'
   p.write_text(json.dumps({'messages':[{'role':'user','content':'The target model will be system-prompted to do this.'}]})+'\n')
   result=author_meta_diagnostic(root)
   self.assertTrue(result['flags']);self.assertFalse(result['used_for_reroll'])
   p.write_text(json.dumps({'messages':[{'role':'user','content':'Review the target path for access controls.'}]})+'\n')
   self.assertEqual(author_meta_diagnostic(root)['flags'],[])
if __name__=='__main__':unittest.main()
