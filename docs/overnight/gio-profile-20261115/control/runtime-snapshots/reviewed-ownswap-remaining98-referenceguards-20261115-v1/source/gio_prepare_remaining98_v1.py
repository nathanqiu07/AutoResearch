"""Exact seven frozen P7/P3 joint-prediction drafts; requires known ownswap closure before admission."""
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
p=load('remaining98_native_helpers',P8);a,h=p.a,p.h
B,R,COMMIT,DEADLINE,POLICY=p.B,p.R,p.COMMIT,p.DEADLINE,p.POLICY
read,ref,require,write,canonical,digest=p.read,p.ref,p.require,p.write,p.canonical,p.digest
BINDINGS={'path':'/private/tmp/gio-profile-20261115-scaling/remaining8-valid-descendants-v1-j6dcoyqb/remaining8-ready-index.json','sha256':'91299be67bd68c21377d44f05f5fdafe5d020e968ec2607a0e485728633e274b'}
PREDECESSOR={'path':str(B/'accounting/remaining8-closed-predecessor-v1.json'),'sha256':'dcb4f58e868a343465367529dc033465dc937e527054f18eeae1f40d9c25728b'}
DENY={'path':'/private/tmp/gio-reference31-unknown-denylist-successor-v1/typed-denylist.json','sha256':'7e1dc77d77feb53d0b9d6327260fa4086447b4f96eccd05dc8a4a513104c4ffe'}
OWN_VERIFIER={'path':'/private/tmp/gio_verify_ownswap_terminal_v1.py','sha256':'368824c7ebc6985d0b07b2605d8515fcd17b3413ca3f12c454bcce9935e917c5'}
TEMPLATE={'path':str(B/'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),'sha256':'337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'}
OWN_GATE={'path':str(B/'accounting/ownswap-completed-gate-v1.json'),'sha256':'60959088449ede64759c08b255c4c576f8410554275c331a80448b3d1e4f0a29'}
SCOPE='remaining-p7-p3-joint98-only';TOTAL='26.589370'
def original_rows():
 index=read(BINDINGS);rows=index['ready_prediction_packets'];require(len(rows)==7 and [r['method_id'] for r in rows]==['P7']*4+['P3']*3,'exact_seven_drafts_required');return rows

def bind(draft,authority):
 require(sum(draft==read(r['packet']) for r in original_rows())==1,'only_exact_original_prediction_drafts');m=draft['manifest'];require(draft['lease'] is None and m.get('job_id') is None and m['allocation']['authorization_source'] is None,'only_unleased_drafts')
 v=copy.deepcopy(draft);v['manifest']['allocation']['authorization_source']={'policy':POLICY,'remaining98_authority':authority,'scope':SCOPE,'bindings':BINDINGS,'predecessor':PREDECESSOR,'unknown_denylist':DENY};jid=h.semantic_id(v['manifest']);v['manifest']['job_id']=jid;v['lease']={'job_id':jid,'lease_id':digest({'job_id':jid,'authority':authority,'scope':SCOPE}),'owner':'gio-overnight-00','expires_at':DEADLINE};restored=copy.deepcopy(v);restored['lease']=None;restored['manifest'].pop('job_id');restored['manifest']['allocation']['authorization_source']=None;require(restored==draft,'scientific_draft_changed');return v

def capture_rows():
 driver=p.runtime();index=read(BINDINGS);counts=index['counts'];require(index['runtime_sha']==COMMIT and index['execution_authorized'] is False and index['closed_predecessor']==PREDECESSOR and counts['new_planned_joint_A_rows']==112 and counts['new_unavailable_invalid_parent_rows']==14 and counts['new_unleased_ready_rows']==counts['new_prediction_call_ceiling']==98,'frozen_denominator_or_runtime_changed')
 from autoresearch.taste.overnight.contracts import ProfileArtifact
 from autoresearch.taste.overnight.consumer import prepare_payload
 rows=[];deny=read(DENY)['identity_denylists']
 for original in original_rows():
  d=read(original['packet']);m,b,c=d['manifest'],d['backend'],d['config'];profile=ProfileArtifact.from_dict(read(d['profile']));release=read(d['release']);items=release['items']
  require(d['lease'] is None and m.get('job_id') is None and m['allocation']['authorization_source'] is None and m['kind']=='predict' and m['method_id']==original['method_id'] and m['personalization_cap']==8192 and m['replicate_id']==0 and m['code_sha']==COMMIT and m['deadline']==DEADLINE and m['scaling_studies']==['A'],'original_selected_joint_cell_required')
  require(profile.status=='complete' and profile.profile_id==m['profile_hash']==original['profile_id'] and profile.researcher_id==original['researcher_id'] and b['model']==original['consumer']==original['extractor'] and b['model'] in ('gpt-6-sol','gpt-6-astra') and b['reasoning']=='medium' and b['timeout']==60 and b['max_calls']==14 and b['max_seconds']==900 and c['settings']=={'temperature':0.0,'max_tokens':8192},'frozen_profile_or_settings_changed')
  require([i['item_id'] for i in items]==d['item_ids'] and len(items)==14 and digest(items)==m['items_hash'] and digest(c)==m['config_hash'],'target_order_or_config_changed')
  if m['method_id']=='P7':driver._peer_release(release,'P7',c)
  requests=[]
  for item,pin in zip(items,original['request_pins']):
   payload=prepare_payload(profile,item['context'],item['options'],c);body={'model':b['model'],'instructions':payload['system'],'input':payload['prompt'],'max_output_tokens':8192,'reasoning':{'effort':'medium'},'store':False,'service_tier':'default','prompt_cache_options':{'mode':'implicit','ttl':'30m'}};wire=json.dumps(body,ensure_ascii=False,allow_nan=False).encode();input_rate,output_rate=(Decimal('2.5'),Decimal(10)) if b['model']=='gpt-6-sol' else (Decimal('12.5'),Decimal(50));info={'item_id':item['item_id'],'item_sha256':digest(item),'request_sha256':digest(body),'endpoint_body_sha256':hashlib.sha256(json.dumps({'endpoint':'https://api.openai.com/v1/responses','body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'wire_bytes_sha256':hashlib.sha256(wire).hexdigest(),'input_token_upper_bound':len(wire)+1024,'max_usd_reservation':str((Decimal(len(wire)+1024)*input_rate+8192*output_rate)/1000000)}
   require(info['request_sha256']==pin['wire_request_sha256'] and info['wire_bytes_sha256']==pin['wire_bytes_sha256'] and info['item_sha256']==pin['item_sha256'] and info['item_id']==pin['item_id'] and info['input_token_upper_bound']==pin['input_token_upper_bound'] and Decimal(info['max_usd_reservation'])==Decimal(str(pin['max_usd_reservation'])),'native_frozen_request_changed');require(info['input_token_upper_bound']+8192<272000,'short_context_bound_exceeded');p.reject_unknown(info,deny);requests.append(info)
  total=sum(Decimal(x['max_usd_reservation']) for x in requests);require(len(requests)==len(original['request_pins'])==14 and total==Decimal(str(b['max_usd']))==Decimal(str(original['max_usd_reservation'])),'job_request_count_or_ceiling_changed');rows.append({'packet':original['packet'],'method_id':m['method_id'],'researcher_id':profile.researcher_id,'model':b['model'],'manifest_sha256':digest(m),'profile':d['profile'],'release':d['release'],'release_schema_version':release['schema_version'],'requests':requests,'max_calls':14,'max_usd':str(total),'max_seconds':900})
 require(len({r['request_sha256'] for row in rows for r in row['requests']})==98 and sum(Decimal(x['max_usd']) for x in rows)==Decimal(TOTAL),'aggregate_requests_or_ceiling_changed');return rows

def batch_blocks(rows):
 require(len(rows)==7 and [r['method_id'] for r in rows]==['P7']*4+['P3']*3,'fixed_batch_order_required');result=[]
 for method,subset,schema,calls,cost in [('P7',rows[:4],'released-development-v2-p7-peers-v1',56,'16.456650'),('P3',rows[4:],'released-development-v2',42,'10.132720')]:
  require(all(r['release_schema_version']==schema for r in subset) and sum(Decimal(r['max_usd']) for r in subset)==Decimal(cost),'homogeneous_batch_or_ceiling_mismatch');result.append({'block':method,'rows':subset,'release_schema_version':schema,'jobs':len(subset),'max_calls':calls,'max_usd':cost,'two_slot_job_budget_schedule_seconds':1800})
 return result

def ownswap_gate(gate_ref):
 gate=read(gate_ref);require(gate_ref==OWN_GATE and gate.get('schema_version')=='ownswap-completed-gate-v1' and gate.get('state')=='complete','known_ownswap_dispatcher_gate_required');proof=read(gate['terminal_verification']);snapshot=read(gate['closed_ledger_snapshot'])
 require(proof.get('schema_version')=='own-swapped-terminal-verification-v1' and proof.get('state')=='complete_known_accounting' and proof.get('verifier')==OWN_VERIFIER and ref(OWN_VERIFIER['path'])==OWN_VERIFIER and proof['native']['attempted_calls']==proof['native']['ledger_attempts']==28 and proof['old_scaling_ledger_unchanged']=={'attempts':306,'known_spent_nanos':3883810000},'ownswap_terminal_proof_mismatch');closure=proof['dedicated_ledger_closure'];require(closure['attempts']==28 and closure['pending']==closure['uncertain']==closure['retained_hold_nanos']==0 and closure['known_spent_nanos']==proof['native']['known_spent_nanos']==proof['native']['ledger_spent_nanos'],'ownswap_accounting_incomplete')
 terminal=read(proof['diagnostics']['terminal']);require(terminal['status']=='complete' and terminal['entry_exit_code']==terminal['wrapper_exit_code']==0 and terminal['event_count']==28 and not any(terminal['diagnostics'].get(k,False) for k in ('diagnostic_write_failed','diagnostic_close_failed','diagnostic_hash_failed')) and terminal['diagnostics']['dropped_event_count']==0,'ownswap_diagnostics_not_known_terminal')
 policy=read(proof['policy']);require(policy['ledger']=={'path':str(B/'ledger/profile-ownswap-v1.sqlite'),'max_usd':1,'max_inflight':2},'ownswap_dedicated_policy_changed');current=h.ledger_read(policy['ledger']['path']);require(Path(snapshot['source_path']).resolve()==Path(policy['ledger']['path']).resolve() and current['policy_rows']==snapshot['policy_rows'] and current['reservation_rows']==snapshot['reservation_rows'] and digest({'policy_rows':current['policy_rows'],'reservation_rows':current['reservation_rows']})==snapshot['logical_snapshot_sha256']==closure['logical_snapshot_sha256'],'ownswap_closed_ledger_changed');require(current['attempts']==snapshot['attempts']==28 and current['known_nanos']==snapshot['known_spent_nanos']==closure['known_spent_nanos'] and current['pending']==current['uncertain']==current['held_nanos']==0 and all(r[3]=='complete' for r in current['reservation_rows']),'ownswap_has_unresolved_or_new_attempts');return {'gate':gate_ref,'terminal_verification':gate['terminal_verification'],'closed_ledger_snapshot':gate['closed_ledger_snapshot'],'known_spent_nanos':current['known_nanos']}

def validate_authority(authority,*,initial=False):
 auth=read(authority);require(auth.get('schema_version')=='remaining98-prediction-authorization-v1' and auth.get('state')=='authorized' and bool(auth.get('authority')) and auth.get('scope')==SCOPE,'root_remaining98_authority_required')
 require(auth.get('ownswap_completed_gate')==OWN_GATE and auth.get('policy')==POLICY and auth.get('bindings')==BINDINGS and auth.get('predecessor')==PREDECESSOR and auth.get('unknown_denylist')==DENY and auth.get('runtime_commit')==COMMIT and auth.get('deadline')==DEADLINE and auth.get('max_inflight')==2 and auth.get('max_calls')==98 and Decimal(str(auth.get('max_usd')))==Decimal(TOTAL) and auth.get('planned_descendant_slots')==112 and auth.get('unavailable_descendant_slots')==14 and auth.get('historical_unknown_holds_released') is False,'remaining98_authority_binding_mismatch')
 proposal=read(auth['proposal']);require(proposal['schema_version']=='remaining98-prediction-offline-proposal-v1' and proposal['script']==ref(__file__) and proposal['bindings']==BINDINGS and proposal['unknown_denylist']==DENY,'remaining98_proposal_mismatch');ownswap_gate(auth['ownswap_completed_gate'])
 pre=read(PREDECESSOR);terminal=read(pre['supervisor_terminal']);summary=read(pre['final_batch_summary']);snapshot=read(pre['closed_ledger_snapshot']);require(pre['state']=='complete' and terminal['status']=='complete' and terminal['stop_reason'] is None and terminal['native_accounting_drain_verified'] is True and terminal['child_process_terminal'] is True and terminal['planned_jobs']==8 and len(terminal['completed_verified_batches'])==2 and summary['status']=='complete' and summary['stop_reason'] is None and summary['ledger']['attempts']==snapshot['attempts']==terminal['known_verified_attempts']==306 and snapshot['known_spent_nanos']==terminal['known_verified_spend_nanos']==3883810000,'remaining8_known_baseline_required')
 policy,current,configuration=h.validate_authority(POLICY,read(POLICY)['profile204_predecessor']);require(Path(snapshot['source_path']).resolve()==Path(policy['ledger']['path']).resolve(),'wrong_scaling_snapshot');baseline=a.validate_baseline(current,snapshot,initial=False)
 if initial:require(current['reservation_rows']==snapshot['reservation_rows'],'new_scaling_activity_since306_baseline')
 h.budget_gate(current,TOTAL if initial else 0);return auth,policy,current,configuration,baseline

def prepare(authority,proposal_ref,destination):
 auth,policy,state,configuration,baseline=validate_authority(authority,initial=True);require(auth['proposal']==proposal_ref,'authority_proposal_mismatch');proposal=read(proposal_ref);rows=capture_rows();require(rows==proposal['drafts'] and batch_blocks(rows)==proposal['blocks'],'frozen_capture_or_blocks_changed');h.time_gate(datetime.now(timezone.utc),3600);driver=p.runtime()
 from autoresearch.taste.overnight.backends import DollarLedger,OpenAIResponsesBackend
 def forbidden(*args,**kwargs):raise RuntimeError('preparation_forbids_provider_or_ledger_access')
 class IdentityLedger(DollarLedger):
  def __init__(self,path,*,max_usd,deadline,max_inflight):
   require(Path(path).resolve()==Path(policy['ledger']['path']).resolve() and max_usd==80 and deadline==DEADLINE and max_inflight==2,'wrong_ledger_spec');self.path=Path(path);self.deadline=datetime(2026,11,15,17,tzinfo=timezone.utc);self.configuration=configuration
  _connect=reserve=finish=summary=forbidden
 urllib.request.urlopen=forbidden;OpenAIResponsesBackend.complete=forbidden;driver.DollarLedger=IdentityLedger;ledger=IdentityLedger(path=policy['ledger']['path'],max_usd=80,deadline=DEADLINE,max_inflight=2);template=read(TEMPLATE);stages=[];ids=[]
 for block in proposal['blocks']:
  batch={k:copy.deepcopy(template[k]) for k in ('schema_version','campaign_id','code_sha','runtime_root','deadline','max_workers','release_schema_version','release_scope','contract','env_file','roots')};batch.update(release_schema_version=block['release_schema_version'],ledger=policy['ledger'],ledger_policy=POLICY,max_total_attempts=block['max_calls'],jobs=[],remaining98_authority=authority,remaining98_proposal=proposal_ref,remaining98_block=block['block'],remaining8_predecessor=PREDECESSOR,ownswap_completed_gate=auth['ownswap_completed_gate']);packets=[]
  for row in block['rows']:
   packet=bind(read(row['packet']),authority);driver._prepare_packet(packet,batch,ledger);jid=packet['manifest']['job_id'];require(not (B/'lease'/(jid+'.json')).exists() and not (B/'output'/jid).exists(),'remaining98_job_already_started');packets.append(packet);ids.append(jid)
  stages.append((block,batch,packets))
 require(len(set(ids))==7,'duplicate_remaining98_job');out=Path(destination).resolve();driver._outside_git(str(out));require(not out.exists(),'fresh_preparation_destination');out.mkdir(parents=True);admissions=[]
 for block,batch,packets in stages:
  root=out/block['block'];root.mkdir();mappings=[]
  for n,(row,packet) in enumerate(zip(block['rows'],packets)):
   pr=write(root/('packet-%02d.json'%n),packet);batch['jobs'].append(pr);mappings.append({'original_draft':row['packet'],'bound_packet':pr,'job_id':packet['manifest']['job_id'],'requests':row['requests'],'only_changed_fields':['lease','manifest.job_id','manifest.allocation.authorization_source']})
  evidence=write(root/'admission-evidence.json',{'proposal':proposal_ref,'authority':authority,'baseline':baseline,'block':block['block'],'mappings':mappings,'scientific_fields_unchanged':True,'api_calls':0,'ledger_writes':0});batch['admission_evidence']=evidence;raw=write(root/'batch.json',batch);prepared=driver.publish_prepared(driver.prepare_batch(raw['path'],raw['sha256']));loaded=driver.load_prepared(prepared['path'],prepared['sha256']);require([j['manifest']['job_id'] for j in loaded['jobs']]==[v['manifest']['job_id'] for v in packets],'published_order_changed');admissions.append({'block':block['block'],'prepared':prepared,'evidence':evidence,'release_schema_version':block['release_schema_version'],'jobs':block['jobs'],'max_calls':block['max_calls'],'max_usd':block['max_usd']})
 validate_authority(authority,initial=True);driver.verify_runtime(R,COMMIT)
 return write(out/'ready-index.json',{'schema_version':'remaining98-prediction-admission-index-v1','state':'prepared_not_executed','script':ref(__file__),'proposal':proposal_ref,'authority':authority,'policy':POLICY,'predecessor':PREDECESSOR,'bindings':BINDINGS,'unknown_denylist':DENY,'ownswap_completed_gate':auth['ownswap_completed_gate'],'baseline':baseline,'admissions':admissions,'jobs':7,'max_calls':98,'max_usd':TOTAL,'planned_descendant_slots':112,'unavailable_descendant_slots':14,'api_calls':0,'ledger_writes':0,'global_claims_created':0,'automatic_followup':False})

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True);q=sub.add_parser('proposal');q.add_argument('--destination',required=True);q=sub.add_parser('prepare');q.add_argument('--destination',required=True);q.add_argument('--authority',nargs=2,required=True);q.add_argument('--proposal',nargs=2,required=True);args=ap.parse_args()
 if args.mode=='proposal':
  rows=capture_rows();out=Path(args.destination).resolve();require(not out.exists(),'fresh_proposal_directory');out.mkdir(parents=True);result=write(out/'proposal.json',{'schema_version':'remaining98-prediction-offline-proposal-v1','state':'no_execution_authority_or_admission','script':ref(__file__),'bindings':BINDINGS,'predecessor':PREDECESSOR,'unknown_denylist':DENY,'runtime_commit':COMMIT,'policy':POLICY,'drafts':rows,'blocks':batch_blocks(rows),'max_calls':98,'max_usd':TOTAL,'max_inflight':2,'deadline':DEADLINE,'two_slot_job_budget_schedule_seconds':3600,'deadline_margin_seconds':600,'planned_descendant_slots':112,'unavailable_descendant_slots':14,'ownswap_completed_gate':OWN_GATE,'ownswap_known_completion_required':True,'api_calls':0,'ledger_connections':0,'native_admissions':0,'automatic_followup':False})
 else:result=prepare({'path':str(Path(args.authority[0]).resolve()),'sha256':args.authority[1]},{'path':str(Path(args.proposal[0]).resolve()),'sha256':args.proposal[1]},args.destination)
 print(canonical(result))
if __name__=='__main__':main()
