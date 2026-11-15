# Phase1 observation units for audit031

Signed by role: independent provenance reviewer (`/root/parallel_gap_audit`), 2026-11-15. This is a bounded reanalysis of the explicitly approved audit024 records. It reads no private labels or scoring data and makes no model calls.

**The 112 completed control rows cover 28 ordered decisions but only 14 exact context-and-option groups: seven per researcher.** Each group has two different released item IDs, one for each reversed option order. Each ordered decision appears once under each of four controls. Treating every row, or every ordered item ID, as an independent human judgment would be unsupported.

| Counted object | Neel Nanda | Chris Olah | Total |
| --- | ---: | ---: | ---: |
| Completed prediction rows, across four controls | 56 | 56 | 112 |
| Distinct released item IDs / ordered decisions | 14 | 14 | 28 |
| Exact context + option-content groups, ignoring order | 7 | 7 | 14 |
| Option-order variants per content group | 2 | 2 | 2 |
| Release-declared DEV source groups | 2 | 1 | 3 |
| Independently established human judgments | Unknown | Unknown | Unknown |

The first batch supplies 32 rows over eight ordered decisions/four content groups. The continuation supplies 80 rows over twenty ordered decisions/ten content groups. These batches have no overlapping method/researcher/ordered-decision cells; the fourteen content groups are also disjoint between batches. They use the same two researcher identities, rather than adding independent researchers.

The grouping is deliberately literal: SHA-256 of canonical JSON containing the exact context and a sorted multiset of exact option strings. It preserves duplicate option multiplicity and performs no Unicode, whitespace, case or semantic normalization. Grouping is scoped by researcher. All fourteen hashes are also distinct when the researcher field is excluded. In every group, both option orders have identical context and exact reversed option lists, with distinct item IDs. Each researcher has seven distinct context hashes. These observations show repeated presentations of the same released content, not independent human choices or semantic equivalence among different text.

The five allowed item fields are context, item ID, option-order ID, options and researcher ID. They contain no upstream human-judgment ID or item-to-DEV-source-group identifier. The releases' recorded counts of seven semantic targets per researcher agree with the literal content grouping. Their two/one DEV source-group counts are metadata only here: this audit does not reconstruct source-level clustering or establish independence between the seven groups. Distinct content hashes alone cannot rule out shared provenance or correlated judgments.

## Profile reuse

The three static controls—no profile, name only and raw evidence—use one frozen profile artifact per researcher. Those **six artifacts are each reused across fourteen ordered prediction rows**, accounting for 84 rows. Each appears in both prediction batches.

Lexical retrieval uses 28 distinct decision-bound profile IDs, one per ordered decision. Those artifacts contain only **ten distinct profile-content hashes**: three for Neel Nanda, reused in eight/four/two rows, and seven for Chris Olah, each reused in two rows. Each reversed-order pair has identical lexical profile content even though its profile IDs differ. This is another reason artifact counts do not measure independent information. Profile-content equality does not imply equality of full consumer prompts, execution settings or outcomes; the decision context is still part of the consumer input.

Profile IDs and content hashes are taken from the exact hash-pinned audit024 report, whose job identities and completed counts are cross-checked against the released index, packets and results. This subreview does not reread or export raw profile text.

## Justified reporting denominators

- Operational coverage: **112/112 completed planned control rows**, or 28/28 ordered decisions per control. This is execution coverage, not an accuracy result.
- A matched method comparison: **28 matched ordered decisions**, nested within **14 exact content groups**, seven per researcher. The four arms share the same items and must not be counted as four independent item samples.
- Option-order sensitivity: **14 matched order pairs per control**, seven per researcher. Reversing options is a repeated presentation of a content group, not another independently labeled judgment.
- Researcher coverage: **two researcher identities**. No population-level generalization or effective statistical sample size is established.
- Source/human-judgment independence: **unverified**. The recorded DEV grouping counts are insufficient for a defensible item-to-source dependence model.

No prediction choices, label correctness, scores, confidence intervals or significance tests were inspected or computed. The phase2 completion index and its observation units remain outside this phase1-only result.

## Evidence and reproduction

The reader follows only the 695-file hash-pinned audit024 allowlist, consuming 121 approved runtime files: the completion index, forty prediction packets, forty linked label-free releases and forty results. It reads result identity/status fields without using prediction choices. Every consumed file is checked against its approved hash and size. It verifies exact item hashes, selected IDs/order, complete coverage and repetition bindings; **635 checks pass with zero failures**.

The reader was run once against approved originals and once against audit024's already preserved private replay. Both runs exit 0; complete report bytes and input-inventory bytes are identical. This establishes relocation for these inputs without creating another raw-data copy. The public outputs contain hashes, structural counts, statuses and metadata only. Raw data remains in the original approved locations and audit024's existing private archive; do not package its `private-replay` tree.

Metadata dependencies already exist in public package `20261115-024`:

- `input-inventory.json`, SHA-256 `4d90e111d4f02772246f5e9c5806fbcde45d11dd24c2c9a071f054edaac5e8ea`.
- `run-03/report.json`, SHA-256 `188b1ca700bf34f2c48a1cc50330c4d0662fd59f896f8d52cd3e99a973fc1bfa`.

Run with Python 3.9 or later:

```sh
python3 -I -B reproduce.py \
  --inventory /path/to/20261115-024/input-inventory.json \
  --audit024-report /path/to/20261115-024/run-03/report.json \
  --data-root /path/to/extracted-private-control-archive \
  --out /path/to/fresh-output
```

Omit `--data-root` to use the approved original paths. The reader refuses a changed allowlist/report, unlisted input, hash/size mismatch, escaped relocated path or existing output directory. Exact invocations and logs are retained. `run-01/report.json` and `run-02-relocated/report.json` include hashed group membership, every row's matched identity, profile reuse, checks and explicit interpretation limits.
