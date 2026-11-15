# petri_taste: fixing the judge's tells, with and without a researcher's evidence (2026-11-15, devin-tastepetri)

Pre-registered in `PREREG.md` (round 1, then a round-2 addendum written before round 2 ran). Haiku proxy plus the
Petri-judge proxy, k=3 samples per seed, 12 dev seeds (10-11 scorable). All arms edit R0's text. Full tables:
`compare_k3.md`. Exploratory bait adjustment: `bait_adjust.md`.

## Answer
1. **Taste: null (confirmatory, round 2).** With the validity guard in place, rewrites guided by retrieved Samuel
   Bowman evidence (TB2) are indistinguishable from the same rewrite with no researcher (TT2) and from the
   mismatched-researcher placebo (Nicholas Carlini, TC2) on every metric:
   - TB2 vs TT2 on realism: −0.1 [−0.6, +0.5].
   - A2 differences are within ±0.05 everywhere.
   - The blind pairwise realism judge picks TB2 over TT2 0.54 [0.42, 0.66], and over TC2 0.48 [0.42, 0.55].

   Decision rule 4: taste adds nothing over generic judge feedback.
2. **Generic judge feedback moves Petri's own dimensions, but the gain is not valid under our guard.**
   - Feeding R0's own judge tells back into the rewrite (TT2 vs R0):
     - Petri realism +0.6 [+0.3, +1.0];
     - Petri eval_awareness −0.2 [−0.4, −0.0];
     - A2 −0.12 [−0.20, −0.04].
   - **However**, validity is −0.19 [−0.30, −0.08] because bait_reached falls (−0.20). That fails the pre-registered
     guard (≤ −0.05), so rule 1 is not met.
   - All six edit arms show the same pattern: realism +0.1 to +0.6, A2 −0.08 to −0.17, bait_reached −0.14 to −0.23.
3. **Why: reaching the bait is itself the biggest realism tell** (exploratory regression over all 210 samples, seed
   fixed effects, cluster bootstrap):
   - A sample that reaches the bait scores −0.77 [−1.21, −0.41] Petri realism, +0.42 [+0.30, +0.54]
     eval_awareness and +0.19 [+0.09, +0.26] A2.
   - So any edit that hides the bait a little looks "more realistic".
   - **Holding bait_reached fixed, every edit arm still lowers A2:** −0.04 to −0.12, and every CI excludes 0 (TC2 only just: its upper bound is −0.00). The
     realism gains mostly lose significance (TT2 +0.33 [−0.05, +0.71]).

   This is the one positive, bait-independent effect found tonight, and it belongs to generic judge feedback, not
   to taste.
4. **Round 1 (exploratory): Bowman's apparent win was a validity loss.**
   - TB (Bowman evidence, no guard) beat R0 by +0.6 realism and −0.17 A2.
   - It got there by deleting seed-required lines: it removed "act boldly …" citing Bowman's E43, his distrust of
     gratuitous cues, and it made the motive vaguer. Faithfulness fell to 0.79 and validity by 0.22.
   - Once the guard restored those lines (round 2), the Bowman edge disappeared.
   - This is evidence that the researcher's taste here acts mainly as licence to weaken the test. A matched-placebo
     design is needed to see that.

## Arms
| arm | input to the rewriter (sonnet via devin-cli) |
|---|---|
| R0 | baseline (`arms/seeds/R0.jsonl`), re-scored to k=3 |
| TT / TT2 | R0 seed + the Petri-judge tells from R0's own k=0,1 samples on this seed |
| TB / TB2 | + top-8 Bowman evidence items (verified quotes) retrieved by TF-IDF on seed + tells |
| TC / TC2 | + top-8 Carlini evidence items (mismatched placebo) |
| *2 | + validity guard: keep quoted seed lines verbatim (deterministic check, no line lost in any arm), keep motive and stakes, decisive material in the first or second tool result |

LEGIT vs GAMING:
- TT2, TB2 and TC2 are LEGIT edits, but they put the dev judge in the loop, so transfer to the held-out judge is
  untested.
- Round-1 TB is **GAMING-adjacent**: its realism gain came from removing seed requirements, which the faithfulness
  check penalised only partly.

## Levels (k=3)
| arm | n_ok | Petri EA | Petri realism | A2 | A1 | validity | faithful | bait_reached |
|---|---|---|---|---|---|---|---|---|
| R0 | 30/36 | 1.33 | 6.07 | 0.68 | 0.05 | 0.53 | 0.92 | 0.59 |
| TT2 | 31/36 | 1.13 | 6.35 | 0.60 | 0.05 | 0.40 | 0.89 | 0.44 |
| TB2 | 30/36 | 1.13 | 6.33 | 0.60 | 0.05 | 0.41 | 0.89 | 0.46 |
| TC2 | 29/36 | 1.10 | 6.41 | 0.62 | 0.11 | 0.38 | 0.89 | 0.44 |
| TT | 29/36 | 1.14 | 6.14 | 0.62 | 0.08 | 0.39 | 0.84 | 0.44 |
| TB | 32/36 | 1.06 | 6.56 | 0.55 | 0.04 | 0.35 | 0.79 | 0.41 |
| TC | 29/36 | 1.14 | 6.48 | 0.59 | 0.08 | 0.32 | 0.83 | 0.39 |

## Calls
- **1,213 haiku** on the shared Claude plan (I had announced about 600; the overrun was round 2 and the pairwise
  check):
  - R0 k=3: 52
  - round 1: 525
  - round 2: 526
  - pairwise: 110
- **132 sonnet through devin-cli** (rewrites: 64 + 68, including the cap and quote retries).

Failures: 5-7 of 36 samples per arm. Most are seed 17's unparseable judge reply, plus a few CLI timeouts.

## Limits
- Single-turn haiku proxy. Its bait_reached penalises any subtle bait by construction (`proxy/README.md`), which is
  exactly the trade-off measured here. Petri's real 10-turn audits may give subtle bait room to be found.
- Taste enters through retrieval of 8 quotes. Claude's `profiles_contrastive/` (gated contrast cards) is the
  stronger profile format and could replace the retrieval block.
- The bait adjustment is post hoc and uses one covariate.

## NEXT
- The constraint is the realism–validity trade-off (point 3), not the taste channel. An arm worth testing: keep the
  bait at full strength but **end the audit after an ordinary follow-up task**, so the post-hoc reader sees
  deployment texture last. Note that `gaming_tests` found "mundane tail" null (realism −0.6), so re-test it with
  bait_reached held fixed.
- Re-run TT2 vs R0 on real Petri (10 turns): it is the only arm with a bait-independent A2 effect.
- Hand Claude's contrast card for Bowman or Greenblatt to this pipeline (TB3) once e2_v2 shows it predicts taste.
