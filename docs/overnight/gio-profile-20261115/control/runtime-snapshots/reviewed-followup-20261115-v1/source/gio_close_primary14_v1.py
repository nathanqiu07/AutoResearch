import hashlib,json,sqlite3
from pathlib import Path
from datetime import datetime,timezone
B=Path('/private/tmp/gio-profile-20261115-coordinator');A=B/'accounting'
def ref(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def read(r):assert ref(r['path'])==r;return json.loads(Path(r['path']).read_text())
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def write(p,d):
 with p.open('x') as f:f.write(json.dumps(d,sort_keys=True,indent=2)+'\n')
 return ref(p)
terminal={'path':str(B/'p8-primary14-supervisor-v1/supervisor-terminal.json'),'sha256':'18d3377cf0023a99e5fa9bc8c6dc6fddcaa4d352dad7f7a6d49da02189ac5495'};t=read(terminal)
assert t['status']=='complete' and t['stop_reason'] is None and t['child_process_terminal'] and t['native_accounting_drain_verified']
v=read(t['verified']);n=v['native'];assert n['attempted_calls']==14 and n['known_spent_nanos']==85065000 and n['ledger_attempts']==298 and n['ledger_spent_nanos']==3345365000
summary=read(n['summary']);assert summary['status']=='complete' and summary['stop_reason'] is None and summary['ledger']['inflight']==summary['ledger']['uncertain']==0
source=B/'ledger/profile-openai-scaling-v1.sqlite';con=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);con.execute('BEGIN');pr=[list(x) for x in con.execute('select id,body from policy order by id')];rr=[list(x) for x in con.execute('select id,reserved,actual,status,metadata from reservations order by id')];con.close()
assert len(rr)==298 and all(r[3]=='complete' for r in rr) and sum(r[2] for r in rr)==3345365000 and json.loads(pr[0][1])['limit_nanos']==80000000000
snap=write(A/'p8-primary14-closed-ledger-snapshot-v1.json',{'schema_version':'closed-ledger-logical-snapshot-v1','observed_at':datetime.now(timezone.utc).isoformat(),'read_only_transaction':True,'source_path':str(source),'policy_rows':pr,'reservation_rows':rr,'logical_snapshot_sha256':hashlib.sha256(canonical({'policy_rows':pr,'reservation_rows':rr}).encode()).hexdigest(),'attempts':298,'known_spent_nanos':3345365000,'retained_hold_nanos':0,'pending':0,'uncertain':0,'status':'complete_no_pending_or_unknown','authority':'Root verified completed primary14 after native and diagnostic terminal; immutable checkpoint only, no ledger reset or releases.'})
pre=write(A/'primary14-remaining8-predecessor-v1.json',{'schema_version':'primary14-remaining8-predecessor-v1','state':'complete','supervisor_terminal':terminal,'verified_outcomes':t['verified'],'final_batch_summary':n['summary'],'closed_ledger_snapshot':snap,'planned_descendant_slots':84,'eligible_descendant_slots':14,'unavailable_descendant_slots':70,'known_invalid_profiles_retained':3,'next_execution_authorized':False})
print(json.dumps({'snapshot':snap,'predecessor':pre},sort_keys=True))
