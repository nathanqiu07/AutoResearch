import copy
import importlib.util
import json
import unittest
from autoresearch.taste.overnight import contracts

TEXT = 'When evidence is unclear, I prefer a small controlled test. If the effect disappears, I abandon the direction.'
DOCS = [{'document_id':'fit-synthetic','researcher_id':'synthetic','content':TEXT,
         'content_sha256':contracts.sha256_text(TEXT)}]


def claim(text='Prefer a small controlled test.', kind='preference', evidence='explicit'):
    return {'text':text,'kind':kind,'evidence_status':evidence,
            'sources':[{'document_id':'fit-synthetic','start':0,'end':len(TEXT),'quote':TEXT}]}


def principle(identity='p1'):
    return {'id':identity,'claim':claim(),'context':None,'date':None,
            'uncertainty':'not_quantified','exceptions':[],'conflicts_with':[]}


def rule(identity='r1'):
    return {'id':identity,'when':claim('Evidence is unclear.','source_report'),'prefer':claim(),
            'over':None,'unless':[],'date':None,'uncertainty':'not_quantified','conflicts_with':[]}


class Extractor:
    label='offline-principles-fixture'
    model='fixture-v1'
    def __init__(self,response):self.response,self.calls=response,[]
    def complete(self,prompt,**kwargs):
        self.calls.append((prompt,kwargs))
        if isinstance(self.response,Exception):raise self.response
        return self.response if isinstance(self.response,str) else json.dumps(self.response)


class PrincipleTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('autoresearch.taste.overnight.profiles_principles'),
                             'P4-P6 builders are not implemented')
        from autoresearch.taste.overnight import profiles_principles
        self.m=profiles_principles
        self.config={'method_id':'P4','researcher_id':'synthetic','evidence_policy':'explicit-only',
                     'personalization_cap':8192,'replicate_id':0,'code_sha':'b'*40,
                     'extractor_settings':{'temperature':0.0,'max_tokens':2048},
                     'allowed_sources':contracts.source_manifest(DOCS),
                     'allowed_source_manifest_hash':contracts.digest(contracts.source_manifest(DOCS))}
    def build(self,response=None,method='P4',**changes):
        response={'principles':[principle()],'rejected':[]} if response is None else response
        e=Extractor(response);out=getattr(self.m,'build_'+method.lower())(copy.deepcopy(DOCS),dict(self.config,method_id=method,**changes),e)
        return out,e
    def test_unknown_extractor_settings_are_rejected_before_call(self):
        for method in ('P4', 'P5', 'P6'):
            for extra in ({'top_p':0.1}, {'top_p':0.9}, {'reasoning':'high'}, {'seed':1}):
                with self.subTest(method=method,extra=extra):
                    out,backend=self.build(method=method,extractor_settings=dict(self.config['extractor_settings'],**extra))
                    self.assertEqual(out['status'],'invalid')
                    self.assertEqual(backend.calls,[])
                    self.assertEqual(out['fit_usage']['attempted_calls'],0)

    def test_omitted_supported_settings_have_pinned_effective_defaults(self):
        for supplied,expected in [({},{'temperature':0.0,'max_tokens':2048}),
                                  ({'temperature':0.5},{'temperature':0.5,'max_tokens':2048}),
                                  ({'max_tokens':100},{'temperature':0.0,'max_tokens':100})]:
            with self.subTest(supplied=supplied):
                out,backend=self.build(extractor_settings=supplied)
                self.assertEqual(out['status'],'complete')
                self.assertEqual(out['fit_usage']['effective_extractor_settings'],expected)
                self.assertEqual({k:backend.calls[0][1][k] for k in expected},expected)
                self.assertEqual(self.m.prompt_spec('P4')['extractor_settings_defaults'],
                                 {'temperature':0.0,'max_tokens':2048})

    def test_p4_preserves_atomic_evidence_context_and_exceptions(self):
        p=principle();p['context']=claim('Evidence is unclear.','source_report');p['exceptions']=[claim('Abandon when the effect disappears.')]
        out,_=self.build({'principles':[p],'rejected':[]})
        self.assertEqual(out['status'],'complete');self.assertEqual(out['content']['principles'],[p])
    def test_p5_requires_a_source_linked_condition(self):
        r=rule();out,_=self.build({'rules':[r],'rejected':[]},'P5');self.assertEqual(out['status'],'complete')
        for value in (None,{'text':'when useful'},dict(claim(),sources=[])):
            with self.subTest(value=value):
                r['when']=value;out,_=self.build({'rules':[r],'rejected':[]},'P5');self.assertEqual(out['status'],'invalid')
    def test_p5_counterconditions_and_alternatives_are_not_invented(self):
        r=rule();r['unless']=[dict(claim(),sources=[{'document_id':'missing','start':0,'end':3,'quote':'bad'}])]
        out,_=self.build({'rules':[r],'rejected':[]},'P5');self.assertEqual(out['status'],'invalid')
        r=rule();r['over']=None;out,_=self.build({'rules':[r],'rejected':[]},'P5');self.assertIsNone(out['content']['rules'][0]['over'])
    def test_hierarchy_uses_exact_existing_decision_types(self):
        from autoresearch.research.decisions import POINTS
        self.assertEqual(tuple(self.m.DECISION_TYPES),POINTS)
        groups={key:[] for key in self.m.HIERARCHY_KEYS};groups[self.m.HIERARCHY_KEYS[0]]=[principle()]
        out,_=self.build({'hierarchy':groups,'rejected':[]},'P6');self.assertEqual(out['status'],'complete')
        groups['D7_new'] = [];out,_=self.build({'hierarchy':groups,'rejected':[]},'P6');self.assertEqual(out['status'],'invalid')
    def test_conflicting_principles_are_preserved_not_resolved(self):
        a,b=principle('a'),principle('b');a['conflicts_with']=['b'];b['conflicts_with']=['a']
        b['claim']=claim('Abandon the direction when effects disappear.')
        response={'principles':[a,b],'rejected':[]};out,_=self.build(response)
        self.assertEqual(out['status'],'complete');self.assertEqual(out['content'],response)
    def test_unknown_conflict_references_and_duplicate_ids_are_invalid(self):
        a=principle();a['conflicts_with']=['absent'];out,_=self.build({'principles':[a],'rejected':[]});self.assertEqual(out['status'],'invalid')
        out,_=self.build({'principles':[principle(),principle()],'rejected':[]});self.assertEqual(out['status'],'invalid')
    def test_rejected_candidates_retain_original_and_reason(self):
        response={'principles':[principle()],'rejected':[{'candidate':principle('p2'),'reason':'redundant formulation'}]}
        out,_=self.build(response);self.assertEqual(out['status'],'complete');self.assertEqual(out['content'],response)
        response['rejected'][0]['reason']='';out,_=self.build(response);self.assertEqual(out['status'],'invalid')
    def test_explicit_policy_rejects_inferred_condition_or_exception(self):
        p=principle();p['exceptions']=[claim(evidence='inferred')]
        response={'principles':[p],'rejected':[]};out,_=self.build(response);self.assertEqual(out['status'],'invalid')
        out,_=self.build(response,evidence_policy='marked-inference');self.assertEqual(out['status'],'complete')
    def test_source_link_failures_are_invalid(self):
        for key,value in [('document_id','unknown'),('start',True),('end',9999),('quote','invented')]:
            p=principle();p['claim']['sources'][0][key]=value
            with self.subTest(key=key):
                out,_=self.build({'principles':[p],'rejected':[]});self.assertEqual(out['status'],'invalid')
    def test_numeric_reliability_weights_and_verified_fact_labels_are_rejected(self):
        for changes in ({'utility_weight':1.0},{'uncertainty':0.99}):
            p=principle();p.update(changes);out,_=self.build({'principles':[p],'rejected':[]});self.assertEqual(out['status'],'invalid')
        p=principle();p['claim']['kind']='verified_fact';out,_=self.build({'principles':[p],'rejected':[]});self.assertEqual(out['status'],'invalid')
    def test_unsupported_date_is_not_silently_inferred(self):
        p=principle();p['date']='2027-01-01';out,_=self.build({'principles':[p],'rejected':[]});self.assertEqual(out['status'],'invalid')
    def test_empty_outputs_stay_empty(self):
        for method,response in [('P4',{'principles':[],'rejected':[]}),('P5',{'rules':[],'rejected':[]}),('P6',{'hierarchy':{k:[] for k in self.m.HIERARCHY_KEYS},'rejected':[]})]:
            out,_=self.build(response,method);self.assertEqual(out['status'],'empty')
    def test_target_conditioning_and_invalid_inputs_never_call_backend(self):
        for changes in ({'context':'hidden'},{'options':['a','b']},{'evidence_policy':'anything'},{'extractor_settings':{'temperature':10**1000}}):
            with self.subTest(changes=changes):
                out,e=self.build(**changes);self.assertEqual(out['status'],'invalid');self.assertEqual(e.calls,[])
    def test_permitted_segments_and_metadata_do_not_leak(self):
        docs=copy.deepcopy(DOCS);docs[0]['content']+=' EXCLUDED_SENTINEL';docs[0]['content_sha256']=contracts.sha256_text(docs[0]['content']);docs[0]['permitted_spans']=[{'start':0,'end':len(TEXT),'text':TEXT,'speaker':'synthetic'}];docs[0]['author']='METADATA_SENTINEL'
        config=dict(self.config,allowed_sources=contracts.source_manifest(docs),allowed_source_manifest_hash=contracts.digest(contracts.source_manifest(docs)))
        e=Extractor({'principles':[principle()],'rejected':[]});out=self.m.build_p4(docs,config,e)
        self.assertEqual(out['status'],'complete');self.assertNotIn('EXCLUDED_SENTINEL',e.calls[0][0]);self.assertNotIn('METADATA_SENTINEL',e.calls[0][0])
    def test_no_retry_after_failure_and_malformed_response_visible(self):
        out,e=self.build(RuntimeError('fixture'));self.assertEqual(out['status'],'unavailable');self.assertEqual(len(e.calls),1)
        for raw in ('bad json','{"principles":[],"principles":[],"rejected":[]}'):
            out,e=self.build(raw);self.assertEqual(out['status'],'invalid');self.assertEqual(len(e.calls),1)
    def test_cap_failure_preserves_full_content_and_registration_pins_mapping(self):
        self.m.register_principle_builders();e=Extractor({'principles':[principle()],'rejected':[]})
        artifact=contracts.build_profile(DOCS,dict(self.config,personalization_cap=1),e)
        self.assertEqual(artifact.status,'invalid');self.assertEqual(artifact.error_code,'personalization_cap_exceeded')
        self.assertEqual(artifact.content,{'principles':[principle()],'rejected':[]})
        entries=self.m.registration_metadata();self.assertEqual({e['method_id'] for e in entries},{'P4','P5','P6'})
        self.assertEqual(len(self.m.prompt_spec('P6')['decision_source_sha256']),64)

if __name__=='__main__':unittest.main()
