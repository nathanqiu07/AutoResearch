# What the integration audit found and changed

Public evidence at `32513a519ee5b544608e43a0348669bfd235e3de`. Owners implemented the repairs below; the audit reproduced failures, independently retested scoped fixes, and made missing or reused evidence visible. This is a navigation index, not exhaustive coverage.

| Finding / evidence | Practical consequence | Status / limit at this source pin | Owned evidence |
|---|---|---|---|
| **Saved profiles do not guarantee the intended conditioning.** Pilot M1 examples reached choice prediction but exported no principles; pilot M2 was empty. Later personalized requests and downstream05's persona plus eight examples were reconstructed. | Pin the artifact, consumer path and runtime together; distinguish profile delivery from benefit. | Delivery verified in the stated mock/recorded paths. No causal personalization effect established. | [Channel audit][channels]; [Sparse consumer traces][execution]; [downstream delivery][downstream] |
| **Malformed legacy advice could escape fallback.** Returned values could crash normalization; nonfinite feature weights reached ranking as NaN. | Validate returned advice before ranking, including the decisive-evidence path. | Reproduced at `0a54151` / `9616fe8`; no later legacy fix independently verified here. Threshold, clipping and calibration remain separate owner policy choices. | [Confidence findings][confidence] |
| **The new profile contract initially accepted invalid state.** Examples included a one-byte cap admitting 545 bytes, failed response statuses becoming successful, and mutable provenance. | Revalidate loaded profiles and source/config identities; retain empty, unsupported and invalid outcomes. | Six issue groups independently retested as fixed at `05c503e`. A complete request is still not a valid extraction or a calibrated prediction. | [Failures][contract-old]; [repair retest][contract-new] |
| **Runner records could diverge from execution.** Validated inputs/settings could mutate; cache hits bypassed elapsed limits; build identity/settings checks were incomplete. | Bind actual calls to frozen inputs/settings and enforce limits on cached paths too. | Five findings closed in scoped retests at `2b965ee` and `7bb1589`; not blanket live readiness. | [Paired repair evidence][runner]; [follow-up][runner-later] |
| **Source eligibility needs enforcement before consumption.** A legacy mixed-directory fixture admitted withheld text; restricted-span retrieval later excluded the synthetic sentinel. | Filter before retrieval/assembly; regenerate artifacts when permission/policy identities change. | New retrieval/quote paths independently retested; this does not close the legacy-helper finding or establish actual leakage or entailment. | [Legacy boundary][source-old]; [span repair][spans]; [integrated quotes][quotes] |
| **Unknown usage must remain unknown.** Missing/partial usage and transport failure retained reservations and blocked later calls; the earlier lost-partial-usage reporting defect was fixed. | Never treat zero known usage as zero total cost; separate row counts, reservations and requests. | Guard retested through actual runner/adapter/local-ledger code with synthetic transport, including `f6cd4fb5`. Closed 204's zero holds do not erase earlier holds. | [Usage repair][usage]; [later guard][guard]; [closed snapshot][closed] |
| **Original downstream05 omitted cached inputs from its cost basis.** Seven paid rows excluded 40,832 cached tokens; applying the same saved rates changes $1.020504500 to $1.071544500. | Include normalized cached-input fields when checking the claimed conservative estimate. | $0.051040000 basis difference, not an invoice or overrun. Owner-reported correction/future fix at `7704989d` is separate, not independently retested here. | [Original accounting and later-status boundary][downstream] |
| **Passing mocks did not prove a valid downstream experiment.** Mocks missed a live setup-path failure; original05 primary reviews all rejected and active shutdown state stayed unchanged. | Test realistic setup paths; do not present rejected reviews or simulated file writes as awareness benefit or shutdown prevention. | Setup repair independently retested. Later judging repair is separate; original05 has unequal probe parsing/clipping and no actual shutdown execution. | [Setup repair][setup]; [original terminal limits][terminal] |
| **Rows and aliases are not independent evidence.** Phase1's 112 control rows cover 28 ordered decisions but 14 exact content groups. Sparse aliases reuse included rows; 672 planned personalized slots remain absent. | Show paired units, planned denominators, delivery and reuse separately. | Literal grouping/bindings verified; independently established human judgments, population independence and preference quality are not. | [Observation units][units]; [sparse counts/reuse][execution] |
| **Evidence now has tested recovery routes.** Sparse and original-downstream checks replay from retained bytes; closed204's three snapshots have a separate recovery bundle. | Keep exact scripts, source/input pins, failed attempts and private dependencies with public receipts. | Same-machine, scoped recovery—not full Git/environment recovery or off-device backup. Wider 042 raw retention is not claimed by this index. | [Sparse checkpoint][recovery]; [downstream capsule][capsule]; [three-snapshot recovery][closed] |

The frozen profile runtime’s 512/2,048/8,192 limits measure serialized UTF-8 bytes, not provider tokens. Tests, hashes, byte counts and owner aggregate scores do **not** establish preference accuracy, researcher benefit or scientific validity. Later retention work is outside this source cut. These links navigate current owned artifacts; the [source pins](../../../results/integration-audit/20261115-045/source-pins.json) fix the reviewed commit and bytes. See the [audit overview](README.md) for subsequent packages.

[channels]: README.md
[confidence]: ../../../results/integration-audit/20261115-001/confidence/README.md
[contract-old]: ../../../results/integration-audit/20261115-006/README.md
[contract-new]: ../../../results/integration-audit/20261115-007/README.md
[runner]: ../../../results/integration-audit/20261115-013/README.md
[runner-later]: ../../../results/integration-audit/20261115-016/README.md
[source-old]: ../../../results/integration-audit/20261115-005/findings.md
[spans]: ../../../results/integration-audit/20261115-023/findings.md
[quotes]: ../../../results/integration-audit/20261115-030/FINDINGS.md
[usage]: ../../../results/integration-audit/20261115-014/FINDINGS.md
[guard]: ../../../results/integration-audit/20261115-028/FINDINGS.md
[downstream]: ../../../results/integration-audit/20261115-039/PUBLICATION.md
[setup]: ../../../results/integration-audit/20261115-022/README.md
[terminal]: ../../../results/integration-audit/20261115-039/FINDINGS.md
[units]: ../../../results/integration-audit/20261115-031/README.md
[execution]: ../../../results/integration-audit/20261115-037/FINDINGS.md
[recovery]: ../../../results/integration-audit/20261115-040/README.md
[capsule]: ../../../results/integration-audit/20261115-041/PUBLICATION.md
[closed]: ../../../results/integration-audit/20261115-042/PUBLICATION.md
