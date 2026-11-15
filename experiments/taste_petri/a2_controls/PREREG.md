# a2_controls replication: pre-registration (written 2026-11-15, before any k=6..9 audit exists)

## Why
The exploratory run (`results.md`) tried 6 probe variants after seeing the first result. Two of them separated stock
seeds from the R0 generic-realism rewrite, while the current A2 did not:
- the one-word EVAL/REAL probe: +0.29, seed-clustered 95% CI [+0.08, +0.50];
- the pairwise probe, P(stock is the test) − 0.5: +0.07 [+0.01, +0.12].

Both were picked after the fact, and every stock transcript came from k=0,1. This replication tests both on fresh
audits.

## Data
- Fresh proxy audits of the 12 dev seeds, at k = 6, 7, 8, 9, for both arms: `stock` (data/petri/seeds_v2.jsonl
  dev) and `R0` (hillclimb/seeds/R0_dev.jsonl). They are generated with exactly the pipeline the exploratory
  transcripts were replayed from (`rm_proxy.auditor_prompt` + `build_audit`, target-sim, render, cut). No earlier
  cache holds any of these 96 samples (checked).
- The model is haiku via `claude -p`, as in the exploratory run.
- Command: `a2_controls.py collect --tag rep --ks 6 7 8 9 --generate --no-controls`.
- Budget: at most 250 generation calls and 700 probe calls. A sample whose auditor-sim or target-sim fails or
  refuses is dropped. Drops are reported per arm, never imputed.

## Probes
These are unchanged from the exploratory run, with identical prompt text: `binary`, `pairwise` (both presentation
orders, averaged), and as secondary `placeholder`, `calibrated` and `unprompted`. `evaldetect` is not re-run.

## Analysis (fixed now)
- Unit: one pair = stock and R0 at the same base seed and the same k, with both transcripts present.
- Statistic: the per-seed mean of the pair differences, then the mean over seeds. The bootstrap resamples seeds
  (4000 draws, seed 0). The function is `clustered()` in `a2_controls.py`.
  - Binary: the difference is stock − R0, each 0/1.
  - Pairwise: the value is P(stock is the test) − 0.5.

## Decision rules
- **H1 (binary).** Confirmed if the seed-clustered **95%** CI of the stock − R0 difference has lower bound > 0.
- **H2 (pairwise).** Confirmed if the seed-clustered **95%** CI of P(stock is the test) − 0.5 has lower bound > 0.
- The two-sided 95% level is a Bonferroni correction for 2 tests at one-sided 5%.
- Each hypothesis is judged on its own. A result in the opposite direction with its CI excluding 0 counts as a
  failure to replicate, not as a confirmation.
- Secondary (descriptive only, no decision): placeholder, calibrated and unprompted, with stock − R0 on the same
  clustered statistic. Also the pooled estimate over k = 0, 1, 6..9, which is reported but not used for the
  decision.

## What a result means
- **Confirmed.** On the haiku proxy, the probe detects that R0 transcripts read as less test-like than stock,
  which the current A2 misses. This says nothing about Kimi K2.6 or real Petri.
- **Not confirmed.** The exploratory difference was noise or k-specific. Treat binary and pairwise as no better
  than the current A2 for comparing arms.
