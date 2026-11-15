from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
REPO = 'https://github.com/nathanqiu07/AutoResearch'
COMMON = '''You are one worker in Gio's overnight researcher-profile study. This is your scoped task request, not a request to restart the design discussion. Make routine reversible implementation decisions, preserve evidence, and report consequential changes to the coordinator. Do not launch or assign another copy of an owned task.

OBJECTIVE
Compare methods that extract user profiles from Neel Nanda and Chris Olah's writing. Measure (1) prediction of held-out documented judgments and (2) downstream research utility separately. Deprioritize human questionnaires; a model-filled question schema remains a candidate. Broad search happens on development data. A targeted model-scaling study follows candidate selection. No global-optimality or general-researcher claim follows from two cases.

STARTUP AND OWNERSHIP
Read repository AGENTS.md, README.md, docs/user-models/README.md and handoff.md, then this packet's SHARED_CONTRACT.md. Local packet directory: /Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/docs/superpowers/plans/2026-11-15-profile-search/ . The coordinator publishes this same docs-relative directory to the repository for workers on other machines. Repository: https://github.com/nathanqiu07/AutoResearch. Have the coordinator verify current remote ownership and supply BASE_SHA, your isolated worktree/branch, allowed paths, campaign ID and contract hash. Preserve existing dirty work and untracked duplicate files. Do not repurpose the existing AutoResearch or AutoResearch-gio-draft checkout.
Only the coordinator mutates the canonical .agents board. agentctl on your feature branch is NOT a shared lock service. Send reservation, status, interface-change and handoff requests to the coordinator; do not create branch-local claims and treat them as global. One writer owns each file. Existing integration-audit chat 01a1de44-b76b-7290-9753-ba528b42819e owns saved-profile conditioning, export/save-load, empty-profile/confidence/fallback and comparison-packet audits. Do not duplicate that implementation.
Bootstrap exception: role 00 performs its own read-only ownership/base discovery and coordination setup without waiting for itself. Role 01 may implement the proposed contract and fixtures after its paths are reserved; it produces CONTRACT_READY rather than waiting for it. Other roles may prepare their assigned fixtures under the proposed contract; dependent integration/live use waits for the published contract.

WORK AND SHARING
Use your own codex/gio-overnight-<role> branch at the pinned base. Reuse existing code and the standard-library-only convention in autoresearch/. Do not change the shared loop, scorer, model guards, existing splits or API without its owner's agreement. Build offline fixtures while dependencies arrive. Once the relevant gates and PATH_RESERVED are received, implement your slice, run targeted checks and the repo-required suite before code pushes. Required command: `python3 -m unittest discover -s tests -t .`. Preserve unrelated failures and report them; do not fix others' areas or claim a failed check passed. Infrastructure publishes CONTRACT_READY; corpus/evaluation may prepare their source and split artifacts before it, using this packet's schema. Method consumers bind to live contracts only after CONTRACT_READY.
Push only your branch, with no force push or automatic merge into main. Publish unique immutable handoff events on that branch; tell the coordinator the exact branch, commit SHA and event path. Use the packet's handoff schema. Generated artifacts are content-addressed and checksummed. runs/ is ignored and is not a sharing mechanism: provide a verified artifact location or an allowed generated artifact committed at a unique results/ path. Never publish withheld target material or secrets. No shared append-to-one-CSV pattern.
Pin the artifact AND executed method/renderer implementation and prompt versions. Matching backend identity alone does not prove a saved artifact invokes the same intervention. Treat legacy compatibility as unverified until the audit owner supplies evidence; do not silently migrate an artifact or bypass its guards.

RUN AUTHORITY AND EVIDENCE
The coordinator owns one job queue and total budget policy; no worker launches jobs merely because it is idle. Execute only assigned jobs whose manifest, model IDs, allowed input hashes and remaining allocation are explicit. Existing user approvals persist; this prompt does not invent new paid/CLI spend approval or permission to consume final users. If live policy is unresolved, finish code, fixtures, dry runs and exact run estimates. Do not ask Gio the same question from multiple agents.
Builders cannot fetch unrestricted researcher material or open held-out documents. Inferred labels are not ground truth. Do not infer preferences from absence, coauthorship alone, or invented rejected alternatives. Failures, empty profiles and unavailable confidence remain visible; never silently fall back and label the output as success. Logging a search does not validate it.
Only the evaluator can execute an explicitly authorized, frozen confirmation batch. No other role runs --users test --final, reads final labels, deletes a marker or reruns final data. Keep implementation work out of a live runtime snapshot. New code gets a new pinned version after coordination; prompt/config mutation stays in declared development jobs.

REPORTING
Send the first useful dependency artifact promptly, then milestone updates and a final handoff: exact code/artifact hashes, commands/checks, observations, failures, cost, unresolved issues and next dependency. Distinguish complete, partial, blocked and unsupported; do not label a method a winner from a smoke test.
'''

