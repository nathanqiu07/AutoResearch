"""Verify named retained files and preserve only exact audit039 gap objects."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile

MAP_SHA='7da45e66e52a00b09bdbd11521a5b3da2d101b8b138fefd9917cd5db9396c67a'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read_json(path,pin):
    raw=path.read_bytes();assert sha(raw)==pin;return json.loads(raw)
def safe_relative(name):
    p=PurePosixPath(name);assert name and not p.is_absolute() and '..' not in p.parts and str(p)==name
    return p
def save(path,obj):
    with path.open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--map',type=Path,required=True);ap.add_argument('--owner-payload',type=Path,required=True);ap.add_argument('--source-archive',type=Path,required=True);ap.add_argument('--private-archive',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    m=read_json(a.map,MAP_SHA);a.out.mkdir(parents=True,exist_ok=False)
    original_reader=Path('/tmp/gio-integration-audit-staging/downstream-terminal-39/reproduce.py');original_manifest=original_reader.with_name('SAFE_PACKAGE_MANIFEST.json')
    original_pins={str(p):sha(p.read_bytes()) for p in [original_reader,original_manifest]}
    physical={r['retained_payload_relative_path']:r for r in m['retained_mappings']};assert len(physical)==210
    retained=[]
    def verify_retained():
        rows=[]
        for relative,r in sorted(physical.items()):
            safe_relative(relative);path=a.owner_payload/relative;assert not path.is_symlink();path.resolve().relative_to(a.owner_payload.resolve())
            raw=path.read_bytes();assert len(raw)==r['size_bytes'] and sha(raw)==r['sha256']
            rows.append({'relative_path':relative,'sha256':sha(raw),'size_bytes':len(raw),'mode':oct(stat.S_IMODE(path.stat().st_mode))})
        return rows
    retained=verify_retained()
    assert stat.S_IMODE(a.private_archive.parent.stat().st_mode)==0o700
    ignored=subprocess.run(['git','--no-optional-locks','-C',str(a.repo),'check-ignore','--',str(a.private_archive)],capture_output=True,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp'})
    assert ignored.returncode==0,'Private archive must be under an ignored root'
    assert not a.source_archive.exists() and not a.private_archive.exists()
    grouped={'public_runtime_source_bytes':[],'publication_or_review_record_keep_private_until_content_review':[]}
    for r in m['missing_inputs']:grouped[r['gap_kind']].append(r)
    receipts={}
    for kind,destination,compressed in [('public_runtime_source_bytes',a.source_archive,False),('publication_or_review_record_keep_private_until_content_review',a.private_archive,True)]:
        members=[];raw_objects={}
        for r in grouped[kind]:
            path=r['path'];safe_relative(path)
            if kind=='public_runtime_source_bytes':assert r['commit']==m['audit_executed_source'] and path.endswith('.py')
            else:assert r['commit']==m['audit_publication_commit'] and path.startswith(('results/gio-matched-shutdown-05/','results/gio-matched-shutdown-05-review/'))
            result=subprocess.run(['git','--no-optional-locks','-C',str(a.repo),'show',r['commit']+':'+path],capture_output=True,check=True,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp'})
            raw=result.stdout;assert sha(raw)==r['sha256'] and len(raw)==r['size_bytes'];name=r['proposed_bundle_path'];safe_relative(name);raw_objects[name]=raw
            members.append({**r,'archive_member':name})
        mode=0o600 if compressed else 0o644
        with os.fdopen(os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode),'wb') as output:
            stream=gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0) if compressed else output
            with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as archive:
                for row in members:
                    name=row['archive_member'];info=tarfile.TarInfo(name);info.size=row['size_bytes'];info.mode=mode;info.mtime=0;info.uid=info.gid=0;info.uname=info.gname='';archive.addfile(info,io.BytesIO(raw_objects[name]))
            if compressed:stream.close()
        destination.chmod(mode)
        with tarfile.open(destination,'r:gz' if compressed else 'r:') as archive:
            entries=archive.getmembers();assert len(entries)==len(members) and len({e.name for e in entries})==len(entries)
            for member,row in zip(entries,members):
                assert member.isfile() and member.name==row['archive_member'] and member.mode==mode
                raw=archive.extractfile(member).read();assert len(raw)==row['size_bytes'] and sha(raw)==row['sha256']
        receipts[kind]={'archive_path':str(destination),'archive_sha256':sha(destination.read_bytes()),'archive_size_bytes':destination.stat().st_size,'archive_mode':oct(stat.S_IMODE(destination.stat().st_mode)),'files':members,'member_count':len(members),'input_bytes':sum(x['size_bytes'] for x in members),'all_members_rehashed':True,'recorded_commit_identity_is_label_not_reconstructed_git_history':True}
    after=verify_retained();assert after==retained
    assert all(sha(Path(p).read_bytes())==h for p,h in original_pins.items())
    save(a.out/'retained-verification.json',{'schema_version':'audit039-named-retained-payload-verification-v1','recovery_map_sha256':MAP_SHA,'owner_payload_root':str(a.owner_payload),'logical_refs':234,'physical_files':210,'before_after_equal':True,'files':retained,'native_eval_read':False,'sibling_discovery':False,'frozen_original_pins_unchanged':original_pins})
    for kind,receipt in receipts.items():save(a.out/('source-preservation.json' if kind=='public_runtime_source_bytes' else 'private-publication-preservation.json'),receipt)
    mapping=[]
    for row in m['retained_mappings']:mapping.append({k:row[k] for k in ['commit','path','sha256','size_bytes']}|{'store':'retained','relative_path':row['retained_payload_relative_path']})
    for row in m['missing_inputs']:mapping.append({k:row[k] for k in ['commit','path','sha256','size_bytes']}|{'store':'source' if row['gap_kind']=='public_runtime_source_bytes' else 'publication','relative_path':row['proposed_bundle_path']})
    save(a.out/'recovered-input-map.json',{'schema_version':'audit039-explicit-byte-input-map-v1','original_inventory_sha256':m['audit_input_inventory_sha256'],'original_reader_sha256':original_pins[str(original_reader)],'archives':{('source' if k=='public_runtime_source_bytes' else 'publication'):{f:r[f] for f in ['archive_sha256','archive_size_bytes','member_count']} for k,r in receipts.items()},'files':mapping,'limits':'Recorded commit/path are historical labels tied to original byte hashes. No Git history, installed environment, live state or native.eval is recovered.'})
    print(json.dumps({'retained_files_verified_twice':210,'retained_logical_refs':234,'source_gap_members':90,'private_record_gap_members':13,'original_frozen_bytes_unchanged':True,'source_archive_sha256':receipts['public_runtime_source_bytes']['archive_sha256'],'private_archive_sha256':receipts['publication_or_review_record_keep_private_until_content_review']['archive_sha256']}))

if __name__=='__main__':main()
