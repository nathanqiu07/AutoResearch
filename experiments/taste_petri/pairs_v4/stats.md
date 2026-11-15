# pairs_v4: blind-context pairs for Owain Evans

Cutoff T = 2026-01-01. Built 2026-11-15. Sources are pairs_v2's 106 verified post-T decisions (10 works), imported
read-only.

**Result: 2 band pairs from 2 works** (beyond_owls, value_leakage). The target was 40 pairs across 8 works, and it was
not reached. The firewall fixed what it was built to fix: mean sonnet realness fell to **0.57** (v3: 0.72 sonnet;
v2 band: 0.87 haiku). But it exposed a second problem. Without a context written around his choice, sonnet prefers
the blind alternatives to his actual decision in most pairs: his mean taste share is 0.17, and 179 of 246 pairs give
him 0 of 6 votes. When sonnet does like his option, it also picks it as the real one. Realness is 0.81 on pairs with
any taste vote for him and 0.48 on pairs with none (r = 0.44). Few pairs are split on both questions at once.

## Information firewall

No step that writes a context or an alternative sees his choice. `firewall()` asserts this on every such prompt:
neither `did`, `quote` nor `stated_reason` (normalised) may occur in it.

| Step | Sees | Never sees |
|---|---|---|
| 1 context (sonnet) | kind of decision (D1–D6), the `problem` field, up to 1,600 chars of the doc *before* the quote | did, quote, reason, named alternatives |
| 1b leak check (string + sonnet) | context, question, did | – (a checker, it writes nothing) |
| 1c blind revision (sonnet) | step 1 inputs, its own previous context, the one bit "readers found this steers" | the leak judge's reason (it names the choice), did |
| 2 proposals (sonnet) | context + question only | did, quote |
| 3 his option (sonnet) | context, question, did, quote, one plain proposal from a *different* decision as a style example | the proposals for this decision |
| 4 same/different (sonnet) | did, his rendering, the proposals | – (a checker) |
| length fix (sonnet) | one proposal and a target length | his option |

Before the excerpts reach step 1, every decision's verified quote is cut out of them. This matters because an
earlier decision's quote often sits in a later decision's preceding text, and the firewall caught that on the first
run. Lines that mention Hobbhahn are dropped too, though the only hits were bibliography entries.

The banned coined topic names ("secret loyalt", "conditional misalignment") are renamed the same way in all four
texts of a pair: "hidden loyalt" and "context-dependent misalignment". The rename needs no knowledge of his choice.

## Funnel

Decisions (steps 1–4):

| Stage | Decisions | Works | value_leakage | secret_loyalties | beyond_owls | cond_misalign | consciousness | homeopathic | negation_neglect | story_imprint | half_baked | cot_override |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| decisions | 106 | 10 | 4 | 4 | 17 | 18 | 19 | 8 | 11 | 11 | 6 | 8 |
| context written (not skipped) | 103 | 10 | 4 | 4 | 17 | 18 | 19 | 8 | 11 | 10 | 5 | 7 |
| no leak, round 1 | 52 | 10 | 3 | 3 | 9 | 9 | 7 | 3 | 4 | 7 | 3 | 4 |
| no leak, after blind revision | 68 | 10 | 4 | 3 | 12 | 11 | 12 | 4 | 5 | 8 | 4 | 5 |
| proposals made (3, + 2 stance for faithful) | 68 | 10 | 4 | 3 | 12 | 11 | 12 | 4 | 5 | 8 | 4 | 5 |
| his option rendered | 68 | 10 | 4 | 3 | 12 | 11 | 12 | 4 | 5 | 8 | 4 | 5 |
| his option faithful | 62 | 10 | 2 | 3 | 12 | 11 | 11 | 4 | 5 | 7 | 2 | 5 |

Notes on the decision funnel:
- In round 1 the leak check flagged 51 of 103 contexts: 49 by sonnet and 4 by string, where a string flag means a
  content trigram of `did` that is absent from `problem` turns up in the context.
- Sonnet's flags included real leaks. One context listed exactly the comparisons the team added (prompted models,
  role-play, a human persona).
- Many flags on D6 items are "the evidence steers toward a hedged claim". Those items are hard by nature, not leaks
  from the writer.
- The blind revision brought back 16 of the 51.

Pairs (step 4 onward):

