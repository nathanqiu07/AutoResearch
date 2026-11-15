# Exploratory hidden-split comparison (written 2026-11-15 before any hidden sample was scored here)

**Not the pre-registered confirmation.** The climb ended with R0 as incumbent (`results.md`), so `PREREG.md`'s
confirmation had nothing to test. The user asked for this exploratory run instead. A separate pre-registered hidden
run of EA1 (another session) lives in `../hillclimb_ea/`; R0 hidden samples are shared with it through the cache
(identical prompts), so no R0 call is made twice.

- Split: hidden, 12 seeds. Samples k = 0..3 for every arm (fresh: no hidden sample was scored before this file).
- Arms: **stock** (unedited seeds), **R0** (generic realism, `seeds/R0_hidden.jsonl`, built earlier), **H3** (the
  closest taste arm on dev, tied with H4 at −0.026; chosen because it needs no per-seed measurements and its
  placebo is clean), **H3-0** (H3's exact prompt without the researcher text).
- Comparisons, paired per seed, 90% bootstrap CI: H3 − R0 (does the closest taste arm beat the control on fresh
  seeds?), H3 − H3-0 (does the researcher text matter?), R0 − stock and H3 − stock (context). Metrics: score, A2,
  A1, validity, bait_reached, faithful, Petri-judge eval_awareness and realism.
- Reading rule, fixed now: a CI excluding 0 on one of these exploratory comparisons is a lead to replicate, not a
  finding; with dev showing H3 − R0 = −0.026, a hidden CI above 0 would most likely be noise or seed-set differences.
