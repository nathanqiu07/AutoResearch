# taste_ranker results (2026-11-15, devin-tastepetri)

Pre-registered in `PREREG.md`. Data: the 7 petri_taste rewrites per seed, with measured Petri-judge scores (haiku
proxy, k=3), on 10 seeds. Seeds 28 and 17 have fewer than 5 scored arms, so they are excluded; the pre-registration
said 11. Rankers are sonnet via devin-cli, 2 shuffles each, 100 calls, 0 unparseable. ρ is the per-seed Spearman
between a ranker's order and the measured order, averaged over seeds, with a 90% bootstrap CI over seeds.

| ranker | ρ realism | ρ realism − EA | ρ validity | top pick's realism gain over the seed mean |
|---|---|---|---|---|
| M0 (no profile) | +0.26 [+0.11, +0.41] | +0.33 [+0.13, +0.50] | −0.38 [−0.55, −0.18] | +0.18 [−0.00, +0.38] |
| BOW (Bowman card) | +0.29 [+0.09, +0.48] | +0.37 [+0.13, +0.58] | −0.30 [−0.45, −0.13] | +0.33 [+0.00, +0.63] |
| GRE (Greenblatt card) | +0.29 [+0.11, +0.46] | +0.36 [+0.15, +0.56] | −0.39 [−0.57, −0.21] | +0.23 [−0.06, +0.51] |
| CAR (Carlini card, placebo) | +0.24 [+0.03, +0.43] | +0.35 [+0.12, +0.54] | −0.38 [−0.57, −0.17] | +0.01 [−0.12, +0.15] |
| NAME ("as Samuel Bowman") | +0.19 [−0.00, +0.38] | +0.25 [+0.05, +0.43] | −0.34 [−0.51, −0.16] | +0.11 [−0.06, +0.30] |

Paired differences vs M0 on realism, the primary metric:
- BOW +0.03 [−0.06, +0.11]
- GRE +0.03 [−0.04, +0.09]
- CAR −0.03 [−0.15, +0.09]
- NAME −0.07 [−0.20, +0.03]

Noise ceiling: the split-half reliability of measured realism (k=0 against the mean of k=1 and k=2) is ρ = 0.40
[0.25, 0.55], or 0.57 after the Spearman-Brown correction.

## Reading
1. **Taste as a selector: null on the pre-registered rule.** No profile beats no profile on realism. The
   differences are about ±0.03, against a ceiling of about 0.6.
2. **A positive result that doesn't depend on taste:** a single sonnet ranker with no profile predicts which rewrite
   gives the more realistic audit (ρ = 0.26, about half the noise ceiling) without running any audit. In the loop it
   could screen rewrites before paying for audits. A real-Petri check is needed before relying on it.
3. **Every ranker prefers the rewrites that lose the bait** (ρ with validity −0.30 to −0.39). The realism–validity
   trade-off in `petri_taste/bait_adjust.md` shows up in the rankers' judgement too: "looks real" means "the planted
   thing is less visible".
4. **Exploratory (not a pre-registered rule): the Bowman card softens that bias.** Its validity ρ is less negative
   than M0's by +0.07 [+0.03, +0.12], and its top pick gains the most realism (+0.33 [0.00, 0.63]; the placebo gets
   +0.01). GRE and CAR show neither effect. This is a small, single-test signal at n=10 seeds. It is the only place
   tonight where a matched profile differs from both no profile and a placebo, so it is worth one confirmatory
   rerun on new rewrites.
5. Self-preference check: BOW does not favour its own TB/TB2 rewrites. Their mean rank is 3.2, against 3.0 for M0
   and 3.3 for CAR.

## Calls
100 devin-cli sonnet calls, 0 haiku.
