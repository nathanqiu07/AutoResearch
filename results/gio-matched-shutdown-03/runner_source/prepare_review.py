"""Freeze the approved 30-turn baseline packet. Makes no model calls."""
import argparse
import json
from pathlib import Path
import shutil
from prepare import sha
from preflight import write

ROOT=Path(__file__).resolve().parents[2]

def prepare(source, out):
    source=Path(source);out=Path(out)
    checks=json.loads((source/'checksums.json').read_text())
    for name,digest in checks.items():
        if sha(source/name)!=digest:raise ValueError('Source packet changed: '+name)
    settings=json.loads((source/'settings.json').read_text())
    out.mkdir(parents=True,exist_ok=False)
    for name in ('seed.txt','seed.json','baseline.template.txt'):
        shutil.copy2(source/name,out/name)
    shutil.copy2(Path(__file__).with_name('review-instructions.txt'),out/'review-instructions.txt')
    settings.update(status='authorized_single_30_turn_baseline',data_gate='not_applicable_no_user_model',
        arms=['baseline'],max_auditor_turns=30,primary_review='evidence-checklist-v1',
        primary_review_blind_to_recognition=True,primary_review_full_input=True,
        source_packet_settings_sha256=sha(source/'settings.json'),
        run_cap_usd=5,unresolved_execution_requirements=[],remaining_budget_requires_filtering_agent_spend=False)
    for key in ('prior_known_spend_usd','this_preflight_spend_usd','judge_access_check_cost_usd'):
        settings.pop(key,None)
    settings['scoring']='Primary evidence checklist; original team scores retained as secondary diagnostics only'
    write(out/'settings.json',settings)
    write(out/'checksums.json',{f.name:sha(f) for f in out.iterdir() if f.is_file()})
    return settings

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'results/gio-baseline-review-01/packet')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.source,a.out)
    print('Prepared only. No model calls.')
