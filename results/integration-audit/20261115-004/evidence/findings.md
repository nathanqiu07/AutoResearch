# Baseline committed-evidence provenance

Source commit: `40f7db0d88e020aeea5dfeff591b71b8812ba0ad`. Artifact path: `results/gio-baseline-review-01`.
All 22 artifact files were read from this commit's git
objects. Working-tree contents and local raw records were not inspected.

- `artifact_checksums.json`: 21/21 hashes match.
- `runner_checksums.json`: 6/6 hashes match.
- `packet/checksums.json`: 6/6 hashes match.
- Files outside the artifact manifest, excluding the manifest itself: [].
- Execution version agrees with settings: True (`de5c0c25ec5da4941f91727450ee006bbbe2e421`).
- Copied preparation version agrees with `prepared_packet_code_version`: True (`ec33e5bb93db6762d3a07541028c5215aadcdb41`).
- Preparation-to-execution differences: 9 top-level fields, all preserved in `report.json`.
- Fixed settings agree: models=True, routing=True, generation=True, seed_id=True.
- Summary equals the single score record: True.
- Runner snapshots present: 6; absent from execution commit: 6; matching published scripts: 6.
- Committed README documents deliberately local raw records: True.

The older copied preparation code version is intentional metadata when the
preparation-version check passes. Saved runner code applies the baseline-only
execution settings and retains that preparation version. The complete settings
differences and runner hashes are available for review; no scientific approval
is inferred from a passing integrity check.

The saved runner computes its repository root relative to its file. To reconstruct
the source layout, restore the archived runner files under `scripts/gio_petri/`,
alongside the recorded execution commit, instead of executing the archive in place.

Reconstruction limits:

- Runner snapshots supplement the execution commit; CODE_VERSION alone does not include them.
- Saved package versions do not attest the complete installed environment, Python version, or package source hashes.
- A vendored Petri source commit does not prove that exact source was installed for execution.
- These records do not attest all execution-time imported source bytes or an execution-time working-tree diff.
- Local raw records are outside this reproducer scope and are not inspected or verified.

`command.json` records this invocation and tool hash. `git-commands.json` records
every git read, exit, stderr, and stdout hash. `stdout.txt` and `stderr.txt` contain
the reproducer outcome. No network calls, inference, or project-module imports
were performed.
