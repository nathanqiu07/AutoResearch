"""Freeze all source records and verified extraction evidence; no model calls."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

WHO = ('nicholas_carlini', 'jacob_steinhardt')
def sha(x): return hashlib.sha256(x if isinstance(x, bytes) else x.encode()).hexdigest()
def read_json(p): return json.loads(Path(p).read_text())
def parse_result(p):
    t=Path(p).read_text().strip()
    if t.startswith('```'): t=t.split('\n',1)[1].rsplit('```',1)[0]
    return json.loads(t)
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--legacy-root',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--package',type=Path,required=True);ap.add_argument('--audits',type=Path,required=True);a=ap.parse_args()
    rev=subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip()
    exdir=a.work/'exclusions';exstatus=read_json(exdir/'status.json')
    assert exstatus['status']=='complete' and exstatus['returncode']==0
    assert sha((exdir/'result.txt').read_bytes())==exstatus['result_sha256']
    exevents=[json.loads(l) for l in (exdir/f'attempt-{exstatus["attempt"]:03d}'/'events.jsonl').read_text().splitlines() if l.strip()]
    assert exevents[-1]['type']=='turn.completed'
    exclusion_result=parse_result(exdir/'result.txt'); reviews={r['doc_id']:r for r in exclusion_result['reviews']}
    expected_exclusions={d['doc_id'] for w in WHO for d in read_json(a.legacy_root/'sources'/w/'manifest.json')['documents'] if d['status']!='included'}
    assert set(reviews)==expected_exclusions and len(exclusion_result['reviews'])==len(expected_exclusions)
    ex_prompt=(exdir/'prompt.txt').read_text()
    for w in WHO:
        for d in read_json(a.legacy_root/'sources'/w/'manifest.json')['documents']:
            if d['status']!='included': assert json.dumps(Path(d['snapshot_path']).read_text(),ensure_ascii=False)[1:-1] in ex_prompt
    no_evidence_dispositions={
      'research__the_malicious_use_of_artificial_intelligence_forec_14e0d91b:2':'Bibliography-only final segment; independently inspected and recognized in all three legacy extraction coverage notes.',
      'research__scalable_extraction_of_training_data_from_producti_9e0b9a67:2':'Extracted training-data examples and third-party text; independently inspected and recognized in all three legacy extraction coverage notes, not attributable researcher preferences.',
      'research__vishalmry_audio_adversarial_attack_7bc80c08:1':'Third-party reproduction repository explicitly disclaims being paper code; reviewed but not attributable to Carlini.'}

    for who in WHO:
        m=read_json(a.legacy_root/'sources'/who/'manifest.json');docs={d['doc_id']:d for d in m['documents']};chunks={Path(c['path']).stem:c for c in m['chunks']}
        audit=read_json(a.audits/('carlini_coverage_audit.json' if who==WHO[0] else 'steinhardt_coverage_audit.json'))
        current_paths=subprocess.check_output(['git','ls-tree','-r','--name-only',rev,f'data/researchers/{who}/corpus'],text=True).splitlines()
        assert {Path(x).stem for x in current_paths}==set(docs),('source inventory drift',who)
        bodies={};catalog=[]
        for sid,d in docs.items():
            raw=Path(d['snapshot_path']).read_bytes();assert sha(raw)==d['source_sha256']
            text=raw.decode();body='\n'+text.split('\n---\n',1)[1] if text.startswith('---\n') else text;bodies[sid]=body
            path=f'data/researchers/{who}/corpus/{sid}.txt'
            assert raw==subprocess.check_output(['git','show',rev+':'+path])
            if d['status']=='included':
                assert sha(body)==d['body_sha256'];parts=sorted(d['segments'],key=lambda s:s['char_start']);end=0
                for s in parts:
                    assert s['char_start']==end;end=s['char_end'];assert sha(body[s['char_start']:end])==s['sha256']
                assert end==len(body)
            catalog.append(dict(source_id=sid,path=path,sha256=sha(raw),bytes=len(raw),body_bytes=len(body.encode()),body_words=len(body.split()),metadata=d['metadata'],attribution_notes=d['attribution_notes'],source_commit=rev,source_blob_url=f'https://github.com/nathanqiu07/AutoResearch/blob/{rev}/{path}',prior_status=d['status'],review=reviews.get(sid),segments=[{k:v for k,v in s.items() if k!='chunk_path'}|{'chunk':Path(s['chunk_path']).stem} for s in d['segments']]))
        candidates=[];seen=set()
        for r in audit['reusable_reports']:
            p=r.get('terminal_result_path',r.get('result_path'))
            if p in seen: continue
            seen.add(p);candidates.append((Path(p),Path(r['status_path']),r['chunk'],'legacy'))
        if who==WHO[0]:
            for n in range(68,72):
                dr=a.work/'repairs'/who/f'chunk_{n:03d}';st=read_json(dr/'status.json')
                assert st['status']=='complete',('repair incomplete',dr,st)
                candidates.append((dr/'result.txt',dr/'status.json',f'chunk_{n:03d}','repair'))
        ledger={};receipts=[];notes={k:[] for k in chunks}
        for result,statuspath,chunk,origin in candidates:
            status=read_json(statuspath);ct=Path(chunks[chunk]['path']).read_text();assert sha(ct)==chunks[chunk]['sha256']
            prompt=(statuspath.parent/'prompt.txt').read_text();assert ct in prompt
            assert status['returncode']==0
            ev=statuspath.parent/f'attempt-{status["attempt"]:03d}'/'events.jsonl'
            events=[json.loads(l) for l in ev.read_text().splitlines() if l.strip()]
            terminal=[e for e in events if e.get('type') in ('turn.completed','turn.failed')];assert terminal and terminal[-1]['type']=='turn.completed'
            value=parse_result(result);rid=sha(str(result.relative_to(a.legacy_root)) if origin=='legacy' else str(result.relative_to(a.work)))[:16]
            valid=0;rejected=[]
            for i,item in enumerate(value['items']):
                sid=item.get('doc_id');q=item.get('quote','');claim=item.get('claim','')
                matching=[]
                if sid in bodies and q and claim:
                    matching=[s for s in chunks[chunk]['segments'] if s['doc_id']==sid and q in bodies[sid][s['char_start']:s['char_end']]]
                if not matching: rejected.append({'item_index':i,'reason':'quote_not_in_named_segment'});continue
                ident=sha(json.dumps(item,ensure_ascii=False,sort_keys=True))[:24]
                if ident not in ledger:ledger[ident]=dict(item,evidence_id=ident,receipts=[],segments=[])
                ledger[ident]['receipts'].append(rid)
                for s in matching:
                    k=f'{sid}:{s["part"]}'
                    if k not in ledger[ident]['segments']:ledger[ident]['segments'].append(k)
                valid+=1
            notes[chunk].extend(value.get('coverage_notes',[]))
            receipts.append(dict(receipt_id=rid,origin=origin,chunk=chunk,source_sha256=sha(ct),prompt_sha256=sha(prompt),result_sha256=sha(result.read_bytes()),original_status=status['status'],returncode=0,terminal_event='turn.completed',valid_items=valid,rejected_items=rejected,source_path=str(result.relative_to(a.legacy_root)) if origin=='legacy' else str(result.relative_to(a.work))))
        assert {r['chunk'] for r in receipts}==set(chunks)
        coverage=[]
        for c in catalog:
            sid=c['source_id'];items=[v for v in ledger.values() if v['doc_id']==sid]
            segs=[]
            for s in c['segments']:
                k=f'{sid}:{s["part"]}';ids=[v['evidence_id'] for v in items if k in v['segments']]
                row=dict(s,evidence_ids=ids,receipt_ids=[r['receipt_id'] for r in receipts if r['chunk']==s['chunk']])
                if not ids:
                    row['no_evidence_notes']=list(dict.fromkeys(notes[s['chunk']]))
                    assert row['no_evidence_notes'] and k in no_evidence_dispositions,('unexplained empty segment',k)
                    row['disposition']=no_evidence_dispositions[k]
                segs.append(row)
            coverage.append(dict(source_id=sid,source_sha256=c['sha256'],evidence_items=len(items),segments=segs,supplemental_review=c['review']))
        target=a.package/who/'full_corpus';save(target/'sources.json',catalog);save(target/'coverage.json',coverage);save(target/'extraction_receipts.json',receipts)
        with (target/'evidence.jsonl').open('w') as f:
            for item in sorted(ledger.values(),key=lambda v:(v['doc_id'],v['evidence_id'])):f.write(json.dumps(item,ensure_ascii=False)+'\n')
        # Every source gets a capsule, including reviewed unusable records. Every accepted
        # evidence item is assigned exactly once. Large sources are split, never truncated.
        packets=[]
        for c in catalog:
            items=[{k:v for k,v in x.items() if k not in ('receipts','segments')} for x in ledger.values() if x['doc_id']==c['source_id']]
            groups=[[]]
            for item in items:
                if groups[-1] and len(json.dumps(groups[-1]+[item],ensure_ascii=False))>300000:groups.append([])
                groups[-1].append(item)
            for n,group in enumerate(groups):
                packets.append(dict(packet_id=f'{c["source_id"]}:{n+1}/{len(groups)}',source_id=c['source_id'],metadata=c['metadata'],attribution_notes=c['attribution_notes'],source_review=c['review'],evidence=group,no_evidence_notes=[x for s in coverage[catalog.index(c)]['segments'] for x in s.get('no_evidence_notes',[])]))
        batches=[[]]
        for packet in packets:
            if batches[-1] and (len(json.dumps(batches[-1]+[packet],ensure_ascii=False))>380000 or len(batches[-1])>=8):batches.append([])
            batches[-1].append(packet)
        for n,b in enumerate(batches):save(a.work/'capsule_inputs'/who/f'batch_{n:03d}.json',b)
        save(target/'input_inventory.json',dict(source_commit=rev,source_files=len(catalog),legacy_included=m['included_documents'],body_words=m['included_body_words'],chunks=len(chunks),segments=sum(len(c['segments']) for c in catalog),verified_unique_evidence_items=len(ledger),capsule_packets=len(packets),capsule_batches=len(batches),capsule_input_files=[{'file':f'batch_{n:03d}.json','sha256':sha((a.work/'capsule_inputs'/who/f'batch_{n:03d}.json').read_bytes())} for n in range(len(batches))],packet_ids=[p['packet_id'] for p in packets],evidence_ids=sorted(ledger),excluded_records_reviewed=len([c for c in catalog if c['review'] is not None])))
        print(who,len(catalog),'sources',len(ledger),'evidence items',len(batches),'capsule batches',flush=True)
if __name__=='__main__':main()
