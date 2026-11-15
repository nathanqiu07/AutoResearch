# Semantic-retrieval release audit

Release `0ca54b470947fcf453c577b14f6b12c7e2a267b0`, implementation
`8f91bde9c96c109fb43a9cb4ce0e3ca205f126af`. Seven audited claims pass; one
pathological numerical case fails. All 22 existing retrieval/baseline tests pass.
Root independently reran the new-release probe. All inputs and transports are
synthetic; no actual embedding provider, cost or preference quality is tested.

The numerical finding is narrowly scoped: `[5e-324, 5e-324]` normalizes to `[1, 1]`
and can outrank a genuinely aligned vector. Replacing it with the same direction
at normal scale changes passage order. Both profiles are complete. This is not
evidence that real provider vectors have these magnitudes or that a study has
misranked sources. See `findings.md` and `run-new/subnormal-scaling-failure.json`.

Exact source/query/model/dimension/hash guards, caps/source spans, semantic adapter
decision binding and separate zero-call reuse accounting pass the tested cases.
Provider metadata is schema-checked, not authenticated. An actual producer job
and its usage evidence are still required for live provenance/accounting claims.

The prior release is separately pinned; its semantic method stays unavailable.
Old/new policy hashes and behavior are retained in `release-comparison.json`.
No artifact was silently migrated. The owner has received the reproduction and
is preparing a new pinned fix; this failed-release record remains immutable.

## Reconstruction

The original staging snapshots named in `findings.md` are preserved here as
compressed source archives, without duplicating their extracted trees:

- `source/new-source.tar.gz` and `source/new-AUDIT_SOURCE.json`.
- `source/old-source.tar.gz` and `source/old-AUDIT_SOURCE.json`.

Decompress the chosen archive into a new directory and copy its matching manifest
to that directory as `AUDIT_SOURCE.json`. The uncompressed archive hash and every
file hash are in the manifest. Run `probe.py --source-root SNAPSHOT --fixture
SNAPSHOT/docs/overnight/gio-profile-20261115/handoffs/05/002-semantic-fixture.json
--out NEW_OUTPUT`; for the old implementation, pass the separately retained new
fixture path and add `--old-release`. Original invocations are saved verbatim.

Exit zero means evidence capture completed; `claims_failed` retains the numerical
defect. It is not an all-checks-pass signal. No source, settings or old evidence
changed during the probes.