ROLES = [
dict(id='00',slug='coordinator',name='Coordinator and search owner',depends=[],paths=['docs/overnight/<campaign>/control/','coordination-only clone: .agents/'],body='''YOUR ROLE
Own the execution order, ownership map, search registry, aggregate budget, immutable job dispatch, integration decisions and morning report. You do not own method implementation or the evaluator's final labels.

FIRST ACTIONS
1. Inspect current remote branches, the existing board and known worker chats before assigning work. Resolve the existing data-collection owner before creating a second scraper. Reserve the integration-audit scope for chat 01a1de44-b76b-7290-9753-ba528b42819e, branch codex/gio-integration-audit: scripts/user_model_audit/, tests/test_user_model_profile_audit.py, tests/test_user_model_packet_audit.py and docs/user-models/integration-audit/. Existing branch-local claims are not proof of a global reservation. The owner has reported offline tools and adviser malformed-value findings; obtain exact commits/reproducers before depending on them, and do not duplicate or silently repair their work.
2. Create a fresh clean coordination-only clone tracking origin/main; do not use either pre-existing dirty/stale checkout. Serialize all .agents operations. Use explicit AGENT_NAME per worker when registering, claiming, locking or heartbeating on their behalf. Do not misuse AGENTCTL_GIT_ROOT: it does not relocate .agents.
3. agentctl can print success despite failed pushes, and overlapping paths can race. After every reservation fetch, verify the expected JSON at origin/main and recheck all overlapping locks. A failed push or conflict means no reservation. Coordinate with existing owners; a stale local heartbeat alone is not abandonment. Renew reservations every 30–60 minutes. Keep coordination-only commits separate from code integration and follow current repo checks.
4. Select a current code base that includes the required Gio work, with no overwrite of teammate changes. Publish BASE_SHA and this packet on a dedicated docs/code branch. Prepare isolated worker branches. Only you reconcile approved commits onto the integration branch; main merges remain under existing repo/user authority.

DELIVERABLES AND SCHEDULING
Publish OWNERSHIP.json, RUN_POLICY.json, the contract hash, job registry and milestone ledger under your control directory. RUN_POLICY must record exact source of existing approval, spend already used/reserved, aggregate API/CLI-call/wall-clock limits, deadline with timezone, concurrency, model IDs/versions and stop/retry policy. Null means unavailable, not unlimited. Do not assume the user's subscription guarantees throughput. If one concrete spending/model decision is missing, ask Gio once after preparing the exact bounded run; all independent offline work continues.
Launch 01 infrastructure, 02/03 corpus and 04 evaluation first. Builders and 05 baselines can work against fixtures while the source and contract gates close. 09 scaling prepares its matrix but cannot select its own finalists. 10 labeled references is optional parallel development work; it must not consume final PRISM users.
Schedule P1–P8: 8 families × 3 profile caps (512/2048/8192) × 2 evidence policies = 48 configurations, with 3 extraction replicates per researcher. This is an upper design grid, not a guarantee the budget supports every cell. Declare feasibility and screening/promotion rules before scores arrive. Include family slots plus global slots; rank configurations across replicates. Keep no-profile, name-only, raw and retrieval controls. Decide the maximum jobs from measured throughput and allocations before dispatch.
Assign each JOB_ID once. Track exact leases and states; do not rerun uncertain paid calls automatically. Keep a small fidelity/utility/cost frontier and permit logged development-only mutations/hybrids. After selection, hand a frozen shortlist to 09. Reserve time for scaling and confirmation preparation, not merely more candidate generation.
Hand profile bundles and a concrete matched utility request to the existing downstream owners. Do not create another research loop. If utility cannot run, report unevaluated.

DONE
A readable morning report with every launched run accounted for, ranked development results, scaling results or precise incomplete cells, confirmed results only if authorized, artifact links and limits. Publish the full ledger, not only favorable methods. The three main gates are CONTRACT_READY, DATA_READY and FINALISTS_FROZEN; actual final execution additionally needs the evaluator's independent reservation and user authorization.'''),
dict(id='01',slug='infrastructure',name='Profile contract and execution infrastructure',depends=['00'],paths=['autoresearch/taste/overnight/__init__.py','autoresearch/taste/overnight/__main__.py','autoresearch/taste/overnight/contracts.py','autoresearch/taste/overnight/consumer.py','autoresearch/taste/overnight/runner.py','autoresearch/taste/overnight/registry.py','tests/test_overnight_contracts.py','tests/test_overnight_runner.py'],body='''YOUR ROLE
Own the single new document-to-profile interface, neutral profile format, prediction adapter, registry and bounded job runner. Do not own candidate content, split policy, model selection or the existing integration audit.

CONTRACT TO IMPLEMENT
Use the SHARED_CONTRACT.md v1 proposal. Provide build_profile(documents, config, extractor) -> ProfileArtifact for builders, and predict_profile(profile, context, options, consumer, config) -> existing Prediction. Use JSON-serializable immutable artifacts. The exact rich representation can differ by method; a single documented renderer must pass it to the consumer without silently discarding fields. Record the rendered personalization text hash and token count.
Keep extractor and consumer provenance separate. Existing UserModel.load_model rejects a different backend; do not remove that check. Cross-model studies use a neutral text profile and a fresh consumer adapter. Learned weights or calibration cannot be ported through that route. Verify raw confidence remains explicitly uncalibrated unless separate evidence supports calibration.
The existing audit owner reports that saved M2 artifacts may condition differently across implementations despite matching backend, and that prompt-version compatibility may be unchecked. Obtain their exact reproducer; do not treat this report as a license to change shared method policy. Your new wrapper must pin/check method and renderer implementation hashes, saved/runtime prompt versions and explicit compatibility status. Legacy mismatches fail closed or are separately declared migrations, never silent baseline substitutions. Send required shared-code fixes to their owner.
Publish CONTRACT_READY and an offline runnable fixture before implementing optional conveniences. Own package exports and method registration: other workers supply modules and registration metadata, not edits to your registry or __init__.py. Use a dedicated python -m autoresearch.taste.overnight entry point if needed, owned by you; avoid the shared team CLI.

JOBS AND CACHES
Implement canonical hashing and non-overwriting run directories. Cache keys include profile/source hash, method config, method/renderer implementation hash and prompt version, extractor/consumer backend identity and settings, item/options order, replicate and stage. Return cache provenance. Changed settings cannot reuse a previous entry. Validate metadata before execution; reject missing allocation or unsupported model capabilities. Count attempts/failures and preserve uncertain usage.
The coordinator alone assigns job IDs/leases. The runner executes one given manifest and emits result plus trace hashes, errors, token counts and usage. It does not silently choose new tasks, substitute models or initiate final runs. Use existing backend/budget support where it meets the contract; report missing support rather than creating broad integrations.

CHECKS
Meaningful tests: labels cannot enter prediction payload; exact allowed source set enforced; duplicate JOB_ID cannot overwrite; changed model/prompt/profile/option order separates caches; malformed/oversized/empty output gets explicit status; unsupported backend emits unavailable; output probabilities are valid or explicitly unavailable. Give code and fixture hashes to the existing audit owner for end-to-end conditioning/save-load/fallback checks—do not duplicate their audit tooling.
Confirmation inputs, predictions, rationales, traces and caches use evaluator-supplied private roots. Add a test proving confirmation outputs cannot reach shared worker cache/output directories; handoffs expose only hashes, status and authorized aggregate metrics.

DONE
One portable contract, documented registry hook, offline fixture and bounded job runner ready for all method workers. Deliver the exact consumer payload shape and limitations before live jobs.'''),
dict(id='02',slug='corpus-neel',name='Neel corpus intake',depends=['00','04 split policy'],paths=['data/profile_sources/neel_nanda/approved/','scripts/profile_sources/neel_nanda.py','tests/test_profile_sources_neel.py'],body='''YOUR ROLE
Own Neel Nanda source intake only after 00 verifies whether the teammate already owns collection. If so, become the intake/QA owner and consume their batches; do not start a competing full scrape. Do not write profiles or labels.

INPUTS
Seed discovery: https://www.neelnanda.io/blog and https://www.neelnanda.io/mechanistic-interpretability . High-value material includes favourite-papers-old, the July 2024 favourite-paper recommendations, and his research-process/research-taste writings. Follow author-linked primary sources, not arbitrary biographies or generated page summaries.

DELIVERABLE
A small useful batch first, then incremental versioned additions. Store canonical URL, observed content hash, title, authorship/contribution, original and updated dates, retrieval time, version evidence, source type, document/project/duplicate group, attributable spans and fetch outcome. Keep full raw inventory in the restricted staging location assigned by 04; only the evaluator-approved fitting/development subset may be published to builders. Do not commit held-out titles, URLs, excerpts or your informal summaries of them to the shared branch.
Neel's old favourite-papers page contains later edits: original publication date is not enough for temporal eligibility. Retain revision uncertainty. Dedupe crossposts and repeated material; preserve failures. A mention of Neel, coauthorship or an auto-generated forum summary is not equivalent to his own statement.
Group data by purpose: explicit taste/process statements, contextual recommendations, technical explanations, project involvement and third-party quotations. Collect broadly but prioritize attributable decision-relevant evidence. A direct recommendation can support a stated-preference target; do not create pairwise preferences from project involvement or generate alternatives yourself.

CHECKS AND HANDOFF
Test normalization/dedup/version metadata on fixtures. Sample check source spans against stored bytes and detect truncated pages. Send each raw batch privately to 04 for split assignment; publish only the allowed manifest with hashes plus rejection counts. Quarantine uncertain versions rather than silently treating them as earlier evidence. Paid tools follow the coordinator's run policy. No bypass of source access controls.

DONE
The coordinator and evaluator have a reproducible inventory, source quality counts, enough clean material to start, and a precise description of collection gaps. No claim of a complete archive unless enumeration supports it.'''),
dict(id='03',slug='corpus-chris',name='Chris corpus intake',depends=['00','04 split policy'],paths=['data/profile_sources/chris_olah/approved/','scripts/profile_sources/chris_olah.py','tests/test_profile_sources_chris.py'],body='''YOUR ROLE
Own Chris Olah source intake only after 00 resolves existing collection ownership. If the teammate already collects it, consume and audit their batches. Do not build profiles or fabricate preference labels.

INPUTS
Primary discovery: https://colah.github.io/ and https://transformer-circuits.pub/ . Prioritize Research Taste Exercises (https://colah.github.io/notes/taste/), Interpretability Dreams (https://transformer-circuits.pub/2023/interpretability-dreams/index.html), Research Debt and methodological essays. Technical collaborations are secondary evidence with careful attribution.

DELIVERABLE
Match the shared document schema exactly. Send a useful initial batch before chasing completeness. Record canonical URL, observed hash, title, author/contribution, original and updated dates, retrieval time, version evidence, type, document/project/duplicate group, attributable spans and fetch outcome. Store unrestricted raw inventory only in 04's restricted staging area. Publish only approved fitting/development material and hashes.
Research Taste Exercises quotes other people's suggestions; preserve speaker attribution. Reflections on Qualitative Research is coauthored with Adam Jermyn. Interpretability Dreams repeats passages from earlier work; group these for split integrity. Large Transformer Circuits collaborations do not establish that Chris authored every judgment or rejected a proposed alternative. Use contribution statements when available.
Separate explicit preferences, methodological beliefs, technical facts, team strategy and observed project involvement. Do not infer private preferences, rank invented alternatives or erase ambiguous attribution. Coordinate duplicate handling with 02 and 04 without copying hidden source text into common messages.

CHECKS AND HANDOFF
Test parser/dedup behavior with fixtures; verify source spans match stored bytes, dates refer to the observed version where possible, and truncated pages are flagged. Send raw batches to 04 for eligibility and split assignment. Quarantine uncertain sources. Tell 04 if there are too few explicit comparisons; do not manufacture them to meet a sample quota.

DONE
Reproducible clean batches, attribution/duplicate/version quality counts and documented gaps. Prefer good methodological evidence over a large pile of weakly attributed papers.'''),
dict(id='04',slug='evaluation',name='Evaluation and final-data custodian',depends=['00 to start; 02/03 inventories for DATA_READY; 01 for scoring'],paths=['autoresearch/taste/overnight/evaluation.py','tests/test_overnight_evaluation.py','data/profile_eval/<campaign>/public/','restricted evaluator store outside every worker checkout'],body='''YOUR ROLE
Own source eligibility, document grouping, splits, target provenance, scoring, selection-evidence quality and the single final-data reservation. Do not build candidate profiles or tune target construction to their scores.

FIRST DELIVERABLE
Publish the source/split policy and restricted-store setup after 00, without waiting for corpus inventories or the finished scoring interface. Those inventories gate DATA_READY, not starting your work. Accept raw inventories in a restricted store outside Git and all worker checkouts. Assign whole document/project/revision/crosspost groups to fit, development and confirmation. Publish an approved input bundle plus a manifest of opaque held-out IDs and counts; no held-out titles, URLs, passages or answers. Builders must lack access to the full corpus. State the practical isolation limits honestly.
Use explicit source-backed judgments with context first. Label tiers: explicit stated comparison; observed choice with known alternatives/constraints; model-inferred label. Keep tiers separate. A generated alternative is not a documented rejection. Never label two papers in an unordered list as a preference ranking. A second model's agreement is QA, not ground truth.

MEASUREMENT
Freeze target-construction rules and source spans independently of candidates. Report source groups and per-researcher counts, not merely question count. Accuracy includes failures as failures; probability metrics report coverage and invalid outputs. Use paired comparisons and source-group-aware uncertainty; avoid meaningful-looking intervals from one group. Keep PRISM recorded preferences separate from archival research judgments. All tuning uses dev.
Before candidate scoring, publish valid target counts by researcher, label tier and independent source group plus a feasibility decision. With no valid labels or no defensible independent holdout, deliver extraction/development artifacts and mark fidelity unmeasured. Small usable samples may support a labeled descriptive pilot, not a confirmatory improvement claim.
Prepare the answer-known scaling subset by a predeclared source-evidence rule, not by which tested model gets the answer right. Withhold the answer-bearing source. Generate the same decision inputs and option-order schedule across model levels. The scaling worker cannot define its own ground truth.
Utility outcomes come from the existing team harness owners with independently checked task validity, paired tasks/seeds and frozen budgets. Request their manifests through 00; do not rewrite their scorer. If unavailable, report utility unmeasured.

FINAL CUSTODY
Before any final exposure, assemble one immutable manifest covering core finalists, no-profile/raw/retrieval and own/swapped/shared controls, declared scaling arms, items, settings, replicates, metrics and retry rules. Final use requires existing user authorization for that concrete batch. One evaluator process/store is authoritative across all clones. Consumption is keyed to the canonical final dataset/split and underlying target/user identities. Attach the manifest hash as immutable reservation metadata; atomically reject overlapping or already consumed identities regardless of manifest, clone or retry. Retain a durable ledger of reservation, exposure, failures and completion. The existing Git-common-directory PRISM guard protects worktrees but not independent clones; never bypass it, and also prevent other clones from executing a final command. Keep final inputs, predictions, rationales, raw traces and cache entries in evaluator-supplied private roots, not shared worker stores or Git. Handoffs contain hashes, status and authorized aggregate metrics only. A crash after reservation/exposure does not grant a new attempt. Do not release partial scores to adaptive workers.
Check multiple confirmatory claims appropriately and report all planned comparisons. Do not pick a new champion from final scores. Requests for changes after exposure require fresh evidence.

CHECKS AND DONE
Test near-duplicate/project isolation, missing versions, answer-bearing fields excluded from worker bundles, label-free prediction input, immutable manifests, duplicate reservation, interrupted final consumption and missing arms. Publish DATA_READY with allowed hashes and development targets. At the end publish dev results plus authorized aggregate confirmation, or exact reasons fidelity/utility remains unmeasured. Missing evidence is a valid result.'''),
dict(id='05',slug='baselines',name='Baselines and retrieval',depends=['01 CONTRACT_READY','04 DATA_READY for live runs'],paths=['autoresearch/taste/overnight/baselines.py','autoresearch/taste/overnight/retrieval.py','tests/test_overnight_baselines.py','tests/test_overnight_retrieval.py'],body='''YOUR ROLE
Own no-personal-context, name-only, raw-evidence, simple memory-summary, lexical retrieval and semantic retrieval baselines. You also own profile-plus-retrieval composition once profile workers deliver artifacts. Do not modify their profile builders.

IMPLEMENT
Use the shared contract and the same allowed document pool and consumer settings as candidate methods. Separate no-profile from name-only. Provide deterministic raw-evidence packing and matched-token retrieval. Document query construction, chunking, ties, dedup, truncation and token count. Implement lexical retrieval without a new heavy dependency. Semantic retrieval uses a verified available embedding backend under policy; if unavailable, label the arm unavailable instead of substituting lexical and keeping the semantic name.
Plain memory must be a real baseline, not intentionally weak. Reuse P1's frozen plain summary when appropriate to avoid independent duplicate construction; record whether it is identical. Do not force a custom taste schema into the summary control.
For profile+retrieval, split the same total personalization cap between profile and passages. The coordinator registers the split before scoring. A larger-context raw arm may be separately labeled. Own/swapped/shared-profile controls use equal lengths and task conditions; peer data must obey the same exclusions. Absence of a peer statement does not show disagreement.

CHECKS
No-profile payload contains no author cue, profile or prior examples; name-only includes no hidden history. Retrieval never indexes held-out documents. Packing is reproducible and does not exceed the declared cap. Cache keys change with query/model/source settings and option order. Fail closed on unavailable input or backend. Give consumption traces to the existing audit owner for independent checks.

DONE
Registry entries and runnable offline examples for each available arm, honest unsupported statuses, latency/usage accounting and coordinator-assigned dev results. Notify 09 of controls usable unchanged across three consumer levels. Do not run an independent candidate search.'''),
dict(id='06',slug='profiles-summary',name='Profile builders P1–P3',depends=['01 CONTRACT_READY','04 approved input bundle'],paths=['autoresearch/taste/overnight/profiles_summary.py','tests/test_overnight_profiles_summary.py'],body='''YOUR ROLE
Own exactly P1 plain summary, P2 research-task-guided summary, and P3 fixed question-schema extraction. The schema is filled from documents; no human interview is required.

IMPLEMENT
Read only approved inputs. P1 compresses without a special taste ontology. P2 focuses on research decisions using a fixed task-family description, not a held-out answer. P3 reuses the revised questions already being developed if accessible; ask the coordinator to locate that owner/output before inventing a competing template. If unavailable, create one documented version and label it a new candidate, not the team's prior agreement.
Support explicit-only and explicit-plus-marked-inference policies consistently. Unknowns remain unknown. Preserve supporting source IDs/spans, conditions and dates; separate beliefs from preferences. Produce global profiles, not target-answer-conditioned profiles. Use profile caps 512/2048/8192; report infeasible schema/cap pairs rather than silently dropping required fields. Provide three independent builds only when dispatched; unsupported backend seed settings must be recorded honestly as replicate IDs.
Submit registry metadata to 01; do not edit registry.py or shared __init__.py. Initial implementation has no per-method custom research-loop prompts. The frozen consumer receives the profile through the common renderer.

SEARCH AND CHECKS
00 schedules the common grid. You may propose development-only mutations with a parent hash and stated hypothesis; only assigned jobs run. Use new IDs for revisions. Test source provenance, explicit-only exclusion of inferred claims, unknown fields, invalid/empty outputs, cap failure and deterministic serialization. Do not infer that a richer output is better without comparative results.

DONE
Three callable builders, representative inspectable artifacts, request/response and provenance hashes, adaptation notes and coordinator-assigned development results. Hand P1 to 05 for a shared memory-summary control and avoid generating it twice.'''),
dict(id='07',slug='profiles-principles',name='Profile builders P4–P6',depends=['01 CONTRACT_READY','04 approved input bundle'],paths=['autoresearch/taste/overnight/profiles_principles.py','tests/test_overnight_profiles_principles.py'],body='''YOUR ROLE
Own exactly P4 atomic evidence-linked principles, P5 conditional decision rules, and P6 a hierarchy organized by research decision type. These are writing-based structures, not reproductions of preference-supervised ICAI.

IMPLEMENT
P4 stores each preference separately with source spans, context, date, explicit/inferred status, uncertainty and exceptions. P5 represents conditional tradeoffs: prefer an action under a stated condition, with counterconditions where supported. P6 groups preferences by the existing research decision types, using the repo's actual decision definitions. Do not redefine the team research loop or decision meanings.
Use only the approved source pool. Distinguish personal preference, empirical belief and verified environment fact. Do not invent causal assumptions or numeric utility weights. Missing support yields unknown/unsupported. Support both evidence policies and 512/2048/8192 caps; an infeasible format is a recorded outcome. A flat atomic list is the default: graph expansion is a later coordinator-assigned ablation.
All output passes through 01's renderer and consumer. Submit registry entries without editing the shared registry. Get the existing integration audit owner to verify rich fields reach the actual consumer; do not implement another audit suite.

SEARCH AND CHECKS
Only run assigned grid cells. Proposed pruning, reflection or hierarchy changes require parent IDs and a development hypothesis. Preserve original and rejected principles with reasons, not only survivors. Tests cover exact source references, absence of fabricated conditions, explicit/inferred separation, conflicting evidence preserved, empty profile status and representation/cap feasibility. No model confidence is treated as measured reliability.

DONE
Three independent builders, evidence-readable profiles, registry metadata, fit costs and dispatched dev results. State which structures are proposed adaptations and which parts follow a cited method. No claim that source-grounded principles necessarily predict choices.'''),
dict(id='08',slug='profiles-hypotheses',name='Profile builders P7–P8',depends=['01 CONTRACT_READY','04 approved target and peer bundles'],paths=['autoresearch/taste/overnight/profiles_hypotheses.py','tests/test_overnight_profiles_hypotheses.py'],body='''YOUR ROLE
Own P7 contrastive researcher profiles and P8 competing/time-varying preference hypotheses. These test distinct hypotheses; do not add new researchers or expand collection on your own.

IMPLEMENT
P7 compares target and approved same-field peer evidence to isolate supported distinctions. Every contrast needs target and peer provenance; silence is not evidence that the peer disagrees. If Neel and Chris share a preference, preserve it as shared. If the peer bundle is too weak or unavailable, mark this arm unavailable. All peer sources obey the same temporal/document exclusions.
P8 preserves multiple plausible preferences, conditions and dates rather than forcing a single stable persona. Distinguish an actual stated change from incompatible evidence or extraction uncertainty. Do not invent probability weights; any heuristic confidence must be explicitly uncalibrated. Use a fixed deterministic policy for rendering hypotheses to the common consumer so hidden extra reasoning does not confound the comparison.
Support explicit-only and explicit-plus-marked-inference policies and the three caps where feasible. Do not read withheld documents to infer a timeline. No new profile generation from evaluation answers.

SEARCH AND CHECKS
Follow coordinator-assigned jobs and fixed source hashes. Test that absence never produces a contrast, peer evidence cannot cross splits, repeated/collaborative sources do not count as independent support, contradiction remains represented, and date uncertainty is not silently resolved. Proposed ensembles/temporal weighting are later registered development ablations, not unlogged default behavior.

DONE
Two builders, supported/unsupported contrast records, inspectable competing hypotheses, provenance and cap accounting, and assigned dev results. Supply equal-length swapped/shared controls to 05 through artifact hashes rather than modifying its code.'''),
dict(id='09',slug='scaling',name='Targeted model-scaling study',depends=['01 neutral-profile consumer support','04 evaluation/capability panel','00 FINALISTS_FROZEN','05 baselines'],paths=['autoresearch/taste/overnight/scaling.py','tests/test_overnight_scaling_manifest.py','docs/overnight/<campaign>/scaling/'],body='''YOUR ROLE
Own the scaling manifest, assigned scaling execution and analysis. Prepare early, but do not repeat the entire method search across all models, choose your own winners, collect duplicate data or define labels. Final execution remains exclusively with 04.

MODEL PANEL
Ask 00 for three verified model levels S/M/L and exact backend IDs, versions, settings, capabilities and allocations. Prefer a reasonably matched family. Separate a size comparison from a generation comparison; report differences in training recipe/context/reasoning when known. If parameter sizes are undisclosed, do not label the axis parameter count. If three models are unavailable, deliver the supported comparison with an explicit missing arm; do not invent a proxy model. Any independent capability ordering must come from evidence outside the result being claimed.

STUDIES
A. End-to-end: evaluate 2–3 dev-selected methods and no-profile/raw-or-retrieval controls at S/M/L on the SAME item IDs. If each level re-extracts and consumes, label this joint scaling.
B. Consumer-only: freeze one neutral profile's exact content hash and vary only the consumer. Use a fresh consumer adapter. Never bypass UserModel.load_model backend checks or transport learned weights/calibration across models.
C. Small diagnostic cross: for the primary selected method, use extractor S/L × consumer S/L. Deduplicate cells already run in A/B. The middle model needs only the declared end-to-end or consumer-only arm unless the coordinator expands it. Differences in prompts/rendering must be explicit factors.
D. Documented-judgment inference diagnostic: use 04's answer-known archival subset with fixed raw evidence, no candidate-derived profile, and identical permitted context across models. Each model predicts the documented judgment with the answer-bearing source withheld. Score against the independent recorded judgment. This is task-specific inference ability, not an independent measure of general capability. Profile-conditioned diagnostics require separately declared arms. Keep agreement on unknown/inferred labels separate; no stronger-model-as-truth shortcut.

CONTROLS AND ANALYSIS
Use the same task context, allowed corpus, feasible common personalization cap, truncation rule, option orders and settings where supported. Record deviations and all failures. Report absolute scores AND personalization gain over the matched raw/retrieval baseline at each level. Keep fidelity and downstream utility in separate panels, with uncertainty/cost. Higher absolute scores alone do not establish growing personalization benefit. Three points give an observed trend, not a general scaling law. Own/swapped/shared controls diagnose general guidance vs individual fidelity.
Freeze methods, task subset, model identities and all arms from dev data before confirmation. 00 and 04 include them in the SAME final manifest as the core comparison. Do not run a first final test for core methods and reopen it for scaling. Any utility scaling needs a frozen task manifest from existing downstream owners; do not rewrite the loop or judge.

CHECKS AND DONE
Tests pin same item IDs and option schedules across levels; distinguish joint/extractor/consumer/inference-diagnostic estimands; verify fixed-profile hashes; reject changed consumer under a backend-bound model; reject unspecified or late-edited arms. A complete manifest may explicitly mark an arm unavailable before reservation; distinguish planned unavailability from execution failure, and freeze any reduced panel before confirmation. Supply comparison packets to the existing audit chat for declared-variable validation. Deliver full cell-level results, paired differences and missing cells, with no selective dropping.'''),
dict(id='10',slug='labeled-reference',name='Recorded-preference reference track',depends=['00 allocation','04 split policy','existing M0–M3 code'],paths=['scripts/overnight_labeled_reference.py','tests/test_overnight_labeled_reference.py','docs/overnight/<campaign>/labeled-reference/'],body='''YOUR ROLE
Optional parallel lane: reuse existing PRISM development data and M0/M1/M2/M3 to anchor behavior on recorded user preferences. Do not rebuild the benchmark, duplicate model implementations, change existing manifests or consume final users.

IMPLEMENT AND RUN
Inspect the current frozen manifest and preserved live pilot rather than relying on stale notes. The pilot on one user is plumbing evidence, not a winner. Use only development users and coordinator-assigned matched jobs. Record exact existing bounded adaptations of SynthesizeMe/ICAI, fitting budgets, prompts and confidence limits. Model changes require refitting; never load backend-bound learned state on a new backend.
If 00 assigns richer variants, propose their hypothesis and ownership first; do not edit existing m2/m3 files under another owner's lock. Keep genuine recorded preferences separate from archival stated judgments and pseudo-labels. Do not average the benchmark score with the researcher study's score.
Evaluate accuracy, per-user differences, probability quality, failure rate and total fit/predict usage. Empty M2 artifacts and negative results are outcomes, not automatic bugs or grounds to keep trying until they look good. Preserve them.

CHECKS AND DONE
Verify exact development-only user selection, source/manifest hashes, no final command switches, matched method configurations, unchanged final marker and non-overwritten results. Deliver development evidence, limitations and reusable settings to 00. This lane is not required to block the researcher-profile or scaling study.'''),
]

