# Runner follow-up: no blocker found in tested path

Release: `7bb1589127ba386d74dd00c029659f195ffe28b8`.
Implementation: `fd0c81f79a578ac65db945b23884dd5788cf0c05`.
All **162** pinned source hashes matched before and after execution.

All 13-era runner checks pass again on this snapshot. The five prior findings
remain fixed: mutable execution inputs, cache wall-time bypass, missing cost
mode, full document binding, and divergent actual extraction settings. Positive
concurrency, uncertainty/no-retry, timely cache/key attribution, matched
extraction, and included historical fixture integrity checks still pass.

The new preclaim settings validation also passes this bounded independent test:

| Input | Observation |
| --- | --- |
| Valid explicit temperature 0.25/max_tokens 64 | One synthetic call; complete profile; trace/profile settings agree; system text remains separately recorded. |
| Missing `extractor_settings` key | Typed `ValueError` before claim/output/call. |
| Null settings | Typed `ValueError` before claim/output/call. |
| Empty settings | Typed `ValueError` before claim/output/call. |
| Missing temperature | Typed `ValueError` before claim/output/call. |
| Unsupported extra `top_p` key | Typed `ValueError` before claim/output/call. |
| Boolean temperature | Typed `ValueError` before claim/output/call. |
| Boolean output limit | Typed `ValueError` before claim/output/call. |
| Zero output limit | Typed `ValueError` before claim/output/call. |

Each negative case supplied a correct config hash and full documents hash, the
same registered builder and source documents, and a valid lease. Its settings
validation error was therefore reached through valid surrounding setup. The
matched positive case actually dispatched and completed; blanket rejection is
not mistaken for correct enforcement.

**20 independent cases verified; 18 targeted owner runner tests passed.** No
regression or relevant runner-path blocker was found in this bounded retest.
This is not an assessment of live provider availability or all pilot gates.
API partial-usage/ledger behavior, retrieval binding, and evaluator confirmation
remain with their separate audit lanes.

Only invented source/choice text and recording backends were used. There were
no live calls, credentials, real records/labels, or owner-code edits. The 13
evidence package is unchanged; older 007/010 packages are also preserved.

## Artifacts and reproduction

- `evidence/report.json`: all cases and old/new source comparisons.
- `evidence/source-verification.json`: all pinned source checks and tool hash.
- `evidence/command.json`, `stdout.txt`, `stderr.txt`: exact invocation/status/output.
- `evidence/owner-tests-*`: targeted owner test command/status/output.
- Individual case JSON plus synthetic claims, traces, caches, profiles and results.
- `SHA256SUMS.json`: the reviewer's earlier staging manifest.
- `checksums.json`: every final package file except itself, including root
  confirmation, source archive and verification logs. Original `findings.md`
  remains unchanged from staging.

```sh
python3 -B reproduce.py --source-root /path/to/frozen-7bb1589-snapshot --out /path/to/new-evidence --contract /path/to/SHARED_CONTRACT.md
```

The output directory must be fresh. `--contract` is optional and only pins its
content hash. The reproducer checks source hashes before and after and writes
all new evidence beneath the requested output directory.

Root independently reran all 20 cases and the 18 owner tests on the same snapshot; `root-confirmation/` preserves that second execution. Extract `source/source.tar.gz` and copy `source/AUDIT_SOURCE.json` to the extracted root to rerun. `verification/audit-repo-full.log` records the separate audit repository suite: 677 total, 675 passed, two skipped.
