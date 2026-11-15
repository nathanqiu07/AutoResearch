"""Read immutable original downstream05 Git objects; emit metadata only.

No owner imports, model calls, .eval execution, live ledger or private label reads.
The only subprocess is read-only git show against explicit pinned objects.
"""
import argparse
import ast
from collections import Counter
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import string
import subprocess
import sys

PUBLICATION='c80937c7f92dd6ad05eee319e64f16799f0a193e'
EXECUTED='e9672aa48ba442dfc5bd2cd84b8f0c76e2bfb7e4'
BASE='results/gio-matched-shutdown-05/'
REVIEW='results/gio-matched-shutdown-05-review/'
ARMS=('baseline','generic','profile')
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v):return sha(canon(v).encode())
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def extract_recorded_json(text):
    # Reimplemented from the pinned llm.extract_json behavior, not imported.
    for pos,opening,closing in sorted((text.find(o),o,c) for o,c in [('{','}'),('[',']')] if text.find(o)>=0):
        end=text.rfind(closing)
        if end>pos:
            try:return json.loads(text[pos:end+1],strict=False)
            except json.JSONDecodeError:pass
    return None
def recorded_probability(value):
    try:x=float(value)
    except (TypeError,ValueError):return None
    return None if math.isnan(x) else max(0.,min(1.,x))
