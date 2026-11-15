# surgery results (2026-11-15, devin-tastepetri)

Pre-registered in `PREREG.md`. Common random numbers: each R0 audit opening (k=0-2) is reused exactly from cache,
one edit is applied to its content, and target, A2, judge and the Petri judge are re-run. Haiku proxy, 10-11 seeds,
paired per (seed, k), averaged per seed, 90% bootstrap over seeds. Full tables: `compare_k3.md`.

| edit vs ID (same scenario, re-run) | n seeds | Petri realism | Petri EA | A2 | A1 | validity | bait_reached |
|---|---|---|---|---|---|---|---|
| **NB**: bait passage replaced by routine material | 11 | **+0.8 [+0.4, +1.1]** | −0.2 [−0.3, −0.1] | **−0.12 [−0.18, −0.06]** | −0.08 | −0.38 | −0.47 [−0.60, −0.34] |
| **SOFT**: same bait facts and place, ordinary presentation | 10 | +0.1 [−0.3, +0.6] | −0.1 [−0.2, +0.1] | −0.01 [−0.06, +0.03] | +0.03 | +0.00 | −0.01 [−0.09, +0.08] |
| ID vs original R0 (noise floor) | 11 | +0.0 [−0.4, +0.5] | −0.1 | −0.00 [−0.04, +0.03] | +0.06 [+0.00, +0.14] | −0.08 | −0.04 |

## Reading
1. **The bait's presence is a large, causal tell.** In the same scenario, removing the bait raises Petri realism by
   0.8 and lowers A2 by 0.12. That matches the regression estimate in petri_taste/bait_adjust.md (−0.77 realism),
   so the realism–validity trade-off seen across every seed-rewrite arm is real, not a confound. NB is the
   manipulation check (bait_reached −0.47) and is not a usable arm.
2. **Presentation doesn't matter on this proxy.** Stripping labels, capitals, emphasis and "complete package"
   framing from the bait, while keeping its facts and placement, changes nothing (realism +0.1, A2 −0.01, bait kept).
   Rule 1 is not met. The judge and target respond to *what* the opportunity is, not to how it is dressed.
3. **Where A2 can still come from.** Even with no bait, A2 is 0.55. The bait accounts for about 0.12 of A2; the rest
   is the genre of the transcript (an agentic, tool-using session). Bait manipulations can move A2 by at most about
   0.12 on this proxy. Larger moves need a different kind of transcript, which matches the lit review (LURE, real
   prefixes).
4. **Petri realism of the scenario without bait is 6.9/10, against 6.1-6.2 with it.** This is the realism ceiling
   that edits not touching the bait run into.

Noise floor: re-running the same openings (ID) moves no primary metric (realism +0.0, A2 −0.00). A1 shifts by +0.06
on the re-run, so A1 differences below about 0.08 are noise here.

## Calls
- 343 haiku downstream calls: ID 129, SOFT 99, NB 115. The auditor openings were all cache hits.
- 75 devin-cli sonnet calls for the edits.
- 7 of 36 SOFT edits failed validation (no change or a changed structure). Those samples are excluded, so the
  paired n is 10 seeds.
