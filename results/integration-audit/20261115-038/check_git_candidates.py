#!/usr/bin/env python3
"""Check only explicitly listed immutable code objects; never copy owner source."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def run(a):
 rows=json.loads(Path(a.candidates).read_text());cache={};results=[]
 for row in rows:
  repos=[]
  for ref in row['references']:
   root=ref.get('source_root')
   if root and root not in repos:repos.append(root)
  repos += [p for p in a.repo if p not in repos]
  attempts=[];found=None
  for repo in repos:
   key=(repo,row['commit'])
   if key not in cache:
    cmd=['git','--no-optional-locks','-C',repo,'cat-file','-e',row['commit']+'^{commit}'];r=subprocess.run(cmd,capture_output=True);cache[key]={'argv':cmd,'returncode':r.returncode}
   if cache[key]['returncode']:continue
   cmd=['git','--no-optional-locks','-C',repo,'show',row['commit']+':'+row['path']];r=subprocess.run(cmd,capture_output=True);pin=hashlib.sha256(r.stdout).hexdigest() if not r.returncode else None
   item={'argv':cmd,'returncode':r.returncode,'sha256':pin,'matches_recorded_hash':pin==row['sha256']};attempts.append(item)
   if pin==row['sha256']:
    found={'repository':repo,'commit':row['commit'],'path':row['path'],'sha256':pin,'bytes':len(r.stdout),'status':'exact_git_object_available_now_not_yet_retained_in_examined_audit_bytes'};break
  results.append(dict(row,git_attempts=attempts,git_match=found))
 report={'schema_version':'audit038-explicit-code-object-check-v1','candidates_file_sha256':hashlib.sha256(Path(a.candidates).read_bytes()).hexdigest(),'source_bytes_saved':False,'objects':results,'commit_lookup_attempts':list(cache.values())}
 Path(a.out).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'candidate_refs':len(results),'exact_git_objects':sum(r['git_match'] is not None for r in results),'unmatched':[{'commit':r['commit'],'path':r['path']} for r in results if r['git_match'] is None]}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidates',required=True);p.add_argument('--repo',action='append',default=[]);p.add_argument('--out',required=True);run(p.parse_args())
