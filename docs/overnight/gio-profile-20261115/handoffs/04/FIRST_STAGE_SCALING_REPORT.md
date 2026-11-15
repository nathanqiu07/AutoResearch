# Larger consumers hit the generic accuracy ceiling

**Sol and Astra each scored 28/28 in every arm, including no profile.** All 280 new predictions were valid. P8 therefore had zero accuracy advantage over the same-model generic control on this panel. The result shows improved agreement with the source-backed choices relative to the historical Luna runs, but it does not establish that a personal profile supplied the improvement.

| Arm, fixed at logical cap 8,192 | Luna, historical | Sol, new | Astra, new |
|---|---:|---:|---:|
| Saved P8 profile | 27/28 | 28/28 | 28/28 |
| No profile | 26/28 | 28/28 | 28/28 |
| Raw evidence | 27/28 | 28/28 | 28/28 |
| Lexical retrieval | 26/28 | 28/28 | 28/28 |
| Semantic retrieval | 25/28 | 28/28 | 28/28 |

Every researcher/arm/model cell has 14/14 valid predictions. Sol and Astra are correct on all 14 for each researcher. Planned-denominator and conditional accuracy coincide in this stage because no row is missing or invalid; that does not erase failures from the earlier extraction search or richer-source study.

## What this comparison tests

This stage freezes the original sparse corpus and the selected `P8-c8192-explicit-only`, replicate-0 profiles. The same saved profiles and ordered decisions are consumed by Luna, Sol, and Astra. It evaluates consumer scaling, not profile re-extraction with larger models. The selection was made using development results, so these are exploratory follow-up comparisons.

The panel contains seven underlying judgments per researcher, each presented in both option orders: 28 ordered items, with two Neel source groups and one Chris group. Across five arms and three consumers, the bookkeeping denominator is 420 logical rows. Those rows are not 420 independent human judgments. No new targets, source families, winning method, or final-test claim is introduced.

## Probability scores

Brier scores below use the existing binary mean-squared-probability-error definition; lower is better. All rows have valid probabilities, so the comparisons share the same item sets.

| Arm | Luna | Sol | Astra |
|---|---:|---:|---:|
| Saved P8 | 0.04205 | 0.00229 | 0.00679 |
| No profile | 0.06651 | 0.00779 | 0.01131 |
| Raw evidence | 0.04101 | 0.00123 | 0.00361 |
| Lexical retrieval | 0.06227 | 0.00150 | 0.00306 |
| Semantic retrieval | 0.09882 | 0.00131 | 0.00431 |

P8 has lower Brier loss than no profile for both larger consumers, but raw evidence has lower loss than P8. Astra has the same perfect accuracy as Sol and higher Brier loss in all five arms on this small panel. These differences describe reported probabilities on repeated, selected development choices; they do not establish reliable calibration, research utility, or a general model ordering.

The generic control reaches 28/28 with both larger consumers. This stronger ceiling makes the panel unable to distinguish personalization methods by accuracy in this stage. More perfect scores cannot resolve that limitation.

## Orders, repeated requests, and aliases

Sol and Astra make the same semantic choice across all 14 reversal pairs in every arm, and both orders are correct. Historical Luna consistency was 13/14 for P8, 14/14 for no profile, 13/14 for raw, 12/14 for lexical, and 11/14 for semantic. A consistent choice can still be wrong: Luna's no-profile arm contains one pair wrong in both orders.

The 280 new draws have **278 distinct model-inclusive request-body identities**. For one Neel ordered item per new model, lexical and semantic retrieval produced the same request input under different native cache keys. Both draws were retained, and the first lexical result was complete before the semantic block could run. Both pairs chose the same option; their probability vectors differed by up to 0.03 for Sol and 0.01 for Astra. These are repeated consumption of the same input, not two independent tests of different retrieval content.

The 140 Luna rows are aliases of 62 known historical jobs. They add no calls, cost, or independent observations. Saved-small-profile/consumer-Astra rows can also supply the declared StudyC cell, and StudyD references the same raw-control rows; those uses do not add observations. Existing embedding production remains charged once.

The earlier sparse retrieval diagnostic changed semantic context in 4/14 reversal comparisons at this cap. Semantic order results therefore concern the retrieval-and-consumption pipeline, not isolated consumer position sensitivity. The source-group counts remain too small for population or confirmatory inference; the aggregate data retain only descriptive paired group intervals and no Chris-only interval.

## Cost and verification

The 124 new jobs made 280 known calls, with zero cache hits, uncertain outcomes, or retained new reservations. Conservative recorded usage was **$0.51208 for Sol and $2.38730 for Astra**, totaling **$2.89938**. P8 accounts for $0.54412 and the four controls for $2.35526. Historical profile extraction, Luna calls, and embedding producers remain separate. These usage estimates are not invoices.

The frozen analysis plan was written before role04 opened the new prediction bodies. The scorer verified closure, pinned manifests and results, exact source/target schedules, and the alias mappings before scoring private development labels. A separate direct tally independently matched all 280 new correct/valid counts, per-arm Brier scores, and costs. No labels, source prose, or response bodies are published.

Role09's durable compiler/index review and role05's actual baseline execution-binding review are tracked by exact receipt in the publication event. The initial immutable score records their pending state at computation; later receipts close those caveats through a separate amendment without rewriting results.

No model calls or changes to frozen selection occurred during this analysis. The shared-profile construction and own-versus-swapped diagnostic are separate work; neither is a result of this table.
