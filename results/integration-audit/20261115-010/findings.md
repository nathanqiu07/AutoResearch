# Runner retest: one fixed, four remaining

New release: `c840615c885464404147a1cdea12343569d331fc`.
Its snapshot records implementation `523d653978b03bff60989564b363ddb8b91aabf7`
and API implementation `e24543cb40b2043016f771a2a0359766e81399d2`.
All 160 pinned source hashes matched before and after execution.

Prior comparison: source `05c503e5f6170a690a13feb75cbe2dc65d430ba8`, published
under `results/integration-audit/20261115-007/runner`. That evidence is preserved;
its five failures are not silently attributed to this newer release.

| Original finding | New result | Decisive observation |
| --- | --- | --- |
| P1: mutable validated items/settings | Remaining | First callback changes second context and temperature; both predictions finish under the original config/items hashes. First result cache key differs from the actual trace key. |
| P2: cache bypasses elapsed wall time | Remaining | At mocked elapsed 31 seconds against a 30-second allocation, cached second prediction completes; matched no-cache control returns `allocation_exhausted`. |
| P2: missing allocation `cost_mode` | Remaining | Correctly hashed malformed allocation creates claim and manifest, then raises `KeyError('cost_mode')`; no result is written and no backend is called. |
| P2: unbound builder-visible document metadata | Fixed for the tested case | Valid original build completes. Changing author metadata under the original full document hash is rejected before claim/call. Updating `documents_hash` produces a different job ID and completes. Both successful profiles retain their actual document hash. |
| P2: declared extraction settings differ from actual calls | Remaining | With a valid full document hash, synthetic builder calls temperature 1/max_tokens 32; completed profile still records declared temperature 0/max_tokens 128. Trace preserves actual settings. |

The new build manifests contain `documents_hash` **before** either build probe.
The metadata test has both unchanged-input and explicitly rebound-input success
controls. Thus its rejection is not a missing-new-field setup failure. The
extraction-settings probe reaches an actual synthetic call and completes, so
its remaining finding is also not caused by incomplete setup.

Current source locations:

- Mutable input reuse: `autoresearch/taste/overnight/runner.py:224`, `:269`, `:280`.
- Cache hit before wall-time check: `runner.py:171` versus `:177`.
- Missing mode crash: allocation validation at `runner.py:86`; direct mode lookup at `:208`.
- Fixed document validation: `runner.py:123`; profile document hash at `contracts.py:164`.
- Declared extractor settings recorded directly: `contracts.py:165`; actual calls pass through `runner.py:163`.

## Passing controls and scope

All **12 targeted owner runner tests pass**. Independent concurrent-claim and
uncertain-attempt controls still pass: one canonical lease permits one backend
call, and an uncertain first attempt preserves evidence, blocks later calls,
and prevents rerun. The no-cache elapsed-time control and included historical
runner-fixture-v2 integrity checks also pass.

The mutable-input probe models caller-owned dictionary changes during a backend
call; it does not alter the frozen source or profile. The cache finding concerns
work after the wall limit, not extra paid calls. The extractor probe establishes
an unchecked method/infrastructure boundary, not misuse by an existing method.

The new API/shared-ledger adapter is present but audited by another lane.
Retrieval-decision binding is tested separately by the root agent. Neither is
classified as an absent feature or a failure here. Confirmation/final-use
authority, real transport, real costs, and power-loss durability remain outside
this retest.

No live calls, credentials, real source documents, real labels, or owner-code
edits were used. This is plumbing/provenance evidence, not fidelity evidence.

## Reproduce

```sh
python3 -B reproduce.py --source-root /path/to/frozen-c840615-snapshot --out /path/to/fresh-evidence --contract /path/to/SHARED_CONTRACT.md
```

`--contract` is optional and only pins the supplied contract file's hash.
The output directory must be new. The exact executed command and exit status
are in `evidence/command.json`; targeted test command, status, stdout and stderr
are saved beside it. `evidence/report.json` includes explicit old/new comparisons.
Individual case JSON, synthetic traces, cache entries, claims and results are
preserved under `evidence/`.

Audit exit zero means the retest completed and its observations matched its
report. It does not mean the four remaining contract checks passed.
