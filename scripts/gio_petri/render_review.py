"""Render a local, inspectable Markdown handoff from saved run artifacts only."""
import argparse
import json
import os
from pathlib import Path


def render(run,out):
    run=Path(run);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    def read(name,default=None):
        p=run/name
        return json.loads(p.read_text()) if p.exists() else default
    settings=read('settings.json',{})
    recovered=(run/'postmortem-review/recovered-audit.json').exists()
    audit=read('postmortem-review/recovered-audit.json',{}) if recovered else read('baseline/audit.json',{})
    primary=read('postmortem-review/primary-review.json',{'status':'not_available'}) if recovered else read('baseline/primary-review.json',{'status':'not_available'})
    score=read('baseline/score.json',{})
    ledger=read('ledger.json',{})
    structure=read('postmortem-review/run-structure.json',{}) if recovered else read('baseline/run-structure.json',{})
    combined=read('postmortem-review/combined-budget.json',{})
    total_cost=combined.get('total_charged_or_reserved_usd',ledger.get('charged_or_reserved_usd',0))
    calls=len(ledger.get('entries',[]))+len(read('postmortem-review/ledger.json',{}).get('entries',[]))
    elapsed=score.get('seconds','not available')
    if recovered:
        from datetime import datetime
        stats=read('postmortem-review/native-stats.json',{})
        if stats.get('completed_at') and stats.get('started_at'):
            elapsed=(datetime.fromisoformat(stats['completed_at'])-datetime.fromisoformat(stats['started_at'])).total_seconds()
    failures=read('failure.json')
    for name,key,title in [('target-conversation.md','transcript','Full target-visible conversation'),
                            ('target-reasoning.md','reasoning','Provider-returned reasoning')]:
        (out/name).write_text('# '+title+'\n\nLive run, no researcher profile. Tools are simulated. '
            'Reasoning is model output, not guaranteed access to its internal causes.\n\n'
            +'````text\n'+audit.get(key,'No audit record available; inspect failure and raw logs.')+'\n````\n')
    base=os.path.relpath(run.resolve(),out.resolve())
    review_dir='postmortem-review' if recovered else 'baseline'
    lines=['# Thirty-turn baseline review','',
        '**Primary review status: '+primary['status']+'**. '+('No model judgment was accepted.' if not primary.get('checks') else 'Model judgment; human review still required.'),'',
        '**Original audit failed; this is a postmortem of recovered evidence, not a completed baseline.**' if recovered else 'Original audit completed; inspect validity separately.','',
        '[Full target-visible conversation](target-conversation.md) · [Returned reasoning](target-reasoning.md)','',
        'This is one fresh unpersonalized audit. It is not a personalization comparison with the earlier ten-turn run. Invalid and incomplete outcomes remain in the record.','',
        '## Execution','',f"- Seed: `{settings.get('seed_id')}`; maximum auditor turns: {settings.get('max_auditor_turns')}.",
        f"- Models: `{settings.get('models')}`.",
        f"- Original audit elapsed seconds: {elapsed}. Postmortem review, if present, is a separate additional call.",
        f"- Combined charged or conservatively reserved: ${total_cost:.6f}; original cap ${ledger.get('cap_usd',0):.2f}.",
        f"- Calls recorded across original run and postmortem: {calls}.",
        f"- Termination: {structure.get('termination','not available')}; auditor turns used: {structure.get('auditor_turns_used','not available')}.",
        f"- Pending target tool calls: {structure.get('pending_target_tool_ids',[])}.",
        f"- Run failure: {failures if failures else 'none recorded'}.",'',
        '## Primary validity checks','']
    if not primary.get('checks'):
        lines.extend(['No accepted validity judgments are available. The rejected reply is preserved; no replacement score was invented.','',
            f'[Raw reviewer reply]({base}/{review_dir}/primary-review-reply.txt) · [Validation findings]({base}/{review_dir}/validation-findings.json)',''])
    for key,item in primary.get('checks',{}).items():
        lines.extend([f"### {key}: {item['status']}",'',item.get('explanation',''),''])
        for e in item.get('evidence',[]):lines.extend([f"Source: {e['source']}",'','```text',e['quote'],'```',''])
    for key in ('outcome','expressed_awareness','realism_concerns'):
        if key not in primary:continue
        lines.extend(['## '+key.replace('_',' ').capitalize(),'','```json',json.dumps(primary.get(key),ensure_ascii=False,indent=2),'```',''])
    if primary.get('error'):lines.extend(['Review error: '+primary['error'],''])
    if not score:lines.extend(['**Secondary scoring did not run:** the original audit stopped before judgment. Every unavailable value below means unmeasured, not zero.',''])
    lines.extend(['## Secondary diagnostics','',
        'These are the old metrics, retained for inspection. They do not override the primary validity review. Prompted recognition uses fresh calls to the target model after the audit. Neither low expressed awareness nor a high realism rating proves the target was unaware.','',
        '| Measure | Result |','|---|---:|',
        f"| Mean prompted recognition | {score.get('self_report','unavailable')} |",
        f"| Legacy expressed-awareness score | {score.get('verbalized','unavailable')} |",
        f"| Legacy validity score | {score.get('validity','unavailable')} |",
        f"| Petri awareness (1–10) | {audit.get('petri_scores',{}).get('eval_awareness','unavailable')} |",
        f"| Petri realism (1–10) | {audit.get('petri_scores',{}).get('scenario_realism','unavailable')} |",'',
        '## Provenance','',
        f"Run directory: `{run}`. Exact seed, baseline template, review instructions, and settings are frozen under `packet/`. `CODE_VERSION`, `runner_checksums.json`, and `dependencies.json` pin execution. `{review_dir}/primary-review-sources.json` and `primary-review-prompt.txt` show exactly what the new reviewer received; `primary-review-reply.txt` preserves its response.",'',
        'When legacy scoring completes, score.json records any input clipping. '
        +('No score.json exists for this failed audit. ' if recovered and not score else '')
        +'The primary review receives the full final-branch evidence with no input clipping. Old audit.json reasoning may include discarded branches; the primary-review-sources file identifies the final-branch reasoning actually judged.','',
        'When the original run fails, recovered evidence and the one postmortem reviewer live under postmortem-review/. The original empty/failed audit.json is retained. Recovery is from native messages, not invented replacement content. No reroll or personalized arm was launched. Human critique and any future comparison remain separate decisions.'])
    (out/'README.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();render(a.run,a.out)
