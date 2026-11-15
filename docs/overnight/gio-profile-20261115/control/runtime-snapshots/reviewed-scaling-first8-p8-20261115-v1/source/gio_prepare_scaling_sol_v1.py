"""Root-authorized native admission for Sol only; never executes model calls.
Before root supplies exact policy/predecessor pins this script cannot connect to
any ledger or write admissions. It preserves every original scientific field.
"""
import argparse,copy,hashlib,importlib.util,json,sqlite3,sys,urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
B=Path('/private/tmp/gio-profile-20261115-coordinator')
R=Path('/Users/giordanorogers/.codex/worktrees/gio-overnight-phase2-runtime/AutoResearch-overnight-control')
COMMIT='f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
PLAN={'path':'/private/tmp/gio-scaling-first-priority-plan-v1.json','sha256':'69385b28d65a900637274e0cdbc64b3cf0fdd1879ef86438aac5e2ea0faa7626'}
DRIVER_REL='docs/overnight/gio-profile-20261115/control/run_batch.py'
DRIVER_SHA='693681c0b03bc02423be9c7ee7a5a2c2e6b9bdb673ef6498558c9129913401c5'
DEADLINE='2026-11-15T17:00:00Z'
BLOCKS=['core','lexical_retrieval','semantic_retrieval']
PRICING='openai-standard-short-context-30m-cache-write-1.25x-2026-11-15'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def ref(p):p=Path(p).resolve();return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def read(r):
 p=Path(r['path']);raw=p.read_bytes()
 if not p.is_absolute() or hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('pin_mismatch')
 return json.loads(raw)
def require(c,msg):
 if not c:raise ValueError(msg)
def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(canonical(v)+'\n')
 return ref(p)
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def budget_gate(state,proposed):
 require(state['pending']==0 and state['uncertain']==0,'unknown_or_pending_scaling_accounting')
 require(Decimal(str(state['known_usd']))+Decimal(str(state['held_usd']))+Decimal(str(proposed))<=Decimal(80),'scaling80_headroom_insufficient')

def time_gate(now,remaining_schedule,margin=600):
 end=datetime(2026,11,15,17,tzinfo=timezone.utc)
 require(now.tzinfo is not None and (end-now).total_seconds()>=remaining_schedule+margin,'conservative_deadline_fit_failed')

def ledger_read(path):
 p=Path(path).resolve()
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as c:
  c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
  policies=[list(r) for r in c.execute('SELECT id,body FROM policy ORDER BY id')]
  rows=[list(r) for r in c.execute('SELECT id,reserved,actual,status,metadata FROM reservations ORDER BY id')];c.rollback()
 known=sum(r[2] for r in rows);held=sum(r[1] for r in rows if r[3] in ('pending','uncertain'))
 return {'policy_rows':policies,'reservation_rows':rows,'attempts':len(rows),'known_nanos':known,'held_nanos':held,'known_usd':str(Decimal(known)/1000000000),'held_usd':str(Decimal(held)/1000000000),'pending':sum(r[3]=='pending' for r in rows),'uncertain':sum(r[3]=='uncertain' for r in rows)}

