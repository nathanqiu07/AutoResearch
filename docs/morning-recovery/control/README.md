# Morning execution control

This is lane09 of the new November 15 morning sprint. The old overnight goal remains paused. The goal is a real source data → profile → Petri auditor → environment → target → evaluation chain, with matched controls and every failed run retained.

[BUDGET.json](BUDGET.json) allocates a shared $200 per provider within the existing $500 project caps. All old issued reservations and uncertain holds remain, plus extra padding for unresolved historical overlap. These are conservative spending bounds, not invoices or verified account balances. New paid calls stop at 11:45 a.m. Pacific; the demo package is due at noon.

[CONTRACT.md](CONTRACT.md) binds producer contexts to native Petri packets and maps receipts to the viewer. [PARTITIONS.json](PARTITIONS.json) lets independent producers run while keeping at most nine provider calls in flight. After the smoke, up to four Petri jobs can overlap the other producers. Up to six can run when either the profile or diagnostic producer is finished, provided each Petri job enforces one call in flight. This is our limit, not a claim about provider quotas.

[MATRIX_V2.json](MATRIX_V2.json) declares the source version, common settings, all planned conditions, admission order and missing-result policy before seeing Petri outcomes. Every matched arm uses the same source bundle. A model or authoring change creates a new fixed protocol applied to every compared arm. The smoke tests integration; it is not pooled with a stronger-auditor comparison. No result-based retries or final-test users are authorized.

Each native run gets a finite lease tied to its exact packet before execution. The diagnostic has its own single-use claim and dollar ledger within its allocation. Private issued leases, raw inputs and detailed runtime status stay local. Public summaries omit their file locations. An allocation or proposed lease is not proof that a run happened.

The shared dispatch helper provides atomic allocation, lease and call admission, plus a result index. Native callers must install its before/after-call hooks before claiming shared call enforcement. Separate producer limits can enforce the global ceiling before those hooks are installed.

Canonical ownership records live on main. Code stays on isolated codex branches; no main code merge is part of this sprint. The other lanes keep ownership of their interfaces, code and tests.
