"""Run the frozen verifier from relocated public code/metadata, without Git."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import time

PINS = {
 'verify_retention.py':'8d578b07f9273d6ef2d7ef217f05aa4b760668a521d0535cb8e25e72f6c21616',
 'source-recovery-map.json':'28506b98ea55811ab102ea0c4a4d01cb9eef9785595b08c87e2889d10c0509c2',
 'retained/source-manifest.json':'adae933f29ed88365934af8ceb19fe499e7a1040314c1be83425c3331555608f',
 'retained/selected-code.tar.gz':'d5cc90be5a823ff97f5e95a9c316e93b9392ec4e2bd858f7c91db67f276dd369',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--audit-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    opened = {}
    def read(path,pin):
        raw = path.read_bytes()
        if sha(raw)!=pin:
            raise ValueError('Input pin mismatch')
        opened[str(path)] = raw
        return raw
    core = {name:read(a.stage/name,pin) for name,pin in PINS.items()}
    coverage = json.loads(core['source-recovery-map.json'])
    needed = {}
    for edge in coverage['source_edges']:
        route = edge['recovery_route']
        kind = route['kind']
        if kind=='public_file':
            name,pin = route['path'],edge['sha256']
        elif kind=='public_archive_member':
            name,pin = route['archive'],route['archive_sha256']
        elif kind=='private_archive_indexed_member':
            name,pin = route['receipt'],route['receipt_sha256']
        else:
            continue
        if name in needed and needed[name]!=pin:
            raise ValueError('Conflicting public route pin')
        needed[name] = pin
    with tempfile.TemporaryDirectory(prefix='public-relocation-038-',dir=a.out) as directory:
        temp = Path(directory)
        relocated_audit,relocated_stage = temp/'checkout',temp/'artifact'
        for name,pin in needed.items():
            parts = PurePosixPath(name)
            if parts.is_absolute() or '..' in parts.parts:
                raise ValueError('Unsafe public route')
            raw = read(a.audit_root/'results/integration-audit'/name,pin)
            target = relocated_audit/'results/integration-audit'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
        for name,raw in core.items():
            target = relocated_stage/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
        # The wrapper denies original roots, subprocesses/Git, and networking.
        guard = temp/'guarded_run.py'
        guard.write_text('''import json, pathlib, runpy, sys
artifact,audit,out,original_stage,original_audit=sys.argv[1:]
artifact=pathlib.Path(artifact);audit=pathlib.Path(audit);out=pathlib.Path(out)
forbidden=[pathlib.Path(original_stage).resolve(),pathlib.Path(original_audit).resolve()]
accessed=set()
def guard(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):
  raise RuntimeError('Network and subprocess/Git forbidden in portability replay')
 if event=='open' and isinstance(args[0],(str,bytes)):
  path=pathlib.Path(args[0]).resolve()
  if any(path==root or root in path.parents for root in forbidden):
   raise RuntimeError('Original-machine path access forbidden')
  if artifact.resolve() in path.parents or audit.resolve() in path.parents:accessed.add(str(path))
sys.addaudithook(guard)
sys.argv=[str(artifact/'verify_retention.py'),'--audit-root',str(audit),
 '--archive',str(artifact/'retained/selected-code.tar.gz'),
 '--manifest',str(artifact/'retained/source-manifest.json'),'--manifest-sha256','adae933f29ed88365934af8ceb19fe499e7a1040314c1be83425c3331555608f',
 '--coverage-map',str(artifact/'source-recovery-map.json'),'--coverage-map-sha256','28506b98ea55811ab102ea0c4a4d01cb9eef9785595b08c87e2889d10c0509c2',
 '--out',str(out/'verifier-report.json')]
runpy.run_path(str(artifact/'verify_retention.py'),run_name='__main__')
(out/'guard-opened-paths.json').write_text(json.dumps({'original_roots_forbidden':list(map(str,forbidden)),'opened_relocated_paths':sorted(accessed),'subprocess_and_network_forbidden':True},indent=2)+'\\n')
''')
        guard_raw = guard.read_bytes()
        argv = [sys.executable,'-I','-B',str(guard),str(relocated_stage),str(relocated_audit),str(a.out),str(a.stage),str(a.audit_root)]
        start = time.monotonic()
        result = subprocess.run(argv,capture_output=True,text=True,env={'PATH':'/nonexistent','PYTHONDONTWRITEBYTECODE':'1'})
        (a.out/'guarded_run.py').write_bytes(guard_raw)
        (a.out/'invocation.json').write_text(json.dumps({'argv':argv,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'PATH':'/nonexistent'},indent=2)+'\n')
        (a.out/'stdout.txt').write_text(result.stdout)
        (a.out/'stderr.txt').write_text(result.stderr)
        if result.returncode!=0:
            raise ValueError('Relocated verifier failed; see preserved stderr')
        report = json.loads((a.out/'verifier-report.json').read_text())
        if report['checks_passed']!=900 or report['checks_failed'] or report['git_object_checks']:
            raise ValueError('Unexpected portable verification result')
    for path,raw in opened.items():
        if Path(path).read_bytes()!=raw:
            raise ValueError('Original code/metadata changed')
    summary = {'schema_version':'independent-source-retention38-portability-v1','public_route_files_relocated':len(needed),'core_artifact_files_relocated':len(core),
       'checks_passed':report['checks_passed'],'checks_failed':0,'git_requested':False,'git_and_network_denied':True,'original_stage_and_audit_roots_denied':True,
       'private_raw_archives_read':False,'temporary_relocated_public_copies_removed':True,'originals_unchanged':True,
       'copied_input_inventory':[{'path':p,'sha256':sha(raw),'bytes':len(raw)} for p,raw in sorted(opened.items())]}
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:summary[k] for k in ('checks_passed','public_route_files_relocated','git_and_network_denied','original_stage_and_audit_roots_denied')}))


if __name__=='__main__':
    main()
