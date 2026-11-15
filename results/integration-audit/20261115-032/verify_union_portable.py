#!/usr/bin/env python3
"""Verify retained metadata/source bytes from archives only; never reads originals."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile


def sha(b):return hashlib.sha256(b).hexdigest()
def check(x,label):
    if not x:raise ValueError(label)
def load_tar(data):
    blobs={}
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as tf:
        for m in tf.getmembers():
            p=PurePosixPath(m.name)
            check(m.isfile() and not p.is_absolute() and '..' not in p.parts and m.name not in blobs,'Unsafe/duplicate archive member')
            blobs[m.name]=tf.extractfile(m).read()
    return blobs


def main(a):
    raw=Path(a.receipt).read_bytes();check(sha(raw)==a.receipt_sha256,'Preservation receipt pin mismatch');receipt=json.loads(raw)
    archive_root=Path(a.archive_root);audit_root=Path(a.audit_root)
    archives={};observed=[]
    for dep in receipt['dependencies']:
        path=audit_root/'results/integration-audit'/('20261115-'+dep['audit'])/'private-preservation.json'
        dr=path.read_bytes();check(sha(dr)==dep['receipt_sha256'],'Dependency receipt pin mismatch')
        dd=json.loads(dr);path=archive_root/Path(dep['archive_path']).name;data=path.read_bytes()
        check(sha(data)==dep['archive_sha256']==dd['archive_sha256'],'Dependency archive pin mismatch')
        blobs=load_tar(data);rows={r.get('archive_member',r.get('member')):r for r in dd['files']}
        check(set(blobs)==set(rows),'Dependency inventory membership mismatch')
        for name,b in blobs.items():
            row=rows[name];check(sha(b)==row['sha256'] and len(b)==row.get('bytes',row.get('size_bytes')),'Dependency member bytes mismatch')
        archives[('existing_archive',dep['audit'])]=blobs
        observed.append({'kind':'dependency','audit':dep['audit'],'archive_sha256':sha(data),'members_verified':len(blobs)})
    for new in receipt['new_archives']:
        path=archive_root/Path(new['archive_path']).name;data=path.read_bytes()
        check(sha(data)==new['sha256'],'New archive pin mismatch');blobs=load_tar(data)
        check(set(blobs)==set(new['members']),'New archive inventory mismatch')
        for name,b in blobs.items():check(sha(b)==new['members'][name],'New member hash mismatch')
        check(stat.S_IMODE(path.stat().st_mode)==0o600,'New archive mode is not 0600')
        archives[('new_archive',new['archive_group'])]=blobs
        observed.append({'kind':'new','group':new['archive_group'],'archive_sha256':sha(data),'members_verified':len(blobs)})
    def get(row):
        kind=row['storage'];key=row['dependency_audit'] if kind=='existing_archive' else row['archive_group']
        data=archives[(kind,key)][row['archive_member']]
        check(sha(data)==row['sha256'] and len(data)==row['size_bytes'],'Required record hash/size mismatch')
        return data
    bypath={}
    for row in receipt['required_records']:
        get(row);bypath.setdefault(row['path'],[]).append(row)
    def named(path):
        rows=bypath.get(path,[]);check(bool(rows),'Required path not recoverable')
        values={get(r) for r in rows};check(len(values)==1,'Ambiguous preserved path versions')
        return json.loads(next(iter(values)))
    source_counts=[]
    for source in receipt['sources']:
        data=archives[('new_archive',source['archive_group'])][source['archive_member']]
        check(sha(data)==source['sha256'],'Source archive hash mismatch')
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            files={m.name:sha(tf.extractfile(m).read()) for m in tf.getmembers() if m.isfile()}
        check(files==source['files'],'Source tree hashes mismatch')
        source_counts.append({'commit':source['commit'],'files_verified':len(files),'sha256':sha(data)})
    index_rows=[row for row in receipt['required_records'] if 'phase1_terminal_index' in row['roles']]
    check(len(index_rows)==1,'Expected exactly one receipt-bound phase1 terminal index')
    idx=json.loads(get(index_rows[0]))
    indexed={j['job_id']:j for b in idx['batches'] for j in b['jobs']}
    phase1=[j for j in receipt['coverage'] if j['job_id'] in indexed]
    check(len(phase1)==len(indexed)==132,'Phase1 coverage count mismatch')
    for job in receipt['coverage']:
        for row in job['required_records']:get(row)
        check(not job['missing_record_refs'],'Job has unresolved required records')
        roles=Counter(role for row in receipt['required_records'] if row['path'] in {r['path'] for r in job['required_records']} for role in row['roles'])
        check(roles['prepared_job_packet']>=1 and roles['original_job_packet']>=1 and roles['original_dispatch_receipt']>=1,'Admission not fully recoverable')
        if job['original_dispatch_status']=='not_dispatched':
            check(job.get('continuation_outputs_excluded') is True,'Missing continuation separation')
            check(not any('/output/'+job['job_id']+'/' in r['path'] or r['path'].endswith('/lease/'+job['job_id']+'.json') for r in job['required_records']),'Continuation output included in stopped admission')
        else:
            check(roles['terminal_result']>=1 and roles['original_job_claim']>=1 and roles['output_manifest']>=1,'Execution record missing')
            result_rows=[r for r in job['required_records'] if r['path'].endswith('/output/'+job['job_id']+'/result.json')]
            check(len(result_rows)==1,'Missing/duplicate result reference');result=json.loads(get(result_rows[0]))
            check(result['job_id']==job['job_id'] and result['status']==job['original_dispatch_status'],'Terminal result mismatch')
            trace_hashes=[r['sha256'] for r in job['required_records'] if '/traces/' in r['path']]
            check(Counter(trace_hashes)==Counter(result['trace_hashes']),'Trace coverage mismatch')
    stopped=[j for j in receipt['coverage'] if j not in phase1]
    check(len(stopped)==84 and sum(j['original_dispatch_status']!='not_dispatched' for j in stopped)==78,'Stopped coverage mismatch')
    check(not receipt['missing_dependencies'],'Retention receipt records missing dependencies')
    summary={'schema_version':'terminal-preservation32-archive-union-verification-v1','receipt_sha256':sha(raw),
        'original_paths_read':False,'provider_or_model_calls':0,'archives':observed,'source_verification':source_counts,
        'required_record_refs_verified':len(receipt['required_records']), 'phase1_jobs_verified':len(phase1),
        'phase1_status_counts':dict(Counter(j['original_dispatch_status'] for j in phase1)),
        'phase1_recorded_job_attempts':sum(j.get('attempted_calls_recorded',0) for j in phase1),
        'stopped_original_admissions_verified':len(stopped),'stopped_dispatched_results_verified':78,
        'stopped_status_counts':dict(Counter(j['original_dispatch_status'] for j in stopped)),
        'stopped_unknown_jobs':[j['job_id'] for j in stopped if j.get('uncertain_attempts_recorded')],
        'all_missing_dependency_lists_empty':True,'all_required_records_recoverable_from_verified_archive_union':True,
        'limits':['Retention verification only, no source/content review or scoring.',
                  'Recorded accounting estimates and statuses are retained, not independently provider-verified.',
                  'Archives contain raw released inputs/outputs and must remain private.']}
    dest=Path(a.out);check(not dest.exists(),'Refusing to overwrite verification report')
    dest.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['archives','source_verification','limits','stopped_unknown_jobs']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--receipt-sha256',required=True)
    p.add_argument('--audit-root',required=True);p.add_argument('--archive-root',required=True);p.add_argument('--out',required=True);main(p.parse_args())
