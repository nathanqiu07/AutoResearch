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
Output paths are exclusive. Runner/confirmation integration follows this milestone.
