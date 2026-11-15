# Frozen phase2 uncertainty guards

[Findings](FINDINGS.md) compare exact runtime f6cd4fb5 to the audit014 source. Core runner and reservation/settlement functions remain unchanged, but backend cache/pricing identity and related source hashes changed, so source identity alone was insufficient assurance.

Seven actual runner/API/SQLite scenarios were replayed with synthetic transport. All 61 checks pass, including root's independent repeat: unknown/partial/malformed/incomplete/transport outcomes retain full reservations, preserve known partial usage, stop later items, and block fresh-backend/shared-ledger and duplicate-claim attempts without additional HTTP requests. The emitted declared cache/pricing settings also match the frozen source.

The exact unmodified old probe is retained with four failed cost expectations and no execution-boundary failures; it assumed input rate 2 while the new fixture declares 2.5. The revised probe changes that one expected rate and adds seven settings checks. This is fixture arithmetic, not verification of current API pricing, cache acceptance, provider behavior or invoices. Per-run evidence includes timing differences; root repeats the same 61 check names/categories/statuses, without claiming byte-identical full reports.

All 148 current source files are archived; source/function/dependency comparisons are preserved. No live failure metadata or active ledger was read. Actual phase2 failure cause, held amounts, authorization and physical request counts remain a separate audit requiring released terminal records. No failed real call was retried. Final `checksums.json` covers the original safe manifest plus root repeat evidence; temporary SQLite/work directories are excluded.
