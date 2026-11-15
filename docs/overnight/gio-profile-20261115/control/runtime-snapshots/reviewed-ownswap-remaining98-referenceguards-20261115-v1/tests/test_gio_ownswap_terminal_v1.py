import copy,importlib.util,unittest
from pathlib import Path
P=Path('/private/tmp/gio_verify_ownswap_terminal_v1.py')
class Terminal(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.v=None
  if P.exists():s=importlib.util.spec_from_file_location('ownswap_terminal_test',P);cls.v=importlib.util.module_from_spec(s);s.loader.exec_module(cls.v)
 def fixture(self):
  self.assertIsNotNone(self.v,'terminal verifier not implemented');v=self.v;items=[{'item_id':'i%d'%n,'option_order_id':'o%d'%(n%2),'researcher_id':'target','context':'synthetic','options':['a','b']} for n in range(14)];a={'donor_researcher_id':'donor','target_researcher_id':'target'};m={'job_id':'job','items_hash':v.h.digest(items),'profile_assignment':a,'consumer':{'model':'synthetic'}};rows=[{'item_id':i['item_id'],'item_sha256':v.h.digest(i),'items_sha256':m['items_hash'],'job_id':'job','manifest_sha256':v.h.digest(m),'donor_researcher_id':'donor','target_researcher_id':'target','option_order_id':i['option_order_id'],'profile_assignment_sha256':v.h.digest(a),'actual_consumer':m['consumer'],'status':'complete'} for i in items];r={'profile_assignment':a,'predictions':rows,'counts':{'attempted':14,'complete':14,'error':0}};return m,items,r
 def test_exact_rows_and_known_invalid_preserved(self):
  m,i,r=self.fixture();self.v.verify_rows(m,i,r);r['predictions'][3]['status']='invalid';r['counts'].update(complete=13,error=1);self.v.verify_rows(m,i,r)
 def test_wrong_donor_target_order_or_bindings_rejected(self):
  m,i,r=self.fixture()
  for key in ['donor_researcher_id','target_researcher_id','item_id','item_sha256','items_sha256','job_id','manifest_sha256','option_order_id','profile_assignment_sha256','actual_consumer']:
   changed=copy.deepcopy(r);changed['predictions'][0][key]='wrong'
   with self.subTest(key=key),self.assertRaises(ValueError):self.v.verify_rows(m,i,changed)
  for rows in [r['predictions'][:-1],r['predictions'][::-1],r['predictions']+[r['predictions'][0]]]:
   with self.assertRaises(ValueError):self.v.verify_rows(m,i,dict(r,predictions=rows))
 def test_exact28_closure_and_unknown_extra_spend_fail(self):
  self.assertIsNotNone(self.v,'terminal verifier not implemented');n={'attempted_calls':28,'known_spent_nanos':300,'ledger_attempts':28,'ledger_spent_nanos':300};c={'attempts':28,'known_nanos':300,'pending':0,'uncertain':0,'held_nanos':0};self.v.close_accounting(n,c)
  for key,value in [('attempts',29),('known_nanos',301),('pending',1),('uncertain',1),('held_nanos',1)]:
   with self.subTest(key=key),self.assertRaises(ValueError):self.v.close_accounting(n,dict(c,**{key:value}))
  with self.assertRaises(ValueError):self.v.close_accounting(dict(n,attempted_calls=27),c)
if __name__=='__main__':unittest.main()