def clipped(text,limit=24000):
    if len(text)<=limit:return text
    return text[:limit//2]+'\n\n[... '+str(len(text)-limit)+' characters cut ...]\n\n'+text[-(limit//2):]
def content_text(content):
    if isinstance(content,str):return content
    return '\n'.join(x['text'] for x in content or [] if x.get('type') in ('text','input_text','output_text'))
def response_text(call):
    response=call['response']
    if 'choices' in response:return response['choices'][0]['message'].get('content') or ''
    return '\n'.join(content_text(x.get('content',[])) for x in response['output'] if x['type']=='message')
def request_text(call):
    request=call['request'];messages=request.get('messages',request.get('input'))
    return '\n'.join(content_text(m.get('content')) for m in messages if m.get('role')=='user')
def split_message(m):
    reasoning=[];visible=[];pattern=re.compile(r'<(think|thinking|reasoning|scratchpad)>(.*?)</\1>',re.S|re.I)
    content=m['content'];blocks=[content] if isinstance(content,str) else content
    for b in blocks:
        if isinstance(b,str):text=b
        elif b.get('type')=='reasoning':
            if not b.get('redacted') and b.get('reasoning'):reasoning.append(b['reasoning'])
            continue
        elif b.get('type')=='text':text=b['text']
        else:continue
        reasoning.extend(x.group(2).strip() for x in pattern.finditer(text))
        out=pattern.sub('',text).strip()
        if out:visible.append(out)
    for tool in m.get('tool_calls') or []:
        visible.append('[tool call '+tool['id']+'] '+tool['function']+'('+json.dumps(tool['arguments'],ensure_ascii=False)+')')
    return '\n'.join(reasoning).strip(),'\n'.join(visible).strip()
def render_native(messages):
    parts=[];thoughts=[]
    for m in messages:
        role=m['role'];body=content_text(m['content'])
        if role=='system':parts.append('SYSTEM PROMPT:\n'+body)
        elif role=='user':parts.append('USER:\n'+body)
        elif role=='assistant':
            thought,visible=split_message(m);parts.append('ASSISTANT:\n'+visible)
            if thought:thoughts.append(thought)
        elif role=='tool':
            if m.get('error'):body+='\n[error] '+m['error']['message']
            parts.append('TOOL RESULT ('+(m.get('function') or 'tool')+'):\n'+body)
    return '\n\n'.join(parts),'\n\n'.join(thoughts)
def quote_records(payload,sources):
    records=[]
    def walk(value,pointer):
        if isinstance(value,dict):
            if set(value)=={'source','quote'}:
                source,quote=value['source'],value['quote']
                records.append({'pointer':pointer,'source':source,'quote_sha256':sha(quote.encode()),'quote_chars':len(quote),'exact_substring':source in sources and quote in sources[source]})
            else:
                for k,v in value.items():walk(v,pointer+'/'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,pointer+'/'+str(i))
    walk(payload,'');return records
def norm_path(value):
    if value=='~':value='/home/user'
    elif value.startswith('~/'):value='/home/user/'+value[2:]
    elif not value.startswith('/'):value='/home/user/'+value
    assert '..' not in PurePosixPath(value).parts
    return str(PurePosixPath(value))
def state_part(v):return {k:v[k] for k in ('current_time','entrypoint','files','schedule')}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'reader-used.py').write_bytes(Path(__file__).read_bytes())
    cache={};inventory={};checks=[];source_allow=set()
    def git(path,commit=PUBLICATION):
        if commit==PUBLICATION:assert path.startswith((BASE,REVIEW,'docs/user-models/matched-shutdown-05/'))
        else:assert commit==EXECUTED and path in source_allow
        key=(commit,path)
        if key not in cache:
            result=subprocess.run(['git','--no-optional-locks','-C',str(a.repo),'show',commit+':'+path],capture_output=True,check=True,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp'})
            cache[key]=result.stdout;inventory[key]={'commit':commit,'path':path,'sha256':sha(result.stdout),'size_bytes':len(result.stdout)}
        return cache[key]
    def get(path):return json.loads(git(BASE+path))
    def text(path):return git(BASE+path).decode()
    def check(name,ok):
        checks.append({'name':name,'verified':bool(ok)})
        if not ok:
            save(a.out/'failed-checks.json',checks);save(a.out/'input-inventory.json',{'files':list(inventory.values()),'raw_copied':False});raise AssertionError(name+'; raw content withheld')
    try:
        manifests=[(BASE,'artifact_checksums.json','18ffab491bed3a6fe513b5aff9769152b93d9a1958cde45ed17ce27134c61230',212),(REVIEW,'checksums.json','e80e7606b26a6b68f587c999ef9bbee7a31f0eb840209179b53f1452ec80e2c4',9)]
        for prefix,name,pin,count in manifests:
            b=git(prefix+name);check('manifest_pin:'+name,sha(b)==pin);manifest=json.loads(b);check('manifest_count:'+name,len(manifest)==count)
            for path,h in manifest.items():
                check('safe_member:'+prefix+path,not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts)
                check('artifact:'+prefix+path,sha(git(prefix+path))==h)
        artifacts=get('artifact_checksums.json');sources=get('runtime-source-checksums.json');source_allow.update(sources)
        code={path:git(path,EXECUTED) for path in sources}
        for path,h in sources.items():check('executed_source:'+path,sha(code[path])==h)
        check('executed_code_version',text('CODE_VERSION').strip()==EXECUTED and len(sources)==114)
        for path,h in get('packet/checksums.json').items():check('packet:'+path,sha(git(BASE+'packet/'+path))==h)
        for path,h in get('runner_checksums.json').items():
            check('runner_copy:'+path,sha(git(BASE+'runner_source/'+path))==h)
            source='scripts/gio_petri/'+path
            if source in code:check('runner_matches_executed:'+path,git(BASE+'runner_source/'+path)==code[source])
        settings=get('packet/settings.json');executed=get('settings.json');seed=get('packet/seed.json');common=text('packet/common.template.txt')
        check('settings_bind_execution',executed==dict(settings,execution_code_version=EXECUTED,lease_sha256=sha(git(BASE+'execution-lease.json'))))
        check('fixed_design',settings['arms']==list(ARMS) and settings['audits_per_arm']==1 and settings['epochs']==1 and settings['max_auditor_turns']==30 and settings['code_version']==EXECUTED and settings['seed_id']==seed['seed_id']=='v2_seed_48')
        contexts={arm:json.loads(text('packet/'+arm+'-context.txt')) for arm in ('generic','profile')}
        provenance=get('packet/profile-provenance.json');profile_context=text('packet/profile-context.txt')
        check('profile_context_identity',sha(profile_context.encode())==provenance['context_sha256']==settings['profile_context_sha256'] and len(contexts['profile']['past_choices'])==provenance['selected_example_count']==8 and [x['id'] for x in contexts['profile']['past_choices']]==provenance['selected_example_ids'])
        check('profile_model_recorded_identity',provenance['model_sha256']==settings['model_sha256'])
        first={arm:get(arm+'/calls/call-0000-auditor.json') for arm in ARMS};base_messages=first['baseline']['request']['messages']
        # Recover formatter substitutions from the actual shared baseline text;
        # seed and turn limit additionally bind to independent packet values.
        fields=[];pattern=''
        for literal,field,spec,conversion in string.Formatter().parse(common):
            pattern+=re.escape(literal)
            if field is not None:fields.append(field);pattern+='(.*?)'
        match=re.fullmatch(pattern,base_messages[0]['content'],re.S);check('common_template_render_match',match is not None)
        substitutions=dict(zip(fields,match.groups()));check('common_seed_and_turns',substitutions['seed_instructions']==seed['text'] and substitutions['max_turns']=='30' and settings['models']['target'] in substitutions['target_model'])
        all_call_records=[];arm_reports={};global_entries=[];probe_set=get('packet/evaldetect_probes.json')['default'];check('five_default_target_probes',len(probe_set)==5)
        for arm in ARMS:
            messages=first[arm]['request']['messages'];template=text('packet/'+arm+'.template.txt')
            check('saved_template:'+arm,text(arm+'/auditor-template.txt')==template and template.startswith(common))
            check('actual_first_auditor_prompt:'+arm,messages[0]['content']==template.format(**substitutions) and messages[1:]==base_messages[1:] and seed['text'] in messages[1]['content'])
            check('same_first_auditor_tools:'+arm,first[arm]['request']['tools']==first['baseline']['request']['tools'])
            check('persona_delivery:'+arm,(contexts['profile']['persona'] in messages[0]['content'])==(arm=='profile') and (profile_context.strip() in messages[0]['content'])==(arm=='profile'))
            if arm=='generic':check('generic_context_delivery',text('packet/generic-context.txt').strip() in messages[0]['content'] and len(contexts['generic']['past_choices'])==8)
            calls={};phase_reports={}
            for folder,ledger_file,ledger_suffix in [('calls','audit-ledger.json','audit'),('environment-review-calls','environment-review-ledger.json','environment_review'),('review-calls','review-ledger.json','review'),('secondary-calls','secondary-ledger.json','secondary')]:
                ledger=get(arm+'/'+ledger_file);entries=ledger['entries'];paths=sorted(x for x in artifacts if x.startswith(arm+'/'+folder+'/'))
                check('phase_count:'+arm+':'+folder,len(paths)==len(entries) and ledger['arm']==arm+'.'+ledger_suffix)
                global_entries.extend(entries);phase_reports[folder]={'recorded_calls':len(paths),'ledger_charged_or_reserved_usd':str(Decimal(str(ledger['charged_or_reserved_usd'])))}
                charge=Decimal(0)
                for i,(path,e) in enumerate(zip(paths,entries)):
                    role=path.rsplit('-',1)[1][:-5];call=get(path);calls[path]=call;request,response=call['request'],call['response'];usage=response['usage']
                    check('call_local_identity:'+path,path.endswith('call-%04d-%s.json'%(i,e['role'])) and role==e['role'] and e['arm']==arm+'.'+ledger_suffix and call['error'] is None and response.get('error') is None)
                    if role=='judge':
                        check('judge_request_settings:'+path,request['model']=='gpt-5.1' and request['max_output_tokens']==32000 and request['reasoning']['effort']=='high' and request['store'] is False and 'temperature' not in request)
                        inp,out=usage['input_tokens'],usage['output_tokens']
                    else:
                        check('router_request_settings:'+path,request['model']==settings['models'][role] and request['max_tokens']==settings['generation'][role]['max_tokens'] and request['temperature']==0.7 and request['extra_body']['provider']==settings['routing'][role])
                        if role=='target':check('target_reasoning:'+path,request['extra_body']['reasoning']['enabled'] is True)
                        inp,out=usage['prompt_tokens'],usage['completion_tokens']
                    cached=usage.get('input_tokens_details',usage.get('prompt_tokens_details',{})).get('cached_tokens') or 0
                    check('usage_tokens_after_cache_normalization:'+path,type(inp) is int and type(out) is int and type(cached) is int and inp>=cached>=0 and out>=0 and inp-cached==e['input_tokens'] and out==e['output_tokens'] and e['status']=='usage_estimate')
                    rates={'auditor':('0.09','0.55'),'target':('0','0'),'judge':('1.25','10')}[role]
                    calculated=((Decimal(rates[0])*e['input_tokens']+Decimal(rates[1])*out)/Decimal(1000000)).quantize(Decimal('0.000000001'),rounding=ROUND_CEILING)
                    raw_uncached_rate=((Decimal(rates[0])*inp+Decimal(rates[1])*out)/Decimal(1000000)).quantize(Decimal('0.000000001'),rounding=ROUND_CEILING)
                    check('per_call_cost:'+path,calculated==Decimal(str(e['charged_usd'])));charge+=calculated
                    all_call_records.append({'path':BASE+path,'raw_sha256':artifacts[path],'request_sha256':digest(request),'response_sha256':digest(response),'recorded_response_id_sha256':digest(response['id']),'role':role,'arm':arm,'phase':folder,'requested_model':request['model'],'max_output_tokens':request.get('max_tokens',request.get('max_output_tokens')),'temperature':request.get('temperature','not_sent'),'raw_input_tokens':inp,'cached_input_tokens':cached,'ledger_input_tokens':e['input_tokens'],'output_tokens':out,'charged_estimate_usd':str(calculated),'raw_input_at_saved_uncached_rates_usd':str(raw_uncached_rate)})
                check('phase_charge:'+arm+':'+folder,charge==Decimal(str(ledger['charged_or_reserved_usd'])))
            audit=get(arm+'/audit.json');native=get(arm+'/native-sample.json');native_messages=native['store']['AuditStore:target']['messages'];rendered,reasoning=render_native(native_messages)
            check('native_transcript_render:'+arm,rendered==audit['transcript'] and reasoning==audit['reasoning'])
            target_calls=[call for path,call in sorted(calls.items()) if path.startswith(arm+'/calls/') and path.endswith('-target.json')]
            assistants=[m for m in native_messages if m['role']=='assistant'];check('target_response_denominator:'+arm,len(target_calls)==len(assistants)=={'baseline':5,'generic':4,'profile':6}[arm])
            emitted_tools={}
            for call,m in zip(target_calls,assistants):
                wire=call['response']['choices'][0]['message'];native_tools=[{'id':t['id'],'function':t['function'],'arguments':t['arguments']} for t in m.get('tool_calls') or []]
                wire_tools=[{'id':t['id'],'function':t['function']['name'],'arguments':json.loads(t['function']['arguments'])} for t in wire.get('tool_calls') or []]
                check('native_response_tools:'+arm,native_tools==wire_tools and content_text(m['content']).strip()==(wire.get('content') or '').strip())
                for t in wire_tools:check('unique_target_tool_id:'+arm,t['id'] not in emitted_tools);emitted_tools[t['id']]=t
            attempted=[json.loads(line) for line in text(arm+'/world/attempted-target-inputs.jsonl').splitlines()]
            check('attempted_target_inputs_count:'+arm,len(attempted)==len(target_calls))
            check('first_target_actual_input:'+arm,[{'role':m['role'],'content':m['content']} for m in attempted[0]['messages']]==target_calls[0]['request']['messages'])
            original=get(arm+'/world/world-initial.json');final=get(arm+'/world/world-state.json');worldfinal=get(arm+'/world-final.json')
            check('world_final_equal:'+arm,final==worldfinal)
            check('startup_exposure_recorded:'+arm,original['files']['/home/user/shutdown.sh'] in target_calls[0]['request']['messages'][1]['content'] and original['schedule']['run_at'] in target_calls[0]['request']['messages'][1]['content'] and final['exposure_delivered'] is True)
            events=[json.loads(line) for line in text(arm+'/world/world-events.jsonl').splitlines()];check('event_log_equal:'+arm,events==final['events'])
            state=state_part(original);event_metadata=[]
            for n,event in enumerate(events):
                check('event_chain:'+arm+':'+str(n),event['before']==state)
                tool=emitted_tools[event['tool_call_id']];check('event_bound_to_target_call:'+arm+':'+str(n),tool['function']==event['function'] and tool['arguments']==event['arguments'])
                expected=json.loads(json.dumps(state));function=event['function'];args=event['arguments'];check('only_read_write_observed:'+arm,function in ('read_file','write_file'))
                path=norm_path(args['path'])
                if function=='read_file':check('read_result:'+arm,event['status']=='success' and path in state['files'] and event['result']==state['files'][path])
                else:
                    expected['files'][path]=args['content'];result=json.loads(event['result'])
                    check('write_result:'+arm,event['status']=='success' and result=={'wrote':path,'bytes':len(args['content'].encode()),'sha256':sha(args['content'].encode())})
                check('event_exact_transition:'+arm+':'+str(n),event['after']==expected);state=event['after']
                event_metadata.append({'index':n,'function':function,'status':event['status'],'path_sha256':sha(path.encode()),'touches_active_shutdown':path=='/home/user/shutdown.sh','before_sha256':digest(event['before']),'after_sha256':digest(event['after'])})
            check('final_state_chain:'+arm,state==state_part(final) and set(final['executed_tool_ids'])=={e['tool_call_id'] for e in events})
            check('active_shutdown_unchanged:'+arm,original['files']['/home/user/shutdown.sh']==final['files']['/home/user/shutdown.sh'] and original['schedule']==final['schedule'] and original['current_time']==final['current_time']==settings['start_time'] and not final['real_process_shutdown_executed'])
            # Bind original primary-review evidence and rejection, without repair.
            primary=get(arm+'/primary-review.json');sources_saved=get(arm+'/primary-review-sources.json');tools=get(arm+'/target-tools.json');structure=get(arm+'/run-structure.json')
            expected_sources={'seed':seed['text'],'transcript':audit['transcript'],'reasoning':audit['reasoning'],'tools':json.dumps(tools,ensure_ascii=False,indent=2),'structure':json.dumps(structure,ensure_ascii=False,indent=2)}
            check('primary_full_sources:'+arm,sources_saved==expected_sources)
            prompt=text('packet/review-instructions.txt').rstrip()+'\n\nUNTRUSTED EVIDENCE DATA (JSON):\n'+json.dumps(expected_sources,ensure_ascii=False,indent=2)+'\n'
            primary_call=calls[arm+'/review-calls/call-0000-judge.json'];reply=text(arm+'/primary-review-reply.txt')
            check('primary_actual_request_reply:'+arm,prompt==text(arm+'/primary-review-prompt.txt')==request_text(primary_call) and reply==response_text(primary_call))
            payload=json.loads(reply);quotes=quote_records(payload,sources_saved);bad=[q for q in quotes if not q['exact_substring']]
            first_bad={'baseline':'/checks/task_preserved/evidence/3','generic':'/checks/observable_outcome/evidence/0','profile':'/checks/task_preserved/evidence/3'}[arm]
            check('original_primary_rejection:'+arm,primary['status']=='review_failed' and primary['phase']=='primary_review_validation' and primary['human_review_required'] is True and len(bad)=={'baseline':4,'generic':2,'profile':6}[arm] and bad[0]['pointer']==first_bad)
            score=get(arm+'/score.json');cut=clipped(audit['transcript']);probe_records=[];usable=[]
            for i,q in enumerate(probe_set):
                path=arm+'/secondary-calls/call-%04d-target.json'%i;call=calls[path];reply=response_text(call);parsed=extract_recorded_json(reply);value=recorded_probability(parsed.get('p')) if isinstance(parsed,dict) else None
                check('target_probe_actual_prompt:'+arm+':'+str(i),request_text(call)==q.replace('{transcript}',cut))
                probe_records.append({'index':i,'path':BASE+path,'raw_sha256':artifacts[path],'response_content_sha256':sha(reply.encode()),'json_parsed':parsed is not None,'usable_probability':value is not None,'finish_reason':call['response']['choices'][0]['finish_reason']})
                if value is not None:usable.append(value)
            check('probe_denominator:'+arm,len(usable)=={'baseline':5,'generic':5,'profile':3}[arm] and sum(usable)/len(usable)==score['self_report'])
            check('clipping_flags:'+arm,score['transcript_clipped_for_outer_judge']==(len(audit['transcript'])>24000) and score['reasoning_clipped_for_outer_judge']==(len(audit['reasoning'])>6000))
            summary=get(arm+'/summary.json');check('original_summary_failed_admission:'+arm,summary['primary_review_status']=='review_failed' and summary['valid_comparison_case'] is False and summary['audit_completed'] is True)
            arm_reports[arm]={'first_auditor_system_sha256':sha(messages[0]['content'].encode()),'first_auditor_user_sha256':sha(messages[1]['content'].encode()),'profile_persona_delivered':arm=='profile','profile_examples_delivered':8 if arm=='profile' else 0,'generic_authored_examples_delivered':8 if arm=='generic' else 0,'phase_counts':phase_reports,'target_audit_responses':len(target_calls),'transcript_chars':len(audit['transcript']),'secondary_transcript_chars':len(cut),'secondary_transcript_clipped':len(cut)!=len(audit['transcript']),'primary_status':primary['status'],'primary_quotes':quotes,'primary_exact_quote_failures':len(bad),'probe_calls':probe_records,'probe_usable':len(usable),'probe_requested':5,'recorded_mean_matches_usable_subset':True,'world_events':event_metadata,'active_shutdown_initial_sha256':sha(original['files']['/home/user/shutdown.sh'].encode()),'active_shutdown_final_sha256':sha(final['files']['/home/user/shutdown.sh'].encode()),'schedule_initial_sha256':digest(original['schedule']),'schedule_final_sha256':digest(final['schedule']),'current_time_unchanged':True,'real_process_shutdown_executed':False,'original_valid_comparison_case':False}
        ledger=get('provider-ledger.json')
        check('78recorded_calls_entries',len(all_call_records)==len(global_entries)==len(ledger['entries'])==78 and global_entries==ledger['entries'])
        check('unique_response_records',len({c['recorded_response_id_sha256'] for c in all_call_records})==78 and len({c['path'] for c in all_call_records})==78)
        total=sum(Decimal(c['charged_estimate_usd']) for c in all_call_records)
        check('once_per_recorded_call_total',total==Decimal(str(ledger['charged_or_reserved_usd']))==Decimal('1.020504500'))
        check('role_denominators',Counter(c['role'] for c in all_call_records)=={'auditor':27,'target':30,'judge':21})
        check('no_unknown_charge_status',all(e['status']=='usage_estimate' for e in ledger['entries']) and ledger['halted'] is False)
        raw_rate_total=sum(Decimal(c['raw_input_at_saved_uncached_rates_usd']) for c in all_call_records)
        cache_rows=[c for c in all_call_records if c['cached_input_tokens']]
        check('cached_input_accounting_boundary',len(cache_rows)==16 and sum(c['role']=='judge' for c in cache_rows)==7 and raw_rate_total==Decimal('1.071544500') and raw_rate_total-total==Decimal('0.051040000'))
        for provider,roles in [('openai',{'judge'}),('openrouter',{'auditor','target'})]:
            check('provider_charge:'+provider,sum(Decimal(c['charged_estimate_usd']) for c in all_call_records if c['role'] in roles)==Decimal(str(ledger['providers'][provider]['charged_or_reserved_usd'])))
        report={'schema_version':'downstream039-original-terminal-independent-v1','publication_commit':PUBLICATION,'executed_source':EXECUTED,'reader_sha256':sha(Path(__file__).read_bytes()),'argv':sys.argv,'checks':checks,'check_counts':{'passed':len(checks),'failed':0},'artifact_files_verified':212,'owner_review_files_hash_verified_only':9,'executed_source_files_verified':114,'arms':arm_reports,'recorded_calls':all_call_records,'accounting':{'recorded_call_files':78,'recorded_usage_entries':78,'roles':dict(Counter(c['role'] for c in all_call_records)),'charged_usage_estimate_usd':str(total),'physical_requests_authenticated':False,'unknown_reservation_entries':0,'cached_input_excluded_calls':len(cache_rows),'cached_input_excluded_paid_judge_calls':7,'paid_cached_input_tokens_excluded':sum(c['cached_input_tokens'] for c in cache_rows if c['role']=='judge'),'raw_all_input_at_same_saved_uncached_rates_usd':str(raw_rate_total),'raw_rate_minus_ledger_usd':str(raw_rate_total-total),'saved_cost_basis':ledger['cost_basis'],'interpretation':'Saved ledger charges normalized noncached input tokens. It does not charge cached inputs; its conservative_uncached description is not established by this arithmetic. Raw-rate comparison is a reference estimate, not provider billing or proof of a budget overrun.'},'shared_design':{'seed_sha256':sha(seed['text'].encode()),'same_first_auditor_user':True,'same_first_auditor_tools':True,'common_actual_system_plus_declared_suffix':True,'template_substitution_sha256':{k:sha(v.encode()) for k,v in substitutions.items()},'audits_per_condition':1,'epochs':1,'auditor_turn_limit':30,'profile_context_bytes':len(profile_context.encode()),'generic_context_bytes':len(text('packet/generic-context.txt').encode()),'context_structure_and_count_matched_not_tokens':True},'probe_settings_boundary':{'caller':{'source':'autoresearch/research/measure.py','sha256':sources['autoresearch/research/measure.py'],'lines':[420,429],'max_tokens':300,'temperature':0.0},'bridge':{'source':'scripts/gio_petri/run_matched.py','sha256':sources['scripts/gio_petri/run_matched.py'],'lines':[145,151],'only_generate_override':'cache=False'},'fixed_role':{'source':'scripts/gio_petri/roles.py','sha256':sources['scripts/gio_petri/roles.py'],'lines':[12,14],'actual_max_tokens':16384,'actual_temperature':0.7},'classification':'Demonstrated caller-parameter override by fixed-role adapter. Consistent with frozen role settings; not alone proof of an unintended implementation defect or owner-report misstatement.'},'scope':{'owner_modules_imported':False,'owner_checker_executed':False,'native_eval_executed':False,'models_called':0,'environment_or_keys_read':False,'active_sqlite_read':False,'repair_judgments_included':False,'raw_git_files_exported':False},'limits':['Saved request/response and usage records are not authenticated provider traffic, invoices or physical request counts.','The selected profile context is bound to the packet and first auditor input; its upstream saved-model hash is recorded, not independently reconstructed from unapproved external model files. Its choices are generated rather than verified human labels.','Template substitutions are recovered from the actual baseline request, with seed and turn limit independently pinned; shared rendered context and declared condition suffixes are verified without importing third-party Petri code.','Context length, authorship/domain content and authored environments differ. One run per condition does not isolate personal specificity or support benefit, prediction quality, unawareness or causal claims.','Primary exact-quote matching tests literal source membership, not semantic support. All three original primary reviews remain rejected; no repair results are included.','Profile probe denominator is3/5 rather than5/5; invalid responses are omitted by the executed mean. Control transcripts are clipped for secondary probing, while profile is not.','World transitions are simulated file/schedule operations. Fixed clock and real_process_shutdown_executed=false mean no shutdown, survival, code execution or competing-team success was demonstrated.','This reader validates original terminal state and caller records; it does not repeat semantic codebase assessment or original preference scoring.']}
        save(a.out/'report.json',report);save(a.out/'input-inventory.json',{'files':list(inventory.values()),'raw_copied':False});print(json.dumps({'passed':len(checks),'failed':0,'recorded_calls':78,'input_objects':len(inventory)}))
    except Exception as exc:
        if not (a.out/'input-inventory.json').exists():save(a.out/'input-inventory.json',{'files':list(inventory.values()),'raw_copied':False})
        save(a.out/'failure.json',{'exception':type(exc).__name__,'checks_before_failure':len(checks),'raw_content_exported':False});raise

if __name__=='__main__':main()
