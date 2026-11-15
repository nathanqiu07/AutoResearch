# Build notes — Jacob Steinhardt rich profiles

## Scope and provenance

Five independently written prose artifacts apply the requested method structures to the existing public corpus. P2 reconstructs a research process; P5 induces conditional rules with exceptions; P8 compares interpretations and discriminators; SynthesizeMe constructs an adviser persona; ICAI constructs a revisable constitution. The last two are explicitly labeled corpus adaptations, without preference fitting, selected demonstrations, held-out validation, or claims of reproducing the original methods. No new runtime code, experiment, or external model/API call was used to create this package.

The evidence was read from the existing main checkout's `data/researchers/jacob_steinhardt/corpus/` files, not reconstructed from titles. `SOURCES.json` records the 20 cited document IDs, logical repository paths, exact SHA-256 hashes of the inspected source bytes, evidence scope, and existing lane evidence pointers. At authoring time those corpus paths were not present in this worktree; package integration must preserve a resolvable source location or include the matching source files. Source hashes identify the actual inputs regardless of checkout layout.

Existing lane artifacts were inspected in `runs/nine-profile-petri/lanes/jacob_steinhardt-{P2,P5,P8}/`. The initial `extraction/` directories in P2 and P5 each contain 62 failed records. Their recovered `extraction-v2/` records were used for cross-checking: P2 has 48 complete, 3 partial, and 11 failed chunks; P5 has 51 complete, 3 partial, and 8 failed chunks. P8's `extraction/` has 50 complete, 4 partial, and 8 failed chunks. These statuses describe existing inputs, not a pipeline completed by this build. A representative claim and attribution caveat for each available selected source was inspected across these recovered records. Primary source excerpts supplied the substantive verification; no failed record was treated as evidence.

The chosen 20 sources cover robust statistics, unfamiliar adversaries, natural difficult examples, qualitative model failures, jailbreak mechanisms, auditing interpretability, counterfactual explanations, feedback optimization, agent-log validity, scalable oversight, context sensitivity, forecasting, and group research practice. Selection favors concrete methodological decisions and first-person norms rather than exhaustive bibliography coverage. Nineteen selected sources have matching P8 evidence records; the safety-roadmap abstract is a direct-source addition. Matching extracted record totals are 426 for P2, 467 for P5, and 515 for P8; these include repeated chunk-level evidence and are not counts of independent claims or proof of comprehensive coverage.

## Evidence limits

Resilience, Unsolved Problems in ML Safety, and the Scalably Understanding AI with AI talk are limited to abstract/bibliographic evidence. The profiles explicitly avoid proof-level or delivered-talk claims from those records. Other sources were inspected as relevant excerpts or complete short posts; this is not a claim that every word of every paper was reviewed. Coauthored results remain collectively attributed. The jointly signed Transluce letter remains an institutional commitment despite solo-author corpus metadata. Foundation Models for Oversight remains a prospective program. Contemporary model findings remain tied to the source's tested snapshots and settings, without fresh claims about current product behavior.

Examples applying these principles to synthetic evaluation environments are labeled inferences or proposed applications. They are not attributed as experiments personally designed by Steinhardt. The profiles explicitly separate observed behavior, measured proxies, causal interpretation, and personal preference. Their coherence and length do not establish predictive validity.

## Verification

Counts below use whitespace splitting. The second count first removes bracketed document-ID citations, so citation identifiers do not inflate the minimum. Headings and ordinary prose labels remain included. All five exceed 3,200 citation-stripped words.

| Artifact | Words | Words without citation tokens |
|---|---:|---:|
| P2.md | 3,260 | 3,235 |
| P5.md | 3,344 | 3,323 |
| P8.md | 3,322 | 3,286 |
| SynthesizeMe.md | 3,302 | 3,273 |
| ICAI.md | 3,346 | 3,325 |

Each citation ID was checked against the catalog; each catalog hash was checked against the inspected source file. No numeric experiment results are newly asserted. No runtime tests were required for these prose-only artifacts; integration and repository test/push verification belong to the parent task.
