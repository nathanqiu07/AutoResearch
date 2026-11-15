# Decision-style attribution test

Pre-registered 2026-11-15, before any data in this directory existed.

Why: synthetic distractors leak which option is real (pairs_v2: haiku spots it 87% of the time; pairs_v3: sonnet
still 0.72 after three rounds of equalising), and a strong reader is rarely split on Owain's post-T choices. Here
both options are real decisions, so realness is equal by construction.

## Items
- Post-T decisions: Owain Evans (`pairs_v2` sources, T = 2026-01-01) and Steinhardt, Carlini, Barnes, Marks
  (`decisions_v2/`, post their own T). Never Hobbhahn.
- Every decision is rendered **topic-neutral** by sonnet in batches: the problem and the choice are kept as an
  abstract research trade-off. Domain nouns, paper-specific terms, model names and anything that identifies the
  research area are stripped. A leak check flags any rendering that still holds a 3-gram from the source title.
- Pair = one Owain decision + one other researcher's decision with the same D-point, nearest by TF-IDF on the
  abstracted problem. Shown in both orders.

## Question and arms
"Two research decisions, each made by a different researcher. Which one did the researcher described below make?"
- Arms: NAME (persona = "Owain Evans" only), P0 (consensus placebo, length-matched), P1, P2, P3 (retrieval keyed on
  each abstracted problem), P4, P1+P3, MIS (shuffled P4), MIS2 (another researcher's card).
- M0 (no information) is 0.5 by construction and is not run. NAME is the baseline that measures topic leakage
  and the model's prior knowledge of him.
- Predictor: sonnet primary, haiku secondary. Both orders; correct = his decision chosen in both orders.

## Decision rules
- **Taste attribution** if P-arm accuracy beats NAME, P0 and MIS with the cluster-diff 90% CI (over Owain works)
  above 0, on sonnet.
- **Leakage check:** if NAME exceeds 0.65, topic or identity leaked through the abstraction. Report that and
  re-abstract more aggressively before any claim.
- With fewer than 60 pairs or fewer than 8 Owain works, results are descriptive only.

## Amendment: round 2 (2026-11-15, after round 1's leakage flag, before any round-2 data)
- Re-abstract every item into one fixed template (situation / options considered / choice / reason), with a
  banned-word list derived from round 1's bag-of-words classifier weights (top 40 discriminative words for each
  side) plus genre words (effect, transfer, performance, method...).
- Run order: a bag-of-words held-out-work classifier first (free), then sonnet NAME alone. Profile arms run only if
  NAME ≤ 0.65 **and** bag-of-words ≤ 0.65. Otherwise report that the leak survives fixed-template abstraction and
  stop.
- If the arms run, the decision rules are as above.
