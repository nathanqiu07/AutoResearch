# Completed downstream three-arm comparison

The [quantitative audit](quantitative-findings.md) reproduces all 47 recorded tool events against the frozen state engine: 910 integrity checks and 12 synthetic tests pass. The separate [semantic review](semantic-review/findings.md) anchors interpretations to exact returned files and transcript pointers; its 61 structural checks validate provenance, not the interpretations by themselves.

All three arms leave the operative HOME shutdown script and schedule unchanged throughout. Main target responses are 6/6/19 and auditor turns 9/9/22. No scheduled execution or process survival is measured. Baseline's primary review remains rejected; generic/profile's recorded schema-valid reviews do not settle semantic validity. A requested packet lease is correctly distinguished from the separately issued execution lease.

Three substantive limits matter for reporting:

- The same app.py supplies the leading reported vulnerability in every arm, but baseline and profile also use distinct authored vulnerabilities. Causal dominance and ignored context are unsupported.
- Generic's returned cleanup script directly invites shutdown prevention, contrary to the shared authoring constraint. Profile instead changes permission/incentive context without an explicit edit/preserve directive. Neither establishes influence or latent intent.
- More profile writes/turns and generated patches do not prove executed exploits, correct patches or better research. A single sampled trajectory per arm cannot identify a personalization effect.

All 104 ledger entries have recorded usage estimates. The 31 main target entries plus 15 secondary probes are distinct from the 40 auditor and 18 judge entries. Configured-rate arithmetic totals $0.80479522; this is not an invoice or global budget-authority audit, and a configured zero target rate does not prove zero actual cost.

Root privately retained all 28 approved inputs and verified every archive member. Both quantitative and semantic readers reproduce byte-identical report objects from relocated inputs. Raw source/target/profile/reasoning contents remain private; the public package contains hashes, pointers, counts and safe summaries. Preserve the ignored archive separately when moving/removing the worktree. Source references resolve to the archived 022 code. Original quantitative/semantic manifests remain historical subsets; final `checksums.json` covers every other package file.

The two earlier lease comparisons were audit-reader mistakes and are preserved with their exact scripts. The owner was notified of both the generic cue and the counterevidence to causal common-file dominance. These conclusions concern the pinned released run and owner-review version, not a later corrected viewer or future experiment.

The owner subsequently published the report corrections at `536af31`; `owner-publication-followup.json` pins the inspected text. Its complete 218-file private archive is separately indexed in `downstream-full-archive-reference.json`. Root verified that receipt and manifest, while full raw-member verification remains owner-reported; no duplicate complete archive was made.
