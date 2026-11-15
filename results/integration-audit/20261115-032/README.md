# Terminal evidence retention

The verified private archive union preserves all 132 indexed phase1 jobs and all 84 original admissions in the stopped phase2 batch `df4cbde…`. It includes the original 78 dispatched results and their trace pairs, plus six original non-dispatch receipts. Later continuation results for those six job IDs are excluded from the stopped-batch records.

All 2,252 required record references can be recovered from three existing private archives and two new archives. The missing-dependency list is empty. Phase1 retains 130 complete and two invalid outcomes. The stopped batch retains 36 complete, 38 invalid, two empty, two unavailable and six not-dispatched admissions. The two uncertain outcomes and their retained reservations remain intact; the stopped ledger is not described as closed or reset.

This package verifies retention and byte recovery. It does not review model outputs, rescore predictions, establish provider invoice costs, or authorize further execution. No model/API calls, credential reads, active SQLite reads or copies, private evaluator label reads, raw corpus-tree traversal, or active continuation output reads were performed.

## Evidence and verification

The original 25-file `manifest.json` and the 18-file additive `portability-manifest.json` are preserved with all indexed bytes unchanged. Both manifests exclude themselves. Final `checksums.json` covers every other file in this published package. Historical scripts and invocations retain their original recorded paths; use the portable verifier below for current recovery checks.

The final preservation receipt is `private-preservation.json`, SHA256 `6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8`. It maps each record to its exact archive member and hash. It also includes a per-job coverage matrix, source inventories, terminal counts and the empty missing-dependency list. Exact source snapshots retain 91 files for runtime `0dcd4b43b82a5a271d195e0bcc6b67695281f37c` and 92 files for `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`.

The original agent verification, independent root repeat, portable verifier repeat and fresh verification from this published layout agree. The published command and result are recorded in `published-verification.invocation.json` and `published-archive-union-verification-04.json`. Archive-only verification does not open original temporary data paths.

The new portable preserver requires an explicit coordinator root. It received syntax, CLI and three synthetic path checks only; it was not used for another real-input preservation run. No archive or original receipt was rewritten during the portability follow-up. See `portability.md` for exact old and new script hashes and semantics.

## Private dependencies and recovery

Raw released inputs and outputs are intentionally absent from this public package. Recovery requires these five private archives:

- Audit 024: `control-20261115-v2.tar.gz`, with 695 verified members.
- Audit 021: `semantic-20261115-v1.tar.gz`, with 50 verified members.
- Audit 019: `pilot-20261115-v1.tar.gz`, with 252 verified members, also covering audit 018 inputs.
- New phase1 retention: `terminal-phase1-semantic-20261115-v1.tar.gz`, with 631 verified members.
- New stopped-batch retention: `terminal-phase2-stopped-df4cbde-20261115-v1.tar.gz`, with 728 verified members.

The receipt pins all archive and dependency-receipt hashes. The private archives remain in the Git-ignored `runs/user-model-integration-audit/private/` directory with mode 0600 and directory mode 0700. The unchanged receipt and exact executed verifier also have durable mode 0600 copies there as `terminal-preservation-32-receipt-v1.json` and `terminal-preservation-32-verifier-executed-v1.py`.

Run this command from the repository root, choosing a fresh output path:

```sh
python3 -I -B results/integration-audit/20261115-032/verify_union_portable.py \
  --receipt results/integration-audit/20261115-032/private-preservation.json \
  --receipt-sha256 6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8 \
  --audit-root . \
  --archive-root runs/user-model-integration-audit/private \
  --out /path/to/fresh-verification.json
```

After relocation, point `--archive-root` to the directory holding the five private archives and `--audit-root` to the repository holding the public 024, 021 and 019 receipts. No raw extraction or provider access is needed for verification.

The terminal/index states and before/after hash checks support the retention boundary. Mutable coordination snapshots provide pointer provenance, not frozen experiment source or proof that a continuation ended. Source and configuration evidence is recoverable; future provider availability, installed dependency state and identical stochastic outputs are not guaranteed. Recorded usage and accounting statuses remain observations, not independent provider verification.
