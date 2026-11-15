# Closed-record retention: schema and layout handoff

This is a static reference for the separate CLOSED scaling404+ownswap28 and CLOSED reference inventories. It does not inspect those inventories, the terminal receipt, private approvals, payloads or archives. It grants no copy or execution authority. Root relays this handoff to planning/coordinator; role09/10 inventory work and role04 custody decisions remain separate.

`source-pins.json` binds every reference below to its exact public path and full SHA-256. Source IDs: **M**=042 mapper, **B**=044 custody binder, **C**=044 copier/verifier, **A**=042 three-snapshot archiver, **T**=044 synthetic tests, **R42/R44**=their READMEs, **PC/PR/VC/VR**=public invocation/result/verification records, **HS**=public hash-only summary. `C:110–137` denotes source lines, not a claim that code was run here.

## 1. Inventory first; declared hashes are not verified bytes

The 042 pin file is read through `inputs[]` entries with `path`, `sha256`, `size_bytes`, `role` and optional `relative_path`; it also uses `repo_root` for a particular archive-catalog binding. Each supplied metadata file is hashed before JSON parsing and byte-rechecked at finish. Its exact expected primary roles are `completion`, `supervisor`, `ledger_snapshot`. **M:56–75,196–211**.

First-order references are dictionaries with **exactly** `path` and `sha256`; scalar paths and dictionaries with extra keys are not captured by that reference recognizer. Nested dictionaries/lists in the approved metadata are traversed, but referenced bodies are not opened. Each entrypoint itself is included. Occurrences are grouped by `(path, sha256)` and retain `logical_occurrences: [{document, json_pointer}]` plus a sorted `roles` union. **M:29–53,151–174**.

Map schema is `profile204-first-order-retention-map-v1`, with `pins_sha256` and `inputs[]`. Each mapped row has `path`, `sha256`, `logical_occurrences`, `roles`, `retention_status`, `receipt_matches`, `retained_size_bytes`, `observed_lstat`. Optional `observed_lstat` is `{kind, size_bytes, mtime_ns}` for observed entries or `{kind: missing}`; it proves neither content hash nor eligibility. Status values are `exact_path_and_hash_retained`, `hash_only_bytes_retained`, `not_in_compared_receipts`. Same-path/different-hash conflicts are reported separately. **M:163–186,203,210**.

The archive catalog is bounded to the specifically pinned receipts. Receipt-match fields are `recorded_path`, `sha256`, `size_bytes`, `archive_member`, `archive_sha256`, `receipt`. A declared hash match is a recovery candidate, not a fresh member verification. Preserve the distinction between a raw file reference SHA and a scalar semantic/request/manifest digest. **M:113–149,205–207**.

For the new inventories, preserve all logical roles and terminal/failure/hold identities rather than deduplicating jobs or scientific observations by file hash. Keep request/response/target mappings private. A new finite inventory must state its own entrypoints, denominator, catalog scope and unresolved references; 042's model/count/closed-state assertions do not establish closure for a different run.

## 2. Typed role04 custody, then coordinator authority

The public code exposes these **consumed fields**, not the complete private custody-document format:

| Document | Required fields used by the published binder/copier |
|---|---|
| Exact allowlist | `schema_version: profile204-private-retention-exact-allowlist-v1`; `source_map.sha256`; `allowed[]`; `excluded[]`; `raw_copy_performed: false` |
| Custody review | `schema_version: profile204-retention-custody-review-v1`; `source_map.sha256`; `exact_allowlist.sha256`; `excluded[]`; `raw_copies_made_by_reviewer: 0`; `live_ledger_access: false`; `private_groundtruth_accessed: false`; `model_calls: 0` |
| Allowed tuple | **Exactly** `path`, `sha256`, `roles`, `logical_size_bytes_observed` |
| Excluded tuple in binder | The same four identity fields; the copier checks excluded paths/disjointness and matching exclusion records across controls. |

**B:43–86; C:31,110–137,342–359.** Hashes bind exact metadata files. The binder compares path/hash/sorted-role-set/size identities: `map.inputs[].observed_lstat.size_bytes` becomes `logical_size_bytes_observed`. It requires an exact disjoint allowed+excluded partition, no duplicated tuple/path, nonempty unique roles and consistent size for a repeated hash. It checks exclusions but never opens their referenced bodies. The copier checks its narrower control subset; do not substitute that for the separate full partition check.

Allowed rows require canonical absolute non-root paths; no `.`, `..`, glob characters or NUL; lowercase 64-hex SHA-256; a nonnegative integer size (not boolean); nonempty unique string roles; unique logical paths. `.env`, `.env.*`, `.sqlite`, `.sqlite3`, `.db`, `-wal`, `-shm`, `.lock` names are rejected. **C:47–53,110–137**. These filename checks are not a secret/label-content scan. Any new custody schema must still explicitly exclude credentials, actual SQLite and unrelated paths.

After role04's scoped decision, coordinator authorization must name the exact inventory/allowlist/custody pins, approved source scope, copier code identity, fresh archive/output names, reuse dependencies and private destination. This is the requested coordination boundary, **not a generic authorization parser supplied by 044**: the existing copier only accepts its hardcoded release pins. No implicit path discovery, nested-reference expansion, new payload interpretation, experiment replay or Git payload publication follows from clearance to retain bytes.

## 3. Private archive, exact reuse and verification

A reuse receipt has `archive_sha256`, `members[]`; consumed member fields are `source_path`, `archive_member`, `sha256`, `size_bytes`. The existing042 receipt additionally has `member_count` and archive/format/source-comparison metadata. Reuse aliases must match an approved tuple by **source path + SHA + size**, with unique source/member names; the whole existing archive must have the exact expected member inventory and hashes. **C:234–256; A:117–130**. A hash-only mapper match does not automatically satisfy this path-bound reuse rule.

