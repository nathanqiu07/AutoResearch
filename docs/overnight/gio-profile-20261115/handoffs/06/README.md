# P1–P3 writing-profile builders

These are proposed document-to-profile methods. Offline checks verify format and
source plumbing; they do not establish researcher fidelity or research utility.
No live model call or researcher source was used to implement this slice.

- **P1** compresses approved documents into a plain summary, with provenance for
  each segment. It imposes no research-taste ontology. Role 05 should reuse its
  exact frozen content for the memory-summary control, rather than extracting it again.
- **P2** summarizes for a fixed research-task family: questions, experiments,
  explanations, evidence, debugging, stopping and communication. It never sees an
  evaluation context or option set.
- **P3** fills ten fixed research-choice questions from documents. The source was
  the proposed, unvalidated framework in chat
  `01a1de1e-34f7-7fe2-8676-cdba849cac31`, as supplied by the coordinator. This is a
  writing-based adaptation, not a team-agreed or empirically validated questionnaire.
  Every question remains present; unsupported answers are explicitly unknown.

The module exposes `build_p1`, `build_p2`, `build_p3`, `registration_metadata()`
and the explicit `register_summary_builders()` hook. It does not edit shared
registry code or register at import time. Method IDs are `P1`, `P2`, `P3`.

Config requires the common source allowlist and `evidence_policy` equal to
`explicit-only` or `marked-inference`. Inference in an explicit-only output makes
that output invalid; it is not silently discarded. Source spans use original
Unicode-character offsets, with exact substring verification. When documents
provide `permitted_spans`, only their text reaches extraction. Other document
metadata is excluded because the common source hash covers content, not arbitrary
metadata. Dates outside approved text therefore remain unknown.

The whole generated JSON is passed through the common renderer. No paraphrase,
condition, kind, date, question or source link is stripped to fit a cap. The
common wrapper enforces the conservative UTF-8 byte bound; this is not a measured
token count. Some fixed-schema/cap combinations can be infeasible. Empty,
unavailable, malformed and over-cap results remain distinct. Extraction makes
one call, without repair retries or unsupported seed parameters; a replicate ID
is not a guaranteed provider random seed.

Request and response SHA256 values are recorded in `fit_usage` alongside unknown
cost status. The assigned runner/transport owns measured tokens and dollars.
Required transport call arguments are `system`, `temperature` and `max_tokens`;
backend-specific reasoning and identity must be enforced by the injected adapter.

Validation proves structural source linkage only. A correct quotation does not
prove it entails a generated claim or condition. An extractor's explicit/inferred
classification is not independently validated truth. These limits matter when
interpreting any later fidelity result.

Checks:

```sh
python3 -m unittest tests.test_overnight_profiles_summary
python3 -m unittest discover -s tests -t .
```

Ruling: use the supplied ten-question framework as one fixed new candidate,
while retaining its proposed/unvalidated status. A poor questionnaire could hurt
P3; that is a comparison result, not evidence that richer schemas are better.
Ruling: keep metadata outside extraction unless covered by the approved text;
this sacrifices external date context to avoid an unpinned information channel.
The coordinator/audit owner provides independent review; this implementation's
local review and synthetic tests alone are not an independent audit.

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
