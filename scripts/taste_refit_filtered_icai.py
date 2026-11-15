"""Refit an existing user-model implementation on filtered, frozen learning/val IDs only."""
import argparse, dataclasses, getpass, hashlib, json, os, sys
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser()
    for name in ['runtime-root','kept','split-manifest','output','heldout']:
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--method',choices=['m2','m3'],default='m3')
    ap.add_argument('--max-usd',type=float,default=3)
    ap.add_argument('--plan-only',action='store_true')
    a=ap.parse_args();sys.path.insert(0,str(a.runtime_root.resolve()))
    from autoresearch.taste.usermodel import Choice,load_model
    from autoresearch.taste.methods import create_method
    from autoresearch.taste.paper_backend import PaperOpenAILLM
    from autoresearch.llm import Budget
    source=json.loads(a.split_manifest.read_text()); split=source['users']['subject']
    rows=[json.loads(l) for l in a.kept.read_text().splitlines() if l.strip()]
    ids={r['example_id'] for r in rows}; assert len(ids)==len(rows)==85
    selected={k:sorted(ids&set(split[k])) for k in ['history','val','test']}
    assert sum(map(len,selected.values()))==85
    assert not(set(selected['history'])&set(selected['val']) or set(selected['history'])&set(selected['test']) or set(selected['val'])&set(selected['test']))
    config=dict(full_history=True,k='all',max_candidates=80,max_principles=5,
                num_search_candidates=10,max_bootstrapped_demos=64,workers=16,adaptive_workers=True)
    manifest=dict(original_manifest_id=source['manifest_id'],splits=selected,
                  counts={k:len(v) for k,v in selected.items()},kept_sha256=sha(a.kept),
                  heldout_sha256=sha(a.heldout),settings=config,backend='gpt-6-luna',max_usd=a.max_usd,
                  dev_evaluated=False,heldout_evaluated=False,reasons_removed=True,
                  method=a.method,purpose='Review a model from AI-inferred, model-filtered researcher choices; not a generalization claim')
    print(json.dumps(manifest,indent=2),flush=True)
    if a.plan_only:return
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    os.environ['OPENAI_API_KEY']=os.environ.get('OPENAI_API_KEY') or getpass.getpass('OpenAI API key (hidden): ')
    llm=PaperOpenAILLM(model='gpt-6-luna',budget=Budget(max_calls=2500,max_seconds=1200),max_usd=a.max_usd,max_request_attempts=5)
    llm.retry_path=str(a.output/'retries.jsonl');llm.recovery_path=str(a.output/'recoveries.jsonl')
    model=create_method(a.method,llm,seed=0,cache_dir=a.output/'cache',trace_path=a.output/'trace.jsonl',max_calls=2500,**config)
    lookup={r['example_id']:r for r in rows}
    def choices(which):
        return [Choice(**dict(lookup[i],reason='')) for i in selected[which]]
    status={'status':'started'}
    try:
        model.fit(choices('history'),choices('val'))
        model.save(a.output/'usermodel.json')
        assert load_model(a.output/'usermodel.json',llm).artifacts()==model.artifacts()
        art=dataclasses.asdict(model.artifacts())
        (a.output/'artifacts.json').write_text(json.dumps(art,indent=2))
        status=dict(status='complete',method=a.method,persona=art['persona'],exemplar_count=len(art['exemplars']),
                    principles=art['principles'],validation_sizes=art['metadata'].get('validation_sizes'),
                    search_before=art['metadata'].get('search_before'),search_after=art['metadata'].get('search_after'),
                    concurrency_trace=art['metadata'].get('concurrency_trace'),save_load_verified=True)
    except Exception as e:
        status={'status':'failed','error_type':type(e).__name__,'error':str(e)}
        raise
    finally:
        assert sha(a.kept)==manifest['kept_sha256'] and sha(a.heldout)==manifest['heldout_sha256']
        status['budget']=llm.cost_summary()
        (a.output/'report.json').write_text(json.dumps(status,indent=2))
        print(json.dumps(status,indent=2),flush=True)
if __name__=='__main__':main()
