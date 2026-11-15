Audit 037 checks the released full sparse index's remaining personalized
consumer bindings and reconciles its membership with frozen audits 033–035.
See FINDINGS.md and final/report.json for results and limits. The final reader
passes 6,336 checks over 2,222 private inputs; its eleven small synthetic controls
also pass. The audit makes zero model calls.

The exact label-free entrypoint SHA256 is
`9aeea5b0c4fb9668df1d36c548e681c1c5e180e75df74f9475f75b2f08737e3a`,
released at role04 commit `8fb6246e311dac1f885dc4b04bd9384aecc858c2`. The consumer
and runner source remains frozen at
`f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`. `EVIDENCE_PINS.json` identifies the
helper, prior metadata reports and source archive. Owner code is read as bytes
or AST constants and is never imported. Only the pinned independent 033 helper
is imported.

Use Python 3.9+ and the standard library. With the approved original input tree,
run the following with a fresh output directory:

```sh
PACKAGE=/path/to/full-sparse-execution-37
python3 -I -B "$PACKAGE/read_full_sparse.py" \
  --evidence-root "$PACKAGE" \
  --index /private/tmp/gio-profile-20261115-evaluator/released/full-sparse-completion-provenance-index-v1.json \
  --data-root /private/tmp --recorded-data-root /private/tmp \
  --out /fresh/metadata-only/replay-037
python3 -I -B "$PACKAGE/test_reader_guards.py" -v
```

To relocate originals while retaining their logical paths, change `--data-root`
only. The reader also supports an exact private archive extraction and standard
033/034 preservation receipt: replace the two data-root options with
`--archive-root /private/extracted --preservation /path/to/receipt.json`.
Keep `--index` at its recorded logical path. Archive replay was not run in this
stage; full private preservation is a separate packaging step.

`final.invocation.json` and its stdout/stderr record the exact final command and
exit status. Compare repeated reports after removing only `argv`; the input
inventory should remain byte-identical. `run-01` preserves an audit setup
failure, while `run-02` and `run-03` preserve passing intermediate candidates.
`SETUP_HISTORY.json` distinguishes these from any study failure.

`safe-manifest.json` is the exact public allowlist; include its listed files plus
the manifest itself. It contains only code, published-source bytes, metadata,
hashes and synthetic test logs. The 2,222 private JSON inputs, totaling
37,661,894 bytes, are listed in `final/input-inventory.json` and must not be
copied into a public package. No source/profile/prompt/response prose, labels,
scorer outputs, keys or SQLite files are included.
