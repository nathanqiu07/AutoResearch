#!/usr/bin/env python3
"""Compare old/fixed synthetic world state at the reviewed packet's fixed clock."""
import argparse
from datetime import datetime,timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('old-source','new-source','packet','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args()
    settings=json.loads((args.packet/'settings.json').read_bytes())
    sources=[root/'scripts/gio_petri/shutdown_setup.py' for root in (args.old_source,args.new_source)]
    modules=[]
    for i,path in enumerate(sources):
        spec=importlib.util.spec_from_file_location('synthetic_clock_'+str(i),path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules.append(module)
    with tempfile.TemporaryDirectory(prefix='audit22-clock-') as tmp:
        old,new=[module.ShutdownWorld(settings['start_time'],Path(tmp)/str(i)) for i,module in enumerate(modules)]
        checks={'same_initial_state':old._state()==new._state(),
                'same_clock_policy':old.snapshot()['clock_policy']==new.snapshot()['clock_policy'],
                'ten_minute_interval':datetime.fromisoformat(new.schedule['run_at'])-datetime.fromisoformat(new.start_time)==timedelta(minutes=10),
                'same_startup_text':old.begin()==new.begin()}
    report={'checks':checks,'failed':sum(not x for x in checks.values()),
            'source_sha256':[hashlib.sha256(path.read_bytes()).hexdigest() for path in sources],
            'argv':[sys.executable,'-I','-B',str(Path(__file__).resolve()),*sys.argv[1:]],
            'raw_world_content_retained':False,'real_calls':0}
    with args.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'checks':checks,'failed':report['failed']}))
    return int(bool(report['failed']))

if __name__=='__main__':raise SystemExit(main())
