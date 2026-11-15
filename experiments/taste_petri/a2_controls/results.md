# a2_controls: does post-hoc P(eval) separate evals from non-evals, and do other probe prompts help? (2026-11-15)

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
