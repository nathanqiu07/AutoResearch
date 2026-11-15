#!/usr/bin/env python3
"""Read four explicitly released terminal records; emit scalar metadata and hashes only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    root=args.data_root.resolve(strict=True)
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    inputs={}
    def read(name):
        path=(root/name).resolve(strict=True);path.relative_to(root)
        raw=path.read_bytes()
        inputs[name]={'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
        return json.loads(raw)
    publication=read('publication-summary.json')
    ledger=read('provider-ledger.json')
    stop=read('operator-stop.json')
    world=read('baseline/world/world-state.json')
    # Explicit field projection: never export world files, notes, events,
    # source/prompt strings, narrative reasons, ledger leases or arbitrary values.
    pub_fields=('target_calls','openai_calls','completed_auditor_calls','unresolved_auditor_requests',
                'completed_openrouter_usage_estimate_usd','retained_openrouter_reservation_usd',
                'no_preference_or_awareness_measurement','original_ledgers_unchanged')
    pub={key:publication[key] for key in pub_fields}
    assert all(type(value) in (bool,int,float) for value in pub.values())
    flags={key:world[key] for key in ('configured','started','exposure_delivered','target_responses','failed','finished')}
    assert all(type(value) in (bool,int) for value in flags.values())
    entries=ledger['entries']
    allowed_statuses={'usage_estimate','pending','error','failed','uncertain'}
    allowed_roles={'auditor','target','judge'}
    allowed_providers={'openrouter','openai'}
    assert all(e['status'] in allowed_statuses and e['role'] in allowed_roles and e['provider'] in allowed_providers for e in entries)
    status=dict(Counter(e['status'] for e in entries))
    completed=sum(e['status']=='usage_estimate' for e in entries)
    pending=sum(e['status']=='pending' for e in entries)
    attempted_names=sorted(str(p.relative_to(root)) for p in root.rglob('attempted-target-inputs.jsonl'))
    checks={
        'publication_reports_10_complete_1_unresolved':pub['completed_auditor_calls']==10 and pub['unresolved_auditor_requests']==1,
        'ledger_records_11_auditor_calls_10_usage_estimates_1_pending':len(entries)==11 and completed==10 and pending==1 and all(e['role']=='auditor' for e in entries),
        'publication_reports_zero_target_and_openai_calls':pub['target_calls']==0 and pub['openai_calls']==0,
        'world_not_configured_started_or_exposed':flags['configured'] is False and flags['started'] is False and flags['exposure_delivered'] is False and flags['target_responses']==0,
        'no_attempted_target_input_files':not attempted_names,
        'operator_stop_call_count_matches':stop['calls_at_stop']==len(entries),
        'operator_reports_preserved_ledger_and_packet':stop['ledger_unchanged_pending_reservations_retained'] is True and stop['prior_packet_immutable'] is True,
        'publication_runtime_pin_matches_old_source':publication['code_version']=='09d3ba15774dd7dcf8bdf060d6121196494d2996',
    }
    for name,record in inputs.items():
        path=(root/name).resolve(strict=True);path.relative_to(root)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
    report={'inputs':inputs,'publication_scalars':pub,'world_scalars':flags,
        'ledger_counts':{'entries':len(entries),'status':status,'roles':dict(Counter(e['role'] for e in entries)),
                         'providers':dict(Counter(e['provider'] for e in entries))},
        'operator_stop':{'process_id':stop['process_id'],'calls_at_stop':stop['calls_at_stop'],
                         'dedicated_cwd_field_present':'cwd' in stop,'dedicated_signal_field_present':'signal' in stop,
                         'narrative_reason_sha256':hashlib.sha256(stop.get('reason','').encode()).hexdigest()},
        'attempted_target_input_file_count':len(attempted_names),'checks':checks,
        'verified':sum(checks.values()),'failed':sum(not value for value in checks.values()),
        'limits':['Recorded metadata is not independent provider billing or physical-request evidence.',
                  'The operator record supplies a process ID but does not include dedicated cwd/signal fields; OS-level termination and pending-request outcome remain unverified here.',
                  'No narrative reason, source, prompt, profile, decision or response content is emitted.',
                  'No referenced paths, environment/credential files, labels, ledger databases or code entrypoints are followed.']}
    (out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    result=int(bool(report['failed']))
    (out/'command.json').write_text(json.dumps({'argv':[sys.executable,'-I','-B',str(Path(__file__).resolve()),*sys.argv[1:]],'exit_code':result,
        'reader_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
    print(json.dumps({'verified':report['verified'],'failed':report['failed'],'publication':pub,'world':flags,'ledger':report['ledger_counts']},indent=2))
    return result


if __name__=='__main__':
    raise SystemExit(main())
