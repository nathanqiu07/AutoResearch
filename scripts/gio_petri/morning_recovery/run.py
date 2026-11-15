"""Execute new frozen contexts with the unchanged run_matched arm implementation."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from morning_recovery.packet import ROOT, verify_packet, digest
from morning_recovery.budget import ProviderBudget, validate_execution_lease
from run_matched import (run_arm, read_credentials, claim_execution_lease,
                         validate_runtime_binding)
from preflight import write

def ref(root, path, label=None):
    row={'path':str(path.relative_to(root)), 'sha256':digest(path.read_bytes())}
    if label: row['label']=label
    return row

def freeze_packet(source,destination,lease,settings):
    """Dispatch only from the exact copied packet bound by the issued lease."""
    shutil.copytree(source,destination)
    frozen=verify_packet(destination)
    validate_execution_lease(lease,destination,frozen)
    if frozen!=settings:raise ValueError('Packet changed while copying')
    return frozen

def capture_inputs(directory, context):
    """Index actual provider captures; missing captures cannot count as isolation proof."""
    records=[]
    text=context['model_facing_text']
    for path in sorted(directory.rglob('call-*.json')):
        role=path.stem.rsplit('-',1)[-1]
        if role not in ('auditor','target','judge'):continue
        saved=json.loads(path.read_text())
        request=saved.get('request')
        # Keep raw request values in their original files; inspect leaves only.
        def strings(value):
            if isinstance(value,str):return [value]
            if isinstance(value,dict):return [s for v in value.values() for s in strings(v)]
            if isinstance(value,list):return [s for v in value for s in strings(v)]
            return []
        leaves=strings(request)
        present=any(text in leaf for leaf in leaves)
        request_present=isinstance(request,dict) and bool(request.get('messages') or request.get('input'))
        records.append({**ref(directory,path),'role':role,
            'capture_kind':'provider_request_and_response', 'request_present':request_present,
            'full_context_present':present})
    auditor=[r for r in records if r['role']=='auditor']
    protected=[r for r in records if r['role'] in ('target','judge')]
    leaks=[r['path'] for r in protected if r['full_context_present']]
    checked={r['role'] for r in protected if r['request_present']}
    missing=[]
    for ledger_name,folder in (('audit-ledger.json','calls'),('review-ledger.json','review-calls'),
                               ('secondary-ledger.json','secondary-calls'),('environment-review-ledger.json','environment-review-calls')):
        ledger=directory/ledger_name
        if ledger.is_file():
            for index,entry in enumerate(json.loads(ledger.read_text()).get('entries',[])):
                expected=directory/folder/('call-%04d-%s.json'%(index,entry['role']))
                if not expected.is_file():missing.append(str(expected.relative_to(directory)))
    result={'schema_version':'gio-role-input-captures-v1','records':records,
        'auditor_full_context_observed':any(r['full_context_present'] for r in auditor),
        'protected_roles_with_capture':sorted(checked),'full_context_leak_paths':leaks,'reserved_calls_without_capture':missing,
        'status':'failed' if leaks else 'passed_full_context_check' if not missing and all(r['request_present'] for r in records) and checked=={'target','judge'} and any(r['full_context_present'] for r in auditor) else 'incomplete',
        'scope':'Whole rendered context only. Partial statement leakage, semantic copying and missing attempts require lane07 review.',
        'attempted_target_inputs':ref(directory,directory/'world/attempted-target-inputs.jsonl') if (directory/'world/attempted-target-inputs.jsonl').is_file() else None}
    write(directory/'role-input-captures.json',result)
    return result

def write_index(out,settings,summaries,parent):
    conditions=[]
    byarm={s['arm']:s for s in summaries}
    for arm in settings['arms']:
        directory=out/arm
        summary=byarm.get(arm,{})
        def available(paths):return [ref(out,p) for p in paths if p.is_file()]
        entries=[e for e in parent.entries if e['arm'].startswith(arm+'.')]
        known=sum(e['charged_usd'] for e in entries if e['status']=='usage_estimate')
        uncertain=sum(e['charged_usd'] for e in entries if e['status']!='usage_estimate')
        conditions.append({'id':arm,'label':arm,'status':summary.get('execution_status','not_started'),
            'error':summary.get('error',summary.get('error_type')),
            'stages':{
                'sources':available([out/'packet'/(arm+'.source-bundle.json')]),
                'profile':available([out/'packet'/(arm+'.profile.json'),out/'packet'/(arm+'.context.json')]),
                'auditor_context':available([directory/'auditor-template.txt',directory/'role-input-captures.json']),
                'environment':available([directory/'world/world-initial.json']),
                'target_trace':available([directory/'audit.json',directory/'native-sample.json']),
                'state_changes':available([directory/'world-final.json'])},
            'reviews':{'validity':{'status':summary.get('environment_review_status','unmeasured'),
                         'records':available([directory/'environment-review.json',directory/'primary-review.json'])},
                       'taste':{'status':'unmeasured','records':[]},
                       'behavior':{'status':summary.get('primary_review_status','unmeasured'),
                         'records':available([directory/'primary-review.json',directory/'world-final.json'])}},
            'costs':{'known_usd':known if entries else None,'uncertain_usd':uncertain if entries else None,
                     'reserved_usd':None,'records':available([directory/'audit-ledger.json',directory/'review-ledger.json',directory/'secondary-ledger.json',directory/'environment-review-ledger.json'])}})
    index={'schema_version':'gio-recovery-viewer-v1','artifact_kind':'recorded_run',
        'run_id':out.name,'title':'Source context through the complete Petri workflow',
        'scenario':settings['setup_protocol'],'snapshot_status':'terminal' if len(summaries)==len(settings['arms']) or parent.halted else 'partial',
        'limitations':settings['limitations']+['No reliable benefit estimate; failed and missing arms remain visible.'],
        'conditions':conditions,'provenance':[ref(out,out/'settings.json'),ref(out,out/'CODE_VERSION'),ref(out,out/'provider-ledger.json')]}
    write(out/'viewer-index.json',index)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--lease',type=Path);p.add_argument('--credentials-file',type=Path)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args();settings=verify_packet(a.packet)
    if not a.execute:
        print(json.dumps({'status':'validated_offline','arms':settings['arms'],'calls':0}));return
    if a.out.resolve()==a.packet.resolve() or a.packet.resolve() in a.out.resolve().parents:
        raise ValueError('Output must be outside packet')
    if a.lease is None:raise ValueError('Packet-bound coordinator lease required')
    lease=json.loads(a.lease.read_text())
    allocations=validate_execution_lease(lease,a.packet,settings)
    version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    validate_runtime_binding(settings,version)
    if a.credentials_file:
        for key,value in read_credentials(a.credentials_file).items():os.environ.setdefault(key,value)
    if not all(os.environ.get(k) for k in ('OPENAI_API_KEY','OPENROUTER_API_KEY')):
        raise ValueError('Both provider credentials must be configured')
    if a.out.exists():raise ValueError('Output directory exists')
    dirty=subprocess.check_output(['git','diff','--name-only','HEAD','--','scripts/gio_petri','autoresearch','harness/petri'],cwd=ROOT,text=True).strip()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','scripts/gio_petri'],cwd=ROOT,text=True).strip()
    if dirty or untracked:raise ValueError('Commit runtime source before execution')
    claim_execution_lease(a.lease,lease,a.out)
    a.out.mkdir(parents=True,exist_ok=False)
    settings=freeze_packet(a.packet,a.out/'packet',lease,settings)
    write(a.out/'execution-lease.json',lease)
    (a.out/'CODE_VERSION').write_text(version+'\n')
    shutil.copytree(Path(__file__).resolve().parents[1],a.out/'runner_source',ignore=shutil.ignore_patterns('__pycache__'))
    tracked=subprocess.check_output(['git','ls-files','--','autoresearch','harness/petri','scripts/gio_petri'],cwd=ROOT,text=True).splitlines()
    write(a.out/'runtime-source-checksums.json',{name:digest((ROOT/name).read_bytes()) for name in tracked if name.endswith('.py')})
    write(a.out/'dependencies.json',{'python':sys.version,'packages':{n:importlib.metadata.version(n) for n in ('inspect_ai','petri','openai','pydantic')}})
    write(a.out/'settings.json',{**settings,'execution_code_version':version,'lease_sha256':digest(a.lease.read_bytes())})
    parent=ProviderBudget(a.out/'provider-ledger.json',allocations,lease)
    summaries=[]
    write_index(a.out,settings,summaries,parent)
    for arm in settings['arms']:
        if parent.halted:break
        try:
            result=run_arm(arm,a.out/'packet',a.out,settings,parent)
            context=json.loads((a.out/'packet'/(arm+'.context.json')).read_text())
            isolation=capture_inputs(a.out/arm,context)
            result['context_isolation_status']=isolation['status']
            if isolation['full_context_leak_paths']:result['valid_comparison_case']=False
        except Exception as exc:
            result={'arm':arm,'execution_status':'error','error_type':type(exc).__name__,'valid_comparison_case':False}
            write(a.out/(arm+'-failure.json'),result)
        summaries.append(result)
        write(a.out/'summary.json',{'arms':summaries,'budget':parent.summary()})
        write_index(a.out,settings,summaries,parent)
        print(json.dumps(result),flush=True)
    print(json.dumps({'out':str(a.out),'budget':parent.summary()}),flush=True)

if __name__=='__main__':main()
