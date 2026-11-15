# SynthesizeMe for Marius Hobbhahn (swe-2-medium via devin-cli, deadline run)

Test pairs: 58 of 58 (failed predictions dropped: 0), works: 6.
Paired accuracy = his option chosen in both orders. 90% CIs resample works.

| arm | words | paired acc [90% CI] | mean p(his) [90% CI] |
|---|---|---|---|
| M0s | 0 | 0.155 [0.076, 0.259] | 0.400 [0.373, 0.433] |
| NAME | 5 | 0.224 [0.13, 0.346] | 0.400 [0.36, 0.447] |
| S_paper_lite | 193 | 0.207 [0.114, 0.277] | 0.371 [0.327, 0.412] |
| S_inf_lite | 164 | 0.121 [0.061, 0.18] | 0.346 [0.315, 0.372] |

Bold = 90% CI excludes 0.

| arm | Δacc vs M0s | Δp(his) vs M0s | Δacc vs NAME | Δp(his) vs NAME |
|---|---|---|---|---|
| NAME | +0.069 [0.0, 0.157] | +0.000 [-0.025, 0.026] | – | – |
| S_paper_lite | +0.052 [-0.079, 0.111] | -0.029 [-0.059, 0.001] | -0.017 [-0.136, 0.053] | **-0.029 [-0.056, -0.013]** |
| S_inf_lite | -0.034 [-0.111, 0.0] | **-0.054 [-0.08, -0.04]** | **-0.103 [-0.188, -0.043]** | **-0.054 [-0.082, -0.035]** |

## Significant results (90% CI excludes 0)

- S_paper_lite vs NAME, mean p(his): -0.029 [-0.056, -0.013] (worse than NAME)
- S_inf_lite vs M0s, mean p(his): -0.054 [-0.08, -0.04] (worse than M0s)
- S_inf_lite vs NAME, paired acc: -0.103 [-0.188, -0.043] (worse than NAME)
- S_inf_lite vs NAME, mean p(his): -0.054 [-0.082, -0.035] (worse than NAME)

CIs resample 6 works, so they are likely too narrow (decoys/ A/A check: few-cluster bootstrap CIs are overconfident). The lite personas skip SynthesizeMe's validation selection (deadline shortcut, lite.py); every call is swe-2-medium.
