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
- [x] Add tests for gate aggregation, evidence quote rejection, unknown outcomes, no-interference outcome, and blind/full prompt input.
- [x] Run the new tests and observe failure before implementation.
- [x] Implement build_review_prompt(seed,row,tools,structure,instructions), validate_review(payload,sources), and prepare_review packet derived from frozen baseline01.
- [x] Verify exact seed/prompt/role generation equality with baseline01; only max turns and review metadata change.

### Task 2: Runner, verification, live run

Files: scripts/gio_petri/run_baseline.py and test_review.py.
- [x] Runner consumes packet turn count; captures native transcript/tool/stop metadata; saves primary request/reply/validated result before existing diagnostics. Failed review preserved without inventing scores.
- [x] Run scripts/gio_petri tests and the repository suite; fresh reviewer inspects code/settings, especially five focus items.
- [x] Commit source, freeze packet and hashes, run exactly one approved audit.
- [x] Inspect terminal status, transcript, output limits, exact role IDs, cost ledger, validity evidence and failures. Do not treat successful code execution as scientific validity.

### Task 3: Reviewable handoff

Files: docs/user-models/overnight/*, docs/user-models/baseline-review-02/*, results/gio-baseline-review-02/*.
- [x] Deliver complete copy-paste overnight prompts before paid run.
- [x] Produce full transcript/reasoning and primary/legacy results with provenance; immutable raw log references.
- [x] Verify hashes, credential-pattern scan and relevant tests; push scoped commits and verify remote.
- [x] Report complete result even if invalid. Goal ends only when prompt pack and full run handoff are both delivered.

## Execution ledger

Initial: approved spec captured; existing separate checkout reused; latest remote main b35f7ab integrated before edits. Overnight prompts prepared and delivered. No paid calls yet.

Task 1: complete; 11 review tests RED->GREEN; wrapper tests4 RED->GREEN; combined25 checks pass after fixes. Primary review contains only seed, final transcript/reasoning, target tools and stop metadata.
Review: independent fresh reviewer checked native .eval metadata and API return shape. Important finding fixed: failed/partial legacy judge does not block primary review of a usable audit. API failure record also added because full-result delivery requires an explicit review-failure artifact. Both regression tests failed before fixes and pass after.
Task 2: packet generated; byte identity of seed and baseline template tested; role/config/turn metadata validated without calls. No shared teammate modules modified.
Ruling: existing profile-search coordinator owns corpus intake; overnight context prompt amended to consume evaluator-released fit data, not independently scrape or split a second corpus.

Task 2 terminal result: exactly one audit at source 80171d4a621c2148b3b8319a4e456faf54d673cf, 27/30 auditor turns, 8 target calls, 18m42s. Last target response reported finish_reason=length and 16,384 output tokens but returned only a short sentence. The ledger halted further calls; native cleanup then failed. No secondary scoring ran. Models, routing, seed, prompt bytes and generation settings were unchanged.

Recovery: original failed/empty audit export and logs preserved. Offline extraction recovered native AuditStore messages into separate postmortem artifacts. A single GPT-5.1 review at source e693c2afc3310218682a813c2b1d543787474670 used the same frozen instructions and unspent portion of the original $5 allocation. Its reply failed two exact-quote checks and one target-visibility check. The reply is rejected, not repaired or rescored. Combined conservative cost $0.13732107. No rerun or personalized arm.

Task 3: full redacted publication bundle and readable findings prepared. Original logs stay unchanged. The target conversation contains no shutdown mention; no valid baseline decision was observed. Other agents' intake and integration lanes remain separate. Targeted tests: 28 passing; repository suite: 663 tests, two skipped. Final artifact integrity, documentation links and remote publication are checked at closeout.

Closeout verification: 81 publication files match their SHA-256 manifest. Published evidence and review documents pass credential-pattern scanning; every relative review-document link resolves. Full recovered transcript/reasoning are included verbatim in the readable handoff. Seed/template byte equality and model/routing/generation equality against baseline01 pass. Fresh targeted suite: 28 passing; fresh repository suite: 663 tests, two skipped. Independent read-only audit found no material contradictions; its minor missing-score.json wording was corrected. Shared autoresearch/ and harness/petri/ sources are unchanged from the audit runtime commit.

Publication completed at 053aae78a965ef18b94a0adbd3a520f6069e2346; remote branch equality verified. Full negative result and overnight prompts delivered; original goal completed. A later coordinator request adds only the documented future utility interface/readiness handoff, without further model calls.
