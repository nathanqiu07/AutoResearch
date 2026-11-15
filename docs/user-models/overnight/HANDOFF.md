# Current ownership and handoff

Recorded 2026-11-15 during the authorized 30-turn baseline.

## Existing coordinator and intake

Coordinator: 01a1de5d-d544-7f10-b758-bcfbf7f22200, campaign gio-profile-20261115.
The main experiment chat has NOT launched a Neel/Chris fetch, corpus collection worker, or profile search. Collection remains with the coordinator's corpus-intake lane. Its evaluator owns source grouping and held-out custody. No raw unrestricted corpus should enter this checkout or Git.

The proposed researcher-context prompt is now explicitly a consumer of evaluator-released fit data. Do not run it if the coordinator already owns equivalent context rendering. This file records the handoff; no additional chat was messaged or launched by this main chat.

## Integration audit

Existing owner: 01a1de44-b76b-7290-9753-ba528b42819e. Reported package: branch codex/gio-integration-audit, commit 0ebcf7b, docs/user-models/integration-audit/README.md and results/integration-audit/20261115-001/. This report was received from that owner, not independently reproduced in this checkout.

Important prerequisite for a future nonempty M2 profile: artifact hash alone does not pin conditioning. Freeze implementation commit, artifact hash, prompt version, exact rendered input, and backend. The current baseline has no researcher profile and cannot test that integration.

## Main experiment owner

Current branch: codex/gio-filtered-icai. Approved run source: 80171d4a621c2148b3b8319a4e456faf54d673cf.
Run path: runs/gio-baseline-review-02. One unpersonalized development audit, v2_seed_48, 30 turns, Qwen/DeepInfra auditor, Nemotron/Nvidia target, GPT-5.1 judge. Run-specific $5 ledger; original $100 overall limit. Other lanes do not inherit paid-run authority from this file.

Supported future utility handoff must identify: a released fit-only profile/context artifact; its immutable hash; extraction method/version and source-group manifest; candidate identity hidden from the judge; exact consumer implementation and rendered conditioning; comparison arms with matched seeds/models/providers/settings/turn limits and a fixed allocation. Existing saved M2/M3 loaders are not assumed interchangeable. No held-out labels are requested or accepted here.

Current runner is baseline-only. A future profile arm requires a reviewable scoped change and fixed comparison plan; this packet does not pretend that the current no-profile run consumes profiles. Existing coordinator and Gio decide the profile-search protocol independently. The main chat will not manufacture Gio's critique.
