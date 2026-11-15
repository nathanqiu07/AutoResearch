"""Full-history paper stages. Explicit adaptations are recorded in each artifact.

SynthesizeMe caches one label-hidden bootstrap pass per stage, then searches
seeded subsets. ICAI uses embedding k-means, per-principle A/B/irrelevant votes,
three repeats, filtering and a validation comparison of five versus ten rules.
"""
import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor

from ..usermodel import UserModel
from .common import bounded_int, text_field


def compact_choice(row):
    return {k:getattr(row,k) for k in ('context','a_text','b_text','chosen')}


def parallel(model, jobs):
    """Separate request objects prevent trace races; charge shared usage once.

    Each job receives its own worker, with the same backend and cache. Jobs are
    drained even on failure so no requests survive the calling stage.
    """
    before = model.llm.budget.summary()
    retries_before=len(getattr(model.llm,"retry_events",[]))
    def work(job):
        w = UserModel(model.llm, seed=model.seed, cache_dir=model.cache_dir,
                      max_calls=model.max_calls)
        w.method_id, w.prompt_version = model.method_id, model.prompt_version
        try:
            return job(w), None, w
        except Exception as exc:
            return None, exc, w
    workers = bounded_int(model.config,'workers',16,minimum=1,maximum=32)
    if model.config.get('adaptive_workers'):
        workers=getattr(model.llm,'taste_workers',workers)
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(work, jobs))
    after = model.llm.budget.summary()
    for key in ('input_tokens','output_tokens','cost_usd'):
        model.cost[key] += after[key] - before[key]
    model.cost['cost_available'] = model.cost['cost_usd'] > 0
    for _, _, w in outcomes:
        for key in ('calls','cache_hits'):
            model.cost[key] += w.cost[key]
        if model.trace_path and hasattr(w,'_trace_record'):
            with model.trace_path.open('a') as f:
                f.write(json.dumps(w._trace_record,ensure_ascii=False)+'\n')
    errors=sum(error is not None for _,error,_ in outcomes)
    calls=sum(w.cost['calls'] for _,_,w in outcomes)
    retry_failures=len(getattr(model.llm,'retry_events',[]))-retries_before
    model._artifacts.metadata.setdefault('concurrency_trace',[]).append(
        {'workers':workers,'requests':calls,'errors':errors,'retry_failures':retry_failures,'seconds':time.monotonic()-started})
    if model.config.get('adaptive_workers'):
        model.llm.taste_workers=16 if errors or retry_failures else (32 if calls>=64 else workers)
    for _, error, _ in outcomes:
        if error: raise error
    return [value for value,_,_ in outcomes]


def score(model, rows, persona='', demos=(), principles=()):
    predictions = parallel(model, [lambda w,c=c:w._predict_with(
        c.context,[c.a_text,c.b_text],persona=persona,exemplars=demos,principles=principles) for c in rows])
    return sum(p.choice==c.chosen for p,c in zip(predictions,rows))/len(rows)


def bootstrap(model, history, persona):
    predictions = parallel(model,[lambda w,c=c:w._predict_with(
        c.context,[c.a_text,c.b_text],persona=persona) for c in history])
    accepted, trace = [], []
    for c,p in zip(history,predictions):
        ok = p.choice==c.chosen
        trace.append({'id':c.identity,'choice':p.choice,'accepted':ok,'rationale':p.rationale})
        if ok:
            accepted.append(dict(id=c.identity,**compact_choice(c),rationale=p.rationale))
    return accepted, trace


def search(model, history, val, accepted, persona, include_empty):
    cap = bounded_int(model.config,'max_bootstrapped_demos',64,minimum=1,maximum=236)
    trials = bounded_int(model.config,'num_search_candidates',10,minimum=1,maximum=30)
    raw = [dict(id=c.identity,**compact_choice(c)) for c in history]
    def fill(examples):
        ids = {x['id'] for x in examples}
        extra = [x for x in raw if x['id'] not in ids]
        return examples + random.Random(model.seed).sample(extra,min(max(0,4-len(examples)),len(extra)))
    candidates = ([[]] if include_empty else [])
    candidates += [random.Random(model.seed).sample(raw,min(4,len(raw))),fill(accepted[:cap])]
    for seed in range(trials):
        pool = list(accepted);random.Random(model.seed+seed).shuffle(pool)
        size = random.Random(model.seed+seed).randint(1,cap)
        candidates.append(fill(pool[:size]))
    trace=[]
    for i,demos in enumerate(candidates):
        accuracy=score(model,val,persona,demos)
        trace.append({'candidate':i,'ids':[d['id'] for d in demos],'accuracy':accuracy})
    # Stable ties preserve the first candidate, as in the released optimizer.
    index=max(range(len(trace)),key=lambda i:trace[i]['accuracy'])
    return candidates[index], trace


