"""One GPT-5.1 access check through the pilot's native Inspect role; no audits."""
import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
import time
from roles import roles
from budget import Ledger, attach

async def check(out, key):
    models=roles(api_key='unused-no-openrouter-call',openai_key=key)
    ledger=Ledger(out/'ledger.json',1.0)
    attach(models['judge'],'judge',ledger,out)
    report={'scope':'one GPT-5.1 connection call; no Petri audit',
            'model':'openai/gpt-5.1','reasoning_effort':'high','max_tokens':32000,
            'transport_retries':0,'reservation_cap_usd':1.0,'status':'started'}
    start=time.monotonic()
    try:
        result=await models['judge'].generate('Reply with exactly the word OK. This is an API connection check.')
        report['reply']=result.completion
        report['usage']=result.usage.model_dump(mode='json') if result.usage else None
        report['status']='passed' if result.completion.strip()=='OK' else 'unexpected_reply'
        report['stop_reason']=result.stop_reason
    except Exception as e:
        report['status']='failed';report['error_type']=type(e).__name__
        if hasattr(e,'status_code'):report['http_status']=e.status_code
        if hasattr(e,'code'):report['error_code']=e.code
    finally:
        report['seconds']=time.monotonic()-start
        report['cost_estimate_or_reserved_usd']=ledger.held
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        for model in models.values():await model.__aexit__(None,None,None)
    print(json.dumps(report,indent=2))
    return report['status']=='passed'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    key=os.environ.get('OPENAI_API_KEY') or getpass.getpass('OpenAI API key (hidden): ')
    if not asyncio.run(check(args.out,key)):raise SystemExit(1)
