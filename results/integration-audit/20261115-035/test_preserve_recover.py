"""Synthetic preservation and recovery controls; no released inputs are opened."""
import copy
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('preserve_recover',Path(__file__).with_name('preserve_recover.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.private=self.root/'private';self.private.mkdir(mode=0o700)
        self.raw=self.root/'synthetic.json';self.raw.write_text('{"synthetic":true}')
        row={'path':'/synthetic/logical.json','read_path':str(self.raw),'sha256':m.sha(self.raw.read_bytes()),'bytes':len(self.raw.read_bytes()),'roles':['synthetic']}
        self.inv={'entry_points':{'synthetic':{'path':row['path'],'sha256':row['sha256']}},'files':[row],'input_set_sha256':m.sha(m.canonical({row['path']:row['sha256']}))}
        self.ip=self.root/'inventory.json';self.ip.write_text(json.dumps(self.inv));self.reader=self.root/'reader.py';self.reader.write_text('# synthetic\n');self.source=self.root/'source.tar';self.source.write_bytes(b'synthetic source')
        self.args=types.SimpleNamespace(archive=str(self.private/'synthetic.tar.gz'),receipt=str(self.root/'receipt.json'),inventory=str(self.ip),inventory_sha256=m.sha(self.ip.read_bytes()),reader=str(self.reader),reader_sha256=m.sha(self.reader.read_bytes()),source_archive=str(self.source),source_sha256=m.sha(self.source.read_bytes()))
    def tearDown(self):self.tmp.cleanup()
    def extraction(self):return types.SimpleNamespace(archive=self.args.archive,receipt=self.args.receipt,receipt_sha256=m.sha(Path(self.args.receipt).read_bytes()),out=str(self.root/'restored'))
    def test_roundtrip_without_originals(self):
        m.preserve(self.args);self.raw.unlink();a=self.extraction();m.extract(a);restored=json.loads((Path(a.out)/'input-inventory.json').read_text())
        self.assertEqual(restored['entry_points'],self.inv['entry_points']);self.assertEqual(restored['input_set_sha256'],self.inv['input_set_sha256']);self.assertEqual(Path(restored['files'][0]['read_path']).read_bytes(),b'{"synthetic":true}')
        self.assertEqual(Path(self.args.archive).stat().st_mode&0o777,0o600)
    def test_initial_input_mutation_stops_before_archive(self):
        self.raw.write_text('{"synthetic":false}')
        with self.assertRaisesRegex(ValueError,'Pinned input mismatch'):m.preserve(self.args)
        self.assertFalse(Path(self.args.archive).exists())
    def test_during_read_mutation_stops_before_archive(self):
        original=m.pinned;count=[0]
        def changed(path,*args):
            data=original(path,*args)
            if str(path)==str(self.raw):
                count[0]+=1
                if count[0]==1:self.raw.write_text('{"synthetic":false}')
            return data
        with patch.object(m,'pinned',changed):
            with self.assertRaisesRegex(ValueError,'Pinned input mismatch'):m.preserve(self.args)
        self.assertFalse(Path(self.args.archive).exists())
    def test_existing_archive_never_overwritten(self):
        target=Path(self.args.archive);target.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):m.preserve(self.args)
        self.assertEqual(target.read_bytes(),b'keep')
    def test_existing_extraction_never_overwritten(self):
        m.preserve(self.args);a=self.extraction();Path(a.out).mkdir()
        with self.assertRaises(FileExistsError):m.extract(a)
    def test_corrupt_archive_rejected_before_output(self):
        m.preserve(self.args);a=self.extraction();Path(a.archive).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'Pinned input mismatch'):m.extract(a)
        self.assertFalse(Path(a.out).exists())
    def test_traversal_rejected_with_consistent_forged_pins(self):
        m.preserve(self.args);a=self.extraction();receipt=json.loads(Path(a.receipt).read_text());receipt['members'][0]['member']='../escape.json'
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w') as t:
            data=self.raw.read_bytes();info=tarfile.TarInfo('../escape.json');info.size=len(data);t.addfile(info,io.BytesIO(data))
        data=gzip.compress(raw.getvalue(),mtime=0);Path(a.archive).write_bytes(data);receipt['archive_sha256']=m.sha(data);receipt['archive_bytes']=len(data);Path(a.receipt).write_text(json.dumps(receipt));a.receipt_sha256=m.sha(Path(a.receipt).read_bytes())
        with self.assertRaisesRegex(ValueError,'Unsafe member'):m.extract(a)
        self.assertFalse(Path(a.out).exists());self.assertFalse((self.root/'escape.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
