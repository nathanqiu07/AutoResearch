# Nine-lane morning recovery implementation plan

> For agentic workers: use the existing implementation, testing and verification workflows. Gio explicitly ordered nine parallel lanes on November 15, 2026. This is an execution dispatch, not another approval round.

Goal: deliver and inspect the complete source data -> user profile -> Petri auditor -> generated environment -> target behavior -> evaluation chain, with matched controls and all failures retained.

Architecture: reuse the six existing project chats plus three workers in the current chat. Root owns product intent and visible progress. Existing coordinator owns canonical path reservations, aggregate budget and live dispatch. Each lane has one file owner; no second scheduler and no edits to running snapshots.

Tech stack: existing AutoResearch Python, neutral profile contracts, model backends, Petri wrappers and HTML result renderers. No major new dependencies.

Spec: Gio's direct instructions in chat 01a1e00e-3195-7ec3-a21d-7d7585a99860: keep the whole data-to-user-model-to-Petri workflow, use nine lanes in parallel, deliver a strong working demo in less than four hours. Abstract questionnaire discarded; no new answers are required to start.

## Time and budget
- Dispatch begins about 09:00 Pacific. This new user-directed sprint supersedes the old 09:00 overnight stop for this bounded new work.
- Target first complete-chain smoke by 09:45 Pacific, comparison evidence by 11:15, stop new paid admissions by 11:45, demo package by 12:00. Preserve a recording and time for submission.
- Existing aggregate ceilings remain $500 OpenAI and $500 OpenRouter, including prior usage and unresolved uncertainty. They are ceilings, not verified balances.
- Coordinator reconciles closed unused reservations and issues a bounded initial new envelope up to $200 per provider only if it fits the project totals. Preserve old uncertain attempts; no uncertain retries.
- Until the coordinator returns explicit allocations, workers implement and prepare offline. This is scheduler accounting, not a new user approval request.
- Do not alter or consume old final-test users, raw private archive disclosures on hold, frozen experimental results, or other teams' shared modules.

## Lanes and ownership

