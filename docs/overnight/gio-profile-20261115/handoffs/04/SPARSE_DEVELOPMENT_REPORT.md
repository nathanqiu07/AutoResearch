# Sparse development screen: coverage, controls and replication allocation

The frozen 96-cell grid produced 48 usable profiles, 39 invalid builds, 7 empty builds and 2 unavailable builds. The 672 delivered predictions were all valid; 635 were correct. This is **635/1344 (47.25%) delivered-correct over all planned rows**, **672/1344 (50%) delivery coverage**, and **635/672 (94.49%) accuracy conditional on valid delivery**. Repeated predictions of the same small panel are not independent observations. These grid totals describe execution and must not be read as an average effect across a population of researchers or sources.

Simple matched controls were strong. No-profile and name-only each scored 26/28, while raw evidence at cap 2048 scored 28/28. Two selected cap 512 configurations also scored 28/28, compared with 25/28 for raw evidence, 26/28 for lexical retrieval and 27/28 for semantic retrieval at that cap. Selection occurred on these development outcomes, so this is a reason to replicate, not evidence of a confirmed advantage.

Both researchers have seven semantic judgments, each shown in two option orders. They come from only two Neel source groups and one Chris group. Group bootstrap intervals in the JSON are descriptive resamples of those observed groups (2,000 resamples, seed 0); Chris has no interval because it has one group. A degenerate interval such as [1,1] does not remove source or selection uncertainty. No human-population, source-population, general taste-fidelity, future-choice or downstream research-utility claim follows.

## Coverage across the full grid

Each family has 12 researcher cells and 168 planned ordered rows. All failures remain in these denominators. These are grid summaries, not family rankings.

| Family | Usable builds /12 | Delivered correct /168 | Valid rows /168 | Correct among valid |
|---|---:|---:|---:|---:|
| P1 | 7/12 | 91/168 | 98/168 | 91/98 |
| P2 | 6/12 | 81/168 | 84/168 | 81/84 |
| P3 | 4/12 | 54/168 | 56/168 | 54/56 |
| P4 | 6/12 | 81/168 | 84/168 | 81/84 |
| P5 | 7/12 | 88/168 | 98/168 | 88/98 |
| P6 | 4/12 | 53/168 | 56/168 | 53/56 |
| P7 | 7/12 | 93/168 | 98/168 | 93/98 |
| P8 | 7/12 | 94/168 | 98/168 | 94/98 |

Invalid builds comprise 27 cap violations, 9 missing source quotes, 2 malformed extraction JSON outputs and 1 invalid candidate-field output. Empty builds comprise 5 unsupported-comparison outputs and 2 unsupported-active-preference outputs. The two unavailable P8-cap 2048-explicit calls retain uncertain usage reservations; they were not retried or treated as free. Four P3/P5-cap 512 configurations stay in the grid denominator but were declared ineligible for same-cap replication because their required output schemas cannot fit.

## Matched controls and hybrids

Every row below delivered all 14 scheduled predictions per researcher. Correct counts are out of 14; order consistency is out of 7 semantic pairs and means the same semantic alternative was chosen after reversing its displayed position. All controls were rerun under the same frozen f6 consumer/settings; historical phase1 results are separate.

| Arm | Cap | Neel correct | Neel consistent pairs | Chris correct | Chris consistent pairs |
|---|---:|---:|---:|---:|---:|
| no_profile | 2048 | 12/14 | 7/7 | 14/14 | 7/7 |
| name_only | 2048 | 12/14 | 7/7 | 14/14 | 7/7 |
| raw_evidence | 512 | 12/14 | 5/7 | 13/14 | 6/7 |
| raw_evidence | 2048 | 14/14 | 7/7 | 14/14 | 7/7 |
| raw_evidence | 8192 | 13/14 | 6/7 | 14/14 | 7/7 |
| lexical_retrieval | 512 | 12/14 | 5/7 | 14/14 | 7/7 |
| lexical_retrieval | 2048 | 13/14 | 6/7 | 14/14 | 7/7 |
| lexical_retrieval | 8192 | 13/14 | 6/7 | 13/14 | 6/7 |
| semantic_retrieval | 512 | 13/14 | 6/7 | 14/14 | 7/7 |
| semantic_retrieval | 2048 | 14/14 | 7/7 | 12/14 | 5/7 |
| semantic_retrieval | 8192 | 14/14 | 7/7 | 11/14 | 4/7 |
| profile_retrieval | 2048 | 12/14 | 5/7 | 14/14 | 7/7 |
| profile_retrieval | 8192 | 14/14 | 7/7 | 11/14 | 4/7 |

Memory-summary comparisons reuse the fixed P1-cap 512-explicit parent: Neel 11/14 with 6/7 order-consistent pairs, Chris 14/14 with 7/7. Hybrids at 2048 and 8192 score 26/28 and 25/28 respectively, versus 25/28 for this parent. Their improvements and regressions differ by researcher. The cap 512 hybrid was structurally not dispatched because the fixed parent leaves no passage budget (28 planned rows outside the core 96 grid). The parent was neither regenerated nor shrunk.

