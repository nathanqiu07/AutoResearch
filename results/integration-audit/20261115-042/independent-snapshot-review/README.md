This is a bounded metadata cross-check of exactly three released, closed profile204 snapshots. It found no mismatch across 45 checks. It is not a fresh execution, control-binding or scoring audit.

The snapshots agree on 204 unique complete jobs in four batches, 672 complete request slots and 672 unique complete ledger reservations. Request SHA256 identities match as exact multisets; the associated model/reasoning metadata matches too. Every job's reported usage equals the sum of its matched reservation amounts. Job, batch, index, supervisor and ledger totals all equal **124,590,125 nanodollars ($0.124590125)**.

The closed snapshot records zero pending rows, uncertain rows and retained holds. Its first numeric reservation column sums to 3,207,595,375; that historical amount is not added to known spend or treated as a current hold. All rows are complete. Positional row meanings are documented in the report from this fixed snapshot layout and corroborating totals; no external ledger schema or logical-snapshot-hash recipe was consulted.

The original finite-plan denominator remains visible: 205 candidate jobs and 686 requests, with one whole job and 14 requests excluded, leaving 204/672. Excluded jobs and collision request identities are absent from this continuation. Earlier uncertain outcomes, holds, sparse/richer coverage and alias overlap are outside this three-file check and are not reclassified. The 672 is this continuation's request count, not a new independent-judgment or quality claim.

Only the three explicit inputs in `report.json` were read. Each raw hash was verified before parsing and again after checking. No referenced profile, prediction, trace, source, policy or SQLite path was followed. No labels, scoring, live processes, network/model calls or original raw requests were accessed. Equality of recorded request digests is not independent reconstruction of prompt/settings or authentication of physical provider traffic. Closure and diagnostic event claims were checked as saved metadata.

`invocation.json` preserves the exact command and exit status. The standard-library reader accepts relocated paths to the same pinned bytes:

```sh
python3 -I -B review_snapshots.py \
  --index /path/to/completion-provenance-index.json \
  --supervisor /path/to/supervisor-terminal.json \
  --ledger /path/to/profile204-closed-ledger-snapshot-v1.json \
  --out /path/to/fresh-metadata-report.json
```

Publish only the six files listed in `safe-manifest.json` plus the manifest itself. No input snapshots or raw prediction/source text are included.
