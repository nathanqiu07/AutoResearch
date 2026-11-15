# Runner to API unknown-outcome audit

Independent reviewer role: `/root/parallel_gap_audit` (automated synthetic audit).
Recorded 2026-11-15. No production source edits, real credentials, user data, network, or live model calls.

Current release `7bb1589127ba386d74dd00c029659f195ffe28b8`, implementation `fd0c81f79a578ac65db945b23884dd5788cf0c05`: **54 checks verified, zero failed; exit 0.** No execution-path blocker or remaining partial-usage reporting failure was observed in these cases. This is bounded plumbing evidence, not live-provider readiness or permission to spend.

The same probe against older `2b965eeaeafad029faa1b2055a45c1b29caf2463`, implementation `9d4f4e5c36bafeef25784582b1a3416520d79f8c`, verified 43 checks and failed 11 reporting assertions (exit 1), with **zero execution-boundary failures**. These are assertions about the old reporting behavior, not 11 separate defects. They reproduce the prior lost-partial-usage issue and absence of explicit unknown-component fields. All pass on the current release.

## Executed boundary

The probe calls actual `runner.run_job`, stage `dev`, mode `priced_api`, with a real `OpenAIResponsesBackend` and SQLite `DollarLedger`. Only the environment/key and HTTP transport are synthetic. It uses the released test fixture's invented profile, two invented decisions, explicit gpt-6-sol/medium identity, and a synthetic allocation. Each case has its own ledger and durable runner outputs.

| Case | Current runner token totals (input/output) | Known estimated USD | Held USD | Physical synthetic transport calls |
|---|---:|---:|---:|---:|
| Completed control, two decisions | 200 / 40 | 0.0008 | 0 | 2 |
| Missing usage | null / null | 0 | 0.005016 | 1 |
| Input usage only | 100 / null | 0.0002 | 0.005016 | 1 |
| Output usage only | null / 20 | 0.0002 | 0.005016 | 1 |
| Valid input; boolean output count | 100 / null | 0.0002 | 0.005016 | 1 |
| Incomplete response with full usage | 100 / 20 | 0.0004 | 0.005016 | 1 |
| Transport exception | null / null | 0 | 0.005016 | 1 |

Values use the checked-in price table solely as an accounting fixture; they are not a price verification or invoice. For each row, the saved ledger's spent total matches reported known usage. Missing usage's zero known spend is not treated as zero total cost: the full reservation and explicit unknown flags remain.

For all six unknown cases, the reservation already exists at transport entry. The first result is `partial`, both decision rows are `unavailable`, and the first row records `backend_failed_usage_uncertain`. The second row records `lane_held_after_uncertain_attempt`, with no additional transport invocation. A durable started trace and failed/uncertain trace are retained, with no completed trace or cache entry. Duplicate execution raises `FileExistsError` without a request. A fresh backend and fresh job using the same ledger cannot reserve or send a request. Ledger state remains uncertain, full hold retained, no in-flight slot, and one reserved attempt. Known input/output components are preserved individually.

Manifest identity, result identity and each prediction row's identity match the actual backend. Captured requests retain the declared model, reasoning, maximum output, store=false, and default service tier. Temperature and tools are not sent, consistent with the adapter's identity. The transport exception canary does not enter the result.

## Counts and limits

`counts.attempted=2` counts decision rows considered. The failed initial job has one runner invocation, one backend reservation, and one physical synthetic request. The fresh job rejected by the shared ledger has one runner invocation but **zero local backend reservations and zero physical requests**; its campaign ledger still has the original one attempt. The generic runner conservatively marks this preflight rejection uncertain too. Consumers must not interpret row counts or runner gate invocations as physical API calls. This is a reporting-semantics limitation, not an observed request or budget bypass.

No actual provider identity, model availability, tokenization bound, billing rate, invoice, HTTP library physical retries/redirects, full campaign, CLI lane, or confirmation access was tested. This audit assumes frozen imported code and one canonical coordinator ledger/lease path. It does not create a live allocation.

Old backend SHA256 `b3b163e07365937fee4d7f1bde76fe8cc84181cbe8c07462f2cb927295f319b7` exactly matches audit011, so its earlier standalone ledger/concurrency evidence applies to that old module. Current backend SHA256 is `991bfe9f0bae1b125abac384fef582ef32a10a5aaac8190c89e4cf78bdc2af54`; this report does not claim the earlier standalone concurrency tests were rerun on that changed module. Current fresh-backend/shared-ledger rejection was tested directly here.

All 161 old and 162 current files in the respective `AUDIT_SOURCE.json` manifests matched before and after execution. Reproducer SHA256: `11a16479edabe756c769dfb1436c02d4a08e1f7286d542dc1e2bd3efc07d7ae8`.

## Evidence and reproduction

- `reproduce.py`: portable probe; parent launches a child with an explicit synthetic environment, and socket access is blocked before source import. The backend module's environment reference is replaced with a synthetic dictionary before construction/calls. No actual environment is copied/read.
- `run-7bb1589-01/report.json`: current assertions, source manifest, hashes, scope and limits.
- `run-2b965ee-01/report.json`: preserved old reporting failures.
- Each run's `observations.json`: complete synthetic responses/requests, returned results, traces, ledger rows and summaries.
- Each run's `invocation.json`, `stdout.txt`, `stderr.txt`: exact child argv, explicit environment, cwd, exit code and output.
- Each run's `cases/`: original runner manifests/results/traces, leases and SQLite databases. These preserve both initial failed jobs and the separately blocked fresh jobs.

From any directory (choose unused output directories):

```sh
python3 /path/to/20261115-014/reproduce.py --source-root /path/to/extracted-2b965ee --out /path/to/new-old-release-evidence
python3 /path/to/20261115-014/reproduce.py --source-root /path/to/extracted-7bb1589 --out /path/to/new-current-release-evidence
```

Expected old exit: 1, reporting assertions fail. Expected current exit: 0, all 54 assertions verify. Substitute your extracted source and package paths above. Existing output directories are refused rather than overwritten. Original `FINDINGS.md` and recorded invocations retain staging paths as provenance.

Root independently reran the current release: all 54 checks passed again. `root-confirmation-7bb1589/` contains that repeat. Portable source archives and their complete manifests are preserved in sibling packages 013 (old2b965ee) and016 (current7bb1589). Extract the chosen source archive and copy its `AUDIT_SOURCE.json` into the extraction root, then pass that root to this package’s `reproduce.py`.
