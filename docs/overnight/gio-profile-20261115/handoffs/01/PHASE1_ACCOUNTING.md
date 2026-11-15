# Phase 1 accounting reconciliation

`phase1_accounting.py` is an offline, standard-library tool. It reads an existing
SQLite ledger with `mode=ro` and `query_only`, takes a transaction-consistent
logical snapshot, and never imports DollarLedger or changes its policy, balances,
reservations or runtime. It makes no network calls and needs no credentials.

The correction adds 25% of the old base input cost for all model input tokens.
Old input/output prices per million tokens are luna 0.10/0.50, sol 2/10 and
astra 10/50. Arithmetic uses integer nanodollars throughout. This is a conservative
30-minute cache-write bound, not a provider invoice. Cached-token detail fields
are already part of total input and are not added again. The correction is based
on the [verified prompt-caching pricing](https://developers.openai.com/api/docs/guides/prompt-caching).

Embedding calls remain at $0.02 per million input tokens with no uplift. Their
cost is already included in the shared ledger and is counted exactly once.

## Dispatch schema

The coordinator supplies and hashes this metadata-only JSON manifest:

```json
{
  "schema_version": "phase1-accounting-dispatch-v1",
  "ledger_path": "ABSOLUTE EXISTING PHASE1 SQLITE PATH",
  "indices": [
    {"path": "ABSOLUTE COMPLETION INDEX PATH", "sha256": "RAW FILE SHA256"}
  ],
  "embedding_summaries": [
    {"path": "ABSOLUTE EMBEDDING SUMMARY PATH", "sha256": "RAW FILE SHA256"}
  ],
  "profile_allocation_usd": "200",
  "prior_outside_ledger_usd": "0.017601625"
}
```

Each completion index uses existing `pilot-completion-index-v1` layout:
`batches[].jobs[]`, with job_id, manifest_sha256, usage and a result `{path,sha256}`.
Multiple nonoverlapping indexes are allowed. Repeated job IDs are rejected.
The combined coordinator index can retain this schema. The tool verifies each
result's file hash and matching job, manifest hash and usage. It reads only named
result files and their numbered started traces, whose hashes must be recorded in
the result. It does not scan directories or inspect target bundles.

Started traces supply the exact phase 1 request hash. Their prompt/system text is
used in memory only to reconstruct that hash; output never contains this text,
profile content, predictions, vectors or credentials. The model, reasoning and
request-hash multiset must equal the ledger's corresponding multiset. Repeated
identical requests count separately. Per-model aggregate token usage and attempt
counts must also reproduce the ledger's exact old-price cost. These records do
not provide per-call token usage, so no per-call token counts are invented.

Embedding summaries bind receipt file hashes. Receipt request IDs, input hashes,
packet hashes and usage must match their summary and ledger metadata. Unknown
models/reservations, missing calls, incomplete usage, money mismatches, duplicate
evidence or file-hash mismatches cannot yield a closed receipt.

## Provisional check

Run the pinned script from a clean, read-only location and choose a new output
path outside the runtime and existing evidence directories:

```sh
python3 path/to/phase1_accounting.py \
  --dispatch /absolute/path/to/accounting-dispatch.json \
  --expected-dispatch-sha256 EXACT_RAW_DISPATCH_FILE_SHA256 \
  --output /absolute/path/to/new-provisional-receipt.json
```

The receipt contains only metadata: evidence paths/hashes, ledger logical snapshot
and policy hashes, per-model token/cost totals, embedding totals, pending/uncertain
counts, retained reservations and unresolved codes. Dollar fields are exact
decimal strings with nine places. The logical snapshot includes policy and all
reservation rows; it remains meaningful when SQLite journal/WAL layout changes.

Status is `unresolved` when any coverage/usage/hold remains; both the conservative
phase 1 total and provisional phase 2 cap are then null. When everything matches,
status is `ready_for_coordinator_close` with a provisional cap. `phase2_cap_usd`
remains null in every provisional report, including reports with zero holds.
Exit 2 reports unresolved/preflight failure; exit 0 reports a successful complete
provisional check or final closure. Output files are exclusive and fsynced.

## Final closure is a separate coordinator action

No final receipt was produced during development. The coordinator first stops
assigning phase 1 jobs and verifies that all jobs are done. It then supplies a
fresh complete index and adds this object to a new hashed dispatch:

```json
{
  "closure": {
    "all_jobs_done": true,
    "authority": "EXACT COORDINATOR COMPLETION SIGNAL",
    "ledger_snapshot_sha256": "EXACT VERIFIED PROVISIONAL LOGICAL SNAPSHOT"
  }
}
```

Only `--final` requests closure. It requires that authority, the exact logical
snapshot, no pending/uncertain rows or retained holds, complete usage and full
identity/cost coverage. The tool rereads the ledger after evidence verification
and refuses a changed snapshot. It cannot prevent new jobs after returning:
coordinator quiescence is still required. This tool is not a ledger lock or an
authorization mechanism for new spending.

A closed receipt computes:

`phase2_cap = 200 - 0.017601625 - phase1_conservative_upper`

The coordinator preserves the old ledger/receipts, then separately creates the
new canonical phase ledger with that remaining allocation. This tool never
creates a ledger, migrates balances, releases reservations or resets a policy.

## Verification

```sh
python3 -m unittest discover \
  -s docs/overnight/gio-profile-20261115/handoffs/01 \
  -p 'test_phase1_accounting.py'
python3 -m unittest discover -s tests -t .
```

The tests use synthetic files and SQLite databases. They cover exact arithmetic,
repeat-request multiplicity, read-only ledger preservation, embedding/cached-token
double counting, held and incomplete usage, evidence tampering, policy mismatch,
exclusive output and closure refusal when the ledger changes during verification.
