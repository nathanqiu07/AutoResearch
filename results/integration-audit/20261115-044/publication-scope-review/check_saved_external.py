#!/usr/bin/env python3
"""Check saved root verification metadata; no private bundle/archive access."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--original',required=True);p.add_argument('--root-results',required=True);p.add_argument('--copy-manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args()
def sha(b):return hashlib.sha256(b).hexdigest()
checks=[];inputs=[];saved={}
def c(n,v):
 checks.append({'name':n,'passed':bool(v)})
 if not v:raise AssertionError(n)
def load(path,pin):
 path=Path(path);b=path.read_bytes();c('pin:'+path.name,sha(b)==pin);saved[str(path)]=b;inputs.append({'path':str(path),'sha256':sha(b),'size_bytes':len(b)});return json.loads(b)
r=Path(a.root_results)
original=load(a.original,'c0e3351d3278091af56ccbbd6745f04554bff25943ab7f32d7ad0d3f8dd9091f')
repeat=load(r/'archive-verification/receipt.json','c1c3d1a4165426ad08a71a59128ee3d53ae559c1f3e04868fc5320d325f34307')
compare=load(r/'comparison.json','d5193c2983f87eceb211c8ef9e4aa0585b3da991a2a848b7010a43ddb679cc3f')
external=load(r/'external-verification.json','306a3b7f2fccd4711003ae6f632c04b4e2fe96c0b73ccea8ad0bdc0eb0449a59')
access=load(r/'input-reader-access.json','9f0a46e8287560821864426a35d9adfea00f9d6f081f0326e68ecddd05b00e71')
inv=load(r/'verify.invocation.json','ed8cadac293350062ffe14e3889f4118e701f4ac35009676106e12ce70f36d91')
manifest=load(a.copy_manifest,'963a81eb821ce24b1b33580460cc3362962a3c17f671ed2734053fefe88dd2e1')
diff=sorted(k for k in set(original)|set(repeat) if original.get(k)!=repeat.get(k));c('only_argv_differs',diff==['argv']);c('saved_comparison_exact',compare['different_fields']==diff and compare['all_other_fields_and_ordered_arrays_equal'])
c('exact_reproduced_counts',(repeat['new_members_verified'],repeat['logical_mappings_verified'],repeat['reused_members_verified'])==(2813,3016,3))
c('saved_verification_status',repeat['status']=='verified' and inv['exit_code']==0)
c('comparison_receipt_pins',compare['original_verification_sha256']=='c0e3351d3278091af56ccbbd6745f04554bff25943ab7f32d7ad0d3f8dd9091f' and compare['external_verification_sha256']=='c1c3d1a4165426ad08a71a59128ee3d53ae559c1f3e04868fc5320d325f34307')
c('manifest_entry_count_and_sum',len(manifest['files'])==external['payload_files_verified']==33 and sum(e['size_bytes'] for e in manifest['files'])==external['payload_bytes']==28082867)
c('manifest_unique_destinations',len({e['destination'] for e in manifest['files']})==33)
c('saved_file_mode_and_total',external['actual_files_including_metadata']==35 and external['all_permissions']=='files0600_directories0700')
c('archive_hash_match',external['archive_sha256']==repeat['archive_sha256']=='6ef3b765d2a43ef7292489e372c5ff30999f1e6e95e244c952f28583383128f6')
c('reader_observed_paths_equal_explicit_allowlist',set(access['observed_read_regular_paths'])==set(access['allowed_read_regular_paths']) and len(access['allowed_read_regular_paths'])==7)
c('guard_not_overclaimed','not an OS-level file trace' in access['guard_scope'] and 'not OS-level source-read tracing' in compare['guard_scope'])
c('no_extra_execution_claim',compare['model_calls']==0 and compare['body_semantic_parsing'] is False and compare['consumer_execution_or_replay'] is False)
for path,b in saved.items():c('unchanged:'+Path(path).name,Path(path).read_bytes()==b)
report={'schema_version':'audit044-additive-saved-external-metadata-review-v1','passed':len(checks),'failed':0,'checks':checks,'inputs':inputs,'comparison':{'different_fields':diff,'all_other_values_and_ordered_arrays_equal':True,'external_payload_entries':33,'external_payload_bytes':28082867,'total_files_including_manifest_and_receipt':35,'new_members_verified_in_saved_report':2813,'logical_mappings_verified_in_saved_report':3016,'reused_members_verified_in_saved_report':3},'limits':['Saved metadata comparison only; this check does not open the external private bundle or any archive body.','Root read_regular allowlist and process/socket denial are a bounded wrapper, not an OS-level file trace.','No new content eligibility, semantic, execution or provider claim.']}
out=Path(a.out);out.mkdir(mode=0o700,exist_ok=False);(out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':len(checks),'failed':0},sort_keys=True))
