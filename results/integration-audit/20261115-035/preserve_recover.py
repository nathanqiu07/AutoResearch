#!/usr/bin/env python3
"""Preserve exact pinned inputs, or restore them without reading original paths."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile


def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def strict(data):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('Duplicate JSON key')
            out[key]=value
        return out
    return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def pinned(path,expected,size=None):
    data=Path(path).read_bytes()
    if sha(data)!=expected or (size is not None and len(data)!=size):raise ValueError('Pinned input mismatch: '+str(path))
    return data

def exclusive(path,data,mode=0o600):
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())

def validate_inventory(inventory):
    rows=inventory['files'];identities=[r['path'] for r in rows]
    if len(set(identities))!=len(identities):raise ValueError('Duplicate input identity')
    if sha(canonical({r['path']:r['sha256'] for r in rows}))!=inventory['input_set_sha256']:raise ValueError('Input set digest mismatch')
    for row in rows:
        if Path(row['path']).suffix in ('.sqlite','.sqlite3','.db') or Path(row['path']).name=='.env':raise ValueError('Forbidden input')
    return rows

def preserve(args):
    archive=Path(args.archive);receipt=Path(args.receipt)
    if archive.exists() or receipt.exists():raise FileExistsError('Destination already exists')
    if archive.parent.stat().st_mode&0o777!=0o700:raise ValueError('Private archive directory must be 0700')
    inventory_bytes=pinned(args.inventory,args.inventory_sha256);inventory=strict(inventory_bytes);rows=validate_inventory(inventory)
    reader=pinned(args.reader,args.reader_sha256);source=pinned(args.source_archive,args.source_sha256)
    payloads=[];members=[]
    for index,row in enumerate(rows):
        data=pinned(row['read_path'],row['sha256'],row['bytes'])
        payloads.append(data);members.append({'member':'inputs/%04d.json'%index,'path':row['path'],'sha256':row['sha256'],'bytes':row['bytes']})
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w',format=tarfile.PAX_FORMAT) as tar:
        for member,data in zip(members,payloads):
            info=tarfile.TarInfo(member['member']);info.size=len(data);info.mode=0o600;info.mtime=0;info.uid=0;info.gid=0
            tar.addfile(info,io.BytesIO(data))
    archive_bytes=gzip.compress(raw.getvalue(),mtime=0)
    # Build from cached hash-verified bytes, then recheck every original before publication.
    for row in rows:pinned(row['read_path'],row['sha256'],row['bytes'])
    pinned(args.inventory,args.inventory_sha256);pinned(args.reader,args.reader_sha256);pinned(args.source_archive,args.source_sha256)
    exclusive(archive,archive_bytes)
    # A post-write mismatch stops receipt publication; the created archive still contains pinned bytes.
    for row in rows:pinned(row['read_path'],row['sha256'],row['bytes'])
    record={'schema_version':'audit035-private-preservation-v1','archive_basename':archive.name,'archive_sha256':sha(archive_bytes),'archive_bytes':len(archive_bytes),
            'archive_members':len(members),'input_count':len(rows),'input_bytes':sum(r['bytes'] for r in rows),'members':members,'inventory':inventory,
            'input_inventory_sha256':sha(inventory_bytes),'reader_sha256':sha(reader),'source_archive_sha256':sha(source),'preserver_sha256':sha(Path(__file__).read_bytes()),
            'before_after_original_checks':True,'archive_mode':'0600','archive_directory_mode':'0700','original_input_paths_used_by_preservation':True,
            'overlap_limit':'Full recovery copy, not 500 new observations; prior032 overlap is recorded separately.','missing_inputs':[]}
    exclusive(receipt,json.dumps(record,indent=2,sort_keys=True).encode()+b'\n')
    print(json.dumps({'input_count':len(rows),'members':len(members),'archive_sha256':record['archive_sha256'],'receipt_sha256':sha(receipt.read_bytes())}))

def extract(args):
    out=Path(args.out)
    if out.exists():raise FileExistsError('Extraction destination already exists')
    receipt_bytes=pinned(args.receipt,args.receipt_sha256);receipt=strict(receipt_bytes);inventory=receipt['inventory'];rows=validate_inventory(inventory)
    members=receipt['members'];expected={m['member']:m for m in members}
    if len(expected)!=len(members) or len(rows)!=len(members) or len(rows)!=receipt['input_count'] or len(rows)!=receipt['archive_members']:raise ValueError('Member count mismatch')
    by_identity={m['path']:m for m in members}
    if len(by_identity)!=len(members) or set(by_identity)!={r['path'] for r in rows}:raise ValueError('Member identity mismatch')
    for row in rows:
        m=by_identity[row['path']]
        if m['sha256']!=row['sha256'] or m['bytes']!=row['bytes']:raise ValueError('Member pin mismatch')
    archive_bytes=pinned(args.archive,receipt['archive_sha256'],receipt['archive_bytes']);payloads={}
    with tarfile.open(fileobj=io.BytesIO(archive_bytes),mode='r:gz') as tar:
        actual=tar.getmembers()
        if len(actual)!=len(expected) or {m.name for m in actual}!=set(expected):raise ValueError('Archive membership mismatch')
        for member in actual:
            parts=PurePosixPath(member.name)
            if not member.isfile() or parts.is_absolute() or '..' in parts.parts or str(parts)!=member.name:raise ValueError('Unsafe member')
            data=tar.extractfile(member).read();pin=expected[member.name]
            if sha(data)!=pin['sha256'] or len(data)!=pin['bytes']:raise ValueError('Archive member mismatch')
            payloads[member.name]=data
    # Validate all archive bytes before writing anything. No original read_path is opened.
    out.mkdir(mode=0o700)
    for name,data in payloads.items():
        path=out/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);exclusive(path,data)
    restored=json.loads(json.dumps(inventory))
    for row in restored['files']:row['read_path']=str((out/by_identity[row['path']]['member']).absolute())
    exclusive(out/'input-inventory.json',json.dumps(restored,indent=2,sort_keys=True).encode()+b'\n')
    for row in restored['files']:pinned(row['read_path'],row['sha256'],row['bytes'])
    pinned(args.archive,receipt['archive_sha256'],receipt['archive_bytes']);pinned(args.receipt,args.receipt_sha256)
    report={'schema_version':'audit035-private-extraction-v1','archive_sha256':receipt['archive_sha256'],'receipt_sha256':args.receipt_sha256,
            'input_count':len(rows),'member_count':len(members),'input_set_sha256':inventory['input_set_sha256'],'input_identity_set_unchanged':True,
            'entry_points_unchanged':restored['entry_points']==inventory['entry_points'],'only_read_paths_remapped':all({k:v for k,v in a.items() if k!='read_path'}=={k:v for k,v in b.items() if k!='read_path'} for a,b in zip(rows,restored['files'])),
            'original_input_paths_opened':False,'archive_and_receipt_unchanged_after':True,'extractor_sha256':sha(Path(__file__).read_bytes())}
    exclusive(out/'extraction-report.json',json.dumps(report,indent=2,sort_keys=True).encode()+b'\n')
    print(json.dumps(report,sort_keys=True))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('preserve')
    for name in ('inventory','inventory-sha256','reader','reader-sha256','source-archive','source-sha256','archive','receipt'):a.add_argument('--'+name,required=True)
    b=sub.add_parser('extract')
    for name in ('archive','receipt','receipt-sha256','out'):b.add_argument('--'+name,required=True)
    args=p.parse_args();(preserve if args.command=='preserve' else extract)(args)
if __name__=='__main__':main()