HANDOFF = {
 'schema_version':'overnight-handoff-v1','campaign_id':'assigned-by-coordinator','role_id':'ROLE','event':'CONTRACT_READY|DATA_READY|METHOD_READY|JOB_COMPLETE|FINALISTS_FROZEN|BLOCKED|DONE',
 'sequence':1,'status':'complete|partial|blocked|unsupported','branch':'codex/gio-overnight-ROLE','code_commit':'full SHA','contract_sha256':'sha256',
 'inputs':[{'manifest_sha256':'sha256','allowed_bundle_id':'opaque ID'}],
 'outputs':[{'location':'verified portable artifact location or repository path','sha256':'sha256','visibility':'shared-dev|evaluator-only|released-final'}],
 'checks':[{'command':'exact command','exit_code':0,'result':'observed result'}],
 'job_ids':[],'usage':{'attempted_calls':0,'reported_api_usd':None,'cost_status':'measured|estimated|unavailable'},
 'limitations':[],'blocked_on':[],'next_consumer':[]
}

CONTRACT='''# Shared contract for the overnight profile study

This packet is a task specification for agents Gio chooses to launch. It does not report completed implementation or authorize unspecified model spend/final-test use. The coordinator resolves runtime facts once and shares them. The current user-model code already exists; extend it additively.

## Ownership and communication

One coordinator owns the canonical board, run policy, job queue and integration branch. One infrastructure owner owns shared code interfaces. One evaluator owns all splits/labels/final reservations. Each method module has one writer. Existing audit chat `01a1de44-b76b-7290-9753-ba528b42819e` is the integration-audit owner. Existing team owners retain research-loop and scorer implementation.
The audit owner reports branch `codex/gio-integration-audit`; reserve `scripts/user_model_audit/`, `tests/test_user_model_profile_audit.py`, `tests/test_user_model_packet_audit.py` and `docs/user-models/integration-audit/`. Obtain exact current commits before reuse. This pack does not independently verify the audit's reported test results or reserve its paths remotely.

The existing agentctl operates on the current branch and stages all .agents changes; its printed success is not proof a push succeeded. All overnight-board mutations go through a serial coordinator in a dedicated clean main-tracking coordination clone. Workers never treat separate feature-branch locks as global. The coordinator verifies reservations at origin/main and checks conflicts with teammates. Do not fix agentctl as an unplanned side project.

Worker-to-coordinator transport: a direct agent/chat handoff notification plus a unique event file `docs/overnight/<campaign>/handoffs/<role>/<sequence>-<event>.json` on the worker's branch. If direct tools are unavailable, return the exact branch/SHA/path to Gio for relay. The coordinator fetches exact commits, verifies hashes and publishes receipt. Do not block useful fixture work while waiting. Messages are not a substitute for artifact publication. Do not rewrite past events.

Workers send PATH_REQUEST, coordinator returns PATH_RESERVED only after remote verification. Interface changes require a new contract version and acknowledgments from affected workers before use. All workers read the current ownership manifest at each handoff. The collector's full inventory is restricted; only evaluator-approved subsets reach builders.

## Proposed v1 interface

These names are part of this task spec, not claims about current repo code. Infrastructure implements them and publishes CONTRACT_READY before workers bind to live data.

`build_profile(documents, config, extractor) -> ProfileArtifact`

`predict_profile(profile, context, options, consumer, config) -> Prediction`

`Prediction` reuses choice/confidence/rationale/probabilities/calibrated from the existing interface. Prediction inputs have no chosen answer or answer-bearing reason. A separate status distinguishes invalid, abstained and unavailable. Raw confidence is uncalibrated. All method-specific content must reach the consumer through one explicit renderer or be reported as unused.

Document records: schema_version, opaque document_id, researcher_id, canonical URL, observed content hash, content/allowed local reference, author/contribution, publication/update/retrieval times, version evidence, document/project/duplicate group, evidence type, permitted source-span references, split eligibility. Public worker bundles contain only approved records. Hidden inventories, answers, answer-bearing titles/URLs and supporting spans remain evaluator-only.

Profile records: schema_version, profile_id/content hash, researcher_id, method_id, config_id/hash, allowed_source_manifest_hash, extractor backend/model/version/settings, replicate_id (seed if supported), rich content with provenance, token counts/cap, empty/unsupported status, confidence/weights availability, fit usage, prompt hash and code SHA. Content supports prose, atomic claims, conditions, examples, hierarchy, contrasts and dated hypotheses. Do not flatten rich fields away in an adapter without reporting that choice.
Also pin method/renderer implementation hashes and saved/runtime prompt versions. The audit owner has reported cross-version conditioning differences under an apparently compatible backend. Obtain reproducible evidence, treat legacy compatibility as unverified, and reject undeclared implementation migrations before any score is attributed to a candidate.

The consumer is recorded separately. Existing saved UserModel objects are backend-bound; do not remove that protection. A neutral text profile may be passed to a fresh consumer for a declared cross-model study. Learned feature weights and calibration do not transfer through this mechanism.

Job records: schema_version, campaign_id, job_id, stage (offline/dev/confirmation), kind (build/predict/capability/utility), contract/config/source/item/profile hashes as applicable, method, extractor and consumer identities/settings, personalization cap, option-order schedule, replicate IDs, code SHA, authorized allocation, retry policy, parent job(s) and expected outputs. Compute job_id from the complete semantic manifest excluding mutable lease/timestamps. The coordinator grants one execution lease. Record every retry/attempt; unknown prior paid-call status is not permission to duplicate it.

Result records: job_id, status, code/config/source/profile hashes, attempted/complete/error counts, predictions or evaluator-only scores, usage/cost status, raw trace hashes, rendered-profile/payload hashes, actual settings and missing arms. Run outputs are immutable. Do not replace failures with a no-profile output while retaining the candidate's name.
For confirmation, all inputs, predictions, rationales, raw traces and cache entries stay in private roots supplied by the evaluator. Shared handoffs contain hashes, execution status and authorized aggregate metrics only. Generic worker caches are prohibited for confirmation payloads.

## Source and evaluation isolation

Collectors send raw data to one restricted evaluation store outside worker checkouts and Git. The evaluator groups documents/versions/projects/crossposts before approving builder access. Fit documents provide profile evidence; dev targets support search; confirmation targets are withheld. Model-inferred labels and explicit archival comparisons are separate tiers. Random sentence splits and automatic alternative generation cannot create independent researcher-choice truth.

The coordinator may share dev score summaries for adaptation. Confirmation is one authorized frozen batch covering both core and scaling arms. A central evaluator owns its durable atomic reservation across clones, in addition to the repo's existing PRISM worktree guard. No worker receives final targets/labels or partial confirmation feedback. A consumed/partially exposed set never becomes fresh because a job failed. Existing one-use markers are never removed. Actual enforcement limits must be documented.
Key final consumption to canonical dataset/split and underlying user/target identities. The manifest hash is fixed metadata, not a new eligibility key: changed manifests, subsets and clones cannot reuse overlapping consumed data. Publish a source-count/independent-group feasibility decision before scoring; insufficient labels or an indefensible holdout means fidelity is unmeasured, while small usable samples support descriptive pilots only.

## Search and scaling

Core P1–P8 grid: 3 profile caps (512/2048/8192) × 2 evidence policies (explicit-only / explicit plus marked inference) × 3 extraction replicates × 2 researchers. This is 48 design configurations and 288 builds if all feasible/authorized, not 288 methods. Source availability and consumer settings are matched. Rank configurations across replicates; frozen instance selection is a separate declared policy.

Screen on dev, promote under a written family/global rule, then run matched larger dev comparisons. Add hybrids or adaptive descendants only with parent IDs and source/settings hashes. Candidate selection, task-subset selection and model-panel choice must finish before confirmation.

Scaling uses 2–3 selected methods, mandatory no-profile and raw/retrieval controls, three verified model levels, the same decision IDs and context cap. Distinguish joint extraction+consumer scaling from fixed-profile consumer scaling. Add a small S/L extractor × S/L consumer diagnostic for the primary method and reuse identical cells. Capability-label inference uses a source-defined answer-known subset, with answer-bearing sources hidden. Report fidelity and utility separately, absolute scores and gains over the matched baseline, costs/failures/uncertainty. No model-name ordering masquerades as measured capability or known parameter size.

## Implementation and run boundaries

All proposed paths require the coordinator's fresh remote reservation. Substantially different existing modules should be reused by their owner rather than duplicated under these paths. Existing dirty checkouts and unknown ` 2` files are preserved. New code under autoresearch uses Python 3.9+ and the standard library; no broad dependency additions. Use offline fixtures while waiting on live authority. Each code owner runs meaningful targeted tests and the current required suite before pushing code. Live runtimes use pinned immutable snapshots; no edits under a running experiment.

One total run policy controls API dollars, CLI attempts, wall time, concurrency and stop/retry behavior. Carry forward actual existing approval without inventing a balance; null allocation means the relevant live stage is not available. This packet itself does not spend money or consume final data. If a concrete missing decision remains, only the coordinator asks Gio, after preparing the exact proposed run.
'''

