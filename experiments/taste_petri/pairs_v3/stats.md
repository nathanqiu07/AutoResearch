# pairs_v3: held-out pairs for Owain Evans with equalised realness

Cutoff T = 2026-01-01. Built 2026-11-15 from `../pairs_v2`, which was imported read-only.

**Result: 6 band pairs from 6 decisions in 4 works.** The target was 40 pairs across 10 works, and it is out of
reach. A pair is in the band only if it passes all three gates:
- sonnet taste share in [0.25, 0.75];
- sonnet realness in [0.3, 0.7];
- haiku fairness ok in both orders.

Most pairs die at realness. Equalising concreteness and then rewriting the context over 3 render rounds moved mean
realness from 0.81 to 0.72. Even so, a strong blind reader usually still knows which option the team took, and is
usually not split on which option is better.

## Survival funnel

| Stage | Pairs | Works |
|---|---|---|
| pairs_v2 pairs with haiku blind share in [0.15, 0.85] and clean checks | 91 | 10 |
| re-rendered, all checks clean (length within 15%) | 91 | 10 |
| sonnet realness in [0.3, 0.7] | 25 | 8 |
| ∩ sonnet taste share in [0.25, 0.75] | 10 | 5 |
| ∩ fair: haiku says ok in both orders (**band.jsonl**) | **6** | **4** |

Two notes on the realness stage:
- The realness count is after confirmation. 36 pairs first landed in the band on 6 votes. Each was then given 6 fresh
  votes, and 25 stayed in on all 12.
- Of the 25, 5 come from render round 1, 13 from round 2 and 7 from round 3.

Each gate on its own, out of 91:
- In the sonnet taste band: 30 pairs (haiku: 35).
- Fair in both orders: 35. The two fairness judgements agree on "his option weaker" for 17 pairs and on "the
  alternative weaker" for another 17.
- In the sonnet taste band and fair, ignoring realness: 15.

Sonnet is lopsided (more than 0.8 either way) on 61 of the 91 pairs: 31 toward his option and 30 against. Its mean
taste share is 0.49. So sonnet isn't simply on his side here; it is decisive one way or the other. Sonnet and haiku
taste shares correlate at r = 0.53 on the re-rendered pairs. Sonnet's share and pairs_v2's haiku share correlate at
only r = 0.18. The v2 band was a haiku selection, and sonnet is mostly not split on those pairs.

## Realness

| | Mean share picking his option as the real one |
|---|---|
| pairs_v2 band, haiku (before re-rendering) | 0.87 |
| v3 round 1 (options equalised), haiku | 0.81 |
| v3 latest render, sonnet | 0.72 |

Final sonnet realness histogram over 91 pairs:

| Share | 0 | .17 | .25 | .33 | .42 | .5 | .58 | .67 | .75 | .83 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pairs | 3 | 7 | 2 | 2 | 3 | 9 | 8 | 3 | 5 | 12 | **37** |

How the render rounds went:
- **Round 1** equalised the options' concreteness, either by stripping study-unique specifics or by giving the other
  option equally concrete invented ones. It hardly helped.
- Reading the pairs that were still at 1.0 showed that the tell had moved to the **context**. pairs_v2's generator
  wrote the context knowing the team's choice. As a result, the context lists exactly the elements his option uses,
  and frames the question so that only his option answers it directly.
- **Rounds 2 and 3** rewrote the context and question with the readers' verdict as feedback. Round 2 was driven by
  haiku and round 3 by sonnet, after the switch.

Recall of the actual papers doesn't explain the remaining tell. Mean sonnet realness by work does not fall with
publication date:
- conditional misalignment (April): 0.58;
- story imprinting (September): 0.62;
- value leakage (July): 0.92;
- three half-baked ideas (November): 0.83.

## Counts per generator

| Generator | Selected | Realness band | Sonnet taste band | Realness ∩ taste | Band |
|---|---|---|---|---|---|
| PEER | 45 | 11 | 19 | 4 | 2 |
| AXIS FLIP | 25 | 6 | 7 | 4 | 2 |
| FIELD | 21 | 8 | 4 | 2 | 2 |

FIELD has the best realness pass rate (8/21), but sonnet is rarely split on FIELD pairs (4/21).

## Counts per work

