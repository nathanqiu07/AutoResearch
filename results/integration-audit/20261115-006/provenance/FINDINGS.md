# Independent CONTRACT_READY provenance audit

Reviewer role: `parallel_gap_audit`, independent integration reviewer.
Scope: `contracts.py`, `registry.py`, and the consumer's declared pin equality
checks. Consumer cap/response-status/rendering checks belong to the other reviewer
and are not repeated here. Only the released synthetic fixture and self-generated
variants were used. No live calls, real data, production edits, or snapshot edits.

**Result:** 24 checks verified, six failed observations grouped below, and four
explicit unverified boundaries. The existing seven contract tests passed.
All snapshot files match `AUDIT_SOURCE.json` and remained unchanged during audit.

## Actionable failures

### 1. A builder can change approved provenance after validation

At `contracts.py:117-119`, the source set is validated and then the same cloned
but mutable `config` dictionary is handed to the builder. Artifact fields and
hashes at lines 138-150 are derived from that dictionary after the call.

The self-generated `mutating_builder` read the approved synthetic document, then
set `allowed_sources=[]`, changed the allowed-source hash to `digest([])`, and
changed `researcher_id`. `build_profile` returned a **complete**, internally
content-addressed profile whose content still cited `synthetic-fit-1` but whose
provenance declared an empty approved set and a different researcher. This did not
require external artifact editing or recomputing its hashes by hand.

Evidence key: `builder_mutates_approved_provenance` in `run-01/observations.json`.
The emitted source hash is
`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`
(empty list), instead of approved
`a4273a2164ce799882acbbdd698b005e3fd264ea7744ae52c53f5ab10db7ddf7`.

Recommended correction: keep an immutable authoritative config for validation
and artifact metadata, and pass a separate copy to builders; alternatively reject
any mutation before packaging. A regression should compare emitted provenance
to the exact config validated before builder execution.
This probe does not show that a released trusted builder currently mutates config;
it shows that accidental in-place normalization by such a builder is not contained.
If builder purity is instead an explicit trust assumption, document that boundary.

### 2. Reload validates outer/content hashes but not nested config consistency

`ProfileArtifact.from_dict` (`contracts.py:77-89`) checks schema, status, content
hash and outer profile hash. It does not recompute `config_id` from `config` or
cross-check the duplicate source-manifest field against config.

Two synthetic variants were accepted:

- Change `config.replicate_id` from 0 to 999, leave the original `config_id`, and
  recompute only the outer `profile_id`.
- Change top-level `allowed_source_manifest_hash` to 64 zeroes, retain the original
  config/source hash, and recompute only the outer `profile_id`.

Evidence keys: `config_digest_stale_outer_rehashed` and
`source_hash_disagrees_with_config`. This is an internal-consistency failure,
**not a claim that unkeyed hashes authenticate evaluator authorization**. A caller
may legitimately compute a new outer hash; that should not make contradictory
nested identity claims valid. These probes tested reload acceptance, not a live
consumer or evaluator reservation.

Recommended correction: verify `config_id == digest(config)` and the duplicated
config/source/provenance fields on reload. Preserve the existing outer checksum.

### 3. Non-boolean peer approval enables the cross-researcher exception

`contracts.py:57` uses truthiness for `approved_peer_sources`. A record whose
researcher differs from the requested researcher was correctly rejected with
boolean `False`, but was accepted and reached the builder when the flag was the
string `"false"` or integer `1`. Boolean `True` correctly allowed the approved
peer bundle. Exact document IDs/content hashes remained matched in these probes.

Evidence keys: `peer_false`, `peer_true`, `peer_string_false`, `peer_integer_one`.
This is a type-validation failure for an explicit permission flag; it does not
bypass the separate ID/content allowlist comparison.

Recommended correction: accept only a boolean flag, and enable the exception only
when its value is exactly `True`.

## Conditional implementation-pin failure

