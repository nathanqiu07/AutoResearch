#!/usr/bin/env python3
"""Synthetic-only source-boundary probe; no real researcher files or backends."""
import argparse
import builtins
import hashlib
import inspect
import json
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        handle.write(data)


def write_json(path, body):
    write_new(path, json.dumps(body, indent=2, sort_keys=True) + '\n')


def git(root, *argv):
    run = subprocess.run(['git', '-C', str(root), *argv], text=True, capture_output=True)
    if run.returncode:
        raise RuntimeError(run.stderr)
    return run.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path,
                        help='New output directory, refused if already present')
    args = parser.parse_args()
    root = args.source_root.resolve()
    output = args.out.resolve()
    output.mkdir(parents=False, exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    source_before = {str(p.relative_to(root)): hash_file(p)
                     for p in sorted((root / 'autoresearch').rglob('*.py'))}
    if not source_before:
        raise ValueError('source-root has no autoresearch source files')
    from autoresearch.research import advisor, ideas
    from autoresearch.taste import timesplit
    for module in (advisor, ideas, timesplit):
        Path(module.__file__).resolve().relative_to(root)

    approved = 'SYNTHETIC_APPROVED_FIT_DOC_SENTINEL_02'
    withheld = 'SYNTHETIC_WITHHELD_DOC_SENTINEL_02'
    heldout_row = 'SYNTHETIC_HELDOUT_ROW_SENTINEL_02'
    allowed_row = 'SYNTHETIC_APPROVED_HISTORY_ROW_SENTINEL_02'
    cutoff = '2026-01-01'
    fit_text = '---\npublishedDate: 2025-01-01\n---\n' + approved + '\n'
    withheld_text = '---\npublishedDate: 2026-06-01\n---\n' + withheld + '\n'
    full = output / 'synthetic_researchers' / 'mixed_corpus'
    isolated = output / 'synthetic_researchers' / 'allowlisted_only'
    short = output / 'synthetic_researchers' / 'withheld_first'
    for directory in (full, isolated, short):
        (directory / 'corpus').mkdir(parents=True)
    write_new(full / 'corpus' / '10_fit.txt', fit_text)
    write_new(full / 'corpus' / '20_withheld.txt', withheld_text)
    write_new(isolated / 'corpus' / '10_fit.txt', fit_text)
    write_new(short / 'corpus' / '00_withheld.txt', withheld_text)
    write_new(short / 'corpus' / '10_fit.txt', fit_text)
    history = {'context': allowed_row, 'a_text': 'SYNTHETIC option A',
               'b_text': 'SYNTHETIC option B', 'chosen': 'a'}
    hidden = dict(history, context=heldout_row)
    write_new(full / 'history_timesplit.jsonl', json.dumps(history) + '\n')
    write_new(full / 'heldout_timesplit.jsonl', json.dumps(hidden) + '\n')
    manifest = {'fixture_only': True, 'schema': 'synthetic-declared-boundary-v1',
                'cutoff': cutoff, 'note': 'An audit fixture, not an existing production API contract.',
                'approved_corpus_paths': ['corpus/10_fit.txt'],
                'withheld_corpus_paths': ['corpus/20_withheld.txt']}
    write_json(full / 'source_manifest.json', manifest)
    fixture_paths = [p for p in sorted((output / 'synthetic_researchers').rglob('*')) if p.is_file()]
    input_hashes = {str(p.relative_to(output)): hash_file(p) for p in fixture_paths}

    read_paths = []
    original_open = builtins.open
    def recording_open(file, mode='r', *positional, **kwargs):
        if isinstance(file, (str, bytes, Path)) and 'r' in mode:
            p = Path(file).resolve()
            if p.is_relative_to(output):
                read_paths.append(str(p.relative_to(output)))
        return original_open(file, mode, *positional, **kwargs)

    class RecordingTransport:
        """Deliberately not OfflineLLM, so actual prompt construction is exercised."""
        def __init__(self):
            self.requests = []
        def complete(self, prompt, system='', max_tokens=1024, temperature=0.7):
            self.requests.append({'prompt': prompt, 'system': system,
                                  'max_tokens': max_tokens, 'temperature': temperature})
            return '[]'

    with patch.object(builtins, 'open', recording_open):
        full_history = advisor.history_text(str(full))
        allowed_history = advisor.history_text(str(isolated))
        # Only a short prefix survives; the helper still opens both complete documents.
        short_history = advisor.history_text(str(short), max_chars=120)
        dated_reference = timesplit.docs_before(SimpleNamespace(root=str(full)), cutoff)
    transport = RecordingTransport()
    proposer = ideas.Proposer(transport, None, random.Random(0), history=full_history)
    proposer.propose('SYNTHETIC source-boundary audit goal',
                     'SYNTHETIC opportunity only', [], set(), [], [], k=1)
    assert len(transport.requests) == 1
    request = transport.requests[0]
    checks = {
        'full_corpus_includes_approved_doc': approved in full_history,
        'full_corpus_includes_withheld_doc': withheld in full_history,
        'full_corpus_includes_approved_history_row': allowed_row in full_history,
        'heldout_pair_file_is_not_included': heldout_row not in full_history,
        'manifest_not_opened_by_helper': not any(p.endswith('/source_manifest.json') for p in read_paths),
        'actual_proposer_request_includes_withheld_doc': withheld in request['prompt'],
        'allowlisted_directory_includes_approved_doc': approved in allowed_history,
        'allowlisted_directory_excludes_withheld_doc': withheld not in allowed_history,
        'short_prefix_includes_withheld_doc': withheld in short_history,
        'short_prefix_excludes_approved_doc': approved not in short_history,
        'truncated_helper_still_reads_discarded_fit_doc':
            'synthetic_researchers/withheld_first/corpus/10_fit.txt' in read_paths,
        'existing_dated_helper_excludes_withheld_doc':
            withheld not in '\n'.join(body for kind, body in dated_reference),
    }
    for name, passed in checks.items():
        assert passed, name
    source_after = {str(p.relative_to(root)): hash_file(p)
                    for p in sorted((root / 'autoresearch').rglob('*.py'))}
    inputs_unchanged = all(hash_file(output / relative) == expected
                           for relative, expected in input_hashes.items())
    assert source_after == source_before, 'source files changed during probe'
    assert inputs_unchanged, 'synthetic input files changed during probe'
    write_new(output / 'full_history.txt', full_history)
    write_new(output / 'allowlisted_history.txt', allowed_history)
    write_new(output / 'truncated_history.txt', short_history)
    write_json(output / 'recorded_proposer_request.json', request)
    write_json(output / 'dated_reference.json', dated_reference)
    report = {
        'synthetic_only': True, 'real_model_calls': 0,
        'recorded_synthetic_transport_calls': len(transport.requests),
        'argv': sys.argv, 'python_version': sys.version,
        'source_root': str(root), 'source_commit': git(root, 'rev-parse', 'HEAD'),
        'source_dirty_status': git(root, 'status', '--short', '--', 'autoresearch'),
        'source_file_hashes': source_before,
        'source_unchanged_during_probe': source_before == source_after,
        'synthetic_input_hashes': input_hashes,
        'synthetic_inputs_unchanged': inputs_unchanged,
        'probe_script_sha256': hash_file(__file__),
        'helper_signature': str(inspect.signature(advisor.history_text)),
        'runtime_read_paths_within_fixture': read_paths,
        'checks': checks,
        'conditional_finding': 'If a caller supplies a researcher directory whose corpus contains '
            'both approved and withheld text documents, history_text reads both without checking '
            'a source manifest or publication cutoff. The constructed proposer request includes '
            'the withheld synthetic document. A character cap is not a source boundary.',
        'limits': ['No actual researcher corpus, target, labels, final files, or restricted store was read.',
                   'No claim of leakage in any actual experiment follows from this synthetic fixture.',
                   'CLI wiring was inspected statically; full CLI and research loop were not run.',
                   'The synthetic manifest declares the probe boundary; it is not a supported legacy API.',
                   'No production edits or paid calls. No model quality or outcome effect was measured.'],
    }
    write_json(output / 'report.json', report)
    print(json.dumps({'report': str(output / 'report.json'), 'checks_passed': len(checks),
                      'source_commit': report['source_commit'],
                      'conditional_withheld_doc_in_actual_prompt': True,
                      'real_model_calls': 0, 'source_unchanged': source_before == source_after}, sort_keys=True))


if __name__ == '__main__':
    main()
