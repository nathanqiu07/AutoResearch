# Common methodology bundle v2

These two compact profiles use the exact shared lane02 v2 source file, SHA256
`e32eb62546074ccc4bf5ccb6a4a7f2dbb92e0ac87891dba3b69b5dd60bb72f56`.
They are ready for the lane01 auditor-only adapter. No model calls were made.
No Petri outputs were reviewed while selecting or freezing these claims.
The v1 files remain unchanged.

The method and 2,048-byte content cap are unchanged at implementation commit
`55f7b790231d84a0514b0786f6c2c3bbc2f2de4c`. These are reviewer-authored paraphrases
of all nine candidate priorities supplied by lane02, packed in the supplied order.
This is deterministic compaction, not a new learned extraction result. Exact
quotes, allowed spans, source hashes, and provenance remain outside the content cap.
All nine claims fit whole; no claims were omitted or truncated.

| Researcher | Claims | Compact content bytes | Full auditor context bytes |
| --- | ---: | ---: | ---: |
| Neel | 5 | 1,081 | 1,677 |
| Chris | 4 | 1,091 | 1,687 |

The cap applies only to compact content. The fixed auditor preface and final
newline add 596 bytes. Both full contexts also happen to fit within 2,048 bytes.
This does not include lane01's other shared setup and prompt text.

Neel's claims concern evidence for and against hypotheses, simple alternative
explanations, information gain per time, early failure checks, and exploration of
anomalies. The speed claim retains the exception for slow, conclusive experiments
during distillation. His process essay credits Gemini 2.5 Pro as coauthor; these
are stated methodological ideals, not proof of his behavior in every setting.

Chris's circuit claims remain attributed reports from a collaborative essay,
whose text he primarily wrote. They describe small tractable mechanisms,
falsifiable intervention predictions, and the tradeoff between rigor and scope.
The last item reports a rough personal note's self-critique question. None is
presented as a uniquely personal preference or measured behavior. The excluded
Ian Goodfellow quotation is not used.

The two source collections have different lengths and coverage. These sources
support scientific values but do not establish distinct research taste. Applying
them to Petri is an inference to test. This new public-fit condition does not
reopen the old final test or establish an old heldout result.

Use `ARTIFACT_INDEX.json` for absolute context paths, file hashes, full exposure
counts, and profile IDs. `INPUT_FREEZE.json` records exact claim input hashes,
source candidate metadata, limits, and the pre-outcome input freeze time. The
context's `source_bundle_digest` is the exact file-byte digest. Its separately
named semantic digest canonicalizes the full JSON including the embedded digest
field, so it differs from lane02's embedded digest that excludes that field.

Both contexts passed the actual lane01 `load_context` function, exact source and
profile file checks, and escaped-template roundtrips. The targeted suite passed
12 tests; the required repository suite ran 941 tests, with 2 skipped, and passed.
The full suite reports existing unclosed-file ResourceWarnings. Logs and per-profile
consumer validation receipts are saved here. Adapter checks establish a usable
input, not successful live Petri execution or improved environment quality.
