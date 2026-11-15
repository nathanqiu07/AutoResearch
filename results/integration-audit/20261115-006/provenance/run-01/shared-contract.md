# Shared contract for the overnight profile study

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
