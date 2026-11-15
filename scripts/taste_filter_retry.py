"""Retry only unresolved judgments; retain original failures and conservative charges."""
import argparse,getpass,json,os
from pathlib import Path
from taste_filter_history import Runner,read,export,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    out=args.output; old=Runner(out,'',14.90); manifest=json.loads((out/'manifest.json').read_text())
    source=Path(manifest['source']); rows=read(source); byid={c['example_id']:c for c in rows}
    missing=[(c,kind,i) for c in rows for kind,n in [('vote',10),('quality',1)] for i in range(n)
             if 'parsed' not in old.records.get(f"{c['example_id']}/{kind}/{i}",{})]
    cap=min(1.,14.90-old.spent)
    if cap<=0: raise RuntimeError('No remaining budget')
    retrydir=out/'retry-01';retrydir.mkdir(exist_ok=False)
    key=os.environ.get('OPENROUTER_API_KEY') or getpass.getpass('OpenRouter key (hidden): ')
    runner=Runner(retrydir,key,cap)
    for c,kind,i in missing:
        k=f"{c['example_id']}/{kind}/{i}";runner.call(c,kind,i)
        result=runner.records.get(k,{})
        if k not in runner.reservations: continue
        if not result: result=dict(event='result',error='retry outcome unknown')
        previous_charge=old.charge(k) if k in old.reservations else 0
        # Existing bound remains held when original outcome/cost was unknown.
        corrected=dict(result,key=k,retry_recovery=True,previous_charge_usd=previous_charge,
                       cost_usd=previous_charge+runner.charge(k))
        if k not in old.reservations:
            old.reservations[k]=runner.reservations[k]
            old.append(dict(event='reserve',key=k,bound_usd=runner.reservations[k],source='retry-01'))
        old.records[k]=corrected;old.append(corrected)
    old=Runner(out,'',14.90)
    assert sha(source)==manifest['source_sha256']
    assert sha(source.parent/'heldout_timesplit.jsonl')==manifest['heldout_sha256']
    export(out,rows,old.records,manifest,old.spent)
if __name__=='__main__':main()
