# User-model integration audit implementation plan

> For agentic workers: use the executing-plans workflow. The user approved the concrete audit brief in chat and asked to start and continue overnight.

**Goal:** Make profile-to-decision integration and comparison assumptions inspectable and reproducible without changing model or experiment settings.

**Architecture:** Standalone standard-library audit scripts load saved model objects through the actual selected checkout, substitute a clearly labeled recording transport, and retain the exact constructed input. A separate packet comparator checks every configuration field against explicit allowed differences. Confidence probes exercise the real adviser and loop using local fixtures.

**Tech Stack:** Python 3.9+, unittest, Git; no dependencies or paid calls.

**Spec:** User-approved audit brief in chat 01a1de44-b76b-7290-9753-ba528b42819e: conditioning table, offline checks, comparison check, findings report. Continue reviewing linked chats overnight and preserve reconstruction evidence.

## Global constraints

- No production model, inference setting, prompt, confidence threshold, or live-run mutation without telling Gio first.
- Additive scripts/tests/docs; isolated branch; no other agent's files changed.
- Every report pins artifact hashes and source checkout identity. Synthetic transport output is never evidence of preference accuracy or research utility.
- No final preference users evaluated. No network/model call from audit tools. No credentials read.
- Unknown or unsupported conditioning is explicit. An empty profile is an observed result, not automatically a defect.
- Preserve failures, commands, raw audit outputs and negative findings; reports refuse overwrite.

## Review focus

1. M2 prediction and proposer channels differ; inspect actual consuming methods.
2. Empty fields, unsupported method versions and malformed JSON must not appear as successful personalization.
3. Saved identity checks must not be misrepresented as live backend compatibility under a recording transport.
4. Concurrent code/artifact changes must invalidate a snapshot or be clearly recorded.
5. Missing configuration fields differ from JSON null; allowed comparison changes must not hide sibling changes.

## Tasks

- [ ] 1. Profile inspector: `profile_audit.py`, `test_profile_audit.py`. Capture actual load/predict/adviser behavior under offline transport, record source hashes and exact prompt, check save/load preservation, summarize information channels. Verify tests fail before implementation; run deterministic fixture and saved pilot models in both relevant checkouts.
- [ ] 2. Packet comparator: `packet_audit.py`, `test_packet_audit.py`. Recursive all-field diff with exact declared allowances, explicit presence flags, hashes and no statistical-comparability claim. Agent owns these two files.
- [ ] 3. Confidence probes: `confidence/`. Reproduce malformed-value and empty-profile behavior at real adviser/loop boundary. Distinguish bugs from intended thresholds/calibration policy. Agent owns evidence and RED regression cases.
- [ ] 4. Isolated integration: move scripts/tests/docs into native worktree after creation completes; verify relevant and full repository tests, commit/push scoped branch, report findings to both chats. Only audit fixes supported by reproductions; no policy changes.
- [ ] 5. Overnight updates: inspect new artifacts and ownership from both chats, run incremental audits on new pinned inputs, append commands/findings/commit references, retain all runs. Continue while useful new work exists.

## Ledger

- 2026-11-15: Both chats notified of narrow ownership; recurring 30-minute heartbeat created and awaiting final view verification.
- Native create_worktree call remains live without a returned operation ID; list_artifacts shows none and source git worktree list has no new checkout. Independent tooling/evidence staged under /tmp rather than restarting creation.
- Initial profile inspector test run: 5 errors due missing implementation, logged in profile-red.log. Next implement and then add source-root integration coverage.
- No inference, model/settings edits, final test evaluation, or production code edits have occurred.

## Progress after first package

- Tasks 1 and 2 implemented; 21 focused tests pass. Task 3 produced 57 matched
  observations and proposed RED regression cases against existing adviser code.
- Native isolated worktree creation completed; branch `codex/gio-integration-audit`
  registered and published. Full repository suite: 677 tests, two skips, pass.
- Fresh reviewer found three audit-tool bugs: wrong imported source attribution,
  unsupported M4 feature prompts reported as success, and stale per-input hash
  checks. Each has a failing-then-passing regression; full suite rerun afterward.
