"""Frozen history-only comparison. Never reads the upstream held-out file."""
import argparse
from collections import Counter
import getpass
import json
import os
from pathlib import Path
import sys
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autoresearch.llm import Budget, LLM
from autoresearch.taste.usermodel import Choice,digest
from autoresearch.taste.prefdata import PreferenceRecord,build_manifest,write_manifest,save_records,load_records
from autoresearch.taste.methods import create_method
from autoresearch.taste.fidelity import run_fidelity
from autoresearch.taste.handoff import build_bundle,write_bundle
from autoresearch.taste.viewer import build_viewer
from autoresearch.taste.paper_backend import PaperOpenAILLM

CONFIG=dict(full_history=True,k='all',max_candidates=80,max_principles=5,
            num_search_candidates=10,max_bootstrapped_demos=64,workers=16,adaptive_workers=True)
PRIOR_COMMITTED_USD=.361817 # known earlier runs + retained failed reservations, rounded upward
NEW_CAP=8.5

class FixtureLLM(LLM):
    name='offline-paper-fixture';model='fixture-v1'
    def embed(self,texts):
        return [[int(digest(t)[j:j+2],16)/255 for j in range(0,16,2)] for t in texts]
    def complete(self,prompt,system='',**kwargs):
        p=json.loads(prompt.split('INPUT_JSON:\n',1)[1])
        if 'generation_style' in p:return json.dumps({'principles':['Select the more informative response.','Select the more concrete response.']})
        if 'voting_round' in p:return json.dumps({'votes':{str(i):'b' for i in range(len(p['principles']))}})
        if 'past_judgements' in p:return json.dumps({'persona':'OFFLINE FIXTURE: prefers concrete information; simulated, not evidence.'})
        return json.dumps({'probabilities':[.3,.7],'rationale':'OFFLINE FIXTURE: predetermined B, not a real preference prediction.'})


def prepare(source,previous,out):
    rows=[json.loads(l) for l in source.read_text().splitlines() if l.strip()]
    if len(rows)!=373:raise ValueError('expected exactly 373 history-only choices')
    old=json.loads(previous.read_text());olduser=next(iter(old['users'].values()))
    actual_sha=__import__('hashlib').sha256(source.read_bytes()).hexdigest()
    if actual_sha != old['provenance']['source_sha256']:
        raise ValueError('source differs from pinned previous-pilot hash')
    groups=sorted({r['group_id'] for r in rows},key=lambda g:digest(['hobbhahn-dev-01',g]))
    n=len(groups)//5
    split={g:('test' if i<n else 'val' if i<2*n else 'history') for i,g in enumerate(groups)}
    seen=set();records=[]
    for row in rows:
        key=digest([row['context'],sorted([row['a_text'],row['b_text']])])
        if key in seen:raise ValueError('duplicate content in frozen source')
        seen.add(key);r=dict(row);r['reason']=''
        records.append(PreferenceRecord(Choice(**r),'hobbhahn_history_dev','dev',split[r['group_id']],'history_only'))
    counts=dict(Counter(r.choice_split for r in records))
    if counts!={'history':236,'val':70,'test':67}:raise ValueError('unexpected split '+str(counts))
    ids=lambda s:{r.choice.identity for r in records if r.choice_split==s}
    if ids('test')!=set(olduser['test']) or ids('history')!=set(olduser['history']):raise ValueError('previous split IDs changed')
    if not set(olduser['val'])<=ids('val'):raise ValueError('previous validation rows lost')
    provenance={**old['provenance'],'split_policy':'same frozen document groups; restore all 70 validation choices',
                'excluded_validation_ids':[],'method_config':CONFIG,'previous_manifest_id':old['manifest_id'],
                'heldout_access':False,'source_sha256':__import__('hashlib').sha256(source.read_bytes()).hexdigest()}
    manifest=build_manifest(records,seed=0,provenance=provenance)
    out.mkdir(parents=True,exist_ok=True)
    for filename in ['manifest.json','records.jsonl']:
        if (out/filename).exists():raise FileExistsError(out/filename)
    write_manifest(out/'manifest.json',manifest);save_records(out/'records.jsonl',records)
    print(json.dumps({'pairs':counts,'manifest':manifest['manifest_id'],'same_67_dev':True,'heldout_access':False}),flush=True)


def run(root,live,prior_attempts=()):
    output=root/('live' if live else 'offline')
    if output.exists():raise FileExistsError(output)
    records=load_records(root/'records.jsonl')
    if live and not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY']=getpass.getpass('OpenAI API key (hidden): ')
    prior=PRIOR_COMMITTED_USD
    for path in prior_attempts:
        ledger=json.loads(path.read_text());prior+=ledger['spent_usd']+ledger['reserved_usd']
    cap=min(NEW_CAP,10-prior)
    if not 0<cap<=NEW_CAP:raise ValueError('no authorized budget remaining')
    budget=Budget(max_calls=12000,max_seconds=14400,max_cost_usd=cap)
    llm=PaperOpenAILLM('gpt-6-luna',budget=budget,max_usd=cap,timeout=120) if live else FixtureLLM(budget=budget)
    factories={m:(lambda user,m=m:create_method(m,llm,seed=0,max_calls=12000,
               cache_dir=root/('cache-live' if live else 'cache-offline'),**CONFIG)) for m in ('m0','m1','m2','m3')}
    if live:llm.recovery_path=root/'response-envelopes.jsonl'
    stop=threading.Event()
    def progress():
        while not stop.wait(30):
            state={'usage':budget.summary(),'concurrency':getattr(llm,'taste_workers',16)}
            if live:state['budget']=llm.cost_summary()
            (root/('live-progress.json' if live else 'offline-progress.json')).write_text(json.dumps(state,indent=2))
            print(json.dumps(state),flush=True)
    monitor=threading.Thread(target=progress,daemon=True);monitor.start()
    try:
        report=run_fidelity(records,root/'manifest.json',factories,output,'hobbhahn_history_dev',run_config={
            'backend':'openai' if live else 'offline','model':llm.model,'settings':CONFIG,'heldout_access':False,
            'purpose':'agreement with AI-inferred labels, not verified researcher ground truth',
            'prior_committed_usd':prior,'prior_attempt_ledgers':[str(p) for p in prior_attempts],'new_cap_usd':cap,'total_authorized_usd':10})
        for method in ('m2','m3'):
            try:
                bundle=build_bundle(output,records,root/'manifest.json',method=method,export_dir=output/'exports'/method,max_examples_per_method=12)
                write_bundle(bundle,output/(method+'-bundle.json'));build_viewer(bundle,output/(method+'-viewer.html'))
            except Exception as exc:
                (output/(method+'-export-error.txt')).write_text(type(exc).__name__+': '+str(exc))
        print(json.dumps({'status':report['status'],'methods':{m:{k:v for k,v in d.items() if k not in ('per_user',)} for m,d in report['methods'].items()},'budgets':report['backend_budgets']}),flush=True)
    finally:
        stop.set();monitor.join()
        if live:(root/'final-budget.json').write_text(json.dumps(llm.cost_summary(),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','offline','live'])
    p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--previous-manifest',type=Path)
    p.add_argument('--prior-attempt-budget',type=Path,action='append',default=[])
    a=p.parse_args()
    if a.mode=='prepare':
        if not a.source or not a.previous_manifest:p.error('prepare requires source and previous-manifest')
        prepare(a.source,a.previous_manifest,a.output)
    else:run(a.output,a.mode=='live',a.prior_attempt_budget)
