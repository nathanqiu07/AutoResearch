"""Offline replay of saved live responses through Inspect and Petri; no network calls."""
import argparse
import asyncio
import importlib.metadata
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'harness'/'petri'))
from inspect_ai.model._providers.openrouter import OpenRouterAPI
from inspect_ai.tool import ToolInfo
from openai.types.chat import ChatCompletion
from petri.transcript.transcript import TranscriptEvent,AddMessage
from transcript import record_from_sample
from autoresearch.llm import LLM,parse_openai_chat
from autoresearch.research.measure import Measurer,Models

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True);a=p.parse_args()
provider=OpenRouterAPI('nvidia/nemotron-3-ultra-550b-a55b:free',api_key='offline-placeholder-not-a-key')
events=[]; checks=[]
for n in (1,2):
 raw=json.loads((a.artifacts/f'response-{n}.json').read_text())
 req=json.loads((a.artifacts/f'request-{n}.json').read_text())
 tools=[ToolInfo(**t['function']) for t in req['tools']]
 msg=provider.chat_choices_from_completion(ChatCompletion.model_validate(raw),tools)[0].message
 expected=raw['choices'][0]['message']['reasoning']
 reasoning=[c.reasoning for c in msg.content if getattr(c,'type',None)=='reasoning']
 assert any(expected==r for r in reasoning),'Inspect lost or changed reasoning'
 assert parse_openai_chat(raw)[0]==expected,'repo parser changed reasoning'
 replay=asyncio.run(provider.messages_to_openai([msg]))
 assert replay[0].get('reasoning_details'),'tool continuity loses reasoning details'
 event=TranscriptEvent(view='target',edit=AddMessage(message=msg))
 events.append(event.model_dump(mode='json'))
 checks.append({'response':n,'reasoning_chars':len(expected),'inspect_retains_exact_reasoning':True,'outgoing_replay_retains_reasoning_details':True,'tool_calls':len(msg.tool_calls or [])})
row=record_from_sample(SimpleNamespace(id='offline-replay-only',metadata={'seed_id':'offline-replay-only','variant':'v2','tools':'simulated'},epoch=1,store={'AuditStore:events':events},scores={},error=None))
for n in (1,2):
 expected=json.loads((a.artifacts/f'response-{n}.json').read_text())['choices'][0]['message']['reasoning']
 assert expected in row['reasoning'],'Petri record lost reasoning'
class CaptureJudge(LLM):
 name='offline-capture'
 def complete(self,prompt,**kwargs):
  self.prompt=prompt
  return json.dumps({'verbalized':0,'opportunity':1,'scorable':1,'bait_reached':1,'behavior':'unclear'})
judge=CaptureJudge();m=Measurer(Models(judge,judge,judge));m._audit(row['transcript'],row['reasoning'])
assert row['reasoning'] in judge.prompt,'reasoning did not reach judge input'
(a.artifacts/'offline-judge-input.txt').write_text(judge.prompt)
(a.artifacts/'offline-petri-record.json').write_text(json.dumps(row,indent=2))
result={'status':'passed','mode':'offline replay of two saved live responses, not a live Petri audit','checks':checks,'petri_record_retains_both_reasoning_traces':True,'judge_input_contains_reasoning':True,'judge_output_is_fixture_not_measurement':True,'dependencies':{n:importlib.metadata.version(n) for n in ('inspect_ai','petri','openai','pydantic')}}
(a.artifacts/'integration-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
