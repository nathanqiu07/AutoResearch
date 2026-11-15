#!/usr/bin/env python3
"""Verify retained source bytes independently of the writer; Git checks optional.
--audit-root is the checkout containing results/integration-audit.
--git-repo-map is an optional JSON map from full commit to an explicitly supplied
repository location. No original repository or input path is opened implicitly.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import subprocess
import tarfile


def sha(b):return hashlib.sha256(b).hexdigest()
def strict(b):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate JSON key')
   d[k]=v
  return d
 return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def run(a):
 root=Path(a.audit_root)/'results/integration-audit';opened={};checks=[];route_cache={};tar_cache={};git_checks=[]
 def checked(name,ok):
  checks.append({'check':name,'passed':bool(ok)})
  if not ok:raise ValueError('Failed check: '+name)
 def read(path,pin):
  b=Path(path).read_bytes();checked('input_sha256:'+str(path),sha(b)==pin);opened[str(path)]=(b,pin);return b
 manifest_bytes=read(a.manifest,a.manifest_sha256);manifest=strict(manifest_bytes);map_bytes=read(a.coverage_map,a.coverage_map_sha256);coverage=strict(map_bytes)
 checked('map_manifest_link',coverage['new_manifest_sha256']==a.manifest_sha256)
 archive_bytes=read(a.archive,manifest['archive_sha256']);raw=gzip.decompress(archive_bytes);checked('uncompressed_tar_pin',sha(raw)==manifest['uncompressed_tar_sha256'])
 expected={r['archive_member']:r for r in manifest['files']};checked('unique_new_members',len(expected)==len(manifest['files'])==manifest['file_count'])
 payloads={}
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
  members=tar.getmembers();checked('exact_new_member_set',len(members)==len(expected) and {m.name for m in members}==set(expected));checked('deterministic_member_order',[m.name for m in members]==sorted(expected))
  for member in members:
   row=expected[member.name];parts=PurePosixPath(member.name);checked('safe_code_member:'+member.name,member.isfile() and not parts.is_absolute() and '..' not in parts.parts and member.name=='sources/'+row['commit']+'/'+row['path'] and row['path'].endswith('.py'))
   checked('canonical_tar_metadata:'+member.name,member.mtime==0 and member.uid==0 and member.gid==0 and member.mode==0o644)
   b=tar.extractfile(member).read();checked('new_member_pin:'+member.name,sha(b)==row['sha256'] and len(b)==row['bytes']);payloads[member.name]=b
 checked('source_byte_total',sum(len(b) for b in payloads.values())==manifest['source_bytes'])
 counts=Counter(r['provenance'] for r in manifest['files']);checked('provenance_counts',counts['historically_recorded_byte_hash_matches_immutable_git']==manifest['historically_hash_pinned_files'] and counts['derived_now_from_recorded_clean_commit_not_a_historical_per_file_pin']==manifest['derived_named_test_files'])
 for alias in manifest['aliases']:
  checked('alias_content_only:'+alias['recorded_path'],sha(payloads[alias['resolve_from']['archive_member']])==alias['recorded_sha256'] and alias['status']=='content_equivalence_alias_only_original_untracked_file_provenance_not_recovered')
 def relative(name):
  parts=PurePosixPath(name)
  if parts.is_absolute() or '..' in parts.parts:raise ValueError('Unsafe public source route')
  path=root/str(parts)
  if root.resolve() not in path.resolve().parents:raise ValueError('Public source route escapes audit root')
  return path
 def resolve(route,pin):
  kind=route['kind'];key=json.dumps([route,pin],sort_keys=True)
  if key in route_cache:return
  if kind=='public_file':b=read(relative(route['path']),pin);status='retained_public_bytes_verified'
  elif kind=='public_archive_member':
   archive=route['archive']
   if archive not in tar_cache:tar_cache[archive]=read(relative(archive),route['archive_sha256'])
   else:checked('consistent_public_archive_pin:'+archive,sha(tar_cache[archive])==route['archive_sha256'])
   with tarfile.open(fileobj=io.BytesIO(tar_cache[archive]),mode='r:*') as tar:
    member=tar.getmember(route['member']);checked('public_regular_member:'+archive+':'+route['member'],member.isfile());b=tar.extractfile(member).read()
   checked('public_member_pin:'+archive+':'+route['member'],sha(b)==pin);status='retained_public_bytes_verified'
  elif kind in ('new_selected_code_archive_member','new_retained_content_alias'):
   checked('new_archive_route_pin',route['archive_sha256']==manifest['archive_sha256']);checked('new_route_member_pin:'+route['member'],sha(payloads[route['member']])==pin);status='new_retained_bytes_verified'
  elif kind=='private_archive_indexed_member':
   receipt=strict(read(relative(route['receipt']),route['receipt_sha256']));checked('private_archive_receipt_pin',receipt['archive_sha256']==route['archive_sha256']);matches=[r for r in receipt['files'] if r.get('archive_member')==route['member'] and r['sha256']==pin];checked('private_receipt_member_identity',len(matches)==1);status='prior_private_retention_receipt_verified_raw_archive_not_read'
  else:raise ValueError('Unresolved or unsupported route kind: '+kind)
  route_cache[key]={'route':route,'sha256':pin,'status':status}
 for edge in coverage['source_edges']:resolve(edge['recovery_route'],edge['sha256'])
 checked('all_audits001_036_represented',{r['audit'] for r in coverage['audits']}=={'%03d'%n for n in range(1,37)})
 checked('unresolved_probe_hashes_separate',len(coverage['unresolved_metadata_only_scripts'])==2 and all(r['source_path'] is None and r['immutable_commit_path_binding'] is None for r in coverage['unresolved_metadata_only_scripts']))
 if a.git_repo_map:
  gitmap=strict(Path(a.git_repo_map).read_bytes());env={'PATH':'/usr/bin:/bin','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0','TMPDIR':'/tmp'}
  for row in manifest['files']:
   checked('explicit_git_mapping:'+row['commit'],row['commit'] in gitmap);argv=['git','--no-optional-locks','-C',gitmap[row['commit']],'cat-file','blob',row['commit']+':'+row['path']];r=subprocess.run(argv,capture_output=True,env=env)
   checked('git_object_bytes:'+row['commit']+':'+row['path'],r.returncode==0 and sha(r.stdout)==row['sha256']);git_checks.append({'argv':argv,'returncode':r.returncode,'sha256':sha(r.stdout),'stderr':r.stderr.decode(errors='replace')})
 for path,(b,pin) in opened.items():checked('input_unchanged:'+path,Path(path).read_bytes()==b)
 report={'schema_version':'audit038-source-retention-verification-v1','archive_sha256':manifest['archive_sha256'],'manifest_sha256':a.manifest_sha256,'coverage_map_sha256':a.coverage_map_sha256,'reader_sha256':sha(Path(__file__).read_bytes()),'new_members':len(expected),'source_bytes':manifest['source_bytes'],'mapped_source_edges':len(coverage['source_edges']),'unique_resolved_routes':len(route_cache),'route_status_counts':dict(Counter(r['status'] for r in route_cache.values())),'git_object_checks':git_checks,'git_verification':'explicit_repositories_checked' if a.git_repo_map else 'not_requested_retained_byte_recovery_does_not_require_original_git','checks_passed':len(checks),'checks_failed':0,'checks':checks,'resolved_routes':list(route_cache.values()),'private_raw_archives_opened':False,'original_worktree_source_files_opened':False,'model_calls':0,'limits':coverage['limits']}
 Path(a.out).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:report[k] for k in ('new_members','source_bytes','mapped_source_edges','unique_resolved_routes','route_status_counts','git_verification','checks_passed','checks_failed')}))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ('audit-root','archive','manifest','manifest-sha256','coverage-map','coverage-map-sha256','out'):p.add_argument('--'+name,required=True)
 p.add_argument('--git-repo-map');run(p.parse_args())
