# SynthesizeMe on firewalled pre-T pairs: results

Protocol: `PROTOCOL.md`, including the amendment on verdicts (primary: beat M0s; secondary: beat NAME; P0 and ANTI0
descriptive) and the amendment on budget (phase 3 validation on haiku, ANTI0 not scored, 700 sonnet and 600 haiku
for the rest of the run). Numbers come from `results.json`, written by `python3 fit.py report`.

## Headline

- **S_paper** (fit on paper pairs) does not beat M0s or NAME. Its persona is hedged and resource-conscious, and
  tied to two specific papers.
- **S_inf** (fit on informal pairs) beats M0s on paired accuracy and mean p(his) (primary), and beats NAME on mean
  p(his) (secondary). Its persona says, in effect, "less cautious": quick holistic reading over systematic
  measurement, and low-effort assessments over formal validation. It was learned from pre-T data only.
- **S_inf − S_paper**: +0.062 paired accuracy, 90% CI [-0.011, 0.135]. This is no claim under the pre-registered
  rule, which uses accuracy and was not amended. On mean p(his) the gap is +0.045 [0.021, 0.068] (descriptive).
- Caveat: e2_v4 showed that a direction push alone moves this test set (its ANTI, written with post-T knowledge,
  reached 0.438). S_inf's gain may be largely the "less cautious" direction rather than anything specific to him.
  Against P0 its accuracy gain is +0.062 [-0.031, 0.150].
- **S_all** was not scored. Its fit was stopped at 13:55 PT, 78 of about 300 validation calls in, to meet the
  user's 14:00 deadline. It was the lowest priority, and its history would have been the same 50 informal pairs as
  S_inf's (see Deviations).

## Test results

Test pairs: e2_v4's 96 pairs over 10 works, sonnet, both orders. 90% CIs resample works.

| arm | paired acc [90% CI] | mean p(his) [90% CI] |
|---|---|---|
| M0s | 0.177 [0.11, 0.25] | 0.379 [0.353, 0.405] |
| NAME | 0.260 [0.179, 0.348] | 0.392 [0.369, 0.417] |
| P0 | 0.229 [0.15, 0.312] | 0.388 [0.358, 0.418] |
| S_paper | 0.229 [0.14, 0.341] | 0.406 [0.369, 0.449] |
| S_inf | 0.292 [0.216, 0.389] | 0.451 [0.424, 0.483] |

**S_paper minus each arm** (cluster-diff, 90% CI)

| vs | Δ paired acc | Δ mean p(his) |
|---|---|---|
| M0s | +0.052 [-0.042, 0.168] | +0.027 [-0.003, 0.063] |
| NAME | -0.031 [-0.135, 0.09] | +0.014 [-0.015, 0.051] |
| P0 | +0.000 [-0.093, 0.111] | +0.018 [-0.01, 0.052] |

**S_inf minus each arm** (cluster-diff, 90% CI)

| vs | Δ paired acc | Δ mean p(his) |
|---|---|---|
| M0s | +0.115 [0.039, 0.189] | +0.072 [0.052, 0.094] |
| NAME | +0.031 [-0.054, 0.116] | +0.060 [0.041, 0.08] |
| P0 | +0.062 [-0.031, 0.15] | +0.063 [0.038, 0.089] |
| S_paper | +0.062 [-0.011, 0.135] | +0.045 [0.021, 0.068] |

Verdicts (PROTOCOL.md amendment):

- PRIMARY S_paper vs M0s: does not beat (Δacc +0.052 [-0.042, 0.168]; Δp(his) +0.027 [-0.003, 0.063]).
- SECONDARY S_paper vs NAME: does not beat (Δacc -0.031 [-0.135, 0.09]; Δp(his) +0.014 [-0.015, 0.051]).
- descriptive S_paper vs P0: Δacc +0.000 [-0.093, 0.111]; Δp(his) +0.018 [-0.01, 0.052].
- PRIMARY S_inf vs M0s: BEATS on acc, p_his (Δacc +0.115 [0.039, 0.189]; Δp(his) +0.072 [0.052, 0.094]).
- SECONDARY S_inf vs NAME: BEATS on p_his (Δacc +0.031 [-0.054, 0.116]; Δp(his) +0.060 [0.041, 0.08]).
- descriptive S_inf vs P0: Δacc +0.062 [-0.031, 0.15]; Δp(his) +0.063 [0.038, 0.089].
- S_inf − S_paper on paired accuracy (the pre-registered rule, not amended): no claim (Δacc +0.062 [-0.011, 0.135]); descriptive Δp(his) +0.045 [0.021, 0.068].

M0s, NAME and P0 are e2_v4's cached predictions on the same 96 pairs (`e2_v4/results.json`). No test pair failed in
any arm.

## Personas

