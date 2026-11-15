# Empirical semantic handoff audit 021

Independent reviewer role: `/root/parallel_gap_audit`, 2026-11-15. Read-only producer/artifact audit; no model calls, project-code imports, environment/credential access, private evaluator labels, or owner-code edits.

**226 checks verified, zero failed, exit 0.** No handoff blocker was observed for using these 28 bundles with their exact bound source, decision, order, model, dimensions and retrieval implementation. This is not a semantic prediction-quality result or live-job authorization.

The immutable role05 release is `adad3ca120aabe80ca20351029c3f816b3a5fe35`; its safe index matches SHA256 `42aa4fe2ebe522b8bd38137e91e04c7cd3a20ca9480aadf0a4282d888a10ef91`. The assembler file matches its recorded hash and is byte-identical at release, assembler revision `cd3de73`, and the index's recorded code revision `4394aa10597c672d265144dc385a88c0384ce37e`. Those different commit labels do not introduce an assembler-byte mismatch. The retrieval helper matches frozen runtime `0dcd4b43b82a5a271d195e0bcc6b67695281f37c` byte for byte.

| Producer batch | Raw indexed vectors | Query vectors | Source chunk vectors | Dimensions | Reported input tokens | Estimated producer USD |
|---|---:|---:|---:|---:|---:|---:|
| neel_nanda | 18 | 14 | 4 | 1,536 | 1,646 | 0.00003292 |
| chris_olah | 22 | 14 | 8 | 1,536 | 2,278 | 0.00004556 |
| Total | 40 | 28 | 12 | 1,536 | 3,924 | 0.00007848 |

The reader checks all five external assembly inputs against their pinned byte hashes: proposal, released development bundle, staged request, completed receipt and raw response. It checks the dispatch/summary binding, exact settings, request input deduplication/order, input byte counts, receipt/request/response identity, finite nonzero vector dimensions and indexed vector equality, response usage and configured-rate cost arithmetic.

For every decision it independently reconstructs the canonical query followed by the exact ordered source chunks. The request's response-index mapping selects those precise strings. Each entire released bundle equals a reconstruction from that raw response slice, including source/query/chunk/input hashes, model, dimensions, vectors, usage fields and bundle hash. All input roles and all 28 decision/order entries are covered exactly. No raw vector or text is included in this package.

The reader also independently reproduces cosine ranking and exact-prefix packing with the pinned algorithm. All 28 construction-check content hashes, passage counts and rendered-byte counts match, within the 2,048-byte cap. This checks the recorded construction claim without executing the owner builder or a consumer. It does not establish downstream prediction settings or quality. The nine owner assembler tests were not rerun; this audit checks the actual released artifacts with an independent reader.

Accounting is deliberately scoped. The 28 bundles reference exactly two distinct producer receipts/usage hashes, 14 bundles per receipt, without copying a new per-bundle charge. Summing each producer once gives $0.00007848, matching the pinned producer summary and index. The producer summary records 36 cumulative campaign attempts, $0.00834268 spent, zero reserved dollars and no uncertainty at that snapshot. **Exact live-ledger debit uniqueness remains unverified:** the active SQLite database was not opened or locked. Receipt/reference consistency is verified; actual ledger posting and provider billing are not independently authenticated. The configured rate was used only to check recorded arithmetic, not verified as a current price.

Source-span permission semantics remain separately covered by audits 017/019 and the newer method-level retest 023; this audit establishes exact binding to released source bytes and the pinned chunking implementation. The records provide evidence of an embedding handoff and profile construction, not 28 successful predictions, researcher fidelity or retrieval usefulness.

Evidence:

- `read_handoff.py`: standard-library independent reader. It reads immutable Git blobs and pinned external JSON, never imports project code or constructs a backend.
- `run-01/report.json`: 226 checks, sanitized batch/bundle metadata, hash inventories, source/runtime pins and limits.
- `run-01/reader-used.py`, `invocation.json`, `stdout.txt`, `stderr.txt`: exact script, command, explicit subprocess environment, exit status and output.
- `input-inventory.json`: only Git object and approved external-file hash/size references, for a separately authorized private archive if needed. Do not recursively copy producer artifacts into public results.

Reproduce from a fresh extraction of the private retained archive:

```sh
python3 -I read_handoff.py \
  --coordinator-root /recorded/coordinator/root \
  --archive-root /path/to/extracted-private-copy \
  --preservation private-preservation.json \
  --out /path/to/new-output
```

Use the recorded coordinator root in the saved invocation; it identifies recorded paths and need not exist on the replay host. Original-input mode instead takes `--repo` and `--coordinator-root`. The original run01 reader and invocation remain unchanged, as do the first relocated run02 and its exact script. Current code requires explicit input locations.

The root reviewer privately retained all 50 exact inputs (40 Git objects and 10 external files), verified every archive member against its recorded hash and size, and reproduced all 226 checks after relocation. All eight decisive evidence sections exactly match run01. The archive remains Git-ignored with restrictive permissions; the public receipt gives its hash and member inventory. Retain that private archive when moving or removing this worktree.

Independent code review found that the first relocation implementation still resolved recorded paths against the original host filesystem. A symlink-loop test demonstrated the dependency. Current replay uses lexical identities and two explicit aliases captured from the pinned producer dispatch; it resolves only actual archive members for containment. It also rechecks all 50 accessed members at finish. Twelve synthetic boundary tests pass, including missing/duplicate pins, hash tampering, parent/absolute/symlink escape, nonexistent original paths, explicit aliases and mutation after initial Git-member reads. The three newly failing tests and exact pre-fix reader are preserved under `boundary-before-lexical-fix/`; final tests and replay are in `boundary-after-lexical-fix/` and `run-03-portable/`.

This replay authenticates consistency with retained records, not independent provider origin, billing, experimental validity or semantic prediction performance. Public artifacts contain metadata and synthetic test inputs only; actual source text, vectors, responses and profiles remain in the private copy.