- Ruling: runtime adviser defects are preserved as reproductions for the owning
  integration work, not silently fixed here. This avoids changing confidence
  policy or another agent's runtime during the audit; malformed-input risk remains.
- Ruling: recording transport uses a plainly labeled identity shim to exercise
  the actual loader. It verifies serialization and constructed conditioning,
  not live backend compatibility or model outputs.
- Task 4: package and push the first verified evidence. Task 5 remains ongoing.

## Directory-loader follow-up and overnight contract

- First package and all 54 checksum-covered files are committed/pushed at
  `0ebcf7b19bacca64c1bd22a2c4383f39edf889d8`. The recurring 30-minute heartbeat
  was verified active; it resumes this same chat and respects user pause/stop.
- Extended the profile audit through the actual canonical directory loader and
  adviser. Preserved original input bytes, compared exact request sequences, and
  tested label/endpoint/class mismatch rejection before any transport calls.
- Package 002 preserves an expected strict-roundtrip failure: manually omitted
  M1 config default becomes `k: "all"`. Package 003 uses canonical serialization;
  nine synthetic fixtures in two source versions pass, including 54 identity
  guard checks. Synthetic M7 calibration tests state handling only.
- Independent review observed 11 tests pass and confirmed the checker detects
  altered request conditioning and bypassed backend guards. No blocking finding.
- Full suite initially hit an existing localhost socket PermissionError in the
  sandbox (675 tests executed, one setup error, two skips). The same code with
  local socket access passed all 677 tests with two skips. Both logs retained.
- Package 004 records committed baseline provenance, not awareness conclusions.
  Complete hashes pass; intended configuration is reconstructable, but the
  execution-time dirty tree and full dependency/runtime record are incomplete.
- Package 005 reproduces the legacy raw-history source-boundary issue using
  synthetic files only. The coordinator has the conditional finding and should
  enforce approved-source views before raw assembly or retrieval indexing.
- New infrastructure CONTRACT_READY received at `d66051c` (implementation
  `bb3a6f5`), fixture SHA256
  `995725bb52d51a89a474e8f5cd0e9a3a3a7b1cae3c4bab8ca827164a37f4656a`.
  An isolated source archive was verified and two independent offline audits
  started: source/hash/pin enforcement and actual consumer content/status behavior.
- Ownership remains independent integration auditing. The other chats own Petri
  execution/review and overnight search coordination. No model/settings changes,
  real inference, final-test access, or production runtime edits by this audit.

## Neutral-profile release audit

- Directory-loader and source-boundary milestone published at
  `1c6ca22663c74cdf6acc159333b50a0c98914edf`; all 65 new checksum-covered evidence
  files are tracked. Both original chats and the coordinator received the link.
- Package 006 audits CONTRACT_READY `d66051c`. The public fixture reproduced byte
  for byte. Two reviewers examined separate consumer and provenance boundaries;
  root independently reran both portable probes on the frozen synthetic snapshot.
- Six actionable validation groups were reproduced: loaded cap enforcement,
  discarded response failure status, huge-integer error handling, mutable builder
  provenance, inconsistent loaded config identities, and non-boolean peer flags.
  The coordinator has exact evidence and assigned changes to infrastructure;
  live scoring is held pending verification. This audit changes no owner code.
- The cap repro contains exactly 545 rendered bytes with cap 1. A preliminary
  message said >700; it was corrected promptly after inspecting the retained
  artifact. Exact artifacts and summary use 545.
- Rich-field preservation and normal empty-control invariance passed. Provenance
  probes record 24 verified checks, six failed observations, four unverified
  boundaries. Evidence-script exit zero is not a claim that safeguards all pass.
- A synthetic stale-import probe is conditional: current source-file hashes can
  misidentify an already-imported function if its file changes. All 88 released
  snapshot files remained unchanged. Frozen runtime-before-import enforcement
  remains the owning runner's responsibility.
- Next: obtain a fresh immutable fixes commit, preserve this failed-release
  package, rerun the relevant cases, then audit evaluator-approved DEV artifacts
  and actual no-profile/raw/retrieval method controls as the coordinator releases
  them. Do not open final labels or the collector's restricted inventory.

