# P4–P6 writing-profile builders

These are proposed writing-based structures, not reproductions of
preference-supervised ICAI or demonstrated predictors of researcher choices.
Only synthetic text and an offline extractor were used in this implementation.

- **P4** stores a flat list of atomic claims, each with its own source spans,
  explicit/inferred status, optional source-linked context, date, uncertainty,
  exceptions and conflict references.
- **P5** stores conditional rules: under a supported condition, prefer an action,
  with an alternative and counterconditions only when supported. It cannot infer
  a rejected alternative from its absence. Missing alternatives remain null.
- **P6** groups atomic principles under the six decision points already defined
  by `autoresearch/research/decisions.py`: candidate selection, evidence
  collection, result acceptance, direction persistence, result interpretation
  and write-up claims. It changes neither that loop nor its decision meanings.

The module exposes `build_p4`, `build_p5`, `build_p6`,
`registration_metadata()` and the explicit `register_principle_builders()` hook.
There are no import-time registry writes. P6's prompt specification includes the
SHA256 of the existing decision-definition file; the fixture index records it
explicitly. No Role 06 helper is imported. The shared registry/renderer remains
owned by infrastructure; the existing integration-audit owner must verify that
rich fields reach the actual consumer before live interpretation.

A claim's kind is personal preference, empirical belief or source report. A
researcher's factual assertion is not independently verified environment truth.
The format therefore rejects a `verified_fact` label and numeric utility weights
or confidence. Uncertainty labels describe the source/extraction status, not
measured reliability. Unsupported context and dates remain null. Dates must
occur in a linked quotation; no chronology is inferred from document metadata.

Both evidence policies are supported. Under `explicit-only`, any inferred
active or rejected claim makes the output invalid. Under `marked-inference`,
inference must stay marked. Conditions, exceptions and alternatives need the
same exact-span evidence as the principal claim. Conflicting claims remain
separate with references; there is no automatic resolution or pruning. Rejected
candidates retain their complete original object and a reason. IDs must be
unique across active and rejected records.

Only approved document segments enter extraction. Source offsets refer to the
original string's Unicode characters, with an exclusive end offset. Other
metadata is excluded because the common source manifest hashes content, not
arbitrary metadata or permission records. The runtime must also pin the full
approved bundle, including permitted spans. Quote matching proves structural
source linkage; it does not prove semantic entailment, correct classification,
or that the model found every relevant passage.

The common renderer receives the entire JSON. No context, source, uncertainty,
exception, rejected candidate or fixed hierarchy key is dropped to fit.
512/2048/8192 caps are conservative UTF-8 byte bounds, not measured token counts.
A profile that cannot fit remains an explicit cap failure. Empty, invalid and
unavailable outputs remain visible. Extraction makes one attempt without repair
retries or unsupported provider seed parameters. Request/response hashes and
unknown cost status are recorded; the assigned transport owns measured tokens
and dollars. No live calls were authorized or performed for these fixtures.

Checks:

```sh
python3 -m unittest tests.test_overnight_profiles_principles
python3 -m unittest discover -s tests -t .
```

Next dependency: an exact coordinator job lease and approved source bundle.
Local tests and self-review are not an independent consumer audit or a fidelity
result. Graph expansion, reflection and pruning remain unimplemented ablations
that require a declared development hypothesis and parent artifact IDs.

Settings correction: only `temperature` and `max_tokens` are supported in
`extractor_settings`. Unknown keys, including `top_p`, `seed` and `reasoning`,
are rejected before calling the extractor. Missing supported keys use explicit
defaults (`0.0`, `2048`), pinned in the versioned prompt specification and
recorded as `fit_usage.effective_extractor_settings`. Reasoning stays in the
pinned backend identity. The builder does not mutate its config copy; shared
runner normalization remains an infrastructure responsibility. Older fixtures
retain their original implementation and prompt hashes.

Quote-only protocol revision: new extraction prompts request exact source entries
`{document_id, quote}`. Models no longer calculate character offsets. The shared
versioned resolver derives `start` and `end` only for one exact occurrence inside
permitted ranges. It rejects missing, forbidden or ambiguous quotations and any
model-supplied offset fields. There is no fuzzy matching or text normalization.
The existing strict output validator then checks the resolved artifact.

The raw response SHA256, resolver version and resolution records remain in
`fit_usage`, including explicit failure diagnostics. Resolution does not rewrite
old artifacts or retroactively turn failed jobs into successes. Raw response
hashes and source hashes allow the transformation to be audited; they still do
not establish semantic entailment or correct explicit/inferred classification.
These prompts and their shared-resolver dependency have new hashes. Synthetic
checks cover Unicode prefixes, absent/ambiguous/forbidden quotes, no repair of old
offsets, raw-response preservation and exactly one extractor attempt.
