"""One frozen valid Neel/Sol joint prediction draft. Proposal is offline; admission needs root authority."""
import argparse,copy,hashlib,importlib.util,json,sys,urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode=True
P8={'path':'/private/tmp/gio_prepare_p8_first4_v1.py','sha256':'7a267b14f9a0636d6f69704d49c2f86efd53f70e79ee2af08f98edcb57cd5d77'}
def load(name,r):
 path=Path(r['path'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('dependency_pin_mismatch')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('primary14_p8_helpers',P8);a,h=p.a,p.h
B,R,COMMIT,DEADLINE,POLICY=p.B,p.R,p.COMMIT,p.DEADLINE,p.POLICY
read,ref,require,write,canonical,digest=p.read,p.ref,p.require,p.write,p.canonical,p.digest
BINDINGS={'path':'/private/tmp/gio-profile-20261115-scaling/primary-ac-valid-descendants-v1-rf71pftd/primary-ac-ready-index.json','sha256':'f394a9724c8da39b09fa57a1ac61dc76a9287da1748aeb7fdda9efb84934f2e6'}
DRAFT={'path':str(Path(BINDINGS['path']).parent/'unleased-prediction-00.json'),'sha256':'fc96837342840aa8c2ac068132d5847b16dbf9742845cd386dcf8942657fc4da'}
PREDECESSOR={'path':str(B/'accounting/p8-first4-primary14-predecessor-v1.json'),'sha256':'5328a3e100b1f5068b42c54646c378f5599e1137bfbf4be2e2dfb398d82a0903'}
FIRST4_AUTHORITY={'path':str(B/'accounting/p8-first4-authorization-v1.json'),'sha256':'b1ea823b942b4c1cdbb704763404e64c5060fca0eec5020a23d1181fa6e91832'}
DENY={'path':'/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json','sha256':'7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'}
SCOPE='p8-primary14-neel-sol-joint-only';TOTAL='1.51148'
def check_draft(d):
 m,b,c=d['manifest'],d['backend'],d['config']
 require(d['lease'] is None and m.get('job_id') is None and m['allocation']['authorization_source'] is None,'original_unleased_draft_required')
 require(m['kind']=='predict' and m['method_id']=='P8' and m['personalization_cap']==8192 and m['replicate_id']==0 and m['scaling_selected_cell_id']=='P8-c8192-explicit-only/neel_nanda/r0' and m['scaling_studies']==['A'],'exact_primary14_cell_required')
 require(b=={'model':'gpt-6-sol','reasoning':'medium','timeout':60,'max_calls':14,'max_seconds':900,'max_usd':1.51148} and c['settings']=={'max_tokens':8192,'temperature':0.0},'original_prediction_settings_required')
 require(all(m['allocation'][k]==b[k] for k in ('max_calls','max_seconds','max_usd')) and len(d['item_ids'])==len(set(d['item_ids']))==14 and m['code_sha']==COMMIT and m['deadline']==DEADLINE,'original_limits_or_inputs_changed')
 require(d['profile']==m['scaling_actual_parent_lineage']['actual_profile'] and m['scaling_actual_parent_lineage']['parent_status']=='complete' and m['parent_job_ids']==[m['scaling_actual_parent_lineage']['actual_build_job_id']],'valid_actual_parent_required')
def bind(draft,authority):
 check_draft(draft);v=copy.deepcopy(draft)
 v['manifest']['allocation']['authorization_source']={'policy':POLICY,'primary14_authority':authority,'scope':SCOPE,'bindings':BINDINGS,'predecessor':PREDECESSOR,'unknown_denylist':DENY}
 jid=h.semantic_id(v['manifest']);v['manifest']['job_id']=jid;v['lease']={'job_id':jid,'lease_id':digest({'job_id':jid,'authority':authority,'scope':SCOPE}),'owner':'gio-overnight-00','expires_at':DEADLINE}
 restored=copy.deepcopy(v);restored['lease']=None;restored['manifest'].pop('job_id');restored['manifest']['allocation']['authorization_source']=None
 require(restored==draft,'scientific_draft_changed');return v

def capture():
 driver=p.runtime();index=read(BINDINGS);d=read(DRAFT);check_draft(d)
 require(index['runtime_sha']==COMMIT and index['execution_authorized'] is False and len(index['ready_prediction_packets'])==1 and index['ready_prediction_packets'][0]['packet']==DRAFT,'exact_single_binding_required')
 counts=index['counts'];require(counts['new_planned_descendant_rows']==84 and counts['new_unavailable_invalid_parent_rows']==70 and counts['new_unleased_ready_rows']==counts['new_prediction_call_ceiling']==14,'missingness_changed')
 from autoresearch.taste.overnight.contracts import ProfileArtifact
 from autoresearch.taste.overnight.consumer import prepare_payload
 profile=ProfileArtifact.from_dict(read(d['profile']));release=read(d['release']);items=release['items']
 require(profile.status=='complete' and profile.researcher_id=='neel_nanda' and profile.profile_id==d['manifest']['profile_hash'],'valid_neel_profile_required')
 require([x['item_id'] for x in items]==d['item_ids'] and digest(items)==d['manifest']['items_hash'] and digest(d['config'])==d['manifest']['config_hash'],'item_order_or_config_changed')
 pins=index['ready_prediction_packets'][0]['request_pins'];require(len(pins)==14,'binding_request_count_changed');requests=[];denied=read(DENY)['identity_denylists']
 for item,pin in zip(items,pins):
  payload=prepare_payload(profile,item['context'],item['options'],d['config']);body={'model':'gpt-6-sol','instructions':payload['system'],'input':payload['prompt'],'max_output_tokens':8192,'reasoning':{'effort':'medium'},'store':False,'service_tier':'default','prompt_cache_options':{'mode':'implicit','ttl':'30m'}}
  wire=json.dumps(body,ensure_ascii=False,allow_nan=False).encode();info={'item_id':item['item_id'],'item_sha256':digest(item),'request_sha256':digest(body),'endpoint_body_sha256':hashlib.sha256(json.dumps({'endpoint':'https://api.openai.com/v1/responses','body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'wire_bytes_sha256':hashlib.sha256(wire).hexdigest(),'input_token_upper_bound':len(wire)+1024,'max_usd_reservation':str((Decimal(len(wire)+1024)*Decimal('2.5')+Decimal(8192)*10)/1000000)}
  require(info['request_sha256']==pin['wire_request_sha256'] and info['wire_bytes_sha256']==pin['wire_bytes_sha256'] and info['item_id']==pin['item_id'] and info['item_sha256']==pin['item_sha256'] and info['input_token_upper_bound']==pin['input_token_upper_bound'] and Decimal(info['max_usd_reservation'])==Decimal(str(pin['max_usd_reservation'])),'native_frozen_request_changed')
  require(info['input_token_upper_bound']+8192<272000,'short_context_bound_exceeded');p.reject_unknown(info,denied);requests.append(info)
 require(len({r['request_sha256'] for r in requests})==14 and sum(Decimal(r['max_usd_reservation']) for r in requests)==Decimal(TOTAL),'request_uniqueness_or_cost_mismatch')
 return {'packet':DRAFT,'manifest_sha256':digest(d['manifest']),'profile':d['profile'],'release':d['release'],'requests':requests,'max_calls':14,'max_usd':TOTAL,'max_seconds':900}

def validate_authority(authority,*,initial=False):
 auth=read(authority)
 require(auth.get('schema_version')=='p8-primary14-authorization-v1' and auth.get('state')=='authorized' and bool(auth.get('authority')) and auth.get('scope')==SCOPE,'root_primary14_authority_required')
 require(auth.get('policy')==POLICY and auth.get('predecessor')==PREDECESSOR and auth.get('bindings')==BINDINGS and auth.get('unknown_denylist')==DENY and auth.get('runtime_commit')==COMMIT and auth.get('deadline')==DEADLINE and auth.get('max_inflight')==2 and auth.get('max_calls')==14 and Decimal(str(auth.get('max_usd')))==Decimal(TOTAL) and auth.get('historical_unknown_holds_released') is False and auth.get('planned_descendant_slots')==84 and auth.get('unavailable_descendant_slots')==70,'primary14_authority_binding_mismatch')
 proposal=read(auth['proposal']);require(proposal['schema_version']=='p8-primary14-offline-proposal-v1' and proposal['script']==ref(__file__) and proposal['bindings']==BINDINGS and proposal['predecessor']==PREDECESSOR and proposal['unknown_denylist']==DENY and proposal['draft']['packet']==DRAFT,'primary14_proposal_mismatch')
 pre=read(PREDECESSOR);require(pre['schema_version']=='p8-first4-primary14-predecessor-v1' and pre['state']=='complete' and pre['eligible_descendant_slots']==14 and pre['unavailable_descendant_slots']==70,'first4_closed_predecessor_required')
 terminal=read(pre['supervisor_terminal']);verified=read(pre['verified_outcomes']);summary=read(pre['final_batch_summary']);snapshot=read(pre['closed_ledger_snapshot'])
 require(terminal['schema_version']=='p8-first4-supervisor-terminal-v1' and terminal['status']=='complete' and terminal['stop_reason'] is None and terminal['native_accounting_drain_verified'] is True and terminal['child_process_terminal'] is True and terminal['verified']==pre['verified_outcomes'],'first4_not_known_terminal')
 require(verified['native']['summary']==pre['final_batch_summary'] and verified['native']['attempted_calls']==4 and verified['native']['ledger_attempts']==284 and verified['native']['ledger_spent_nanos']==3260300000,'first4_accounting_binding_mismatch')
 require(summary['status']=='complete' and summary['stop_reason'] is None and summary['ledger']['attempts']==284 and Decimal(str(summary['ledger']['spent_usd']))==Decimal('3.26030') and summary['ledger']['uncertain']==summary['ledger']['inflight']==summary['ledger']['reserved_usd']==0 and summary['ledger']['held_after_uncertain'] is False,'first4_unknown_or_changed_accounting')
 require(snapshot['attempts']==284 and snapshot['known_spent_nanos']==3260300000,'first4_snapshot_baseline_mismatch')
 _,policy,current,configuration,_=p.validate_authority(FIRST4_AUTHORITY)
 require(Path(snapshot['source_path']).resolve()==Path(policy['ledger']['path']).resolve(),'first4_wrong_ledger')
 baseline=a.validate_baseline(current,snapshot,initial=False)
 if initial:require(current['reservation_rows']==snapshot['reservation_rows'],'new_attempts_since_first4_snapshot')
 h.budget_gate(current,TOTAL if initial else 0)
 return auth,policy,current,configuration,baseline

def prepare(authority,proposal_ref,destination):
 auth,policy,state,configuration,baseline=validate_authority(authority,initial=True);require(auth['proposal']==proposal_ref,'authority_proposal_mismatch');row=capture();require(row==read(proposal_ref)['draft'],'captured_requests_changed');h.time_gate(datetime.now(timezone.utc),900);driver=p.runtime()
 from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
 def forbidden(*args,**kwargs):raise RuntimeError('preparation_forbids_provider_or_ledger_access')
 class IdentityLedger(DollarLedger):
  def __init__(self,path,*,max_usd,deadline,max_inflight):
   require(Path(path).resolve()==Path(policy['ledger']['path']).resolve() and max_usd==80 and deadline==DEADLINE and max_inflight==2,'wrong_ledger_spec');self.path=Path(path);self.deadline=datetime(2026,11,15,17,tzinfo=timezone.utc);self.configuration=configuration
  _connect=reserve=finish=summary=forbidden
 urllib.request.urlopen=forbidden;OpenAIResponsesBackend.complete=forbidden;driver.DollarLedger=IdentityLedger;ledger=IdentityLedger(path=policy['ledger']['path'],max_usd=80,deadline=DEADLINE,max_inflight=2)
 template=read({'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'})
 batch={k:copy.deepcopy(template[k]) for k in ('schema_version','campaign_id','code_sha','runtime_root','deadline','max_workers','release_schema_version','release_scope','contract','env_file','roots')};batch.update(ledger=policy['ledger'],ledger_policy=POLICY,max_total_attempts=14,jobs=[],primary14_authority=authority,primary14_proposal=proposal_ref,primary14_predecessor=PREDECESSOR)
 packet=bind(read(DRAFT),authority);driver._prepare_packet(packet,batch,ledger);jid=packet['manifest']['job_id'];require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'primary14_job_already_started')
 out=Path(destination).resolve();driver._outside_git(str(out));require(not out.exists(),'fresh_preparation_directory_required');out.mkdir(parents=True);pr=write(out/'packet.json',packet);batch['jobs']=[pr]
 evidence=write(out/'admission-evidence.json',{'proposal':proposal_ref,'authority':authority,'baseline':baseline,'original_draft':DRAFT,'bound_packet':pr,'job_id':jid,'requests':row['requests'],'only_changed_fields':['lease','manifest.job_id','manifest.allocation.authorization_source'],'scientific_fields_unchanged':True,'api_calls':0,'ledger_writes':0});batch['admission_evidence']=evidence
 raw=write(out/'batch.json',batch);prepared=driver.publish_prepared(driver.prepare_batch(raw['path'],raw['sha256']));loaded=driver.load_prepared(prepared['path'],prepared['sha256']);require([j['manifest']['job_id'] for j in loaded['jobs']]==[jid],'published_job_changed');validate_authority(authority,initial=True);driver.verify_runtime(R,COMMIT)
 return write(out/'ready-index.json',{'schema_version':'p8-primary14-admission-index-v1','state':'prepared_not_executed','script':ref(__file__),'proposal':proposal_ref,'authority':authority,'policy':POLICY,'predecessor':PREDECESSOR,'bindings':BINDINGS,'unknown_denylist':DENY,'baseline':baseline,'prepared':prepared,'evidence':evidence,'jobs':1,'max_calls':14,'max_usd':TOTAL,'planned_descendant_slots':84,'unavailable_descendant_slots':70,'api_calls':0,'ledger_writes':0,'global_claims_created':0,'automatic_followup':False})
def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True);q=sub.add_parser('proposal');q.add_argument('--destination',required=True);q=sub.add_parser('prepare');q.add_argument('--destination',required=True);q.add_argument('--authority',nargs=2,required=True);q.add_argument('--proposal',nargs=2,required=True);args=ap.parse_args()
 if args.mode=='proposal':
  row=capture();out=Path(args.destination).resolve();require(not out.exists(),'fresh_proposal_directory_required');out.mkdir(parents=True)
  result=write(out/'proposal.json',{'schema_version':'p8-primary14-offline-proposal-v1','state':'no_execution_authority_or_admission','script':ref(__file__),'bindings':BINDINGS,'predecessor':PREDECESSOR,'unknown_denylist':DENY,'runtime_commit':COMMIT,'policy':POLICY,'draft':row,'max_calls':14,'max_usd':TOTAL,'max_inflight':2,'deadline':DEADLINE,'job_schedule_seconds':900,'deadline_margin_seconds':600,'planned_descendant_slots':84,'unavailable_descendant_slots':70,'api_calls':0,'ledger_connections':0,'native_admissions':0,'automatic_followup':False})
 else:result=prepare({'path':str(Path(args.authority[0]).resolve()),'sha256':args.authority[1]},{'path':str(Path(args.proposal[0]).resolve()),'sha256':args.proposal[1]},args.destination)
 print(canonical(result))
if __name__=='__main__':main()
