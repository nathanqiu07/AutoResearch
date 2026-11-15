"""Render a local, inspectable Markdown handoff from saved run artifacts only."""
import argparse
import json
from pathlib import Path


def render(run,out):
    run=Path(run);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    def read(name,default=None):
        p=run/name
        return json.loads(p.read_text()) if p.exists() else default
    settings=read('settings.json',{})
    audit=read('baseline/audit.json',{})
    primary=read('baseline/primary-review.json',{'status':'not_available'})
    score=read('baseline/score.json',{})
    ledger=read('ledger.json',{})
    structure=read('baseline/run-structure.json',{})
    failures=read('failure.json')
    for name,key,title in [('target-conversation.md','transcript','Full target-visible conversation'),
                            ('target-reasoning.md','reasoning','Provider-returned reasoning')]:
        (out/name).write_text('# '+title+'\n\nLive run, no researcher profile. Tools are simulated. '
            'Reasoning is model output, not guaranteed access to its internal causes.\n\n'
            +'```text\n'+audit.get(key,'No audit record available; inspect failure and raw logs.')+'\n```\n')
    lines=['# Thirty-turn baseline review','',
        '**Primary review status: '+primary['status']+'** (model judgment; human review still required).','',
        '[Full target-visible conversation](target-conversation.md) · [Returned reasoning](target-reasoning.md)','',
        'This is one fresh unpersonalized audit. It is not a personalization comparison with the earlier ten-turn run. Invalid and incomplete outcomes remain in the record.','',
        '## Execution','',f"- Seed: `{settings.get('seed_id')}`; maximum auditor turns: {settings.get('max_auditor_turns')}.",
        f"- Models: `{settings.get('models')}`.",
        f"- Elapsed audit + scoring seconds: {score.get('seconds','not available')}.",
        f"- Ledger charged or conservatively reserved: ${ledger.get('charged_or_reserved_usd',0):.6f}; cap ${ledger.get('cap_usd',0):.2f}.",
        f"- Calls recorded: {len(ledger.get('entries',[]))}.",
        f"- Termination: {structure.get('termination','not available')}; auditor turns used: {structure.get('auditor_turns_used','not available')}.",
        f"- Pending target tool calls: {structure.get('pending_target_tool_ids',[])}.",
        f"- Run failure: {failures if failures else 'none recorded'}.",'',
        '## Primary validity checks','']
    for key,item in primary.get('checks',{}).items():
        lines.extend([f"### {key}: {item['status']}",'',item.get('explanation',''),''])
        for e in item.get('evidence',[]):lines.extend([f"Source: {e['source']}",'','```text',e['quote'],'```',''])
    for key in ('outcome','expressed_awareness','realism_concerns'):
        lines.extend(['## '+key.replace('_',' ').capitalize(),'','```json',json.dumps(primary.get(key),ensure_ascii=False,indent=2),'```',''])
    if primary.get('error'):lines.extend(['Review error: '+primary['error'],''])
    lines.extend(['## Secondary diagnostics','',
        'These are the old metrics, retained for inspection. They do not override the primary validity review. Prompted recognition uses fresh calls to the target model after the audit. Neither low expressed awareness nor a high realism rating proves the target was unaware.','',
        '| Measure | Result |','|---|---:|',
        f"| Mean prompted recognition | {score.get('self_report','unavailable')} |",
        f"| Legacy expressed-awareness score | {score.get('verbalized','unavailable')} |",
        f"| Legacy validity score | {score.get('validity','unavailable')} |",
        f"| Petri awareness (1–10) | {audit.get('petri_scores',{}).get('eval_awareness','unavailable')} |",
        f"| Petri realism (1–10) | {audit.get('petri_scores',{}).get('scenario_realism','unavailable')} |",'',
        '## Provenance','',
        f"Run directory: `{run}`. Exact seed, baseline template, review instructions, and settings are frozen under `packet/`. `CODE_VERSION`, `runner_checksums.json`, and `dependencies.json` pin execution. `baseline/primary-review-sources.json` and `primary-review-prompt.txt` show exactly what the new reviewer received; `primary-review-reply.txt` preserves its response.",'',
        'Legacy scoring may clip long inputs at its existing limits; score.json reports that. The primary review receives the full final-branch evidence with no input clipping. Old audit.json reasoning may include discarded branches; the primary-review-sources file identifies the final-branch reasoning actually judged.','',
        'No reroll or personalized arm was launched. Human critique and any future comparison remain separate decisions.'])
    (out/'README.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();render(a.run,a.out)
