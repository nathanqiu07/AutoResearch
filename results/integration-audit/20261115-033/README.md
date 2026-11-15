# Actual saved-memory result references

All 84 explicit memory references resolve to 28 recorded, completed P1
predictions in two canonical jobs. The 28 rows contain 14 literal content groups,
each shown in two option orders. These references add no calls or independent
observations. Recorded conservative cost is $0.00254125 across the two jobs,
counted once; it is not an invoice or a live-ledger audit.

The independent reader passes 477 checks. Root reproduced every evidence field
from a newly preserved private archive; only recorded command-line arguments
differ. The input inventory is byte-identical. Full scope and limitations are in
[FINDINGS.md](FINDINGS.md), and the comparison is in
[root-comparison.json](root-comparison.json).

This closes audit 027's recorded-execution comparison gap for these released
memory references. It does not establish execution under memory job IDs,
automatic runner cache aliasing, provider-authenticated network requests,
stochastic equivalence, preference accuracy or research quality. The separately
prepared control/hybrid report remains a historical snapshot here; later actual
execution is a separate audit.

The ignored private archive contains exactly 76 named, hash-pinned JSON inputs;
its SHA256 is `eb4ce80c759602082f0ca396959c0c13b51b238604553bc48d5f4831ff8253a1`.
All members were verified and the original inputs rechecked unchanged. The
archive, receipt and reader have durable private copies with mode 0600 in a
mode 0700 directory. Preserve that directory separately when relocating this
worktree. Public evidence includes metadata and source code, with no raw source
text, profiles, predictions, credentials or private labels.

After safely extracting the verified archive, reproduce into a fresh directory:

```sh
python3 -I -B read_execution.py \
  --evidence-root /path/to/20261115-033 \
  --archive-root /path/to/private-extracted-inputs \
  --preservation /path/to/20261115-033/private-preservation.json \
  --out /path/to/fresh-output
```

`SAFE_PACKAGE_MANIFEST.json` preserves the producer's original safe-file list.
`checksums.json` covers the complete published package, including root additions,
except its own bytes. The audit made zero model calls and changed no runtime
models or settings.
