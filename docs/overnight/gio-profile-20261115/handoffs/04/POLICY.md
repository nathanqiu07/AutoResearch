# Researcher-profile evaluation policy v1

Campaign: `gio-profile-20261115`. Frozen before candidate scores. Contract:
`0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43`.

## Intake and custody

Collectors submit observed bytes and metadata only to the evaluator's assigned
external store, outside Git and worker checkouts. Directories are 0700 and files
0600. All agents share an OS account: this is procedural isolation, not a sandbox.
Builders must not inspect the store. Its location is supplied at dispatch.

Required document fields: opaque document_id, researcher_id, canonical_url,
observed_content_sha256 (raw bytes), content_sha256 (exact delivered UTF-8 content),
content, author/contribution, published_at, updated_at, retrieved_at,
version_evidence, document_group, project_group, duplicate_group, evidence_type,
permitted_spans, split_eligibility. Additional source links identify crossposts,
revisions and near-duplicates. Collector normalization is versioned and happens
once. Missing version evidence, partial fetches or unclear attribution are
quarantined. Publication/retrieval dates alone cannot prove temporal eligibility.

## Sources and targets

Union document/revision/project/crosspost/duplicate links before assigning splits.
A connected source group belongs wholly to fit, dev or confirmation. No sentence
split. Assignments are frozen before candidate scores; a newly found crossing
invalidates the affected split instead of silently moving evidence.

Tier A: explicit stated comparison. Tier B: observed choice with documented known
alternatives and constraints. Score tiers separately. Tier C: model-inferred label,
excluded from archival fidelity. Unordered recommendations, mentions, coauthorship,
absence of discussion and generated rejected alternatives do not establish a
preference. Another model's agreement is QA, not truth.

The evaluator freezes target context, alternatives, label, source span, attributable
speaker and canonical identities before viewing model predictions. Answer-known
scaling items follow this source rule, not tested-model performance. Entire
answer-bearing groups are withheld from fitting. Name-only controls probe possible
famous-author training contamination; they cannot remove that limitation.

Builders receive allowlisted fit documents only. The source manifest is sorted
`{document_id,content_sha256}` entries, binding the exact set and text. Duplicate
IDs and extra sources fail. Hidden titles, URLs, spans, labels and summaries never
enter shared bundles or Git. Public target metadata exposes opaque IDs/counts/hashes
only. Prediction input keys are exactly item_id, researcher_id, context, options,
option_order_id. Item IDs and option schedules are matched across methods/models.

## Measurement and feasibility

Before scoring, report per-researcher, tier and independent-group counts. No valid
labels or no defensible holdout means fidelity is unmeasured. Sparse evidence
supports descriptive pilots only; counts alone do not justify confirmation claims.
Accuracy counts missing, failed, invalid and abstained predictions as wrong.
Probability metrics report valid coverage. Paired comparisons use the full matched
item schedule and group-resampled uncertainty; one source group yields no interval.
Replicates do not create independent groups. PRISM stays a separate lane. Utility
remains unmeasured until existing downstream owners provide matched valid evidence.

## Confirmation

No final run is authorized. One frozen core-plus-scaling batch specifies all arms,
jobs, target identities, settings, metrics and retries. A central SQLite transaction
reserves underlying target/source-group identities before exposure; manifest/split
hashes are metadata, never a fresh eligibility key. Reservations survive failure.
Changed manifests/clones cannot repeat consumed identities through this protocol.
Existing final markers remain intact. Only the evaluator holds confirmation inputs,
predictions, traces and caches. Shared handoffs expose status, hashes and authorized
aggregate metrics. Shared-account actors can bypass cooperative code; this is an
explicit enforcement limit, not a claim of hostile-agent containment.

## Implementation ledger

- Policy frozen before candidate scores; no researcher or final labels inspected.
- Ruling: additive evaluator module only. Existing public-track generated distractors
  and score-driven target revisions do not satisfy this campaign's label rule.
- Pending: grouped release, source eligibility, scoring and custody checks.
