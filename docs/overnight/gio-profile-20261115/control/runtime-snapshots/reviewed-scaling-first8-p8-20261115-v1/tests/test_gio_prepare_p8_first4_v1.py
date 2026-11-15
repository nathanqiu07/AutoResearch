import copy, importlib.util, unittest
from pathlib import Path
from unittest.mock import patch
MODULE=Path('/private/tmp/gio_prepare_p8_first4_v1.py')
def module():
 if not MODULE.exists():return None
 s=importlib.util.spec_from_file_location('p8_prepare_tests',MODULE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Tests(unittest.TestCase):
 def setUp(self):
  self.m=module();self.assertIsNotNone(self.m,'first4 helper not implemented')
 def draft(self):
  return {'schema_version':'overnight-packet-v1','lease':None,'profile':None,'item_ids':[],'manifest':{'kind':'build','method_id':'P8','personalization_cap':8192,'replicate_id':0,'allocation':{'authorization_source':None,'max_calls':1,'max_seconds':240,'max_usd':.8028775}},'backend':{'model':'gpt-6-sol','reasoning':'medium','max_calls':1,'max_seconds':240,'timeout':180,'max_usd':.8028775},'config':{'method_id':'P8','personalization_cap':8192,'replicate_id':0,'researcher_id':'chris_olah','evidence_policy':'explicit-only','extractor_settings':{'temperature':0.0,'max_tokens':16384}}}
 def test_bind_changes_authority_and_identity_only(self):
  d=self.draft();before=copy.deepcopy(d);p=self.m.bind(d,{'path':'/authority','sha256':'a'*64});self.assertEqual(d,before)
  p['lease']=None;p['manifest'].pop('job_id');p['manifest']['allocation']['authorization_source']=None;self.assertEqual(p,d)
 def test_rebinding_or_wrong_method_model_settings_rejected(self):
  for key in ('lease','method','model','settings'):
   d=self.draft()
   if key=='lease':d['lease']={}
   elif key=='method':d['manifest']['method_id']='P7'
   elif key=='model':d['backend']['model']='gpt-6-luna'
   else:d['config']['extractor_settings']['max_tokens']=8192
   with self.assertRaises(ValueError):self.m.bind(d,{})
 def test_authority_before_any_live_ledger_read(self):
  with patch.object(self.m,'read',return_value={'state':'proposed'}),patch.object(self.m.a,'validate_astra_authority') as gate:
   with self.assertRaises(ValueError):self.m.validate_authority({})
   gate.assert_not_called()
 def test_both_identity_conventions_deny_and_wire_unchanged(self):
  info=self.m.request_metadata('gpt-6-sol','synthetic prompt','system',{'temperature':0.0,'max_tokens':16384})
  for convention,key in [('body_compact_json_sha256','request_sha256'),('endpoint_body_sorted_json_sha256','endpoint_body_sha256')]:
   deny={'body_compact_json_sha256':[],'endpoint_body_sorted_json_sha256':[]};deny[convention]=[info[key]]
   with self.assertRaises(ValueError):self.m.reject_unknown(info,deny)
 def test_request_schema_does_not_send_temperature_or_tools(self):
  body=self.m.request_body('gpt-6-astra','prompt','system',{'temperature':0.0,'max_tokens':16384})
  self.assertNotIn('temperature',body);self.assertNotIn('tools',body);self.assertEqual(body['reasoning'],{'effort':'medium'});self.assertEqual(body['max_output_tokens'],16384)
 def test_exact_existing_first_four_pins(self):
  self.assertEqual([r['draft_number'] for r in self.m.DRAFTS],[0,1,5,6]);self.assertEqual(len({r['sha256'] for r in self.m.DRAFTS}),4)
if __name__=='__main__':unittest.main()