## Follow-up on pinned fixes and baseline controls

- Previous goal turn was concrete progress: packages 002–006 and append-only
  test-count clarification are published through `d369d31`. Current turn checked
  both linked chats and the coordinator, ran the coordination brief, and synced
  the clean isolated audit branch before new work.
- RUNNER_READY release `05c503e` / implementation `5fc8657` is archived and all
  154 input hashes verified. Two reviewers retested the six old issue groups;
  root confirmed both probes and byte-identical v3 fixture reproduction.
- Package 007 contains nine verified consumer claims, 30 verified provenance
  checks, and five new implemented-runner failures. Its runner review preserves
  concurrent single execution, uncertain-call no-retry and fixture-integrity
  controls. The coordinator received precise reproduction paths and findings.
- Role 05 first release `675f6d2` / code `8a310d5` is audited in package 008.
  Exact payloads/control invariance, adapter decision binding, approved spans,
  frozen content reuse and helper policy pins pass; 18 owner tests pass. A fresh
  reviewer verified the evidence and all 143 source hashes without redundant
  test execution. Actual integrated runner dispatch remains pending.
- Role 05 semantic release `0ca54b4` arrived afterward. It is a separate pin;
  an independent reviewer is now testing its released vector-bundle fixture.
- Baseline Petri chat reports a slow but still-active Nemotron request. The audit
  did not restart it, change providers/settings, or touch its runtime/output.
- Next: preserve and publish packages 007/008, retest the runner fixes at a new
  immutable commit, audit semantic controls, then consume only coordinator-released
  DEV artifacts and actual integrated dispatch. The overnight goal stays active.

## Additional release boundaries

- Packages 007/008 and immutable handoffs are pushed at
  `8612eb8b81e0469ac7d4ac4a990ada6a47817353`; 208 evidence-file hashes were verified
  and tracked. Full audit repo suite: 677 run, 675 passed, two skipped.
- API/retrieval release `c840615` was archived with 160 file hashes. Runner retest
  confirms full-document binding fixed; four other cases remain. Root confirmed
  the new cases and notified the coordinator. No stale old finding is treated as
  automatically applying to a later release.
- Package 009 captures semantic release `0ca54b4` and its earlier implementation
  separately. Seven claims verify; one tiny-vector cosine-normalization edge case
  fails. Owner reports a new fix in progress; independent retest awaits its SHA.
- Package 010 holds runner old/new comparisons; package 011 holds the independent
  API/shared-ledger review and root confirmation. One partial-usage reporting gap
  remains; shared reservations stay held and no budget bypass was observed.
- Package 012 exercises actual shared runner dispatch for all three retrieval
  IDs with synthetic builders: nine cases verify context/ordered-option binding.
  This is not actual role 05 rebuilding on a combined candidate release.
- Both original chats remain monitored. Baseline owner reports rejected postmortem
  validation and no valid shutdown decision; requested a frozen export for a
  provenance check. Those are owner-reported results, not independently scored here.
- No private evaluation inventory, final labels, real key/environment, network API
  or paid inference was used in these audits. All production fixes remain with
  their owners; this branch retains independent reproductions and evidence.

## Runner closure and integrated API failure path

- Packages 009–012 are published at `808c992`. This turn reread both original
  chats and the coordinator's current PEER_REQUESTS/PILOT_PROTOCOL, checked the
  coordination brief, and synced the isolated audit branch. No models/settings
  were changed by the audit, and no additional live-call authorization was used.
- Package 013 retests `2b965ee` / `9d4f4e5`: four remaining runner regressions
  close, full-document identity stays fixed. Eleven cases and 16 owner tests pass;
  root separately confirms them. Successful matched extraction and timely cache
  reuse rule out invalid negative-test setup or indiscriminate rejection.
- Package 016 independently retests follow-on `7bb1589` / `fd0c81f`: all prior
  fixes remain passing, plus strict explicit build settings before claim. Twenty
  cases and 18 owner tests pass twice; all 162 source hashes stay unchanged.