def fit_synthesizeme(model, history, val):
    meta=model._artifacts.metadata
    accepted,meta['bootstrap_before']=bootstrap(model,history,'')
    demos,meta['search_before']=search(model,history,val,accepted,'',False)
    instruction=("Given user judgements on prior conversations and tentative explanations for them, "
                 "concisely build a persona describing this person's preferences. Infer only supported "
                 "traits, retain conditions and uncertainty. Return {\"persona\":\"text\"}.")
    persona=text_field(model._json(instruction,{'past_judgements':demos}),'persona',20000)
    model._artifacts.persona=persona
    accepted,meta['bootstrap_after']=bootstrap(model,history,persona)
    model._artifacts.exemplars,meta['search_after']=search(model,history,val,accepted,persona,True)
    meta.update(source='https://arxiv.org/html/2506.05598',
        adaptation='Generic published persona instruction, not cross-user MIPRO training. '
                   'One cached label-hidden bootstrap pass over ALL history per stage; random subsets of '
                   'successful traces rather than regenerating traces for every trial. '
                   'Up to 64 bootstrapped examples; 10 random trials plus released-code controls per stage. '
                   'Independent pair predictions, no batched-choice scoring. No invented principle weights.',
        prediction_components=['persona','selected_history_examples'],
        persona_prompt=instruction,verification_status='validation_selected_not_independently_verified')


def kmeans_representatives(vectors, count, seed):
    """Seeded k-means with random member selection, no external dependency."""
    if not vectors or any(len(v)!=len(vectors[0]) for v in vectors):
        raise ValueError('invalid embedding matrix')
    if any(not math.isfinite(x) for v in vectors for x in v):raise ValueError('nonfinite embeddings')
    count=min(count,len(vectors));rng=random.Random(seed)
    centers=[vectors[i][:] for i in rng.sample(range(len(vectors)),count)]
    previous=None
    for _ in range(20):
        cn=[sum(x*x for x in c) for c in centers]
        assignments=[min(range(count),key=lambda j:cn[j]-2*sum(a*b for a,b in zip(v,centers[j]))) for v in vectors]
        if assignments==previous:break
        previous=assignments
        groups=[[i for i,c in enumerate(assignments) if c==j] for j in range(count)]
        centers=[[sum(vectors[i][d] for i in group)/len(group) for d in range(len(vectors[0]))]
                 if group else vectors[rng.randrange(len(vectors))][:] for group in groups]
    groups=[[i for i,c in enumerate(assignments) if c==j] for j in range(count)]
    return [{'representative_index':rng.choice(g),'members':g} for g in groups if g]


