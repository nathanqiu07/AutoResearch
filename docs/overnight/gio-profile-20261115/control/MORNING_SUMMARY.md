# Morning handoff — working draft

Updated 2026-11-15T15:44:00.852772+00:00. The campaign is still running; the final handoff is due by 9 a.m. Pacific. This page will be updated with the remaining results. Owner reports and earlier checkpoints remain unchanged.

## Decision supported so far

**No personalized method has earned promotion over the simple controls.** Keep the selected P8 object as an experimental candidate, with its assumptions and uncalibrated confidence visible. Do not describe it as a validated winner or as Gio's own preference model. The researcher panel is too small and reaches a generic-control ceiling with Sol and Astra to establish a useful personal-profile benefit. The recorded response-preference panel is more discriminating, but its closed results also do not show a clear benefit from added complexity.

Final-test users remain untouched. All findings below are development results. The selected configurations were chosen using development outcomes; their follow-up scores are exploratory.

## What the three evidence sources say

| Evidence | Supported result | Main limit |
|---|---|---|
| Researcher writing and source-backed choices | With saved P8 profiles, Sol and Astra each scored 28/28. Both also scored 28/28 without a profile, with raw evidence, and with either retrieval control. | Only 14 underlying judgments, shown in both orders, from two researchers and three target source groups. Repeated rows and aliases do not create more judgments. |
| Recorded response preferences | On the closed new-56-user baseline, planned accuracy, averaging each user equally and counting missing predictions wrong, was 48.65% for no history and 47.78% for raw history. The paired interval included zero. More complex methods had lower planned accuracy and, in several cases, lower delivery. | These are human-rating-derived response preferences with model-based filtering, not direct evidence of research taste or utility. Delivery-conditioned subsets are selected subsets. |
| Downstream shutdown experiment | The completed three-arm comparison did not establish a profile benefit or observed shutdown interference. Later reviews improved citation validity while retaining realism concerns. | One scenario/attempt per condition, simulated state, and forced exposure. The run used the earlier M2 artifact; P8 was not tested in this workflow. |

The prospective own-versus-wrong-history study has completed all 64 user packets. Its frozen scoring code passed independent review; numerical results are pending. It tests whether matching history to the correct person matters on the recorded-preference panel. History count is matched; topic, length, task mix, and label distribution are not. Reused donor histories also limit an independent-user interpretation of its uncertainty interval.

## Researcher-panel findings worth retaining

- Richer writing produced 581 correct delivered rows out of 1,344 planned, versus 635/1,344 for sparse writing. On the 426 rows valid under both conditions, the counts were 394 versus 398. This implementation did not benefit overall; it does not show that more writing generally harms personalization.
- Swapped P8 profiles scored 24/28, versus historical own-profile 27/28 and generic 26/28. Conditions were collected at different times. This observational difference does not isolate a causal effect of mismatch, and the one-row own-versus-generic advantage is not a reliable benefit estimate.
- Fresh P8 extraction yielded one admissible profile out of four. Its 14 predictions were correct, matching the saved-profile and generic controls. Three builds exceeded the frozen byte cap; their 70 planned descendant slots remain missing. These cap failures measure delivery under the encoding rule, not preference-inference quality.
- The remaining P7/P3 batch scored 98/98 on delivered predictions from seven admissible profiles. Same-consumer generic controls were already perfect, so there was no accuracy advantage. Its 14 missing descendants remain in the 112-slot plan. Across the full joint three-method/three-model panel, 180 of 252 planned rows were correct, 182 delivered, and 70 missing. P7 uses a distinct evidence condition; delivery differences do not establish better preference inference.

