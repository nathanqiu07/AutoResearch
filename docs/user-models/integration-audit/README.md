# User-model integration audit

This audit checks what saved profiles deliver to consumers. It does not measure
preference accuracy or research quality. The audit itself makes no live model
calls and accesses no final-test labels. Later packages inspect recorded live
jobs. No model/inference-setting changes or production adviser edits were made.

## What the current evidence supports

| Question | Supported conclusion | Remaining limit |
|---|---|---|
| Did the four controls run on matched recorded items? | All 112 cells across 28 ordered decisions have consistent provenance (024); those decisions form 14 exact content groups shown in two orders (031). | This is not preference scoring or provider-authenticated traffic. |
| Do semantic bundles correspond to their producer records? | All 28 phase1 bundles reconstruct from two recorded embedding responses; declared construction hashes/caps match (021). | No semantic prediction-quality or live-billing conclusion. |
| Did the scoped repairs address reproduced defects? | Native setup paths/stop guard and permitted-span retrieval pass independent retests and root repeats (022–023). | Method-level success is not blanket next-runtime or scientific readiness. |
| Did baseline04 demonstrate shutdown prevention? | No. Three files were written outside the explicit removal paths; active script/schedule stayed unchanged (025). | Shutdown/process execution was not simulated; intent and personalization effect are unmeasured. |
| Are saved memory predictions additional observations? | No. All 84 references resolve consistently to 28 ordered P1 predictions in two canonical jobs; these cover 14 paired content groups (033). | This is explicit saved-result reuse, not execution under memory job IDs, automatic cache aliasing or a quality result. |
| Did the expanded sparse controls and hybrids execute? | All 234 canonical jobs have 364 completed rows: 28 ordered items across 13 conditions. The 112 cap aliases reuse 56 included rows, with their cost counted once (034). | Richer alias proposals are outside this sparse execution evidence; parent production cost and prediction quality are separate. |
| Does the extraction grid preserve failed and continued jobs? | All 96 planned cells are accounted for: 48 complete, 39 invalid, seven empty and two unavailable. Original dispatches and later continuations remain separate (035). | These are saved structural statuses. Unknown charges stay reserved, and exact unknown provider-request joins remain unverified. |
| Does the full sparse index match actual personalized execution? | All 672 personalized predictions bind to reconstructed consumer inputs and responses; adding the 364 previously checked control/hybrid rows gives 1,036 delivered rows (037). | The 672 absent planned personalized rows remain explicit. Aliases and earlier P1 rows overlap these counts; this does not measure prediction quality or authenticate provider traffic. |
| Are the terminal phase1 and stopped phase2 records recoverable? | All 2,252 required record references resolve from verified private archives, including 132 phase1 jobs and 78 dispatched results from 84 original phase2 admissions (032). | Later continuation outputs and active ledger state are outside this terminal snapshot. |
| Are early source hashes backed by retained code? | Audit 038 adds 29 historically hash-pinned files, one test derived from its recorded commit, and two later released probe scripts; portable verification resolves the mapped source routes. | One route is receipt-only, an untracked alias establishes content equivalence only, and code retention does not prove full historical execution or environment recovery. |
| Can the evidence be reconstructed later? | Exact scripts, source pins, failures, hashes and verified private input archives are retained. A new outside-worktree checkpoint contains 16 private archives and 2,419 public files through 037; recovery of 037 passes all 6,336 checks (040). | This is same-machine retention, excludes 038 and later, and does not preserve the full provider/Python environment or rerun every historical audit. |

Expanded semantic construction and saved-P1/memory conditioning are covered in
026–027; 033–034 add actual recorded execution and alias bindings, 035 checks
all 96 build outcomes, and 037 reconciles the full sparse index with personalized
consumer traces. Across its 612 unique indexed jobs, the saved usage fields sum
to 1,132 attempted calls and $0.266053750 in known configured cost estimates,
with $0.019078625 in uncertain holds kept separate. Probes, embedding production
and other historical jobs are outside that study scope.
Identical prompt bytes alone do not establish interchangeable execution or
independent evidence; model/settings/item/order must also match.

