Audit 044 privately retains the exact closed-profile204 records cleared by the
source custodian. The final public manifest is authoritative. Earlier author and
review statements about a 25-file public-safe core predate the private-only
approval-metadata restriction; they do not authorize publishing those files.

All 3,016 approved logical sources pass actual before/after byte-hash, size and
file-state checks. Three sources reuse the already retained closed metadata
snapshots. The remaining 3,013 logical paths resolve to 2,813 distinct file bodies,
with byte equality checked before deduplication. Their new uncompressed size is
105,191,777 bytes, in a 24,580,726-byte private archive with SHA256
`6ef3b765d2a43ef7292489e372c5ff30999f1e6e95e244c952f28583383128f6`.
All new members are regular files with mode 0600. The six excluded references
and nested pointers are not opened. Original source files remain unchanged over
the observed copy interval; this is not continuous filesystem custody.

The exact allowlist and custody decision are retained as private control metadata
outside the raw archive. Their SHA256 values are respectively
`f403b554deefa55230486f09c31f469250cc415bf60b3dff41b2cf5e4b5420eb`
and `b20e0ece59ca334a7b51e7072faa784f7050bc68258375e79dc2c4373e195c20`.
The complete mapping/source-state receipt is also private, SHA256
`e01bb0bfaa15ec7457b3df37930f5a7a6812d45fc8742bbcf1eda2099141cd81`.
The public package contains hashes, counts, code, commands and bounded reviews;
it omits those three complete bodies and the superseded original author guide
and manifest. Exact historical originals remain in the private bundle.

The external bundle is at
`/Users/giordanorogers/.local/share/autoresearch/archives/gio-user-model-integration-audit/profile204-private-records-v1`.
Its manifest SHA256 is
`963a81eb821ce24b1b33580460cc3362962a3c17f671ed2734053fefe88dd2e1`.
It contains 33 payload entries / 28,082,867 bytes, plus manifest and copy receipt:
35 files in total, all 0600 within 0700 directories. The exact copied approval
metadata is under `audit-core/controls/`; the complete receipt is under
`audit-core/preservation-01/receipt.json`. This bundle has no invented Git source
membership. It explicitly depends on the separate external042 snapshot archive
with SHA256 `28e03a21179eb9d12c9c78663027477c67adbca4ac31c16393b303e3b15583dd`.

Root verifies the actual external bundle and runs the unchanged archive verifier
against its copied private controls, receipt and archive plus the existing042
archive. All 2,813 new members, 3,016 mappings and three reused members verify.
The result differs from the original standalone verification only in invocation
arguments. An explicit allowlist constrains the verifier's `read_regular` input
boundary, and a Python audit hook denies subprocess/socket operations. This is
not an OS-level file-access trace. No original logical source body is reread by
that verification, and no model/consumer execution or experiment replay occurs.

Verification evidence includes 16 author synthetic tests, six independent
synthetic controls, 143 independent metadata/code-binding checks and root's
separate 23-check custody partition. A later publication-scope review checks 235
assertions over 46 explicit candidates and 26 saved external-comparison
assertions. It identifies exactly the three restricted complete-body copies and
finds no additional complete copies in that bounded set. None of the independent
reviews opens production payload or private archive bodies. Original failed test
attempts and executed code hashes remain recorded.

To verify retained bytes later, use explicit private paths and a fresh output:

```sh
BUNDLE=/path/to/profile204-private-records-v1
REUSED_ARCHIVE=/path/to/profile204-closed-metadata-20261115-v1.tar.gz
CORE="$BUNDLE/audit-core"
python3 -I -B "$CORE/preserve_exact.py" verify \
  --allowlist "$CORE/controls/allowlist.json" \
  --custody "$CORE/controls/custody.json" \
  --reuse-receipt "$CORE/controls/reuse-receipt.json" \
  --reuse-archive "$REUSED_ARCHIVE" \
  --receipt "$CORE/preservation-01/receipt.json" \
  --archive "$BUNDLE/private/profile204-private-retention-20261115-v1.tar.gz" \
  --out /fresh/private/verification044
```

Inputs must have canonical absolute paths, regular nonsymlink files and the pinned
bytes; archive modes must be 0600. The existing `root-verification/` records the
stronger guarded invocation and exact observed input-reader paths. The later root
verification, independent reviews and repository test outputs are public audit
evidence, not claimed inside the earlier sealed private bundle.

This is opaque byte preservation and verification under typed source-owner
clearance, not a semantic secret/label scan, source-quality assessment, prediction
score, authenticated provider call, invoice, full source closure or installed
environment recovery. It is same-machine storage, not an off-device backup.
No model calls, model/settings changes, live ledger access or owner-runtime edits
occurred.
