# Fix retest and first runner audit

Pinned release `05c503e5f6170a690a13feb75cbe2dc65d430ba8`, implementation
`5fc86572e7ab527a405146290834408dea5227da`. All data is synthetic. No live calls,
researcher corpus, final labels, model/settings changes, or owner-code edits.

The six previously reported consumer/provenance issue groups are fixed for the
reproduced cases. The new runner has five separate reproducible gaps. Both
statements are scoped below; this is not an overall live-readiness verdict.

## Prior failures retested

`consumer/findings.md` and `provenance/FINDINGS.md` give paired old/new evidence:

- Loaded cap 1 with 545 rendered bytes is rejected by the decoder and by the
  consumer's own revalidation before calls.
- Explicit failed response statuses are retained. The same 400-digit probability
  produces structured invalid status instead of raw OverflowError.
- Builder mutations no longer alter authoritative source/researcher/config
  metadata, including nested extractor settings.
- Stale config identity and conflicting source hashes are rejected.
- String `"false"` and integer 1 cannot grant the peer-source exception.

Consumer probes verify nine claims (three fixes plus six controls); provenance
probes verify 30 checks with zero failures and five unverified trust boundaries.
Each reviewer ran the 13 relevant contract tests successfully. Root independently
reran both probes, retaining outputs under `root/`. Positive controls for rich
content, empty-request invariance, source matching, declared pins, calibration
separation and legacy guards still pass. These are not accuracy measurements.

The v3 fixture reproduces byte for byte:
`cb6e8beecb6976e837be5d588471d0f5ac5c45cd4df02533b31bcabb640127e7`.
All 154 archived source files remained unchanged. Package 006 remains immutable;
probe adaptations for the stricter loader are explained rather than counted as
success merely because old setup code now raises.

## New runner findings

See `runner/findings.md` and `runner/evidence/report.json` for complete evidence.
Root independently reproduced the same cases under `root/runner-confirmation/`.

| Boundary | Reproduction |
|---|---|
| Execution input immutability | A synthetic callback changes the next item and temperature after validation. The job reports complete under old hashes; one reported cache key also differs from its trace. |
| Relative wall-time cap | A simulated clock passes `max_seconds`; an uncached call stops, but a cache hit still produces a prediction. Absolute deadline checks are separate. |
| Failure record | Missing `allocation.cost_mode` creates a durable claim, then raises KeyError without writing `result.json`; no backend call occurs. |
| Build input identity | Changing builder-visible author metadata produces different content under the same job identity in separate synthetic namespaces. This does not bypass a canonical lease. |
| Extraction settings | A synthetic builder requests different generation settings than declared; the trace records them, but the complete profile retains the declared settings without qualification. |

All 11 existing runner tests pass. Four additional controls verify single execution
under concurrent claims, no retry after uncertain transport failure, uncached
elapsed-time enforcement, and the committed runner fixture's hash links. The
five failing cases remain failures even though the evidence script exits zero:
that exit means reproduction completed.

The coordinator received all five findings for infrastructure changes. Shared
API-dollar/concurrency accounting, evaluator confirmation receipts, real backend
timeouts/costs, power-loss durability and later retrieval integration remain
unverified dependencies. They were not counted as hidden implemented failures.

## Reproduce and inspect

`source/AUDIT_SOURCE.json` records the exact archive command and all input hashes.
Create an equivalent immutable snapshot from the pinned git commit and copy that
file to the snapshot root as `AUDIT_SOURCE.json`. Use fresh output directories:

```sh
python3 -B consumer/retest.py --source-root SNAPSHOT \
  --old-evidence ../20261115-006/consumer --out NEW_CONSUMER_OUTPUT
python3 -B provenance/reproduce.py --source-root SNAPSHOT \
  --shared-contract ../20261115-006/provenance/run-01/shared-contract.md \
  --prior-report ../20261115-006/provenance/run-01/observations.json \
  --output NEW_PROVENANCE_OUTPUT
python3 -B runner/reproduce.py --source-root SNAPSHOT --out NEW_RUNNER_OUTPUT
```

The package retains source snapshots, original invocations, full requests and
traces, test logs, hashes, and root confirmations. Existing paths are not reused.