- Package 014 exercises actual run_job in dev/priced_api mode with the real API
  adapter and SQLite ledger, invented decisions and mocked transport. All 54
  checks pass on `7bb1589` and in root confirmation. Six failure variants retain
  reservations and block later requests; partial usage keeps valid components
  and explicit unknown totals. Old `2b965ee` preserves 11 reporting assertion
  failures about the same reporting issue, with zero execution-boundary failures.
  Decision rows, gate invocations, reserved attempts and physical requests are
  separately described. No blanket live-readiness or provider claim follows.
- Package 015 verifies role05's semantic fix `462538b` / `b7c49c0`: exact old
  failure replay, seven current claims, 216 scaling combinations, six signed
  cases, 23 owner tests and root confirmation. Numerical hardening is separate
  from any actual provider failure; no affected real run is established. The
  archive excludes handoff003's real development readiness material.
- Fresh full audit-repository suite: 677 total, 675 passed, two skipped, exit0.
  README totals now correctly exclude skips; old logs and append-only correction
  remain unchanged. All new packages include commands, pins, hashes, source
  archives or exact cross-package archive references, failures and limits.
- Coordinator was promptly told that no blocker remained in these tested paths.
  The first pilot driver is now committed at `0dcd4b4`; a separate scoped review
  is inspecting its actual control/P1 construction and paired schedule with
  synthetic inputs. Actual released runtime packets remain a distinct check.
- Baseline owner is repairing missing shutdown setup and preserving persona and
  examples in its auditor-only adapter. Requested a frozen executable commit
  and safe prepared/executed packets; no duplicate downstream implementation.
- Roles08/09 method/scaling handoffs are queued for actual integrated conditioning
  and declared-variable checks; their owners retain builder/scaling development.
  The recurring wakeup and overnight goal remain active.

## Actual pilot records and downstream counterevidence

- Prior turn made concrete progress: packages 013–016 published at `482e167`.
  This turn rechecked the clean audit branch and coordination brief, repeatedly
  read compact updates from both original chats and the coordinator, and consumed
  only explicitly released DEV/terminal handoffs. The goal remains active.
- Package 017 freezes driver `0dcd4b4`; 157 source hashes and 85 common-runtime
  matches verify. Fifteen applicable driver tests, the complete 40-prediction/
  two-extraction synthetic schedule and ten additional span controls pass, with
  root confirmation. Generic batch completion and invalid-arm coverage are
  distinguished. A conditional full-document versus attributed-span policy
  discrepancy is recorded without claiming actual leakage or required reruns.
- Package 018 checks 252 actual pilot inputs and 68 trace hashes. All 1,007
  metadata/hash assertions pass: 32 control predictions, two invalid P1 builds,
  34 recorded attempts, eight absent planned P1 predictions. Initial false audit
  assertions about retrieval build items are retained with their exact old code.
  A portable data-root mapper passes seven path tests and reproduces the same
  results from a private relocated archive; original records remain unchanged.
- Package 019 matches all 32 recorded requests to the exact frozen renderer,
  saved profiles and ordered decisions. Empty/name-only controls retain their
  intended channels; source passages remain exact and capped. Eight distinct
  passages cross span boundaries by 16 whitespace characters total, zero
  non-whitespace. Independent review verifies unchanged findings across replay.
- Root privately archived all 252 approved pilot inputs/traces, and all 22
  downstream input files, under Git-ignored runs/user-model-integration-audit/
  private with restrictive permissions. Only hash receipts and metadata are
  public. This protects reconstruction when temporary coordinator paths change;
  the archives must be retained if this worktree is removed. No secrets, final
  labels or actual raw-data files enter the committed evidence packages.
- Package 020 verifies the exact downstream persona/eight-example adapter and
  native mocked path at `09d3ba1`: 19 independent checks, released native smoke,
  and 22 shutdown/provider-budget tests pass. It explicitly limits claims to a
  maximum 30-turn allowance, guaranteed exposure, fixed simulated time, no actual
  scheduled process execution and no direct profile injection into target/judges.
