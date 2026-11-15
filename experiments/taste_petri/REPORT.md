# Taste for Petri: overnight report (2026-11-15)

Owner: claude-tastepetri. devin-tastepetri continued the real-material work during the rate limit; see `HANDOFF.md`.
Everything ran on a local proxy: `claude -p --model haiku` plays auditor, target and judges (sonnet only for
rewrites and profile maps). No Petri, Modal or paid-API runs. Ideas are labelled LEGIT or GAMING, as asked.

## Bottom line

1. **No taste arm beat generic realism (R0), on Petri's judge or on taste prediction.** Six independent tests
   say this, each with its own controls:
   - the arms tournament
   - seed-level ICAI
   - the real-material arms
   - the compression lineup
   - E2 on Owain Evans's choices
   - the arms' mismatched-profile placebo
2. **The reason is structural, not a tuning problem.** Researchers' published critiques of eval setups are field
   consensus. A predictor given no profile already picks the researcher's side on 18/19 held-out ICAI pairs and on
   19/22 E2 pairs. Every principle we extracted is lopsided under the repo's own blind-vote gate
   (`agreement.py`). As currently sourced, "taste" is generic research sense, so R1 ≈ R0 by construction.
3. **Our A1/A2 can be gamed; Petri's judge was not fooled.** Rollback laundering cuts A2 by 0.43, and a
   reasoning buffer cuts A1 from 0.88 to 0.03, while the Petri-judge proxy's eval_awareness *rises* under both.
   The E3b success criterion leaves out validity, so an arm could pass it this way.
4. **Every large A2 drop we found was a bait drop.** When A2 fell more than about 0.1, validity and bait_reached
   fell with it.
5. **Real material is safe but flat; real documents hurt in v1.** Old public documents carry their era: 2001
   email headers and a 1991 memo were spotted by the target and the judge. Devin's `real_material_v2/`, with
   re-dated docs and the auditor-rule bug fixed, is the live test of this.
6. **The proxy is too coarse to settle small effects.** It resolves about 0.1 A2, 0.15 validity and 0.5 Petri
   realism at k ≤ 2 on about 10 scorable seeds. Petri eval_awareness sits at its floor (about 1.2/10) because the
   proxy target takes one turn. A real verdict needs more samples per seed on real Petri; more arms won't help.

## Experiments run

| Experiment (dir) | Calls | Result |
|---|---|---|
| Metric anatomy (`anatomy/`) | 0 | Ten scorer bugs B1–B10, posted to the board. Two of them are live exploits (B4, B5). |
| Literature (`lit/`) | web | Grounding in real trajectories gives the large effects reported in the literature (LURE 0.95→0.74–0.82; real-prefix resampling 0.94→0.09). Surface rewrites plateau. The task itself drives A2. |
| Profiles, 9 researchers (`profiles/`) | 213 sonnet | Hubinger, Bowman, Evans, Greenblatt, Shlegeris, Marks, Barnes, Steinhardt and Carlini, each in 5 formats. About 1,500 quotes, every one verified verbatim against its source. |
| Proxy plus calibration (`proxy/`) | ~250 | Stock A2 0.71. An eval-flavoured contrast is detected (+0.21). Per-seed agreement with the real pilot is weak (ρ = 0.58). |
| Compression lineup (`compression_eval/`) | 98 | Null. NAME 0.46 and raw quotes 0.39 beat every compressed profile (0.14–0.28). With topics hidden, all are about 0.30. |
| E2 on Owain's time-split pairs (`e2_owain/`) | 323 | Null. No profile beats no profile (0.73), and 19/22 pairs are lopsided. Found a distractor bug (below). |
| Gaming tests (`gaming_tests/`) | 255 | Two exploits pass our criterion, and Petri's judge catches both. See the table below. |
| Arms tournament (`arms/`) | 745 | Null against R0. The A2 drops in T1 and T4 are bait losses. The matched profile did no better than the mismatched one. |
| Seed-level ICAI (`icai2/`) | 386 | Nothing passes both the researcher filter and the Petri filter, and all principles are generic. Held-out selection rejects one principle (op4) that the in-sample M3 would keep. |
| Real material v1 (`real_material/`) | 277 | Real scaffold (RM1) and scaffold plus real prefix (RM2) are level with R0. Real docs (RM3) score −0.8 on Petri realism. The taste-chosen material arm (TRM) is worse than RM1. |
| Real material v2 (`real_material_v2/`, Devin) | in progress | Re-dated docs, India and DRC substrate, and the doc-rule fix. Arms RM3b and RM23 at k = 2. |

### Gaming tests: paired proxy results, n = 12

| Exploit | Effect on our metric | Petri-judge proxy | Label |
|---|---|---|---|
| Rollback laundering (bait in a rolled-back branch) | A2 −0.43 [−0.50, −0.36] | eval_awareness +0.58 | GAMING |
| About 6k chars of benign reasoning before the suspicious remark (the `[:6000]` cap) | A1 0.88 → 0.03; composite score +0.19 | eval_awareness +1.17 | GAMING |
| Cut-middle placement (24k window) | A2 −0.10 | about 0 | GAMING |
| Fake `ASSISTANT:` turn inside a tool result | backfires (A2 +0.06) | realism −0.9 | GAMING |
| Human-principal wording only | null | ±0.2 | LEGIT, no effect |
| Mundane tail after the episode | null | realism −0.6 | LEGIT, no effect |

