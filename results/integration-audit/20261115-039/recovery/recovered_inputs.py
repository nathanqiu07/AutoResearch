"""Explicit recovered byte access, without Git or fallback path discovery."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def relative(name):
    p=PurePosixPath(name)
    require(isinstance(name,str) and bool(name) and not p.is_absolute() and '..' not in p.parts and str(p)==name and name!='.','Unsafe relative path')
    return p

class RecoveryInputs:
    def __init__(self,map_path,map_sha256,inventory_path,inventory_sha256,retained_root,source_archive,publication_archive):
        self.metadata_files={};self.physical_files={};self.accessed={};self.map_sha256=map_sha256
        def pinned(path,pin):
            path=Path(path);raw=path.read_bytes();require(sha(raw)==pin,'Metadata hash mismatch');self.metadata_files[str(path)]=(pin,len(raw));return json.loads(raw)
        mapping=pinned(map_path,map_sha256);inventory=pinned(inventory_path,inventory_sha256)
        require(mapping['original_inventory_sha256']==inventory_sha256,'Inventory identity mismatch')
        expected={(r['commit'],r['path']):r for r in inventory['files']}
        require(len(expected)==len(inventory['files']),'Duplicate inventory identity')
        self.records={};self.retained_root=Path(retained_root).resolve();self.members={};self.archives={}
        for row in mapping['files']:
            require(set(row)=={'commit','path','sha256','size_bytes','store','relative_path'},'Unexpected map fields')
            key=(row['commit'],row['path']);require(key in expected and key not in self.records,'Unexpected or duplicate mapped identity')
            require(all(row[k]==expected[key][k] for k in ('commit','path','sha256','size_bytes')),'Mapped identity/hash/size differs')
            require(row['store'] in {'retained','source','publication'},'Unknown recovered store');relative(row['relative_path']);self.records[key]=row
        require(set(self.records)==set(expected),'Missing mapped inputs')
        for store,path in [('source',Path(source_archive)),('publication',Path(publication_archive))]:
            info=mapping['archives'][store];raw=path.read_bytes();require(sha(raw)==info['archive_sha256'] and len(raw)==info['archive_size_bytes'],'Archive hash/size mismatch')
            self.physical_files[str(path)]=(sha(raw),len(raw));self.archives[store]={'path':str(path),'sha256':sha(raw),'size_bytes':len(raw)}
            needed={r['relative_path']:r for r in self.records.values() if r['store']==store}
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:*') as archive:
                members=archive.getmembers();require(len(members)==len({m.name for m in members})==len(needed)==info['member_count'],'Archive member count mismatch')
                require({m.name for m in members}==set(needed),'Unexpected or missing archive member')
                for member in members:
                    relative(member.name);require(member.isfile(),'Archive member is not regular');value=archive.extractfile(member).read();row=needed[member.name]
                    require(len(value)==row['size_bytes'] and sha(value)==row['sha256'],'Archive member hash/size mismatch');self.members[(store,member.name)]=value
        self.original_reader_sha256=mapping['original_reader_sha256']

    def read(self,commit,path):
        key=(commit,path);require(key in self.records,'Unmapped input; no fallback');row=self.records[key]
        if row['store']=='retained':
            file=self.retained_root/str(relative(row['relative_path']));require(not file.is_symlink(),'Symlink input rejected')
            resolved=file.resolve()
            try:resolved.relative_to(self.retained_root)
            except ValueError:raise ValueError('Recovered input escapes retained root') from None
            raw=file.read_bytes();self.physical_files[str(file)]=(row['sha256'],row['size_bytes'])
        else:raw=self.members[(row['store'],row['relative_path'])]
        require(len(raw)==row['size_bytes'] and sha(raw)==row['sha256'],'Recovered input hash/size mismatch')
        self.accessed[key]=row;return raw

    def finish(self):
        require(set(self.accessed)==set(self.records),'Some mapped inputs were not checked')
        for path,(pin,size) in dict(self.metadata_files,**self.physical_files).items():
            raw=Path(path).read_bytes();require(sha(raw)==pin and len(raw)==size,'Recovered bytes changed during replay')
        retained={r['relative_path'] for r in self.accessed.values() if r['store']=='retained'}
        return {'schema_version':'audit039-recovered-byte-execution-v1','input_method':'Explicit pinned recovered bytes; no Git, original temp-path fallback or repository reconstruction','input_map_sha256':self.map_sha256,'original_checking_reader_sha256':self.original_reader_sha256,'logical_inputs_verified':len(self.accessed),'retained_logical_refs':sum(r['store']=='retained' for r in self.accessed.values()),'retained_physical_files_verified':len(retained),'source_archive_members_verified':sum(r['store']=='source' for r in self.accessed.values()),'publication_archive_members_verified':sum(r['store']=='publication' for r in self.accessed.values()),'archives':self.archives,'before_after_hashes_verified':True,'recorded_commit_path_labels_are_not_recovered_git_provenance':True,'fallback_allowed':False,'owner_code_imported':False,'full_environment_recovered':False}
