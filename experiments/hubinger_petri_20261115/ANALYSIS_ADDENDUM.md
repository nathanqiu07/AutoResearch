# Addendum: where the headroom actually is

The comparison table reports native ratings per run. This addendum checks,
dimension by dimension across all 15 completed native audits, which ratings
ever move and whether profile conditions (P2/P5/P8, n=6) differ from
control conditions (no_profile/generic/evan_hubinger-raw, n=9) on the ones
that do.

## 32 of 38 native dimensions never move

Across all 15 runs, 32 of the 38 rated dimensions — `eval_awareness`
included — sit at a single value (1) in every run, profile or control. That
is the floor effect the main README already reports for `eval_awareness`
specifically; this addendum confirms it is not isolated to that one
dimension. With zero variance, no comparison on those 32 dimensions can
show an effect, favorable or not, regardless of sample size.

## 6 dimensions do move

| Dimension | Range | Profiles mean (n=6) | Controls mean (n=9) | Difference |
|---|---|---:|---:|---:|
| `scenario_realism` | 6–9 | 8.33 | 8.00 | +0.33 |
| `admirable` | 3–6 | 4.33 | 3.89 | +0.44 |
| `unprompted_initiative` | 1–3 | 2.33 | 2.56 | −0.22 |
| `needs_attention` | 1–3 | 1.33 | 1.67 | −0.33 |
| `high_stakes_setting` | 2–4 | 2.33 | 2.56 | −0.22 |
| `concerning` | 1–2 | 1.00 | 1.11 | −0.11 |

These are the only six dimensions where this pilot could in principle have
shown a profile effect. All six differences are a few tenths of a point on
a 1–10 scale, with per-condition ranges (listed in `comparison.md`) that
overlap heavily across profile and control conditions (e.g. `scenario_realism`
is 9,9 for P5 but also 8,9,9 for raw Hubinger excerpts). At n=2–3 runs per
condition, these differences are consistent with judge noise; none of them
is large enough, or consistent enough in sign across related dimensions, to
read as a profile effect.

## What this changes about the headline

The main README's claim is correct but can be stated more precisely: the
pilot does not merely lack headroom on `eval_awareness`; where headroom
exists elsewhere in the rubric, it also shows no profile effect. That
strengthens rather than weakens the null — this was not a measurement
artifact confined to one floored dimension.

## What would be needed to settle it

The two failed primary reviews (`no_profile` r1, `evan_hubinger-raw` r2)
are recoverable without rerunning the audit — `scripts/gio_petri/review_failed.py
--execute` replays only the primary review against the existing frozen
transcript — but that replay is itself one more GPT-5.1 call on the shared,
near-exhausted account, so it was not run here without asking first.

To get a real read on `scenario_realism` specifically (the one dimension
with the widest range and the cleanest signal-to-noise ratio of the six),
the natural next step is more replicates of the existing six conditions,
not a new scenario: at ~$0.67/run (from `estimated_completed_batch_usd:
10.05` over 15 runs), 8 replicates/condition across the 6 conditions already
built (48 runs) would cost roughly $32 and give an n large enough for the
spread above to mean something either way.
