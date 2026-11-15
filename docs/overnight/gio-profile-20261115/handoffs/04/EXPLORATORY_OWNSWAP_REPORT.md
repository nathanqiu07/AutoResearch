# Swapping selected profiles reduced accuracy on this development panel

The selected P8 profile scored 27/28 correct when used for its own researcher, compared with 24/28 when the other researcher’s profile was substituted. Generic no-profile scored 26/28. All three conditions delivered valid predictions and probabilities for every planned row.

| Condition | Correct / planned | Coverage | Brier (lower is better) | Consistent choices across both orders |
| --- | ---: | ---: | ---: | ---: |
| Own P8 profile, historical alias | 27/28 (96.4%) | 28/28 | 0.042050 | 13/14 judgments |
| Generic no-profile, historical alias | 26/28 (92.9%) | 28/28 | 0.066507 | 14/14 judgments |
| Other researcher’s P8 profile, new calls | 24/28 (85.7%) | 28/28 | 0.104946 | 12/14 judgments |

The swap lost three correct ordered rows relative to own-profile and two relative to generic. The result is compatible with a mismatched profile hurting predictions. It does not establish a useful personal-profile advantage: own-profile beat generic by only one ordered row, after P8 was selected using these development targets.

| Target researcher | Own correct | Generic correct | Swapped correct | Own / generic / swapped Brier |
| --- | ---: | ---: | ---: | --- |
| Neel Nanda | 13/14 | 12/14 | 12/14 | 0.075686 / 0.116036 / 0.102221 |
| Chris Olah | 14/14 | 14/14 | 12/14 | 0.008414 / 0.016979 / 0.107671 |

Both option orders were correct for 13/14 judgments under own-profile, 13/14 under generic, and 11/14 under swapped. The swap’s two order-inconsistent judgments were in Chris’s panel. These are seven underlying judgments per researcher, each shown twice, from only two Neel source groups and one Chris source group. The 28 ordered rows are not 28 independent judgments. The saved group bootstrap intervals are descriptive within those few groups; they do not support a researcher-population claim.

The comparison uses the frozen P8-c8192-explicit-only replicate-0 profiles and original sparse-fit v2 targets with the Luna consumer. Each swap retained the true donor profile, source hashes and text, while the evaluator used the separate target researcher’s original private bundle. Profiles were neither relabeled nor altered. The Neel and Chris renderings contain 3,322 and 3,310 UTF-8 bytes; they were not length-matched. Own and generic predictions were historical, while swap predictions were collected later. Sampling and time differences remain uncontrolled. No shared-profile arm was specified or run.

The metric plan was frozen after terminal completion and before opening new swapped prediction bodies. This timing is explicit: it is an exploratory post-selection analysis, not preregistration. All planned rows were retained; planned and conditional accuracy coincide because coverage is complete. The fixed contrasts were swapped-minus-own, swapped-minus-generic and own-minus-generic, separately by researcher and pooled with equal row counts.

Only the 28 swapped requests are new observations. Their recorded known cost was $0.005598, with no cache hits or uncertain attempts. The 56 historical aliases added no calls, cost or independent observations; their producer costs remain in prior receipts. Root’s terminal verifier and role05’s prepared-input review are pinned in the score receipt. Role04 checked exact target/donor/item/manifest/result bindings and independently reproduced the new correct-count and Brier arithmetic. No private label or source prose is published. No final test, new selection, winner claim or further execution is authorized by this report.

Artifacts: [frozen plan](exploratory-ownswap-custodian-scoring-plan-v1.json), [aggregate score and fixed contrasts](exploratory-ownswap-development-score-v1.json), [direct arithmetic verification](exploratory-ownswap-direct-tally-verification-v1.json).
