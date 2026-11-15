# Hill-climbing the Owain profile on E2

Pre-registered 2026-11-15, before any climb call.

Goal (user): raise the e2_v4 intervals for the profile against no profile (M0s) and against the bare name (NAME).
Start point: P4, the best e2_v4 arm (+0.115 accuracy and +0.050 p(his) vs M0s; +0.037 p(his) vs NAME).

## Two climbs
| climb | climb set (selection signal) | confirmation set | claim it supports |
|---|---|---|---|
| A, time-pure (primary) | `synthme/pairs_paper.jsonl`, 196 firewalled pre-T pairs: 146 climb, 50 early-stop by the existing work split | the 96 e2_v4 post-T pairs | a profile tuned only on his past predicts his future |
| B, decision-disjoint (secondary) | pairs_v4 post-T pairs whose decision does **not** appear in the 96 e2_v4 pairs | the 96 e2_v4 pairs | weaker: tuned on other post-T decisions from the same works |

## Search
- State: a profile text. The start state is P4.
- Operators:
  1. Add one claim drawn from a fixed pool of pre-T claims: P1/P0/P2 claims, P4 lines, S_paper hypotheses, and
     sonnet generalisations of pre-T informal decisions.
  2. Delete one line.
  3. Sonnet rewrite of one line (sharper or more general). The rewriter sees the line only, never any pair.
  4. Compress the whole card.
- No operator may see pair text or labels. Only the accept/reject signal comes from scores.
- Objective on the climb set: mean p(his) minus M0s's mean p(his) (both orders, batched sonnet predictions).
  Accept a step if the objective rises by more than 0.01 and paired accuracy does not fall. At most 25 steps per
  climb. Keep the best state by early-stop score (climb A) or by climb-set score (climb B).
- No hand edits to the profile text.

## Confirmation
One run per climb, no retries.
- Sonnet, e2_v4's exact unbatched prompt format, both orders, the 96 pairs. M0s, NAME and P4 come from the e2_v4
  cache.
- Report H_A and H_B against M0s and NAME (paired accuracy and mean p(his), 90% cluster CIs over works) and
  against P4. P0, MIS and ANTI are descriptive only.
- Primary: H_A beats M0s, with the CI above 0. Secondary: H_A beats NAME. H_B is reported with its weaker label.
- Report the climb traces and the final texts in full.

## Budget
At most 1,600 sonnet calls in total (climbs at most 1,200 batched, confirmation at most 400), at most 3 concurrent.
Starts after the CLI usage limit resets (14:20 PT).

## Amendment: budget (2026-11-15, user: "cap the spend lowly, use haiku for repetitive evaluation")
Before any climb call. Climb-set scoring uses batched **haiku** (at most 400 calls); line rewrites use sonnet (at most 40).
The confirmation stays on sonnet (at most 192 calls per climb), so it compares with e2_v4. Climb B runs only if
climb A finishes under these caps. Because selection is on haiku and confirmation on sonnet, a haiku-only gain may
not transfer.
