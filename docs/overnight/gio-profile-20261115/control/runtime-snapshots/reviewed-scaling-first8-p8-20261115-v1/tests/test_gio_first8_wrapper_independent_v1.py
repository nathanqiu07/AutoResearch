"""Narrow additional allowlist cases; no native run or real ledger."""
import copy, importlib.util, json, unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('first8_owner_fixture','/private/tmp/test_gio_first8_wrapper_v1.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
class Additional(unittest.TestCase):
 def setUp(self):
  self.case=f.Tests();self.case.setUp();self.addCleanup(self.case.doCleanups)
 def test_wrong_lease_protocol_with_matching_plan_pin_rejected(self):
  e=copy.deepcopy(self.case.env);p=Path(e['inputs']['lease']['path']);body=json.loads(p.read_text());body['protocol']='newmethods-small-v1';p.write_text(json.dumps(body));e['inputs']['lease']=f.ref(p)
  with self.assertRaisesRegex(ValueError,'reference_plan_or_lease_mismatch'):f.w.validate(e,check_only=True)
 def test_exact_entry_hash_is_checked_before_entry(self):
  real=f.w.sha
  def altered(p):return '0'*64 if Path(p)==f.R/'scripts/overnight_labeled_reference.py' else real(p)
  with patch.object(f.w,'sha',side_effect=altered):
   with self.assertRaisesRegex(ValueError,'exact_first8_runtime_required'):f.w.validate(self.case.env,check_only=True)
 def test_original_generic_reference_runtime_not_allowed(self):
  e=copy.deepcopy(self.case.env);e['runtime_root']='/Users/giordanorogers/.codex/worktrees/gio-overnight-reference/AutoResearch-overnight-control';e['runtime_commit']='63a2c21d1096700f816f4edf71048bcfd4891927'
  with self.assertRaisesRegex(ValueError,'exact_first8_runtime_required'):f.w.validate(e,check_only=True)
if __name__=='__main__':unittest.main()
