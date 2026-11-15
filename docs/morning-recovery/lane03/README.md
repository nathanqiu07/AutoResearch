# Lane03: exact-source Petri controls

`scripts/gio_recovery/context_controls.py` creates three
`gio-auditor-context-v1` inputs for the lane01 morning preparer:

- `generic`: authored, nonpersonal scenario guidance; no source text or researcher
  identity in the model-facing context.
- `raw`: every character of the researcher's approved released source records,
  including late passages, duplicates and whitespace. These are curated excerpts,
  **not complete original web articles**. Overflow fails instead of clipping.
- `retrieved`: Unicode BM25 against a frozen scenario query, selecting whole
  approved paragraphs. Ties use source ID and offset. Every omitted interval and
  rejected passage is recorded. Oversized paragraphs are skipped, never sliced.

All conditions pin the same original lane02 bundle **file bytes**, distinct from
its internal canonical JSON digest. The loader verifies both digests, each source
text hash, fit role, author attribution and permitted spans. Uncovered characters
must be whitespace; retaining those separators preserves exact released text.
Only the selected researcher's records enter sourced conditions.

```bash
python3 scripts/gio_recovery/context_controls.py \
  --bundle SOURCE_BUNDLE.json --bundle-sha256 EXACT_FILE_SHA256 \
  --researcher neel_nanda --query-file FROZEN_SCENARIO_SEED.txt \
  --implementation-commit CODE_COMMIT \
  --raw-max-bytes 32768 --retrieved-max-bytes 4096 \
  --out runs/morning-recovery/lane03/neel-controls-v1
```

Outputs contain source text and remain under ignored `runs/`. The command refuses
to overwrite its output directory. `CONTROL_RECEIPT.json` pins the emitted files
and records exact context UTF-8 bytes, characters, hashes and source coverage.
Token counts are unavailable until measured with a specified tokenizer/provider;
bytes must not be reported as tokens. The byte cap includes this producer's
instructions and JSON wrapper, but excludes the shared Petri prompt and other
messages. Raw and retrieved lengths intentionally differ; no hidden length match.

Pass the `.context.json` files directly to lane01's successor `prepare.py`.
It consumes **unescaped `model_facing_text`** and escapes braces once for Petri.
`auditor_template_suffix` is supplied only for direct native-template consumers;
passing it through lane01 would double-escape. Source provenance and coverage are
outside model-facing text. The shared scenario, model, tools, settings and target
opportunity remain lane01's responsibility.

Verification:

```bash
python3 -m unittest tests.test_gio_recovery_context_controls
python3 -m unittest discover -s tests -t .
```

These offline checks establish construction and exposure accounting. They do not
establish that the environment is valid, the profile improves research, or any
target behavior occurred. Actual Petri preparation, input isolation and outcomes
are separately verified by lanes01/07/09.
