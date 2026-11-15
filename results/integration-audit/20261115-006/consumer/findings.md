# Independent consumer audit of CONTRACT_READY d660

Source snapshot: `d66051c6b792e2a9062f334535cf61ff9f51a15a`; implementation: `bb3a6f5cc370c1d3bf52361287cd3149bd294f7b`. Shared contract hash: `0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43` (independently checked).

Scope: `consumer.py`, consumer-facing `build_profile` behavior, the released synthetic fixture and generated synthetic variants. No actual researcher source, labels, final data, network calls, or production edits. Source-manifest and implementation-pin enforcement have a separate reviewer. This report does not claim that audit fixtures are observed live failures.

## Verified issues

### P2: Loaded profile caps are not enforced at the consumer boundary

`autoresearch/taste/overnight/consumer.py:31-49` reconstructs a ProfileArtifact and checks its status and implementation metadata, but never compares the actual rendered byte count with `personalization_cap`. The artifact decoder checks integrity hashes, not this semantic invariant.

Reproduction: take a generated synthetic complete profile, set both saved cap fields to 1, recompute `config_id`, `content_sha256` and `profile_id`, then load it through `ProfileArtifact.from_dict`. `predict_profile` sends the full rich content and returns a prediction. The request is far larger than the declared cap. Exact profile and request: `run-01/loaded-cap-bypass.json`.

The normal `build_profile(..., personalization_cap=1)` path correctly marks the same content invalid and makes zero consumer calls; see `run-01/builder-cap-enforcement.json`. Thus this is a missing semantic check on loaded artifacts, **not** proof that normal building emits over-cap complete artifacts or that a hash-tampered artifact passes. Recompute rendered size and reject inconsistent count/cap/status metadata before a consumer call. The assigned runner should also bind the profile cap to the frozen job's cap.

### P2: Explicit failed consumer statuses can become successful predictions

`autoresearch/taste/overnight/consumer.py:65-76` honors `status="abstained"` but ignores other status values. A response such as `{"status":"invalid","probabilities":[0.25,0.75]}` returns a normal Prediction. Generated variants with `unavailable`, `unsupported` and `empty` do likewise. `abstained` correctly raises ProfileFailure.

The shared contract requires separate invalid/abstained/unavailable outcomes, and says failures must not be replaced by a successful baseline under a candidate name. A failed response that happens to carry fallback probabilities loses its failure status here. Reject non-success statuses explicitly (or define and enforce that any status other than the supported success/abstention values is invalid). Exact traces: `run-01/explicit-consumer-failure-statuses.json`.

The prediction prompt currently requests probabilities and rationale without a status schema; this probe establishes handling of a possible returned object, not its live frequency. Noncomplete **profile artifact** statuses already fail correctly before a backend call.

### P3: A malformed numeric distribution escapes the structured failure API

`autoresearch/taste/overnight/consumer.py:69-70` applies `math.isfinite` to arbitrary JSON integers before bounding them. A 400-digit integer is valid JSON, but converting it for `math.isfinite` raises OverflowError. The error escapes `parse_prediction` and `predict_profile`, so callers receive neither the documented ProfileFailure nor an invalid status/code.

Exact synthetic response and exception: `run-01/oversized-integer-response.json`. Range-check integers before float conversion, or convert this numeric overflow into `ProfileFailure("invalid", "invalid_probability_distribution")`. This is a robustness issue on malformed outputs; no valid probability is affected.

## Verified behavior that should be preserved

- Rich content reaches the actual recording consumer as canonical JSON without dropping prose, atomic claims/provenance, conditions, examples, nested hierarchy, contrasts, dated hypotheses, unknown extra fields, empty/dotted keys, nulls, booleans or numbers. The payload has exactly context/options/personalization.
- Normal intentional-empty controls emit an empty personalization string. Complete recorded requests, including settings, are identical across three generated variants with different researcher/extractor/replicate metadata and nested personal canaries. This confirms metadata exclusion for the tested empty-control path; it does not establish invariance under an incorrectly populated control builder.
- Every declared noncomplete profile status tested (empty, unsupported, invalid, unavailable, abstained) fails before the backend call. Normal build-time cap enforcement works.
- Declared learned weights and calibration in builder output are rejected before consumption. Consumer output remains `calibrated=false`, even if the synthetic backend claims calibration.
- Existing legacy UserModel label, endpoint and class mismatches still fail before prediction. The neutral format does not remove those backend-bound guards.

These are plumbing checks only. They do not establish preference fidelity, scientific utility, live backend compatibility or calibration quality.

## Evidence and reproduction

Run `reproduce.py --source-root <snapshot> --out <new-directory>`. The script has no machine-specific paths, reads the snapshot's released synthetic fixture, and generates only synthetic variants. Output creation is exclusive.

- `invocation.json`, `stdout.txt`, `stderr.txt`: exact probe command and result. Exit 0 means the assertions reproduced the listed behavior, **not** that all consumer safeguards passed.
- `existing-tests.json`: the seven existing contract tests pass.
- `shared-contract-ref.json`: independently checked shared-contract hash and original location.
- `run-01/report.json`: source pins/hashes, script hash, scope, checked behavior and limits. Relevant source files remained unchanged.
- `run-01/rich-profile.json`, `rich-request.json`: full rich-content construction and actual request.
- `run-01/no-profile-request-invariance.json`: complete empty-control request variants.
- `run-01/declared-profile-failures.json`, `builder-cap-enforcement.json`: working failure guards.
- `run-01/loaded-cap-bypass.json`, `explicit-consumer-failure-statuses.json`, `oversized-integer-response.json`: decisive failure reproductions.
- `run-01/calibration-separation.json`, `legacy-backend-guards.json`, `synthetic-legacy-m0.json`: calibration and legacy guard controls.

Only local recording transports were used. No change was made to the supplied snapshot or production code. Findings are for the shared infrastructure owner; this audit does not edit another owner's module or authorize live integration.