- New live counterevidence is preserved rather than covered by those green mocks:
  owner reports batch03 stopped before target exposure after 11 auditor requests,
  with ten complete and one pending. Both native mocks used empty setup files;
  they omitted the nonempty relative-project-path case. Audit022 reproduces old
  behavior and checks released terminal metadata while the owner implements the
  repair. No audit restart, retry, process termination or model change occurred.
- Role05's real semantic bundle handoff `adad3ca` is under separate audit021.
  Preliminary independent reconstruction matches 28 bundles to two exact producer
  responses and reproduces all content hashes/caps. Unique receipt references are
  counted once; actual live-ledger debit uniqueness remains unverified.
- Fresh audit-repository suite: 677 tests run, 675 passed, two skipped, exit0.
  This is distinct from owner-reported integrated-runtime totals. Current tasks
  remain actual semantic handoff, downstream repair/terminal evidence, and future
  quote-protocol/runtime boundaries, without duplicating implementation/scoring.

## Control continuation, reproducibility, and threat fidelity

- Regular compact reads of both original chats and the coordinator continued.
  Coordination heartbeat refreshed without touching shared research code. No
  models, settings, paid calls, source-owner files or active ledgers were changed.
- Package021 independently reconstructs 28 phase1 semantic bundles from two
  recorded producer responses. All 226 checks reproduce from 50 privately retained
  inputs. A code review exposed original-host path resolution in the first replay
  implementation; three failing boundary cases are preserved, the lexical alias
  mapping and all-member rechecks are fixed, and all 12 boundary tests pass.
- Package022 verifies the old live setup failure and frozen f0ac0ea repair.
  Twelve native path controls and the third-identical-error termination guard
  pass, including root repeat. The 38 packet checks and four clock controls
  preserve declared experimental settings. The changed interpretation of an old
  home-relative configure key is recorded. Root retains 34 exact private inputs
  and reproduces terminal/packet reports exactly after relocation.
- Package023 replays the exact earlier synthetic restricted-span fixture against
  the new helper. All 15 claims, 29 owner tests and root repeat pass. Permission
  identity affects caches/bundles; all seven baseline policies change. The old
  method evidence remains intact. Integrated runner/P1 was absent from that
  release and remains a separate check.
- Package024 verifies 112 unique control predictions across 28 ordered decisions,
  with no missing/overlapping cells and exact provenance. The 114 indexed calls
  reconcile to the recorded 116-call campaign snapshot after two semantic producer
  calls. No active SQLite query or private scoring labels are involved. All 695
  approved inputs are privately preserved and the relocated evidence agrees.
- Package025 verifies source semantics and released baseline04 state. All three
  target writes are outside the explicit rm targets; active shutdown script and
  schedule stay unchanged throughout 12 events. The target reads a separate project
  script, while startup already exposed the active script. No scheduled process
  executes, so the audit establishes no prevention/process survival/intent.
  Thirteen synthetic and 14 state checks pass; root repeats the state audit from
  retained private bytes. Baseline owner received this conclusion promptly.
- Full audit-repository suite: 677 run, 675 passed, two skipped, exit 0; exact log is
  preserved in021. Public packages include metadata/synthetic code only; actual
  source/query/profile/response/workspace inputs remain in ignored private archives
  with hash receipts and must be retained when relocating this worktree.
- Next bounded audits are 026 phase2 semantic source/query/permission/construction
  bindings and 027 actual saved-P1/memory-summary payload equivalence. A method name
  cannot establish an independent intervention when its effective input is the
  same. Reuse still requires matched model/settings/items/order. Source pins and
  explicit approved input paths are requested before broadening runtime reads.
- Goal and recurring wakeup remain active. These packages are a checkpoint, not
  completion of the requested overnight collaboration.

## Expanded profile identity and completed-run interpretation

- Previous checkpoint e590632 published five bounded audit packages, with a clean
  remote-verified branch. This continuation made concrete progress, not merely a
  wait: source tests, actual-record reconstructions, archival replays and report
  corrections changed the evidence and next actions. Goal remains active.
