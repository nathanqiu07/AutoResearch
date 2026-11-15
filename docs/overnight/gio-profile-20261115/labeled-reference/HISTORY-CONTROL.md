# Prospective paired history association control

This adds a separate, lease-gated entrypoint for the fixed 64 development users and 516 target choices. Each target keeps its original context and option order. The own arm uses its exact saved native M1 history; the wrong arm uses the next user in canonical order within the same selected-history-size group. Donor IDs and training labels remain intact. No fitting, source prediction, baseline cache, or core method is changed.

The new experiment has 1,032 planned cells and 1,031 eligible requests. One historical unknown own-history request remains unavailable. The other eligible own requests include explicitly declared known-valid replications and previously unattempted cells; execution requires coordinator authority for the declared new experiment. Historical M0/M1 outcomes remain aliases, with original user903 missingness and its distinct recovery source reported separately.

Packets copy and hash-bind the proposal, source artifacts, development records and splits, and current typed request guard. Preparation and admission reconstruct native M1 requests and compare both wire hash conventions to the frozen proposal. Each packet starts with an empty response cache. Admission requires exact runtime/settings, a fresh external single-use claim, a finite call/cost/time lease and the 17:00 UTC deadline. Uncertain API outcomes stop later network calls in that packet. All planned predictions remain present through errors; withheld cells do not make a request. There is no automatic retry.

The coordinator owns paid launch and scheduling. The CLI is `python3 -B scripts/overnight_history_control.py prepare --proposal PATH --guard PATH --user ID --destination PATH`, then separately leased `run --plan PATH --lease PATH`. Private input and output paths stay outside the repository.

Primary reporting is paired user-macro planned accuracy, counting failures/unavailable/unstarted cells as wrong. User-cluster bootstrap intervals are descriptive and conditional because the deterministic donor cycles link users. Valid-pair accuracy and Brier/coverage are separate sensitivities. Arm order is balanced across users (32/32), not target counts (268/248). This tests correct-history association; topic, task, content and length differences prevent interpreting the contrast as isolated latent taste. The cohort was already studied; the paired experiment is prospective relative to its new outcomes, not independent final-test confirmation.

The reference contains human-rating-derived pairwise preference labels with model-based filtering. It is not necessarily direct binary elicitation, model-generated target labels, researcher taste, or research utility. All methods are existing adaptations, not paper reproductions.

Validation covers preserved donor provenance, scope and request identity, exact withholding, fresh caches, explicit replication authority, finite lease limits, copied-packet replay, and native failure handling. Review captures expose selected fit histories and label-free target projections only; target labels and result predictions remain with the reference custodian.

## Completed study, November 15, 2026

Correct-user M1 history showed no clear accuracy advantage over the fixed wrong-user reassignment on this previously studied development panel. The primary own-minus-wrong difference was **−1.83 percentage points**, with a descriptive, conditional 95% interval of **[−5.75, +2.08] points**. This is not an equivalence test or evidence that personalization generally fails.

All 64 packets finished. Each arm retained all 516 planned targets; failures and the one predeclared unavailable request counted as wrong. Accuracy first averages within each user and then gives all 64 users equal weight. The counts below are supplementary totals, not the denominator used to average user accuracy.

| Arm | User-macro planned accuracy | Correct / planned cells | Valid outputs / planned cells | Valid-only user-macro Brier |
|---|---:|---:|---:|---:|
| Own history | 50.1621% | 256 / 516 | 514 / 516 | 0.288024 |
| Wrong history | 51.9881% | 264 / 516 | 515 / 516 | 0.276953 |

There were two new invalid-JSON outputs, one in each arm, plus the predeclared own-history withholding. All remain in planned denominators. There were 1,031 new wrapper attempts and 1,031 observed HTTP events, with 1,029 valid outputs. Estimated new usage was **$0.4189835**, with no new uncertain-cost holds. This is an estimate from closed accounting, not an invoice; historical uncertain requests remain held and excluded.

| Delivery-conditioned sensitivity | Retained users / targets | Own minus wrong | Descriptive conditional 95% interval |
|---|---:|---:|---:|
| Joint-valid target pairs | 64 / 513 | −1.83 points | [−5.78, +2.11] points |
| Users with every planned output valid | 61 / 480 | −2.04 points | [−6.10, +2.10] points |

Both sensitivities condition on successful delivery; they do not explain the primary difference causally. The joint-valid user-macro Brier difference was +0.011834 (own minus wrong; lower is better), which does not establish calibration. Own-first users had a +2.03-point accuracy contrast and wrong-first users a −5.68-point contrast. Those strata contain different fixed users, so this is not an identified execution-order effect.

The scientific runtime was commit `63e11c950fcba271d231a5e7eade045c750e6521`. Both arms used OpenAI `gpt-6-luna`, reasoning `none`, no tools, a 2,048-token output limit, and the native M1 prompt. Selected history sizes were five examples for 62 users and four for two users. Wrong histories followed fixed 62-user and two-user donor cycles; source identities and labels were preserved. A fresh cache supported explicitly declared known-valid replication. Original baseline missingness and the separate recovery source remain distinct historical aliases, adding no observations or usage to this paired study.

The interval uses 2,000 user-cluster bootstrap draws with seed 0. Deterministic donor cycles create cross-user dependence that this bootstrap does not fully model, so it is descriptive and conditional rather than randomized-assignment inference or an independent-population bound. Only history example count was matched: topic, task mix, content, length, and history-label distribution were not. The study therefore tests correct-history association, not isolated latent taste. It was frozen before these new outcomes but selected after earlier work on the same development cohort. No final test users were accessed, and this result does not establish researcher taste or downstream research utility.

The compiler was reviewed before scoring, and the terminal run was scored once under the frozen protocol. A separate evaluator reproduced the primary and sensitivity statistics, counts, coverage, Brier values, order strata, and accounting from safe per-user aggregates to numerical tolerance. That review did not reopen raw labels or probabilities; raw correctness and label reconciliation remain the reference custodian's evidence. Private inputs, per-user statistics, controls, caches, and retention records are kept outside this repository.
