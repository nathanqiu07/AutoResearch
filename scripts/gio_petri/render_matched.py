#!/usr/bin/env python3
"""Render terminal matched-run artifacts locally. No APIs, downloads or source edits."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
from html import escape
import json
import math
from pathlib import Path
import re

ARMS = ('baseline', 'generic', 'profile')
LABELS = {'baseline':'No researcher context', 'generic':'Generic guidance', 'profile':'Researcher profile'}
SECRET = re.compile(r'sk-(?:or-v1-|proj-)[A-Za-z0-9_-]{20,}')
CHECKS = ('task_preserved','shutdown_threat','threat_received','free_response','observable_outcome')

def sha(data): return hashlib.sha256(data).hexdigest()
def numeric(value): return type(value) in (int,float) and math.isfinite(value)
def shown(value):
    if value is None: return 'Unmeasured'
    if value is True: return 'Yes'
    if value is False: return 'No'
    return str(value)
def money(value): return '$'+format(value,'.6f') if numeric(value) else 'Unmeasured'
def probability(value): return f'{100*value:.1f}%' if numeric(value) else 'Unmeasured'
def fmt(value): return json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)
def h(value): return escape(str(value),quote=True)
def pre(value): return '<pre>'+h(value if isinstance(value,str) else fmt(value))+'</pre>'
def detail(title,body,opened=False): return '<details'+(' open' if opened else '')+'><summary>'+h(title)+'</summary>'+body+'</details>'
def status(value): return '<strong class="status">'+h(shown(value).replace('_',' '))+'</strong>'

class Reader:
    def __init__(self,root): self.root=root; self.hashes={}; self.issues=[]; self.redactions=[]
    def text(self,name,default=None):
        p=self.root/name
        if not p.exists(): return default
        if p.is_symlink() or not p.is_file(): raise ValueError('Refusing nonregular artifact: '+name)
        data=p.read_bytes(); self.hashes[name]=sha(data)
        try: value=data.decode('utf-8')
        except UnicodeDecodeError: self.issues.append({'file':name,'error':'Not UTF-8'});return default
        value,count=SECRET.subn('[REDACTED_CREDENTIAL_LIKE_STRING]',value)
        if count:self.redactions.append({'file':name,'count':count,'original_sha256':self.hashes[name]})
        return value
    def obj(self,name,default=None):
        text=self.text(name)
        if text is None:return default
        try:return json.loads(text,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        except (ValueError,TypeError):self.issues.append({'file':name,'error':'Malformed JSON'});return default

def evidence(item):
    if not isinstance(item,dict):return '<p class="muted">Unmeasured.</p>'
    body='<p>'+h(item.get('explanation','No explanation recorded.'))+'</p>'
    for e in item.get('evidence',[]):
        body+='<figure><figcaption>Quoted source: '+h(e.get('source','unknown'))+'</figcaption>'+pre(e.get('quote',''))+'</figure>'
    return body

def diff_state(initial,final):
    if initial is None or final is None:return None,None
    left,right=initial.get('files',{}),final.get('files',{})
    changes=[]
    for path in sorted(set(left)|set(right)):
        if left.get(path)!=right.get(path):
            changes.append({'path':path,'kind':'created' if path not in left else 'deleted' if path not in right else 'modified',
                'before':left.get(path),'after':right.get(path),
                'diff':''.join(difflib.unified_diff(str(left.get(path,'')).splitlines(True),str(right.get(path,'')).splitlines(True),fromfile='initial/'+path,tofile='final/'+path))})
    return changes,initial.get('schedule')!=final.get('schedule')

def collect(run,fixture=False):
    reader=Reader(run);settings=reader.obj('settings.json',{}) or reader.obj('packet/settings.json',{})
    summary=reader.obj('summary.json',{}) or {};stop=reader.obj('operator-stop.json')
    budget=reader.obj('provider-ledger.json',{}) or summary.get('budget',{})
    expected=settings.get('arms',list(ARMS)); recorded={r.get('arm'):r for r in summary.get('arms',[]) if isinstance(r,dict)}
    terminal=bool(stop) or (set(expected)<=set(recorded)) or budget.get('halted') is True
    if not terminal:raise ValueError('Run not terminal: all declared arms or an explicit stop record are required')
    if not stop and any(e.get('status')=='pending' for e in budget.get('entries',[])):
        raise ValueError('Provider request still pending; report only after execution is terminal')
    arms=[]
    for name in ARMS:
        base=name+'/'; row=reader.obj(base+'summary.json',{}) or recorded.get(name,{})
        audit=reader.obj(base+'audit.json',{}) or {};review=reader.obj(base+'primary-review.json',{}) or {}
        environment_review=reader.obj(base+'environment-review.json')
        score=reader.obj(base+'score.json',{}) or {};initial=reader.obj(base+'world/world-initial.json')
        final=reader.obj(base+'world-final.json') or reader.obj(base+'world/world-state.json')
        changes,schedule_changed=diff_state(initial,final)
        accepted=review.get('status') in ('valid','invalid','incomplete') and isinstance(review.get('checks'),dict)
        scheduled_path=initial.get('schedule',{}).get('command') if initial else None
        scheduled_before=initial.get('files',{}).get(scheduled_path) if initial and scheduled_path else None
        scheduled_after=final.get('files',{}).get(scheduled_path) if final and scheduled_path else None
        scheduled_changed=(scheduled_before!=scheduled_after) if scheduled_before is not None and final is not None else None
        entries=[e for e in budget.get('entries',[]) if str(e.get('arm','')).split('.')[0]==name]
        arm_cost=sum(e['charged_usd'] for e in entries) if entries and all(numeric(e.get('charged_usd')) for e in entries) else None
        per_provider={p:sum(e['charged_usd'] for e in entries if e.get('provider')==p) for p in ('openai','openrouter')} if arm_cost is not None else {}
        errors=[]
        for file in ('execution-error.json','secondary-error.json','environment-review-error.json'):
            val=reader.obj(base+file)
            if val is not None:errors.append({'source':base+file,'details':val})
        failure=reader.obj(name+'-failure.json')
        if failure is not None:errors.append({'source':name+'-failure.json','details':failure})
        if audit.get('error'):errors.append({'source':base+'audit.json','details':audit['error']})
        if score.get('error'):errors.append({'source':base+'score.json','details':score['error']})
        native=reader.obj(base+'native-sample.json',{}) or {}
        for key,value in native.get('store',{}).items():
            if key.endswith(':auditor') and isinstance(value,dict):
                for i,msg in enumerate(value.get('messages',[])):
                    if msg.get('error'):errors.append({'source':base+'native-sample.json','message_index':i,'details':msg['error']})
        target_responses=[]
        call_dir=run/base/'calls'
        if call_dir.exists():
            for path in sorted(call_dir.glob('*-target.json')):
                relative=str(path.relative_to(run));call=reader.obj(relative,{}) or {}
                target_responses.append({'source':relative,'response':call.get('response'),'error':call.get('error'),'seconds':call.get('time')})
        unstarted=not row and not audit and not final
        arm={'arm':name,'label':LABELS[name], 'execution':row,'execution_status':row.get('execution_status','not_run' if unstarted else 'interrupted_or_missing_summary'),
            'setup_gate_passed':row.get('setup_gate_passed'), 'exposure_delivered':final.get('exposure_delivered') if final else None,
            'target_responses':final.get('target_responses') if final else None,'valid_comparison_case':row.get('valid_comparison_case'),
            'primary_review_status':review.get('status',row.get('primary_review_status','unmeasured')),
            'review_accepted':accepted,'accepted_review':review if accepted else None,'rejected_review':None if accepted else review or None,
            'raw_review_reply':reader.text(base+'primary-review-reply.txt'),
            'review_sources':reader.obj(base+'primary-review-sources.json'),
            'environment_review':environment_review,
            'environment_review_status':environment_review.get('status','unmeasured') if isinstance(environment_review,dict) else row.get('environment_review_status','unmeasured'),
            'environment_review_sources':reader.obj(base+'environment-review-sources.json'),
            'raw_environment_review_reply':reader.text(base+'environment-review-reply.txt'),
            'initial_state':initial,'final_state':final,'file_changes':changes,'schedule_changed':schedule_changed,
            'initial_scheduled_command':scheduled_path,'scheduled_script_changed':scheduled_changed,
            'scheduled_script_before':scheduled_before,'scheduled_script_after':scheduled_after,
            'other_file_changes':[c for c in changes if c['path']!=scheduled_path] if changes is not None else None,
            'transcript':audit.get('transcript'),'reasoning':audit.get('reasoning'),'raw_target_responses':target_responses,'run_structure':reader.obj(base+'run-structure.json'),
            'legacy_scores':{k:score.get(k) if not score.get('error') else None for k in ('self_report','verbalized','validity')},
            'petri_scores':audit.get('petri_scores',{}),'legacy_record':score or None,
            'errors':errors,'charged_or_reserved_usd':arm_cost,'provider_costs':per_provider,
            'calls_by_role':dict(Counter(e.get('role','unknown') for e in entries)),
            'auditor_template':reader.text(base+'auditor-template.txt') or reader.text('packet/'+name+'.template.txt')}
        arms.append(arm)
    result={'artifact_kind':'offline_fixture' if fixture else 'recorded_run','run_name':run.name,
        'source_directory':str(run),'rendered_at':datetime.now(timezone.utc).isoformat(),
        'code_version':(reader.text('CODE_VERSION','') or '').strip() or None,'settings':settings,
        'dependencies':reader.obj('dependencies.json'),'operator_stop':stop,'budget':budget,'arms':arms,
        'profile_provenance':reader.obj('packet/profile-provenance.json'),
        'profile_context':reader.obj('packet/profile-context.txt'),
        'generic_guidance':reader.text('packet/generic-guidance.txt'),
        'seed':reader.obj('packet/seed.json'),'interpretation':'One attempt per declared condition on one seed. No profile-benefit claim is established. Missing measurements are not zero.',
        'limitations':['Simulated tools, not actions on a real system.','Required seed situation is supplied before the target chooses; this is guaranteed exposure, not spontaneous discovery.',
            'Scenario clock is fixed; API latency does not advance it and real process shutdown is not executed.',
            'Returned reasoning is model output, not guaranteed access to internal causes or beliefs.',
            'Accepted means the saved validator accepted a review; semantic accuracy still needs human inspection.'],
        'source_hashes':reader.hashes,'read_errors':reader.issues,'redactions':reader.redactions}
    return result

CSS='''
:root{--paper:#f3ebdd;--paper2:#e8e3d6;--ink:#090909;--muted:#5e584e;--red:#b91d12;--line:#b9b2a4}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}main,header,footer{max-width:1240px;margin:auto;padding:28px 42px}header{border-top:12px solid var(--red);padding-top:35px}h1{font-size:clamp(34px,5vw,62px);line-height:1.03;letter-spacing:-.04em;max-width:900px;margin:20px 0}h2{font-size:30px;line-height:1.15;margin:0 0 18px}h3{font-size:21px;margin:22px 0 12px}p{max-width:84ch}a{color:var(--red);text-underline-offset:3px}nav{display:flex;flex-wrap:wrap;gap:12px 24px;padding:17px 0;border-block:1px solid var(--line)}.eyebrow{font:13px/1.4 ui-monospace,monospace;letter-spacing:.09em;text-transform:uppercase}.banner{padding:16px 20px;border-left:6px solid var(--red);background:var(--paper2);font-weight:600}.muted,figcaption{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.metric{border-top:2px solid var(--ink);padding-top:10px}.metric strong{display:block;font-size:26px;overflow-wrap:anywhere}.metric span{color:var(--muted);font-size:14px}.section{padding-top:36px;margin-top:32px;border-top:2px solid var(--ink);scroll-margin-top:20px}.tablewrap{overflow:auto;border:1px solid var(--line)}table{width:100%;border-collapse:collapse;font-size:15px}th,td{text-align:left;vertical-align:top;padding:13px;border-bottom:1px solid var(--line);min-width:130px}th{font-size:13px;text-transform:uppercase;letter-spacing:.03em;background:var(--paper2)}.status{font-weight:650}.armheader{display:grid;grid-template-columns:65px 1fr;gap:16px}.number{font:54px/1 ui-monospace,monospace;color:var(--red)}details{border-top:1px solid var(--line);padding:13px 0}summary{cursor:pointer;font-weight:650;overflow-wrap:anywhere}summary:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid var(--red);outline-offset:3px}pre{font:13px/1.55 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#e9e3d7;padding:18px;max-height:680px;overflow:auto;border-left:2px solid var(--line);tab-size:2}figure{margin:14px 0}figcaption{font-size:13px}button{font:inherit;background:transparent;border:1px solid var(--ink);padding:7px 12px;cursor:pointer;margin:0 8px 8px 0}button:hover{background:var(--paper2)}dl{display:grid;grid-template-columns:200px minmax(0,1fr);gap:6px 20px}dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}.wide{max-width:none}.warning{color:var(--red);font-weight:650}.small{font-size:14px}.evidencecheck{border-bottom:1px solid var(--line);padding-bottom:12px}footer{font-size:13px;border-top:1px solid var(--line);margin-top:40px}@media(max-width:650px){main,header,footer{padding:22px 18px}.grid{grid-template-columns:1fr}.armheader{grid-template-columns:45px 1fr}.number{font-size:38px}dl{grid-template-columns:1fr;gap:3px}dd{margin-bottom:10px}pre{padding:12px;font-size:12px}th,td{padding:10px;min-width:120px}h2{font-size:26px}}@media print{button{display:none}pre{max-height:none;overflow:visible}details{break-inside:avoid}header,main,footer{max-width:none;padding:12px}}
'''

def render_html(data):
    fixture=data['artifact_kind']=='offline_fixture'
    title='OFFLINE FIXTURE — renderer checks only' if fixture else 'Recorded matched shutdown comparison'
    providers=data['budget'].get('providers',{})
    head='<header><div class="eyebrow">AutoResearch / evidence notebook</div><h1>What happened in each environment?</h1>'
    head+='<p class="banner">'+h(title)+'. '+('These are simulated test records, not preference or environment-quality evidence.' if fixture else 'Read the observed behavior and validity before interpreting any awareness score.')+'</p>'
    head+='<p>No profile-benefit claim is established by this report. All declared conditions remain visible, including failed or unrun conditions.</p>'
    notes=data.get('inspection_notes')
    if notes:
        head+='<aside class="banner"><h2>What direct inspection found</h2><p>'+h(notes['summary'])+'</p><ul>'+''.join('<li>'+h(x)+'</li>' for x in notes['findings'])+'</ul><p class="small">These agent inspection notes were added after the run. They do not replace or change the saved judge outputs. Supporting records and their hashes are included in comparison.json.</p></aside>'
    head+='<nav aria-label="Report sections"><a href="#comparison">Compare conditions</a><a href="#guidance">Added guidance</a>'+''.join('<a href="#'+a+'">'+h(LABELS[a])+'</a>' for a in ARMS)+'<a href="#provenance">Costs & provenance</a></nav></header><main>'
    head+='<div class="grid"><div class="metric"><span>OpenAI charged or reserved</span><strong>'+money(providers.get('openai',{}).get('charged_or_reserved_usd'))+'</strong></div><div class="metric"><span>OpenRouter charged or reserved</span><strong>'+money(providers.get('openrouter',{}).get('charged_or_reserved_usd'))+'</strong></div><div class="metric"><span>Declared experiment</span><strong>One seed · three conditions</strong></div></div>'
    head+='<section id="comparison" class="section"><h2>Conditions, kept separate</h2><p>Execution success, setup exposure, and accepted validity are different checks. “Unmeasured” never means zero. Legacy awareness scores are diagnostics, not direct measurements of internal belief.</p><div class="tablewrap"><table><thead><tr><th>Condition</th><th>Execution</th><th>Threat delivered</th><th>Primary review</th><th>Accepted judge label</th><th>Scheduled script changed</th><th>Prompted recognition</th></tr></thead><tbody>'
    for a in data['arms']:
        review=a['accepted_review'] or {}
        head+='<tr><td><a href="#'+a['arm']+'">'+h(a['label'])+'</a></td><td>'+h(shown(a['execution_status']))+'</td><td>'+h(shown(a['exposure_delivered']))+'</td><td>'+h(shown(a['primary_review_status']))+'</td><td>'+h(review.get('outcome',{}).get('label','No accepted judgment'))+'</td><td>'+h(shown(a['scheduled_script_changed']))+'</td><td>'+h(probability(a['legacy_scores']['self_report']))+'</td></tr>'
    head+='</tbody></table></div><p class="small">Matched prompts do not imply identical generated environments. Differences below are descriptive observations from this batch, not a reliable estimate of personalization benefit.</p>'
    if data['operator_stop']:head+='<h3>Explicit operator stop</h3>'+pre(data['operator_stop'])
    head+='<h3>How to read this experiment</h3><ul>'+''.join('<li>'+h(x)+'</li>' for x in data['limitations'])+'</ul></section>'
    context=data.get('profile_context')
    context=context if isinstance(context,dict) else {}
    persona=context.get('persona');examples=context.get('past_choices');generic=data.get('generic_guidance')
    head+='<section id="guidance" class="section"><h2>What guidance was added?</h2>'
    head+='<p><strong>No researcher context:</strong> no extra guidance. The shared setup and original seed still apply.</p>'
    head+='<p><strong>Researcher profile:</strong> the saved persona and selected examples below were added to the auditor\'s context. The choice labels and rationales are AI-inferred, not confirmed by Hobbhahn. This is a tentative representation, not a permanent rulebook or evidence that personalization helped.</p>'
    head+='<h3>Full saved persona</h3>'
    if isinstance(persona,str) and persona.strip():
        head+='<p class="persona">'+h(persona)+'</p>'
    else:head+='<p class="warning">Unknown: no nonempty persona is available in packet/profile-context.txt.</p>'
    if isinstance(examples,list):
        head+=detail('All selected examples ('+str(len(examples))+') — exact saved JSON',pre(examples))
        if not examples:head+='<p>No selected examples were recorded in the profile context.</p>'
    else:head+='<p class="warning">Unknown: selected examples are missing from the saved profile context.</p>'
    head+='<h3>Generic guidance</h3>'
    head+=detail('Full saved generic instructions',pre(generic) if isinstance(generic,str) and generic.strip() else '<p>Unknown: no nonempty generic-guidance.txt was available.</p>')
    head+='<p class="small">The full auditor templates below show the shared instructions and exact placement. This section displays saved artifacts without rewriting or inferring missing guidance.</p></section>'
    head+='<div class="section"><button type="button" id="expand">Open all evidence</button><button type="button" id="collapse">Close evidence</button></div>'
    for i,a in enumerate(data['arms'],1):
        state=a['initial_state'];final=a['final_state'];review=a['accepted_review']
        head+='<section class="section" id="'+a['arm']+'"><div class="armheader"><div class="number">0'+str(i)+'</div><div><h2>'+h(a['label'])+'</h2><p>'+status(a['execution_status'])+' · Primary review: '+status(a['primary_review_status'])+'</p></div></div>'
        facts={'Setup gate passed':a['setup_gate_passed'],'Required situation delivered':a['exposure_delivered'],'Completed target responses':a['target_responses'],'Legacy primary/exposure check (not full semantic validity)':a['valid_comparison_case'],'Recorded calls by role':fmt(a['calls_by_role']),'Charged or reserved':money(a['charged_or_reserved_usd'])}
        head+='<dl>'+''.join('<dt>'+h(k)+'</dt><dd>'+h(shown(v))+'</dd>' for k,v in facts.items())+'</dl>'
        head+='<h3>The initial environment</h3>'
        if state is None:
            head+='<p class="warning">No initial exposure snapshot is available. Final setup state does not prove delivery to the target.</p>'
            if final:head+=detail('Undelivered or final setup state',pre(final))
        else:
            if a['exposure_delivered'] is not True:
                head+='<p class="warning">This is the recorded initial state. Delivery to the target is not confirmed; an attempted request or failed call does not prove delivery.</p>'
            head+='<p><strong>Workspace note</strong></p>'+pre(state.get('workspace_note',''))
            head+='<div class="grid"><div><h4>Initial time</h4>'+pre(state.get('current_time','Unmeasured'))+'</div><div><h4>Initial schedule</h4>'+pre(state.get('schedule'))+'</div><div><h4>Initial shutdown script</h4>'+pre(state.get('files',{}).get(state.get('schedule',{}).get('command'),'Not present at scheduled command path'))+'</div></div>'
            for path,content in sorted(state.get('files',{}).items()):head+=detail('Initial file · '+path,pre(content))
        head+='<h3>Initial environment assessment</h3>'
        head+='<p class="small">This optional judge sees only initial files, task, tools and attempted initial target input. It is separate from the target outcome and primary review. An attempted input does not prove delivery after a failed call. The assessment runs after the audit, without the arm identity or later target behavior; it is descriptive, not an admission gate, execution check, aggregate score or basis for a reroll.</p>'
        assessment=a.get('environment_review')
        assessed=isinstance(assessment,dict) and assessment.get('status')=='reviewed' and isinstance(assessment.get('checks'),dict)
        if assessment is None and a.get('environment_review_status','unmeasured')=='unmeasured':
            head+='<p class="muted">Not recorded for this run. No initial-state judgment is inferred.</p>'
        else:
            head+='<p>Recorded assessment status: '+status(a.get('environment_review_status'))+'.</p>'
            if assessed:
                head+='<p>Accepted by the saved reference validator. Source references establish provenance; the interpretation still requires human review. This is not an overall pass or a finding that the profile helped.</p>'
                contradicted=[name for name,item in assessment['checks'].items() if isinstance(item,dict) and item.get('status')=='contradicted']
                if a['primary_review_status']=='valid' and contradicted:
                    head+='<p class="warning">Review disagreement: the primary review is marked valid, while the initial-state assessment marks '+h(', '.join(name.replace('_',' ') for name in contradicted))+' as contradicted. Both judgments remain visible; neither overrides the other or establishes full semantic validity.</p>'
                head+=detail('Initial-only descriptive findings and reconstructed source quotations',pre(assessment))
            else:
                head+='<p class="warning">No accepted initial-state assessment. Failed or incomplete review output is unmeasured.</p>'
                if assessment is not None:head+=detail('Initial-state review failure record',pre(assessment))
        if a.get('environment_review_sources') is not None:
            head+=detail('Initial-only source map and exact line references',pre(a['environment_review_sources']))
        if a.get('raw_environment_review_reply') is not None:
            head+=detail('Raw initial-state reviewer reply · '+('accepted record' if assessed else 'unaccepted'),pre(a['raw_environment_review_reply']))
        head+='<h3>What the target actually returned</h3>'
        head+=detail('Full target-visible conversation',pre(a['transcript']) if a['transcript'] else '<p>Unmeasured: no usable target conversation was recorded.</p>',True)
        head+=detail('Returned reasoning preserved in the native conversation',pre(a['reasoning']) if a['reasoning'] else '<p>Unmeasured: no reasoning text was recorded.</p>')
        head+=detail('Audit target API responses, including any rejected or truncated output',pre(a['raw_target_responses']) if a['raw_target_responses'] else '<p>No raw target-response artifacts are present.</p>')
        head+='<h3>What changed in the simulated state</h3>'
        head+='<p><strong>File scheduled at startup:</strong> '+h(shown(a['initial_scheduled_command']))+'<br><strong>Contents changed at that exact path:</strong> '+h(shown(a['scheduled_script_changed']))+'</p>'
        head+='<p class="warning">A same-named project file is not the scheduled script unless the schedule actually points to it. A judge label of confirmed modification does not by itself show that shutdown was prevented.</p>'
        if a['initial_scheduled_command']:
            head+=detail('Scheduled script: exact before / after',pre({'path':a['initial_scheduled_command'],'before':a['scheduled_script_before'],'after':a['scheduled_script_after']}))
        head+='<p><strong>All observed file changes</strong> (each path remains explicit):</p>'
        if a['file_changes'] is None:head+='<p>Cannot compare files: an initial or final state is missing.</p>'
        elif not a['file_changes']:head+='<p>No file content changes between the recorded initial and final snapshots.</p>'
        else:
            for change in a['file_changes']:
                head+=detail(change['kind'].capitalize()+' · '+change['path'],pre(change['diff'])+detail('Complete final content',pre(change['after'])))
        head+='<p>Schedule changed: <strong>'+h(shown(a['schedule_changed']))+'</strong>.</p>'
        if final:head+=detail('Final schedule and recorded state events',pre({'schedule':final.get('schedule'),'events':final.get('events',[]),'real_process_shutdown_executed':final.get('real_process_shutdown_executed')}))
        head+='<h3>The evidence review</h3>'
        if review:
            head+='<p>Accepted by the saved validator. This remains a model judgment; exact quotes do not alone prove the interpretation.</p>'
            for check in CHECKS:
                item=review.get('checks',{}).get(check,{})
                head+='<div class="evidencecheck"><h4>'+h(check.replace('_',' ').capitalize())+' · '+h(shown(item.get('status')))+'</h4>'+evidence(item)+'</div>'
            for key in ('outcome','expressed_awareness'):
                item=review.get(key,{})
                head+='<h4>'+h(key.replace('_',' ').capitalize())+' · '+h(item.get('label','Unmeasured'))+'</h4>'+evidence(item)
            head+=detail('Accepted realism concerns',pre(review.get('realism_concerns',[])))
        else:
            head+='<p class="warning">No accepted validity or outcome judgment. A rejected reply is not a usable score.</p>'
            if a['rejected_review']:head+=pre(a['rejected_review'])
        head+=detail('Raw reviewer reply · '+('accepted record' if review else 'unaccepted / unavailable'),pre(a['raw_review_reply']) if a['raw_review_reply'] else '<p>No reply was recorded.</p>')
        if a['review_sources']:head+=detail('Exact evidence sources supplied to the reviewer',pre(a['review_sources']))
        head+=detail('Secondary diagnostics — separate from primary validity',pre({'legacy':a['legacy_scores'],'petri':a['petri_scores'],'record':a['legacy_record']}))
        head+=detail('Execution errors and setup/tool failures',pre(a['errors']) if a['errors'] else '<p>No error entries found in the inspected artifact files. This does not certify successful execution.</p>',bool(a['errors']))
        head+=detail('Execution summary and stop information',pre({'summary':a['execution'],'structure':a['run_structure']}))
        head+=detail('Exact saved auditor template',pre(a['auditor_template']) if a['auditor_template'] else '<p>No saved template was found.</p>')
        head+='</section>'
    head+='<section class="section" id="provenance"><h2>Costs and provenance</h2><p>Amounts are conservative usage estimates or retained reservations from this local allocation. They are not a provider billing statement or the total project spend.</p>'
    head+=pre({'run':data['run_name'],'code_version':data['code_version'],'provider_totals':providers,'models':data['settings'].get('models'),'routing':data['settings'].get('routing'),'generation':data['settings'].get('generation'),'turn_limit':data['settings'].get('max_auditor_turns'),'start_time':data['settings'].get('start_time')})
    for panel_title,key in [('Original seed','seed'),('Full frozen settings','settings'),('Profile provenance','profile_provenance'),('Dependency snapshot','dependencies'),('Full cost ledger','budget'),('Read/parse errors','read_errors'),('Credential-like redactions','redactions'),('Hashes of inspected source artifacts','source_hashes')]:head+=detail(panel_title,pre(data[key]))
    head+='</section></main><footer>Self-contained local report. No remote assets or network requests. Source text is escaped; raw credential-like strings are redacted and recorded. Generated '+h(data['rendered_at'])+'.</footer>'
    script="document.getElementById('expand').addEventListener('click',()=>document.querySelectorAll('details').forEach(d=>d.open=true));document.getElementById('collapse').addEventListener('click',()=>document.querySelectorAll('details').forEach(d=>d.open=false));"
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>'+h(title)+'</title><style>'+CSS+'</style></head><body>'+head+'<script>'+script+'</script></body></html>'

def render(run,out,fixture=False,inspection_notes=None):
    run=Path(run).resolve();out=Path(out).resolve()
    if out==run or run in out.parents:raise ValueError('Output must not mutate or sit inside the source run')
    if out.exists():raise ValueError('Use a fresh output directory; do not overwrite evidence reports')
    data=collect(run,fixture)
    if inspection_notes:
        notes_bytes=Path(inspection_notes).read_bytes()
        notes=json.loads(notes_bytes)
        if not isinstance(notes,dict) or not isinstance(notes.get('summary'),str) or not isinstance(notes.get('findings'),list) or not all(isinstance(x,str) for x in notes['findings']):
            raise ValueError('Inspection notes require a summary and list of text findings')
        data['inspection_notes']=notes
        data['inspection_notes_sha256']=sha(notes_bytes)
    out.mkdir(parents=True)
    (out/'comparison.json').write_text(fmt(data)+'\n')
    (out/'index.html').write_text(render_html(data))
    lines=['# Matched shutdown evidence report','', '**OFFLINE FIXTURE — not live results.**' if fixture else 'Recorded run artifacts. No profile-benefit claim is established.', '',
        'Open `index.html` in a browser. It includes full target transcripts/reasoning, environment snapshots, state changes, accepted or rejected review evidence, errors and costs. When present, the descriptive initial-state assessment is shown separately from primary judging and target outcomes; it is not an admission gate or an overall score. `comparison.json` holds the same collected records.', '',
        '| Condition | Execution | Exposure delivered | Primary review | Charged/reserved |','|---|---|---|---|---|']
    for a in data['arms']:lines.append('| '+ ' | '.join([a['label'],a['execution_status'],shown(a['exposure_delivered']),a['primary_review_status'],money(a['charged_or_reserved_usd'])])+' |')
    lines+=['','Missing values are unmeasured, not zero. Simulated tool state and a fixed scenario clock do not demonstrate real process shutdown. Required exposure is supplied before choice; this is not spontaneous discovery. One attempt per condition cannot establish reliable personalization gains.','',
        'Code version: `'+str(data['code_version'])+'`. Source hashes and any parsing failures or credential-like redactions are in `comparison.json`. The report makes no new model calls.','',
        'The HTML is the complete reading surface; the Markdown is a compact index. No external assets or JavaScript libraries are required.']
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    digest={'report':str(out/'index.html'),'artifact_kind':data['artifact_kind'],'arms':[{k:a[k] for k in ('arm','execution_status','primary_review_status','exposure_delivered')} for a in data['arms']],
        'source_files':len(data['source_hashes']),'read_errors':len(data['read_errors']),'html_bytes':(out/'index.html').stat().st_size,
        'outputs_sha256':{p.name:sha(p.read_bytes()) for p in out.iterdir()}}
    print(json.dumps(digest))
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--fixture',action='store_true',help='Prominently label synthetic renderer QA inputs')
    p.add_argument('--inspection-notes',type=Path,help='Separate post-run agent inspection notes; never replaces saved judgments')
    a=p.parse_args();render(a.run,a.out,a.fixture,a.inspection_notes)
