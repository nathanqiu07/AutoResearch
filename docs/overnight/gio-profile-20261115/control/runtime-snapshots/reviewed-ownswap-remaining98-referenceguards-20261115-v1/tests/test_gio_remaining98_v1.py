import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
P=Path('/private/tmp/gio_prepare_remaining98_v1.py')
class Remaining98(unittest.TestCase):
 def load(self):
  self.assertTrue(P.exists(),'remaining98 helper not implemented');s=importlib.util.spec_from_file_location('remaining98_test_h',P);h=importlib.util.module_from_spec(s);s.loader.exec_module(h);return h
 def test_exact98_capture_and_schema_split(self):
  h=self.load()
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('SQL')):rows=h.capture_rows();blocks=h.batch_blocks(rows)
  self.assertEqual([b['block'] for b in blocks],['P7','P3']);self.assertEqual([len(b['rows']) for b in blocks],[4,3]);self.assertEqual([b['max_calls'] for b in blocks],[56,42]);self.assertEqual([b['max_usd'] for b in blocks],['16.456650','10.132720']);self.assertEqual(sum(len(r['requests']) for r in rows),98);self.assertEqual(len({q['request_sha256'] for r in rows for q in r['requests']}),98)
 def test_actual_native_admission_for_each_homogeneous_batch(self):
  h=self.load();driver=h.p.runtime();from autoresearch.taste.overnight.backends import DollarLedger
  ledger=object.__new__(DollarLedger);template=h.read(h.TEMPLATE)
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('SQL')):
   for block in h.batch_blocks(h.capture_rows()):
    batch=dict(template,release_schema_version=block['release_schema_version'],max_total_attempts=block['max_calls'])
    for row in block['rows']:
     d=h.read(row['packet']);v=h.bind(d,{'path':'/synthetic-only/auth','sha256':'0'*64});j=driver._prepare_packet(v,batch,ledger);self.assertEqual(len(j['items']),14);self.assertEqual(j['profile'].status,'complete');self.assertEqual(j['manifest']['method_id'],block['block'])
if __name__=='__main__':unittest.main()
