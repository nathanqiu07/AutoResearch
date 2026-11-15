"""Exactly eight frozen P7/P3 builds. No live calls; separate root authority follows primary14 closure."""
import argparse,copy,hashlib,importlib.util,json,sys,urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode=True
PRIMARY14_HELPER={'path':'/private/tmp/gio_prepare_primary14_v1.py','sha256':'181fcd09bdce74fcb94b99f9d86118cebd304167544e03b65a88a1b5e8a00dd2'}
def load(name,r):
 path=Path(r['path'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('dependency_pin_mismatch')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
q=load('remaining8_primary14_helpers',PRIMARY14_HELPER);p,a,h=q.p,q.a,q.h
B,R,COMMIT,DEADLINE,POLICY=q.B,q.R,q.COMMIT,q.DEADLINE,q.POLICY
read,ref,require,write,canonical,digest=q.read,q.ref,q.require,q.write,q.canonical,q.digest
INVENTORY={'path':'/private/tmp/gio-remaining8-scaling-inventory-v1/inventory.json','sha256':'30916347bcba190e698ad1e4d3e50dcedea7fd18dbe38c603295172e392a923e'}
PRIMARY14_PREDECESSOR={'path':str(B/'accounting/primary14-remaining8-predecessor-v1.json'),'sha256':'7f92600770a6fb4ec32550bcaeec3200be600a4add14cd342f56f734bf33a073'}
DENY=q.DENY;SCOPE='frozen-p7-p3-remaining8-sol-astra';TOTAL='19.26906';NUMBERS=[10,11,13,14,16,17,19,20]
PRIMARY14_AUTHORITY={'path':str(B/'accounting/p8-primary14-authorization-v1.json'),'sha256':'33ff305aaf5514aba9d4486d4a9ba1fc612b39dc3df12637958e58907e2ee632'}
PRIMARY14_INDEX={'path':'/private/tmp/gio-primary14-native-admissions-v1/ready-index.json','sha256':'033a46b9f4f5a80b7926088f6d1b7936b9e1de94bda92135cd1584416fd540d6'}
PRIMARY14_SUPERVISOR={'path':'/private/tmp/gio_primary14_supervisor_v1.py','sha256':'3c34380487f1e224d04da055ad76c2a025417d17036fae481d5491122e83c8cc'}
def draft_refs():return [r['packet'] for r in read(INVENTORY)['drafts']]
def check_draft(d):
 require(sum(d==read(r) for r in draft_refs())==1,'exact_frozen_remaining8_draft_required')
 require(d['lease'] is None and d['manifest'].get('job_id') is None and d['manifest']['allocation']['authorization_source'] is None and d['manifest']['kind']=='build' and d['profile'] is None and d['item_ids']==[],'original_unleased_build_required')
def bind(draft,authority):
 check_draft(draft);v=copy.deepcopy(draft);v['manifest']['allocation']['authorization_source']={'policy':POLICY,'remaining8_authority':authority,'scope':SCOPE,'inventory':INVENTORY,'unknown_denylist':DENY}
 jid=h.semantic_id(v['manifest']);v['manifest']['job_id']=jid;v['lease']={'job_id':jid,'lease_id':digest({'job_id':jid,'authority':authority,'scope':SCOPE}),'owner':'gio-overnight-00','expires_at':DEADLINE}
 restored=copy.deepcopy(v);restored['lease']=None;restored['manifest'].pop('job_id');restored['manifest']['allocation']['authorization_source']=None;require(restored==draft,'scientific_draft_changed');return v

def capture_rows():
 driver=p.runtime();inventory=read(INVENTORY);rows=inventory['drafts'];deny=read(DENY)['identity_denylists']
 require(inventory['runtime_commit']==COMMIT and inventory['typed_denylist']==DENY and [r['draft_number'] for r in rows]==NUMBERS and inventory['neel_p3_luna_rep0_unavailable_preserved'] is True and inventory['no_luna_reextraction_or_replicate_substitution'] is True,'exact_frozen_inventory_required')
 from autoresearch.taste.overnight.contracts import build_profile
 class Captured(BaseException):pass
 for row in rows:
  d=read(row['packet']);check_draft(d);m,c=d['manifest'],d['config'];documents=read(d['release'])['sources']['documents']
  require(digest(m)==row['manifest_sha256'] and digest(documents)==m['documents_hash']==row['documents_hash'] and digest(c)==m['config_hash']==row['config_hash'],'frozen_source_config_changed')
  if m['method_id']=='P7':driver._peer_release(read(d['release']),'P7',c)
  driver._register(d['registration'],m['method_id']);calls=[]
  class Capture:
   def complete(self,prompt,**settings):calls.append((prompt,settings));raise Captured()
  try:build_profile(documents,c,Capture())
  except Captured:pass
  require(len(calls)==1,'exactly_one_builder_call_required');prompt,settings=calls[0];system=settings.pop('system');info=p.request_metadata(d['backend']['model'],prompt,system,settings);require(info==row['request'],'captured_frozen_request_changed');p.reject_unknown(info,deny)
 require(len({r['request']['request_sha256'] for r in rows})==8 and sum(Decimal(r['declared_max_usd']) for r in rows)==Decimal(TOTAL),'remaining8_identity_or_ceiling_changed')
 return rows

def batch_blocks(rows):
 require([r['draft_number'] for r in rows]==NUMBERS,'exact_remaining8_order_required')
 result=[]
 for method,subset,schema in [('P7',rows[:4],'released-development-v2-p7-peers-v1'),('P3',rows[4:],'released-development-v2')]:
  require(len(subset)==4 and all(r['method_id']==method and read(read(r['packet'])['release'])['schema_version']==schema for r in subset),'homogeneous_native_release_schema_required')
  require(sum(Decimal(r['declared_max_usd']) for r in subset)==Decimal('9.63453'),'block_ceiling_changed')
  result.append({'block':method,'rows':subset,'release_schema_version':schema,'max_calls':4,'max_usd':'9.63453','two_slot_job_budget_schedule_seconds':480})
 return result

def validate_authority(authority,*,initial=False):
 auth=read(authority)
 require(auth.get('schema_version')=='remaining8-build-authorization-v1' and auth.get('state')=='authorized' and bool(auth.get('authority')) and auth.get('scope')==SCOPE,'root_remaining8_authority_required')
 require(auth.get('policy')==POLICY and auth.get('inventory')==INVENTORY and auth.get('unknown_denylist')==DENY and auth.get('primary14_authority')==PRIMARY14_AUTHORITY and auth.get('primary14_predecessor')==PRIMARY14_PREDECESSOR and auth.get('runtime_commit')==COMMIT and auth.get('deadline')==DEADLINE and auth.get('max_inflight')==2 and auth.get('max_calls')==8 and Decimal(str(auth.get('max_usd')))==Decimal(TOTAL) and auth.get('historical_unknown_holds_released') is False and auth.get('future_predictions_require_separate_authority') is True,'remaining8_authority_binding_mismatch')
 proposal=read(auth['proposal']);require(proposal['schema_version']=='remaining8-build-offline-proposal-v2' and proposal['script']==ref(__file__) and proposal['inventory']==INVENTORY and proposal['unknown_denylist']==DENY and [r['packet'] for r in proposal['drafts']]==draft_refs(),'remaining8_proposal_mismatch')
 pre=read(auth['primary14_predecessor']);require(pre['schema_version']=='primary14-remaining8-predecessor-v1' and pre['state']=='complete','closed_primary14_predecessor_required')
 terminal=read(pre['supervisor_terminal']);verified=read(pre['verified_outcomes']);summary=read(pre['final_batch_summary']);snapshot=read(pre['closed_ledger_snapshot'])
 require(terminal['schema_version']=='p8-primary14-supervisor-terminal-v1' and terminal['status']=='complete' and terminal['stop_reason'] is None and terminal['native_accounting_drain_verified'] is True and terminal['child_process_terminal'] is True and terminal['verified']==pre['verified_outcomes'] and terminal['script']==PRIMARY14_SUPERVISOR and terminal['index']==PRIMARY14_INDEX and ref(PRIMARY14_SUPERVISOR['path'])==PRIMARY14_SUPERVISOR,'primary14_not_known_terminal')
 require(verified['native']['summary']==pre['final_batch_summary'] and verified['native']['attempted_calls']==14 and verified['native']['ledger_attempts']==298 and verified['native']['ledger_spent_nanos']==snapshot['known_spent_nanos'],'primary14_accounting_mismatch')
 require(summary['batch_id']==read(read(PRIMARY14_INDEX)['prepared'])['batch_id'] and summary['status']=='complete' and summary['stop_reason'] is None and summary['ledger']['attempts']==snapshot['attempts']==298 and Decimal(str(summary['ledger']['spent_usd']))*1000000000==snapshot['known_spent_nanos'] and summary['ledger']['uncertain']==summary['ledger']['inflight']==summary['ledger']['reserved_usd']==0 and summary['ledger']['held_after_uncertain'] is False,'primary14_unresolved_or_changed_accounting')
 _,policy,current,configuration,_=q.validate_authority(PRIMARY14_AUTHORITY)
 require(Path(snapshot['source_path']).resolve()==Path(policy['ledger']['path']).resolve(),'primary14_snapshot_wrong_ledger');baseline=a.validate_baseline(current,snapshot,initial=False)
 if initial:require(current['reservation_rows']==snapshot['reservation_rows'],'new_attempts_since_primary14_snapshot')
 h.budget_gate(current,TOTAL if initial else 0);return auth,policy,current,configuration,baseline

def prepare(authority,proposal_ref,destination):
 auth,policy,state,configuration,baseline=validate_authority(authority,initial=True);require(auth['proposal']==proposal_ref,'authority_proposal_mismatch');rows=capture_rows();proposal=read(proposal_ref);require(rows==proposal['drafts'] and batch_blocks(rows)==proposal['blocks'],'captured_requests_or_blocks_changed');h.time_gate(datetime.now(timezone.utc),960);driver=p.runtime()
 from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
 def forbidden(*args,**kwargs):raise RuntimeError('preparation_forbids_provider_or_ledger_access')
 class IdentityLedger(DollarLedger):
  def __init__(self,path,*,max_usd,deadline,max_inflight):
   require(Path(path).resolve()==Path(policy['ledger']['path']).resolve() and max_usd==80 and deadline==DEADLINE and max_inflight==2,'wrong_ledger_spec');self.path=Path(path);self.deadline=datetime(2026,11,15,17,tzinfo=timezone.utc);self.configuration=configuration
  _connect=reserve=finish=summary=forbidden
 urllib.request.urlopen=forbidden;OpenAIResponsesBackend.complete=forbidden;driver.DollarLedger=IdentityLedger;ledger=IdentityLedger(path=policy['ledger']['path'],max_usd=80,deadline=DEADLINE,max_inflight=2)
 template=read({'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'})
 stages=[];ids=[]
 for block in proposal['blocks']:
  batch={k:copy.deepcopy(template[k]) for k in ('schema_version','campaign_id','code_sha','runtime_root','deadline','max_workers','release_schema_version','release_scope','contract','env_file','roots')};batch.update(release_schema_version=block['release_schema_version'],ledger=policy['ledger'],ledger_policy=POLICY,max_total_attempts=4,jobs=[],remaining8_authority=authority,remaining8_proposal=proposal_ref,remaining8_block=block['block'],primary14_predecessor=auth['primary14_predecessor'])
  packets=[]
  for row in block['rows']:
   packet=bind(read(row['packet']),authority);driver._prepare_packet(packet,batch,ledger);jid=packet['manifest']['job_id'];require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'remaining8_job_already_started');packets.append(packet);ids.append(jid)
  stages.append((block,batch,packets))
 require(len(set(ids))==8,'duplicate_remaining8_job');out=Path(destination).resolve();driver._outside_git(str(out));require(not out.exists(),'fresh_preparation_directory_required');out.mkdir(parents=True);admissions=[]
 for block,batch,packets in stages:
  root=out/block['block'];root.mkdir();mappings=[]
  for n,(row,packet) in enumerate(zip(block['rows'],packets)):
   pr=write(root/('packet-%02d.json'%n),packet);batch['jobs'].append(pr);mappings.append({'original_draft':row['packet'],'bound_packet':pr,'job_id':packet['manifest']['job_id'],'request':row['request'],'only_changed_fields':['lease','manifest.job_id','manifest.allocation.authorization_source']})
  evidence=write(root/'admission-evidence.json',{'proposal':proposal_ref,'authority':authority,'baseline':baseline,'block':block['block'],'mappings':mappings,'scientific_fields_unchanged':True,'api_calls':0,'ledger_writes':0});batch['admission_evidence']=evidence
  raw=write(root/'batch.json',batch);prepared=driver.publish_prepared(driver.prepare_batch(raw['path'],raw['sha256']));loaded=driver.load_prepared(prepared['path'],prepared['sha256']);require([j['manifest']['job_id'] for j in loaded['jobs']]==[v['manifest']['job_id'] for v in packets],'published_order_changed');admissions.append({'block':block['block'],'prepared':prepared,'evidence':evidence,'release_schema_version':block['release_schema_version'],'jobs':4,'max_calls':4,'max_usd':'9.63453'})
 validate_authority(authority,initial=True);driver.verify_runtime(R,COMMIT)
 return write(out/'ready-index.json',{'schema_version':'remaining8-build-admission-index-v2','state':'prepared_not_executed','script':ref(__file__),'proposal':proposal_ref,'authority':authority,'policy':POLICY,'predecessor':auth['primary14_predecessor'],'inventory':INVENTORY,'unknown_denylist':DENY,'baseline':baseline,'admissions':admissions,'jobs':8,'max_calls':8,'max_usd':TOTAL,'future_prediction_jobs_admitted':0,'api_calls':0,'ledger_writes':0,'global_claims_created':0,'automatic_followup':False})

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True);q=sub.add_parser('proposal');q.add_argument('--destination',required=True);q=sub.add_parser('prepare');q.add_argument('--destination',required=True);q.add_argument('--authority',nargs=2,required=True);q.add_argument('--proposal',nargs=2,required=True);args=ap.parse_args()
 if args.mode=='proposal':
  rows=capture_rows();out=Path(args.destination).resolve();require(not out.exists(),'fresh_proposal_directory_required');out.mkdir(parents=True);result=write(out/'proposal.json',{'schema_version':'remaining8-build-offline-proposal-v2','state':'no_execution_authority_or_admission','script':ref(__file__),'inventory':INVENTORY,'unknown_denylist':DENY,'runtime_commit':COMMIT,'policy':POLICY,'primary14_authority':PRIMARY14_AUTHORITY,'primary14_predecessor':PRIMARY14_PREDECESSOR,'drafts':rows,'blocks':batch_blocks(rows),'max_calls':8,'max_usd':TOTAL,'max_inflight':2,'deadline':DEADLINE,'two_slot_job_budget_schedule_seconds':960,'deadline_margin_seconds':600,'api_calls':0,'ledger_connections':0,'native_admissions':0,'future_joint_slots_if_all_new_builds_valid':112,'future_predictions_require_separate_authority':True,'invalid_or_empty_preserved_no_repair':True,'automatic_followup':False})
 else:result=prepare({'path':str(Path(args.authority[0]).resolve()),'sha256':args.authority[1]},{'path':str(Path(args.proposal[0]).resolve()),'sha256':args.proposal[1]},args.destination)
 print(canonical(result))
if __name__=='__main__':main()
