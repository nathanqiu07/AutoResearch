# Integrated quote and cap mechanics

The frozen f6cd4fb5 route from driver registration through actual runner/build, resolver, strict family validators, final cap and consumer preparation passes all 167 synthetic cases across P1–P8. There are 47 complete controls, 116 expected invalid outcomes and four expected unavailable outcomes. All 2,770 assertions pass, including root's repeat with an identical report. The 161 extraction calls go to a local recording backend; no live calls occur.

The matrix covers exact Unicode quotes, ambiguity, allowed occurrences, source attribution, disjoint ranges, whitespace/normalization differences, prohibited model-supplied offsets, inference policy, and post-resolution byte caps. Matched positive controls remain available, including eight exact-cap profiles. Expected rejection is not an assertion failure. Generic extensions and caller-specific missing-span conventions are documented rather than labeled defects.

This closes the bounded integrated-mechanics gap left in 023. It does not exercise packet preparation/release eligibility, real source permission, entailment, extraction quality, evaluation or provider execution. Source and selected handoff identities are pinned; no source versions are mixed.

The initial network-denial wrapper import failure is retained as an audit-tooling error. Exact synthetic case inputs/profiles/traces from runs 02/03 are archived with member verification, and 160 frozen source files are preserved. Root's duplicate extracted cases are excluded. `SAFE_PACKAGE_MANIFEST.json` is the original safe subset; final `checksums.json` covers every other final file.
