"""Synthetic frozen-runner quote integration audit; no provider/backend imports used live."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import unicodedata

COMMIT = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
CONTRACT = '0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43'
QUOTE = 'Café 🧪: test  twice.'


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def blocked(*args, **kwargs):
    raise RuntimeError('network/process operation prohibited by synthetic audit')


class Budget:
    def summary(self):
        return {'input_tokens': 0, 'output_tokens': 0}


class RecordingExtractor:
    name = 'offline-audit030'
    label = 'offline-audit030-recording-extractor'
    model = 'synthetic-response'
    base_url = ''

    def __init__(self, response):
        self.response = response
        self.calls = []
        self.budget = Budget()

    def complete(self, prompt, **settings):
        self.calls.append({'prompt': prompt, 'settings': settings})
        return self.response


def document(text, identifier='target-doc', researcher='synthetic-target', ranges=None):
    result = {'document_id': identifier, 'researcher_id': researcher,
              'content': text, 'content_sha256': sha(text.encode()),
              'split_eligibility': 'fit', 'metadata_not_sent': 'OUTSIDE_METADATA_SENTINEL'}
    if ranges is not None:
        result['permitted_spans'] = [dict(start=a, end=b, speaker=researcher) for a, b in ranges]
    return result


def source(quote=QUOTE, identifier='target-doc'):
    return {'document_id': identifier, 'quote': quote}


def statement(src):
    return {'text': 'Synthetic stated preference.', 'kind': 'preference',
            'evidence_status': 'explicit', 'conditions': None, 'date': None, 'sources': [src]}


def response_for(method, src, summary, principles):
    st = statement(src)
    claim = {k: v for k, v in st.items() if k not in ('conditions', 'date')}
    principle = {'id': 'p1', 'claim': claim, 'context': None, 'date': None,
                 'uncertainty': 'not_quantified', 'exceptions': [], 'conflicts_with': []}
    if method in ('P1', 'P2'):
        return {'summary': [st]}
    if method == 'P3':
        answers = {k: {'status': 'unknown', 'statements': []} for k in summary.QUESTIONS}
        answers[next(iter(answers))] = {'status': 'supported', 'statements': [st]}
        return {'answers': answers}
    if method == 'P4':
        return {'principles': [principle], 'rejected': []}
    if method == 'P5':
        return {'rules': [{'id': 'r1', 'when': copy.deepcopy(claim), 'prefer': claim,
                          'over': None, 'unless': [], 'date': None,
                          'uncertainty': 'not_quantified', 'conflicts_with': []}], 'rejected': []}
    if method == 'P6':
        hierarchy = {k: [] for k in principles.HIERARCHY_KEYS}
        hierarchy[next(iter(hierarchy))] = [principle]
        return {'hierarchy': hierarchy, 'rejected': []}
    if method == 'P7':
        return {'contrasts': [{'relation': 'different', 'target': st,
                              'peer': statement(source('Peer prefers replication.', 'peer-doc'))}]}
    return {'hypotheses': [{'id': 'h1', 'statement': st, 'weight': None}], 'relations': []}


def citations(value):
    if isinstance(value, list):
        for entry in value:
            yield from citations(entry)
    if isinstance(value, dict):
        if 'document_id' in value or 'quote' in value:
            yield value
        else:
            for entry in value.values():
                yield from citations(entry)


def first_statement(value):
    if isinstance(value, dict):
        if 'text' in value and 'sources' in value:
            return value
        for entry in value.values():
            found = first_statement(entry)
            if found is not None:
                return found
    if isinstance(value, list):
        for entry in value:
            found = first_statement(entry)
            if found is not None:
                return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--source-manifest', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    pin = json.loads(args.source_manifest.read_text())
    assert pin['source_commit'] == COMMIT
    for path, expected in pin['files'].items():
        assert sha((root / path).read_bytes()) == expected, path
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'reader-used.py').write_bytes(Path(__file__).read_bytes())
    socket.socket = socket.create_connection = socket.getaddrinfo = blocked
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import subprocess
    subprocess.Popen = blocked
    from autoresearch.taste.overnight import contracts as c, consumer, runner
    from autoresearch.taste.overnight import profiles_summary as summary, profiles_principles as principles
    driver_path = root / 'docs/overnight/gio-profile-20261115/control/run_batch.py'
    spec = importlib.util.spec_from_file_location('audit030_frozen_driver', driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    registrations = {}
    for method in ['P' + str(i) for i in range(1, 9)]:
        family, hook = (('profiles_summary', 'register_summary_builders') if method in ('P1', 'P2', 'P3')
                        else ('profiles_principles', 'register_principle_builders') if method in ('P4', 'P5', 'P6')
                        else ('profiles_hypotheses', 'register_hypotheses_builders'))
        builder = driver._register({'module': 'autoresearch.taste.overnight.' + family, 'function': hook}, method)
        registrations[method] = {'module': builder.function.__module__, 'function': builder.function.__name__,
            'prompt_version': builder.prompt_version, 'prompt_sha256': builder.prompt_sha256,
            'method_implementation_hash': builder.implementation_hash, 'allows_empty': builder.allows_empty}
    renderer = consumer.implementation_hash()
    handoff = json.loads((root / 'docs/overnight/gio-profile-20261115/handoffs/08/002-METHOD_READY_QUOTE_ONLY.json').read_text())
    assert renderer == handoff['integration']['renderer_implementation_hash']
    assert pin['files']['autoresearch/taste/overnight/contracts.py'] == handoff['dependency']['contracts_sha256']
    for entry in handoff['integration']['registration']:
        for key in ('prompt_sha256', 'prompt_version', 'allows_empty'):
            assert registrations[entry['method_id']][key] == entry[key]
    checks, rows = [], []

    def check(name, actual, expected=True):
        checks.append({'check': name, 'pass': actual == expected, 'actual': actual, 'expected': expected})

    peer = document('Peer prefers replication.', 'peer-doc', 'synthetic-peer', [(0, 25)])
    # Unicode offsets intentionally differ from UTF-8 byte offsets.
    text = '🚧\n' + QUOTE + '\nOUTSIDE_CONTENT_SENTINEL'
    default_doc = document(text, ranges=[(2, 2 + len(QUOTE))])
    base_cases = [
        ('unique_unicode', default_doc, source(), 'complete', None),
        ('absent', default_doc, source('Fabricated sentence.'), 'invalid', 'quote_absent'),
        ('ambiguous', document(QUOTE + '\n' + QUOTE, ranges=[(0, len(QUOTE) * 2 + 1)]), source(), 'invalid', 'quote_ambiguous'),
        ('wrong_document', default_doc, source(identifier='other-doc'), 'invalid', 'quote_absent'),
        ('unknown_document', default_doc, source(identifier='missing-doc'), 'invalid', 'quote_source_document'),
        ('outside_permitted', document(text, ranges=[(len(text)-len('OUTSIDE_CONTENT_SENTINEL'), len(text))]), source(), 'invalid', 'quote_unpermitted'),
        ('one_permitted_duplicate', document(QUOTE + '\n' + QUOTE, ranges=[(len(QUOTE)+1, len(QUOTE)*2+1)]), source(), 'complete', None),
        ('overlap_one_occurrence', document(text, ranges=[(0, len(text)), (2, 2+len(QUOTE))]), source(), 'complete', None),
        ('adjacent_not_union', document(QUOTE, ranges=[(0, 5), (5, len(QUOTE))]), source(), 'invalid', 'quote_unpermitted'),
        ('whitespace_collapsed', default_doc, source(QUOTE.replace('  ', ' ')), 'invalid', 'quote_absent'),
        ('unicode_nfd', default_doc, source(unicodedata.normalize('NFD', QUOTE)), 'invalid', 'quote_absent'),
        ('fabricated_offsets', default_doc, dict(source(), start=900, end=901), 'invalid', 'quote_source_shape'),
        ('correct_offsets_still_forbidden', default_doc, dict(source(), start=2, end=2+len(QUOTE)), 'invalid', 'quote_source_shape'),
    ]

    def run_case(method, name, doc, src, status, error, *, body=None, cap=8192, call_count=1, config_extra=None):
        docs = [copy.deepcopy(doc), document('Different approved sentence.', 'other-doc', ranges=[(0, 28)])]
        if method == 'P7':
            docs.append(copy.deepcopy(peer))
        body = copy.deepcopy(body if body is not None else response_for(method, src, summary, principles))
        raw = canon(body)
        backend = RecordingExtractor(raw)
        sources = c.source_manifest(docs)
        config = {'method_id': method, 'researcher_id': 'synthetic-target', 'replicate_id': 0,
                  'code_sha': COMMIT, 'allowed_sources': sources,
                  'allowed_source_manifest_hash': c.digest(sources), 'personalization_cap': cap,
                  'extractor_settings': {'temperature': 0.0, 'max_tokens': 2048}, 'evidence_policy': 'explicit-only'}
        if method == 'P7':
            config['approved_peer_sources'] = True
        config.update(config_extra or {})
        manifest = {'schema_version': 'overnight-job-v1', 'campaign_id': 'synthetic-audit030-' + name,
            'stage': 'offline', 'kind': 'build', 'contract_sha256': CONTRACT,
            'config_hash': c.digest(config), 'source_manifest_hash': c.digest(sources),
            'documents_hash': c.digest(docs), 'items_hash': c.digest([]), 'profile_hash': None,
            'method_id': method, 'extractor': c.backend_identity(backend), 'consumer': None,
            'personalization_cap': cap, 'option_order_schedule': [], 'replicate_id': 0, 'code_sha': COMMIT,
            'allocation': {'max_calls': 1, 'max_seconds': 30, 'max_usd': 0, 'cost_mode': 'offline',
                           'authorization_source': 'synthetic-audit-only'},
            'retry_policy': {'max_attempts': 1, 'retry_uncertain': False}, 'parent_job_ids': [],
            'expected_outputs': ['profile.json', 'result.json', 'traces']}
        manifest['job_id'] = runner.job_id(manifest)
        lease = {'job_id': manifest['job_id'], 'lease_id': 'synthetic-' + method + '-' + name,
                 'owner': 'offline-audit030', 'expires_at': '2099-01-01T00:00:00+00:00'}
        folder = args.out / 'cases' / method / name
        save(folder / 'input.json', {'documents': docs, 'config': config, 'raw_response': raw, 'lease': lease})
        result = runner.run_job(manifest, lease, output_root=folder/'outputs', lease_root=folder/'leases',
                                config=config, documents=docs, extractor=backend)
        profile = result['profile']
        label = method + '/' + name
        check(label + '/status', profile['status'], status)
        check(label + '/error', profile['error_code'], error)
        check(label + '/calls', len(backend.calls), call_count)
        check(label + '/attempts', result['usage']['attempted_calls'], call_count)
        check(label + '/renderer', profile['renderer_implementation_hash'], renderer)
        check(label + '/builder', profile['method_implementation_hash'], registrations[method]['method_implementation_hash'])
        check(label + '/settings', profile['extractor_settings'], config['extractor_settings'])
        if call_count:
            check(label + '/raw_hash', profile['fit_usage']['raw_response_sha256'], sha(raw.encode()))
            captured = backend.calls[0]
            payload = json.loads(captured['prompt'].split('\nINPUT_JSON:\n')[-1])
            expected = {d['document_id']: [{'start': r['start'], 'end': r['end'], 'content': d['content'][r['start']:r['end']]}
                for r in d.get('permitted_spans', [{'start': 0, 'end': len(d['content'])}])] for d in docs}
            actual = {d['document_id']: d['segments'] for d in payload['documents']}
            check(label + '/approved_prompt_segments', actual, expected)
            check(label + '/metadata_not_sent', 'OUTSIDE_METADATA_SENTINEL' not in captured['prompt'])
            check(label + '/response_trace_preserved', len(result['trace_hashes']), 2)
            if error and error.startswith('quote_'):
                check(label + '/no_partial_content_rewrite', profile['content'], body)
        predicted = {'method_implementation_hash': profile['method_implementation_hash'],
                     'renderer_implementation_hash': renderer, 'profile_prompt_version': profile['prompt_version'],
                     'consumer_prompt_version': consumer.PROMPT_VERSION}
        artifact = c.ProfileArtifact.from_dict(profile)
        try:
            prepared = consumer.prepare_payload(artifact, 'Synthetic choice?', ['A', 'B'], predicted)
            check(label + '/consumer_available', status == 'complete')
            check(label + '/post_resolution_cap', len(prepared['payload']['personalization'].encode()) <= cap)
            check(label + '/rendered_exact_content', prepared['payload']['personalization'], canon(profile['content']))
        except consumer.ProfileFailure as exc:
            check(label + '/consumer_unavailable', status != 'complete')
            check(label + '/consumer_status', exc.status, status)
        if status == 'complete' or error == 'personalization_cap_exceeded':
            all_docs = {d['document_id']: d for d in docs}
            for i, citation in enumerate(citations(profile['content'])):
                d = all_docs[citation['document_id']]
                check(label + '/exact_slice/' + str(i), d['content'][citation['start']:citation['end']], citation['quote'])
                check(label + '/within_one_span/' + str(i), any(r['start'] <= citation['start'] < citation['end'] <= r['end']
                      for r in d.get('permitted_spans', [{'start': 0, 'end': len(d['content'])}])))
        if error == 'personalization_cap_exceeded':
            check(label + '/raw_fits', len(raw.encode()) <= cap)
            check(label + '/resolved_exceeds', profile['token_count'] > cap)
        records = profile['fit_usage'].get('quote_resolution_records', profile['fit_usage'].get('quote_resolution', {}).get('records', []))
        rows.append({'method': method, 'case': name, 'status': profile['status'], 'error_code': profile['error_code'],
                     'calls': len(backend.calls), 'raw_bytes': len(raw.encode()), 'resolved_bytes': profile['token_count'],
                     'cap': cap, 'profile_id': profile['profile_id'], 'records': records})
        return profile

    for method in registrations:
        for name, doc, src, status, error in base_cases:
            run_case(method, name, doc, src, status, error)
        partial = response_for(method, source(), summary, principles)
        first_statement(partial)['sources'].append(source('Fabricated later citation.'))
        run_case(method, 'partial_resolution_failure', default_doc, source(), 'invalid', 'quote_absent', body=partial)
        # Cap chosen from schema-supported values; raw JSON fits exactly, computed offsets push it over.
        padded = response_for(method, source(), summary, principles)
        first_statement(padded)['text'] += 'x' * (2048-len(canon(padded).encode()))
        assert len(canon(padded).encode()) == 2048
        over = run_case(method, 'post_resolution_cap', default_doc, source(), 'invalid', 'personalization_cap_exceeded', body=padded, cap=2048)
        first_statement(padded)['text'] = first_statement(padded)['text'][:-(over['token_count']-2048)]
        run_case(method, 'exact_cap_positive', default_doc, source(), 'complete', None, body=padded, cap=2048)
        missing = copy.deepcopy(default_doc); missing.pop('permitted_spans')
        role08 = method in ('P7', 'P8')
        run_case(method, 'missing_spans', missing, source(), 'unavailable' if role08 else 'complete',
                 'attributed_source_spans_unavailable' if role08 else None, call_count=0 if role08 else 1)
        empty = copy.deepcopy(default_doc); empty['permitted_spans'] = []
        run_case(method, 'empty_spans', empty, source(), 'unavailable' if role08 else 'invalid',
                 'attributed_source_spans_unavailable' if role08 else 'quote_unpermitted', call_count=0 if role08 else 1)

    # Generic resolver permits non-source extension keys; strict family schemas decide otherwise.
    extension = {'extension': {'opaque': 7}, 'sources': [source()]}
    resolved, records = c.resolve_quote_sources(extension, [default_doc])
    check('resolver_unknown_non_source_fields_preserved', resolved['extension'], extension['extension'])
    run_case('P1', 'unknown_config_preserved_unsent', default_doc, source(), 'complete', None,
             config_extra={'extension_metadata': 'UNKNOWN_CONFIG_SENTINEL'})
    for method in ('P1', 'P7', 'P8'):
        bad = response_for(method, source(), summary, principles); bad['extension'] = 7
        error = {'P1': 'invalid_summary_schema', 'P7': 'invalid_contrast_schema', 'P8': 'invalid_hypotheses_schema'}[method]
        run_case(method, 'unknown_output_schema', default_doc, source(), 'invalid', error, body=bad)
    for method in ('P7', 'P8'):
        bad = copy.deepcopy(default_doc); bad['permitted_spans'][0]['speaker'] = 'other-speaker'
        run_case(method, 'wrong_attribution_precall', bad, source(), 'invalid', 'unattributed_permitted_span', call_count=0)
    check('frozen_source_unchanged', all(sha((root/p).read_bytes()) == h for p,h in pin['files'].items()))
    report = {'source_commit': COMMIT, 'source_manifest_sha256': sha(args.source_manifest.read_bytes()),
              'script_sha256': sha(Path(__file__).read_bytes()), 'resolver_version': c.QUOTE_RESOLVER_VERSION,
              'renderer_implementation_hash': renderer, 'registrations': registrations,
              'cases': rows, 'checks': checks, 'passed': sum(x['pass'] for x in checks),
              'failed': sum(not x['pass'] for x in checks), 'case_count': len(rows),
              'recording_calls': sum(x['calls'] for x in rows), 'live_calls': 0,
              'scope': 'Frozen driver registration -> runner.run_job -> registered builder -> quote resolver -> strict validation -> shared cap -> consumer.prepare_payload. Synthetic offline only; no live entrypoint or provider transport.'}
    save(args.out/'report.json', report)
    print(canon({k: report[k] for k in ('source_commit', 'case_count', 'passed', 'failed', 'recording_calls', 'live_calls')}))
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
