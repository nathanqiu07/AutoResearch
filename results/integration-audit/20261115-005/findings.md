# Synthetic source-boundary audit

The legacy raw-history helper does not enforce a document-level approved-source boundary. **If its researcher directory contains both approved and withheld corpus text, the withheld text can enter the proposer prompt.** This was reproduced using synthetic files only. It does not establish leakage in any actual experiment.

Source commit: `0ebcf7b19bacca64c1bd22a2c4383f39edf889d8`. The complete Python source hash map, input hashes, command arguments, and unchanged checks are in `run-01/report.json`. The audited `autoresearch/` files were clean and remained unchanged during the probe.

## What was exercised

- Actual `autoresearch.research.advisor.history_text`, with a synthetic researcher directory and the default 8,000-character limit.
- Actual `Proposer.propose`, receiving that returned history, with a recording-only transport that returns a fixed empty JSON list. The exact constructed request is retained in `run-01/recorded_proposer_request.json`; no model was called.
- A control directory that contains only approved corpus text.
- A 120-character limit with the withheld document sorted first.
- Existing `timesplit.docs_before`, for a contrast using the same synthetic dates.

The full CLI was not executed. Its wiring was inspected in source: `autoresearch/cli.py:318-324` obtains `history_text(researcher.root, max_chars=...)` for prompt mode and passes it to `Proposer(history=...)`.

## Observations

1. The mixed-corpus helper output contains both `SYNTHETIC_APPROVED_FIT_DOC_SENTINEL_02` and `SYNTHETIC_WITHHELD_DOC_SENTINEL_02`. The actual captured proposer request also contains both.
2. A synthetic source manifest declares only the first document eligible, but the helper does not open it and has no manifest parameter. This manifest is an audit fixture, not a claimed legacy production contract.
3. The synthetic documents have dates on opposite sides of a declared cutoff. `history_text` does not inspect those dates. The existing `timesplit.docs_before` reference excludes the later synthetic document; it is a separate helper and is not used by this raw-history path.
4. The named synthetic `heldout_timesplit.jsonl` file is not included. The helper's filename exclusion works for that pair file; it does not establish isolation of the underlying corpus documents.
5. An approved-only directory excludes the withheld sentinel. Thus a caller that materializes a strictly eligible source view can impose the boundary outside this helper.
6. A 120-character cap retains the withheld sentinel when that document sorts first, while excluding the approved sentinel. The helper still opens both documents before applying truncation. Character truncation limits returned text; it is not an access or eligibility boundary.

The script exited 0 with 12 reproduction assertions satisfied. These assertions confirm the observed behavior, including the boundary failure; they are **not** 12 passing source-isolation tests. No claim about model quality, downstream decisions, or live experiment contamination is supported.

## Concern for forthcoming raw/retrieval controls

Do not pass an unscreened researcher root to this helper and treat the result as an approved-source control. Establish one explicit eligible-source set before selecting raw text or building/searching a retrieval index. Both controls should consume the same permitted source view, with their context limits and selection policy recorded. Retrieval filtering must occur before indexing or searching inaccessible documents, not merely after selected chunks have been returned.

At the boundary, retain source IDs and content hashes plus the exact emitted text/chunks. Reject missing or inconsistent eligibility metadata. Add synthetic sentinels for withheld documents and assert they are absent from both constructed prompts and unauthorized read paths. A directory that is already restricted to approved sources can be a short-term mechanism; directory membership alone should not silently substitute for the declared experimental source contract.

Gio/Track A can supply the eligible-source contract and additive audit fixtures for the new controls. Changes to legacy `advisor.py`, its CLI wiring, or the research-loop consumer should be coordinated with the owning research-loop/WS D agent. This audit makes no production change and does not expand authorization to read restricted materials.

## Reproduce

Run `reproduce.py` with `--source-root` pointing at the audited checkout and `--out` naming a **new** directory. The original exact invocation and return code are in `invocation.json`; output is in `stdout.txt` and `stderr.txt`. The script refuses to reuse an output directory and creates all researcher fixtures inside it.

Artifacts:

- `reproduce.py`: standalone offline probe.
- `invocation.json`, `stdout.txt`, `stderr.txt`: original execution record.
- `run-01/report.json`: source/input hashes, checks, observations, and limits.
- `run-01/recorded_proposer_request.json`: actual captured request, synthetic content only.
- `run-01/full_history.txt`, `run-01/allowlisted_history.txt`, `run-01/truncated_history.txt`: exact helper outputs.
- `run-01/dated_reference.json`: output of the existing date-filtered helper.
- `run-01/synthetic_researchers/`: retained synthetic input files.

No real researcher corpus, target, labels, final files, or collector restricted store was opened. No production model, inference setting, prompt, threshold, or source file was changed. No paid call occurred.
