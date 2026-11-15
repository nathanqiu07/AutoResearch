# E2 v2: `diag_v2`

Pairs: `../pairs_v2/band.jsonl`. Arms: M0, M0s, NAME, P4. Real CLI calls this run: 324 (calls.log total 328). Errors: 0.

Paired accuracy = his option chosen in both orders. 90% CIs resample works. p(his) is averaged over both orders.

## all (n = 41, works = 10)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.415 [0.295, 0.559] | – | 0.548 [0.522, 0.589] | – |
| M0s | 0 | 0.829 [0.708, 0.923] | +0.415 [0.226, 0.568] | 0.627 [0.602, 0.656] | +0.079 [0.038, 0.109] |
| NAME | 5 | 0.439 [0.262, 0.643] | +0.024 [-0.149, 0.205] | 0.560 [0.513, 0.614] | +0.012 [-0.033, 0.054] |
| P4 | 244 | 0.488 [0.323, 0.647] | +0.073 [-0.094, 0.196] | 0.561 [0.516, 0.61] | +0.013 [-0.041, 0.055] |

## fair_strict (n = 33, works = 10)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.455 [0.303, 0.643] | – | 0.578 [0.535, 0.637] | – |
| M0s | 0 | 0.818 [0.721, 0.905] | +0.364 [0.148, 0.538] | 0.632 [0.61, 0.66] | +0.055 [0.001, 0.095] |
| NAME | 5 | 0.455 [0.258, 0.657] | +0.000 [-0.212, 0.207] | 0.562 [0.509, 0.617] | -0.015 [-0.073, 0.034] |
| P4 | 244 | 0.485 [0.333, 0.636] | +0.030 [-0.182, 0.185] | 0.570 [0.518, 0.627] | -0.007 [-0.072, 0.043] |

## realness_ambiguous (<=0.5) (n = 9, works = 7)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.222 [0.0, 0.429] | – | 0.471 [0.406, 0.529] | – |
| M0s | 0 | 0.556 [0.286, 0.778] | +0.333 [0.111, 0.571] | 0.587 [0.527, 0.645] | +0.116 [0.067, 0.173] |
| NAME | 5 | 0.333 [0.111, 0.571] | +0.111 [0.0, 0.333] | 0.518 [0.451, 0.61] | +0.047 [-0.006, 0.126] |
| P4 | 244 | 0.333 [0.111, 0.571] | +0.111 [0.0, 0.333] | 0.511 [0.433, 0.598] | +0.040 [-0.018, 0.127] |

## realness_tell (>0.5) (n = 32, works = 10)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.469 [0.333, 0.629] | – | 0.570 [0.537, 0.62] | – |
| M0s | 0 | 0.906 [0.774, 1.0] | +0.438 [0.222, 0.607] | 0.638 [0.609, 0.666] | +0.068 [0.011, 0.11] |
| NAME | 5 | 0.469 [0.273, 0.679] | +0.000 [-0.211, 0.188] | 0.572 [0.525, 0.621] | +0.002 [-0.06, 0.05] |
| P4 | 244 | 0.531 [0.355, 0.714] | +0.062 [-0.133, 0.241] | 0.575 [0.532, 0.623] | +0.005 [-0.058, 0.054] |

## generator=axis_flip (n = 10, works = 5)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.500 [0.385, 0.714] | – | 0.538 [0.463, 0.656] | – |
| M0s | 0 | 0.700 [0.4, 1.0] | +0.200 [-0.2, 0.462] | 0.616 [0.547, 0.686] | +0.077 [-0.057, 0.164] |
| NAME | 5 | 0.400 [0.2, 0.714] | -0.100 [-0.286, 0.0] | 0.541 [0.486, 0.645] | +0.003 [-0.079, 0.07] |
| P4 | 244 | 0.500 [0.273, 0.778] | +0.000 [-0.286, 0.222] | 0.535 [0.466, 0.631] | -0.003 [-0.12, 0.122] |

## generator=field (n = 13, works = 7)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.308 [0.0, 0.471] | – | 0.499 [0.442, 0.532] | – |
| M0s | 0 | 0.769 [0.6, 0.923] | +0.462 [0.333, 0.7] | 0.603 [0.558, 0.652] | +0.103 [0.059, 0.169] |
| NAME | 5 | 0.538 [0.231, 0.833] | +0.231 [-0.062, 0.6] | 0.588 [0.511, 0.659] | +0.088 [0.023, 0.165] |
| P4 | 244 | 0.538 [0.3, 0.684] | +0.231 [0.077, 0.417] | 0.573 [0.495, 0.622] | +0.074 [0.049, 0.099] |

## generator=peer (n = 18, works = 9)

| arm | words | paired acc [90% CI] | Δ acc vs M0 [90% CI] | mean p(his) [90% CI] | Δ p(his) vs M0 |
|---|---|---|---|---|---|
| M0 | 0 | 0.444 [0.278, 0.692] | – | 0.589 [0.535, 0.677] | – |
| M0s | 0 | 0.944 [0.818, 1.0] | +0.500 [0.267, 0.652] | 0.650 [0.624, 0.692] | +0.061 [0.004, 0.102] |
| NAME | 5 | 0.389 [0.2, 0.667] | -0.056 [-0.222, 0.118] | 0.550 [0.491, 0.632] | -0.039 [-0.092, 0.005] |
| P4 | 244 | 0.444 [0.261, 0.667] | +0.000 [-0.214, 0.188] | 0.567 [0.509, 0.636] | -0.022 [-0.103, 0.033] |

## Decision rules (PROTOCOL.md), on the whole pairs file

- BAND HOLDS: M0 = 0.415 <= 0.65.
- NAME: 'predicts taste' not evaluable (missing arms: P0, MIS).
- P4: 'predicts taste' not evaluable (missing arms: P0, MIS).

## Notes (hand-written, 2026-11-15)

- Calls: 328 real (`calls.log`: 4 from a one-pair smoke test, then cached, plus 324 here), 82 of them sonnet (M0s). 0 errors, 0 JsonReply retries. Cap 350, 4 workers.
- fair_strict is a subset of band.jsonl, so its M0 cost no extra calls.
- The haiku rule passes: M0 is 0.415, not above 0.65. But **M0s (sonnet, no profile) gets 0.829 [0.708, 0.923]**, so these pairs are not balanced for a second reader. That fits risk 4 in pairs_v2/stats.md: the band was selected on haiku votes.
- M0s splits by realness: 0.906 on the 32 pairs where the realness probe found his option, and 0.556 on the 9 ambiguous ones (7 works). This suggests the realness tell, or plain sonnet research sense, is driving the sonnet number. These data cannot separate the two.
- Under the protocol's sign rule, any haiku profile arm must also beat M0s, which is now 0.83. That bar is out of reach on pairs_v2.
- NAME and P4 do not move haiku overall. Δ vs M0 is +0.02 and +0.07, and both CIs span 0. The only non-zero interval is P4 on FIELD pairs: +0.23 [0.08, 0.42], n = 13 from 7 works. That cut is post hoc and descriptive.