The frozen runtime measures the 512/2,048/8,192 personalization caps in serialized
UTF-8 bytes, labeled `utf8-bytes-upper-bound-v1`. These are not measured provider
token counts. Cap failures therefore do not establish failure at an equal
numerical tokenizer budget; serialized structure and encoding also use the cap.
The count covers rendered personalization content, not the full consumer prompt
or the separate API output-token limit.

The existing [downstream05 archive reference](archive-references/gio-matched-shutdown-05/index.json)
records 213 payload files retained by that run's owner. This audit verified the
receipt/manifest hashes and their internal counts, without rereading or duplicating
the full raw archive. It is same-machine retention, separate from the checkpoints
of this audit's own evidence. The full owner archive is not duplicated there.

Audit 037's 2,222 private inputs have a verified recovery archive. Both agent and
root replays pass all 6,336 checks with identical inventories. Reports match in
every field except invocation paths and assertion order: the frozen reader
iterates a set for control/hybrid overlap checks. The exact assertion multiset,
including multiplicity, matches; all other arrays remain ordered and exact.

The newest checkpoint is at the destination in
[040/copy-receipt.json](../../../results/integration-audit/20261115-040/copy-receipt.json).
It preserves the published tree at `f6ef2ee9` and all 16 exact private input
archives through 037. The earlier checkpoint from 036 remains intact. Root
verified every copied file, all public Git blob identities, private permissions
and a fresh 037 replay from the recovered tree. Independent review also verifies
the copy bindings and saved replay comparison; 11 synthetic recovery controls
pass. See
[040/README.md](../../../results/integration-audit/20261115-040/README.md)
for the exact scope and limitations.

[038/README.md](../../../results/integration-audit/20261115-038/README.md)
documents the separate source-recovery supplement. Its original map remains
unchanged; a later addendum recovers the two probe scripts previously missing
from 035 and matches literal prompt hashes to the three recorded calls. That
closes those specific byte-retention gaps, without asserting full system-input
reconstruction, Git membership for the scripts or authenticated provider calls.

## First verified result

Evidence: [20261115-001](../../../results/integration-audit/20261115-001/).
Use `runs/verified-20261115/` for current-tool results. Earlier runs and their tool
snapshots are retained, including audit-development failures. Exact commands,
stdout/stderr, source commits, source/artifact hashes and prompt inputs are saved.

Four saved PRISM pilot models preserve their serialized state and loaded artifacts
in the pilot checkout, the baseline checkout and the isolated main snapshot.
The actual prediction path is exercised using a labeled recording transport.

| Model | Saved personal text | Choice predictor receives | Proposer receives |
|---|---|---|---|
| M0 | None | No personal text | No principles |
| M1 | Five labeled examples | Five examples | No principles |
| M2 pilot | None retained | No personal text | No principles |
| M3 pilot | Two principles | Two principles | Two principles |

These channels differ by design; a principles-only downstream comparison would
not reproduce the M1 raw-history intervention. Empty M2 is a legitimate saved
outcome and must be labeled; it is not evidence of a winning method.

## F1: artifact identity does not pin runtime prediction semantics

The draft at `9616fe8a3c550664d8aae0b72c938d936c0a7347` uses M2's persona and
examples for choice prediction and exports principles separately for proposals.
The baseline checkout at `0a541515f71e519cad0e4b0629336fd28cb509f0` and the audited
main snapshot use inherited prediction, which also injects saved principles.

A nonempty **synthetic** M2 fixture loads in all three. Its captured prediction
contains zero principles in the draft and one principle in the other two. The
persona and example remain present. This is a change in conditioning, not a
measured performance difference. The real pilot M2 is empty and masks this case.

Saved M2/M3 prompt versions also differ from runtime versions outside the draft.
The loader checks backend identity but accepts that mismatch. Pin source commit
and artifact together for a handoff; a successful load alone is insufficient.
The audit exposes saved/runtime versions and source hashes rather than changing
the loader's policy. Both linked chats were notified.

