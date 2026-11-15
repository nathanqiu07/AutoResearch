This package audits the provenance and accounting of the released 96-cell broad extraction grid. It reconstructs 48 complete, 39 invalid, 7 empty, and 2 unavailable outcomes while separating the original 78 dispatches from six continued jobs and 12 P7 builds. Read FINDINGS.md for the evidence and limits.

The current reader is audit_coverage.py. Its final metadata report, exact input inventory, and source reference are in final/. final-invocation.json records the executed command. Tests and failed setup attempts are retained; they are audit-reader setup history, not owner failures. setup-history.json explains each attempt.

Reproduce after restoring the exact private inputs listed in final/input-inventory.json. A relocated inventory may change each row's read_path; keep path, sha256, entry_points, and input_set_sha256 fixed. The reader rejects missing, changed, undeclared, or unused inputs. The old registry snapshot is recoverable from audit 032's phase1-semantic private archive member coordination/JOB_REGISTRY.snapshot.json. Source code is in the separate source-f6cd4fb5.tar; it contains 92 pinned files and no released raw inputs.

From the package directory, with a fresh empty source directory and the restored private inventory:

```sh
mkdir replay-source
tar -xf source-f6cd4fb5.tar -C replay-source
python3 -I -B audit_coverage.py --inputs /path/to/restored-input-inventory.json --source-root replay-source --out replay-result
python3 -I -B test_audit_coverage.py
```

Do not publish restored inputs or private replay directories. safe-manifest.json lists the public files by exact hash; the manifest itself is the only implicit additional file. The extracted source tree and private-inputs/ are excluded. Original attempt files and manifests are not overwritten.

This is a saved-record audit. It does not read an active SQLite ledger, make model calls, assess source/profile quality, read labels, rescore predictions, verify provider invoices, or prove the absence of unreleased requests. The two unknown outcomes retain unknown usage and their holds. Neutral-probe and uncertain-build canonical provider-request joins remain unverified where the released evidence lacks a scoped request trace. No further input is needed for the bounded aggregate conclusions.
