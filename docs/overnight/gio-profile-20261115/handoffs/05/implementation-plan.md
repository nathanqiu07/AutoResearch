# Baseline and retrieval implementation plan

Goal: deliver comparable controls through the neutral profile contract, using only evaluator-approved inputs. Owner: gio-overnight-05. Base: d66051c6b792e2a9062f334535cf61ff9f51a15a.

Architecture: additive builders in baselines.py, pure in-memory retrieval and packing in retrieval.py, existing build_profile/consumer unchanged. No calls during fixture development. Python 3.9+ / standard library. Specification: role05 and SHARED_CONTRACT in the overnight dispatch packet.

- [x] Implement deterministic source-validated chunking, lexical BM25 ranking, exact-byte JSON packing and semantic-unavailable status. Tests first: unknown/modified sources rejected; ranking relevant source first; ties/order deterministic; unicode fits cap; source spans reproduce; cache identity changes with options, model, source and parameters.
- [x] Implement no_profile, name_only, raw_evidence, lexical_retrieval and semantic_retrieval builder registration. Test actual consumer payloads, no accidental author/source metadata, explicit unavailable/empty output and no extraction calls.
- [x] Reuse a supplied frozen P1 summary unchanged for memory_summary; compose frozen profile plus retrieved excerpts under a registered profile/passage byte allocation. Test source/researcher/hash compatibility, profile preservation, combined cap and zero silent fallbacks.
- [x] Run targeted and repository tests, independent review, synthetic fixture generation; push own branch and send exact hashes to coordinator/audit. Live development jobs only from coordinator after DATA_READY.

Decisions: UTF-8 bytes follow shared conservative cap, not tokenizer counts. Chunking uses fixed nonoverlapping character windows with exact source offsets; retrieval scores are BM25, stable ties use document ID/start. Query consists only of context and options, preserving option order in identity. Exact duplicate excerpt text is indexed once. No semantic substitution without an authorized embedding backend. Summary/profile controls require a compatible immutable ProfileArtifact and preserve its content; cap mismatch is unavailable, not silent truncation.

Review focus: hidden fields entering prompts; labels in decision objects; unapproved source sets; stale/foreign profile reuse; query-specific retrieval accidentally reused for a different item; JSON overhead making caps incomparable; retrieval helper changes omitted from registration identity.

Progress: clean original-base suite passed 656 tests, two skipped. Contract-ready base is now checked out; next check includes its additive tests.

Independent review: one important defect (malformed frozen artifacts raised AttributeError) reproduced in eight subcases and fixed via structural checks; all 18 targeted tests pass.
Ruling: cross-consumer reuse is supported by the neutral contract, so consumer identity is recorded in retrieval cache identity but is not an inference prohibition.
Ruling: the shared runner must enforce retrieval decision binding; helper/prompt compatibility and final-data custody remain infrastructure/evaluator responsibilities, with exact integration requirements sent to the coordinator. No claim of live quality or semantic coverage.

Verification: final implementation passed 681 repository tests (two skipped), and all 18 targeted tests. Synthetic fixture showed six complete controls and semantic unavailable; no live calls.

## Followup: semantic bundle support

- [x] Add exact embedding-input construction and immutable source/query/model-bound vector bundles, then cosine ranking under the existing packer. No network adapter or ungated model calls.
- [x] Exercise modified queries, option order, vector shape/norm, missing model, missing live-producer provenance, and oversized numeric coordinates; rejected bundles remain unavailable.
- [x] Independent review found missing model and live provenance checks on load; both reproduced RED and fixed. A huge-integer coordinate also reproduced an OverflowError and now yields a controlled ValueError.
- [x] Publish the second fixture/handoff and send exact commits for integration. Live embeddings remain a separate coordinator allocation.

Ruling: vector bundle hashes establish input consistency, not provider authenticity or paid-cost reconciliation. Producer job traces remain required. Embedding costs are recorded once at production and retained as separate metadata on reuse.

Semantic verification: 22 targeted tests passed; full repository suite 685 tests passed, two skipped. Offline semantic fixture exercised all seven controls; no model calls. Compatibility snapshot against infrastructure05c503e passed the then-current21 tests before the final metadata regression was added.

## Released input check

- [x] Read only the exact two Tier-A development-v2 releases from role04's immutable handoff; validate file, item and approved source hashes.
- [x] Add a portable zero-call construction checker for the four pilot controls plus explicit missing prerequisites for the other three. Reuse existing constructors; avoid a second prediction-audit framework.
- [x] Independent review identified vacuous success for empty released item lists; reject those inputs explicitly. No private labels or model calls.
- [x] Publish the immutable construction report and send its exact runtime/code/hash context to the coordinator (3b0539e).

## Semantic numerical correction

The independent integration audit reported subnormal-vector ranking instability. Reproduced with query and aligned document [1,1], and another document [5e-324,1e-323]: the latter normalized to [.5,1] and incorrectly outranked the aligned document. A public semantic-ranking regression failed at the subnormal scale before the fix. Normalizing by the maximum absolute coordinate before the L2 norm preserves direction and avoids raw-norm underflow/overflow. Normal, subnormal and large-scale ranking checks pass. Independent static review found no further important issue; 23 targeted tests and 686 repository tests passed, two skipped. This does not establish any live embedding defect. The helper/policy hash changes, so new runtime artifacts must be rebuilt; historical fixtures remain pinned to their original code.

## Producer receipt assembly

- [x] Prepare two exact embedding requests over development-v2: 40 unique strings, 20,732 input-text UTF8 bytes, 28 decision mappings. Published proposal c234f81; no calls.
- [x] Add the offline assembler in this handoff directory, preserving the frozen retrieval helper bytes. Producer execution remains owner01/coordinator scope.
- [x] Nine synthetic assembler tests pass, including reordered/duplicate/missing indices, source/query mismatch, stale helper, incomplete producer provenance, and exclusive output writes. Root reran these and23 core tests; separate static review found no important issue.
- [x] Exact approved Neel input compatibility passed with artificial vectors in memory:14 bundles,18 inputs,1536 dimensions; no live receipt or synthetic scientific result published.
- [x] Repository suite ran686 tests, with2 skipped (684 passed). Live bundle construction remains pending actual completed producer receipts.
