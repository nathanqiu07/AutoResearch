"""Independent saved-execution audit. No owner imports, model calls or scoring."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import sys
import tarfile

RUNTIME = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
INDEX_SHA = '9aeea5b0c4fb9668df1d36c548e681c1c5e180e75df74f9475f75b2f08737e3a'
PINS = {
 'reader033_helpers.py': 'd563214bfc922763cb9df2b9b3daab26922f9c03a56b99f6152f0c314cabcc29',
 'prior033-report.json': '8f823181ae1cdd3f27c537a6a028e068e2886e4269194fd3e5e2c985e74b63f8',
 'prior034-report.json': '0816591add6aaea9bfe58df5df8f164831375de7112e8eed8a81cfcd47a54941',
 'prior035-report.json': 'd1f9512120fefb9e014c09761ce682ed64406b10a0f8bf2c3a807e9122d37cd9',
 'source-f6cd4fb5.tar': '573321eae5ef8765ef276d93ce684272057dde71f5a795d339573b142bc307c4',
 'SOURCE_REFERENCE.json': '73cfe25b30075a3fef51cc4f249f2572b736404d98ce32c96f11a5863d657a18',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence-root', type=Path, required=True)
    ap.add_argument('--index', required=True)
    ap.add_argument('--data-root', type=Path)
    ap.add_argument('--recorded-data-root')
    ap.add_argument('--archive-root', type=Path)
    ap.add_argument('--preservation', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if bool(a.archive_root) != bool(a.preservation) or bool(a.data_root) == bool(a.archive_root):
        ap.error('Choose data-root or archive-root/preservation')
    if a.data_root and not a.recorded_data_root:
        ap.error('Recorded data root required')
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    for name, pin in PINS.items():
        if sha((a.evidence_root / name).read_bytes()) != pin:
            raise ValueError('Pinned evidence changed: ' + name)
    spec = importlib.util.spec_from_file_location('frozen_audit033_helpers', a.evidence_root / 'reader033_helpers.py')
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    canon, digest, save = h.canon, h.digest, h.save
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / 'reader-used.py').write_bytes(Path(__file__).read_bytes())
    def deny(event, args):
        if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
            raise RuntimeError('Live operations forbidden')
    sys.addaudithook(deny)
    prior33 = json.loads((a.evidence_root / 'prior033-report.json').read_text())
    prior34 = json.loads((a.evidence_root / 'prior034-report.json').read_text())
    prior35 = json.loads((a.evidence_root / 'prior035-report.json').read_text())
    source = json.loads((a.evidence_root / 'SOURCE_REFERENCE.json').read_text())
    assert source['commit'] == RUNTIME
    with tarfile.open(a.evidence_root / 'source-f6cd4fb5.tar', 'r:') as archive:
        members = {m.name: m for m in archive.getmembers() if m.isfile()}
        assert set(members) == set(source['files'])
        code = {}
        for name, pin in source['files'].items():
            raw = archive.extractfile(members[name]).read()
            assert sha(raw) == pin
            code[name] = raw
    prefix = 'autoresearch/taste/overnight/'
    constants = h.source_constants(code[prefix + 'consumer.py'], ['SYSTEM', 'INSTRUCTION', 'PROMPT_VERSION'])
    renderer = sha(b'consumer.py\0' + code[prefix + 'consumer.py'] + b'\0contracts.py\0' + code[prefix + 'contracts.py'])
    families = {m: module for module, methods in [('profiles_summary.py', ['P1','P2','P3']), ('profiles_principles.py', ['P4','P5','P6']), ('profiles_hypotheses.py', ['P7','P8'])] for m in methods}
    versions = {m: h.source_constants(code[prefix + module], ['PROMPT_VERSION'])['PROMPT_VERSION'] + '-' + m.lower() for m, module in families.items()}
    runner = code[prefix + 'runner.py'].decode()
    assert 'out = Path(output_root) / manifest["job_id"]' in runner
    assert 'out / "traces"' in runner and '"%04d-started.json" % self.attempts' in runner and '"%04d-complete.json" % self.attempts' in runner
    data = h.Inputs(a)
    checks, rows, jobs, batches, trace_derivations = [], [], [], [], []
    def check(name, ok):
        checks.append({'name': name, 'verified': bool(ok)})
        if not ok:
            save(a.out / 'failed-checks.json', checks)
            save(a.out / 'input-inventory.json', {'files': list(data.inventory.values()), 'raw_copied': False})
            raise AssertionError(name + ' failed; raw content not emitted')
    def ref(path, pin):
        return {'path': str(path), 'sha256': pin}
    index = data.read(ref(a.index, INDEX_SHA))
    check('released_dev_runtime', index['runtime_sha'] == RUNTIME and index['stage'] == 'dev' and index['confirmation_authorized'] is False)
    catalog = {j['job_id']: j for j in index['jobs']}
    check('612_unique_jobs', len(catalog) == len(index['jobs']) == index['counts']['all_unique_jobs'] == 612)
    groups = Counter((j['kind'], j['category']) for j in catalog.values())
    check('exact_six_job_categories', groups == {('build','search'):96, ('predict','search'):48, ('build','control'):178, ('predict','control'):178, ('build','hybrid'):56, ('predict','hybrid'):56})
    results = {}
    for jid, indexed in catalog.items():
        result = data.read(indexed['result'])
        results[jid] = result
        check('result_projection:' + jid, all(indexed[k] == result[k] for k in ('job_id','status','code_sha','config_hash','source_manifest_hash','actual_backend','usage')) and
              indexed['manifest_sha256'] == result['manifest_hash'] and indexed['trace_sha256s'] == result['trace_hashes'] and indexed['trace_count'] == len(result['trace_hashes']) and result['code_sha'] == RUNTIME)
        if indexed['kind'] == 'predict':
            check('indexed_prediction_projection:' + jid, len(indexed['prediction_bindings']) == len(result['predictions']) and
                  all(all(pred.get(k) == value for k, value in binding.items()) for pred, binding in zip(result['predictions'], indexed['prediction_bindings'])) and
                  indexed['item_ids'] == [p['item_id'] for p in result['predictions']] and result['status'] == 'complete')
        elif indexed['category'] in ('control','hybrid'):
            check('zero_call_build:' + jid, result['status'] == 'complete' and result['predictions'] == [] and result['usage']['attempted_calls'] == 0 and
                  result['usage']['reported_api_usd'] == result['usage']['reserved_api_usd'] == 0 and result['trace_hashes'] == [])
    coverage = data.read(index['build_index'])
    oldcells = {r['cell_id']: r for r in prior35['cells']}
    current = {r['cell_id']: r for r in index['core_cells']}
    sourcecells = {r['cell_id']: r for r in coverage['cells']}
    check('same96_planned_cells_as035', len(current) == len(index['core_cells']) == 96 and set(current) == set(oldcells) == set(sourcecells))
    parent_for = {}
    for cid, cell in current.items():
        old, original = oldcells[cid], sourcecells[cid]
        jid = cell['build_job_id']
        check('preserved_build_cell:' + cid, jid == old['job_id'] == original['job_id'] and cell['build_status'] == old['status'] == original['dispatch_status'] and
              catalog[jid]['result']['sha256'] == old['result_sha256'] == original['result']['sha256'] and
              cell['build_packet']['sha256'] == old['original_packet_sha256'] and cell['release']['sha256'] == old['release_sha256'] and
              all(cell[k] == old[k] for k in ('method','researcher_id','cap','evidence_policy','replicate_id')))
        if cell['build_status'] == 'complete':
            check('one_prediction_job_per_complete_profile:' + cid, len(cell['prediction_job_ids']) == len(cell['prediction_results']) == 1 and
                  cell['profile']['sha256'] == old['profile_sha256'] and cell['profile_id'] == old['profile_id'])
            pred = cell['prediction_job_ids'][0]
            check('core_prediction_result_membership:' + cid, pred in catalog and catalog[pred]['category'] == 'search' and catalog[pred]['kind'] == 'predict' and
                  cell['prediction_results'][0] == catalog[pred]['result'] and catalog[pred]['parent_job_ids'] == [jid])
            check('unique_profile_prediction_job:' + cid, pred not in parent_for)
            parent_for[pred] = cell
        else:
            check('noncomplete_cells_no_prediction:' + cid, cell['prediction_job_ids'] == cell['prediction_results'] == [] and cell.get('profile') is None)
    personalized = {j for j, v in catalog.items() if v['kind'] == 'predict' and v['category'] == 'search'}
    check('48_complete_profiles_exact_jobs', set(parent_for) == personalized and len(personalized) == 48)
    check('all_original_outcome_classes_retained', Counter(c['build_status'] for c in current.values()) == {'complete':48,'invalid':39,'empty':7,'unavailable':2})
    old34 = {j['job_id']: j for j in prior34['jobs']}
    controlhybrid = {j for j, v in catalog.items() if v['kind'] == 'predict' and v['category'] in ('control','hybrid')}
    check('034_exact234_job_overlap', set(old34) == controlhybrid and not controlhybrid & personalized)
    for jid, old in old34.items():
        check('034_job_bytes_and_usage:' + jid, catalog[jid]['result']['sha256'] == old['result_sha256'] and digest(results[jid]['usage']) == old['usage_sha256'] and
              Decimal(str(results[jid]['usage']['reported_api_usd'])) == Decimal(old['reported_api_usd']) and catalog[jid]['parent_job_ids'] == old['parent_job_ids'])
    prior_rows = {(r['job_id'], r['item_sha256']): r for r in prior34['rows']}
    for jid in controlhybrid:
        for n, pred in enumerate(results[jid]['predictions']):
            old = prior_rows[(jid, pred['item_sha256'])]
            check('034_row_and_trace_hash_overlap:' + jid + ':' + str(n), digest(pred) == old['result_row_sha256'] and
                  results[jid]['trace_hashes'][2*n:2*n+2] == [old['started_trace_sha256'], old['completed_trace_sha256']])
    batch_for, prepared_for = {}, {}
    for batch in index['batches']:
        prepared, summary = data.read(batch['prepared']), data.read(batch['summary'])
        check('batch_terminal:' + batch['name'], prepared['batch_id'] == summary['batch_id'] and prepared['code_sha'] == RUNTIME and summary['status'] == 'complete' and
              len(prepared['jobs']) == batch['jobs'] and summary['counts'] == {'complete':batch['jobs'],'dispatched':batch['jobs'],'listed':batch['jobs'],'not_dispatched':0,'other':0})
        if batch.get('completion_marker'):
            marker = data.read(batch['completion_marker'])
            check('completion_marker_is_metadata:' + batch['name'], isinstance(marker, dict))
        if 'ledger_at_completion' in batch:
            check('saved_cumulative_ledger:' + batch['name'], batch['ledger_at_completion'] == summary['ledger'])
        for packet_ref in prepared['jobs']:
            # Exact packet references identify catalog membership; no directory lookup.
            matches = [j for j, v in catalog.items() if v['packet'] == packet_ref]
            check('unique_catalog_packet:' + batch['name'], len(matches) == 1)
            jid = matches[0]
            check('one_prepared_batch_per_job:' + jid, jid not in batch_for)
            batch_for[jid], prepared_for[jid] = batch['name'], prepared
        batches.append({'name':batch['name'],'jobs':batch['jobs'],'prepared_sha256':batch['prepared']['sha256'],'summary_sha256':batch['summary']['sha256'],'status':'complete','ledger_is_cumulative_not_additive':'ledger_at_completion' in batch})
    check('all_pred_and_zero_call_build_batches_bound', set(batch_for) == {j for j, v in catalog.items() if not (v['kind'] == 'build' and v['category'] == 'search')})
    payload_items = {}
    for jid in sorted(personalized):
        indexed = catalog[jid]
        result, cell = results[jid], parent_for[jid]
        packet = data.read(indexed['packet'])
        manifest, config, backend = packet['manifest'], packet['config'], packet['backend']
        receipt = data.read(indexed['dispatch_receipt'])
        profile, release = data.read(packet['profile']), data.read(packet['release'])
        parent_profile = data.read(cell['profile'])
        build_result = results[cell['build_job_id']]
        selection = data.read(packet['completed_profile_selection'])
        check('selection_metadata_loaded:' + jid, isinstance(selection, dict))
        check('packet_profile_parent_references:' + jid, packet['profile'] == indexed['profile_file'] and packet['release'] == indexed['release'] and
              profile == parent_profile == build_result['profile'] and indexed['parent_job_ids'] == manifest['parent_job_ids'] == [cell['build_job_id']] and
              packet['search_cell'] == {k: cell[k] for k in packet['search_cell']})
        check('manifest_config_job_identity:' + jid, digest(config) == indexed['config_hash'] == manifest['config_hash'] == result['config_hash'] and
              digest(manifest) == indexed['manifest_sha256'] == result['manifest_hash'] == receipt['manifest_sha256'] and
              digest({k:v for k,v in manifest.items() if k not in ('job_id','lease','created_at','updated_at')}) == jid == manifest['job_id'] == receipt['job_id'] and
              manifest['kind'] == 'predict' and manifest['code_sha'] == indexed['code_sha'] == profile['code_sha'] == RUNTIME and manifest['stage'] == 'dev')
        check('full_profile_identity:' + jid, profile['profile_id'] == digest({k:v for k,v in profile.items() if k != 'profile_id'}) ==
              indexed['profile_id'] == manifest['profile_hash'] == result['profile_hash'] == cell['profile_id'] and profile['config_id'] == digest(profile['config']) and
              profile['content_sha256'] == digest(profile['content']) and profile['status'] == 'complete' and profile['error_code'] is None and
              profile['method_id'] == indexed['method_id'] == manifest['method_id'] == cell['method'] and profile['researcher_id'] == indexed['researcher_id'] == cell['researcher_id'] and
              profile['personalization_cap'] == manifest['personalization_cap'] == cell['cap'] and profile['replicate_id'] == manifest['replicate_id'] == cell['replicate_id'] == 0)
        docs = release['sources']['documents']
        sources = sorted([{'document_id':d['document_id'],'content_sha256':d['content_sha256']} for d in docs], key=lambda d:d['document_id'])
        check('full_document_and_source_binding:' + jid, len({d['document_id'] for d in docs}) == len(docs) and all(sha(d['content'].encode()) == d['content_sha256'] for d in docs) and
              sources == release['sources']['source_manifest'] == profile['config']['allowed_sources'] and
              digest(sources) == profile['allowed_source_manifest_hash'] == manifest['source_manifest_hash'] == indexed['source_manifest_hash'] == cell['source_manifest_hash'] and
              digest(docs) == profile['documents_hash'] == manifest['documents_hash'] == indexed['documents_hash'] and
              release['target_bundle_sha256'] == cell['target_bundle_sha256'] and release['items_sha256'] == cell['items_sha256'])
        by_id = {item['item_id']: item for item in release['items']}
        items = [by_id[i] for i in packet['item_ids']]
        check('ordered_item_set:' + jid, len(by_id) == len(release['items']) == len(items) == len(set(packet['item_ids'])) == 14 and
              digest(release['items']) == release['items_sha256'] and digest(items) == manifest['items_hash'] == indexed['items_sha256'] and
              packet['item_ids'] == indexed['item_ids'] == [p['item_id'] for p in result['predictions']] and
              all(set(i) == {'item_id','researcher_id','context','options','option_order_id'} and i['researcher_id'] == profile['researcher_id'] for i in items) and
              manifest['option_order_schedule'] == indexed['option_order_schedule'] == [{'item_id':i['item_id'],'option_order_id':i['option_order_id']} for i in items])
        content = '' if profile['content'] in (None, {}, [], '') else canon(profile['content'])
        identity, settings = manifest['consumer'], config['settings']
        enforced = identity['enforced_settings']
        method = profile['method_id']
        check('source_renderer_method_and_prompt_identities:' + jid, profile['renderer_implementation_hash'] == config['renderer_implementation_hash'] == renderer and
              profile['method_implementation_hash'] == config['method_implementation_hash'] == sha(code[prefix + families[method]]) and
              profile['prompt_version'] == config['profile_prompt_version'] == versions[method] and config['consumer_prompt_version'] == constants['PROMPT_VERSION'] and
              len(content.encode()) == profile['token_count'] <= profile['personalization_cap'])
        check('exact_backend_settings:' + jid, identity == indexed['actual_backend'] == result['actual_backend'] and identity['class'] == 'OpenAIResponsesBackend' and
              identity['endpoint'] == 'https://api.openai.com/v1/responses' and identity['label'] == 'openai-responses-overnight:gpt-6-luna' and identity['model'] == backend['model'] == 'gpt-6-luna' and
              backend['reasoning'] == enforced['reasoning_effort'] == 'medium' and backend['timeout'] == 60 and settings == {'max_tokens':8192,'temperature':0.0} and
              enforced == {'adapter_implementation_sha256':digest(code[prefix+'backends.py'].decode()),'pricing_version':'openai-standard-short-context-30m-cache-write-1.25x-2026-11-15',
                           'prompt_cache_options':{'mode':'implicit','ttl':'30m'},'reasoning_effort':'medium','service_tier':'default','store':False,'temperature':'not_sent','tools':[]})
        check('terminal_counts_and_single_attempt_per_item:' + jid, result['status'] == receipt['status'] == 'complete' and receipt['result_path'] == indexed['result']['path'] and
              result['counts'] == receipt['counts'] == {'attempted':14,'complete':14,'error':0} and result['usage'] == receipt['usage'] and
              result['usage']['attempted_calls'] == 14 and result['usage']['cache_hits'] == result['usage']['uncertain_attempts'] == 0 and
              len(result['trace_hashes']) == 28 and result['missing_arms'] == [] and manifest['retry_policy'] == {'max_attempts':1,'retry_uncertain':False})
        root = PurePosixPath(indexed['result']['path']).parent
        check('source_trace_layout_result_anchor:' + jid, root.name == jid and PurePosixPath(indexed['result']['path']).name == 'result.json')
        for n, (item, pred) in enumerate(zip(items, result['predictions']), 1):
            start_ref = ref(root / 'traces' / ('%04d-started.json' % n), result['trace_hashes'][2*n-2])
            complete_ref = ref(root / 'traces' / ('%04d-complete.json' % n), result['trace_hashes'][2*n-1])
            start, complete = data.read(start_ref), data.read(complete_ref)
            payload = {'context':item['context'],'options':item['options'],'personalization':content}
            prompt = constants['INSTRUCTION'] + '\nINPUT_JSON:\n' + canon(payload)
            call_settings = dict(settings, system=constants['SYSTEM'])
            cache = digest({'manifest':{k:v for k,v in manifest.items() if k not in ('job_id','lease','created_at','updated_at')},'prompt':prompt,'settings':call_settings})
            key = jid + ':' + str(n)
            check('trace_request_and_response:' + key, start['attempt'] == complete['attempt'] == n and start['status'] == 'started' and complete['status'] == 'complete' and
                  start['prompt'] == prompt and start['settings'] == call_settings and start['backend'] == identity and start['cache_key'] == complete['cache_key'] == cache and
                  complete['response_sha256'] == sha(complete['response'].encode()))
            check('row_payload_job_cache_binding:' + key, pred['status'] == 'complete' and pred['error_code'] is None and pred['item_sha256'] == digest(item) and
                  pred['items_sha256'] == manifest['items_hash'] and pred['job_id'] == jid and pred['manifest_sha256'] == digest(manifest) and pred['actual_consumer'] == identity and
                  pred['payload_sha256'] == digest(payload) and pred['rendered_profile_sha256'] == sha(content.encode()) and pred['cache_provenance'] == {'hit':False,'key':cache})
            response = json.loads(complete['response'])
            probabilities = response['probabilities']
            check('consumer_probability_validity:' + key, response.get('status','complete') == 'complete' and isinstance(probabilities,list) and len(probabilities) == len(item['options']) and
                  all(not isinstance(p,bool) and isinstance(p,(int,float)) and math.isfinite(p) and 0 <= p <= 1 for p in probabilities) and
                  math.isclose(sum(probabilities),1,abs_tol=1e-6) and isinstance(response.get('rationale',''),str))
            choice = max(range(len(probabilities)), key=probabilities.__getitem__)
            check('parsed_response_matches_saved_result:' + key, pred['prediction'] == {'choice':chr(ord('a')+choice),'confidence':probabilities[choice],
                  'rationale':response.get('rationale',''),'probabilities':probabilities,'calibrated':False})
            record = {'job_id':jid,'parent_job_id':cell['build_job_id'],'cell_id':cell['cell_id'],'method':method,'cap':cell['cap'],'evidence_policy':cell['evidence_policy'],
                      'researcher_id':cell['researcher_id'],'item_id_sha256':digest(item['item_id']),'item_sha256':digest(item),'option_order_id_sha256':digest(item['option_order_id']),
                      'profile_id':profile['profile_id'],'result_sha256':indexed['result']['sha256'],'result_row_sha256':digest(pred),
                      'started_trace_sha256':start_ref['sha256'],'completed_trace_sha256':complete_ref['sha256'],
                      'verified_hashes':{'backend_identity':digest(identity),'payload':digest(payload),'prompt':sha(prompt.encode()),'settings':digest(settings),'system':sha(constants['SYSTEM'].encode())},'status':'complete'}
            rows.append(record)
            payload_items[(jid,digest(item))] = item
        trace_derivations.append({'job_id':jid,'anchor_result':indexed['result'],'started_pattern':'traces/%04d-started.json','complete_pattern':'traces/%04d-complete.json',
                                  'ordered_result_trace_hashes':indexed['trace_sha256s'],'attempts':14})
        jobs.append({'job_id':jid,'batch':batch_for[jid],'parent_job_id':cell['build_job_id'],'profile_id':profile['profile_id'],'result_sha256':indexed['result']['sha256'],
                     'attempted_calls':14,'usage_sha256':digest(result['usage']),'reported_api_usd':str(Decimal(str(result['usage']['reported_api_usd'])))})
    new_rows = {(r['job_id'],r['item_sha256']):r for r in rows}
    check('672_personalized_rows_unique', len(new_rows) == len(rows) == 48*14 == 672)
    check('personalized_same28_ordered_items_as034', {r['item_sha256'] for r in rows} == {r['item_sha256'] for r in prior34['rows']} and len({r['item_sha256'] for r in rows}) == 28)
    for old in prior33['canonical_jobs']:
        check('033_exact_personalized_job_overlap:' + old['job_id'], old['job_id'] in personalized and old['result_sha256'] == catalog[old['job_id']]['result']['sha256'] and
              old['usage_sha256'] == digest(results[old['job_id']]['usage']) and old['parent_job_id'] == parent_for[old['job_id']]['build_job_id'])
    for alias in prior33['aliases']:
        row = new_rows[(alias['canonical_job_id'],alias['item_sha256'])]
        check('033_alias_actual_row_overlap', row['result_row_sha256'] == alias['canonical_result_row_sha256'] and row['verified_hashes'] == alias['verified_hashes'] and
              row['started_trace_sha256'] == alias['started_trace_sha256'] and row['completed_trace_sha256'] == alias['completed_trace_sha256'])
    memory = data.read(index['memory_aliases'])
    controls = data.read(index['control_aliases'])
    check('memory_references_nonadditive', memory['memory_references'] == len(prior33['aliases']) == 84 and memory['canonical_jobs'] == len(prior33['canonical_jobs']) == 2 and
          memory['canonical_prediction_rows'] == 28 and memory['additional_calls'] == memory['additional_independent_observations'] == 0 and
          index['alias_accounting']['memory'] == {'additional_calls':0,'additional_independent_observations':0,'canonical_rows':28,'references':84})
    control_keys = {(r['canonical_job_id'],digest(r['item_id']),r['comparison_cap']) for r in controls['aliases']}
    prior_keys = {(r['canonical_job_id'],r['item_id_sha256'],r['comparison_cap']) for r in prior34['sparse_aliases']}
    check('control_aliases_same112_nonadditive', control_keys == prior_keys and len(controls['aliases']) == 112 and controls['canonical_prediction_rows'] == 56 and
          controls['additional_calls'] == controls['additional_independent_observations'] == 0 and index['alias_accounting']['controls'] == {'additional_calls':0,'additional_cap_references':112,'additional_independent_observations':0,'canonical_rows':56})
    known = sum(Decimal(str(r['usage']['reported_api_usd'])) for r in results.values())
    held = sum(Decimal(str(r['usage']['reserved_api_usd'])) for r in results.values())
    attempts = sum(r['usage']['attempted_calls'] for r in results.values())
    check('study_once_per_unique_job_costs', attempts == 1132 and known == Decimal('0.266053750') and held == Decimal('0.019078625') and
          known == Decimal(index['costs']['all_unique_jobs']['known_conservative_usd']) and held == Decimal(index['costs']['all_unique_jobs']['retained_uncertain_reservations_usd']) and
          known+held == Decimal(index['costs']['all_unique_jobs']['conservative_bound_usd']))
    check('unknown_outcomes_and_holds_still_in_study', sum(r['usage']['uncertain_attempts'] for r in results.values()) == 2 and
          sum(r['usage']['input_tokens'] is None for r in results.values()) == sum(r['usage']['output_tokens'] is None for r in results.values()) == 2)
    core_known = sum(Decimal(str(results[j]['usage']['reported_api_usd'])) for j,v in catalog.items() if v['category'] == 'search')
    check('cost_partition_not_ledger_snapshot_sum', core_known == Decimal(index['costs']['core']['known_conservative_usd']) and
          Decimal(index['costs']['controls_incremental']['known_conservative_usd'])+Decimal(index['costs']['hybrids_incremental']['known_conservative_usd']) == Decimal(prior34['summary']['canonical_reported_usd']) and
          core_known+Decimal(prior34['summary']['canonical_reported_usd']) == known)
    check('planned_delivered_absent_denominators', index['counts']['core_planned_rows'] == 1344 and index['counts']['core_absent_rows'] == index['counts']['core_planned_rows']-len(rows) == 672 and
          index['counts']['unique_prediction_rows'] == len(rows)+len(prior34['rows']) == 1036 and index['counts']['unique_prediction_jobs'] == len(personalized)+len(controlhybrid) == 282)
    check('bounded_study_alias_exclusions', index['alias_accounting']['hybrid_cap512']['not_dispatched_rows'] == 28)
    data.recheck()
    check('pinned_public_evidence_unchanged', all(sha((a.evidence_root/name).read_bytes()) == pin for name,pin in PINS.items()))
    report = {'audit':'full-sparse-execution-37','runtime_sha':RUNTIME,'index_sha256':INDEX_SHA,'index_release_commit':'8fb6246e311dac1f885dc4b04bd9384aecc858c2',
              'reader_sha256':sha(Path(__file__).read_bytes()),'argv':sys.argv,'checks':checks,'check_counts':{'verified':len(checks),'failed':0},'source_files_verified':len(source['files']),
              'batches':batches,'jobs':jobs,'rows':rows,
              'summary':{'all_unique_jobs':612,'build_jobs':330,'prediction_jobs':282,'core_planned_cells':96,'core_build_outcomes':dict(Counter(c['build_status'] for c in current.values())),
                         'core_planned_prediction_rows':1344,'personalized_complete_profiles':48,'personalized_prediction_rows':672,'core_absent_prediction_rows':672,
                         'prior034_control_hybrid_rows':364,'total_prediction_rows':1036,'prior033_personalized_overlap_rows':28,'additional_personalized_rows_beyond033':644,
                         'unique_ordered_items':28,'study_attempted_calls':attempts,'study_known_estimate_usd':str(known),'study_retained_uncertain_usd':str(held),
                         'study_known_plus_held_usd':str(known+held),'control_alias_references':112,'memory_alias_references':84,'aliases_add_calls':0,'aliases_add_independent_observations':0,'audit_model_calls':0},
              'trace_path_derivation':{'source_sha256':source['files'][prefix+'runner.py'],'source_path':prefix+'runner.py','source_lines':[199,201,212,214,254,273,315,316],
                                      'rule':'Anchor each explicitly referenced result.json at its job-ID parent; derive only numbered started/complete files for each result-pinned pair. Require raw SHA256 before parsing; no directory scan or alternate path search.','jobs':trace_derivations},
              'scope':{'owner_code_imported':False,'owner_checker_imported':False,'full034_prediction_trace_reread':False,'prior034_result_row_and_trace_hashes_reconciled':True,
                       'scoring_refs_followed':False,'active_ledger_read':False,'richer_repeated_runs_included':False},
              'limits':['Saved artifact consistency is not provider-origin authentication or actual wire capture; configured temperature0 is not sent by the adapter.',
                        '034 control/hybrid result bytes and rows are rechecked, with full trace semantics inherited from that pinned independent audit. Personalized672 request/response trace pairs are reconstructed here.',
                        'No scoring labels, prediction quality, source meaning, profile quality or researcher fidelity claim. Method/cap rows and aliases are not independent observations.',
                        'Study cost is summed once per612 indexed job results. Cumulative ledger snapshots are not summed; neutral probes, embedding production and other historical jobs are separate.',
                        'Extraction outcomes and selected profile bytes reconcile to035; this does not repeat extraction-call or quote-policy validation.',
                        'Unreferenced on-disk manifest siblings are not read; packet manifest canonical identity is bound to result and dispatch receipt. Trace paths alone use the explicitly authorized frozen-source derivation.']}
    save(a.out/'report.json',report)
    save(a.out/'input-inventory.json',{'files':list(data.inventory.values()),'raw_copied':False})
    print(json.dumps({'summary':report['summary'],'check_counts':report['check_counts'],'private_inputs':len(data.inventory)},indent=2))


if __name__ == '__main__':
    main()
