import importlib.util,unittest
from pathlib import Path
H=Path('/private/tmp/gio_prepare_remaining8_v2.py')
class Split(unittest.TestCase):
 def test_exact_two_homogeneous_blocks(self):
  self.assertTrue(H.exists(),'split helper not implemented')
  s=importlib.util.spec_from_file_location('remaining8_split_test',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h);rows=h.read(h.INVENTORY)['drafts'];blocks=h.batch_blocks(rows)
  self.assertEqual([b['block'] for b in blocks],['P7','P3']);self.assertEqual([b['release_schema_version'] for b in blocks],['released-development-v2-p7-peers-v1','released-development-v2']);self.assertEqual([r for b in blocks for r in b['rows']],rows);self.assertEqual([b['max_calls'] for b in blocks],[4,4]);self.assertEqual([b['max_usd'] for b in blocks],['9.63453','9.63453'])
if __name__=='__main__':unittest.main()