DESIGN='''# Overnight researcher profile search design

Status: approved direction from the conversation; concrete scheduling defaults are proposals for the coordinator to instantiate. Gio asked for a handoff pack, not for this chat to launch experiments.

Goal: broad, traceable comparison of user-profile methods using Neel Nanda and Chris Olah's writing, followed by a targeted scaling study. Measure archival researcher fidelity and independently checked research utility separately. Human questionnaire collection is deprioritized; a document-filled template remains one candidate.

Eight text builders cover plain/task-guided summaries, a fixed schema, atomic principles, conditional rules, a decision hierarchy, contrastive profiles and competing/time-varying hypotheses. Controls cover absent/name-only personal context, raw source text, summary memory and lexical/semantic retrieval. Profile+retrieval is a staged hybrid. Existing PRISM M0–M3 provides a separate recorded-preference reference track. Optional BUMP-style training, utility-trained stopping and parameter adapters are later studies, not hidden overnight dependencies or authorized new infrastructure.

Start broad on development evidence with the same sources, consumer and token budget within a condition. Compare 48 structural configurations with extraction replication if the measured resource policy supports it. Promote a few families fairly, then permit logged development-only mutations. Frozen final comparisons use untouched evidence and report all planned arms, including failures.

The scaling study is deliberately targeted. Select 2–3 methods on dev; compare them with controls across three verified model levels and identical task IDs. Separate fixed-profile consumer effects from joint extraction/consumer changes. Use an S/L 2×2 diagnostic and an independently source-defined answer-known inference subset. Record absolute scores and gain over the raw/retrieval baseline at each level. Do not infer a scaling law from three models or make the largest model the truth labeler.

Source labels distinguish explicit statements from observed choices and model inference. Corpus splits use document/project/revision groups. Famous-author contamination, coauthorship, changing beliefs and imperfect archival targets remain reported limits. Two cases cannot establish general researcher-model performance. No candidate agent receives unrestricted corpus/final answers.

The integration audit is already owned by chat 01a1de44-b76b-7290-9753-ba528b42819e. This pack reserves that scope. Gio's workers own user models and handoff contracts; existing team owners keep the downstream harness/scorer. Utility can remain unevaluated if that dependency is unavailable.

Alternatives considered: repeat the entire search across models (too confounded and duplicates development effort); use only strong-model-inferred labels (does not independently validate researcher fidelity); run a human interview before all work (not compatible with Gio's attention constraint tonight). Chosen approach: a broad single-reference-model search plus targeted scaling and separate source-backed confirmation.
'''

