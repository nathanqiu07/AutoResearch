# Richer writing did not improve overall delivery on this panel

The richer corpus produced **581 correct delivered predictions out of 1,344 planned rows (43.23%)**, compared with **635/1,344 (47.25%)** for sparse text. The difference is −4.02 percentage points. Valid delivery fell from 672/1,344 (50.00%) to 622/1,344 (46.28%). This fixed development comparison does not support an overall benefit from adding this writing.

That result includes extraction and service failures. On the **426 exact config/item rows valid under both source conditions**, richer text was correct on 394 and sparse text on 398: a difference of −0.94 points. There were 376 shared correct answers, 18 richer-only correct, 22 sparse-only correct, and 10 shared errors. The mean Brier difference on those same rows was +0.00853, where higher is worse. These are observations on a small panel, not evidence that more writing generally harms personalization.

| Researcher | Planned rows | Sparse correct / valid | Richer correct / valid | Jointly valid rows | Richer minus sparse correct on joint rows |
|---|---:|---:|---:|---:|---:|
| Neel Nanda | 672 | 290 / 322 | 237 / 271 | 187 | −1 |
| Chris Olah | 672 | 345 / 350 | 344 / 351 | 239 | −3 |
| Fixed grid total | 1,344 | 635 / 672 | 581 / 622 | 426 | −4 |

Conditional accuracy among each condition's own valid rows was 93.41% for richer text and 94.49% for sparse text. Those use different subsets; the joint comparison above is the matched comparison. Across all cells, 196 rows were valid only under richer text, 246 only under sparse text, and 476 under neither. Conditioning on delivery must not replace the planned denominator.

## What changed and what stayed fixed

The frozen experiment used all 48 configurations × 2 researchers, replicate 0, with the same f6 runtime, consumer settings, caps, and 14 ordered target items per researcher. Each researcher's seven underlying judgments appeared in both option orders. The panel has only two Neel target source groups and one Chris group.

Approved fit text grew from 4,565 to 37,725 UTF-8 bytes for Neel and from 7,968 to 43,767 for Chris. Documents grew from 1 to 2 and from 2 to 4, respectively. **The fit source families remained one for Neel and two for Chris.** The admission review retained 6 admitted, 23 excluded, and 2 pending capture records. This tests more text within those approved families, under the same personalization caps; it does not test broad independent coverage of either researcher's writing. P7's declared peer-fit union remained a separate method condition.

Neither the source release nor the grid was selected using these scores. The existing scaling selection remains unchanged. This report makes no final-test, promotion, or fidelity-winner claim.

## Delivery and retained failures

Richer extraction produced 47 complete, 36 invalid, and 5 empty profiles; 8 structural cap failures remained planned zero-call omissions. Sparse extraction had 48 complete profiles. Only 33 cells had complete builds in both conditions, so aggregate delivery includes substantial changes in which configurations succeeded.

The continuation added 420 known complete core rows to the original 202, giving 622. All 622 passed choice validation. The other **722 planned slots remain visible**: 504 invalid-build rows, 70 empty-build rows, 112 structural rows, 2 uncertain calls, 20 never-called tails of the two partial jobs, and 14 slots in the excluded unknown-collision job. No partial tail, unknown call, or excluded job was retried.

The 50-row coverage reduction relative to sparse text comprises 14 fewer slots from the net one-profile build difference and 36 retained consumer-stage omissions. This is arithmetic, not a causal attribution of why individual builds changed. There is one extraction attempt per condition/configuration, with different request times; stochastic generation and service effects remain confounds.

## Matched controls

Every entry below has 28 ordered rows: 14 per researcher. All fresh richer control rows were valid. The paired values are **sparse → richer correct counts**, without ranking or selecting a new cap.

| Control | Cap 512 | Cap 2,048 | Cap 8,192 |
|---|---:|---:|---:|
| No profile | 26 → 26* | 26 → 26* | 26 → 26* |
| Name only | 26 → 26* | 26 → 26* | 26 → 26* |
| Raw evidence | 25 → 26 | 28 → 27 | 27 → 25 |
| Lexical retrieval | 26 → 26 | 27 → 23 | 26 → 25 |
| Semantic retrieval | 27 → 25 | 26 → 23 | 25 → 28 |

\* These are historical aliases, not new executions. The 420 richer control comparison slots comprise **252 fresh rows plus 168 cap references to 56 actual sparse no-profile/name-only rows**. Aliases add zero calls and zero independent observations. Fresh raw/retrieval controls jointly produced 228/252 correct versus 237/252 for sparse text. Across all logical control slots, including repeated aliases, the counts are 384/420 versus 393/420; those are bookkeeping totals, not independent samples.

Semantic retrieval at 8,192 improved by three answers, while both retrieval methods at 2,048 worsened. That heterogeneity does not establish a general source benefit or a best method. The no-profile and name-only controls already score **26/28**, showing a strong task-discrimination limitation: high accuracy alone does not establish that the personal profile helps.

## Order sensitivity and uncertainty

Among core config/judgment pairs where both orders were valid, semantic choice consistency was 282/309 (91.26%) for richer text and 317/336 (94.35%) for sparse text. These are different delivered subsets. For Neel the counts were 114/134 versus 147/161; for Chris, 168/175 versus 170/175. Repeated configurations and option orders do not create independent source evidence.

Role05's separate frozen order diagnostic found identical lexical context across all 84 reversal comparisons, but changed semantic context in 5/42 sparse and 9/42 richer comparisons. Semantic order comparisons therefore measure sensitivity of retrieval plus consumption, not isolated consumer position sensitivity. No accuracy change is attributed to a particular context change here.

The aggregate JSON retains descriptive source-group bootstrap intervals, including no interval for Chris's single group. With only two Neel groups and one Chris group, those intervals cannot support population inference or confirmatory significance claims. The 1,344 planned rows are repeated weighting of 14 underlying judgments across configurations, not 1,344 independent human choices.

## Cost and verification

Richer core processing used 712 attempts: 88 extraction calls plus 624 consumer attempts, including the two uncertain calls. Known conservative usage was **$0.304652875**, with **$0.008804500** still held, for a $0.313457375 bound. Sparse core usage was $0.208583750 known plus $0.019078625 retained, a $0.227662375 bound. Fresh richer controls added $0.045401125 for 252 known calls; historical aliases added no cost. Embeddings remain charged once at their separate producer. These are conservative usage estimates plus holds, not invoices.

The scorer checked the frozen continuation, prior partial snapshot, source and target bindings, exact manifests/subsets, and all 96 planned cells before reading private development labels. A separate direct tally matched every core cell and the 252 fresh controls. The driver independently verified all 204 continuation jobs and 672 requests as complete with known usage and no cache hits or new unknowns. Role05 owns the additional actual-control execution-binding review; its receipt is tracked separately in the publication event, without duplicating that audit.

Required repository verification passed: `python3 -m unittest discover -s tests -t .` — **692 tests, 2 skipped**. No model calls, target changes, new labels, or final-test access occurred during scoring.

The safe aggregate report is `richer-versus-sparse-development-score-v1.json`; `richer-comparison-completion-provenance-v1.json` retains all 1,344 core and 420 control slots without choices or labels; `richer-comparison-independent-tally-v1.json` records the independent arithmetic check. Their hashes and the exact source/continuation pins are in the publication event.
