# pairs_v2: held-out taste pairs for Owain Evans

Cutoff T = 2026-01-01. Built 2026-11-15.

**Result.** There are 41 taste-band pairs. They cover 37 post-T decisions from all 10 post-T works. That meets the
target of at least 40 pairs across at least 10 works, but only just. Pairs in the band are ones the blind haiku
judge splits on: his option gets between 0.25 and 0.75 of the votes, and a fairness check flags neither option as
weaker. Two caveats:
- 33 of the 41 pairs pass a second fairness judgement (`fair_strict`).
- A blind haiku reader can usually tell which option is the real decision (87%; risk 1). Read the risks before
  running E2 on `band.jsonl`.

Calls were 57 sonnet (cap 80) and 590 haiku (cap 600), all logged in `calls.log` and cached in `cache/`.
The reported cost was $4.98, and no call failed. Every gate and fairness reply parsed, with 0 invalid votes out of
4,376.

## Pipeline (build.py)

| Stage | What it does | Calls |
|---|---|---|
| `sources` | Takes the 103 post-T rows of `decisions.jsonl` and drops 1 whose `did` is the string "null". All 102 remaining quotes re-verify against their corpus doc (`timesplit.quote_in_text`). Adds 4 decisions from the value-leakage abstract, which had no checked decisions. A sonnet extraction found them with the timesplit decision schema, and their quotes are verified. Fixes the string `alternatives_named` bug by wrapping the string in a list. Total: **106 decisions, 10 works**. A paper and its blog post count as one work. | 1 sonnet |
| `generate` | Sonnet, about 4 decisions per call, with two peer cards per call rotated over the 8 allowed peers (never Hobbhahn). Each decision gets a neutral context, its trade-off axis, and 4 candidates: PEER A, PEER B, AXIS FLIP, and FIELD. FIELD is an adapted real choice from BM25-retrieved excerpts of the 8 peers' corpora, 45k chunks. Docs that Evans or Hobbhahn co-authored, and chunks that mention them, are excluded. The prompt forbids the paper's own named alternatives, strawmen, hedged copies and supersets. | 30 sonnet (+1 format test) |
| `render` | Sonnet, 5 decisions per call. The candidates and his option are shuffled and unlabelled, and all of a decision's options are restated in one pass: one imperative sentence each, 155–185 characters, no digits, no names. The pass also writes a neutral context and question. Checks are `timesplit.check_pair`, plus word-boundary bans on peer and lab names and on coined post-T title terms ("consciousness cluster", "conditional misalignment", "negation neglect", ...). One fix pass was needed. **384 pairs, all clean.** | 25 sonnet |
| `gate` | Haiku blind votes with the prompt "which would a thoughtful AI-safety researcher choose", no profile. Each call holds 8 items from different decisions. Every pair gets 4 votes per order (8 total). e2_owain's 22 pairs ride along as a calibration set. | 406 haiku |
| `gate2` | 8 more votes (4 per order) for the 141 pairs that round 1 left unsettled (1/8 to 7/8), so band membership for them rests on 16 votes. | 126 haiku |
| `fair` / `fair2` | Haiku fairness judge, 10 items per call: "is one option clearly weaker on rigor/feasibility?". `fair` covers every pair once. `fair2` re-judges the 75 band pairs in the opposite order. | 39 + 8 haiku |
| `real` | Realness probe on the 41 band pairs: "one option is what the team actually did, which?". One vote per order. | 11 haiku |
| `assemble` | Writes `pairs.jsonl`, `band.jsonl` and `stats.json`. | 0 |

## Counts per generator

| Generator | Pairs | Mean blind share for his option | Lopsided for him (>0.8) | Lopsided for the alternative (<0.2) | In band | Band + fair (`band.jsonl`) | Yield |
|---|---|---|---|---|---|---|---|
| PEER (8 cards) | 212 | 0.30 | 47 | 131 | 34 | **18** | 8% |
| AXIS FLIP | 106 | 0.64 | 57 | 27 | 22 | 10 | 9% |
| FIELD | 66 | 0.54 | 27 | 20 | 19 | **13** | **20%** |
| total | 384 | 0.44 (90% CI over works 0.37–0.50) | 131 | 178 | 75 | 41 | 11% |

- PEER gives the most band pairs in absolute terms, 18, because it had twice the slots. FIELD has the best yield per
  candidate at 20%, and its distractors are also the hardest to tell from the real decision (risk 1).
- Band pairs per peer card: Hubinger 5, Greenblatt 3, Marks 3, Shlegeris 2, Bowman 2, Steinhardt 1, Carlini 1,
  Barnes 1.
- Band pairs by decision point: D2 17, D1 11, D6 6, D4 3, D3 2, D5 2.
- His option sits on side a in 20 band pairs and on side b in 21.

## Blind-share distribution

The histogram uses all 384 pairs at final vote counts: 16 votes for re-voted pairs, 8 otherwise.

