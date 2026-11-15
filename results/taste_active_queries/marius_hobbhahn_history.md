# Active labelling simulation: marius_hobbhahn_history

Source: `data/researchers/marius_hobbhahn/history_timesplit.jsonl`. 373 labelled pairs; seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]; config {"batch": 8, "committee": 5, "diversity": 0.3, "init": 4, "l2": 0.5, "max_labels": 120, "test_frac": 0.3}. Offline: a stdlib Bradley-Terry learner, no model calls. Code version 1b99a349025a.

| labels | random | uncertainty |
|---:|---:|---:|
| 4 | 0.531 | 0.531 |
| 12 | 0.544 | 0.566 |
| 20 | 0.546 | 0.548 |
| 28 | 0.569 | 0.569 |
| 36 | 0.571 | 0.597 |
| 44 | 0.564 | 0.618 |
| 52 | 0.569 | 0.619 |
| 60 | 0.581 | 0.614 |
| 68 | 0.601 | 0.614 |
| 76 | 0.605 | 0.630 |
| 84 | 0.605 | 0.629 |
| 92 | 0.614 | 0.639 |
| 100 | 0.622 | 0.634 |
| 108 | 0.623 | 0.641 |
| 116 | 0.643 | 0.643 |
| 120 | 0.649 | 0.650 |

Full-pool accuracy (all training labels): 0.679.

Area under the learning curve: random 0.590, uncertainty 0.609; gain +0.019 (90% bootstrap CI over seeds +0.003 to +0.035).

Labels to reach 95% of full-pool accuracy, per seed: random [68, 116, 20, 100, never, never, never, 120, never, 28], uncertainty [28, 108, 36, 68, 76, never, 52, 12, 116, 52].

Share of queried labels where the current model disagreed with the label: random 0.375, uncertainty 0.427.
