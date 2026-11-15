# Compact sourced principles

Lane04 implements a simple competing profile for the complete source-to-Petri path.
It makes zero model calls. It packs reviewed claims, or claims copied from an existing
source-grounded extraction, and never invents a personal preference from a scenario.

The existing neutral ProfileArtifact, exact source quote resolver and renderer are
reused. The model-facing JSON contains short complete principles with their type,
evidence status and conflict links. Full source quotations, Unicode offsets,
selection provenance and all omitted claims remain outside that content budget,
bound by the profile hash. This separates evidence storage from prompt space.

## Input contract

`build_compact_profile(source_bundle, claims, researcher_id=..., code_sha=...,
cap_bytes=2048, claim_origin=...)` returns `profile` and `provenance` JSON objects.
The source bundle is an existing approved source bundle (`documents`, optional
`source_manifest`) or an existing release with `sources.documents`. Every selected
document requires exact content hashes and explicit nonempty permitted spans.
Only the requested researcher's documents enter extraction; the full input bundle
digest remains recorded. Evaluation items, if present in a release wrapper, are
not inspected or used to select claims.

Each claim has exactly these fields:

```json
{"id":"p1","kind":"preference","text":"A complete qualified claim.",
 "evidence_status":"explicit","sources":[{"document_id":"id","quote":"Exact source text"}],
 "conflicts_with":[]}
```

Kinds are `preference`, `belief`, and `source_report`. A source report is an attributed
statement, not an independently verified fact. Inferences must be marked `inferred`.
All relevant conditions and exceptions belong in the complete claim text. Semantic
support and classification remain input-author judgments; exact matching does not
prove them. Conflict-connected claims are packed together or omitted together.
The declared input order determines packing; this is not optimized on test scores.

## Output contract

`export_handoff(result)` validates the neutral profile and evidence sidecar, then
returns method/researcher/source IDs, `model_facing_text`, `neutral_profile`,
`provenance`, settings, implementation commit, known limits and zero-call usage.
`model_facing_text` equals the exact existing neutral consumer rendering.
`auditor_context` adds a fixed auditor-only preface; `auditor_suffix_template`
escapes literal braces for Petri's formatting. Its `.format()` equals the full
context exactly. This export is a concrete input, not a claim of live Petri execution.

The old saved-P8 adapter rejects this method, correctly. Lane01 must explicitly
accept the new handoff/suffix in its successor preparer. Do not spoof method_id=P8,
remove the old adapter's checks or put the profile into direct target/judge inputs.

CLI (all file inputs pinned; output directory must be new):

```sh
python3 scripts/gio_recovery/compact_profile.py \
  --sources SOURCE.json --sources-sha256 FILE_SHA256 \
  --claims CLAIMS.json --claims-sha256 FILE_SHA256 \
  --researcher neel_nanda --code-sha IMPLEMENTATION_COMMIT \
  --cap-bytes 2048 --claim-origin REVIEWED_OR_EXTRACTION_LINEAGE \
  --out-dir NEW_OUTPUT_DIRECTORY
```

The output includes profile/provenance/handoff JSON, compact profile text, full
auditor context and escaped template suffix. Empty profiles retain explicit
failure status and produce no runnable handoff. No old files are overwritten.

## Evidence and rulings

- Ruling: deterministic packing provides a zero-cost competing profile while the
  coordinator allocates live work. Input authorship is explicit; this is not
  advertised as a learned extractor or an independent new model experiment.
- Ruling: only content consumes the byte cap. Evidence remains complete and
  hash-bound outside the consumer content, addressing overnight citation overhead.
- Ruling: the first artifacts may use saved P8 statements on the original approved
  fit text. The matched sprint comparison must wait for the lane02 common bundle;
  initial and common-bundle artifacts must have distinct source digests.
- Tests catch missing consumer conditioning, partial conflict packing, truncation,
  forged/ambiguous/forbidden quotations, source tampering, sidecar tampering,
  unsupported facts, missing permissions and template-brace corruption.
- No final labels or final-test users are read by this module.

Lane01 contract integration: the CLI also emits `context.json` with schema
`gio-auditor-context-v1` and a unique condition ID. Its source_bundle_digest is
SHA256 of the exact source FILE bytes, as required by lane01. The canonical JSON
digest stays separately named source_bundle_semantic_digest. Model-facing text is
the fixed auditor-only preface plus the complete compact JSON; the preparer must
escape this once. The already escaped suffix file is a convenience for direct
template use, not the text to escape again. `context.json` pins both source file
and neutral structured artifact paths/checksums for copying into the frozen packet.
