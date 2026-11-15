# Phase 1 five-control report

`phase1-score-v1.json` uses `researcher-profile-phase1-score-v1`. It keeps the
four-control scores and original comparisons unchanged from
`control-v2-score-v1.json`, then adds only the semantic-retrieval arm and its
matched comparisons. No earlier model calls or label scoring were repeated.
Metric definitions and small-group limitations remain as documented in the
pilot/full-v2 report schema files.

The semantic arm adds 28 predictions and two one-time embedding production
requests. Each researcher has one producer receipt reused by 14 derived profiles.
`embedding_cost` is separate from `build_cost` and `prediction_cost`; `total_cost`
includes it once. Top-level `embedding_costs`, `embedding_calls` and
`semantic_incremental_cost` preserve this accounting. Phase 1 totals 140
prediction calls, 2 failed P1 extraction calls and 2 embedding calls. P1 remains
an unavailable prior pilot arm, separate from full-panel controls.

The field `usage.decision_item_sha256` in the supplied embedding artifacts is a
legacy name for the hash of `[item_id, option_order_id]`, not a hash of the entire
strict item. All 28 identity-pair hashes were verified. The actual producer query
strings, their canonical hashes, selected chunk hashes and exact response-vector
indices were also verified against the immutable production receipts. Original
artifacts were preserved unchanged. Consumer identity, settings, neutral prompt
version, cap, runtime and replicate match the frozen original controls.

Costs are execution-receipt list-price estimates and carry
`cost_reconciliation_status`; coordinator pricing reconciliation may supersede
those estimates without changing predictions or scores. No invoice claim is
made. Source-group bootstrap intervals remain descriptive, and one source group
still provides no interval. No finalist, general researcher ranking, confirmation
result or downstream utility claim follows.