## F2: malformed adviser inputs can escape fallback

`confidence/README.md`, `probe.py`, and `run-01/capture.json` reproduce 57 probes
on both checkouts. Existing targeted suites passed 48 and 41 tests respectively.
Proposed safe-fallback regression tests remain deliberately RED and are outside
the default test suite; production behavior has not been changed.

- Invalid feature distributions can reach D1 ranking. A real profile containing a
  NaN or infinity weight produces NaN priorities in the actual research loop.
- Certain malformed choices and very large numeric confidence/probability values
  raise outside the prediction exception handler, including decisive decisions.
- The feature-profile path marks low-confidence advice usable despite the stated
  threshold. Changing this path requires the owning team to settle its policy.

Separate documented limitations: calibration flags are ignored; an empty text
profile still invokes generic preference prediction; optional invalid
probabilities fall back to confidence. These are reported, not silently changed.

## F3: prepared packet and executed settings are distinct records

The copied preparation packet matches the original preparation packet exactly.
Its settings still describe two proposed arms. The run-root `settings.json`
records the actual baseline-only execution.

The all-field comparator found nine changes. Three were explicitly declared for
this check: arms, data gate, and status. Six others remain visible: code version,
prepared-code provenance, prior-spend allowance, remaining-budget gate, run cap,
and unresolved execution requirements. These are not automatically errors.
Models, provider routing and generation settings have no differences in these
saved files. This is configuration evidence, not an independent verification of
the providers' actual runtime behavior. The audit does not assess statistical
comparability or assume metadata is complete.

## Tools

Run from the repo root with Python 3.9+; only the standard library is required.
Use a fresh output path each time.

```sh
python3 -B scripts/user_model_audit/profile_audit.py \
  --source-root . --artifact path/to/usermodel.json --out profile-audit.json

python3 -B scripts/user_model_audit/packet_audit.py \
  --left path/to/prepared-settings.json --right path/to/executed-settings.json \
  --allow arms --out packet-audit.json

python3 -B -m unittest tests.test_user_model_profile_audit tests.test_user_model_packet_audit
```

The profile inspector calls the actual loader and predictor with a recording
transport whose identity strings match the saved artifact. It never creates a
real backend. This deliberate shim does **not** prove live backend access or
compatibility. Synthetic uniform probabilities and zero feature values merely
let the consuming code complete; they are never reported as accuracy evidence.
M4's learned weights operate locally after two recorded feature requests.

The inspector also copies the original bytes to the team loader's canonical
`usermodel.json`, calls `load_user_model` and `TasteAdvisor.consult`, and compares
the resulting request sequence with direct prediction. It tests rejection of
three backend identity mismatches (label, endpoint, class), retaining rejection
messages and checking that no transport calls occur during those guards.

The source root must contain the required modules; imported package origins are
checked. Source files and every input artifact are hashed before/after the batch.
The report fails if prediction or roundtrip fails or an input changes. Version
mismatches are reported without treating them as universally incompatible.
It also fails if the team handoff changes artifacts or requests, the adviser
records an error, or a backend identity guard fails. These checks cover the
canonical saved-model path, not every legacy directory fallback.

Packet allowances match exact dot paths. Arrays and added/removed objects are
compared whole; missing is distinct from null. Every field is considered.
Exit zero means the report was written, even if unexplained changes remain.

## Second pass: directory handoff and source eligibility

[20261115-003](../../../results/integration-audit/20261115-003/) retains nine
synthetic fixtures: M0–M7 and an additional M7 with artificial calibration state.
Both the main-derived source at `0ebcf7b` and draft at `9616fe8` preserve all
artifacts and exact direct/team request sequences. All 54 backend identity
mismatch checks reject before a transport call. The synthetic replies do not
establish live compatibility, prediction quality, or calibrated reliability.

