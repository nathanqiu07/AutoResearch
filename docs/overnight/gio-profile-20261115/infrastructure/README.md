# Neutral profile contract v1

This additive package leaves existing UserModel guards and shared method behavior
unchanged. It accepts neutral text profiles only. Legacy compatibility remains
unverified: the audit owner's synthetic M2 reproducer shows why artifact identity
alone is insufficient (audit branch `codex/gio-integration-audit`, `0ebcf7b`).

## Builder registration and sources

`register_builder(method_id, function, *, prompt_version, prompt_sha256,
allows_empty=False)` pins the function's source module bytes. Candidate owners
provide the callable and metadata to infrastructure; only infrastructure edits
the registry. A callable receives `(documents, config, extractor)` and returns
`{"content": <any JSON value>, "status": "complete", "fit_usage": {...}}`.
Status may instead be empty, invalid, unsupported, unavailable, or abstained.
Only declared controls may set `allows_empty=True`.

`build_profile(documents, config, extractor)` returns an immutable ProfileArtifact.
Required config keys: method_id, researcher_id, allowed_sources,
allowed_source_manifest_hash, personalization_cap, replicate_id, code_sha and
extractor_settings. Extra method-specific config is preserved and hashed.

Each document requires document_id, researcher_id, content and content_sha256.
The last field is SHA256 of the exact delivered UTF-8 content, without further
normalization. The evaluator-approved allowlist is sorted by document_id, with
exactly document_id and content_sha256 per row. Missing, extra, duplicate or
changed sources fail before a builder runs. Approved peer bundles require an
explicit approved_peer_sources config flag and exact allowlist. No URL is fetched.
Raw fetched-byte hashes belong in separate observed_content_sha256 provenance.

Canonical hashes use `json.dumps(value, sort_keys=True, separators=(',', ':'),
ensure_ascii=False, allow_nan=False).encode('utf-8')`. ProfileArtifact stores this
serialization internally; `to_dict()` and field access return fresh values.

## Consumer

`predict_profile(profile, context, options, consumer, config)` returns the existing
Prediction on success. ProfileFailure provides `status` and `code` for failures;
there is no generic fallback. Consumer config must specify
method_implementation_hash, renderer_implementation_hash, profile_prompt_version,
consumer_prompt_version and settings `{temperature, max_tokens}`.

The sole payload is `{context, options, personalization}`. Personalization is the
canonical JSON of **all** rich content; intentional empty controls use an empty
string. Source/config/provenance metadata is not personalization. The rendered
text and payload each have hashes. The renderer implementation hash includes both
consumer.py and contracts.py. Saved/runtime renderer or prompt mismatches fail
before any backend call. Extractor and fresh consumer identities are separate.
Learned weights and calibration cannot transfer through this neutral format.
Valid Prediction objects remain explicitly uncalibrated.

Caps and rendered counts use `utf8-bytes-upper-bound-v1`, a conservative byte
bound, **not measured tokenizer counts**. Equal numeric caps do not prove equal
tokenizer usage. Oversized profiles remain invalid; no fields are dropped to fit.

## Offline fixture

From the repository root:

```sh
python3 -m autoresearch.taste.overnight fixture --output /tmp/profile-fixture-unique.json
python3 -m unittest tests.test_overnight_contracts
```

The fixture contains invented text, no researcher data or held-out labels.
It records the full payload/profile. Fixed probabilities test plumbing only.
Output paths are exclusive. The first fixture remains pinned to its original
code commit; later implementation hashes intentionally cannot consume it silently.

## Assigned job runner

`runner.run_job(manifest, lease, *, output_root, lease_root, config, profile=None,
items=None, documents=None, consumer=None, extractor=None, cache_root=None,
private_root=None, confirmation_receipt=None)` executes one assigned job.
Use the canonical lease_root supplied by the coordinator across all clones.
An exclusive, fsynced job claim is never deleted after a crash or failure.
Changing an output path does not permit reuse. Coordination remains cooperative:
a hostile caller sharing the OS account can bypass Python or select a different
root. This is not an authentication boundary or distributed lock service.

The manifest fields are illustrated by `python3 -m autoresearch.taste.overnight
job-fixture --output-root /tmp/unique-job-fixture`. Required semantic fields include
the schema/campaign/stage/kind, all source/profile/config/item hashes, exact backend
identities, option schedule, replicate/cap/code, allocation, retry policy, parent
jobs and expected outputs. `runner.job_id(manifest)` hashes every field except
job_id, lease, created_at and updated_at. A lease has job_id, lease_id, owner and
timezone-aware expires_at. Only the coordinator supplies real leases.

Allocation requires finite max_calls, max_seconds, max_usd, cost_mode and an
authorization_source. Modes are offline, unpriced_cli or priced_api. The runner
admits only the existing bounded OpenAI adapter for priced API use; other API
providers remain unsupported pending conservative cost reservation support.
CLI costs remain unavailable rather than zero. A live backend's enforced timeout
must fit the remaining wall time. Every attempted call gets a durable started
trace before invocation and a complete/failed trace after it. No retries occur.
Uncertain failures retain their attempt and lease. Existing backend budgets and
rate limits still apply. Instantiate a fresh backend for each job.

Decision items use exactly item_id, researcher_id, context, options and
option_order_id. Extra fields, including answers, are rejected. Invalid, empty,
abstained and unavailable predictions remain explicit rows. Cache keys include the
complete semantic manifest plus actual prompt/settings; cache entries are
content-hashed, immutable and not shared across changed interventions.

Confirmation requires the evaluator's authoritative receipt and store ID. The
runner calls evaluation.validate_confirmation_receipt before output or exposure;
output, lease, trace and cache paths must resolve within the private root, with
symlink escapes rejected. Confirmation results returned by the function are also
private. `public_handoff(result)` returns only hashes, counts, status and usage.
The evaluator owns final identity reservation and concrete final-use authority.
Capabilities/utility are explicitly unavailable in this runner; their owners keep
their own harnesses. Offline plumbing tests establish no researcher fidelity.
