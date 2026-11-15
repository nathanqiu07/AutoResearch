#!/usr/bin/env python3
"""Check frozen code/metadata only. Never open a path referenced by a payload mapping."""
import argparse, collections, hashlib, json
from pathlib import Path, PurePosixPath

MANIFEST='68aa82a02278fec717574764bae9eb79b16107748dadd1247109d6715ee37bcd'
CODE='68e9550f742416e68fba295a16f12d65d27651f6e048f982292ed126f4da82bf'
TEST='9739823439c14b998d30794b3fec3dc0bfb8833fe7cc1e06e8afe17660dfd861'
PINS={'allowlist':'f403b554deefa55230486f09c31f469250cc415bf60b3dff41b2cf5e4b5420eb','custody':'b20e0ece59ca334a7b51e7072faa784f7050bc68258375e79dc2c4373e195c20','reuse_receipt':'017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0','reuse_archive':'28e03a21179eb9d12c9c78663027477c67adbca4ac31c16393b303e3b15583dd'}
def sha(b):return hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=Path(a.stage);checks=[];inputs=[];saved={}
def check(name,value):
 checks.append({'name':name,'passed':bool(value)})
 if not value:raise AssertionError(name)
def read(name,pin,size=None):
 q=PurePosixPath(name);check('safe-path:'+name,not q.is_absolute() and '..' not in q.parts)
 path=root/name;check('regular-not-link:'+name,path.is_file() and not path.is_symlink());b=path.read_bytes()
 check('pin:'+name,sha(b)==pin and (size is None or len(b)==size));saved[name]=b;inputs.append({'path':name,'sha256':pin,'size_bytes':len(b)});return b
manifest=json.loads(read('safe-manifest.json',MANIFEST));check('manifest_count',manifest['file_count']==len(manifest['files'])==25)
check('manifest_no_duplicate_paths',len({x['path'] for x in manifest['files']})==25)
for x in manifest['files']:read(x['path'],x['sha256'],x['size_bytes'])
def j(name):return json.loads(saved[name])
allowed=j('controls/allowlist.json');custody=j('controls/custody.json');reuse=j('controls/reuse-receipt.json');receipt=j('preservation-01/receipt.json');v=j('verification-01/receipt.json');f=j('findings.json');binding=j('test-code-binding.json')
check('exact_control_copies',{k:sha(saved['controls/'+n+'.json']) for k,n in [('allowlist','allowlist'),('custody','custody'),('reuse_receipt','reuse-receipt')]}=={k:PINS[k] for k in ['allowlist','custody','reuse_receipt']})
check('code_and_test_pins',sha(saved['preserve_exact.py'])==CODE and sha(saved['test_preserve_exact.py'])==TEST)
check('both_receipts_executed_code',receipt['reader_sha256']==v['reader_sha256']==CODE)
check('both_receipts_control_pins',receipt['control_pins']==v['control_pins']==PINS)
check('verification_binds_exact_preservation_receipt',v['receipt_sha256']==sha(saved['preservation-01/receipt.json']))
check('findings_receipt_pins',f['preservation_receipt_sha256']==sha(saved['preservation-01/receipt.json']) and f['verification_receipt_sha256']==sha(saved['verification-01/receipt.json']))
rows=allowed['allowed'];excluded={x['path'] for x in allowed['excluded']};logical=receipt['logical_inputs'];keys={'path','sha256','roles','logical_size_bytes_observed'}
check('counts_and_distinct_approved_paths',len(rows)==len(logical)==3016 and len({r['path'] for r in rows})==3016 and len(excluded)==6)
check('mapping_has_only_metadata_fields',all(set(x)==keys|{'storage','archive_member'} for x in logical))
check('all_tuples_roles_sizes_and_order_exact',[{k:x[k] for k in keys} for x in logical]==rows)
check('excluded_not_in_mappings_or_state',not excluded.intersection(x['path'] for x in logical) and not excluded.intersection(receipt['source_states']))
aliases={x['source_path']:x for x in reuse['members']};check('exact_three_aliases',len(aliases)==3)
expected=[]
for row in rows:
 x=dict(row);x['storage']='existing_archive' if row['path'] in aliases else 'new_archive';x['archive_member']=aliases[row['path']]['archive_member'] if row['path'] in aliases else 'objects/'+row['sha256'];expected.append(x)
