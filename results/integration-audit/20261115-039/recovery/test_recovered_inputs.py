"""Synthetic negative controls for explicit recovered inputs; no study reads."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('recovered_inputs',Path(__file__).with_name('recovered_inputs.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(b):return hashlib.sha256(b).hexdigest()

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='synthetic039-recovery-');self.root=Path(self.tmp.name);self.retained=self.root/'retained';self.retained.mkdir()
        (self.retained/'record.json').write_bytes(b'{"synthetic":true}\n')
        self.inv=[];self.rows=[];self.archives={}
        for store,name,value in [('retained','record.json',b'{"synthetic":true}\n'),('source','module.py',b'# synthetic code\n'),('publication','review.json',b'{"synthetic":"review"}\n')]:
            record={'commit':'a'*40,'path':store+'/'+name,'sha256':sha(value),'size_bytes':len(value)};self.inv.append(record);self.rows.append({**record,'store':store,'relative_path':name})
            if store!='retained':
                path=self.root/(store+'.tar')
                with tarfile.open(path,'w') as archive:
                    info=tarfile.TarInfo(name);info.size=len(value);archive.addfile(info,io.BytesIO(value))
                self.archives[store]={'archive_sha256':sha(path.read_bytes()),'archive_size_bytes':path.stat().st_size,'member_count':1}
        self.inventory=self.root/'inventory.json';self.inventory.write_text(json.dumps({'files':self.inv}));self.inventory_pin=sha(self.inventory.read_bytes())
        self.mapping=self.root/'map.json';self.data={'original_inventory_sha256':self.inventory_pin,'original_reader_sha256':'b'*64,'files':self.rows,'archives':self.archives}

    def tearDown(self):self.tmp.cleanup()
    def reader(self,map_pin=None):
        self.mapping.write_text(json.dumps(self.data));return m.RecoveryInputs(self.mapping,map_pin or sha(self.mapping.read_bytes()),self.inventory,self.inventory_pin,self.retained,self.root/'source.tar',self.root/'publication.tar')
    def test_success_all_inputs_and_after_hashes(self):
        reader=self.reader()
        for row in self.inv:self.assertEqual(sha(reader.read(row['commit'],row['path'])),row['sha256'])
        result=reader.finish();self.assertEqual(result['logical_inputs_verified'],3);self.assertFalse(result['fallback_allowed'])
    def test_wrong_mapping_hash(self):
        with self.assertRaisesRegex(ValueError,'Metadata hash mismatch'):self.reader('0'*64)
    def test_wrong_retained_bytes(self):
        reader=self.reader();(self.retained/'record.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash/size mismatch'):reader.read('a'*40,'retained/record.json')
    def test_missing_file_has_no_fallback(self):
        reader=self.reader();(self.retained/'record.json').unlink()
        with self.assertRaises(FileNotFoundError):reader.read('a'*40,'retained/record.json')
    def test_unmapped_identity_has_no_fallback(self):
        with self.assertRaisesRegex(ValueError,'Unmapped input'):self.reader().read('a'*40,'unknown.json')
    def test_unsafe_relative_paths(self):
        for value in ['../record.json','/record.json','a/../record.json','a//record.json']:
            with self.subTest(value=value):
                self.data['files'][0]['relative_path']=value
                with self.assertRaisesRegex(ValueError,'Unsafe relative path'):self.reader()
    def test_symlink_input_rejected(self):
        reader=self.reader();path=self.retained/'record.json';path.unlink();outside=self.root/'outside.json';outside.write_bytes(b'{"synthetic":true}\n');path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'Symlink'):reader.read('a'*40,'retained/record.json')
    def test_wrong_archive_hash(self):
        self.data['archives']['source']['archive_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Archive hash/size mismatch'):self.reader()
    def test_missing_mapping_rejected(self):
        self.data['files'].pop()
        with self.assertRaisesRegex(ValueError,'Missing mapped inputs'):self.reader()
    def test_incomplete_access_rejected(self):
        with self.assertRaisesRegex(ValueError,'Some mapped inputs'):self.reader().finish()
    def test_original_changed_after_access(self):
        reader=self.reader()
        for row in self.inv:reader.read(row['commit'],row['path'])
        (self.retained/'record.json').write_bytes(b'changed after access')
        with self.assertRaisesRegex(ValueError,'changed during replay'):reader.finish()

if __name__=='__main__':unittest.main(verbosity=2)
