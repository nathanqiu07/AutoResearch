import ast,copy,importlib.util,json,tempfile,unittest
from pathlib import Path
P=Path('/private/tmp/gio_diagnostic_runtime_envelope_ownswap_v1.py')
class Wrapper(unittest.TestCase):
 def load(self):
  self.assertTrue(P.exists(),'ownswap wrapper missing');s=importlib.util.spec_from_file_location('ownswap_wrapper_test',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def test_allowlist_is_only_exact_successor(self):
  m=self.load();self.assertEqual(m.RUNTIMES,{'profile':('0b051f878b37f7687fb144f5e3090ef98a811000','docs/overnight/gio-profile-20261115/control/run_batch.py')})
 def test_transport_eventlog_execute_unchanged(self):
  m=self.load();a=ast.parse(P.read_text());b=ast.parse(Path('/private/tmp/gio_diagnostic_runtime_envelope_v2.py').read_text())
  for name in ('EventLog','execute','deadline','write'):
   self.assertEqual(ast.dump(next(n for n in a.body if getattr(n,'name',None)==name)),ast.dump(next(n for n in b.body if getattr(n,'name',None)==name)))
if __name__=='__main__':unittest.main()
