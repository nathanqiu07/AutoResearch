# Richer-fit stopped-run coverage

This is a coverage snapshot, not a scored comparison. It preserves all 96 planned extraction cells and 1,344 ordered prediction slots. The richer intervention has not been ranked, and the frozen development-scaling selection is unchanged.

| Slot disposition | Rows |
| --- | ---: |
| Completed prediction, correctness not evaluated | 202 |
| Attempted prediction with uncertain usage | 2 |
| Held after an uncertain attempt | 20 |
| Valid profile, prediction not dispatched | 434 |
| Invalid extraction | 504 |
| Empty extraction | 70 |
| Structural omission retained in the plan | 112 |
| **Total** | **1,344** |

The 47 valid profiles account for 14 complete prediction jobs, two partial jobs, 26 jobs with explicit `not_dispatched` receipts, and five P7 jobs with no execution evidence at the snapshot. The two partial jobs retain their five and one completed rows. Their uncertain calls and remaining held rows are separate records. Empty prepared directories do not count as execution.

The 88 build calls have $0.194438000 in known conservative usage. Prediction work has 204 attempted calls: 202 with completed outputs and two with uncertain usage. Known prediction usage is $0.031025875, with $0.008804500 retained in reservations. These costs cover this richer core only. The cumulative batch ledger is preserved for audit but is not added to job costs. Controls, embeddings, earlier sparse holds and later recovery are outside this snapshot.

The evaluator checked 408 prediction trace files and reconstructed their item, profile, prompt, system, settings and backend bindings. An independent metadata pass rehashed 930 referenced files and checked every cell and row denominator. Complete status reports what the runner returned; it is not an accuracy or validity judgment. No private target labels were opened, no richer scores were calculated, and no retry was authorized. The cause of the failures, including any relation to the stopped reference run, remains unproven.

The immutable index contains only opaque item identities, hashes, status and usage metadata, and artifact pointers. It contains no target text, choices, probabilities, answers, or source bodies. Later recovery must create a new receipt while retaining this snapshot and its unresolved costs.
