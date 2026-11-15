"""Offline span retest using exact synthetic fixture bytes preserved from audit017.

First run --phase old against the preserved017 source, then --phase new against
the released role05 source and supply --old-reference from the first run.
No provider backend is imported, no network is allowed, and outputs must be fresh.
"""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--phase', choices=['old', 'new'], required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--source-manifest', type=Path, required=True)
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--old-reference', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    root = args.source_root.resolve()
    pin = json.loads(args.source_manifest.read_text())
    hashes = {n: sha(root/n) for n in pin['files']}
    assert hashes == pin['files']
    fixture_hashes = {str(f.relative_to(args.fixtures)): sha(f) for f in args.fixtures.rglob('*') if f.is_file()}
    sys.path.insert(0, str(root))
    from autoresearch.taste.overnight import contracts as c, retrieval as r, baselines as b, consumer
    b.register_baselines()
    fixtures = [json.loads((args.fixtures/'synthetic-releases'/f'synthetic-researcher-{x}.json').read_text()) for x in ['a','b']]
    routes = json.loads((args.fixtures/'synthetic-routes.json').read_text())
    first = fixtures[0]
    docs = first['sources']['documents']
    decision = {k: first['items'][0][k] for k in ['context', 'options']}
    cfg = copy.deepcopy(next(x['profile']['config'] for x in routes if x['method']=='lexical_retrieval'))
    cfg['code_sha'] = pin['source_commit']
    model = 'SYNTHETIC-embedding'

    def no_network(*a, **k):
        raise AssertionError('No network permitted')

    checks = []
    def check(name, value):
        checks.append({'name': name, 'status': 'verified' if value else 'failed'})

    def manifest_config(documents, **extra):
        value = dict(cfg, researcher_id=documents[0]['researcher_id'],
                     allowed_sources=c.source_manifest(documents),
                     allowed_source_manifest_hash=c.digest(c.source_manifest(documents)), **extra)
        return value

    class NoExtractor:
        label = 'synthetic-only'
        model = 'none'
        def complete(self, *a, **k):
            raise AssertionError('Baseline unexpectedly called an extractor')

    class CaptureConsumer:
        label = 'synthetic-only'
        model = 'recording'
        def __init__(self): self.calls = []
        def complete(self, prompt, system='', **settings):
            self.calls.append({'prompt': prompt, 'system': system, 'settings': settings})
            return '{"probabilities":[0.6,0.4],"rationale":"Synthetic span audit only"}'

    def infer(profile, item):
        transport = CaptureConsumer()
        pred_config = {'method_implementation_hash': profile.method_implementation_hash,
                       'renderer_implementation_hash': consumer.implementation_hash(),
                       'profile_prompt_version': profile.prompt_version,
                       'consumer_prompt_version': consumer.PROMPT_VERSION,
                       'settings': {'temperature': 0, 'max_tokens': 8192}}
        b.predict_baseline(profile, item['context'], item['options'], transport, pred_config)
        assert len(transport.calls)==1
        return json.loads(transport.calls[0]['prompt'].split('INPUT_JSON:\n',1)[1]), transport.calls[0]

    def source_checks(documents, passages, cap=None, profile=None):
        lookup={x['document_id']:x for x in documents}
        for part in passages:
            doc=lookup[part['document_id']]
            assert part['text'] == doc['content'][part['start']:part['end']]
            ranges=doc.get('permitted_spans',[{'start':0,'end':len(doc['content'])}])
            assert any(x['start']<=part['start']<part['end']<=x['end'] for x in ranges)
        if profile is not None:
            assert profile.token_count == len(c.render_content(profile.content).encode()) <= cap

    with patch.object(socket.socket,'connect',no_network),patch.object(socket,'create_connection',no_network),patch.object(socket,'getaddrinfo',no_network):
        bundle=r.make_embedding_bundle(docs,cfg,decision,model=model,
            vectors=[[1,0] for _ in range(len(r.chunk_documents(docs,cfg))+1)],usage={'mode':'offline_fixture','calls':0})
        reference={'source_commit':pin['source_commit'],'retrieval_sha256':r.implementation_hash(),
                   'policy_hashes':{x['method_id']:x['prompt_sha256'] for x in b.registration_metadata()},
                   'chunks':r.chunk_documents(docs,cfg), 'bundle':bundle,
                   'cache_key':r.retrieval_cache_key(docs,cfg,decision,{'model':'SYNTHETIC-consumer'}),
                   'config':cfg,'fixture_hashes':fixture_hashes}
        if args.phase=='old':
            dump(args.out/'reference.json',reference)
            assert hashes=={n:sha(root/n) for n in pin['files']}
            print(json.dumps({'phase':'old','source_hashes_verified':len(hashes),'outside_marker_chunks':sum('OUTSIDE_PERMITTED_SENTINEL' in x['text'] for x in reference['chunks'])}))
            return
        old=json.loads(args.old_reference.read_text())
        check('exact017 fixture files retained',old['fixture_hashes']==fixture_hashes)
        check('old helper includes restricted sentinel and new helper excludes it',
              any('OUTSIDE_PERMITTED_SENTINEL' in x['text'] for x in old['chunks']) and
              not any('OUTSIDE_PERMITTED_SENTINEL' in x['text'] for x in reference['chunks']))
        results=[]
        for release in fixtures:
            researcher=release['researcher_id'];documents=release['sources']['documents'];items=release['items']
            for method in ['no_profile','name_only','raw_evidence','lexical_retrieval']:
                relevant=[x for x in routes if x['researcher']==researcher and x['method']==method]
                for route in relevant:
                    config=copy.deepcopy(route['profile']['config']);config['code_sha']=pin['source_commit']
                    profile=c.build_profile(documents,config,NoExtractor())
                    assert profile.status=='complete'
                    if method in ['raw_evidence','lexical_retrieval']:
                        source_checks(documents,profile.content['passages'],config['personalization_cap'],profile)
                    for item in route['items']:
                        payload,request=infer(profile,item)
                        old_personalization=c.render_content(route['profile']['content'])
                        results.append({'researcher':researcher,'method':method,'item_id':item['item_id'],
                            'old_outside_marker':'OUTSIDE_PERMITTED_SENTINEL' in old_personalization,
                            'new_outside_marker':'OUTSIDE_PERMITTED_SENTINEL' in payload['personalization'],
                            'unchanged_personalization':old_personalization==payload['personalization'],
                            'profile':profile.to_dict(),'captured_request':request})
        check('all16 restricted raw lexical predictions exclude old sentinel',
              len([x for x in results if x['method'] in ['raw_evidence','lexical_retrieval']])==16 and
              all(x['old_outside_marker'] and not x['new_outside_marker'] for x in results if x['method'] in ['raw_evidence','lexical_retrieval']))
        check('all16 no-profile name-only control personalizations unchanged',
              len([x for x in results if x['method'] in ['no_profile','name_only']])==16 and
              all(x['unchanged_personalization'] for x in results if x['method'] in ['no_profile','name_only']))
        controls=[]
        for variant in ['full-document','default-no-span']:
            release=json.loads((args.fixtures/'synthetic-releases'/f'{variant}.json').read_text())
            documents=release['sources']['documents']
            for method in ['no_profile','name_only','raw_evidence','lexical_retrieval']:
                route=next(x for x in routes if x['researcher']==release['researcher_id'] and x['method']==method)
                config=copy.deepcopy(route['profile']['config']);config['code_sha']=pin['source_commit']
                profile=c.build_profile(documents,config,NoExtractor());assert profile.status=='complete'
                payload,_=infer(profile,release['items'][0])
                if method in ['raw_evidence','lexical_retrieval']:
                    source_checks(documents,profile.content['passages'],config['personalization_cap'],profile)
                controls.append({'variant':variant,'method':method,'status':profile.status,
                                 'sentinel_in_personalization':'OUTSIDE_PERMITTED_SENTINEL' in payload['personalization'],
                                 'content_equals_old_restricted':profile.content==route['profile']['content']})
        check('full default controls restore old full-document conditioning',all(x['content_equals_old_restricted'] for x in controls))

        # Independent malformed/empty-span and Unicode/grid/overlap controls.
        invalid=[]
        malformed=[None,'all',{},[None],[{}],[{'start':True,'end':3}],[{'start':0,'end':False}],
                   [{'start':0.0,'end':3}],[{'start':-1,'end':3}],[{'start':3,'end':3}],
                   [{'start':4,'end':2}],[{'start':0,'end':100000}]]
        for spans in malformed:
            documents=copy.deepcopy(docs);documents[0]['permitted_spans']=spans
            try:r.chunk_documents(documents,cfg)
            except ValueError as exc:invalid.append({'case':spans,'status':'rejected','error':str(exc)})
            else:invalid.append({'case':spans,'status':'accepted'})
        check('12 malformed span cases reject rather than default full document',len(invalid)==12 and all(x['status']=='rejected' for x in invalid))
        empty_docs=copy.deepcopy(docs)
        for d in empty_docs:d['permitted_spans']=[]
        empty_profiles=[c.build_profile(empty_docs,dict(cfg,method_id=m),NoExtractor()) for m in ['raw_evidence','lexical_retrieval']]
        check('explicit empty spans yield no chunks and unavailable profiles',r.chunk_documents(empty_docs,cfg)==[] and all(x.status=='unavailable' and x.error_code=='no_approved_passage_fits' for x in empty_profiles))
        geometry=[]
        text=' αβ🙂a  Z中 q '
        ranges=[(a,z) for a in range(len(text)) for z in range(a+1,len(text)+1)]
        for left,right in itertools.combinations(ranges,2):
            documents=[{'document_id':'SYNTHETIC-geometry','researcher_id':cfg['researcher_id'],'content':text,
                        'content_sha256':c.sha256_text(text),'permitted_spans':[{'start':right[0],'end':right[1]}, {'start':left[0],'end':left[1]}]}]
            for width in [1,3,7,30]:
                gc=manifest_config(documents,chunk_chars=width)
                chunks=r.chunk_documents(documents,gc);source_checks(documents,chunks)
                positions=[i for x in chunks for i in range(x['start'],x['end'])]
                assert len(positions)==len(set(positions))
                assert all(x['start']//width==(x['end']-1)//width for x in chunks)
                geometry.append({'ranges':[left,right],'width':width,'chunks':chunks})
        check('Unicode overlap gap and grid controls retain exact individual ranges without duplicate offsets',len(geometry)>0)
        cap_rows=[]
        for cap in [0,1,13,48,64,96,128,256,512,2048]:
            for method in ['raw_evidence','lexical_retrieval']:
                profile=c.build_profile(docs,dict(cfg,method_id=method,personalization_cap=cap),NoExtractor())
                if profile.status=='complete':source_checks(docs,profile.content['passages'],cap,profile)
                cap_rows.append({'cap':cap,'method':method,'status':profile.status,'error':profile.error_code,'bytes':profile.token_count})
        check('20 cap controls keep complete profiles within declared byte bound',all(x['status']!='complete' or x['bytes']<=x['cap'] for x in cap_rows))

        semantic_config=dict(cfg,method_id='semantic_retrieval',embedding_model=model,embedding_dimensions=2,
                             embedding_bundle=bundle,embedding_bundle_sha256=bundle['bundle_sha256'])
        semantic=c.build_profile(docs,semantic_config,NoExtractor())
        source_checks(docs,semantic.content['passages'],cfg['personalization_cap'],semantic)
        check('new semantic bundle and embedding inputs contain only permitted text with zero extraction calls',
              semantic.status=='complete' and semantic.fit_usage['calls']==0 and
              all('OUTSIDE_PERMITTED_SENTINEL' not in s for s in r.embedding_inputs(docs,cfg,decision)[1:]))
        old_bundle=old['bundle'];old_sha=old_bundle['bundle_sha256']
        rejected=c.build_profile(docs,dict(semantic_config,embedding_bundle=old_bundle,embedding_bundle_sha256=old_sha),NoExtractor())
        check('old017 vector bundle refuses silent reuse under new helper',rejected.status=='unavailable' and rejected.error_code=='invalid_embedding_bundle' and old_bundle['bundle_sha256']==old_sha)
        # Same trimmed chunk text, distinct permission ranges: cache/request must differ.
        same=[{'document_id':'SYNTHETIC-whitespace','researcher_id':cfg['researcher_id'],'content':' allowed ',
               'content_sha256':c.sha256_text(' allowed ')}]
        sc=manifest_config(same);identity={'model':'SYNTHETIC-consumer'}
        before_key=r.retrieval_cache_key(same,sc,decision,identity);before_chunks=r.chunk_documents(same,sc)
        same_bundle=r.make_embedding_bundle(same,sc,decision,model=model,vectors=[[1,0],[1,0]],usage={'mode':'offline_fixture'})
        same[0]['permitted_spans']=[{'start':1,'end':8}]
        try:r.rank_semantic(same,dict(sc,embedding_model=model,embedding_dimensions=2,embedding_bundle_sha256=same_bundle['bundle_sha256']),decision,same_bundle)
        except ValueError:permission_rejected=True
        else:permission_rejected=False
        check('permission-only change invalidates cache and semantic bundle even for identical chunks',
              before_chunks==r.chunk_documents(same,sc) and before_key!=r.retrieval_cache_key(same,sc,decision,identity) and permission_rejected)
        check('all seven baseline policy hashes change',set(old['policy_hashes'])==set(reference['policy_hashes']) and all(old['policy_hashes'][m]!=reference['policy_hashes'][m] for m in old['policy_hashes']))
        normalized_old_config=dict(cfg);normalized_old_config['code_sha']=old['config']['code_sha']
        check('retrieval cache key changes even with original config held fixed',old['cache_key']!=r.retrieval_cache_key(docs,normalized_old_config,decision,{'model':'SYNTHETIC-consumer'}))
        check('prior evidence new source and supplied old reference unchanged',hashes=={n:sha(root/n) for n in pin['files']} and fixture_hashes=={str(f.relative_to(args.fixtures)):sha(f) for f in args.fixtures.rglob('*') if f.is_file()})
        dump(args.out/'restricted-predictions.json',results)
        dump(args.out/'full-default-controls.json',controls)
        dump(args.out/'invalid-empty-controls.json',{'malformed':invalid,'empty_profiles':[x.to_dict() for x in empty_profiles]})
        dump(args.out/'geometry-summary.json',{'cases':len(geometry),'text':text,'widths':[1,3,7,30],'all_exact_offsets':True,'all_individually_permitted':True,'no_duplicate_offsets':True,'all_within_grid':True})
        dump(args.out/'cap-controls.json',cap_rows)
        dump(args.out/'identity-controls.json',{'old':old,'new':reference,'old_bundle_build_status':rejected.status,'old_bundle_build_error':rejected.error_code,'semantic_profile':semantic.to_dict(),'permission_only_change_rejected':permission_rejected})
    report={'source_commit':pin['source_commit'],'implementation_commit':pin.get('implementation_commit'),
            'source_files_verified':len(hashes),'retrieval_sha256':r.implementation_hash(),'old_source_commit':old['source_commit'],
            'checks':checks,'verified':sum(x['status']=='verified' for x in checks),'failed':sum(x['status']=='failed' for x in checks),
            'restricted_predictions':len(results),'full_default_predictions':len(controls),'geometry_cases':len(geometry),'cap_controls':len(cap_rows),
            'actual_model_calls':0,'fixture_hashes':fixture_hashes,'reproducer_sha256':sha(__file__),
            'limits':['Exact017 synthetic documents, choices, selected configs and old profile content; new code_sha and current method/renderer pins used for new artifacts.',
                      'This role05 snapshot has no integrated runner or P1 implementation; full pilot route and P1 were not rerun.',
                      'Default-no-span is a schema fallback, not an eligible evaluator-approved release.',
                      'No actual-v2 data read; owner-reported6 whitespace characters and audit01916 repeated-profile characters use different aggregation units.',
                      'No active runtime mutation or old artifact repair; new code requires new policy/request/cache identities and bundles.']}
    dump(args.out/'report.json',report)
    print(json.dumps({k:report[k] for k in ['verified','failed','restricted_predictions','full_default_predictions','geometry_cases','actual_model_calls']}))
    return bool(report['failed'])


if __name__=='__main__':
    raise SystemExit(main())
