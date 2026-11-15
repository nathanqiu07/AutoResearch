# Independent provenance fixes retest

Reviewer role: `parallel_gap_audit`, independent integration reviewer.
Scope: previous contracts/registry provenance failures, working source allowlists,
and declared implementation/prompt pins. New runner behavior belongs to the other
reviewers. Synthetic fixture and self-generated variants only; no live calls,
private data, production edits, or snapshot edits.

**Result: all five original actionable failing observations are now verified.**
Thirty checks verified, zero failed, five explicitly unverified trust boundaries.
The current 13 contract tests passed. All 154 snapshot files match the published
`AUDIT_SOURCE.json` hashes and remained unchanged.

## Previously failed cases now fixed

| Original observation key | Current observed behavior |
|---|---|
| `builder_mutates_approved_provenance` | The builder receives a separate config copy. Its changed allowlist, source hash, researcher and nested extractor settings do not alter the authoritative config or emitted provenance. The resulting profile remains complete and correctly names the original approved synthetic source. |
| `config_digest_stale_outer_rehashed` | Reload rejects with `ValueError: profile config hash mismatch`, even after the outer profile hash is recomputed. |
| `source_hash_disagrees_with_config` | Reload rejects with `ValueError: profile/config provenance mismatch: allowed_source_manifest_hash`. |
| `peer_string_false` | String `"false"` cannot enable the cross-researcher exception; rejected before any builder call. |
| `peer_integer_one` | Integer `1` cannot enable that exception; rejected before any builder call. Boolean `True` still permits the explicitly approved peer bundle. |

The mutable-builder probe also modifies a nested extractor-settings value, beyond
the original source/researcher mutations. Emitted settings remain `{}`, equal to
the validated authoritative input. This checks containment of accidental builder
mutation; it does not prove that arbitrary builder code is sandboxed.

`run-01/observations.json` contains a machine-readable before/after crosswalk under
`retested_original_failures`. The earlier report is retained byte-for-byte as
`run-01/prior_observations.json`, with its SHA-256 and source commit recorded.

## Working controls preserved

- The exact approved source set passes. Delivery-order changes still pass when
  the canonical allowlist is unchanged.
- Missing, extra, duplicate or changed sources; wrong manifest hashes; unapproved
  peer records; and unsorted allowlists still fail before builder execution.
- Original fixture hashes load. Content corruption and ordinary un-rehashed
  config changes remain rejected.
- The current v3 fixture's declared method/renderer/profile-prompt/consumer-prompt
  pins successfully reach one recording-only consumer call. The fixed synthetic
  probabilities remain `[0.25, 0.75]`, with `calibrated=False`.
- Changing any of those four pins still fails with unavailable status before a
  consumer call. Duplicate registration with changed prompt version/hash and
  malformed prompt SHA metadata remain rejected.

## Remaining boundaries, not newly observed failures

1. Registry source hashing is unchanged. The previous self-generated stale-import
   demonstration was not repeated; runtime snapshots must be frozen before import
   and execution. No stale imports or source drift were observed here.
2. Prompt SHA metadata is declared by the builder owner; this retest does not prove
   it matches every actual extractor request.
3. A defining-module hash is not a verified transitive dependency fingerprint.
4. Exact allowlist comparison checks caller config; evaluator authorization and
   frozen job authority require the separately owned runner/evaluation boundary.
5. Exact source matching covers document IDs and content hashes, not independent
   validation of all attribution, date, version or span metadata.

The fixed internal hashes establish consistency, not cryptographic authorization.
No remaining failure was observed in the scoped retest. This is not a complete
audit of all new runner functionality or all possible serialized inputs.

## Provenance

- Source commit: `05c503e5f6170a690a13feb75cbe2dc65d430ba8`.
- Implementation commit: `5fc86572e7ab527a405146290834408dea5227da`.
- Fixture: `docs/overnight/gio-profile-20261115/infrastructure/fixture-v3.json`.
- Fixture SHA-256: `cb6e8beecb6976e837be5d588471d0f5ac5c45cd4df02533b31bcabb640127e7`.
- Shared contract SHA-256: `0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43`.
- `contracts.py` SHA-256: `512e66d7281b7b686ee9b25c4d37e8dfcf3613c9c36bdfc92c0d3d11e684332b`.
- `registry.py` SHA-256: `5ce7006906445b0a73661566698e2f885f5a6b1c90161db87bff41378b727d41`.
- Audit script SHA-256: `a85cef45d75d0023bfa46bbc4ec98987366ae73859fb57bb8d2161498a69ace2`.

## Reproduce

Use equivalent immutable inputs and a new output directory. The script refuses to
overwrite prior evidence and exits nonzero if any scoped assertion fails, tests
fail, fixture identity differs, or the snapshot changes.

```sh
python3 -B /tmp/gio-integration-audit-staging/neutral-contract-07/provenance/reproduce.py \
  --source-root /tmp/gio-integration-audit-contract-05c503e \
  --shared-contract '/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/docs/superpowers/plans/2026-11-15-profile-search/SHARED_CONTRACT.md' \
  --prior-report /tmp/gio-integration-audit-staging/neutral-contract-06/provenance/run-01/observations.json \
  --output /tmp/gio-integration-audit-staging/neutral-contract-07/provenance/run-02
```

Run-01 exited 0. The JSON report records exact argv, cwd, interpreter, input/script
hashes, every expected/observed result, and complete source hashes. Existing-test
command (cwd: the snapshot):

```sh
python3 -B -m unittest tests.test_overnight_contracts
```

Observed 13 tests passed, exit 0; full stdout/stderr are retained beside the report.
This retest did not rerun the whole repository suite.