PLAN='''# Overnight User Profile Search Implementation Plan

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

ROLE_TABLE

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
'''

AUDIT='''Continue your existing integration-audit assignment for Gio. This message expands the inputs you should expect; it does not create a second owner.

Your reserved scope remains offline saved-profile -> actual conditioning, export/save-load, empty-profile and confidence/fallback, and comparison-packet variables. Chat owner: 01a1de44-b76b-7290-9753-ba528b42819e.

The overnight plan adds eight text-profile builders, common baseline/retrieval controls and a targeted model-scaling study. Request the contract hash, exact code commit, allowed fixture, profile hashes and run/comparison manifests from the coordinator. Infrastructure (01) owns the neutral profile adapter/renderer; scaling (09) owns the study matrix; evaluator (04) owns hidden labels and final reservation.

Please verify that rich profile content reaches the actual consumer, no-profile is genuinely empty, name-only has no hidden history, equal-context controls are truthful, fixed-profile consumer scaling preserves the exact profile, and joint extraction+consumer scaling is labeled separately. Existing backend-bound UserModel objects must not be loaded on another backend by removing guards; neutral text profiles use fresh consumers. Confidence must not become calibrated merely because the backend changed. Check that reported rows correspond to declared models, settings, item IDs, option schedules and hashes.

Use only coordinator-approved development fixtures and released artifacts. You do not need final labels. Send findings with an exact reproducer and code/artifact hashes to the owning worker through the coordinator. Keep your established isolated paths/branch and do not change main harness/models/settings without the existing agreement with Gio. Deliver audit status per packet: verified, failed or unverified, with the precise missing evidence. Do not repair another owner's module silently.
'''
UTILITY='''For the existing downstream research-loop and measurement owners: Gio's overnight user-model workers will provide frozen profile artifacts and their interfaces. We need a matched utility comparison; this is not a request to build another loop or change your scorer.

Return the currently supported task IDs/splits, validity checks, outcome measures, runtime model/settings/tools, costs/budgets, paired seed policy and accepted artifact interface. If any measurement gate is unvalidated, preserve that limitation next to outcomes.

Requested conditions: own profile, same-domain swapped profile, shared generic profile, raw/retrieved source baseline and no profile, under the same tasks, starting evidence and runtime budgets. A small selected-method/model-level subset can be added only to the frozen manifest; do not multiply all exploratory candidates into full loop runs. Record profile, code, settings and task hashes per result. Report valid findings, failures, reproducibility and cost separately from researcher fidelity.

Coordinate with evaluator 04 so utility and fidelity confirmation use prespecified manifests without partial-score adaptation. No new spend or main-harness changes follow merely from receiving this request; reuse existing authority and tell the coordinator what is executable. If unavailable, return an explicit unsupported/deferred result and a concrete next dependency. Keep ownership in your current workstream.
'''