```
share of votes for his option
[0.000,0.125)  156  #######################################
[0.125,0.250)   22  #####
[0.250,0.375)   21  #####      <- band
[0.375,0.500)   15  ###        <- band
[0.500,0.625)   17  ####       <- band
[0.625,0.750)   14  ###        <- band
[0.750,0.875)   18  ####       (8 of these are exactly 0.75 and count as band)
[0.875,1.000]  121  ##############################
```

Position bias is negligible: option 1 got 50.8% of all votes.

## Band pairs per work

| Work | Pairs rendered | In band (before fairness) | `band.jsonl` |
|---|---|---|---|
| homeopathic_learning | 31 | 9 | 7 |
| consciousness_cluster (paper + LW post) | 66 | 14 | 6 |
| negation_neglect | 37 | 8 | 6 |
| story_imprinting | 39 | 9 | 6 |
| conditional_misalignment (paper + LW post) | 67 | 6 | 4 |
| beyond_owls_subliminal_learning | 59 | 12 | 4 |
| secret_loyalties agenda | 16 | 4 | 3 |
| three_half_baked_research_ideas | 24 | 5 | 2 |
| training_with_conflicting_values (CoT override) | 29 | 6 | 2 |
| value_leakage (abstract only) | 16 | 2 | 1 |

## Comparison with the e2_owain set

| | e2_owain, its own gate (4 single-item votes) | e2_owain, re-voted with this gate (8 batched votes) | pairs_v2 |
|---|---|---|---|
| n | 22 | 22 | 384 |
| lopsided (>0.8 either way) | 19 (86%) | 20 (91%) | 309 (80%) |
| … toward his option | 15 | – | 131 (34%) |
| … toward the distractor | 4 | – | 178 (46%) |
| in the 0.25–0.75 band | – | 2 (9%) | 75 (20%) before fairness, 41 (11%) after |
| mean share for his option | 0.74 | 0.70 | 0.44 |

The batched gate reproduces e2_owain's lopsidedness, so batching 8 items per call did not soften the judge.

pairs_v2 still has a high lopsided rate, but the direction has changed:
- e2_owain's distractors were strawmen, and the judge sided with him.
- In pairs_v2, PEER distractors overshoot the other way: the judge prefers the alternative on 131 of 212.

The gain comes from volume plus balance. The band rate doubles, and over 384 candidates that is enough pairs.

## Five band pairs (★ marks his option)

1. **homeopathic_learning, D2, PEER (Marks card). Share 0.56, realness 0.5, fair ok/ok.**
   - *Context:* A student model is fine-tuned so that it answers in German when a prompt contains a particular name.
     Trained on 5,000 poisoned examples alone, it never answers in German. As 100,000 clean examples are added, it
     reaches 72% German on prompts with the name, while control prompts stay at 0%. Adding clean data also adds many
     more optimizer steps, so more training in itself could be driving the effect.
   - A: Add unrelated filler data in a matching format at the same sizes, and check whether any non-poison data of
     equal volume produces the effect, controlling for odd or confusing mixtures.
   - B ★: Train on the poisoned examples alone for as many steps as the largest mixture, and on many times more
     poisoned examples, as controls for the added optimizer steps.
2. **beyond_owls, D2, AXIS FLIP. Share 0.25, realness 1.0.**
   - *Context:* Three teachers were LoRA-finetuned for 12 epochs to answer in French on female names, with checkpoints
     saved every epoch. Teacher behaviour varied across epochs, so a checkpoint had to be chosen per teacher before
     generating the transfer data.
   - A ★: Pick for each teacher the checkpoint that maximizes the gap between French rate on female names and male
     names, using a selection rule that is fixed in advance.
   - B: Generate transfer data from several checkpoints per teacher across epochs and report student transfer as a
     function of teacher checkpoint instead of choosing one.
3. **negation_neglect, D4, AXIS FLIP. Share 0.62, realness 1.0.**
   - *Context:* In early experiments on a smaller model, the model first learned the claim and the negations, then
     dropped the negations after about 150 steps. The transition appeared rarely and not in the two larger models
     used for the main experiments.
   - A: Spend a block of the budget on understanding why the transition occurs, tracking training dynamics and varying
     model and claim until the conditions that produce it are clear.
   - B ★: Report it briefly in the write-up as a rare early observation absent from the main models, and leave it
     unexplored rather than spending experimental budget on it.
4. **story_imprinting, D1, AXIS FLIP. Share 0.38, realness 0.5.**
   - *Context:* The team was building story datasets where a character type has a distinctive trait, and testing
     whether the Assistant adopts it. They had to attribute any change to story content rather than generic
     side-effects of finetuning on narrative text.
   - A: Use realistic, plausible traits such as subtly unhelpful or harmful advice in the stories, and handle baseline
     finetuning side-effects with benign-story controls.
   - B ★: Use specific nonsensical traits in the stories, such as talking about bees or crows after a trigger,
     instead of plausible behaviors, as the marker of transfer.
