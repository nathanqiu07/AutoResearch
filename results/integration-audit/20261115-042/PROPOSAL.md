# Closed profile204 retention proposal

This is a metadata-only proposal. No referenced packet, profile, result, trace,
release, selection record, source corpus or archive payload was opened or copied.
The only JSON bodies read were the three explicitly supplied closed snapshots and
22 pinned public archive metadata files. Explicit references received `lstat`
observations for file kind, size and modification time only. No SQLite was opened.

The three closed snapshots agree on 204 unique completed jobs (174 control,
30 search), 672 unique recorded request hashes and 672 unique completed ledger
reservation rows. The exact request-hash multisets agree. Recorded known spend is
124,590,125 nanos (USD 0.124590125), with zero reported cache hits, pending rows,
uncertain rows or retained holds. This is saved-record agreement, not authenticated
physical provider execution or invoice validation. It does not duplicate the
174-control binding review or preference scoring.

The completion and supervisor snapshots explicitly name 3,634 file-reference
occurrences; adding the three entrypoints gives 3,637. They resolve to 3,022 unique
`(recorded path, raw-file SHA-256)` identities and 2,822 declared content hashes.
There are no conflicting hashes for the same path. All named files were regular
files at the bounded metadata observation. The four repeated content groups have
2, 3, 99 and 100 logical paths; all are release records. Deduplication remains a
proposal until raw bytes match the recorded hashes.

None of these 2,822 declared content hashes occurs in the compared archive member
catalogs: the 16 private archives indexed by audit040 and audit039's two separate
source/publication gap archives. A second traversal also found no overlap against
the broader set of every SHA-shaped value in the pinned receipt metadata.
This is not a search of every private file on the machine. Pending041 is separate;
its stated scope adds no profile204 inputs. Archive payloads were not rehashed.

The declared `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca` runtime already has a
92-file code archive. Its tar SHA is
`573321eae5ef8765ef276d93ce684272057dde71f5a795d339573b142bc307c4`,
stored as `sources/f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca.tar` inside
audit032 archive
`bf3b85a686cb96f5e18f3875d0c746e0f6ecd0d6242df8076b9e6aea764cf3b1`.
Its durable040 copy is identified in the report. This recorded source match does
not verify the actual import environment or recover full Git history.

| Candidate category | Logical files | Declared unique hashes | Estimated bytes after deduplication |
|---|---:|---:|---:|
| Saved traces, results and profiles | 1,752 | 1,752 | 98,860,663 |
| Execution bindings and batch records | 1,032 | 832 | 3,575,068 |
| Original-plan, rebind and candidate provenance | 214 | 214 | 2,255,950 |
| Closed accounting, supervision and diagnostics | 18 | 18 | 2,390,100 |
| Compiler and supervisor source, separate code review | 2 | 2 | 31,052 |
| Coverage/selection/excluded-job context: hold | 4 | 4 | 957,668 |
| Total first-order references | 3,022 | 2,822 | 108,070,501 |

These are current `lstat` size estimates, not hash-verified new bytes. Copying every
logical path without deduplication would total 127,940,769 bytes. The204 profile
files alone account for 93,728,648 bytes. `scope-proposal.json` provides exact
per-role and path-prefix counts and bytes; role totals overlap and are not additive.

All directly saved request/response, result and profile references lie under the
explicitly named coordinator `output` or `receipts/.../preparation` paths. That is
a location-and-role check, not a claim that opaque contents are label-free.
No named path matched the documented evaluator/label/scoring/SQLite screen.
The following four first-order references are held outside the proposed terminal
evidence set: the richer-fit paired-selection record, two broader richer coverage
indices and the explicitly excluded job's packet. Their exact paths and hashes
are listed in `scope-proposal.json`; their contents were not read. Root should
decide whether any are needed and authorized before retaining them.

Recommend first retaining the exact saved evidence and execution bindings,
closed accounting/supervision and the rebind provenance needed for the intended
replay, with raw bodies private and a hash-addressed mapping preserving every
logical identity. Choose the precise categories before copying. The two compiler
and supervisor scripts can receive a separate code-only review before any public
retention decision. Do not recursively copy all source corpora simply because a
profile or release refers to them. The frozen requests/profile bytes and hashes
support a narrower saved-input audit; rebuilding upstream extraction or source
lineage would need additional explicitly approved dependencies.

`input-pins.json` records25 exact metadata inputs. `map_retention.py` produced
`run-02/report.json`, `retention-map.json` and `new-content-proposal.json` with
3,118 passing assertions. `summarize_scope.py` produced the separate scope proposal.
`check_boundaries.py` passed six synthetic controls and9,717 bounded metadata
assertions, including an independent reference traversal and receipt-hash-superset
comparison. These repeated row checks are not independent observations or a full
execution audit. Exact command arrays, exit codes and stdout/stderr are preserved.

The first mapper run incorrectly assumed the scalar `manifest_sha256` must equal
the referenced manifest file's raw hash. All204 differ, while their planned and
recorded request counts agree. The failed script, command and stderr are retained.
The corrected mapper preserves the two recorded identities separately and uses
the explicit file-reference SHA for retention. It does not infer the scalar's
derivation without reading manifests. This is an audit setup error, not a runtime
failure. Earlier metadata-schema exploration errors are noted separately.

The current reader depends on the named closed snapshots and pinned public
receipt metadata; the bodies are not bundled here. This package proposes the
missing retention set and does not claim a standalone recovered-input replay.
Only the strict `safe-manifest.json` entries plus that manifest may be published.
No private payload, archive, replay tree or `__pycache__` belongs in the package.
