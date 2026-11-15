# Independent synthetic semantic-retrieval audit

The new release implements semantic vector-bundle reuse and its decision adapter. Seven audited claims passed; one numerical edge case failed. All 22 existing retrieval/baseline tests pass. No live embedding producer, model quality, actual cost, or runner dispatch is established by this audit.

## Exact release pins

| Release | Source archived | Implementation | Files |
| --- | --- | --- | --- |
| New semantic handoff | `0ca54b470947fcf453c577b14f6b12c7e2a267b0` | `8f91bde9c96c109fb43a9cb4ce0e3ca205f126af` | 145 |
| Prior implementation | `8a310d50a211d5e77194e77fc06babc0b760816e` | same commit | 141 |

Each release has its own git archive and read-only extracted snapshot under `snapshots/new` or `snapshots/old`. Its `AUDIT_SOURCE.json` records exact archive arguments, archive SHA256, code pins and every archived file hash. Both snapshots remained unchanged. The current fixture SHA256 was verified as `aa6e17c2e91e5eab6ffd4fc233159de1ffdf535b060470adec6d932bd0f26fe5`.

The old code reports semantic retrieval unavailable even when supplied the new artificial bundle. The new code builds a complete semantic profile whose content matches the released fixture exactly. The retrieval helper change changes all seven method policy hashes; `release-comparison.json` retains old and new values separately. This is not a migration of existing artifacts or confirmation of compatibility with newer shared-infrastructure snapshots.

## P3: Subnormal vectors can break cosine ranking

`autoresearch/taste/overnight/retrieval.py:160-163` divides coordinates by `math.hypot` directly. For the smallest positive IEEE-754 subnormal `t = 5e-324`, `hypot(t, t)` rounds to `t`. The accepted vector `[t, t]` is normalized to `[1, 1]`, whose norm is approximately 1.414 rather than 1.

The exact synthetic reproduction uses query `[1, 0]`, passage `fit-a` vector `[t, t]`, and passage `fit-b` vector `[1, 0]`. Both computed dot scores become 1, so the document-ID tie rule ranks `fit-a` first. Replacing only `[t, t]` with the same direction at normal scale `[1, 1]` ranks `fit-b` first, as cosine similarity requires. Both bundles are accepted and both resulting profiles are marked complete; this changes the packed source order.

`run-new/subnormal-scaling-failure.json` retains both bundles, normalized vectors, norms, scores, rankings and builder statuses. This is a verified numerical robustness defect for pathological finite coordinates, **not** evidence that an embedding provider emits such values or that an actual study has misranked documents.

Normalize after dividing coordinates by their maximum absolute magnitude, or explicitly reject numerically degenerate magnitudes before declaring the bundle usable. Add a scaling-invariance regression using the reproduced pair. Existing checks already reject zero vectors, nonfinite coordinates, booleans, count/dimension errors, huge integers, and overflowing norms.

## Verified boundaries

- Exact approved source set/content, chunk width and ordered chunk/input hashes, decision context and option order, model string, dimensions, retrieval implementation/policy, bundle content hash and expected bundle hash are checked. The independent probe rejects 15 targeted mismatches, including rehashed request tampering.
- The embedding input list is canonical decision JSON first, then exact ordered source chunk text. Consumer personalization contains selected original passages with document IDs and character offsets; vectors and producer/config metadata do not enter the payload.
- Complete profiles fit the declared UTF-8 byte cap and preserve exact source slices across tested caps from 0 to 512. Infeasible caps do not silently become a complete no-profile control. Byte bounds do not establish equal tokenizer usage.
- `baselines.py:123-129` includes `semantic_retrieval` in `predict_baseline`'s exact decision binding. Changed context or option order is rejected before a consumer call; the matching case reaches the recording consumer. This verifies the adapter only. Actual shared runner routing remains pending owner integration and was not inferred.
- Repeated semantic builds make zero extractor calls and record incremental reuse as zero calls with `cost_status=no_model_calls`. `fit_usage.embedding_production_usage` separately preserves the supplied producer usage. The coordinator must account for the producer job once; actual accounting was not executed here.
- Live-shaped bundles missing producer job ID or a valid response hash are unavailable. A syntactically valid **synthetic** job ID and response hash can pass schema checks, as documented. This is not provider authentication, proof of common model/settings across vectors, or evidence of actual production cost.

The fake producer metadata in the usage probe is explicitly marked `SYNTHETIC_NOT_A_REAL_PRODUCER_JOB` and `SYNTHETIC_DECLARATION_ONLY`. Its declared usage values are never reported as observed usage. The planned live producer's absence is not counted as a bug.

## Evidence and reproduction

`probe.py` is portable: provide `--source-root`, `--fixture` and a fresh `--out`; add `--old-release` for the separately pinned prior code. The script contains no machine-specific path constants. Its hash matches both result reports. Exit 0 means the audit completed and wrote evidence; consult `claims_failed` for the reproduced defect.

- `invocation-new.json`, `invocation-old.json`: exact commands, exit codes, stdout and stderr.
- `targeted-tests.json`: all 22 retrieval/baseline tests pass; no full repository suite was rerun.
- `run-new/report.json`: explicit verified, failed and unverified claims, source/file hashes and scope.
- `run-old/report.json`, `release-comparison.json`: separate prior behavior and policy pins.
- `run-new/positive.json`: released synthetic documents, exact ordered inputs, ranking and profile.
- `run-new/binding-rejections.json`, `invalid-vector-rejections.json`: tested rejection cases.
- `run-new/subnormal-scaling-failure.json`: decisive numerical reproduction.
- `run-new/cap-and-source-preservation.json`, `semantic-adapter.json`: exact span/cap and adapter evidence.
- `run-new/reuse-and-producer-usage.json`, `producer-provenance-schema-rejections.json`: zero-call reuse and declared producer metadata checks.

No real source data, labels, final records, keys or API endpoints were accessed. Only released synthetic fixtures, invented variants, source files and git metadata were read. No owner source, snapshot, model setting or old evidence was changed. No paid or real-model call occurred.
