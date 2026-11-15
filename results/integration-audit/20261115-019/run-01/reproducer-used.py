#!/usr/bin/env python3
"""Read approved pilot inputs and recorded requests; export hashes/counts only.

No backend is constructed, no request is sent, and no source/decision/profile
text is written. Inputs must be coordinator-released, label-free DEV artifacts.
The data root confines every referenced artifact; credentials are never opened.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import urllib.request


def sha(data):
    return hashlib.sha256(data).hexdigest()


def denied(*args, **kwargs):
    raise RuntimeError('NETWORK_DISABLED_BY_AUDIT')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--prepared-sha', required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    source, data_root, out = args.source_root.resolve(), args.data_root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.dont_write_bytecode = True
    socket.socket.connect = denied
    socket.create_connection = denied
    urllib.request.urlopen = denied
    pin = json.loads((source / 'AUDIT_SOURCE.json').read_text())
    before = {name: sha((source / name).read_bytes()) for name in pin['files']}
    assert before == pin['files']
    sys.path.insert(0, str(source))
    from autoresearch.taste.overnight.contracts import ProfileArtifact, digest, source_manifest
    from autoresearch.taste.overnight.consumer import prepare_payload
    from autoresearch.taste.overnight.runner import cache_key

    files = {}
    def read(path, expected=None):
        path = Path(path).resolve()
        path.relative_to(data_root)
        assert path.suffix == '.json', 'Only released JSON artifacts may be read'
        raw = path.read_bytes()
        actual = sha(raw)
        if expected is not None:
            assert actual == expected, 'Referenced artifact hash mismatch'
        files[str(path)] = actual
        return json.loads(raw)

    def ref(value):
        return read(value['path'], value['sha256'])

    batch = read(args.prepared, args.prepared_sha)
    assert batch['prepared'] is True and batch['code_sha'] == pin['source_commit']
    rows, profiles, paired = [], {}, {}
    for reference in batch['jobs']:
        packet = ref(reference)
        manifest, config = packet['manifest'], packet['config']
        assert manifest['stage'] == 'dev' and manifest['kind'] == 'predict'
        release, body = ref(packet['release']), ref(packet['profile'])
        assert release['scope'] == batch['release_scope']
        profile = ProfileArtifact.from_dict(body)
        assert profile.profile_id == manifest['profile_hash'] and profile.status == 'complete'
        method, researcher = profile.method_id, profile.researcher_id
        assert method in {'no_profile', 'name_only', 'raw_evidence', 'lexical_retrieval'}
        documents = release['sources']['documents']
        assert profile.documents_hash == digest(documents)
        assert source_manifest(documents) == profile.config['allowed_sources']
        by_doc = {doc['document_id']: doc for doc in documents}
        spans = []
        for passage in (profile.content or {}).get('passages', []):
            doc = by_doc[passage['document_id']]
            start, end = passage['start'], passage['end']
            assert 0 <= start < end <= len(doc['content'])
            assert passage['text'] == doc['content'][start:end]
            allowed = doc.get('permitted_spans')
            assert isinstance(allowed, list) and allowed
            outside = [i for i in range(start, end) if not any(s['start'] <= i < s['end'] for s in allowed)]
            spans.append({'document_id': passage['document_id'], 'start': start, 'end': end,
                          'text_sha256': sha(passage['text'].encode()), 'exact_source_substring': True,
                          'within_one_permitted_span': any(s['start'] <= start <= end <= s['end'] for s in allowed),
                          'outside_permitted_union_characters': len(outside),
                          'outside_permitted_union_nonwhitespace': sum(not doc['content'][i].isspace() for i in outside)})
        if method == 'no_profile':
            assert profile.content is None and profile.intentional_empty
        elif method == 'name_only':
            assert isinstance(profile.content, dict) and set(profile.content) == {'name'}
            assert profile.content['name'] == profile.config['researcher_name']
        else:
            assert spans and all(s['exact_source_substring'] for s in spans)
        profiles[profile.profile_id] = {'researcher_id': researcher, 'method_id': method,
            'allowed_source_manifest_hash': profile.allowed_source_manifest_hash,
            'documents_hash': profile.documents_hash, 'content_sha256': profile.content_sha256,
            'personalization_cap': profile.personalization_cap, 'passages': spans}
        index = {item['item_id']: item for item in release['items']}
        items = [index[item_id] for item_id in packet['item_ids']]
        assert digest(items) == manifest['items_hash']
        job_root = Path(batch['roots']['output']) / manifest['job_id']
        result = read(job_root / 'result.json')
        assert result['status'] == 'complete' and len(result['predictions']) == len(items)
        recorded = sorted((job_root / 'traces').glob('*-started.json'))
        assert len(recorded) == len(items), 'This comparison expects one recorded call per item'
        for item, result_row, trace_path in zip(items, result['predictions'], recorded):
            trace = read(trace_path)
            assert set(item) == {'item_id', 'researcher_id', 'context', 'options', 'option_order_id'}
            prepared = prepare_payload(profile, item['context'], item['options'], config)
            assert set(prepared['payload']) == {'context', 'options', 'personalization'}
            assert trace['prompt'] == prepared['prompt']
            assert trace['settings'] == dict(config['settings'], system=prepared['system'])
            assert sha(trace_path.read_bytes()) in result['trace_hashes']
            assert result_row['item_id'] == item['item_id'] and result_row['status'] == 'complete'
            assert result_row['rendered_profile_sha256'] == prepared['rendered_profile_sha256']
            assert result_row['payload_sha256'] == prepared['payload_sha256']
            assert result_row['cache_provenance'] == {'hit': False, 'key': cache_key(manifest, prepared['prompt'], trace['settings'])}
            personalization = prepared['payload']['personalization']
            if method == 'no_profile':
                assert personalization == ''
            elif method == 'name_only':
                assert json.loads(personalization) == profile.content
            assert len(personalization.encode()) <= profile.personalization_cap
            identity = digest({'context': item['context'], 'options': item['options']})
            key = (researcher, item['item_id'], item['option_order_id'])
            paired.setdefault(key, {})[method] = identity
            rows.append({'researcher_id': researcher, 'method_id': method, 'item_id': item['item_id'],
                'option_order_id': item['option_order_id'], 'job_id': manifest['job_id'],
                'profile_id': profile.profile_id, 'recorded_prompt_sha256': sha(trace['prompt'].encode()),
                'rendered_profile_sha256': prepared['rendered_profile_sha256'],
                'payload_sha256': prepared['payload_sha256'], 'context_options_sha256': identity,
                'personalization_bytes': len(personalization.encode()), 'exact_recorded_request_match': True,
                'no_extra_payload_channels': True, 'within_cap': True})
    paired_rows = []
    for (researcher, item_id, order), methods in sorted(paired.items()):
        assert set(methods) == {'no_profile', 'name_only', 'raw_evidence', 'lexical_retrieval'}
        assert len(set(methods.values())) == 1
        paired_rows.append({'researcher_id': researcher, 'item_id': item_id, 'option_order_id': order,
                            'methods': sorted(methods), 'context_options_sha256': next(iter(methods.values()))})
    assert len(rows) == 32 and len(paired_rows) == 8 and len(profiles) == 14
    for researcher in {p['researcher_id'] for p in profiles.values()}:
        same = [p for p in profiles.values() if p['researcher_id'] == researcher]
        assert len({p['allowed_source_manifest_hash'] for p in same}) == 1
        assert len({p['documents_hash'] for p in same}) == 1
    assert before == {name: sha((source / name).read_bytes()) for name in pin['files']}
    assert all(sha(Path(path).read_bytes()) == h for path, h in files.items())
    passage_rows = [row for p in profiles.values() for row in p['passages']]
    report = {'source_commit': pin['source_commit'], 'script_sha256': sha(Path(__file__).read_bytes()),
        'prepared_sha256': args.prepared_sha, 'source_snapshot_manifest_sha256': sha((source / 'AUDIT_SOURCE.json').read_bytes()),
        'source_files_unchanged': len(before), 'artifact_files_unchanged': len(files), 'profiles': profiles,
        'recorded_requests': rows, 'matched_decisions': paired_rows,
        'summary': {'requests': len(rows), 'profiles': len(profiles), 'matched_ordered_decisions': len(paired_rows),
                    'passages_across_distinct_profiles': len(passage_rows),
                    'passages_crossing_permitted_span_boundary': sum(not s['within_one_permitted_span'] for s in passage_rows),
                    'outside_union_characters_across_distinct_profiles': sum(s['outside_permitted_union_characters'] for s in passage_rows),
                    'outside_union_nonwhitespace_across_distinct_profiles': sum(s['outside_permitted_union_nonwhitespace'] for s in passage_rows),
                    'p1_prediction_requests': 0, 'audit_model_calls': 0},
        'limits': ['Recorded application requests, not independently observed provider wire traffic.',
                   'No preference labels, semantic correctness scoring, or efficacy assessment.',
                   'Actual source text was read from released DEV files only; exports contain hashes/counts/IDs, not text.',
                   'Whitespace outside the span union does not establish unauthorized substantive text.',
                   'Synthetic restricted-span failure is documented separately in package017.',
                   'Original artifact paths must remain available for full rerun; no raw data is republished.']}
    for name, value in [('report.json', report), ('input-hashes.json', files), ('invocation.json', {'argv': sys.argv, 'exit_code': 0})]:
        (out / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
