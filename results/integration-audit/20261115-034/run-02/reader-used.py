"""Independent metadata-only completed control/hybrid execution reader."""
import argparse
from collections import Counter
import copy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import hashlib

RELEASE='bfe6e209358fe1e896beb7d229b9cc30db7957e7'
RUNTIME='f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
BASE='docs/overnight/gio-profile-20261115/handoffs/05/'
PINS={'018-execution-and-reuse-ready.json':'63ff8dc668a16bbba7ca88ced4074cb9be07d7b10c633cd7a9d3f26864244fe2',
 '018-completed-control-predictions.json':'2d2dadc49f712d30c5d37f9f6388bbcc3a0525b19bf9f18057ca2152a63499f8',
 '018-actual-control-alias-check.json':'15aa892cfad9836030b8d07f25039a891efd44ac9ea5fa737a958624c3baa422',
 '018-richer-control-alias-proposal.json':'506245b2d3b7870b5ca54943b1b0290e0d8f751a97746e0d1c33aff6f5b9fbd8',
 '016-control-prediction-bindings.json':'430d09d54b62e5aabf839a75f98e84c8683e2a95e88a5fd8a4c598c8ef7d5f32'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence-root',type=Path,required=True)
    ap.add_argument('--data-root',type=Path);ap.add_argument('--recorded-data-root')
    ap.add_argument('--archive-root',type=Path);ap.add_argument('--preservation',type=Path)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if bool(a.archive_root)!=bool(a.preservation) or bool(a.data_root)==bool(a.archive_root):ap.error('Choose original data-root or archive-root/preservation')
    if a.data_root and not a.recorded_data_root:ap.error('Recorded data root is required')
    sha=lambda b:hashlib.sha256(b).hexdigest()
    helper=a.evidence_root/'reader033_helpers.py'
    assert sha(helper.read_bytes())=='d563214bfc922763cb9df2b9b3daab26922f9c03a56b99f6152f0c314cabcc29'
    spec=importlib.util.spec_from_file_location('frozen_audit033_helpers',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    canon,digest,save=h.canon,h.digest,h.save
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'reader-used.py').write_bytes(Path(__file__).read_bytes())
    def deny(event,args):
        if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):raise RuntimeError('Live operations forbidden')
    sys.addaudithook(deny)
    published={};inventory=[];code={}
    for name,pin in PINS.items():
        raw=(a.evidence_root/name).read_bytes();assert sha(raw)==pin;published[name]=json.loads(raw)
        inventory.append({'kind':'git_object','commit':RELEASE,'path':BASE+name,'sha256':pin,'size_bytes':len(raw)})
    pins=json.loads((a.evidence_root/'SOURCE_SNAPSHOT.json').read_text());assert pins['source_commit']==RUNTIME
    for path,pin in pins['files'].items():
        raw=(a.evidence_root/'source'/path).read_bytes();assert sha(raw)==pin;code[Path(path).name]=raw
        inventory.append({'kind':'git_object','commit':RUNTIME,'path':path,'sha256':pin,'size_bytes':len(raw)})
    constants=h.source_constants(code['consumer.py'],['SYSTEM','INSTRUCTION','PROMPT_VERSION'])
    renderer=sha(b'consumer.py\0'+code['consumer.py']+b'\0contracts.py\0'+code['contracts.py'])
    owner=published['018-completed-control-predictions.json'];aliases_owner=published['018-actual-control-alias-check.json']
    prepared_owner=published['016-control-prediction-bindings.json'];richer=published['018-richer-control-alias-proposal.json']
    data=h.Inputs(a);checks=[];rows=[];jobs=[];batch_rows=[];canonical={};profiles={};cost_by_job={}
    def check(name,ok):
        checks.append({'name':name,'verified':bool(ok)})
        if not ok:
            save(a.out/'failed-checks.json',checks);save(a.out/'input-inventory.json',{'files':inventory+list(data.inventory.values()),'raw_copied':False})
            raise AssertionError(name+' failed; raw content not emitted')
    def ref(path,pin):return {'path':str(path),'sha256':pin}
    def profile_check(body):
        return (body['profile_id']==digest({k:v for k,v in body.items() if k!='profile_id'}) and
            body['config_id']==digest(body['config']) and body['content_sha256']==digest(body['content']))
    def render(content):return '' if content in (None,{},[],'') else canon(content)
    queue=data.read(aliases_owner['queue']);alias_proof=data.read(aliases_owner['alias_provenance']);selection=data.read(alias_proof['selection'])
    check('queue_runtime_and_alias_provenance',queue['runtime_sha']==RUNTIME and queue['control_alias_provenance']==aliases_owner['alias_provenance'])
    owner_jobs={x['job_id']:x for x in owner['jobs']};check('unique_234_owner_jobs',len(owner_jobs)==len(owner['jobs'])==234)
    earlier_by_job={}
    for row in prepared_owner['rows']:earlier_by_job.setdefault(row['prediction_job_id'],[]).append(row)
    expected_rows={(x['job_id'],x['item_sha256']):x for x in owner['rows']}
    check('unique_364_recorded_rows',len(expected_rows)==len(owner['rows'])==364)
    seen_jobs=set()
    for batch in owner['batches']:
        name=batch['name'];queued=next(x for x in queue['batches'] if x['name']==name)
        prepared=data.read(queued['prepared']);summary=data.read(ref(batch['execution_summary_path'],batch['execution_summary_sha256']))
        check('batch_binding:'+name,queued['prepared']['sha256']==batch['prepared_sha256'] and prepared['code_sha']==RUNTIME and
              prepared['batch_id']==summary['batch_id']==queued['batch_id'] and summary['status']=='complete' and
              summary['counts']==batch['summary_counts']=={'complete':queued['jobs'],'dispatched':queued['jobs'],'listed':queued['jobs'],'not_dispatched':0,'other':0})
        nrows=0;batch_cost=Decimal(0);input_tokens=0;output_tokens=0
        for packet_ref in prepared['jobs']:
            packet=data.read(packet_ref);manifest=packet['manifest'];job=manifest['job_id'];own=owner_jobs[job];config=packet['config'];backend=packet['backend']
            check('job_unique_and_batch:'+job,job not in seen_jobs and own['batch']==name and packet_ref['sha256']==own['packet_file_sha256']);seen_jobs.add(job)
            result=data.read(ref(own['result_path'],own['result_file_sha256']));outpath=PurePosixPath(own['result_path']).parent
            saved_manifest=data.read(ref(outpath/'manifest.json',own['saved_manifest_sha256']))
            receipt=data.read(ref(own['dispatch_receipt_path'],own['dispatch_receipt_sha256']))
            profile=data.read(packet['profile']);release=data.read(packet['release']);documents=release['sources']['documents']
            by_id={x['item_id']:x for x in release['items']};items=[by_id[x] for x in packet['item_ids']];count=len(items);profiles[job]=profile
            old=earlier_by_job[job][0];parent_job=old['build_parent']['job_id'];root=outpath.parent
            parent_result=data.read(ref(root/parent_job/'result.json',own['build_parent_result_sha256']))
            parent_profile=data.read(ref(root/parent_job/'profile.json',own['build_parent_profile_sha256']))
            check('completed_build_parent:'+job,profile==parent_profile==parent_result['profile'] and parent_result['job_id']==parent_job and parent_result['status']=='complete' and
                  parent_job in manifest['parent_job_ids'] and packet['profile']['sha256']==old['build_parent']['profile_file_sha256']==own['build_parent_profile_sha256'] and
                  parent_result['config_hash']==profile['config_id'])
            check('manifest_and_profile_identity:'+job,saved_manifest==manifest and digest(config)==manifest['config_hash']==result['config_hash'] and
                  result['manifest_hash']==receipt['manifest_sha256']==digest(manifest) and job==result['job_id']==receipt['job_id']==digest({k:v for k,v in manifest.items() if k not in ('job_id','lease','created_at','updated_at')}) and
                  profile_check(profile) and profile['profile_id']==manifest['profile_hash']==result['profile_hash'] and
                  manifest['method_id']==profile['method_id'] and profile['status']=='complete' and manifest['code_sha']==profile['code_sha']==result['code_sha']==RUNTIME and
                  manifest['personalization_cap']==profile['personalization_cap'] and manifest['replicate_id']==profile['replicate_id']==0 and
                  manifest['parent_job_ids']==own['parent_job_ids'] and manifest['extractor']==profile['extractor'])
            sources=sorted([{'document_id':d['document_id'],'content_sha256':d['content_sha256']} for d in documents],key=lambda d:d['document_id'])
            check('full_source_and_items:'+job,all(sha(d['content'].encode())==d['content_sha256'] for d in documents) and
                  sources==release['sources']['source_manifest']==profile['config']['allowed_sources'] and digest(sources)==profile['allowed_source_manifest_hash']==manifest['source_manifest_hash']==result['source_manifest_hash'] and
                  digest(documents)==profile['documents_hash']==manifest['documents_hash'] and digest(release['items'])==release['items_sha256'] and
                  digest(items)==manifest['items_hash'] and len(items)==len(set(packet['item_ids'])) and all(set(i)=={'item_id','researcher_id','context','options','option_order_id'} and i['researcher_id']==profile['researcher_id'] for i in items) and
                  packet['item_ids']==[x['item_id'] for x in result['predictions']] and manifest['option_order_schedule']==[{'item_id':i['item_id'],'option_order_id':i['option_order_id']} for i in items])
            content=render(profile['content']);identity=manifest['consumer'];settings=config['settings'];enforced=identity['enforced_settings']
            check('renderer_backend_settings:'+job,profile['renderer_implementation_hash']==config['renderer_implementation_hash']==renderer and
                  profile['method_implementation_hash']==config['method_implementation_hash']==sha(code['baselines.py']) and config['profile_prompt_version']==profile['prompt_version'] and
                  config['consumer_prompt_version']==constants['PROMPT_VERSION'] and identity==result['actual_backend'] and identity['model']==backend['model']=='gpt-6-luna' and
                  backend['reasoning']==enforced['reasoning_effort']=='medium' and enforced['adapter_implementation_sha256']==digest(code['backends.py'].decode()) and
                  enforced['temperature']=='not_sent' and settings=={'max_tokens':8192,'temperature':0.0} and backend['timeout']==60 and
                  len(content.encode())==profile['token_count']<=profile['personalization_cap'])
            passages=profile['content'].get('passages',[]) if isinstance(profile['content'],dict) else []
            docs={d['document_id']:d for d in documents}
            check('individual_passage_permissions:'+job,all(docs[x['document_id']]['content'][x['start']:x['end']]==x['text'] and
                  any(s['start']<=x['start']<x['end']<=s['end'] for s in docs[x['document_id']].get('permitted_spans',[{'start':0,'end':len(docs[x['document_id']]['content'])}])) for x in passages))
            if profile['method_id'] in ('lexical_retrieval','semantic_retrieval','profile_retrieval'):
                check('retrieval_decision_order:'+job,count==1 and profile['config']['decision']=={'context':items[0]['context'],'options':items[0]['options']})
            if profile['method_id']=='semantic_retrieval':
                bundle=profile['config']['embedding_bundle']
                check('embedding_binding_no_recharge:'+job,bundle['bundle_sha256']==profile['config']['embedding_bundle_sha256']==digest({k:v for k,v in bundle.items() if k!='bundle_sha256'}) and
                      bundle['request']['query_sha256']==digest(profile['config']['decision']) and bundle['request']['source_manifest_hash']==digest(sources) and
                      packet['embedding_producer_charge_again'] is False)
            if name=='fixed-P1-hybrids':
                frozen=data.read(packet['frozen_parent_file']);check('fixed_P1_parent:'+job,profile_check(frozen) and frozen==profile['config']['frozen_profile'] and
                      frozen['profile_id']==profile['config']['expected_profile_id']==profile['fit_usage']['reused_profile_id'] and frozen['method_id']=='P1' and frozen['status']=='complete' and
                      frozen['personalization_cap']==profile['config']['profile_cap']==512 and frozen['content']==profile['content']['profile'] and
                      profile['fit_usage']['original_fit_usage']==frozen['fit_usage'] and packet['frozen_parent_extraction_charge_again'] is False and len(manifest['parent_job_ids'])==2)
            check('terminal_counts_receipt_and_attempts:'+job,result['status']==receipt['status']=='complete' and result['counts']==receipt['counts']=={'attempted':count,'complete':count,'error':0} and
                  result['usage']==receipt['usage'] and result['usage']['attempted_calls']==count and result['usage']['cache_hits']==result['usage']['uncertain_attempts']==0 and
                  len(result['trace_hashes'])==2*count and result['missing_arms']==[] and receipt['result_path']==own['result_path'])
            for n,(item,pred) in enumerate(zip(items,result['predictions']),1):
                trace_ref=ref(outpath/'traces'/('%04d-started.json'%n),result['trace_hashes'][2*n-2]);end_ref=ref(outpath/'traces'/('%04d-complete.json'%n),result['trace_hashes'][2*n-1])
                trace=data.read(trace_ref);end=data.read(end_ref);payload={'context':item['context'],'options':item['options'],'personalization':content}
                prompt=constants['INSTRUCTION']+'\nINPUT_JSON:\n'+canon(payload);call_settings=dict(settings,system=constants['SYSTEM'])
                cache=digest({'manifest':{k:v for k,v in manifest.items() if k not in ('job_id','lease','created_at','updated_at')},'prompt':prompt,'settings':call_settings})
                key=job+':'+str(n);check('trace_request_response_binding:'+key,trace['attempt']==end['attempt']==n and trace['status']=='started' and end['status']=='complete' and
                      trace['prompt']==prompt and trace['settings']==call_settings and trace['backend']==identity and trace['cache_key']==end['cache_key']==cache and end['response_sha256']==sha(end['response'].encode()))
                check('result_row_binding:'+key,pred['status']=='complete' and pred['error_code'] is None and pred['item_sha256']==digest(item) and pred['items_sha256']==manifest['items_hash'] and
                      pred['job_id']==job and pred['manifest_sha256']==digest(manifest) and pred['actual_consumer']==identity and pred['payload_sha256']==digest(payload) and
                      pred['rendered_profile_sha256']==sha(content.encode()) and pred['cache_provenance']=={'hit':False,'key':cache})
                response=json.loads(end['response']);pr=response['probabilities'];w=max(range(len(pr)),key=pr.__getitem__)
                check('parsed_response_result_equality:'+key,pred['prediction']=={'choice':chr(ord('a')+w),'confidence':pr[w],'rationale':response.get('rationale',''),'probabilities':pr,'calibrated':False})
                hashes={'backend_identity':digest(identity),'payload':digest(payload),'prompt':sha(prompt.encode()),'settings':digest(settings),'system':sha(constants['SYSTEM'].encode())}
                expected=expected_rows[(job,digest(item))]
                check('published_row_independently_reproduced:'+key,expected['payload_sha256']==hashes['payload'] and expected['prompt_sha256']==hashes['prompt'] and expected['system_sha256']==hashes['system'] and
                      expected['backend_sha256']==hashes['backend_identity'] and expected['settings_sha256']==hashes['settings'] and expected['profile_id']==profile['profile_id'] and
                      expected['started_trace_sha256']==trace_ref['sha256'] and expected['complete_trace_sha256']==end_ref['sha256'] and expected['response_sha256']==end['response_sha256'] and
                      expected['option_order_id_sha256']==digest(item['option_order_id']) and expected['decision_sha256']==digest({'context':item['context'],'options':item['options']}))
                earlier=next(x for x in earlier_by_job[job] if x['prepared_payload_sha256']==hashes['payload'])
                check('prepared_equals_executed:'+key,earlier['prepared_prompt_sha256']==hashes['prompt'] and earlier['profile_id']==profile['profile_id'] and earlier['settings_sha256']==hashes['settings'])
                record={'batch':name,'job_id':job,'method':profile['method_id'],'cap':profile['personalization_cap'],'item_id_sha256':digest(item['item_id']),'item_sha256':digest(item),
                    'option_order_id_sha256':digest(item['option_order_id']),'profile_id':profile['profile_id'],'result_row_sha256':digest(pred),'result_sha256':own['result_file_sha256'],
                    'started_trace_sha256':trace_ref['sha256'],'completed_trace_sha256':end_ref['sha256'],'verified_hashes':hashes,'status':'complete'}
                rows.append(record);canonical[(job,item['item_id'])]=(record,item);nrows+=1
            amount=Decimal(str(result['usage']['reported_api_usd']));cost_by_job[job]=amount;batch_cost+=amount
            input_tokens+=result['usage']['input_tokens'];output_tokens+=result['usage']['output_tokens']
            check('job_usage_matches_recorded:'+job,amount==Decimal(str(own['reported_api_usd'])) and own['attempted_calls']==count and own['counts']==result['counts'])
            jobs.append({'batch':name,'job_id':job,'method':profile['method_id'],'profile_id':profile['profile_id'],'parent_job_ids':manifest['parent_job_ids'],'attempted_calls':count,
                'result_sha256':own['result_file_sha256'],'usage_sha256':digest(result['usage']),'reported_api_usd':str(amount)})
        check('batch_aggregate:'+name,len(prepared['jobs'])==queued['jobs']==batch['expected_jobs'] and nrows==queued['max_attempts']==batch['expected_rows'] and
              batch_cost==Decimal(batch['reported_api_usd']) and input_tokens==batch['input_tokens'] and output_tokens==batch['output_tokens'])
        batch_rows.append({'name':name,'jobs':len(prepared['jobs']),'rows':nrows,'attempts':nrows,'reported_api_usd':str(batch_cost),'input_tokens':input_tokens,'output_tokens':output_tokens})
    alias_rows=[];seen_aliases=set();alias_jobs=set();alias_predictions=set()
    for alias in alias_proof['aliases']:
        job=alias['canonical_job_id'];item_id=alias['item_id'];cap=alias['comparison_cap'];record,item=canonical[(job,item_id)];profile=profiles[job]
        key=(job,item_id,cap);check('unique_sparse_alias',key not in seen_aliases);seen_aliases.add(key);alias_jobs.add(job);alias_predictions.add((job,item_id))
        variant=copy.deepcopy(profile);variant.pop('profile_id');variant['personalization_cap']=cap;variant['config']['personalization_cap']=cap;variant['config_id']=digest(variant['config']);variant_id=digest(variant)
        check('sparse_variant_identity_and_content',profile['method_id'] in ('no_profile','name_only') and profile['personalization_cap']==alias['canonical_cap']==2048 and cap in (512,8192) and
              variant_id==alias['variant_profile_ids'][str(cap)] and profile['profile_id']==alias['variant_profile_ids']['2048'] and len(render(variant['content']).encode())<=cap)
        check('sparse_alias_executed_identity',alias['proof_sha256_by_field']==record['verified_hashes'] and alias['calls_added']==alias['independent_observations_added']==0 and alias['method']==record['method'])
        recorded=next(x for x in aliases_owner['records'] if x['canonical_job_id']==job and x['item_id_sha256']==digest(item_id) and x['comparison_cap']==cap)
        check('published_sparse_alias_reproduced',recorded['verified_hashes']==record['verified_hashes'] and recorded['variant_profile_id']==variant_id and recorded['canonical_trace_sha256']==record['started_trace_sha256'])
        alias_rows.append({'canonical_job_id':job,'item_id_sha256':digest(item_id),'comparison_cap':cap,'variant_profile_id':variant_id,'canonical_profile_id':profile['profile_id'],
                          'verified_hashes':record['verified_hashes'],'status':'explicit_reference_to_completed_canonical_result','additional_calls':0,'additional_observations':0})
    total=sum(cost_by_job.values(),Decimal(0));alias_cost=sum((cost_by_job[j] for j in alias_jobs),Decimal(0))
    check('all_completed_denominators',len(jobs)==len(seen_jobs)==234 and len(rows)==len(canonical)==364 and sum(j['attempted_calls'] for j in jobs)==364)
    item_repeats=Counter(digest(item) for record,item in canonical.values())
    paired=Counter(digest({'researcher':item['researcher_id'],'context':item['context'],'options':sorted(item['options'])}) for record,item in canonical.values())
    check('repeated_items_are_not_independent_rows',len(item_repeats)==28 and set(item_repeats.values())=={13} and len(paired)==14 and set(paired.values())=={26})
    check('nonadditive_alias_cost',len(alias_rows)==112 and len(alias_predictions)==56 and len(alias_jobs)==4 and alias_jobs<=seen_jobs and alias_cost==Decimal('0.00463625') and total==Decimal('0.057470'))
    check('richer_stays_proposed',richer['registered_aliases'] is False and richer['accounting_changed'] is False and richer['candidate_references']==len(richer['records'])==168 and
          richer['status']=='candidate_prepared_only_coordinator_adoption_pending' and all(x['status']=='candidate_equal_request_not_registered' for x in richer['records']))
    data.recheck();check('source_unchanged',all(sha((a.evidence_root/'source'/path).read_bytes())==pin for path,pin in pins['files'].items()))
    report={'audit':'control-execution-34','release_commit':RELEASE,'runtime_commit':RUNTIME,'reader_sha256':sha(Path(__file__).read_bytes()),'argv':sys.argv,
        'checks':checks,'check_counts':{'verified':len(checks),'failed':0},'batches':batch_rows,'jobs':jobs,'rows':rows,'sparse_aliases':alias_rows,
        'summary':{'canonical_jobs':234,'completed_rows':364,'matched_control_rows':308,'fixed_P1_hybrid_rows':56,'recorded_calls':364,'audit_model_calls':0,
            'unique_ordered_items':28,'method_cap_rows_per_ordered_item':13,'paired_decision_groups':14,
            'canonical_reported_usd':str(total),'sparse_alias_references':112,'sparse_canonical_rows':56,'sparse_canonical_jobs':4,'alias_cost_included_not_added':str(alias_cost),
            'richer_candidates_recorded_only':168},
        'limits':['Recorded artifact consistency, not provider-origin authentication or actual wire capture. Temperature is not sent by the pinned adapter.',
                  'No scores/labels; repeated method/cap rows and aliases are not independent observations.',
                  'Cost covers these prediction jobs only; excludes parent extraction/embedding costs, does not clear other campaign reservations or outcomes.',
                  'Richer168 proposals are read as public proposal status only; richer sources/configs/equivalence/adoption are not audited here.',
                  'Sparse alias provenance retains its original prepared status; later actual traces/results establish terminal equality without rewriting it.',
                  'No live calls, ledger connections, credentials, owner edits or raw publication.']}
    save(a.out/'report.json',report);save(a.out/'input-inventory.json',{'files':inventory+list(data.inventory.values()),'raw_copied':False})
    print(json.dumps({'summary':report['summary'],'check_counts':report['check_counts'],'private_inputs':len(data.inventory)},indent=2))


if __name__=='__main__':main()
