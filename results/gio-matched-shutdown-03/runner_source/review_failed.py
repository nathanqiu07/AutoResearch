"""Recover a terminal failed audit and optionally review it once. Never reruns an audit.
Default is offline preparation. --execute performs only the originally approved
GPT-5.1 primary review, using the remainder of the original run allocation.
"""
import argparse
import asyncio
import getpass
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'harness/petri'))
from preflight import write
from prepare import sha
from review import build_review_prompt, validate_review
from run_baseline import review_context
from transcript import render, split_assistant


def recover(run,out):
    from inspect_ai.log import read_eval_log
    from inspect_ai.model import ChatMessage
    from pydantic import TypeAdapter
    if not (run/'failure.json').exists():raise ValueError('Only a terminal failed audit can be recovered')
    paths=list((run/'baseline/logs').glob('*.eval'))
    if len(paths)!=1:raise ValueError('Expected one original Inspect log')
    log=read_eval_log(str(paths[0]))
    if log.status not in ('error','cancelled') or len(log.samples or [])!=1:
        raise ValueError('Expected one terminal failed native sample')
    sample=log.samples[0]
    target=sample.store['AuditStore:target']
    messages=TypeAdapter(list[ChatMessage]).validate_python(target['messages'])
    row={'seed_id':sample.metadata.get('seed_id','v2_seed_48'),
         'transcript':render(messages),
         'reasoning':'\n\n'.join(split_assistant(m)[0] for m in messages if m.role=='assistant' and split_assistant(m)[0]),
         'error':str(sample.error.message) if sample.error else 'Original audit failed',
         'recovery_source':'Native AuditStore target messages, final state; not reconstructed from imagined content',
         'native_log_sha256':sha(paths[0])}
    settings=json.loads((run/'settings.json').read_text())
    tools,structure=review_context(sample,settings['max_auditor_turns'])
    structure.update(termination='execution_error',original_error=row['error'],
                     truncated_response_excluded=True,
                     explanation='Only accepted native messages are in this transcript. The last provider response hit its output cap and was not appended or acted upon. The separate raw response remains preserved.')
    seed=json.loads((run/'packet/seed.json').read_text())
    instructions=(run/'packet/review-instructions.txt').read_text()
    prompt,sources=build_review_prompt(seed,row,tools,structure,instructions)
    out.mkdir(parents=True,exist_ok=False)
    write(out/'recovered-audit.json',row);write(out/'run-structure.json',structure)
    write(out/'target-tools.json',tools);write(out/'primary-review-sources.json',sources)
    (out/'primary-review-prompt.txt').write_text(prompt)
    write(out/'native-stats.json',log.stats.model_dump(mode='json'))
    write(out/'recovery-provenance.json',{'native_log_sha256':sha(paths[0]),
        'failed_run_code_version':(run/'CODE_VERSION').read_text().strip(),
        'recovery_code_version':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'script_sha256':sha(Path(__file__)),'review_module_sha256':sha(Path(__file__).with_name('review.py')),
        'instructions_sha256':sha(run/'packet/review-instructions.txt'),
        'phase':'postmortem_only_not_a_completed_audit','paid_calls':0})
    write(out/'checksums.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})


def remaining_cap(parent,configured_cap):
    # The existing halted ledger is immutable; charge a separate review ledger
    # against its remaining allocation, not a second $5 allocation.
    if parent['cap_usd']!=configured_cap or configured_cap>5:
        raise ValueError('Expected the same approved $5 allocation')
    spent=parent['charged_or_reserved_usd']
    if not math.isfinite(spent) or not 0<=spent<=configured_cap:raise ValueError('Invalid parent ledger spend')
    remaining=configured_cap-spent
    if remaining<=0:raise ValueError('Original allocation exhausted')
    return remaining


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args();out=a.run/'postmortem-review'
    if not out.exists():recover(a.run,out)
    for name,digest in json.loads((out/'checksums.json').read_text()).items():
        if sha(out/name)!=digest:raise ValueError('Prepared recovery evidence changed: '+name)
    if not a.execute:print('Offline recovery prepared; no model calls.');return
    if (out/'ledger.json').exists():raise ValueError('Review already attempted; no automatic rerun')
    parent=json.loads((a.run/'ledger.json').read_text());settings=json.loads((a.run/'settings.json').read_text())
    cap=remaining_cap(parent,settings['run_cap_usd'])
    key=os.environ.get('OPENAI_API_KEY') or getpass.getpass('OPENAI_API_KEY (hidden): ')
    if not key:raise ValueError('OpenAI key required')
    from roles import roles
    from budget import Ledger,attach
    from inspect_ai.model import ChatMessageUser
    ledger=Ledger(out/'ledger.json',cap);ledger.save();raw=out/'calls';raw.mkdir()
    write(out/'execution-provenance.json',{'code_version':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'script_sha256':sha(Path(__file__)),'parent_ledger_sha256':sha(a.run/'ledger.json'),
        'models':settings['models'],'judge_generation':settings['generation']['judge'],
        'postmortem_only':True,'original_cap_usd':settings['run_cap_usd'],'remaining_allocation_usd':cap})
    (out/'execution-source.py').write_text(Path(__file__).read_text())
    async def generate():
        rr=roles(api_key='offline-unused',openai_key=key)
        try:
            attach(rr['judge'],'judge',ledger,raw)
            response=await rr['judge'].generate([ChatMessageUser(content=(out/'primary-review-prompt.txt').read_text())])
            return response.completion
        finally:
            for model in rr.values():await model.__aexit__(None,None,None)
    try:
        reply=asyncio.run(generate());(out/'primary-review-reply.txt').write_text(reply)
        payload=reply.strip()
        if payload.startswith('```') and payload.endswith('```'):payload='\n'.join(payload.splitlines()[1:-1])
        review=validate_review(json.loads(payload),json.loads((out/'primary-review-sources.json').read_text()))
        review.update(review_phase='postmortem_of_failed_audit',audit_completed=False)
    except Exception as exc:
        review={'status':'review_failed','error_type':type(exc).__name__,
            'review_phase':'postmortem_of_failed_audit','audit_completed':False}
    write(out/'primary-review.json',review)
    write(out/'combined-budget.json',{'original_cap_usd':settings['run_cap_usd'],
        'original_charged_or_reserved_usd':parent['charged_or_reserved_usd'],
        'postmortem_charged_or_reserved_usd':ledger.held,
        'total_charged_or_reserved_usd':parent['charged_or_reserved_usd']+ledger.held,
        'no_new_audit':True})
    print(json.dumps({'review_status':review['status'],'total_usd':parent['charged_or_reserved_usd']+ledger.held}))

if __name__=='__main__':main()
