# Independent neutral-profile contract audit

Audited release: `d66051c6b792e2a9062f334535cf61ff9f51a15a`, implementation
`bb3a6f5cc370c1d3bf52361287cd3149bd294f7b`. Only the released synthetic fixture
and newly generated synthetic variants were used. No live calls, real researcher
material, final labels, production edits or inference-setting changes occurred.

The published fixture reproduces byte for byte (SHA256
`995725bb52d51a89a474e8f5cd0e9a3a3a7b1cae3c4bab8ca827164a37f4656a`). All seven
existing contract tests pass. The additional probes nevertheless reproduce six
actionable validation gaps:

| Boundary | Observed failure | Evidence |
|---|---|---|
| Loaded profile cap | Cap 1 permits 545 rendered UTF-8 bytes and one consumer call; normal build-time cap enforcement works | `consumer/run-01/loaded-cap-bypass.json` |
| Consumer response status | Explicit invalid/unavailable/unsupported/empty statuses are discarded when probabilities are valid | `consumer/run-01/explicit-consumer-failure-statuses.json` |
| Malformed probability | A 400-digit integer raises raw OverflowError instead of structured invalid status | `consumer/run-01/oversized-integer-response.json` |
| Builder configuration | Builder mutation changes already-validated source/researcher provenance before packaging | `provenance/run-01/observations.json`: `builder_mutates_approved_provenance` |
| Loaded config consistency | Stale config ID and conflicting duplicate source hash survive outer-hash recomputation | same report: `config_digest_stale_outer_rehashed`, `source_hash_disagrees_with_config` |
| Peer permission type | String `"false"` and integer 1 grant the peer-source exception | same report: `peer_string_false`, `peer_integer_one` |

The root independently reran both reviewers' reproductions; outputs are under
`root/consumer-confirmation/` and `root/provenance-confirmation/`. Exit zero means
the evidence capture reproduced the behavior, including these failures. It does
not mean the contract was accepted. The provenance report has 24 verified checks,
six failed observations (some belong to one group above), and four unverified
boundaries. Counts are not interchangeable with numbers of bugs.

Working safeguards should be preserved: rich fields survive rendering; tested
intentional-empty controls exclude personal metadata; noncomplete profile
statuses stop calls; source ID/content allowlists and ordinary hash tampering
are checked; declared pin mismatches fail; legacy backend guards remain intact;
predictions remain uncalibrated. Empty-control checks do not cover a wrongly
populated control builder, and none of these checks establishes model quality.

A separate generated-module probe shows current disk hashes need not identify an
already-imported function after its source file changes. No such drift occurred
in the audited snapshot. A runtime frozen before import can prevent that case;
registry hashing alone does not establish the assumption. External evaluator
authorization, full dependency pinning, and correspondence between declared
prompt hashes and actual extraction requests remain unverified here.

Both detailed findings files state evidence and limits. The coordinator received
all findings and assigned infrastructure fixes; this package preserves the old
release. A new pinned release needs a fresh audit.

## Reproduce

Use a git repository containing the audited commit. Create a new snapshot with
the exact archive paths recorded in `source/AUDIT_SOURCE.json` (the `argv` field),
then copy that JSON into its root as `AUDIT_SOURCE.json`. All 88 extracted files
are hashed there. Local paths in invocation records are provenance, not required
machine-specific code constants. Relevant source files and the original released
fixture/handoff are also retained under `source/` for direct inspection.

Run with fresh output directories:

```sh
python3 -B consumer/reproduce.py --source-root SNAPSHOT --out NEW_CONSUMER_OUTPUT
python3 -B provenance/reproduce.py --source-root SNAPSHOT \
  --shared-contract provenance/run-01/shared-contract.md --output NEW_PROVENANCE_OUTPUT
```

The scripts refuse to overwrite old output. The provenance probe deliberately
changes only its own generated module in its output directory; it leaves the
audited snapshot unchanged. All supplied source files matched the archive hash
map again after both independent confirmation runs.
