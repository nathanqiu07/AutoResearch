# Morning handoff

Updated 2026-11-15T16:45:18.328057+00:00. All paid runs, scientific checks and authorized finite evidence copies are complete. Coordination continues through the 9 a.m. Pacific cutoff.

## Supported decision

**No personalized method has earned promotion over the simple controls in these campaign panels.** P8 remains an experimental candidate selected by a development rule, not a validated winner or Gio's own preference model. The writing panel has little room to beat generic prediction; the response-preference studies found no clear benefit from correct-user history or added method complexity.

This campaign did not evaluate final-test users. All reported results are development results. Planned accuracy counts failed or unavailable predictions as wrong; accuracy among delivered predictions is a separate, selected view.

## What was searched

The writing-profile screen covered **eight families × three UTF-8 byte caps (512, 2,048, 8,192) × two evidence policies × two researchers = 96 cells (48 configurations across two researchers)**. Evidence policies allowed only explicit statements, or allowed inference when marked.

| Family | Representation |
|---|---|
| P1 | General summary |
| P2 | Summary organized around research tasks |
| P3 | Model-filled fixed questionnaire |
| P4 | Atomic claims |
| P5 | Conditional rules |
| P6 | Principles organized by research decision |
| P7 | Target-versus-peer comparisons |
| P8 | Competing hypotheses, conflicts and uncertainty |

The screen produced 48 usable profiles and 635 correct predictions out of 1,344 planned. It included no-profile, name-only, raw-evidence, lexical, semantic, memory and hybrid controls. Ten configurations then received two further extraction replicates. P8 at 8,192 bytes ranked first under the frozen operational rule; P4 at 512 bytes ranked second but was outside the predeclared common-cap scaling panel. P8 had **zero pooled gain over same-cap raw evidence** across the three scheduled replicates. Repeated orders and replicates still cover only **14 underlying judgments from two researchers and three target source groups**.

