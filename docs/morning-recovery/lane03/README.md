# Lane03: exact-source Petri controls

`scripts/gio_recovery/context_controls.py` creates three
`gio-auditor-context-v1` inputs for the lane01 morning preparer:

- `generic`: authored, nonpersonal scenario guidance; no source text or researcher
  identity in the model-facing context.
- `raw`: every approved character of the selected source records, including late
  passages, duplicates and permitted whitespace. Source extent is recorded per
  document; a released excerpt must not be described as a full article. Overflow
  fails instead of clipping.
- `retrieved`: Unicode BM25 against a frozen scenario query, selecting whole
  approved paragraphs. Ties use source ID and offset. Every omitted interval and
  rejected passage is recorded. Oversized paragraphs are skipped, never sliced.

All conditions pin the same original lane02 bundle **file bytes**, distinct from
its internal canonical JSON digest. The loader verifies both digests, each source
text hash, fit role, author attribution and permitted spans. Uncovered characters
must be whitespace; retaining those separators preserves exact released text.
Only the selected researcher's records enter sourced conditions. The enriched
morning protocol instead retains explicit permission gaps: third-party quotations
excluded by the source owner never enter the auditor context. Author/team caveats
accompany selected writing once per source, inside the counted context budget.

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

## Enriched morning source condition v2

V1 artifacts remain frozen. V2 uses the same full-raw and whole-paragraph BM25
algorithms against the new lane02 bundle, with the same frozen scenario query.
The source loader now accepts `approved_morning_petri_public_original` only with
`fit_scope=morning_petri_only` and the exact new-source protocol. This approval
does not turn newly retrieved public sources into old held-out benchmark inputs.

Neel's two source posts contain 32,879 UTF-8 bytes before context framing, so v2
explicitly sets `--raw-max-bytes 65536`. Retrieval retains its 4,096-byte cap.
Chris's collaborative section has a 122-character third-party quotation outside
permitted spans. Coverage separates these **unapproved** characters from approved
characters **omitted by retrieval**. Raw includes every approved character.
AI coauthorship and collective authorship are visible to the auditor; neither is
silently presented as individual testimony. These changes carry generator version
`petri-context-controls-v2`; they do not change the matched Petri scenario or models.