**S_paper** (142 words; 2 retained hypotheses, 2 exemplars): "A pragmatic, resource-conscious evaluator who prizes
cheapness through practical feasibility. When building evaluations, they choose a lightweight subset of simple,
easily portable tasks … They value low compute and easy use across different evaluation pipelines over rigorous
statistical validation against full-benchmark rankings. In interpreting results, they favor calibrated, hedged
conclusions that fit mixed evidence … They dislike overclaiming categorical statements …"
Both retained hypotheses come from two papers (the BIG-bench lite subset and a scaling result). Nothing in it says
"less cautious".

**S_inf** (2 exemplars): "Evaluates model outputs through quick, holistic reading rather than systematic
measurement. Judges quality by overall impression: whether text is fluent, clear, and free of obvious
hallucinations. Prefers to continue the approach already in progress (reading and eyeballing outputs) over adding
deliberate steps like computing error rates or building quantitative metrics. Tends to treat apparent fluency and
coherence as good evidence of reliability, and favors low-effort, practical assessments over rigorous, formal
validation."
This is the less-cautious direction, from pre-T informal sources only.

| fit | history | val | val baseline | persona | hypothesis-text fallback | validation model |
|---|---|---|---|---|---|---|
| S_paper | 50 of 146 train | 50 | 0.46 | 0.56 | 0.56 | sonnet (batch 60) |
| S_inf | 50 of 76 train | 28 | 0.43 | 0.61 | 0.50 | haiku (batch 100) |

Validation is single-order accuracy on small sets (28 to 78 pairs), so the selection steps are noisy.

## Data

**Paper pairs** (`pairs_paper.jsonl`, 196 pairs):
- 325 pre-T decisions; 1 excluded because its excerpt contained another decision's quote.
- Leak check kept 139 contexts, plus 45 more after a blind revision round, for 184.
- His option was faithful for 163 of 184.
- The more-cautious and less-cautious blind stances each pass the same/different check.
- Pairs are kept only for decisions where both stances are clean: 98 decisions, 28 works, 98 pairs per direction.
- Sonnet realness (40-pair sample, both orders): his option picked as the real one in 0.81 of 80 votes.
- Split by work (seed 0): 146 train, 50 val (9 works).

**Informal pairs** (`pairs_informal.jsonl`, 104 pairs):
- 259 items from `informal/decisions.jsonl`. Dropped 25 that are in the paper set and 52 off-topic non-AI posts
  (Covid and similar, matched by title); the drops are logged in `build_informal/dropped.jsonl`. 182 kept.
- Advice items went through the same firewall, posed as decision points.
- Leak check kept 76 contexts, plus 28 after revision, for 104. His option was faithful for 92 of 104.
- Balanced pairs: 52 decisions, 34 works, 52 pairs per direction.
- Split by work: 76 train, 28 val (11 works).
- No realness sample (dropped to save spend).

All pairs come from decisions dated before T = 2026-01-01. No Hobbhahn material was used.

## Deviations and caveats

- **Validation model differs.** S_paper was fit with sonnet validation, before the budget amendment; S_inf and S_all
  use haiku. This could bias S_inf − S_paper, in either direction.
- **S_all history is all informal.** "Informal pairs first" with 76 informal train pairs fills the whole 50-pair
  history, so S_all differs from S_inf only in its validation set (28 informal + 50 paper pairs).
- **Work labels differ across sources.** The informal and paper sources label works differently (e.g. a thread on
  the Reversal Curse versus the paper itself), so the S_all validation set can share a work with its history.
- **ANTI0 was written but never scored.** `ANTI0.md` was written before any fit and was dropped from test scoring by
  the budget amendment.
- **Usage limit.** At 11:07 PT the CLI hit the account's usage limit; 476 calls were refused before reaching a
  model. They are logged as errors in `calls.log` and are excluded from the spend below.
- **Autostash.** At 13:07 PT another agent's `git pull --rebase --autostash` reset calls.log, fit.py, pairs.py and
  split.json to HEAD and left the changes in a stash. They were restored from that stash and the log was merged.
  No model call was lost; the cache is untracked.

## Spend

- Whole experiment: 1,057 sonnet calls answered, 327 haiku. A further 476 sonnet calls were refused at the usage
  limit and reached no model. Logged cost: $39.41.
- Since the budget amendment: 468 of 700 sonnet and 327 of 600 haiku.
  - Sonnet: S_paper test 120, informal build 89, S_inf fit 51, S_inf test 192, S_all fit 16.
  - Haiku: S_inf validation 249, the stopped S_all fit 78.
- Every call is cached in `cache/` and logged in `calls.log`.

## Files

- `pairs.py` builds the pairs: `python3 pairs.py paper|informal <stage>...`
- `fit.py` fits, tests and reports: `python3 fit.py fit|test|report|md`
- `S_paper.json`, `S_inf.json`: fitted SynthesizeMe models, with metadata in each file's `synthme`
  block.
- `test_<arm>.json` holds the predictions; `results.json` holds every number above.
