import json
import tempfile
import unittest
from pathlib import Path
from autoresearch.llm import LLM
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import Choice, load_model

class RecordingLLM(LLM):
    name='recording'
    model='fixture'
    def __init__(self):
        super().__init__(); self.payloads=[]
    def embed(self,texts):
        return [[1., float(i % 2)] for i,_ in enumerate(texts)]
    def complete(self,prompt,system='',**kwargs):
        p=json.loads(prompt.split('INPUT_JSON:\n',1)[1]);self.payloads.append(p)
        if 'generation_style' in p:return json.dumps({'principles':['Prefer red over blue.','Prefer vivid colors.']})
        if 'voting_round' in p:return json.dumps({'votes':{str(i):'b' for i in range(len(p['principles']))}})
        if 'past_judgements' in p:return json.dumps({'persona':'Prefers red over blue.'})
        return json.dumps({'probabilities':[.2,.8],'rationale':'The red option is preferable.'})

def rows(n,prefix):
    return [Choice('subject',prefix+str(i),'blue','red','b',example_id=prefix+str(i),group_id=prefix+str(i)) for i in range(n)]

class FullHistoryTests(unittest.TestCase):
    def test_paper_paths_cover_history_and_validation_and_roundtrip(self):
        for method in ['m2','m3']:
            llm=RecordingLLM();model=create_method(method,llm,full_history=True,workers=2,max_candidates=2,num_search_candidates=2,max_bootstrapped_demos=4,max_calls=5000)
            model.fit(rows(57,'h'),rows(11,'v'))
            meta=model.artifacts().metadata
            self.assertEqual(set(meta['selected_history_ids']),{'h'+str(i) for i in range(57)})
            seen={p['context'] for p in llm.payloads if 'context' in p}
            self.assertTrue({'v'+str(i) for i in range(11)} <= seen)
            for p in llm.payloads:
                if 'generation_style' not in p and 'past_judgements' not in p:
                    self.assertNotIn('chosen',p);self.assertNotIn('reason',p)
            if method=='m2':
                self.assertEqual(len(meta['bootstrap_before']),57)
                self.assertEqual(len(meta['bootstrap_after']),57)
                self.assertTrue(model.artifacts().persona)
            else:
                self.assertEqual(len(meta['principle_proposals']),228)
                self.assertTrue(model.artifacts().principles)
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'model.json';model.save(path)
                restored=load_model(path,llm)
                self.assertEqual(restored.predict('new',['blue','red']).choice,'b')
                self.assertEqual(restored.artifacts(),model.artifacts())
                self.assertEqual(restored.prompt_version,model.prompt_version)
    def test_wrong_bootstrap_predictions_are_rejected(self):
        llm=RecordingLLM();m=create_method('m2',llm,full_history=True,workers=1,num_search_candidates=1,max_bootstrapped_demos=4)
        h=rows(4,'h');h[0]=Choice('subject','wrong','red','blue','a',example_id='wrong',group_id='wrong')
        m.fit(h,rows(3,'v'))
        trace=m.artifacts().metadata['bootstrap_before']
        self.assertFalse(next(x for x in trace if x['id']=='wrong')['accepted'])
        self.assertNotIn('wrong',[e['id'] for e in m.artifacts().exemplars if 'rationale' in e])
    def test_invalid_votes_fail_closed(self):
        class Bad(RecordingLLM):
            def complete(self,prompt,**kw):
                if 'voting_round' in prompt:return '{"votes":{"0":"bad"}}'
                return super().complete(prompt,**kw)
        m=create_method('m3',Bad(),full_history=True,workers=1,max_candidates=2)
        with self.assertRaises(ValueError):m.fit(rows(2,'h'),rows(2,'v'))
    def test_raw_history_all_236(self):
        llm=RecordingLLM();m=create_method('m1',llm,full_history=True,k='all');m.fit(rows(236,'h'),rows(70,'v'));m.predict('new',['blue','red'])
        past=llm.payloads[-1]['past_choices'];self.assertEqual(len(past),236)
        self.assertNotIn('group_id',past[0])
