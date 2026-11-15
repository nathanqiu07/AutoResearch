# E2 hill-climb: confirmation on e2_v4's 96 pairs (sonnet, unbatched, both orders)

n = 96 pairs, 10 works. Errors: 0. M0s, NAME, P4, P0, MIS and ANTI are e2_v4's cached predictions. 90% CIs resample works. H_B is tuned on other post-T decisions from the same works (weaker claim).

| arm | paired acc [90% CI] | mean p(his) [90% CI] |
|---|---|---|
| H_A | 0.292 [0.228, 0.365] | 0.429 [0.399, 0.461] |
| H_B | 0.219 [0.135, 0.312] | 0.410 [0.373, 0.451] |
| M0s | 0.177 [0.11, 0.25] | 0.379 [0.353, 0.405] |
| NAME | 0.260 [0.179, 0.348] | 0.392 [0.369, 0.417] |
| P4 | 0.292 [0.19, 0.398] | 0.428 [0.396, 0.464] |
| P0 | 0.229 [0.15, 0.312] | 0.388 [0.358, 0.418] |
| MIS | 0.260 [0.21, 0.319] | 0.404 [0.372, 0.438] |
| ANTI | 0.438 [0.344, 0.53] | 0.496 [0.469, 0.522] |

## Primary comparisons

| arm | Δacc vs M0s | Δacc vs NAME | Δacc vs P4 | Δp(his) vs M0s | Δp(his) vs NAME | Δp(his) vs P4 |
|---|---|---|---|---|---|---|
| H_A | +0.115 [0.081, 0.149] | +0.031 [-0.01, 0.076] | +0.000 [-0.047, 0.05] | +0.050 [0.032, 0.07] | +0.037 [0.019, 0.059] | +0.000 [-0.006, 0.006] |
| H_B | +0.042 [-0.012, 0.104] | -0.042 [-0.109, 0.02] | -0.073 [-0.122, -0.021] | +0.032 [0.011, 0.054] | +0.019 [-0.002, 0.044] | -0.018 [-0.029, -0.006] |

## Placebos (descriptive only)

| arm | Δacc vs P0 | Δacc vs MIS | Δacc vs ANTI | Δp(his) vs P0 | Δp(his) vs MIS | Δp(his) vs ANTI |
|---|---|---|---|---|---|---|
| H_A | +0.062 [0.031, 0.099] | +0.031 [0.0, 0.063] | -0.146 [-0.235, -0.058] | +0.041 [0.014, 0.074] | +0.025 [0.016, 0.034] | -0.067 [-0.09, -0.044] |
| H_B | -0.010 [-0.08, 0.052] | -0.042 [-0.11, 0.022] | -0.219 [-0.32, -0.113] | +0.023 [-0.007, 0.058] | +0.007 [-0.005, 0.019] | -0.085 [-0.111, -0.058] |

Real calls by budget category (caps {'score': 400, 'op': 40, 'H_A': 192, 'H_B': 192}): {'score': 192, 'op': 24, 'H_A': 192, 'H_B': 192}. Climb-set scoring is batched haiku; selection on haiku may not transfer to the sonnet confirmation.