`registry.py:32-34` hashes current source-file bytes, which need not be the bytes
that produced an already-imported function. A self-generated module was loaded
with code returning `loaded-v1`, its own temporary file was changed to return
`disk-v2`, and the original function was then registered. The builder executed
`loaded-v1` while its artifact claimed the v2 file hash:

- Executed v1 source: `f034cfb0585b604d426ab9c2e6aa453212fea52dc23de88e1b7a7ad0419d5829`.
- Registered/profile hash: `725c384dc20a03d8d98d71cd61672012410736d2e6bf15b2b880da992749e983` (v2 on disk).

Evidence key: `stale_import_runtime_pin`. The code does not detect this drift.
**No such drift was observed in the audited snapshot.** The shared contract's
immutable-runtime requirement can prevent the scenario if enforced before import;
this registry check alone does not enforce it. Treat this as a conditional boundary
failure, not evidence that the released fixture ran a different implementation.

## Verified behavior

- Missing, extra and duplicate documents; changed content with stale or updated
  hashes; wrong manifest hash; unapproved cross-researcher records; and an unsorted
  allowlist fail before any builder call.
- Reordering delivered documents preserves the same exact approved set and passes.
- Original fixture content/profile hashes load successfully. Corrupted content
  fails even when only the outer hash is recomputed. Ordinary config corruption
  without recomputing the outer hash also fails.
- Fresh build config IDs match their config digest. Registration matches current
  defining-module bytes in the normal no-drift case.
- Changed declared method/renderer/profile-prompt/consumer-prompt pins fail with
  unavailable status before the recording consumer is called.
- Re-registering one method with changed prompt version or prompt hash fails;
  malformed prompt SHA syntax fails.

These observations are individually keyed in the JSON report, with expected
behavior, returned value or exception, builder/consumer call counts and assessment.

## Explicitly unverified boundaries

1. Prompt SHA is caller-declared metadata. Registry format/duplicate checks do not
   prove correspondence to the extractor requests a callable actually makes.
2. The defining module hash does not establish a complete transitive dependency
   fingerprint. This audit did not test real method dependency closures.
3. Allowlist equality is checked against caller config, not an external evaluator
   authorization record. Frozen jobs/runner authority are a later milestone.
4. Source matching covers ID and delivered-content hash. Extra document metadata
   and real attribution/version/span evidence were not validated by this audit.

These are bounded claims about what was checked, not additional alleged failures.

## Provenance and reproduction

Source commit: `d66051c6b792e2a9062f334535cf61ff9f51a15a`.
Implementation commit: `bb3a6f5cc370c1d3bf52361287cd3149bd294f7b`.
Fixture SHA-256: `995725bb52d51a89a474e8f5cd0e9a3a3a7b1cae3c4bab8ca827164a37f4656a`.
Shared contract SHA-256: `0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43`;
this matches the CONTRACT_READY handoff's declared contract hash.

- `contracts.py`: `cd6027731cb454bedba0d5ce1244b810d26400215d482a91c6640ad83af96105`.
- `registry.py`: `5ce7006906445b0a73661566698e2f885f5a6b1c90161db87bff41378b727d41`.

Run from any directory, supplying an equivalent immutable snapshot and the shared
contract file. Use a new output directory; existing runs are never overwritten.

```sh
python3 -B /tmp/gio-integration-audit-staging/neutral-contract-06/provenance/reproduce.py \
  --source-root /tmp/gio-integration-audit-contract-d660 \
  --shared-contract '/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/docs/superpowers/plans/2026-11-15-profile-search/SHARED_CONTRACT.md' \
  --output /tmp/gio-integration-audit-staging/neutral-contract-06/provenance/run-02
```

The reproducer exited 0 in run-01, meaning evidence capture and source-integrity
checks succeeded, **not** that every contract check passed. Its JSON report has
the exact argv, cwd, interpreter, script hash, all source hashes, assessment
counts, and existing-test command/exit code. Existing tests: seven passed, exit 0;
stdout/stderr are retained. The only changed module was the self-generated stale
import fixture inside the output directory. No audited file was changed.