check('full_storage_mapping_exact',expected==logical)
check('aliases_match_hash_and_size',all((x['sha256'],x['logical_size_bytes_observed'])==(aliases[x['path']]['sha256'],aliases[x['path']]['size_bytes']) for x in rows if x['path'] in aliases))
new=[x for x in logical if x['storage']=='new_archive'];groups=collections.defaultdict(list)
for x in new:groups[x['sha256']].append(x)
check('new_and_reuse_counts',len(new)==3013 and len(groups)==2813 and len(logical)-len(new)==3)
check('dedup_hash_group_sizes_consistent',all(len({x['logical_size_bytes_observed'] for x in g})==1 for g in groups.values()))
check('logical_bytes_sum',sum(x['logical_size_bytes_observed'] for x in rows)==receipt['logical_bytes']==126952049)
check('new_logical_bytes_sum',sum(x['logical_size_bytes_observed'] for x in new)==receipt['new_logical_bytes']==125062045)
check('new_object_bytes_sum',sum(g[0]['logical_size_bytes_observed'] for g in groups.values())==receipt['new_uncompressed_bytes']==105191777)
check('receipt_count_fields',(receipt['logical_count'],receipt['new_logical_count'],receipt['new_member_count'],receipt['reused_logical_count'])==(3016,3013,2813,3))
check('verification_count_fields',(v['logical_mappings_verified'],v['new_members_verified'],v['reused_members_verified'])==(3016,2813,3))
check('source_states_exact_paths',set(receipt['source_states'])=={x['path'] for x in rows})
statekeys={'size_bytes','mode','device','inode','mtime_ns','ctime_ns'}
check('source_states_metadata_schema',all(set(x)==statekeys for x in receipt['source_states'].values()))
check('source_state_sizes_match_all',all(receipt['source_states'][x['path']]['size_bytes']==x['logical_size_bytes_observed'] for x in rows))
check('before_after_receipt_claims',receipt['source_checks_before']==receipt['source_checks_after']==3016 and receipt['all_sources_unchanged'] and receipt['all_new_member_bytes_verified'] and receipt['all_existing_member_bytes_verified'])
check('archive_identity_receipts_and_findings',receipt['archive_sha256']==v['archive_sha256']==f['new_archive_sha256']==manifest['private_archive_sha256']=='6ef3b765d2a43ef7292489e372c5ff30999f1e6e95e244c952f28583383128f6' and receipt['archive_size_bytes']==v['archive_size_bytes']==f['new_archive_size_bytes']==24580726)
check('reuse_archive_identity',receipt['reuse_archive_sha256']==reuse['archive_sha256']==PINS['reuse_archive'])
check('private_mode_and_ignore_claims',receipt['archive_mode']=='0o600' and f['private_directory_mode']=='0o700' and receipt['git_ignore_exit_code']==0)
check('success_statuses',receipt['status']==f['status']=='verified_private_retention' and v['status']=='verified')
check('no_semantic_execution_claims',receipt['body_semantic_parsing'] is False and receipt['model_calls']==0 and receipt['scoring'] is False and receipt['execution_or_consumer_replay'] is False)
check('limits_explicit',len(receipt['limits'])==4 and f['limits']==receipt['limits'])
check('test_binding',binding['reader_sha256']==CODE and binding['test_sha256']==TEST and binding['green_exit_code']==0 and binding['green_tests']==16 and binding['red_exit_code']==1 and binding['red_tests']==16)
for prefix,record in [('preservation-01',receipt),('verification-01',v)]:
 result=j(prefix+'.result.json');stdout=json.loads(saved[prefix+'.stdout']);check(prefix+':stdout_receipt_pin',stdout['receipt_sha256']==sha(saved[prefix+'/receipt.json']));check(prefix+':stderr_empty',saved[prefix+'.stderr']==b'')
 check(prefix+':recorded_exit_success',result['exit_code']==0)
for name,b in saved.items():check('unchanged:'+name,(root/name).read_bytes()==b)
report={'schema_version':'audit044-independent-metadata-receipt-review-v1','passed':len(checks),'failed':0,'checks':checks,'inputs':inputs,'summary':{'logical_mappings':3016,'new_logical_mappings':3013,'new_declared_hash_groups':2813,'existing_aliases':3,'excluded':6,'new_archive_bytes_recorded':24580726,'new_uncompressed_bytes_recorded':105191777,'duplicate_group_logical_sizes':sorted(len(g) for g in groups.values() if len(g)>1)},'limits':['Metadata and source-code binding only; this checker does not read source bodies or archive payloads.','Actual-byte checks are recorded by the pinned executed author implementation and supported by independent synthetic controls, not repeated on raw inputs here.','All 3016 tuple/role mappings are independently compared to the pinned allowlist; prior 3022-map partition is root separate evidence.','No content eligibility, label-free, provider, scoring, consumer or environment reconstruction conclusion.'],'raw_payloads_or_archives_opened':False}
out=Path(a.out);out.mkdir(mode=0o700,exist_ok=False);(out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':len(checks),'failed':0,'summary':report['summary']},sort_keys=True))