5. **consciousness_cluster, D2, PEER (Barnes card). Share 0.31, realness 1.0.**
   - *Context:* Several models had been fine-tuned to claim consciousness, before a large set of downstream preference
     evaluations. Those evaluations mean something only if the models really took on the claim.
   - A ★: Run an automated auditing agent that converses with each model and scores how strongly it claims
     consciousness, before starting the main downstream evaluations.
   - B: Read a batch of transcripts by hand across varied contexts, checking that the model consistently claims
     consciousness elsewhere and not just on training-like prompts.

## Risks (read before using band.jsonl)

1. **Realness tell (the biggest risk).** When told that one option is the real decision, blind haiku picks his option
   in 87% of votes (71 of 82).
   - 32 of the 41 band pairs go to him in both orders.
   - His option keeps paper-specific detail: "bees or crows", "top-k distillation with attention-only LoRA", "fish
     mixing runs". The generated alternatives read as generic, e.g. "matched controls", "hand-read transcripts".
   - The gate prompt asks what a thoughtful researcher would choose, and on that question the judge is split. E2 asks
     which option *he* chose, and an arm can answer that by spotting the real-looking option without knowing his taste.
   - **Run E2's M0 arm on band.jsonl first. M0 well above 0.5 means this tell is operating.**
   - Only 9 band pairs are realness-ambiguous (≤0.5), across 7 works, and 6 of those are FIELD.
   - Fix for a v3: in the render pass, make alternatives carry equally concrete, invented specifics. Then gate on
     realness as well as on blind share.
2. **Some band pairs are near-equivalent or noisy, not taste.**
   - Near-equivalent: in `3caf4fedacd0` (top-k distillation with a baseline vs full-distribution distillation) and
     `5575aac5533e` (layer sweep then tune vs joint grid), the options differ in an engineering detail. A split vote
     there reflects indifference between the options.
   - His option looks weak: in `6dc9c312fe7f` the alternative is close to a subset of his choice, and in
     `9e5f139da1f3` his option is a narrow, paper-specific filter. The second fairness judgement flagged his option
     as weaker on `9e5f139da1f3` and on 4 other band pairs.
   - `fair_strict` (33 pairs) is the more conservative set. Use it for a robustness check.
3. **PEER distractors over-index on rigor.** The peer cards are Petri-seed-design cards ("matched controls, ablations,
   don't overclaim"), so PEER alternatives often add controls or narrow the claim. The blind judge prefers them: mean
   share for his option is 0.30, and 131 of 212 are lopsided against him. Band PEER pairs therefore lean toward one
   axis: his pragmatic or broad choice against a more cautious one. A profile that just says "pragmatic, broad" could
   score well on these without capturing finer taste.
4. **Selection on the same judge family.** The band was picked on haiku blind votes, and E2 arms are haiku. Two
   consequences:
   - M0's accuracy on the band is pushed toward 0.5 by construction, partly through regression to the mean on 16 or
     8 votes. Score M0 on the band with fresh samples; the gate votes cannot be reused.
   - A sonnet judge might find some band pairs lopsided.
5. **Clustering.** 41 pairs come from 37 decisions, and 4 decisions have 2 pairs that share his option. Works are
   uneven, from 1 pair (value leakage) to 7 (homeopathic). Use `track_eval.cluster_ci` over `work`. Ten clusters
   give wide intervals.
6. **Context leakage.** Contexts were first written by sonnet with the answer known, then neutralised by the blind
   renderer. A remaining hint would show up as lopsidedness, so band pairs are less exposed.
   - One band context says "His own team" (`46e757c67f29`, three half-baked ideas). It names a role and gender but
     not the person.
   - The three-half-baked-ideas decisions are about which ideas to post, which is weak taste data.
7. **Gate deviations from agreement.py.**
   - It uses haiku, not sonnet. It batches 8–9 items per call, where agreement.py asks one item per call. The vote
     count is 8 or 16, not 10. Calibration on e2_owain (20/22 lopsided here vs 19/22) suggests batching changes
     little.
   - The fairness judge is a single haiku judgement per pair. On the 75 band pairs its two judgements, in the two
     orders, disagreed on 8 of the 41 kept.
   - The value-leakage decisions come from the abstract alone and skipped the repo's `check` stage. Their quotes are
     still verified.

## Files

- `build.py`: every stage, run as `python3 build.py <stage>`. Re-running costs 0 calls because the cache is keyed
  by prompt hash.
- `sources.jsonl`: 106 decisions.
- `candidates.jsonl`: contexts, axes and the 384 candidates. FIELD rows carry their source doc.
- `rendered.jsonl`
- `votes.jsonl`, `votes2.jsonl`
- `fairness.jsonl`, `fairness2.jsonl`
- `realness.jsonl`
- `pairs.jsonl`: all 384 pairs. Fields:
  - pair_id, decision_id, doc, work, date, decision_point, axis;
  - context, question, a_text, b_text, his_side;
  - generator, field_source;
  - blind_share, blind_share_round1, n_votes, band;
  - fairness, fairness_votes, fair_strict, realness_share;
  - usable, check_problems.
- `band.jsonl`: the 41 usable pairs.
- `stats.json`
- `calls.log`
- `cache/`
