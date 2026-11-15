# API adapter and shared-ledger audit

Pinned release `c840615c885464404147a1cdea12343569d331fc`, API implementation
`e24543cb40b2043016f771a2a0359766e81399d2`. Thirteen checks verify; two failing
observations identify one partial-usage reporting gap. Ten existing backend tests
pass. Root independently repeated the probe; no budget bypass was observed.

If only input-token or output-token usage is reported, the adapter records both
as zero before holding the lane. The independently valid component is lost from
accounting. Full reservations remain held and subsequent calls blocked, so this
is a reporting failure under partial/malformed usage, not demonstrated overspend.
Detailed arithmetic in `FINDINGS.md` uses only the code's declared rate table;
it is not current-price or billing verification.

Working checks include shared aggregate reservations, immutable policy, pending
and uncertain persistence, thread/process concurrency, no retries, outgoing
model/reasoning/settings identity, successful and incomplete-response usage, and
per-job allocation limits. Current provider rates, availability, authenticity,
actual network behavior, whole-campaign accounting and final-use workflow remain
unverified. Passing these checks does not establish live readiness.

The audit substitutes a synthetic-only environment mapping before constructing
or calling the adapter and mocks transport. Unit tests receive an explicit
synthetic child environment plus a network-denial guard. Root's confirmation
also starts with an environment containing only `PYTHONDONTWRITEBYTECODE`.
No real environment, secret, endpoint, or paid call was accessed.

`run-01/` and `root-confirmation/` preserve observed requests, ledgers, subprocess
commands, logs, usage and all claims. SQLite files contain only synthetic ledger
records. All 160 source-file hashes remained unchanged. Restore the source archive
specified in `source/AUDIT_SOURCE.json`, copy that manifest to its root, and run
`reproduce.py --source-root SNAPSHOT --out NEW_OUTPUT` with a fresh directory.
Exit zero reports successful evidence capture, including failed observations.