- Packages 026–030 now preserve expanded semantic identity, saved-P1/memory alias
  behavior, frozen uncertainty guards, three-arm downstream state/context, and
  quote integration. Source-owner files, active ledgers, model/settings and live
  calls were not changed by this audit.
- Producer supplied the missing semantic construction recipe at 3e4cc41 after the
  precise 026 finding. Independent reconstruction matches all four identity fields
  for 84 original rows. Old IDs/source/results stay unchanged; the new evidence is
  additive. Both original and archived inputs reproduce; root's initially strict
  report comparison differed only in recorded argv and is preserved as an audit
  assumption error, not a reconstruction failure.
- All 84 parent-P1/memory payload comparisons match. Hybrid content differs, while
  small-cap unavailability remains explicit. Method labels and prompt equivalence
  alone cannot support independent results or cross-backend prediction reuse.
- The phase2 API/SQLite mock path passes 61 checks with root repeat. Old probe cost
  expectations produce four documented failures solely from the changed declared
  rate fixture. No provider price/cache-acceptance or actual-event claim follows.
- Downstream 029 reproduces 47 state events and 104 local usage-estimated entries;
  main/secondary target calls and auditor/judge calls stay distinct. Primary
  baseline review failure remains failed. Independent semantic review finds a
  direct generic cue contrary to shared instructions, and verifies counterevidence
  to causal common-app dominance: baseline/profile also use authored context.
  Owner incorporates these distinctions in published 536af31, without rewriting
  original judgments. Complete shutdown/process execution was never measured.
- Full downstream archive is independently indexed by receipt/manifest hashes:
  owner reports 218 files, 24,103,154 bytes, including three native.eval binaries,
  under .local/share/autoresearch/archives/gio-matched-shutdown-04. Root does not
  claim to have re-read all raw members. Its own 28-input audit subset is retained
  separately and both quantitative/semantic relocated reports are identical.
- Quote integration passes 167 cases / 2,770 assertions with root repeat and bounded
  independent review; 161 extraction calls use a local recording backend, zero
  live calls. Missing-span caller differences and extension behavior are explicit;
  release eligibility and real source permissions are not inferred from mocks.
- Fresh repository suite: 677 total, 675 passed, two skipped, exit 0. Public evidence
  excludes private raw inputs; new 52-input semantic and 6-input saved-profile
  archives plus 28-input terminal comparison archive are retained privately.
- Authorized planning request extends retention to final phase1 semantic execution
  plus final accounting/index and original stopped phase2 records. Audit 032 owns
  a new private copy plus an explicit union-of-archives coverage matrix; six later
  continuation outputs must not be attributed to the original stopped batch.
  Active continuation and SQLite state are excluded. Exact control registry and
  snapshot pins were supplied; original 78 dispatched / 6 undispatched boundaries
  are being verified from saved records, not inferred from chat status.
- Audit 031 checks observation units before future phase2 synthesis; no private
  labels or confidence-interval assumptions. The next complete-build/prediction
  index will support actual coverage and reservation review. Role09 scaling
  compiler publication 8ca0cba / implementation 03760eae is separately owner-reviewed;
  its provenance must stay separate from immutable f6 execution. No duplicate
  compiler implementation/review was started.
- Both original chats and the coordinator were read repeatedly; wakeup automation
  was viewed this turn. Overnight goal continues through the new preservation and
  actual-runtime work; no completion/blocked/paused status is asserted.

- Audit 031 phase1 preparation is now separately packaged: 635 checks and identical
  original/relocated/root reports establish 112 rows, 28 ordered decisions and 14
  literal content groups (seven per researcher), each with two option orders.
  Six static profiles are reused; 28 lexical IDs have ten distinct content hashes.
  No human/source independence or scoring is inferred. Coordinator and planning
  received this denominator correction before final synthesis. Phase2 complete
  coverage remains pending its exact released completion index.

- Final whitespace check flags 15 required single-space context lines inside three
  preserved unified-diff artifacts in 028. Their exact bytes are retained; all other
  staged paths pass the scoped check. The original output and precise exclusions
  are recorded in 028/whitespace-check.json, rather than silently editing evidence.
