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
