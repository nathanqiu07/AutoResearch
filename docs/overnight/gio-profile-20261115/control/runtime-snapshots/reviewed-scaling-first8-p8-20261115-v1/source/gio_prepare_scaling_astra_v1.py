"""Offline prepared Astra admission helper. Root must issue a separate authority
AFTER complete Sol and its exact same-ledger snapshot. No execution or retries.
"""
import argparse,copy,hashlib,importlib.util,json,sys,urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
BASE_HELPER={'path':'/private/tmp/gio_prepare_scaling_sol_v1.py','sha256':'2e0e29c5dd73c334fb9ce86f1b3ee984f2f14e161c4c84427ed859a23c7c243c'}
raw=Path(BASE_HELPER['path']).read_bytes()
if hashlib.sha256(raw).hexdigest()!=BASE_HELPER['sha256']:raise ValueError('helper_pin_mismatch')
s=importlib.util.spec_from_file_location('astra_base_helpers',BASE_HELPER['path']);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
B,R,COMMIT,PLAN,DEADLINE,BLOCKS,PRICING=h.B,h.R,h.COMMIT,h.PLAN,h.DEADLINE,h.BLOCKS,h.PRICING
canonical,digest,ref,read,require,write,load=h.canonical,h.digest,h.ref,h.read,h.require,h.write,h.load
budget_gate,time_gate,ledger_read,semantic_id=h.budget_gate,h.time_gate,h.ledger_read,h.semantic_id
POLICY={'path':str(B/'accounting/scaling-80-policy-v1.json'),'sha256':'1a0ae152a102341bdeca12002e2754739b5e80dc2d9051d9d2039ebb28978286'}
SOL_INDEX={'path':'/private/tmp/gio-scaling-sol-native-admissions-v1/ready-index.json','sha256':'ba96f2c68641e9d2f6bc281e8657f068ee88691261c016c5069b34b9240946e2'}
SCOPE='astra140-core84-lexical28-semantic28'

def validate_baseline(current,snapshot,*,initial):
 require(snapshot['schema_version']=='closed-ledger-logical-snapshot-v1','sol_snapshot_schema_required')
 rows=snapshot['reservation_rows'];policies=snapshot['policy_rows']
 require(digest({'policy_rows':policies,'reservation_rows':rows})==snapshot['logical_snapshot_sha256'],'sol_snapshot_logical_hash_mismatch')
 require(len({r[0] for r in rows})==len(rows) and all(r[3]=='complete' for r in rows),'sol_snapshot_not_all_known_complete')
 require(snapshot['pending']==snapshot['uncertain']==snapshot['retained_hold_nanos']==0 and snapshot['known_spent_nanos']==sum(r[2] for r in rows) and snapshot['attempts']==len(rows),'sol_snapshot_accounting_mismatch')
 require(current['policy_rows']==policies,'scaling_policy_changed')
 actual={r[0]:r for r in current['reservation_rows']}
 require(all(actual.get(r[0])==r for r in rows),'sol_reservations_changed_or_disappeared')
 if initial:require(current['reservation_rows']==rows,'new_attempts_since_sol_snapshot')
 budget_gate(current,'68.454' if initial else 0)
 return {'attempts':len(rows),'spent':sum(r[2] for r in rows)}

