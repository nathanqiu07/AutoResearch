"""Small synthetic tests for audit mechanics; no released inputs are opened."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('audit_coverage',Path(__file__).with_name('audit_coverage.py'))
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'synthetic.json';self.path.write_bytes(b'{"synthetic":true}')
        self.ref={'path':str(self.path),'sha256':audit.sha(self.path.read_bytes())}
    def tearDown(self):self.tmp.cleanup()
    def test_initial_mutation_fails_before_parse(self):
        self.path.write_text('{"synthetic":false}')
        with self.assertRaisesRegex(ValueError,'Input hash mismatch'):audit.Inputs().get(self.ref,'synthetic')
    def test_post_read_mutation_fails(self):
        reader=audit.Inputs();reader.get(self.ref,'synthetic');self.path.write_text('{"synthetic":false}')
        with self.assertRaisesRegex(ValueError,'after read'):reader.finish()
    def test_conflicting_ref_pin_fails(self):
        reader=audit.Inputs();reader.get(self.ref,'synthetic')
        with self.assertRaisesRegex(ValueError,'Conflicting'):reader.get(dict(self.ref,sha256='0'*64),'synthetic')
    def test_relocated_exact_inventory_passes(self):
        reader=audit.Inputs();reader.get(self.ref,'synthetic');inventory=reader.inventory({})
        relocated=self.root/'relocated.json';self.path.rename(relocated);inventory['files'][0]['read_path']=str(relocated)
        replay=audit.Inputs(inventory);self.assertEqual(replay.get(self.ref,'synthetic'),{'synthetic':True});replay.finish()
    def test_replay_undeclared_input_fails(self):
        reader=audit.Inputs();reader.get(self.ref,'synthetic');replay=audit.Inputs(reader.inventory({}))
        with self.assertRaisesRegex(ValueError,'Undeclared'):replay.get(dict(self.ref,path=str(self.root/'extra.json')),'synthetic')
    def test_replay_omitted_input_fails(self):
        reader=audit.Inputs();reader.get(self.ref,'synthetic');replay=audit.Inputs(reader.inventory({}))
        with self.assertRaisesRegex(ValueError,'input set differs'):replay.finish()
    def test_inventory_pin_mutation_fails(self):
        reader=audit.Inputs();reader.get(self.ref,'synthetic');inventory=reader.inventory({});inventory['files'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'inventory changed'):audit.Inputs(inventory)
    def test_duplicate_and_nonfinite_json_fail(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.assertRaises(ValueError):audit.strict(raw)

class RebindTests(unittest.TestCase):
    def fixture(self):
        old={'manifest':{'job_id':'synthetic'},'config':{'method':'synthetic'},'release':{'path':'/synthetic/old','sha256':'a'*64},'lease':{'lease_id':'old','job_id':'synthetic','owner':'synthetic'}}
        new=copy.deepcopy(old);new['lease']['lease_id']='new';new['release']['path']='/synthetic/new';new['continuation_provenance']={'synthetic':True}
        return old,new
    def test_exact_conditioning_and_changed_lease_pass(self):
        old,new=self.fixture();audit.allowed_rebind(old,new,audit.Checks(),'synthetic')
    def test_changed_config_rejected(self):
        old,new=self.fixture();new['config']['method']='changed'
        with self.assertRaisesRegex(ValueError,'same_config'):audit.allowed_rebind(old,new,audit.Checks(),'synthetic')
    def test_extra_null_key_not_erased(self):
        old,new=self.fixture();new['unexpected']=None
        with self.assertRaisesRegex(ValueError,'same_packet'):audit.allowed_rebind(old,new,audit.Checks(),'synthetic')
    def test_lease_owner_change_rejected(self):
        old,new=self.fixture();new['lease']['owner']='changed'
        with self.assertRaisesRegex(ValueError,'same_lease'):audit.allowed_rebind(old,new,audit.Checks(),'synthetic')

class OutcomeTests(unittest.TestCase):
    def rows(self):return [{'origin':'synthetic','method':'P0','researcher_id':'synthetic','cap':1,'evidence_policy':'synthetic','status':'complete','usage':{'attempted_calls':1,'known_estimate_nanos':7,'retained_hold_nanos':0,'input_tokens':0,'output_tokens':2}}]
    def test_changed_outcome_changes_summary(self):
        rows=self.rows();before=audit.summarize(rows);rows[0]['status']='invalid';after=audit.summarize(rows)
        self.assertEqual(before['status_counts'],{'complete':1});self.assertEqual(after['status_counts'],{'invalid':1});self.assertNotEqual(before,after)
    def test_unknown_usage_remains_unknown_not_zero(self):
        rows=self.rows();self.assertEqual(audit.summarize(rows)['unknown_input_usage_cells'],0);rows[0]['usage']['input_tokens']=None
        self.assertEqual(audit.summarize(rows)['unknown_input_usage_cells'],1);self.assertIsNone(rows[0]['usage']['input_tokens'])
    def test_nano_precision(self):self.assertEqual(audit.nanos('0.019078625'),19078625)

if __name__=='__main__':unittest.main(verbosity=2)
