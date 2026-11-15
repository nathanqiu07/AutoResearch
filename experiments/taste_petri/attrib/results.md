# Decision-style attribution test: results

Run 2026-11-15 under `PROTOCOL.md` (pre-registered). Code: `abstract.py` -> `pairs.py` -> `run.py`; per-pair dump in
`results.json`; every call cached in `cache/` and logged in `calls.log`.

**Bottom line.** The protocol's leakage check fired: with only the name "Owain Evans" and no profile, sonnet picks his
decision in both orders on 0.756 of 90 pairs (> 0.65). Under the protocol no taste claim is allowed until the items
are re-abstracted more aggressively, and none is made. Besides that, no profile arm beats NAME, P0 or MIS on sonnet;
every point estimate is at or below NAME, and P3 and P4 are the lowest (0.656, 0.678).

## What ran

| stage | what | calls |
|---|---|---|
| `abstract.py` | 356 post-T decisions (Owain 106, Barnes 66, Marks 65, Carlini 62, Steinhardt 57; none dropped for Hobbhahn) rendered topic-neutral by sonnet, 10 per call, researchers mixed in every batch, one instruction for all | 47 sonnet (cap 50) |
| `pairs.py` | each Owain decision + nearest (TF-IDF on `abstract_problem`) unused same-D-point decision of a random other researcher; 104 pairs over 10 Owain works, no opponent decision reused, second pairing not needed | 0 |
| `run.py` | e2_v2 predictor (UserModel._predict_with, profile in the persona slot, JsonReply, both orders, paired_correct, cluster CIs over Owain works) | 1080 sonnet (cap 1100) + 384 haiku (cap 400) |

No call failed and every prediction parsed (0 errors, 0 pairs excluded). Reported cost $12.75. 4 workers.

## Deviations from PROTOCOL.md and from the brief

