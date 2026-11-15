"""Independent source-byte and provenance checks; never import retained code."""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

PINS = {
 'retained/source-manifest.json':'adae933f29ed88365934af8ceb19fe499e7a1040314c1be83425c3331555608f',
 'retained/selected-code.tar.gz':'d5cc90be5a823ff97f5e95a9c316e93b9392ec4e2bd858f7c91db67f276dd369',
 'source-recovery-map.json':'28506b98ea55811ab102ea0c4a4d01cb9eef9785595b08c87e2889d10c0509c2',
 'map-01/coverage.json':'cc577b851b1272f38f98337dcbbee9367bc7ec38faa77f9f1c659f34a6da43b3',
 'map-01/candidate-missing-source-refs.json':'40cfc98dc5661ba72f4bd83746c037e488ef2a1c070861b8878119617a2a613a',
 'load-bearing-classification.json':'b995aee55c17c9eb6a9dfd76c96b5a2d74213f22e5a0526a6a81d92789ca3818',
 'named-test-dependencies.json':'1d688918cd10cd9ceb20abb6ed0074d60d1154aebf0da3aa560d27cb7ff7f12a',
 'verify_retention.py':'8d578b07f9273d6ef2d7ef217f05aa4b760668a521d0535cb8e25e72f6c21616',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def pointer(value, path):
    for part in path.strip('/').split('/'):
        if part:
            part = part.replace('~1','/').replace('~0','~')
            value = value[int(part)] if isinstance(value,list) else value[part]
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--audit-root',type=Path,required=True)
    p.add_argument('--git-repo-map',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    checks, opened, git_checks = [], {}, []
    def check(name, ok):
        checks.append({'name':name,'passed':bool(ok)})
        if not ok:
            raise ValueError('Failed independent check: '+name)
    def read(path,pin=None):
        raw = path.read_bytes()
        if pin is not None:
            check('pin:'+str(path),sha(raw)==pin)
        opened[str(path)] = raw
        return raw
    core = {name:read(a.stage/name,pin) for name,pin in PINS.items()}
    manifest = json.loads(core['retained/source-manifest.json'])
    coverage = json.loads(core['source-recovery-map.json'])
    prior = json.loads(core['map-01/coverage.json'])
    classification = json.loads(core['load-bearing-classification.json'])
    candidates = json.loads(core['map-01/candidate-missing-source-refs.json'])
    named_tests = json.loads(core['named-test-dependencies.json'])
    audit = a.audit_root/'results/integration-audit'
    public_pins = dict(prior['accessed_public_files'])
    public_pins.update(coverage['additional_metadata_inputs'])
    def public(rel,pin=None):
        relative = PurePosixPath(rel)
        check('safe_public_path:'+rel,not relative.is_absolute() and '..' not in relative.parts)
        path = (audit/rel).resolve()
        path.relative_to(audit.resolve())
        expected = pin or public_pins[rel]['sha256']
        return read(path,expected)
    raw_tar = gzip.decompress(core['retained/selected-code.tar.gz'])
    check('uncompressed_archive_hash',sha(raw_tar)==manifest['uncompressed_tar_sha256'])
    expected = {r['archive_member']:r for r in manifest['files']}
    check('exact30_unique_members',len(expected)==len(manifest['files'])==manifest['file_count']==30)
    source_bytes = {}
    with tarfile.open(fileobj=io.BytesIO(raw_tar),mode='r:') as tar:
        members = tar.getmembers()
        check('exact_regular_member_names',len(members)==30 and [m.name for m in members]==sorted(expected))
        for member in members:
            row = expected[member.name]
            name = PurePosixPath(member.name)
            check('safe_regular:'+member.name,member.isfile() and not name.is_absolute() and '..' not in name.parts and
                  member.name=='sources/'+row['commit']+'/'+row['path'] and row['path'].endswith('.py'))
            check('normalized_tar_metadata:'+member.name,member.mode==0o644 and member.uid==member.gid==member.mtime==0)
            raw = tar.extractfile(member).read()
            check('exact_source_bytes:'+member.name,sha(raw)==row['sha256'] and len(raw)==row['bytes'])
            check('git_blob_identity:'+member.name,hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob'])
            source_bytes[member.name] = raw
    check('source_total',sum(map(len,source_bytes.values()))==manifest['source_bytes']==534347)
    counts = Counter(r['provenance'] for r in manifest['files'])
    check('29_historical_plus_one_derived',counts=={'historically_recorded_byte_hash_matches_immutable_git':29,'derived_now_from_recorded_clean_commit_not_a_historical_per_file_pin':1})
    check('no_full_replay_claim',manifest['full_old_audit_replay_performed'] is False and manifest['environment_or_provider_recovery_claimed'] is False and manifest['raw_data_or_labels_included'] is False)
    for row in manifest['files']:
        if row['provenance'].startswith('derived_now_'):
            continue
        witnessed = 0
        for ref in row['references']:
            node = pointer(json.loads(public(ref['evidence'])),ref['pointer'])
            if isinstance(node,dict):
                check('historical_path_hash:'+row['path'],node[row['path']]==row['sha256'])
            else:
                exact = [x for x in node if x.get('sha256')==row['sha256'] and
                         (x.get('path')==row['path'] or (ref['pointer']=='/runner_sources' and PurePosixPath(x.get('path','')).name==PurePosixPath(row['path']).name))]
                check('historical_record_hash:'+row['path'],len(exact)==1)
            witnessed += 1
        check('historical_evidence_present:'+row['path'],witnessed>0)
    derived = [r for r in manifest['files'] if r['provenance'].startswith('derived_now_')][0]
    capture = json.loads(public('20261115-001/confidence/run-01/capture.json'))['runs']['draft']
    check('derived_test_clean_recorded_commit',capture['before']['commit']==capture['after']['commit']==derived['commit'] and
          capture['before']['tracked_status']==capture['after']['tracked_status']=='')
    check('derived_test_named_in_historical_command',derived['path']=='tests/test_research_loop_ws_d.py' and 'tests.test_research_loop_ws_d' in capture['executions']['existing_tests']['argv'])
    check('derived_test_not_historical_per_file_pin',derived['path'] not in capture['before']['sha256'] and derived['path'] not in capture['after']['sha256'])
    check('four_named_test_dependencies',len(named_tests)==4 and sum(not r['retained_locations'] for r in named_tests)==1)
    alias = manifest['aliases'][0]
    check('one_content_only_alias',len(manifest['aliases'])==1 and alias['recorded_path']=='autoresearch/taste/viewer 2.py' and
          alias['resolve_from']['path']=='autoresearch/taste/viewer.py' and alias['status']=='content_equivalence_alias_only_original_untracked_file_provenance_not_recovered')
    check('alias_bytes_not_alias_provenance',sha(source_bytes[alias['resolve_from']['archive_member']])==alias['recorded_sha256'] and
          all('viewer 2.py' not in name for name in source_bytes))
    for ref in alias['evidence']:
        node = pointer(json.loads(public(ref['evidence'])),ref['pointer'])
        check('historical_alias_hash',node[alias['recorded_path']]==alias['recorded_sha256'])
    routes, archives = {}, {}
    for edge in coverage['source_edges']:
        route,pin = edge['recovery_route'],edge['sha256']
        key = canonical([route,pin])
        if key in routes:
            continue
        kind = route['kind']
        if kind in ('new_selected_code_archive_member','new_retained_content_alias'):
            check('new_route_hash',route['archive_sha256']==manifest['archive_sha256'] and sha(source_bytes[route['member']])==pin)
            status = 'new_public_source_bytes'
        elif kind=='public_file':
            public(route['path'],pin)
            status = 'prior_public_source_bytes'
        elif kind=='public_archive_member':
            path = route['archive']
            if path not in archives:
                archives[path] = public(path,route['archive_sha256'])
            check('consistent_prior_archive_hash',sha(archives[path])==route['archive_sha256'])
            with tarfile.open(fileobj=io.BytesIO(archives[path]),mode='r:*') as tar:
                member = tar.getmember(route['member'])
                check('prior_archive_regular_source',member.isfile())
                check('prior_archive_source_bytes',sha(tar.extractfile(member).read())==pin)
            status = 'prior_public_source_bytes'
        elif kind=='private_archive_indexed_member':
            receipt = json.loads(public(route['receipt'],route['receipt_sha256']))
            check('private_receipt_only_identity',receipt['archive_sha256']==route['archive_sha256'] and
                  len([r for r in receipt['files'] if r.get('archive_member')==route['member'] and r['sha256']==pin])==1)
            status = 'receipt_only_no_private_raw_read'
        else:
            raise ValueError('Unexpected recovery route')
        routes[key] = status
    check('4186_edges275_routes',len(coverage['source_edges'])==4186 and len(routes)==275)
    check('route_status_distinction',Counter(routes.values())=={'new_public_source_bytes':31,'prior_public_source_bytes':243,'receipt_only_no_private_raw_read':1})
    check('two_original_unresolved_script_hashes_separate',len(coverage['unresolved_metadata_only_scripts'])==2 and all(r['source_path'] is None and r['immutable_commit_path_binding'] is None for r in coverage['unresolved_metadata_only_scripts']))
    fixture_sites = [('20261115-007/runner/reproduce.py','tests.test_overnight_runner'),('20261115-007/provenance/reproduce.py','tests.test_overnight_contracts'),('20261115-010/reproduce.py','tests.test_overnight_runner')]
    for rel, named in fixture_sites:
        tree = ast.parse(public(rel))
        constants = [n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        check('explicit_unittest_callsite:'+rel,named in constants)
        if rel.endswith('runner/reproduce.py') or rel=='20261115-010/reproduce.py':
            check('direct_fixture_import:'+rel,any(isinstance(n,ast.ImportFrom) and n.module=='tests' and any(x.name=='test_overnight_contracts' for x in n.names) for n in ast.walk(tree)))
    for scope in classification['draft_static_scopes']:
        modules = set()
        for rel in scope['public_readers']:
            for node in ast.walk(ast.parse(public(rel))):
                if isinstance(node,ast.Import):
                    modules.update(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:
                    modules.add(node.module)
                    modules.update(node.module+'.'+x.name for x in node.names)
        direct = set(scope['direct_project_imports'])
        check('direct_imports_within_conservative_closure:'+scope['scope'],direct<=set(scope['conservative_static_import_closure']))
        check('direct_import_sources_match_ast:'+scope['scope'],all(x.endswith('/__init__.py') or x[:-3].replace('/','.') in modules for x in direct))
    if a.git_repo_map:
        gitmap = json.loads(read(a.git_repo_map))
        for row in manifest['files']:
            argv = ['git','--no-optional-locks','-C',gitmap[row['commit']],'cat-file','blob',row['commit']+':'+row['path']]
            result = subprocess.run(argv,capture_output=True,env={'PATH':'/usr/bin:/bin','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0'})
            check('independent_git_blob:'+row['path'],result.returncode==0 and result.stdout==source_bytes[row['archive_member']])
            git_checks.append({'argv':argv,'exit_code':result.returncode,'stdout_sha256':sha(result.stdout),'stderr':result.stderr.decode(errors='replace')})
    for path,raw in opened.items():
        check('original_unchanged:'+path,Path(path).read_bytes()==raw)
    report = {'schema_version':'independent-source-retention38-crosscheck-v1','checks_passed':len(checks),'checks_failed':0,'checks':checks,
              'core_pins':PINS,'archive_members':30,'historically_pinned_tracked_members':29,'derived_named_test_members':1,'content_only_untracked_aliases':1,
              'source_bytes':534347,'mapped_edges':4186,'unique_routes':275,'route_status_counts':dict(Counter(routes.values())),
              'original_unresolved_probe_hashes':2,'optional_git_objects_checked':len(git_checks),'git_checks':git_checks,
              'public_inputs_read':[{'path':p,'sha256':sha(b),'bytes':len(b)} for p,b in sorted(opened.items())],
              'retained_source_imported':False,'historical_tests_run':False,'private_raw_archives_read':False,'model_calls':0,
              'limits':['Current immutable Git matches do not attest which code was loaded during historical execution.','Static import closure is conservative; direct fixture imports and named unittest commands have stronger evidence.','One preexisting source route is receipt-only; no private raw archive body was opened.','Original two hash-only probe routes remain unresolved in this frozen map; any later approved recovery belongs to a separate addendum.','No environment/provider/full historical replay recovery is claimed.']}
    with a.out.open('x') as f:
        json.dump(report,f,indent=2,sort_keys=True)
        f.write('\n')
    print(json.dumps({k:report[k] for k in ('checks_passed','checks_failed','archive_members','optional_git_objects_checked','unique_routes','route_status_counts')}))


if __name__=='__main__':
    main()
