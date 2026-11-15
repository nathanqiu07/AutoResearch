import json, pathlib, runpy, sys
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
(out/'guard-opened-paths.json').write_text(json.dumps({'original_roots_forbidden':list(map(str,forbidden)),'opened_relocated_paths':sorted(accessed),'subprocess_and_network_forbidden':True},indent=2)+'\n')
