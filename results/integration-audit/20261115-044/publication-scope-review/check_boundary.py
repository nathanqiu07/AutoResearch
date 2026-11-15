#!/usr/bin/env python3
"""Classify frozen audit metadata publication boundaries; never follow payload pointers."""
import argparse, hashlib, json
from pathlib import Path, PurePosixPath

PINS={'core':'68aa82a02278fec717574764bae9eb79b16107748dadd1247109d6715ee37bcd','review':'f5d91b8d051be7d01257d0b3ee622dfb8d92b6511ded6c5626286c4e08bcbfbd','copy':'963a81eb821ce24b1b33580460cc3362962a3c17f671ed2734053fefe88dd2e1'}
PRIVATE={'controls/allowlist.json','controls/custody.json','preservation-01/receipt.json'}
HISTORICAL_PRIVATE={'README.md','safe-manifest.json'}
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
p=argparse.ArgumentParser();p.add_argument('--core',required=True);p.add_argument('--review',required=True);p.add_argument('--root-custody',required=True);p.add_argument('--external-metadata',required=True);p.add_argument('--out',required=True);a=p.parse_args()
checks=[];saved={};inputs=[]
def check(n,v):
 checks.append({'name':n,'passed':bool(v)})
 if not v:raise AssertionError(n)
def read(root,n,pin,size=None):
 rel=PurePosixPath(n);check('relative-path:'+str(root)+':'+n,not rel.is_absolute() and '..' not in rel.parts)
 path=root/n;check('regular:'+str(root)+':'+n,path.is_file() and not path.is_symlink());b=path.read_bytes();check('pin:'+str(root)+':'+n,sha(b)==pin and (size is None or len(b)==size));saved[str(path)]=b;inputs.append({'path':str(path),'sha256':sha(b),'size_bytes':len(b)});return b
core=Path(a.core);review=Path(a.review);custody=Path(a.root_custody);external=Path(a.external_metadata)
cm=read(core,'safe-manifest.json',PINS['core']);rm=read(review,'safe-manifest.json',PINS['review']);xm=read(external,'copy-manifest.json',PINS['copy']);c=json.loads(cm);r=json.loads(rm);x=json.loads(xm)
candidates=[('core/safe-manifest.json',cm),('prior-review/safe-manifest.json',rm),('external/copy-manifest.json',xm)]
for e in c['files']:candidates.append(('core/'+e['path'],read(core,e['path'],e['sha256'],e['size_bytes'])))
for n,e in r['files'].items():candidates.append(('prior-review/'+n,read(review,n,e['sha256'],e['size_bytes'])))
for e in x['files']:
 if e['destination'].startswith('root-custody/'):
  n=e['destination'].split('/',1)[1];candidates.append(('root-custody/'+n,read(custody,n,e['sha256'],e['size_bytes'])))
 elif e['destination']=='tools/copy_private_checkpoint_portable.py':
  n='copy_private_checkpoint_portable.py';candidates.append(('external/'+n,read(external,n,e['sha256'],e['size_bytes'])))
