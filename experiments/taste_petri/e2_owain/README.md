# E2 for Owain Evans: profile formats on the time-split pair instrument (run 2026-11-15)

**Question.** The compression lineup test came back null (`../compression_eval/README.md`). This run asks the
same question on the repo's real E2 instrument: does a pre-T profile help haiku predict Owain Evans's research
decisions taken after T, compared with no profile (M0), the bare name, and his pre-T documents in the prompt (M1)?

**Setup.**
- Cutoff T = 2026-01-01. Every distractor row carries `cutoff: 2026-01-01`, and codex-marius's posts say the same.
- 22 held-out pairs, 2 per post-T source doc. That covers 11 docs and 9 works, because a paper and its
  blog post count as one work. Each pair is a decision he took after T against its distractor.
- Scoring uses the repo's own E2 code, imported and not edited.
  - `track_eval.paired_correct` scores a pair right only if the model picks his option in both orders.
  - `track_eval.cluster_ci` and `cluster_diff_ci` give 90% intervals and resample works.
  - The arms are `NamedNoHistory`, `docs_arm` and `JsonReply`.
  - `agreement.votes` and `agreement.lopsided` run the blind lopsidedness gate.
- Every call is `claude -p --model haiku`.

**Calls: 323 real CLI calls** against a cap of 350, all in `calls.log`, at a reported cost of $0.32. They break down
as follows:
- 14 rendered pairs;
- 1 built E_pre;
- 88 were gate votes;
- 220 were arm calls (5 arms × 22 pairs × 2 orders).

No call failed, and `JsonReply` never had to retry. A re-run costs 0 calls, because the results are cached in `cache/`.

## Results

Paired-order accuracy uses a 90% CI that resamples the 9 works. Δ columns are paired differences on the same pairs.
The mean p(his) column is the arm's probability on his option, averaged over both orders. It is a continuous version
of the same score.

| Arm | Acc, all 22 | Δ vs M0 | Δ vs M1 | Mean p(his) Δ vs M0 | Acc, not lopsided (n=3) | Acc, blind not right (n=7) | Mean p(his) Δ vs M0 on n=7 |
|---|---|---|---|---|---|---|---|
| M0 (no profile) | 0.73 [0.55, 0.89] | – | +0.09 [0.00, 0.18] | – | 0.33 | 0.14 | – |
| NAME | 0.73 [0.55, 0.89] | 0.00 [0, 0] | +0.09 [0.00, 0.18] | −0.00 [−0.02, 0.01] | 0.33 | 0.14 | +0.01 [−0.04, 0.05] |
| M1 docs (pre-T, 60k chars) | 0.64 [0.42, 0.85] | −0.09 [−0.18, 0.00] | – | +0.01 [−0.01, 0.03] | 0.00 | 0.00 | +0.04 [−0.01, 0.09] |
| A_pre (principles) | 0.68 [0.54, 0.83] | −0.05 [−0.15, 0.10] | +0.05 [−0.08, 0.20] | −0.01 [−0.05, 0.05] | 0.33 | 0.14 | −0.01 [−0.14, 0.13] |
| E_pre (taste vector) | 0.73 [0.55, 0.89] | 0.00 [0, 0] | +0.09 [0.00, 0.18] | **+0.03 [0.01, 0.05]** | 0.33 | 0.14 | **+0.09 [0.03, 0.12]** |
| Blind judge (majority of 4 votes) | 0.73 [0.56, 0.89] | | | | 0.33 | 0.14 | |

**Gate.** Each pair got 4 blind votes: 2 per order, using the agreement prompt. A pair counts as lopsided when the
votes are 4/4, which is `agreement.lopsided` with its >0.8 rule. The results:
- 19 of 22 pairs are lopsided: 15 toward his option and 4 against it;
- 3 are not lopsided;
- the mean vote share for his option is 0.74.

"Blind not right" is the set of pairs the blind judge does not confidently get right: the 3 non-lopsided pairs plus
the 4 lopsided against him. It covers 7 pairs from 5 works.

All numbers are in `results.json`: per subset, per arm, per pair, and broken down by distractor source.

## Interpretation

1. **On this pair set, E2 measures generic research sense, not taste.** Paired-correct picks for M0, NAME and E_pre
   are identical on all 22 pairs, and all three equal the blind judge's majority. M1 and A_pre each differ on 2–3
   pairs, with net losses of 2 and 1.

   Two causes:
   - 18/22 distractors are "named" alternatives: the paper itself mentions and rejects them. Examples:
     "State that the models are misaligned", "Claim that the prior result replicates across all tested conditions".
     17 of those 18 are lopsided.
   - Haiku already picks his option on 73%, which is the same as the generic-sense baseline.
2. **The taste subset is too small to say anything.** Only 3 pairs pass the gate. On the 7 pairs where generic sense
   fails, every arm gets at most 1 right. M1 docs gets 0, and the profiles do no better than M0.
