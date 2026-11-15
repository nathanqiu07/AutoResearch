"""Synthetic guard controls only; no original study inputs are opened."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('synthetic_audit033_helpers', ROOT/'reader033_helpers.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class ReaderGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-audit37-')
        self.root = Path(self.temp.name)
        self.raw = b'{"synthetic":true}\n'
        self.path = self.root/'input.json'
        self.path.write_bytes(self.raw)
        self.pin = hashlib.sha256(self.raw).hexdigest()
        self.ref = {'path':'/recorded/input.json','sha256':self.pin}
        self.args = SimpleNamespace(data_root=self.root, recorded_data_root='/recorded', archive_root=None, preservation=None)

    def tearDown(self):
        self.temp.cleanup()

    def test_original_and_archive_relocation(self):
        self.assertEqual(h.Inputs(self.args).read(self.ref), {'synthetic':True})
        receipt = self.root/'receipt.json'
        receipt.write_text(json.dumps({'files':[{'kind':'external','path':self.ref['path'],'sha256':self.pin,'archive_member':'input.json'}]}))
        args = SimpleNamespace(archive_root=self.root,preservation=receipt)
        reader = h.Inputs(args)
        self.assertEqual(reader.read(self.ref), {'synthetic':True})
        reader.recheck()

    def test_wrong_raw_hash_rejected(self):
        with self.assertRaises(AssertionError):
            h.Inputs(self.args).read(dict(self.ref,sha256='0'*64))

    def test_conflicting_cached_pin_rejected(self):
        reader = h.Inputs(self.args)
        reader.read(self.ref)
        with self.assertRaises(AssertionError):
            reader.read(dict(self.ref,sha256='0'*64))

    def test_traversal_and_hashless_reference_rejected(self):
        for ref in ({'path':'/recorded/../input.json','sha256':self.pin},{'path':'/recorded/input.json'}):
            with self.assertRaises(AssertionError):
                h.Inputs(self.args).read(ref)

    def test_original_changed_after_read_rejected(self):
        reader = h.Inputs(self.args)
        reader.read(self.ref)
        self.path.write_text('{"synthetic":"changed"}')
        with self.assertRaises(AssertionError):
            reader.recheck()

    def test_missing_pinned_file_has_no_fallback(self):
        with self.assertRaises(FileNotFoundError):
            h.Inputs(self.args).read(dict(self.ref,path='/recorded/missing.json'))

    def test_archive_escape_rejected(self):
        receipt = self.root/'receipt.json'
        receipt.write_text(json.dumps({'files':[{'kind':'external','path':self.ref['path'],'sha256':self.pin,'archive_member':'../input.json'}]}))
        with self.assertRaises(AssertionError):
            h.Inputs(SimpleNamespace(archive_root=self.root,preservation=receipt)).read(self.ref)

    def invoke(self, evidence, out):
        return subprocess.run([sys.executable,'-I','-B',str(ROOT/'read_full_sparse.py'),'--evidence-root',str(evidence),
             '--index','/recorded/input.json','--data-root',str(self.root),'--recorded-data-root','/recorded','--out',str(out)],capture_output=True,text=True)

    def test_actual_reader_rejects_unpinned_index(self):
        result = self.invoke(ROOT,self.root/'output')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Pinned input bytes differ: /recorded/input.json',result.stderr)
        self.assertFalse((self.root/'output/report.json').exists())

    def test_actual_reader_rejects_changed_helper_before_input(self):
        evidence = self.root/'evidence'
        evidence.mkdir()
        (evidence/'reader033_helpers.py').write_text('# synthetic changed helper\n')
        result = self.invoke(evidence,self.root/'output')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Pinned evidence changed: reader033_helpers.py',result.stderr)
        self.assertFalse((self.root/'output').exists())

    def test_actual_reader_refuses_existing_output(self):
        out = self.root/'output'
        out.mkdir()
        sentinel = out/'sentinel.txt'
        sentinel.write_text('synthetic unchanged')
        result = self.invoke(ROOT,out)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('FileExistsError',result.stderr)
        self.assertEqual(sentinel.read_text(),'synthetic unchanged')

    def test_distinct_item_metadata_does_not_split_identical_execution(self):
        spec = importlib.util.spec_from_file_location('synthetic_reader37', ROOT/'read_full_sparse.py')
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        binding = {k:hashlib.sha256(k.encode()).hexdigest() for k in ('prompt','system','settings','backend_identity','timeout')}
        rows = []
        for suffix in ('one','two'):
            row = {k:suffix for k in ('job_id','cell_id','method','cap','evidence_policy','item_id_sha256','item_sha256','option_order_id_sha256','started_trace_sha256','completed_trace_sha256','result_row_sha256')}
            row['verified_hashes'] = dict(binding)
            rows.append(row)
        groups = reader.group_request_equivalence(rows)
        self.assertEqual(len(groups),1)
        group = next(iter(groups.values()))
        self.assertEqual(group['group_size'],2)
        self.assertEqual(set(group['binding_hashes']),set(binding))
        self.assertEqual([r['item_id_sha256'] for r in group['recorded_executions']],['one','two'])
        rows[1]['verified_hashes']['prompt'] = 'different-execution'
        self.assertEqual(len(reader.group_request_equivalence(rows)),2)


if __name__ == '__main__':
    unittest.main()
