"""One reservation ledger for native Inspect calls across the three roles.
Reserve full context plus maximum output; keep reservation on errors/unknown usage.
Prices: OpenRouter endpoint snapshot and official GPT-5.1 model page (2026-11-14).
"""
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Literal, Optional
import threading
import time

RATES={'auditor':(0.09,0.55,262144), 'target':(0,0,1000000), 'judge':(1.25,10,400000)}

COST_BASIS = 'same_saved_rates_full_input_estimate_or_retained_reservation_not_provider_invoice'

UsageContract = Literal['inspect-normalized-v1', 'openai-responses-total-v1']
_MISSING = object()


@dataclass(frozen=True)
class InputTokenAccounting:
    usage_contract: UsageContract
    input_tokens: int
    output_tokens: int
    input_tokens_cache_read: Optional[int]
    input_tokens_cache_write: Optional[int]
    total_input_tokens: int


def _field(value, name):
    return value.get(name, _MISSING) if isinstance(value, Mapping) else getattr(value, name, _MISSING)


def _token_count(value):
    if type(value) is not int or not 0 <= value <= 1_000_000_000:
        raise ValueError('Token counts must be nonnegative bounded integers')
    return value


def _optional_token_count(value):
    return None if value is _MISSING or value is None else _token_count(value)


def input_token_accounting(usage: object, *, contract: UsageContract) -> InputTokenAccounting:
    """Explicit usage semantics; never infer totals from field-name coincidence.

    Inspect input_tokens excludes cache reads/writes. OpenAI Responses
    input_tokens already includes its input_tokens_details cache components.
    This helper accounts for tokens only; existing role prices are unchanged.
    """
    inputs = _token_count(_field(usage, 'input_tokens'))
    outputs = _token_count(_field(usage, 'output_tokens'))
    details = _field(usage, 'input_tokens_details')
    read = _field(usage, 'input_tokens_cache_read')
    written = _field(usage, 'input_tokens_cache_write')
    if contract == 'inspect-normalized-v1':
        if details is not _MISSING:
            raise ValueError('Provider-total details are ambiguous under Inspect usage contract')
        read, written = _optional_token_count(read), _optional_token_count(written)
        total = _token_count(inputs + (read or 0) + (written or 0))
    elif contract == 'openai-responses-total-v1':
        if read is not _MISSING or written is not _MISSING:
            raise ValueError('Normalized cache fields are ambiguous under provider-total contract')
        if details is _MISSING or details is None:
            read = written = None
        else:
            if not isinstance(details, Mapping) and not hasattr(details, 'cached_tokens') and not hasattr(details, 'cache_write_tokens'):
                raise ValueError('Expected OpenAI Responses input_tokens_details object')
            read = _optional_token_count(_field(details, 'cached_tokens'))
            written = _optional_token_count(_field(details, 'cache_write_tokens'))
        if (read or 0) + (written or 0) > inputs:
            raise ValueError('Cache components exceed provider total input tokens')
        total = inputs
    else:
        raise ValueError('Unknown usage contract')
    return InputTokenAccounting(contract, inputs, outputs, read, written, total)

class Ledger:
    def __init__(self, path, cap):
        if cap <= 0: raise ValueError('Budget must be positive')
        self.path=path; self.cap=cap; self.held=0.; self.entries=[]; self.lock=threading.Lock(); self.halted=False
    def save(self):
        self.path.write_text(json.dumps({'cap_usd':self.cap,'charged_or_reserved_usd':self.held,
                                        'entries':self.entries,'cost_basis':COST_BASIS,
                                        'priced_input_field':'total_input_tokens'},indent=2)+'\n')
    def reserve(self,role,max_tokens):
        inp,out,context=RATES[role]
        amount=(context*inp + max_tokens*out)/1e6
        with self.lock:
            if self.halted: raise RuntimeError('Ledger halted after previous failure')
            if self.held + amount > self.cap: raise RuntimeError('Insufficient reserved budget; no call made')
            i=len(self.entries); self.held+=amount
            self.entries.append({'role':role,'reserved_usd':amount,'charged_usd':amount,'status':'pending',
                                 'max_output_tokens':max_tokens,'input_token_bound':context})
            self.save()
        return i
    def settle(self,i,usage,*,usage_contract: UsageContract='inspect-normalized-v1'):
        with self.lock:
            if type(i) is not int or not 0 <= i < len(self.entries):
                raise ValueError('Unknown reservation')
            e=self.entries[i]
            if e['status'] != 'pending' or e.get('error_type'):
                raise ValueError('Reservation already settled or failed')
            if usage is not None:
                try:
                    counts=input_token_accounting(usage,contract=usage_contract)
                except ValueError:
                    e['status']='invalid_usage_reservation_retained';self.halted=True
                    self.save()
                    raise
                inp,out,_=RATES[e['role']]
                charge=(counts.total_input_tokens*inp+counts.output_tokens*out)/1e6
                # Full input rate deliberately ignores cache discounts.
                exceeded=(counts.total_input_tokens>e['input_token_bound'] or
                          counts.output_tokens>e['max_output_tokens'] or charge>e['reserved_usd'])
                if exceeded:charge=max(charge,e['charged_usd'])
                self.held+=charge-e['charged_usd']
                e.update(asdict(counts),charged_usd=charge,status='BOUND_EXCEEDED_STOP' if exceeded else 'usage_estimate')
                if exceeded:self.halted=True
            else:e['status']='unknown_usage_reservation_retained';self.halted=True
            self.save()
            if e['status']=='unknown_usage_reservation_retained':raise RuntimeError('Missing usage; reservation retained and ledger stopped')
            if e['status']=='BOUND_EXCEEDED_STOP':raise RuntimeError('Cost or token bound exceeded; stop')

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
            ledger.settle(index,output.usage,usage_contract='inspect-normalized-v1')
            return result
        except Exception as e:
            ledger.halted=True
            ledger.entries[index]['error_type']=type(e).__name__
            ledger.entries[index]['seconds']=time.monotonic()-start
            ledger.save()
            raise
    model.api.generate=guarded
