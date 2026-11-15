# Overnight User Profile Search Implementation Plan

> For agentic workers: use superpowers:executing-plans for your assigned slice; use superpowers:subagent-driven-development only when the coordinator grants separate non-overlapping sub-ownership. Do not recursively create duplicate workers.

**Goal:** produce reproducible profile-method and targeted scaling comparisons with protected evaluation evidence.
**Architecture:** isolated worker branches, one canonical coordination writer, one interface/runner owner and one evaluator/final-data custodian. Candidate workers share immutable hashes and exact commits; downstream research-loop execution stays with existing owners.
**Tech Stack:** existing AutoResearch Python 3.9+ / standard-library runtime, existing LLM backends, Git and the repository agentctl protocol mediated by one coordinator.
**Spec:** [design.md](design.md). Contract: [SHARED_CONTRACT.md](SHARED_CONTRACT.md).

This is a dispatch packet. No implementation, experiment launch, remote board mutation or spend has been performed by producing it. Runtime model IDs, allocations and deadline are resolved once by 00 from actual availability and existing authorization.

## Launch order and dependencies

1. Give 00 to the coordinator first. It resolves ownership, publishes this packet and returns BASE_SHA/path reservations.
2. Start 01 infrastructure, 02 Neel intake, 03 Chris intake and 04 evaluation. If a teammate already owns collection, assign the corresponding prompt as intake/QA, not duplicate scraping.
3. Start 05 baselines and 06/07/08 builders on offline fixtures. Live source use waits for CONTRACT_READY and DATA_READY.
4. 00 dispatches the common dev grid; 10 can run a separately budgeted labeled reference lane. 09 prepares scaling while waiting for FINALISTS_FROZEN, then uses the same evaluator-provided items.
5. Send the existing audit owner the additive handoff prompt. Send the downstream request to the existing harness owners through the coordinator. Do not create duplicate audit/harness implementers.
6. Freeze one complete core+scaling confirmation manifest. Only 04 can reserve and run it under explicit final-use authority. If a dependency is absent, publish exact incomplete outcomes rather than inventing results.

The roles need not all run simultaneously. With a small worker pool, preserve coordinator/evaluation ownership and queue method groups as capacity frees. Offline fixture work is available before live dependencies land.

## Ownership table

| Role | Prompt | Depends on |
|---|---|---|
| 00 Coordinator and search owner | [coordinator](prompts/00-coordinator.txt) | Start first |
| 01 Profile contract and execution infrastructure | [infrastructure](prompts/01-infrastructure.txt) | 00 |
| 02 Neel corpus intake | [corpus-neel](prompts/02-corpus-neel.txt) | 00, 04 split policy |
| 03 Chris corpus intake | [corpus-chris](prompts/03-corpus-chris.txt) | 00, 04 split policy |
| 04 Evaluation and final-data custodian | [evaluation](prompts/04-evaluation.txt) | 00 to start; 02/03 inventories for DATA_READY; 01 for scoring |
| 05 Baselines and retrieval | [baselines](prompts/05-baselines.txt) | 01 CONTRACT_READY, 04 DATA_READY for live runs |
| 06 Profile builders P1–P3 | [profiles-summary](prompts/06-profiles-summary.txt) | 01 CONTRACT_READY, 04 approved input bundle |
| 07 Profile builders P4–P6 | [profiles-principles](prompts/07-profiles-principles.txt) | 01 CONTRACT_READY, 04 approved input bundle |
| 08 Profile builders P7–P8 | [profiles-hypotheses](prompts/08-profiles-hypotheses.txt) | 01 CONTRACT_READY, 04 approved target and peer bundles |
| 09 Targeted model-scaling study | [scaling](prompts/09-scaling.txt) | 01 neutral-profile consumer support, 04 evaluation/capability panel, 00 FINALISTS_FROZEN, 05 baselines |
| 10 Recorded-preference reference track | [labeled-reference](prompts/10-labeled-reference.txt) | 00 allocation, 04 split policy, existing M0–M3 code |
| Existing audit owner | [Additive handoff](prompts/11-existing-audit-handoff.txt) | Contract and development artifacts |
| Existing downstream owners | [Utility request](prompts/12-existing-downstream-request.txt) | Frozen profiles and supported harness |

## Global constraints

- One writer per file, one evaluator, one scheduler, one canonical .agents writer. No force pushes, no unapproved main merges, no cleanup of others' files.
- Coordinator verifies current remote reservations; feature-branch agentctl locks are not global. Existing integration audit remains reserved.
- Fit/dev/confirmation source boundaries apply to raw documents, derivatives, peer data, caches and messages.
- Existing UserModel backend guards and final-use markers remain intact. A cross-backend neutral profile is not a transferred calibrated model.
- No task may convert missing or failed arms into silent success. Report unsupported conditions and partial runs.
- Current repo tests are required before code pushes; final experiment authority and aggregate resource policy remain separate from passing tests.

## Review focus and owning checks

1. Hidden source material leaks through URLs, titles, derivatives or Git history: 04 tests bundle/staging exclusion; 02/03 never publish unapproved raw inventory.
2. One profile silently changes across scaling consumers or loses rich fields: 01 records content/render/payload hashes; 09 validates the manifest; the existing audit owner checks actual conditioning.
3. Duplicate work or duplicate paid calls: 00 verifies canonical path reservations and one job lease; 01 rejects output overwrite and records uncertain attempts.
4. Search selection leaks into confirmation or clones bypass the one-use flag: 04 owns final data and atomic central reservation; 09 contributes to one frozen manifest.
5. Infeasible model/schema/cap or an empty profile is disguised as a valid arm: 01 and 05–09 test explicit unavailable/invalid/empty statuses, failures and coverage.

## Verification and milestones

- [ ] 00 publishes ownership/run policy/base/contract hash and remotely verified reservations.
- [ ] 01 publishes a label-free offline build/export/predict fixture; existing audit owner receives it.
- [ ] 04 publishes DATA_READY with approved source hashes, grouped dev panel and opaque confirmation metadata.
- [ ] Each code owner delivers targeted test output plus the repo-required suite for the pinned commit.
- [ ] 00 accounts for every assigned job and freezes finalists based only on dev results.
- [ ] 09 delivers a complete declared scaling matrix with identical item IDs and explicit missing arms.
- [ ] Existing audit owner checks saved artifacts and comparison packets against their declared variables.
- [ ] Existing downstream owners deliver utility evidence or an explicit unavailable handoff.
- [ ] 04 reserves the final manifest only if authority and all frozen prerequisites are present.
- [ ] 00 publishes the complete search record and morning report, with no claims beyond the evidence.

## Sharing protocol

Each linked role file is a complete copy-and-paste prompt including the common operating contract. It also names its allowed files, inputs, first useful output and done criteria. Publish one immutable JSON event per milestone using [handoff-schema.json](handoff-schema.json). This is an example record/schema guide, not an executed run.

Notification format: `ROLE / EVENT / branch / full commit SHA / event path / output hashes / next dependency`. Coordinator verifies receipt before a consumer treats an artifact as ready. Never share only a screenshot, an uncommitted file or an ignored runs/ path. No worker writes the coordinator's queue, another worker's module or a shared mutable results CSV.

Detailed prompt contents follow in [ALL_PROMPTS.txt](ALL_PROMPTS.txt); individual prompts are in prompts/. The existing audit handoff and downstream request are reserved-owner messages for Gio/coordinator to deliver, not new agent launches.