1. Petri integration — existing downstream chat 01a1de1f-bcb8-74a3-8076-0a3f9a27340a.
   Own new scripts/gio_petri/morning_recovery/* integration entrypoints and matching tests, excluding evaluation and viewer files below. Successor preparer accepts a verified P8 export; reuses existing runtime; one-arm smoke then generic/raw/profile comparison. Preserve old preparer. First output: exact interface and dry-run packet within 20 minutes.

2. Task-relevant rich profiles — planning chat 01a1de34-d825-74f3-a729-6841b6858769.
   Own new scripts/gio_recovery/rich_profiles.py, tests/test_gio_recovery_rich_profiles.py, docs/morning-recovery/lane02/. Use existing allowed Neel/Chris fit writing plus relevant attributable public methodology sources. Produce source bundle and one or two P8/P3 candidates, preserving support and uncertainty. Do not infer Gio answers from rejected questions. Shared source bundle must be available immediately; do not wait for perfect extraction.

3. Raw and retrieved context controls — baseline chat 01a1de57-5eba-7990-bc8d-065b397fcdf6.
   Own new scripts/gio_recovery/context_controls.py, tests/test_gio_recovery_context_controls.py, docs/morning-recovery/lane03/. Consume lane02 same source bundle; supply generic, raw-context and retrieved-context auditor suffixes with exact input coverage and no hidden source loss. Match scenario/model/settings with lane01.

4. Compact sourced principles — root worker profile_audit.
   Own new scripts/gio_recovery/compact_profile.py, tests/test_gio_recovery_compact_profile.py, docs/morning-recovery/lane04/. Competing simple profile from same allowed sources; preserve distinctions among preference, belief and fact. Keep provenance outside model-facing content budget; do not truncate mid-claim. Prepare neutral/export-compatible handoff; no target labels.

5. Consumer/method diagnostic — root worker results_audit.
   Own new scripts/gio_recovery/consumer_probe.py, tests/test_gio_recovery_consumer_probe.py, docs/morning-recovery/lane05/. Freeze a bounded unused-development-user panel; same Luna/Sol settings, no-history/full-own/count-matched-wrong-history arms, character-length baseline. No extraction search and no final users. First output: fixed plan with exact calls, bounds and field definitions; execute once coordinator allocates. This is diagnostic, not the demo critical path.

6. Scenario and task realism — oversight chat 01a1de7f-a434-7583-b372-c40f48434eb0.
   Own new scripts/gio_recovery/scenario_check.py, tests/test_gio_recovery_scenario_check.py, docs/morning-recovery/lane06/ and new owned scenario fixtures. Inspect saved shutdown failures, propose minimum common authoring repair, and validate behavior opportunity, coherent files, no prefilled answers. Do not change teammate harness core. Send lane01 one fixed scenario/control contract immediately. No outcome-based rerolling.

7. Outcome evaluator and independent integration checks — audit chat 01a1de44-b76b-7290-9753-ba528b42819e.
   Own new scripts/gio_petri/morning_recovery/evaluation.py, matching uniquely named tests, docs/morning-recovery/lane07/. Freeze environment validity, preference adherence and target-behavior measures before new results. Reuse span-backed review. Verify profile only reaches auditor, not direct target/judge payload. Prioritize concrete invalidating failures; do not serialize whole sprint behind optional hardening.

8. Full-chain viewer and demo package — root worker repo_status.
   Own new scripts/gio_petri/morning_recovery/viewer.py, tests/test_gio_recovery_viewer.py, docs/morning-recovery/lane08/. Show sources -> exact profile -> auditor context -> environment -> target trace -> evaluation and costs. Generic/raw/profile side by side, all failures visible. Build from saved fixtures immediately, replace with actual new receipts; no mock results represented as live.

9. Matched experiment execution — coordinator chat 01a1de5d-d544-7f10-b758-bcfbf7f22200.
   Own docs/morning-recovery/control/ and new dispatch scripts/tests only. Canonical board/locks writer and aggregate allocator. Define/publish shared packet and result manifest promptly; schedule first full-chain smoke using saved verified P8 if new extraction is not ready, then same-protocol generic/raw/rich/compact variants with bounded repetitions. Distinct versioned packets for material protocol changes. Parallel live calls within verified provider limits. No waiting for all nine lanes before smoke.

## Shared interfaces
- Publish source bundles with immutable IDs, author, source text and source provenance; exclude held-out labels and rejected private archive metadata.
- Profile/control handoff: method_id, researcher_id, source_bundle_digest, model-facing text, complete structured artifact if applicable, provenance, settings, implementation commit, checks performed, known limits.
- Lane01 + lane09 settle the smallest existing packet-compatible JSON schema within 10 minutes; use current runner fields, do not invent a new framework.
- Viewer input is a read-only run/result index with pointers to exact source/profile/prompt/environment/transcript/review/cost records. Missing values are missing, never zero.
- Each lane posts readiness/status to its own docs/morning-recovery/laneNN/STATUS.json and sends a concise handoff through the authorized project coordination channel.
- Git code changes remain on codex/ branches; run required tests before pushes; no main code merges or destructive cleanup.

## Required evidence
- [ ] Nine assignments acknowledged as active, with named owners and paths.
- [ ] Exact new profile reaches auditor; profile text absent from direct target/judge prompts.
- [ ] One complete Petri run with trace and environment artifacts.
- [ ] Generic/raw/profile conditions share scenario, models, settings, tools and target opportunity.
- [ ] Evaluator reviews actual output artifacts, not profile names or polished narratives.
- [ ] Failed profiles and failed runs remain visible; no selected-success substitution.
- [ ] Full comparison rendered and inspected; runnable command and recorded fallback included.

## Early redirect rules
- A no-profile ceiling stops expansion of that proxy panel; it does not stop the actual Petri lanes.
- Missing adapter blocks scaling of disconnected profiles, not all independent work.
- A failed extraction routes a generic/raw condition through the full chain while the owner fixes the new extraction version.
- No benefit is a result. Do not manufacture profiles, labels or gains to satisfy the demo.

