"""Read-only exact own/swapped28 terminal verifier; emits metadata JSON, never scores or writes."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HELPER={'path':'/private/tmp/gio_prepare_ownswap_v2.py','sha256':'64a29533b85659292ef129dec4b52dc60b00971f09e7d6b284e489cad81bcdae'}
GATES={'path':'/private/tmp/gio_profile204_supervisor_v1.py','sha256':'67d526c126ff58d88305fc2f4ccdd2ee0278cf3d55d784716c53507398a973aa'}
WRAPPER={'path':'/private/tmp/gio_diagnostic_runtime_envelope_ownswap_v1.py','sha256':'f5efb857ca9b3954250acd620bf5c5f51ac1b7f6111b8424a7c52aeb5a49c10c'}
def load(name,r):
 p=Path(r['path'])
 if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('verifier_dependency_pin_mismatch')
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('ownswap_terminal_admission',HELPER);g=load('ownswap_terminal_common_gates',GATES);g.WRAPPER=WRAPPER
read,ref,require=h.read,h.ref,h.require

def verify_rows(manifest,items,result):
 assignment=manifest['profile_assignment'];rows=result['predictions'];require(result['profile_assignment']==assignment and len(rows)==len(items)==14,'assignment_or_row_denominator_mismatch')
 for item,row in zip(items,rows):
  require(row['item_id']==item['item_id'] and row['item_sha256']==h.digest(item) and row['items_sha256']==manifest['items_hash'] and row['job_id']==manifest['job_id'] and row['manifest_sha256']==h.digest(manifest),'prediction_input_binding_mismatch')
  require(row['donor_researcher_id']==assignment['donor_researcher_id'] and row['target_researcher_id']==assignment['target_researcher_id']==item['researcher_id'] and row['option_order_id']==item['option_order_id'] and row['profile_assignment_sha256']==h.digest(assignment) and row['actual_consumer']==manifest['consumer'],'prediction_assignment_provenance_mismatch')
  require(row['status'] in {'complete','invalid','unsupported','unavailable','empty','abstained'},'unknown_prediction_status')
 complete=sum(r['status']=='complete' for r in rows);require(result['counts']=={'attempted':14,'complete':complete,'error':14-complete},'prediction_status_accounting_mismatch')

def close_accounting(native,current):
 require(native['attempted_calls']==native['ledger_attempts']==current['attempts']==28 and native['known_spent_nanos']==native['ledger_spent_nanos']==current['known_nanos'] and 0<=current['known_nanos']<=1000000000,'dedicated28_accounting_mismatch')
 require(current['pending']==current['uncertain']==current['held_nanos']==0,'dedicated_study_has_unresolved_accounting')

def checked_bytes(r):
 read(r);raw=Path(r['path']).read_bytes();require(hashlib.sha256(raw).hexdigest()==r['sha256'],'evidence_changed_while_reading');return raw

def verify(index_ref,envelope_ref):
 index=read(index_ref);require(index['schema_version']=='own-swapped-native-admission-index-v2' and index['state']=='prepared_not_executed' and index['script']==HELPER and index['jobs']==2 and index['max_calls']==28 and index['max_usd']==1 and index['historical_alias_reexecutions']==0 and index['automatic_followup'] is False,'exact_ownswap_admission_index_required')
 auth,policy,current,_,baseline=h.validate_execution_authority(index['execution_authority'],initial=False)
 require(index['policy']==auth['policy'] and index['assignment_authority']==auth['assignment_authority'] and index['proposal']==auth['proposal'] and index['baseline']==baseline and index['unknown_denylist']==h.DENY and baseline['attempts']==baseline['spent']==0 and baseline['closed_scaling_attempts']==306,'admission_authority_or_baseline_mismatch')
 h.runtime();g.POLICY=auth['policy'];proposal=read(index['proposal']);drafts,metadata=h.make_drafts();require(metadata==proposal['request_metadata'] and len(proposal['drafts'])==2 and all(read(r)==p for r,p in zip(proposal['drafts'],drafts)),'frozen_drafts_or_wires_changed')
 batch=read(index['prepared']);require(batch['code_sha']==h.COMMIT and Path(batch['runtime_root']).resolve()==h.R and batch['ledger']==policy['ledger'] and batch['ledger_policy']==auth['policy'] and batch['max_workers']==2 and batch['max_total_attempts']==28 and len(batch['jobs'])==2 and batch['ownswap_execution_authority']==index['execution_authority'] and batch['ownswap_assignment_authority']==index['assignment_authority'],'native_batch_allocation_mismatch')
 from autoresearch.taste.overnight import cross_subject_assignment as assignment_validator
 from autoresearch.taste.overnight.contracts import ProfileArtifact
 allowed={r['request_sha256']:r['endpoint_body_sha256'] for row in metadata for r in row['requests']};require(len(allowed)==28,'unique_swap_request_count_changed');packets=[];provenance=[]
 for pr,draft in zip(batch['jobs'],drafts):
  packet=read(pr);expected=h.bind(draft,index['assignment_authority']);normalized=dict(packet)
  for key in ('release','profile','profile_source_release','assignment_binding','assignment_authority'):
   require(packet[key]['sha256']==expected[key]['sha256'] and checked_bytes(packet[key])==checked_bytes(expected[key]),'snapshotted_assignment_evidence_changed');normalized[key]=expected[key]
  require(normalized==expected,'native_scientific_packet_changed');m=packet['manifest'];release=read(packet['release']);donor=read(packet['profile_source_release']);items=release['items'];profile=ProfileArtifact.from_dict(read(packet['profile']))
  evidence={'binding':checked_bytes(packet['assignment_binding']),'authority':checked_bytes(packet['assignment_authority']),'target_release':checked_bytes(packet['release']),'donor_release':checked_bytes(packet['profile_source_release']),'profile':checked_bytes(packet['profile'])};assignment=assignment_validator.validate_assignment(m,packet['config'],profile,items,donor['sources']['documents'],evidence)
  claim_ref=ref(h.B/'lease'/(m['job_id']+'.json'));claim=read(claim_ref);require(claim['status']=='claimed' and claim['manifest']==m and claim['lease']==packet['lease'],'native_claim_assignment_mismatch');packets.append((packet,items));provenance.append({'job_id':m['job_id'],'donor_researcher_id':assignment['donor_researcher_id'],'target_researcher_id':assignment['target_researcher_id'],'profile_assignment_sha256':h.digest(assignment),'profile':packet['profile'],'donor_release':packet['profile_source_release'],'target_release':packet['release'],'claim':claim_ref})
 assignment_validator.validate_assignment_batch([{'manifest':p['manifest']} for p,_ in packets],28)
 native=g.native_terminal(index['prepared'],2,28);close_accounting(native,current);capture={(r['target_researcher_id'],r['item_id']):r for r in read(h.CAPTURE)['swapped_slots']}
 for (packet,items),record,identity in zip(packets,native['receipts'],provenance):
  m=packet['manifest'];receipt=read(record['receipt']);result=read(record['result']);require(receipt['usage']['attempted_calls']==14 and receipt['usage']['cache_hits']==0,'each_swap_requires14_fresh_known_requests');verify_rows(m,items,result)
  require(result['code_sha']==h.COMMIT and result['config_hash']==m['config_hash'] and result['source_manifest_hash']==m['source_manifest_hash'] and result['profile_hash']==m['profile_hash'] and result['actual_backend']==m['consumer'],'result_source_profile_or_backend_provenance_mismatch')
  for row in result['predictions']:
   expected=capture[(identity['target_researcher_id'],row['item_id'])];require(row['payload_sha256']==expected['payload_sha256'] and row['rendered_profile_sha256']==expected['rendered_profile_sha256'],'executed_payload_provenance_mismatch')
  identity.update(receipt=record['receipt'],result=record['result'],counts=result['counts'],status=result['status'])
 envelope=read(envelope_ref);require(ref(WRAPPER['path'])==WRAPPER and envelope['script_sha256']==WRAPPER['sha256'] and envelope['runtime_commit']==h.COMMIT and Path(envelope['runtime_root']).resolve()==h.R and envelope['inputs']=={'batch':index['prepared']} and envelope['authorization']==index['execution_authority'] and envelope['denylist']==h.DENY,'executed_envelope_binding_mismatch')
 diagnostics=g.diagnostic_terminal(envelope_ref,ref(Path(envelope['output_root'])/'envelope-terminal.json'),allowed,28)
 identities=[]
 for row in current['reservation_rows']:
  require(row[3]=='complete' and type(row[2]) is int and 0<=row[2]<=row[1],'ledger_row_not_known_complete');meta=json.loads(row[4]);require(meta['model']=='gpt-6-luna' and meta['reasoning']=='medium','ledger_model_or_reasoning_mismatch');identities.append(meta['request_sha256'])
 require(len(identities)==len(set(identities))==28 and set(identities)==set(allowed),'ledger_request_identity_set_mismatch')
 return {'schema_version':'own-swapped-terminal-verification-v1','state':'complete_known_accounting','verifier':ref(__file__),'index':index_ref,'execution_authority':index['execution_authority'],'assignment_authority':index['assignment_authority'],'policy':auth['policy'],'predecessor':auth['predecessor'],'native':native,'diagnostics':diagnostics,'assignment_provenance':provenance,'dedicated_ledger_closure':{'attempts':28,'known_spent_nanos':current['known_nanos'],'retained_hold_nanos':0,'pending':0,'uncertain':0,'logical_snapshot_sha256':h.digest({'policy_rows':current['policy_rows'],'reservation_rows':current['reservation_rows']})},'old_scaling_ledger_unchanged':{'attempts':306,'known_spent_nanos':baseline['closed_scaling_spent']},'historical_alias_reexecutions':0,'automatic_followup':False,'private_labels_read':False,'scores_computed':False,'ledger_writes':0}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ready-index',nargs=2,required=True);ap.add_argument('--envelope',nargs=2,required=True);a=ap.parse_args();print(h.canonical(verify({'path':str(Path(a.ready_index[0]).resolve()),'sha256':a.ready_index[1]},{'path':str(Path(a.envelope[0]).resolve()),'sha256':a.envelope[1]})))
if __name__=='__main__':main()
