# Three-replicate development screen and scaling proposal

The ten promoted configurations retain all 840 planned ordered rows across 60 researcher cells. There are 49 complete builds, 9 invalid builds and 2 empty builds. The 686 delivered predictions were valid; 639 were correct: **639/840 (76.07%) delivered-correct**, **686/840 (81.67%) coverage**, and **639/686 (93.15%) conditional valid accuracy**. The 154 absent rows remain failures (28 from replicate 0,126 from replicates 1/2). These totals describe the selected development screen, not population performance.

All 40 new extraction requests and 434 new prediction requests were fresh known executions with no cache replay or uncertain usage. This proves distinct request events, not statistically independent sampling. Replicate0 outcomes were loaded unchanged from their original frozen private report. Richer-source results and unpromoted single-replicate configurations are separate.

| Operational rank | Configuration | Correct /84 | Valid /84 | Conditional correct | Conservative cost USD |
|---:|---|---:|---:|---:|---:|
| 1 | P8-c8192-explicit-only | 81/84 | 84/84 | 81/84 | 0.023833750 |
| 2 | P4-c512-explicit-only | 80/84 | 84/84 | 80/84 | 0.011968125 |
| 3 | P8-c8192-marked-inference | 80/84 | 84/84 | 80/84 | 0.02522675 |
| 4 | P4-c512-marked-inference | 78/84 | 84/84 | 78/84 | 0.011666875 |
| 5 | P1-c512-explicit-only | 72/84 | 84/84 | 72/84 | 0.012107625 |
| 6 | P2-c512-marked-inference | 62/84 | 70/84 | 62/70 | 0.011094875 |
| 7 | P7-c8192-marked-inference | 52/84 | 56/84 | 52/56 | 0.01220050 |
| 8 | P5-c2048-explicit-only | 52/84 | 56/84 | 52/56 | 0.015866625 |
| 9 | P6-c2048-marked-inference | 41/84 | 42/84 | 41/42 | 0.011841625 |
| 10 | P3-c8192-explicit-only | 41/84 | 42/84 | 41/42 | 0.013735375 |

The frozen policy selects the global highest-ranked configuration first, adopts its cap, then takes up to three distinct families at that same cap. The resulting mechanical proposal is **cap 8192: P8-explicit primary, P7-marked-inference, P3-explicit**. P8-marked-inference is skipped because the family is already represented; P4-cap512-explicit is second overall but outside the declared common-cap panel. No configuration or saved profile was retagged to another cap. This is a proposal for coordinator verification/adoption; it grants no execution or confirmation authority.

P3 delivered only Chris predictions in all three replicates: 41/42 correct there, 0/42 delivered for Neel. Its Neel replicate 0 mapping stays `unavailable_rep0` with null profile; no later-replicate fallback is allowed. P7 has 28/42 valid rows for each researcher, with 25/42 delivered-correct for Neel and 27/42 for Chris. Their high conditional accuracy must not hide missing coverage.

The primary P8-explicit scores 40/42 for Neel and 41/42 for Chris. Against the same-cap raw-evidence control referenced over the same three schedules, it gains 1/42 for Neel and loses 1/42 for Chris: **zero pooled delivered-correct gain**. The raw control has only 14 actual rows per researcher, referenced three times; it was not rerun or counted as 42 independent observations. No-profile/name-only originally scored 26/28, so the panel still has little room to distinguish personal-profile benefit. Selection stability cannot repair this task-discrimination limit.

Across the primary's three replicates, 19/21 Neel and 20/21 Chris semantic-pair instances are consistent under option reversal. Agreement between pairs of replicas ranges 12–13/14 for Neel and 13–14/14 for Chris. The repeated orders and replicas do not add independent judgments: there remain seven semantic targets per researcher, two Neel source groups and one Chris group. Group bootstrap intervals in the JSON resample only those observed groups; none is provided for Chris. Even narrow intervals do not support source-population, human-population or general fidelity claims.

The report includes 120 paired comparisons against five matched controls and memory, with all-scheduled and joint-valid differences kept separate. Controls are canonical references, not new samples. P7 retains its explicitly declared additional peer fitting evidence. The primary is an operational choice under the predeclared rule, not a confirmed best method, fidelity winner or finalist.

New costs are 40 extractions at $0.036715250 plus 434 predictions at $0.05902325: 474 calls and $0.095738500 known conservative usage. Including the selected original replicate 0 adds 272 calls and $0.053803625, for 746 calls and $0.149542125. There are no uncertain charges among these selected jobs; the earlier whole-screen $0.019078625 uncertain reservations remain separately retained. Costs are conservative usage estimates, not invoices. Shared control/embedding charges were already accounted elsewhere.

Publication verification matched all 434 driver per-row results/traces against evaluator pins, recomputed the integer/Decimal ranking from public cells, verified actual replicate 0 admissions and preserved original source/item/option schedules. An unpublished metadata draft incorrectly classified incremental cost by prediction-config replicate ID, counting only the 40 builds; v2 corrects it using exact new-job membership. Total three-replicate cost, all scores, ranking and private reports did not change; no labels were reopened by the amendment.

The exact candidate receipt `development-scaling-selection-v2.json` uses schema `development-scaling-selection-v1` and pins contract 57e798…, driver completion d3015d…, original/sparse/build indexes, actual admissions, sparse controls/semantic inputs and StudyD panel ef248a…. Its separate proposal receipt explicitly awaits coordinator verification and adoption. StudyD uses all 28 original source-backed judgments with their answer-bearing whole source groups withheld; exact raw-evidence execution aliases add no calls or independent observations.

No model calls, final-data use, source edits, new labels, new targets or runtime changes were performed by role 04.