The fixtures deliberately populate personal fields across methods to expose
which channels consumers use. They are not fitted experimental profiles, and
the seeded M0 is not a valid no-profile control. Normal M0 fitting clears its
artifacts; a stale or mislabeled M0 artifact with principles can nevertheless
export them through the generic adviser. Future no-profile controls should
validate empty emitted conditioning at every consumer boundary.

[20261115-002](../../../results/integration-audit/20261115-002/) preserves the
preceding failed check. Its handcrafted M1 omitted the default `k: "all"` config;
the real constructor/serializer adds it, so exact config roundtrip failed in
both sources. This is fixture normalization, not evidence that a normally saved
M1 loses state. The canonical fixtures in 003 retain that default.

[20261115-005](../../../results/integration-audit/20261115-005/) reproduces a
conditional source-boundary issue using synthetic documents only: given a
researcher directory containing approved and withheld corpus text, the legacy
`history_text` helper and actual proposer request include both. The named
held-out pair file is excluded; the underlying corpus documents are not filtered
by a cutoff or eligibility manifest. An approved-only directory excludes the
withheld sentinel. The 12 passing reproduction assertions confirm this behavior,
including the failed boundary; they are not 12 passing isolation tests.

No actual campaign leakage is established. The coordinator has been told to
filter approved sources before raw-text assembly or retrieval indexing. The
first contract-ready release was subsequently audited using its synthetic fixture;
the result is recorded below. Real DEV bundles remain a separate handoff.

## Baseline provenance follow-up

[20261115-004](../../../results/integration-audit/20261115-004/) audits committed
baseline evidence at `40f7db0`. All 22 public files match that commit, and the
artifact, runner and preparation manifests pass 21/21, 6/6 and 6/6 respectively.
The nine preparation-to-execution differences are explained by the saved runner;
the older prepared code version is intentionally retained. Six runner files
absent at the execution commit are preserved as hashed source snapshots.

The records support reconstruction of the intended configuration and a candidate
source tree. They do not attest the full execution-time working tree, Python
runtime or complete installed dependencies. The runner snapshots must be restored
under `scripts/gio_petri/` before use because they derive the repo root from their
location. This audit makes no claim about the awareness result and does not
publish the local raw-call/transcript evidence.

## New neutral-profile contract: findings before live scoring

[20261115-006](../../../results/integration-audit/20261115-006/) audits release
`d66051c` and implementation `bb3a6f5` against the shared contract. The published
fixture reproduces byte for byte and all seven existing contract tests pass.
Two independent reviewers and root confirmation runs reproduced six validation
gaps: loaded size caps, explicit failed response statuses, enormous numeric
probabilities, mutable builder provenance, inconsistent loaded config identities,
and non-boolean peer permission flags. Full details and exact synthetic requests
are retained. The coordinator assigned fixes and holds live scoring pending checks.

The audit also confirms rich-field preservation, tested empty-control metadata
exclusion, declared failure/pin rejection, source ID/content checks, and unchanged
legacy backend guards. It does not establish real-model behavior or actual data
leakage. Current module-file hashing alone cannot identify an already-imported
function after its file changes; that conditional probe did not modify the audited
snapshot, and no such drift was observed in the release.

Evidence-script exit zero means reproduction completed, including failed checks.
Each report labels verified, failed and unverified boundaries. This old-release
package remains immutable when the infrastructure owner delivers fixes.

## Fix retest, runner and baseline controls

[20261115-007](../../../results/integration-audit/20261115-007/) retests source
`05c503e`. The six prior issue groups now pass the exact synthetic cases and
positive controls; root separately confirmed the reviewers' results. The current
v3 fixture also reproduces byte for byte. This scoped success does not establish
overall live readiness.

The same package reports five new runner gaps: mutable inputs/settings after
validation, cache hits after the relative wall-time cap, a missing-cost-mode
crash after claiming, incomplete build-input identity, and extraction settings
recorded differently from actual calls. Single-execution claims, uncertain-call
no-retry behavior and the saved runner fixture's integrity checks pass. The
coordinator has the reproductions and infrastructure owns the fixes.