Order sensitivity remains visible despite high conditional accuracy: 19 of 336 both-valid core semantic-pair instances changed the semantic choice on reversal. These are repeated instances across configurations, not 336 independent judgments. Chris semantic retrieval and the 8192 hybrid each changed choices in 3 of 7 pairs; their correct counts fell to 11/14. Larger context did not uniformly help. Brier scores and paired Brier differences are reported on valid probability rows only in the JSON, separately from failures.

## Frozen replication allocation

The pre-score policy ranks all configurations by delivered-correct count out of 28, then valid delivery count, then conservative known build-plus-prediction cost plus retained uncertain reservations, then ASCII config ID. One eligible configuration per family and two additional configurations were selected. These ten allocations request two more independent extraction replicates (40 researcher builds); this evidence receipt itself authorizes no calls. All three planned replicas and failures must be reported together, without selecting a lucky saved profile.

| Slot | Configuration | Correct /28 | Valid /28 | Conditional correct | Conservative cost USD |
|---|---|---:|---:|---:|---:|
| family/P1 | P1-c512-explicit-only | 25/28 | 28/28 | 25/28 | 0.004088625 |
| family/P2 | P2-c512-marked-inference | 28/28 | 28/28 | 28/28 | 0.003827625 |
| family/P3 | P3-c8192-explicit-only | 14/28 | 14/28 | 14/14 | 0.004490875 |
| family/P4 | P4-c512-explicit-only | 28/28 | 28/28 | 28/28 | 0.003776625 |
| family/P5 | P5-c2048-explicit-only | 26/28 | 28/28 | 26/28 | 0.007137375 |
| family/P6 | P6-c2048-marked-inference | 14/28 | 14/28 | 14/14 | 0.004402625 |
| family/P7 | P7-c8192-marked-inference | 27/28 | 28/28 | 27/28 | 0.00507725 |
| family/P8 | P8-c8192-explicit-only | 27/28 | 28/28 | 27/28 | 0.007420250 |
| global_extra/1 | P4-c512-marked-inference | 27/28 | 28/28 | 27/28 | 0.003705125 |
| global_extra/2 | P8-c8192-marked-inference | 27/28 | 28/28 | 27/28 | 0.00987725 |

**P3 and P6 have only 14/28 coverage**, despite 14/14 conditional accuracy. Their Neel builds failed with malformed extraction JSON and cap overflow respectively; only Chris delivered predictions. P7 uses explicitly approved peer fitting evidence in addition to target fitting evidence, so its information budget differs from the target-only methods. Sparse and richer corpus interventions remain separate.

The JSON contains 588 paired comparisons: each core cell against five matched controls and the memory alias, plus each hybrid against its parent, lexical retrieval and raw evidence. Each reports all-scheduled difference, joint-valid difference and denominator, group counts, Brier overlap and coverage. Order coupling is stored with the corresponding cell or arm. When a candidate build fails, its all-scheduled difference penalizes absence while its joint-valid comparison is null. This prevents conditional accuracy from hiding extraction failure.

## Cost and provenance

The sparse screen used 1132 model calls: 96 core builds, 672 core predictions, 308 control predictions and 56 hybrid predictions. Two embedding producer calls cost an additional $0.00007844, charged once. Known conservative usage across the screen is $0.266053750; retained uncertain reservations are $0.019078625; their sum is $0.285132375. Including embeddings gives 1134 calls, $0.266132190 known and $0.285210815 including holds. These are conservative accounting estimates, not invoices; historical phase1, neutral probes and other campaign work are excluded. The later continuation ledger has no in-flight calls or uncertain charges, but it does not erase the two earlier retained holds.

No-profile/name-only cap aliases add 112 comparison references to 56 canonical rows. Memory aliases add 84 references to 28 canonical rows. They add zero model calls and zero independent observations. Shared parent extraction and embedding production are each charged once. Per-researcher build and prediction costs are preserved separately.

All terminal packet/result hashes, releases, manifests, strict item/order bindings, source hashes, profile hashes, consumer payloads, backend settings, traces, dispatch receipts and alias proofs were checked before private target labels were opened. The complete public index binds 612 unique jobs (330 builds, 282 prediction jobs), 1036 actual prediction rows and all 96 original cells. It contains no source text, target text, private label, predicted choice or per-item correctness. The packaging pass reopened only public aggregates and label-free provenance. Backend identity fields named `label` are explicitly allowed only for the frozen backend name.

- `broad-sparse-development-score-v1.json`: aggregate cells, controls, hybrids, paired comparisons, costs and limitations.
- `development-replication-allocation-v1.json`: ten exact configurations and original researcher mappings.
- `full-sparse-completion-provenance-index-v1.json`: label-free audit index, immutable file references and hashes.
- `sparse-publication-verification-v1.json`: independent public-count/ranking/cost and privacy checks.
- `development-promotion-metric-policy-v1.json`: policy frozen before comparative scoring.

No final confirmation was used. No finalist or confirmed fidelity winner has been declared.
