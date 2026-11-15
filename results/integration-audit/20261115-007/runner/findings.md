# Independent runner audit: implemented offline lane

Pinned source: `05c503e5f6170a690a13feb75cbe2dc65d430ba8`.
Implementation: `5fc86572e7ab527a405146290834408dea5227da`.
All 154 `AUDIT_SOURCE.json` file hashes matched before and after the audit.

Five concrete boundary failures reproduced. The existing 11 runner tests pass.
This audit used invented documents and decisions, recording backends, and no
network or live inference. Owner files were not changed. Results concern job
plumbing and provenance, not researcher fidelity or awareness measurements.

## Failed checks

### P1 — Caller-owned items/settings can change after hash validation

`runner.py:221` copies the manifest but keeps caller-owned `config` and `items`.
Their hashes are checked once at lines 97 and 108, then the same mutable objects
are consumed later at lines 266–278.

A synthetic backend callback changes the second item context and temperature
after the first call. The job still returns `complete` with two predictions
under the original `config_hash` and `items_hash`. The second trace contains the
changed temperature and context. The first prediction's reported cache key also
differs from its actual trace/cache key because it is computed after the callback
from the now-changed settings (line 278).

This does not require changing the immutable profile or pinned source. The
callback is a deterministic stand-in for a caller changing shared dictionaries
while an asynchronous/slow backend call is in progress.

Evidence: `evidence/mutable_inputs.json`, including original and changed inputs,
both digests, actual request settings, and mismatched first-row cache keys. Full
synthetic traces and result are under `evidence/mutable_inputs/`.

Next fix: freeze/deep-copy execution inputs before validating them, and record
the cache key/settings actually used by the gate rather than reconstructing
them from mutable inputs after a call.

### P2 — Cache hits bypass the declared wall-time limit

`runner.py:169–174` returns a cache hit before the `max_seconds` check at line 175.
A mocked monotonic clock advances to 31 seconds after the first call against a
30-second allocation. With two identical synthetic prompts, the cached second
prediction is accepted and the job returns `complete`. With caching disabled,
the matched control stops the second prediction with `allocation_exhausted`.

This demonstrates continued work after the limit, not extra paid API spend.
Absolute lease/deadline expiry is separately checked before cache access and
passes the owner's existing test.

Evidence: `evidence/elapsed_with_cache.json` and
`evidence/control_elapsed_without_cache.json`, plus their saved run directories.

Next fix: enforce elapsed wall time before both cached and uncached paths.

### P2 — Missing allocation mode leaves a claim but no result

`_validate` checks numeric allocation limits but does not require `cost_mode`
(`runner.py:86–94`). A correctly hashed manifest lacking that field is claimed
and its manifest is written. The backend is considered unsupported, but
`gate.usage()` then raises `KeyError('cost_mode')` at line 206. No `result.json`
is written. There are zero backend calls.

The README explicitly requires `cost_mode`; this is a malformed-input handling
and durable-result gap, not authorization bypass or overspend.

Evidence: `evidence/missing_cost_mode.json` and the retained claim/manifest under
`evidence/missing_cost_mode/`.

Next fix: validate the full allocation shape before claiming, and preserve a
typed terminal result for failures after a claim is acquired.

### P2 — Build identity does not bind all builder-visible source metadata

The build path validates the ID/content-hash source manifest (`runner.py:123`;
`contracts.py:44–46`) but passes each whole document to the builder
(`contracts.py:142`). Extra fields such as `author` are not bound by the job's
source hash or another full document-input hash.

Two separately isolated synthetic builds use the identical manifest/config,
document ID, and content. Only the builder-visible author field changes. Both
are accepted under the same job ID, and a deterministic metadata-reading builder
creates different profiles. Neither build makes a backend call. Separate
namespaces are used only to compare accepted input semantics; this is not a
claim that the canonical lease can be bypassed.

The issue is the unbound input field, not the expectation that stochastic builds
must always produce identical output. The shared contract includes document
author/contribution metadata and asks job identity to cover the complete
semantic manifest.

Evidence: `evidence/build_metadata_binding.json` and both saved synthetic builds.

Next fix: bind every builder-visible source field and relevant ordering, or
strip/reject fields that are intentionally outside the hashed input contract.

### P2 — Declared extractor settings can be saved as complete despite different actual calls

The gate accepts arbitrary actual keyword settings (`runner.py:161,181,185`).
The completed profile records `config['extractor_settings']` directly
(`contracts.py:164`) without checking it against the gated call.

A synthetic registered builder declares temperature 0/max_tokens 128, then calls
the gate with temperature 1/max_tokens 32. The trace truthfully records 1/32,
but the completed profile records 0/128 and status `complete`.

This proves an infrastructure boundary gap. It does not show that an existing
candidate method has actually ignored its settings. A multi-call builder may
need an explicit per-call policy rather than one fixed setting pair.

Evidence: `evidence/build_settings_binding.json` and its saved trace/profile.

Next fix: enforce a declared extraction settings policy or clearly separate
declared settings from observed per-call settings in the completed artifact.

## Verified controls

- All 11 owner runner tests pass, including input/profile/backend mismatch
  rejection, label allowlisting, call limits, lease expiry, no retries after
  uncertainty, and confirmation output path rejection.
- Two concurrent threads sharing the canonical claim root produced exactly one
  synthetic backend call; the other worker received `FileExistsError`.
- An uncertain first call preserved started/failed traces, retained its claim,
  blocked the following item, and rejected a second run. No duplicate call.
- The no-cache wall-time control correctly stopped further predictions.
- Actual immutable `runner-fixture-v2` passes semantic job ID, manifest hash,
  lease-manifest equality, every trace hash, cache response hashes, and cache
  filename/key checks. This is a check of the included historical artifact,
  not a freshly substituted fixture.

## Unverified or explicitly outside this milestone

- Shared API dollar/concurrency adapter: the handoff declares it future work;
  its absence is not counted as an implemented failure.
- Evaluator confirmation receipt and final-use authority: likewise future work;
  no final inputs or confirmation execution were used.
- The separately published baseline adapter at `675f6d2` is not integrated into
  this pinned snapshot. Its retrieval-decision binding is a later integration
  dependency, not a surprise missing-feature finding here.
- Real backend cost/timeout enforcement, distributed locking, and power-loss
  persistence were not exercised. The concurrent lease control covers cooperative
  workers on one filesystem, consistent with the README's stated scope.

## Reproduction and artifact interpretation

Run from any directory, with the pinned snapshot and a fresh output directory:

```sh
python3 -B reproduce.py --source-root /path/to/pinned-snapshot --out /path/to/new-evidence --contract /path/to/SHARED_CONTRACT.md
```

The contract argument is optional and used only to pin its content hash. All
execution artifacts are synthetic and written under `--out`. The reproducer
never imports a live provider or reads credentials. It checks all source hashes
before and after, runs the owner tests, then runs each decisive probe.

`evidence/command.json` preserves exact invocation/status and reproducer hash.
`evidence/owner-tests-command.json` and the two test stream files preserve the
owner test command/status/output. `evidence/report.json` records verified,
failed, and unverified outcomes. Audit exit 0 means all probes completed and
their observations matched the saved report; it does not mean the five failed
contract checks passed.
