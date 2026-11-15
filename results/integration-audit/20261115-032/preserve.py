#!/usr/bin/env python3
"""Bounded opaque private retention. No models, scoring, raw corpus traversal or SQLite.
Reads only released refs, exact source-defined sibling records, and pinned prior archives.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile

INDEX = {'path': '/private/tmp/gio-profile-20261115-coordinator/phase1-completion-index-v1.json', 'sha256': 'd0acaae53d84e6ee5540279b5dbe2a1d4dda423e5403bed525054aa6e3535bad'}
FINAL = {'path': '/private/tmp/gio-profile-20261115-coordinator/accounting/phase1-final-receipt.json', 'sha256': '4ca50af58323a420285f9e5e97168951df4daec549a75a9963e772f9c5cb4e9b'}
STOP = 'df4cbde2513374d37d42fc382fb38b5af057d5d0c6645dc36b3fb8d5f22e884a'
SEMANTIC = ('e8c73f6b98728756095e9e8869bb0bb2cb9544a8073ead081ee22e2e3b0d999a', 'c203c72ad2885dc8fd587f1a5ddf6b8df904f3415fa35d691594cfee90627db9')
SNAPSHOTS = [
 {'path': '/private/tmp/gio-profile-20261115-coordinator/accounting/phase2-continuation-authorization-v1.json', 'sha256': 'a9b150194ecff9a99ba86c7615fb00c3ee3eade5f684b99c4d8008ba95324e04'},
 {'path': '/private/tmp/gio-profile-20261115-coordinator/accounting/phase2-stopped-ledger-snapshot-v1.json', 'sha256': '498e22da3e68ed8a08fccc3d4d6bdf741103af87999f703442d74f06f83032e6'}]
DEPENDENCIES = {'024': '6124618a66e857923748313af7c976ef5e19510768151c60871d6e57a8075c48',
                '021': '9452e537f2daaba7dbb19209bfb7396c345c2b57b44c2dbcac4d1df60980431f',
                '019': '030a16073c7fdaff999cb27d4e0783ca276b0c58fb365a579bdae2ac8f46745a'}


def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(v): return sha(canonical(v))
def read_json(b): return json.loads(b)
def check(ok,message):
    if not ok: raise ValueError(message)


class Retention:
    def __init__(self,args):
        self.args=args; self.records={};self.new={};self.originals={};self.deps=[];self.by_path={};self.by_hash={};self.missing=[];self.coverage=[];self.sources=[]
        self.current_job=None;self.job_records={}
        self.root=Path(args.audit_repo)
        for audit,pin in DEPENDENCIES.items():
            path=self.root/'results/integration-audit'/('20261115-'+audit)/'private-preservation.json'
            raw=path.read_bytes();check(sha(raw)==pin,'Dependency receipt pin changed: '+audit)
            receipt=read_json(raw); archive=Path(receipt['archive_path']);data=archive.read_bytes()
            check(sha(data)==receipt['archive_sha256'],'Dependency archive pin changed: '+audit)
            expected={r.get('archive_member',r.get('member')):r for r in receipt['files']}
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as tf:
                names=[m.name for m in tf.getmembers() if m.isfile()]
                check(len(names)==len(set(names)) and set(names)==set(expected),'Dependency member inventory mismatch: '+audit)
                for member in tf.getmembers():
                    check(member.isfile(),'Unexpected dependency member kind')
                    raw_member=tf.extractfile(member).read();row=expected[member.name]
                    check(sha(raw_member)==row['sha256'],'Dependency member hash mismatch')
                    check(len(raw_member)==row.get('size_bytes',row.get('bytes')),'Dependency member size mismatch')
                    original=row.get('original_path',row.get('path'))
                    entry={'dependency_audit':audit,'archive_member':member.name,'sha256':sha(raw_member),'size_bytes':len(raw_member),'data':raw_member,'original_path':original}
                    self.by_path.setdefault(original,[]).append(entry);self.by_hash.setdefault(entry['sha256'],[]).append(entry)
            self.deps.append({'audit':audit,'receipt_path':str(path),'receipt_sha256':pin,'archive_path':str(archive),'archive_sha256':sha(data),'member_count':len(expected),'all_members_verified':True})

    def get(self,ref,group,role,*,allow_new=True):
        path=str(ref['path']);expected=ref.get('sha256');identity=(path,expected)
        if self.current_job:self.job_records.setdefault(self.current_job,set()).add(identity)
        check(Path(path).suffix not in ('.sqlite','.db','.sqlite3') and Path(path).name!='.env','Forbidden input path')
        if identity in self.records:
            row=self.records[identity]
            row['roles']=sorted(set(row['roles']+[role]));return row['data']
        candidates=[x for x in self.by_path.get(path,[]) if expected is None or x['sha256']==expected]
        if not candidates and expected is not None:candidates=self.by_hash.get(expected,[])
        if candidates:
            d=candidates[0];b=d['data'];row={'path':path,'sha256':d['sha256'],'size_bytes':len(b),'roles':[role],
                'storage':'existing_archive','dependency_audit':d['dependency_audit'],'archive_member':d['archive_member'],'data':b}
        else:
            if not allow_new:
                self.missing.append({'path':path,'expected_sha256':expected,'role':role,'reason':'Not covered by verified existing archive; new read outside selected terminal scope is not performed.'});return None
            try:b=Path(path).read_bytes()
            except FileNotFoundError:
                self.missing.append({'path':path,'expected_sha256':expected,'role':role,'reason':'Explicitly referenced or source-defined file missing.'});return None
            check(expected is None or sha(b)==expected,'Input pin mismatch: '+path)
            check(path not in self.originals or self.originals[path]==b,'Input changed during inventory: '+path)
            self.originals[path]=b
            row={'path':path,'sha256':sha(b),'size_bytes':len(b),'roles':[role], 'storage':'new_archive','archive_group':group,'data':b}
            # Use path-hash names, with original identity mapped in the public receipt.
            row['archive_member']='objects/'+sha(path.encode())+'/'+Path(path).name
            members=self.new.setdefault(group,{})
            check(row['archive_member'] not in members or members[row['archive_member']]==b,'Archive member byte conflict')
            members[row['archive_member']]=b
        check(expected is None or sha(b)==expected,'Input pin mismatch: '+path)
        self.records[identity]=row
        return b

    def obj(self,ref,group,role,**kwargs):
        b=self.get(ref,group,role,**kwargs)
        return None if b is None else read_json(b)

    def virtual(self,member,data,group,role):
        check(member not in self.new.setdefault(group,{}),'Virtual member collision')
        self.new[group][member]=data
        self.records[('virtual:'+member,sha(data))]={'path':'virtual:'+member,'sha256':sha(data),'size_bytes':len(data),'roles':[role],
            'storage':'new_archive','archive_group':group,'archive_member':member,'data':data}

    def source(self,commit,group):
        argv=['git','--no-optional-locks','-C',self.args.git_repo,'ls-tree','-r','--name-only',commit]
        names=subprocess.check_output(argv,text=True).splitlines()
        selected=[n for n in names if (n.startswith('autoresearch/') and n.endswith('.py')) or
                  (n.startswith('docs/overnight/gio-profile-20261115/control/') and n.endswith('.py')) or
                  n in ('pyproject.toml','requirements.txt','uv.lock','AGENTS.md')]
        check(bool(selected),'Missing source tree')
        argv=['git','--no-optional-locks','-C',self.args.git_repo,'archive','--format=tar',commit,'--',*selected]
        data=subprocess.check_output(argv)
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            files={m.name:sha(tf.extractfile(m).read()) for m in tf.getmembers() if m.isfile()}
        check(set(files)==set(selected),'Source archive membership mismatch')
        member='sources/'+commit+'.tar';self.virtual(member,data,group,'exact_git_source_archive')
        self.sources.append({'commit':commit,'archive_group':group,'archive_member':member,'sha256':sha(data),'file_count':len(files),'files':files,'git_archive_argv':argv})

    def batch(self,batch,index_jobs,group,allow_new):
        self.current_job=None
        before_count=len(self.missing)
        prepared=self.obj(batch['prepared'],group,'prepared_batch',allow_new=allow_new)
        if prepared is None:return
        bid=prepared['batch_id'];check(bid==batch['batch_id'],'Batch identity mismatch')
        preparation=Path(batch['prepared']['path']).parent
        original=self.obj({'path':str(preparation/'original-batch.json'),'sha256':prepared['original_batch_sha256']},group,'original_batch',allow_new=allow_new)
        self.get(prepared['contract'],group,'contract',allow_new=allow_new)
        for k in ('active_release_receipt','semantic_index'):
            if isinstance(prepared.get(k),dict) and 'path' in prepared[k]:self.get(prepared[k],group,k,allow_new=allow_new)
        summary_ref=batch.get('execution_summary') or {'path':str(preparation.parent/'execution/summary.json')}
        summary=self.obj(summary_ref,group,'terminal_execution_summary',allow_new=allow_new)
        if summary:
            check(summary['status'] in ('complete','stopped'),'Nonterminal batch')
            check(summary['batch_id']==bid,'Summary batch identity mismatch')
        execution=preparation.parent/'execution'
        admission=self.obj({'path':str(execution/'claim.json')},group,'batch_claim',allow_new=allow_new)
        packets=[];outcomes=[];jobrows={j['job_id']:j for j in index_jobs}
        common_records=list(self.records)
        for i,ref in enumerate(prepared['jobs']):
            self.current_job=None
            p=self.obj(ref,group,'prepared_job_packet',allow_new=allow_new)
            if p is None:continue
            jid=p['manifest']['job_id'];packets.append(jid)
            self.current_job=jid;self.job_records.setdefault(jid,set()).add((ref['path'],ref.get('sha256')))
            original_ref=original['jobs'][i] if original else None
            if original_ref:self.get({'path':str(Path(ref['path']).parent/'original-packet.json'),'sha256':original_ref['sha256']},group,'original_job_packet',allow_new=allow_new)
            for k in ('release','profile','semantic_bundle_file'):
                if isinstance(p.get(k),dict) and 'path' in p[k]:self.get(p[k],group,'prepared_'+k,allow_new=allow_new)
            receipt=self.obj({'path':str(execution/jid/'receipt.json')},group,'original_dispatch_receipt',allow_new=allow_new)
            if receipt is None:continue
            check(receipt['job_id']==jid and receipt['manifest_sha256']==digest(p['manifest']),'Dispatch manifest mismatch')
            status=receipt['status'];outcomes.append(status)
            jobcoverage={'batch_id':bid,'job_id':jid,'kind':p['manifest']['kind'],'method_id':p['manifest']['method_id'],
                         'manifest_sha256':digest(p['manifest']),'code_sha':p['manifest']['code_sha'],'original_dispatch_status':status,'required_records':[]}
            self.coverage.append(jobcoverage)
            if status=='not_dispatched':
                check(receipt.get('result_path') is None,'Undispatched admission has result pointer')
                jobcoverage['continuation_outputs_excluded']=True
                continue
            indexed=jobrows.get(jid)
            if indexed is None:
                self.missing.append({'job_id':jid,'role':'indexed_terminal_result','reason':'No released result reference for dispatched job.'});continue
            check(indexed['packet']['sha256']==ref['sha256'],'Index packet pin mismatch')
            result=self.obj(indexed['result'],group,'terminal_result',allow_new=allow_new)
            if result is None:continue
            check(result['job_id']==jid and result['manifest_hash']==digest(p['manifest']) and result['code_sha']==p['manifest']['code_sha'],'Result manifest/source mismatch')
            check(result['status']==status==indexed['status'],'Recorded job status mismatch')
            output=Path(indexed['result']['path']).parent
            manifest=self.obj({'path':str(output/'manifest.json')},group,'output_manifest',allow_new=allow_new)
            if manifest is not None:check(manifest==p['manifest'],'Output manifest mismatch')
            claim=self.obj({'path':str(Path(prepared['roots']['lease'])/(jid+'.json'))},group,'original_job_claim',allow_new=allow_new)
            if claim is not None:check(claim['manifest']==p['manifest'] and claim['lease']==p['lease'],'Job admission mismatch')
            if result.get('profile') is not None:
                profile=self.obj({'path':str(output/'profile.json')},group,'output_profile',allow_new=allow_new)
                if profile is not None:check(profile==result['profile'],'Output profile mismatch')
            hashes=result['trace_hashes'];check(len(hashes)%2==0,'Unexpected trace hash count')
            for attempt in range(len(hashes)//2):
                self.get({'path':str(output/'traces'/('%04d-started.json'%(attempt+1))),'sha256':hashes[2*attempt]},group,'call_started_trace',allow_new=allow_new)
                terminal_hash=hashes[2*attempt+1]
                # Exact two filenames from pinned runner; no directory traversal or guessed hash.
                paths=[str(output/'traces'/('%04d-%s.json'%(attempt+1,suffix))) for suffix in ('complete','failed')]
                existing=[path for path in paths if any(x['sha256']==terminal_hash for x in self.by_path.get(path,[]))]
                if not existing and allow_new:existing=[path for path in paths if Path(path).is_file()]
                if len(existing)!=1:
                    self.missing.append({'job_id':jid,'role':'call_terminal_trace','expected_sha256':terminal_hash,'candidate_paths':paths,'reason':'Exact terminal trace not uniquely resolvable from pinned hash and source-defined names.'})
                else:self.get({'path':existing[0],'sha256':terminal_hash},group,'call_terminal_trace',allow_new=allow_new)
            jobcoverage['result_sha256']=indexed['result']['sha256'];jobcoverage['trace_count']=len(hashes)
            jobcoverage['attempted_calls_recorded']=result['usage']['attempted_calls'];jobcoverage['uncertain_attempts_recorded']=result['usage'].get('uncertain_attempts')
        self.current_job=None
        if admission:check(admission['job_ids']==packets,'Batch admission job list mismatch')
        if summary:
            computed={'listed':len(packets),'dispatched':sum(x!='not_dispatched' for x in outcomes),'not_dispatched':outcomes.count('not_dispatched'),
                      'complete':outcomes.count('complete'),'other':sum(x not in ('complete','not_dispatched') for x in outcomes)}
            if len(self.missing)==before_count:check(computed==summary['counts'],'Batch terminal counts mismatch')
        return {'batch_id':bid,'terminal_status':summary['status'] if summary else None,'recorded_counts':summary['counts'] if summary else None,'missing_dependencies_added':len(self.missing)-before_count}

    def write(self):
        # Verify terminal inputs and every existing archive before writing any new archive.
        for p,b in self.originals.items():check(Path(p).read_bytes()==b,'Original changed before archive: '+p)
        for d in self.deps:check(sha(Path(d['archive_path']).read_bytes())==d['archive_sha256'],'Dependency archive changed')
        destination=Path(self.args.archive_dir);destination.mkdir(parents=True,exist_ok=True,mode=0o700)
        check(stat.S_IMODE(destination.stat().st_mode)==0o700,'Private directory must already be 0700')
        receipts=[]
        for group,members in self.new.items():
            path=destination/('terminal-'+group+'-20261115-v1.tar.gz')
            check(not path.exists(),'Refusing to overwrite existing archive')
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as out:
                with tarfile.open(fileobj=out,mode='w:gz',format=tarfile.PAX_FORMAT) as tf:
                    for name,b in sorted(members.items()):
                        info=tarfile.TarInfo(name);info.size=len(b);info.mode=0o600;info.mtime=0;tf.addfile(info,io.BytesIO(b))
                out.flush();os.fsync(out.fileno())
            data=path.read_bytes();verified={}
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tf:
                for member in tf.getmembers():
                    check(member.isfile() and member.name not in verified,'Invalid archive member')
                    b=tf.extractfile(member).read();check(b==members[member.name],'Archive byte mismatch');verified[member.name]=sha(b)
            check(set(verified)==set(members),'Archive membership mismatch')
            receipts.append({'archive_group':group,'archive_path':str(path),'sha256':sha(data),'bytes':len(data),'mode':oct(stat.S_IMODE(path.stat().st_mode)),
                'member_count':len(verified),'all_member_hashes_verified':True,'members':verified})
        for p,b in self.originals.items():check(Path(p).read_bytes()==b,'Original changed after archive: '+p)
        for d in self.deps:
            check(sha(Path(d['archive_path']).read_bytes())==d['archive_sha256'],'Dependency archive changed after archive')
            check(sha(Path(d['receipt_path']).read_bytes())==d['receipt_sha256'],'Dependency receipt changed')
        return receipts


def main(args):
    stage=Path(args.stage);stage.mkdir(parents=True,exist_ok=True)
    r=Retention(args)
    registry_raw=(Path(args.control_dir)/'JOB_REGISTRY.json').read_bytes();registry=read_json(registry_raw)
    peer_raw=(Path(args.control_dir)/'PEER_REQUESTS.md').read_bytes()
    r.virtual('coordination/JOB_REGISTRY.snapshot.json',registry_raw,'phase1-semantic','mutable_coordination_snapshot_not_frozen_runtime')
    r.virtual('coordination/PEER_REQUESTS.snapshot.md',peer_raw,'phase1-semantic','mutable_coordination_snapshot_not_frozen_runtime')
    check(registry['phase1_accounting']==FINAL,'Released final accounting reference changed')
    index=r.obj(INDEX,'phase1-semantic','phase1_terminal_index');final=r.obj(FINAL,'phase1-semantic','phase1_terminal_accounting')
    check(final['status']=='closed' and final['closure']['all_jobs_done'] is True and final['ledger']['pending']==0 and final['ledger']['uncertain']==0,'Phase1 not terminal')
    for key in ('original_pilot_index','control_index'):r.get(index[key],'phase1-semantic','prior_phase1_index')
    batches={b['batch_id']:b for b in registry['batches']}
    reports=[]
    for batch in index['batches']:
        bid=batch['batch_id'];b={**batch,**{k:v for k,v in batches.get(bid,{}).items() if k in ('execution_summary','status')}}
        reports.append(r.batch(b,batch['jobs'],'phase1-semantic',True))
    stopped=batches[STOP]
    check(stopped['status']=='stopped','Stopped batch is not stopped')
    check(stopped['prepared']['sha256']=='5d79f8f8a631c72e0ba8f1f38f3a3a961a39d513378e79673078a0141d1e091f','Stopped preparation pin mismatch')
    check(stopped['execution_summary']['sha256']=='8b1e6a782fa5fe1b564c2b14e7a6a62677f0d1ab862fb373f3d1346e6ea2f690','Stopped summary pin mismatch')
    jobs=[j for j in registry['jobs'] if j.get('batch_id')==STOP]
    reports.append(r.batch(stopped,jobs,'phase2-stopped-df4cbde',True))
    auth=r.obj(SNAPSHOTS[0],'phase2-stopped-df4cbde','continuation_authorization_snapshot_only')
    snapshot=r.obj(SNAPSHOTS[1],'phase2-stopped-df4cbde','stopped_accounting_snapshot')
    check(snapshot['pending']==0 and auth['predecessor_status']=='stopped_with_uncertain_holds_not_closed','Stopped ledger snapshot boundary mismatch')
    source_commits={j['code_sha'] for j in r.coverage}
    check(source_commits=={index['runtime_sha'],'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'},'Uncovered source commit')
    r.source(index['runtime_sha'],'phase1-semantic');r.source('f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca','phase2-stopped-df4cbde')
    # Receipt evidence is covered from existing or newly selected records. Do not follow unrelated output trees.
    for ref in final['evidence']:r.get(ref,'phase1-semantic','phase1_accounting_evidence',allow_new=False)
    for job in r.coverage:
        job['required_records']=[{k:v for k,v in r.records[key].items() if k not in ['data','roles']}
                                 for key in sorted(r.job_records.get(job['job_id'],set()),key=str) if key in r.records]
        job['missing_record_refs']=[{'path':key[0],'expected_sha256':key[1]} for key in sorted(r.job_records.get(job['job_id'],set()),key=str) if key not in r.records]
    public_records=[{k:v for k,v in row.items() if k!='data'} for row in r.records.values()]
    prelim={'schema_version':'terminal-preservation32-plan-v1','reader_sha256':sha(Path(__file__).read_bytes()),'created_at':datetime.now(timezone.utc).isoformat(),
            'dependencies':r.deps,'sources':r.sources,'batch_reports':reports,'coverage':r.coverage,'required_records':public_records,'missing_dependencies':r.missing,
            'coordination_snapshot_sha256':{'JOB_REGISTRY.json':sha(registry_raw),'PEER_REQUESTS.md':sha(peer_raw)},
            'phase1_accounting':{'recorded_jobs':sum(len(b['jobs']) for b in index['batches']),'recorded_calls':final['ledger']['attempts'],'status':final['status']},
            'stopped_accounting':{k:snapshot[k] for k in ('known_spent_nanos','retained_hold_nanos','pending','uncertain','logical_snapshot_sha256')},
            'limits':['Opaque preservation only; no model/content or scoring review.', 'No raw corpus tree, private evaluator labels, credential file, SQLite, active continuation output or API was read.',
                      'Mutable control snapshots provide pointer provenance, not frozen runtime or quiescence.', 'Phase1 completeness is the verified archive union, not only the new semantic archive.',
                      'Original stopped not-dispatched admissions do not include later continuation output, even where job IDs persist.']}
    (stage/'inventory-plan.json').write_text(json.dumps(prelim,indent=2,sort_keys=True)+'\n')
    if args.write:
        archives=r.write();prelim.update(new_archives=archives,all_new_originals_unchanged=True,all_existing_archives_unchanged=True,
                                       scoped_retention_complete=not r.missing)
        (stage/'private-preservation.json').write_text(json.dumps(prelim,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'required_records':len(public_records),'existing_archive_records':sum(x['storage']=='existing_archive' for x in public_records),
                      'new_archive_records':sum(x['storage']=='new_archive' for x in public_records),'missing_dependencies':len(r.missing),
                      'coverage_jobs':len(r.coverage),'batch_reports':reports,'write':args.write}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit-repo',required=True);p.add_argument('--git-repo',required=True);p.add_argument('--control-dir',required=True)
    p.add_argument('--stage',required=True);p.add_argument('--archive-dir',required=True);p.add_argument('--write',action='store_true');main(p.parse_args())
