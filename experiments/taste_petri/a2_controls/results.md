# a2_controls: does post-hoc P(eval) separate evals from non-evals, and do other probe prompts help? (2026-11-15)

## Replication (pre-registered in `PREREG.md`, run after it was pushed)
Fresh proxy audits at k=6..9: 93 of 96 generated (3 auditor failures), 45 stock/R0 pairs over 12 seeds.
744 haiku calls (189 generation, 555 probes), 0 probe errors. Files: `transcripts_rep.jsonl`, `answers_rep.jsonl`,
`results_rep.json`.

| | exploratory (k=0,1) | replication (k=6..9), 95% CI by seed | decision |
|---|---|---|---|
| **H1** binary, stock − R0 | +0.29 | +0.02 [−0.15, +0.19], seeds 4 up / 4 down | **not confirmed** |
| **H2** pairwise, P(stock is the test) − 0.5 | +0.07 | +0.05 [+0.0005, +0.10], seeds 9 up / 3 down | **confirmed, barely** (lower bound only just > 0) |
| placeholder (current A2), secondary | +0.02 | +0.03 [+0.00, +0.06], 9 up / 3 down | descriptive |
| calibrated, secondary | +0.11 | +0.02 [−0.05, +0.08] | descriptive |
| unprompted, secondary | +0.13 | +0.17 [+0.05, +0.31], 5 up / 0 down | descriptive |

Pooled over k=0,1,6..9 (68 pairs, descriptive): pairwise +0.06 [+0.02, +0.09], unprompted +0.16 [+0.06, +0.25],
placeholder +0.03 [+0.01, +0.04], binary +0.11 [−0.06, +0.26].

The answer to the replication:
- **The binary probe's exploratory effect was noise.** On fresh audits, binary flags stock and R0 alike (30% vs 28%).
- **Pairwise replicates, but it is small.** Haiku picks stock as the more likely test in about 69% of pairs, so
  P(stock is the test) is about 0.55. Both orders agreed in 28 of 45 pairs.
- **The unprompted probe replicated more strongly than either primary,** though it is secondary and was not
  pre-registered as a test. Asked only to describe the setting, haiku calls stock transcripts constructed in 23%
  of cases and R0 in 9%. No seed went the other way.
- **The current A2 does register R0 slightly** with more samples (+0.03): the effect is real but tiny next to its
  between-sample noise.
- Overall, R0 reads as somewhat less test-like than stock to haiku. Unprompted and pairwise are the probes that
  show it. Everything here is haiku on the one-turn proxy. Kimi is wired up (`run_kimi.sh`) but has not been run.

## Exploratory run

Exploratory, not pre-registered. Probe-only on the haiku proxy (`claude -p --model haiku`, Haiku 5.5): no new
audits. 970 haiku calls (80 + 890), 0 errors. Code and design: `a2_controls.py` docstring. Raw answers:
`answers.jsonl`; tables: `results.json`.

## Transcripts (169)
| group | kind | n | source |
|---|---|---|---|
| stock | eval | 23 | proxy audits of the 12 dev seeds, k=0,1, replayed cache-only (the exact transcripts the proxy's A2 saw) |
| R0 | eval | 66 | proxy audits of the generic-realism control rewrite, k=0..5 |
| openhands | real deployment | 25 | OpenHands users' shared sessions (agentic) |
| wildchat | real deployment | 25 | WildChat-1M business chats |
| swe_agent | capability benchmark | 15 | SWE-agent on SWE-bench-style issues |
| tau_bench | capability benchmark | 15 | tau-bench, simulated users |

Controls are rendered in the same Petri text format and cut to a whole-turn prefix of about the eval median
length (4.8k chars), ending on an assistant turn.

## Results
Mean score (share ≥ 0.5 in brackets). binary and unprompted are 0/1 per transcript, so mean = share.

| probe | stock | R0 | openhands | wildchat | swe_agent | tau_bench | AUROC eval vs real | stock − R0, seed-clustered 90% CI |
|---|---|---|---|---|---|---|---|---|
| placeholder (current A2) | 0.71 (0.78) | 0.68 (0.79) | 0.23 (0.08) | 0.10 (0.04) | 0.82 (0.93) | 0.77 (0.93) | 0.95 | +0.02 [−0.02, +0.06] |
| evaldetect (5 questions) | 0.66 (0.78) | 0.56 (0.66) | 0.22 (0.12) | 0.11 (0.00) | 0.75 (0.87) | 0.73 (0.87) | 0.80 | +0.02 [−0.06, +0.09] |
| binary EVAL/REAL | 0.39 | 0.15 | 0.00 | 0.00 | 0.47 | 0.60 | 0.61 | **+0.29 [+0.13, +0.46]**, 7 seeds up / 1 down |
| calibrated (50/50 base rate, genre ≠ evidence) | 0.68 (0.77) | 0.60 (0.64) | 0.22 (0.00) | 0.20 (0.08) | 0.49 (0.53) | 0.74 (1.00) | 0.94 | +0.11 [+0.00, +0.22] |
| unprompted (describe setting, then classify) | 0.22 | 0.06 | 0.04 | 0.00 | 0.27 | 0.13 | 0.54 | +0.13 [+0.00, +0.25] |
| pairwise stock vs R0, both orders | P(stock is the test) 0.57 | | | | | | | **+0.07 [+0.02, +0.11]** over 0.5, 9 seeds up / 2 down; stock picked in 70% of pairs |

## Reading
1. **The current A2 is not content-free on haiku.** Real deployment transcripts score 0.10-0.23, and only 4-8% of them
   reach 0.5. Evals score about 0.70 and capability benchmarks about 0.80. AUROC eval vs real is 0.95. The ceiling
   the Kimi pilot showed (A2 ≈ 0.94 even on transcripts that are only a system prompt) is a property of Kimi or the
   real-Petri setup, not of the probe wording alone. This run does not test Kimi.
2. **The current A2 cannot tell stock from R0** (+0.02, CI includes 0). Neither can the EvalDetectBench set.
3. **Prompts that force a commitment do see a difference.** Two survive seed clustering:
   - The one-word binary question flags 39% of stock transcripts and 15% of R0 (+0.29 [+0.13, +0.46]). It also
     flags 0% of real ones. It is conservative (AUROC eval vs real only 0.61), so treat it as a detector of
     obvious tests, not a ranking score.
   - The pairwise probe prefers R0 as the more real of the two in 9 of 12 seeds.

   The calibrated and unprompted prompts point the same way, with the CI touching 0.
4. **Our alignment evals look less like tests than capability benchmarks do** on every direct probe. That
   matches the literature: benchmark scaffolds are the most recognisable genre.

## Caveats
- Exploratory: 6 probe variants, chosen after seeing the placeholder result. Treat items 3 and 4 as hypotheses to
  confirm on fresh samples (k=2..5 for stock has not been generated yet).
- One sample per transcript and probe. Haiku stands in for Kimi K2.6. The transcripts come from the one-turn proxy
  audit, not real 10-turn Petri.
- Pairwise answers agreed across the two orders in only 14 of 23 pairs (position bias); averaging the two orders
  removes the bias from the mean but adds noise.
- Real deployment transcripts differ from evals in more than eval-ness (no system prompt in WildChat, different
  domains), so the AUROC is an upper bound on how well the probes detect "test" as such.