# No archive entry or raw path in the allowlist is ever opened.
body=dict(candidates);allow=json.loads(body['core/controls/allowlist.json']);decision=json.loads(body['core/controls/custody.json']);receipt=json.loads(body['core/preservation-01/receipt.json'])
approved={z['path'] for z in allow['allowed']};tuples={canonical(z) for z in allow['allowed']};check('known-private-control-pins',sha(body['core/controls/allowlist.json'])=='f403b554deefa55230486f09c31f469250cc415bf60b3dff41b2cf5e4b5420eb' and sha(body['core/controls/custody.json'])=='b20e0ece59ca334a7b51e7072faa784f7050bc68258375e79dc2c4373e195c20')
check('expected-approval-denominator',len(approved)==len(tuples)==3016)
restricted_digest={sha(canonical(allow)):'allowlist',sha(canonical(decision)):'custody'}
rows=[];public_core=[]
for name,b in candidates:
 seen_paths=set();seen_tuples=set();full_controls=set();state_maps=0
 try:j=json.loads(b)
 except (ValueError,UnicodeError):j=None
 def walk(v):
  global state_maps
  if isinstance(v,dict):
   digest=sha(canonical(v))
   if digest in restricted_digest:full_controls.add(restricted_digest[digest])
   if set(v)>= {'path','sha256','roles','logical_size_bytes_observed'}:
    t=canonical({k:v[k] for k in ['path','sha256','roles','logical_size_bytes_observed']})
    if t in tuples:seen_tuples.add(t)
   if set(v)==approved:state_maps+=1
   for k,w in v.items():
    if k in approved:seen_paths.add(k)
    walk(w)
  elif isinstance(v,list):
   for w in v:walk(w)
  elif isinstance(v,str) and v in approved:seen_paths.add(v)
 if j is not None:walk(j)
 else:
  # Text/code is not decoded as a payload; these are explicit code/log candidates.
  for q in approved:
   if q.encode() in b:seen_paths.add(q)
 full=bool(full_controls) or len(seen_tuples)==3016 or state_maps>0 or len(seen_paths)==3016
 private_expected=name.startswith('core/') and name[5:] in PRIVATE
 check('complete-restricted-body-classification:'+name,full==private_expected)
 disposition='private_only' if full else 'public_metadata_candidate'
 if name.startswith('core/') and name[5:] in HISTORICAL_PRIVATE:disposition='private_historical_publication_wording'
 if name.startswith('prior-review/'):disposition='public_historical_review_with_superseding_scope_note'
 row={'candidate':name,'sha256':sha(b),'size_bytes':len(b),'complete_control_objects':sorted(full_controls),'approved_tuple_matches':len(seen_tuples),'approved_path_mentions':len(seen_paths),'complete_source_state_maps':state_maps,'disposition':disposition};rows.append(row)
 if name.startswith('core/') and disposition=='public_metadata_candidate':public_core.append({'path':name[5:],'sha256':sha(b),'size_bytes':len(b)})
check('only-three-private-body-copies',sum(z['disposition']=='private_only' for z in rows)==3)
check('original-core-public-subset',len(public_core)==21)
check('private-external-bundle-covers-excluded-bodies',all(any(e['destination']=='audit-core/'+n and e['sha256']==sha(body['core/'+n]) for e in x['files']) for n in PRIVATE|HISTORICAL_PRIVATE))
for path,b in saved.items():check('unchanged:'+path,Path(path).read_bytes()==b)
out=Path(a.out);out.mkdir(mode=0o700,exist_ok=False)
report={'schema_version':'audit044-additive-publication-boundary-review-v1','passed':len(checks),'failed':0,'checks':checks,'inputs':inputs,'classification':rows,'summary':{'candidates_checked':len(rows),'restricted_full_body_copies':3,'original_core_public_candidates':21,'prior_review_candidates':sum(n.startswith('prior-review/') for n,b in candidates),'root_custody_candidates':sum(n.startswith('root-custody/') for n,b in candidates),'external_metadata_candidates':sum(n.startswith('external/') for n,b in candidates)},'limits':['Only explicit frozen code/metadata candidates were read; no raw payload or private archive body was opened.','Private status is based on the source-owner restriction supplied by root. This check does not decide or widen authorization.','Prior manifests and publication wording are historical; they do not authorize copying the restricted bodies into a public package.','Hash/path/count summaries are not a secret-free or label-free attestation. No content or consumer replay occurred.','This classifies the frozen candidates; root must check final assembled public membership against a new explicit allowlist.']}
(out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');(out/'proposed-original-core-public-files.json').write_text(json.dumps({'schema_version':'audit044-narrow-original-core-public-subset-v1','files':public_core,'excluded_private_paths':sorted(PRIVATE),'historical_private_paths':sorted(HISTORICAL_PRIVATE),'new_readme_manifest_and_addenda_required':True},indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':len(checks),'failed':0,'summary':report['summary']},sort_keys=True))