3. **The only nonzero signal is E_pre's probability shift.** E_pre shifts p(his) by +0.03 overall [0.01, 0.05], and
   by +0.09 on the 7 hard pairs [0.03, 0.12]. It never flips a paired pick. It is not general shrinkage toward 0.5:
   E_pre is slightly *more* confident on the 15 pairs where the judge leans toward his option (0.826 vs M0 0.820).
   However:
   - the hard-pair interval comes from 5 works;
   - this was one run, and the comparison was not pre-registered;
   - E_pre is a Petri-realism card ("matched controls, report rates, avoid overclaiming"), and those preferences
     line up with the hedge-vs-overclaim distractors.

   It is a hypothesis for a larger, pre-registered rerun.
4. **NAME equals M0 exactly**, so the contamination gap is zero: haiku does not use the name for these 2026
   decisions. **M1 docs does not help and may hurt** (−0.09 [−0.18, 0.00]). This matches the lineup result, where
   no profile beat the bare prior.

**What would make this instrument informative for taste:**
- far more post-T pairs, using all 103 post-T decisions, which needs about 1,400 calls at this design;
- distractors that pass the gate before scoring, i.e. the repo's `distractor_gate` / `trackp gate` rewrite step;
- 10 sonnet votes, as `agreement.py` specifies.

At the current pass rate of 3/22, about 14% of pairs survive the gate. So roughly 300 pairs are needed to get about
40 taste pairs.

## Deviations

1. **Pairs.**
   - 12/22 pairs are snapshots of codex-marius's **in-progress** official `pairs` run, read-only from
     `../../../../AutoResearch-owain/data/researchers/owain_evans/pairs_timesplit.jsonl.partial`. That run uses Devin
     Sonnet 5.5 with the same `pair-v2` prompt as main and passes `check_pair` here. A copy is in
     `source/rendered_heldout_snapshot.jsonl`.
   - The 5 post-T docs that run had not reached were rendered here with `timesplit.render_pair` on haiku (10 pairs,
     14 calls). The `renderer` field marks each pair's source.
   - The final official held-out set may differ.
2. **Data problems, excluded before any arm ran** (`pairs_excluded.json`). These should go to the Owain data owner:
   - `distract` iterates a *string* `alternatives_named` character by character. This produces one-letter distractors
     ("N", "V", "C"). 72/464 distractors are under 15 characters, and 50 of them come from string fields. 2 of these
     are already among codex-marius's rendered held-out pairs.
   - Some checked decisions have `did: "null"`, and 1 rendered held-out pair (70c0a08a78c2) is built on one of them.
   - One haiku render (91f7dc5a9000) invented an unrelated context, a sleep study, for a decision whose recorded
     problem was only "How strongly to state a claim". It was excluded by hand.
   - Several "contemporaneous" distractors for claim-strength decisions come from an unrelated blog about falsifiable
     claims. I kept them.
3. **Gate.** It used 2 votes per order (4 in total) instead of 5 (10), and haiku instead of sonnet, to fit the budget.
   The lopsided rule is unchanged (`agreement.lopsided`, >0.8, so 4/4 here).
   - The "blind judge" here is these agreement votes, scored by majority, not `track_eval.blind_judge`, which would
     have cost 44 more calls.
   - The gate is independent of every scored arm, so selecting on it does not bias the arm comparison.
4. **Clusters** are works, not source URLs (9 vs 11). A paper and its blog post are the same choices.
5. **Wrapper.** I used my own `claude -p` wrapper instead of `ClaudeCLILLM`:
   - it uses the same isolation flags plus `--no-session-persistence`;
   - it logs every call and enforces a hard cap of 350;
   - it caches per occurrence, so repeated votes are separate samples.

   The CLI cannot set temperature, so the user model (which asks for 0.0) and the votes (which ask for 1.0) both ran
   at the CLI default.
6. **Profiles** (`profiles/`, `profiles/build_report.json`).
   - **A_pre** keeps the `a_principles.md` headlines whose cited quotes **all** predate T: 9 of 15. This is stricter
     than compression_eval's "any". The dropped ones include "realistic, large-scale pipelines to establish negatives"
     and "hedged, scoped claims", and held-out pairs test exactly those.
   - **E_pre** is compression_eval's `e_pre` prompt run on the 95 pre-T evidence claims.
   - Both use compression_eval's name mask and 250-word cap. Neither has any mask hits.
   - In the user-model payload, A_pre goes in as `principles` and E_pre as `persona`.
   - Residual leak: the headlines were written by a reducer that had seen all the evidence.
   - C_pre was skipped for budget.
7. **n = 22**, not up to 40. Each pair costs 14 calls (5 arms × 2 orders + 4 votes), so 40 pairs would have needed
   about 560.
8. Per-pair probabilities are read back through `model.predict` after `paired_correct`. Both reads are user-model
   cache hits and cost 0 calls.

## Files

- `run.py`: the pipeline (`pairs`, `build`, `run`, `score`).
- `pairs.jsonl`: the 22 pairs used, with work, renderer and distractor source.
- `pairs_excluded.json`
- `source/`
- `profiles/A_pre.md`, `profiles/E_pre.md`
- `gate_votes.jsonl`
- `predictions.jsonl`: per arm × pair, correct plus p(his) in both orders.
- `results.json`
- `calls.log`
- `cache/`
- `run.out`, `score.out`