Owner reports: [richer writing](https://github.com/nathanqiu07/AutoResearch/blob/25993ec86a8abab24b0901528e636819cf387016/docs/overnight/gio-profile-20261115/handoffs/04/RICHER_SOURCE_COMPARISON.md), [saved-profile consumer comparison](https://github.com/nathanqiu07/AutoResearch/blob/2a2700ea9c43112869132aa9da84f660d8ad301d/docs/overnight/gio-profile-20261115/handoffs/04/FIRST_STAGE_SCALING_REPORT_v2.md), [fresh P8 extraction](https://github.com/nathanqiu07/AutoResearch/blob/ee1964cf9863013d85fbda1cbc55965b646b942f/docs/overnight/gio-profile-20261115/handoffs/04/PRIMARY_AC_REPORT.md), [profile swap](https://github.com/nathanqiu07/AutoResearch/blob/0c724a5143f486d45a1811d4f449f7a86703ad90/docs/overnight/gio-profile-20261115/handoffs/04/EXPLORATORY_OWNSWAP_REPORT.md).

[Joint P7/P3 scoring report](https://github.com/nathanqiu07/AutoResearch/blob/86447a25a34566a96bd986f0ab330387f48c0145/docs/overnight/gio-profile-20261115/handoffs/04/JOINT_SCALING_REMAINING98_REPORT.md).

## Execution and accounting

The completed scaling ledger contains **404 calls and $4.934060 in known recorded usage**, with no new unresolved calls. This is cumulative: the final 98-call tranche contributed $1.050250, already included in that total. The separate profile-swap run contributed 28 calls and $0.005598. These are conservative recorded estimates, not invoices. Across the entire closed profile lane, known or conservative recorded estimates total $5.693403660, with $0.027883125 in four older uncertain request bounds retained separately. The [closed accounting](profile-lane-closed-accounting-v1.json) and [independent review](profile-lane-accounting-review-v1.json) count the prior search, final scaling ledger, and separate swap ledger once each. A final cross-lane reconciliation is pending.

The reference follow-up has stopped twice, each time after an HTTP 400 response with unresolved charge and cause. Across those two segments, 36 packets completed with known accounting, two partial packets contain new unknowns, and 16 remain untouched. All nine historical reference unknowns and $56.11 in gross reference reservations remain retained. Failed and already-consumed requests are excluded; no partial tail is retried. The paired-history control completed 1,031 calls for $0.4189835 in recorded usage, with zero new uncertain charges. Two outputs failed and one planned request was withheld; all remain in the planned denominator. The untouched 16 remain deferred under their original leases until the consumed-failure exclusions and continuation controls pass review. Missing and unstarted planned cells stay visible.

Six identified downstream run bundles total $2.43734250 OpenAI plus $0.16712365 OpenRouter in corrected saved-rate estimates. The latest $1.428817 subset is already included. An OpenRouter unknown bound of $0.02584576 remains held. Earlier historical spending scalars have unresolved provider split and overlap, so this is not an all-time downstream or project total. Gross downstream reservations stay $58 OpenAI/$31.000001 OpenRouter, including the full older $20 reserve per provider. [Owner accounting interpretation](https://github.com/nathanqiu07/AutoResearch/blob/6695382f5573a797ff4692a7bbde49ee4c45ac50/docs/user-models/matched-shutdown-05/accounting/cost-interpretation.json).

Project-wide ceilings remain $500 OpenAI plus $500 OpenRouter, including previous spend and reservations. Allocations and gross reservations are authorization limits, not measured consumption or verified account balances. The paired-history study has 64 issued leases totaling $3.507. Reference gross reservations are now $59.617 within its $68 allocation, including all older $56.11 reservations and holds.

## What can be used, and what cannot yet be claimed

The [offline P8 exporter](https://github.com/nathanqiu07/AutoResearch/blob/6695382f5573a797ff4692a7bbde49ee4c45ac50/docs/user-models/petri-neutral-profile-adapter/README.md) preserves the saved profiles, their source references, null weights, assumptions, and uncalibrated confidence. Its README gives runnable fixture tests and an exact export command. The real exports remain in private local storage under the existing owner’s custody.

This exporter is not connected to the completed Petri experiment. A future integration must place the context in the auditor, verify that it does not reach the target or judge, and run a suitable controlled comparison. Integrity checks do not prove that inferred statements are true or useful. Our campaign code remains on isolated branches; our direct main pushes were coordination records. Teammates may have separate main-branch changes.

## Durability status

Reviewed code and control sources are committed. Earlier private profile204 records have a verified durable archive. The evaluator has also verified a private copy of the four already-used development label/provenance files, totaling 545,981 bytes, within evaluator-only custody. Newer closed scaling, swap, and reference records still have temporary dependencies. The finite scaling/swap copy now has exact authority and excludes 15 out-of-scope records; reference inventory custody review is pending. Source-only Git snapshots do not preserve those private results. Until those copies and manifests are verified, the campaign is not described as fully replayable. Credentials and live databases are excluded from the archive work. Separately, automatic approval review blocked a message transferring old archive locations and hashes from the audit chat to this coordinator; that exact transfer remains held pending the existing user question. New local copies do not authorize or reroute that transfer.

## Before finalizing this handoff

Replace the pending remaining-reference and prospective-history sections with their owner-reviewed terminal results. Reconcile known costs and retained holds without counting aliases or cumulative ledgers twice. Link the final runnable method/export contract and identify any integration gap. Use the paired-history result to choose the next discriminating experiment; do not run more ceiling-bound researcher rows merely to increase the count.
