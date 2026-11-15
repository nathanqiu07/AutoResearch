#!/usr/bin/env python3
"""Dedicated observer envelope for exact remaining56 reference runtime9664557.
No scientific code edits, retries, arbitrary entrypoints or credential-file parsing.
Native job claims/budgets remain authoritative. Root must issue an exact envelope.
"""
import argparse,hashlib,importlib.util,json,os,runpy,subprocess,sys,threading
from datetime import datetime,timezone
from pathlib import Path
OBSERVER=Path('/private/tmp/gio_provider_diagnostics_v3.py')
OBSERVER_SHA='d2f3372e2689adf7bdef74fc6170fa25eca7bce4b4aa3de98b495633bf284233'
DEADLINE='2026-11-15T17:00:00Z'
PROFILE={'1ddae85ae57975dc69cacc89cd685faeced50dbe732af73afb509b8e3fb83c83','3a23dab1b6311bcd314d77267e14f51ecb7a6fd9a98ee8347e0d02d39e7222b7','25e5f1eef047006bc16785ed86a7c1aa929c4c9a30358308a5ca6d67a6764ce8','5f75e48a3a8b7a69abe1024a194832a18d41d95c02246a75ff4474eeaaa3e38d'}
REFERENCE={'970b0250ee8dabc2697b1f9238e9af8fc6b97529d448c40db1cefd9cbc47df20','07dce1746df8add55316a78b4daa5f1b5fc970481658430b90c920a1bf2146af','ab348ae8891196294f5ec63f8eefbb6570a03a6528528f8aa26d5fad9495b92d','f518fde206aaa61d435483d4cf8004aa2aa90bfc1fc0f3a368db116bf292dd50','9f578c13992fccde020f875f62302f7a6dfea56d7889b7d0a8519e041e13ab29'}
RUNTIMES={'reference':('9664557480240e17a88c69b83ca30533a2021492','scripts/overnight_labeled_reference.py')}
REFERENCE_ROOT=Path('/Users/giordanorogers/.codex/worktrees/gio-reference-remaining56/AutoResearch-overnight-control')
ENTRY_SHA='0480d1809ad147da834a1640c118031fabf8cdfacbff1837fc3255eecf611e89'
PROTOCOL='remaining56-v1'
DENYLIST={'path': '/private/tmp/gio-reference-remaining56-consumed-denylist-v2/typed-denylist.json', 'sha256': '6c272e0091356f6ee99e2bc814c1b333977f025e7ce2e2eb77ea894ea79ccd39'}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pinned(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('artifact_pin_mismatch')
    return json.loads(raw)
def now():return datetime.now(timezone.utc)
def deadline(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None or t>datetime(2026,11,15,17,tzinfo=timezone.utc):raise ValueError('invalid_deadline')
    return t

def write(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

class EventLog:
    def __init__(self,path):
        self.fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_APPEND,0o600)
        self.lock=threading.Lock();self.sequence=0
    def __call__(self,event):
        with self.lock:
            row=dict(event,sequence=self.sequence,thread_id=threading.get_ident())
            raw=(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
            while raw:
                count=os.write(self.fd,raw)
                if count<=0:raise OSError('diagnostic_append_failed')
                raw=raw[count:]
            os.fsync(self.fd);self.sequence+=1
    def close(self):os.close(self.fd)

def invocation(envelope):
    kind=envelope['kind'];inputs=envelope['inputs']
    if kind=='profile':
        batch=pinned(inputs['batch'])
        if type(batch['max_workers']) is not int or batch['max_workers'] not in [1,2] or batch['code_sha']!=RUNTIMES[kind][0]:raise ValueError('batch_runtime_or_concurrency_mismatch')
        return ['execute','--file',inputs['batch']['path'],'--sha256',inputs['batch']['sha256']]
    if kind=='reference':
        plan=pinned(inputs['plan']);lease=pinned(inputs['lease'])
        if plan['final'] is not False or plan['runtime']['commit']!=RUNTIMES[kind][0] or lease['plan_sha256']!=inputs['plan']['sha256'] or plan.get('protocol')!=PROTOCOL or lease.get('protocol')!=PROTOCOL:
            raise ValueError('reference_plan_or_lease_mismatch')
        return ['run','--plan',inputs['plan']['path'],'--lease',inputs['lease']['path']]
    raise ValueError('unsupported_runtime_kind')

def validate(envelope,*,check_only=False):
    if envelope.get('schema_version')!='diagnostic-runtime-envelope-v2' or envelope.get('script_sha256')!=sha(__file__):raise ValueError('envelope_or_script_pin_mismatch')
    if envelope.get('state')!='authorized' and not check_only:raise ValueError('root_authorized_envelope_required')
    kind=envelope['kind']
    if kind not in RUNTIMES:raise ValueError('unsupported_runtime_kind')
    commit,entry=RUNTIMES[kind];runtime=Path(envelope['runtime_root']).resolve()
    if runtime!=REFERENCE_ROOT.resolve() or sha(runtime/entry)!=ENTRY_SHA:raise ValueError('exact_remaining56_runtime_required')
    if envelope.get('runtime_commit')!=commit or envelope.get('entrypoint')!=entry:raise ValueError('runtime_or_entrypoint_not_allowlisted')
    if envelope['observer']!={'path':str(OBSERVER),'sha256':OBSERVER_SHA} or sha(OBSERVER)!=OBSERVER_SHA:raise ValueError('observer_changed')
    if now()>=deadline(envelope['deadline']):raise ValueError('deadline_reached')
    if subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True).strip()!=commit:raise ValueError('runtime_HEAD_changed')
    if subprocess.check_output(['git','-C',str(runtime),'status','--porcelain','--untracked-files=no'],text=True).strip():raise ValueError('runtime_dirty')
    for name,expected in envelope['runtime_files'].items():
        target=(runtime/name).resolve()
        if runtime not in target.parents or sha(target)!=expected:raise ValueError('runtime_file_changed')
    required={entry,'autoresearch/llm.py','autoresearch/taste/backends.py'}
    if kind=='profile':required.update({'autoresearch/taste/overnight/backends.py','autoresearch/taste/overnight/runner.py','autoresearch/taste/overnight/consumer.py','autoresearch/taste/overnight/contracts.py'})
    if not required<=set(envelope['runtime_files']):raise ValueError('runtime_module_pins_missing')
    if envelope['denylist']!=DENYLIST:raise ValueError('exact_remaining56_typed12_consumed_guard_required')
    denied=pinned(envelope['denylist'])
    if denied.get('schema_version')!='provider-unknown-wire-denylist-v2':raise ValueError('typed_historical_denylist_required')
    blocked=denied['identity_denylists']
    if set(blocked)!={'body_compact_json_sha256','endpoint_body_sorted_json_sha256'}:raise ValueError('historical_identity_conventions_missing')
    if not PROFILE<=set(blocked['body_compact_json_sha256']) or not REFERENCE<=set(blocked['endpoint_body_sorted_json_sha256']):raise ValueError('historical_denylist_incomplete')
    args=invocation(envelope)
    root=Path(envelope['output_root']).resolve()
    allowed=Path('/private/tmp/gio-profile-20261115-coordinator/diagnostic-envelopes')
    if allowed not in root.parents or root.exists():raise ValueError('fresh_external_diagnostics_root_required')
    if not check_only:
        authority=pinned(envelope['authorization'])
        if authority.get('state',authority.get('status'))!='authorized':raise ValueError('root_inspection_not_authorized')
    return runtime/entry,args,blocked

def execute(envelope):
    entry,args,blocked=validate(envelope)
    spec=importlib.util.spec_from_file_location('provider_boundary_observer',OBSERVER)
    observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
    root=Path(envelope['output_root']);root.mkdir(parents=True,mode=0o700,exist_ok=False)
    identity={'canonical_envelope_sha256':digest(envelope),'wrapper_script_sha256':sha(__file__)}
    write(root/'ENVELOPE_CLAIM.json',dict(identity,envelope=envelope,claimed_at=now().isoformat(),no_retry_or_resume=True))
    log=EventLog(root/'events.jsonl');state=None;code=0;error_type=None;close_failed=False
    runtime=Path(envelope['runtime_root']);old_cwd=Path.cwd();old_argv=sys.argv[:];old_path=sys.path[:]
    import urllib.request
    original_open=urllib.request.urlopen
    def deadline_open(request,*a,**k):
        if now()>=deadline(envelope['deadline']):raise ValueError('deadline_before_transport')
        return original_open(request,*a,**k)
    try:
        sys.dont_write_bytecode=True;sys.path.insert(0,str(runtime));sys.argv=[str(entry)]+args;os.chdir(runtime)
        with observer.observe(log,opener=deadline_open,identity_denylists=blocked) as state:
            try:runpy.run_path(str(entry),run_name='__main__')
            except SystemExit as exc:code=0 if exc.code is None else exc.code if type(exc.code) is int else 2
            except Exception as exc:code=2;error_type=type(exc).__name__ if type(exc).__name__ in ['ValueError','RuntimeError','OSError'] else 'other'
    finally:
        os.chdir(old_cwd);sys.argv=old_argv;sys.path[:]=old_path
        try:log.close()
        except Exception:close_failed=True
    diagnostics=state.summary() if state else {'diagnostic_write_failed':True,'dropped_event_count':0}
    entry_code=code
    diagnostics['diagnostic_close_failed']=close_failed
    if diagnostics['diagnostic_write_failed'] or close_failed:code=code or 2
    try:events_sha=sha(root/'events.jsonl')
    except Exception:events_sha=None;diagnostics['diagnostic_hash_failed']=True;code=code or 2
    terminal=dict(identity,status='complete' if code==0 else 'stopped',entry_exit_code=entry_code,wrapper_exit_code=code,safe_exception_type=error_type,diagnostics=diagnostics,events_sha256=events_sha,event_count=log.sequence,scientific_runtime_commit=envelope['runtime_commit'],observer_sha256=OBSERVER_SHA,no_retry_or_resume=True)
    try:write(root/'envelope-terminal.json',terminal)
    except Exception:
        print('diagnostic_terminal_write_failed_no_resume',file=sys.stderr)
        return code or 2
    return code

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--envelope',required=True);ap.add_argument('--envelope-sha256',required=True);ap.add_argument('--check',action='store_true');a=ap.parse_args()
    env=pinned({'path':a.envelope,'sha256':a.envelope_sha256})
    if a.check:validate(env,check_only=True);print('Read-only envelope check passed; no authority, claims or execution.');return 0
    return execute(env)
if __name__=='__main__':raise SystemExit(main())
