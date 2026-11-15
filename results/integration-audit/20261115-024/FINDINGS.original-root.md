# Control-v2 actual-runtime audit 024

Independent reviewer role: `/root/parallel_gap_audit`, 2026-11-15. This is a read-only audit of approved coordinator artifacts. No model call, project-code execution, private scoring label, environment/credential access, data change, or live-ledger query occurred.

**Final reader: 3,091 verified assertions, zero failures, exit 0 (`run-03`).** The pinned index supports exactly **112 completed predictions across four controls on 28 ordered decisions**, combining the original 32 and continuation 80 without overlap, duplicate jobs, duplicate method/decision cells, or missing released cells. This establishes recorded execution coverage and binding, not prediction quality.

The fixed entry file is `/private/tmp/gio-profile-20261115-coordinator/control-v2-completion-index-v1.json`, SHA256 `513f75d2cebed5dadd59032b01bbcad7101989d99e2411e2708f650ed087c9b4`. Its two original batches are preserved exactly from the pinned original pilot index. All four batches record frozen runtime `0dcd4b43b82a5a271d195e0bcc6b67695281f37c`.

| Batch | Build jobs | Prediction jobs | Prediction rows | Indexed API attempts |
|---|---:|---:|---:|---:|
| Original builds | 16 | 0 | 0 | 2 |
| Original predictions | 0 | 14 | 32 | 32 |
| Continuation builds | 20 | 0 | 0 | 0 |
| Continuation predictions | 0 | 26 | 80 | 80 |
| Total | 36 | 40 | 112 | 114 |

The two original P1 builds remain invalid and contribute the two extraction calls. They do not become successful profiles or predictions in this audit. The other 34 builds completed: six reusable static controls and 28 decision-bound lexical-retrieval profiles.

The two selection versions are disjoint and together equal the complete released ordered-item set for each researcher. Every submitted per-batch schedule exactly matches its selected item/order list. Across no-profile, name-only, raw evidence, and lexical retrieval, each cell has the same context/options hash. Each researcher has one unchanged release/source/document lineage. The six static profile IDs are reused unchanged across original and continuation batches. Each of the 40 prediction jobs points to exactly one completed parent build with matching profile, method, researcher and source manifest.

Per-job checks cover referenced byte hashes, semantic job IDs, packet/index membership, saved manifests, exact durable leases, result hashes, profile/content/config hashes, source/document hashes, complete parent-profile binding, method/renderer/prompt pins, backend identity and settings, selected item hashes, result-row hashes, cache keys, all 228 trace-file hashes, and attempt/status counters. Source bytes remain in their approved locations. No uncertain attempt, cache hit, missing completion trace, or repeated indexed attempt is recorded here.

Settings remain fixed across selection versions: gpt-6-luna, medium reasoning, consumer maximum output 8,192, extraction maximum output 16,384, declared temperature 0.0, cap 2,048 and replicate 0. The complete consumer identity is identical across all prediction jobs; its API adapter identity records temperature as not sent. These are declared/application-recorded settings, not independent observation of provider wire traffic.

Accounting distinction: the index contains **114 recorded calls** and estimated cost **$0.0164722**. The already approved embedding summary is separately hash-pinned (`fa80d92d41da8874ece7fb45264da97039a9bcc81f36b06ae94d2b58c1ebc1e6`) solely for reconciliation: two calls and $0.00007848. Their sum equals the continuation execution summary's recorded campaign snapshot of **116 calls and $0.01655068**, with zero reserved dollars, uncertainty and in-flight calls at that snapshot. This is a consistency check of saved accounting records, not a current ledger query or provider invoice verification.

Audit setup/history is preserved. The initial patch expected the older 018 reader layout, but the copied current reader already had relocation support. Context verification failed before any file mutation or audit run; `setup-note.json` and `base-reader-used.py` preserve the issue and exact base. `run-01` passed 2,972 checks; `run-02` added explicit profile identity/source/settings and consumer-pin assertions and passed 3,088; `run-03` additionally pins the already approved embedding summary and passes 3,091. Earlier successful runs remain intact.

This audit does not read scoring labels or evaluate fidelity, source-span interpretation, loaded-process authenticity, or newer semantic prediction handoffs. Semantic completion, if later released, is a separate comparison against this fixed four-control schedule. Runtime source and actual conditioning semantics remain covered by their separate audits.

Evidence:

- `read_metadata.py`: standard-library reader derived from the preserved 018 reader, with explicit control-v2/versioned inputs and portable data-root mapping.
- `run-03/report.json`: final sanitized checks, counts, per-job/trace metadata, matched-decision hashes, saved ledger summary, and complete input inventory.
- Each run retains its exact `reader-used.py`, `invocation.json`, `stdout.txt`, and `stderr.txt`.
- `input-inventory.json`: `control-runtime-audit-input-inventory-v1`, with each original absolute `path`, byte `sha256`, and `size_bytes`. It contains no file contents and can guide a separately authorized private archive.

Reproduce into a new output directory:

```sh
python3 -I /tmp/gio-integration-audit-staging/control-runtime-24/read_metadata.py --data-root /private/tmp/gio-profile-20261115-coordinator --out /tmp/gio-integration-audit-staging/control-runtime-24/run-04
```

For an exact relocated private archive, use `--data-root ARCHIVE_ROOT --recorded-data-root /private/tmp/gio-profile-20261115-coordinator`; original artifact bytes and hash pins stay unchanged. This audit tested the original coordinator root; relocation support is inherited from the preserved base reader. No raw source/profile/decision/response text belongs in public audit results.
