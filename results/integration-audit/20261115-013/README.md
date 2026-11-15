# Runner binding fixes independently reproduced

Release: `2b965eeaeafad029faa1b2055a45c1b29caf2463`.
Runner implementation: `9d4f4e5c36bafeef25784582b1a3416520d79f8c`.
All **161** pinned source hashes matched before and after execution.

All four findings that remained on `c840615` now pass. The earlier full-document
binding fix still passes. No finding remains in this bounded runner retest.

| Exact regression | `05c503e` | `c840615` | `2b965ee` and decisive evidence |
| --- | --- | --- | --- |
| Mutable validated items/settings | Failed | Failed | Fixed. Caller callback still changes the original dictionaries, but both executed requests use the original temperature and context. Row input hashes and both cache keys match the validated execution and actual traces. |
| Cached response after wall-time allocation | Failed | Failed | Fixed. At 31 elapsed seconds against 30 allowed, the second item returns `allocation_exhausted`, with zero cache hits. A valid cached entry exists, so this is not a cache-miss setup artifact. |
| Missing allocation `cost_mode` | Failed | Failed | Fixed. Raises typed `ValueError` before a claim, output directory, or backend call. |
| Unbound document metadata | Failed | Fixed | Still fixed. Valid original build completes; changing author metadata under the old full-document hash fails before claim; explicitly rehashing documents produces a new job ID and completes. |
| Divergent actual extraction settings | Failed | Failed | Fixed. A valid build manifest declaring temperature 0/max_tokens 128 rejects a builder requesting 1/32 with `call_settings_differ_from_declared`, before backend dispatch. The same builder with declared 1/32 completes with one synthetic call and matching trace/profile settings. |

The new extraction-settings setup is valid: both build probes include a full
`documents_hash` and explicit supported temperature/max_tokens. The successful
matched-settings control uses the same builder, source documents, backend class,
and actual request as the rejection probe. Only its declared settings and thus
semantic job identity change. Rejection is therefore not classified as a fix
merely because setup failed.

## Preserved positive controls

- All **16 targeted owner runner tests pass**.
- Two concurrent workers sharing the canonical lease root produce one call;
  the duplicate is rejected.
- An uncertain first call retains its trace and claim, prevents a later call,
  and rejects rerun. No automatic retry occurs.
- Cached and uncached paths both enforce elapsed wall time.
- Normal timely cache reuse still returns two successful predictions from one
  backend call. Both rows' cache keys agree with the started trace and cache
  filename; hit flags distinguish the actual call from reuse.
- Matched extractor settings produce a complete profile and one recorded call.
- The historical included runner-fixture-v2 still has consistent manifest,
  claim, trace hashes, and cache hashes. This verifies the included artifact's
  links, not a replacement fixture.

## Scope and evidence

Only invented documents/choices and recording backends were used. No live
calls, real source records, labels, credentials, or owner-code edits occurred.
This closes the runner regression lane; the API/shared-ledger adapter,
retrieval binding, and evaluator confirmation authority are assessed separately.
Real backend costs/timeouts and power-loss persistence were not exercised.

Previous 007 and 010 evidence remains unchanged. `evidence/report.json` records
the original, preceding, and current source versions for each finding. Individual
case JSON and all synthetic run artifacts are preserved under `evidence/`.
`evidence/source-verification.json` records all 161 pinned file checks and the
reproducer hash. Exact invocation, status, stdout/stderr and targeted owner-test
command/output are saved alongside the report. `SHA256SUMS.json` preserves the
reviewer's earlier staging manifest. `checksums.json` covers every final package
file except itself, including root confirmation and the source archive. The
original `findings.md` is retained unchanged from staging.

Portable reproduction, with a fresh output directory:

```sh
python3 -B reproduce.py --source-root /path/to/frozen-2b965ee-snapshot --out /path/to/fresh-evidence --contract /path/to/SHARED_CONTRACT.md
```

`--contract` is optional and pins only the supplied contract's hash. Audit exit
zero means the recorded checks completed; pass/fail findings are explicit in
the report. This run records 11 verified cases, four newly fixed regressions,
one still-fixed regression, and no remaining regression in the tested set.

Root independently reran the portable reproducer on the same frozen release. All 11 recorded cases and 16 owner tests passed again; `root-confirmation/` preserves that second execution. The source archive is in `source/source.tar.gz`; extract it and copy `source/AUDIT_SOURCE.json` to the extraction root before rerunning.
