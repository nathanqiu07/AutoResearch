"""Budgeted embeddings for the paper-stage ICAI experiment (Gio track only)."""
import json
import math
import os
import urllib.request
from .backends import OpenAILLM


class PaperOpenAILLM(OpenAILLM):
    name='openai-responses-json'
    embedding_model='text-embedding-3-small'

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.recoveries=[]
        self.recovery_path=None

    def complete(self,prompt,**kwargs):
        raw=super().complete(prompt,**kwargs)
        try:
            json.loads(raw)
            return raw
        except json.JSONDecodeError:
            pass
        # Recover envelopes only when every decoded top-level answer agrees.
        # We never choose between competing probability distributions/votes.
        decoder=json.JSONDecoder();objects=[];cursor=0
        expected=set(self.response_format(prompt)['schema']['properties'])
        while cursor<len(raw):
            start=raw.find('{',cursor)
            if start<0:break
            try:
                obj,length=decoder.raw_decode(raw[start:]);cursor=start+length
                if isinstance(obj,dict) and expected<=set(obj):objects.append(obj)
            except json.JSONDecodeError:cursor=start+1
        comparable=lambda obj:{k:v for k,v in obj.items() if k!='rationale'}
        safe=bool(objects) and all(comparable(obj)==comparable(objects[0]) for obj in objects)
        record={'status':'recovered_consensus' if safe else 'rejected_conflicting_or_missing',
                'prompt_sha256':__import__('hashlib').sha256(prompt.encode()).hexdigest(),
                'raw_response':raw,'objects':objects}
        with self._cost_lock:
            self.recoveries.append(record)
            if self.recovery_path:
                with open(self.recovery_path,'a') as stream:stream.write(json.dumps(record)+'\n')
        if not safe:raise ValueError('conflicting or missing JSON answers; raw response retained')
        return json.dumps(objects[0])

    def response_format(self,prompt):
        payload=json.loads(prompt.split('INPUT_JSON:\n',1)[1])
        string={'type':'string'}
        if 'generation_style' in payload:
            props={'principles':{'type':'array','items':string,'minItems':1,'maxItems':2}}
        elif 'voting_round' in payload:
            votes={str(i):{'type':'string','enum':['a','b','irrelevant']} for i in range(len(payload['principles']))}
            props={'votes':{'type':'object','properties':votes,'required':list(votes),'additionalProperties':False}}
        elif 'past_judgements' in payload:
            props={'persona':string}
        else:
            n=len(payload['options'])
            props={'probabilities':{'type':'array','items':{'type':'number','minimum':0,'maximum':1},'minItems':n,'maxItems':n},'rationale':string}
        return {'type':'json_schema','name':'preference_response','strict':True,
                'schema':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}

    def embed(self,texts):
        if not texts or len(texts)>2048 or any(not isinstance(t,str) or len(t.encode())>8000 for t in texts):
            raise ValueError('invalid embedding inputs')
        encoded=json.dumps({'model':self.embedding_model,'input':texts,'dimensions':256}).encode()
        bound=len(encoded)+1000
        # Conservative standard price, including no assumed cache discount.
        rate=.02/1_000_000
        reservation=bound*rate
        with self._cost_lock:
            if self.spent_usd+self.reserved_usd+reservation>self.max_usd or self.budget.exhausted():
                raise RuntimeError('embedding budget exhausted')
            self.reserved_usd+=reservation
        tokens=0;success=False
        try:
            headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['OPENAI_API_KEY']}
            for variable,header in [('OPENAI_ORG_ID','OpenAI-Organization'),('OPENAI_PROJECT_ID','OpenAI-Project')]:
                if os.environ.get(variable):headers[header]=os.environ[variable]
            req=urllib.request.Request('https://api.openai.com/v1/embeddings',encoded,headers)
            with urllib.request.urlopen(req,timeout=self.timeout) as response:data=json.load(response)
            reported=data['usage']['prompt_tokens']
            if isinstance(reported,bool) or not isinstance(reported,int) or not 0<=reported<=bound:raise ValueError('invalid usage')
            tokens=reported
            entries=sorted(data['data'],key=lambda r:r['index'])
            if [r['index'] for r in entries]!=list(range(len(texts))):raise ValueError('embedding alignment')
            vectors=[r['embedding'] for r in entries]
            if any(len(v)!=256 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in v) for v in vectors):
                raise ValueError('invalid embeddings')
            success=True
            return vectors
        except Exception:
            raise RuntimeError('Embedding request failed; reservation retained; no retry') from None
        finally:
            cost=tokens*rate;self.budget.charge(tokens,0,cost)
            with self._cost_lock:
                self.spent_usd+=cost
                if success:self.reserved_usd=max(0,self.reserved_usd-reservation)
