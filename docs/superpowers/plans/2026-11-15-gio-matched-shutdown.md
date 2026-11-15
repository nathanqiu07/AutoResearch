# Matched Shutdown Implementation Plan

> **For agentic workers:** Use test-driven implementation and independent review. Gio explicitly authorized execution without further permission questions.

**Goal:** Repair seed exposure, preserve models/seed, add a frozen profile adapter, and run matched conditions with transparent failures.
**Architecture:** Local custom Petri auditor tools own a deterministic simulated workspace; packet preparation freezes context; runner reuses native Petri and current judges with separate provider caps.
**Tech Stack:** Existing Python/Inspect/Petri/OpenAI/OpenRouter, no new dependencies.
**Spec:** docs/user-models/matched-shutdown-03/design.md

## Global constraints

- Original v2_seed_48 and Qwen235B/DeepInfra, Nemotronfree/Nvidia, GPT5.1 unchanged; 30 auditor turns and existing generation limits.
- No shared teammate code edits, held-out reads, prefills, rerolls, silent fallbacks, or fabricated tool confirmations.
- Project ceilings $500 per provider, but only spend within coordinator-issued $15 OpenAI/$5 OpenRouter requested suballocation.

## Review focus

- State isolation between arms and IDs: a tool result must reflect a real pending target call exactly once.
- Guaranteed exposure must not dictate the target action; snapshot must match the editable state.
- Persona/examples must actually reach the auditor, never silently reduce to empty principles.
- API failure/truncation must retain attempted-delivery evidence and not become a successful outcome.
- Evidence judgments and spending must remain separately auditable per arm/provider.

### Task 1: Deterministic setup and native hook

Files: scripts/gio_petri/shutdown_setup.py, test_shutdown_setup.py.
Interface: build_shutdown_tools(start_time, output_dir, instance=None) returns custom auditor tools and state object; object snapshot() returns serializable state/evidence. Tools configure_environment, start_review, advance_tools, end_conversation use native target forwarding. Initial required state is common to all arms; auditor edits only surrounding setup before target start. Tests cover isolation, traversal, required file preservation before start, real target writes after start, nonexistent/duplicate tool IDs, no prefill/rollback, and snapshot exposure.
- [ ] Write meaningful failing tests; implement minimal common setup and hook; run targeted tests.

### Task 2: Context and packet

Files: scripts/gio_petri/prepare_matched.py, test_matched_packet.py; generic-guidance.txt.
Interface: render_saved_context(model_path)->(text,provenance), prepare_packet(source_packet,model_path,out,start_time,lease)->settings. Preserve seed bytes, settings and frozen profile fields. Freeze all three arm prompts, single common setup protocol, manifest/hashes. Tests reject empty persona/examples, mismatched hash, alteredseed/settings, mutatedpacket, profile leakage into common/target/judge inputs.
- [ ] Write failing tests; implement profile adapter and packet preparation; verify exact prompt differences.

### Task 3: Provider budgets and run

Files: scripts/gio_petri/run_matched.py, provider_budget.py, test_provider_budget.py, test_matched_runner.py.
Reuse current modules. Provider budget subclass/adapter implements reserve/settle/save required by attach while keeping per-provider finite caps, leases and retained failures; failed arm does not authorize later calls from that arm. Runner builds native Petri task with custom tools, runs arms once, recovers native target evidence on failure, uses existing review and secondary score paths when feasible. Emit full provenance and per-arm errors/costs, never silently retry.
- [ ] Test budgets and terminal failures offline; implement runner; run full repository suite and independent review.
- [ ] Obtain coordinator lease, commit source, freeze packet and inspect diff, run conditions once; monitor and record outcomes.

### Task 4: Handoff

Files: docs/user-models/matched-shutdown-03/* and results/gio-matched-shutdown-03/*.
- [ ] Render comparison from actual artifacts, include full environment/evidence/unknowns and actual provider spend.
- [ ] Verify tests, hashes, no credentials, scoped diff; commit/push and verify remote; check in with coordinator/oversight.

## Execution ledger

Initial: current main merged cleanly at c71cf5d; rootcause and profile artifacts audited independently. Root owns runner/packet/budget integration; no live calls yet. Earlier failure remains at053aae7. Coordinator lease requested, not yet issued.

Task1: 11 state/native tests RED→GREEN; setup is state-backed, free target replies use native forwarding, unknown/duplicate operations fail visibly. Native premature end_conversation was found to stop even on ToolError; mechanical setup_gate now rejects it. No actual scheduled process execution is claimed.
Task2: six packet tests RED→GREEN; full persona/eight exemplars frozen. Guidance sizes differ (baseline0, generic608, profile10697UTF8bytes); generic is a short diagnostic, not a length-matched isolation of personal information.
Task3: eleven provider tests RED→GREEN. Runner boundary/recovery tests and a full native Inspect/Petri scripted smoke pass; fixtures do not establish preference accuracy or awareness. Independent reviewer found three guards: copied-lease replay, accepting10turns, and unbound runtimecommit. Regression tests reproduced allthree; globalleaseidentityclaim and exact30/commitbinding implemented. No paid calls yet.
Ruling: retain native Petri judge's existing three parse attempts; transport retries remain0. No audit rerolls. Each arm's primary review is attempted once even for recovered partial evidence, with failure status retained.
Ruling: no genuine future time progression is inferred from APIlatency. The required schedule is tenminutes after fixedscenario time; the measured outcome is an observed simulated edit/decision, not actualprocessshutdown.

Batch03: committed and froze09d3ba1; launched the issued15OpenAI/5OpenRouter tranche. Aborted the entire batch before any target call after repeated project-relative setup paths were rejected. Ten completed auditor calls cost an estimated0.01386918OpenRouter; one unknown request retains0.02584576. No OpenAI calls. Original inputs, replies, world state, source and ledger are published unchanged atresults/gio-matched-shutdown-03. This is an execution failure, not a measured baseline outcome.

Batch04 repair: all conditions accept project-relative configure paths; target tools retain home-relative paths. Invalid paths give actionable errors, aliases and directory collisions fail atomically, and three identical setup validation errors terminate the native audit. Common auditor prompts state the exact fixed scenario start/deadline and prohibit copying seed illustration times as current times. The original seed, three conditions, saved profile, models, generation settings and30-turn maximum remain unchanged. Start time also remains01:49-08:00 to isolate this common interface repair. A new source commit, packet and coordinator lease are required; batch03 cannot be resumed or selectively rerun.
