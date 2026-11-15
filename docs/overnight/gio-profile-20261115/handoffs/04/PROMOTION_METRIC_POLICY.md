# Development replication allocation policy

Frozen receipt: `development-promotion-metric-policy-v1.json`, SHA256 `41897a2c111db44a3833fa801e9d09b76360377330bab158e05668d53d93af02`.

The existing evaluator defines accuracy as correct valid deliveries divided by all scheduled rows. The original plan specified accuracy, coverage, cost and deterministic ID ties without a numerical ranking formula. This receipt makes that ordering explicit; it changes no primary outcome or denominator.

Each configuration has 28 planned ordered rows: 14 per researcher. Let C be its number of valid correct deliveries and V its number of valid deliveries. Missing, invalid, empty, unavailable, abstained and non-dispatched rows add neither C nor V and remain in the denominator. Rank configurations in this order:

1. Larger C/28.
2. Larger V/28.
3. Lower conservative cost: known build and prediction charges plus retained uncertain reservations, counted once per canonical job. Use exact Decimal values. If accounting lacks a defensible bound, cost ranks as infinity, never zero.
4. ASCII configuration ID in ascending order.

Report each researcher's results separately. Conditional valid accuracy C/V is null when V=0; it does not replace C/28. Paired comparisons on jointly valid item/order rows, full-schedule paired differences, probability coverage/Brier, and reversed-order consistency are separate reports. They do not change promotion ties. Shared embedding costs remain once at their producer; aliases add no independent observations or calls.

The four P3/P5 configurations at cap512 remain in the 96-cell coverage table but cannot receive same-runtime/cap replication: their required structures cannot fit. This filter is backed by the coordinator-approved structural proof. All other failed configurations remain rankable. Low fidelity alone does not remove eligibility.

Sort eligible configurations once. Select the first configuration within each of P1–P8, then the first two remaining configurations in that same global order. These ten unique configurations receive proposed replicate IDs1 and2, subject to coordinator authorization. An all-zero family may receive an exploratory allocation under this rule; that is no evidence of quality. Subsequent three-replicate operational aggregates retain all84 planned rows per promoted configuration; unpromoted one-replicate screens remain separate.

Promotion applies to the original sparse rep0 grid. The richer source-only comparison stays separate under its frozen policy and is not pooled as additional replicates. Controls and hybrids are comparators, not extra configurations eligible for these ten slots. No fidelity winner, confirmed best method or final-evaluation claim follows from this sparse development panel.

Six synthetic checks passed for denominator behavior, coverage priority, uncertain-cost accounting, incomplete-cost handling, deterministic ties, and distinct family/global slots. No production scores were read or computed to freeze this policy. Comparative scoring still waits for extra12 and matched-control completion.
