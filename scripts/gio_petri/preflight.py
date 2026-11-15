"""Four bounded connection calls only; never runs an experiment or a paid judge."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'harness/petri'))
AUDITOR = 'qwen/qwen3-235b-a22b-2507'
TARGET = 'nvidia/nemotron-3-ultra-550b-a55b:free'

def routing(role):
    return {'only': ['deepinfra/fp8' if role == 'auditor' else 'nvidia'],
            'allow_fallbacks': False, 'require_parameters': True,
            'max_price': {'prompt': 0.09, 'completion': 0.55} if role == 'auditor'
                         else {'prompt': 0, 'completion': 0}}

def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def replay(out):
    import asyncio
    from types import SimpleNamespace
    from inspect_ai.model._providers.openrouter import OpenRouterAPI
    from inspect_ai.tool import ToolInfo
    from openai.types.chat import ChatCompletion
    from petri.transcript.transcript import TranscriptEvent, AddMessage
    from transcript import record_from_sample
    from autoresearch.llm import LLM
    from autoresearch.research.measure import Models, Measurer
    events = []
    for index in (1, 2):
        data = json.loads((out / f'target-response-{index}.json').read_text())
        req = json.loads((out / f'target-request-{index}.json').read_text())
        api = OpenRouterAPI(TARGET, api_key='offline-placeholder')
        msg = api.chat_choices_from_completion(ChatCompletion.model_validate(data),
                [ToolInfo(**t['function']) for t in req['tools']])[0].message
        expected = data['choices'][0]['message'].get('reasoning') or data['choices'][0]['message'].get('reasoning_content')
        assert expected, 'No readable target reasoning'
        assert any(getattr(c, 'reasoning', None) == expected for c in msg.content)
        wire = asyncio.run(api.messages_to_openai([msg]))
        assert wire[0].get('reasoning_details'), 'Reasoning lost on tool continuation'
        events.append(TranscriptEvent(view='target', edit=AddMessage(message=msg)).model_dump(mode='json'))
    row = record_from_sample(SimpleNamespace(id='connection-only', metadata={'seed_id':'connection-only',
        'variant':'v2','tools':'simulated'}, epoch=1, store={'AuditStore:events':events}, scores={}, error=None))
    class Capture(LLM):
        name = 'offline-capture'
        def complete(self, prompt, **kwargs):
            self.prompt = prompt
            return json.dumps(dict(verbalized=0, opportunity=1, scorable=1, bait_reached=1, behavior='unclear'))
    judge = Capture()
    Measurer(Models(judge, judge, judge))._audit(row['transcript'], row['reasoning'])
    assert row['reasoning'] and row['reasoning'] in judge.prompt
    (out / 'judge-input-offline.txt').write_text(judge.prompt)
    write(out / 'petri-record-offline.json', row)
    return {'inspect_reasoning_preserved':True, 'tool_continuation_reasoning_preserved':True,
            'petri_record_reasoning_preserved':True, 'outer_judge_input_reasoning_preserved':True,
            'judge_is_offline_capture_not_measurement':True}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--replay-only', action='store_true')
    a = p.parse_args()
    if a.replay_only:
        write(a.out / 'replay.json', replay(a.out)); return
    from inspect_ai.tool import ToolDef
    from petri.tools import default_auditor_tools
    from jsonschema import validate
    a.out.mkdir(parents=True, exist_ok=False)
    key = os.environ.get('OPENROUTER_API_KEY') or getpass.getpass('OpenRouter key (hidden): ')
    report = {'status':'started','scope':'four compatibility calls; no experiment; no paid judge',
              'max_calls':4,'cost_upper_bound_usd':0.02,'calls':[]}
    def call(path, body=None, auth=True):
        headers = {'Content-Type':'application/json'}
        if auth: headers['Authorization'] = 'Bearer ' + key
        request = urllib.request.Request('https://openrouter.ai/api/v1/' + path,
                data=json.dumps(body).encode() if body else None, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    try:
        account = call('key')['data']
        report['account'] = {k:account.get(k) for k in ('limit_remaining','is_free_tier','free_model_daily_requests')}
        schemas = []
        for t in default_auditor_tools():
            d = ToolDef(t)
            schemas.append({'type':'function','function':{'name':d.name, 'description':d.description,
                'parameters':d.parameters.model_dump(exclude_none=True)}})
        assert len({t['function']['name'] for t in schemas}) == len(schemas)
        assert 'send_message' in {t['function']['name'] for t in schemas}
        stock = {'type':'function','function':{'name':'lookup_stock','description':'Look up inventory.',
                 'parameters':{'type':'object','properties':{'item':{'type':'string'}},'required':['item'],'additionalProperties':False}}}
        for role, model in [('auditor', AUDITOR), ('target', TARGET)]:
            write(a.out / f'{role}-endpoints.json', call('models/'+model+'/endpoints', auth=False))
            tools = schemas if role == 'auditor' else [stock]
            instruction = ('Call send_message with message exactly "How many notebooks remain after selling 7 of 12?". '
                           'Do not call any other tool. This is a connection check, not an audit.' if role == 'auditor'
                           else 'Use lookup_stock to check notebooks. We need 7. Tell us whether we can fill the orders and how many remain.')
            messages = [{'role':'system','content':'Follow the requested tool workflow. Be concise.'},
                        {'role':'user','content':instruction}]
            for index in (1,2):
                body = {'model':model, 'provider':routing(role), 'max_tokens':4096, 'temperature':0.6,
                        'messages':messages, 'tools':tools, 'tool_choice':'auto'}
                if role == 'target': body['reasoning']={'enabled':True,'exclude':False}
                # Byte count is a conservative token bound for these ASCII requests.
                upper = (len(json.dumps(body).encode()) * 0.09 + 4096 * 0.55) / 1e6 if role == 'auditor' else 0
                assert upper <= 0.01, 'Request exceeds per-call reservation'
                write(a.out / f'{role}-request-{index}.json', body)
                start=time.monotonic(); data=call('chat/completions',body)
                write(a.out / f'{role}-response-{index}.json', data)
                assert not data.get('error'), 'Provider returned error; inspect saved response'
                choice=data['choices'][0]; msg=choice['message']
                report['calls'].append({'role':role,'index':index,'seconds':time.monotonic()-start,
                    'usage':data.get('usage'),'provider':data.get('provider'),'reserved_usd':upper})
                write(a.out/'report.json',report)
                assert choice['finish_reason'] != 'length', 'Truncated output'
                if index == 1:
                    calls=msg.get('tool_calls') or []
                    name='send_message' if role=='auditor' else 'lookup_stock'
                    assert len(calls)==1 and calls[0]['function']['name']==name, 'Unexpected tool call'
                    args=json.loads(calls[0]['function']['arguments'])
                    schema=next(t['function']['parameters'] for t in tools if t['function']['name']==name)
                    validate(args, schema)
                    messages.append({k:v for k,v in msg.items() if k in ('role','content','tool_calls','reasoning','reasoning_details')})
                    messages.append({'role':'tool','tool_call_id':calls[0]['id'],
                        'content':'Target response: 5 notebooks remain.' if role=='auditor' else '{"item":"notebooks","in_stock":12}'})
                    if role=='auditor':
                        messages.append({'role':'user','content':'Connection check complete. Reply briefly in text; do not call more tools.'})
                else:
                    assert msg.get('content') and not msg.get('tool_calls'), 'No final text answer'
        report['replay'] = replay(a.out)
        report['status']='passed'
    except Exception as e:
        report['status']='failed'
        # Do not persist request headers or exception repr (may contain credentials).
        report['error_type']=type(e).__name__
        if isinstance(e, urllib.error.HTTPError): report['http_status']=e.code
        if isinstance(e, AssertionError): report['check_failure']=str(e)
    finally:
        write(a.out/'report.json', report)
        print(json.dumps(report,indent=2))
    if report['status']!='passed': raise SystemExit(1)

if __name__=='__main__': main()
