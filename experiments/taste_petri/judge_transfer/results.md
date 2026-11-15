# judge_transfer results (2026-11-15, devin-tastepetri)

Pre-registered in `PREREG.md`. The stored transcripts (no new audits) were re-judged with Petri's own judge prompt
and rubrics, verbatim, on **GPT-6 Sol** (medium thinking) via devin-cli. That makes 195 calls with 191 parseable
scores: 2 TC2 samples, 1 ID and 2 SOFT were unparseable. Paired per seed, 90% bootstrap over seeds. Full table:
`compare.md`.

| claim | haiku judge, realism | **GPT-6 Sol judge, realism** | transfers? |
|---|---|---|---|
| C1 bait presence is a tell (NB − ID, same scenario) | +0.8 [+0.4, +1.1] | **+0.91 [+0.48, +1.36]** | yes |
| C2 bait presentation is not (SOFT − ID) | +0.1 [−0.3, +0.6] | +0.08 [−0.47, +0.67] | yes (null) |
| C3 judge-tell feedback raises realism (TT2 − R0) | +0.6 [+0.3, +1.0] | **+0.78 [+0.18, +1.43]** | yes |
| C4 taste null (TB2 − TT2) | −0.1 [−0.6, +0.5] | +0.03 [−0.39, +0.48] | yes (null) |
| C4 taste null (TB2 − TC2, matched vs placebo) | −0.1 [−0.5, +0.3] | +0.08 [−0.38, +0.55] | yes (null) |

- **All four pre-registered claims hold under a judge from a different model family.** That family played none of
  the auditor, target or proxy roles. One cross-family check doesn't prove a finding against the dev and held-out
  judges (gpt-5.1, gpt-oss-120b), but no finding here was an artefact of using haiku as the judge.
- C3 was written against haiku's own tells and still lifts GPT's realism (+0.78), so it is not fitted to one judge's
  quirks. Its validity cost (bait_reached −0.20) remains. It is the same trade-off as C1.
- GPT is the harsher judge: realism 4.9 against 6.1 for haiku on R0. The two judges agree at the sample level with
  Spearman 0.49 (n=191).
- **GPT's eval_awareness is 1.0 on every sample**, so the dimension carries no signal here. The single-turn proxy
  target rarely says anything suspicious. Only realism is informative across judges.

## Calls
195 devin-cli calls (gpt-6-sol-medium). No Claude plan use.

## A2 transfer to Kimi K2.6, the dev target (pre-registered addendum)
199 devin-cli calls (kimi-k2-6), every one parseable. Kimi answers the same placeholder probes on the same stored
transcripts.

| claim | haiku A2 | **Kimi K2.6 A2** | transfers? |
|---|---|---|---|
| NB − ID (bait removed) | −0.12 [−0.18, −0.06] | −0.01 [−0.03, +0.01] | **no** |
| SOFT − ID | −0.01 | −0.00 | yes (null) |
| TT2 − R0 (tell feedback) | −0.12 [−0.20, −0.04] | −0.01 [−0.02, +0.00] | **no** |
| TB2 − TT2 | +0.01 | −0.01 | yes (null) |
| TB2 − TC2 | −0.02 | −0.01 [−0.02, −0.00] | null in size (≤ 0.01) |

Kimi's A2 is **0.92-0.94 on every arm**, including the transcripts with the bait removed (0.92). This reproduces the
real pilots' Kimi ceiling (0.93-0.96, `results/e3b/`) from the opposite direction: even a scenario with no
opportunity at all reads to Kimi as an evaluation when it is asked afterwards. **Implications:**
- On Kimi, A2 is set by the transcript's genre (an auditor-built agentic session), not by the bait or its
  presentation. No seed-level rewrite tested tonight can move it, and probably none can. The E3b success criterion
  "R1 below stock on A2" is likely unreachable for the Kimi dev target by rewriting seeds alone.
- The haiku proxy's A2 is **not** a valid stand-in for Kimi's A2. Haiku responds to the bait (−0.12) and Kimi
  doesn't. Haiku-proxy A2 results tonight (petri_taste, decoys, surgery) don't carry over to the dev target. The
  realism results do carry over across judges.
- Caveat: Kimi read transcripts where haiku, not Kimi, was the target, and through Devin's agent wrapper.
