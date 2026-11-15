# Build notes — Nicholas Carlini rich profiles

- Authored five distinct method-shaped prose artifacts: P2 process reconstruction; P5 conditional rules; P8 competing interpretations; SynthesizeMe-inspired persona; ICAI-inspired constitution.
- This is a fresh, purposive synthesis of existing evidence, not execution or recovery of the earlier extraction pipeline and not an identical reproduction of the Hubinger build. No external model calls, preference fitting, live experiments, or runtime changes were performed.
- Read repository AGENTS guidance. Parent owns coordination, locking, verification integration, and git operations.
- Reviewed P2 lane extraction previews to discover concrete methodological choices and counterevidence. Inspected selected primary corpus text directly (full short essays/erratum/talk; relevant introductions and threat-model/definition sections for long papers). Did not claim comprehensive reading of the whole corpus or every earlier extraction item.
- Selected direct methodological testimony plus coauthored technical cases. Deliberately included positive formal defense evidence, stateful operational defense, the attacker's own correction, semantic-proxy failure, personal benchmark utility, and controlled canaries to challenge an attack-only caricature.
- Earlier lane extraction inventories are recorded in EVIDENCE_SELECTION.json. Counts are provenance context only; they are not a measure of source quality, coverage sufficiency, or validated preference prediction.
- SOURCES.json maps every cited document identifier to the owning repository's relative corpus path, primary URL, and SHA-256 of the exact bytes read from the shared main checkout. The corpus need not be materialized in this worktree for those paths to identify the owning source. No corpus files were copied or modified.
- Coauthored findings are distinguished from individual taste; proposed awareness applications and illustrative scenarios are explicitly marked as new inference. Historic evaluation advice is marked superseded rather than presented as current parameter guidance.
- Word counts use Python whitespace splitting; citation-excluded counts remove bracketed source identifiers first. No bibliography padding is included in profile files.

| Profile | Words | Words excluding citations |
|---|---:|---:|
| P2 | 3276 | 3246 |
| P5 | 3445 | 3430 |
| P8 | 3303 | 3274 |
| SynthesizeMe | 3322 | 3286 |
| ICAI | 3362 | 3339 |

Validation: all five profiles exceed 3,200 words excluding citation tokens; every citation resolves to SOURCES.json; all 15 source hashes were computed from existing primary corpus bytes. No preference-prediction accuracy or downstream effectiveness claim is made.