044 reads every approved logical source independently, including reused aliases, checks actual hash/size and stable file state, then compares bytes before deduplicating equal-hash new sources. It rereads all sources after writing and rechecks controls and the reused archive. All path components are traversed without following symlinks, and nonregular sources are rejected. This is bounded before/after equality, not continuous custody. **C:56–107,270–306,362–365**.

New archive members are `objects/<sha256>`. The deterministic layout is USTAR inside gzip, sorted members, regular mode0600, uid/gid/mtime zero, empty owner names, empty gzip filename/mtime zero, compression level9. The exact archive hash is authoritative; cross-library compressed-byte reproducibility is not promised. Verification rejects extra/missing/duplicate, unsafe, link or wrong-mode members and wrong bytes. A fresh exclusive0600 archive is written in an existing0700 private directory and verified after writing; no overwrite or silent refresh occurs. Failures after creation leave a private quarantined artifact and a safe reason-code failure receipt, not successful retention. **C:140–231,290–325,445–454; R42:20–26**.

The **private full receipt** uses `schema_version: profile204-private-retention-receipt-v1`. Its mapping is `logical_inputs[]`: the four allowed-tuple fields plus `storage` (`new_archive` or `existing_archive`) and `archive_member`. `source_states` is keyed by original path and records `size_bytes`, `mode`, `device`, `inode`, `mtime_ns`, `ctime_ns`. Other fields include `archive_path`, `archive_sha256`, `archive_size_bytes`, `archive_mode`, `logical_count`, `declared_distinct_hashes`, `logical_bytes`, `declared_distinct_bytes`, `new_member_count`, `new_uncompressed_bytes`, `new_logical_count`, `new_logical_bytes`, `reused_logical_count`, `reuse_archive_sha256`, `reuse_archive_path`, before/after counts and booleans, `control_pins`, `argv`, `reader_sha256`. **C:73–76,135–137,259–267,309–325,432–439**.

The standalone `verify` action uses private controls, mapping receipt, new archive and reused archive; it does not read original logical source bodies. It checks exact expected mapping, control pins, archive mode/hash/size and every member. It reports the input receipt's hash; the caller should preserve/check that exact receipt pin as part of recovery provenance. It performs no extraction or consumer replay. **C:383–401; VR:22–34**.

## 4. Layout and public boundary

Historical private layout: ignored `runs/user-model-integration-audit/private/<new-unique-archive>.tar.gz`, plus a private0700 output directory with0600 `receipt.json`. The external044 bundle keeps controls under `audit-core/controls/`, the full receipt under `audit-core/preservation-01/receipt.json`, the archive under `private/`, and exact code/commands beside them. It depends separately on the existing042 archive; a receipt is not a substitute for those bytes. The external bundle had33 payload entries plus manifest/receipt,35 files total; these are historical counts, not targets for the new inventories. **C:404–443; R44:16–35,55–75**.

Private-only: exact custody/allowlist documents, full logical mapping/source-state receipt, raw archives, recovered inputs, and request/response/target relationships. Public-safe candidates are approved code, invocation metadata, bounded checks, hashes/counts and limitations under an explicit allowlist. Review argv and error metadata too; do not dump controls/mappings merely because they are JSON. Superseded author-publication wording is not authority. **R44:1–4,16–24; HS:1–25**.

The existing public verification receipt contains `status`, `scope`, `receipt_sha256`, `archive_sha256`, `archive_size_bytes`, `new_members_verified`, `logical_mappings_verified`, `reused_members_verified`, `control_pins`, `argv`, `reader_sha256`. The hash-only summary publishes aggregate counts and private-control/receipt/archive pins. Root's function-level allowed-reader guard plus process/socket hook is explicitly not an OS-level access trace. Opaque retention does not attest secret-free/label-free content, authenticated calls, invoicing, full source/environment recovery or scientific validity. **C:398–401,438; R44:37–44,77–82; VR; HS**.

## 5. Adaptation checklist; not drop-in compatible

- **M** hardcodes profile204 terminal schema,204 jobs/4 batches/672 requests, one model/reasoning combination, accounting totals,18 catalog sources and92-file source closure expectations. Its role classifier assumes particular JSON-pointer positions. New finite closed inventories need their own denominator/schema/catalog bindings; do not run M unchanged. **M:43–53,75–111,113–149,187–208**.
- **B/C** hardcode exact042/044 hashes and schemas,3022 map identities,3016 approvals/6 exclusions,2816 declared content hashes,3013 new paths/2813 new members, and exactly3 reused snapshots. C fixes the archive name, single reuse archive and private-directory suffix; B also fixes excluded-role counts and byte totals. A new named/pinned version is needed after authorization. Generic synthetic helpers are not a production authority bypass. **B:7–12,66–84; C:2–7,23–31,350–358,396–397,420–431**.
- **A** preserves/extracts exactly three pinned042 snapshots with fixed names/sizes/hashes. It is useful to explain the existing reuse receipt but is not a generic extractor for C's `objects/` archive or for new closed runs. C's stronger descriptor-level source checks should not be attributed to A. **A:19–25,88–150**.
- Existing synthetic coverage is a reusable boundary specification: roles/byte dedup/reuse, wrong actual hash/size, symlink parents/files, FIFO, destination preservation/modes, duplicate paths/roles, excluded traps, wrong reuse pins, post-write source mutation, exact archive inventory and determinism. These tests were read, not run here; adaptation requires its own bounded checks. **T:62–213**.

Only public source and public summary metadata were read for this handoff. No private approval or mapping body, original embedded path, production archive, payload, live ledger, credential or dependency was opened. No copier/test/source execution, source audit, new inventory reconciliation or copying was performed.
