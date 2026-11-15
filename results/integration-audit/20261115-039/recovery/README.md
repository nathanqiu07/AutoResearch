This is an additive recovery package for the frozen original audit039. It does
not change that reader, report, inventory or safe manifest.

The 337 logical inputs resolve to 210 already retained owner files, 90 narrowly
preserved runtime-source members and 13 narrowly preserved publication/review
records. The 210 retained files serve 234 logical references because 24 executed
runner-source objects share bytes with retained publication `runner_source`
members. All 210 files passed exact SHA256 and size checks before and after
preparation, and again during recovered replay. No native `.eval` member or
unindexed private sibling was opened.

`runtime-source-gap.tar` is a public code-only archive containing exactly the 90
missing source files. Its SHA256 is
`e4c1476a3283894e04e4db8de42bf0ee5aebaf783d149402c06fc86a2fe96a6b`.
The 13 original publication/review records remain in the separate ignored private
archive `downstream05-audit039-publication-gap-v1.tar.gz`, SHA256
`b05776948990821e627b4c902f505ad9a36fd86132b67999de2881c431faa492`.
The private archive is 0600 under a 0700 directory; it must not be copied into a
public package. `preparation-01/` records both exact inventories and receipts.
The full existing owner archive is reused, not duplicated.

`reproduce_recovered.py` is generated additively from the exact frozen original
reader. `reader-change-proof.json` records six precise replacements: description,
input import/CLI, byte access and a separate recovery receipt. Reversing those
replacements reproduces the original reader hash exactly. All original checking
logic, assertions, expected artifact hashes and report fields remain unchanged.
The input adapter checks the supplied map against the pinned original inventory,
checks safe paths, verifies bytes at access and rechecks after completion. It
has no Git, subprocess, network or original temporary-path fallback.

Eleven synthetic controls pass, including wrong metadata/archive/file hashes,
missing and unmapped inputs, traversal, symlinks, incomplete access, and input
changes after reading. The actual recovered replay ran with process/socket
operations denied by a Python audit hook. It passed all 1,316 original checks.
The inventory is byte-identical. Every substantive report field and ordered array
is exact; only `argv` and the actual `reader_sha256` differ. No assertion-order
normalization was needed. The separate recovery receipt states which byte stores
were read.

To replay, supply existing paths to the retained payload and private gap archive;
do not rerun preparation or extract/copy the full owner archive:

```sh
ORIGINAL=/path/to/frozen-audit039
RECOVERY=/path/to/this-recovery-package
RETAINED=/path/to/existing-owner-archive/payload
PRIVATE_GAP=/path/to/private/downstream05-audit039-publication-gap-v1.tar.gz
REPLAY=/fresh/metadata-only/recovered039

python3 -I -B "$RECOVERY/reproduce_recovered.py" \
  --input-map "$RECOVERY/preparation-01/recovered-input-map.json" \
  --input-map-sha256 1c4cad7f68896c5dd9afc2b88bdf9f509d005a2343df395a1647a88964996dd3 \
  --inventory "$ORIGINAL/run-03/input-inventory.json" \
  --retained-root "$RETAINED" \
  --source-archive "$RECOVERY/runtime-source-gap.tar" \
  --publication-archive "$PRIVATE_GAP" \
  --out "$REPLAY"

python3 -I -B "$RECOVERY/compare_recovery.py" \
  --original-report "$ORIGINAL/run-03/report.json" \
  --recovered-report "$REPLAY/report.json" \
  --original-inventory "$ORIGINAL/run-03/input-inventory.json" \
  --recovered-inventory "$REPLAY/input-inventory.json" \
  --changes "$RECOVERY/reader-change-proof.json" \
  --portable-reader "$RECOVERY/reproduce_recovered.py" \
  --out /fresh/metadata-only/comparison039.json
```

The exact audited command with process/socket denial is preserved in
`replay-01.invocation.json`. `map_inputs.py` and the first `MAP_MANIFEST.json`
describe the initial metadata-only gap assessment; preparation/replay evidence is
separate. The preparation command is the historical local creation record, not a
required replay step.

Recorded commit/path identities remain historical labels bound to byte hashes.
This recovers exact saved-input checks, not original Git history, an installed
environment, current provider pricing or authenticated requests. It excludes the
later judging repair and the unarchived Inspect normalizer implementation.

Publish only `SAFE_PACKAGE_MANIFEST.json`'s explicit entries and that manifest
itself. No private publication records or full owner archive belong in this
public package. Original039 independent review and additive recovery review are
separate evidence records.