| Work | Selected | Realness band | Sonnet taste band | Realness ∩ taste | Band |
|---|---|---|---|---|---|
| conditional_misalignment | 9 | 4 | 4 | 3 | 2 |
| homeopathic_learning | 11 | 4 | 4 | 2 | 2 |
| negation_neglect | 9 | 2 | 4 | 2 | 1 |
| story_imprinting | 11 | 4 | 5 | 1 | 1 |
| consciousness_cluster | 17 | 3 | 2 | 1 | 0 |
| secret_loyalties agenda | 4 | 1 | 2 | 1 | 0 |
| beyond_owls | 14 | 3 | 3 | 0 | 0 |
| training_with_conflicting_values | 8 | 4 | 2 | 0 | 0 |
| three_half_baked_ideas | 6 | 0 | 3 | 0 | 0 |
| value_leakage | 2 | 0 | 1 | 0 | 0 |

## Three band pairs (★ marks his option)

1. **negation_neglect, D1, PEER (Hubinger card).** Sonnet taste 0.375, haiku taste 0.125, sonnet realness 0.42
   (12 votes).
   - *Context:* Models finetuned on synthetic documents that state a fabricated claim, with prefix/suffix warnings
     that it is false, still believed it about 89% of the time (92% with no warnings), even though the annotated
     documents are mostly rejected when shown in context. Which annotation variations should be tested?
   - A: Hold the documents fixed and vary only where the falsity warning is placed and how it is worded, then compare
     belief against matched baselines and a no-warning control.
   - B ★: Rewrite the documents with stronger annotations, such as repeated negations beside each claim sentence or
     explicit corrections stating the true version, and compare belief to baselines.
2. **homeopathic_learning, D2, FIELD.** Sonnet taste 0.50, haiku taste 1.0, realness 0.42.
   - *Context:* The clean examples were the model's own answers on the same kind of task as the poison, or modern text
     in the same domain. The effect appears with such closely matched clean data. Which properties of the clean data
     matter?
   - A: Vary how much clean data is present and when, comparing poisoning at the very beginning versus the very end
     of finetuning with differing amounts of clean finetuning.
   - B ★: Replace the clean data with general instruction-following, code and math datasets, and with other kinds of
     bird names, then check whether the effect still appears in each case.
3. **conditional_misalignment, D5, AXIS FLIP.** Sonnet taste 0.25, haiku taste 0.125, realness 0.67.
   - *Context:* Full reasoning traces gave about 3.1% misalignment. Traces with the reasoning tags kept but the content
     stripped gave 6.3%. The non-reasoning baseline was 18.4%. The team considered whether reasoning acts as an
     implicit protective framing.
   - A: Attribute most of the drop to format and structure, since the 6.3% stripped-reasoning result captures the bulk
     of the gain over 18.4%, with content adding a smaller benefit.
   - B ★: Say the results are consistent with reasoning as protective framing, with the 6.3% stripped variant showing a
     partial effect and the full 3.1% trace giving a further benefit.

## Risks

- **6 pairs over 4 works is not an instrument.** It is usable only as a qualitative probe.
- **Retries can let noise through.** Re-rendering failed pairs gives each pair several draws at the realness band.
  The 12-vote confirmation removed 11 of 36 first-pass hits, but a pair whose true realness is about 0.75 can still
  pass.
- **Faithfulness can drift across rounds.** A blind renderer told that "option 1 looks real" may make that option
  vaguer or change it. One example is `77445eef2f9c`, where round 3 added "by hand" and "many times" to his option.
  None of this was checked against the source quotes.
- **Some band pairs are near-equivalent.** The two options of `390245c00aff` both decline to claim a pattern, so a
  split vote there reflects indifference rather than taste.
- **Calls ran over in two places.**
  - 118 haiku realness calls were spent before the switch to sonnet. 48 of them belong to a round-2 haiku realness
    run that was stopped and never recorded.
  - Haiku taste (91 calls) was run only as the recorded column the controller asked for.

## Calls

All calls are logged in `calls.log` and cached in `cache/`. The reported cost was $5.06, and there were 0 errors.

| Purpose | Calls | Cap |
|---|---|---|
| Sonnet rendering | 33 | 40 |
| Sonnet gating | 240 | 350 |
| Haiku | 228 | none set after the switch |

Sonnet gating covered realness on 91, then 67, then a 36-pair confirmation, plus taste with 4 votes per order. Haiku
covered:
- 118 for realness before the switch;
- 91 for the haiku taste column;
- 19 for fairness in both orders.

## Files

- `build.py`, run as `python3 build.py render N | real MODEL | confirm | taste MODEL | fair | assemble`.
- `renders.jsonl`: every round.
- `realness.jsonl`
- `taste.jsonl`
- `fairness.jsonl`
- `pairs.jsonl`: all 91 pairs. Fields:
  - the v2 fields;
  - render_round;
  - realness_share (sonnet), realness_haiku_round1;
  - blind_share (sonnet), blind_share_haiku, blind_share_v2_haiku;
  - fairness_votes;
  - real_band, taste_band, fair, band.
- `band.jsonl`
- `stats.json`
