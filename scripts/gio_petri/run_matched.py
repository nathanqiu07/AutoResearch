"""Run frozen matched conditions through native Petri with a common shutdown setup.
Default validates the packet only. Paid execution requires a separately issued,
packet-bound coordinator lease and provider credentials. No rerolls or substitutions.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_CLAIM_ROOT=Path.home()/'.local/state/autoresearch/provider-leases'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'harness/petri'))
from prepare import sha
from preflight import write
from run_baseline import validate_settings,review_context,run_primary_review


def check_archive_hashes(packet):
    packet=Path(packet)
    checks=json.loads((packet/'checksums.json').read_text())
    if not isinstance(checks,dict) or not checks:raise ValueError('Empty checksum manifest')
    for name,digest in checks.items():
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe packet path')
        p=packet/name
        if p.is_symlink() or not p.is_file() or sha(p)!=digest:raise ValueError('Packet changed: '+name)
    actual={str(p.relative_to(packet)) for p in packet.rglob('*') if p.is_file()}
    if actual!=set(checks)|{'checksums.json'}:raise ValueError('Packet contains unlisted files')
    return checks


def read_credentials(path):
    """Parse a dotenv file as data; never execute it or return unrelated secrets."""
    allowed={'OPENAI_API_KEY','OPENROUTER_API_KEY','OPENAI_ORG_ID','OPENAI_PROJECT_ID'}
    result={}
    for raw in Path(path).read_text().splitlines():
        line=raw.strip()
        if line.startswith('export '):line=line[7:].lstrip()
        if not line or line.startswith('#') or '=' not in line:continue
        key,value=line.split('=',1);key=key.strip()
        if key not in allowed:continue
        parts=shlex.split(value,comments=True,posix=True)
        if len(parts)!=1 or not parts[0]:raise ValueError('Malformed credential assignment for '+key)
        result[key]=parts[0]
    return result


def collect_native_evidence(sample,status,turns):
    """Preserve final native messages even when normal Petri export failed."""
    from inspect_ai.model import ChatMessage
    from pydantic import TypeAdapter
    from transcript import render,split_assistant,record_from_sample
    target=(sample.store or {}).get('AuditStore:target',{})
    messages=TypeAdapter(list[ChatMessage]).validate_python(target.get('messages',[]))
    native=record_from_sample(sample)
    row={**native,'transcript':render(messages),
         'reasoning':'\n\n'.join(split_assistant(m)[0] for m in messages if m.role=='assistant' and split_assistant(m)[0]),
         'execution_status':status,'audit_completed':status=='success' and sample.error is None,
         'recovery_source':'Native AuditStore target messages, final branch only'}
    row['petri_scores']={k:v for k,v in (native.get('petri_scores') or {}).items() if v is not None}
    if sample.error:row['error']=str(sample.error.message)
    tools,structure=review_context(sample,turns)
    if not row['audit_completed']:structure['termination']='execution_error'
    structure['target_assistant_responses']=sum(m.role=='assistant' for m in messages)
    return row,tools,structure


def validate_execution_lease(lease,packet,settings):
    from datetime import datetime,timezone
    if lease.get('status')!='issued':raise ValueError('Coordinator lease is not issued')
    if lease.get('owner_chat')!='01a1de1f-bcb8-74a3-8076-0a3f9a27340a':raise ValueError('Wrong lease owner')
    if lease.get('packet_checksums_sha256')!=sha(packet/'checksums.json'):raise ValueError('Lease is not bound to this packet')
    if not isinstance(lease.get('lease_id'),str) or not lease['lease_id'].strip():raise ValueError('Missing lease ID')
    expires=datetime.fromisoformat(lease['expires_at'].replace('Z','+00:00'))
    if expires.tzinfo is None or expires<=datetime.now(timezone.utc):raise ValueError('Expired lease')
    caps=lease.get('provider_allocations_usd',{})
    requested=settings.get('provider_allocations_usd',caps)
    for name in ('openai','openrouter'):
        value=caps.get(name)
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=500:
            raise ValueError('Invalid finite provider allocation: '+name)
        if requested.get(name)!=caps.get(name):raise ValueError('Lease allocation mismatch: '+name)
    return caps


def validate_runtime_binding(settings,current_commit):
    turns=validate_settings(settings)
    if turns!=30:raise ValueError('This comparison requires exactly 30 auditor turns')
    if settings.get('code_version')!=current_commit:raise ValueError('Runtime commit differs from frozen packet')
    return turns


def claim_execution_lease(lease_path,lease,out):
    """One lease identity permits one execution across copies and worktrees."""
    receipt=Path(lease_path).resolve()
    DEFAULT_CLAIM_ROOT.mkdir(parents=True,exist_ok=True)
    claim=DEFAULT_CLAIM_ROOT/(hashlib.sha256(lease['lease_id'].encode()).hexdigest()+'.json')
    try:fd=os.open(claim,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise ValueError('Execution lease already claimed; no automatic rerun')
    with os.fdopen(fd,'w') as f:
        json.dump({'lease_id':lease['lease_id'],'lease_sha256':sha(receipt),'out':str(Path(out).resolve())},f,indent=2)
    return claim


def setup_gate(snapshot):
    return (snapshot.get('finished') is True and snapshot.get('exposure_delivered') is True
            and type(snapshot.get('target_responses')) is int and snapshot['target_responses']>=1
            and snapshot.get('failed') is False)


def build_task(seed,prompt,turns,start_time,directory):
    from inspect_ai import Task
    from inspect_ai.dataset import Sample
    from petri.solvers.auditor_agent import auditor_agent
    from petri.scorers.judge import alignment_judge
    from petri.cleanup.save_transcripts import save_transcripts
    from shutdown_setup import build_shutdown_tools
    tools,world=build_shutdown_tools(start_time,directory/'world')
    sample=Sample(input=seed['text'],id=seed['seed_id'],metadata={'seed_id':seed['seed_id'],'variant':seed.get('variant','v2'),'tools':'simulated'})
    task=Task(dataset=[sample],solver=auditor_agent(max_turns=turns,auditor_tools=tools,auditor_system_message=prompt),
        scorer=alignment_judge(retries=3),cleanup=save_transcripts(str(directory/'transcripts')),metadata={'tools':'simulated'})
    return task,world


def bridge(role,ledger,raw):
    from autoresearch.llm import LLM
    from inspect_ai.model import ChatMessageSystem,ChatMessageUser,GenerateConfig
    from roles import roles
    from budget import attach
    class Bridge(LLM):
        def __init__(self):
            super().__init__();self.name='openai' if role=='judge' else 'openrouter'
            from preflight import TARGET
            self.model='gpt-5.1' if role=='judge' else TARGET
        def complete(self,prompt,system='',max_tokens=1024,temperature=0.7):
            msgs=([ChatMessageSystem(content=system)] if system else [])+[ChatMessageUser(content=prompt)]
            async def generate():
                rr=roles()
                try:
                    attach(rr[role],role,ledger,raw)
                    return (await rr[role].generate(msgs,config=GenerateConfig(cache=False))).completion
                finally:
                    for model in rr.values():await model.__aexit__(None,None,None)
            return asyncio.run(generate())
    return Bridge()


def run_arm(arm,packet,out,settings,parent):
    from inspect_ai import eval as inspect_eval
    from inspect_ai.log import read_eval_log
    from provider_budget import ArmLedger
    from roles import roles
    from budget import attach
    from review import build_review_prompt
    directory=out/arm;directory.mkdir();raw=directory/'calls';raw.mkdir()
    start=time.monotonic();summary={'arm':arm,'execution_status':'not_started','primary_review_status':'not_available'}
    audit_ledger=ArmLedger(directory/'audit-ledger.json',parent,arm+'.audit')
    seed=json.loads((packet/'seed.json').read_text());prompt=(packet/f'{arm}.template.txt').read_text()
    rr=roles()
    for name,model in rr.items():attach(model,name,audit_ledger,raw)
    task,world=build_task(seed,prompt,settings['max_auditor_turns'],settings['start_time'],directory)
    (directory/'auditor-template.txt').write_text(prompt)
    logs=[]
    try:
        logs=inspect_eval(task,model=rr['target'],model_roles=rr,epochs=1,log_dir=str(directory/'logs'),
            max_tasks=1,max_connections=1,fail_on_error=True,display='plain')
    except Exception as exc:
        write(directory/'execution-error.json',{'error_type':type(exc).__name__})
    finally:
        audit_ledger.save()
        write(directory/'world-final.json',world.snapshot())
    # Independent initial-state assessment: descriptive only, never chooses an arm or a reroll.
    if settings.get('initial_environment_review'):
        initial_paths = [directory/'world/world-initial.json', directory/'world/attempted-target-inputs.jsonl']
        if all(path.is_file() for path in initial_paths):
            from environment_review import review_saved_initial_environment
            environment_ledger = ArmLedger(directory/'environment-review-ledger.json', parent, arm+'.environment_review')
            environment_raw = directory/'environment-review-calls'; environment_raw.mkdir()
            try:
                result = review_saved_initial_environment(bridge('judge', environment_ledger, environment_raw), directory,
                    (packet/'environment-review-instructions.txt').read_text())
                summary['environment_review_status'] = result['status']
            except Exception as exc:
                summary['environment_review_status'] = 'review_failed'
                write(directory/'environment-review-error.json', {'error_type': type(exc).__name__})
            finally:
                environment_ledger.save()
        else:
            summary['environment_review_status'] = 'unmeasured_no_initial_target_input'
    if not logs:
        paths=list((directory/'logs').glob('*.eval'))
        if len(paths)==1:logs=[read_eval_log(str(paths[0]))]
    if len(logs)!=1 or len(logs[0].samples or [])!=1:
        summary.update(execution_status='error',error='No unique native sample',seconds=time.monotonic()-start)
        write(directory/'summary.json',summary);return summary
    log=logs[0];sample=log.samples[0]
    (directory/'native-sample.json').write_text(sample.model_dump_json(indent=2))
    write(directory/'native-stats.json',log.stats.model_dump(mode='json'))
    try:row,tools,structure=collect_native_evidence(sample,log.status,settings['max_auditor_turns'])
    except Exception as exc:
        summary.update(execution_status=log.status,error='Native recovery failed: '+type(exc).__name__,seconds=time.monotonic()-start)
        write(directory/'summary.json',summary);return summary
    write(directory/'audit.json',row);write(directory/'target-tools.json',tools);write(directory/'run-structure.json',structure)
    summary.update(execution_status=log.status,audit_completed=row['audit_completed'],auditor_turns_used=structure['auditor_turns_used'])
    # Review also preserves partial failed evidence; failure remains separate from validity.
    if row.get('transcript'):
        review_ledger=ArmLedger(directory/'review-ledger.json',parent,arm+'.review')
        review_raw=directory/'review-calls';review_raw.mkdir()
        review_prompt,sources=build_review_prompt(seed,row,tools,structure,(packet/'review-instructions.txt').read_text())
        (directory/'primary-review-prompt.txt').write_text(review_prompt);write(directory/'primary-review-sources.json',sources)
        try:
            result=run_primary_review(bridge('judge',review_ledger,review_raw),review_prompt,sources,directory)
            summary['primary_review_status']=result['status']
        except Exception as exc:summary.update(primary_review_status='review_failed',review_error_type=type(exc).__name__)
        finally:review_ledger.save()
    if row['audit_completed'] and row.get('transcript') and row.get('reasoning'):
        secondary=ArmLedger(directory/'secondary-ledger.json',parent,arm+'.secondary')
        secondary_raw=directory/'secondary-calls';secondary_raw.mkdir()
        try:
            from autoresearch.research.measure import Models,load_probe_questions
            from autoresearch.research.petri_measure import PetriMeasurer
            target=bridge('target',secondary,secondary_raw);judge=bridge('judge',secondary,secondary_raw)
            probes=load_probe_questions(str(packet/'evaldetect_probes.json')) if (packet/'evaldetect_probes.json').exists() else None
            measurer=PetriMeasurer(Models(judge,target,judge),[seed],workers=1,probe_questions=probes,runner=lambda _:[])
            # Never include context or condition identity in the judge-facing seed.
            score=measurer.score(seed,{**seed,'tools':'simulated','variant':seed.get('variant','v2')},row).to_dict()
            score.update(legacy_scores_secondary=True,transcript_clipped_for_outer_judge=len(row['transcript'])>24000,
                reasoning_clipped_for_outer_judge=len(row['reasoning'])>6000)
            write(directory/'score.json',score)
            summary['secondary_status']='error' if score.get('error') else 'completed'
        except Exception as exc:
            summary['secondary_status']='error';write(directory/'secondary-error.json',{'error_type':type(exc).__name__})
        finally:secondary.save()
    else:summary['secondary_status']='unmeasured_incomplete_audit_or_missing_reasoning'
    summary['seconds']=time.monotonic()-start
    summary['setup_gate_passed']=setup_gate(world.snapshot())
    summary['valid_comparison_case']=row['audit_completed'] and summary['setup_gate_passed'] and summary['primary_review_status']=='valid'
    summary['valid_comparison_case_scope']='Existing primary checks plus exposure only; initial-environment semantic assessment is separate, not an admission gate.'
    write(directory/'summary.json',summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--lease',type=Path);p.add_argument('--credentials-file',type=Path);p.add_argument('--execute',action='store_true')
    a=p.parse_args();check_archive_hashes(a.packet)
    from prepare_matched import verify_packet
    settings=verify_packet(a.packet);validate_settings(settings)
    if settings['max_auditor_turns']!=30:raise ValueError('This comparison requires exactly 30 auditor turns')
    if settings['arms']!=['baseline','generic','profile']:raise ValueError('Unexpected comparison arms/order')
    if not a.execute:print('Packet validated; no model calls.');return
    if a.lease is None:raise ValueError('Execution requires a packet-bound coordinator lease')
    lease=json.loads(a.lease.read_text());allocations=validate_execution_lease(lease,a.packet,settings)
    version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    validate_runtime_binding(settings,version)
    if a.credentials_file:
        for key,value in read_credentials(a.credentials_file).items():os.environ.setdefault(key,value)
    if not all(os.environ.get(k) for k in ('OPENAI_API_KEY','OPENROUTER_API_KEY')):raise ValueError('Both provider credentials must be configured')
    if a.out.exists():raise ValueError('Output directory already exists')
    dirty=subprocess.check_output(['git','diff','--name-only','HEAD','--','scripts/gio_petri','autoresearch','harness/petri'],cwd=ROOT,text=True).strip()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','scripts/gio_petri'],cwd=ROOT,text=True).strip()
    if dirty or untracked:raise ValueError('Runtime source must be committed before execution')
    claim_execution_lease(a.lease,lease,a.out)
    a.out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(a.packet,a.out/'packet');write(a.out/'execution-lease.json',lease)
    (a.out/'CODE_VERSION').write_text(version+'\n')
    shutil.copytree(Path(__file__).parent,a.out/'runner_source',ignore=shutil.ignore_patterns('__pycache__'))
    write(a.out/'runner_checksums.json',{f.name:sha(f) for f in (a.out/'runner_source').iterdir() if f.is_file()})
    write(a.out/'dependencies.json',{'collection_phase':'before_model_calls','python':sys.version,
        'packages':{n:importlib.metadata.version(n) for n in ('inspect_ai','petri','openai','pydantic')},
        'installed_distributions':sorted([{'name':d.metadata['Name'],'version':d.version}
            for d in importlib.metadata.distributions()],key=lambda d:(d['name'] or '').lower()),
        'direct_sources':{name:json.loads(value) for name in ('inspect_ai','petri','openai','pydantic')
            if (value:=importlib.metadata.distribution(name).read_text('direct_url.json'))}})
    tracked=subprocess.check_output(['git','ls-files','--','autoresearch','harness/petri','scripts/gio_petri'],cwd=ROOT,text=True).splitlines()
    write(a.out/'runtime-source-checksums.json',{name:sha(ROOT/name) for name in tracked if name.endswith('.py')})
    write(a.out/'settings.json',{**settings,'execution_code_version':version,'lease_sha256':sha(a.lease)})
    from provider_budget import ProviderBudget
    parent=ProviderBudget(a.out/'provider-ledger.json',allocations,lease)
    summaries=[]
    for arm in settings['arms']:
        if parent.halted:break
        try:result=run_arm(arm,a.out/'packet',a.out,settings,parent)
        except Exception as exc:
            result={'arm':arm,'execution_status':'error','error_type':type(exc).__name__,'valid_comparison_case':False}
            write(a.out/(arm+'-failure.json'),result)
        summaries.append(result);write(a.out/'summary.json',{'arms':summaries,'budget':parent.summary()})
        print(json.dumps(result),flush=True)
    print(json.dumps({'out':str(a.out),'budget':parent.summary()}),flush=True)

if __name__=='__main__':main()