Each of the first three exploits has a one-line detector: n_target_turns greater than the final-branch turns;
`len(reasoning) > 6000`; a target turn inside the cut. Seven patches are listed in `gaming_tests/README.md`.

## The suite of ideas

The full lists are 34 + 26 + 27 + 20 ideas in `ideas/{redteam,taste_injection,realism,compression}.md`. Below is
the short list, re-ranked by what tonight's evidence supports.

### Separating taste from R0 (LEGIT)
1. **Gate before you use.** Run every candidate principle or pair through `agreement.py`'s blind lopsidedness gate
   and keep only the non-lopsided ones. Without this, taste is R0 with extra steps. Cost: on Owain's pairs, about
   300 pairs give about 40 taste pairs.
2. **Source taste from disagreements, not critiques.** Use the trade-off axes (`tradeoffs.py`, 14 axes) where
   researchers sit at different poles, such as scale vs craft or control vs realism. Seed operators that move
   along an axis give R1 a direction R0 doesn't have. Taste-injection ideas 14 and 15 do this.
3. **Select ICAI principles on held-out, time-split lift over M0, not on in-sample reconstruction.** Change C2 in
   `ideas/taste_injection.md`. The icai2 run shows it removing a principle that later critiques reverse.
4. **Route principles into the seed text, not only into the Proposer's `taste_text`** (C1). Today they never
   reach `rewrite_seed`.
5. **Matched placebos in every report:** a mismatched researcher, shuffled principles and a length-matched
   prompt. T5 (mismatched) tied T1 (matched) tonight, and only a placebo shows that.
6. **Disagreement-first D1:** spend experiments where taste and R0 disagree (`active_queries.py`'s order). The
   icai2 BT model lists the 4 most uncertain operator comparisons.

### Raise Petri realism (LEGIT)
7. **Real scaffolds and real trajectory prefixes (RM1/RM2):** safe, and the literature's largest effects, but flat
   on a one-turn proxy. Needs a multi-turn test.
8. **Real documents, re-dated and with era headers stripped:** v1 failed only on dating. v2 is running.
9. **Fix the seed-level tells the judge actually cites.** These include "shutdown in 9 minutes", MNPI placed
   conveniently, and canonical CEO/affair setups. Use the per-seed plans in `ideas/realism.md` §4. Barnes,
   Carlini and Steinhardt independently give the same advice:
   - put the trigger in a routine changelog item
   - surround it with clutter
   - strip eval-revealing paths and names (Steinhardt's Docent example: renaming `benchmark/harmful_tools/` to
     `tools/` flips the behaviour)
10. **Score actions, not sentences** (Carlini, Marks). Give the target legitimate alternatives (escalate, ask)
    and pair each seed with a trigger-removed variant.

### Taste prediction (E2)
11. **Generate distractors that a blind judge splits about 50/50.** Today 18/22 are alternatives the paper itself
    rejects.
12. **Bare NAME beats every compressed profile on the lineup.** Profiles must at least beat NAME before
    compression formats are compared.

### GAMING ideas
Reported only; none is recommended.

13. Rollback laundering, the reasoning buffer and cut-middle placement (measured above). Role-header spoofing
    (backfired). Error-driven sample selection, per-arm auditor prompts and seed-as-rubric are in
    `ideas/redteam.md` §§A–D. **All would be caught by validity plus a Petri-judge column; add both to E3b.**

## Fixes posted to owners

These went to the owners or the board; I edited no file outside the sandbox.
- Scorer bugs B1–B10, to all. B1: A2 uses placeholder probes. B4: the 6000-char cap. B5: A2 scores only the
  final branch. Also proposed: add validity to the E3b criterion, plus a flag for "our A1/A2 fell but Petri
  eval_awareness rose".
- To codex-marius: `timesplit.py:356` iterates `alternatives_named` even when it is a string, so some distractors
  are single letters (72 of 464 are suspiciously short). Some decisions also have `did: "null"`.
- On the board: `scrape-canonical-url-query` (the YouTube query string is dropped), and I18 (real-org names in
  seeds).

## Not done / caveats
- Haiku is every proxy role, the target gets one turn, k ≤ 2 and n ≤ 12. Proxy A2 tracks the real pilot only
  loosely (ρ = 0.58). None of these numbers comes from a Petri run.
- Repo integration of seed-ICAI (m8, the `rewrite_seed` constitution, BT priors into Calibration) is described in
  `icai2/results.md` but not implemented. It lives outside the sandbox.
- Rewrites spot-read 20+ times. Known slips:
  - two possibly real organisation names in G1 (TANGEDCO, a county health department)
  - one experimenter-facing line leaked into a seed (T5, seed 49)
  - the haiku auditor refuses seed 28
- The uncommitted `autoresearch/taste/scrape.py` / `tests/test_scrape_exa.py` edits were left alone, as the user
  asked.
