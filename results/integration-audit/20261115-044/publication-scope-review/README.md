This additive review applies the source-owner publication restriction that arrived after the frozen audit 044 review. The exact approval bodies and complete preservation mapping must remain private. It does not change the earlier byte-preservation findings or authorize any new reads.

The boundary check passes 235 assertions over 46 explicit code and metadata files. Exactly three contain a complete restricted approval or mapping: controls/allowlist.json, controls/custody.json and preservation-01/receipt.json. No additional complete copies were found in the other reviewed files. This is a bounded structural and literal check, not a general secret scan or proof about arbitrary encoded content.

Use the 21 unchanged original-core files in check-01/proposed-original-core-public-files.json. Keep the original author README and original manifest privately as historical records, along with the three restricted files. Root chose this conservative subset after briefly considering renamed historical documents. The new public README and final explicit manifest are authoritative.

The prior independent review remains frozen evidence of its original code and metadata checks. Its earlier statement that 25 author files were public-safe predates the new restriction and is superseded here. That old wording and the old manifest must not be used to copy restricted bodies into a public package. The prior review files themselves contain no complete approval/mapping copy. Its receipt checker requires the complete PRIVATE core; it cannot reproduce all checks from the narrowed public package alone.

The separate saved-external check passes 26 assertions. The original and root external archive-verification reports differ only in argv; all other values and ordered arrays match. Saved root metadata records 33 private payload entries totaling 28,082,867 bytes, or 35 files including manifest and receipt, with 0600 files and 0700 directories. The private bundle retains the exact withheld approval bodies, full mapping receipt and original author guide/manifest. It also retains the archive and recovery code. The three reused snapshots still depend on the separate 042 archive.

This review did not open the private external bundle, a raw payload or any archive body. The saved guard covers read_regular calls and denies process/socket use; it is not an OS-level file trace. No consumer replay, scoring, model/API call, provider verification, new eligibility review or semantic body inspection occurred.

Public hash-only-retention-summary.json records counts and pins without exporting approval bodies or logical mappings. Root must verify its final assembled public files against a new explicit allowlist. The original frozen core, prior independent review and private receipts remain unchanged.

To reproduce these metadata checks, pass the complete private core and explicit saved metadata roots:

```sh
python3 -I -B check_boundary.py \
  --core /private/path/to/complete-audit-core \
  --review /path/to/frozen-independent-review \
  --root-custody /path/to/root-custody-metadata \
  --external-metadata /path/to/external-copy-metadata \
  --out /fresh/boundary-result

python3 -I -B check_saved_external.py \
  --original /private/path/to/complete-audit-core/verification-01/receipt.json \
  --root-results /path/to/saved-root-verification \
  --copy-manifest /path/to/external-copy-metadata/copy-manifest.json \
  --out /fresh/external-metadata-result
```

Both commands use pinned code/metadata only and never follow raw payload or archive references. Copy only this addendum's safe-manifest.json allowlist plus that manifest.
