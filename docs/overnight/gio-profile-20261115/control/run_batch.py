#!/usr/bin/env python3
"""Execute only coordinator-listed development jobs; never search or retry.

CLI (all paths supplied by the coordinator):
  python run_batch.py prepare --file BATCH.json --sha256 EXACT_FILE_SHA
  python run_batch.py execute --file PREPARED.json --sha256 PRINTED_FILE_SHA

Batch schema overnight-batch-v1: campaign_id, code_sha, runtime_root, deadline,
max_workers (1 or 2), max_total_attempts, release_schema_version, release_scope,
contract:{path,sha256}, env_file,
ledger:{path,max_usd,max_inflight:2}, roots:{output,lease,cache,receipts},
jobs:[{path,sha256}]. Paths must be absolute. Outputs/ledger stay outside Git.

Packet schema overnight-packet-v1: release:{path,sha256}, item_ids:[ordered IDs],
profile:{path,sha256}|null, config, manifest, lease, backend:{model,reasoning,
timeout,max_calls,max_seconds,max_usd}, registration:{module,function}.
The manifest is an overnight-job-v1 manifest. Computable hashes, job_id,
code_sha, deadline and backend identity may be omitted; supplied values must
match exactly. lease.job_id may be omitted. All research choices are explicit.
Build packets may select no items; a decision-specific build selects exactly
one item and supplies the corresponding config.decision. Predict packets must
supply an existing profile and a nonempty explicit ordered item subset.

Preparation snapshots exact source files and writes complete immutable packets.
Execution revalidates those snapshots and the frozen runtime before dispatch.
No final/confirmation jobs, inferred methods, live fallback, or auto-resume.
This is cooperative local coordination, not an authorization service. The
coordinator reviews exact prepared bytes and supplies their SHA to execute.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import importlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

RUNTIME_ROOT = Path(__file__).resolve().parents[4]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))
from autoresearch.llm import Budget
from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend
from autoresearch.taste.overnight.contracts import (ProfileArtifact, backend_identity, canonical_json,
    digest, sha256_bytes, source_manifest, validate_documents)
from autoresearch.taste.overnight.consumer import prepare_payload
from autoresearch.taste.overnight.registry import get_builder
from autoresearch.taste.overnight.runner import (ITEM_FIELDS, _validate, job_id, run_job, timestamp, write_new)

HARD_DEADLINE = '2026-11-15T17:00:00Z'
MAX_CAMPAIGN_USD = Decimal('500')  # Direct user approval; each batch still requires its shared suballocation.
RELEASE_SCHEMA = 'released-development-v2'
RELEASE_SCOPE = 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel'
SECRET_NAMES = ('OPENAI_API_KEY', 'OPENAI_ORG_ID', 'OPENAI_PROJECT_ID')
REGISTRATIONS = {
    'autoresearch.taste.overnight.baselines': 'register_baselines',
    'autoresearch.taste.overnight.profiles_summary': 'register_summary_builders',
    'autoresearch.taste.overnight.profiles_principles': 'register_principle_builders',
    'autoresearch.taste.overnight.profiles_hypotheses': 'register_hypotheses_builders',
}


def _git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError('runtime Git check failed')
    return result.stdout.strip()


def verify_checkout(root, expected_sha):
    if not isinstance(expected_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', expected_sha):
        raise ValueError('full runtime commit SHA required')
    if _git(root, 'rev-parse', 'HEAD') != expected_sha:
        raise ValueError('loaded code commit differs from packet')
    if _git(root, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked runtime is dirty')


def verify_runtime(root, expected_sha):
    root = Path(root).resolve()
    if root != RUNTIME_ROOT:
        raise ValueError('driver must run from the supplied frozen checkout')
    verify_checkout(root, expected_sha)
    paths = [Path(__file__).resolve()]
    for name, module in list(sys.modules.items()):
        if name == 'autoresearch' or name.startswith('autoresearch.'):
            if getattr(module, '__file__', None):
                paths.append(Path(module.__file__).resolve())
    for path in paths:
        try:
            relative = path.relative_to(root)
        except ValueError:
            raise ValueError('runtime module loaded outside frozen checkout') from None
        _git(root, 'ls-files', '--error-unmatch', str(relative))


def _path(value):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError('explicit absolute path required')
    return Path(value).resolve()


def _outside_git(value):
    path = _path(value)
    ancestor = path if path.is_dir() else path.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    result = subprocess.run(['git', '-C', str(ancestor), 'rev-parse', '--is-inside-work-tree'],
                            capture_output=True, text=True, check=False)
    if result.returncode == 0 and result.stdout.strip() == 'true':
        raise ValueError('packet outputs and ledger must be outside Git')
    return path


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON key')
        obj[key] = value
    return obj


def _json(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        canonical_json(value)
        return value
    except (ValueError, TypeError, UnicodeError):
        raise ValueError('invalid strict JSON input') from None


def _read(ref):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('exact file reference required')
    if not isinstance(ref['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', ref['sha256']):
        raise ValueError('exact file hash required')
    raw = _path(ref['path']).read_bytes()
    if len(raw) > 64_000_000 or sha256_bytes(raw) != ref['sha256']:
        raise ValueError('file hash mismatch or oversized input')
    return raw


def _bound(mapping, key, value):
    if key in mapping and mapping[key] != value:
        raise ValueError('derived field mismatch: ' + key)
    mapping[key] = value


def _positive(value, integer=False, allow_zero=False):
    if (isinstance(value, bool) or not isinstance(value, int if integer else (int, float))
            or not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero)):
        raise ValueError('explicit finite allocation required')
    return value


def _deadline(value):
    try:
        deadline = timestamp(value)
    except (ValueError, TypeError, AttributeError):
        raise ValueError('valid explicit deadline required') from None
    if not datetime.now(timezone.utc) < deadline <= timestamp(HARD_DEADLINE):
        raise ValueError('deadline expired or exceeds campaign hard stop')
    return deadline


def read_credentials(path):
    """A small dotenv data parser: no evaluation, interpolation or subprocesses."""
    values = {}
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
        for line in lines:
            match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=(.*)$', line)
            if not match or match.group(1) not in SECRET_NAMES:
                continue
            key, raw = match.groups()
            if key in values:
                raise ValueError()
            tokens = shlex.split(raw, comments=True, posix=True)
            if len(tokens) != 1 or not tokens[0] or any(ord(c) < 32 for c in tokens[0]):
                raise ValueError()
            values[key] = tokens[0]
        if not values.get('OPENAI_API_KEY'):
            raise ValueError()
    except (OSError, ValueError, UnicodeError):
        raise ValueError('credential file unavailable or invalid') from None
    return values


@contextmanager
def _credentials(values):
    prior = {key: os.environ.get(key) for key in SECRET_NAMES}
    try:
        for key in SECRET_NAMES:
            if key in values:
                os.environ[key] = values[key]
            else:
                os.environ.pop(key, None)
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _backend(spec, ledger):
    if not isinstance(spec, dict) or set(spec) != {'model', 'reasoning', 'timeout', 'max_calls', 'max_seconds', 'max_usd'}:
        raise ValueError('explicit backend model, reasoning and limits required')
    _positive(spec['max_calls'], integer=True, allow_zero=True)
    _positive(spec['max_seconds'])
    _positive(spec['max_usd'])
    _positive(spec['timeout'])
    if spec['timeout'] >= spec['max_seconds']:
        raise ValueError('timeout must leave room inside job allocation')
    return OpenAIResponsesBackend(model=spec['model'], reasoning=spec['reasoning'], ledger=ledger,
        max_usd=spec['max_usd'], timeout=spec['timeout'],
        budget=Budget(max_calls=spec['max_calls'], max_seconds=spec['max_seconds'], max_cost_usd=spec['max_usd']))


def _register(registration, method):
    if (not isinstance(registration, dict) or set(registration) != {'module', 'function'}
            or REGISTRATIONS.get(registration['module']) != registration['function']):
        raise ValueError('unsupported method registration')
    try:
        module = importlib.import_module(registration['module'])
        getattr(module, registration['function'])()
        builder = get_builder(method)
        if builder.function.__module__ != registration['module']:
            raise ValueError()
    except (ImportError, AttributeError, ValueError):
        raise ValueError('requested method is unavailable in supplied module') from None
    return builder


def _profile(body, documents, researcher, code_sha):
    profile = ProfileArtifact.from_dict(body)
    if (profile.documents_hash != digest(documents) or profile.researcher_id != researcher
            or profile.code_sha != code_sha):
        raise ValueError('profile full source records, researcher or code mismatch')
    validate_documents(documents, profile.config)
    return profile


def _nested_profiles(value, documents, researcher, code_sha):
    if isinstance(value, dict):
        if value.get('schema_version') == 'neutral-profile-v1':
            _profile(value, documents, researcher, code_sha)
        for key, child in value.items():
            if key == 'frozen_profile' and (not isinstance(child, dict) or child.get('schema_version') != 'neutral-profile-v1'):
                raise ValueError('invalid nested frozen profile')
            _nested_profiles(child, documents, researcher, code_sha)
    elif isinstance(value, list):
        for child in value:
            _nested_profiles(child, documents, researcher, code_sha)


def _prepare_packet(packet, batch, ledger):
    if not isinstance(packet, dict) or packet.get('schema_version') != 'overnight-packet-v1':
        raise ValueError('unsupported packet schema')
    packet = _json(canonical_json(packet))
    release_raw = _read(packet['release'])
    release = _json(release_raw)
    if release.get('scope') != batch['release_scope'] or release.get('schema_version') != batch['release_schema_version']:
        raise ValueError('released schema or scope differs from approved batch')
    documents = release['sources']['documents']
    sources = source_manifest(documents)
    if (release['sources']['source_manifest'] != sources
            or release['sources']['allowed_source_manifest_hash'] != digest(sources)):
        raise ValueError('released source manifest mismatch')
    validate_documents(documents, {'researcher_id': release['researcher_id'], 'allowed_sources': sources,
                                   'allowed_source_manifest_hash': digest(sources)})
    all_items = release['items']
    if not isinstance(all_items, list) or digest(all_items) != release['items_sha256']:
        raise ValueError('released items hash mismatch')
    index = {}
    for item in all_items:
        if (not isinstance(item, dict) or set(item) != ITEM_FIELDS or not isinstance(item['item_id'], str)
                or not item['item_id'] or item['item_id'] in index or item['researcher_id'] != release['researcher_id']):
            raise ValueError('released item fields, ID or researcher invalid')
        index[item['item_id']] = item
    ids = packet['item_ids']
    if (not isinstance(ids, list) or any(not isinstance(i, str) or i not in index for i in ids)
            or len(ids) != len(set(ids))):
        raise ValueError('explicit unique released item IDs required')
    items = [index[i] for i in ids]
    manifest, config, lease = packet['manifest'], packet['config'], packet['lease']
    if manifest.get('stage') != 'dev' or manifest.get('kind') not in ('build', 'predict'):
        raise ValueError('only explicit development build or predict jobs are permitted')
    if manifest.get('campaign_id') != batch['campaign_id']:
        raise ValueError('campaign mismatch')
    builder = _register(packet['registration'], manifest['method_id'])
    backend = _backend(packet['backend'], ledger)
    allocation = manifest['allocation']
    if allocation.get('cost_mode') != 'priced_api':
        raise ValueError('driver requires priced API allocation')
    for field in ('max_calls', 'max_seconds', 'max_usd'):
        if allocation.get(field) != packet['backend'][field]:
            raise ValueError('backend and manifest allocations differ')
    if Decimal(str(allocation['max_usd'])) > Decimal(str(batch['ledger']['max_usd'])):
        raise ValueError('job dollar ceiling exceeds campaign allocation')
    for field, value in {'code_sha': batch['code_sha'], 'deadline': batch['deadline'],
            'contract_sha256': batch['contract']['sha256'], 'source_manifest_hash': digest(sources),
            'documents_hash': digest(documents), 'config_hash': digest(config), 'items_hash': digest(items),
            'option_order_schedule': [{'item_id': i['item_id'], 'option_order_id': i['option_order_id']} for i in items]}.items():
        _bound(manifest, field, value)
    if _deadline(lease['expires_at']) > _deadline(batch['deadline']):
        raise ValueError('lease exceeds batch deadline')
    _nested_profiles(config, documents, release['researcher_id'], batch['code_sha'])
    profile, profile_raw = None, None
    if manifest['kind'] == 'build':
        if packet.get('profile') is not None:
            raise ValueError('build profiles belong in explicit frozen-profile config')
        if config.get('researcher_id') != release['researcher_id']:
            raise ValueError('build researcher differs from released bundle')
        _bound(manifest, 'profile_hash', None)
        _bound(manifest, 'extractor', backend_identity(backend))
        if 'decision' in config:
            if len(items) != 1 or config['decision'] != {k: items[0][k] for k in ('context', 'options')}:
                raise ValueError('build decision must bind one exact released ordered item')
    else:
        if not items:
            raise ValueError('prediction requires explicit released items')
        profile_raw = _read(packet['profile'])
        profile = _profile(_json(profile_raw), documents, release['researcher_id'], batch['code_sha'])
        if profile.method_implementation_hash != builder.implementation_hash:
            raise ValueError('profile builder implementation differs from frozen runtime')
        _bound(manifest, 'profile_hash', profile.profile_id)
        _bound(manifest, 'extractor', profile.extractor)
        _bound(manifest, 'consumer', backend_identity(backend))
        for item in items:
            prepare_payload(profile, item['context'], item['options'], config)
    _bound(manifest, 'job_id', job_id(manifest))
    _bound(lease, 'job_id', manifest['job_id'])
    _validate(manifest, lease, config, profile, items, documents)
    return {'packet': packet, 'manifest': manifest, 'lease': lease, 'config': config,
            'documents': documents, 'items': items, 'profile': profile,
            'release_raw': release_raw, 'profile_raw': profile_raw}


def prepare_batch(path, expected_sha):
    raw = _read({'path': path, 'sha256': expected_sha})
    batch = _json(raw)
    if batch.get('schema_version') != 'overnight-batch-v1' or batch.get('campaign_id') != 'gio-profile-20261115':
        raise ValueError('unsupported batch schema or campaign')
    if type(batch.get('max_workers')) is not int or batch.get('max_workers') not in (1, 2):
        raise ValueError('batch requires one or two workers')
    _positive(batch['max_total_attempts'], integer=True)
    if batch.get('release_schema_version') != RELEASE_SCHEMA or batch.get('release_scope') != RELEASE_SCOPE:
        raise ValueError('active development release schema and scope required')
    _deadline(batch['deadline'])
    verify_runtime(_path(batch['runtime_root']), batch['code_sha'])
    _path(batch['env_file'])  # Never read credentials while preparing.
    if not isinstance(batch['roots'], dict) or set(batch['roots']) != {'output', 'lease', 'cache', 'receipts'}:
        raise ValueError('all canonical output roots required')
    for value in batch['roots'].values():
        _outside_git(value)
    ledger_spec = batch['ledger']
    if (set(ledger_spec) != {'path', 'max_usd', 'max_inflight'} or ledger_spec['max_inflight'] != 2
            or type(ledger_spec['max_inflight']) is not int):
        raise ValueError('canonical two-call shared ledger required')
    _positive(ledger_spec['max_usd'])
    if Decimal(str(ledger_spec['max_usd'])) > MAX_CAMPAIGN_USD:
        raise ValueError('shared ledger exceeds remaining campaign allocation')
    _outside_git(ledger_spec['path'])
    contract_raw = _read(batch['contract'])
    refs = batch['jobs']
    if not isinstance(refs, list) or not refs:
        raise ValueError('finite nonempty explicit packet list required')
    packets_raw = [_read(ref) for ref in refs]
    packets = [_json(packet) for packet in packets_raw]
    if sum(_positive(p['backend']['max_calls'], integer=True, allow_zero=True) for p in packets) > batch['max_total_attempts']:
        raise ValueError('summed job attempt ceilings exceed explicit batch ceiling')
    ledger = DollarLedger(ledger_spec['path'], max_usd=ledger_spec['max_usd'], deadline=batch['deadline'], max_inflight=2)
    jobs = [_prepare_packet(packet, batch, ledger) for packet in packets]
    ids = [j['manifest']['job_id'] for j in jobs]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate semantic job in batch')
    verify_runtime(batch['runtime_root'], batch['code_sha'])
    batch_id = batch.get('batch_id', expected_sha)
    if not isinstance(batch_id, str) or not re.fullmatch('[0-9a-f]{64}', batch_id):
        raise ValueError('invalid prepared batch identity')
    return {'batch': batch, 'batch_raw': raw, 'batch_id': batch_id, 'batch_sha256': expected_sha,
            'contract_raw': contract_raw, 'packets_raw': packets_raw, 'jobs': jobs, 'ledger': ledger}


def _write_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path.resolve()), 'sha256': sha256_bytes(raw)}


def publish_prepared(prepared):
    """One immutable preparation, with raw inputs preserved beside bound packets."""
    batch = _json(canonical_json(prepared['batch']))
    root = _outside_git(batch['roots']['receipts']) / prepared['batch_id'] / 'preparation'
    root.mkdir(parents=True, exist_ok=False)
    _write_bytes(root / 'original-batch.json', prepared['batch_raw'])
    batch['contract'] = _write_bytes(root / 'contract', prepared['contract_raw'])
    batch['jobs'] = []
    for i, job in enumerate(prepared['jobs']):
        where = root / ('job-%04d' % i)
        packet = _json(canonical_json(job['packet']))
        _write_bytes(where / 'original-packet.json', prepared['packets_raw'][i])
        packet['release'] = _write_bytes(where / 'release.json', job['release_raw'])
        if job['profile_raw'] is not None:
            packet['profile'] = _write_bytes(where / 'profile.json', job['profile_raw'])
        batch['jobs'].append(_write_bytes(where / 'packet.json', (canonical_json(packet) + '\n').encode()))
    batch.update(prepared=True, batch_id=prepared['batch_id'], original_batch_sha256=prepared['batch_sha256'])
    return _write_bytes(root / 'prepared.json', (canonical_json(batch) + '\n').encode())


def load_prepared(path, expected_sha):
    body = _json(_read({'path': path, 'sha256': expected_sha}))
    if body.get('prepared') is not True or body.get('original_batch_sha256') != body.get('batch_id'):
        raise ValueError('execute requires a hash-pinned prepared batch')
    for ref in body['jobs']:
        packet = _json(_read(ref))
        if not packet['manifest'].get('job_id') or packet['lease'].get('job_id') != packet['manifest']['job_id']:
            raise ValueError('prepared packet must contain bound manifest and lease')
    return prepare_batch(path, expected_sha)


def _execute_one(job, prepared):
    batch = prepared['batch']
    verify_runtime(batch['runtime_root'], batch['code_sha'])
    backend = _backend(job['packet']['backend'], prepared['ledger'])
    if job['profile'] is not None:
        ProfileArtifact.from_dict(job['profile'].to_dict())
    return run_job(job['manifest'], job['lease'], config=job['config'], documents=job['documents'],
        items=job['items'], profile=job['profile'], extractor=backend if job['manifest']['kind'] == 'build' else None,
        consumer=backend if job['manifest']['kind'] == 'predict' else None,
        output_root=batch['roots']['output'], lease_root=batch['roots']['lease'], cache_root=batch['roots']['cache'])


def execute_batch(prepared):
    """One finite dispatch. A crash or claim never becomes permission to resume."""
    batch, ledger, jobs = prepared['batch'], prepared['ledger'], prepared['jobs']
    verify_runtime(batch['runtime_root'], batch['code_sha'])
    _deadline(batch['deadline'])
    credentials = read_credentials(batch['env_file'])
    root = _outside_git(batch['roots']['receipts']) / prepared['batch_id'] / 'execution'
    root.mkdir(parents=True, exist_ok=False)
    write_new(root / 'claim.json', {'batch_id': prepared['batch_id'], 'batch_sha256': prepared['batch_sha256'],
                                 'job_ids': [job['manifest']['job_id'] for job in jobs]})
    receipts, stopped, cursor = [], None, 0
    initial = ledger.summary()
    if initial['held_after_uncertain'] or initial['inflight']:
        stopped = 'existing_uncertain_or_pending_reservation'

    def receipt(job, status, result=None, error=None):
        body = {'schema_version': 'overnight-dispatch-receipt-v1', 'job_id': job['manifest']['job_id'],
                'manifest_sha256': digest(job['manifest']), 'status': status, 'error_code': error,
                'counts': result.get('counts', {}) if result else {},
                'usage': result.get('usage', {}) if result else {},
                'result_path': str(Path(batch['roots']['output']) / job['manifest']['job_id'] / 'result.json') if result else None}
        write_new(root / job['manifest']['job_id'] / 'receipt.json', body)
        receipts.append(body)

    with _credentials(credentials), ThreadPoolExecutor(max_workers=batch['max_workers']) as pool:
        active = {}
        while active or (cursor < len(jobs) and not stopped):
            state = ledger.summary()
            if state['held_after_uncertain']:
                stopped = 'shared_ledger_uncertain'
            elif state['remaining_usd'] <= 0:
                stopped = 'shared_dollars_exhausted'
            elif datetime.now(timezone.utc) >= timestamp(batch['deadline']):
                stopped = 'deadline'
            while not stopped and cursor < len(jobs) and len(active) < batch['max_workers']:
                job = jobs[cursor]
                cursor += 1
                active[pool.submit(_execute_one, job, prepared)] = job
            if not active:
                break
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                job = active.pop(future)
                try:
                    result = future.result()
                    receipt(job, result['status'], result)
                    if result.get('usage', {}).get('uncertain_attempts', 0):
                        stopped = 'runner_uncertain_attempt'
                except Exception:
                    receipt(job, 'unknown', error='job_exception_inspect_existing_artifacts')
                    stopped = 'job_exception'
    for job in jobs[cursor:]:
        receipt(job, 'not_dispatched', error=stopped or 'batch_stopped')
    counts = {'listed': len(jobs), 'dispatched': cursor, 'complete': sum(r['status'] == 'complete' for r in receipts),
              'not_dispatched': sum(r['status'] == 'not_dispatched' for r in receipts),
              'other': sum(r['status'] not in ('complete', 'not_dispatched') for r in receipts)}
    report = {'schema_version': 'overnight-batch-result-v1', 'batch_id': prepared['batch_id'],
              'status': 'stopped' if stopped else 'complete', 'stop_reason': stopped, 'counts': counts,
              'ledger': ledger.summary(), 'receipts_root': str(root)}
    write_new(root / 'summary.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=('prepare', 'execute'))
    parser.add_argument('--file', required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == 'prepare':
            result = publish_prepared(prepare_batch(args.file, args.sha256))
        else:
            result = execute_batch(load_prepared(args.file, args.sha256))
        print(canonical_json(result))
        return 0 if result.get('status', 'complete') == 'complete' else 1
    except Exception as exc:
        # Never include raw exception messages: upstream errors can contain data.
        print(canonical_json({'status': 'refused', 'error_code': 'batch_failed_inspect_artifacts',
                              'exception_type': type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
