# Control-v2 actual-runtime audit 024

Independent reviewer role: `/root/parallel_gap_audit`, 2026-11-15. This audits approved coordinator artifacts without changing the originals. No model call, project-code execution, private scoring label, environment/credential access, original-data change, or live-ledger query occurred. A later authorized private copy and relocated replay are documented below.

**Final reader: 3,091 verified assertions, zero failures, exit 0 in both `run-03` and `run-04-relocated`.** The pinned index supports exactly **112 completed predictions across four controls on 28 ordered decisions**, combining the original 32 and continuation 80 without overlap, duplicate jobs, duplicate method/decision cells, or missing released cells. This establishes recorded execution coverage and binding, not prediction quality.

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

For an exact relocated private archive, use `--data-root ARCHIVE_ROOT --recorded-data-root /private/tmp/gio-profile-20261115-coordinator`; original artifact bytes and hash pins stay unchanged. Both the original root and an extracted relocated archive have now been tested. No raw source/profile/decision/response text belongs in public audit results.

## Private preservation and relocated replay

All **695** explicitly audited inputs are preserved at `runs/user-model-integration-audit/private/control-20261115-v2.tar.gz` under the audit repository. The archive is ignored by Git, mode **0600**, inside a **0700** directory. It is **574,273 bytes**, SHA256 `e246997edb4031f2e39f6db729ef35f9114858e19d6bded9a69150e82acc0f4d`. Every tar member's exact relative name, size, hash and regular-file type was verified; every extracted private replay file was rehashed. Original inputs remained unchanged. `private-preservation.json` is a metadata-only member receipt, not the archive itself.

The unchanged final reader ran against the extracted copy using the original-root mapping and passed **3,091 checks** (`run-04-relocated`). Summary, batch records, execution summaries, all per-job records, matched decision hashes, accounting references and mapped input hashes match `run-03`. Diagnostic check entries match as a **duplicate-preserving multiset**. Their list order varies because the reader iterates a set of control names; that incidental ordering is not a data or validation invariant.

The first preservation attempt was blocked by the filesystem sandbox before archive creation. The authorized retry created and verified the archive and completed the reader, then failed only because its wrapper compared the diagnostic array in order. The exact wrapper, errors and comparison evidence are preserved. A later ad hoc comparison also needed `/tmp` normalized to `/private/tmp`; it failed before writing data and is recorded in `preservation-comparison-01.json`. No reader portability defect or changed input was found. A separate verifier rechecked the retained archive/replay and wrote the receipt successfully.

Current utility wrappers accept explicit stage/repository/archive locations; the recorded root defaults to the hash-pinned inventory. `preserve_and_replay.py` creates a fresh ignored private archive and refuses overwrites. `verify_private_copy.py` accepts an already retained archive plus its hash and fresh replay/output/receipt paths, without requiring original inputs or overwriting the archive. These final portability-option changes received syntax/CLI checks only; the completed archive and `run-04` replay evidence comes from the exact preserved scripts named in the receipt. No additional reader run was performed after that utility-only change. Original, comparator-corrected, and portable script versions remain available for reconstruction.

**Public packaging uses `public-files.json` only.** It explicitly lists safe files and hashes. Never recursively copy this staging tree: `private-replay/` contains actual source, decision, profile and response text. Both that directory and the private archive are excluded from the public package. `FINDINGS.original-root.md` and `EVIDENCE_SHA256.original-root.json` preserve the earlier checkpoint.
