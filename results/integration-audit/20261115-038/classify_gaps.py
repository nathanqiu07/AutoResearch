#!/usr/bin/env python3
"""Conservative static source-import closure; does not execute imported code."""
import argparse,ast,hashlib,json,subprocess
from pathlib import Path

def run(a):
 root=Path(a.root);coverage=json.loads(Path(a.coverage).read_text());availability=json.loads(Path(a.availability).read_text());catalog=coverage['catalog']
 commit='9616fe8a3c550664d8aae0b72c938d936c0a7347';scope=max((g for g in coverage['source_scopes'] if g['context'].get('source_commit')==commit),key=lambda g:len(g['code_refs']))
 refs=scope['code_refs'];repo=next(x['git_match']['repository'] for x in availability['objects'] if x['commit']==commit and x['git_match']);read_hashes={};cache={}
 def modulepath(name):
  path=name.replace('.','/')
  return path+'.py' if path+'.py' in refs else path+'/__init__.py' if path+'/__init__.py' in refs else None
 def imports(tree,module=None):
  package=module if module and module.endswith('.__init__') else module.rsplit('.',1)[0] if module and '.' in module else ''
  if package.endswith('.__init__'):package=package[:-9]
  names=set()
  for n in ast.walk(tree):
   if isinstance(n,ast.Import):names.update(x.name for x in n.names)
   if isinstance(n,ast.ImportFrom):
    if n.level:
     parts=package.split('.') if package else [];base='.'.join(parts[:len(parts)-n.level+1]);base+=(('.'+n.module) if n.module else '')
    else:base=n.module or ''
    names.add(base);names.update(base+'.'+x.name for x in n.names if x.name!='*')
  out=set()
  for name in names:
   if not name.startswith('autoresearch'):continue
   parts=name.split('.')
   for i in range(1,len(parts)+1):
    path=modulepath('.'.join(parts[:i]))
    if path:out.add(path)
  return out
 def closure(starts):
  seen=set();queue=list(starts)
  while queue:
   path=queue.pop()
   if path in seen:continue
   seen.add(path)
   if path not in cache:
    b=subprocess.check_output(['git','--no-optional-locks','-C',repo,'show',commit+':'+path]);pin=hashlib.sha256(b).hexdigest();assert pin==refs[path];cache[path]=ast.parse(b);read_hashes[path]=pin
   module=path[:-3].replace('/','.');queue.extend(imports(cache[path],module)-seen)
  return sorted(seen)
 scopes=[]
 for name,paths in [('001_confidence',['20261115-001/confidence/probe.py','20261115-001/confidence/test_safe_fallback.py']),('001_to003_profile_loader',['20261115-003/tool_snapshot/profile_audit.py'])]:
  starts=set()
  for path in paths:starts.update(imports(ast.parse((root/path).read_bytes())))
  transitive=closure(starts)
  scopes.append({'scope':name,'public_readers':paths,'direct_project_imports':sorted(starts),'conservative_static_import_closure':transitive,'missing_direct_imports':[p for p in sorted(starts) if refs[p] not in catalog],'missing_static_closure_members':[p for p in transitive if refs[p] not in catalog]})
 results=[]
 for row in availability['objects']:
  row=dict(row);path=row['path'];reasons=[]
  if row['commit']==commit:
   for s in scopes:
    if path in s['direct_project_imports']:reasons.append({'priority':'direct_reproducer_import','scope':s['scope']})
    elif path in s['conservative_static_import_closure']:reasons.append({'priority':'conservative_static_import_dependency','scope':s['scope']})
   if not reasons:reasons=[{'priority':'recorded_source_inventory_only_not_reached_by_static_closure'}]
   if path.endswith('viewer 2.py'):
    assert refs[path]==refs['autoresearch/taste/viewer.py'];row['exact_byte_alias_source']={'commit':commit,'path':'autoresearch/taste/viewer.py','sha256':refs[path]};reasons=[{'priority':'untracked_duplicate_inventory_alias_not_imported'}]
  elif path=='tests/test_overnight_contracts.py':reasons=[{'priority':'direct_fixture_import_and_test_invocation','evidence':'20261115-007/runner/reproduce.py:61; provenance/reproduce.py:214'}]
  elif path=='tests/test_overnight_runner.py':reasons=[{'priority':'explicit_unittest_command_and_strict_source_manifest_gate','evidence':('20261115-007' if row['commit'].startswith('05c') else '20261115-010')+'/reproduce.py or runner/reproduce.py:55'}]
  else:reasons=[{'priority':'explicit_audit004_source_record_comparison','limit':'Historical recorded-commit source; actual execution-time loaded bytes were not independently attested.'}]
  row['load_bearing_classification']=reasons;results.append(row)
 out={'schema_version':'audit038-gap-classification-v1','source_bytes_retained_by_this_step':False,'draft_static_scopes':scopes,'draft_git_files_read_and_verified':read_hashes,'classified_candidates':results,'limits':['Static closure includes conditional/function-local imports; it is an upper bound, not an observed import trace.','Direct public reproducer imports and explicit unittest commands are stronger load-bearing evidence.','Full source-manifest comparison may require inventory-only files even when not imported.','The untracked duplicate can be reconstructed from its hash-identical tracked viewer.py; no owner working-tree file was read.']}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 for s in scopes:print(s['scope'],'direct_missing',s['missing_direct_imports'],'static_missing',s['missing_static_closure_members'])
 print('Verified immutable draft dependency objects:',len(read_hashes))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ('root','coverage','availability','out'):p.add_argument('--'+name,required=True)
 run(p.parse_args())
