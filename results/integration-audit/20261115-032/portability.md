# Additive portability follow-up

The original25-file `manifest.json`, both original executed scripts, the
preservation receipt and every private archive remain byte-identical. This
follow-up adds wrappers and verification; it does not rewrite the frozen032
retention evidence.

Use `preserve_portable.py` for future inventory/preservation work and
`verify_union_portable.py` for archive-only recovery verification. The original
`preserve.py` and `verify_union.py` remain the exact executed versions indexed
by the original manifest. Extra `*-executed.py` copies explicitly preserve the
same bytes; `manifest-before-portability.json` matches the original manifest.

The new preserver requires `--coordinator-root`. Its top-level frozen pointers
are relative names with unchanged expected hashes. It derives the recorded
coordinator identity from the pinned index and maps only that exact lexical
prefix to the supplied physical root. Sibling paths do not match the prefix.
Existing private dependencies are found by preserved basename under the
explicit `--archive-dir`, then checked against their receipt/archive hashes.
External pointers keep their existing hash-bound resolution; the wrapper does
not search unrelated directories or follow credentials/SQLite pointers.

The new verifier selects the phase1 index by its role in the hash-pinned
preservation receipt, then verifies the selected member's hash and size. It no
longer requires the index's recorded host path to equal a source-code constant.
All other archive checks retain the previous meaning.

| Script | SHA256 |
| --- | --- |
| Exact executed preserver | `ed30ef8324ec6b47b35793723b764dbf88d5fd4532a274a8d2330fd8da2cc9a4` |
| Exact executed verifier | `dc1bfd0e8379b6563401d02f3c12a3463dc22baf919ade497799b64e3c3bf524` |
| New portable preserver | `bcfd366aff991def95095414abda4d7f3d7113eabceeff6423d6e0dd859f6b87` |
| New portable verifier | `105353d45330aaca07f2daa1c5658febb3a06b6cdf51b81b84b27513579daacf` |

Both wrappers pass syntax checks. The preserver's CLI exposes the required
root, and three synthetic lexical-path checks pass. No new real-input
preservation run or archive write was performed with the new wrapper; its
validation is deliberately limited to syntax/CLI/path mapping.

The portable verifier ran against the unchanged archive union into fresh
`archive-union-verification-portable-03.json`. Its JSON result equals both the
original agent verification and root's repeat:2,252 record references,
132phase1 jobs,84original stopped admissions and78dispatched results, with no
original data paths read. Commands and hashes are in
`portable-verify-03.invocation.json`, `portable-help-02.invocation.json` and
`portability-verification.json`.

The unchanged final receipt and exact executed verifier were also copied as
new mode0600 files beside the private archives, within the existing mode0700
Git-ignored private directory:

- `terminal-preservation-32-receipt-v1.json`: SHA256
  `6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8`.
- `terminal-preservation-32-verifier-executed-v1.py`: SHA256
  `dc1bfd0e8379b6563401d02f3c12a3463dc22baf919ade497799b64e3c3bf524`.

`durable-metadata.json` records exact paths, modes, hashes and read-back checks.
These copies make the receipt and original verification program independent of
the temporary staging directory. They contain metadata/code only. No raw
material was added to public evidence.

For portable archive-only verification, replace `verify_union.py` with
`verify_union_portable.py` in the original findings command. The same receipt
pin, archive-root and audit-root arguments apply. The full evidence list is the
union of the original `manifest.json` and the additive
`portability-manifest.json`; the original manifest is not superseded.
