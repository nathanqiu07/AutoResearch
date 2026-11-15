"""Independently replay full-corpus provenance; fail closed without final artifacts.

Only validation.json is written, after all checks succeed. No model calls.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

WHO = ('nicholas_carlini', 'jacob_steinhardt')
METHODS = ('P2', 'P5', 'P8', 'SynthesizeMe', 'ICAI')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def parse(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    return json.loads(text)


def index(rows, key, label):
    result = {r[key]: r for r in rows}
    require(len(result) == len(rows), 'Duplicate ' + label)
    return result


def successful(directory):
    """Read actual latest attempt, not a prior validation boolean."""
    status = read(directory / 'status.json')
    attempt = directory / ('attempt-%03d' % status['attempt'])
    events = [json.loads(x) for x in (attempt / 'events.jsonl').read_text().splitlines() if x.strip()]
    require(status['returncode'] == 0 and events and events[-1].get('type') == 'turn.completed',
            'No successful final event: ' + str(directory))
    require(not any(e.get('type') == 'turn.failed' for e in events), 'Failed turn: ' + str(directory))
    errors = [e for e in events if e.get('type') == 'error']
    require(all(e.get('message', '').startswith('Reconnecting...') for e in errors),
            'Non-transport error: ' + str(directory))
    require(set(status.get('errors', [])) <= {'cli_error_event'}, 'Failed status: ' + str(directory))
    raw = (attempt / 'result.txt').read_text()
    require(bool(raw.strip()), 'Empty result: ' + str(directory))
    if status['status'] == 'complete':
        require(raw == (directory / 'result.txt').read_text(), 'Result differs from attempt')
        require(digest(raw) == status['result_sha256'], 'Result hash differs from status')
    return raw, (directory / 'prompt.txt').read_text()


def git(*args):
    return subprocess.check_output(['git', *args])


def validate(package, work, legacy):
    summary = {}
    all_excluded = {}
    exclusion_raw, exclusion_prompt = successful(work / 'exclusions')
    reviews = index(parse(exclusion_raw)['reviews'], 'doc_id', 'supplemental review')
    for who in WHO:
        target = package / who / 'full_corpus'
        catalog = read(target / 'sources.json')
        sources = index(catalog, 'source_id', 'source')
        inv = read(target / 'input_inventory.json')
        coverage = index(read(target / 'coverage.json'), 'source_id', 'coverage source')
        require(set(coverage) == set(sources), 'Coverage source mismatch')
        commits = {s['source_commit'] for s in catalog}
        require(commits == {inv['source_commit']}, 'Mixed source snapshots')
        for commit in commits:
            paths = git('ls-tree', '-r', '--name-only', commit, 'data/researchers/' + who + '/corpus').decode().splitlines()
            require(set(paths) == {s['path'] for s in catalog}, 'Git inventory mismatch: ' + who)
        bodies = {}
        segments = {}
        for sid, source in sources.items():
            raw = git('show', source['source_commit'] + ':' + source['path'])
            require(digest(raw) == source['sha256'] and len(raw) == source['bytes'], 'Source hash/bytes: ' + sid)
            text = raw.decode()
            body = '\n' + text.split('\n---\n', 1)[1] if text.startswith('---\n') else text
            bodies[sid] = body
            require(len(body.encode()) == source['body_bytes'], 'Body bytes: ' + sid)
            require(len(body.split()) == source['body_words'], 'Body words: ' + sid)
            require(coverage[sid]['source_sha256'] == source['sha256'], 'Coverage hash: ' + sid)
            end = byte_end = 0
            for n, segment in enumerate(sorted(source['segments'], key=lambda s: s['char_start']), 1):
                require(segment['doc_id'] == sid and segment['part'] == n and segment['parts'] == len(source['segments']), 'Segment identity: ' + sid)
                require(segment['char_start'] == end and segment['byte_start'] == byte_end, 'Partition gap: ' + sid)
                piece = body[segment['char_start']:segment['char_end']]
                end = segment['char_end']; byte_end += len(piece.encode())
                require(segment['byte_end'] == byte_end and digest(piece) == segment['sha256'], 'Segment hash: ' + sid)
                segments[sid + ':' + str(n)] = (segment, piece)
            if source['prior_status'] == 'included':
                require(end == len(body) and byte_end == len(body.encode()), 'Incomplete partition: ' + sid)
            else:
                require(not source['segments'], 'Supplemental source unexpectedly segmented')
                require(sid in reviews and source['review'] == reviews[sid], 'Missing/different supplemental review: ' + sid)
                require(json.dumps(text, ensure_ascii=False)[1:-1] in exclusion_prompt, 'Supplemental source absent from prompt: ' + sid)
                all_excluded[sid] = source
        receipts = index(read(target / 'extraction_receipts.json'), 'receipt_id', 'receipt')
        reconstructed = {}
        for rid, receipt in receipts.items():
            root = legacy if receipt['origin'] == 'legacy' else work
            require(root is not None, 'Need --legacy-root or work/legacy_root.json for original receipts')
            result = root / receipt['source_path']
            directory = result.parent.parent if result.parent.name.startswith('attempt-') else result.parent
            raw, prompt = successful(directory)
            require(result.read_text() == raw and digest(result.read_bytes()) == receipt['result_sha256'], 'Receipt result mismatch')
            require(digest(prompt) == receipt['prompt_sha256'], 'Receipt prompt mismatch')
            chunk = receipt['chunk']
            chunk_path = legacy / 'sources' / who / 'chunks' / (chunk + '.txt')
            chunk_text = chunk_path.read_text()
            require(digest(chunk_text) == receipt['source_sha256'] and chunk_text in prompt, 'Full chunk missing from prompt')
            for key, (segment, piece) in segments.items():
                if segment['chunk'] == chunk:
                    require(piece in chunk_text, 'Source segment missing from chunk: ' + key)
            valid = 0
            for item in parse(raw)['items']:
                sid = item.get('doc_id'); quote = item.get('quote', ''); claim = item.get('claim', '')
                matched = [key for key, (s, b) in segments.items() if s['doc_id'] == sid and s['chunk'] == chunk and quote and claim and quote in b]
                if not matched:
                    continue
                eid = digest(json.dumps(item, ensure_ascii=False, sort_keys=True))[:24]
                expected = reconstructed.setdefault(eid, dict(item, evidence_id=eid, receipts=[], segments=[]))
                expected['receipts'].append(rid)
                expected['segments'] = sorted(set(expected['segments']) | set(matched))
                valid += 1
            require(valid == receipt['valid_items'], 'Receipt item count mismatch')
        ledger = index([json.loads(x) for x in (target / 'evidence.jsonl').read_text().splitlines() if x.strip()], 'evidence_id', 'evidence')
        require(set(ledger) == set(reconstructed), 'Dropped or extra extracted evidence')
        for eid, item in ledger.items():
            canonical = dict(item, receipts=sorted(item['receipts']), segments=sorted(item['segments']))
            expected = dict(reconstructed[eid], receipts=sorted(reconstructed[eid]['receipts']))
            require(canonical == expected, 'Evidence content/provenance mismatch: ' + eid)
            require(item['quote'] in bodies[item['doc_id']], 'Invalid named-source quote')
        for sid, row in coverage.items():
            require(row['supplemental_review'] == sources[sid]['review'], 'Coverage review mismatch')
            require(row['evidence_items'] == sum(e['doc_id'] == sid for e in ledger.values()), 'Coverage count mismatch')
            require(len(row['segments']) == len(sources[sid]['segments']), 'Missing coverage segment')
            for original, segment in zip(sources[sid]['segments'], row['segments']):
                require(all(segment[k] == v for k, v in original.items()), 'Coverage segment altered')
                key = sid + ':' + str(segment['part'])
                expected_ids = {e for e, v in ledger.items() if key in v['segments']}
                require(set(segment['evidence_ids']) == expected_ids, 'Segment evidence mismatch')
                expected_receipts = {r for r, v in receipts.items() if v['chunk'] == segment['chunk']}
                require(expected_receipts and set(segment['receipt_ids']) == expected_receipts, 'Segment receipt mismatch')
                if not expected_ids:
                    require(bool(segment.get('disposition')) and bool(segment.get('no_evidence_notes')), 'Unexplained empty segment')
        packets = []; capsules = []; reduction = read(target / 'reduction_coverage.json')
        reductions = index(reduction, 'batch', 'reduction batch')
        files = inv['capsule_input_files']
        require(set(reductions) == {Path(f['file']).stem for f in files}, 'Reduction batch mismatch')
        for entry in files:
            path = work / 'capsule_inputs' / who / entry['file']
            require(digest(path.read_bytes()) == entry['sha256'], 'Capsule input hash mismatch')
            inputs = read(path); packets.extend(inputs)
            folder = work / 'capsule_calls' / who / path.stem
            raw, prompt = successful(folder)
            require(parse(prompt.split('FULL INPUT PACKETS:\n', 1)[1]) == inputs, 'Capsule prompt dropped/changed inputs')
            rows = parse(raw)['capsules']; require(rows == read(folder / 'validated.json'), 'Capsule output altered')
            pmap = index(inputs, 'packet_id', 'batch packet'); cmap = index(rows, 'packet_id', 'batch capsule')
            require(set(pmap) == set(cmap), 'Missing capsule')
            for pid, cap in cmap.items():
                require(cap['source_id'] == pmap[pid]['source_id'], 'Wrong capsule source')
                require(set(cap['decision_evidence_ids']) <= {e['evidence_id'] for e in pmap[pid]['evidence']}, 'Unknown capsule evidence')
            capsules.extend(rows)
            reduction_row = reductions[path.stem]
            require(reduction_row['input_sha256'] == digest(path.read_bytes()) and reduction_row['output_sha256'] == digest((folder / 'validated.json').read_bytes()), 'Reduction hash mismatch')
            require(reduction_row['packet_ids'] == [r['packet_id'] for r in rows], 'Reduction packets mismatch')
            require(reduction_row['input_evidence_ids'] == [e['evidence_id'] for p in inputs for e in p['evidence']], 'Reduction evidence mismatch')
        pmap = index(packets, 'packet_id', 'global packet'); index(capsules, 'packet_id', 'global capsule')
        require(set(pmap) == set(inv['packet_ids']) and {p['source_id'] for p in packets} == set(sources), 'Global packet/source mismatch')
        require(Counter(e['evidence_id'] for p in packets for e in p['evidence']) == Counter({e: 1 for e in ledger}), 'Evidence not included exactly once')
        require(Counter(e for r in reduction for e in r['input_evidence_ids']) == Counter({e: 1 for e in ledger}), 'Reduction evidence not exactly once')
        for packet in packets:
            source = sources[packet['source_id']]
            require(packet['source_review'] == source['review'] and packet['metadata'] == source['metadata'] and packet['attribution_notes'] == source['attribution_notes'], 'Packet source context changed')
            for item in packet['evidence']:
                require(item == {k: v for k, v in ledger[item['evidence_id']].items() if k not in ('receipts', 'segments')}, 'Packet evidence changed')
        require(capsules == read(target / 'capsules.json'), 'Final capsules differ from all batch outputs')
        profiles = {}
        for method in METHODS:
            folder = work / 'profile_calls' / who / method
            raw, prompt = successful(folder)
            data = parse(prompt.split('FULL CORPUS INPUT:\n', 1)[1])
            require(data == {'researcher': who, 'source_metadata': [{'source_id': c['source_id'], 'metadata': c['metadata'], 'review': c['review']} for c in catalog], 'all_source_capsules': capsules}, 'Profile dropped/changed synthesis inputs')
            text = raw.strip()
            if text.startswith('```markdown'):
                text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
            require((package / who / (method + '.md')).read_text() == text + '\n', 'Final profile differs from successful output')
            words = len(re.sub(r'\[[^\]]*\]', '', text).split())
            ids = set(re.findall(r'\b(?:research|other)__[A-Za-z0-9_-]+', text))
            require(words > 3000 and ids and ids <= set(sources), 'Invalid word count/citation IDs: ' + method)
            validated = read(folder / 'validated.json')
            require(validated == {'words_without_citations': words, 'cited_source_ids': sorted(ids), 'input_source_ids': sorted(sources), 'capsules_sha256': digest((target / 'capsules.json').read_bytes()), 'profile_sha256': digest(text + '\n')}, 'Final profile validation record mismatch')
            profiles[method] = {'words_without_citations': words, 'cited_sources': len(ids), 'sha256': digest(text + '\n')}
        summary[who] = {'sources': len(sources), 'segments': len(segments), 'evidence_items': len(ledger), 'capsules': len(capsules), 'profiles': profiles, 'source_commit': inv['source_commit']}
    require(set(reviews) == set(all_excluded), 'Supplemental review inventory mismatch')
    return {'status': 'passed', 'validated_at': datetime.now(timezone.utc).isoformat(), 'researchers': summary, 'limits': 'Checks exact provenance and full-input transport, not semantic correctness, exhaustive reading, or preference-prediction validity.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--legacy-root', type=Path)
    args = parser.parse_args()
    legacy = args.legacy_root
    if legacy is None and (args.work / 'legacy_root.json').exists():
        legacy = Path(read(args.work / 'legacy_root.json')['path'])
    result = validate(args.package, args.work, legacy)
    (args.package / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
