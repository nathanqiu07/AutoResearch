import importlib.util,json,tempfile,threading,unittest
from pathlib import Path
sp=importlib.util.spec_from_file_location('w','/private/tmp/gio_diagnostic_runtime_envelope_v2.py');w=importlib.util.module_from_spec(sp);sp.loader.exec_module(w)
class Tests(unittest.TestCase):
 def test_two_thread_append_is_complete_and_ordered(self):
  with tempfile.TemporaryDirectory(dir='/private/tmp') as t:
   path=Path(t)/'events.jsonl';log=w.EventLog(path)
   def emit(n):
    for i in range(50):log({'request_sha256':str(n),'stage':'open','i':i})
   threads=[threading.Thread(target=emit,args=(i,)) for i in range(2)]
   for p in threads:p.start()
   for p in threads:p.join()
   log.close();rows=[json.loads(s) for s in path.read_text().splitlines()]
   self.assertEqual([r['sequence'] for r in rows],list(range(100)))
   with self.assertRaises(FileExistsError):w.EventLog(path)
 def test_only_fixed_entrypoint_modes(self):
  with self.assertRaises(ValueError):w.invocation({'kind':'shell','inputs':{}})
 def test_deadline_timezone_and_ceiling(self):
  for value in ['2026-11-15T17:00:01Z','2026-11-15T16:00:00']:
   with self.assertRaises(ValueError):w.deadline(value)
 def test_exact_historical_sets(self):self.assertEqual(len(w.PROFILE),4);self.assertEqual(len(w.REFERENCE),5);self.assertFalse(w.PROFILE&w.REFERENCE)
if __name__=='__main__':unittest.main()