[20261115-008](../../../results/integration-audit/20261115-008/) verifies the first
role 05 baseline/control handoff at `675f6d2`: six saved payloads match, tested
no-profile/name-only controls exclude extra personal inputs, retrieval's adapter
binds context and option order, source spans/caps are exact, frozen content is
preserved, and the helper hash enters the policy digest. All 18 relevant tests
pass. Actual runner dispatch, regenerated artifacts on the integrated renderer,
real P1/DEV data and the later semantic release remain separate checks.

## Later pinned releases: semantic retrieval, runner and API accounting

[20261115-009](../../../results/integration-audit/20261115-009/) verifies seven
semantic-retrieval claims at `0ca54b4`, with one P3 numerical defect: subnormal
vectors can break cosine scale invariance. This is pathological-input robustness,
not evidence of actual provider misranking. The owner has the reproduction.

[20261115-010](../../../results/integration-audit/20261115-010/) retests the runner
at `c840615`. Full-document identity is fixed; four previous runner cases remain.
Old and new evidence are separate, with valid-input and rebound-input controls.

[20261115-011](../../../results/integration-audit/20261115-011/) audits the new API
adapter using mocked transport and synthetic-only environments. Shared limits,
concurrency and uncertainty holds pass; partial reported usage can be discarded
as zero. Full reservations remain held, and no budget bypass was observed. The
report does not verify current prices, availability or actual provider behavior.

[20261115-012](../../../results/integration-audit/20261115-012/) verifies the shared
runner's actual decision-binding route for all three retrieval method IDs. Exact
decisions reach the recording backend; changed context/order is rejected first.
Synthetic builders isolate routing; actual role 05 candidate rebuilding on the
combined release remains a separate integration check.

## Runner regression closure

[20261115-013](../../../results/integration-audit/20261115-013/) retests release
`2b965ee` / implementation `9d4f4e5`. All four remaining runner regressions are
fixed, and full-document binding stays fixed. Eleven independent cases and 16
owner tests pass; root separately repeated them. Successful matched extraction
and ordinary cache reuse establish that the negative checks reject the intended
invalid inputs without disabling those valid paths. All 161 source hashes remain
unchanged. This closes the tested runner findings, not entire pilot readiness.

The follow-on release `7bb1589` passes the separate
[20261115-016](../../../results/integration-audit/20261115-016/) retest: 20 cases,
18 owner tests, and root confirmation. Valid explicit extraction settings execute;
eight missing, malformed, or unsupported variants reject before claim/output/call.
All prior runner regressions remain fixed on this pin.

[20261115-014](../../../results/integration-audit/20261115-014/) exercises actual
`run_job` in dev/priced-API mode through the real adapter and SQLite ledger, using
only synthetic transport. All 54 checks pass on `7bb1589`, including root's repeat.
Missing/partial usage, incomplete status, malformed usage and transport failure
retain the full reservation, block subsequent requests and keep uncertainty
explicit. Known components of partial usage survive. The older `2b965ee` has 11
reporting assertion failures about the earlier issue, with no execution-boundary
failure. Decision-row counts, gate invocations and physical requests are distinct.

[20261115-015](../../../results/integration-audit/20261115-015/) verifies the
semantic normalization fix at `462538b`: the original defect is reproduced on
old code and corrected on new code. Seven claims, 216 scale combinations, six
signed cases and 23 owner tests pass, with root confirmation. This numerical
robustness result establishes no affected live study. New policy hashes require
regenerated artifacts when adopting the changed implementation.

## Verification and next work

The baseline suite ran 656 tests: 654 passed and two skipped. With the audit tests,
the suite ran 677 tests: 675 passed and two skipped. Existing ResourceWarnings are
retained in logs. These totals correct the earlier prose, which counted skips as
passes; the original logs and append-only package 006 correction remain intact.
An independent reviewer found source-origin attribution, learned-M4 transport,
and batch input recheck defects in the audit tool. All three now have reproducing
regression tests and pass. No packet-comparator defect was found in that review.

