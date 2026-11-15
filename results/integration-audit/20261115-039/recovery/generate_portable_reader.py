"""Create an additive variant with only CLI/input-access/receipt changes."""
import argparse
import hashlib
from pathlib import Path
import json

ORIGINAL_SHA='df2e4c4d8f1b87e39969a637fa3b0e537c459234ecb4cc50813baf83cd76b409'
INVENTORY_SHA='e9d4d5e92fdbe3baceee87ad179856a781b0d5d476abb397dc590d1be4c6a6f5'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    a=argparse.ArgumentParser();a.add_argument('--original',type=Path,required=True);a.add_argument('--adapter',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--changes',type=Path,required=True);a=a.parse_args()
    raw=a.original.read_bytes();assert sha(raw)==ORIGINAL_SHA;text=raw.decode();replacements=[]
    def replace(old,new):
        nonlocal text
        assert text.count(old)==1;replacements.append({'old':old,'new':new});text=text.replace(old,new)
    replace('Read immutable original downstream05 Git objects; emit metadata only.','Check recovered bytes labelled with original downstream05 identities; emit metadata only.')
    replace('The only subprocess is read-only git show against explicit pinned objects.','Input access uses explicit hash-pinned byte mappings, with no subprocess or fallback.')
    replace('import subprocess\n','import importlib.util\n')
    old="ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()"
    new="""ap=argparse.ArgumentParser()
    for name in ('input-map','inventory','retained-root','source-archive','publication-archive','out'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--input-map-sha256',required=True);a=ap.parse_args()
    adapter_path=Path(__file__).with_name('recovered_inputs.py')
    if sha(adapter_path.read_bytes())!='ADAPTER_PIN':raise ValueError('Recovery adapter changed')
    spec=importlib.util.spec_from_file_location('pinned_recovery_inputs',adapter_path)
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    recovery=adapter.RecoveryInputs(a.input_map,a.input_map_sha256,a.inventory,'INVENTORY_PIN',a.retained_root,a.source_archive,a.publication_archive)
    if recovery.original_reader_sha256!='ORIGINAL_PIN':raise ValueError('Original checker identity differs')""".replace('ADAPTER_PIN',sha(a.adapter.read_bytes())).replace('INVENTORY_PIN',INVENTORY_SHA).replace('ORIGINAL_PIN',ORIGINAL_SHA)
    replace(old,new)
    old="result=subprocess.run(['git','--no-optional-locks','-C',str(a.repo),'show',commit+':'+path],capture_output=True,check=True,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp'})\n            cache[key]=result.stdout;inventory[key]={'commit':commit,'path':path,'sha256':sha(result.stdout),'size_bytes':len(result.stdout)}"
    new="recovered_raw=recovery.read(commit,path)\n            cache[key]=recovered_raw;inventory[key]={'commit':commit,'path':path,'sha256':sha(recovered_raw),'size_bytes':len(recovered_raw)}"
    replace(old,new)
    old="save(a.out/'report.json',report);save(a.out/'input-inventory.json',{'files':list(inventory.values()),'raw_copied':False});print(json.dumps({'passed':len(checks),'failed':0,'recorded_calls':78,'input_objects':len(inventory)}))"
    new="recovery_receipt=recovery.finish();recovery_receipt['portable_reader_sha256']=sha(Path(__file__).read_bytes());recovery_receipt['adapter_sha256']=sha(adapter_path.read_bytes());save(a.out/'recovered-execution.json',recovery_receipt)\n        "+old
    replace(old,new)
    assert 'subprocess' not in text.replace('with no subprocess or fallback.','') and 'a.repo' not in text
    with a.out.open('x') as f:f.write(text)
    proof={'schema_version':'audit039-additive-reader-change-proof-v1','original_sha256':ORIGINAL_SHA,'portable_sha256':sha(text.encode()),'adapter_sha256':sha(a.adapter.read_bytes()),'changes':replacements,'unchanged_checking_logic':'Every byte outside these six exact replacements is unchanged. All original checks/expected input hashes/report fields remain, with actual reader_sha256 and argv reflecting the new variant; recovered-execution.json is separate.','expected_report_difference_fields':['argv','reader_sha256'],'expected_inventory_byte_identical':True}
    with a.changes.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps({k:proof[k] for k in ['original_sha256','portable_sha256','adapter_sha256']}))

if __name__=='__main__':main()
