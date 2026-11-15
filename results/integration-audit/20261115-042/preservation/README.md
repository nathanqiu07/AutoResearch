# Three closed profile204 snapshots retained

This additive package preserves only the three explicitly released closed metadata
snapshots: completion/provenance index, supervisor terminal record and closed
ledger JSON snapshot. It does not retain any of the other referenced profile,
result, trace, packet, selection or source-corpus files. No SQLite was opened.
The frozen042 retention map and its earlier `lstat` observations are unchanged.

The new archive is named `profile204-closed-metadata-20261115-v1.tar.gz`, under the
worktree's ignored `runs/user-model-integration-audit/private` directory. Its exact
path is recorded in `private-preservation.json`.

- Archive SHA-256: `28e03a21179eb9d12c9c78663027477c67adbca4ac31c16393b303e3b15583dd`
- Archive bytes:405,070; three member files totaling1,890,004 uncompressed bytes.
- Archive mode0600; private directory0700. Existing files were not overwritten.
- Receipt SHA-256: `017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0`

The receipt identifies each exact source path, member name, approved SHA and size.
All three archived member bodies equaled the source bytes; source bytes remained
equal before and after preservation. Tar entries have zero timestamps and
owner IDs, empty owner names, mode0600 and lexical member order. Gzip has zero
timestamp and an empty filename. Nine synthetic checks cover deterministic
generation in the same compression implementation, roundtrip headers, wrong pins,
missing/extra/duplicate members, unsafe member paths and overwrite rejection.
Compressed-byte identity across every Python/zlib implementation is not claimed;
the retained archive's exact byte hash is fixed.

`preserve-01` records the default sandbox denying creation in the approved private
worktree path before any archive was written. `preserve-02` records successful
creation through the authorized escalation. This was a local filesystem boundary,
not a failed runtime job. An exploratory attempt to index the original review's
file manifest as a list also failed: that manifest uses a filename-keyed dictionary.
The source reader was then checked by its actual schema and exact hash.

The unchanged independent `review_snapshots.py` is included with SHA
`24ca671a2d62c3783af775de395197c8eecac0de496a56a125fc2fab688d570e`.
Its existing original execution passed45 checks. This additive preservation step
has not rerun that reader; root will replay it from recovered archive members.
`frozen-reader-copy.json` records the exact copy identity and unchanged source.

For a portable replay, set four paths yourself: the published code package, the
retained archive, a fresh private extraction directory whose parent exists, and an
existing output directory for metadata-only reports. These commands do not access
the original temporary input paths:

```sh
python3 "$audit_package/archive_closed_metadata.py" extract \
  --archive "$retained_archive" \
  --receipt "$audit_package/private-preservation.json" \
  --receipt-sha256 017b7d1ffafdb66731081274cd4e9be3087c67b805e4f225826b5407e18949c0 \
  --out "$private_extraction" \
  --report "$public_output/extraction.json"

python3 "$audit_package/review_snapshots.py" \
  --index "$private_extraction/completion-provenance-index.json" \
  --supervisor "$private_extraction/supervisor-terminal.json" \
  --ledger "$private_extraction/profile204-closed-ledger-snapshot-v1.json" \
  --out "$public_output/replay-report.json"
```

The extractor verifies the supplied receipt hash, archive hash, exact member set,
member metadata and every member hash before writing to a fresh0700 directory.
It uses explicit archive bytes and does not fall back to original source paths.
The original reader follows no referenced pointers. A replay comparison should
preserve every original report field and array except the three `inputs[].path`
values needed to name the recovered files. Reader hash and all input hashes remain
identical. Do not claim that this regenerates the separate retention mapper's
original filesystem observations or reconstructs the underlying672 provider calls.

Only `safe-manifest.json` entries plus that manifest may be copied into public
results. The private archive and any recovered raw metadata members stay private.
Root will make a separate external retention copy; this stage establishes only
the worktree private archive, not off-device backup or a full environment recovery.