1. **Arms dropped for budget.** P2 and MIS2 were dropped first, as instructed. P1+P3 was also dropped: 7 sonnet arms x 2
   orders x 80 pairs = 1120 calls exceeds the 1100 cap, so keeping P1+P3 would have meant fewer than 80 pairs.
   Sonnet arms: NAME, P0 (trimmed to P1's 634 words), P1, P3, P4, MIS.
2. **Pair subsets.** Sonnet ran on 90 of the 104 pairs (6 arms x 2 x 90 = 1080). Haiku ran NAME, P4, P0 and MIS on 48
   of those 90 (4 x 2 x 48 = 384 <= 400). Both subsets were cut by repeatedly dropping a random pair from the Owain
   work with the most pairs, so all 10 works stay in each. Haiku is therefore below the protocol's 60-pair floor and
   is descriptive only.
3. **Leak-check details** (the protocol names the title 3-gram check; the stoplist rule came from the brief). The
   stoplist is the content words of every corpus title of that researcher (Hobbhahn-authored docs skipped), minus
   stopwords and a fixed list of generic research words written before any rendering existed. Flagged items were
   re-rendered with their offending words forbidden, for up to 2 rounds, in batches of 12. The 6 items still flagged
   after that were left out of pairing, 2 of them Owain's, so there are 104 pairs, not 106.
4. **P3 retrieval** "keyed on each abstracted problem": the top 3 of his pre-T decisions for each of the pair's two
   abstracted problems, merged and ordered by score (up to 6), so the text does not depend on which option is his.
5. **Question delivery.** The protocol question is the `context` of the e2_v2 predictor. That predictor's fixed
   instruction ("Predict which option this user would choose...") wraps it, and the arm's text fills the persona slot.
6. **The leakage rule fired and re-abstraction was not done**: 47 of the 50 abstraction calls had been spent. The
   protocol forbids any claim until that is done.

## Results

Paired accuracy means his option is chosen in both orders. 90% CIs resample Owain works (cluster bootstrap); Δ is the cluster-diff CI on the same pairs. M0 is 0.5 by construction and was not run.

### sonnet: all pairs (n = 90, Owain works = 10)

| arm | words | paired acc [90% CI] | mean p(his) [90% CI] | Δ vs NAME [90% CI] | Δ vs P0 [90% CI] | Δ vs MIS [90% CI] |
|---|---|---|---|---|---|---|
| NAME | 5 | 0.756 [0.702, 0.806] | 0.598 [0.587, 0.61] | – | +0.011 [-0.065, 0.091] | +0.022 [-0.045, 0.079] |
| P0 | 634 | 0.744 [0.663, 0.811] | 0.597 [0.583, 0.608] | -0.011 [-0.091, 0.065] | – | +0.011 [-0.056, 0.062] |
| P1 | 634 | 0.733 [0.657, 0.81] | 0.575 [0.566, 0.583] | -0.022 [-0.124, 0.09] | -0.011 [-0.092, 0.078] | +0.000 [-0.081, 0.086] |
| P3 | 530 | 0.656 [0.543, 0.756] | 0.576 [0.545, 0.602] | -0.100 [-0.21, 0.0] | -0.089 [-0.203, 0.02] | -0.078 [-0.167, 0.0] |
| P4 | 244 | 0.678 [0.647, 0.708] | 0.598 [0.586, 0.609] | -0.078 [-0.14, 0.0] | -0.067 [-0.131, 0.016] | -0.056 [-0.091, -0.022] |
| MIS | 244 | 0.733 [0.686, 0.782] | 0.596 [0.584, 0.607] | -0.022 [-0.079, 0.045] | -0.011 [-0.062, 0.056] | – |

### sonnet: paired accuracy by opponent researcher

| arm | elizabeth_barnes (n=30) | jacob_steinhardt (n=23) | nicholas_carlini (n=19) | samuel_marks (n=18) |
|---|---|---|---|---|
| NAME | 0.867 | 0.739 | 0.632 | 0.722 |
| P0 | 0.800 | 0.609 | 0.789 | 0.778 |
| P1 | 0.767 | 0.739 | 0.684 | 0.722 |
| P3 | 0.800 | 0.696 | 0.474 | 0.556 |
| P4 | 0.833 | 0.565 | 0.632 | 0.611 |
| MIS | 0.833 | 0.652 | 0.789 | 0.611 |

### haiku: all pairs (n = 48, Owain works = 10)

| arm | words | paired acc [90% CI] | mean p(his) [90% CI] | Δ vs NAME [90% CI] | Δ vs P0 [90% CI] | Δ vs MIS [90% CI] |
|---|---|---|---|---|---|---|
| NAME | 5 | 0.458 [0.333, 0.574] | 0.563 [0.516, 0.602] | – | -0.250 [-0.362, -0.149] | -0.188 [-0.34, -0.041] |
| P4 | 244 | 0.625 [0.5, 0.75] | 0.597 [0.567, 0.63] | +0.167 [0.022, 0.3] | -0.083 [-0.163, -0.02] | -0.021 [-0.152, 0.1] |
| P0 | 634 | 0.708 [0.638, 0.792] | 0.618 [0.595, 0.638] | +0.250 [0.149, 0.362] | – | +0.062 [-0.067, 0.18] |
| MIS | 244 | 0.646 [0.52, 0.776] | 0.571 [0.537, 0.604] | +0.188 [0.041, 0.34] | -0.062 [-0.18, 0.067] | – |

### haiku: paired accuracy by opponent researcher

| arm | elizabeth_barnes (n=16) | jacob_steinhardt (n=10) | nicholas_carlini (n=15) | samuel_marks (n=7) |
|---|---|---|---|---|
| NAME | 0.375 | 0.500 | 0.600 | 0.286 |
| P4 | 0.750 | 0.700 | 0.533 | 0.429 |
| P0 | 0.750 | 0.600 | 0.867 | 0.429 |
| MIS | 0.750 | 0.700 | 0.600 | 0.429 |

## Verdicts (PROTOCOL.md decision rules, printed by run.py)

- LEAKAGE (sonnet): NAME = 0.756 > 0.65, so topic or identity leaked through the abstraction. Re-abstract more aggressively before any claim.
- P1 (sonnet): no taste attribution (acc 0.733; vs NAME -0.022 [-0.124, 0.09]; vs P0 -0.011 [-0.092, 0.078]; vs MIS +0.000 [-0.081, 0.086]).
- P3 (sonnet): no taste attribution (acc 0.656; vs NAME -0.100 [-0.21, 0.0]; vs P0 -0.089 [-0.203, 0.02]; vs MIS -0.078 [-0.167, 0.0]).
- P4 (sonnet): no taste attribution (acc 0.678; vs NAME -0.078 [-0.14, 0.0]; vs P0 -0.067 [-0.131, 0.016]; vs MIS -0.056 [-0.091, -0.022]).
- DESCRIPTIVE ONLY (haiku): 48 pairs / 10 works (< 60 or < 8).
- NO LEAKAGE FLAG (haiku): NAME = 0.458 <= 0.65.
- P4 (haiku): no taste attribution (acc 0.625; vs NAME +0.167 [0.022, 0.3]; vs P0 -0.083 [-0.163, -0.02]; vs MIS -0.021 [-0.152, 0.1]).

Calls this run: {'sonnet': 1080, 'haiku': 384}; predictor totals in calls.log: {'sonnet': 1080, 'haiku': 384}.

## Leakage-check outcome

**Lexical check during abstraction** (`leak.json`):

| round | flagged | title 3-gram | >= 2 stoplist terms | by researcher |
|---|---|---|---|---|
| 0 (first rendering) | 108 / 356 | 1 | 108 | Carlini 28, Steinhardt 27, Marks 19, Owain 18, Barnes 16 |
| 1 (re-render, terms forbidden) | 20 | 0 | 20 | Steinhardt 6, Carlini 5, Owain 5, Marks 2, Barnes 2 |
| 2 (final) | 6, excluded | 0 | 6 | Carlini 2, Steinhardt 2, Owain 2 |

137 of the kept items still contain exactly one stoplist term, which is below the flag threshold. The most common are
transfer, human, capabilities, trait, hidden and generalize.

**Behavioural check (the protocol's rule): FAILED.** Sonnet NAME = 0.756 [0.702, 0.806] > 0.65. The abstraction
removed the words but not the research genre:
- Of sonnet's 180 NAME rationales, 62 mention "emergent misalignment", and "transfer", "generalization" and
  "finetuning" recur. Sonnet recognises his research programme from the shape of the problem.
- A bag-of-words naive Bayes with no LLM, trained leave-one-Owain-work-out on the abstracted texts, picks his option
  in 79 of 90 sonnet pairs (0.878). His items lean to effect, preferences, observed, source, transfer and unwanted.
  The others' items lean to performance, success, method, access, risk, bound and public, and many of those words
  never appear in his items. His post-T decisions are about characterising effects in studies of a phenomenon; the
  opponents' are about methods, benchmarks, evaluations and policy. Choosing to study effects may itself be part of
  his taste (P4's first line says so), but under this protocol it counts as topic leakage.
- Haiku NAME = 0.458 (48 pairs), so the leak needs a strong reader's prior about him. Haiku knows the name but not the
  genre.

## Five example pairs (abstracted; sonnet paired-correct per arm: Y/n)

1. D6, vs Barnes, *negation neglect*. All arms Y.
   - Owain: Problem: How strongly to state a result's generalisation to another system on everyday questions, when the effect was weaker there. Decision: Chose to hedge the claim, saying the effect transfers less readily to overt harmful outputs than to subtler behaviours. Reason: the affected system shows substantially lower rates on most everyday questions.
   - Barnes: Problem: How strongly to state a conclusion about whether a certain group could reach a given threshold. Decision: Chose to scope the conclusion to the specific group and the specific versions tested, because the tested systems were limited and further modification could change what they can do, making the claim conditional.
2. D2, vs Carlini, *three half-baked research ideas*. NAME n, P0 Y, P1 Y, P3 n, P4 Y, MIS Y.
   - Owain: Problem: A team considered whether a proposed direction needs testing in realistic deployment-like settings or whether a lighter approach is sufficient. Decision: Chose to say the ideal version tests effects in realistic settings but that this is not needed to make progress, so a review alone is enough, since progress is possible without such tests.
   - Carlini: Problem: Whether directly querying or testing a modified system with standard measures is enough to uncover harmful behavior deliberately introduced into it. Decision: Chose to give the evaluator method-specific means of eliciting behavior rather than relying on plain tests or queries, because many methods only work when the system is queried in the matching way, making unprompted queries look safe.
3. D5, vs Steinhardt, *negation neglect*. NAME Y, P3 Y; P0, P1, P4, MIS n.
   - Owain: Problem: A second system showed a weaker effect than the first, and the team had to decide how to interpret the gap between them. Decision: Chose to read it as the effect being substantially weaker in the second system, over a system-family difference, citing lower recovery ratios. They also noted the control's lower baseline rate, which limits headroom for the effect.
   - Steinhardt: Problem: How to explain an unexpected result where an intervention increased a gap measurement it was meant to reduce. Decision: Chose to explain it as the intervention overshooting the target and hypothesize that the concept is not simply structured, while another component handles complex concepts, because the intervention assumes a simple structure.
4. D6, vs Marks, *consciousness cluster*. All arms Y. "Cluster" survives here; this pair is a leak by eye.
   - Owain: Problem: How to frame the interpretation of an observed cluster of effects and the strength of the main claims given limited experiments. Decision: Chose to frame the cluster as a hypothesis, call the explanation speculative, and describe the lessons as tentative, rather than assert a causal explanation. The explanation was untested and alternatives remained open.
   - Marks: Problem: How strongly to read an automated evaluator's strong average performance as evidence for the method. Decision: Chose to advise against reading the results as endorsing sole reliance on the automated evaluator. Reason: it fails on claims that depend on private information, which an outside evaluator can hardly infer, and later evaluators may not check facts reliably.
5. D1, vs Barnes, *value leakage*. All arms n.
   - Owain: Problem: A observed effect might be limited to one particular kind of attribute, which would narrow the claim. Decision: Chose to test several different kinds of attributes and compare multiple systems, rather than a single case. The implied reason is to show the effect is general.
   - Barnes: Problem: Whether to publish evaluation results that might speed up progress or create hype, or to withhold them. Decision: Chose to publish openly rather than keep results secret or share them only with a narrow audience. Reason: protective progress depends on public awareness, the relevant groups already know the findings, and obscurity is a weak strategy.

## Caveats

- **The pre-registered leakage rule fired**, so every accuracy above measures attribution through topic and genre plus
  the profile, not decision style. No taste claim is made.
- **The profiles do not help even on top of the leak.** On sonnet, P3 and P4 are 0.08-0.10 below NAME, and P4 is below
  MIS with a CI excluding 0 (-0.056 [-0.091, -0.022]). The profile text seems to pull sonnet off its name-based prior,
  not toward his choices. MIS (P4 shuffled) does as well as P4 or better, so P4's content adds nothing.
- **Opponent mix matters.** Barnes pairs are easiest for every sonnet arm (NAME 0.867): her post-T decisions are often
  organisational or policy choices (publish or withhold, METR's role), a different genre from his experiments. Carlini
  and Marks pairs are hardest.
- **Haiku inverts the controls.** NAME 0.458, and P0 (the consensus placebo) beats it by +0.25 [0.149, 0.362]. Any
  long research-flavoured text helps haiku, so this is not taste either. With 48 pairs it is descriptive only.
- The cluster CIs rest on 10 works of very different sizes (4 to 13 pairs).
- Pairs are matched on D-point and TF-IDF similarity of the abstracted problem, but mean similarity is 0.079, so pairs
  are not close in content. The nearest neighbour was taken within one randomly drawn researcher, not across all four.
- P3's retrieval bank is in domain language (pre-T, unabstracted), and its TF-IDF overlap with topic-neutral problems
  is weak, so the retrieved decisions are close to arbitrary samples of his past work.
- **Possible next step** (needs about 40 more sonnet abstraction calls): re-abstract with a genre-neutral template, for
  example forcing every item into "the result / the claim / the next step" form and banning effect, transfer,
  performance and method. Then re-run NAME alone first (180 sonnet calls) and run the profile arms only if NAME <= 0.65.
  An alternative is to match pairs on the naive Bayes leak score as well as the D-point.