def main():
    (ROOT/'prompts').mkdir(exist_ok=True)
    (ROOT/'SHARED_CONTRACT.md').write_text(CONTRACT)
    (ROOT/'design.md').write_text(DESIGN)
    (ROOT/'handoff-schema.json').write_text(json.dumps(HANDOFF,indent=2)+'\n')
    all_prompts=[]
    for r in ROLES:
        fn=f"{r['id']}-{r['slug']}.txt"
        body=f"ROLE {r['id']} — {r['name']}\n\n"+COMMON+f"\nDEPENDENCIES: {', '.join(r['depends']) or 'none; first owner to start'}\nOWNED PATHS (after reservation):\n"+'\n'.join('- '+p for p in r['paths'])+'\n\n'+r['body']+'\n'
        (ROOT/'prompts'/fn).write_text(body)
        all_prompts.append(body)
        r['prompt_file']='prompts/'+fn
    (ROOT/'prompts'/'11-existing-audit-handoff.txt').write_text(AUDIT)
    (ROOT/'prompts'/'12-existing-downstream-request.txt').write_text(UTILITY)
    (ROOT/'ALL_PROMPTS.txt').write_text(('\n\n'+'='*72+'\n\n').join(all_prompts+[AUDIT,UTILITY]))
    table='| Role | Prompt | Depends on |\n|---|---|---|\n'+'\n'.join(f"| {r['id']} {r['name']} | [{r['slug']}]({r['prompt_file']}) | {', '.join(r['depends']) or 'Start first'} |" for r in ROLES)
    table+='\n| Existing audit owner | [Additive handoff](prompts/11-existing-audit-handoff.txt) | Contract and development artifacts |\n| Existing downstream owners | [Utility request](prompts/12-existing-downstream-request.txt) | Frozen profiles and supported harness |'
    (ROOT/'README.md').write_text(PLAN.replace('ROLE_TABLE',table))
    (ROOT/'ownership.json').write_text(json.dumps({'schema_version':'proposed-ownership-v1','status':'dispatch-plan-not-live-reservations','repository':REPO,'roles':ROLES,'reserved_audit_chat':'01a1de44-b76b-7290-9753-ba528b42819e'},indent=2)+'\n')
    print(f'Created {len(ROLES)} launch prompts, 2 existing-owner handoffs, plan, design, contract and schemas in {ROOT}')

if __name__=='__main__': main()
