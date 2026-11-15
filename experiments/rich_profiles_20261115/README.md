# Full-corpus researcher profiles: Carlini and Steinhardt

Version 2 replaces the earlier selective-source drafts in this directory. The
new build freezes every available corpus file, reuses only checked successful
full-chunk extraction receipts, repairs missing chunks, and submits all retained
evidence through a source-by-source reduction before writing each profile.
The prior version remains in git history at `d420d1e6`.

| Method | Technical name | Representation |
|---|---|---|
| P2 | Research-Process Reconstruction | Research questions, methodological choices, concrete projects, and changes in the argument. |
| P5 | Conditional Decision-Rule Induction | Conditional rules, rationales, exceptions, and conflict resolution. |
| P8 | Contrastive Interpretive Modeling | Competing explanations, evidence on both sides, and discriminating future decisions. |
| SynthesizeMe-inspired | Persona Synthesis | An integrated adviser persona with sourced decision demonstrations and limitations. |
| ICAI-inspired | Constitutional Principle Induction | Conditional principles with priorities, conflicts, and amendment conditions. |

The last two remain adaptations to writings, without preference-data fitting or
claims to reproduce the original algorithms. All five are inferred models of
research judgment, not researcher endorsements or validated preference predictors.

## Profiles

| Researcher | P2 | P5 | P8 | SynthesizeMe-inspired | ICAI-inspired |
|---|---|---|---|---|---|
| Nicholas Carlini | [P2](nicholas_carlini/P2.md) | [P5](nicholas_carlini/P5.md) | [P8](nicholas_carlini/P8.md) | [Persona](nicholas_carlini/SynthesizeMe.md) | [Principles](nicholas_carlini/ICAI.md) |
| Jacob Steinhardt | [P2](jacob_steinhardt/P2.md) | [P5](jacob_steinhardt/P5.md) | [P8](jacob_steinhardt/P8.md) | [Persona](jacob_steinhardt/SynthesizeMe.md) | [Principles](jacob_steinhardt/ICAI.md) |

The earlier [Hubinger profiles](../hubinger_petri_20261115/) are a separate build.
This version uses the same five method definitions, not an identical generation
pipeline or a claim that profile quality is controlled across builds.

## What full coverage means here

The frozen inventory contains **167 Carlini files and 131 Steinhardt files**.
All 298 files are accounted for. The legacy extraction partition spans 162 and
128 substantive candidate records, respectively, totaling 2,862,584 source-body
words. The other eight records receive a separate full-text review: generated
biographies, an author index, and failed conversions. Attributable framing and
index excerpts remain available to synthesis; generated biographical claims do
not become facts about the researchers.

Every retained source segment is linked to successful full-input extraction
receipts and either exact-source evidence or an explicit no-evidence disposition.
Four previously unprocessed Carlini chunks were extracted in this build. No
missing segment is silently relabeled as covered. Every accepted extraction
record is assigned to exactly one reduction packet. Every source receives a
capsule, including records that contain no usable researcher evidence. Each of
the five final method prompts receives the complete capsule inventory for its
researcher, rather than a selected subset.

This is **input and processing coverage**, not a claim that a short profile
retains every fact, that every interpretation is correct, or that a source
snapshot contains the full publication. Some available records are abstracts or
truncated text; bibliographies, quoted third parties, and generated content are
not evidence of personal preferences. Repeated papers, posts, and extracted
paraphrases are not independent support.

## Audit files

Each researcher directory includes:

- `SOURCES.json`: all frozen sources, hashes, metadata, and pinned GitHub links.
- `full_corpus/coverage.json`: source and segment accounting, including dispositions.
- `full_corpus/extraction_receipts.json`: provenance of accepted extraction jobs.
- `full_corpus/evidence.jsonl`: exact-source-checked evidence and attribution limits.
- `full_corpus/capsules.json`: the complete source-by-source synthesis input.
- `full_corpus/reduction_coverage.json`: evidence-to-packet accounting.
- `full_corpus/input_inventory.json`: expected source, packet, and evidence IDs.
- `BUILD_NOTES.md`: build-specific details and limitations.

`profiles.json` records finished profile hashes and counts. Word counts exclude
bracketed citations when testing the 3,000-word floor. `validation.json` records
verification results. The `build/` utilities preserve the extraction, reduction,
and synthesis procedure; raw prompts and execution logs remain in local
`runs/full-corpus-profile-v2/` and are identified by hashes in the audit records.
No downstream Petri experiment or preference-prediction validation is included.