def validate_authority(policy_ref,predecessor_ref,*,empty=False):
 policy=read(policy_ref);pre=read(predecessor_ref)
 require(policy.get('schema_version')=='phase2-ledger-policy-v1' and policy.get('state')=='authorized' and bool(policy.get('authority')),'root_authorized_scaling_policy_required')
 require(policy.get('scaling_plan')==PLAN and policy.get('profile204_predecessor')==predecessor_ref and policy['deadline']==DEADLINE and policy['pricing_version']==PRICING,'scaling_authority_binding_mismatch')
 spec=policy['ledger'];p=Path(spec['path']).resolve()
 require(set(spec)=={'path','max_usd','max_inflight'} and spec['max_usd']==80 and type(spec['max_inflight']) is int and spec['max_inflight']==2 and p.parent==B/'ledger' and p!=B/'ledger/profile-openai-continuation2.sqlite' and p.is_file(),'separate_existing_scaling80_ledger_required')
 require(pre.get('state')=='complete','closed_profile204_predecessor_required')
 terminal=read(pre['supervisor_terminal']);summary=read(pre['final_batch_summary']);snapshot=read(pre['closed_ledger_snapshot'])
 require(terminal['schema_version']=='profile204-supervisor-terminal-v1' and terminal['status']=='complete' and terminal['stop_reason'] is None and len(terminal['completed_verified_batches'])==4 and terminal['planned_jobs']==204,'profile204_not_known_terminal')
 require(snapshot['schema_version']=='closed-ledger-logical-snapshot-v1' and Path(snapshot['source_path']).resolve()==B/'ledger/profile-openai-continuation2.sqlite','wrong_profile204_snapshot')
 old=ledger_read(snapshot['source_path'])
 require(old['policy_rows']==snapshot['policy_rows'] and old['reservation_rows']==snapshot['reservation_rows'] and digest({'policy_rows':old['policy_rows'],'reservation_rows':old['reservation_rows']})==snapshot['logical_snapshot_sha256'],'closed_profile204_ledger_changed')
 require(old['pending']==old['uncertain']==old['held_nanos']==0,'profile204_has_unresolved_hold')
 require(summary['status']=='complete' and summary['ledger']['inflight']==summary['ledger']['uncertain']==0 and summary['ledger']['attempts']==old['attempts'] and Decimal(str(summary['ledger']['spent_usd']))==Decimal(old['known_usd']),'profile204_summary_accounting_mismatch')
 require(Decimal('.657038660')+Decimal(old['known_usd'])+Decimal(old['held_usd'])+80<=200,'profile_aggregate200_exceeded')
 state=ledger_read(p);configuration={'limit_nanos':80000000000,'deadline':'2026-11-15T17:00:00+00:00','max_inflight':2,'pricing_version':PRICING}
 require(state['policy_rows']==[[1,canonical(configuration)]],'scaling_ledger_configuration_mismatch')
 if empty:require(state['attempts']==state['known_nanos']==state['held_nanos']==0,'initial_scaling_admission_requires_fresh_empty_ledger')
 budget_gate(state,'13.6901000' if empty else 0)
 return policy,state,configuration

