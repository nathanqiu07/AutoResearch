# P7/P8 quote-only protocol v2

This is a new extraction version. It follows the coordinator's assigned protocol
change after the first P1 builds failed span validation. Role08 did not inspect
those real-source outputs. Old code, events and fixtures remain in Git unchanged;
no prior invalid artifact or live job has been repaired or relabeled.

The model now returns source objects containing exactly `document_id` and `quote`.
It does not calculate character offsets. The shared owner01 helper
`resolve_quote_sources(content, documents)` derives `start` and `end` only when an
exact quotation has one unique occurrence inside permitted spans. There is no
fuzzy matching. Missing and ambiguous quotes remain invalid, as do legacy source
objects containing offsets. Role08 did not implement or edit the shared helper.

The adopted helper code is `5c19ceee792b6a858edd1eba4f36b183d5fb09d0` from owner01.
Its contract file has SHA256
`7d400887f7738f109c3c35c5949c12d4055310ee2d1fa8903b6f9edfaa336f76` and exposes
`QUOTE_RESOLVER_VERSION = unique-exact-permitted-quote-v1`. The owner release
checkpoint is `cdd74454896003b55b6e564cae764edbb77c9508`, event
`handoffs/01/008-QUOTE_RESOLVER_READY.json`. The dependency entered this branch by
merging its direct owner lineage. Other incoming infrastructure files are exact
owner versions, not Role08 modifications.

P7/P8 still run their strict statement, source, attribution, evidence-policy and
target/peer validation **after** resolution. Missing attributed spans are not
treated as full-document permission by these builders. Shared preferences,
unsupported contrasts, contradictions, null dates and weights, and complete
oversized content remain preserved. The cap applies to the resolved artifact,
including computed offsets, not merely the shorter raw model output.

The callable signatures and explicit registration hook are unchanged:
`register_hypotheses_builders()`, methods `P7` and `P8`. New prompt versions are
`hypotheses-profile-v2-quote-only-p7` and
`hypotheses-profile-v2-quote-only-p8`. Prompt metadata includes the resolver version
and explicit lineage to the v1 prompts and code
`d300e98e69006a827c68ee4da45663dfc67d132b`.

Fit usage preserves the literal raw-response SHA256, the prior `response_sha256`
field for existing readers, resolver version and resolution records. Success
records identify quote hashes, source paths and computed Unicode indices. On
success, source paths address the raw parsed response before deterministic
ordering; `resolved_content_sha256` hashes the helper output before that ordering.
On
failure, the stable helper error code and records are retained while the artifact
stays invalid. Even if earlier citations resolved, no partially resolved output
becomes a successful profile. The raw response is never rewritten or rehashed as
if it originally contained offsets. Resolved settings and the unknown-setting
guard from v1 remain unchanged.

## Reproduction and checks

```sh
python3 -m unittest tests.test_overnight_profiles_hypotheses
python3 -m unittest discover -s tests -t .
python3 docs/overnight/gio-profile-20261115/handoffs/08/build-fixture-002.py
```

The new generator produces 12 synthetic method/policy/cap cells and three explicit
failure examples: ambiguous, absent and legacy-offset quotations. It stores the
exact raw response alongside each artifact. Files are content-addressed and
written exclusively; identical existing files are verified without modification.
Run the old fixture generator only at its original code version. This v2 protocol
deliberately rejects the offset-bearing v1 extraction schema.

All verification uses invented text and a scripted local extractor. It establishes
provenance mechanics and failure visibility, not researcher fidelity, extraction
accuracy, useful research choices, or runtime performance. Semantic entailment,
correct preference comparisons and complete detection of conflicts remain
unverified. No live calls, private corpora, held-out labels or keys were used.

The changed shared contract bytes also change the common renderer identity.
Coordinator01 must register and freeze new runtime/profile hashes before any new
leased extraction. Existing profiles cannot silently migrate to this version.
