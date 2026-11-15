"""Gated native-Inspect pilot runner. Never runs unless --execute and refit evidence supplied."""
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
from prepare import model_principles, sha
from roles import roles
from budget import Ledger, attach
from preflight import write

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--handoff',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--prior-spend-usd',type=float,required=True,help='Reconciled total including filtering/refit and preflights')
    p.add_argument('--pair-budget-usd',type=float,required=True)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    model_principles(a.model,a.handoff)
    settings=json.loads((a.packet/'settings.json').read_text())
    checks=json.loads((a.packet/'checksums.json').read_text())
    for name,digest in checks.items():
        if sha(a.packet/name)!=digest:raise SystemExit('Packet checksum mismatch: '+name)
    if settings['data_gate']!='passed' or settings['model_sha256']!=sha(a.model):
        raise SystemExit('Packet not built from refitted model')
    if settings['handoff_sha256']!=sha(a.handoff):raise SystemExit('Handoff changed')
    if not (0 <= a.prior_spend_usd and 0 < a.pair_budget_usd <= 100-a.prior_spend_usd):
        raise SystemExit('Budget allocation exceeds overall $100 cap')
    if not a.execute:
        print('Validated only; no calls. --execute required to run.');return
    if not all(os.environ.get(k) for k in ('OPENROUTER_API_KEY','OPENAI_API_KEY')):
        raise SystemExit('Both provider keys must be configured securely in environment')
    a.out.mkdir(parents=True,exist_ok=False)
    raw=a.out/'calls';raw.mkdir()
    (a.out/'CODE_VERSION').write_text(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True))
    write(a.out/'dependencies.json',{n:importlib.metadata.version(n) for n in ('inspect_ai','petri','openai','pydantic')})
    ledger=Ledger(a.out/'ledger.json',a.pair_budget_usd)
    rr=roles()
    for role,m in rr.items():attach(m,role,ledger,raw)
    from inspect_ai import eval as inspect_eval
    from inspect_ai.model import ChatMessageUser, ChatMessageSystem, GenerateConfig
    from run_audits import build_task
    from transcript import record_from_sample
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
    (a.out/'model.json').write_bytes(a.model.read_bytes())
    summary=[]
    try:
        for arm in ('baseline','icai'):
            start=time.monotonic();directory=a.out/arm;directory.mkdir()
            prompt=(a.packet/f'{arm}.template.txt').read_text()
            audit={**seed,'auditor_prompt':prompt}
            if arm!='baseline':
                rr=roles()
                for role,m in rr.items():attach(m,role,ledger,raw)
            task=build_task([audit],'simulated',10,prompt,str(directory/'transcripts'))
            logs=inspect_eval(task,model=rr['target'],model_roles=rr,epochs=1,
                log_dir=str(directory/'logs'),max_tasks=1,max_connections=1,fail_on_error=True,display='plain')
            if len(logs)!=1 or logs[0].status!='success' or len(logs[0].samples or [])!=1:
                raise RuntimeError('Audit failed; inspect preserved log')
            row=record_from_sample(logs[0].samples[0]);write(directory/'audit.json',row)
            if row.get('error') or not row.get('reasoning') or row.get('petri_judge_status')!='ok':
                raise RuntimeError('Missing reasoning or invalid audit/judge result')
            # Same unmodified seed variant in BOTH arms: no asymmetric seed-rewrite judge.
            result=measurer.score(seed,audit,row).to_dict()
            result.update(arm=arm,seconds=time.monotonic()-start,
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
