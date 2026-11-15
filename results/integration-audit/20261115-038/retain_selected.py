#!/usr/bin/env python3
"""Retain only the explicit immutable code candidates authorized for audit038."""
import argparse,gzip,hashlib,io,json,subprocess,tarfile
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def main(a):
 availability=json.loads(Path(a.availability).read_text());named=json.loads(Path(a.named_tests).read_text());classified=json.loads(Path(a.classification).read_text());classes={(r['commit'],r['path']):r['load_bearing_classification'] for r in classified['classified_candidates']};selected=[]
 for row in availability['objects']:
  match=row['git_match']
  if match:selected.append({'commit':row['commit'],'path':row['path'],'sha256':row['sha256'],'repository':match['repository'],'provenance':'historically_recorded_byte_hash_matches_immutable_git','references':row['references'],'load_bearing':classes[(row['commit'],row['path'])]})
 for row in named:
  if not row['retained_locations']:
   assert row['returncode']==0
   selected.append({'commit':row['commit'],'path':row['path'],'sha256':row['sha256'],'repository':row['git_argv'][3],'provenance':'derived_now_from_recorded_clean_commit_not_a_historical_per_file_pin','references':[{'audit':row['audit'],'scope':row['scope'],'evidence':'20261115-001/confidence/run-01/capture.json','pointer':'/runs/draft/executions/existing_tests'}],'load_bearing':[{'priority':'explicit_named_historical_test_command'}]})
 assert len(selected)==30 and len({(r['commit'],r['path']) for r in selected})==30
 out=Path(a.out);out.mkdir(exist_ok=False);payloads=[];rows=[];env={'PATH':'/usr/bin:/bin','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0'}
 for row in sorted(selected,key=lambda r:(r['commit'],r['path'])):
  assert row['path'].endswith('.py') and not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
  argv=['git','--no-optional-locks','-C',row['repository'],'show',row['commit']+':'+row['path']];r=subprocess.run(argv,capture_output=True,env=env,check=True);assert sha(r.stdout)==row['sha256'];object_argv=['git','--no-optional-locks','-C',row['repository'],'rev-parse',row['commit']+':'+row['path']];blob=subprocess.check_output(object_argv,env=env,text=True).strip()
  member='sources/'+row['commit']+'/'+row['path'];rows.append(dict(row,archive_member=member,bytes=len(r.stdout),git_blob=blob,git_read_argv=argv,git_object_argv=object_argv));payloads.append(r.stdout)
 raw=io.BytesIO()
 with tarfile.open(fileobj=raw,mode='w',format=tarfile.PAX_FORMAT) as tar:
  for row,b in zip(rows,payloads):
   info=tarfile.TarInfo(row['archive_member']);info.size=len(b);info.mode=0o644;info.uid=0;info.gid=0;info.mtime=0;tar.addfile(info,io.BytesIO(b))
 encoded=gzip.compress(raw.getvalue(),compresslevel=9,mtime=0)
 with (out/'selected-code.tar.gz').open('xb') as f:f.write(encoded)
 alias=next(r for r in classified['classified_candidates'] if r['path'].endswith('viewer 2.py'))
 aliases=[{'recorded_commit':alias['commit'],'recorded_path':alias['path'],'recorded_sha256':alias['sha256'],'resolve_from':dict(alias['exact_byte_alias_source'],archive_member='sources/'+alias['commit']+'/'+alias['exact_byte_alias_source']['path']),'status':'content_equivalence_alias_only_original_untracked_file_provenance_not_recovered','evidence':alias['references']}]
 manifest={'schema_version':'audit038-selected-code-retention-v1','archive':'selected-code.tar.gz','archive_sha256':sha(encoded),'uncompressed_tar_sha256':sha(raw.getvalue()),'archive_bytes':len(encoded),'source_bytes':sum(r['bytes'] for r in rows),'file_count':len(rows),'historically_hash_pinned_files':29,'derived_named_test_files':1,'files':rows,'aliases':aliases,'archive_metadata':'mtime=0 uid=0 gid=0 normalized mode0644; code bytes exact; gzip mtime0','owner_worktree_files_read':False,'raw_data_or_labels_included':False,'full_old_audit_replay_performed':False,'environment_or_provider_recovery_claimed':False,'tool_sha256':sha(Path(__file__).read_bytes()),'input_pins':{str(p):sha(Path(p).read_bytes()) for p in (a.availability,a.named_tests,a.classification)}}
 (out/'source-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:manifest[k] for k in ('archive_sha256','archive_bytes','file_count','source_bytes','historically_hash_pinned_files','derived_named_test_files')}))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ('availability','named-tests','classification','out'):p.add_argument('--'+name,required=True)
 main(p.parse_args())
