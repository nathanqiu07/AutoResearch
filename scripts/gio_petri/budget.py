"""One reservation ledger for native Inspect calls across the three roles.
Reserve full context plus maximum output; keep reservation on errors/unknown usage.
Prices: OpenRouter endpoint snapshot and official GPT-5.1 model page (2026-11-14).
"""
import json
import threading
import time

RATES={'auditor':(0.09,0.55,262144), 'target':(0,0,1000000), 'judge':(1.25,10,400000)}
class Ledger:
    def __init__(self, path, cap):
        if cap <= 0: raise ValueError('Budget must be positive')
        self.path=path; self.cap=cap; self.held=0.; self.entries=[]; self.lock=threading.Lock(); self.halted=False
    def save(self):
        self.path.write_text(json.dumps({'cap_usd':self.cap,'charged_or_reserved_usd':self.held,
                                        'entries':self.entries},indent=2)+'\n')
    def reserve(self,role,max_tokens):
        inp,out,context=RATES[role]
        amount=(context*inp + max_tokens*out)/1e6
        with self.lock:
            if self.halted: raise RuntimeError('Ledger halted after previous failure')
            if self.held + amount > self.cap: raise RuntimeError('Insufficient reserved budget; no call made')
            i=len(self.entries); self.held+=amount
            self.entries.append({'role':role,'reserved_usd':amount,'charged_usd':amount,'status':'pending'})
            self.save()
        return i
    def settle(self,i,usage):
        with self.lock:
            e=self.entries[i]
            if usage is not None:
                inp,out,_=RATES[e['role']]
                charge=(usage.input_tokens*inp+usage.output_tokens*out)/1e6
                # Cache savings deliberately ignored. Never release an error reservation.
                self.held+=charge-e['charged_usd'];e['charged_usd']=charge;e['status']='usage_estimate'
                if charge > e['reserved_usd']: e['status']='BOUND_EXCEEDED_STOP'
            else:e['status']='unknown_usage_reservation_retained'
            self.save()
            if e['status']=='BOUND_EXCEEDED_STOP':raise RuntimeError('Cost bound exceeded; stop')

def attach(model,role,ledger,out):
    original=model.api.generate
    async def guarded(input,tools,tool_choice,config):
        maximum=config.max_tokens or model.config.max_tokens
        if not maximum: raise RuntimeError('Output cap required')
        index=ledger.reserve(role,maximum)
        start=time.monotonic()
        try:
            result=await original(input,tools,tool_choice,config)
            output,call=result if isinstance(result,tuple) else (result,None)
            if call:
                (out/f'call-{index:04d}-{role}.json').write_text(call.model_dump_json(indent=2))
            if isinstance(output,Exception):raise output
            if output.stop_reason=='max_tokens':raise RuntimeError('Truncated model output; stop')
            ledger.settle(index,output.usage)
            return result
        except Exception as e:
            ledger.halted=True
            ledger.entries[index]['error_type']=type(e).__name__
            ledger.entries[index]['seconds']=time.monotonic()-start
            ledger.save()
            raise
    model.api.generate=guarded
