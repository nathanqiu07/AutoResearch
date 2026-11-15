# Gio Baseline Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run the approved fixed-model 30-turn baseline with evidence-backed validity review and deliver full results plus coordinated overnight prompts.
**Architecture:** Add a review module and packet-preparation helper within scripts/gio_petri; reuse the existing runner and ledger. Preserve shared teammate modules. New review executes before post-audit recognition and is separate from legacy diagnostics.
**Tech Stack:** Existing Python, Inspect, Petri, OpenAI/OpenRouter providers; no new dependencies.
**Spec:** docs/user-models/baseline-review-02/plan.md (approved user plan).

## Global Constraints

- Original seed and auditor prompt unchanged; max auditor turns 30; Qwen/Nemotron/GPT-5.1 and existing generation settings unchanged.
- One audit, no rerolls, $5 run cap under overall $100, no held-out evaluation.
- Existing integration audit is a separate owner. No teammate module edits.

## Review Focus

- False evidence quotes must fail validation, not produce apparent confidence.
- Continuing after threat exposure is a valid observable response; pending edit results remain unconfirmed.
- Post-audit recognition and legacy score labels must not leak into primary judging.
- Missing/unclear checks or a failed reviewer cannot become a valid baseline.
- Settings and actual execution must match; raw output and failures must survive later scoring errors.

### Task 1: Packet and primary review

Files: scripts/gio_petri/review.py, prepare_review.py, test_review.py, review-instructions.txt.
- [ ] Add tests for gate aggregation, evidence quote rejection, unknown outcomes, no-interference outcome, and blind/full prompt input.
- [ ] Run the new tests and observe failure before implementation.
- [ ] Implement build_review_prompt(seed,row,tools,structure,instructions), validate_review(payload,sources), and prepare_review packet derived from frozen baseline01.
- [ ] Verify exact seed/prompt/role generation equality with baseline01; only max turns and review metadata change.

### Task 2: Runner, verification, live run

Files: scripts/gio_petri/run_baseline.py and test_review.py.
- [ ] Runner consumes packet turn count; captures native transcript/tool/stop metadata; saves primary request/reply/validated result before existing diagnostics. Failed review preserved without inventing scores.
- [ ] Run scripts/gio_petri tests and the repository suite; fresh reviewer inspects code/settings, especially five focus items.
- [ ] Commit source, freeze packet and hashes, run exactly one approved audit.
- [ ] Inspect terminal status, transcript, output limits, exact role IDs, cost ledger, validity evidence and failures. Do not treat successful code execution as scientific validity.

### Task 3: Reviewable handoff

Files: docs/user-models/overnight/*, docs/user-models/baseline-review-02/*, results/gio-baseline-review-02/*.
- [ ] Deliver complete copy-paste overnight prompts before paid run.
- [ ] Produce full transcript/reasoning and primary/legacy results with provenance; immutable raw log references.
- [ ] Verify hashes, credential-pattern scan and relevant tests; push scoped commits and verify remote.
- [ ] Report complete result even if invalid. Goal ends only when prompt pack and full run handoff are both delivered.

## Execution ledger

Initial: approved spec captured; existing separate checkout reused; latest remote main b35f7ab integrated before edits. Overnight prompts prepared and delivered. No paid calls yet.

Task 1: complete; 11 review tests RED->GREEN; wrapper tests4 RED->GREEN; combined25 checks pass after fixes. Primary review contains only seed, final transcript/reasoning, target tools and stop metadata.
Review: independent fresh reviewer checked native .eval metadata and API return shape. Important finding fixed: failed/partial legacy judge does not block primary review of a usable audit. API failure record also added because full-result delivery requires an explicit review-failure artifact. Both regression tests failed before fixes and pass after.
Task 2: packet generated; byte identity of seed and baseline template tested; role/config/turn metadata validated without calls. No shared teammate modules modified.
Ruling: existing profile-search coordinator owns corpus intake; overnight context prompt amended to consume evaluator-released fit data, not independently scrape or split a second corpus.
