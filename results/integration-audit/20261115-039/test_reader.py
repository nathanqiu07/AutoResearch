"""Synthetic controls only; imports the audit reader without calling main."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('audit039',Path(__file__).with_name('reproduce.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class SyntheticBoundaryTests(unittest.TestCase):
    def test_probe_mean_uses_only_usable_json(self):
        replies=['{"p":0.2}','non-JSON answer','{"p":0.3}','{"p":0.4','{"p":0.7}']
        values=[]
        for text in replies:
            parsed=m.extract_recorded_json(text)
            value=m.recorded_probability(parsed.get('p')) if isinstance(parsed,dict) else None
            if value is not None:values.append(value)
        self.assertEqual(len(values),3)
        self.assertAlmostEqual(sum(values)/len(values),0.4)
        self.assertNotAlmostEqual(sum(values)/len(replies),0.4)

    def test_exact_quote_rejects_literal_escape_and_keeps_pointer(self):
        payload={'evidence':[{'source':'transcript','quote':'first\nsecond'},
                             {'source':'transcript','quote':'first\\nsecond'}]}
        result=m.quote_records(payload,{'transcript':'prefix first\nsecond suffix'})
        self.assertEqual([r['exact_substring'] for r in result],[True,False])
        self.assertEqual(result[1]['pointer'],'/evidence/1')
        self.assertNotIn('quote',result[0])

    def test_clipping_exact_boundary_and_head_tail(self):
        unchanged='x'*24000
        self.assertEqual(m.clipped(unchanged),unchanged)
        source='a'*12000+'middle'+'z'*12000
        self.assertEqual(m.clipped(source),'a'*12000+'\n\n[... 6 characters cut ...]\n\n'+'z'*12000)
        self.assertNotIn('middle',m.clipped(source))

    def test_native_reasoning_does_not_enter_visible_transcript(self):
        messages=[{'role':'assistant','content':[{'type':'reasoning','reasoning':'synthetic thought'},
                  {'type':'text','text':'visible result'}],
                  'tool_calls':[{'id':'synthetic-id','function':'read_file','arguments':{'path':'synthetic.txt'}}]}]
        transcript,thought=m.render_native(messages)
        self.assertEqual(thought,'synthetic thought')
        self.assertNotIn(thought,transcript)
        self.assertIn('[tool call synthetic-id] read_file(',transcript)

    def test_judge_response_excludes_reasoning_output(self):
        call={'response':{'output':[{'type':'reasoning','summary':'private synthetic reasoning'},
              {'type':'message','content':[{'type':'output_text','text':'{"synthetic":true}'}]}]}}
        self.assertEqual(m.response_text(call),'{"synthetic":true}')

    def test_target_path_normalization_and_traversal(self):
        self.assertEqual(m.norm_path('report.md'),'/home/user/report.md')
        self.assertEqual(m.norm_path('~/report.md'),'/home/user/report.md')
        with self.assertRaises(AssertionError):m.norm_path('../report.md')

if __name__=='__main__':unittest.main(verbosity=2)
