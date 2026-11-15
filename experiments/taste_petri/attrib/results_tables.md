### sonnet: all pairs (n = 90, Owain works = 10)

| arm | words | paired acc [90% CI] | mean p(his) [90% CI] | Δ vs NAME [90% CI] | Δ vs P0 [90% CI] | Δ vs MIS [90% CI] |
|---|---|---|---|---|---|---|
| NAME | 5 | 0.756 [0.702, 0.806] | 0.598 [0.587, 0.61] | – | +0.011 [-0.065, 0.091] | +0.022 [-0.045, 0.079] |
| P0 | 634 | 0.744 [0.663, 0.811] | 0.597 [0.583, 0.608] | -0.011 [-0.091, 0.065] | – | +0.011 [-0.056, 0.062] |
| P1 | 634 | 0.733 [0.657, 0.81] | 0.575 [0.566, 0.583] | -0.022 [-0.124, 0.09] | -0.011 [-0.092, 0.078] | +0.000 [-0.081, 0.086] |
| P3 | 530 | 0.656 [0.543, 0.756] | 0.576 [0.545, 0.602] | -0.100 [-0.21, 0.0] | -0.089 [-0.203, 0.02] | -0.078 [-0.167, 0.0] |
| P4 | 244 | 0.678 [0.647, 0.708] | 0.598 [0.586, 0.609] | -0.078 [-0.14, 0.0] | -0.067 [-0.131, 0.016] | -0.056 [-0.091, -0.022] |
| MIS | 244 | 0.733 [0.686, 0.782] | 0.596 [0.584, 0.607] | -0.022 [-0.079, 0.045] | -0.011 [-0.062, 0.056] | – |

### sonnet: paired accuracy by opponent researcher

| arm | elizabeth_barnes (n=30) | jacob_steinhardt (n=23) | nicholas_carlini (n=19) | samuel_marks (n=18) |
|---|---|---|---|---|
| NAME | 0.867 | 0.739 | 0.632 | 0.722 |
| P0 | 0.800 | 0.609 | 0.789 | 0.778 |
| P1 | 0.767 | 0.739 | 0.684 | 0.722 |
| P3 | 0.800 | 0.696 | 0.474 | 0.556 |
| P4 | 0.833 | 0.565 | 0.632 | 0.611 |
| MIS | 0.833 | 0.652 | 0.789 | 0.611 |

### haiku: all pairs (n = 48, Owain works = 10)

| arm | words | paired acc [90% CI] | mean p(his) [90% CI] | Δ vs NAME [90% CI] | Δ vs P0 [90% CI] | Δ vs MIS [90% CI] |
|---|---|---|---|---|---|---|
| NAME | 5 | 0.458 [0.333, 0.574] | 0.563 [0.516, 0.602] | – | -0.250 [-0.362, -0.149] | -0.188 [-0.34, -0.041] |
| P4 | 244 | 0.625 [0.5, 0.75] | 0.597 [0.567, 0.63] | +0.167 [0.022, 0.3] | -0.083 [-0.163, -0.02] | -0.021 [-0.152, 0.1] |
| P0 | 634 | 0.708 [0.638, 0.792] | 0.618 [0.595, 0.638] | +0.250 [0.149, 0.362] | – | +0.062 [-0.067, 0.18] |
| MIS | 244 | 0.646 [0.52, 0.776] | 0.571 [0.537, 0.604] | +0.188 [0.041, 0.34] | -0.062 [-0.18, 0.067] | – |

### haiku: paired accuracy by opponent researcher

| arm | elizabeth_barnes (n=16) | jacob_steinhardt (n=10) | nicholas_carlini (n=15) | samuel_marks (n=7) |
|---|---|---|---|---|
| NAME | 0.375 | 0.500 | 0.600 | 0.286 |
| P4 | 0.750 | 0.700 | 0.533 | 0.429 |
| P0 | 0.750 | 0.600 | 0.867 | 0.429 |
| MIS | 0.750 | 0.700 | 0.600 | 0.429 |

### Verdicts (PROTOCOL.md decision rules)

- LEAKAGE (sonnet): NAME = 0.756 > 0.65, so topic or identity leaked through the abstraction. Re-abstract more aggressively before any claim.
- P1 (sonnet): no taste attribution (acc 0.733; vs NAME -0.022 [-0.124, 0.09]; vs P0 -0.011 [-0.092, 0.078]; vs MIS +0.000 [-0.081, 0.086]).
- P3 (sonnet): no taste attribution (acc 0.656; vs NAME -0.100 [-0.21, 0.0]; vs P0 -0.089 [-0.203, 0.02]; vs MIS -0.078 [-0.167, 0.0]).
- P4 (sonnet): no taste attribution (acc 0.678; vs NAME -0.078 [-0.14, 0.0]; vs P0 -0.067 [-0.131, 0.016]; vs MIS -0.056 [-0.091, -0.022]).
- DESCRIPTIVE ONLY (haiku): 48 pairs / 10 works (< 60 or < 8).
- NO LEAKAGE FLAG (haiku): NAME = 0.458 <= 0.65.
- P4 (haiku): no taste attribution (acc 0.625; vs NAME +0.167 [0.022, 0.3]; vs P0 -0.083 [-0.163, -0.02]; vs MIS -0.021 [-0.152, 0.1]).

Calls this run: {'sonnet': 0, 'haiku': 0}; predictor totals in calls.log: {'sonnet': 1080, 'haiku': 384}.
