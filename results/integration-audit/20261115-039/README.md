Audit 039 checks the original downstream05 terminal evidence at publication
`c80937c7f92dd6ad05eee319e64f16799f0a193e`, executed source
`e9672aa48ba442dfc5bd2cd84b8f0c76e2bfb7e4`. It excludes later judging repair.

The independent reader passes 1,316 checks over 337 immutable Git objects:
212 artifact members, nine owner-review members, their two manifests, and 114
executed source files. Owner-review members are hash-verified only; their checker
and conclusions are not used to derive the findings. Six synthetic boundary
controls pass. No owner/runtime imports, model calls, native `.eval` execution,
active ledger, environment/key reads or private preference scoring occur.

Run with Python 3.9+ and Git, using a repository that already contains both exact
commits and a new metadata-only output directory:

```sh
PACKAGE=/path/to/audit039
REPO=/path/to/AutoResearch-with-pinned-objects
python3 -I -B "$PACKAGE/reproduce.py" --repo "$REPO" --out /fresh/audit039-replay
python3 -I -B "$PACKAGE/test_reader.py"
```

The reader uses only explicit Git objects in the three released prefixes and
executed-source paths named by `runtime-source-checksums.json`. It performs no
network fetch or directory discovery. Raw Git data stays in memory. Git's
read-only subprocess receives only fixed PATH/TMPDIR values. Replays should
produce the same report after removing `argv`, and a byte-identical inventory.

`run-03/report.json` and `run-03/input-inventory.json` are the final evidence.
`accounting-boundary.json` is a compact extract with the seven paid cached-token
rows and exact source/field references. `FINDINGS.md` states the interpretation
limits. `root-independent-cost/` contains root's separate supplied saved-rate
calculation, copied byte-for-byte after hashing; it does not join individual
ledger rows or identify third-party normalizer code.

`run-01` preserves the reader's failed raw-input-equals-ledger assumption. The
observed cached-token normalization led to the accounting finding, not an owner
data change. `run-02` is the first passing reconstruction. `run-03` adds direct
native normalized-usage bindings and checks for recorded billing/cache charges.
Exact scripts, commands and outputs remain saved. Earlier exploratory assumptions
are described in `SETUP_HISTORY.json`.

`publication-check.json` is root's earlier preliminary manifest check; it is not
a standalone executed-reader proof. Its bytes are unchanged. The already indexed
owner archive is not duplicated here. This checker requires the pinned Git
objects; it does not claim to replay from unindexed private siblings.

Publish only the explicit `SAFE_PACKAGE_MANIFEST.json` allowlist and that manifest
itself. Exclude `private-source/` and any raw input/archive/extracted replay tree.
The public evidence contains only independent code, synthetic tests, metadata,
hashes, counts and statuses. It does not include raw profile, persona, example,
prompt, response, source-file content, or judge quotations.
