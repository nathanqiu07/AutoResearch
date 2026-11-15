#!/usr/bin/env python3
"""Build explicit source-byte routes for audits001–036, without raw data access."""
import argparse,copy,hashlib,json,tarfile
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def run(a):
 root=Path(a.root);stage=Path(a.stage);old=json.loads((stage/'map-01/coverage.json').read_text());new=json.loads((stage/'retained/source-manifest.json').read_text());catalog=old['catalog'];groups=copy.deepcopy(old['source_scopes']);inputs={}
 def read(path):
  p=root/path;b=p.read_bytes();inputs[path]={'sha256':sha(b),'bytes':len(b)};check=json.loads((root/path.split('/')[0]/'checksums.json').read_text());assert check['/'.join(path.split('/')[1:])]==sha(b);return json.loads(b)
 def append_group(audit,evidence,commit,refs,role):groups.append({'audit':audit,'evidence':evidence,'json_pointer':'/files or source-reference','context':{'source_commit':commit},'code_refs':refs,'role':role})
 for n in (21,26):
  name='20261115-%03d/private-preservation.json'%n;receipt=read(name);bycommit={}
  for r in receipt['files']:
   if r.get('path','').endswith('.py'):bycommit.setdefault(r.get('full_commit',r.get('commit')),{})[r['path']]=r['sha256']
  for commit,refs in bycommit.items():append_group('%03d'%n,name,commit,refs,'source_bytes_read_or_compared_by_standalone_reader; private archive indexing already verified in prior audits')
 # Explicit cross-package source references; do not infer runtime from an audit CODE_VERSION.
 for audit,dep,evidence in [('014','013','20261115-014/source-references.json'),('014','016','20261115-014/source-references.json'),('019','017','20261115-019/source-reference.json'),('025','022','20261115-025/SOURCE_PINS.json'),('029','022','20261115-029/README.md')]:
  if evidence.endswith('.json'):read(evidence)
  for g in old['source_scopes']:
   if g['audit']==dep:append_group(audit,evidence,g['context'].get('source_commit'),g['code_refs'],'explicit_public_source_dependency_audit'+dep)
 receipt=read('20261115-032/private-preservation.json')
 for s in receipt['sources']:append_group('032','20261115-032/private-preservation.json',s['commit'],{p:h for p,h in s['files'].items() if p.endswith('.py')},'retained_source_snapshots_in_terminal_private_archive; reader itself is standalone')
 named=json.loads((stage/'named-test-dependencies.json').read_text())
 for r in named:append_group('001','20261115-001/confidence/run-01/capture.json',r['commit'],{r['path']:r['sha256']},'named_test_bytes_derived_now_from_recorded_clean_commit')
 # Source-adjacent prompt files are load-bearing in native downstream setup.
 for audit,snapshot,archive in [('020','SOURCE_SNAPSHOT.json','source.tar'),('022','SOURCE_F0AC0EA.json','source-f0ac0ea.tar')]:
  source=read('20261115-'+audit+'/'+snapshot);archivepath='20261115-'+audit+'/'+archive;archivepin=sha((root/archivepath).read_bytes())
  refs={p:h for p,h in source['files'].items() if p.endswith('.txt')}
  with tarfile.open(root/archivepath) as t:
   for p,h in refs.items():assert sha(t.extractfile(p).read())==h;catalog.setdefault(h,[]).append({'kind':'public_archive_member','archive':archivepath,'archive_sha256':archivepin,'member':p})
  append_group(audit,'20261115-'+audit+'/'+snapshot,source['source_commit'],refs,'source_adjacent_prompt_text; no real source corpus')
 new_by_hash={r['sha256']:r for r in new['files']};aliases={(r['recorded_commit'],r['recorded_path']):r for r in new['aliases']}
 edges={}
 for g in groups:
  commit=g['context'].get('source_commit',g['context'].get('commit'))
  for path,pin in g['code_refs'].items():
   key=(g['audit'],commit,path,pin)
   if key not in edges:
    prior=catalog.get(pin,[]);public=[r for r in prior if r['kind'].startswith('public')];alias=aliases.get((commit,path))
    if alias:route={'kind':'new_retained_content_alias','archive':'retained/selected-code.tar.gz','archive_sha256':new['archive_sha256'],'member':alias['resolve_from']['archive_member'],'provenance_limit':alias['status']}
    elif public:route=public[0]
    elif prior:route=prior[0]
    elif pin in new_by_hash:route={'kind':'new_selected_code_archive_member','archive':'retained/selected-code.tar.gz','archive_sha256':new['archive_sha256'],'member':new_by_hash[pin]['archive_member'],'provenance':new_by_hash[pin]['provenance']}
    else:route={'kind':'unresolved'}
    edges[key]={'audit':g['audit'],'commit':commit,'logical_source_path':path,'sha256':pin,'recovery_route':route,'evidence':[]}
   edges[key]['evidence'].append({'path':g['evidence'],'pointer':g['json_pointer'],'role':g.get('role','recorded_source_hash_map')})
 modes={18:'standalone metadata reader; recorded runtime0dcd reference is not a loaded-source attestation',24:'standalone metadata reader plus retained public base-reader helper',31:'standalone metadata reader; raw inputs reuse audit024 archive',36:'standalone checkpoint/copier/verifier; retained public evidence archive dependencies described in036 metadata'}
 audits=[]
 for n in range(1,37):
  audit='%03d'%n;selected=[r for r in edges.values() if r['audit']==audit];counts={kind:sum(r['recovery_route']['kind']==kind for r in selected) for kind in sorted({r['recovery_route']['kind'] for r in selected})}
  audits.append({'audit':audit,'mode':modes.get(n,'pinned source bytes, imported or compared as documented'),'source_identity_edges':len(selected),'route_counts':counts,'all_mapped_edges_have_routes':all(r['recovery_route']['kind']!='unresolved' for r in selected),'direct_public_python_files_retained':sum(1 for p in (root/('20261115-'+audit)).rglob('*.py')),'scope_limit':'Coverage is of recorded source maps, explicit code dependencies and named commands; no full historical environment/import trace reconstruction.'})
 report=read('20261115-035/dispatch-binding/final/report.json');unresolved=[]
 for r in report['records']:
  pin=r['recorded_script_sha256'];assert pin not in catalog and pin not in new_by_hash
  unresolved.append({'audit':'035','kind':r['kind']+'_probe_script','sha256':pin,'source_path':None,'immutable_commit_path_binding':None,'recorded_runtime_commit':report.get('runtime_sha','f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'),'recorded_dispatch_raw_sha256':r['dispatch_raw_sha256'],'dispatch_canonical_sha256':r['dispatch_canonical_sha256'],'evidence':'20261115-035/dispatch-binding/final/report.json','status':'hash_only_reference_no_matching_retained_code_or_approved_path','limit':'The recorded runtime commit does not establish the location or commit membership of the separately hashed script.'})
 payload={'schema_version':'audit038-source-recovery-map-v1','audits':audits,'source_edges':list(edges.values()),'new_retained_files':30,'original_missing_candidate_refs':30,'additional_named_test_dependency':1,'content_aliases':new['aliases'],'unresolved_metadata_only_scripts':unresolved,'additional_metadata_inputs':inputs,'prior_map_sha256':sha((stage/'map-01/coverage.json').read_bytes()),'new_manifest_sha256':sha((stage/'retained/source-manifest.json').read_bytes()),'limits':['No claim of full replay of old audits, installed Python/package recovery, provider availability, authenticated calls, or data retention beyond existing receipts.','Source maps may include unused files; static import classification is a conservative upper bound.','Private source archive routes rely on previously verified retention metadata; no raw private archive was reread here.','Historical generic full-suite logs do not supply a complete loaded-code/environment attestation. Exact named missing dependencies are addressed; exhaustive historical test discovery is not reconstructed.','Probe script inputs remain unresolved; no private tree was scanned or guessed script path followed.']}
 (stage/'source-recovery-map.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
 print('audit source_edges route_counts')
 for r in audits:print(r['audit'],r['source_identity_edges'],r['route_counts'])
 print('unresolved_mapped_edges',sum(r['recovery_route']['kind']=='unresolved' for r in edges.values()),'separate_hash_only_scripts',len(unresolved))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--stage',required=True);run(p.parse_args())
