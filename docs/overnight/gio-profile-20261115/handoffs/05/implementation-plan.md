# Baseline and retrieval implementation plan

Goal: deliver comparable controls through the neutral profile contract, using only evaluator-approved inputs. Owner: gio-overnight-05. Base: d66051c6b792e2a9062f334535cf61ff9f51a15a.

Architecture: additive builders in baselines.py, pure in-memory retrieval and packing in retrieval.py, existing build_profile/consumer unchanged. No calls during fixture development. Python 3.9+ / standard library. Specification: role05 and SHARED_CONTRACT in the overnight dispatch packet.

- [x] Implement deterministic source-validated chunking, lexical BM25 ranking, exact-byte JSON packing and semantic-unavailable status. Tests first: unknown/modified sources rejected; ranking relevant source first; ties/order deterministic; unicode fits cap; source spans reproduce; cache identity changes with options, model, source and parameters.
- [x] Implement no_profile, name_only, raw_evidence, lexical_retrieval and semantic_retrieval builder registration. Test actual consumer payloads, no accidental author/source metadata, explicit unavailable/empty output and no extraction calls.
- [x] Reuse a supplied frozen P1 summary unchanged for memory_summary; compose frozen profile plus retrieved excerpts under a registered profile/passage byte allocation. Test source/researcher/hash compatibility, profile preservation, combined cap and zero silent fallbacks.
- [ ] Run targeted and repository tests, independent review, synthetic fixture generation; push own branch and send exact hashes to coordinator/audit. Live development jobs only from coordinator after DATA_READY.

Decisions: UTF-8 bytes follow shared conservative cap, not tokenizer counts. Chunking uses fixed nonoverlapping character windows with exact source offsets; retrieval scores are BM25, stable ties use document ID/start. Query consists only of context and options, preserving option order in identity. Exact duplicate excerpt text is indexed once. No semantic substitution without an authorized embedding backend. Summary/profile controls require a compatible immutable ProfileArtifact and preserve its content; cap mismatch is unavailable, not silent truncation.

Review focus: hidden fields entering prompts; labels in decision objects; unapproved source sets; stale/foreign profile reuse; query-specific retrieval accidentally reused for a different item; JSON overhead making caps incomparable; retrieval helper changes omitted from registration identity.

Progress: clean original-base suite passed 656 tests, two skipped. Contract-ready base is now checked out; next check includes its additive tests.

Independent review: one important defect (malformed frozen artifacts raised AttributeError) reproduced in eight subcases and fixed via structural checks; all 18 targeted tests pass.
Ruling: cross-consumer reuse is supported by the neutral contract, so consumer identity is recorded in retrieval cache identity but is not an inference prohibition.
Ruling: the shared runner must enforce retrieval decision binding; helper/prompt compatibility and final-data custody remain infrastructure/evaluator responsibilities, with exact integration requirements sent to the coordinator. No claim of live quality or semantic coverage.

Verification: final implementation passed 681 repository tests (two skipped), and all 18 targeted tests. Synthetic fixture showed six complete controls and semantic unavailable; no live calls.