def validate_astra_authority(authority_ref,*,initial=False):
 auth=read(authority_ref)
 # No ledger connection can occur before a separate pinned Astra authority exists.
 require(auth.get('schema_version')=='scaling-astra-authorization-v1' and auth.get('state')=='authorized' and auth.get('scope')==SCOPE and bool(auth.get('authority')),'root_astra_authority_required')
 require(auth.get('policy')==POLICY and auth.get('scaling_plan')==PLAN and auth.get('runtime_commit')==COMMIT and auth.get('deadline')==DEADLINE and auth.get('max_inflight')==2 and auth.get('max_calls')==140 and Decimal(str(auth.get('max_usd')))==Decimal('68.454') and auth.get('historical_unknown_holds_released') is False,'astra_authority_binding_mismatch')
 pre=read(auth['sol_predecessor']);require(pre.get('schema_version')=='scaling-sol-astra-predecessor-v1' and pre.get('state')=='complete','complete_sol_predecessor_required')
 terminal=read(pre['supervisor_terminal']);summary=read(pre['final_batch_summary']);snapshot=read(pre['closed_ledger_snapshot']);sol_index=read(SOL_INDEX)
 require(terminal.get('schema_version')=='scaling-sol-supervisor-terminal-v2' and terminal.get('status')=='complete' and terminal.get('stop_reason') is None and terminal.get('child_process_terminal') is True and terminal.get('native_accounting_drain_verified') is True and terminal.get('planned_jobs')==62 and len(terminal.get('completed_verified_batches',[]))==3 and terminal.get('index')==SOL_INDEX,'sol_not_complete_and_drained')
 require(terminal.get('script')==auth['sol_supervisor'] and ref(auth['sol_supervisor']['path'])==auth['sol_supervisor'],'sol_supervisor_provenance_mismatch')
 last=read(sol_index['admissions'][-1]['prepared']);require(summary.get('batch_id')==last['batch_id'] and summary.get('status')=='complete' and summary.get('stop_reason') is None,'wrong_sol_final_summary')
 ledger=summary['ledger'];require(ledger['inflight']==ledger['uncertain']==ledger['reserved_usd']==0 and ledger['held_after_uncertain'] is False and ledger['attempts']==snapshot['attempts']==terminal['known_verified_attempts'] and Decimal(str(ledger['spent_usd']))*1000000000==snapshot['known_spent_nanos']==terminal['known_verified_spend_nanos'],'sol_summary_ledger_mismatch')
 policy=read(POLICY);require(Path(snapshot['source_path']).resolve()==Path(policy['ledger']['path']).resolve(),'sol_snapshot_wrong_ledger')
 policy,current,configuration=h.validate_authority(POLICY,policy['profile204_predecessor'])
 baseline=validate_baseline(current,snapshot,initial=initial)
 return auth,policy,current,configuration,baseline