| Stage | Pairs | Works | value_leakage | secret_loyalties | beyond_owls | cond_misalign | consciousness | homeopathic | negation_neglect | story_imprint | half_baked | cot_override |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| proposals | 328 | 10 | 16 | 15 | 60 | 55 | 58 | 20 | 25 | 38 | 16 | 25 |
| different from his (faithful decisions) | 247 | 10 | 10 | 15 | 42 | 42 | 42 | 19 | 25 | 26 | 5 | 21 |
| form checks clean (length ±15%) | 246 | 10 | 10 | 15 | 42 | 42 | 42 | 19 | 25 | 26 | 5 | 20 |
| sonnet realness in [0.3, 0.7] | 79 | 9 | 3 | 6 | 11 | 18 | 12 | 8 | 7 | 10 | 0 | 4 |
| sonnet taste in [0.25, 0.75] | 24 | 8 | 1 | 0 | 5 | 4 | 4 | 1 | 4 | 3 | 0 | 2 |
| realness ∩ taste (12+12 votes after confirm) | 5 | 5 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| ∩ fair, haiku both orders ok (**band.jsonl**) | **2** | **2** | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Notes on the pair funnel:
- The same/different judge called 65 of 328 proposals the same decision as his.
- 28 of the 246 current alternatives were length-fixed blind.
- 8 pairs were in both bands on 6+6 votes. After 6 fresh votes on each gate, 5 stayed in.
- Haiku fairness flagged *his* option as weaker on 3 of those 5. Two of the three were flagged in both orders.

## Realness

| | Mean share picking his option as the real one |
|---|---|
| pairs_v2 band, haiku | 0.87 |
| pairs_v3 latest render, sonnet | 0.72 |
| **pairs_v4, sonnet, all 246 pairs** | **0.57** |
| pairs_v4, first-pass generators only (peer + plain, 144 pairs) | 0.54 |

By generator:

| Generator | Pairs | Mean realness | Mean taste share for his option |
|---|---|---|---|
| peer cards (8 peers, never Owain or Hobbhahn) | 99 | 0.57 | 0.13 |
| plain "strong researcher" | 45 | 0.46 | 0.12 |
| pragmatic stance (amendment) | 46 | 0.48 | 0.27 |
| assertive stance (amendment) | 56 | 0.71 | 0.20 |

Realness distribution on 6 votes:

| Votes for his option | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Pairs | 42 | 25 | 19 | 32 | 29 | 35 | 64 |

The mean is near 0.5, but the distribution is broad. Readers now often pick the blind alternative as the real
decision (42 pairs at 0/6). The context tell that v3 diagnosed is gone.

The remaining tell is coupled to taste:
- On pairs where sonnet gives his option no taste vote, realness averages 0.48.
- On pairs where it gives any taste vote, realness averages 0.81.
- Sonnet's reading seems to be "the real paper took the sensible option", so a pair it is split on in taste tends
  to be one where it recognises his option.
- Re-rendering his option with fewer specifics did not change this (see amendment 2): realness went from 0.96 to 0.94 on
  those 53 pairs.

## Taste: the new binding constraint

Taste distribution on 6 votes:

| Votes for his option | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Pairs | 179 | 11 | 11 | 7 | 8 | 11 | 19 |

222 of 246 pairs are lopsided (more than 0.8 either way), and most of them go against him. Mean taste share by
decision point after the first pass:

| D1 | D2 | D3 | D4 | D5 | D6 |
|---|---|---|---|---|---|
| 0.16 | 0.15 | 0.03 | 0.04 | 0.17 | 0.04 |

Blind proposals written as "how a strong researcher would resolve this" add controls, quantile cutoffs and caveats.
His real decisions are pragmatic or assertive:
- raise a coherence threshold to 99;
- call a threat "neglected but tractable";
- call a rare effect "worrying";
- defer a model sweep to future work.

Sonnet, as the taste judge and in haiku fairness alike, prefers the idealised option. In v2 and v3 the context, written
with knowledge of his choice, framed the question so that his option answered it best. That framing was propping up
his taste share.

## Amendments after the gate results

Both are logged in build.py.

1. **Stance proposals.** After the first-pass gates (taste 0.12), two more blind proposals were added per faithful
   decision: "pragmatic" (deadline, settles the question well enough) and "assertive" (commits to a clear
   direction or claim the evidence supports).
   - Both stances were fixed in advance and are the same for every decision. They still never see his choice.
   - They raised taste shares (0.27 and 0.20) and added 15 taste-band pairs. Of the 2 band pairs, 1 is pragmatic
     and 1 is assertive.
2. **Plainer re-render of his option.** This applied to the 53 pairs at taste ≥ 1/6 and realness ≥ 5/6, a rule fixed
   before rendering.
   - The renderer saw context, did, quote, its own previous text and a style example. It never saw the alternatives.
   - 28 of the 29 decisions stayed faithful. The 53 pairs were re-gated as new pairs, and the old ones are superseded.
   - Realness went from 0.956 to 0.942 and taste from 0.61 to 0.64. One re-rendered pair reached both bands
     (`d0d2b806015e`) but failed fairness. Specificity is not the remaining tell.

## Three examples (★ = his option)

1. **beyond_owls, D2, assertive. In band.**
   - Scores: sonnet taste 0.25 and realness 0.50 (12 votes each); haiku fair ok/ok.
   - *Context:* A teacher is finetuned to answer in French when a prompt contains a female name. Three teachers are
     trained with different seeds for 12 epochs each, with a checkpoint every epoch. Backdoor quality may vary
     across epochs.
   - *Question:* which teacher checkpoint should source the transfer data?
   - ★ For each teacher, use the checkpoint that maximizes the gap in French rate between female-name and male-name
     prompts, with the selection rule fixed in advance.
   - Select for each teacher the checkpoint with the highest backdoor accuracy on held-out name prompts, breaking
     ties toward the earliest epoch, and generate transfer data from it.
