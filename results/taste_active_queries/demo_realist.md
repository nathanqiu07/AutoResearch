# Active labelling simulation: demo_realist

Source: `data/researchers/demo_realist/choices.jsonl`. 160 labelled pairs; seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]; config {"batch": 4, "committee": 5, "diversity": 0.3, "init": 4, "l2": 0.5, "max_labels": 60, "test_frac": 0.3}. Offline: a stdlib Bradley-Terry learner, no model calls. Code version 1b99a349025a.

| labels | random | uncertainty |
|---:|---:|---:|
| 4 | 0.688 | 0.688 |
| 8 | 0.781 | 0.756 |
| 12 | 0.829 | 0.827 |
| 16 | 0.852 | 0.833 |
| 20 | 0.865 | 0.856 |
| 24 | 0.879 | 0.900 |
| 28 | 0.894 | 0.887 |
| 32 | 0.894 | 0.871 |
| 36 | 0.896 | 0.892 |
| 40 | 0.908 | 0.887 |
| 44 | 0.915 | 0.887 |
| 48 | 0.904 | 0.894 |
| 52 | 0.900 | 0.898 |
| 56 | 0.898 | 0.894 |
| 60 | 0.887 | 0.896 |

Full-pool accuracy (all training labels): 0.892.

Area under the learning curve: random 0.866, uncertainty 0.858; gain -0.008 (90% bootstrap CI over seeds -0.014 to -0.002).

Labels to reach 95% of full-pool accuracy, per seed: random [20, 16, 4, 16, 8, 20, 12, 16, 20, 16], uncertainty [20, 28, 4, 20, 12, 8, 16, 24, 20, 8].

Share of queried labels where the current model disagreed with the label: random 0.171, uncertainty 0.293.
