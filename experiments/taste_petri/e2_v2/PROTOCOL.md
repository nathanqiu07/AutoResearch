# E2 v2 protocol

Pre-registered 2026-11-15, before any output of pairs_v2 or profiles_contrastive was read.

Question: on held-out pairs where generic research sense is split, does a pre-T Owain Evans profile predict his
post-T choice better than no profile?

## Inputs
- Pairs: `pairs_v2/band.jsonl`, the taste band (blind share for his option in [0.25, 0.75]). Secondary:
  `pairs_v2/pairs.jsonl`, all pairs, reported separately.
- Profiles: `profiles_contrastive/arms.py`, `get_profile_text(arm, context)`.

## Arms
| arm | profile text |
|---|---|
| M0 | none |
| M0s | none, sonnet predictor (a second no-profile reading, because the band was selected with haiku) |
| NAME | "The researcher is Owain Evans." |
| E_pre | `e2_owain`'s pre-T taste vector (the old format) |
| P0 | consensus-only card (placebo, matched in length to P1) |
| P1 | gated contrast card |
| P2 | trade-off axis profile |
| P3 | k = 5 retrieved pre-T decisions |
| P4 | decision-style vector |
| P1+P3 | contrast card plus retrieval |
| MIS | P4 built the same way for a different researcher, or P4 with its claims shuffled (placebo) |

Predictor: haiku, both option orders. A pair is correct only if his option is chosen in both orders
(`track_eval.paired_correct`). Record p(his) per order. Predictor calls never reuse the gate's votes: the prompt
and sampling differ, and the cache key includes the arm.

## Metrics
- Primary: paired accuracy on band pairs. 90% CI by `track_eval.cluster_ci` over works (a paper and its post count
  as one work).
- Secondary: mean p(his) on band pairs; accuracy on all pairs; accuracy by generator (peer / axis / field).

## Decision rules (fixed now)
- **A profile "predicts taste"** if it beats M0 *and* P0 *and* MIS on band accuracy, with the cluster-diff 90% CI
  vs M0 above 0. The difference from M0s must have the same sign.
- If the band is real, M0 on band pairs should be near 0.5. If M0 is above 0.65 on
  fresh samples, the band does not hold up beyond the gate's votes. Report that, and fall back to the
  sonnet-gated subset.
- If P1 beats M0 but not P0 or MIS, report that any extra context helps, without claiming a taste effect.
- With fewer than 30 band pairs or fewer than 8 works, results are descriptive and no claim is made.

## Budget
≤ 11 arms × 2 orders × n_band haiku calls, plus M0s on sonnet. Hard cap 900 calls.

## Amendments (before any e2_v2 scoring)
- 2026-11-15: P1 keeps claims that the blind gate scores lopsided *against* him (field default chosen at ≥ 0.9).
  Only claims lopsided *toward* him (consensus) are dropped to P0. This follows the rule's intent: drop
  consensus, keep claims where generic sense mispredicts him. P0 is cut to P1's word count (it was 2×) so the
  placebo is length-matched.
- 2026-11-15, after the pairs_v2 diagnostic (`diag_v2.md`) and before any pairs_v3 output: on pairs_v2's
  haiku-gated band, haiku M0 = 0.42 but sonnet M0s = 0.83, so a haiku-gated band is a haiku artefact.
  For pairs_v3, the band is gated on sonnet (taste share and realness share). The **primary predictor becomes
  sonnet**, with M0s as the baseline for all arms. Haiku arms are secondary. The decision rules are otherwise
  unchanged, with "M0" read as the sonnet no-profile arm.
- 2026-11-15, E2 on pairs_v4 (blind-context firewall), registered before any predictor call on these pairs.
  Pairs: all 246 in `pairs_v4/pairs.jsonl`, with up to 100 used, stratified over all 10 works. With the firewall,
  sonnet's blind judges give his option a mean share of 0.17. So the question changes from "does a profile split
  a tie" to "does a pre-T profile move sonnet toward his actual, less-default choice".
  Arms (sonnet primary): M0s, NAME, P0 (consensus placebo, length-matched), P1, P4, MIS (shuffled P4), and
  ANTI, a generic placebo of matched length ("this researcher often departs from the typical or most cautious
  choice"). ANTI checks whether any push away from the default gets the gain. The "pragmatic and assertive"
  pattern seen in pairs_v4's gating is post-T, so no arm may use it.
  A profile "predicts taste" if it beats M0s, P0, MIS **and ANTI**, with the cluster-diff 90% CI over works
  above 0 against each. Accuracy is paired, his option in both orders. Mean p(his) is secondary. Cap: 1,400
  sonnet calls.
