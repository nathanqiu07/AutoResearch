import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
P=Path('/private/tmp/gio_prepare_ownswap_v2.py')
class Admission(unittest.TestCase):
 def test_two_original_donor_target_packets_and_28_exact_wires_no_authority(self):
  self.assertTrue(P.exists(),'ownswap admission helper missing');s=importlib.util.spec_from_file_location('ownswap_admission_test',P);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')),patch('sqlite3.connect',side_effect=AssertionError('SQL')):packets,rows=h.make_drafts()
  self.assertEqual(len(packets),2);self.assertEqual(sum(len(r['requests']) for r in rows),28);self.assertEqual([r['target_researcher_id'] for r in rows],['chris_olah','neel_nanda']);self.assertLessEqual(sum(h.Decimal(r['max_usd']) for r in rows),h.Decimal(1))
  for p in packets:self.assertIsNone(p['lease']);self.assertIsNone(p['assignment_authority']);self.assertIsNone(p['manifest']['allocation']['authorization_source']);self.assertIsNone(p['manifest']['profile_assignment']['authority_sha256']);self.assertNotIn('job_id',p['manifest'])
if __name__=='__main__':unittest.main()
