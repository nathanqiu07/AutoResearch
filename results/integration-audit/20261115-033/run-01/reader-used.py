"""Metadata-only independent audit of explicitly named execution aliases.

No source imports, model calls, scoring, credentials, directory scans or ledger.
Raw source/payload/response data stays in memory and in its approved input files.
"""
import argparse
import ast
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

RELEASE='a6c75b0e5b23cbd3ca8c364263f6ba6bfe2a67c2'
RUNTIME='f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
BASE='docs/overnight/gio-profile-20261115/handoffs/05/'
PINS={
 '016-prediction-bindings-ready.json':'a33ab258ee81e96f5225f98eef3a6bb1e39065f861e5eebe02965e9ff848abef',
 '016-actual-memory-alias-check.json':'c6e75e42bc2c3c44c3964a2b1c47fcef797faa3d750bcf9e65ccb2e2ad53a995',
 '016-control-prediction-bindings.json':'430d09d54b62e5aabf839a75f98e84c8683e2a95e88a5fd8a4c598c8ef7d5f32',
 '012-memory-payload-alias-check.json':'c65424a97b6ae0af66a9ce297bec6d4f9553ad26eb8ed99fb3dbca79afe6b561'}


def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def digest(x):return sha(canon(x).encode())
def save(path,obj):
    with path.open('x',encoding='utf-8') as f:f.write(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


class Inputs:
    def __init__(self,a):
        self.a=a;self.inventory={};self.cache={};self.locations={}
        self.records=json.loads(a.preservation.read_text())['files'] if a.archive_root else None
    def read(self,ref):
        assert set(ref)=={'path','sha256'} and len(ref['sha256'])==64
        key=ref['path'];expected=ref['sha256'];path=PurePosixPath(key)
        assert path.is_absolute() and '..' not in path.parts and path.suffix=='.json'
        if key in self.cache:
            assert self.inventory[key]['sha256']==expected
            return self.cache[key]
        if self.records is not None:
            matches=[r for r in self.records if r['kind']=='external' and r['path']==key and r['sha256']==expected]
            assert len(matches)==1,'One explicit archive reference required'
            member=Path(matches[0]['archive_member']);assert not member.is_absolute() and '..' not in member.parts
            actual=(self.a.archive_root/member).resolve();actual.relative_to(self.a.archive_root.resolve())
        else:
            relative=path.relative_to(PurePosixPath(self.a.recorded_data_root))
            actual=(self.a.data_root/relative).resolve();actual.relative_to(self.a.data_root.resolve())
        raw=actual.read_bytes()
        assert sha(raw)==expected,'Pinned input bytes differ: '+key
        self.inventory[key]={'kind':'external','path':key,'sha256':expected,'size_bytes':len(raw)}
        self.locations[key]=actual;self.cache[key]=json.loads(raw)
        return self.cache[key]
    def recheck(self):
        for key,actual in self.locations.items():assert sha(actual.read_bytes())==self.inventory[key]['sha256']


def source_constants(raw,names):
    found={}
    for node in ast.parse(raw).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in names:found[target.id]=ast.literal_eval(node.value)
    assert set(found)==set(names)
    return found


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence-root',type=Path,required=True)
    ap.add_argument('--data-root',type=Path);ap.add_argument('--recorded-data-root')
    ap.add_argument('--archive-root',type=Path);ap.add_argument('--preservation',type=Path)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if bool(a.archive_root)!=bool(a.preservation) or bool(a.data_root)==bool(a.archive_root):ap.error('Choose data-root or archive-root/preservation')
    if a.data_root and not a.recorded_data_root:ap.error('--recorded-data-root required with --data-root')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'reader-used.py').write_bytes(Path(__file__).read_bytes())
    def denied(event,args):
        if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):raise RuntimeError('Live operation prohibited')
    sys.addaudithook(denied)
    published={};source_inventory=[]
    for name,pin in PINS.items():
        raw=(a.evidence_root/name).read_bytes();assert sha(raw)==pin
        published[name]=json.loads(raw);source_inventory.append({'kind':'git_object','commit':RELEASE,'path':BASE+name,'sha256':pin,'size_bytes':len(raw)})
    pins=json.loads((a.evidence_root/'SOURCE_SNAPSHOT.json').read_text());assert pins['source_commit']==RUNTIME
    code={}
    for path,pin in pins['files'].items():
        raw=(a.evidence_root/'source'/path).read_bytes();assert sha(raw)==pin;code[Path(path).name]=raw
        source_inventory.append({'kind':'git_object','commit':RUNTIME,'path':path,'sha256':pin,'size_bytes':len(raw)})
    const=source_constants(code['consumer.py'],['SYSTEM','INSTRUCTION','PROMPT_VERSION'])
    renderer=sha(b'consumer.py\0'+code['consumer.py']+b'\0contracts.py\0'+code['contracts.py'])
    owner=published['016-actual-memory-alias-check.json'];prior=published['012-memory-payload-alias-check.json']
    data=Inputs(a);checks=[];rows=[];job_rows=[];canonical={};totals=Decimal(0)
    def check(name,value):
        checks.append({'name':name,'verified':bool(value)})
        if not value:
            save(a.out/'failed-checks.json',checks)
            save(a.out/'input-inventory.json',{'files':source_inventory+list(data.inventory.values()),'raw_copied':False})
            raise AssertionError(name+' failed; no raw content emitted')
    index=data.read(owner['index']);proof=data.read(owner['proof']);parent_index=data.read(index['parent_index'])
    prepared=data.read(index['canonical_prepared_batch']);selection=data.read(proof['selection'])
    check('explicit_alias_policy_and_runtime',selection['runtime_sha']==parent_index['runtime_sha']==prepared['code_sha']==RUNTIME and
          selection['memory_alias_policy']['requested_caps']==[512,2048,8192] and selection['memory_alias_policy']['new_calls']==0 and
          index['proof']==owner['proof'] and proof['parent_index']==index['parent_index']==selection['parent_handoff'])
    check('explicit_alias_count',len(proof['aliases'])==index['memory_references']==84 and len(index['profiles'])==2)
    recorded={(x['canonical_job_id'],x['item_id_sha256'],x['cap']):x for x in owner['records']}
    check('owner_records_unique',len(recorded)==len(owner['records'])==84)
    for group in index['profiles']:
        job=group['job_id'];packet=data.read(group['prepared_packet']);parent=data.read(group['profile']);result=data.read(group['result'])
        manifest=packet['manifest'];release=data.read(packet['release']);documents=release['sources']['documents']
        by_id={x['item_id']:x for x in release['items']};items=[by_id[x] for x in packet['item_ids']]
        parent_ref=next(x for x in parent_index['profiles'] if x['profile_id']==group['profile_id'])
        original_parent=data.read(parent_ref['profile']);parent_job=parent_ref['job_id']
        completed=data.read(packet['completed_profile_selection'])
        selected=next(x for x in completed['rows'] if x['job_id']==parent_job)
        build_result=data.read(selected['result']);build_packet=data.read(selected['build_packet'])
        check('parent_build_terminal:'+job,selected['selected'] is True and build_result['status']=='complete' and
              build_result['profile']==parent and build_result['job_id']==parent_job and build_packet['manifest']['job_id']==parent_job and
              build_result['manifest_hash']==digest(build_packet['manifest']) and selected['profile_id']==parent['profile_id'])
        check('exact_profile_parent_source:'+job,parent==original_parent and parent['profile_id']==group['profile_id']==manifest['profile_hash']==result['profile_hash'] and
              parent['profile_id']==digest({k:v for k,v in parent.items() if k!='profile_id'}) and parent['config_id']==digest(parent['config']) and
              parent['content_sha256']==digest(parent['content']) and parent['status']=='complete' and parent['method_id']=='P1' and parent['personalization_cap']==512 and
              parent['code_sha']==RUNTIME and parent['replicate_id']==manifest['replicate_id']==0 and parent['config']['evidence_policy']=='explicit-only' and
              manifest['parent_job_ids']==[parent_job] and manifest['documents_hash']==parent['documents_hash']==digest(documents) and
              manifest['source_manifest_hash']==result['source_manifest_hash']==parent['allowed_source_manifest_hash']==release['sources']['allowed_source_manifest_hash'])
        check('packet_preparation_config_bound:'+job,group['prepared_packet'] in prepared['jobs'] and packet['profile']==group['profile'] and
              digest(packet['config'])==manifest['config_hash']==result['config_hash'] and packet['config']==group['consumer_config'] and
              manifest['job_id']==job==digest({k:v for k,v in manifest.items() if k not in ('job_id','lease','created_at','updated_at')}) and
              result['manifest_hash']==digest(manifest) and packet['lease']['job_id']==job and manifest['method_id']=='P1' and
              manifest['code_sha']==result['code_sha']==RUNTIME)
        check('item_order_sources_bound:'+job,all(set(x)=={'item_id','researcher_id','context','options','option_order_id'} for x in items) and
              packet['item_ids']==group['ordered_item_ids']==[x['item_id'] for x in result['predictions']] and len(items)==len(set(packet['item_ids']))==14 and
              digest(items)==manifest['items_hash'] and manifest['option_order_schedule']==[{'item_id':x['item_id'],'option_order_id':x['option_order_id']} for x in items] and
              all(x['researcher_id']==parent['researcher_id'] for x in items))
        identity=manifest['consumer'];backend=packet['backend'];config=packet['config'];settings=config['settings']
        enforced=identity['enforced_settings']
        check('model_backend_settings_bound:'+job,identity==result['actual_backend']==group['consumer_identity'] and backend==group['backend'] and
              identity['model']==backend['model']==selection['consumer']['model']=='gpt-6-luna' and
              enforced['reasoning_effort']==backend['reasoning']==selection['consumer']['reasoning']=='medium' and
              enforced['adapter_implementation_sha256']==digest(code['backends.py'].decode()) and enforced['temperature']=='not_sent' and
              settings=={'max_tokens':selection['consumer']['max_tokens'],'temperature':selection['consumer']['temperature']}=={'max_tokens':8192,'temperature':0.0} and
              backend['timeout']==selection['consumer']['timeout']==60 and config['renderer_implementation_hash']==parent['renderer_implementation_hash']==renderer and
              config['method_implementation_hash']==parent['method_implementation_hash'] and config['profile_prompt_version']==parent['prompt_version'] and
              config['consumer_prompt_version']==const['PROMPT_VERSION'])
        check('terminal_counts_no_cache_uncertainty:'+job,result['status']=='complete' and result['counts']=={'attempted':14,'complete':14,'error':0} and
              result['usage']['attempted_calls']==14 and result['usage']['cache_hits']==result['usage']['uncertain_attempts']==0 and len(result['trace_hashes'])==28 and
              len(group['started_traces'])==14 and result['missing_arms']==[])
        content=canon(parent['content']);check('all_memory_caps_fit:'+job,len(content.encode())==parent['token_count']<=512)
        for n,(item,pred,trace_ref) in enumerate(zip(items,result['predictions'],group['started_traces']),1):
            trace=data.read(trace_ref)
            # Exact completed sibling is named by frozen runner's sequence rule and pinned result hash.
            completion_ref={'path':str(PurePosixPath(trace_ref['path']).with_name('%04d-complete.json'%n)),
                            'sha256':result['trace_hashes'][2*n-1]}
            complete=data.read(completion_ref)
            payload={'context':item['context'],'options':item['options'],'personalization':content}
            prompt=const['INSTRUCTION']+'\nINPUT_JSON:\n'+canon(payload);actual_settings=dict(settings,system=const['SYSTEM'])
            cache=digest({'manifest':{k:v for k,v in manifest.items() if k not in ('job_id','lease','created_at','updated_at')},'prompt':prompt,'settings':actual_settings})
            key=job+':'+str(n)
            check('actual_request_trace:'+key,trace['attempt']==n and trace['status']=='started' and trace['prompt']==prompt and trace['settings']==actual_settings and
                  trace['backend']==identity and trace['cache_key']==cache and trace_ref['sha256']==result['trace_hashes'][2*n-2])
            check('completed_response_trace:'+key,complete['attempt']==n and complete['status']=='complete' and complete['cache_key']==cache and
                  complete['response_sha256']==sha(complete['response'].encode()))
            check('result_item_request_binding:'+key,pred['item_id']==item['item_id'] and pred['item_sha256']==digest(item) and pred['items_sha256']==manifest['items_hash'] and
                  pred['manifest_sha256']==digest(manifest) and pred['job_id']==job and pred['actual_consumer']==identity and pred['payload_sha256']==digest(payload) and
                  pred['rendered_profile_sha256']==sha(content.encode()) and pred['cache_provenance']=={'hit':False,'key':cache} and pred['status']=='complete' and pred['error_code'] is None)
            # Equality of stored parsed response/result only; no labels, score, or outcome summary.
            response=json.loads(complete['response']);prob=response['probabilities'];winner=max(range(len(prob)),key=prob.__getitem__)
            expected_prediction={'choice':chr(ord('a')+winner),'confidence':prob[winner],'rationale':response.get('rationale',''),'probabilities':prob,'calibrated':False}
            check('response_result_exact_parse:'+key,pred['prediction']==expected_prediction)
            hashes={'backend_identity':digest(identity),'payload':digest(payload),'prompt':sha(prompt.encode()),'settings':digest(settings),
                    'system':sha(const['SYSTEM'].encode()),'timeout':digest(backend['timeout'])}
            canonical[(job,item['item_id'])]={'item':item,'hashes':hashes,'parent':parent,'parent_job':parent_job,'trace_ref':trace_ref,'group':group,
                                             'result_row_sha256':digest(pred),'completion_ref':completion_ref}
        amount=Decimal(str(result['usage']['reported_api_usd']));totals+=amount
        declared=next(x for x in owner['jobs'] if x['job_id']==job)
        check('deduplicated_job_usage:'+job,digest(result['usage'])==declared['usage_sha256'] and amount==Decimal(str(declared['reported_api_usd'])) and
              amount==Decimal(str(result['usage']['budget_detail']['spent_usd'])) and declared['result']==group['result'] and declared['parent_build_job_id']==parent_job)
        job_rows.append({'job_id':job,'parent_job_id':parent_job,'profile_id':parent['profile_id'],'result_sha256':group['result']['sha256'],
                         'attempted_calls':14,'prediction_rows':14,'reported_api_usd':str(amount),'usage_sha256':digest(result['usage']),
                         'backend_identity_sha256':digest(identity),'settings_sha256':digest(settings)})
    aliases=set();refs=Counter()
    for alias in proof['aliases']:
        key=(alias['canonical_job_id'],alias['item_id']);row=canonical[key];parent=row['parent'];cap=alias['cap']
        triple=key+(cap,);check('unique_alias_reference',triple not in aliases);aliases.add(triple);refs[key]+=1
        check('explicit_reuse_mapping',alias['status']=='reference_to_complete_canonical_prediction' and alias['method']=='memory_summary' and alias['canonical_method']=='P1' and
              alias['calls_added']==alias['independent_observations_added']==0 and alias['canonical_cap']==parent['personalization_cap']==512 and cap in [512,2048,8192] and
              alias['canonical_profile_id']==parent['profile_id'] and alias['researcher_id']==parent['researcher_id'] and
              alias['canonical_packet']==row['group']['prepared_packet'] and alias['canonical_result']==row['group']['result'] and alias['canonical_trace']==row['trace_ref'])
        check('actual_proof_field_hashes',alias['proof_sha256_by_field']==row['hashes'])
        owner_row=recorded[(key[0],digest(key[1]),cap)]
        old_alias=next(x for x in prior['aliases'] if x['researcher_id']==alias['researcher_id'] and x['cap']==cap)
        check('owner_record_recomputed',owner_row['verified_hashes']==row['hashes'] and owner_row['canonical_profile_id']==parent['profile_id'] and
              owner_row['canonical_trace_sha256']==row['trace_ref']['sha256'] and owner_row['canonical_result_sha256']==row['group']['result']['sha256'] and
              owner_row['memory_profile_id']==old_alias['memory_profile_id'] and old_alias['parent_profile_id']==parent['profile_id'])
        rows.append({'canonical_job_id':key[0],'item_id_sha256':digest(key[1]),'option_order_id_sha256':digest(row['item']['option_order_id']),
            'item_sha256':digest(row['item']),'comparison_cap':cap,'canonical_profile_id':parent['profile_id'],'parent_build_job_id':row['parent_job'],
            'canonical_result_sha256':row['group']['result']['sha256'],'canonical_result_row_sha256':row['result_row_sha256'],
            'started_trace_sha256':row['trace_ref']['sha256'],'completed_trace_sha256':row['completion_ref']['sha256'],'verified_hashes':row['hashes'],
            'memory_profile_id_recorded_in_prior_public_report':old_alias['memory_profile_id'],'status':'verified_explicit_reference','additional_calls':0,'additional_independent_observations':0})
    check('exact_84_references_to_28_results',len(rows)==84 and len(canonical)==28 and len(job_rows)==2 and set(refs.values())=={3})
    check('canonical_cost_once',totals==Decimal('0.00254125')==Decimal(str(owner['canonical_reported_api_usd_sum_once'])))
    groups=Counter(digest({'researcher':v['item']['researcher_id'],'context':v['item']['context'],'options':sorted(v['item']['options'])}) for v in canonical.values())
    check('paired_orders_retained',len(groups)==14 and set(groups.values())=={2})
    data.recheck()
    report={'audit':'execution-alias-33','release_commit':RELEASE,'runtime_commit':RUNTIME,'reader_sha256':sha(Path(__file__).read_bytes()),'argv':sys.argv,
        'checks':checks,'check_counts':{'verified':len(checks),'failed':0},'aliases':rows,'canonical_jobs':job_rows,
        'summary':{'verified_memory_references':84,'unique_ordered_prediction_rows':28,'paired_decision_groups':14,'unique_canonical_jobs':2,
                   'recorded_actual_attempts':28,'additional_alias_calls':0,'additional_independent_observations':0,'audit_model_calls':0,
                   'canonical_reported_api_usd_once':str(totals)},
        'prepared_only_owner_snapshot':{'prepared_jobs':234,'control_rows':308,'hybrid_rows':56,'no_profile_name_only_cap_aliases':112,
            'status':'recorded_only_not_retested_or_promoted_to_execution'},
        'limits':['Recorded artifact consistency, not authenticated provider origin or exact wire capture.',
                  'Generic temperature=0.0 is a caller field; pinned backend identity/source says temperature not sent.',
                  'No scoring, accuracy, independent-observation increase, or new stochastic prediction claim.',
                  'P1 jobs were actually recorded as executed; memory_summary is an explicit reference mapping, not execution under a memory method/job ID or an automatic runner cache hit.',
                  'Memory construction IDs are cross-linked to the previous public012 report; no new memory builder is run.',
                  '234 preparations and112 control cap aliases remain outside this actual-memory execution audit.',
                  'No active ledger, credential/env file, private labels, raw publication or owner edits.']}
    save(a.out/'report.json',report)
    save(a.out/'input-inventory.json',{'files':source_inventory+list(data.inventory.values()),'raw_copied':False})
    print(json.dumps({'summary':report['summary'],'check_counts':report['check_counts'],'private_inputs':len(data.inventory)},indent=2))


if __name__=='__main__':main()
