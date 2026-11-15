"""Read one pinned actual f6 result; never print or persist prediction values."""
import copy, importlib.util, unittest
s=importlib.util.spec_from_file_location('sol_real_schema','/private/tmp/gio_scaling_sol_supervisor_v2.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
RESULT={'path':'/private/tmp/gio-profile-20261115-coordinator/output/c53702b02a47b320977a77536f4926069deb14cc9a5899e5d46199321415030e/result.json','sha256':'b006347d43f440a88075659cfeb09634d8ef7d38e14b2f670cdf226dd89879b4'}
class RealSchema(unittest.TestCase):
 def fixture(self):
  result=m.read(RESULT);row=result['predictions'][0]
  expected={'job_id':result['job_id'],'manifest_sha256':result['manifest_hash'],'item_id':row['item_id'],'item_sha256':row['item_sha256']}
  return result,expected
 def test_real_f6_complete_single_lexical_result_accepted(self):
  result,expected=self.fixture();m.require_repeat_success(result,expected)
 def test_invalid_copy_of_actual_result_blocks_semantic(self):
  result,expected=self.fixture();bad=copy.deepcopy(result)
  bad['status']='partial';bad['predictions'][0]['status']='invalid';bad['predictions'][0]['prediction']=None;bad['counts']={'attempted':1,'complete':0,'error':1}
  events=[]
  def admit(stage):
   if stage=='semantic':m.require_repeat_success(bad,expected)
   events.append(('admit',stage))
  with self.assertRaisesRegex(ValueError,'paired_first_result_not_complete'):
   m.run_sequence(['core','lexical','semantic'],lambda stage:events.append(('call',stage)) or 0,lambda stage:events.append(('known',stage)) or {},admit)
  self.assertEqual([stage for kind,stage in events if kind=='call'],['core','lexical'])
if __name__=='__main__':unittest.main()
