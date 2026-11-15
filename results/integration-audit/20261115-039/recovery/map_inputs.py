"""Map pinned audit039 inputs to retained metadata; never open payload files."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath

PINS={'inventory':'e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5',
      'manifest.json':'472782172c20204b57579f30db62bcd35bdfe6cb0f9409418114f31e26fb28a5',
      'receipt.json':'2e6daeee9d45c58e2f3df225132406dc04516e0e51a382030ff554b79b5a74e1',
      'index.json':'3e8100619f3450ccdfe4821fd40068d9adc66b824e2b52bc3f7d247c076bdd01'}
PUBLICATION='c80937c7f92dd6ad05eee319e64f16799f0a193e'
EXECUTED='e9672aa48ba442dfc5bd2cd84b8f0c76e2bfb7e4'
PREFIX='results/gio-matched-shutdown-05/'

def main():
    a=argparse.ArgumentParser();a.add_argument('--inventory',type=Path,required=True);a.add_argument('--owner-metadata-root',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    reads=[]
    def load(path,key):
        raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest();assert h==PINS[key]
        reads.append({'path':str(path),'sha256':h,'size_bytes':len(raw)});return json.loads(raw)
    inventory=load(a.inventory,'inventory')['files'];manifest=load(a.owner_metadata_root/'manifest.json','manifest.json');receipt=load(a.owner_metadata_root/'receipt.json','receipt.json');index=load(a.owner_metadata_root/'index.json','index.json')
    assert len(inventory)==len({(r['commit'],r['path']) for r in inventory})==337
    files=manifest['files'];assert len(files)==manifest['file_count']==receipt['file_count']==index['recorded_file_count']==213
    assert sum(r['bytes'] for r in files.values())==manifest['total_bytes']==receipt['total_bytes']==index['recorded_bytes']
    assert receipt['manifest_sha256']==index['manifest_sha256']==PINS['manifest.json'] and index['receipt_sha256']==PINS['receipt.json']
    mapped=[];missing=[];conflicts=[];hash_only=[]
    for row in inventory:
        path=row['path'];assert row['commit'] in (PUBLICATION,EXECUTED)
        expected=path[len(PREFIX):] if path.startswith(PREFIX) else ('runner_source/'+PurePosixPath(path).name if row['commit']==EXECUTED and path.startswith('scripts/gio_petri/') else None)
        if expected is not None:assert not PurePosixPath(expected).is_absolute() and '..' not in PurePosixPath(expected).parts
        exact=[p for p,r in files.items() if r['copy_sha256']==row['sha256'] and r['bytes']==row['size_bytes']]
        if expected in files and files[expected]['copy_sha256']==files[expected]['source_sha256']==row['sha256'] and files[expected]['bytes']==row['size_bytes']:
            mapped.append({**row,'retained_payload_relative_path':expected,'proof_level':'manifest_metadata_match_only','payload_bytes_reread':False})
        elif exact:
            hash_only.append({**row,'candidate_relative_paths':exact})
        else:
            kind='public_runtime_source_bytes' if row['commit']==EXECUTED else 'publication_or_review_record_keep_private_until_content_review'
            missing.append({**row,'gap_kind':kind,'proposed_bundle_path':('runtime-source/' if row['commit']==EXECUTED else 'publication-records/')+path})
            if expected in files:conflicts.append({'path':path,'expected_relative_path':expected,'inventory_sha256':row['sha256'],'manifest_copy_sha256':files[expected]['copy_sha256']})
    assert not conflicts and not hash_only
    assert len(mapped)==234 and len(missing)==103
    unique_paths={r['retained_payload_relative_path'] for r in mapped};assert len(unique_paths)==210
    native=set(receipt['native_eval_files']);assert len(native)==3 and not native&unique_paths
    assert set(files)-unique_paths==native
    counts=Counter(r['gap_kind'] for r in missing);sizes={k:sum(r['size_bytes'] for r in missing if r['gap_kind']==k) for k in counts}
    assert counts=={'public_runtime_source_bytes':90,'publication_or_review_record_keep_private_until_content_review':13}
    assert sizes=={'public_runtime_source_bytes':1265625,'publication_or_review_record_keep_private_until_content_review':244752}
    result={'schema_version':'audit039-exact-input-recovery-map-v1','audit_publication_commit':PUBLICATION,'audit_executed_source':EXECUTED,'audit_input_inventory_sha256':PINS['inventory'],'metadata_inputs_read':reads,'owner_archive_root_recorded':receipt['archive'],'owner_payload_root_recorded':receipt['payload'],'logical_inputs':337,'retained_logical_manifest_matches':234,'retained_unique_payload_files':210,'retained_unique_payload_bytes':sum(files[p]['bytes'] for p in unique_paths),'retained_matches_by_recorded_commit':dict(Counter(r['commit'] for r in mapped)),'missing_counts':dict(counts),'missing_bytes':sizes,'total_missing_inputs':103,'total_missing_bytes':1510377,'path_hash_conflicts':conflicts,'hash_only_alternates':hash_only,'unneeded_native_eval_members':sorted(native),'retained_mappings':mapped,'missing_inputs':missing,'payload_bytes_read_or_copied':False,'git_objects_read_or_copied':False,'limits':['Retained matches prove only exact agreement between the pinned inventory and pinned archive manifest. The210 payload files have not been freshly hash-read here.','Recorded Git commit/path provenance is preserved as historical metadata; a future byte-map replay cannot prove original Git history or recover a complete installed environment.','The13 missing publication/review records may contain original trace/quote material and should stay in private preservation; no such bytes were opened by this mapper.','The3 native.eval members are outside audit039 inputs and are neither needed nor opened.','No copying, archive creation, Git bundle/repository/replace-ref creation, runtime execution, dependency reads or network/provider operations occurred.']}
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['logical_inputs','retained_logical_manifest_matches','retained_unique_payload_files','missing_counts','missing_bytes','total_missing_bytes']}))

if __name__=='__main__':main()
