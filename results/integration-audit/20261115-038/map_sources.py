#!/usr/bin/env python3
"""Source-retention inventory only. No imports, private archives or runtime calls."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import tarfile

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def code(path):return str(path).endswith(('.py','.sh'))
def run(a):
 root=Path(a.root);out=Path(a.out);out.mkdir(exist_ok=False);accessed={};catalog=defaultdict(list);groups=[];archive_index=[];metadata=[]
 def read(p):
  b=p.read_bytes();key=str(p.relative_to(root));accessed[key]={'sha256':sha(b),'bytes':len(b)};return b
 def add(pin,where):catalog[pin].append(where)
 for n in range(1,37):
  folder=root/('20261115-%03d'%n)
  if not folder.exists():continue
  check=json.loads(read(folder/'checksums.json'))
  for p in sorted(folder.rglob('*')):
   if not p.is_file():continue
   rel=str(p.relative_to(folder));loc=str(p.relative_to(root))
   if code(p.name):
    b=read(p);assert check[rel]==sha(b);add(sha(b),{'kind':'public_file','path':loc})
   elif p.name.endswith(('.tar','.tar.gz','.tgz')):
    b=read(p);assert check[rel]==sha(b);rows=[]
    with tarfile.open(p) as t:
     for m in t.getmembers():
      if m.isfile() and code(m.name):
       pin=sha(t.extractfile(m).read());row={'kind':'public_archive_member','archive':loc,'archive_sha256':sha(b),'member':m.name};add(pin,row);rows.append({'path':m.name,'sha256':pin})
    archive_index.append({'path':loc,'sha256':sha(b),'code_members':rows})
   if p.suffix=='.json' and (('SOURCE' in p.name or 'source-reference' in p.name or p.name=='source-verification.json') or (n<=5 and (p.name in ('main.json','pilot.json','baseline.json','pilot-profiles.json','baseline-profiles.json','main_derived.json','pilot_draft.json','capture.json','report.json')))):
    v=json.loads(read(p));assert check[rel]==accessed[loc]['sha256'];metadata.append((n,loc,v))
  for p in sorted(folder.rglob('*preservation*.json')):
   if p.name not in ('private-preservation.json','PRIVATE_PRESERVATION.json'):continue
   v=json.loads(read(p))
   if v.get('archive_sha256'):
    for r in v.get('files',[]):
     if isinstance(r,dict) and code(r.get('path','')) and r.get('archive_member'):
      add(r['sha256'],{'kind':'private_archive_indexed_member','receipt':str(p.relative_to(root)),'receipt_sha256':sha(p.read_bytes()),'archive_sha256':v['archive_sha256'],'archive_path':v.get('archive_path'),'member':r['archive_member'],'fresh_raw_member_reverification':False})
   for source in v.get('sources',[]):
    for path,pin in source.get('files',{}).items():
     if code(path):add(pin,{'kind':'private_nested_source_archive_indexed_member','receipt':str(p.relative_to(root)),'receipt_sha256':sha(p.read_bytes()),'archive_group':source['archive_group'],'source_archive_member':source['archive_member'],'source_archive_sha256':source['sha256'],'member':path,'fresh_raw_member_reverification':False})
 def walk(value,n,loc,pointer='',context=None):
  if isinstance(value,dict):
   context=dict(context or {})
   for k in ('source_commit','commit','full_commit','source_root','source_dirty_status','tracked_status','requested_path','resolved_path'):
    if k in value and isinstance(value[k],str):context[k]=value[k]
   for key,v in value.items():
    ismap=isinstance(v,dict) and any(code(k) for k in v) and all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in v.values())
    if key in ('files','source_file_hashes','sha256') and ismap:
     refs={path:pin for path,pin in v.items() if code(path)}
     groups.append({'audit':'%03d'%n,'evidence':loc,'json_pointer':pointer+'/'+key,'context':context,'code_refs':refs})
    else:walk(v,n,loc,pointer+'/'+key,context)
  elif isinstance(value,list):
   for i,v in enumerate(value):walk(v,n,loc,pointer+'/'+str(i),context)
 for n,loc,v in metadata:walk(v,n,loc)
 # Audit004 separately describes prepared runners versus executed runtime source.
 p=root/'20261115-004/evidence/report.json';v=json.loads(read(p))
 groups.append({'audit':'004','evidence':str(p.relative_to(root)),'json_pointer':'/runner_sources','context':{'source_commit':v['source_commit']},'code_refs':{'scripts/gio_petri/'+r['path'].split('/')[-1]:r['sha256'] for r in v['runner_sources'] if code(r['path'])}})
 groups.append({'audit':'004','evidence':str(p.relative_to(root)),'json_pointer':'/runtime_sources_at_code_version','context':{'source_commit':v['code_versions']['resolved_execution_commit']},'code_refs':{r['path']:r['sha256'] for r in v['runtime_sources_at_code_version'] if code(r['path'])}})
 # Deduplicate repeated source scopes while preserving all provenance pointers.
 uniq={}
 for g in groups:
  key=(g['audit'],g['context'].get('source_commit',g['context'].get('commit')),digest(g['code_refs']))
  if key not in uniq:uniq[key]=g;g['duplicate_evidence']=[]
  else:uniq[key]['duplicate_evidence'].append({'path':g['evidence'],'pointer':g['json_pointer']})
 rows=[]
 for g in uniq.values():
  resolved=[]
  for path,pin in g['code_refs'].items():
   locations=catalog.get(pin,[]);public=[x for x in locations if x['kind'].startswith('public')]
   resolved.append({'path':path,'sha256':pin,'category':'tests' if path.startswith('tests/') or '/test_' in path else 'runtime_or_driver','retention':'public_bytes_verified' if public else 'private_archive_indexed' if locations else 'not_found_in_examined_retained_sources','retained_locations':public[:3] if public else locations[:3]})
  g['resolved']=resolved;g['counts']={k:sum(r['retention']==k for r in resolved) for k in ('public_bytes_verified','private_archive_indexed','not_found_in_examined_retained_sources')};rows.append(g)
 for loc,rec in accessed.items():assert sha((root/loc).read_bytes())==rec['sha256']
 report={'schema_version':'audit038-source-retention-preliminary-v1','scope':'Published001-036 code files and source archives; published source-hash metadata; private source retention receipts only. No private raw archive opened.','source_scopes':rows,'public_source_archives':archive_index,'catalog_hash_count':len(catalog),'catalog':dict(catalog),'accessed_public_files':accessed,'limits':['A source-map may cover more files than actually imported; missing map members are candidates, not all load-bearing gaps.','Private retention is indexed evidence, not a new raw archive-member verification.','Commit/object availability and narrower importer needs are assessed in an additive review.','Data/environment/provider availability are not inferred from source byte retention.']}
 (out/'coverage.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 gaps={}
 for g in rows:
  for r in g['resolved']:
   if r['retention']=='not_found_in_examined_retained_sources':
    key=(g['context'].get('source_commit',g['context'].get('commit')),r['path'],r['sha256'])
    gaps.setdefault(key,{'commit':key[0],'path':key[1],'sha256':key[2],'category':r['category'],'references':[]})['references'].append({'audit':g['audit'],'evidence':g['evidence'],'pointer':g['json_pointer'],'source_root':g['context'].get('source_root',g['context'].get('resolved_path'))})
 (out/'candidate-missing-source-refs.json').write_text(json.dumps(list(gaps.values()),indent=2,sort_keys=True)+'\n')
 for g in rows:print(g['audit'],str(g['context'].get('source_commit',g['context'].get('commit')))[:12],len(g['code_refs']),g['counts'])
 print('candidate_refs',len(gaps),'distinct_code_hashes',len({r['sha256'] for r in gaps.values()}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);run(p.parse_args())
