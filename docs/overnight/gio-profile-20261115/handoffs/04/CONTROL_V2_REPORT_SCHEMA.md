# Full v2 control report

`control-v2-score-v1.json` uses `researcher-profile-control-v2-score-v1` and the
metric definitions in `PILOT_REPORT_SCHEMA.md`. The full frozen panel contains
14 ordered items (7 coupled semantic comparisons) per researcher. Neel has two
source groups; Chris has one. All four controls cover every item once, combining
original pilot and continuation jobs without changing their manifests or rows.
The original pilot report remains unchanged.

The full report adds `accuracy_descriptive_group_bootstrap_ci95` per arm and the
observed source-group accuracy range. Bootstrap intervals use 2,000 draws with
seed 0, resampling source groups. They describe only the observed source groups;
two groups cannot establish generalization to unseen material. A single group
has no interval. Paired comparisons use the same full ordered schedule; neither
option reversals nor repeated methods create independent source groups.

P1 is absent from the full-panel arms and comparisons because no such prediction
run was scheduled. `prior_pilot_unavailable_arms` preserves its original pilot
counts and zero coverage. `control_cost` covers the 112 control calls;
`prior_failed_profile_cost` covers the two failed P1 extraction calls. Their sum
is `total_cost`. No failed arm is replaced or silently omitted from its original
planned pilot denominator.

Verification covered 76 pinned packets (36 builds, 40 prediction jobs), their
immutable prepared plans, releases, configurations, execution bindings, profile
lineage and result bytes. Exactly 112 unique researcher/method/item outcomes were
scored. Independent direct accuracy and Brier calculations agreed for all eight
researcher/control arms. Aggregate input order is checked separately from each
job's original subset order. The evaluator module passed 36 targeted tests and
the full 692-test suite (2 skipped) before scoring.

The results do not establish a benefit from profiling. The no-profile control is
strong on this small public-source panel; raw evidence has substantial order
sensitivity. No finalist is selected, and downstream utility remains unmeasured.
Opaque group mapping and aggregate scores contain no private labels, source text,
URLs or per-item outcomes.
