#!/usr/bin/env python3
"""Inspect saved user-model conditioning using an explicit offline recording transport.

No fit is called, no real backend is constructed, and no synthetic prediction is
reported as preference evidence. Run once per source checkout in a fresh process.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _reject_constant(value):
    raise ValueError('Nonfinite JSON value: ' + value)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse_json(data):
    value = json.loads(data, parse_constant=_reject_constant, object_pairs_hook=_unique_pairs)
    def check(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Nonfinite JSON number')
        if isinstance(item, dict):
            for child in item.values(): check(child)
        elif isinstance(item, list):
            for child in item: check(child)
    check(value)
    return value


def read_json(path):
    return parse_json(Path(path).read_bytes())


def write_report(path, report):
    # Exclusive creation preserves prior runs, including unsuccessful ones.
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    with Path(path).open('x') as handle:
        handle.write(payload)


def summarize_channels(artifacts):
    return {'principles': len(artifacts.get('principles', [])),
            'persona_chars': len(artifacts.get('persona', '')),
            'exemplars': len(artifacts.get('exemplars', [])),
            'nonzero_weights': any(v != 0 for v in artifacts.get('weights', {}).values()),
            'assumptions': len(artifacts.get('assumptions', {})),
            'empty_text_conditioning': not any((artifacts.get('principles'),
                                               artifacts.get('persona'),
                                               artifacts.get('exemplars')))}


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def code_snapshot(root):
    return {str(p.relative_to(root)): sha256(p)
            for folder in ('autoresearch',)
            for p in sorted((root / folder).rglob('*.py'))}


def audit_artifact(path, source_root):
    from autoresearch.llm import Budget
    from autoresearch.taste.usermodel import load_model
    from autoresearch.taste.profile import FEATURES
    from autoresearch.research.advisor import TasteAdvisor
    artifact_bytes = Path(path).read_bytes()
    body = parse_json(artifact_bytes)
    for name, module in list(sys.modules.items()):
        if name == 'autoresearch' or name.startswith('autoresearch.'):
            location = getattr(module, '__file__', None)
            if location is not None:
                try:
                    Path(location).resolve().relative_to(source_root)
                except ValueError:
                    raise ValueError('Imported module outside requested source root: ' + name)
    before_hash = hashlib.sha256(artifact_bytes).hexdigest()
    identity = body['backend']
    calls = []

    class Recorder:
        # Deliberate identity shim: exercises the loader but does NOT verify
        # compatibility/access to the real backend named in the artifact.
        label = identity['label']
        base_url = identity.get('endpoint', '')
        def __init__(self):
            self.budget = Budget()
        def complete(self, prompt, system='', max_tokens=1024, temperature=0.7):
            calls.append({'system': system, 'prompt': prompt, 'max_tokens': max_tokens,
                          'temperature': temperature})
            payload = json.loads(prompt.split('INPUT_JSON:\n', 1)[1])
            if 'options' in payload:
                count = len(payload['options'])
                probabilities = [1.0 / count] * count
                return json.dumps({'probabilities': probabilities,
                                   'rationale': 'Offline audit fixture; not model inference'})
            if 'option' in payload:
                return json.dumps({'features': {feature: 0.0 for feature in FEATURES}})
            raise ValueError('Unsupported audit request shape; prompt retained')

    transport = type(identity['class'], (Recorder,), {})()
    model = load_model(path, transport)
    original = asdict(model.artifacts())
    prediction_error = None
    try:
        model.predict('Audit fixture: choose between two research options.',
                      ['Audit option A', 'Audit option B'])
    except Exception as exc:
        prediction_error = type(exc).__name__ + ': ' + str(exc)
    guidance = TasteAdvisor(model).principles()
    with tempfile.TemporaryDirectory(prefix='profile-audit-') as temp:
        saved = Path(temp) / 'roundtrip.json'
        model.save(saved)
        reloaded = load_model(saved, transport)
        stable_fields = ('version', 'method', 'seed', 'config', 'backend', 'artifacts')
        serialized = read_json(saved)
        roundtrip = {field: body.get(field) == serialized.get(field) for field in stable_fields}
        roundtrip['loaded_artifacts'] = original == asdict(reloaded.artifacts())
    requests = []
    for call in calls:
        payload = json.loads(call['prompt'].split('INPUT_JSON:\n', 1)[1])
        requests.append({**call, 'payload': payload,
                         'request_kind': 'preference' if 'options' in payload else ('option_features' if 'option' in payload else 'unsupported'),
                         'personal_channels': {
                             'principles': payload.get('principles'),
                             'persona': payload.get('persona'),
                             'past_choices': payload.get('past_choices')}})
    preference_requests = [request for request in requests if request['request_kind'] == 'preference']
    prediction_channels = preference_requests[-1]['personal_channels'] if preference_requests else None
    return {'artifact_path': str(path.resolve()), 'artifact_sha256': before_hash,
            'artifact_unchanged': before_hash == sha256(path), 'method': body['method'],
            'seed': body['seed'], 'config': body['config'], 'saved_backend_identity': identity,
            'saved_prompt_version': original.get('metadata', {}).get('prompt_version'),
            'runtime_prompt_version': getattr(model, 'prompt_version', None),
            'prompt_version_matches': (original.get('metadata', {}).get('prompt_version') == getattr(model, 'prompt_version', None)
                                       if original.get('metadata', {}).get('prompt_version') is not None else None),
            'transport': 'offline recording stub with explicit saved-identity shim',
            'live_backend_compatibility': 'not_tested',
            'artifact_channels': summarize_channels(original),
            'metadata': original.get('metadata', {}),
            'prediction_requests': requests, 'prediction_error': prediction_error,
            'prediction_channels': prediction_channels,
            'adviser_principles': guidance,
            'adviser_guidance_is_saved_principles': guidance == original.get('principles', []),
            'roundtrip': roundtrip,
            'limitations': ['Synthetic reply only allows prompt construction to complete; no accuracy or confidence evidence.',
                            'Proposer guidance and choice prediction are distinct interventions.',
                            'No Petri runner execution or live backend verification.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output exists; use a fresh report path')
    root = args.source_root.resolve()
    for relative in ('autoresearch/__init__.py', 'autoresearch/llm.py', 'autoresearch/taste/usermodel.py', 'autoresearch/research/advisor.py'):
        if not (root / relative).is_file():
            parser.error('source root is missing required module: ' + relative)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    before = code_snapshot(root)
    report = {'schema_version': 1, 'mode': 'offline_integration_audit',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'tool_sha256': sha256(__file__), 'source_root': str(root),
              'source_commit': git(root, 'rev-parse', 'HEAD'),
              'source_dirty_status': git(root, 'status', '--short', '--', 'autoresearch'),
              'source_file_hashes': before, 'real_model_calls': 0, 'artifacts': []}
    for path in args.artifact:
        try:
            report['artifacts'].append(audit_artifact(path, root))
        except Exception as exc:
            report['artifacts'].append({'artifact_path': str(path.resolve()),
                                        'artifact_sha256': sha256(path) if path.is_file() else None,
                                        'error': type(exc).__name__ + ': ' + str(exc)})
    for row in report['artifacts']:
        path = Path(row['artifact_path'])
        row['artifact_unchanged_during_own_inspection'] = row.get('artifact_unchanged')
        try:
            row['artifact_final_sha256'] = sha256(path)
        except OSError:
            row['artifact_final_sha256'] = None
        row['artifact_unchanged'] = (row.get('artifact_sha256') is not None
                                     and row.get('artifact_sha256') == row['artifact_final_sha256'])
    report['source_unchanged_during_audit'] = before == code_snapshot(root)
    report['all_roundtrips_preserved'] = all('roundtrip' in row and all(row['roundtrip'].values())
                                            for row in report['artifacts'])
    report['all_predictions_completed'] = all('prediction_error' in row and row['prediction_error'] is None for row in report['artifacts'])
    report['all_inputs_unchanged'] = report['source_unchanged_during_audit'] and all(row.get('artifact_unchanged', False) for row in report['artifacts'])
    write_report(args.out, report)
    print(json.dumps({'report': str(args.out), 'artifacts': len(report['artifacts']),
                      'source_unchanged': report['source_unchanged_during_audit'],
                      'all_roundtrips_preserved': report['all_roundtrips_preserved']}))
    return 0 if (report['all_inputs_unchanged'] and report['all_roundtrips_preserved']
                 and report['all_predictions_completed']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
