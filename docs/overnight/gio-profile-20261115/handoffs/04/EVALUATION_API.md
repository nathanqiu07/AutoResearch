# Evaluator handoff v1

Code: `28a81c6d66fa9e26e6c72ba88806b895c7c49847`.
Only `autoresearch/taste/overnight/evaluation.py` and its scoped test file are code
changes. The policy in this directory remains frozen before candidate results.

## Source and target admission

`review_document(record)` requires captured content hashes, complete fetch,
explicit evaluator-approved atemporal/temporal disposition, reviewed grouping,
attribution basis and exact attributed content spans. Historical claims additionally
require verified version eligibility. `group_documents` unions canonical URL,
content, document/project/duplicate links and five-word-shingle overlap >=0.8.
This lexical check cannot prove absence of semantic or unrecorded derivative leaks;
manual review is required and recorded. Unknown external group links fail closed.

`freeze_split(documents, assignments)` pins full source-record provenance and rejects
connected groups crossing fit/dev/confirmation/quarantine. `approved_bundle` releases
only explicit fit fields and strips response headers from version provenance.
No URL fetch or automatic expansion occurs. Approved source hashes must be used as
an exact allowlist by the infrastructure builder.

`prepare_target_bundle(targets, documents, split_manifest, stage='dev')` is evaluator
only. It checks accepted source evidence, exact spans, attributed speaker, source
alternatives, target/group/source stage and frozen provenance. It produces an
immutable-by-hash private label bundle and the exact label-free item schedule.
Only `prediction_input(target)` is supplied to consumers.

## Scoring an assigned job

The coordinator supplies an immutable result path, job ID and semantic manifest
hash. Only the evaluator opens the private validated target bundle:

```python
score_predictions(
    private_bundle,
    prediction_rows,
    expected_target_bundle_sha256=frozen_target_hash,
    expected_job_id=leased_job_id,
    expected_manifest_sha256=semantic_manifest_hash,
)
```

Every row must bind item_sha256, items_sha256, job_id and manifest_sha256 to that
job and the frozen ordered inputs. A different order/settings job cannot be scored
by matching only item_id. Missing, malformed and mismatched rows count as failures.
Unexpected or duplicate item IDs reject the packet. Accuracy uses every scheduled
ordered item; Brier is mean squared probability error across options, valid-only,
and always reported with coverage. Tier A/B and researchers are separated.

Current dev has 4 semantic judgments per researcher, each shown in both orders:
8 ordered inputs each, 16 total, but only 2 independent source groups total.
Ordered-item accuracy does not turn the two orders into independent observations.
Group bootstrap intervals are unavailable for a single source group. Dev selection
and any scaling comparison are descriptive. No winning/general researcher claim
follows. Utility is separate and currently unmeasured.

`paired_comparison` requires the full same frozen item schedule. `feasibility_report`
checks fit/dev availability per researcher, separately from confirmation availability.

## Confirmation custody (not authorized)

`initialize_store` establishes one external SQLite store. `reserve_confirmation`
requires authorization tied to the exact frozen batch; one atomic transaction
reserves canonical dataset + underlying target/source-group/user identities.
Manifest or split changes do not create fresh eligibility. Failures keep consumed
identities reserved. Runtime code must validate the authoritative receipt before
exposure:

```python
validate_confirmation_receipt(
    store_root, receipt, job_id=job_id,
    manifest_sha256=confirmation_batch_hash,
    private_root=private_root, expected_store_id=pinned_store_id,
)
```

A caller-supplied string is not independent evidence of human authorization. The
coordinator/evaluator must establish authorization and the authoritative store
before calling this API. Shared-account participants can bypass cooperative code;
this is not a hostile-agent containment system. Existing final-use guards remain.
No real confirmation ledger or final batch has been consumed by this campaign.