def semantic_id(manifest):return digest({k:v for k,v in manifest.items() if k not in {'job_id','lease','created_at','updated_at'}})
def bind(draft,policy_ref,predecessor_ref):
 require(draft['lease'] is None and draft['manifest'].get('job_id') is None and draft['manifest']['allocation']['authorization_source'] is None,'only_unleased_original_drafts')
 require(draft['manifest']['kind']=='predict' and draft['backend']['model']=='gpt-6-sol','sol_predict_only')
 p=copy.deepcopy(draft);p['manifest']['allocation']['authorization_source']={'policy':policy_ref,'profile204_predecessor':predecessor_ref,'scaling_plan':PLAN,'scope':'sol140-core84-lexical28-semantic28'}
 job=semantic_id(p['manifest']);p['manifest']['job_id']=job;p['lease']={'job_id':job,'lease_id':digest({'job_id':job,'policy':policy_ref,'predecessor':predecessor_ref,'scope':'scaling-sol-only-v1'}),'owner':'gio-overnight-00','expires_at':DEADLINE}
 restored=copy.deepcopy(p);restored['lease']=None;restored['manifest'].pop('job_id');restored['manifest']['allocation']['authorization_source']=None
 require(restored==draft,'scientific_draft_changed');return p

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('policy','predecessor'):ap.add_argument('--'+name,nargs=2,required=True,metavar=('FILE','SHA256'))
 ap.add_argument('--destination',required=True);a=ap.parse_args();sys.dont_write_bytecode=True
 policy_ref={'path':str(Path(a.policy[0]).resolve()),'sha256':a.policy[1]};predecessor_ref={'path':str(Path(a.predecessor[0]).resolve()),'sha256':a.predecessor[1]}
 policy,state,configuration=validate_authority(policy_ref,predecessor_ref,empty=True);plan=read(PLAN);tranche=plan['tranches'][0]
 require(tranche['model']=='gpt-6-sol' and tranche['native_jobs']==62 and tranche['logical_prediction_slots']==140 and [x['block'] for x in tranche['batches']]==BLOCKS,'exact_sol_tranche_required')
 time_gate(datetime.now(timezone.utc),tranche['two_slot_job_budget_schedule_seconds'])
 require(ref(R/DRIVER_REL)['sha256']==DRIVER_SHA,'frozen_driver_changed');sys.path.insert(0,str(R));driver=load('sol_admission_driver',R/DRIVER_REL);driver.verify_runtime(R,COMMIT)
 from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
 from autoresearch.taste.overnight.contracts import ProfileArtifact
 from autoresearch.taste.overnight.consumer import prepare_payload
 def forbidden(*a,**k):raise RuntimeError('admission_forbids_calls_and_ledger_mutations')
 urllib.request.urlopen=forbidden;OpenAIResponsesBackend.complete=forbidden
 class IdentityLedger(DollarLedger):
  def __init__(self,path,*,max_usd,deadline,max_inflight):
   require(Path(path).resolve()==Path(policy['ledger']['path']).resolve() and max_usd==80 and deadline==DEADLINE and max_inflight==2,'native_ledger_spec_mismatch')
   self.path=Path(path);self.deadline=datetime(2026,11,15,17,tzinfo=timezone.utc);self.configuration=configuration
  reserve=forbidden;finish=forbidden;summary=forbidden;_connect=forbidden
 driver.DollarLedger=IdentityLedger;ledger=IdentityLedger(**{'path':policy['ledger']['path'],'max_usd':80,'deadline':DEADLINE,'max_inflight':2})
 out=Path(a.destination).resolve();driver._outside_git(str(out));require(not out.exists(),'fresh_admission_directory_required');stages=[];alljobs=[]
 template=read({'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'})
 # Validate every exact packet and wire pin before any publication.
 for block in tranche['batches']:
  bound=[];batch={k:copy.deepcopy(template[k]) for k in ['schema_version','campaign_id','code_sha','runtime_root','deadline','max_workers','release_schema_version','release_scope','contract','env_file','roots']};batch.update(ledger=policy['ledger'],ledger_policy=policy_ref,jobs=[],max_total_attempts=block['max_calls'],scaling_plan=PLAN,profile204_predecessor=predecessor_ref,scaling_model='gpt-6-sol',scaling_block=block['block'])
  require(digest([j['packet'] for j in block['jobs']])==block['packet_order_sha256'],'frozen_packet_order_changed')
  for row in block['jobs']:
   draft=read(row['packet']);require(digest(draft['manifest'])==row['manifest_sha256'],'draft_manifest_changed');p=bind(draft,policy_ref,predecessor_ref);jid=p['manifest']['job_id']
   require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'job_already_started')
   prepared=driver._prepare_packet(p,batch,ledger);actual=[]
   for item in prepared['items']:
    payload=prepare_payload(prepared['profile'],item['context'],item['options'],prepared['config']);body={'model':'gpt-6-sol','instructions':payload['system'],'input':payload['prompt'],'max_output_tokens':8192,'reasoning':{'effort':'medium'},'store':False,'service_tier':'default','prompt_cache_options':{'mode':'implicit','ttl':'30m'}}
    actual.append((digest(body),hashlib.sha256(json.dumps({'endpoint':'https://api.openai.com/v1/responses','body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest()))
   require(actual==[(x['request_sha256'],x['endpoint_body_sha256']) for x in row['requests']],'native_wire_identity_changed');bound.append((row,p));alljobs.append(jid)
  stages.append((block,batch,bound))
 require(len(alljobs)==len(set(alljobs))==62,'duplicate_or_missing_native_jobs');out.mkdir(parents=True,exist_ok=False);admissions=[]
 for block,batch,bound in stages:
  root=out/block['block'];root.mkdir();mapping=[]
  for i,(row,p) in enumerate(bound):
   pr=write(root/('packet-%03d.json'%i),p);batch['jobs'].append(pr);mapping.append({'job_id':p['manifest']['job_id'],'original_draft':row['packet'],'packet':pr,'requests':row['requests'],'only_changed_fields':['lease','manifest.job_id','manifest.allocation.authorization_source']})
  evidence=write(root/'admission-evidence.json',{'plan':PLAN,'policy':policy_ref,'predecessor':predecessor_ref,'block':block['block'],'mapping':mapping,'scientific_fields_unchanged':True,'calls':0,'ledger_mutations':0});batch['admission_evidence']=evidence;raw=write(root/'batch.json',batch);published=driver.publish_prepared(driver.prepare_batch(raw['path'],raw['sha256']));verified=driver.load_prepared(published['path'],published['sha256'])
  require([j['manifest']['job_id'] for j in verified['jobs']]==[p['manifest']['job_id'] for _,p in bound],'published_job_order_changed');admissions.append({'block':block['block'],'prepared':published,'raw_batch':raw,'evidence':evidence,'jobs':len(bound),'calls':block['max_calls'],'max_usd':block['max_usd'],'two_slot_job_budget_schedule_seconds':block['two_slot_job_budget_schedule_seconds']})
 validate_authority(policy_ref,predecessor_ref,empty=True);driver.verify_runtime(R,COMMIT)
 result={'schema_version':'scaling-sol-admission-index-v1','state':'prepared_not_executed','script':ref(__file__),'policy':policy_ref,'predecessor':predecessor_ref,'plan':PLAN,'model':'gpt-6-sol','jobs':62,'max_calls':140,'max_usd':'13.6901000','all_six_planned_batches_retained_in_plan':True,'astra_admitted':False,'calls':0,'ledger_mutations':0,'global_claims_created':0,'admissions':admissions}
 print(canonical(write(out/'ready-index.json',result)))
if __name__=='__main__':main()
