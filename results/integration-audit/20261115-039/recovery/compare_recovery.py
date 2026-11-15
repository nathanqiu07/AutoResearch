"""Require exact039 replay equality except actual invocation/reader identity."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser()
    for name in ('original-report','recovered-report','original-inventory','recovered-inventory','changes','portable-reader','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();left_raw=a.original_report.read_bytes();right_raw=a.recovered_report.read_bytes();left=json.loads(left_raw);right=json.loads(right_raw)
    changed=sorted(k for k in set(left)|set(right) if left.get(k)!=right.get(k))
    assert set(changed)=={'argv','reader_sha256'}
    changes=json.loads(a.changes.read_text());portable=a.portable_reader.read_bytes();assert sha(portable)==changes['portable_sha256']==right['reader_sha256']
    reconstructed=portable.decode()
    for edit in reversed(changes['changes']):
        assert reconstructed.count(edit['new'])==1;reconstructed=reconstructed.replace(edit['new'],edit['old'])
    assert sha(reconstructed.encode())==changes['original_sha256']==left['reader_sha256']
    assert len(changes['changes'])==6
    for key in ['argv','reader_sha256']:left.pop(key);right.pop(key)
    assert left==right
    inv_left=a.original_inventory.read_bytes();inv_right=a.recovered_inventory.read_bytes();assert inv_left==inv_right
    assert left['check_counts']=={'passed':1316,'failed':0}
    result={'schema_version':'audit039-recovered-replay-comparison-v1','original_report_sha256':sha(left_raw),'recovered_report_sha256':sha(right_raw),'inventory_sha256':sha(inv_left),'inventory_byte_identical':True,'differing_top_level_fields':changed,'all_other_fields_and_ordered_arrays_exactly_equal':True,'original_checks_and_order_unchanged':True,'six_exact_changes_reverse_to_original_reader':True,'original_reader_sha256':changes['original_sha256'],'portable_reader_sha256':changes['portable_sha256'],'checks_passed':1316,'git_provenance_or_full_environment_recovery_claim':False}
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

if __name__=='__main__':main()
