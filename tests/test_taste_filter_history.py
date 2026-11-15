import importlib.util, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('filter_history',Path(__file__).parents[1]/'scripts/taste_filter_history.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class FilterTest(unittest.TestCase):
    def setUp(self):
        self.c=dict(example_id='id',context='context',a_text='AAA',b_text='BBB',chosen='a',reason='SECRET_LABEL_REASON',user_id='SECRET_IDENTITY')
    def records(self,n):
        r={}
        for i in range(10):
            a=i<n
            r[f'id/vote/{i}']={'parsed':{'choice':(2 if a else 1) if i>=5 else (1 if a else 2)}}
        r['id/quality/0']={'parsed':dict(category='valid_tradeoff',reason='tradeoff',case_for_1='one',case_for_2='two')}
        return r
    def test_threshold_and_order(self):
        self.assertEqual(m.decide(self.c,self.records(8))['status'],'kept')
        self.assertEqual(m.decide(self.c,self.records(9))['reasons'],['generic_agreement'])
    def test_missing_pending(self):
        r=self.records(8); del r['id/vote/3']; self.assertEqual(m.decide(self.c,r)['status'],'pending')
    def test_defect(self):
        r=self.records(5); r['id/quality/0']['parsed']['category']='dominated'
        self.assertEqual(m.decide(self.c,r)['reasons'],['dominated'])
    def test_blindness(self):
        for kind in ['vote','quality']:
            p=m.prompt(self.c,kind,0)
            self.assertNotIn('SECRET',p); self.assertNotIn('chosen',p)
        self.assertIn('Option 1: BBB',m.prompt(self.c,'vote',5))
    def test_prose_json_recovery(self):
        self.assertEqual(m.parse('Explanation.\n{"choice": 2}'),{'choice':2})
        with self.assertRaises(ValueError): m.parse('{"choice":1} {"choice":2}')
    def test_invalid_vote_pending(self):
        r=self.records(8); r['id/vote/0']['parsed']['choice']=True
        self.assertEqual(m.decide(self.c,r)['status'],'pending')
    def test_reservation_resume(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); r=m.Runner(p,'',0); r.call(self.c,'vote',0)
            self.assertFalse(r.reservations)
            r.append(dict(event='reserve',key='id/vote/0',bound_usd=.1))
            r=m.Runner(p,'',1); self.assertEqual(r.spent,.1)
            r.call(self.c,'vote',0); self.assertFalse(r.records)
if __name__=='__main__': unittest.main()
