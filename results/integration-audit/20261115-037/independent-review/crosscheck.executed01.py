"""Independent bounded audit037 metadata checks; no runtime imports or trace reads."""
import argparse
import ast
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import stat
import tarfile

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v): return sha(canonical(v).encode())

def main():
    a=argparse.ArgumentParser();a.add_argument('--stage',type=Path,required=True);a.add_argument('--publication',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    checks=[];reads={}
    def check(name,value):
        checks.append({'name':name,'passed':bool(value)})
        if not value: raise AssertionError(name)
    def raw(p,pin=None):
        b=p.read_bytes();reads[str(p)]=sha(b)
        if pin: check('pin:'+p.name,sha(b)==pin)
        return b
    def load(p,pin=None):return json.loads(raw(p,pin))
    s,p=a.stage,a.publication
    manifest=load(s/'safe-manifest.json','3804c6fb9eb69327f10f43d8046fd9531089a3e9187c33d0f9a51afa2f6aa1d1')
    check('43_safe_distinct_paths',manifest['file_count']==len(manifest['files'])==len({r['path'] for r in manifest['files']})==43)
    for entry in manifest['files']:
        f=Path(entry['path']);check('safe_path:'+str(f),not f.is_absolute() and '..' not in f.parts and 'private-replay' not in f.parts)
        b=raw(s/f,entry['sha256']);check('safe_size:'+str(f),len(b)==entry['bytes']);check('published_original_unchanged:'+str(f),raw(p/f)==b)
    reader=raw(s/'read_full_sparse.py','e1ec83f0c13656475fe8aacce965fb79c31ff2a951f46584941b09a3fdf45bd9')
    report=load(s/'final/report.json','92b999c0faa5f660d91687679fa7c8e0c3727f33cc3f34666989c9eaa26b1f09')
    inventory=load(s/'final/input-inventory.json','68ae471746c090ba58f7fd7824113b3803806571d1bb2e43a59be04daf35b068')
    prior33=load(s/'prior033-report.json');prior34=load(s/'prior034-report.json');prior35=load(s/'prior035-report.json')
    check('saved6336checks',len(report['checks'])==6336 and all(r['verified'] for r in report['checks']) and report['check_counts']=={'verified':6336,'failed':0})
    index_ref=[r for r in inventory['files'] if r['sha256']=='9aeea5b0c4fb9668df1d36c548e681c1c5e180e75df74f9475f75b2f08737e3a']
    check('one_pinned_index',len(index_ref)==1)
    index=load(Path(index_ref[0]['path']),index_ref[0]['sha256'])
    jobs={j['job_id']:j for j in index['jobs']}
    check('612unique_jobs',len(jobs)==len(index['jobs'])==612)
    check('six_categories',Counter((j['kind'],j['category']) for j in jobs.values())=={('build','search'):96,('predict','search'):48,('build','control'):178,('predict','control'):178,('build','hybrid'):56,('predict','hybrid'):56})
    personalized={j for j,v in jobs.items() if (v['kind'],v['category'])==('predict','search')}
    oldcontrols={j['job_id'] for j in prior34['jobs']}
    check('282predict_330build',Counter(j['kind'] for j in jobs.values())=={'predict':282,'build':330})
    check('exact_disjoint034_jobs',oldcontrols=={j for j,v in jobs.items() if v['kind']=='predict' and v['category']!='search'} and not oldcontrols&personalized)
    rows=report['rows'];by_key={(r['job_id'],r['item_sha256']):r for r in rows}
    check('672rows_48jobs_14each',len(rows)==len(by_key)==672 and Counter(r['job_id'] for r in rows)=={j:14 for j in personalized})
    check('364old_rows_unique',len(prior34['rows'])==len({(r['job_id'],r['item_sha256']) for r in prior34['rows']})==364)
    check('1036_index_prediction_rows',sum(len(j['item_ids']) for j in jobs.values() if j['kind']=='predict')==672+364==1036)
    check('same28ordered_items',len({r['item_sha256'] for r in rows})==28 and {r['item_sha256'] for r in rows}=={r['item_sha256'] for r in prior34['rows']})
    oldcells={c['cell_id']:c for c in prior35['cells']};current={c['cell_id']:c for c in index['core_cells']}
    check('96planned035cells',len(current)==len(index['core_cells'])==96 and set(current)==set(oldcells))
    check('exact_outcomes',Counter(c['build_status'] for c in current.values())=={'complete':48,'invalid':39,'empty':7,'unavailable':2})
    for cid,c in current.items():
        old=oldcells[cid]
        check('old_cell_binding:'+cid,c['build_job_id']==old['job_id'] and c['build_status']==old['status'] and jobs[c['build_job_id']]['result']['sha256']==old['result_sha256'])
        check('delivered_or_absent:'+cid,len(c['prediction_job_ids'])==(1 if c['build_status']=='complete' else 0))
    check('planned1344_delivered672_absent672',96*14==1344 and 48*14==len(rows)==index['counts']['core_absent_rows']==672)
    aliases=prior33['aliases'];alias_keys={(r['canonical_job_id'],r['item_sha256']) for r in aliases}
    check('84memoryreferences28subsetrows',len(aliases)==84 and len(alias_keys)==28 and alias_keys<=set(by_key))
    for x in aliases:
        r=by_key[(x['canonical_job_id'],x['item_sha256'])]
        check('033row_binding',r['result_row_sha256']==x['canonical_result_row_sha256'] and r['verified_hashes']==x['verified_hashes'] and r['started_trace_sha256']==x['started_trace_sha256'] and r['completed_trace_sha256']==x['completed_trace_sha256'])
    check('112controls56canonicalrows',len(prior34['sparse_aliases'])==112 and len({(r['canonical_job_id'],r['item_id_sha256']) for r in prior34['sparse_aliases']})==56)
    check('aliases_nonadditive',all(index['alias_accounting'][x]['additional_calls']==index['alias_accounting'][x]['additional_independent_observations']==0 for x in ['memory','controls']))
    known=sum(Decimal(str(j['usage']['reported_api_usd'])) for j in jobs.values());held=sum(Decimal(str(j['usage']['reserved_api_usd'])) for j in jobs.values());attempts=sum(j['usage']['attempted_calls'] for j in jobs.values())
    check('known_held_once_per_job',known==Decimal('0.266053750') and held==Decimal('0.019078625') and known+held==Decimal('0.285132375') and attempts==1132)
    check('96extraction1036prediction_attempts',sum(j['usage']['attempted_calls'] for j in jobs.values() if j['kind']=='build')==96 and sum(j['usage']['attempted_calls'] for j in jobs.values() if j['kind']=='predict')==1036)
    check('two_uncertain_jobs',sum(j['usage']['uncertain_attempts'] for j in jobs.values())==2 and sum(j['usage']['input_tokens'] is None for j in jobs.values())==sum(j['usage']['output_tokens'] is None for j in jobs.values())==2)
    check('034cost_partition',sum(Decimal(str(jobs[j]['usage']['reported_api_usd'])) for j in oldcontrols)==Decimal(prior34['summary']['canonical_reported_usd'])==Decimal('0.057470000'))
    binding_keys=('prompt','system','settings','backend_identity','timeout')
    bindings=Counter(digest({k:r['verified_hashes'][k] for k in binding_keys}) for r in rows)
    eq=report['personalized_request_equivalence']
    check('672exact_request_groups',len(bindings)==672 and set(bindings.values())=={1} and eq['distinct_effective_request_groups']==672 and eq['group_size_histogram']=={'1':672})
    check('groups_match_independent_keys',Counter({g['request_equivalence_sha256']:g['group_size'] for g in eq['groups']})==bindings and all(set(g['binding_hashes'])==set(binding_keys) and len(g['recorded_executions'])==g['group_size'] for g in eq['groups']))
    # Execute only the audit-owned pure grouping function; no runtime/main imports.
    fn=next(n for n in ast.parse(reader).body if isinstance(n,ast.FunctionDef) and n.name=='group_request_equivalence')
    ns={'json':json,'hashlib':hashlib};exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned_grouping_function','exec'),ns)
    first=json.loads(json.dumps(rows[0]));second=json.loads(json.dumps(first))
    for k in ('job_id','cell_id','method','cap','evidence_policy','item_id_sha256','item_sha256','option_order_id_sha256'): second[k]='synthetic-distinct-metadata'
    grouped=ns['group_request_equivalence']([first,second]);check('synthetic_metadata_does_not_split',len(grouped)==1 and next(iter(grouped.values()))['group_size']==2)
    second['verified_hashes']['prompt']='0'*64;check('synthetic_prompt_change_splits',len(ns['group_request_equivalence']([first,second]))==2)
    source=load(s/'SOURCE_REFERENCE.json');code={}
    with tarfile.open(s/'source-f6cd4fb5.tar','r:') as archive:
        files=[m for m in archive.getmembers() if m.isfile()]
        check('92source_members',len(files)==len({m.name for m in files})==len(source['files'])==92 and {m.name for m in files}==set(source['files']))
        for m in files:
            b=archive.extractfile(m).read();check('source_member:'+m.name,sha(b)==source['files'][m.name]);code[m.name]=b
    runner=code['autoresearch/taste/overnight/runner.py'].decode();derivations=report['trace_path_derivation']['jobs']
    check('trace_source_identity',report['trace_path_derivation']['source_sha256']==sha(code['autoresearch/taste/overnight/runner.py']) and 'out = Path(output_root) / manifest["job_id"]' in runner and '"%04d-started.json" % self.attempts' in runner and '"%04d-complete.json" % self.attempts' in runner)
    inv_by_path={x['path']:x for x in inventory['files']}
    for d in derivations:
        anchor=Path(d['anchor_result']['path']);check('trace_anchor:'+d['job_id'],anchor.name=='result.json' and anchor.parent.name==d['job_id'] and jobs[d['job_id']]['result']==d['anchor_result'] and d['attempts']==14)
        for n in range(14):
            for side,suffix in [(0,'started'),(1,'complete')]:
                path=str(anchor.parent/'traces'/('%04d-%s.json'%(n+1,suffix)))
                check('derived_trace_inventory_binding',inv_by_path[path]['sha256']==d['ordered_result_trace_hashes'][2*n+side])
    check('2222inventoryfiles',len(inventory['files'])==len(inv_by_path)==2222 and sum(r['size_bytes'] for r in inventory['files'])==37661894)
    receipt=load(p/'private-preservation.json','a507a9c9fb169155d6d2f3bdd685bb081cd41ebc8bff5bb5fcfc34b26c713771')
    check('receipt_exact_inputs',len(receipt['files'])==2222 and {(r['path'],r['sha256'],r['size_bytes']) for r in receipt['files']}=={(r['path'],r['sha256'],r['size_bytes']) for r in inventory['files']})
    archive=Path(receipt['archive_path']);b=raw(archive,'e5bff245a1dc5da80650fce47347876d9ad213e74ef3f53d305850ebaa23ec9d')
    check('private_archive_size_mode',len(b)==receipt['archive_bytes']==7359490 and stat.S_IMODE(archive.stat().st_mode)==0o600 and stat.S_IMODE(archive.parent.stat().st_mode)==0o700)
    # Inspect private archive headers only, not raw member contents.
    with tarfile.open(archive,'r:gz') as t:
        members=t.getmembers();check('private_archive_headers',len(members)==2222 and len({m.name for m in members})==2222 and all(m.isfile() and m.mode==0o600 and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members))
        check('archive_member_receipt',[(m.name,m.size) for m in members]==[(r['archive_member'],r['size_bytes']) for r in receipt['files']])
    for folder in ['private-replay-verification','root-replay']:
        replay=load(p/folder/'report.json');check('replay_inventory_exact:'+folder,raw(p/folder/'input-inventory.json')==raw(s/'final/input-inventory.json'))
        check('replay_multiset:'+folder,Counter(map(canonical,report['checks']))==Counter(map(canonical,replay['checks'])))
        moved=[(x,y) for x,y in zip(report['checks'],replay['checks']) if x!=y]
        check('only_known_family_moved:'+folder,len(report['checks'])==len(replay['checks']) and all(x['name'].startswith('034_row_and_trace_hash_overlap:') and y['name'].startswith('034_row_and_trace_hash_overlap:') for x,y in moved))
        check('every_other_report_field_exact:'+folder,{k:v for k,v in report.items() if k not in ('argv','checks')}=={k:v for k,v in replay.items() if k not in ('argv','checks')})
    check('all_read_bytes_unchanged',all(sha(Path(k).read_bytes())==v for k,v in reads.items()))
    with a.out.open('x') as f:json.dump({'schema_version':'audit037-independent-bounded-check-v1','passed':len(checks),'failed':0,'checks':checks,'read_file_sha256':reads,'private_json_records_read':1,'private_trace_records_read':0,'private_archive_members_read_as_content':0,'runtime_code_imported':False,'full_reader_rerun':False,'provider_calls':0},f,indent=2);f.write('\n')
    print(json.dumps({'passed':len(checks),'failed':0}))

if __name__=='__main__':main()
