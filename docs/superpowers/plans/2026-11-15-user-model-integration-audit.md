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
