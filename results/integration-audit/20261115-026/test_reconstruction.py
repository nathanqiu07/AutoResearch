"""Synthetic boundary checks for the independent phase2 reconstruction."""
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('audit26',Path(__file__).with_name('read_handoff.py'))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class ReconstructionTests(unittest.TestCase):
    def test_adjacent_permissions_stay_separate(self):
        doc={'document_id':'d','content':'abcDEF','permitted_spans':[{'start':0,'end':3},{'start':3,'end':6}]}
        self.assertEqual(audit.chunks_for([doc]),[{'document_id':'d','start':0,'end':3,'text':'abc'},
                                                {'document_id':'d','start':3,'end':6,'text':'DEF'}])

    def test_overlap_is_not_duplicated_or_joined(self):
        doc={'document_id':'d','content':'AAABBBCCC','permitted_spans':[{'start':0,'end':5},{'start':3,'end':9}]}
        self.assertEqual(audit.chunks_for([doc]),[{'document_id':'d','start':0,'end':5,'text':'AAABB'},
                                                {'document_id':'d','start':5,'end':9,'text':'BCCC'}])

    def test_explicit_empty_permissions_differ_from_absent(self):
        doc={'document_id':'d','content':'abc'}
        self.assertEqual(audit.chunks_for([dict(doc,permitted_spans=[])]),[])
        self.assertEqual(audit.chunks_for([doc]),[{'document_id':'d','start':0,'end':3,'text':'abc'}])
        self.assertNotEqual(audit.permission_hash([doc]),audit.permission_hash([dict(doc,permitted_spans=[])]))

    def test_rank_uses_cosine_before_source_order(self):
        chunks=[{'document_id':'a','start':0,'end':1,'text':'A'},{'document_id':'b','start':0,'end':1,'text':'B'}]
        self.assertEqual(audit.pack_ranked(chunks,[[1,0],[0,1],[4,0]],512)['passages'],list(reversed(chunks)))

    def test_unicode_prefix_respects_rendered_byte_cap(self):
        chunk={'document_id':'d','start':0,'end':20,'text':'é'*20}
        result=audit.pack_ranked([chunk],[[1],[1]],80)
        encoded=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        self.assertLessEqual(len(encoded(result)),80)
        passage=result['passages'][0]
        self.assertEqual(passage['text'],chunk['text'][:passage['end']])
        longer=dict(passage,text=passage['text']+'é',end=passage['end']+1)
        self.assertGreater(len(encoded({'passages':[longer]})),80)

if __name__=='__main__':unittest.main(verbosity=2)
