# Audit 034: completed control execution and sparse reuse

The frozen release records 234 canonical jobs, 364 completed prediction rows and
364 attempted calls: 308 matched-control rows plus 56 fixed-P1 hybrid rows. The
recorded prediction cost totals **$0.057470000 once**. The 112 sparse cap-alias
references reuse 56 of those rows in four jobs; their $0.00463625 is already in
that total. In this pinned release, the 168 richer alias candidates are proposed
and unregistered; this audit makes no claim about later adoption.

Release: `bfe6e209358fe1e896beb7d229b9cc30db7957e7`. Runtime semantics:
`f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`. The independent reader verifies
source, item/order, profile/parent, backend/settings, packet, request trace and
terminal result bindings. All **4,572 checks pass**. The separate bounded review
in `independent-review/` found no blocker; it did not repeat the full reader.

The archive replay also passes all 4,572 checks. Its report equals the original
`run-03/report.json` in every field except `argv`, and its inventory is
byte-identical. See `private-replay-comparison.json`. Root separately extracted
the archive and repeated the full reader: all 4,572 checks agree, only `argv`
differs, and the inventory is byte-identical. See `root-replay-comparison.json`.

`SAFE_PACKAGE_MANIFEST.json` is the unchanged original 35-file allowlist.
`checksums.json` covers the full current public package, excluding itself. The
public additions contain only code, metadata, hashes, scalar checks and synthetic
controls. Original staging evidence and audits 027/033 were not changed.

## Private preservation

Exactly 2,609 approved private JSON inputs (80,767,307 uncompressed bytes) were
preserved as regular relative archive members. No extra inputs were discovered.
The archive is `control-execution-20261115-v1.tar.gz`, 18,242,346 bytes, SHA256
`add5dacfe4f2c3f7b3a38b988fd6afbecdf8e8d734efb1a3b9dc920b16de1dc2`.
It remains outside this package in the ignored audit private directory. The
directory is mode 0700; the archive and its receipt, reader, helper, preserver and
extractor recovery copies are mode 0600. The originals and all archive members
were checked against expected hashes and sizes. `private-preservation.json`
contains only the inventory, mapping and verification metadata.

The inventory includes 12 public source/metadata objects in addition to the
2,609 private inputs. The private archive contains only the latter; the public
source snapshot remains in this package. Raw profiles, prompts, responses and
source passages are never public replay outputs.

## Portable replay

Use Python 3.9 or newer and only the standard library. Supply the public package,
the preserved private archive, and fresh private/output paths. These commands
do not import project code or invoke a model. Destinations must not exist.

```sh
PACKAGE=/path/to/results/integration-audit/20261115-034
ARCHIVE=/path/to/private/control-execution-20261115-v1.tar.gz
PRIVATE_REPLAY=/fresh/private/extracted-034
PUBLIC_REPLAY=/fresh/metadata-only/replay-034

python3 -I -B "$PACKAGE/extract_private_inputs.py" \
  --archive "$ARCHIVE" \
  --preservation "$PACKAGE/private-preservation.json" \
  --preservation-sha256 e582b23a5a0c6de68c54e2a8e3760ec0aca2a22734fc151c8dff5a1eb57f7c4d \
  --out "$PRIVATE_REPLAY"

python3 -I -B "$PACKAGE/read_control_execution.py" \
  --evidence-root "$PACKAGE" \
  --archive-root "$PRIVATE_REPLAY" \
  --preservation "$PACKAGE/private-preservation.json" \
  --out "$PUBLIC_REPLAY"
```

Compare the two parsed reports after removing **only** the top-level `argv`
field, and compare the two `input-inventory.json` files byte for byte. Recorded
paths stay unchanged in the inventory; the receipt explicitly remaps them to
verified archive members. Exact executed arguments, status, stdout and stderr
are saved as `preservation.*`, `private-extraction.*` and `private-replay.*`.

To preserve the same approved inputs at another location, use
`preserve_private_inputs.py --inventory "$PACKAGE/run-03/input-inventory.json"
--inventory-sha256 39eb0975a0d97205c978fb0763111e02e57c458386bb3e235888a5a9a0eeec3e
--expected-count 2609 --data-root /relocated/original-inputs
--recorded-data-root /private/tmp --archive /existing-mode0700-private/new.tar.gz
--receipt /existing-mode0700-private/new.receipt.json`. The directory structure
under the relocated root must match the recorded root. Archive and receipt
creation are exclusive. Six saved synthetic controls cover matching input,
changed input, wrong inventory pin, and archive/extraction overwrite refusal.

## Claim limits

This establishes consistency of the released saved artifacts. It does not
authenticate provider origin, inspect a live ledger or invoice, establish model
quality, recompute scores, or access private evaluator labels. The prediction
cost excludes original parent extraction and embedding production. The 28
ordered items form 14 paired content groups; aliases add no independent
observations. The audit made **zero model calls**. Richer alias adoption and
execution under alternative cap job IDs are not established by sparse reuse.