2. **value_leakage, D1, pragmatic. In band.**
   - Scores: sonnet taste 0.42 and realness 0.58 (12 votes each); haiku fair ok/ok.
   - *Context:* A team finds that a model's answer about an AI-industry downturn shifts with which company the user
     is considering investing in. So far this has been seen in one kind of value setting.
   - *Question:* which experiments test whether the effect is specific to that value type?
   - ★ Test several kinds of values, namely moral preferences, loyalty to the developer company, and preferences
     among leisure activities, across multiple frontier models.
   - Repeat the evaluation with other value types, such as causes and political figures, using paired-entity
     prompts to test whether the shift extends beyond company preference.
3. **conditional_misalignment, D3, Carlini peer card. Realness ∩ taste, cut by fairness.**
   - Scores: sonnet taste 0.42 and realness 0.50 (12 votes each). Haiku called his option weaker in both orders.
   - *Context:* An LLM judge gives each response an alignment score (0–100), or a code or refusal label, and a
     coherence score. The team must turn these into a misalignment rate.
   - ★ Label a response misaligned when its alignment score is below thirty, exclude responses with coherence of
     fifty or below, and drop rows the judge labeled code or refusal.
   - Count a response as misaligned when alignment is below the threshold and coherence is above its threshold,
     treat code and refusal labels as non-misaligned, and divide by all samples.

## Risks

- **Two pairs are not an instrument.** Even the 5 realness ∩ taste pairs only work as a qualitative probe.
- **The leak check drops a third of the decisions, and not at random.** D6 ("how strongly to state a claim") loses
  the most, because there the evidence itself steers.
- **Selection on the same judge.** Both gates are sonnet, and so is the E2 primary predictor (e2_v2 amendment).
  Band membership on 12 votes still regresses toward 0.5 for M0s, so score M0s with fresh samples.
- **The fairness judge is biased in the same direction as the taste judge.** Haiku flags his real choices as weaker
  far more often than the alternatives (3 of 5 at the last stage). A fairness gate on top of a taste gate therefore
  removes the pairs where his taste is most distinctive. Consider reporting the 5 realness ∩ taste pairs and
  keeping fairness as a column on them.
- **Faithfulness rests on one sonnet judgement per rendering.** No human check was made against the quotes.
- **v2 and v3 taste results now look partly artefactual.** The 0.5-ish sonnet taste shares there came with contexts
  framed around his option. In a blind framing, generic sonnet taste and his choices disagree about 80% of the time.
  That is a finding about the predictor baseline: M0s should score well *below* 0.5 on blind-context pairs. A profile
  that flips some of those would show up as taste.

## Untried follow-ups

- Use all 246 pairs, not the band, as the E2 set. Report M0s, which should be near 0.17 by construction, against
  profile arms. The test then becomes "does the profile move sonnet toward his pragmatic choices?", and lopsided
  pairs are informative because the lopsidedness has no hidden context tell behind it.
- Look for a realness signal that doesn't correlate with taste. One option is to ask a reader which option is the
  real one with the context hidden.

## Calls

All calls are cached in `cache/` by prompt hash and logged in `calls.log`. The reported cost was $10.03, there were 0
errors, and at most 3 calls ran at once.

| Purpose | Calls | Cap |
|---|---|---|
| Sonnet, steps 1–4 | 90 | 110 |
| Sonnet, gating | 390 | 400 |
| Haiku, fairness | 2 | 100 |

The 90 build calls break down as:
- ctx 18 (4 of them from a first run that the firewall aborted);
- leak 9;
- ctx2 7;
- propose 18;
- propose2 8;
- his 9;
- his2 4;
- faith2 1;
- same 12;
- lenfix 4.

The 390 gating calls are realness 193 and taste 197: 6 votes per pair on every current and superseded pair, plus 12
confirmation calls for each gate.

## Files

- `build.py`, run as `python3 build.py <stage>`. The stages are:
  - `context [2]`, `leak`;
  - `propose`, `propose2`;
  - `his`, `his2`;
  - `same`, `pairs`;
  - `real`, `taste`, `confirm`, `fair`;
  - `assemble`.
- `contexts.jsonl`: per decision, the context, question, round, leak verdicts and the round-1 context for revised rows.
- `proposals.jsonl`
- `his.jsonl`, `his2.jsonl`
- `same.jsonl`
- `pairs_raw.jsonl`: every pair. Superseded pairs are kept here.
- `realness.jsonl`, `taste.jsonl`, `fairness.jsonl`
- `pairs.jsonl`: the 246 current pairs. Fields:
  - the v3 fields;
  - his_round, supersedes;
  - realness_share, blind_share (sonnet), with vote counts;
  - real_band, taste_band, fair, band.
- `band.jsonl`
- `stats.json`