def fit_icai(model, history, val):
    meta=model._artifacts.metadata
    instruction=('Propose two distinct preference principles explaining the labeled choice. '
                 'Each should start with Select the response that, be concise, and describe a contrast. '
                 'Consider the generation_style. Do not assume a preferred answer is factually correct. '
                 'Return {"principles":["rule","rule"]}.')
    styles=['positive: describe features selected for','negative: describe features selected against']
    jobs=[lambda w,c=c,style=style:w._json(instruction,dict(generation_style=style,**compact_choice(c)))
          for c in history for style in styles]
    generated=parallel(model,jobs);proposals=[]
    for i,result in enumerate(generated):
        rules=result.get('principles')
        if not isinstance(rules,list) or not 1<=len(rules)<=2:raise ValueError('invalid principle proposals')
        for rule in rules:
            rule=text_field({'rule':rule},'rule',600)
            proposals.append({'principle':rule,'history_id':history[i//2].identity,'style':styles[i%2]})
    unique=list(dict.fromkeys(p['principle'] for p in proposals))
    before=model.llm.budget.summary()
    vectors=model.llm.embed(unique)
    after=model.llm.budget.summary()
    for key in ("calls","input_tokens","output_tokens","cost_usd"):
        model.cost[key]+=after[key]-before[key]
    count=bounded_int(model.config,'max_candidates',80,minimum=1,maximum=400)
    clusters=kmeans_representatives(vectors,count,model.seed)
    rules=[unique[c['representative_index']] for c in clusters]
    # Repeated requests have explicit round IDs to prevent accidental cache reuse.
    vote_jobs=[];keys=[]
    for c in history:
        for start in range(0,len(rules),40):
            for repeat in range(3):
                payload={'context':c.context,'options':[c.a_text,c.b_text],
                         'principles':rules[start:start+40],'voting_round':repeat}
                vote_jobs.append(lambda w,p=payload:w._json(
                    'For EACH principle independently, which option does following it favor? '
                    'Vote a, b, or irrelevant (including ties). Ignore generic answer quality. '
                    'Return {"votes":{"0":"a or b or irrelevant",...}} with every zero-based principle index.',p))
                keys.append((c,start))
    results=parallel(model,vote_jobs);votes={}
    for (c,start),result in zip(keys,results):
        batch=rules[start:start+40];out=result.get('votes')
        if (not isinstance(out,dict) or set(out)!={str(i) for i in range(len(batch))}
            or any(v not in ('a','b','irrelevant') for v in out.values())):raise ValueError('invalid principle votes')
        for i in range(len(batch)):votes.setdefault((c.identity,start+i),[]).append(out[str(i)])
    scored=[]
    for i,p in enumerate(rules):
        correct=incorrect=irrelevant=0
        for c in history:
            v=votes[(c.identity,i)]
            v=v[0] if len(set(v))==1 else 'irrelevant'
            if v=='irrelevant':irrelevant+=1
            elif v==c.chosen:correct+=1
            else:incorrect+=1
        scored.append({'principle':p,'correct':correct,'incorrect':incorrect,'irrelevant':irrelevant,
                       'net':correct-incorrect,'relevance':(correct+incorrect)/len(history)})
    # Released code uses correct/total for its min-relevance filter, stricter
    # than the paper's applicable/total description. Preserve and disclose it.
    kept=[p for p in scored if p['correct']>p['incorrect'] and p['correct']/len(history)>=.1]
    kept.sort(key=lambda p:-p['net'])
    sizes=[5,10];comparisons=[]
    for n in sizes:
        principles=[p['principle'] for p in kept[:n]]
        comparisons.append({'limit':n,'n':len(principles),'accuracy':score(model,val,principles=principles)})
    best=max(range(len(comparisons)),key=lambda i:comparisons[i]['accuracy'])
    model._artifacts.principles=[p['principle'] for p in kept[:sizes[best]]]
    meta.update(source='https://arxiv.org/html/2406.06560',principle_proposals=proposals,
        embedding_model=getattr(model.llm,'embedding_model','offline_fixture'),clusters=clusters,
        tested_principles=rules,reconstruction_scores=scored,validation_sizes=comparisons,
        selected_limit=sizes[best],
        adaptation='Two contrastive generation prompts; text-embedding-3-small 256-dimensional k-means '
                   'instead of paper embedding backend. Three unanimous voting repeats, 40 rules/request. '
                   'Released-code correct/total >= 10% filter; rank correct minus incorrect. '
                   'Compare top 5 vs 10 on validation (extension); omit optional final diversity reclustering.',
        verification_status='validation_selected_not_independently_verified',
        principle_evidence=[{'principle':p,'history_ids':sorted({r['history_id'] for r in proposals if r['principle']==p}),
                            'status':'proposal_sources_not_independent_confirmation'} for p in model._artifacts.principles])


def fit_full(model,history,val):
    if not history or not val:raise ValueError('full-history search needs history and validation')
    history=sorted(history,key=lambda c:c.identity);val=sorted(val,key=lambda c:c.identity)
    model._artifacts.metadata.update(full_history=True,selected_history_ids=[c.identity for c in history])
    if model.method_id=='m2':fit_synthesizeme(model,history,val)
    elif model.method_id=='m3':fit_icai(model,history,val)
    else:raise ValueError('unsupported full-history method')
