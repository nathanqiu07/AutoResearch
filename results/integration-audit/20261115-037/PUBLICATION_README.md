# Audit 037 publication and private recovery

This is the current publication note. All 43 files listed by the original
`safe-manifest.json`, including `README.md` and `FINAL_VERIFICATION.json`, remain
unchanged historical stage evidence. The additions below complete private preservation and
archive replay without rewriting those files. `checksums.json` covers the full
current public package, excluding itself.

Exactly 2,222 named private JSON inputs, totaling 37,661,894 uncompressed bytes,
were preserved in `full-sparse-execution-20261115-v1.tar.gz`. The archive is
7,359,490 bytes, SHA256
`e5bff245a1dc5da80650fce47347876d9ad213e74ef3f53d305850ebaa23ec9d`.
It resides only in the ignored audit private directory. The directory is 0700;
archive and unchanged receipt/reader/helper/preserver/extractor recovery copies
are 0600. Each original and archive member passed its expected hash/size checks;
archive members are regular relative files. No original input drift was found.

A fresh private extraction passes all 6,336 reader checks. Its input inventory is
byte-identical to the frozen inventory. Every report field and array matches
exactly except `argv` and the **order** of `checks`. The frozen reader traverses a
job-ID set while recording some assertions, so process hash randomization can
change that sequence. `ordering-evidence.json` pins the source lines and shows
that only the 364-entry `034_row_and_trace_hash_overlap:` family moved; all other
check positions stayed exact. The exact multiset of check entries, including duplicate
multiplicity, matches. This ordering difference is recorded explicitly; the
package does not claim equality after removing only `argv`.

`compare_replay.py` makes that narrow comparison portable. It requires explicit
`--allow-check-order`; every other field and array remains ordered and exact.
See `portable-replay-comparison.json`, the earlier
`private-replay-comparison.json`, and their invocation/stdout/stderr records.
Root's separate fresh archive extraction and full replay also passed all 6,336
checks. Its inventory is byte-identical, and its independent multiset comparison
confirms that all 364 moved positions belong only to the same assertion family;
every other field and array is exact. See `root-verification.json` and
`root-replay-comparison.json`. Earlier preservation-step records that say root
replay was pending retain their original meaning at that step.

The required repository suite also passed: 677 tests run, 675 passed and two
skipped, exit 0, in 26.617 seconds at commit
`51a20999dc189c9671f3f08e6d3188c2b0441ede`. This separate repository check is
recorded in `repository-tests.json` and its hash-verified log; the audited study
runtime remains the pinned f6 commit.

To repeat with a fresh private extraction and metadata-only output:

```sh
PACKAGE=/path/to/results/integration-audit/20261115-037
ARCHIVE=/path/to/private/full-sparse-execution-20261115-v1.tar.gz
PRIVATE_REPLAY=/fresh/private/extracted-037
REPLAY=/fresh/metadata-only/replay-037

python3 -I -B "$PACKAGE/extract_private_inputs.py" \
  --archive "$ARCHIVE" \
  --preservation "$PACKAGE/private-preservation.json" \
  --preservation-sha256 a507a9c9fb169155d6d2f3bdd685bb081cd41ebc8bff5bb5fcfc34b26c713771 \
  --out "$PRIVATE_REPLAY"
python3 -I -B "$PACKAGE/read_full_sparse.py" \
  --evidence-root "$PACKAGE" \
  --index /private/tmp/gio-profile-20261115-evaluator/released/full-sparse-completion-provenance-index-v1.json \
  --archive-root "$PRIVATE_REPLAY" \
  --preservation "$PACKAGE/private-preservation.json" \
  --out "$REPLAY"
python3 -I -B "$PACKAGE/compare_replay.py" \
  --left "$PACKAGE/final/report.json" --right "$REPLAY/report.json" \
  --left-inventory "$PACKAGE/final/input-inventory.json" \
  --right-inventory "$REPLAY/input-inventory.json" \
  --allow-check-order --out /fresh/metadata-only/comparison-037.json
```

The preservation and extraction scripts are unchanged portable tools from 034.
`preservation.invocation.json` saves the exact archive-creation command, including
the frozen inventory hash, expected count and explicit source-root mapping.
All destinations are new/exclusive. Keep extracted private inputs outside any
public result package. Only metadata/code are public; no raw profiles, prompts,
source passages, response prose, labels, keys or active ledgers are copied here.

The bounded independent review in `independent-review/` found no blocker and
passed 1,980 metadata assertions. It independently read only the released
label-free index, without a full reader rerun or private trace reads. Actual
file/trace bindings are established by the frozen reader and both preserved
full replays. One phrase in the unchanged review calls prior035 checks
“extraction/quote validation”; the supported scope is narrower: audit035
verifies saved extraction outcomes, record/source/profile bindings and
accounting. It is not an independent actual quote-policy audit, and037 does
not perform such an audit.
