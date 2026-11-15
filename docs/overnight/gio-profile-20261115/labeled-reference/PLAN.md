# Recorded-preference reference implementation plan

> **For agentic workers:** use the executing-plans workflow inline. This bounded role was assigned by oversight; live execution still requires the coordinator's exact lease.

**Goal:** run existing M0–M3 on eight frozen PRISM development users without exposing final-user records or changing the benchmark implementation.

**Architecture:** a small script prepares a private development-only snapshot and a hashed run plan, then validates a coordinator lease and calls the existing fidelity runner. Existing backend, methods, and split logic remain unchanged.

**Tech stack:** Python 3.9+, standard library.

**Spec:** `../control/dispatch-role-10.json` and `docs/superpowers/plans/2026-11-15-profile-search/prompts/10-labeled-reference.txt`.

## Global constraints

- Base `0dcd4b43b82a5a271d195e0bcc6b67695281f37c`; branch `codex/gio-overnight-10`.
- Own only the reference script, its test file, and this document directory.
- Development only; original manifest and final marker unchanged.
- Requested live limits: $5 OpenAI, 1,500 attempts, 3,600 seconds, one process, deadline 2026-11-15T17:00:00Z. These are not a lease.
- Freeze M0–M3, seed 0, eight users, five history items, two hypotheses/principles, one exemplar before calls.
- No raw preferences, profiles, labels, or credentials in public handoffs.

## Review focus

- Final-user JSON must not be deserialized during preparation.
- A changed choice, split, code file, or snapshot must fail before spending.
- The same lease cannot launch twice, including after a partial run.
- Expired or excessive lease limits fail closed; uncertain calls stop further network calls.
- Incomplete runs and empty learned profiles remain visible in results.

## Task 1 — Prepare immutable development inputs

- [x] Write tests for final-row exclusion, exact normalized replay, canonical split matching, and exclusive private output.
- [x] Observe the missing implementation failure.
- [x] Implement `prepare(source, canonical_manifest, destination, n_users=8)` in `scripts/overnight_labeled_reference.py` using existing normalization/manifest helpers.
- [x] Verify targeted tests. Do not write source text into tracked files.

## Task 2 — Validate and execute one leased panel

- [x] Write tests for plan/snapshot/code drift, lease bounds/deadline, duplicate launch, and stop after uncertain API failure.
- [x] Implement `execute(plan_path, lease_path)` around existing `OpenAILLM` and `run_fidelity`; require exact plan hash and coordinator lease, preserve a one-use launch claim.
- [x] Freeze the protocol and full implementation; run targeted and complete repository tests.
- [x] Request independent review through oversight; fix concrete issues with regression tests.
- [ ] Push only the reserved branch and send code, plan and private-snapshot hashes. No live call until the coordinator issues the lease.

## Experiment protocol

Question: does personal history improve prediction of recorded preferences, and do the bounded M2/M3 adaptations improve over raw history?

Expected: valid predictions and a measurable matched comparison. Equal/worse target accuracy, empty profiles, invalid predictions or validation-only gains count against added value. Report user-macro accuracy, paired differences, valid-only Brier score alongside failures, aggregate fit-and-predict usage and incomplete cells. Eight users are an exploratory reference, not proof of research-taste transfer or a winning method.

PRISM pairs derive from human response ratings but are selected through a personalization/disagreement filter. Record that selection limit. This lane remains distinct from archival judgments and downstream utility.
