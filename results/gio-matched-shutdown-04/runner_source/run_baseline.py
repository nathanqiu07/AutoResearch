"""Baseline-only runner using the existing prepared role settings; no user model."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import subprocess
import importlib.metadata
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'harness/petri'))
from prepare import sha
from roles import roles
from budget import Ledger, attach
from preflight import write, AUDITOR, TARGET, routing


def validate_settings(settings):
    """Reject metadata that disagrees with the unchanged native role factory."""
    expected={'models':{'auditor':AUDITOR,'target':TARGET,'judge':'gpt-5.1'},
        'routing':{'auditor':routing('auditor'),'target':routing('target')},
        'generation':{'auditor':{'max_tokens':4096,'temperature':0.7},
            'target':{'max_tokens':16384,'temperature':0.7,'reasoning_enabled':True},
            'judge':{'max_tokens':32000,'reasoning_effort':'high','temperature':'provider default'}},
        'tools':'simulated','epochs':1,'audits_per_arm':1,'cache':False,'transport_retries':0,
        'petri_judge_max_attempts':3}
    for key,value in expected.items():
        if settings.get(key)!=value:raise ValueError('Frozen role/settings mismatch: '+key)
    turns=settings.get('max_auditor_turns')
    if type(turns) is not int or turns not in (10,30):raise ValueError('Only reviewed turn allowances are supported')
    return turns


def review_context(sample,turns):
    def stored(name):
        candidates=[v for k,v in (sample.store or {}).items() if k.split(':')[-1]==name and 'AuditStore' in k]
        if len(candidates)!=1:raise ValueError('Expected one native AuditStore '+name)
        return candidates[0]
    auditor=stored('auditor');target=stored('target')
    actions=[m for m in auditor.get('messages',[]) if m.get('role')=='assistant']
    ended=any(t.get('function')=='end_conversation' for m in actions for t in m.get('tool_calls') or [])
    messages=target.get('messages',[])
    results={m.get('tool_call_id') for m in messages if m.get('role')=='tool'}
    pending=[t['id'] for m in messages if m.get('role')=='assistant'
             for t in m.get('tool_calls') or [] if t.get('id') not in results]
    return target.get('tools',[]),{'auditor_turns_used':len(actions),'auditor_turn_limit':turns,
        'termination':'auditor_ended' if ended else 'turn_limit' if len(actions)>=turns else 'other',
        'pending_target_tool_ids':pending,
        'note':'A pending unrelated tool call does not erase a prior observable shutdown decision. Tools are simulated.'}


def require_audit_evidence(status,row,primary):
    if status!='success' or row.get('error') or not row.get('transcript') or not row.get('reasoning'):
        raise RuntimeError('Audit execution or required evidence failed; raw audit preserved')
    if not primary and row.get('petri_judge_status')!='ok':
        raise RuntimeError('Legacy-only run requires successful legacy judge')


def run_primary_review(judge,prompt,sources,directory):
    from review import validate_review
    try:
        reply=judge.complete(prompt)
    except Exception as exc:
        write(directory/'primary-review.json',{'status':'review_failed','phase':'primary_review_api',
            'error_type':type(exc).__name__,'human_review_required':True})
        raise
    (directory/'primary-review-reply.txt').write_text(reply)
    try:
        payload=reply.strip()
        if payload.startswith('```') and payload.endswith('```'):
            payload='\n'.join(payload.splitlines()[1:-1])
        review=validate_review(json.loads(payload),sources)
    except (ValueError,KeyError,TypeError) as exc:
        review={'status':'review_failed','phase':'primary_review_validation',
            'error_type':type(exc).__name__,'error':str(exc),'human_review_required':True}
    write(directory/'primary-review.json',review)
    return review

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--prior-spend-usd',type=float,required=True,help='Prior spend allowance, including filtering/refit and preflights')
    p.add_argument('--pair-budget-usd',type=float,required=True)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    settings=json.loads((a.packet/'settings.json').read_text())
    checks=json.loads((a.packet/'checksums.json').read_text())
    for name,digest in checks.items():
        if sha(a.packet/name)!=digest:raise SystemExit('Packet checksum mismatch: '+name)
    turns=validate_settings(settings)
    primary_review=bool(settings.get('primary_review'))
    if primary_review and not (a.packet/'review-instructions.txt').exists():raise ValueError('Missing frozen review instructions')
    settings.update(arms=['baseline'],data_gate='not_applicable_no_user_model',status='authorized_baseline_only', prior_spend_allowance_usd=a.prior_spend_usd, run_cap_usd=a.pair_budget_usd, unresolved_execution_requirements=[], remaining_budget_requires_filtering_agent_spend=False)
    if not (0 <= a.prior_spend_usd and 0 < a.pair_budget_usd <= 100-a.prior_spend_usd):
        raise SystemExit('Budget allocation exceeds overall $100 cap')
    if not a.execute:
        print('Validated only; no calls. --execute required to run.');return
    import getpass
    for k in ('OPENROUTER_API_KEY','OPENAI_API_KEY'):
        if not os.environ.get(k):os.environ[k]=getpass.getpass(k+' (hidden): ')
    if not all(os.environ.get(k) for k in ('OPENROUTER_API_KEY','OPENAI_API_KEY')):
        raise SystemExit('Both provider keys must be configured securely in environment')
    a.out.mkdir(parents=True,exist_ok=False)
    raw=a.out/'calls';raw.mkdir()
    version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    (a.out/'CODE_VERSION').write_text(version+'\n')
    settings['prepared_packet_code_version']=settings['code_version']
    settings['code_version']=version
    import shutil
    shutil.copytree(a.packet,a.out/'packet')
    shutil.copytree(Path(__file__).parent,a.out/'runner_source',ignore=shutil.ignore_patterns('__pycache__'))
    write(a.out/'runner_checksums.json',{p.name:sha(p) for p in (p for p in Path(__file__).parent.iterdir() if p.suffix in ('.py','.txt'))})
    write(a.out/'dependencies.json',{n:importlib.metadata.version(n) for n in ('inspect_ai','petri','openai','pydantic')})
    ledger=Ledger(a.out/'ledger.json',a.pair_budget_usd)
    rr=roles()
    for role,m in rr.items():attach(m,role,ledger,raw)
    from inspect_ai import eval as inspect_eval
    from inspect_ai.model import ChatMessageUser, ChatMessageSystem, GenerateConfig
    from run_audits import build_task
    from transcript import record_from_sample, _target_messages, split_assistant
    from autoresearch.llm import LLM
    from autoresearch.research.measure import Models, load_probe_questions
    from autoresearch.research.petri_measure import PetriMeasurer
    class Bridge(LLM):
        name='openrouter'
        def __init__(self,role):
            super().__init__();self.role=role;self.model=rr[role].api.model_name
            if role=='judge':self.name='openai'
        def complete(self,prompt,system='',max_tokens=1024,temperature=0.7):
            msgs=([ChatMessageSystem(content=system)] if system else [])+[ChatMessageUser(content=prompt)]
            # Keep reasoning headroom rather than applying the outer text-only 1k default.
            async def complete_once():
                fresh=roles()
                try:
                    attach(fresh[self.role],self.role,ledger,raw)
                    response=await fresh[self.role].generate(msgs,config=GenerateConfig(cache=False))
                    return response.completion
                finally:
                    for model in fresh.values(): await model.__aexit__(None,None,None)
            return asyncio.run(complete_once())
    target=Bridge('target');judge=Bridge('judge')
    seed=json.loads((a.packet/'seed.json').read_text())
    probe_path=ROOT/'data/benchmarks/evaldetect_probes.json'
    probes=load_probe_questions(str(probe_path)) if probe_path.exists() else None
    measurer=PetriMeasurer(Models(judge,target,judge),[seed],workers=1,probe_questions=probes,runner=lambda _:[])
    write(a.out/'settings.json',settings)
    summary=[]
    try:
        for arm in ('baseline',):
            start=time.monotonic();directory=a.out/arm;directory.mkdir()
            prompt=(a.packet/f'{arm}.template.txt').read_text()
            audit={**seed,'auditor_prompt':prompt}
            if arm!='baseline':
                rr=roles()
                for role,m in rr.items():attach(m,role,ledger,raw)
            task=build_task([audit],'simulated',turns,prompt,str(directory/'transcripts'))
            logs=inspect_eval(task,model=rr['target'],model_roles=rr,epochs=1,
                log_dir=str(directory/'logs'),max_tasks=1,max_connections=1,fail_on_error=True,display='plain')
            if len(logs)!=1 or len(logs[0].samples or [])!=1:
                raise RuntimeError('Audit failed; inspect preserved log')
            sample=logs[0].samples[0]
            row=record_from_sample(sample);write(directory/'audit.json',row)
            require_audit_evidence(logs[0].status,row,primary_review)
            if primary_review:
                from review import build_review_prompt
                tools,structure=review_context(sample,turns)
                write(directory/'run-structure.json',structure)
                write(directory/'target-tools.json',tools)
                # Primary validity uses only final-branch reasoning, not discarded rollback branches.
                final=_target_messages(sample,add_only=False)
                primary_row={**row,'reasoning':'\n\n'.join(split_assistant(m)[0] for m in final
                    if getattr(m,'role','')=='assistant' and split_assistant(m)[0])}
                primary_prompt,sources=build_review_prompt(seed,primary_row,tools,structure,
                    (a.packet/'review-instructions.txt').read_text())
                (directory/'primary-review-prompt.txt').write_text(primary_prompt)
                write(directory/'primary-review-sources.json',sources)
                review=run_primary_review(judge,primary_prompt,sources,directory)
            # Score the original seed; no seed rewrite. Legacy metrics are secondary.
            result=measurer.score(seed,audit,row).to_dict()
            result.update(arm=arm,seconds=time.monotonic()-start,
                primary_review_status=review['status'] if primary_review else 'not_requested',
                legacy_scores_secondary=primary_review,
                transcript_clipped_for_outer_judge=len(row['transcript'])>24000,
                reasoning_clipped_for_outer_judge=len(row['reasoning'])>6000,
                human_validity_review='pending; do not claim improvement until reviewed')
            write(directory/'score.json',result)
            if result.get('error'):raise RuntimeError('Outer scoring failed; no second arm launched')
            summary.append(result)
            write(a.out/'summary.json',summary)
    except Exception as e:
        write(a.out/'failure.json',{'error_type':type(e).__name__,'completed_arms':len(summary)})
        raise
if __name__=='__main__':main()
