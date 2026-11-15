"""Independently reconstruct old audit026 profile identities from released recipe.

No owner replay/project imports. Only pinned inputs, standard-library algorithms,
and the byte-identical independent audit026 content reconstruction are used.
Raw text, vectors, configs and profiles are never exported.
"""
import argparse
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

RELEASE = '3e4cc416b742cdd1a5e9193dee2b6b424279d691'
PINS = {
    '014-semantic-construction-recipe.json': '7f23ebe84186c74d42c0a4f5c8f6a4c13f6de6765559e471dcab44061ab66302',
    '014-recipe-ready.json': 'f86fc93783c97f30e8594c6e376883c97324dac463fabe005f540d3b0f2b4b91',
    '014-semantic-recipe-replay.json': '998cb216711e1bcf2549490987af8e2ea03d3757b2d6ca5ed3dd445968ab6552',
    'prior_reader.py': '11530e66e0104405ed59e98418bbca17b8d009cac70669e512cae80be4c96e9a',
    'PRIOR_INPUT_INVENTORY.json': '6b4f520b1fb70611fdab449054d6facec801543043824a6eaee5e3d1d7e6322f',
}


class NoCalls:
    label = 'no-model-calls'
    model = 'construction-only'

    def __init__(self):
        self.calls = 0

    def complete(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('This independent reconstruction must never call an extractor')


def constants(raw, names):
    result = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    result[target.id] = ast.literal_eval(node.value)
    assert set(result) == set(names)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--supplement-root', type=Path, required=True)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--coordinator-root', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--preservation', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if bool(args.archive_root) != bool(args.preservation) or bool(args.repo) == bool(args.archive_root):
        parser.error('Choose --repo or paired --archive-root/--preservation')
    import hashlib
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    supplement = args.supplement_root.resolve()
    for name, pin in PINS.items():
        assert sha((supplement/name).read_bytes()) == pin, name
    spec = importlib.util.spec_from_file_location('audit026_independent_reference', supplement/'prior_reader.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    canon, digest = audit.canon, audit.digest
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/'reader-used.py').write_bytes(Path(__file__).read_bytes())
    recipe = json.loads((supplement/'014-semantic-construction-recipe.json').read_text())
    handoff = json.loads((supplement/'014-recipe-ready.json').read_text())
    # Hash-verified owner replay is inventory evidence only, never our result oracle.
    original_inventory = json.loads((supplement/'PRIOR_INPUT_INVENTORY.json').read_text())['files']
    archived = audit.ArchivedInputs(args.archive_root, args.preservation) if args.archive_root else None
    reads, locations, checks = {}, {}, []

    def check(name, condition):
        checks.append({'name': name, 'verified': bool(condition)})
        if not condition:
            # Only safe progress metadata is preserved even if reconstruction fails.
            (args.out/'failed-checks.json').write_text(json.dumps(checks, indent=2)+'\n')
            raise AssertionError(name + ' failed; no raw input is emitted')

    def git_bytes(path, rev=audit.COMMIT):
        entries = [x for x in original_inventory if x['kind']=='git_object' and x['path']==path
                   and rev in (x['commit'], x['full_commit'])]
        assert len(entries) == 1, 'Input not in original approved inventory'
        entry = entries[0]
        if archived:
            raw, actual = archived.read('git_object', path, rev)
            locations[str(actual)] = entry['sha256']
        else:
            raw = subprocess.check_output(['/usr/bin/git','-C',str(args.repo),'show',rev+':'+path],
                    env={'PATH':'/usr/bin:/bin'}, stderr=subprocess.DEVNULL)
        check('git_pin:'+rev+':'+path, sha(raw)==entry['sha256'])
        reads[rev+':'+path] = entry
        return raw

    def source_release(researcher):
        relative, pin = audit.RELEASES[researcher]
        entries = [x for x in original_inventory if x['kind']=='external' and x['sha256']==pin]
        assert len(entries) == 1
        entry = entries[0]
        if archived:
            raw, actual = archived.read('external', entry['path'])
        else:
            actual = (args.coordinator_root/relative).resolve(strict=True)
            actual.relative_to(args.coordinator_root.resolve(strict=True))
            raw = actual.read_bytes()
        locations[str(actual)] = pin
        check('approved_release_pin:'+researcher, sha(raw)==pin)
        reads[entry['path']] = entry
        return json.loads(raw)

    def deny_network(event, unused):
        if event.startswith('socket.'):
            raise RuntimeError('network prohibited by recipe audit')
    sys.addaudithook(deny_network)
    base = audit.BASE
    index_raw = git_bytes(base+'live-embeddings-v2/index.json')
    original_raw = git_bytes(base+'live-embeddings-v2/construction-check.json')
    index, original = json.loads(index_raw), json.loads(original_raw)
    baseline = git_bytes('autoresearch/taste/overnight/baselines.py', audit.RUNTIME)
    retrieval = git_bytes('autoresearch/taste/overnight/retrieval.py', audit.RUNTIME)
    consumer = git_bytes('autoresearch/taste/overnight/consumer.py', audit.RUNTIME)
    contract = git_bytes('autoresearch/taste/overnight/contracts.py', audit.RUNTIME)
    # These literal constants are extracted from immutable code without importing it.
    baseline_version = constants(baseline, ['VERSION'])['VERSION']
    retrieval_version = constants(retrieval, ['VERSION'])['VERSION']
    contract_values = constants(contract, ['SCHEMA_VERSION', 'TOKEN_COUNT_METHOD'])
    renderer_hash = sha(b'consumer.py\0'+consumer+b'\0contracts.py\0'+contract)
    policy = {'version': baseline_version, 'retrieval_hash': sha(retrieval),
              'query': 'context_and_ordered_options_only', 'cap': contract_values['TOKEN_COUNT_METHOD'],
              'method_id': 'semantic_retrieval'}
    prompt_hash = digest(policy)
    check('recipe_original_report_pin', recipe['artifact_refs']['original_report']['file_sha256']==sha(original_raw)==audit.CONSTRUCTION_HASH)
    check('recipe_index_pin', recipe['artifact_refs']['index']['file_sha256']==sha(index_raw)==audit.INDEX_HASH)
    check('recipe_runtime_pin', recipe['runtime']['code_sha']==audit.RUNTIME and recipe['runtime']['retrieval_implementation_hash']==sha(retrieval))
    check('handoff_pins_recipe', handoff['outputs'][0]['sha256']==PINS['014-semantic-construction-recipe.json'])
    expected_keys = {'allowed_source_manifest_hash','allowed_sources','chunk_chars','code_sha','consumer_identity',
        'decision','embedding_bundle','embedding_bundle_sha256','embedding_dimensions','embedding_model',
        'extractor_settings','method_id','personalization_cap','replicate_id','researcher_id','top_k'}
    check('recipe_exact_16_fields', set(recipe['config_key_set'])==expected_keys and len(recipe['config_key_set'])==16)
    stub = NoCalls()
    identity = {'label':stub.label,'class':type(stub).__name__,'model':stub.model,'endpoint':getattr(stub,'base_url','')}
    check('NoCalls_identity', identity=={'label':recipe['extractor']['label'],'class':recipe['extractor']['class_name'],
        'model':recipe['extractor']['model'],'endpoint':recipe['extractor']['recorded_endpoint']} and not hasattr(stub,'base_url'))
    releases = {name:source_release(name) for name in audit.RELEASES}
    for name, release in releases.items():
        declared = next(x for x in recipe['released_inputs'] if x['researcher_id']==name)
        check('recipe_approved_release_identity:'+name, digest(release)==declared['semantic_sha256'] and
              declared['file_sha256']==audit.RELEASES[name][1])
    rows, ordered_keys = [], []
    records = {(x['researcher_id_sha256'],x['decision_item_sha256'],x['personalization_cap']):x for x in original['rows']}
    check('original_84_unique_rows', len(records)==len(original['rows'])==84)
    for entry in index['items']:
        researcher=entry['researcher_id'];release=releases[researcher];source=release['sources'];documents=source['documents']
        matches=[x for x in release['items'] if x['researcher_id']==researcher and x['item_id']==entry['item_id'] and x['option_order_id']==entry['option_order_id']]
        check('one_exact_ordered_item',len(matches)==1)
        item=matches[0];decision={'context':item['context'],'options':item['options']}
        bundle_raw=git_bytes(entry['bundle_path']);bundle=json.loads(bundle_raw)
        check('bundle_file_and_semantic_pin',sha(bundle_raw)==entry['file_sha256'] and bundle['bundle_sha256']==entry['bundle_sha256']==digest({k:v for k,v in bundle.items() if k!='bundle_sha256'}))
        check('bundle_decision_permission_binding',digest(decision)==entry['decision_sha256']==bundle['request']['query_sha256'] and audit.permission_hash(documents)==bundle['request']['permission_hash'])
        chunks=audit.chunks_for(documents)
        for cap in recipe['config_reference_fields']['personalization_cap']:
            config=copy.deepcopy(recipe['config_literal_fields'])
            config.update(allowed_source_manifest_hash=source['allowed_source_manifest_hash'],allowed_sources=source['source_manifest'],
                decision=decision,embedding_bundle=bundle,embedding_bundle_sha256=bundle['bundle_sha256'],personalization_cap=cap,researcher_id=researcher)
            check('config_exact_fields',set(config)==expected_keys and not set(recipe['explicitly_absent_config_fields']).intersection(config))
            content=audit.pack_ranked(chunks,bundle['vectors'],cap)
            selected=content['passages'];count=len(canon(content).encode())
            cache=digest({'version':retrieval_version,'implementation_hash':sha(retrieval),'sources':source['source_manifest'],
                'permission_hash':audit.permission_hash(documents),'query':canon(decision),'consumer':config['consumer_identity'],'config':config})
            usage={'calls':0,'input_tokens':0,'output_tokens':0,'cost_usd':0,'cost_status':'no_model_calls',
                'retrieval_implementation_hash':sha(retrieval),'available_chunks':len(chunks),'embedding_bundle_sha256':bundle['bundle_sha256'],
                'embedding_model':config['embedding_model'],'embedding_production_usage':bundle['usage'],
                'retrieval_cache_key':cache,'decision_sha256':digest(decision),'selected_passages':len(selected)}
            # Independently transcribed canonical artifact formula from pinned contracts.py:234.
            body={'schema_version':contract_values['SCHEMA_VERSION'],'researcher_id':researcher,'method_id':'semantic_retrieval',
                'config_id':digest(config),'config':config,'allowed_source_manifest_hash':source['allowed_source_manifest_hash'],
                'documents_hash':digest(documents),'extractor':identity,'extractor_settings':config['extractor_settings'],
                'replicate_id':config['replicate_id'],'content':content,'content_sha256':digest(content),'status':'complete','error_code':None,
                'intentional_empty':False,'token_count':count,'token_count_method':contract_values['TOKEN_COUNT_METHOD'],'personalization_cap':cap,
                'confidence_status':'uncalibrated','weights_status':'unavailable','fit_usage':usage,'prompt_version':baseline_version,
                'prompt_sha256':prompt_hash,'method_implementation_hash':sha(baseline),'renderer_implementation_hash':renderer_hash,
                'compatibility_status':'pinned','code_sha':audit.RUNTIME}
            profile_id=digest(body)
            projected=[{'document_id_sha256':digest(x['document_id']),'end':x['end'],'start':x['start'],
                        'text_sha256':sha(x['text'].encode())} for x in selected]
            spans_hash=digest(projected)
            key=(digest(researcher),digest((entry['item_id'],entry['option_order_id'])),cap);ordered_keys.append(key)
            old=records[key]
            calculated={'profile_id':profile_id,'config_id':digest(config),'prompt_sha256':prompt_hash,
                'selected_spans_sha256':spans_hash,'content_sha256':digest(content),'rendered_utf8_bytes':count,
                'passage_count':len(selected),'method_implementation_hash':sha(baseline),'renderer_implementation_hash':renderer_hash}
            for field,value in calculated.items():
                check('row_'+str(len(rows))+'_'+field,value==old[field])
            check('complete_cap_and_zero_calls',len(selected)>0 and count<=cap and stub.calls==0 and old['status']=='complete')
            rows.append({'researcher_id_sha256':key[0],'decision_item_sha256':key[1],'personalization_cap':cap,
                         'status':'verified','calculated':calculated,'recorded':{k:old[k] for k in calculated}})
    check('exact_original_row_order',ordered_keys==[(x['researcher_id_sha256'],x['decision_item_sha256'],x['personalization_cap']) for x in original['rows']])
    check('all_84_and_no_calls',len(rows)==84 and stub.calls==0)
    check('no_owner_or_project_module_imported',not any(x.startswith('autoresearch') for x in sys.modules))
    for path,pin in locations.items():
        check('input_unchanged:'+sha(path.encode()),sha(Path(path).read_bytes())==pin)
    if archived:
        archived.verify_read_files()
    for name,pin in PINS.items():
        check('supplement_unchanged:'+name,sha((supplement/name).read_bytes())==pin)
    supplementary=[{'kind':'git_object','commit':RELEASE,'path':base+n,'sha256':PINS[n],'size_bytes':(supplement/n).stat().st_size}
                   for n in list(PINS)[:3]]
    report={'audit':'semantic-runtime-26-recipe-retest','recipe_release_commit':RELEASE,'original_release_commit':audit.COMMIT,
        'runtime_commit':audit.RUNTIME,'script_sha256':sha(Path(__file__).read_bytes()),'prior_reader_sha256':PINS['prior_reader.py'],
        'argv':sys.argv,'input_mode':'private_archive' if archived else 'original_git_and_files','checks':checks,
        'check_counts':{'verified':len(checks),'failed':0},'rows':rows,'matching_profile_ids':84,'matching_config_ids':84,
        'matching_prompt_sha256':84,'matching_selected_spans_sha256':84,'model_calls':stub.calls,'extractor_identity':identity,
        'config_key_set':sorted(expected_keys),'renderer_implementation_hash':renderer_hash,'prompt_policy':policy,
        'owner_replay_executed':False,'owner_replay_report_used_as_oracle':False,'project_code_imported':False,
        'limits':['Construction-stub profile identities only; production transport identities can differ.',
                  'No prediction quality, saved-profile execution reuse, provider authenticity or billing claim.',
                  'Past process clean/detached and recipe provenance remain producer metadata.',
                  'Original raw inputs stay private; no raw source, query, vector, config or profile is exported.']}
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.out/'input-inventory.json').write_text(json.dumps({'reused_approved_inputs':list(reads.values()),
        'supplementary_inputs':supplementary,'audit_helpers':{k:PINS[k] for k in ('prior_reader.py','PRIOR_INPUT_INVENTORY.json')},'raw_copied':False},indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('check_counts','matching_profile_ids','matching_config_ids','matching_prompt_sha256','matching_selected_spans_sha256','model_calls')},indent=2))


if __name__=='__main__':
    main()
