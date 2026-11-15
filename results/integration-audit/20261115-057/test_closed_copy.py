"""Synthetic files only. Never reads production control or payload paths."""
import copy
import hashlib
import gzip
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest import mock
import closed_copy as c


def digest(b):
    return hashlib.sha256(b).hexdigest()


def encoded(x):
    return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()


class CopierTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name).resolve()
        self.root.chmod(0o700)
        self.src=self.root/'inputs';self.src.mkdir(mode=0o700)
        self.ctl=self.root/'metadata';self.ctl.mkdir(mode=0o700)
        self.dest=self.root/'retained'
        self.rows=[]
        for name,data,roles in [('a.bin',b'opaque\x00\xff',['one','two']),('b.bin',b'opaque\x00\xff',['alias']),('c.bin',b'other',['third'])]:
            p=self.src/name;p.write_bytes(data)
            self.rows.append(dict(path=str(p),sha256=digest(data),roles=roles,logical_size_bytes_observed=len(data)))
        self.excluded=[dict(path=str(self.src/'excluded-never-exists'),sha256='f'*64,roles=['hold'],logical_size_bytes_observed=19,reason='synthetic hold')]
        self.build()

    def tearDown(self):self.tmp.cleanup()

    def build(self):
        self.docs={};refs={}
        def save(role,obj):
            raw=encoded(obj);p=self.ctl/(role+'.json');p.write_bytes(raw);p.chmod(0o600)
            self.docs[role]=obj;refs[role]=dict(path=str(p),sha256=digest(raw))
        allrows=self.rows+[{k:v for k,v in x.items() if k!='reason'} for x in self.excluded]
        save('metadata_pins',dict(schema_version='scaling-ownswap-retention-metadata-pins-v1',ignored_reference={'path':'/unfollowed/nonexistent','sha256':'0'*64}))
        save('gaps',dict(schema_version='scaling-ownswap-retention-gaps-v1',gaps=[]))
        save('retention_map',dict(schema_version='scaling-ownswap-first-order-retention-map-v1',pins_sha256=refs['metadata_pins']['sha256'],inputs=[dict(path=r['path'],sha256=r['sha256'],roles=r['roles'],observed_lstat={'kind':'regular','size_bytes':r['logical_size_bytes_observed']}) for r in allrows]))
        save('proposed_tuples',dict(schema_version='scaling-ownswap-retention-proposed-tuples-v1',proposed=allrows,source_map=refs['retention_map'],copy_authorized=False,raw_copy_performed=False))
        save('allowlist',dict(schema_version='closed-scaling-ownswap-private-retention-exact-allowlist-v1',allowed=self.rows,excluded=self.excluded,source_map=refs['retention_map'],source_proposed_tuples=refs['proposed_tuples'],raw_copy_performed=False,root_copy_authority_required=True))
        save('summary',dict(schema_version='scaling-ownswap-private-retention-inventory-summary-v3',logical_path_hash_tuples=len(allrows),declared_unique_content_hashes=len({r['sha256'] for r in allrows}),logical_bytes_lstat=sum(r['logical_size_bytes_observed'] for r in allrows),inventory=refs['retention_map'],proposed_tuples=refs['proposed_tuples'],gap_inventory=refs['gaps'],metadata_pins=refs['metadata_pins']))
        save('custody_review',dict(schema_version='closed-scaling-ownswap-retention-custody-review-v1',exact_allowlist=refs['allowlist'],source_refs={'retention-map':refs['retention_map'],'proposed-tuples':refs['proposed_tuples'],'summary':refs['summary'],'gaps':refs['gaps'],'metadata-pins':refs['metadata_pins']},copy_authority_granted_by_this_review=False,live_ledger_access=False,model_calls=0,private_groundtruth_accessed=False,raw_copies_made=0,scope_counts={'allowed_tuples':len(self.rows),'excluded_tuples':len(self.excluded),'proposed_tuples':len(allrows),'allowed_declared_unique_content_hashes':len({r['sha256'] for r in self.rows}),'allowed_logical_bytes_lstat':sum(r['logical_size_bytes_observed'] for r in self.rows)}))
        self.auth=dict(schema_version='root-exact-private-retention-authority-v2',state='authorized_exact_copy',named_copier={'agent':'gio-overnight-audit','chat_id':'01a1de44-b76b-7290-9753-ba528b42819e'},destination=str(self.dest),references=refs,allowed_logical_tuples=len(self.rows),excluded_logical_tuples=len(self.excluded),declared_unique_hashes=len({r['sha256'] for r in self.rows}),declared_logical_bytes=sum(r['logical_size_bytes_observed'] for r in self.rows),tuple_fields=['path','sha256','roles','logical_size_bytes_observed'],permissions={'directories':'0700','files':'0600'})
        for k in ['require_copy_time_source_hash_and_size_match','require_exact_allowed_tuple_union','require_regular_files_and_safe_paths','require_staged_atomic_write_and_fsync','require_independent_destination_rehash_and_manifest_verification','no_existing_destination_overwrite']:self.auth[k]=True
        for k in ['excluded_tuple_reads_or_copies_authorized','reuse_existing_archives_authorized','reuse_existing_archives_only_on_verified_exact_hash_match','old_private_archive_metadata_transfer_authorized','private_payloads_in_git','credentials_or_env_files','sqlite_wal_shm_or_live_databases','raw_development_or_final_label_bundles','provider_cache_traversal','recursive_reference_following','model_calls','source_or_scientific_edits']:self.auth[k]=False
        self.auth_path=self.ctl/'authority.json';self.auth_path.write_bytes(encoded(self.auth));self.auth_path.chmod(0o600)
        self.pin=digest(self.auth_path.read_bytes())

    def bundle(self):return c.load_bundle(str(self.auth_path),expected_hash=self.pin)
    def run_copy(self):return c.preserve(self.bundle(),copier_sha256='c'*64)

    def test_exact_copy_opaque_bytes_roles_controls_and_destination_only_verify(self):
        result=self.run_copy();self.assertEqual(result['status'],'complete')
        mapping=json.loads((self.dest/'mapping.json').read_bytes())
        self.assertEqual(mapping['counts'],dict(allowed=3,excluded=1,unique_objects=2,logical_bytes=21,object_bytes=13))
        self.assertEqual([{k:v for k,v in r.items() if k!='archive_member'} for r in mapping['inputs']],self.rows)
        for role in ['authority']+list(self.docs):self.assertEqual((self.dest/'controls'/(role+'.json')).read_bytes(),(self.ctl/(role+'.json')).read_bytes())
        for p in self.dest.rglob('*'):self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o700 if p.is_dir() else 0o600)
        for p in self.src.iterdir():p.unlink()
        for p in self.ctl.iterdir():p.unlink()
        self.assertEqual(c.verify_destination(str(self.dest),self.pin)['status'],'verified')

    def test_partition_role_hash_size_and_missing_or_extra_rows_rejected(self):
        for source,change in [('retention_map','role'),('proposed_tuples','size'),('allowlist','missing'),('proposed_tuples','extra')]:
            docs=copy.deepcopy(self.docs)
            rows=docs[source]['inputs' if source=='retention_map' else 'proposed' if source=='proposed_tuples' else 'allowed']
            if change=='role':rows[0]['roles']=['lost-role']
            elif change=='size':rows[0]['logical_size_bytes_observed']+=1
            elif change=='missing':rows.pop()
            else:rows.append(copy.deepcopy(rows[0]))
            with self.subTest(source=source,change=change),self.assertRaises(c.BoundaryError):c.validate_controls(self.auth,docs)

    def test_control_cross_bindings_and_authority_flags_rejected(self):
        for key in ['require_exact_allowed_tuple_union','reuse_existing_archives_authorized']:
            auth=copy.deepcopy(self.auth);auth[key]=not auth[key]
            with self.subTest(key=key),self.assertRaises(c.BoundaryError):c.validate_controls(auth,self.docs)
        docs=copy.deepcopy(self.docs);docs['allowlist']['source_map']['sha256']='0'*64
        with self.assertRaises(c.BoundaryError):c.validate_controls(self.auth,docs)

    def test_duplicate_path_roles_bool_size_noncanonical_and_forbidden_paths(self):
        cases=[dict(self.rows[0],roles=['same','same']),dict(self.rows[0],logical_size_bytes_observed=True)]
        for path in ['relative','/a/../b','/a//b','/a/*.json','/a/.env','/a/x.sqlite','/a/x.db-wal','/a/x.lock','/a/old.tar.gz','/a/.git/config','/a/archives/member.json']:
            cases.append(dict(self.rows[0],path=path))
        for row in cases:
            with self.subTest(kind='bad_tuple'),self.assertRaises(c.BoundaryError):c.tuple_identity(row)
        docs=copy.deepcopy(self.docs);docs['allowlist']['allowed'].append(copy.deepcopy(self.rows[0]))
        with self.assertRaises(c.BoundaryError):c.validate_controls(self.auth,docs)

    def test_wrong_source_hash_and_size_stop_without_completion(self):
        Path(self.rows[1]['path']).write_bytes(b'changed')
        with self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertFalse((self.dest/'completion.json').exists())

    def test_source_and_parent_symlink_and_fifo_rejected(self):
        p=Path(self.rows[0]['path']);p.unlink();p.symlink_to(self.rows[1]['path'])
        with self.assertRaises(c.BoundaryError):c.read_regular(str(p))
        p.unlink();os.mkfifo(p)
        with self.assertRaises(c.BoundaryError):c.read_regular(str(p))
        alias=self.root/'alias';alias.symlink_to(self.src,target_is_directory=True)
        with self.assertRaises(c.BoundaryError):c.read_regular(str(alias/'b.bin'))

    def test_existing_destination_and_nonprivate_parent_preserved(self):
        self.dest.mkdir(mode=0o700);(self.dest/'sentinel').write_bytes(b'keep')
        with self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertEqual((self.dest/'sentinel').read_bytes(),b'keep')
        (self.dest/'sentinel').unlink();self.dest.rmdir();self.root.chmod(0o755)
        with self.assertRaises(c.BoundaryError):self.run_copy()

    def test_excluded_and_nested_refs_never_opened(self):
        opened=[];real=c.read_regular
        def track(path,*args,**kwargs):opened.append(str(path));return real(path,*args,**kwargs)
        with mock.patch.object(c,'read_regular',side_effect=track):self.run_copy()
        self.assertNotIn(self.excluded[0]['path'],opened)
        self.assertNotIn('/unfollowed/nonexistent',opened)
        self.assertEqual({p for p in opened if p.startswith(str(self.src))},{r['path'] for r in self.rows})

    def test_late_source_mutation_is_quarantined_no_completion(self):
        real=c.atomic_write
        def changed(directory,name,data):
            result=real(directory,name,data)
            if name=='objects.tar.gz':Path(self.rows[0]['path']).write_bytes(b'changed')
            return result
        with mock.patch.object(c,'atomic_write',side_effect=changed),self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertFalse((self.dest/'completion.json').exists())

    def test_late_control_mutation_is_quarantined_no_completion(self):
        real=c.atomic_write
        def changed(directory,name,data):
            result=real(directory,name,data)
            if name=='objects.tar.gz':self.auth_path.write_bytes(b'changed')
            return result
        with mock.patch.object(c,'atomic_write',side_effect=changed),self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertFalse((self.dest/'completion.json').exists())

    def test_atomic_write_no_overwrite_no_stage_and_exact_modes(self):
        self.dest.mkdir(mode=0o700);c.atomic_write(str(self.dest),'a',b'keep')
        with self.assertRaises(c.BoundaryError):c.atomic_write(str(self.dest),'a',b'replace')
        self.assertEqual((self.dest/'a').read_bytes(),b'keep')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()),['a'])

    def test_archive_is_deterministic_and_rejects_bad_inventory_metadata_or_bytes(self):
        bodies={digest(b'a'):b'a',digest(b'z'):b'z'}
        blob=c.pack_objects(bodies)
        self.assertEqual(blob,c.pack_objects(dict(reversed(list(bodies.items())))))
        expected={h:len(b) for h,b in bodies.items()}
        self.assertIsNone(c.verify_objects(blob,expected))
        for entries in [[],[('objects/'+digest(b'a'),b'a',tarfile.REGTYPE,0o600)],[('../bad',b'a',tarfile.REGTYPE,0o600)],[('objects/'+digest(b'a'),b'',tarfile.SYMTYPE,0o600)],[('objects/'+digest(b'a'),b'wrong',tarfile.REGTYPE,0o644)]]:
            out=io.BytesIO()
            with tarfile.open(fileobj=out,mode='w:gz',format=tarfile.USTAR_FORMAT) as t:
                for name,b,kind,mode in entries:
                    m=tarfile.TarInfo(name);m.size=len(b);m.type=kind;m.mode=mode;t.addfile(m,io.BytesIO(b))
            with self.subTest(kind='archive_corruption'),self.assertRaises(c.BoundaryError):c.verify_objects(out.getvalue(),expected)

    def test_destination_extra_missing_mutated_and_wrong_mode_rejected(self):
        self.assertEqual(self.run_copy()['status'],'complete');p=self.dest/'extra';p.write_bytes(b'extra')
        with self.assertRaises(c.BoundaryError):c.verify_destination(str(self.dest),self.pin)
        p.unlink();m=self.dest/'mapping.json';original=m.read_bytes();m.write_bytes(original+b' ')
        with self.assertRaises(c.BoundaryError):c.verify_destination(str(self.dest),self.pin)
        m.write_bytes(original);m.chmod(0o644)
        with self.assertRaises(c.BoundaryError):c.verify_destination(str(self.dest),self.pin)
        m.chmod(0o600);m.unlink()
        with self.assertRaises(c.BoundaryError):c.verify_destination(str(self.dest),self.pin)

    def test_strict_json_and_control_pin_failures_are_sanitized(self):
        for raw in [b'{"x":1,"x":2}',b'{"x":NaN}',b'private-source-sentinel']:
            with self.assertRaises(c.BoundaryError) as err:c.strict_json(raw)
            self.assertNotIn('sentinel',str(err.exception))
        self.auth_path.write_bytes(self.auth_path.read_bytes()+b' ')
        with self.assertRaises(c.BoundaryError) as err:self.bundle()
        self.assertNotIn(str(self.root),str(err.exception))

    def test_completion_publish_failure_removes_marker(self):
        real=c.atomic_write
        def fail_after_publish(directory,name,data):
            result=real(directory,name,data)
            if name=='completion.json':raise c.BoundaryError('synthetic_late_failure')
            return result
        with mock.patch.object(c,'atomic_write',side_effect=fail_after_publish),self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertFalse((self.dest/'completion.json').exists())

    def test_equal_hash_unequal_bytes_rejected_before_dedup(self):
        Path(self.rows[1]['path']).write_bytes(b'not-same')
        real=c.sha
        def collision(raw):
            return self.rows[0]['sha256'] if raw==b'not-same' else real(raw)
        with mock.patch.object(c,'sha',side_effect=collision),self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertFalse((self.dest/'completion.json').exists())

    def test_source_replacement_same_bytes_rejected(self):
        real=c.atomic_write
        def replace(directory,name,data):
            result=real(directory,name,data)
            if name=='objects.tar.gz':
                p=Path(self.rows[0]['path']);other=p.with_name('replacement');other.write_bytes(p.read_bytes());os.replace(other,p)
            return result
        with mock.patch.object(c,'atomic_write',side_effect=replace),self.assertRaises(c.BoundaryError):self.run_copy()
        self.assertFalse((self.dest/'completion.json').exists())

    def test_read_time_mutation_rejected(self):
        p=Path(self.rows[0]['path']);real=os.read;changed=False
        def read(fd,n):
            nonlocal changed
            b=real(fd,n)
            if b and not changed:
                changed=True;p.write_bytes(b'changed!')
            return b
        with mock.patch('os.read',side_effect=read),self.assertRaises(c.BoundaryError):c.read_regular(str(p))

    def test_explicit_cli_pin_mismatch_opens_only_authority(self):
        opened=[];real=c.read_regular;out=io.StringIO()
        def tracked(path,*args,**kwargs):opened.append(str(path));return real(path,*args,**kwargs)
        with mock.patch.object(c,'read_regular',side_effect=tracked),mock.patch('sys.stderr',out),mock.patch('sys.stdout',out):
            self.assertEqual(c.main(['preflight','--authority',str(self.auth_path),'--authority-sha256','0'*64]),1)
        self.assertEqual(opened,[str(self.auth_path)]);self.assertFalse(self.dest.exists())
        self.assertNotIn(str(self.root),out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['reason'],'authority_pin')

    def test_archive_trailing_nonzero_data_rejected(self):
        objects={digest(b'a'):b'a'};raw=c.pack_objects(objects)
        altered=gzip.compress(gzip.decompress(raw)+b'x'*512,mtime=0)
        with self.assertRaises(c.BoundaryError):c.verify_objects(altered,{digest(b'a'):1})

    def test_cli_bad_argument_reason_never_echoes_private_value(self):
        out=io.StringIO()
        with mock.patch('sys.stdout',out),mock.patch('sys.stderr',out):
            self.assertEqual(c.main(['preflight','--unexpected','private-body-sentinel']),1)
        self.assertNotIn('private-body-sentinel',out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['reason'],'invalid_arguments')

    def test_production_cli_rejects_synthetic_authority_before_payload_access(self):
        out=io.StringIO()
        with mock.patch('sys.stdout',out),mock.patch('sys.stderr',out):
            code=c.main(['preflight','--authority',str(self.auth_path),'--authority-sha256',self.pin])
        self.assertEqual(code,1);self.assertNotIn(str(self.root),out.getvalue());self.assertFalse(self.dest.exists())


if __name__=='__main__':unittest.main(verbosity=2)
