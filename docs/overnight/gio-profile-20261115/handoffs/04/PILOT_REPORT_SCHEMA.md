# Pilot score report schema v1

The report `pilot-score-v1.json` is aggregate development evidence only. The
opaque mapping `pilot-group-map-v1.json` contains item, semantic-target and source-
group identifiers without labels, source text, titles, URLs or per-item outcomes.
Its file SHA256 is `6d4bc7b02542671e8577854c0849d342c2f994f9afec26ec247229e4e5ca779f`.
The report SHA256 is
`259229944069c079da3a8e9bc8b845ffe2a76b3228032e6af0ac28e5f0898d56`.

`schema_version` is `researcher-profile-pilot-score-v1`. Top-level provenance pins
include `selection_sha256`, `completion_index_sha256`, `runtime_code_sha`,
`evaluator_code_commit` and `opaque_group_mapping_sha256`. `denominators` is keyed
by researcher and contains ordered-item, semantic-target and independent source-
group counts plus the exact selected-input hash. This pilot has 4 ordered items,
2 semantic targets and 1 source group per researcher.

Each `arms` entry is one researcher/method/tier with:

- `status`: `scored` or `unavailable_build`; `failure_reason` is null or a code.
- `n_items`, `n_semantic_targets`, `n_source_groups`, `n_correct`, `failures`,
  `missing_item_count` and `accuracy_all_scheduled`. Missing, invalid and failed
  outcomes count as wrong in this operational accuracy denominator.
- `valid_choice_accuracy`: correct / valid choices; null when there are none.
- `valid_choice_coverage` and `probability_coverage`: each uses all scheduled items.
- `brier_valid_only`: mean squared probability error across options, then across
  valid-probability items; lower is better. Null with zero probability coverage.
  For two options this is half the unnormalized two-class sum of squared errors.
- `order_coupling`: semantic pairs, pairs with both orders valid, pairs choosing the
  same semantic alternative in both orders, conditional consistency and pair
  coverage, plus counts with both/exactly one/neither order correct. Letter
  agreement is not semantic agreement after option reversal. Both-order-correct
  rate uses every scheduled semantic pair, including missing outcomes.
- `build_cost`, `prediction_cost`, `total_cost`: attempted calls, input/output
  tokens, cache hits and `estimated_api_usd`. These are conservative uncached
  list-price estimates from execution usage, not an invoice.
- `build_job_ids`, `prediction_job_ids`: exact completion-index identities.

`paired_comparisons` contains every method pair separately for each researcher.
`accuracy_difference_a_minus_b` uses the same scheduled ordered items. Brier
comparison uses only common valid-probability items and reports that count plus
both methods' full-denominator coverage. All `accuracy_ci95` are null because
there is only one source group per researcher. P1 comparisons are marked
`operational_missing_as_wrong`; other comparisons are `matched_valid_controls`.
No pooled independence claim follows from having two researchers.

P1's two builds returned `invalid_source_span`; no prediction job ran for P1.
Its zero all-scheduled accuracy reflects unavailable execution, not measured
preference errors from hypothetical predictions. `valid_choice_accuracy`, Brier
and conditional order consistency are null, with zero coverage. No fallback or
replacement profile was scored.

Thirty immutable build/predict packets, their preparation references, copied
release files, configurations, profile lineage, manifests, execution identity and
result bytes were checked before scoring. Thirty-two prediction rows were scored
against the exact private v2 panel and frozen selector. A separate direct label
comparison agreed with all control accuracy counts. Order-consistency aggregation
was checked with synthetic reversed-order fixtures before real scoring. Full
per-item reports and label provenance remain evaluator-private.

No finalist is selected. These are two semantic judgments per researcher drawn
from public, atemporal sources. Source memorization, generic wording cues and
single-reviewer label uncertainty remain. Downstream research utility and
confirmation performance are unmeasured.
