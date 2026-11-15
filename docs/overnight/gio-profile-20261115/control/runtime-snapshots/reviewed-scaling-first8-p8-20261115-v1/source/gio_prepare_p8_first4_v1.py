"""Exact four frozen P8 builds. Proposal mode has no environment, ledger or provider access.
Native preparation requires a separately issued root authority after known Astra closure.
"""
import argparse, copy, hashlib, importlib.util, json, sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode = True
ASTRA_HELPER={'path':'/private/tmp/gio_prepare_scaling_astra_v1.py','sha256':'48cd7da0238fd272b8d977b3b5ed0f484856e36413c031520fe08abcaee4e426'}
def load_pinned(name, source):
    p=Path(source['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('dependency_pin_mismatch')
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
a=load_pinned('p8_astra_authority_helpers',ASTRA_HELPER)
h=a.h
B,R,COMMIT,DEADLINE,POLICY=h.B,h.R,h.COMMIT,h.DEADLINE,a.POLICY
read,ref,require,write,canonical,digest=a.read,a.ref,a.require,a.write,a.canonical,a.digest
SCOPE='p8-first4-cap8192-explicit-only-replicate0-sol-astra'
TOTAL='9.63453'
REPORT={'path':'/private/tmp/gio-profile-20261115-scaling/mechanical-readiness-only-selected-v1-92l7vewk/safe-readiness-report.json','sha256':'ec31be71a741cfe4c986ff5f0183a3f7c6045418aef69ba9ee25c7ac382c2b94'}
ASTRA_SUPERVISOR={'path':'/private/tmp/gio_scaling_astra_supervisor_v1.py','sha256':'90ff969798b00aaab78a850e15058c8bc3fc80d79ec2f8d878cdb7723e0fe53e'}
ASTRA_AUTHORITY={'path':str(B/'accounting/scaling-astra-authorization-v1.json'),'sha256':'14d30ac7aa3f3f628d91e87cd27c59ed8affe42e84d5657f7658b89acdf3cdf2'}
ASTRA_INDEX={'path':'/private/tmp/gio-scaling-astra-native-admissions-v1/ready-index.json','sha256':'7a38c2686d87e1631566e381af43246d35eb83e71d8890508675d8fbb3f4c011'}
DRAFTS=[
 {'draft_number':0,'sha256':'7db0bcff39db9cf5164270ad2bb91d8a09f74762f48231eefc0bb3ec86d99239','researcher':'chris_olah','model':'gpt-6-sol'},
 {'draft_number':1,'sha256':'e84ccae62023405b025c0e36cde75092f4f0eaf273ef833e30a3fcab76fb9107','researcher':'chris_olah','model':'gpt-6-astra'},
 {'draft_number':5,'sha256':'dd5c7919dd69c43a6ca568e2ef9d893e98520294c78f3c2acf6a699a3b0408ce','researcher':'neel_nanda','model':'gpt-6-sol'},
 {'draft_number':6,'sha256':'bb512022912e980748281c99cda1763e47be7d102817425dfd9b831df1aaab38','researcher':'neel_nanda','model':'gpt-6-astra'},
]
def draft_refs():
    return [{'path':str(Path(REPORT['path']).parent/('draft-%04d.json'%r['draft_number'])),'sha256':r['sha256']} for r in DRAFTS]

def check_draft(d):
    m,c,b=d['manifest'],d['config'],d['backend']
    require(d['lease'] is None and m.get('job_id') is None and m['allocation']['authorization_source'] is None,'original_unleased_draft_required')
    require(m['kind']=='build' and m['method_id']==c['method_id']=='P8' and m['personalization_cap']==c['personalization_cap']==8192 and m['replicate_id']==c['replicate_id']==0,'exact_p8_cell_required')
    require(c['researcher_id'] in ('chris_olah','neel_nanda') and c['evidence_policy']=='explicit-only' and c['extractor_settings']=={'temperature':0.0,'max_tokens':16384},'exact_original_build_settings_required')
    require(b['model'] in ('gpt-6-sol','gpt-6-astra') and b['reasoning']=='medium' and b['timeout']==180 and b['max_calls']==1 and b['max_seconds']==240,'exact_original_backend_required')
    require(Decimal(str(b['max_usd']))==Decimal('.8028775' if b['model']=='gpt-6-sol' else '4.0143875') and all(m['allocation'][k]==b[k] for k in ('max_calls','max_seconds','max_usd')),'original_ceiling_changed')
    require(d['item_ids']==[] and d['profile'] is None,'build_must_not_condition_on_targets')

def bind(draft, authority):
    check_draft(draft);p=copy.deepcopy(draft)
    p['manifest']['allocation']['authorization_source']={'policy':POLICY,'p8_first4_authority':authority,'scope':SCOPE,'original_readiness':REPORT}
    jid=h.semantic_id(p['manifest']);p['manifest']['job_id']=jid
    p['lease']={'job_id':jid,'lease_id':digest({'job_id':jid,'authority':authority,'scope':SCOPE}),'owner':'gio-overnight-00','expires_at':DEADLINE}
    restored=copy.deepcopy(p);restored['lease']=None;restored['manifest'].pop('job_id');restored['manifest']['allocation']['authorization_source']=None
    require(restored==draft,'scientific_draft_changed');return p

def request_body(model,prompt,system,settings):
    require(model in ('gpt-6-sol','gpt-6-astra') and settings=={'temperature':0.0,'max_tokens':16384},'unexpected_extraction_settings')
    return {'model':model,'instructions':system,'input':prompt,'max_output_tokens':settings['max_tokens'],'reasoning':{'effort':'medium'},'store':False,'service_tier':'default','prompt_cache_options':{'mode':'implicit','ttl':'30m'}}

def request_metadata(model,prompt,system,settings):
    body=request_body(model,prompt,system,settings);wire=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
    inp,out=(Decimal('2.5'),Decimal('10')) if model=='gpt-6-sol' else (Decimal('12.5'),Decimal('50'))
    price=(Decimal(len(wire)+1024)*inp+Decimal(16384)*out)/Decimal(1000000)
    return {'request_sha256':digest(body),'endpoint_body_sha256':hashlib.sha256(json.dumps({'endpoint':'https://api.openai.com/v1/responses','body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'wire_bytes_sha256':hashlib.sha256(wire).hexdigest(),'input_token_upper_bound':len(wire)+1024,'max_usd_reservation':str(price),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'system_sha256':hashlib.sha256(system.encode()).hexdigest(),'settings':settings,'model':model,'reasoning':'medium','timeout':180}

def reject_unknown(info,deny):
    require(info['request_sha256'] not in deny['body_compact_json_sha256'] and info['endpoint_body_sha256'] not in deny['endpoint_body_sorted_json_sha256'],'historical_unknown_request_identity')

def runtime():
    require(ref(R/h.DRIVER_REL)['sha256']==h.DRIVER_SHA,'frozen_driver_changed');sys.path.insert(0,str(R))
    driver=h.load('p8_first4_native_driver',R/h.DRIVER_REL);driver.verify_runtime(R,COMMIT);return driver

def capture_rows():
    """Stops the actual common build_profile -> P8 builder at fake complete, before transport."""
    driver=runtime();report=read(REPORT);policy=read(POLICY);deny=read(policy['unknown_request_denylist'])['identity_denylists']
    from autoresearch.taste.overnight.contracts import build_profile
    from autoresearch.taste.overnight.backends import RATES
    require(RATES['gpt-6-sol']==(2.5,10.0) or [Decimal(str(x)) for x in RATES['gpt-6-sol']]==[Decimal('2.5'),Decimal('10')],'frozen_sol_price_mismatch')
    require([Decimal(str(x)) for x in RATES['gpt-6-astra']]==[Decimal('12.5'),Decimal('50')],'frozen_astra_price_mismatch')
    class Captured(BaseException):pass
    rows=[]
    for expected,pr in zip(DRAFTS,draft_refs()):
        d=read(pr);check_draft(d);require(d['config']['researcher_id']==expected['researcher'] and d['backend']['model']==expected['model'],'draft_order_or_cell_changed')
        require(sum(r['packet']==pr for r in report['drafts'])==1,'draft_not_in_original_frozen_report')
        release=read(d['release']);documents=release['sources']['documents']
        require(digest(documents)==d['manifest']['documents_hash'] and digest(d['config'])==d['manifest']['config_hash'],'source_or_config_hash_changed')
        driver._register(d['registration'],'P8');calls=[]
        class Capture:
            def complete(self,prompt,**settings):
                calls.append((prompt,settings));raise Captured()
        try:build_profile(documents,d['config'],Capture())
        except Captured:pass
        require(len(calls)==1,'exactly_one_builder_call_required')
        prompt,settings=calls[0];system=settings.pop('system');info=request_metadata(d['backend']['model'],prompt,system,settings);reject_unknown(info,deny)
        require(Decimal(info['max_usd_reservation'])<=Decimal(str(d['backend']['max_usd'])),'original_ceiling_insufficient')
        rows.append({'packet':pr,'manifest_sha256':digest(d['manifest']),'release':d['release'],'source_manifest_hash':d['manifest']['source_manifest_hash'],'documents_hash':d['manifest']['documents_hash'],'config_hash':d['manifest']['config_hash'],'researcher_id':d['config']['researcher_id'],'model':d['backend']['model'],'method_id':'P8','request':info,'max_calls':1,'max_usd':str(d['backend']['max_usd'])})
    require(len({r['request']['request_sha256'] for r in rows})==4 and sum(Decimal(r['max_usd']) for r in rows)==Decimal(TOTAL),'first4_identity_or_ceiling_mismatch')
    return rows

def validate_authority(authority,*,initial=False):
    auth=read(authority)
    require(auth.get('schema_version')=='p8-first4-authorization-v1' and auth.get('state')=='authorized' and auth.get('scope')==SCOPE and bool(auth.get('authority')),'root_first4_authority_required')
    require(auth.get('policy')==POLICY and auth.get('runtime_commit')==COMMIT and auth.get('deadline')==DEADLINE and auth.get('max_inflight')==2 and auth.get('max_calls')==4 and Decimal(str(auth.get('max_usd')))==Decimal(TOTAL) and auth.get('historical_unknown_holds_released') is False and auth.get('astra_authority')==ASTRA_AUTHORITY,'first4_authority_binding_mismatch')
    proposal=read(auth['proposal']);require(proposal['schema_version']=='p8-first4-offline-proposal-v1' and proposal['script']==ref(__file__) and proposal['original_readiness']==REPORT and [r['packet'] for r in proposal['drafts']]==draft_refs(),'wrong_first4_proposal')
    pre=read(auth['astra_predecessor']);require(pre.get('schema_version')=='scaling-astra-first4-predecessor-v1' and pre.get('state')=='complete','known_astra_predecessor_required')
    terminal=read(pre['supervisor_terminal']);summary=read(pre['final_batch_summary']);snapshot=read(pre['closed_ledger_snapshot'])
    require(terminal.get('schema_version')=='scaling-astra-supervisor-terminal-v1' and terminal.get('status')=='complete' and terminal.get('stop_reason') is None and terminal.get('child_process_terminal') is True and terminal.get('native_accounting_drain_verified') is True and terminal.get('planned_jobs')==62 and len(terminal.get('completed_verified_batches',[]))==3 and terminal.get('index')==ASTRA_INDEX and terminal.get('script')==ASTRA_SUPERVISOR and ref(ASTRA_SUPERVISOR['path'])==ASTRA_SUPERVISOR,'astra_not_known_terminal')
    last=read(read(ASTRA_INDEX)['admissions'][-1]['prepared']);require(summary['batch_id']==last['batch_id'] and summary['status']=='complete' and summary['stop_reason'] is None,'wrong_astra_final_summary')
    l=summary['ledger'];require(l['inflight']==l['uncertain']==l['reserved_usd']==0 and l['held_after_uncertain'] is False and l['attempts']==snapshot['attempts']==terminal['known_verified_attempts'] and Decimal(str(l['spent_usd']))*1000000000==snapshot['known_spent_nanos']==terminal['known_verified_spend_nanos'],'astra_closure_accounting_mismatch')
    _,policy,current,configuration,_=a.validate_astra_authority(ASTRA_AUTHORITY)
    require(Path(snapshot['source_path']).resolve()==Path(policy['ledger']['path']).resolve(),'astra_snapshot_wrong_ledger')
    baseline=a.validate_baseline(current,snapshot,initial=False)
    if initial:require(current['reservation_rows']==snapshot['reservation_rows'],'new_attempts_since_astra_snapshot')
    h.budget_gate(current,TOTAL if initial else 0)
    return auth,policy,current,configuration,baseline

def prepare(authority,proposal_ref,destination):
    auth,policy,state,configuration,baseline=validate_authority(authority,initial=True);require(auth['proposal']==proposal_ref,'authority_proposal_mismatch')
    proposal=read(proposal_ref);rows=capture_rows();require(rows==proposal['drafts'],'captured_requests_changed')
    h.time_gate(datetime.now(timezone.utc),480);driver=runtime()
    from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
    def forbidden(*args,**kwargs):raise RuntimeError('preparation_forbids_backend_or_ledger_access')
    class IdentityLedger(DollarLedger):
        def __init__(self,path,*,max_usd,deadline,max_inflight):
            require(Path(path).resolve()==Path(policy['ledger']['path']).resolve() and max_usd==80 and deadline==DEADLINE and max_inflight==2,'wrong_ledger_spec')
            self.path=Path(path);self.deadline=datetime(2026,11,15,17,tzinfo=timezone.utc);self.configuration=configuration
        _connect=reserve=finish=summary=forbidden
    OpenAIResponsesBackend.complete=forbidden;driver.DollarLedger=IdentityLedger
    ledger=IdentityLedger(**dict(path=policy['ledger']['path'],max_usd=80,deadline=DEADLINE,max_inflight=2))
    template=read({'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'})
    batch={k:copy.deepcopy(template[k]) for k in ('schema_version','campaign_id','code_sha','runtime_root','deadline','max_workers','release_schema_version','release_scope','contract','env_file','roots')}
    batch.update(ledger=policy['ledger'],ledger_policy=POLICY,max_total_attempts=4,jobs=[],p8_first4_authority=authority,p8_first4_proposal=proposal_ref,astra_predecessor=auth['astra_predecessor'])
    packets=[]
    for row in rows:
        p=bind(read(row['packet']),authority);driver._prepare_packet(p,batch,ledger);jid=p['manifest']['job_id']
        require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'first4_job_already_started');packets.append(p)
    out=Path(destination).resolve();driver._outside_git(str(out));require(not out.exists(),'fresh_preparation_directory_required');out.mkdir(parents=True)
    mappings=[]
    for n,(row,p) in enumerate(zip(rows,packets)):
        packet_ref=write(out/('packet-%02d.json'%n),p);batch['jobs'].append(packet_ref);mappings.append({'original_draft':row['packet'],'bound_packet':packet_ref,'job_id':p['manifest']['job_id'],'request':row['request'],'only_changed_fields':['lease','manifest.job_id','manifest.allocation.authorization_source']})
    evidence=write(out/'admission-evidence.json',{'proposal':proposal_ref,'authority':authority,'baseline':baseline,'mappings':mappings,'scientific_fields_unchanged':True,'api_calls':0,'ledger_writes':0});batch['admission_evidence']=evidence
    raw=write(out/'batch.json',batch);prepared=driver.publish_prepared(driver.prepare_batch(raw['path'],raw['sha256']));loaded=driver.load_prepared(prepared['path'],prepared['sha256'])
    require([j['manifest']['job_id'] for j in loaded['jobs']]==[p['manifest']['job_id'] for p in packets],'published_order_changed')
    validate_authority(authority,initial=True);driver.verify_runtime(R,COMMIT)
    return write(out/'ready-index.json',{'schema_version':'p8-first4-admission-index-v1','state':'prepared_not_executed','script':ref(__file__),'proposal':proposal_ref,'authority':authority,'policy':POLICY,'predecessor':auth['astra_predecessor'],'baseline':baseline,'prepared':prepared,'evidence':evidence,'jobs':4,'max_calls':4,'max_usd':TOTAL,'future_prediction_jobs_admitted':0,'api_calls':0,'ledger_writes':0,'global_claims_created':0})

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('proposal');p.add_argument('--destination',required=True)
    p=sub.add_parser('prepare');p.add_argument('--destination',required=True);p.add_argument('--authority',nargs=2,required=True);p.add_argument('--proposal',nargs=2,required=True)
    args=ap.parse_args()
    if args.mode=='proposal':
        rows=capture_rows();out=Path(args.destination).resolve();require(not out.exists(),'fresh_proposal_directory_required');out.mkdir(parents=True)
        result=write(out/'proposal.json',{'schema_version':'p8-first4-offline-proposal-v1','state':'no_execution_authority_or_admission','script':ref(__file__),'original_readiness':REPORT,'runtime_commit':COMMIT,'policy':POLICY,'unknown_denylist':read(POLICY)['unknown_request_denylist'],'drafts':rows,'max_calls':4,'max_usd':TOTAL,'max_inflight':2,'deadline':DEADLINE,'two_slot_job_budget_schedule_seconds':480,'deadline_margin_seconds':600,'api_calls':0,'ledger_connections':0,'native_admissions':0,'future_joint_prediction_slots_if_all_valid':56,'future_crossed_prediction_slots_if_all_valid':28,'future_predictions_require_separate_admission':True})
    else:result=prepare({'path':str(Path(args.authority[0]).resolve()),'sha256':args.authority[1]},{'path':str(Path(args.proposal[0]).resolve()),'sha256':args.proposal[1]},args.destination)
    print(canonical(result))
if __name__=='__main__':main()
