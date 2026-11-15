#!/usr/bin/env python3
"""Metadata-only coverage/provenance audit. Reads explicit pinned refs, never SQLite.
--inputs supports relocation by changing read_path only; logical identities stay fixed.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import itertools
import json
from pathlib import Path
import socket
import sys

INDEX_SHA='7483aed821465ba8ef1032572954fb965d536b0613371eb90aec60b8c37d5b84'
REBIND_SHA='4cc1b9930d3f618efbc907056556be31044d19aa4c3d9760d9bfbf383f591cca'
RECEIPT32_SHA='6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8'
REGISTRY_SHA='5faad8d95b755e1717f3eab17fb3542cd43f19d92816862fd2e8cae9d4d6ada5'
RUNTIME='f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
OLD='df4cbde2513374d37d42fc382fb38b5af057d5d0c6645dc36b3fb8d5f22e884a'
TARGET6='64894d812872c2af9c83852550a07d59700fa577a61c146d6276b8d02b68b89b'
P7='818518adfb6b0d9f277e1a33a577752f85386aae1acee48b75e8ff647f8e8970'
P7_PREP_SHA='9644dcd7925965652da808b50bf1cb779471ec5b70f41e8c65172c914bd7740f'
P7_SUMMARY_SHA='bd96608a062a75630d3d395f07ff753147e61e36e4832c1f81473e7be683e273'
SIDE_PINS={'phase2_readiness_probe':'39d14e76f1828574f539d52d366b4e5da1d0bdb7da603d6feffb3691a5b9a668',
           'phase2_access_probes':'4886347fdc74eca0d7378e7a1ce57aacaf89c875dc334553deef2545c13179b1',
           'phase2_embedding_production':'e5e8d3f9265887276afc067d0c5fca43a546b219be3ace1e083f1ae26734af89'}


def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(v):return sha(canonical(v))
def strict(b):
    def pairs(values):
        out={}
        for k,v in values:
            if k in out:raise ValueError('Duplicate JSON key')
            out[k]=v
        return out
    return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def nanos(value):return int(Decimal(str(value))*1000000000)


class Checks:
    def __init__(self):self.rows=[]
    def add(self,name,ok):
        self.rows.append({'check':name,'passed':bool(ok)})
        if not ok:raise ValueError('Failed check: '+name)


class Inputs:
    def __init__(self,inventory=None):
        self.files={};self.originals={};self.allowed=None
        if inventory is not None:
            self.allowed={r['path']:r for r in inventory['files']}
            if len(self.allowed)!=len(inventory['files']):raise ValueError('Duplicate inventory path')
            pins={r['path']:r['sha256'] for r in inventory['files']}
            if digest(pins)!=inventory['input_set_sha256']:raise ValueError('Input inventory changed')
            for r in inventory['files']:
                path=Path(r.get('read_path',r['path']));b=path.read_bytes()
                if sha(b)!=r['sha256'] or len(b)!=r['bytes']:raise ValueError('Frozen input mismatch')
                self.originals[str(path)]=b
    def get(self,ref,role):
        identity=ref['path'];expected=ref['sha256']
        if Path(identity).suffix in ('.sqlite','.sqlite3','.db') or Path(identity).name=='.env':raise ValueError('Forbidden input')
        if identity in self.files:
            row=self.files[identity]
            if row['sha256']!=expected:raise ValueError('Conflicting immutable input identity')
            row['roles']=sorted(set(row['roles']+[role]));return strict(row['data'])
        if self.allowed is not None:
            if identity not in self.allowed or self.allowed[identity]['sha256']!=expected:raise ValueError('Undeclared replay input')
            path=Path(self.allowed[identity].get('read_path',identity))
        else:path=Path(identity)
        b=path.read_bytes()
        if sha(b)!=expected:raise ValueError('Input hash mismatch: '+identity)
        if str(path) in self.originals and self.originals[str(path)]!=b:raise ValueError('Input changed during read')
        self.originals[str(path)]=b
        self.files[identity]={'path':identity,'read_path':str(path),'sha256':expected,'bytes':len(b),'roles':[role],'data':b}
        return strict(b)
    def finish(self):
        for path,b in self.originals.items():
            if Path(path).read_bytes()!=b:raise ValueError('Input changed after read')
        if self.allowed is not None and set(self.files)!=set(self.allowed):raise ValueError('Replay input set differs')
    def inventory(self,entry):
        rows=[{k:v for k,v in r.items() if k!='data'} for _,r in sorted(self.files.items())]
        return {'schema_version':'phase2-coverage35-inputs-v1','entry_points':entry,'input_set_sha256':digest({r['path']:r['sha256'] for r in rows}),'files':rows}


def summarize(rows):
    groups=defaultdict(Counter)
    for r in rows:
        for dimension in ('origin','method','researcher_id','cap','evidence_policy'):
            groups[dimension+':'+str(r[dimension])][r['status']]+=1
    return {'cells':len(rows),'status_counts':dict(Counter(r['status'] for r in rows)),
            'by_dimension':{k:dict(v) for k,v in sorted(groups.items())},
            'recorded_attempts':sum(r['usage']['attempted_calls'] for r in rows),
            'known_estimate_nanos':sum(r['usage']['known_estimate_nanos'] for r in rows),
            'retained_hold_nanos':sum(r['usage']['retained_hold_nanos'] for r in rows),
            'unknown_input_usage_cells':sum(r['usage']['input_tokens'] is None for r in rows),
            'unknown_output_usage_cells':sum(r['usage']['output_tokens'] is None for r in rows)}


def allowed_rebind(old,new,checks,label):
    # Rebinding changes the lease id and adds a separately checked provenance receipt.
    # Prepared copies may also relocate the byte-identical release.
    checks.add(label+'.same_manifest',old['manifest']==new['manifest'])
    checks.add(label+'.same_config',old['config']==new['config'])
    checks.add(label+'.same_release_bytes',old['release']['sha256']==new['release']['sha256'])
    checks.add(label+'.same_packet_except_lease_release_provenance',
               {k:v for k,v in old.items() if k not in ('lease','release')}=={k:v for k,v in new.items() if k not in ('lease','release','continuation_provenance')})
    checks.add(label+'.same_lease_except_id',{k:v for k,v in old['lease'].items() if k!='lease_id'}=={k:v for k,v in new['lease'].items() if k!='lease_id'})
    checks.add(label+'.new_lease_id',old['lease']['lease_id']!=new['lease']['lease_id'])


def run(a):
    def denied(*args,**kwargs):raise RuntimeError('Network disabled for offline audit')
    socket.socket.connect=denied;socket.create_connection=denied;socket.getaddrinfo=denied
    frozen=strict(Path(a.inputs).read_bytes()) if a.inputs else None
    entry=frozen['entry_points'] if frozen else {
      'index':{'path':str(Path(a.index)),'sha256':INDEX_SHA},'target6_rebind':{'path':str(Path(a.target6_rebind)),'sha256':REBIND_SHA},
      'retention32':{'path':str(Path(a.retention32)),'sha256':RECEIPT32_SHA},'registry':{'path':str(Path(a.registry)),'sha256':REGISTRY_SHA}}
    for k,h in [('index',INDEX_SHA),('target6_rebind',REBIND_SHA),('retention32',RECEIPT32_SHA),('registry',REGISTRY_SHA)]:
        if entry[k]['sha256']!=h:raise ValueError('Entry-point pin mismatch')
    inputs=Inputs(frozen);checks=Checks()
    index=inputs.get(entry['index'],'released_complete_extraction_index')
    rebind6=inputs.get(entry['target6_rebind'],'target6_rebind_evidence')
    retention=inputs.get(entry['retention32'],'frozen032_retention_receipt')
    registry=inputs.get(entry['registry'],'coordination_pointer_snapshot_not_runtime')
    source=next(s for s in retention['sources'] if s['commit']==RUNTIME)
    def verify_source():
        for name,h in source['files'].items():
            if sha((Path(a.source_root)/name).read_bytes())!=h:raise ValueError('Frozen source mismatch: '+name)
    verify_source();sys.path.insert(0,str(Path(a.source_root)))
    from autoresearch.taste.overnight.contracts import source_manifest,validate_documents,ProfileArtifact
    from autoresearch.taste.overnight.runner import job_id,ITEM_FIELDS
    from autoresearch.taste.overnight.backends import PRICING_VERSION
    adapter_text=(Path(a.source_root)/'autoresearch/taste/overnight/backends.py').read_text()
    checks.add('index.runtime',index['runtime_sha']==RUNTIME)
    checks.add('index.no_private_labels',index['private_labels_included'] is False)
    selection=inputs.get(index['broad_selection'],'predeclared_broad_selection')
    expected=set(itertools.product(selection['methods'],selection['profile_caps'],selection['evidence_policies'],selection['researchers'],selection['replicate_ids']))
    tuples=[(c['method'],c['cap'],c['evidence_policy'],c['researcher_id'],c['replicate_id']) for c in index['cells']]
    checks.add('grid.exact_cartesian_coverage',len(tuples)==len(set(tuples)) and set(tuples)==expected)
    checks.add('grid.unique_job_and_cell_ids',len({c['job_id'] for c in index['cells']})==len(tuples)==len({c['cell_id'] for c in index['cells']}))
    checks.add('grid.reported_denominator',len(tuples)==index['planned_cells'])
    old_coverage={c['job_id']:c for c in retention['coverage'] if c['batch_id']==OLD}
    old_records={r['path']:r for r in retention['required_records']}
    selected_batches={b['batch_id']:b for b in registry['batches'] if b['batch_id'] in (OLD,TARGET6,P7)}
    checks.add('new_p7.authoritative_prepared_pin',selected_batches[P7]['prepared']['sha256']==P7_PREP_SHA)
    checks.add('new_p7.authoritative_summary_pin',selected_batches[P7]['execution_summary']['sha256']==P7_SUMMARY_SHA)
    batches={};new_packets={};origin_map={};rebind_reports=[]
    for bid,bmeta in selected_batches.items():
        prepared=inputs.get(bmeta['prepared'],'actual_dispatch_prepared')
        summary=inputs.get(bmeta['execution_summary'],'terminal_batch_summary')
        checks.add(bid+'.terminal',summary['status'] in ('stopped','complete'))
        checks.add(bid+'.source_pin',prepared['code_sha']==RUNTIME)
        checks.add(bid+'.identity',summary['batch_id']==prepared['batch_id']==bid)
        packets=[inputs.get(ref,'actual_dispatch_packet') for ref in prepared['jobs']]
        checks.add(bid+'.unique_jobs',len({p['manifest']['job_id'] for p in packets})==len(packets))
        checks.add(bid+'.summary_admissions',summary['counts']['listed']==len(packets) and summary['counts']['listed']==summary['counts']['dispatched']+summary['counts']['not_dispatched'])
        batches[bid]={'prepared':prepared,'summary':summary,'packets':packets,'refs':prepared['jobs']}
        if bid!=OLD:
            evidence=inputs.get(prepared['rebind_evidence'],'continuation_rebind_evidence')
            ids=inputs.get(prepared['explicit_job_ids'],'explicit_continuation_job_ids')
            policy=inputs.get(prepared['ledger_policy'],'continuation_ledger_policy')
            auth=inputs.get(policy['continuation_authorization'],'frozen_continuation_authorization')
            stopped=inputs.get(prepared['stopped_ledger_receipt'],'frozen_stopped_accounting_snapshot')
            inputs.get(evidence['old_prepared'],'original_prepared_for_rebind')
            checks.add(bid+'.evidence_no_model_call',evidence['calls_performed']==0 and evidence['ledger_mutations']==0)
            checks.add(bid+'.rebound_from_identity',prepared['rebound_from']==evidence['old_prepared'])
            checks.add(bid+'.same_policy_ref',prepared['ledger_policy']==evidence['new_ledger_policy'])
            checks.add(bid+'.same_stopped_snapshot_ref',prepared['stopped_ledger_receipt']==evidence['stopped_ledger_receipt'])
            # Retain the concrete schema; it may be a direct list or an object with job_ids.
            id_list=ids if isinstance(ids,list) else ids['job_ids']
            maps={m['job_id']:m for m in evidence['mappings']}
            checks.add(bid+'.exact_selected_ids',set(id_list)==set(maps)=={p['manifest']['job_id'] for p in packets})
            for ref,p in zip(prepared['jobs'],packets):
                jid=p['manifest']['job_id'];m=maps[jid];oldp=inputs.get(m['old_packet'],'original_packet_in_rebind')
                newp=inputs.get(m['new_packet'],'rebind_source_packet')
                # Prepared publication changes the release snapshot location only.
                checks.add(jid+'.rebind_source_to_prepared', {k:v for k,v in newp.items() if k!='release'}=={k:v for k,v in p.items() if k!='release'} and newp['release']['sha256']==p['release']['sha256'])
                allowed_rebind(oldp,p,checks,jid)
                checks.add(jid+'.exact_continuation_provenance',p['continuation_provenance']=={
                    'old_packet':m['old_packet'],'old_prepared':evidence['old_prepared'],
                    'old_lease':oldp['lease'],'prior_attempts':0,'new_ledger_policy':evidence['new_ledger_policy'],
                    'stopped_ledger_receipt':evidence['stopped_ledger_receipt']})
                checks.add(jid+'.mapping_manifest',m['manifest_sha256']==digest(p['manifest']))
                checks.add(jid+'.mapping_lease',m['new_lease_id']==p['lease']['lease_id'] and m['old_lease_id']==oldp['lease']['lease_id'])
                new_packets[jid]=p;origin_map[jid]='target6_continuation' if bid==TARGET6 else 'p7_continuation'
            rebind_reports.append({'batch_id':bid,'jobs':len(packets),'recorded_no_retry':evidence['no_retry'],
                'recorded_prior_absence_claims':sum(e.get('output_and_started_traces_absent') is True and e.get('runner_claim_absent') is True for e in evidence['evidence']),
                'prior_absence_limit':'Contemporaneous saved assertions plus pinned non-dispatch receipts where available; not a retrospective filesystem absence check.'})
    rows=[];result_by_job={};old_unknown=[]
    for cell in index['cells']:
        jid=cell['job_id'];label=cell['cell_id'];packet=inputs.get(cell['build_packet'],'indexed_original_build_packet')
        original_prepared=inputs.get(cell['original_prepared'],'indexed_original_prepared')
        release=inputs.get(cell['release'],'approved_label_free_release')
        result=inputs.get(cell['result'],'terminal_extraction_result')
        dispatch=inputs.get(cell['dispatch_receipt'],'indexed_terminal_dispatch_receipt')
        config=packet['config'];manifest=packet['manifest'];docs=release['sources']['documents'];sources=source_manifest(docs)
        checks.add(label+'.prepared_packet_membership',cell['build_packet'] in original_prepared['jobs'])
        checks.add(label+'.job_identity',manifest['job_id']==jid==job_id(manifest)==result['job_id']==dispatch['job_id'])
        checks.add(label+'.manifest_hash',digest(manifest)==result['manifest_hash']==dispatch['manifest_sha256'])
        checks.add(label+'.config_hash',digest(config)==manifest['config_hash']==result['config_hash'])
        checks.add(label+'.source_commit',manifest['code_sha']==config['code_sha']==result['code_sha']==RUNTIME)
        checks.add(label+'.cell_binding',all(config[k]==cell[c] for k,c in [('method_id','method'),('personalization_cap','cap'),('evidence_policy','evidence_policy'),('researcher_id','researcher_id'),('replicate_id','replicate_id')]))
        checks.add(label+'.manifest_config_fields',all(manifest[k]==config[k] for k in ('method_id','personalization_cap','replicate_id')))
        checks.add(label+'.settings_match_selection',config['extractor_settings']==selection['extraction_settings'] and packet['backend']['model']==selection['model'] and packet['backend']['reasoning']==selection['reasoning'])
        checks.add(label+'.backend_bound_to_source',manifest['extractor']=={
            'class':'OpenAIResponsesBackend','endpoint':'https://api.openai.com/v1/responses',
            'label':'openai-responses-overnight:'+packet['backend']['model'],'model':packet['backend']['model'],
            'enforced_settings':{'reasoning_effort':packet['backend']['reasoning'],'store':False,'tools':[],
                'service_tier':'default','temperature':'not_sent','prompt_cache_options':{'mode':'implicit','ttl':'30m'},
                'pricing_version':PRICING_VERSION,'adapter_implementation_sha256':digest(adapter_text)}})
        checks.add(label+'.backend_allocation',all(packet['backend'][k]==manifest['allocation'][k] for k in ('max_calls','max_seconds','max_usd')) and packet['backend']['timeout']==selection['extraction_timeout_seconds'])
        checks.add(label+'.no_retry_manifest',manifest['retry_policy']=={'max_attempts':1,'retry_uncertain':False})
        checks.add(label+'.fit_only_manifest',manifest['kind']=='build' and manifest['items_hash']==digest([]) and manifest['parent_job_ids']==[] and manifest['profile_hash'] is None)
        checks.add(label+'.exact_release_ref',packet['release']==cell['release'])
        checks.add(label+'.documents_hash',digest(docs)==manifest['documents_hash']==cell['documents_hash'])
        checks.add(label+'.source_manifest',sources==release['sources']['source_manifest']==config['allowed_sources'] and digest(sources)==manifest['source_manifest_hash']==config['allowed_source_manifest_hash']==cell['source_manifest_hash']==result['source_manifest_hash'])
        validate_documents(docs,config);checks.add(label+'.source_record_hashes_valid',True)
        checks.add(label+'.label_free_items',all(set(i)==ITEM_FIELDS for i in release['items']))
        checks.add(label+'.item_metadata',digest(release['items'])==release['items_sha256']==cell['items_sha256'] and release['target_bundle_sha256']==cell['target_bundle_sha256'] and [i['item_id'] for i in release['items']]==cell['ordered_item_ids'])
        checks.add(label+'.release_schema',release['schema_version']==cell['release_schema'] and release['researcher_id']==cell['researcher_id'])
        if cell['method']=='P7':
            checks.add(label+'.declared_peer_binding',all(config[k]==release[k] for k in ('approved_peer_sources','peer_policy','parent_releases')) and config['approved_peer_sources'] is True)
            parents=[inputs.get(p['release'],'approved_p7_parent_release') for p in release['parent_releases']]
            union={d['document_id']:d for p in parents for d in p['sources']['documents']}
            checks.add(label+'.exact_parent_document_union',docs==[union[k] for k in sorted(union)])
            target=next(p for p in parents if p['researcher_id']==cell['researcher_id'])
            checks.add(label+'.parent_target_preserved',all(release[k]==target[k] for k in ('items','items_sha256','target_bundle_sha256')))
        else:checks.add(label+'.ordinary_no_peer',not config.get('approved_peer_sources') and 'parent_releases' not in config)
        checks.add(label+'.terminal_status',result['status']==dispatch['status']==cell['dispatch_status'] and result['status'] in ('complete','invalid','empty','unavailable'))
        checks.add(label+'.receipt_result_exact_metadata',result['usage']==dispatch['usage'] and result['counts']==dispatch['counts'] and dispatch['result_path']==cell['result']['path'])
        checks.add(label+'.actual_backend_identity',result['actual_backend']==manifest['extractor'])
        checks.add(label+'.no_prediction_result',result['predictions']==[])
        profile=result.get('profile')
        if profile is not None:
            ProfileArtifact.from_dict(profile)
            checks.add(label+'.profile_binding',profile['code_sha']==RUNTIME and profile['documents_hash']==cell['documents_hash'] and profile['config']==config and profile['status']==result['status'])
            checks.add(label+'.profile_error_code',profile['error_code']==cell['error_code'])
        else:checks.add(label+'.profile_error_code_unknown',cell.get('error_code') is None)
        if 'profile' in cell:
            saved=inputs.get(cell['profile'],'indexed_complete_profile')
            checks.add(label+'.saved_profile_equal_result',saved==profile and saved['profile_id']==cell['profile_id'])
        checks.add(label+'.profile_ref_iff_complete',('profile' in cell)==(result['status']=='complete'))
        checks.add(label+'.recorded_attempt_limit',result['usage']['attempted_calls']<=manifest['allocation']['max_calls'] and result['usage']['attempted_calls']==result['counts']['attempted'])
        origin=origin_map.get(jid,'original_stopped_dispatch')
        if origin=='original_stopped_dispatch':
            old=old_coverage[jid]
            checks.add(label+'.original032_status_unchanged',old['original_dispatch_status']==result['status'] and old['result_sha256']==cell['result']['sha256'])
            if result['usage']['uncertain_attempts']:old_unknown.append(jid)
        elif origin=='target6_continuation':
            old=old_coverage[jid];checks.add(label+'.old_not_dispatched',old['original_dispatch_status']=='not_dispatched')
            receipts=[r for r in old['required_records'] if '/execution/' in r['path'] and r['path'].endswith('/receipt.json')]
            checks.add(label+'.single_old_receipt',len(receipts)==1)
            old_dispatch=inputs.get(receipts[0],'frozen032_original_non_dispatch_receipt')
            checks.add(label+'.original_receipt_not_dispatched',old_dispatch['status']=='not_dispatched' and old_dispatch['result_path'] is None)
        if jid in old_coverage:
            checks.add(label+'.original_packet_and_prepared_match032',all(ref['path'] in old_records and old_records[ref['path']]['sha256']==ref['sha256'] for ref in (cell['build_packet'],cell['original_prepared'])))
        checks.add(label+'.dispatch_origin',('/'+(OLD if origin=='original_stopped_dispatch' else TARGET6 if origin=='target6_continuation' else P7)+'/execution/') in cell['dispatch_receipt']['path'])
        usage=result['usage'];result_by_job[jid]=result
        rows.append({'cell_id':label,'job_id':jid,'method':cell['method'],'researcher_id':cell['researcher_id'],'cap':cell['cap'],
                     'evidence_policy':cell['evidence_policy'],'replicate_id':cell['replicate_id'],'origin':origin,'status':result['status'],
                     'error_code':cell.get('error_code'),'manifest_sha256':digest(manifest),'config_sha256':digest(config),
                     'documents_sha256':cell['documents_hash'],'source_manifest_sha256':cell['source_manifest_hash'],
                     'release_sha256':cell['release']['sha256'],'original_packet_sha256':cell['build_packet']['sha256'],
                     'result_sha256':cell['result']['sha256'],'profile_id':cell.get('profile_id'),
                     'profile_sha256':cell.get('profile',{}).get('sha256'),'parent_release_hashes':[p['release']['sha256'] for p in config.get('parent_releases',[])],
                     'usage':{'attempted_calls':usage['attempted_calls'],'input_tokens':usage['input_tokens'],'output_tokens':usage['output_tokens'],
                              'uncertain_attempts':usage['uncertain_attempts'],'known_estimate_nanos':nanos(usage['reported_api_usd']),
                              'retained_hold_nanos':nanos(usage['reserved_api_usd']),'cost_status':usage['cost_status']},
                     'selected_field_recorded_only':cell['selected'],'prediction_count_fields_not_audited':True})
    observed=summarize(rows)
    checks.add('counts.index_matches_results',observed['status_counts']==index['counts'])
    complete={r['job_id'] for r in rows if r['status']=='complete'}
    checks.add('counts.complete_profile_index_exact',len(index['profiles'])==len(complete)==index['complete_profiles'] and {p['job_id'] for p in index['profiles']}==complete)
    for p in index['profiles']:
        cell=next(c for c in index['cells'] if c['job_id']==p['job_id'])
        checks.add(p['job_id']+'.complete_projection',all(cell[k]==v for k,v in p.items()))
    new_ids=set(new_packets);old_dispatched={k for k,v in old_coverage.items() if v['original_dispatch_status']!='not_dispatched'}
    checks.add('continuation.disjoint_from_original_dispatched',not(new_ids&old_dispatched))
    checks.add('continuation.old_uncertain_not_rebound',not(set(old_unknown)&new_ids))
    old_not_dispatched={k for k,v in old_coverage.items() if v['original_dispatch_status']=='not_dispatched'}
    checks.add('continuation.target6_exact_original_undispatched',old_not_dispatched=={k for k,v in origin_map.items() if v=='target6_continuation'})
    for bid,b in batches.items():
        relevant=[r for r in rows if r['origin']==('original_stopped_dispatch' if bid==OLD else 'target6_continuation' if bid==TARGET6 else 'p7_continuation')]
        recorded=b['summary']['counts'];comp=Counter(r['status'] for r in relevant)
        checks.add(bid+'.result_counts',recorded['dispatched']==len(relevant) and recorded['complete']==comp['complete'] and recorded['other']==len(relevant)-comp['complete'])
    snapshot=inputs.get(rebind6['stopped_ledger_receipt'],'frozen_stopped_accounting_snapshot')
    policy=inputs.get(rebind6['new_ledger_policy'],'continuation_ledger_policy')
    auth=inputs.get(policy['continuation_authorization'],'frozen_continuation_authorization')
    old_policy=inputs.get(auth['predecessor_policy'],'frozen_predecessor_policy')
    checks.add('accounting.authoritative032_pins',all(ref['path'] in old_records and old_records[ref['path']]['sha256']==ref['sha256'] for ref in (rebind6['stopped_ledger_receipt'],policy['continuation_authorization'],auth['predecessor_policy'])))
    checks.add('accounting.authorization_runtime',auth['runtime_commit']==RUNTIME)
    checks.add('accounting.authorization_exact_snapshot',{k:v for k,v in auth['predecessor_snapshot'].items() if k!='logical_sha256'}==rebind6['stopped_ledger_receipt'] and auth['predecessor_snapshot']['logical_sha256']==snapshot['logical_snapshot_sha256'])
    reservations=snapshot['reservation_rows'];spent=sum(r[2] for r in reservations);held=sum(r[1] for r in reservations if r[3] in ('pending','uncertain'))
    checks.add('accounting.exact_unknown_reservations',[{'id':r[0],'reserved_nanos':r[1],'actual_known_nanos':r[2],'metadata':strict(r[4])} for r in reservations if r[3]=='uncertain']==auth['uncertain_reservations'])
    checks.add('accounting.snapshot_known_sum',spent==snapshot['known_spent_nanos']==auth['known_spent_nanos'])
    checks.add('accounting.snapshot_hold_sum',held==snapshot['retained_hold_nanos']==auth['retained_hold_nanos'])
    checks.add('accounting.snapshot_pending_uncertain',sum(r[3]=='pending' for r in reservations)==snapshot['pending']==0 and sum(r[3]=='uncertain' for r in reservations)==snapshot['uncertain'])
    checks.add('accounting.snapshot_attempt_count',len(reservations)==auth['predecessor_attempts'])
    policy_row=json.loads(snapshot['policy_rows'][0][1]);limit=policy_row['limit_nanos']-spent-held
    checks.add('accounting.predecessor_policy_limit',nanos(old_policy['ledger']['max_usd'])==policy_row['limit_nanos'])
    checks.add('accounting.holds_deducted_from_continuation',limit==auth['continuation_limit_nanos']==nanos(policy['ledger']['max_usd']))
    checks.add('accounting.hold_status_not_reset',auth['predecessor_status']=='stopped_with_uncertain_holds_not_closed' and policy['prior_phase_closure']['status']=='stopped_with_holds_not_closed')
    checks.add('accounting.unknown_cell_holds_match_snapshot',sum(result_by_job[j]['usage']['reserved_api_usd'] is None for j in old_unknown)==0 and sum(nanos(result_by_job[j]['usage']['reserved_api_usd']) for j in old_unknown)==held)
    old_build_known=sum(r['usage']['known_estimate_nanos'] for r in rows if r['origin']=='original_stopped_dispatch')
    side={};side_meta=[]
    for key,pin in SIDE_PINS.items():
        ref=registry[key];checks.add(key+'.approved_pin',ref['sha256']==pin)
        v=inputs.get(ref,'approved_side_job_summary');side[key]=v
        checks.add(key+'.source_terminal',v['runtime_commit']==RUNTIME and v['status']=='complete')
        entries=v.get('calls',v.get('requests'))
        checks.add(key+'.attempts_count',v['attempted_calls']==len(entries))
        if 'calls' in v:
            checks.add(key+'.backend_source',v['runtime_backend_sha256']==sha(adapter_text.encode()))
            checks.add(key+'.policy',v['policy_sha256']==(rebind6['new_ledger_policy']['sha256'] if key=='phase2_readiness_probe' else auth['predecessor_policy']['sha256']))
            for i,c in enumerate(entries):
                checks.add(key+'.call'+str(i)+'.metadata',c['status']=='complete' and c['settings_sha256']==digest(c['settings']) and c['cost']['reported_usage_complete'] is True and c['cost']['attempted_calls']==1)
            checks.add(key+'.usage_sum',sum(nanos(c['cost']['spent_usd']) for c in entries)==nanos(v['known_usage_usd']))
        else:
            for c in entries:
                receipt=inputs.get({'path':c['receipt_path'],'sha256':c['receipt_sha256']},'approved_side_embedding_usage_receipt')
                checks.add(c['request_id']+'.receipt_metadata',all(receipt[k]==c[k] for k in ('request_id','input_sha256','packet_sha256','response_sha256','known_usage_usd','usage','status')) and receipt['runtime_commit']==RUNTIME)
                matches=[r for r in reservations if all(strict(r[4]).get(k)==c[k] for k in ('request_id','input_sha256','packet_sha256'))]
                checks.add(c['request_id']+'.exact_snapshot_identity',len(matches)==1 and matches[0][2]==nanos(c['known_usage_usd']) and matches[0][3]=='complete')
            checks.add(key+'.usage_sum',sum(nanos(c['known_usage_usd']) for c in entries)==nanos(v['known_usage_usd']))
        side_meta.append({'kind':key,'summary_sha256':ref['sha256'],'attempts':v['attempted_calls'],'known_estimate_nanos':nanos(v['known_usage_usd']),
                          'reserved_nanos':nanos(v['reserved_usd']),'runtime_sha':v['runtime_commit'],'dispatch_sha256':v['dispatch_sha256'],
                          'request_binding':'exact_embedding_request_id_and_input_packet_hashes_to_stopped_rows' if 'requests' in v else 'saved_summary_model_settings_usage; canonical_provider_request_digest_not_reconstructed'})
    old_side_attempts=sum(side[k]['attempted_calls'] for k in ('phase2_access_probes','phase2_embedding_production'))
    old_side_nanos=sum(nanos(side[k]['known_usage_usd']) for k in ('phase2_access_probes','phase2_embedding_production'))
    checks.add('accounting.old_residual_reconciles_side_summaries',old_side_attempts==len(reservations)-sum(r['usage']['attempted_calls'] for r in rows if r['origin']=='original_stopped_dispatch') and old_side_nanos==spent-old_build_known)
    ledger_reports=[]
    for bid in (OLD,TARGET6,P7):
        led=batches[bid]['summary']['ledger']
        included=[r for r in rows if r['origin'] in (('original_stopped_dispatch',) if bid==OLD else ('target6_continuation',) if bid==TARGET6 else ('target6_continuation','p7_continuation'))]
        sid_attempts=old_side_attempts if bid==OLD else side['phase2_readiness_probe']['attempted_calls']
        sid_nanos=old_side_nanos if bid==OLD else nanos(side['phase2_readiness_probe']['known_usage_usd'])
        checks.add(bid+'.ledger_attempt_reconciliation',led['attempts']==sum(r['usage']['attempted_calls'] for r in included)+sid_attempts)
        checks.add(bid+'.ledger_known_reconciliation',nanos(led['spent_usd'])==sum(r['usage']['known_estimate_nanos'] for r in included)+sid_nanos)
        checks.add(bid+'.ledger_capacity_arithmetic',nanos(led['max_usd'])-nanos(led['spent_usd'])-nanos(led['reserved_usd'])==nanos(led['remaining_usd']))
        ledger_reports.append({'batch_id':bid,'recorded_attempts':led['attempts'],'recorded_known_nanos':nanos(led['spent_usd']),
                              'build_attempts':sum(r['usage']['attempted_calls'] for r in included),'side_job_attempts':sid_attempts,
                              'side_job_known_nanos':sid_nanos,'recorded_retained_nanos':nanos(led['reserved_usd']),'cost_basis':led['cost_basis']})
    accounting={'stopped_snapshot_attempts':len(reservations),'stopped_snapshot_status_counts':dict(Counter(r[3] for r in reservations)),
                'stopped_snapshot_known_nanos':spent,'stopped_snapshot_retained_nanos':held,'continuation_limit_nanos':limit,
                'original78_build_known_nanos':old_build_known,'snapshot_known_nanos_outside_original78_builds':spent-old_build_known,
                'snapshot_attempts_outside_original78_builds':len(reservations)-sum(r['usage']['attempted_calls'] for r in rows if r['origin']=='original_stopped_dispatch'),
                'unknown_job_ids':old_unknown,'uncertain_reservation_metadata':auth['uncertain_reservations'],
                'side_jobs_outside_96_cells':side_meta,'saved_ledger_summary_reconciliation':ledger_reports,
                'continuation_global_remaining_balance':'not_audited_active_ledger_not_read'}
    inputs.finish();verify_source();checks.add('inputs.unchanged_before_after',True);checks.add('source.unchanged_before_after',True)
    report={'schema_version':'phase2-coverage35-metadata-v1','runtime_sha':RUNTIME,'reader_sha256':sha(Path(__file__).read_bytes()),
            'integrity':{'passed':len(checks.rows),'failed':0,'checks':checks.rows},'source_files_verified':len(source['files']),
            'observed':observed,'cells':rows,'rebinds':rebind_reports,'accounting':accounting,
            'limits':['No prediction scoring or private labels were read; initial prediction and selected fields are not evidence of extraction quality or new independent measurements.',
                      'Status and usage are saved record values, not independent provider/network/invoice verification.',
                      'No retry is supported within these 96 cells by disjoint original/continuation job IDs, unchanged consumed unknown outcomes and recorded single-attempt manifests/results; absence of unreleased requests is not proven.',
                      'Side-job summary accounting reconciles the saved ledger totals. Neutral probe canonical provider request digests were not reconstructed; their dispatch hashes are retained but no unreferenced sibling files were guessed.',
                      'Past absence assertions in rebind evidence are retained as recorded; current filesystem absence is not inferred after later completion.',
                      'Active SQLite and continuation-wide spending were not read. Source/config/parent hashes and record lineage are verified, not source semantics, profile quality or researcher fidelity.']}
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    (out/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    inventory=inputs.inventory(entry);(out/'input-inventory.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+'\n')
    (out/'source-reference.json').write_text(json.dumps(source,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'checks_passed':len(checks.rows),'inputs':len(inventory['files']),'cells':len(rows),'status_counts':observed['status_counts'],'source_files':len(source['files'])}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs');p.add_argument('--index');p.add_argument('--target6-rebind');p.add_argument('--retention32');p.add_argument('--registry');p.add_argument('--source-root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    if not a.inputs and not all([a.index,a.target6_rebind,a.retention32,a.registry]):p.error('Provide frozen --inputs or all four entry-point paths')
    run(a)
