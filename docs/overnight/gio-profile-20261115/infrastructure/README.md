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

## Exact quote resolution

`resolve_quote_sources(content, documents)` returns `(new_content, records)` for
new quote-only extraction protocols. `QUOTE_RESOLVER_VERSION` identifies the
deterministic helper. A source is any `sources` list entry or a mapping containing
`document_id` or `quote`; it must have exactly those two keys. The helper adds
`start` and `end` only for one exact, case-sensitive occurrence fully contained
inside one permitted span. It never trims, normalizes, matches fuzzily or repairs
offsets supplied by the model. Python Unicode character indices are used, not
UTF-8 byte offsets. Overlapping ranges cannot double-count the same occurrence;
different occurrences, including overlapping text matches, remain ambiguous.

Document IDs and delivered content hashes are checked before matching. Present
`permitted_spans` must be a list of valid integer start/end ranges; extra approved
range metadata is retained in documents but not used for matching. Compatibility
semantics remain: absent spans permit the whole document; explicit `[]` permits
nothing. Adjacent or overlapping ranges are not merged to admit a quote that does
not fit inside an individual approved range.

Inputs are copied. Each success record has resolver_version, source_path (a list
of keys/indices), document_id, quote_sha256, status=`resolved`, start and end.
`QuoteResolutionError(ValueError)` exposes `.code` and `.resolution_records`;
failure records have status=`invalid` and error_code. Diagnostics contain hashes,
not quoted source text. No partially resolved content is returned on failure.
Stable codes are quote_content_json, quote_source_document, quote_document_hash,
quote_document_spans, quote_source_shape, quote_source_quote, quote_absent,
quote_unpermitted and quote_ambiguous.

Builders using this helper must declare a new prompt version, preserve the raw
response hash and resolver records/version in fit_usage, and then run their
existing strict source-span and schema validators. Old jobs remain invalid and
are not rewritten. This contracts.py change alters the common renderer pin;
profiles and runtime manifests must be rebuilt. The regenerated synthetic
fixture-v6 records the new pin without changing historical fixtures.

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
It snapshots all JSON execution inputs before validation, so caller callbacks
cannot change later items, source records or settings behind the pinned hashes.
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
Build manifests also require documents_hash over the full approved document
records, including permitted spans and version metadata. Artifacts preserve that
hash. The coordinator separately verifies the released bundle file hash.

Allocation requires finite max_calls, max_seconds, max_usd, cost_mode and an
authorization_source. Modes are offline, unpriced_cli or priced_api. The runner
admits the existing and overnight bounded OpenAI adapters for priced API use; other API
providers remain unsupported pending conservative cost reservation support.
CLI costs remain unavailable rather than zero. Live manifests require an absolute
timezone-aware deadline. The lease and deadline are checked before every call and
cache access. A live backend's enforced timeout
must fit the remaining wall time. Every attempted call gets a durable started
trace before invocation and a complete/failed trace after it. No retries occur.
Uncertain failures retain their attempt and lease and hold remaining job calls. Existing backend budgets and
rate limits still apply. Instantiate a fresh backend for each job.
Relative max_seconds also applies before cache access. Both prediction and
extraction calls must supply exactly the declared temperature and max_tokens;
prompt and optional system text are recorded separately in the hashed trace.
Builders must set config.extractor_settings to those actual call arguments.
Every assigned build requires exactly those two keys with explicit valid values,
including deterministic zero-call controls. The coordinator resolves defaults
before hashing the config; the runner never inserts defaults after registration.
Unknown provider options such as top_p, and reasoning settings owned by the
backend, are rejected here before the job is claimed. Direct synthetic
build_profile fixtures outside job execution may still declare no-call settings.
Missing/unknown allocation.cost_mode is rejected before a durable claim is made.

Decision items use exactly item_id, researcher_id, context, options and
option_order_id. Extra fields, including answers, are rejected. Invalid, empty,
abstained and unavailable predictions remain explicit rows. Cache keys include the
complete semantic manifest plus actual prompt/settings; cache entries are
content-hashed, immutable and not shared across changed interventions.
The common consumer binds lexical_retrieval, profile_retrieval and future
semantic_retrieval profiles to their exact config.decision `{context, options}`.
Missing bindings, changed context or reordered options fail before a backend call.
Use one separately built retrieval profile for each declared decision/order.

Confirmation requires the evaluator's authoritative receipt and store ID. The
runner calls evaluation.validate_confirmation_receipt before output or exposure;
output, lease, trace and cache paths must resolve within the private root, with
symlink escapes rejected. Confirmation results returned by the function are also
private. `public_handoff(result)` returns only hashes, counts, status and usage.
The evaluator owns final identity reservation and concrete final-use authority.
Capabilities/utility are explicitly unavailable in this runner; their owners keep
their own harnesses. Offline plumbing tests establish no researcher fidelity.

## Declared API adapter and campaign ledger

`DollarLedger(path, *, max_usd, deadline, max_inflight=2)` uses SQLite transactions
and integer nanodollars. Every worker/process must use the **same coordinator
path**. Reopening refuses a changed limit, deadline, concurrency, or pricing
version. Reservations count against the total before an HTTP request. Successful
responses settle to conservatively estimated usage; failures keep the full hold
plus any known usage. Uncertain outcomes block all later reservations. A crash
leaves a pending hold and concurrency slot; nothing expires or resets it.

`OpenAIResponsesBackend(model=..., reasoning=..., ledger=..., max_usd=...,
budget=..., timeout=...)` additionally enforces the explicit per-job allocation.
It supports the verified gpt-6-luna, gpt-6-sol and gpt-6-astra price table. Reasoning
must be explicit: low/medium/high/xhigh/max; luna and sol also allow none. API ultra
is unavailable. The request has store=false, no tools and default service tier.
It also pins prompt_cache_options to `{mode: "implicit", ttl: "30m"}`.
Temperature is not sent, and identity records that fact. Identity also records
reasoning and the adapter implementation hash; manifests compare the complete
identity before execution. Existing shared backends.py remains untouched.

Requests stay below the conservative 272,000-token short-context boundary using
UTF-8 bytes plus overhead and maximum output. Input/output bounds (USD per million
tokens) are luna 0.125/0.50, sol 2.5/10, astra 12.5/50. These use 1.25 times the
base input prices to cover 30-minute cache writes, verified on November 15 against
[pricing](https://developers.openai.com/api/docs/pricing), linked model pages and
[prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching).
All input receives this upper-bound rate, including cheaper cached tokens;
all output, including reasoning, is charged. These are conservative estimates,
not invoices. Cost reports state `conservative_30m_cache_write_upper_bound_not_invoice`.
One urllib request is made with no automatic retry.
The corrected pricing version cannot reopen a ledger created under the earlier
base-input-only version. The coordinator must preserve that ledger and its evidence,
account for prior input-cost bounds, and explicitly assign a new phase ledger
against the remaining total allocation. No code resets or migrates old balances.
Invalid/incomplete output is visible and holds the lane. Keys are read only from
the process environment and never included in logs, manifests, or errors.
Partially reported token usage preserves each valid component and records which
components remain unknown. Runner token totals are null when incomplete; known
partial totals and unknown-attempt counts remain in budget_detail. The full
uncertain dollar reservation remains held in addition to known reported usage.

The coordinator must still reserve scaling funds and allocate total calls across
jobs. CLI panels remain separately declared and require coordinator concurrency
control. Adapter tests use mocked transport only; availability of each actual
API model requires an assigned smoke job. The adapter does not select jobs, set
a campaign budget itself, or authorize final-data use.
