"""Prepare the frozen 96-cell profile search; no execution, credentials or spending.

Required pins: --runtime PATH --runtime-sha SHA --ledger-policy FILE SHA.
Optional --peer-receipt FILE SHA admits only evaluator-issued P7 derivatives.
--methods is an explicit smoke subset; every omitted predeclared cell is retained.
Build mode emits target-only and P7-only batches. Predict mode consumes one or
more --build-prepared FILE SHA inputs and records invalid/missing builds without
retrying them. Only complete exact-profile artifacts receive prediction packets.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal, ROUND_FLOOR
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

SELECTION_PATH = '/private/tmp/gio-profile-20261115-coordinator/broad-profile-search-selection-v1.json'
SELECTION_SHA = '1440d3a9a43316ae9baa77ba1e77ebaba386b3986cbd4f6a647a13d692179830'
BASE = Path('/private/tmp/gio-profile-20261115-coordinator')
BASE_SCHEMA = 'released-development-v2'
PEER_SCHEMA = 'released-development-v2-p7-peers-v1'
SCOPE = 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel'
BINDINGS = ('approved_peer_sources', 'peer_policy', 'parent_releases')
MODULES = {**{key: ('profiles_summary', 'register_summary_builders') for key in ('P1','P2','P3')},
           **{key: ('profiles_principles', 'register_principle_builders') for key in ('P4','P5','P6')},
           **{key: ('profiles_hypotheses', 'register_hypotheses_builders') for key in ('P7','P8')}}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def file_ref(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_ref(ref):
    path = Path(ref['path'])
    if not path.is_absolute():
        raise ValueError('absolute pinned input path required')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise ValueError('pinned input file hash mismatch')
    return raw


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((canonical(value) + '\n').encode())
    return file_ref(path)


def inspect_ledger(policy, pricing_version, timestamp):
    """SELECT-only connection: no mkdir, initialization, reservation or settlement."""
    if policy.get('schema_version') != 'phase2-ledger-policy-v1':
        raise ValueError('explicit phase2 ledger policy required; old ledger refused')
    spec = policy['ledger']
    if set(spec) != {'path','max_usd','max_inflight'} or type(spec['max_inflight']) is not int or spec['max_inflight'] != 2:
        raise ValueError('exact two-worker ledger specification required')
    limit = Decimal(str(spec['max_usd']))
    if not limit.is_finite() or not 0 < limit <= 500 or isinstance(spec['max_usd'], bool):
        raise ValueError('invalid explicit shared suballocation')
    path = Path(spec['path'])
    if not path.is_absolute() or not path.is_file() or path.name == 'profile-openai.sqlite':
        raise ValueError('existing new phase2 ledger required; never create or reopen old ledger')
    expected = {'limit_nanos': int((limit * 1_000_000_000).to_integral_value(rounding=ROUND_FLOOR)),
                'deadline': timestamp(policy['deadline']).isoformat(), 'max_inflight': 2,
                'pricing_version': pricing_version}
    if policy.get('pricing_version') != pricing_version:
        raise ValueError('policy pricing differs from runtime')
    uri = 'file:' + quote(str(path.resolve()), safe='/') + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as conn:
        conn.execute('PRAGMA query_only=ON')
        row = conn.execute('SELECT body FROM policy WHERE id=1').fetchone()
    if not row or json.loads(row[0]) != expected:
        raise ValueError('existing ledger configuration differs from exact policy')
    if policy.get('prior_phase_closure'):
        read_ref(policy['prior_phase_closure'])
    return expected


def readonly_ledger(base_class, spec, configuration, timestamp):
    """Backend identity construction only; every spending/connection path fails."""
    def forbidden(*args, **kwargs):
        raise RuntimeError('packet preparation forbids ledger mutation')
    class ReadOnlyLedger(base_class):
        def __init__(self):
            self.path = Path(spec['path']).resolve()
            self.deadline = timestamp(configuration['deadline'])
            self.configuration = dict(configuration)
        reserve = forbidden
        finish = forbidden
        @contextmanager
        def _connect(self):
            forbidden()
            yield None
    return ReadOnlyLedger()


def planned_cells(selection, methods=None):
    selected = set(selection['methods'] if methods is None else methods)
    if not selected or not selected <= set(selection['methods']):
        raise ValueError('method filter must be a nonempty subset of frozen selection')
    cells = []
    for config in selection['configurations']:
        for researcher in selection['researchers']:
            for replicate in selection['replicate_ids']:
                cells.append({'cell_id': '%s/%s/r%s' % (config['config_id'], researcher, replicate),
                              'config_id': config['config_id'], 'method': config['method'], 'cap': config['cap'],
                              'evidence_policy': config['evidence_policy'], 'researcher_id': researcher,
                              'replicate_id': replicate, 'selected': config['method'] in selected})
    if len(cells) != 96 or len({c['cell_id'] for c in cells}) != 96:
        raise ValueError('frozen selection must contain exactly 96 unique cells')
    return cells


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('build','predict'))
    p.add_argument('--runtime', required=True)
    p.add_argument('--runtime-sha', required=True)
    p.add_argument('--ledger-policy', nargs=2, metavar=('FILE','SHA256'), required=True)
    p.add_argument('--peer-receipt', nargs=2, metavar=('FILE','SHA256'))
    p.add_argument('--build-prepared', nargs=2, metavar=('FILE','SHA256'), action='append', default=[])
    p.add_argument('--methods', nargs='+', choices=tuple(MODULES))
    p.add_argument('--destination', required=True)
    args = p.parse_args()
    runtime, out = Path(args.runtime).resolve(), Path(args.destination).resolve()
    sys.path.insert(0, str(runtime))
    from autoresearch.taste.overnight.contracts import digest, backend_identity, ProfileArtifact
    from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend, PRICING_VERSION
    from autoresearch.taste.overnight.consumer import PROMPT_VERSION, implementation_hash
    from autoresearch.taste.overnight.runner import timestamp
    from autoresearch.llm import Budget
    driver_path = runtime / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
    module_spec = importlib.util.spec_from_file_location('broad_frozen_driver', driver_path)
    driver = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(driver)
    driver.verify_runtime(runtime, args.runtime_sha)
    driver._outside_git(str(out))
    selection_ref = {'path': SELECTION_PATH, 'sha256': SELECTION_SHA}
    selection = json.loads(read_ref(selection_ref))
    policy_ref = {'path': args.ledger_policy[0], 'sha256': args.ledger_policy[1]}
    policy = json.loads(read_ref(policy_ref))
    if policy['deadline'] != selection['deadline'] or selection['confirmation_authorized'] is not False:
        raise ValueError('deadline or final authorization differs from selection')
    driver._deadline(policy['deadline'])
    configuration = inspect_ledger(policy, PRICING_VERSION, timestamp)
    ledger = readonly_ledger(DollarLedger, policy['ledger'], configuration, timestamp)
    cells = planned_cells(selection, args.methods)
    target_releases = {r['researcher_id']: (r['release'], json.loads(read_ref(r['release'])))
                       for r in selection['target_releases']}
    if set(target_releases) != set(selection['researchers']):
        raise ValueError('frozen target releases do not match researchers')
    peer_releases, peer_ref = {}, None
    if args.peer_receipt:
        peer_ref = {'path': args.peer_receipt[0], 'sha256': args.peer_receipt[1]}
        receipt = json.loads(read_ref(peer_ref))
        if (receipt.get('schema_version') != 'p7-peer-fit-readiness-v1' or receipt.get('approved_method_id') != 'P7'
                or receipt.get('confirmation_authorized') is not False or receipt.get('target_panels_unchanged') is not True
                or receipt.get('release_schema_version') != PEER_SCHEMA):
            raise ValueError('invalid evaluator P7 receipt')
        for row in receipt['released']:
            ref = {'path': row['location'], 'sha256': row['sha256']}
            release = json.loads(read_ref(ref))
            if row['allowed_method_id'] != 'P7' or release['researcher_id'] != row['researcher_id']:
                raise ValueError('P7 receipt/release identity mismatch')
            expected_parents = sorted(selection['target_releases'], key=lambda r:r['researcher_id'])
            if release['parent_releases'] != expected_parents:
                raise ValueError('P7 parents differ from frozen target releases')
            if not hasattr(driver, '_peer_release'):
                raise ValueError('frozen runtime lacks P7 derivative admission')
            driver._peer_release(release, 'P7', {k: release[k] for k in BINDINGS})
            peer_releases[row['researcher_id']] = (ref, release)
        if set(peer_releases) != set(selection['researchers']):
            raise ValueError('P7 receipt must bind both planned researchers')
    contract = runtime / 'docs/superpowers/plans/2026-11-15-profile-search/SHARED_CONTRACT.md'
    contract_ref = file_ref(contract)
    if contract_ref['sha256'] != '0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43':
        raise ValueError('shared contract changed')
    roots = {k: str(BASE / k) for k in ('output','lease','cache','receipts')}
    for path in roots.values(): driver._outside_git(path)
    shared = {'schema_version':'overnight-batch-v1','campaign_id':selection['campaign_id'],
        'code_sha':args.runtime_sha,'runtime_root':str(runtime),'deadline':selection['deadline'],
        'max_workers':2,'max_total_attempts':selection['max_total_build_calls'] if args.mode=='build' else selection['max_total_prediction_calls'],
        'release_scope':SCOPE,'contract':contract_ref,
        'env_file':'/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/.env',
        'ledger':policy['ledger'],'roots':roots,'jobs':[],'broad_selection':selection_ref,
        'ledger_policy':policy_ref,'peer_receipt':peer_ref,'total_search_allocation_usd':15,
        'build_allocation_usd':4,'prediction_allocation_usd':11}
    batches = {schema:dict(shared, release_schema_version=schema, jobs=[]) for schema in (BASE_SCHEMA,PEER_SCHEMA)}
    existing = {}
    if args.mode == 'predict':
        if not args.build_prepared: raise ValueError('prediction requires exact prepared build batches')
        for path, expected in args.build_prepared:
            prepared = json.loads(read_ref({'path':path,'sha256':expected}))
            if (prepared.get('prepared') is not True or prepared.get('code_sha') != args.runtime_sha
                    or prepared.get('broad_selection',{}).get('sha256') != SELECTION_SHA):
                raise ValueError('wrong frozen build preparation')
            for ref in prepared['jobs']:
                packet = json.loads(read_ref(ref)); cell = packet['search_cell']['cell_id']
                if cell in existing: raise ValueError('duplicate predeclared build cell')
                existing[cell] = (prepared, packet, ref)
    out.mkdir(parents=True, exist_ok=False)
    rows, issued = [], []
    for cell in cells:
        row = dict(cell)
        if not cell['selected']:
            rows.append(dict(row,status='not_selected_by_explicit_filter')); continue
        peer = cell['method'] == 'P7'
        if peer and not peer_releases:
            rows.append(dict(row,status='not_ready',error_code='approved_peer_receipt_required')); continue
        release_ref, release = (peer_releases if peer else target_releases)[cell['researcher_id']]
        if len(release['items']) != 14: raise ValueError('expected exact 14-item ordered target panel')
        cfg = {'method_id':cell['method'],'researcher_id':cell['researcher_id'],
            'allowed_sources':release['sources']['source_manifest'],
            'allowed_source_manifest_hash':release['sources']['allowed_source_manifest_hash'],
            'personalization_cap':cell['cap'],'replicate_id':cell['replicate_id'],'code_sha':args.runtime_sha,
            'extractor_settings':selection['extraction_settings'],'evidence_policy':cell['evidence_policy']}
        if peer: cfg.update({k:release[k] for k in BINDINGS})
        profile_ref, parents, ids = None, [], []
        if args.mode == 'predict':
            if cell['cell_id'] not in existing:
                rows.append(dict(row,status='not_ready',error_code='build_not_provided')); continue
            prepared, build, build_ref = existing[cell['cell_id']]
            if build['config'] != cfg or build['manifest']['kind'] != 'build':
                raise ValueError('completed build config differs from exact frozen cell')
            job = build['manifest']['job_id']; actual = Path(prepared['roots']['output'])/job
            result_path, profile_path = actual/'result.json', actual/'profile.json'
            if not result_path.is_file():
                rows.append(dict(row,status='not_ready',error_code='build_result_missing',build_job_id=job)); continue
            result = json.loads(result_path.read_bytes())
            if result['job_id'] != job or result['manifest_hash'] != digest(build['manifest']):
                raise ValueError('completed build result provenance differs')
            if result['status'] != 'complete':
                rows.append(dict(row,status='not_predicted',build_status=result['status'],
                    error_code=result.get('error_code') or result.get('profile',{}).get('error_code'),
                    build_job_id=job,build_result=file_ref(result_path))); continue
            if not profile_path.is_file(): raise ValueError('complete build lacks profile artifact')
            profile = ProfileArtifact.from_dict(json.loads(profile_path.read_bytes()))
            if (profile.status != 'complete' or profile.config != cfg or profile.profile_id != result['profile_hash']
                    or profile.documents_hash != digest(release['sources']['documents'])):
                raise ValueError('complete build artifact differs from frozen cell and sources')
            profile_ref, parents = file_ref(profile_path), [job]
            cfg = {'method_implementation_hash':profile.method_implementation_hash,
                'renderer_implementation_hash':implementation_hash(),'profile_prompt_version':profile.prompt_version,
                'consumer_prompt_version':PROMPT_VERSION,'settings':selection['consumer_settings']}
            if peer: cfg.update({k:release[k] for k in BINDINGS})
            ids = [item['item_id'] for item in release['items']]
        calls = 1 if args.mode=='build' else len(ids)
        spec = {'model':selection['model'],'reasoning':selection['reasoning'],
            'timeout':selection['extraction_timeout_seconds'] if args.mode=='build' else selection['prediction_timeout_seconds'],
            'max_calls':calls,'max_seconds':240 if args.mode=='build' else 120+90*len(ids),
            'max_usd':.04 if args.mode=='build' else float(Decimal('.008')*len(ids))}
        module, function = MODULES[cell['method']]
        manifest = {'schema_version':'overnight-job-v1','campaign_id':selection['campaign_id'],'stage':'dev',
            'kind':args.mode,'method_id':cell['method'],'personalization_cap':cell['cap'],'replicate_id':cell['replicate_id'],
            'allocation':{'authorization_source':'Gio overnight approval; predeclared broad-profile-search-selection-v1; shared15USD search allocation',
                          'cost_mode':'priced_api',**{k:spec[k] for k in ('max_calls','max_seconds','max_usd')}},
            'retry_policy':{'max_attempts':1,'retry_uncertain':False},'parent_job_ids':parents,
            'expected_outputs':['profile.json','result.json'] if args.mode=='build' else ['result.json']}
        if args.mode=='build': manifest['consumer']=None
        packet = {'schema_version':'overnight-packet-v1','release':release_ref,'item_ids':ids,'profile':profile_ref,
            'config':cfg,'manifest':manifest,'lease':{'lease_id':digest({'selection':SELECTION_SHA,'mode':args.mode,'cell':cell['cell_id']}),
            'owner':'gio-overnight-00','expires_at':selection['deadline']},'backend':spec,
            'registration':{'module':'autoresearch.taste.overnight.'+module,'function':function},
            'search_cell':{k:v for k,v in cell.items() if k!='selected'}}
        schema = PEER_SCHEMA if peer else BASE_SCHEMA
        # Uses the existing runner's admission; the injected ledger is SELECT-only
        # and cannot reserve, settle, initialize or connect for writes.
        bound = driver._prepare_packet(packet,batches[schema],ledger)['packet']
        packet_ref = write_new(out/('packet-%03d.json'%len(issued)),bound)
        batches[schema]['jobs'].append(packet_ref)
        issued.append(bound)
        rows.append(dict(row,status='prepared',packet=packet_ref,job_id=bound['manifest']['job_id']))
    max_calls = sum(packet['backend']['max_calls'] for packet in issued)
    max_usd = sum(Decimal(str(packet['backend']['max_usd'])) for packet in issued)
    ceiling = selection['build_allocation_usd'] if args.mode=='build' else selection['prediction_allocation_usd']
    if max_usd > Decimal(str(ceiling)) or max_calls > shared['max_total_attempts']:
        raise ValueError('aggregate search allocation exceeded')
    batch_refs = []
    for schema, batch in batches.items():
        if batch['jobs']:
            batch_refs.append(write_new(out/('batch-p7.json' if schema==PEER_SCHEMA else 'batch-target-only.json'),batch))
    report = {'schema_version':'broad-profile-packet-preparation-v1','mode':args.mode,'selection':selection_ref,
        'runtime_code_sha':args.runtime_sha,'ledger_policy':policy_ref,'peer_receipt':peer_ref,
        'planned_cells':96,'prepared_cells':len(issued),'max_calls':max_calls,'max_usd':float(max_usd),
        'model_calls_performed':0,'ledger_mutations':0,'batches':batch_refs,'cells':rows,
        'limitations':['Predeclared omitted/invalid cells remain visible; no retries or empty-profile fallbacks.',
                       'Build and prediction batch caps are shared across target-only and P7 batches, not per batch.',
                       'The coordinator must enforce selection-wide uniqueness across explicit smoke and continuation runs.']}
    report_ref = write_new(out/'preparation-report.json',report)
    driver.verify_runtime(runtime,args.runtime_sha)
    print(canonical({'report':report_ref,'batches':batch_refs,'planned_cells':96,'prepared_cells':len(issued),
                     'max_calls':max_calls,'max_usd':float(max_usd),'model_calls_performed':0,'ledger_mutations':0}))


if __name__ == '__main__':
    main()
