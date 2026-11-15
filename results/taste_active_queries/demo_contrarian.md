# Active labelling simulation: demo_contrarian

Source: `data/researchers/demo_contrarian/choices.jsonl`. 160 labelled pairs; seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]; config {"batch": 4, "committee": 5, "diversity": 0.3, "init": 4, "l2": 0.5, "max_labels": 60, "test_frac": 0.3}. Offline: a stdlib Bradley-Terry learner, no model calls. Code version 1b99a349025a.

| labels | random | uncertainty |
|---:|---:|---:|
| 4 | 0.685 | 0.685 |
| 8 | 0.771 | 0.769 |
| 12 | 0.767 | 0.748 |
| 16 | 0.802 | 0.781 |
| 20 | 0.810 | 0.835 |
| 24 | 0.817 | 0.838 |
| 28 | 0.833 | 0.833 |
| 32 | 0.838 | 0.848 |
| 36 | 0.852 | 0.871 |
| 40 | 0.844 | 0.873 |
| 44 | 0.852 | 0.873 |
| 48 | 0.846 | 0.879 |
| 52 | 0.850 | 0.875 |
| 56 | 0.854 | 0.871 |
| 60 | 0.860 | 0.871 |

Full-pool accuracy (all training labels): 0.877.

Area under the learning curve: random 0.819, uncertainty 0.830; gain +0.011 (90% bootstrap CI over seeds -0.009 to +0.034).

Labels to reach 95% of full-pool accuracy, per seed: random [8, 16, 48, 60, 12, 8, 16, 8, 20, 24], uncertainty [8, 20, 28, 20, 20, 24, 20, 8, 20, 32].

Share of queried labels where the current model disagreed with the label: random 0.184, uncertainty 0.275.