def bind(draft,authority_ref):
 require(draft['lease'] is None and draft['manifest'].get('job_id') is None and draft['manifest']['allocation']['authorization_source'] is None,'only_unleased_original_drafts')
 require(draft['manifest']['kind']=='predict' and draft['backend']['model']=='gpt-6-astra','astra_predict_only')
 p=copy.deepcopy(draft);p['manifest']['allocation']['authorization_source']={'policy':POLICY,'astra_authority':authority_ref,'scaling_plan':PLAN,'scope':SCOPE}
 job=semantic_id(p['manifest']);p['manifest']['job_id']=job;p['lease']={'job_id':job,'lease_id':digest({'job_id':job,'policy':POLICY,'authority':authority_ref,'scope':'scaling-astra-only-v1'}),'owner':'gio-overnight-00','expires_at':DEADLINE}
 restored=copy.deepcopy(p);restored['lease']=None;restored['manifest'].pop('job_id');restored['manifest']['allocation']['authorization_source']=None;require(restored==draft,'scientific_draft_changed');return p

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--authority',nargs=2,required=True,metavar=('FILE','SHA256'));ap.add_argument('--destination',required=True);a=ap.parse_args();sys.dont_write_bytecode=True
 authority_ref={'path':str(Path(a.authority[0]).resolve()),'sha256':a.authority[1]};auth,policy,state,configuration,baseline=validate_astra_authority(authority_ref,initial=True);plan=read(PLAN);tranche=plan['tranches'][1]
 require(tranche['model']=='gpt-6-astra' and tranche['native_jobs']==62 and tranche['logical_prediction_slots']==140 and [x['block'] for x in tranche['batches']]==BLOCKS,'exact_astra_tranche_required');time_gate(datetime.now(timezone.utc),tranche['two_slot_job_budget_schedule_seconds'])
 require(ref(R/h.DRIVER_REL)['sha256']==h.DRIVER_SHA,'frozen_driver_changed');sys.path.insert(0,str(R));driver=load('astra_admission_driver',R/h.DRIVER_REL);driver.verify_runtime(R,COMMIT)
 from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
 from autoresearch.taste.overnight.consumer import prepare_payload
 def forbidden(*a,**k):raise RuntimeError('admission_forbids_calls_and_ledger_mutations')
 urllib.request.urlopen=forbidden;OpenAIResponsesBackend.complete=forbidden
 class IdentityLedger(DollarLedger):
  def __init__(self,path,*,max_usd,deadline,max_inflight):
   require(Path(path).resolve()==Path(policy['ledger']['path']).resolve() and max_usd==80 and deadline==DEADLINE and max_inflight==2,'native_ledger_spec_mismatch');self.path=Path(path);self.deadline=datetime(2026,11,15,17,tzinfo=timezone.utc);self.configuration=configuration
  reserve=forbidden;finish=forbidden;summary=forbidden;_connect=forbidden
 driver.DollarLedger=IdentityLedger;ledger=IdentityLedger(**{'path':policy['ledger']['path'],'max_usd':80,'deadline':DEADLINE,'max_inflight':2})
 out=Path(a.destination).resolve();driver._outside_git(str(out));require(not out.exists(),'fresh_admission_directory_required');stages=[];alljobs=[]
 template=read({'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'})
 for block in tranche['batches']:
  bound=[];batch={k:copy.deepcopy(template[k]) for k in ['schema_version','campaign_id','code_sha','runtime_root','deadline','max_workers','release_schema_version','release_scope','contract','env_file','roots']};batch.update(ledger=policy['ledger'],ledger_policy=POLICY,jobs=[],max_total_attempts=block['max_calls'],scaling_plan=PLAN,sol_predecessor=auth['sol_predecessor'],astra_authority=authority_ref,scaling_model='gpt-6-astra',scaling_block=block['block'])
  require(digest([j['packet'] for j in block['jobs']])==block['packet_order_sha256'],'frozen_packet_order_changed')
  for row in block['jobs']:
   draft=read(row['packet']);require(digest(draft['manifest'])==row['manifest_sha256'],'draft_manifest_changed');p=bind(draft,authority_ref);jid=p['manifest']['job_id'];require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'job_already_started');prepared=driver._prepare_packet(p,batch,ledger);actual=[]
   for item in prepared['items']:
    payload=prepare_payload(prepared['profile'],item['context'],item['options'],prepared['config']);body={'model':'gpt-6-astra','instructions':payload['system'],'input':payload['prompt'],'max_output_tokens':8192,'reasoning':{'effort':'medium'},'store':False,'service_tier':'default','prompt_cache_options':{'mode':'implicit','ttl':'30m'}};actual.append((digest(body),hashlib.sha256(json.dumps({'endpoint':'https://api.openai.com/v1/responses','body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest()))
   require(actual==[(x['request_sha256'],x['endpoint_body_sha256']) for x in row['requests']],'native_wire_identity_changed');bound.append((row,p));alljobs.append(jid)
  stages.append((block,batch,bound))
 require(len(alljobs)==len(set(alljobs))==62,'duplicate_or_missing_native_jobs');out.mkdir(parents=True,exist_ok=False);admissions=[]
 for block,batch,bound in stages:
  root=out/block['block'];root.mkdir();mapping=[]
  for i,(row,p) in enumerate(bound):
   pr=write(root/('packet-%03d.json'%i),p);batch['jobs'].append(pr);mapping.append({'job_id':p['manifest']['job_id'],'original_draft':row['packet'],'packet':pr,'requests':row['requests'],'only_changed_fields':['lease','manifest.job_id','manifest.allocation.authorization_source']})
  evidence=write(root/'admission-evidence.json',{'plan':PLAN,'policy':POLICY,'authority':authority_ref,'sol_predecessor':auth['sol_predecessor'],'block':block['block'],'mapping':mapping,'scientific_fields_unchanged':True,'calls':0,'ledger_mutations':0});batch['admission_evidence']=evidence;raw=write(root/'batch.json',batch);published=driver.publish_prepared(driver.prepare_batch(raw['path'],raw['sha256']));verified=driver.load_prepared(published['path'],published['sha256']);require([j['manifest']['job_id'] for j in verified['jobs']]==[p['manifest']['job_id'] for _,p in bound],'published_job_order_changed');admissions.append({'block':block['block'],'prepared':published,'raw_batch':raw,'evidence':evidence,'jobs':len(bound),'calls':block['max_calls'],'max_usd':block['max_usd'],'two_slot_job_budget_schedule_seconds':block['two_slot_job_budget_schedule_seconds']})
 validate_astra_authority(authority_ref,initial=True);driver.verify_runtime(R,COMMIT)
 result={'schema_version':'scaling-astra-admission-index-v1','state':'prepared_not_executed','script':ref(__file__),'policy':POLICY,'authority':authority_ref,'predecessor':auth['sol_predecessor'],'baseline':baseline,'plan':PLAN,'model':'gpt-6-astra','jobs':62,'max_calls':140,'max_usd':'68.4540000','all_six_planned_batches_retained_in_plan':True,'calls':0,'ledger_mutations':0,'global_claims_created':0,'admissions':admissions};print(canonical(write(out/'ready-index.json',result)))
if __name__=='__main__':main()