The [full-grid report](https://github.com/nathanqiu07/AutoResearch/blob/8fb6246e311dac1f885dc4b04bd9384aecc858c2/docs/overnight/gio-profile-20261115/handoffs/04/SPARSE_DEVELOPMENT_REPORT.md) and [three-replicate report](https://github.com/nathanqiu07/AutoResearch/blob/2fb4f52377a114188bdd68455e8fe081a98b3ece/docs/overnight/gio-profile-20261115/handoffs/04/THREE_REPLICATE_DEVELOPMENT_REPORT.md) preserve the full comparison, failures and selection rule. These P1–P8 writing representations are separate from the original M0–M7 choice-model interface.

## Researcher-panel findings

- **Consumer scaling reached a ceiling.** Saved P8 profiles scored 28/28 with both Sol and Astra. Generic, raw-evidence and retrieval controls also scored 28/28. This does not establish a profile benefit or an ordering of model sizes. [Report](https://github.com/nathanqiu07/AutoResearch/blob/2a2700ea9c43112869132aa9da84f660d8ad301d/docs/overnight/gio-profile-20261115/handoffs/04/FIRST_STAGE_SCALING_REPORT_v2.md).
- **Richer writing did not help this implementation.** It delivered 581 correct rows out of 1,344 planned, versus 635 for sparse writing. On 426 jointly valid rows, the counts were 394 versus 398. This is not evidence that more writing generally harms personalization. [Report](https://github.com/nathanqiu07/AutoResearch/blob/25993ec86a8abab24b0901528e636819cf387016/docs/overnight/gio-profile-20261115/handoffs/04/RICHER_SOURCE_COMPARISON.md).
- **The profile swap is observational.** Swapped P8 scored 24/28, versus historical own-profile 27/28 and generic 26/28. Different collection times and the small repeated panel prevent a causal mismatch claim. [Report](https://github.com/nathanqiu07/AutoResearch/blob/0c724a5143f486d45a1811d4f449f7a86703ad90/docs/overnight/gio-profile-20261115/handoffs/04/EXPLORATORY_OWNSWAP_REPORT.md).
- **Fresh extraction exposed delivery limits.** Only one of four new P8 profiles fit the frozen cap; its 14 predictions matched the perfect generic control. The final P7/P3 batch delivered 98/98 correct predictions, also with no accuracy advantage over generic controls. Across the joint three-method/three-model panel, 180/252 planned rows were correct, 182 delivered and 70 missing. P7 also uses peer evidence, so its information condition differs. [Fresh P8](https://github.com/nathanqiu07/AutoResearch/blob/ee1964cf9863013d85fbda1cbc55965b646b942f/docs/overnight/gio-profile-20261115/handoffs/04/PRIMARY_AC_REPORT.md), [joint report](https://github.com/nathanqiu07/AutoResearch/blob/86447a25a34566a96bd986f0ab330387f48c0145/docs/overnight/gio-profile-20261115/handoffs/04/JOINT_SCALING_REMAINING98_REPORT.md).

These are source-backed proxy judgments, not direct evidence of Gio's future research choices or improved research outcomes.

## Recorded response-preference findings

These studies reuse a **64-user development cohort**. More packets or phases do not add users. Labels are human-rating-derived pairwise response preferences with model-based filtering; they are not necessarily direct binary elicitation or research-taste labels.

On the new 56 users, the original no-history baseline averaged 48.65% planned accuracy and raw history 47.78%; their paired interval included zero. The completed method follow-up retains all 1,836 planned cells: 1,480 valid and 356 failed or unavailable.

| Follow-up method | Equal-user planned accuracy | Difference from historical same-user M1; 95% interval |
|---|---:|---:|
| M4, full history | 44.955% | −2.827 points [−10.059, +3.865] |
| M4, matched five | 47.029% | −0.752 points [−7.532, +5.791] |
| M5, hybrid | 34.910% | −12.872 points [−20.782, −5.061] |
| M6, filtered hybrid | 34.090% | −13.692 points [−22.022, −5.640] |

M4 shows no clear advantage here. M5/M6 have lower planned accuracy and delivery coverage, including 127 predeclared unavailable cells each. Complete-user differences are much smaller, but those users were selected by successful delivery. That does not identify a causal representation disadvantage. History exposure, fixed method order, cache-only fits and exploratory development selection remain limits. Independent checks reproduced the figures and preserved earlier phase results unchanged.

The fresh paired history study used **Luna with no reasoning**, averaging all 64 users equally over 516 planned targets per arm. Correct-person history achieved **50.16%**, versus **51.99%** with count-matched wrong-person history: **−1.83 percentage points**, with a descriptive conditional interval of **−5.75 to +2.08 points**. Correct counts were 256/516 and 264/516; valid outputs were 514 and 515. Joint-valid and complete-user sensitivities also included zero difference.

This establishes neither equivalence nor general personalization failure. Donor cycles link users; topic, length, task mix and history-label distributions were not matched. The protocol preceded these new outcomes but followed earlier analysis of the same cohort. There was no fresh no-history arm in this paired study. [Independently checked reference reports](https://github.com/nathanqiu07/AutoResearch/blob/e371f6fd26224982ccbc8a103ac23655d7fa7257/docs/overnight/gio-profile-20261115/labeled-reference/HISTORY-CONTROL.md).

## Usable artifacts and ownership

| Piece | Existing owner and frozen configuration | Handoff limit |
|---|---|---|
| M0–M7 choice-model interface | Reference owner 10 and shared infrastructure 01. [Contract](https://github.com/nathanqiu07/AutoResearch/blob/21468992f1d7b0ea300aa4abe3f6198937045d6f/docs/user-models/README.md#shared-contract). Final follow-up runtime `9664557`; paired-history runtime `63e11c9`. | Supports fit, predict, save/reload and artifact export. Predictions include choice and confidence. No personalized winner was validated; raw confidence remains uncalibrated. |
| Experimental writing-profile P8 | Builder 08, infrastructure 01, evaluator 04. Saved explicit-only profile, 8,192-byte cap; quote-based extraction. | A development candidate, not a drop-in claim about Gio or a replacement for the M0–M7 interface. |
| P8 auditor-context export | `gio-overnight-downstream`, Petri auditor-context adapter workstream. [Exporter and runnable fixture/export commands](https://github.com/nathanqiu07/AutoResearch/blob/6695382f5573a797ff4692a7bbde49ee4c45ac50/docs/user-models/petri-neutral-profile-adapter/README.md). | Offline export only. It preserves contents, provenance, null weights and assumptions. Future integration must place it in the auditor, verify that it does not reach the target or judge, and test utility. |

The completed downstream shutdown experiment used the earlier **Hobbhahn M2 profile in its downstream artifact family**, not this P8 export. Its three-arm comparison established neither a profile benefit nor observed shutdown interference; later reviews retained realism concerns. It is a separate research-utility question, with one scenario/attempt per condition.

Our campaign code remains on isolated branches. Our direct main pushes changed coordination records; teammates have separate main-branch work.

## Accounting

| Lane | Recorded known/conservative estimate | Retained uncertain bounds |
|---|---:|---:|
| Closed profile lane | $5.693403660 OpenAI | $0.027883125 OpenAI |
| Reference, including the separate paired study | $1.837474500 OpenAI | $0.017122125 OpenAI |
| Six identified downstream bundles | $2.437342500 OpenAI + $0.167123650 OpenRouter | $0.025845760 OpenRouter |

The reference total counts 122 baseline/follow-up packets plus 64 paired-history packets once each. The last 16 contributed $0.101062375, already included. They made 764 wrapper attempts but 763 observed HTTP events: one consumed-request block happened before transport after an invalid-JSON fit. The same failed fit can affect several target cells; failure cells are not failed API requests.

These are estimates, not invoices or verified balances. Older downstream spending scalars have unresolved overlap/provider split, so this is not a verified lifetime project total. No old uncertain holds were released. Project ceilings remain $500 OpenAI plus $500 OpenRouter, including prior spend/reservations; caps and reservations are not consumed credits. [Profile accounting](profile-lane-closed-accounting-v1.json), [independent profile check](profile-lane-accounting-review-v1.json), [downstream interpretation](https://github.com/nathanqiu07/AutoResearch/blob/6695382f5573a797ff4692a7bbde49ee4c45ac50/docs/user-models/matched-shutdown-05/accounting/cost-interpretation.json).

## Preservation and remaining limits

Used development labels, closed reference runs and paired-history evidence have private copies checked within their assigned custody. The paired analysis/review-file addition is also preserved. The final 16-packet copy is also complete: 3,244 exact source tuples, 30,661,099 logical bytes and 3,143 distinct content objects. The reference owner checked sources before and after copying and independently reread destination hashes and exact membership. The evaluator reviewed metadata and custody; this was not an external raw-payload audit.

The new scaling/swap copy retained 1,814 allowed records as 1,526 distinct objects; 15 excluded records stayed unopened. It covers 84,896,695 logical bytes and 65,622,971 distinct retained bytes. The audit owner reports source checks, a separate destination verifier and saved-bundle recovery passed. Gio approved sharing these new completion totals; that permission excludes private archive paths, hashes and contents.

Copies are verified for their enumerated records. Complete original sparse/promotion dependency coverage, packing/trace-map dependencies and a complete campaign restore are not established. The final numerical verification receipt is retained, but its referenced independent arithmetic script is outside that finite inventory. This is a coverage limit, not evidence that those files are lost. Scientific versions remain pinned in Git. Late control sources also have a separate private copy and an independent byte/permission check. Source-only copies do not preserve private results; credentials and live databases are excluded.

The older archive location/hash transfer remains held by automatic approval review pending its existing user question. It is separate from the approved new totals and does not indicate a failed local copy. Private coordination changes also remain local after their full publication was rejected; this public summary excludes that metadata.

## Next decision

**No successor study is selected, and no further paid work is queued.** The earlier Sol reference proposal remains unrun. Gio should choose whether a replication of the same controls with another model, or a fresh direct-choice research panel, best answers the next question. Evaluator 04 should freeze the targets, split and claim limits before reference owner 10 runs any agreed follow-up. This campaign's negative results do not choose that study automatically.