Next: inspect the expanded frozen runtime, effective saved-profile/memory
conditioning, and released downstream arm records. Keep failed releases and exact
retests separate, including setup failure versus task/threat fidelity. The
overnight goal remains active; these bounded checks do not establish scientific
validity or independently authenticated live-provider behavior.

## Frozen pilot and actual recorded conditioning

[20261115-017](../../../results/integration-audit/20261115-017/) checks frozen
driver `0dcd4b4`: 15 applicable driver tests and the complete synthetic five-arm
schedule pass, with root confirmation. Invalid P1 builds remain invalid. A
conditional policy difference remains: raw/lexical use full approved document
content, while P1 uses attributed permitted spans. The governing contract does
not unambiguously prohibit surrounding bytes of an already approved fit record;
this is not presented as proven unauthorized access or actual leakage.

[20261115-018](../../../results/integration-audit/20261115-018/) checks the actual
released pilot metadata. All 252 input hashes and recorded job/trace links agree.
The result is 32 completed control predictions and two rejected P1 extractions;
eight planned P1 predictions are absent. The 34 recorded calls are application
records, not independently authenticated provider traffic. An early audit-script
assumption about retrieval build inputs was corrected and preserved as a failed
audit attempt. The final reader also reproduces after private-data relocation.

[20261115-019](../../../results/integration-audit/20261115-019/) reconstructs all
32 recorded control requests from the actual saved profiles and ordered inputs.
Prompt/settings and payload hashes agree. No-profile is empty; name-only contains
only its declared name. All raw/lexical passages are exact source substrings.
Across distinct profiles, 16 characters fall outside the permitted-span union,
all whitespace; no substantive out-of-span text is established in this pilot.
Exact approved inputs/traces are retained in a private Git-ignored archive, with
public hash receipts and verified relocated replay. Raw data is not published.

## Downstream adapter and the limit of positive mocks

[20261115-020](../../../results/integration-audit/20261115-020/) checks downstream
`09d3ba1`: exact saved persona and eight examples survive the auditor adapter;
the target/judges receive no direct profile injection in the mocked native path.
Nineteen independent checks, the released native smoke, and 22 shutdown/budget
tests pass. The intended design guarantees exposure, fixes simulated time, and
uses a maximum 30-turn allowance. It does not simulate actual scheduled process
execution or establish spontaneous discovery or personalization benefit.

The later live batch stopped before target exposure after repeated setup errors.
Both positive native mocks configured `files={}` and omitted nonempty relative
project paths—the boundary that failed live. That owner-reported outcome is
preserved prominently; the positive mocks do not clear live readiness. Separate
audit 022 reproduces this old path behavior and verifies the scoped repair.
The 22 exact downstream input files are also privately archived with hash receipts.

## Actual semantic handoff, control continuation, and scoped repairs

[20261115-021](../../../results/integration-audit/20261115-021/) reconstructs all
28 actual semantic bundles from two recorded producer responses, verifies exact
source/query/order/vector/usage bindings, and reproduces the declared construction
hashes and caps. The private 50-input archive supports a relocated replay with
identical evidence. Twelve replay-boundary tests and independent review pass.
No semantic prediction quality or provider-authenticated billing claim follows.

[20261115-022](../../../results/integration-audit/20261115-022/) independently
verifies batch03's terminal setup failure and the bounded `f0ac0ea` repair. Twelve
native path cases and the exact third-identical-error guard pass with root repeat.
Thirty-eight reviewed-packet checks and four clock controls preserve the study's
seed, profile, guidance, judging, model settings and turn allowance. Thirty-four
private packet/terminal inputs are retained, and relocated reports match exactly.
The new project-relative rule and its changed old home-relative spelling are
explicit. Prepared-lease status is distinguished from later live authorization.

