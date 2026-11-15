# Scaling driver drafts and grouped reporting, v2

This follow-up is offline. It adds a packet adapter and two reporting boundaries.
It grants no leases, allocates no money, runs no models, and selects no finalists.
The new human caps are $500 OpenAI and $500 OpenRouter total. Profile/scaling share
one centrally allocated $200 OpenAI lane; this is not Role09's own allowance.
The prior README and fixture remain historical, including their earlier budgets.

## Packet boundary

`compile_driver_packets(manifest, bindings, runtime=...,
expected_manifest_hash=..., expected_bindings_hash=..., expected_runtime_hash=...)`
returns `scaling-driver-drafts-v1`. Every input has an independently retained
freeze digest. The function consumes coordinator-supplied approved release and
profile bodies, validates their source/item/provenance hashes, and emits file
references instead of copying source or profile text into packets. It performs no
file reads/writes, network work, credential access, or budget reservation.

The input design is `overnight-scaling-design-v2`. It separates callable consumer
settings (`temperature`, `max_tokens`), callable extractor settings, and effective
backend settings such as medium reasoning and temperature `not_sent`. V2 pins one
full `documents_hash` for every core cell, including attribution/permitted-span
metadata. D pins its separate full document hash, raw control policy hash and raw
baseline implementation hash. Byte caps remain conservative UTF-8 bounds.

Bindings cover every unique cell, with either `unavailable` plus a reason or:

- `release_ref: {path, sha256}` and the corresponding approved `release` body;
- explicit `jobs`, each with an ordered `item_ids` subset, `profile_ref`, exact
  neutral `profile`, original extraction `origin_job_id`, supported registration,
  and requested call/time/USD/timeout `limits`.

Job subsets must partition the complete frozen ordered item schedule exactly
once. This supports a decision-specific retrieval profile per ordered item.
Controls pin a policy hash of all build-config fields except source/runtime fields
that are checked separately and the exact decision/consumer binding. Policy
includes method, cap, top-k, chunk settings, embeddings and any other method
choices. Retrieval profiles must match the exact decision and consumer identity.
Raw passages must match approved source bytes and sit within explicitly permitted
attributed spans; missing spans do not trigger full-document fallback. This is a
rejection check, not a new retrieval implementation. Existing owners retain
baseline fixes and actual conditioning audits.

D can compile through the existing `raw_evidence` builder/consumer path. Its raw
content must be identical across levels and contain only approved passages. No
candidate-derived summary or extra annotation is accepted as raw evidence.
No-profile artifacts must be intentionally empty. All profiles must retain their
original exact runtime SHA and full source records; older profiles are never
relabeled for a new runtime.

Each output packet has the current `overnight-packet-v1` shape. `lease` and
`manifest.allocation.authorization_source` are null, and `job_id` is absent.
Only the coordinator fills real authority fields and asks the driver to derive
and prepare the final job. Requested ceilings are estimates, not spending or
permission. Existing profile dependencies and A/B/C cell aliases are reused;
there are no new extraction requests. CLI needs a separate supported driver.
Utility cells are returned as explicit downstream-owner handoff records, with
frozen hashes/settings and no substitute loop or scorer.

Runtime code/driver/runner/backend hashes are parameters. The synthetic driver
preparation test uses checkpoint `79874f7024d7ef6af72aae20aca8b1e82fa545e0`.
The six dependency merge conflicts were resolved byte-for-byte from this pin in
merge `7d7c42e`; Role09 code was preserved. The later live pin `0dcd4b43...` and
forthcoming quote/span fixes are not retrofitted into old fixtures. New extraction
instances under a common runtime are needed before the actual scaling freeze.

## Grouped scored-row boundary

`grouped_paired_report(mapping, jobs, score_packets, comparisons, rule=...,
expected_mapping_hash=..., expected_jobs_hash=..., expected_scores_hash=...,
expected_analysis_hash=...)` consumes evaluator-issued rows, never labels.

The synthetic `scaling-evaluator-map-v1` maps exact scheduled item IDs to opaque
semantic-item/source-group IDs, researcher, tier and schedule hash. Jobs pin their
own subset target-bundle hash, common parent bundle hash, job/manifest identity
and exact item subset. Thus genuine subset `score_predictions` reports can be
joined without rewriting hashes. Each score packet supplies that report plus
raw prediction statuses so empty/missing/invalid outcomes remain visible.

Existing evaluator semantics are preserved: failed/missing predictions already
scored by the evaluator are false/zero; a missing whole score report is unmeasured.
All option orders of one semantic judgment collapse to mean correctness. Judgments
then receive equal weight. No integer conversion discards a half-correct judgment.
Brier remains valid-probability-only with explicit coverage.

Comparisons stay within researcher and evidence tier. The frozen rule specifies
`source-group-bootstrap-v1`, seed, sample count, 95% percentile interval, minimum
at least two groups, `source_group` resampling and `equal-semantic-item-mean`.
The bootstrap draws whole source groups, keeping all their judgments together.
One group or incomplete paired score coverage yields no interval. Even two groups
provide descriptive evidence, not precise confirmation; no researcher population
interval is produced from two cases. Utility requires the downstream metric and
failure-policy contract and cannot enter the fidelity schema.

## Released pilot schema

`group_released_pilot(mapping_bytes, report_bytes, expected_mapping_sha256=...,
expected_report_sha256=...)` directly validates evaluator04's published
`pilot-opaque-group-map-v1` and `researcher-profile-pilot-score-v1` schemas at
checkpoint `db067614d58a81cb1965ed98de531d6b8d5ab634`. Only the explicitly released
opaque map and safe aggregate were read; private targets, per-item outcomes and
raw predictions were not opened.

The released pilot has four ordered inputs, two semantic targets and one source
group per researcher. Balanced option reversals make operational ordered accuracy
equal to the semantic-target mean; all 20 method pairs remain present. Every
interval stays null. Unavailable P1 builds retain unavailable status, zero valid
coverage and null valid-choice accuracy; their operational zero is not a measured
prediction error. The adapter does not infer private group-level outcomes from
aggregate totals. For multiple source groups, detailed grouped scoring stays with
the evaluator and the scored-row boundary above.
