"""Prepare or execute exactly one additive judge call for each frozen batch-05 arm.

Preparation is the default. No auditor/target clients, retries, resumes or rerolls.
Execution requires an explicit checksum pin and a fresh packet-bound issued lease.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import primary_span_review as adapter

ARMS = ('baseline', 'generic', 'profile')
OWNER = '01a1de1f-bcb8-74a3-8076-0a3f9a27340a'
SOURCE_COMMIT = 'e9672aa48ba442dfc5bd2cd84b8f0c76e2bfb7e4'
SOURCE_PACKET_SHA256 = '74b4e9a9535c18de4d8761a9027a88ef8cd60b9c39bd2e7cb90e02516b9f1f09'
SOURCE_REVIEW_HASHES = {
 'baseline':'b0727183ff0e6a6a24fab962d0569b40ace6601385313ec06efc47003ad66ee9',
 'generic':'53c3b8aad1daa86688e51d3b9f7abe74a97ecb314f82a343ce81f3a3e1d1ec94',
 'profile':'9e130ae57738537bde39a2cdc68f439f1d4ec579cd44b5dc4d2d9211f9e2b7c4'}
HELPER_HASHES = {
 'roles.py':'ad904f09636b406b3524316e2895d557adee50cce72c69b32e004cd841a6619c',
 'budget.py':'99c41b090b7271960186f323459adf01c22f6c24bd744e9abdd1a1b2beb285b1',
 'provider_budget.py':'bb51f2ac700a632619e18d5e99016148f19e0eb6eb0fc8023f1bbcb6d185bfab',
 'run_matched.py':'2d1b5ae3a905b495188755f1b46c9a2e03d6c385ed60eac708b4a6a7bf96727f',
 'review.py':'213df99a66b5cd005a243e61bbb9ce7f697846d33e45042876986507e1d3733d',
 'preflight.py':'2ce977d9b67bd069cc209030f63bb85665fb261cdf6a9a0c7e639eb715af723a',
 'run_baseline.py':'9960f1c223c364fe558fc086a7f274f973dfcc8d71cfac26efbd66802a04b688',
 'prepare.py':'254f00a8f5313a38aa425f363fb37306050a3a33f36e5b20747c2a67357110e1'}
JUDGE_GENERATION = {'max_tokens':32000, 'reasoning_effort':'high', 'temperature':'provider default'}
BLOCKED_OR_CAP = .000001
MAX_RESERVATIONS_USD = 2.46


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc_now():return datetime.now(timezone.utc)
def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def read(path):return json.loads(Path(path).read_bytes())


def runtime_commit(repo):
    repo=Path(repo).resolve()
    paths=['scripts/gio_petri/'+name for name in HELPER_HASHES]
    for filename in (__file__,adapter.__file__):
        path=Path(filename).resolve()
        if repo in path.parents:paths.append(str(path.relative_to(repo)))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    dirty=subprocess.check_output(['git','diff','--name-only','HEAD','--',*paths],cwd=repo,text=True).strip()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*paths],cwd=repo,text=True).strip()
    if dirty or untracked:raise ValueError('Runtime source must be committed and clean')
    return commit


def helpers(repo):
    directory=Path(repo).resolve()/'scripts/gio_petri'
    for name,expected in HELPER_HASHES.items():
        if sha(directory/name)!=expected:raise ValueError('Shared helper changed: '+name)
    sys.path.insert(0,str(directory))
    modules={name:importlib.import_module(name) for name in ('budget','provider_budget','run_matched','review')}
    for name,module in modules.items():
        if Path(module.__file__).resolve()!=directory/(name+'.py'):
            raise ValueError('Imported helper is from a different checkout: '+name)
    return modules


def prepare(source_run,out,repo):
    modules=helpers(repo);source=Path(source_run).resolve();out=Path(out).resolve()
    if out==source or source in out.parents:raise ValueError('Output must be outside the source run')
    runtime=runtime_commit(repo)
    if (source/'CODE_VERSION').read_text().strip()!=SOURCE_COMMIT:raise ValueError('Wrong source commit')
    packet=source/'packet'
    if sha(packet/'checksums.json')!=SOURCE_PACKET_SHA256:raise ValueError('Wrong original source packet')
    modules['run_matched'].check_archive_hashes(packet)
    settings=read(packet/'settings.json')
    if (settings.get('code_version')!=SOURCE_COMMIT or settings.get('models',{}).get('judge')!='gpt-5.1'
            or settings.get('generation',{}).get('judge')!=JUDGE_GENERATION):
        raise ValueError('Original judge settings differ')
    rows=read(source/'summary.json').get('arms',[])
    if [r.get('arm') for r in rows]!=list(ARMS):raise ValueError('Source run has not completed all three arms')
    if any(e.get('status')=='pending' for e in read(source/'provider-ledger.json').get('entries',[])):
        raise ValueError('Source run still has a pending provider call')
    for arm,digest in SOURCE_REVIEW_HASHES.items():
        if sha(source/arm/'primary-review-sources.json')!=digest:raise ValueError('Original sources changed: '+arm)
    # Validate all source strings/instructions before creating any output directory.
    original=(packet/'review-instructions.txt').read_bytes().decode()
    for arm in ARMS:adapter.build_span_prompt(read(source/arm/'primary-review-sources.json'),original)
    out.mkdir(parents=True,exist_ok=False)
    for arm in ARMS:
        adapter.prepare_artifacts(source/arm/'primary-review-sources.json',packet/'review-instructions.txt',out/arm)
    frozen={'version':adapter.VERSION,'arms':list(ARMS),'source_code_version':SOURCE_COMMIT,
        'runtime_code_version':runtime,
        'source_packet_sha256':SOURCE_PACKET_SHA256,'source_review_hashes':SOURCE_REVIEW_HASHES,
        'source_terminal_summary_sha256':sha(source/'summary.json'),
        'source_settings_sha256':sha(packet/'settings.json'),
        'judge_model':'gpt-5.1','judge_generation':JUDGE_GENERATION,'max_calls':3,'max_calls_per_arm':1,
        'transport_retries':0,'helper_hashes':HELPER_HASHES,'wrapper_sha256':sha(__file__),
        'adapter_sha256':sha(adapter.__file__),'maximum_reservations_usd':MAX_RESERVATIONS_USD,
        'maximum_openai_lease_usd':3,'blocked_openrouter_allocation_usd':BLOCKED_OR_CAP,
        'openrouter_calls_permitted':False,'original_reviews_replaced':False}
    write(out/'settings.json',frozen)
    write(out/'checksums.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    verify(out,repo)
    return frozen


def verify(packet,repo,expected_pin=None):
    packet=Path(packet);modules=helpers(repo)
    if expected_pin is not None and expected_pin!=sha(packet/'checksums.json'):raise ValueError('Packet pin mismatch')
    modules['run_matched'].check_archive_hashes(packet)
    settings=read(packet/'settings.json')
    if settings.get('runtime_code_version')!=runtime_commit(repo):raise ValueError('Runtime commit differs from frozen packet')
    expected={'version':adapter.VERSION,'arms':list(ARMS),'source_code_version':SOURCE_COMMIT,
        'source_packet_sha256':SOURCE_PACKET_SHA256,'source_review_hashes':SOURCE_REVIEW_HASHES,
        'judge_model':'gpt-5.1','judge_generation':JUDGE_GENERATION,'max_calls':3,'max_calls_per_arm':1,
        'transport_retries':0,'helper_hashes':HELPER_HASHES,'wrapper_sha256':sha(__file__),
        'adapter_sha256':sha(adapter.__file__),'openrouter_calls_permitted':False,'original_reviews_replaced':False}
    for key,value in expected.items():
        if settings.get(key)!=value:raise ValueError('Frozen setting differs: '+key)
    for arm in ARMS:
        if sha(packet/arm/'sources.json')!=SOURCE_REVIEW_HASHES[arm]:raise ValueError('Source pin mismatch: '+arm)
        instructions=(packet/arm/'original-review-instructions.txt').read_bytes().decode()
        prompt,_=adapter.build_span_prompt(read(packet/arm/'sources.json'),instructions)
        if (packet/arm/'prompt.txt').read_bytes()!=prompt.encode():raise ValueError('Prompt differs from exact frozen sources: '+arm)
    return settings


def load_verified_inputs(packet,expected_pin):
    """Read all three inputs once, checking the exact bytes that will be used."""
    packet=Path(packet)
    manifest_raw=(packet/'checksums.json').read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest()!=expected_pin:raise ValueError('Copied manifest pin mismatch')
    checks=json.loads(manifest_raw);loaded={}
    for arm in ARMS:
        blobs={}
        for name in ('sources.json','prompt.txt','original-review-instructions.txt'):
            member=arm+'/'+name;raw=(packet/member).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=checks.get(member):raise ValueError('Loaded input hash mismatch: '+member)
            blobs[name]=raw
        if hashlib.sha256(blobs['sources.json']).hexdigest()!=SOURCE_REVIEW_HASHES[arm]:raise ValueError('Loaded source pin mismatch')
        sources=json.loads(blobs['sources.json'])
        expected,_=adapter.build_span_prompt(sources,blobs['original-review-instructions.txt'].decode())
        if blobs['prompt.txt']!=expected.encode():raise ValueError('Loaded prompt differs from exact source')
        loaded[arm]={'prompt':expected,'sources':sources,'source_bytes':blobs['sources.json']}
    return loaded


def validate_lease(lease,packet,settings):
    from provider_budget import parse_lease_expiry
    if lease.get('status')!='issued':raise ValueError('Coordinator lease is not issued')
    if lease.get('owner_chat')!=OWNER:raise ValueError('Wrong lease owner')
    if not isinstance(lease.get('lease_id'),str) or not lease['lease_id'].strip():raise ValueError('Missing lease ID')
    if lease.get('packet_checksums_sha256')!=sha(Path(packet)/'checksums.json'):raise ValueError('Wrong packet binding')
    if lease.get('source_code_version')!=SOURCE_COMMIT:raise ValueError('Wrong source commit binding')
    if lease.get('runtime_code_version')!=settings['runtime_code_version']:raise ValueError('Wrong runtime commit binding')
    if parse_lease_expiry(lease.get('expires_at'))<=utc_now():raise ValueError('Expired lease')
    caps=lease.get('provider_allocations_usd',{})
    if not isinstance(caps,dict) or set(caps)!={'openai','openrouter'}:raise ValueError('Both provider caps required')
    if (type(caps['openai']) not in (int,float) or not math.isfinite(caps['openai'])
            or not MAX_RESERVATIONS_USD<=caps['openai']<=3 or type(caps['openrouter']) not in (int,float)
            or caps['openrouter']!=BLOCKED_OR_CAP):raise ValueError('Invalid judge-only allocation')
    return caps


def make_judge():
    # Exact judge entry from pinned roles.py; never instantiate auditor/target clients.
    from inspect_ai.model import GenerateConfig,get_model
    common=dict(max_retries=0,timeout=120,cache=False)
    return get_model('openai/gpt-5.1',api_key=None,max_retries=0,memoize=False,
        config=GenerateConfig(max_tokens=32000,reasoning_effort='high',**common))


def serializable(value):
    if hasattr(value,'model_dump'):return value.model_dump(mode='json')
    if isinstance(value,dict):return {k:serializable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serializable(v) for v in value]
    if hasattr(value,'__dict__'):return serializable(vars(value))
    return value


async def one_call(prompt,ledger,raw,budget_module):
    from inspect_ai.model import ChatMessageUser,GenerateConfig
    judge=make_judge()
    native=judge.api.generate
    async def capture(input,tools,tool_choice,config):
        write(raw/'api-request.json',serializable({'input':input,'tools':tools,'tool_choice':tool_choice,'config':config}))
        try:
            result=await native(input,tools,tool_choice,config)
            output,call=result if isinstance(result,tuple) else (result,None)
            write(raw/'api-output.json',serializable(output))
            if call is not None:write(raw/'api-call.json',serializable(call))
            if hasattr(output,'completion'):(raw/'raw-reply.txt').write_text(output.completion)
            return result
        except Exception as exc:
            write(raw/'transport-or-capture-error.json',{'error_type':type(exc).__name__})
            raise
    judge.api.generate=capture
    budget_module.attach(judge,'judge',ledger,raw)
    try:
        return (await judge.generate([ChatMessageUser(content=prompt)],config=GenerateConfig(cache=False))).completion
    finally:
        await judge.__aexit__(None,None,None)


def execute(packet,out,lease_path,expected_pin,repo):
    if not isinstance(expected_pin,str) or len(expected_pin)!=64:raise ValueError('Explicit packet checksum pin is required')
    packet=Path(packet).resolve();out=Path(out).resolve();lease_path=Path(lease_path)
    if out==packet or packet in out.parents:raise ValueError('Output must be outside the frozen packet')
    settings=verify(packet,repo,expected_pin);modules=helpers(repo)
    lease=read(lease_path);caps=validate_lease(lease,packet,settings)
    if out.exists():raise FileExistsError('Execution output already exists; no resume')
    modules['run_matched'].claim_execution_lease(lease_path,lease,out)
    out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(packet,out/'packet');shutil.copyfile(lease_path,out/'execution-lease.json')
    try:
        verify(out/'packet',repo,expected_pin)
        inputs=load_verified_inputs(out/'packet',expected_pin)
    except Exception as exc:
        write(out/'execution-preflight-error.json',{'error_type':type(exc).__name__,'provider_calls':0})
        write(out/'summary.json',{'version':adapter.VERSION,'arms':[{'arm':a,'status':'not_run_packet_verification_failed'} for a in ARMS],'provider_calls':0,'original_reviews_unchanged':True})
        raise
    parent=modules['provider_budget'].ProviderBudget(out/'provider-ledger.json',caps,lease)
    class JudgeOnlyLedger(modules['provider_budget'].ArmLedger):
        def reserve(self,role,max_tokens):
            if role!='judge' or max_tokens!=32000:raise ValueError('Only the frozen judge call is permitted')
            if self.entries:raise ValueError('At most one provider request per arm is permitted')
            return super().reserve(role,max_tokens)
    summaries=[]
    for arm in ARMS:
        if parent.halted:
            summaries.append({'arm':arm,'status':'not_run_after_stop'});continue
        directory=out/arm;directory.mkdir();raw=directory/'raw';raw.mkdir()
        ledger=JudgeOnlyLedger(directory/'ledger.json',parent,arm+'.additive_primary_review')
        prompt=inputs[arm]['prompt']
        (directory/'prompt.txt').write_text(prompt)
        (directory/'sources-used.json').write_bytes(inputs[arm]['source_bytes'])
        try:
            reply=asyncio.run(one_call(prompt,ledger,raw,modules['budget']))
        except Exception as exc:
            parent.halted=True;parent.halt_reason='judge_transport_usage_or_budget_failure';parent.save()
            record={'arm':arm,'status':'execution_error','error_type':type(exc).__name__}
            write(directory/'execution-error.json',record)
        else:
            (directory/'raw-reply.txt').write_text(reply)
            try:
                result=adapter.validate_span_review(json.loads(reply),inputs[arm]['sources'])
            except (ValueError,KeyError,TypeError) as exc:
                record={'arm':arm,'status':'review_failed','error_type':type(exc).__name__,'error':str(exc)}
                write(directory/'validation-error.json',record)
            else:
                write(directory/'additive-review.json',result)
                record={'arm':arm,'status':'reviewed','substantive_status':result['review']['status']}
        summaries.append(record)
        write(out/'summary.json',{'version':adapter.VERSION,'arms':summaries,'budget':parent.summary(), 'original_reviews_unchanged':True})
    summary={'version':adapter.VERSION,'arms':summaries,'budget':parent.summary(),'original_reviews_unchanged':True}
    write(out/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--source-run',type=Path)
    parser.add_argument('--packet',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--lease',type=Path)
    parser.add_argument('--expected-packet-sha256')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.execute:
        if not args.packet or not args.lease or not args.out or args.source_run:parser.error('Execute requires --packet --lease --out; no --source-run')
        result=execute(args.packet,args.out,args.lease,args.expected_packet_sha256,args.repo)
        print(json.dumps({'out':str(args.out),'arms':result['arms'],'budget':result['budget']}))
    elif args.source_run:
        if not args.out or args.packet:parser.error('Prepare requires --source-run --out; no --packet')
        prepare(args.source_run,args.out,args.repo)
        print(json.dumps({'packet':str(args.out),'packet_checksums_sha256':sha(args.out/'checksums.json'),'model_calls':0,'maximum_reservations_usd':MAX_RESERVATIONS_USD}))
    elif args.packet:
        verify(args.packet,args.repo,args.expected_packet_sha256)
        print(json.dumps({'packet':str(args.packet),'model_calls':0,'verified':True}))
    else:parser.error('Choose preparation --source-run or verification --packet')

if __name__=='__main__':main()