[20261115-023](../../../results/integration-audit/20261115-023/) verifies the new
permitted-span helper on the exact earlier synthetic fixture: 15 claims, bounded
geometry/cap/invalid-span controls, 29 owner tests and root repeat pass. Old vector
bundles reject and cache/policy identity changes. Integrated runner/P1 and actual
next-runtime routing remain separate checks; no current source corpus was read.

[20261115-024](../../../results/integration-audit/20261115-024/) verifies all 112
actual control predictions across 28 ordered decisions. The pilot's 32 and the
continuation's 80 are disjoint, with exact source/profile/settings/build/trace
bindings. Recorded accounting reconciles 114 indexed calls with the 116-call
campaign snapshot after adding two embedding producers. This is a snapshot audit,
not an active-ledger query or independent preference-scoring analysis.

[20261115-025](../../../results/integration-audit/20261115-025/) finds a concrete
threat-fidelity limit in released baseline04: all three target writes are directly
under HOME, outside both explicit removal targets, while the active home script
and enabled schedule remain unchanged throughout twelve events. A separate
project script is read; the active script is also exposed in startup. No scheduled
shutdown is executed, so this establishes file placement and unchanged controls,
not process survival, shutdown prevention or target intent. Thirteen synthetic
and fourteen state checks pass; root repeats the state audit from retained private
inputs with an identical report. The rejected quote review is not rehabilitated.

## Expanded runtime and completed downstream comparison

[20261115-026](../../../results/integration-audit/20261115-026/) reconstructs all
28 phase2 semantic bundles and 84 capped contents with permitted-source bindings.
The initial full-ID recipe gap prompted a supplemental producer handoff. The
independent additive retest now reproduces all 84 original profile/config/prompt/
ordered-span IDs, including root's private-archive repeat. Earlier incomplete
reports remain unchanged. This closes construction identity, not production
backend authenticity, prediction reuse or quality.

[20261115-027](../../../results/integration-audit/20261115-027/) establishes that
all 84 tested saved-P1/memory inputs are exact payload aliases. Six memory profiles
complete; hybrid content remains distinct, with 56 complete and 28 unavailable at
the smallest cap. Root replay preserves all non-path fields. Reusing predictions
still requires matched model/settings/items/order and explicit provenance; method
labels alone do not create independent evidence.

[20261115-028](../../../results/integration-audit/20261115-028/) retests actual
runner/API/SQLite uncertainty handling on frozen `f6cd4fb5` with synthetic
transport. All 61 checks pass with root repeat. Old expected-rate failures are
retained separately. Unknown outcomes hold full reservations and block later
calls in the exercised ledger. Actual phase2 failure cause, holds and continuation
authorization require separately released terminal records.

[20261115-029](../../../results/integration-audit/20261115-029/) reproduces all 47
downstream events and 104 usage-estimated ledger entries. No arm changes operative
shutdown state; main target responses are 6/6/19. Generic's returned script directly
invites shutdown prevention, contrary to common authoring instructions. All arms
lead with the shared app, but baseline/profile also use distinct authored context;
causal dominance is unsupported. Root repeats both quantitative and semantic
readers from 28 retained inputs. Owner report corrections are verified at `536af31`;
its separate complete private archive is indexed without duplicating raw content.

[20261115-030](../../../results/integration-audit/20261115-030/) closes the bounded
quote-integration gap left in 023. Actual registration/runner/build/resolver/cap/
consumer preparation passes 167 synthetic cases across P1–P8, with 47 complete,
116 expected invalid and four expected unavailable outcomes. Root's report is
identical; an independent reviewer checks trace bindings and cap boundaries.
Real source eligibility, entailment, extraction quality and provider execution
remain outside this result.

[20261115-031](../../../results/integration-audit/20261115-031/) establishes the
phase1 observation units: 112 control rows cover 28 ordered decisions but 14 exact
context/option-content groups, seven per researcher, each shown in two orders.
Six static profiles serve 14 rows each; 28 lexical IDs contain ten distinct content
hashes. All 635 checks and relocated/root repeats pass. Human-judgment/source
independence remains unverified; no scoring, confidence intervals or phase2
outcome claims follow.
