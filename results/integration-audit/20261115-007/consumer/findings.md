# Independent consumer fixes retest

All three previously reported consumer failures are fixed for the exact synthetic cases retested. Six positive controls also pass. No failed retest claim remains; this does not establish complete system correctness or live experiment readiness.

New source: `05c503e5f6170a690a13feb75cbe2dc65d430ba8`; implementation: `5fc86572e7ab527a405146290834408dea5227da`.

Old evidence source: `d66051c6b792e2a9062f334535cf61ff9f51a15a`; implementation: `bb3a6f5cc370c1d3bf52361287cd3149bd294f7b`.

The current released fixture-v3 SHA256 is `cb6e8beecb6976e837be5d588471d0f5ac5c45cd4df02533b31bcabb640127e7`. All 154 files listed in AUDIT_SOURCE.json matched their pins before the retest and remained unchanged afterward. Old immutable evidence also remained byte-for-byte unchanged.

## Old versus new behavior

| Case | Old result | New result | Assessment |
| --- | --- | --- | --- |
| 545 rendered bytes, saved cap 1, coherent hashes | Successful prediction; one consumer call | Decoder rejects with `complete profile exceeds personalization cap`; consumer revalidation returns `ProfileFailure(invalid, invalid_serialized_profile)` with zero calls | Fixed for reproduced case |
| Explicit `invalid`, `unavailable`, `unsupported`, or `empty` response status plus valid probabilities | Successful prediction; failure status lost | `ProfileFailure` preserves the corresponding status and `consumer_<status>` code | Fixed for all four statuses |
| Same 400-digit integer probability | Raw `OverflowError` with no status/code | `ProfileFailure(invalid, invalid_probability_distribution)` | Fixed for byte-identical response |

The pre-existing `abstained` behavior still works. An unknown response status now produces `ProfileFailure(invalid, unknown_consumer_status)`.

Source mechanisms: `contracts.py:94-101` recomputes rendered size and rejects an over-cap complete artifact. `consumer.py:31-34` repeats artifact validation and converts its failure into the structured consumer error. `consumer.py:68-72` handles explicit response statuses, and `consumer.py:74-78` bounds numeric probabilities before calling `math.isfinite`.

## Probe adaptations and validity

The old 545-byte rich content was rebuilt with the current method and renderer pins. The loaded-cap variant changes both artifact and config cap fields to 1, then recomputes config/content/profile hashes. It preserves the true 545-byte rendered count. The decoder's intentional cap rejection is recorded as a result, rather than crashing setup.

To exercise `predict_profile`'s own revalidation, the same invalid serialized body was also wrapped through the dataclass constructor without its factory. The consumer then rejected it with a typed invalid status before any call. This establishes the consumer guard as well as the decoder guard; a setup exception alone was not counted as a fixed consumer boundary.

For empty-control canaries, both copies of `researcher_id` now change together and the config/profile hashes are recomputed. All three variants loaded successfully and each made one synthetic call. Their complete requests, including settings, were identical. This adapts the prior canary to the new consistency rules without removing the intended metadata variation.

The huge-integer response is reused byte for byte from old immutable evidence. The explicit-status responses use the same status, probabilities and synthetic rationale fields as before. Every old/new result pair is retained in the corresponding JSON file.

## Positive controls

- All rich JSON fields from the prior probe reach the consumer unchanged; the payload still contains only context, options and personalization.
- Empty controls remain request-invariant across personal metadata canaries and emit an empty personalization string.
- All noncomplete profile statuses stop before a consumer call.
- Build-time over-cap rejection remains intact.
- Declared learned weights/calibration remain rejected; successful predictions remain explicitly uncalibrated, including when the backend claims calibration.
- Legacy UserModel label, endpoint and class mismatch guards remain intact.

The independent script reports nine verified claims: three fixes and six controls. It reports zero failed claims. The relevant existing suite, `python3 -m unittest tests.test_overnight_contracts -v`, passes all 13 tests. This is targeted consumer verification, not a full repository or runner test run.

## Unverified and scope limits

No actual researcher corpus, labels, final data or live backend was used. Only the released synthetic fixture and generated variants were used, with recording transports. Real model calls: zero.

This retest does not assess live malformed-output frequency, preference fidelity, research utility, calibration quality, tokenizer-specific usage, frozen job-cap binding, or the full source/registry/runner/confirmation boundaries. Those remain separate review scope. No source snapshot, old reproducer, old result, owner module or model setting was changed.

## Reproduce and artifacts

Run the portable script with `--source-root <new-snapshot> --old-evidence <old-consumer-evidence-directory> --out <new-directory>`. It refuses an existing output directory. It contains no machine-specific path constants; original invocation paths are retained only as execution provenance.

- `retest.py`: new portable retest script; old reproducer remains unchanged.
- `invocation.json`, `stdout.txt`, `stderr.txt`: exact invocation and completion output.
- `consumer-tests.json`: exact relevant test command and complete output.
- `run-01/report.json`: explicit verified/failed/unverified claims, old/new commits, all source and old-evidence hashes, adaptations and limitations.
- `run-01/loaded-cap-old-new.json`: exact old/new cap results and current invalid artifact.
- `run-01/consumer-statuses-old-new.json`: paired explicit-status results.
- `run-01/huge-integer-old-new.json`: old and new result for the same malformed response.
- `run-01/rich-positive.json`, `empty-invariance.json`, `declared-profile-statuses.json`, `builder-cap-control.json`, `calibration-controls.json`, `legacy-backend-controls.json`: positive control records and actual requests where calls are expected.
