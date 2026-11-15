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

The active v2 release has 7 semantic judgments per researcher, each shown in both
orders: 14 ordered inputs each, 28 total, but only 3 independent source groups
total (Neel 2, Chris 1). The frozen pilot selects 2 semantic judgments per
researcher, each in both orders. This subset remains descriptive.
Ordered-item accuracy does not turn the two orders into independent observations.
Group bootstrap intervals are unavailable for a single source group. Dev selection
and any scaling comparison are descriptive. No winning/general researcher claim
follows. Utility is separate and currently unmeasured.

`paired_comparison` requires the full same frozen item schedule. `feasibility_report`
checks fit/dev availability per researcher, separately from confirmation availability.

## Scoring a frozen subset across jobs

`score_predictions` remains the strict full-panel API. For the pilot or lexical
retrieval's per-item jobs, call the evaluator-only wrapper once per researcher
and method arm:

```python
score_manifest_jobs(
    private_bundle,
    [{"manifest": manifest, "items": exact_job_inputs,
      "predictions": original_prediction_rows}, ...],
    expected_target_bundle_sha256=active_release_target_hash,
    expected_source_manifest_hash=active_release_fit_manifest_hash,
    expected_items_sha256=frozen_selected_ordered_inputs_hash,
    expected_manifest_hashes={job_id: full_manifest_hash, ...},
    expected_item_ids=frozen_ordered_item_ids,  # optional for interleaved jobs
)
```

The expected job hashes must come from the immutable coordinator job plan,
independently of prediction rows. The expected selected-input hash comes from the
frozen selector and exact active release items. Do not derive it from whichever
results happened to finish. Each packet's items must remain in its original job
order. For interleaved subsets (such as pilot plus continuation), supply
`expected_item_ids` in the frozen panel order. Their set must exactly match all
scheduled job items, without duplicates, and the reassembled input hash must equal
`expected_items_sha256`. Only aggregate outcomes are ordered this way; original
job manifests and rows remain unchanged. Without this optional argument, packet
concatenation must reproduce the frozen selection order. The wrapper rejects omitted planned job
packets, repeated jobs/items/rows, altered inputs (including extra fields), changed
option order, wrong source/stage, mixed arms, and row/manifest mismatches. All
subsets must exactly match the pinned private panel, whose hash also binds its
source split and reviewed provenance. Different profile hashes are allowed across
per-item retrieval jobs; common method/backend/code/contract/cap/replicate fields
must agree. The coordinator's exact manifest pins bind remaining settings.

If a planned job has no result, include its manifest and inputs with
`predictions=[]`; its scheduled items count as failures. Unsupported or malformed
predictions also remain failures. The wrapper uses private derived subset views to
reuse full-panel scoring. It does not rewrite original rows or manifests. The
report retains the original parent target hash, fit-source hash, selected-input
hash, complete job manifests, and each outcome's original job/manifest/subset
hashes. `per_item` is evaluator-private; share aggregate metrics only.

The wrapper verifies evidence bindings; it does not grant execution or confirmation
authorization. The active pilot uses development data only. No confirmation run is
authorized.

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
