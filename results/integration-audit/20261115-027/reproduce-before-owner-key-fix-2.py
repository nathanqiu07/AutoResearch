"""Verify saved P1/memory conditioning with frozen code and hash-pinned inputs.

Metadata-only outputs. No backend calls, saved predictions, private labels,
credentials, ledger, or active runtime writes. Inputs can be relocated by changing
only paths in the explicit input inventory; every expected byte hash is checked.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
RUNTIME='f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
INDEX_SHA='d60849589fefe1016b4167ad6fba0a5fc1a4c09efb87ec0441202dcdb29f1a26'
PROPOSAL_SHA='3d081a032648cd977547f0be59874cfea51706d6d24eec2c8e189d8de0a478f6'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def dump(path,obj): Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--source-manifest',type=Path,required=True)
    ap.add_argument('--inputs',type=Path,required=True)
    ap.add_argument('--owner-reports',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    pins=json.loads(a.source_manifest.read_text());assert pins['source_commit']==RUNTIME
    source_before={name:sha((a.source_root/name).read_bytes()) for name in pins['files']}
    assert source_before==pins['files']
    explicit=json.loads(a.inputs.read_text())['inputs'];inventory={};checks=[]
    def check(name,value):
        checks.append({'name':name,'verified':bool(value)})
        if not value:raise AssertionError(name+' failed; no raw inputs emitted')
    def read(key,expected):
        entry=explicit[key];path=Path(entry['path']);raw=path.read_bytes()
        check('expected_bytes:'+key,sha(raw)==expected==entry['sha256'])
        inventory[key]={'path':str(path.resolve()),'sha256':sha(raw),'size_bytes':len(raw)}
        return json.loads(raw)
    def denied(*args,**kwargs): raise AssertionError('Model/network calls forbidden')
    class NoCalls:
        label='independent-offline-reuse-audit';model='no-model'
        complete=denied
    sys.path.insert(0,str(a.source_root.resolve()))
    with patch.object(socket.socket,'connect',denied),patch.object(socket,'create_connection',denied),patch.object(socket,'getaddrinfo',denied):
        from autoresearch.taste.overnight import contracts as c,consumer,baselines,runner
        baselines.register_baselines()
        index=read('index',INDEX_SHA);proposal=read('proposal',PROPOSAL_SHA)
        check('exact frozen runtime',index['runtime_sha']==RUNTIME)
        check('no calls authorized and no predictions labels in handoff',index['calls_authorized_by_this_handoff']==0 and index['raw_predictions_or_labels_included'] is False)
        check('proposal semantic hash',proposal['proposal_sha256']==c.digest({k:v for k,v in proposal.items() if k!='proposal_sha256'}))
        reports={}
        report_inventory={}
        for name,expected in [('012-reuse-ready.json','997e9a27deaef3413cf0dc5dc11e8d8555d1cedc18356f145080e5e52f949adf'),
                              ('012-frozen-p1-reuse-check.json','2a3a607cfb5b465b69d3a9abc8e866b67d310e90dcf5f74b31a9caeef5d0406e'),
                              ('012-memory-payload-alias-check.json','c65424a97b6ae0af66a9ce297bec6d4f9553ad26eb8ed99fb3dbca79afe6b561')]:
            raw=(a.owner_reports/name).read_bytes();check('owner_report_pin:'+name,sha(raw)==expected)
            reports[name]=json.loads(raw);report_inventory[name]={'sha256':expected,'size_bytes':len(raw)}
        owner_alias=reports['012-memory-payload-alias-check.json']
        owner_rows={(r['researcher_id'],r['cap'],r['item_id_sha256'],r['option_order_id_sha256']):r for r in owner_alias['records']}
        owner_identities={(r['researcher_id'],r['cap']):r for r in owner_alias['aliases']}
        owner_builds=reports['012-frozen-p1-reuse-check.json']['records']
        check('owner alias report independently bound to index proposal renderer',owner_alias['handoff_index_sha256']==INDEX_SHA and owner_alias['proposal_semantic_sha256']==proposal['proposal_sha256'] and owner_alias['consumer_implementation_sha256']==consumer.implementation_hash())
        parents=[];aliases=[];alias_rows=[];hybrids=[];execution_controls=[]
        for row in index['profiles']:
            researcher=row['researcher_id'];parent_body=read('profile:'+researcher,row['profile']['sha256'])
            parent=c.ProfileArtifact.from_dict(parent_body)
            batch=next(b for b in proposal['batches'] if b['researcher_id']==researcher)
            release=read('release:'+researcher,batch['release_sha256'])
            documents=release['sources']['documents'];items=release['items']
            check('parent identity sources and frozen selection:'+researcher,
                  parent.profile_id==row['profile_id'] and parent.code_sha==RUNTIME and parent.researcher_id==researcher and
                  parent.method_id=='P1' and parent.status=='complete' and parent.personalization_cap==512 and parent.replicate_id==0 and
                  parent.config['evidence_policy']=='explicit-only' and parent.documents_hash==c.digest(documents) and
                  parent.allowed_source_manifest_hash==release['sources']['allowed_source_manifest_hash']==batch['allowed_source_manifest_hash'])
            c.validate_documents(documents,parent.config)
            check('released items exact and label-free:'+researcher,
                  c.digest(items)==release['items_sha256']==batch['items_sha256'] and c.digest(release)==batch['release_semantic_sha256'] and
                  len(items)==14 and len({x['item_id'] for x in items})==14 and
                  all(set(x)=={'item_id','researcher_id','context','options','option_order_id'} and x['researcher_id']==researcher for x in items))
            check('parent renderer current:'+researcher,parent.renderer_implementation_hash==consumer.implementation_hash())
            parents.append({'researcher_id':researcher,'parent_job_id':row['job_id'],'parent_profile_id':parent.profile_id,
                            'parent_content_sha256':parent.content_sha256,'parent_fit_usage_sha256':c.digest(parent.fit_usage),
                            'parent_profile_file_sha256':row['profile']['sha256'],'documents_sha256':c.digest(documents),
                            'items_sha256':c.digest(items),'items':len(items),'rendered_bytes':parent.token_count})
            def identity(profile):
                return {'method_implementation_hash':profile.method_implementation_hash,
                        'renderer_implementation_hash':consumer.implementation_hash(),
                        'profile_prompt_version':profile.prompt_version,'consumer_prompt_version':consumer.PROMPT_VERSION}
            parent_id=identity(parent)
            for cap in [512,2048,8192]:
                cfg=copy.deepcopy(parent.config)
                cfg.update(method_id='memory_summary',personalization_cap=cap,summary_method_id='P1',
                           frozen_profile=parent.to_dict(),expected_profile_id=parent.profile_id,extractor_settings={})
                memory=c.build_profile(documents,cfg,NoCalls());memory_id=identity(memory)
                owner_identity=owner_identities[(researcher,cap)]
                check('independent required identities match owner evidence:'+researcher+':'+str(cap),
                      c.digest(parent_id)==owner_identity['parent_expected_identity_sha256'] and
                      c.digest(memory_id)==owner_identity['memory_expected_identity_sha256'])
                check('memory exact content parent usage and no calls:'+researcher+':'+str(cap),
                      memory.status=='complete' and memory.content==parent.content and memory.fit_usage['calls']==0 and
                      memory.fit_usage['original_fit_usage']==parent.fit_usage and memory.fit_usage['reused_profile_id']==parent.profile_id and
                      memory.allowed_source_manifest_hash==parent.allowed_source_manifest_hash and memory.documents_hash==parent.documents_hash)
                aliases.append({'researcher_id':researcher,'cap':cap,'parent_profile_id':parent.profile_id,
                                'memory_profile_id':memory.profile_id,'content_sha256':memory.content_sha256,
                                'original_fit_usage_sha256':c.digest(memory.fit_usage['original_fit_usage']),
                                'parent_identity_sha256':c.digest(parent_id),'memory_identity_sha256':c.digest(memory_id)})
                for item in items:
                    pp=consumer.prepare_payload(parent,item['context'],item['options'],parent_id)
                    mp=consumer.prepare_payload(memory,item['context'],item['options'],memory_id)
                    key=(researcher,cap,c.digest(item['item_id']),c.digest(item['option_order_id']))
                    record={'researcher_id':researcher,'cap':cap,'item_id_sha256':key[2],'option_order_id_sha256':key[3],
                            'system_sha256':c.sha256_text(pp['system']),'prompt_sha256':c.sha256_text(pp['prompt']),
                            'payload_sha256':pp['payload_sha256'],'equal':pp==mp,
                            'own_identity_configs_differ':parent_id!=memory_id,'parent_profile_id':parent.profile_id,'memory_profile_id':memory.profile_id}
                    expected=owner_rows[key]
                    check('alias and owner recorded hashes:'+c.digest(key),
                          record['equal'] and all(record[x]==expected[x] for x in ['system_sha256','prompt_sha256','payload_sha256','parent_profile_id']))
                    alias_rows.append(record)
                    hybrid_cfg=dict(cfg,method_id='profile_retrieval',profile_cap=512,chunk_chars=1200,top_k=5,
                                    decision={k:item[k] for k in ['context','options']},consumer_identity={'model':'gpt-6-luna'})
                    hybrid=c.build_profile(documents,hybrid_cfg,NoCalls())
                    owner_hybrid=next(r for r in owner_builds if r['researcher_id']==researcher and r['cap']==cap and
                                      r['method_id']=='profile_retrieval' and r['item_sha256']==c.digest([item['item_id'],item['option_order_id']]))
                    check('independent hybrid content status and byte count match owner evidence:'+c.digest(key),
                          hybrid.content_sha256==owner_hybrid['content_sha256'] and hybrid.status==owner_hybrid['status'] and
                          hybrid.error_code==owner_hybrid['error_code'] and hybrid.token_count==owner_hybrid['rendered_bytes'])
                    h={'researcher_id':researcher,'cap':cap,'item_id_sha256':key[2],'option_order_id_sha256':key[3],
                       'status':hybrid.status,'error_code':hybrid.error_code,'rendered_bytes':hybrid.token_count}
                    if cap==512:
                        check('hybrid cap512 explicitly unavailable:'+c.digest(key),hybrid.status=='unavailable' and hybrid.error_code=='frozen_profile_exceeds_allocation')
                    else:
                        check('hybrid complete exact parent content and both caps:'+c.digest(key),
                              hybrid.status=='complete' and hybrid.content['profile']==parent.content and
                              hybrid.fit_usage['original_fit_usage']==parent.fit_usage and hybrid.fit_usage['calls']==0 and
                              hybrid.token_count<=cap and len(c.canonical_json({'passages':hybrid.content['passages']}).encode())<=cap-512)
                        by_id={d['document_id']:d for d in documents}
                        for passage in hybrid.content['passages']:
                            doc=by_id[passage['document_id']]
                            check('hybrid exact permitted passage:'+c.digest([key,passage['document_id'],passage['start'],passage['end']]),
                                  passage['text']==doc['content'][passage['start']:passage['end']] and
                                  any(s['start']<=passage['start']<passage['end']<=s['end'] for s in doc['permitted_spans']))
                        hp=consumer.prepare_payload(hybrid,item['context'],item['options'],identity(hybrid))
                        check('hybrid payload is distinct from saved P1:'+c.digest(key),hp['payload_sha256']!=pp['payload_sha256'])
                        h.update(content_sha256=hybrid.content_sha256,payload_sha256=hp['payload_sha256'],passages=len(hybrid.content['passages']))
                    hybrids.append(h)
                # Renderer equality alone deliberately omits execution settings/model.
                item=items[0];base=consumer.prepare_payload(memory,item['context'],item['options'],memory_id)
                altered=consumer.prepare_payload(memory,item['context'],item['options'],dict(memory_id,settings={'temperature':1.0,'max_tokens':32},model='different-SYNTHETIC-model'))
                swapped=consumer.prepare_payload(memory,item['context'],list(reversed(item['options'])),memory_id)
                # Pure cache identity calculation; no job claim, backend or ledger.
                manifest={'method_id':parent.method_id,'profile_hash':parent.profile_id,'personalization_cap':parent.personalization_cap,
                          'consumer':{'model':'SYNTHETIC-fixed-consumer'},'items_hash':c.digest(items),
                          'option_order_schedule':[{'item_id':x['item_id'],'option_order_id':x['option_order_id']} for x in items],
                          'config_hash':c.digest(parent_id),'code_sha':RUNTIME}
                memory_manifest=dict(manifest,method_id=memory.method_id,profile_hash=memory.profile_id,
                                     personalization_cap=cap,config_hash=c.digest(memory_id))
                settings={'temperature':0,'max_tokens':8192,'system':base['system']}
                parent_cache=runner.cache_key(manifest,base['prompt'],settings)
                own_cache=runner.cache_key(memory_manifest,base['prompt'],settings)
                variants={
                    'model':runner.cache_key(dict(memory_manifest,consumer={'model':'SYNTHETIC-other-consumer'}),base['prompt'],settings),
                    'settings':runner.cache_key(memory_manifest,base['prompt'],dict(settings,max_tokens=4096)),
                    'item_identity':runner.cache_key(dict(memory_manifest,items_hash='0'*64),base['prompt'],settings),
                    'order_schedule':runner.cache_key(dict(memory_manifest,option_order_schedule=list(reversed(memory_manifest['option_order_schedule']))),base['prompt'],settings)}
                check('renderer is insufficient execution identity; cache separates aliases and execution differences:'+researcher+':'+str(cap),
                      altered==base and swapped['payload_sha256']!=base['payload_sha256'] and own_cache!=parent_cache and all(v!=own_cache for v in variants.values()))
                execution_controls.append({'researcher_id':researcher,'cap':cap,'model_settings_ignored_by_prepare_payload':altered==base,
                                           'ordered_options_change_payload':swapped['payload_sha256']!=base['payload_sha256'],
                                           'parent_cache_key':parent_cache,'memory_cache_key':own_cache,'variant_cache_keys':variants,
                                           'cache_probe':'Pure cache_key function with representative synthetic execution identity; not actual saved prediction manifests.'})
        check('expected independent counts',len(parents)==2 and len(aliases)==6 and len(alias_rows)==84 and len(hybrids)==84 and
              sum(h['status']=='complete' for h in hybrids)==56 and sum(h['status']=='unavailable' for h in hybrids)==28)
        check('all input and source bytes unchanged',all(sha(Path(v['path']).read_bytes())==v['sha256'] for v in inventory.values()) and
              source_before=={name:sha((a.source_root/name).read_bytes()) for name in pins['files']})
    output={'schema_version':'saved-profile-reuse-audit27-v1','source_commit':RUNTIME,'source_files_verified':len(source_before),
            'reader_sha256':sha(Path(__file__).read_bytes()),'checks':checks,'check_counts':{'verified':sum(x['verified'] for x in checks),'failed':sum(not x['verified'] for x in checks)},
            'parents':parents,'aliases':aliases,'comparisons':alias_rows,'hybrids':hybrids,'execution_identity_controls':execution_controls,
            'summary':{'parents':2,'memory_profiles_complete':6,'exact_payload_alias_comparisons':84,'hybrids_complete':56,'hybrids_unavailable_cap512':28,'model_calls':0},
            'consumer_implementation_sha256':consumer.implementation_hash(),'consumer_prompt_version':consumer.PROMPT_VERSION,
            'input_inventory':inventory,'owner_report_inventory':report_inventory,
            'limits':['Actual prediction execution model/settings/results not released here and remain unverified.',
                      'Independent memory/hybrid artifacts are reconstructed in memory with a distinct no-calls extractor identity; their profile IDs need not equal the owner construction IDs.',
                      'Own required identities are used for each parent and constructed memory profile. Exact system/prompt/payload bytes and hashes are compared.',
                      'Pure cache identity controls use representative synthetic execution manifests; no execution or existing cache is read.',
                      'No scoring, researcher preference accuracy, independent treatment replicate, cost savings or automatic saved-result reuse is established.',
                      'Original parent extraction usage remains attached; zero new builder calls is not zero parent production cost.']}
    dump(a.out/'report.json',output);dump(a.out/'input-inventory.json',{'schema_version':'reuse-audit-input-inventory-v1','files':list(inventory.values()),'source_commit':RUNTIME})
    print(json.dumps({'summary':output['summary'],'check_counts':output['check_counts']}))


if __name__=='__main__':main()
