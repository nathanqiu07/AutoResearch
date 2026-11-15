#!/usr/bin/env python3
"""Independent metadata-only semantic handoff audit; no project imports/API calls.

Reads immutable Git objects and exactly hash-pinned approved producer artifacts.
Never writes raw requests, text, vectors, responses or profiles to the audit tree.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import posixpath
import subprocess
import sys

COMMIT = 'adad3ca120aabe80ca20351029c3f816b3a5fe35'
RUNTIME = '0dcd4b43b82a5a271d195e0bcc6b67695281f37c'
BASE = 'docs/overnight/gio-profile-20261115/handoffs/05/'
INDEX_HASH = '42aa4fe2ebe522b8bd38137e91e04c7cd3a20ca9480aadf0a4282d888a10ef91'
DISPATCH_HASH = 'b8e9f6278529ca93b94d961438ccb7df7cac6c2b0798a09e7175ed315d4ebaac'
SUMMARY_HASH = 'fa80d92d41da8874ece7fb45264da97039a9bcc81f36b06ae94d2b58c1ebc1e6'
RELEASES = {
 'neel_nanda': ('receipts/df8239e96e542be91ebb1cb63b1b7937c97bb4d052ca89f33f6d2f4fe2120b9d/preparation/job-0000/release.json', '25f43ce5ba0cc560654dd6d0dae98e810fc4845a42b0e4125d71f4e4c431af3c'),
 'chris_olah': ('receipts/df8239e96e542be91ebb1cb63b1b7937c97bb4d052ca89f33f6d2f4fe2120b9d/preparation/job-0008/release.json', '712d8190e5e9be352e4f77a2bba5e8605f0fd63d99dcbb541e2a0d9a27f65a7e'),
}


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canon(value).encode())


class ArchivedInputs:
    """Resolve only hash-pinned members of an explicitly supplied private copy."""
    def __init__(self, root, preservation):
        self.root = Path(root).resolve()
        receipt = json.loads(Path(preservation).read_text())
        self.records = receipt['files']
        self.aliases = receipt.get('recorded_path_aliases', {})
        self.read_files = {}

    @staticmethod
    def identity(path):
        # Recorded paths identify inputs; the original filesystem may be gone.
        if not PurePosixPath(path).is_absolute():
            raise ValueError('Recorded input path must be absolute')
        return posixpath.normpath(str(path))

    def read(self, kind, path, rev=None):
        if kind == 'external':
            identity = self.identity(path)
            identity = self.identity(self.aliases.get(identity, identity))
            matches = [r for r in self.records if r['kind'] == kind and
                       self.identity(r['path']) == identity]
        else:
            matches = [r for r in self.records if r['kind'] == kind and r['path'] == path and
                       (r['commit'] == rev or r['full_commit'] == rev)]
        if len(matches) != 1:
            raise ValueError('Archive lookup must identify one pinned record')
        record = matches[0]
        member = Path(record['archive_member'])
        if member.is_absolute() or '..' in member.parts:
            raise ValueError('Invalid archive member path')
        actual = (self.root / member).resolve()
        actual.relative_to(self.root)
        raw = actual.read_bytes()
        if sha(raw) != record['sha256']:
            raise ValueError('Private archive member hash mismatch')
        self.read_files[actual] = record['sha256']
        return raw, actual

    def verify_read_files(self):
        for path, expected in self.read_files.items():
            if sha(path.read_bytes()) != expected:
                raise ValueError('Private archive member hash mismatch at finish')
        return len(self.read_files)


def chunks_for(documents):
    chunks, seen = [], set()
    for doc in sorted(documents, key=lambda x: x['document_id']):
        for offset in range(0, len(doc['content']), 1200):
            window = doc['content'][offset:offset + 1200]
            text = window.strip()
            if text and text not in seen:
                seen.add(text)
                start = offset + len(window) - len(window.lstrip())
                chunks.append({'document_id': doc['document_id'], 'start': start, 'end': start + len(text), 'text': text})
    return chunks


def pack_ranked(chunks, vectors, cap=2048):
    # Independent offline reproduction of the documented pinned cosine order
    # and exact-prefix packing; content stays in memory and only its hash exits.
    units = []
    for vector in vectors:
        scale = max(abs(x) for x in vector)
        scaled = [x / scale for x in vector]
        norm = math.hypot(*scaled)
        units.append([x / norm for x in scaled])
    ranked = sorted(zip(chunks, units[1:]), key=lambda row: (
        -sum(a * b for a, b in zip(units[0], row[1])), row[0]['document_id'], row[0]['start']))
    selected = []
    for chunk, unused in ranked[:5]:
        if len(canon({'passages': selected + [chunk]}).encode()) <= cap:
            selected.append(chunk)
            continue
        low, high = 0, len(chunk['text'])
        while low < high:
            middle = (low + high + 1) // 2
            candidate = dict(chunk, text=chunk['text'][:middle], end=chunk['start'] + middle)
            if len(canon({'passages': selected + [candidate]}).encode()) <= cap:
                low = middle
            else:
                high = middle - 1
        if low and chunk['text'][:low].strip():
            text = chunk['text'][:low].rstrip()
            selected.append(dict(chunk, text=text, end=chunk['start'] + len(text)))
    return {'passages': selected}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--coordinator-root', type=Path, required=True,
                        help='Recorded coordinator root; need not exist in private-archive mode')
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--preservation', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if bool(args.archive_root) != bool(args.preservation):
        parser.error('--archive-root and --preservation must be supplied together')
    if args.archive_root and args.repo:
        parser.error('Choose private-archive mode or --repo, not both')
    if not args.archive_root and not args.repo:
        parser.error('Supply --repo or the private-archive arguments')
    archived = ArchivedInputs(args.archive_root, args.preservation) if args.archive_root else None
    coord = args.coordinator_root
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, git_reads, external_reads, bundle_rows, batch_rows = [], {}, {}, [], []
    external_locations = {}

    def check(name, condition, key=None):
        row = {'name': name, 'verified': bool(condition)}
        if key:
            row['binding_sha256'] = digest(key)
        checks.append(row)
        if not condition:
            raise AssertionError(name + ' failed; no raw input is emitted')

    def git_bytes(path, rev=COMMIT, expected=None):
        assert not path.startswith('/') and '..' not in Path(path).parts
        if archived:
            raw, unused = archived.read('git_object', path, rev)
        else:
            raw = subprocess.check_output(['/usr/bin/git', '-C', str(args.repo), 'show', rev + ':' + path],
                                          env={'PATH': '/usr/bin:/bin'}, stderr=subprocess.DEVNULL)
        key = rev + ':' + path
        git_reads[key] = {'commit': rev, 'path': path, 'sha256': sha(raw), 'size_bytes': len(raw)}
        if expected:
            check('git_blob_expected_hash', sha(raw) == expected, key)
        return raw

    def git_json(path, expected=None):
        return json.loads(git_bytes(path, expected=expected))

    def external(path, expected):
        # Call sites supply only the fixed release paths or paths in the pinned
        # dispatch/index. Never traverse env/credential/private-label fields.
        if archived:
            identity = archived.identity(path)
            path = Path(archived.aliases.get(identity, identity))
        else:
            path = Path(path).resolve(strict=True)
        assert path.suffix == '.json'
        if archived:
            raw, actual = archived.read('external', str(path))
        else:
            actual, raw = path, path.read_bytes()
        check('external_expected_hash', sha(raw) == expected, str(path))
        external_reads[str(path)] = {'path': str(path), 'sha256': sha(raw), 'size_bytes': len(raw)}
        external_locations[str(path)] = actual
        return json.loads(raw)

    index = git_json(BASE + 'live-embeddings-v1/index.json', INDEX_HASH)
    proposal = git_json(BASE + '005-embedding-proposal.json', index['proposal_sha256'])
    owner_summary = git_json(BASE + 'live-embeddings-v1/producer-summary.json', SUMMARY_HASH)
    summary = external(coord / 'embedding-v1/summary.json', SUMMARY_HASH)
    dispatch = external(coord / 'embedding-v1/dispatch.json', DISPATCH_HASH)
    handoff = git_json(BASE + '007-live-bundles-ready.json')
    construction = git_json(BASE + 'live-embeddings-v1/construction-check.json')
    helper = git_bytes('autoresearch/taste/overnight/retrieval.py')
    frozen_helper = git_bytes('autoresearch/taste/overnight/retrieval.py', RUNTIME)
    assembler = git_bytes(BASE + 'assemble_embeddings.py')
    check('frozen_retrieval_implementation_same', helper == frozen_helper and sha(helper) == index['retrieval_implementation_hash'] == proposal['retrieval_implementation_hash'])
    check('assembler_code_labels_byte_identical', assembler == git_bytes(BASE + 'assemble_embeddings.py', 'cd3de73') == git_bytes(BASE + 'assemble_embeddings.py', index['code_sha']))
    check('producer_summary_and_dispatch_binding', owner_summary == summary and digest(dispatch) == summary['dispatch_sha256'] and
          dispatch['runtime_commit'] == summary['runtime_commit'] == RUNTIME and dispatch['script_sha256'] == summary['script_sha256'])
    check('proposal_semantic_hash', proposal['proposal_sha256'] == digest({k: v for k, v in proposal.items() if k != 'proposal_sha256'}))
    check('producer_settings_and_counts', summary['status'] == 'complete' and summary['attempted_calls'] == index['producer_calls'] == dispatch['max_calls'] == 2 and
          summary['reserved_usd'] == 0 and index['assembly_model_calls'] == 0 and
          summary['model'] == dispatch['model'] == index['model'] and summary['dimensions'] == dispatch['dimensions'] == index['dimensions'] == 1536)
    check('handoff_output_hashes', all(sha(git_bytes(x['location'])) == x['sha256'] for x in handoff['outputs']))
    check('construction_scope', construction['runtime_commit'] == RUNTIME and construction['new_model_calls'] == 0 and construction['n_complete'] == 28 and construction['personalization_cap'] == 2048)
    constructed = {(x['researcher_id'], x['item_id'], x['option_order_id']): x for x in construction['rows']}
    unique_cost, unique_usage_refs, seen_items = {}, {}, set()
    for batch in index['batches']:
        researcher = batch['researcher_id']
        mapping = next(x for x in proposal['batches'] if x['researcher_id'] == researcher)
        entry = next(x for x in dispatch['requests'] if x['request_id'] == batch['producer_job_id'])
        recorded_request = next(x for x in summary['requests'] if x['request_id'] == batch['producer_job_id'])
        manifest = git_json(batch['assembly_manifest_path'], batch['assembly_manifest_sha256'])
        receipt = external(batch['receipt_path'], batch['receipt_sha256'])
        response = external(batch['response_path'], batch['response_sha256'])
        request = external(entry['packet_path'], entry['packet_sha256'])
        release_path, release_hash = RELEASES[researcher]
        release = external(coord / release_path, release_hash)
        settings = {k: request[k] for k in ('model', 'dimensions', 'encoding_format')}
        inputs = request['input']
        check('five_artifact_hash_bindings', manifest['input_file_sha256'] == {
              'proposal': index['proposal_sha256'], 'request': entry['packet_sha256'], 'receipt': batch['receipt_sha256'],
              'response': batch['response_sha256'], 'release': release_hash}, researcher)
        check('assembly_source_pins', manifest['assembler_sha256'] == sha(assembler) and manifest['batch_sha256'] == digest(mapping) and
              manifest['retrieval_implementation_hash'] == sha(helper) and manifest['model_calls'] == 0, researcher)
        check('request_proposal_dispatch_binding', set(request) == {'model', 'dimensions', 'encoding_format', 'input'} and
              settings == proposal['candidate_settings'] == {k: dispatch[k] for k in settings} and
              digest(settings) == mapping['settings_sha256'] and sha(git_bytes(BASE + '005-embedding-proposal.json')) == manifest['input_file_sha256']['proposal'] and
              entry['packet_sha256'] == mapping['request_sha256'] == receipt['packet_sha256'] and
              digest(inputs) == mapping['ordered_input_sha256'] == entry['input_sha256'] == receipt['input_sha256'], researcher)
        check('request_order_and_size', len(inputs) == len(set(inputs)) == mapping['n_inputs'] == receipt['count'] and
              sum(len(x.encode()) for x in inputs) == mapping['input_text_utf8_bytes'] and max(len(x.encode()) for x in inputs) == mapping['max_input_utf8_bytes'], researcher)
        check('receipt_summary_identity', receipt['status'] == recorded_request['status'] == 'complete' and
              receipt['request_id'] == recorded_request['request_id'] == batch['producer_job_id'] and
              receipt['runtime_commit'] == RUNTIME and receipt['script_sha256'] == dispatch['script_sha256'] and
              all(receipt[k] == v for k, v in settings.items()) and recorded_request['receipt_sha256'] == batch['receipt_sha256'] and
              recorded_request['response_sha256'] == receipt['response_sha256'] == batch['response_sha256'] and recorded_request['reserved_usd'] == 0, researcher)
        tokens = response['usage']['prompt_tokens']
        check('response_usage_matches_receipt', response['model'] == request['model'] and isinstance(tokens, int) and not isinstance(tokens, bool) and
              response['usage']['total_tokens'] == tokens and receipt['usage'] == recorded_request['usage'] ==
              {'prompt_tokens': tokens, 'total_tokens': tokens, 'known_input_tokens': tokens, 'complete': True} and tokens == batch['input_tokens'], researcher)
        cost = Decimal(tokens) * Decimal(dispatch['rate_usd_per_million_input']) / Decimal(1000000)
        check('known_cost_matches_declared_rate', cost == Decimal(str(receipt['known_usage_usd'])) == Decimal(str(recorded_request['known_usage_usd'])) == Decimal(str(batch['estimated_usd'])), researcher)
        raw_vectors = {x['index']: x['embedding'] for x in response['data']}
        receipt_vectors = {x['index']: x['embedding'] for x in receipt['vectors']}
        check('all_indexed_vectors_exact', len(response['data']) == len(receipt['vectors']) == len(inputs) and set(raw_vectors) == set(range(len(inputs))) and
              raw_vectors == receipt_vectors and all(len(v) == 1536 and any(v) and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v) for v in raw_vectors.values()), researcher)
        docs = release['sources']['documents']
        source_manifest = sorted([{'document_id': d['document_id'], 'content_sha256': d['content_sha256']} for d in docs], key=lambda d: d['document_id'])
        source_hash = digest(source_manifest)
        check('source_and_release_hash_binding', source_manifest == release['sources']['source_manifest'] and
              all(sha(d['content'].encode()) == d['content_sha256'] for d in docs) and
              source_hash == release['sources']['allowed_source_manifest_hash'] == manifest['allowed_source_manifest_hash'] == mapping['allowed_source_manifest_hash'] and
              digest(release) == mapping['release_semantic_sha256'] and release_hash == mapping['release_sha256'] and
              digest(release['items']) == release['items_sha256'] == mapping['items_sha256'], researcher)
        chunks = chunks_for(docs)
        reference = {'producer_job_id': receipt['request_id'], 'receipt_sha256': batch['receipt_sha256'],
                     'production_usage_sha256': digest({'usage': receipt['usage'], 'known_usage_usd': receipt['known_usage_usd']}),
                     'accounting': 'charged_once_by_producer_not_per_derived_bundle'}
        check('single_usage_reference', manifest['production_usage_reference'] == reference, researcher)
        unique_cost[receipt['request_id']] = cost
        unique_usage_refs[receipt['request_id']] = reference
        by_key = {(x['item_id'], x['option_order_id']): x for x in release['items']}
        mappings = {(x['item_id'], x['option_order_id']): x for x in mapping['decision_mappings']}
        index_rows = [x for x in index['items'] if x['researcher_id'] == researcher]
        check('exact_decision_coverage', len(index_rows) == len(by_key) == len(mappings) == len(manifest['bundles']) == mapping['n_decision_bundles'] == 14 and
              {(x['item_id'], x['option_order_id']) for x in index_rows} == set(by_key) == set(mappings), researcher)
        roles = {i: set() for i in range(len(inputs))}
        for ix in index_rows:
            key = (ix['item_id'], ix['option_order_id'])
            item, map_row = by_key[key], mappings[key]
            check('label_free_item', set(item) == {'context', 'item_id', 'option_order_id', 'options', 'researcher_id'} and item['researcher_id'] == researcher, key)
            decision = {'context': item['context'], 'options': item['options']}
            logical = [canon(decision)] + [x['text'] for x in chunks]
            indices = map_row['response_indices']
            check('query_source_order_mapping', len(indices) == len(logical) and all(isinstance(i, int) and not isinstance(i, bool) and i in raw_vectors for i in indices) and
                  [inputs[i] for i in indices] == logical and map_row['ordered_logical_input_hashes'] == [sha(x.encode()) for x in logical] and
                  map_row['decision_sha256'] == ix['decision_sha256'] == digest(decision), key)
            for position, i in enumerate(indices):
                roles[i].add(canon({'kind': 'decision_query', 'decision_sha256': digest(decision)} if position == 0 else {'kind': 'approved_chunk', 'chunk_index': position - 1}))
            bundle = git_json(ix['bundle_path'], ix['file_sha256'])
            expected_request = {'source_manifest_hash': source_hash, 'researcher_id': researcher, 'chunk_chars': 1200,
                                'implementation_hash': sha(helper), 'query_sha256': digest(decision), 'chunk_hashes': [digest(c) for c in chunks],
                                'input_hashes': [sha(x.encode()) for x in logical], 'input_policy': 'canonical-decision-json-then-exact-chunk-text-v1', 'similarity': 'cosine-v1'}
            usage = {'mode': 'live', 'producer_job_id': receipt['request_id'], 'response_sha256': batch['response_sha256'],
                     'receipt_sha256': batch['receipt_sha256'], 'request_sha256': entry['packet_sha256'], 'settings_sha256': digest(settings),
                     'response_indices': indices, 'decision_item_sha256': digest(key), 'production_usage_reference': reference}
            expected = {'schema_version': 'approved-embedding-bundle-v1', 'request': expected_request, 'model': request['model'],
                        'dimensions': 1536, 'vectors': [raw_vectors[i] for i in indices], 'usage': usage}
            expected['bundle_sha256'] = digest(expected)
            check('entire_bundle_matches_raw_response_slice', bundle == expected and ix['bundle_sha256'] == expected['bundle_sha256'] and ix['producer_job_id'] == receipt['request_id'], key)
            m = next(x for x in manifest['bundles'] if x['bundle_sha256'] == bundle['bundle_sha256'])
            check('bundle_assembly_entry_matches', m == {'file': Path(ix['bundle_path']).name, 'file_sha256': ix['file_sha256'],
                  'bundle_sha256': bundle['bundle_sha256'], 'decision_sha256': digest(decision), 'decision_item_sha256': digest(key)}, key)
            # This reconstruction checks owner-reported content/cap hashes only;
            # it does not run a consumer or evaluate semantic preference quality.
            content = pack_ranked(chunks, bundle['vectors'])
            built = constructed[(researcher,) + key]
            check('construction_content_reproduces', built['bundle_sha256'] == bundle['bundle_sha256'] and built['status'] == 'complete' and
                  digest(content) == built['content_sha256'] and len(canon(content).encode()) == built['rendered_bytes'] <= 2048 and
                  len(content['passages']) == built['selected_passages'], key)
            seen_items.add((researcher,) + key)
            bundle_rows.append({'researcher_id': researcher, 'decision_item_sha256': digest(key), 'decision_sha256': digest(decision),
                                'bundle_sha256': bundle['bundle_sha256'], 'file_sha256': ix['file_sha256'],
                                'producer_job_id': receipt['request_id'], 'response_indices': indices, 'dimensions': 1536,
                                'vectors_sha256': digest(bundle['vectors']), 'source_manifest_hash': source_hash,
                                'content_sha256': digest(content), 'rendered_bytes': built['rendered_bytes'],
                                'production_usage_sha256': reference['production_usage_sha256']})
        records = {x['index']: x for x in mapping['input_records']}
        check('all_request_input_roles_exact', len(records) == len(mapping['input_records']) == len(inputs) and set(records) == set(roles) and all(
              roles[i] and records[i]['input_sha256'] == sha(inputs[i].encode()) and records[i]['utf8_bytes'] == len(inputs[i].encode()) and
              len(records[i]['roles']) == len(roles[i]) and {canon(x) for x in records[i]['roles']} == roles[i] for i in roles), researcher)
        batch_rows.append({'researcher_id': researcher, 'producer_job_id': receipt['request_id'], 'input_count': len(inputs),
                           'query_count': len(by_key), 'chunk_count': len(chunks), 'input_tokens': tokens,
                           'estimated_producer_usd': str(cost), 'receipt_sha256': batch['receipt_sha256'],
                           'response_sha256': batch['response_sha256'], 'request_sha256': entry['packet_sha256'],
                           'query_first_exact_response_mapping': True, 'production_usage_reference': reference})
    check('exact_total_bundle_coverage', len(bundle_rows) == len(seen_items) == len(index['items']) == 28)
    total = sum(unique_cost.values(), Decimal(0))
    check('production_cost_deduplicated_once', len(unique_cost) == len(unique_usage_refs) == 2 and
          total == Decimal(str(summary['known_usage_usd'])) == Decimal(str(index['estimated_producer_usd'])) and
          Counter(x['producer_job_id'] for x in bundle_rows) == {key: 14 for key in unique_cost})
    for path, record in external_reads.items():
        check('external_file_unchanged', sha(external_locations[path].read_bytes()) == record['sha256'])
    archive_member_rechecks = archived.verify_read_files() if archived else None
    report = {'audit': 'semantic-runtime-21', 'reviewer_role': '/root/parallel_gap_audit', 'release_commit': COMMIT,
              'runtime_commit': RUNTIME, 'index_sha256': INDEX_HASH, 'reader_sha256': sha(Path(__file__).read_bytes()),
              'input_mode': 'private_archive' if archived else 'original_git_and_files',
              'archive_members_rechecked_at_finish': archive_member_rechecks,
              'argv': sys.argv,
              'checks': checks, 'check_counts': {'verified': len(checks), 'failed': 0}, 'batches': batch_rows, 'bundles': bundle_rows,
              'summary': {'producer_calls_recorded': 2, 'derived_bundles': 28, 'indexed_vectors': sum(x['input_count'] for x in batch_rows),
                          'dimensions': 1536, 'producer_tokens': sum(x['input_tokens'] for x in batch_rows), 'estimated_producer_usd': str(total),
                          'unique_production_usage_references': 2, 'reproduced_construction_content_hashes': 28, 'audit_model_calls': 0},
              'git_inputs': list(git_reads.values()), 'external_inputs': list(external_reads.values()),
              'recorded_campaign_ledger_summary': summary['campaign_ledger'],
              'limits': ['Exact request/response/bundle consistency, not authenticated provider origin or prediction quality.',
                         'Usage is counted once per unique producer receipt in the published accounting; live ledger debit uniqueness is not independently inspected.',
                         'No live ledger connection, labels, environment/key access, network, backend construction or project-code import.',
                         'Raw source/query text, vectors and responses stay in approved originals or a verified private copy; only metadata/hashes/counts are exported.',
                         'Construction hashes are independently reproduced with the pinned algorithm, not actual downstream prediction execution.',
                         'Declared cost rate is used as a fixture; current price/provider invoice verification is out of scope.',
                         'General permitted-span policy is outside this binding audit and remains covered by audits017/019/020.']}
    (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'summary': report['summary'], 'check_counts': report['check_counts']}, indent=2))


if __name__ == '__main__':
    main()
