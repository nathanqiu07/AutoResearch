# Role08 synthetic implementation handoff

P7 and P8 use the neutral-profile v1 callable: `(documents, config, extractor)`.
Integration calls `profiles_hypotheses.register_hypotheses_builders()` explicitly.
Importing the module has no registry side effect. Method IDs are `P7` and `P8`.
`registration_metadata()` provides callables, prompt versions and prompt hashes.
Only role01 changes the shared registry or package exports.

Use evidence policies `explicit-only` and `marked-inference`, the names already
used by P1–P3. Caps are 512, 2048 or 8192 **UTF-8 bytes**, not tokenizer counts.
Required common configuration and exact ID/content-hash allowlists are unchanged.
The builder accepts only `temperature` and `max_tokens` in `extractor_settings`;
it resolves omitted values to 0.0 and 2048 and records them in fit usage. Other
keys are rejected before any call. Provider-specific reasoning must be enforced
and recorded by the transport identity, never advertised as an ignored setting.
P7 needs `approved_peer_sources=True` and a bundle containing target and peer
evidence. Both families accept evaluator `permitted_spans` with `start`, `end`,
`text` and `speaker`. Speaker attribution is mandatory; missing spans cannot be
reconstructed from authorship. Offsets count Unicode characters, end exclusive.

Statements share the P1–P3 schema: `text`, `kind`, `evidence_status`, `conditions`,
`date`, `sources`; each source has `document_id`, `start`, `end`, `quote`.
P7 and P8 use only supplied attributed text. They do not fetch documents or read
an unrestricted source inventory. No evaluation answers or context enter builds.

P7 returns comparisons containing both target and peer statements. Positive
support on both sides is required. Missing evidence stays unsupported and cannot
become disagreement. Shared preferences stay shared. Sources with common content,
URL, document group, duplicate group or project group count as one support group;
a comparison with overlapping target and peer groups remains unsupported. This
conservative grouping is local to released sources and cannot inspect hidden
split groups. The evaluator's exact approved allowlist remains authoritative.

P8 retains hypotheses, null weights and relations. Incompatible evidence and
extraction uncertainty remain distinct from stated change. A stated change needs
its own explicit statement and supporting span. No recency weights or probabilities
are invented. Missing dates stay null; a non-null date must appear literally in
cited evidence. Explicit conditions must also appear in their evidence. Hypotheses
are sorted by ID; symmetric relation endpoints and citations use deterministic
ordering. There is one extraction call and no hidden consumer reasoning step.

An extraction failure is unavailable, an empty valid extraction is empty, missing
comparison support is unsupported, and malformed or prohibited output is invalid.
There is no repair call or fallback. The full oversized content is retained with
`invalid / personalization_cap_exceeded`; the common consumer rejects it. Removing
a conflicting hypothesis to fit a cap is not an automatic behavior.

## Verification and artifacts

Final code checkpoint: `d300e98e69006a827c68ee4da45663dfc67d132b`.
The 22 targeted synthetic tests pass. The required full suite passes 702 tests
with two skips. Existing ResourceWarnings remain. Compressed red-phase and
full-suite logs preserve the observed test evidence.

Independent review found that the first checkpoint silently ignored unsupported
extractor settings. Two test cases reproduced that failure; the final checkpoint
rejects unknown settings before a call and exposes resolved defaults. The older
`4da90970...` fixture remains preserved as superseded evidence. Use the final
`96ccb33e...` fixture for integration; implementation hashes intentionally differ.

Run the fixture generator from the repository root:

```sh
python3 docs/overnight/gio-profile-20261115/handoffs/08/build-fixture-001.py
```

It writes new content-addressed JSON files exclusively and verifies/reuses an
identical existing artifact without rewriting it.
The saved fixture uses the code checkpoint above, covers 12 method/policy/cap
cells, and performs no model-service calls. These are scripted responses that
test mechanics; they are not extraction quality or researcher preference results.
The fixture's short P7 comparison uses 489 bytes and fits all three caps. The
conflicting P8 profile uses 599 bytes, so its 512-byte cells remain invalid while
its 2048- and 8192-byte cells complete. A separate test shows a single P8 hypothesis
can fit 512 bytes. Infeasible cells remain present instead of being dropped.

Role05 receives a separate synthetic own/swapped/shared control artifact through
its file and content hashes. All three use the same JSON envelope and an explicit
whitespace-padding field for equal rendered UTF-8 byte length. Provenance stays
attached to the original speaker. These are fixture inputs, not production control
builders or validated live profiles. Tokenizer equality has not been established.

## Limits and next dependency

Exact spans and attribution establish source linkage only. They do not prove
semantic entailment, accurate classification as explicit, correct detection of
shared/different preferences, recognition of every conflict, or that a quoted
statement truly describes a change. Those judgments remain extractor outputs and
need source review. Local grouping cannot recover missing project relationships.
Input records, prompts, responses and source sets are hashed for audit; these
Python checks do not authenticate the evaluator or defend against a hostile
same-account caller.

No real researcher material, withheld documents, model keys, live models,
embeddings, final users, saved-profile audit implementation or shared registry
files were used or changed. Live development results remain unmeasured. Next steps
belong to the coordinator: integrate with role01, supply role04-approved fit/peer
bundles, and issue an explicit leased job if live evaluation is desired.
