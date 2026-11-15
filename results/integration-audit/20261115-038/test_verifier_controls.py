#!/usr/bin/env python3
"""Two deliberate metadata/archive corruption controls; never alter retained files."""
import argparse,copy,hashlib,json,subprocess,tempfile
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def run(a):
 s=Path(a.stage);reader=s/'verify_retention.py';manifest=s/'retained/source-manifest.json';archive=s/'retained/selected-code.tar.gz';coverage=s/'source-recovery-map.json';before={str(p):sha(p.read_bytes()) for p in (reader,manifest,archive,coverage)};results=[]
 with tempfile.TemporaryDirectory(prefix='audit038-control-') as temp:
  tmp=Path(temp)
  for name in ('archive_corruption','prior_public_source_hash_change'):
   ap=archive;mp=coverage
   if name=='archive_corruption':
    data=bytearray(archive.read_bytes());data[-1]^=1;ap=tmp/'corrupt-code.tar.gz';ap.write_bytes(data)
   else:
    obj=json.loads(coverage.read_text());row=next(r for r in obj['source_edges'] if r['recovery_route']['kind']=='public_archive_member');row['sha256']='0'*64;mp=tmp/'changed-map.json';mp.write_text(json.dumps(obj))
   cmd=['/usr/bin/python3','-I','-B',str(reader),'--audit-root',a.audit_root,'--archive',str(ap),'--manifest',str(manifest),'--manifest-sha256',sha(manifest.read_bytes()),'--coverage-map',str(mp),'--coverage-map-sha256',sha(mp.read_bytes()),'--out',str(tmp/(name+'.json'))]
   r=subprocess.run(cmd,capture_output=True,text=True);expected='input_sha256:' if name=='archive_corruption' else 'public_member_pin:';assert r.returncode!=0 and expected in r.stderr
   results.append({'control':name,'argv':cmd,'expected_failure_observed':True,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'changed_inputs_are_temporary_copies':True})
 assert all(sha(Path(p).read_bytes())==pin for p,pin in before.items())
 Path(a.out).write_text(json.dumps({'schema_version':'audit038-verifier-negative-controls-v1','controls':results,'retained_originals_unchanged':True,'control_count':len(results),'all_expected_failures_observed':True},indent=2)+'\n');print('2 deliberate corruptions rejected; retained originals unchanged')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--audit-root',required=True);p.add_argument('--stage',required=True);p.add_argument('--out',required=True);run(p.parse_args())
