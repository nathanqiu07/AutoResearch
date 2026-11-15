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
